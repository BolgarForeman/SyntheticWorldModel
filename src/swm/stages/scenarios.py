"""Scenarios stage: what the storm damages in each scenario.

Given each scenario's wind and flood fields (the storm stage), every element fails independently
(structure v0.7 §4.3b):
- **overhead lines** fail by wind: the power layer's links, the power feeds from a substation to
  its consumers, and the telecom links. Each kilometre of a pole line fails or survives at its
  own local 3-second gust, from the stored per-km chance; a line is down if any kilometre
  fails, and each failed kilometre is a failure point. A line on transmission towers collapses
  with the stored tower chance at its peak gust, one failure point;
- **facilities** fail by flood only, when the water at the site passes their functional depth.
  The damage state follows the depth over the threshold, held to the recipe's cap.

Protection is the solver's: a protected element is read as undamaged. Every facility and every
overhead line is protectable. Nothing here runs time; the dynamics is Work Order 7.

At runtime only +, -, x, / and sqrt are used (§3); the fragility curves are stored tables.

Spec: structure v0.7 §4.3b; Work Order 6, Parts D, F and G; decision 0012.
"""

import math
from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum
from itertools import pairwise

import numpy as np
from numpy.typing import NDArray

from swm import rng
from swm.coordinates import cell_of
from swm.recipe.dependencies import Role
from swm.recipe.schema import DamageState, Hazard, Layer, NodeClass
from swm.rules.registry import Registry
from swm.stages.couplings import CouplingsResult
from swm.stages.layers import LayersResult, Link, _segment_cells
from swm.stages.roads import sub_polyline
from swm.stages.storm import (
    StormResult,
    StormScenario,
    _coast_distance_km,
    flood_threshold_m,
    signed_distance_km,
)
from swm.stages.terrain import TerrainResult
from swm.stages.topography import directional_factors, wind_direction

M_PER_KM = 1000.0

LENGTH_STEPS_PER_KM = 1024
"""Line lengths are taken in 1/1024 km (about 1 m), so (1 - p)^L needs only sqrt and products."""
ROOT_HALVINGS = 10
"""Square roots giving (1 - p)^(1/1024): 2^10 = LENGTH_STEPS_PER_KM."""

SUBSTATIONS = frozenset({NodeClass.DISTRIBUTION_SUBSTATION, NodeClass.TRANSMISSION_SUBSTATION})


class LineKind(StrEnum):
    """Which overhead lines the storm can bring down (§4.3b)."""

    POWER_LINK = "power_link"
    POWER_FEED = "power_feed"
    TELECOM_LINK = "telecom_link"


class Structure(StrEnum):
    """What carries an overhead line, which decides its fragility."""

    POLE = "pole"
    TOWER = "tower"


@dataclass(frozen=True)
class OverheadLine:
    """One overhead line: a layer link or a power feed."""

    line_id: str
    kind: LineKind
    structure: Structure
    from_id: str
    to_id: str
    points: tuple[tuple[float, float], ...]
    """EPSG:32710 metres."""
    length_km: float


@dataclass(frozen=True)
class Element:
    """One element the storm can damage, and whether protection can target it (F1)."""

    element_id: str
    kind: str
    """``facility`` or the line kind."""
    node_class: str | None
    structure: Structure | None
    length_km: float | None
    protectable: bool


@dataclass(frozen=True)
class LineOutcome:
    """One overhead line in one scenario: the gust that drove it, its chance, and the draw."""

    line_id: str
    peak_gust_m_per_s: float
    """The highest 3-second gust anywhere along the line, as read against its fragility curve
    (over the site's design factor for a tower designed for its site)."""
    failure_probability: float
    """The chance that the line is down: any kilometre failing, or its towers collapsing."""
    failed: bool
    failure_points: int
    failure_km: tuple[float, ...]
    """Where each failure point lies: km along the line from its first end (piece midpoints)."""
    crew_work_h: float
    """Crew work to restore it: the per-point crew work times its failure points."""


@dataclass(frozen=True)
class FacilityDamage:
    """One flood-damaged facility in one scenario."""

    node_id: str
    node_class: str
    flood_depth_m: float
    threshold_m: float
    depth_over_m: float
    damage_state: DamageState
    capped: bool
    """True if the depth called for a worse state than the recipe's cap."""


