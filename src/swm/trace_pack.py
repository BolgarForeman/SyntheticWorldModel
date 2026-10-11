"""The printable hand-trace pack: one scenario's map, tables and timeline (§4.6; E8).

A one-page map (nodes with ids and class symbols, power lines and towers, the links within
layers, the switched-on couplings as arrows, the crew base, the storm's track and the damaged
elements) and four tables, each as PDF pages and as CSV:
- the nodes, with class, requirement, stocks with their hours, and failure mode per commodity;
- the dependencies, with supplier, consumer, commodity, κ and transfer form;
- the scenario's damage, with the gust or flood depth and the repair it needs;
- the reference run's timeline, hour by hour, with the crews' jobs: the saved reference run's
  own values, so the hand trace and the golden run cannot disagree.

The PDFs are written with a fixed producer, no creation date and no stream compression, so
they are identical on every platform. Needs the optional ``preview`` dependencies.

Spec: structure v0.10 §4.6 (printable hand-trace pack); Work Order 8, Part D; Emission ruling
sheet v0.2, E8.
"""

import io
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING

from swm.coordinates import domain_origin_m
from swm.dynamics.output import state_rows
from swm.dynamics.records import Run
from swm.recipe.schema import Layer
from swm.stages.buffers import BuffersResult
from swm.stages.couplings import CouplingsResult
from swm.stages.crews import CrewsResult
from swm.stages.layers import LayersResult
from swm.stages.repair import RepairResult
from swm.stages.requirements import RequirementsResult
from swm.stages.scenarios import ScenarioDamage
from swm.stages.storm import StormScenario
from swm.stages.strength import StrengthResult
from swm.stages.terrain import TerrainResult

if TYPE_CHECKING:
    from matplotlib.axes import Axes
    from matplotlib.figure import Figure

PRODUCER = "swm trace-pack"
MAP_MARGIN_KM = 4.0
"""White space around the nodes and the track on the hand-trace map (layout only)."""
ToKm = Callable[[tuple[float, float]], tuple[float, float]]
LINES_PER_PAGE = 58
LAYER_COLOURS = {
    Layer.POWER: "#d62728", Layer.TELECOM: "#9467bd", Layer.WATER: "#1f77b4",
    Layer.TRANSPORT: "#ff7f0e", Layer.FUEL: "#8c564b", Layer.HEALTHCARE: "#e377c2",
}  # fmt: skip


@dataclass(frozen=True)
class TraceInputs:
    """What the pack is drawn from."""

    scenario: int
    terrain: TerrainResult
    layers: LayersResult
    requirements: RequirementsResult
    couplings: CouplingsResult
    strength: StrengthResult
    buffers: BuffersResult
    crews: CrewsResult
    repair: RepairResult
    field: StormScenario
    damage: ScenarioDamage
    run: Run


@dataclass(frozen=True)
class TracePack:
    """The pack's PDFs and its tables as rows."""

    map_pdf: bytes
    tables_pdf: bytes
    tables: dict[str, list[dict[str, object]]]


def trace_pack(inputs: TraceInputs) -> TracePack:
    """Build the hand-trace pack for one scenario.

    Parameters
    ----------
    inputs : TraceInputs
        The world's stages, the scenario's storm field and damage, and its reference run.

    Returns
    -------
    TracePack
        The map, the tables as PDF pages, and the tables as rows for CSV.

    Spec: Work Order 8, D1-D3.
    """
    tables = {
        "nodes": node_rows(inputs),
        "dependencies": dependency_rows(inputs),
        "damage": damage_rows(inputs),
        "timeline": timeline_rows(inputs.run),
    }
    return TracePack(_map_pdf(inputs), _tables_pdf(inputs.scenario, tables), tables)


# --- Tables (D2) ----------------------------------------------------------------------------


def node_rows(inputs: TraceInputs) -> list[dict[str, object]]:
    """Return one row per node: class, requirement, stocks with hours, failure modes."""
    needs = inputs.requirements.by_id()
    stocks: dict[str, list[str]] = {}
    for reserve in inputs.buffers.reserves:
        stocks.setdefault(reserve.node_id, []).append(f"{reserve.kind} {reserve.hours:.1f} h")
    modes: dict[str, list[str]] = {}
    for mode in inputs.buffers.failure_modes:
        modes.setdefault(mode.node_id, []).append(f"{mode.supplier_layer.value}: {mode.mode}")
    rows: list[dict[str, object]] = []
    for node in sorted(inputs.layers.nodes, key=lambda n: n.node_id):
        need = needs[node.node_id]
        requirement = [
            f"{name} {value:g}"
            for name, value in (("MW", need.electricity_mw), ("m3/day", need.water_m3_per_day),
                                ("GJ/day", need.fuel_gj_per_day))
            if value is not None
        ]  # fmt: skip
        rows.append({
            "node": node.node_id,
            "class": node.node_class.value,
            "requirement": "; ".join(requirement),
            "stocks": "; ".join(sorted(stocks.get(node.node_id, []))),
            "failure_modes": "; ".join(sorted(modes.get(node.node_id, []))),
        })  # fmt: skip
    return rows