@dataclass(frozen=True)
class ScenarioDamage:
    """What one scenario damages."""

    index: int
    lines: tuple[LineOutcome, ...]
    """Every overhead line, failed or not, with the field value that drove it."""
    facilities: tuple[FacilityDamage, ...]
    """Damaged facilities only."""

    @property
    def failed_lines(self) -> tuple[LineOutcome, ...]:
        """The lines that came down."""
        return tuple(line for line in self.lines if line.failed)


@dataclass(frozen=True)
class ScenariosResult:
    """The scenarios stage's output. Real but unobserved: never emitted."""

    elements: tuple[Element, ...]
    lines: tuple[OverheadLine, ...]
    scenarios: tuple[ScenarioDamage, ...]


@dataclass(frozen=True)
class DamageStreams:
    """One scenario's damage streams: a child stream per element, keyed by its stable id."""

    root_seed: int
    path: str

    def __call__(self, element_id: str) -> np.random.Generator:
        """Return the element's own damage stream in this scenario."""
        return rng.element_stream(self.root_seed, self.path, element_id)


def scenarios_streams(root_seed: int, scenarios: int) -> tuple[DamageStreams, ...]:
    """Return each scenario's damage streams.

    Parameters
    ----------
    root_seed : int
        The recipe's root seed.
    scenarios : int
        How many scenarios the recipe draws.

    Returns
    -------
    tuple of DamageStreams
        One per scenario, keyed by its index. Within a scenario each element draws from its
        own child stream, so adding or removing an element moves no other element's draws.

    Spec: Work Order 6, D3; PR 15 answers, 2.
    """
    base = f"shared_causes/{Hazard.STORM_CORRIDOR}"
    return tuple(DamageStreams(root_seed, f"{base}/{i}/damage") for i in range(scenarios))


def overhead_lines(layers: LayersResult, couplings: CouplingsResult) -> tuple[OverheadLine, ...]:
    """Return every overhead line: power and telecom links, then power feeds, in id order.

    Parameters
    ----------
    layers : LayersResult
        The layers: their links and node classes.
    couplings : CouplingsResult
        The couplings: the power feeds from substations to their consumers.

    Returns
    -------
    tuple of OverheadLine
        The lines, each with what carries it.

    Spec: structure v0.7 §4.3b (what the storm damages); Work Order 6, D1.
    """
    classes = {node.node_id: node.node_class for node in layers.nodes}
    lines = []
    for link in layers.links:
        if link.layer == Layer.POWER:
            # Every mapped power line runs on towers along its terrain route (§4.2).
            lines.append(_link_line(link, LineKind.POWER_LINK, Structure.TOWER))
        elif link.layer == Layer.TELECOM:
            lines.append(_link_line(link, LineKind.TELECOM_LINK, Structure.POLE))
    for edge in couplings.edges:
        if edge.supplier_layer != Layer.POWER or edge.role != Role.PRIMARY_SUPPLY:
            continue
        supplier = classes[edge.supplier_id]
        if supplier not in SUBSTATIONS:
            continue
        # Feeds run on poles along their road route (§4.2; Work Order 6c, B1).
        route = edge.route or edge.points
        length_km = edge.route_km if edge.route_km is not None else edge.length_km
        lines.append(OverheadLine(edge.edge_id, LineKind.POWER_FEED, Structure.POLE,
                                  edge.supplier_id, edge.consumer_id, route,
                                  length_km))  # fmt: skip
    return tuple(lines)


def build_scenarios(
    cap: DamageState,
    storm: StormResult,
    terrain: TerrainResult,
    layers: LayersResult,
    couplings: CouplingsResult,
    rules: Registry,
    streams: Sequence[DamageStreams],
) -> ScenariosResult:
    """Draw what each scenario damages: overhead lines by wind, facilities by flood.

    Parameters
    ----------
    cap : DamageState
        The worst state a facility can take (recipe ``shared_causes.facility_damage_cap``).
    storm : StormResult
        Each scenario's wind (10-minute, m/s) and flood depth (m).
    terrain : TerrainResult
        The ground: land and grid, for the gust factor and for reading lines' cells.
    layers : LayersResult
        The layers: nodes and links.
    couplings : CouplingsResult
        The couplings: the power feeds.
    rules : Registry
        The modeling rules in force.
    streams : sequence of DamageStreams
        Each scenario's damage streams, one per element.

    Returns
    -------
    ScenariosResult
        The elements with their protectability, the overhead lines, and each scenario's
        line outcomes and damaged facilities.

    Spec: structure v0.7 §4.3b; Work Order 6, D1-D3 and F1.
    """
    lines = overhead_lines(layers, couplings)
    reader = _LineReader(terrain, rules)
    pieces = [reader.pieces(line) for line in lines]
    damaged = []
    for scenario, stream in zip(storm.scenarios, streams, strict=True):
        gusts = {s: reader.gust(scenario, s).ravel() for s in Structure}
        outcomes = [
            _line_outcome(
                line,
                line_pieces,
                gusts[line.structure],
                reader,
                crew_work_per_point_h(line, rules),
                stream(line.line_id),
            )
            for line, line_pieces in zip(lines, pieces, strict=True)
        ]
        facilities = _flooded(scenario.flood_depth_m, layers, rules, cap)
        damaged.append(ScenarioDamage(scenario.index, tuple(outcomes), tuple(facilities)))
    return ScenariosResult(_elements(layers, lines, rules), lines, tuple(damaged))


def _link_line(link: Link, kind: LineKind, structure: Structure) -> OverheadLine:
    return OverheadLine(
        link.link_id, kind, structure, link.from_id, link.to_id, link.points, link.length_km
    )


# --- Overhead lines (D1) --------------------------------------------------------------------


class _LineReader:
    """The gust field, the cells each line crosses, and its failure chance."""

    def __init__(self, terrain: TerrainResult, rules: Registry) -> None:
        self.grid = terrain.grid
        factors = rules.value("storm.gust_factors")
        coast, inland = float(factors["coast"]), float(factors["inland"])
        transition = float(rules.value("storm.sea_to_land")["transition_km"])
        land = np.asarray(terrain.land)
        distance = _coast_distance_km(land, terrain.grid.cell_size_m / 1000, transition)
        # CHOICE: the gust factor ramps from the coast's to the inland value over the same
        # first km inland as the sea-to-land drop; sea cells take the coast factor.
        share = np.where(land, np.minimum(distance, transition) / transition, 0.0)
        self.factor = coast + (inland - coast) * share
        line = rules.value("storm.line_fragility_table")
        tower = rules.value("storm.tower_fragility_table")
        self.line_table = (tuple(line["gust_m_per_s"]), tuple(line["failures_per_km"]))
        self.tower_table = (tuple(tower["gust_m_per_s"]), tuple(tower["collapse"]))
        heights = rules.value("storm.line_heights_m")
        # The ridge and hill speed-up at each structure's height, for each of the eight wind
        # directions (§4.3b; Work Order 6c, C2; PR 14 answer 1).
        self.directional = {
            structure: directional_factors(terrain, rules, float(heights[structure.value]))
            for structure in Structure
        }
        self.sense = _rotation_sense(str(rules.value("storm.rotation")))
        # The factor on the wind is held to the ceiling calibrated on Taiwan's gust record
        # (PR 14 second answers, 1); the tower design factor below is the code's, uncapped.
        self.ceiling = rules.number("storm.ridge_factor_ceiling")
        # A tower designed for its site is built to the code's worst-direction factor there,
        # so it reads its gust divided by that factor (PR 14 answer 2).
        designed = bool(rules.value("storm.towers_designed_for_site"))
        self.design = {
            structure: self.directional[structure].max(axis=0)
            if designed and structure == Structure.TOWER
            else np.ones(land.shape)
            for structure in Structure
        }

    def ridge(self, scenario: StormScenario, structure: Structure) -> NDArray[np.float64]:
        """Return each cell's ridge factor for the direction the scenario's wind blows there.

        To the right of the track a counterclockwise storm's wind travels along the track, to
        the left against it; within the radius of maximum wind a place meets the eyewall from
        both sides and takes the worse of the two (§4.3b, PR 14 answer 1). The factor is held
        to ``storm.ridge_factor_ceiling`` (PR 14 second answers, 1).
        """
        factors = self.directional[structure]
        track = scenario.track
        if track is None:
            return np.ones(factors.shape[1:])
        east, south = track.direction
        # CHOICE: the wind's inflow angle across the isobars is neglected: it travels parallel
        # to the track (PR 14 answer 1).
        along = factors[wind_direction((self.sense * south, self.sense * east))]
        against = factors[wind_direction((-self.sense * south, -self.sense * east))]
        offset = signed_distance_km(track, self.grid.cell_size_m)
        eyewall = np.abs(offset) <= track.radius_max_wind_km
        one_side = np.where(offset > 0.0, along, against)
        worse = np.where(eyewall, np.maximum(along, against), one_side)
        ridge: NDArray[np.float64] = np.minimum(worse, self.ceiling)
        return ridge

    def gust(self, scenario: StormScenario, structure: Structure) -> NDArray[np.float64]:
        """Return the 3-second gust each structure is read at, against its fragility curve.

        The 10-minute wind times the gust factor and the ridge factor at the structure's
        height, over the factor a tower designed for its site is built to (1 otherwise).
        """
        speed_up = self.ridge(scenario, structure) / self.design[structure]
        gust: NDArray[np.float64] = scenario.wind_m_per_s * self.factor * speed_up
        return gust

    def cells(self, line: OverheadLine) -> NDArray[np.int64]:
        """Return the flat indices of the grid cells the line's polyline crosses."""
        return self._cells_of(line.points)

    def _cells_of(self, points: Sequence[tuple[float, float]]) -> NDArray[np.int64]:
        corners = [cell_of(x, y, self.grid) for x, y in points]
        crossed: list[int] = []
        for start, end in pairwise(corners):
            crossed += _segment_cells(start, end)
        return np.array(sorted(set(crossed)), dtype=np.int64)

    def pieces(self, line: OverheadLine) -> list["_Piece"]:
        """Split the line into whole kilometres along its route; the last piece is the rest."""
        return [
            _Piece(km.start_km, km.end_km, self._cells_of(km.points)) for km in kilometres(line)
        ]

    def piece_probability(self, gust: float, length_km: float) -> float:
        """Return a pole-line piece's chance of failing at its local gust: 1 - (1 - p)^length."""
        per_km = _interpolate(self.line_table, gust)
        return 1.0 - _power(1.0 - per_km, length_km)

    def tower_probability(self, gust: float) -> float:
        """Return a towered line's chance of collapsing at its peak gust."""
        # CHOICE: a towered line collapses once per line at its peak gust; §4.3b gives no
        # towers-per-km.
        return _interpolate(self.tower_table, gust)