def dependency_rows(inputs: TraceInputs) -> list[dict[str, object]]:
    """Return one row per coupling edge: supplier, consumer, commodity, κ, transfer form."""
    kappa = {s.edge_id: s.kappa for s in inputs.strength.edges}
    return [
        {
            "edge": edge.edge_id,
            "supplier": edge.supplier_id,
            "consumer": edge.consumer_id,
            "commodity": edge.commodity,
            "kappa": round(kappa[edge.edge_id], 6),
            "transfer_form": edge.transfer_form,
            "switched_on": edge.switched_on,
        }
        for edge in sorted(inputs.couplings.edges, key=lambda e: e.edge_id)
    ]


def damage_rows(inputs: TraceInputs) -> list[dict[str, object]]:
    """Return the scenario's damaged elements: the gust or flood depth and the repair needed."""
    rows: list[dict[str, object]] = []
    for outcome in inputs.damage.failed_lines:
        rows.append({
            "element": outcome.line_id,
            "cause": "wind",
            "gust_m_per_s": round(outcome.peak_gust_m_per_s, 3),
            "flood_depth_m": None,
            "failure_points": outcome.failure_points,
            "repair": f"{outcome.crew_work_h:g} h of crew work",
        })  # fmt: skip
    permanent = {(p.node_id, p.damage_state): p for p in inputs.repair.permanent}
    for facility in inputs.damage.facilities:
        repair = permanent.get((facility.node_id, facility.damage_state.value))
        rows.append({
            "element": facility.node_id,
            "cause": "flood",
            "gust_m_per_s": None,
            "flood_depth_m": round(facility.flood_depth_m, 3),
            "failure_points": None,
            "repair": "unrepairable in the window" if repair is None else
                      f"{repair.lead_time_h:g} h lead, {repair.crew_work_h:g} h of crew work",
        })  # fmt: skip
    return rows


def timeline_rows(run: Run) -> list[dict[str, object]]:
    """Return the reference run's states and crew jobs hour by hour (its own values)."""
    per_hour = int(1.0 / run.step_h + 0.5)
    states = state_rows(run)
    rows = []
    for index in range(0, len(run.times), per_hour):
        row: dict[str, object] = dict(states[index])
        for crew, doing in run.crew_positions[index]:
            row[crew] = doing
        rows.append(row)
    return rows


# --- The map (D1) ---------------------------------------------------------------------------


def _map_pdf(inputs: TraceInputs) -> bytes:
    from matplotlib.figure import Figure

    figure = Figure(figsize=(11.69, 8.27))
    axes = figure.add_subplot()
    terrain, layers = inputs.terrain, inputs.layers
    side_km = terrain.grid.cells * terrain.grid.cell_size_m / 1000
    west_m, south_m = domain_origin_m(terrain.grid)

    def km(point: tuple[float, float]) -> tuple[float, float]:
        return (point[0] - west_m) / 1000, (point[1] - south_m) / 1000

    axes.contour(terrain.land.astype(float), levels=[0.5], colors="#888888", linewidths=0.6,
                 extent=(0, side_km, side_km, 0))  # fmt: skip
    damaged = {o.line_id for o in inputs.damage.failed_lines}
    damaged |= {f.node_id for f in inputs.damage.facilities}
    _links(axes, layers, km, damaged)
    _couplings(axes, inputs, km)
    xs = [km((n.x_m, n.y_m))[0] for n in layers.nodes]
    ys = [km((n.x_m, n.y_m))[1] for n in layers.nodes]
    nearest = _track(axes, inputs.field, side_km, (sum(xs) / len(xs), sum(ys) / len(ys)))
    if nearest is not None:
        # The frame reaches the track's closest point, so a storm passing offshore still shows.
        xs.append(nearest[0])
        ys.append(nearest[1])
    _nodes(axes, layers, km, damaged)
    for base in inputs.crews.bases:
        x, y = (base.column + 0.5) * terrain.grid.cell_size_m / 1000, side_km - (
            base.row + 0.5) * terrain.grid.cell_size_m / 1000  # fmt: skip
        axes.plot([x], [y], marker="*", color="black", markersize=14)
        axes.annotate(f"crew base {base.base_id}", (x, y), fontsize=7, xytext=(6, -10),
                      textcoords="offset points")  # fmt: skip
    axes.set_xlim(min(xs) - MAP_MARGIN_KM, max(xs) + MAP_MARGIN_KM)
    axes.set_ylim(min(ys) - MAP_MARGIN_KM, max(ys) + MAP_MARGIN_KM)
    axes.set_aspect("equal")
    axes.set_xlabel("km east")
    axes.set_ylabel("km north")
    axes.set_title(
        f"Hand-trace map, scenario {inputs.scenario}: nodes, lines and towers, links, the "
        "switched-on couplings (arrows), the crew base, the storm track; damage in red",
        fontsize=9,
    )
    return _pdf([figure])