def _rotation_sense(rotation: str) -> float:
    """Return +1 if the wind right of the track travels with it (counterclockwise), else -1."""
    senses = {"counterclockwise": 1.0, "clockwise": -1.0}
    if rotation not in senses:
        raise ValueError(f"storm.rotation must be one of {sorted(senses)}, not {rotation!r}")
    return senses[rotation]


@dataclass(frozen=True)
class _Piece:
    """One kilometre of a line (the last may be shorter), and the cells it crosses."""

    start_km: float
    end_km: float
    cells: NDArray[np.int64]


def _line_outcome(
    line: OverheadLine,
    pieces: Sequence[_Piece],
    gust: NDArray[np.float64],
    reader: _LineReader,
    work_h: float,
    stream: np.random.Generator,
) -> LineOutcome:
    """Draw one line in one scenario: kilometre by kilometre on poles, once on towers."""
    peak = max(float(gust[piece.cells].max()) for piece in pieces)
    if line.structure == Structure.TOWER:
        chance = reader.tower_probability(peak)
        failed = float(stream.random()) < chance
        points = (round(line.length_km / 2, 6),) if failed else ()
        return LineOutcome(line.line_id, peak, chance, failed, len(points), points,
                           work_h * len(points))  # fmt: skip
    survive = 1.0
    points_km = []
    # Every piece draws, so a piece's draw never depends on another's chance.
    for piece in pieces:
        local = float(gust[piece.cells].max())
        chance = reader.piece_probability(local, piece.end_km - piece.start_km)
        survive *= 1.0 - chance
        if float(stream.random()) < chance:
            points_km.append((piece.start_km + piece.end_km) / 2)
    return LineOutcome(line.line_id, peak, 1.0 - survive, bool(points_km), len(points_km),
                       tuple(points_km), work_h * len(points_km))  # fmt: skip


def crew_work_per_point_h(line: OverheadLine, rules: Registry) -> float:
    """Return the crew work per failure point of a line: a pole-line km or a tower collapse.

    Parameters
    ----------
    line : OverheadLine
        The line.
    rules : Registry
        The modeling rules in force.

    Returns
    -------
    float
        Hours of crew work for each failure point (6 h on poles, 72 h for a collapsed tower).

    Spec: structure v0.7 §4.3b (overhead lines: repair); decision 0012, second addendum.
    """
    if line.structure == Structure.TOWER:
        return rules.number("storm.tower_crew_work_h")
    return rules.number("storm.line_crew_work_h")


def _length_m(a: tuple[float, float], b: tuple[float, float]) -> float:
    dx, dy = b[0] - a[0], b[1] - a[1]
    return math.sqrt(dx * dx + dy * dy)


@dataclass(frozen=True)
class Kilometre:
    """One kilometre of a line along its route (the last may be shorter)."""

    index: int
    start_km: float
    end_km: float
    points: tuple[tuple[float, float], ...]
    """Its stretch of the route, EPSG:32710 metres."""

    @property
    def midpoint(self) -> tuple[float, float]:
        """The point halfway along this kilometre."""
        steps = [_length_m(a, b) for a, b in pairwise(self.points)]
        half = math.fsum(steps) / 2
        middle = sub_polyline(self.points, steps, half, half)
        return middle[0]


def kilometres(line: OverheadLine) -> list[Kilometre]:
    """Split a line into whole kilometres along its route, the last piece being the rest.

    Parameters
    ----------
    line : OverheadLine
        The line.

    Returns
    -------
    list of Kilometre
        Each kilometre's span along the line and its stretch of the route.

    Spec: structure v0.8 §4.3b (lines by the kilometre); Work Order 6c, C1 and D1.
    """
    steps = [_length_m(a, b) for a, b in pairwise(line.points)]
    total_m = math.fsum(steps)
    count = max(1, math.ceil(total_m / M_PER_KM - 1e-9))
    pieces = []
    for k in range(count):
        start_m, end_m = k * M_PER_KM, min((k + 1) * M_PER_KM, total_m)
        points = tuple(sub_polyline(line.points, steps, start_m, end_m))
        pieces.append(Kilometre(k, start_m / M_PER_KM, end_m / M_PER_KM, points))
    return pieces


def _interpolate(table: tuple[Sequence[float], Sequence[float]], x: float) -> float:
    """Interpolate a stored table linearly; beyond its ends, hold the end values."""
    knots, values = table
    if x <= knots[0]:
        return float(values[0])
    for i in range(len(knots) - 1):
        if x <= knots[i + 1]:
            share = (x - knots[i]) / (knots[i + 1] - knots[i])
            return float(values[i] + share * (values[i + 1] - values[i]))
    return float(values[-1])


def _power(base: float, exponent_km: float) -> float:
    """Return base ** exponent for an exponent in 1/1024 steps, with sqrt and products only."""
    steps = int(exponent_km * LENGTH_STEPS_PER_KM + 0.5)
    root = base
    for _ in range(ROOT_HALVINGS):
        root = math.sqrt(root)
    result = 1.0
    while steps:
        if steps & 1:
            result *= root
        root *= root
        steps >>= 1
    return result


# --- Facilities (D2) ------------------------------------------------------------------------


def _flooded(
    depth_m: NDArray[np.float64], layers: LayersResult, rules: Registry, cap: DamageState
) -> list[FacilityDamage]:
    order = list(DamageState)
    damaged = []
    for node in layers.nodes:
        threshold = flood_threshold_m(node.node_class.value, rules)
        depth = float(depth_m[node.row, node.column])
        if threshold is None or depth <= threshold:
            continue
        over = depth - threshold
        state = damage_state(over, rules)
        held = order[min(order.index(state), order.index(cap))]
        damaged.append(
            FacilityDamage(
                node.node_id, node.node_class.value, depth, threshold, over, held, held != state
            )
        )
    return damaged


def damage_state(over_m: float, rules: Registry) -> DamageState:
    """Return the damage state for a flood depth over a facility's threshold.

    Parameters
    ----------
    over_m : float
        Depth over the functional threshold, in m (positive).
    rules : Registry
        The modeling rules in force: the depth cuts.

    Returns
    -------
    DamageState
        Up to 0.5 m slight, above 0.5 m moderate, above 1.5 m extensive, above 3 m complete.

    Spec: structure v0.7 §4.3b (flood).
    """
    cuts = rules.value("storm.flood_damage_states_m")
    state = DamageState.SLIGHT
    for candidate in DamageState:
        if over_m > float(cuts[candidate.value]):
            state = candidate
    return state


# --- Elements and records (F1, G2) ----------------------------------------------------------