def _links(axes: "Axes", layers: LayersResult, km: ToKm, damaged: set[str]) -> None:
    for link in layers.links:
        points = [km(p) for p in link.points]
        broken = link.link_id in damaged
        axes.plot([p[0] for p in points], [p[1] for p in points],
                  color="red" if broken else LAYER_COLOURS[link.layer],
                  linewidth=2.0 if link.layer == Layer.POWER else 0.9,
                  linestyle="--" if broken else "-", alpha=0.85)  # fmt: skip
    for line in layers.power_lines:
        points = [km(p) for p in line.tower_points]
        axes.plot([p[0] for p in points], [p[1] for p in points], linestyle="", marker=".",
                  markersize=2.5, color="black")  # fmt: skip


def _couplings(axes: "Axes", inputs: TraceInputs, km: ToKm) -> None:
    nodes = {n.node_id: n for n in inputs.layers.nodes}
    for edge in inputs.couplings.edges:
        if not edge.switched_on:
            continue
        start = km((nodes[edge.supplier_id].x_m, nodes[edge.supplier_id].y_m))
        end = km((nodes[edge.consumer_id].x_m, nodes[edge.consumer_id].y_m))
        axes.annotate("", xy=end, xytext=start, arrowprops={
            "arrowstyle": "-|>", "color": LAYER_COLOURS[edge.supplier_layer], "linewidth": 0.6,
            "alpha": 0.6, "shrinkA": 4, "shrinkB": 4})  # fmt: skip


def _track(
    axes: "Axes", field: StormScenario, side_km: float, centre: tuple[float, float]
) -> tuple[float, float] | None:
    """Draw the storm track; return its point closest to the nodes' centre, in map km."""
    track = field.track
    if track is None:
        return None
    (x, y), (east, south) = track.point_km, track.direction
    reach = 2 * side_km
    axes.plot([x - reach * east, x + reach * east],
              [side_km - (y - reach * south), side_km - (y + reach * south)],
              color="#1a9850", linewidth=1.4, label="storm track")  # fmt: skip
    # The map's y runs north, the track's south: its direction on the map is (east, -south).
    along = (centre[0] - x) * east + (centre[1] - (side_km - y)) * -south
    return x + along * east, side_km - y - along * south


def _nodes(axes: "Axes", layers: LayersResult, km: ToKm, damaged: set[str]) -> None:
    markers = {Layer.POWER: "s", Layer.TELECOM: "^", Layer.WATER: "o", Layer.TRANSPORT: "D",
               Layer.FUEL: "v", Layer.HEALTHCARE: "P"}  # fmt: skip
    for node in sorted(layers.nodes, key=lambda n: n.node_id):
        x, y = km((node.x_m, node.y_m))
        colour = "red" if node.node_id in damaged else LAYER_COLOURS[node.layer]
        axes.plot([x], [y], marker=markers[node.layer], color=colour, markersize=7,
                  markeredgecolor="black", markeredgewidth=0.5)  # fmt: skip
        label = f"{node.node_id.replace('SWM-', '')}\n{node.node_class.value}"
        axes.annotate(label, (x, y), fontsize=5.5, xytext=(5, 3), textcoords="offset points")


# --- PDF pages (D2, D3) ---------------------------------------------------------------------


def _tables_pdf(scenario: int, tables: Mapping[str, list[dict[str, object]]]) -> bytes:
    from matplotlib.figure import Figure

    figures = []
    for name, rows in tables.items():
        lines = _text_table(rows)
        for start in range(0, max(1, len(lines)), LINES_PER_PAGE):
            figure = Figure(figsize=(11.69, 8.27))
            page = start // LINES_PER_PAGE + 1
            figure.text(0.02, 0.97, f"Scenario {scenario}: {name} (page {page})", fontsize=10,
                        va="top")  # fmt: skip
            figure.text(0.02, 0.93, "\n".join(lines[start:start + LINES_PER_PAGE]), fontsize=5.2,
                        family="monospace", va="top")  # fmt: skip
            figures.append(figure)
    return _pdf(figures)


def _text_table(rows: Sequence[Mapping[str, object]]) -> list[str]:
    if not rows:
        return ["(none)"]
    columns = list(rows[0])
    cells = [[_text(row.get(c)) for c in columns] for row in rows]
    widths = [max(len(c), *(len(r[i]) for r in cells)) for i, c in enumerate(columns)]
    head = "  ".join(c.ljust(w) for c, w in zip(columns, widths, strict=True))
    return [head] + ["  ".join(v.ljust(w) for v, w in zip(r, widths, strict=True)) for r in cells]


def _text(value: object) -> str:
    return "" if value is None else str(value)


def _pdf(figures: Sequence["Figure"]) -> bytes:
    """Write figures as one PDF with fixed metadata and no stream compression (D3)."""
    import matplotlib
    from matplotlib.backends.backend_pdf import PdfPages

    buffer = io.BytesIO()
    with matplotlib.rc_context({"pdf.compression": 0, "svg.hashsalt": "swm"}):
        metadata = {"Creator": PRODUCER, "Producer": PRODUCER, "CreationDate": None}
        with PdfPages(buffer, metadata=metadata) as pages:
            for figure in figures:
                pages.savefig(figure)
    return buffer.getvalue()