def _elements(
    layers: LayersResult, lines: Sequence[OverheadLine], rules: Registry
) -> tuple[Element, ...]:
    """Return every facility and overhead line, all protectable.

    Road junctions and rail nodes are not facilities (decision 0011, addendum).
    """
    not_facilities = set(rules.value("repair.no_repair_rows"))
    elements = [
        Element(node.node_id, "facility", node.node_class.value, None, None, True)
        for node in layers.nodes
        if node.node_class.value not in not_facilities
    ]
    elements += [
        Element(line.line_id, line.kind.value, None, line.structure, line.length_km, True)
        for line in lines
    ]
    return tuple(elements)


def scenarios_tables(result: ScenariosResult) -> dict[str, list[dict[str, object]]]:
    """Return the elements and each scenario's outcomes as plain data, for canonical output.

    Parameters
    ----------
    result : ScenariosResult
        The scenarios stage's output.

    Returns
    -------
    dict
        Tables by name, numbers rounded to six decimals.

    Spec: Work Order 6, D3 and F1.
    """

    def plain(record: object, **extra: object) -> dict[str, object]:
        row: dict[str, object] = dict(extra)
        for name, value in vars(record).items():
            if isinstance(value, float):
                value = round(value, 6)
            elif isinstance(value, StrEnum):
                value = value.value
            elif name == "points":
                continue
            row[name] = value
        return row

    return {
        "elements": [plain(e) for e in result.elements],
        "line_outcomes": [
            plain(line, scenario=s.index) for s in result.scenarios for line in s.lines
        ],
        "facility_damage": [
            plain(damage, scenario=s.index) for s in result.scenarios for damage in s.facilities
        ],
    }


def statistics_record(result: ScenariosResult) -> dict[str, object]:
    """Return, per scenario, failed lines, km of line down and damaged facilities.

    Parameters
    ----------
    result : ScenariosResult
        The scenarios stage's output.

    Returns
    -------
    dict
        Plain data ready for canonical YAML.

    Spec: Work Order 6, G2.
    """
    lengths = {line.line_id: line.length_km for line in result.lines}
    kinds = {line.line_id: line.kind.value for line in result.lines}
    towers = {line.line_id for line in result.lines if line.structure == Structure.TOWER}
    total_km = math.fsum(lengths.values())
    scenarios = []
    shares = []
    for scenario in result.scenarios:
        failed = scenario.failed_lines
        by_kind: dict[str, int] = {}
        for line in failed:
            by_kind[kinds[line.line_id]] = by_kind.get(kinds[line.line_id], 0) + 1
        km_down = math.fsum(lengths[line.line_id] for line in failed)
        # CHOICE: a line that is down is out over its whole length (failed-or-working), so
        # the length lost counts every down line in full.
        share = km_down / total_km if total_km > 0.0 else 0.0
        shares.append(share)
        facilities: dict[str, dict[str, int]] = {}
        for damage in scenario.facilities:
            states = facilities.setdefault(damage.node_class, {})
            states[damage.damage_state.value] = states.get(damage.damage_state.value, 0) + 1
        scenarios.append(
            {
                "index": scenario.index,
                "failed_lines": len(failed),
                "failed_lines_by_kind": dict(sorted(by_kind.items())),
                "failure_points": sum(line.failure_points for line in failed),
                "towered_lines_down": sum(line.line_id in towers for line in failed),
                "line_km_down": round(km_down, 3),
                "line_length_share_down": round(share, 6),
                "line_crew_work_h": round(math.fsum(line.crew_work_h for line in failed), 3),
                "failed_line_ids": [line.line_id for line in failed],
                "damaged_facilities": {
                    k: dict(sorted(v.items())) for k, v in sorted(facilities.items())
                },
                "damaged_facility_ids": [d.node_id for d in scenario.facilities],
                "damages_anything": bool(failed or scenario.facilities),
            }
        )
    return {
        "overhead_lines": _line_summary(result.lines),
        "protectable_elements": sum(e.protectable for e in result.elements),
        "mean_line_length_share_down": round(math.fsum(shares) / len(shares), 6) if shares else 0.0,
        "scenarios": scenarios,
    }


def _line_summary(lines: Sequence[OverheadLine]) -> dict[str, object]:
    summary: dict[str, object] = {}
    for kind in LineKind:
        chosen = [line for line in lines if line.kind == kind]
        summary[kind.value] = {
            "count": len(chosen),
            "on_towers": sum(line.structure == Structure.TOWER for line in chosen),
            "km": round(math.fsum(line.length_km for line in chosen), 3),
        }
    return summary
