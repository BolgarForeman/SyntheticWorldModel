"""Layers stage: every node of the six layers sited on the ground, with its links.

From the resolved recipe's layers section, the terrain result and the ``layers/*`` streams, the
stage sites each node, gives it a class and observed attributes, and builds each layer's own
links. Coordinates are EPSG:32710 metres anchored at Point Nemo. When a siting rule cannot be
met, the node goes to the best available site and a siting note says which rule was relaxed and
how; a class with no eligible land at all is an error (decision 0006).

Spec: structure v0.4 §4.1a, §4.2 and §5; Work Order 3, Part B.
"""

import heapq
import math
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from itertools import combinations, pairwise

import numpy as np
from numpy.typing import NDArray

from swm import rng
from swm.coordinates import cell_centre_m, to_lonlat
from swm.recipe.schema import (
    LAYER_NODE_CLASSES,
    SOURCE_SCOPES,
    Layer,
    Layers,
    LayerSettings,
    LayerState,
    NodeClass,
)
from swm.stages.terrain import (
    D8_OFFSETS,
    GRID_CELLS,
    SQRT_2,
    City,
    CoverClass,
    TerrainResult,
    _chessboard_distance,
    _dilate,
    _label_land,
)

# CHOICE: layers are sited in this order, so later rules can refer to earlier nodes (the
# seaport's city, the generation plants, the reservoirs).
SITING_ORDER = (
    Layer.TRANSPORT,
    Layer.WATER,
    Layer.POWER,
    Layer.FUEL,
    Layer.TELECOM,
    Layer.HEALTHCARE,
)

LAYER_CODES: Mapping[Layer, str] = {
    Layer.POWER: "POW",
    Layer.TELECOM: "TEL",
    Layer.WATER: "WAT",
    Layer.TRANSPORT: "TRN",
    Layer.FUEL: "FUE",
    Layer.HEALTHCARE: "HLT",
}
"""Layer codes in synthetic identifiers, such as SWM-POW-0001 (Work Order 3, B6)."""

TREE_LAYERS = frozenset({Layer.WATER, Layer.FUEL})
"""Layers whose signature is a tree: they stop at n - 1 links (decision 0006)."""

WEIGHT_RESOLUTION = 1_000_000
"""Siting weights are quantised to integers at this resolution, so draws are exact."""


@dataclass(frozen=True)
class ClassShare:
    """One class's share of a layer's nodes."""

    node_class: NodeClass
    share: float
    backbone: bool


# CHOICE: placeholder (open decision: realism ranges). Backbone classes get one node each, in
# order, while the count allows; the rest go by largest shortfall against the shares. At four
# nodes per layer this gives the pilot composition ruled on 2026-09-28.
COMPOSITION: Mapping[Layer, tuple[ClassShare, ...]] = {
    Layer.POWER: (
        ClassShare(NodeClass.GENERATION, 0.2, True),
        ClassShare(NodeClass.TRANSMISSION_SUBSTATION, 0.2, True),
        ClassShare(NodeClass.DISTRIBUTION_SUBSTATION, 0.6, True),
    ),
    Layer.TELECOM: (
        ClassShare(NodeClass.EXCHANGE, 0.1, True),
        ClassShare(NodeClass.MAST, 0.8, True),
        ClassShare(NodeClass.DATA_CENTRE, 0.05, False),
        ClassShare(NodeClass.CABLE_LANDING, 0.05, False),
    ),
    Layer.WATER: (
        ClassShare(NodeClass.RESERVOIR, 0.25, True),
        ClassShare(NodeClass.TREATMENT, 0.25, True),
        ClassShare(NodeClass.PUMPING, 0.25, True),
        ClassShare(NodeClass.STORAGE, 0.25, True),
    ),
    Layer.TRANSPORT: (
        ClassShare(NodeClass.SEAPORT, 0.1, True),
        ClassShare(NodeClass.AIRPORT, 0.1, True),
        ClassShare(NodeClass.FREIGHT_YARD, 0.1, True),
        ClassShare(NodeClass.BRIDGE, 0.1, True),
        ClassShare(NodeClass.ROAD_JUNCTION, 0.6, False),
    ),
    Layer.FUEL: (
        ClassShare(NodeClass.IMPORT_TERMINAL, 0.1, True),
        ClassShare(NodeClass.TANK_FARM, 0.15, True),
        ClassShare(NodeClass.DEPOT, 0.7, True),
        ClassShare(NodeClass.REFINERY, 0.05, False),
    ),
    Layer.HEALTHCARE: (
        ClassShare(NodeClass.TERTIARY, 0.1, True),
        ClassShare(NodeClass.REGIONAL, 0.15, True),
        ClassShare(NodeClass.CLINIC, 0.65, True),
        ClassShare(NodeClass.BLOOD_BANK, 0.1, True),
    ),
}


# CHOICE: every siting distance and threshold below (Work Order 3, B3; decision 0006).
@dataclass(frozen=True)
class SitingMappings:
    """Distances and thresholds the siting rules use."""

    near_city_km: float = 3.0
    """Generation, import terminals and freight yards sit within this of their city (km)."""
    beside_city_km: float = 1.0
    """Distribution substations sit in or within this of a city (km)."""
    storage_beside_city_km: float = 1.5
    """Water storage sits within this of a city's edge, outside it (km)."""
    seaport_city_km: float = 2.0
    """Seaports sit on the coast within this of their city (km)."""
    shelter_radius_cells: int = 4
    """Half-width of the window over which a coast cell's shelter is measured (cells)."""
    corridor_km: float = 1.5
    """Transmission and pumping sit within this of the line they lie between (km)."""
    corridor_middle_share: float = 0.5
    """...and in the middle share of that line, away from both ends (ratio)."""
    upland_share: float = 0.35
    """Uplands: at or above this share of the island's highest point (ratio)."""
    treatment_gap_cells: int = 3
    """Treatment sits at least this far downstream of its reservoir (cells)."""
    tank_farm_km: float = 2.0
    """Tank farms sit within this of their import terminal (km)."""
    refinery_km: float = 5.0
    """Refineries sit on the coast within this of an import terminal (km)."""
    mast_spacing_km: float = 2.0
    """Masts sit at least this far from other telecom nodes (km)."""
    clinic_spacing_km: float = 2.0
    """Clinics sit at least this far from other healthcare nodes (km)."""
    runway_km: float = 2.5
    """An airport needs a straight flat run at least this long (km; decision 0006)."""
    runway_grade: float = 0.02
    """...whose height varies by no more than this share of its length (ratio)."""
    runway_city_km: float = 5.0
    """...with its middle within this of a city (km)."""
    flat_slope: float = 0.06
    """Flat ground for freight yards: slope at or below this (m/m)."""
    freight_road_km: float = 0.5
    """Freight yards weigh closeness to the main road on this scale (km)."""
    waypoint_candidates: int = 4_000
    """Land waypoints tried, shortest first, before a road falls back to the grid (count)."""


SITING = SitingMappings()


# CHOICE: placeholder (open decision: realism ranges). Taiwan placeholders for the voltages
# (Taipower's levels). Ranges scale with the served city's size relative to the largest city.
ATTRIBUTE_RANGES: Mapping[NodeClass, Mapping[str, tuple[float, float]]] = {
    NodeClass.GENERATION: {"capacity_mw": (50.0, 1_500.0)},
    NodeClass.TRANSMISSION_SUBSTATION: {"capacity_mva": (200.0, 1_000.0)},
    NodeClass.DISTRIBUTION_SUBSTATION: {"capacity_mva": (10.0, 100.0)},
    NodeClass.RESERVOIR: {"storage_m3": (1.0e6, 5.0e7)},
    NodeClass.TREATMENT: {"capacity_m3_per_day": (1.0e4, 5.0e5)},
    NodeClass.PUMPING: {"capacity_m3_per_day": (5.0e3, 2.0e5)},
    NodeClass.STORAGE: {"storage_m3": (5.0e3, 1.0e5)},
    NodeClass.FREIGHT_YARD: {"area_m2": (1.0e4, 2.0e5)},
    NodeClass.BRIDGE: {"length_m": (30.0, 300.0)},
    NodeClass.IMPORT_TERMINAL: {"storage_m3": (1.0e5, 1.0e6)},
    NodeClass.TANK_FARM: {"storage_m3": (5.0e4, 5.0e5)},
    NodeClass.DEPOT: {"storage_m3": (1.0e3, 2.0e4)},
    NodeClass.REFINERY: {"storage_m3": (1.0e5, 1.0e6)},
    NodeClass.TERTIARY: {"bed_count": (500.0, 2_000.0)},
    NodeClass.REGIONAL: {"bed_count": (200.0, 600.0)},
    NodeClass.CLINIC: {"bed_count": (0.0, 20.0)},
}
"""Numeric attribute ranges per class, with the unit in each name."""

TRANSMISSION_VOLTAGES_KV = ((0.6, 345.0), (0.25, 161.0), (0.0, 69.0))
"""Transmission voltage by served city share: (share at or above, kV). 69 kV serves small
loads. placeholder (open decision: realism ranges); Taipower's levels."""

DISTRIBUTION_VOLTAGES_KV = ((0.3, 22.8), (0.0, 11.4))
"""Distribution voltage by served city share: (share at or above, kV). Taipower's levels."""

AIRPORT_SIZES = ((0.66, "large_airport"), (0.33, "medium_airport"), (0.0, "small_airport"))
"""Airport size class by served city share, in OurAirports' own values."""

SEAPORT_SIZES = ((0.75, "L"), (0.5, "M"), (0.25, "S"), (0.0, "V"))
"""Seaport harbour size by served city share, in the World Port Index's values."""

FUEL_TYPES = (("gas", 0.5), ("coal", 0.3), ("oil", 0.2))
"""Thermal generation fuel types and their draw weights. placeholder (open decision)."""

TELECOM_OPERATORS = ("SWM Telecom A", "SWM Telecom B")
"""Synthetic operator names, from a reserved list (CLAUDE.md §9)."""

OPERATIONAL = "operational"
"""Every node's status in Phase 1 (Work Order 3, B4)."""

AttributeValue = str | int | float


@dataclass(frozen=True)
class Node:
    """One sited node. Coordinates are EPSG:32710 metres; latitude and longitude WGS 84."""

    node_id: str
    layer: Layer
    node_class: NodeClass
    row: int
    column: int
    x_m: float
    y_m: float
    longitude: float
    latitude: float
    city_id: int
    attributes: tuple[tuple[str, AttributeValue], ...]
    runway: tuple[tuple[float, float], tuple[float, float]] | None


@dataclass(frozen=True)
class Link:
    """One intra-layer link. A straight link is a two-point polyline (EPSG:32710 metres)."""

    link_id: str
    layer: Layer
    from_id: str
    to_id: str
    points: tuple[tuple[float, float], ...]
    length_km: float
    river_crossings: int
    crosses_sea: bool


@dataclass(frozen=True)
class LayerStatistics:
    """Realised statistics of one layer."""

    layer: Layer
    state: LayerState
    class_counts: dict[str, int]
    link_count: int
    mean_links_per_node: float
    mean_spacing_km: float
    classes_without_source: tuple[str, ...]
    notes: tuple[str, ...]


@dataclass(frozen=True)
class LayersResult:
    """The layers stage's output."""

    nodes: tuple[Node, ...]
    links: tuple[Link, ...]
    states: dict[Layer, LayerState]
    statistics: tuple[LayerStatistics, ...]


@dataclass(frozen=True)
class LayersStreams:
    """The layers streams. The stage can reach no other stream."""

    siting: Mapping[Layer, np.random.Generator]
    attributes: Mapping[Layer, np.random.Generator]
    dual_membership: np.random.Generator


def layers_streams(root_seed: int) -> LayersStreams:
    """Return the ``layers/*`` streams the stage draws from.

    Parameters
    ----------
    root_seed : int
        The recipe's root seed.

    Returns
    -------
    LayersStreams
        Siting and attribute streams per layer, and the dual-membership stream.

    Spec: structure v0.4 §3 (independent random streams); Work Order 3, B1.
    """
    return LayersStreams(
        siting={layer: rng.stream(root_seed, f"layers/{layer}/siting") for layer in Layer},
        attributes={layer: rng.stream(root_seed, f"layers/{layer}/attributes") for layer in Layer},
        dual_membership=rng.stream(root_seed, "layers/dual_membership"),
    )


def class_counts(layer: Layer, node_count: int) -> dict[NodeClass, int]:
    """Split a layer's node count across its classes by the composition table.

    Parameters
    ----------
    layer : Layer
        The layer.
    node_count : int
        Nodes in the layer.

    Returns
    -------
    dict
        Nodes per class, in table order.

    Spec: Work Order 3, B2.
    """
    shares = COMPOSITION[layer]
    counts = dict.fromkeys((share.node_class for share in shares), 0)
    remaining = node_count
    for share in shares:
        if share.backbone and remaining > 0:
            counts[share.node_class] += 1
            remaining -= 1
    while remaining > 0:
        shortfalls = [share.share * node_count - counts[share.node_class] for share in shares]
        best = max(range(len(shares)), key=lambda i: (shortfalls[i], -i))
        counts[shares[best].node_class] += 1
        remaining -= 1
    return counts


def build_layers(layers: Layers, terrain: TerrainResult, streams: LayersStreams) -> LayersResult:
    """Site every node of every layer that is not off, and build each layer's links.

    Parameters
    ----------
    layers : Layers
        The resolved recipe's layers section (node counts filled in).
    terrain : TerrainResult
        The terrain stage's output.
    streams : LayersStreams
        The layers streams.

    Returns
    -------
    LayersResult
        Node and link tables, layer states and realised statistics with siting notes.

    Spec: structure v0.4 §4.2; Work Order 3, Part B; decision 0006.
    """
    ground = _Ground.from_terrain(terrain)
    siter = _Siter(ground)
    for layer in SITING_ORDER:
        settings = layers.get(layer)
        if settings.state == LayerState.OFF:
            continue
        if settings.node_count is None:
            raise ValueError("build_layers needs a resolved recipe: node counts are not set")
        dual = layers.dual_membership and layer == Layer.POWER
        siter.site_layer(layer, settings.node_count, streams.siting[layer], dual, streams)
    nodes: list[Node] = []
    links: list[Link] = []
    statistics: list[LayerStatistics] = []
    for layer in Layer:
        settings = layers.get(layer)
        if settings.state == LayerState.OFF:
            continue
        layer_nodes = _make_nodes(layer, siter, ground, streams.attributes[layer])
        builder = _LinkBuilder(layer, layer_nodes, siter, ground, settings.links_per_node)
        layer_links = builder.build()
        nodes.extend(layer_nodes)
        links.extend(layer_links)
        notes = siter.notes.get(layer, []) + builder.notes
        statistics.append(_statistics(layer, settings, layer_nodes, layer_links, notes))
    states = {layer: layers.get(layer).state for layer in Layer}
    return LayersResult(tuple(nodes), tuple(links), states, tuple(statistics))


def node_table(result: LayersResult) -> list[dict[str, object]]:
    """Return the node table as plain data in a fixed key order, for canonical output.

    Parameters
    ----------
    result : LayersResult
        The layers stage's output.

    Returns
    -------
    list of dict
        One row per node, coordinates rounded to the centimetre.

    Spec: Work Order 3, B7 and C3.
    """
    return [
        {
            "id": node.node_id,
            "layer": node.layer.value,
            "class": node.node_class.value,
            "x_m": round(node.x_m, 2),
            "y_m": round(node.y_m, 2),
            "longitude": node.longitude,
            "latitude": node.latitude,
            "city_id": node.city_id,
            "attributes": dict(node.attributes),
            "runway_m": None
            if node.runway is None
            else [[round(x, 2), round(y, 2)] for x, y in node.runway],
        }
        for node in result.nodes
    ]


def link_table(result: LayersResult) -> list[dict[str, object]]:
    """Return the link table as plain data in a fixed key order, for canonical output.

    Parameters
    ----------
    result : LayersResult
        The layers stage's output.

    Returns
    -------
    list of dict
        One row per link, with its polyline rounded to the centimetre.

    Spec: Work Order 3, B7 and C3; decision 0006.
    """
    return [
        {
            "id": link.link_id,
            "layer": link.layer.value,
            "from": link.from_id,
            "to": link.to_id,
            "length_km": link.length_km,
            "river_crossings": link.river_crossings,
            "crosses_sea": link.crosses_sea,
            "points_m": [[round(x, 2), round(y, 2)] for x, y in link.points],
        }
        for link in result.links
    ]


def statistics_record(result: LayersResult) -> dict[str, object]:
    """Return the realised statistics and siting notes per layer, in a fixed order.

    Parameters
    ----------
    result : LayersResult
        The layers stage's output.

    Returns
    -------
    dict
        Plain data ready for canonical YAML.

    Spec: Work Order 3, B7 and C3.
    """
    return {
        "layers": {
            stats.layer.value: {
                "state": stats.state.value,
                "nodes": sum(stats.class_counts.values()),
                "class_counts": dict(stats.class_counts),
                "links": stats.link_count,
                "mean_links_per_node": stats.mean_links_per_node,
                "mean_spacing_km": stats.mean_spacing_km,
                "classes_without_source": list(stats.classes_without_source),
                "notes": list(stats.notes),
            }
            for stats in result.statistics
        }
    }


# --- The ground the siting rules read -------------------------------------------------------


@dataclass
class _Ground:
    """What siting reads from the terrain, and which cells are taken."""

    terrain: TerrainResult
    land: NDArray[np.bool_]
    main_land: NDArray[np.bool_]
    river: NDArray[np.bool_]
    sea: NDArray[np.bool_]
    buildable: NDArray[np.bool_]
    coast: NDArray[np.bool_]
    elevation_m: NDArray[np.float64]
    height: NDArray[np.float64]
    slope: NDArray[np.float64]
    accumulation: NDArray[np.int32]
    downstream: NDArray[np.int64]
    cities: tuple[City, ...]
    rows: NDArray[np.int64]
    columns: NDArray[np.int64]
    occupied: NDArray[np.bool_]
    _city_distance: dict[int, NDArray[np.int64]] = field(default_factory=dict)

    @classmethod
    def from_terrain(cls, terrain: TerrainResult) -> "_Ground":
        land = np.asarray(terrain.land)
        river = np.asarray(terrain.river)
        wetland = np.asarray(terrain.land_cover) == CoverClass.WETLAND
        elevation_m = np.asarray(terrain.elevation_dm) / 10
        peak_m = max(float(elevation_m.max()), 0.1)
        labels, sizes = _label_land(land)
        main_land = labels == 1 + max(range(len(sizes)), key=lambda i: (sizes[i], -i))
        cells = np.arange(GRID_CELLS * GRID_CELLS)
        offsets = np.array([dr * GRID_CELLS + dc for dr, dc in D8_OFFSETS])
        direction = np.asarray(terrain.flow_direction).ravel()
        downstream = np.where(direction >= 0, cells + offsets[direction], -1)
        rows, columns = np.divmod(cells.reshape(GRID_CELLS, GRID_CELLS), GRID_CELLS)
        return cls(
            terrain=terrain,
            land=land,
            main_land=main_land,
            river=river,
            sea=~land,
            buildable=land & ~river & ~wetland,
            coast=land & _dilate(~land),
            elevation_m=elevation_m,
            height=elevation_m / peak_m,
            slope=_slope_m_per_m(np.asarray(terrain.elevation_dm), terrain.grid.cell_size_m),
            accumulation=np.asarray(terrain.flow_accumulation),
            downstream=downstream,
            cities=tuple(sorted(terrain.cities, key=lambda c: (-c.cell_count, c.city_id))),
            rows=rows,
            columns=columns,
            occupied=np.zeros_like(land),
        )

    def cells_for_km(self, km: float) -> int:
        return max(1, math.ceil(km * 1000 / self.terrain.grid.cell_size_m))

    def city_for(self, index: int) -> City:
        """Return the index-th city in size order, cycling: 0 is the largest."""
        return self.cities[index % len(self.cities)]

    def city_distance(self, city: City) -> NDArray[np.int64]:
        """Chessboard distance in cells to a city's footprint, capped at 64 cells."""
        if city.city_id not in self._city_distance:
            footprint = np.asarray(self.terrain.urban_id) == city.city_id
            self._city_distance[city.city_id] = _chessboard_distance(footprint, 64)
        return self._city_distance[city.city_id]

    def distance_to(self, row: int, column: int) -> NDArray[np.float64]:
        """Straight-line distance in cells from every cell to one cell."""
        dr = (self.rows - row).astype(np.float64)
        dc = (self.columns - column).astype(np.float64)
        return np.sqrt(dr * dr + dc * dc)

    def nearest_city(self, cell: int) -> City:
        row, column = divmod(cell, GRID_CELLS)
        return min(
            self.cities,
            key=lambda c: (
                (c.centre_row - row) ** 2 + (c.centre_column - column) ** 2,
                c.city_id,
            ),
        )

    def city_of(self, cell: int) -> City:
        """Return the city a cell lies in, or the nearest city."""
        urban = int(np.asarray(self.terrain.urban_id).flat[cell])
        for city in self.cities:
            if city.city_id == urban:
                return city
        return self.nearest_city(cell)


@dataclass
class _Sited:
    """A sited node before it becomes a table row."""

    node_class: NodeClass
    cell: int
    runway: tuple[int, int] | None = None
    dam_of: int | None = None
    river_accumulation: int = 0


class _Siter:
    """Sites every layer, keeping the notes and the cross-layer references the rules need."""

    def __init__(self, ground: _Ground) -> None:
        self.ground = ground
        self.sited: dict[Layer, list[_Sited]] = {}
        self.notes: dict[Layer, list[str]] = {}
        self.bridge_roads: dict[int, tuple[int, int]] = {}
        self.road_cache: dict[tuple[int, int], tuple[list[tuple[int, int]], bool]] = {}

    def of_class(self, node_class: NodeClass) -> list[_Sited]:
        return [s for nodes in self.sited.values() for s in nodes if s.node_class == node_class]

    def site_layer(
        self,
        layer: Layer,
        node_count: int,
        stream: np.random.Generator,
        dual: bool,
        streams: LayersStreams,
    ) -> None:
        self.sited[layer] = []
        self.notes[layer] = []
        rules = _RULES[layer]
        for node_class, count in class_counts(layer, node_count).items():
            for index in range(count):
                if dual and node_class == NodeClass.GENERATION and index == 0:
                    dam = self._hydro_dam(streams.dual_membership)
                    if dam is not None:
                        self.sited[layer].append(dam)
                        continue
                sited = rules[node_class](self, layer, index, stream)
                self.sited[layer].append(sited)

    def place(
        self,
        layer: Layer,
        node_class: NodeClass,
        rule: str,
        stream: np.random.Generator,
        strict: NDArray[np.bool_],
        weight: NDArray[np.float64],
        relaxed: NDArray[np.bool_] | None = None,
        relaxed_weight: NDArray[np.float64] | None = None,
        how_relaxed: str = "placed on the best available land",
    ) -> int:
        """Draw a cell for a node; relax the rule, with a note, only if it cannot be met."""
        ground = self.ground
        usable = self._usable(layer)
        cell = _draw_cell(stream, strict & usable, weight)
        if cell is None:
            fallback = usable if relaxed is None else relaxed & usable
            cell = _draw_cell(
                stream, fallback, weight if relaxed_weight is None else relaxed_weight
            )
            if cell is None:
                cell = _draw_cell(
                    stream, usable, weight if relaxed_weight is None else relaxed_weight
                )
            if cell is None:
                raise ValueError(f"no eligible land cell for {layer} {node_class}: {rule}")
            self.notes[layer].append(f"{node_class}: {rule} could not be met; {how_relaxed}")
        ground.occupied.flat[cell] = True
        return cell

    def _usable(self, layer: Layer) -> NDArray[np.bool_]:
        ground = self.ground
        # CHOICE: transport nodes sit on the main island; roads cannot cross the sea.
        land = ground.main_land if layer == Layer.TRANSPORT else ground.land
        return ground.buildable & land & ~ground.occupied

    def _hydro_dam(self, stream: np.random.Generator) -> _Sited | None:
        on_river = [r for r in self.of_class(NodeClass.RESERVOIR) if r.river_accumulation > 0]
        if not on_river:
            self.notes[Layer.POWER].append(
                "generation: dual membership is on but no reservoir sits on a river; "
                "no hydro dam, and generation is sited by its own rule"
            )
            return None
        chosen = on_river[int(stream.integers(0, len(on_river)))]
        return _Sited(NodeClass.GENERATION, chosen.cell, dam_of=chosen.cell)

    def road(self, start: int, end: int) -> tuple[list[tuple[int, int]], bool]:
        """Return a road's vertices (row, column) avoiding the sea, and whether it used the grid."""
        key = (min(start, end), max(start, end))
        if key not in self.road_cache:
            self.road_cache[key] = _road_route(self.ground, key[0], key[1])
        vertices, on_grid = self.road_cache[key]
        return (vertices if key[0] == start else vertices[::-1]), on_grid


# --- Siting rules ---------------------------------------------------------------------------

SitingRule = Callable[[_Siter, Layer, int, np.random.Generator], _Sited]


def _near(distance: NDArray[np.float64] | NDArray[np.int64], scale: float) -> NDArray[np.float64]:
    return 1.0 / (1.0 + np.asarray(distance, dtype=np.float64) / scale)


def _site_seaport(s: _Siter, layer: Layer, index: int, stream: np.random.Generator) -> _Sited:
    g = s.ground
    city = g.city_for(index)
    distance = g.city_distance(city)
    strict = g.coast & (distance <= g.cells_for_km(SITING.seaport_city_km))
    weight = _shelter(g) * _near(distance, g.cells_for_km(1.0))
    cell = s.place(
        layer,
        NodeClass.SEAPORT,
        "on the coast at a city",
        stream,
        strict,
        weight,
        relaxed=g.coast,
        how_relaxed="placed on the nearest sheltered coast instead",
    )
    return _Sited(NodeClass.SEAPORT, cell)


def _site_airport(s: _Siter, layer: Layer, index: int, stream: np.random.Generator) -> _Sited:
    g = s.ground
    usable = s._usable(layer)
    near_city = _any_city_distance(g) <= g.cells_for_km(SITING.runway_city_km)
    directions = _runway_directions(g, usable)
    qualifying = [
        (d, int(start))
        for d, runs in enumerate(directions)
        for start in np.flatnonzero(
            (runs.fits & runs.flat_enough & near_city[runs.middle_of]).ravel()
        )
    ]
    if qualifying:
        weights = [
            (1.0 - directions[d].range_m.flat[start] / directions[d].limit_m + 0.1)
            * float(1.0 / (1.0 + _any_city_distance(g)[directions[d].middle_of].flat[start] / 10.0))
            for d, start in qualifying
        ]
        d, start = qualifying[_draw_index(stream, weights)]
    else:
        candidates = [
            (float(runs.range_m.flat[start]) / runs.length_m, d, int(start))
            for d, runs in enumerate(directions)
            for start in np.flatnonzero(runs.fits.ravel())
        ]
        if not candidates:
            cell = s.place(
                layer,
                NodeClass.AIRPORT,
                "a straight flat run",
                stream,
                usable,
                _near(g.slope, 0.05),
                how_relaxed="no straight run fits on buildable land; placed on the flattest "
                "ground, with no runway line",
            )
            return _Sited(NodeClass.AIRPORT, cell)
        flat_enough = [c for c in candidates if c[0] <= SITING.runway_grade]
        if flat_enough:
            # Flat runs exist but none near a city: take the flat run nearest a city.
            city_km = _city_km(g)
            distance_km, d, start = min(
                (float(city_km[directions[d].middle_of].flat[start]), d, start)
                for _, d, start in flat_enough
            )
            s.notes[layer].append(
                f"airport: no {SITING.runway_km:g} km run within {SITING.runway_grade:.0%} "
                f"grade lies within {SITING.runway_city_km:g} km of a city; placed on the "
                f"nearest such run, {distance_km:.1f} km from a city centre"
            )
        else:
            grade, d, start = min(candidates)
            runs = directions[d]
            s.notes[layer].append(
                f"airport: no {SITING.runway_km:g} km run lies within "
                f"{SITING.runway_grade:.0%} grade; the flattest run varies "
                f"{runs.range_m.flat[start]:.0f} m over {runs.length_m / 1000:.2f} km "
                f"({grade:.1%})"
            )
    cells = directions[d].cells_from(start)
    for cell in cells:
        g.occupied.flat[cell] = True
    return _Sited(NodeClass.AIRPORT, cells[len(cells) // 2], runway=(cells[0], cells[-1]))


def _site_freight_yard(s: _Siter, layer: Layer, index: int, stream: np.random.Generator) -> _Sited:
    g = s.ground
    seaports = s.of_class(NodeClass.SEAPORT)
    port = seaports[index % len(seaports)].cell if seaports else None
    city = g.nearest_city(port) if port is not None else g.city_for(index)
    distance = g.city_distance(city)
    road_start, road_end = _main_road_ends(s, port)
    to_road = _segment_distance(g, road_start, road_end)[0]
    to_port = g.distance_to(*divmod(port, GRID_CELLS)) if port is not None else to_road
    near_city = distance <= g.cells_for_km(SITING.near_city_km)
    strict = near_city & (g.slope <= SITING.flat_slope)
    weight = _near(to_road, g.cells_for_km(SITING.freight_road_km)) * _near(to_port, 10.0)
    cell = s.place(
        layer,
        NodeClass.FREIGHT_YARD,
        "on flat land near the seaport's city",
        stream,
        strict,
        weight,
        relaxed=near_city,
        how_relaxed="placed on the least steep land near that city",
    )
    return _Sited(NodeClass.FREIGHT_YARD, cell)


def _site_bridge(s: _Siter, layer: Layer, index: int, stream: np.random.Generator) -> _Sited:
    g = s.ground
    free = ~g.occupied
    for start, end in _bridge_roads(s):
        vertices, _ = s.road(start, end)
        crossing = [c for c in _polyline_cells(vertices) if g.river.flat[c] and free.flat[c]]
        if crossing:
            weights = [math.sqrt(float(g.accumulation.flat[c])) for c in crossing]
            cell = crossing[_draw_index(stream, weights)]
            s.bridge_roads[cell] = (start, end)
            g.occupied.flat[cell] = True
            return _Sited(NodeClass.BRIDGE, cell, river_accumulation=int(g.accumulation.flat[cell]))
    return _relaxed_bridge(s, layer)


def _relaxed_bridge(s: _Siter, layer: Layer) -> _Sited:
    g = s.ground
    road_cells = sorted(
        {c for start, end in _bridge_roads(s) for c in _polyline_cells(s.road(start, end)[0])}
    )
    rivers = np.flatnonzero((g.river & g.main_land & ~g.occupied).ravel())
    if rivers.size and road_cells:
        road_rows, road_columns = np.divmod(np.array(road_cells), GRID_CELLS)
        river_rows, river_columns = np.divmod(rivers, GRID_CELLS)
        dr = river_rows[:, None] - road_rows[None, :]
        dc = river_columns[:, None] - road_columns[None, :]
        cell = int(rivers[int(np.argmin((dr * dr + dc * dc).min(axis=1)))])
        s.notes[layer].append(
            "bridge: no road crosses a river; placed on the river cell nearest the road "
            "network, joined by a spur road"
        )
        g.occupied.flat[cell] = True
        return _Sited(NodeClass.BRIDGE, cell, river_accumulation=int(g.accumulation.flat[cell]))
    start, end = _bridge_roads(s)[0] if _bridge_roads(s) else (0, 0)
    candidates = [
        c
        for c in _polyline_cells(s.road(start, end)[0])
        if g.land.flat[c] and not g.occupied.flat[c] and c not in (start, end)
    ]
    if not candidates:
        raise ValueError("no eligible cell for transport bridge: no river and no main road")
    cell = min(candidates, key=lambda c: (float(g.elevation_m.flat[c]), c))
    s.bridge_roads[cell] = (start, end)
    s.notes[layer].append(
        "bridge: the island has no river; placed as a viaduct at the main road's lowest land "
        "crossing of a valley"
    )
    g.occupied.flat[cell] = True
    return _Sited(NodeClass.BRIDGE, cell)


def _site_road_junction(s: _Siter, layer: Layer, index: int, stream: np.random.Generator) -> _Sited:
    g = s.ground
    if index < len(g.cities):
        city = g.cities[index]
        strict = g.city_distance(city) == 0
        weight = _near(g.distance_to(city.centre_row, city.centre_column), 5.0)
        rule = "in a city"
    else:
        pairs = list(combinations(g.cities, 2)) or [(g.cities[0], g.cities[0])]
        a, b = pairs[(index - len(g.cities)) % len(pairs)]
        distance, along = _segment_distance(
            g,
            a.centre_row * GRID_CELLS + a.centre_column,
            b.centre_row * GRID_CELLS + b.centre_column,
        )
        strict = (distance <= 2) & (along > 0.2) & (along < 0.8)
        weight = _near(np.abs(along - 0.5), 0.1)
        rule = "on the road between cities"
    cell = s.place(layer, NodeClass.ROAD_JUNCTION, rule, stream, strict, weight)
    return _Sited(NodeClass.ROAD_JUNCTION, cell)


def _site_reservoir(s: _Siter, layer: Layer, index: int, stream: np.random.Generator) -> _Sited:
    g = s.ground
    # CHOICE: "on a river" means beside a river cell; nodes never sit on river cells.
    river_accumulation = _neighbour_river_accumulation(g)
    uplands = g.height >= SITING.upland_share
    strict = uplands & (river_accumulation > 0)
    weight = np.sqrt(river_accumulation.astype(np.float64))
    cell = s.place(
        layer,
        NodeClass.RESERVOIR,
        "on a river in the uplands",
        stream,
        strict,
        weight,
        relaxed=uplands,
        relaxed_weight=np.sqrt(g.accumulation.astype(np.float64)),
        how_relaxed="placed in the upland valley with the largest upstream area",
    )
    return _Sited(NodeClass.RESERVOIR, cell, river_accumulation=int(river_accumulation.flat[cell]))


def _site_treatment(s: _Siter, layer: Layer, index: int, stream: np.random.Generator) -> _Sited:
    g = s.ground
    reservoirs = s.of_class(NodeClass.RESERVOIR)
    reservoir = reservoirs[index % len(reservoirs)].cell
    path = np.zeros(g.land.shape, dtype=bool)
    for cell in _downstream_path(g, reservoir):
        path.flat[cell] = True
    lower = g.elevation_m < g.elevation_m.flat[reservoir]
    apart = g.distance_to(*divmod(reservoir, GRID_CELLS)) >= SITING.treatment_gap_cells
    largest = g.cities[0]
    weight = _near(g.distance_to(largest.centre_row, largest.centre_column), 10.0)
    cell = s.place(
        layer,
        NodeClass.TREATMENT,
        "downstream of its reservoir toward the largest city",
        stream,
        _dilate(path) & lower & apart,
        weight,
        relaxed=lower,
        how_relaxed="placed on lower ground toward the largest city, off the river path",
    )
    return _Sited(NodeClass.TREATMENT, cell)


def _site_between(
    s: _Siter,
    layer: Layer,
    node_class: NodeClass,
    rule: str,
    start: int,
    end: int,
    stream: np.random.Generator,
) -> int:
    g = s.ground
    distance, along = _segment_distance(g, start, end)
    half = SITING.corridor_middle_share / 2
    middle = (along >= 0.5 - half) & (along <= 0.5 + half)
    strict = (distance <= g.cells_for_km(SITING.corridor_km)) & middle
    weight = _near(np.abs(along - 0.5), 0.1) * _near(distance, 3.0)
    return s.place(
        layer,
        node_class,
        rule,
        stream,
        strict,
        weight,
        how_relaxed="placed on the nearest land to the middle of that line",
    )


def _site_pumping(s: _Siter, layer: Layer, index: int, stream: np.random.Generator) -> _Sited:
    g = s.ground
    treatments = s.of_class(NodeClass.TREATMENT)
    start = treatments[index % len(treatments)].cell
    city = g.cities[0]
    end = city.centre_row * GRID_CELLS + city.centre_column
    rule = "between treatment and the city"
    return _Sited(
        NodeClass.PUMPING, _site_between(s, layer, NodeClass.PUMPING, rule, start, end, stream)
    )


def _site_storage(s: _Siter, layer: Layer, index: int, stream: np.random.Generator) -> _Sited:
    g = s.ground
    city = g.city_for(index)
    distance = g.city_distance(city)
    beside = (distance >= 1) & (distance <= g.cells_for_km(SITING.storage_beside_city_km))
    footprint = distance == 0
    city_height = float(np.mean(g.elevation_m[footprint])) if footprint.any() else 0.0
    raised = np.maximum(g.elevation_m - city_height, 0.0)
    cell = s.place(
        layer,
        NodeClass.STORAGE,
        "on raised ground beside a city",
        stream,
        beside,
        raised / 10.0 + 0.1,
        relaxed=distance <= g.cells_for_km(3.0),
        how_relaxed="placed on the highest land near that city",
    )
    return _Sited(NodeClass.STORAGE, cell)


def _site_generation(s: _Siter, layer: Layer, index: int, stream: np.random.Generator) -> _Sited:
    g = s.ground
    city = g.city_for(index)
    distance = g.city_distance(city)
    strict = g.coast & (distance <= g.cells_for_km(SITING.near_city_km))
    cell = s.place(
        layer,
        NodeClass.GENERATION,
        "on the coast near a city",
        stream,
        strict,
        _near(distance, 5.0),
        relaxed=g.coast,
        how_relaxed="placed on the coast nearest the cities",
    )
    return _Sited(NodeClass.GENERATION, cell)


def _site_transmission(s: _Siter, layer: Layer, index: int, stream: np.random.Generator) -> _Sited:
    g = s.ground
    plants = s.of_class(NodeClass.GENERATION)
    largest = g.cities[0]
    start = (
        plants[index % len(plants)].cell
        if plants
        else largest.centre_row * GRID_CELLS + largest.centre_column
    )
    city = g.city_for(index + 1) if len(g.cities) > 1 else g.cities[0]
    end = city.centre_row * GRID_CELLS + city.centre_column
    rule = "between generation and the cities"
    cell = _site_between(s, layer, NodeClass.TRANSMISSION_SUBSTATION, rule, start, end, stream)
    return _Sited(NodeClass.TRANSMISSION_SUBSTATION, cell)


def _site_distribution(s: _Siter, layer: Layer, index: int, stream: np.random.Generator) -> _Sited:
    g = s.ground
    city = g.city_for(index)
    strict = g.city_distance(city) <= g.cells_for_km(SITING.beside_city_km)
    weight = _near(g.distance_to(city.centre_row, city.centre_column), 5.0)
    cell = s.place(
        layer, NodeClass.DISTRIBUTION_SUBSTATION, "in or beside a city", stream, strict, weight
    )
    return _Sited(NodeClass.DISTRIBUTION_SUBSTATION, cell)


def _site_in_city(
    node_class: NodeClass, city_index: Callable[[_Siter, int], City], rule: str
) -> SitingRule:
    def site(s: _Siter, layer: Layer, index: int, stream: np.random.Generator) -> _Sited:
        g = s.ground
        city = city_index(s, index)
        strict = g.city_distance(city) == 0
        weight = _near(g.distance_to(city.centre_row, city.centre_column), 5.0)
        cell = s.place(
            layer,
            node_class,
            rule,
            stream,
            strict,
            weight,
            relaxed=g.city_distance(city) <= g.cells_for_km(SITING.beside_city_km),
            how_relaxed="placed beside that city",
        )
        return _Sited(node_class, cell)

    return site


def _site_spaced(
    node_class: NodeClass, spacing_km: float, weight_of: Callable[[_Ground], NDArray[np.float64]]
) -> SitingRule:
    def site(s: _Siter, layer: Layer, index: int, stream: np.random.Generator) -> _Sited:
        g = s.ground
        taken = np.zeros(g.land.shape, dtype=bool)
        for sited in s.sited[layer]:
            taken.flat[sited.cell] = True
        spacing = g.cells_for_km(spacing_km)
        apart = _chessboard_distance(taken, spacing + 1) >= spacing
        rule = f"spread at least {spacing_km:g} km from others in the layer"
        cell = s.place(
            layer,
            node_class,
            rule,
            stream,
            apart,
            weight_of(g),
            how_relaxed="placed closer than the spacing",
        )
        return _Sited(node_class, cell)

    return site


def _mast_weight(g: _Ground) -> NDArray[np.float64]:
    urban = (np.asarray(g.terrain.urban_id) >= 0).astype(np.float64)
    return 1.0 + 2.0 * urban + 2.0 * g.height


def _clinic_weight(g: _Ground) -> NDArray[np.float64]:
    urban_id = np.asarray(g.terrain.urban_id)
    big = {c.city_id for c in g.cities[:2]}
    in_town = (urban_id >= 0) & ~np.isin(urban_id, sorted(big))
    return 1.0 + 2.0 * in_town.astype(np.float64)


def _site_on_coast_near(
    node_class: NodeClass, anchor: Callable[[_Siter, int], int | None], km: float, rule: str
) -> SitingRule:
    def site(s: _Siter, layer: Layer, index: int, stream: np.random.Generator) -> _Sited:
        g = s.ground
        target = anchor(s, index)
        if target is None:
            city = g.city_for(index)
            target = city.centre_row * GRID_CELLS + city.centre_column
        distance = g.distance_to(*divmod(target, GRID_CELLS))
        strict = g.coast & (distance <= g.cells_for_km(km))
        cell = s.place(
            layer,
            node_class,
            rule,
            stream,
            strict,
            _near(distance, 5.0),
            relaxed=g.coast,
            how_relaxed="placed on the nearest coast instead",
        )
        return _Sited(node_class, cell)

    return site


def _seaport_city_centre(s: _Siter, index: int) -> int | None:
    ports = s.of_class(NodeClass.SEAPORT)
    if not ports:
        return None
    city = s.ground.nearest_city(ports[index % len(ports)].cell)
    return city.centre_row * GRID_CELLS + city.centre_column


def _terminal_cell(s: _Siter, index: int) -> int | None:
    terminals = s.of_class(NodeClass.IMPORT_TERMINAL)
    return terminals[index % len(terminals)].cell if terminals else None


def _site_tank_farm(s: _Siter, layer: Layer, index: int, stream: np.random.Generator) -> _Sited:
    g = s.ground
    terminal = _terminal_cell(s, index)
    largest = g.cities[0]
    anchor = (
        terminal
        if terminal is not None
        else largest.centre_row * GRID_CELLS + largest.centre_column
    )
    distance = g.distance_to(*divmod(anchor, GRID_CELLS))
    strict = distance <= g.cells_for_km(SITING.tank_farm_km)
    cell = s.place(
        layer, NodeClass.TANK_FARM, "near the import terminal", stream, strict, _near(distance, 3.0)
    )
    return _Sited(NodeClass.TANK_FARM, cell)


def _hospital_city(node_class: NodeClass, offset: int) -> Callable[[_Siter, int], City]:
    def city(s: _Siter, index: int) -> City:
        cities = s.ground.cities
        if node_class == NodeClass.BLOOD_BANK:
            tertiary = s.of_class(NodeClass.TERTIARY)
            if tertiary:
                return s.ground.city_of(tertiary[index % len(tertiary)].cell)
        if len(cities) == 1:
            return cities[0]
        return cities[(index + offset) % len(cities)]

    return city


def _largest_city_first(s: _Siter, index: int) -> City:
    return s.ground.city_for(index)


_RULES: Mapping[Layer, Mapping[NodeClass, SitingRule]] = {
    Layer.TRANSPORT: {
        NodeClass.SEAPORT: _site_seaport,
        NodeClass.AIRPORT: _site_airport,
        NodeClass.FREIGHT_YARD: _site_freight_yard,
        NodeClass.BRIDGE: _site_bridge,
        NodeClass.ROAD_JUNCTION: _site_road_junction,
    },
    Layer.WATER: {
        NodeClass.RESERVOIR: _site_reservoir,
        NodeClass.TREATMENT: _site_treatment,
        NodeClass.PUMPING: _site_pumping,
        NodeClass.STORAGE: _site_storage,
    },
    Layer.POWER: {
        NodeClass.GENERATION: _site_generation,
        NodeClass.TRANSMISSION_SUBSTATION: _site_transmission,
        NodeClass.DISTRIBUTION_SUBSTATION: _site_distribution,
    },
    Layer.FUEL: {
        NodeClass.IMPORT_TERMINAL: _site_on_coast_near(
            NodeClass.IMPORT_TERMINAL,
            _seaport_city_centre,
            SITING.near_city_km,
            "on the coast, preferring the seaport's city",
        ),
        NodeClass.TANK_FARM: _site_tank_farm,
        NodeClass.DEPOT: _site_in_city(NodeClass.DEPOT, _largest_city_first, "in a city"),
        NodeClass.REFINERY: _site_on_coast_near(
            NodeClass.REFINERY,
            _terminal_cell,
            SITING.refinery_km,
            "on the coast near an import terminal",
        ),
    },
    Layer.TELECOM: {
        NodeClass.EXCHANGE: _site_in_city(
            NodeClass.EXCHANGE, _largest_city_first, "in the largest city"
        ),
        NodeClass.MAST: _site_spaced(NodeClass.MAST, SITING.mast_spacing_km, _mast_weight),
        NodeClass.DATA_CENTRE: _site_in_city(
            NodeClass.DATA_CENTRE, _largest_city_first, "in a city"
        ),
        NodeClass.CABLE_LANDING: _site_on_coast_near(
            NodeClass.CABLE_LANDING,
            lambda s, i: None,
            SITING.near_city_km,
            "on the coast near a city",
        ),
    },
    Layer.HEALTHCARE: {
        NodeClass.TERTIARY: _site_in_city(
            NodeClass.TERTIARY, _hospital_city(NodeClass.TERTIARY, 0), "in the largest city"
        ),
        NodeClass.REGIONAL: _site_in_city(
            NodeClass.REGIONAL, _hospital_city(NodeClass.REGIONAL, 1), "in the second city"
        ),
        NodeClass.CLINIC: _site_spaced(NodeClass.CLINIC, SITING.clinic_spacing_km, _clinic_weight),
        NodeClass.BLOOD_BANK: _site_in_city(
            NodeClass.BLOOD_BANK,
            _hospital_city(NodeClass.BLOOD_BANK, 0),
            "in the tertiary hospital's city",
        ),
    },
}


# --- Siting helpers -------------------------------------------------------------------------


def _draw_cell(
    stream: np.random.Generator, mask: NDArray[np.bool_], weight: NDArray[np.float64]
) -> int | None:
    """Draw one cell from the mask with probability proportional to its weight."""
    cells = np.flatnonzero(mask.ravel())
    if cells.size == 0:
        return None
    quantised = np.floor(np.asarray(weight).ravel()[cells] * WEIGHT_RESOLUTION).astype(np.int64)
    # Integer weights make the cumulative total exact on every platform.
    cumulative = np.cumsum(np.maximum(quantised, 0) + 1)
    pick = int(stream.integers(0, int(cumulative[-1])))
    return int(cells[int(np.searchsorted(cumulative, pick, side="right"))])


def _draw_index(stream: np.random.Generator, weights: Sequence[float]) -> int:
    quantised = np.floor(np.asarray(weights) * WEIGHT_RESOLUTION).astype(np.int64)
    cumulative = np.cumsum(np.maximum(quantised, 0) + 1)
    pick = int(stream.integers(0, int(cumulative[-1])))
    return int(np.searchsorted(cumulative, pick, side="right"))


def _shelter(g: _Ground) -> NDArray[np.float64]:
    """One minus the share of sea in a square window: higher in bays than on headlands."""
    radius = SITING.shelter_radius_cells
    sea = np.pad(g.sea.astype(np.int64), radius + 1)
    integral = sea.cumsum(axis=0).cumsum(axis=1)
    size = 2 * radius + 1
    window = (
        integral[size:, size:]
        - integral[:-size, size:]
        - integral[size:, :-size]
        + integral[:-size, :-size]
    )
    shape = g.sea.shape
    return 1.0 - window[: shape[0], : shape[1]] / (size * size)


def _city_km(g: _Ground) -> NDArray[np.float64]:
    """Straight-line distance in km from every cell to the nearest city centre."""
    nearest = np.full(g.land.shape, np.inf)
    for city in g.cities:
        nearest = np.minimum(nearest, g.distance_to(city.centre_row, city.centre_column))
    return nearest * g.terrain.grid.cell_size_m / 1000


def _any_city_distance(g: _Ground) -> NDArray[np.int64]:
    return _chessboard_distance(np.asarray(g.terrain.urban_id) >= 0, 64)


def _segment_distance(
    g: _Ground, start: int, end: int
) -> tuple[NDArray[np.float64], NDArray[np.float64]]:
    """Distance in cells from every cell to the segment, and position along it (0-1)."""
    r0, c0 = divmod(start, GRID_CELLS)
    r1, c1 = divmod(end, GRID_CELLS)
    dr, dc = float(r1 - r0), float(c1 - c0)
    length2 = dr * dr + dc * dc
    if length2 == 0.0:
        return g.distance_to(r0, c0), np.full(g.land.shape, 0.5)
    along = np.clip(((g.rows - r0) * dr + (g.columns - c0) * dc) / length2, 0.0, 1.0)
    er = g.rows - (r0 + along * dr)
    ec = g.columns - (c0 + along * dc)
    return np.sqrt(er * er + ec * ec), along


def _neighbour_river_accumulation(g: _Ground) -> NDArray[np.int64]:
    """For each non-river cell, the largest upstream area of an adjacent river cell."""
    on_river = np.where(g.river, g.accumulation, 0).astype(np.int64)
    padded = np.pad(on_river, 1)
    best = np.zeros(g.land.shape, dtype=np.int64)
    for dr, dc in D8_OFFSETS:
        best = np.maximum(best, padded[1 + dr : 1 + dr + GRID_CELLS, 1 + dc : 1 + dc + GRID_CELLS])
    return np.where(g.river, 0, best)


def _downstream_path(g: _Ground, cell: int) -> list[int]:
    """Cells from a node's cell down the flow directions to the sea."""
    path: list[int] = []
    current = int(g.downstream[cell])
    while current >= 0 and g.land.flat[current] and len(path) < GRID_CELLS * GRID_CELLS:
        path.append(current)
        current = int(g.downstream[current])
    return path


def _main_road_ends(s: _Siter, port: int | None) -> tuple[int, int]:
    # CHOICE: the main road joins the two largest cities; with one city, the city and its port.
    g = s.ground
    first = g.cities[0].centre_row * GRID_CELLS + g.cities[0].centre_column
    if len(g.cities) > 1:
        second = g.cities[1].centre_row * GRID_CELLS + g.cities[1].centre_column
        return first, second
    return first, (port if port is not None else first)


def _bridge_roads(s: _Siter) -> list[tuple[int, int]]:
    """Roads a bridge may sit on: between cities, largest first; else from the only city."""
    g = s.ground
    centres = [c.centre_row * GRID_CELLS + c.centre_column for c in g.cities]
    if len(centres) > 1:
        roads = list(combinations(centres, 2))
    else:
        roads = [
            (centres[0], sited.cell)
            for node_class in (NodeClass.AIRPORT, NodeClass.FREIGHT_YARD, NodeClass.SEAPORT)
            for sited in s.of_class(node_class)
        ]
    used = set(s.bridge_roads.values())
    return [road for road in roads if road not in used] + [road for road in roads if road in used]


@dataclass(frozen=True)
class _Runs:
    """Every straight run of one direction, indexed by its start cell."""

    step: tuple[int, int]
    steps: int
    fits: NDArray[np.bool_]
    range_m: NDArray[np.float64]
    length_m: float
    limit_m: float
    flat_enough: NDArray[np.bool_]
    middle_of: tuple[NDArray[np.int64], NDArray[np.int64]]

    def cells_from(self, start: int) -> list[int]:
        row, column = divmod(start, GRID_CELLS)
        dr, dc = self.step
        return [(row + k * dr) * GRID_CELLS + column + k * dc for k in range(self.steps + 1)]


def _runway_directions(g: _Ground, usable: NDArray[np.bool_]) -> list[_Runs]:
    """Straight runs of usable cells, at least the runway length, in four directions."""
    directions = []
    cell_m = g.terrain.grid.cell_size_m
    for dr, dc in ((0, 1), (1, 0), (1, 1), (1, -1)):
        step_m = cell_m * (SQRT_2 if dr and dc else 1.0)
        steps = math.ceil(SITING.runway_km * 1000 / step_m)
        fits = usable.copy()
        highest = g.elevation_m.copy()
        lowest = g.elevation_m.copy()
        for k in range(1, steps + 1):
            fits &= _shift(usable, k * dr, k * dc, False).astype(bool)
            highest = np.maximum(highest, _shift(g.elevation_m, k * dr, k * dc, -np.inf))
            lowest = np.minimum(lowest, _shift(g.elevation_m, k * dr, k * dc, np.inf))
        length_m = steps * step_m
        range_m = np.where(fits, highest - lowest, np.inf)
        half = steps // 2
        middle_rows = np.clip(g.rows + half * dr, 0, GRID_CELLS - 1)
        middle_columns = np.clip(g.columns + half * dc, 0, GRID_CELLS - 1)
        directions.append(
            _Runs(
                step=(dr, dc),
                steps=steps,
                fits=fits,
                range_m=range_m,
                length_m=length_m,
                limit_m=SITING.runway_grade * length_m,
                flat_enough=range_m <= SITING.runway_grade * length_m,
                middle_of=(middle_rows, middle_columns),
            )
        )
    return directions


def _shift(array: NDArray[np.generic], dr: int, dc: int, fill: object) -> NDArray[np.generic]:
    """``out[r, c] = array[r + dr, c + dc]``, with ``fill`` outside the grid."""
    out = np.full(array.shape, fill, dtype=array.dtype)
    rows, columns = array.shape
    out[max(0, -dr) : rows - max(0, dr), max(0, -dc) : columns - max(0, dc)] = array[
        max(0, dr) : rows - max(0, -dr), max(0, dc) : columns - max(0, -dc)
    ]
    return out


def _slope_m_per_m(elevation_dm: NDArray[np.int32], cell_size_m: float) -> NDArray[np.float64]:
    elevation = np.pad(elevation_dm / 10, 1, mode="edge")
    gx = (elevation[1:-1, 2:] - elevation[1:-1, :-2]) / (2 * cell_size_m)
    gy = (elevation[2:, 1:-1] - elevation[:-2, 1:-1]) / (2 * cell_size_m)
    return np.sqrt(gx * gx + gy * gy)


# --- Roads ----------------------------------------------------------------------------------


def _segment_cells(a: tuple[int, int], b: tuple[int, int]) -> list[int]:
    """Cells a straight segment passes through, sampled at half-cell steps."""
    steps = 2 * max(abs(b[0] - a[0]), abs(b[1] - a[1])) + 1
    rows = np.rint(np.linspace(a[0], b[0], steps)).astype(np.int64)
    columns = np.rint(np.linspace(a[1], b[1], steps)).astype(np.int64)
    cells = rows * GRID_CELLS + columns
    return [int(c) for i, c in enumerate(cells) if i == 0 or c != cells[i - 1]]


def _polyline_cells(vertices: Sequence[tuple[int, int]]) -> list[int]:
    cells: list[int] = []
    for a, b in pairwise(vertices):
        for cell in _segment_cells(a, b):
            if not cells or cells[-1] != cell:
                cells.append(cell)
    return cells


def _crosses_sea(g: _Ground, a: tuple[int, int], b: tuple[int, int]) -> bool:
    return any(g.sea.flat[c] for c in _segment_cells(a, b))


def _road_route(g: _Ground, start: int, end: int) -> tuple[list[tuple[int, int]], bool]:
    """Route a road from start to end that never crosses the sea (decision 0006).

    Straight if it can be; otherwise the shortest two-segment path through one land waypoint;
    otherwise the shortest land path on the grid, simplified. Returns the vertices and whether
    the grid fallback was needed.
    """
    a, b = divmod(start, GRID_CELLS), divmod(end, GRID_CELLS)
    if not _crosses_sea(g, a, b):
        return [a, b], False
    candidates = np.flatnonzero(g.main_land.ravel())
    rows, columns = np.divmod(candidates, GRID_CELLS)
    via_a = np.sqrt((rows - a[0]) ** 2.0 + (columns - a[1]) ** 2.0)
    via_b = np.sqrt((rows - b[0]) ** 2.0 + (columns - b[1]) ** 2.0)
    order = np.argsort(via_a + via_b, kind="stable")[: SITING.waypoint_candidates]
    for index in order:
        waypoint = (int(rows[index]), int(columns[index]))
        if not _crosses_sea(g, a, waypoint) and not _crosses_sea(g, waypoint, b):
            return [a, waypoint, b], False
    return _simplify(g, _grid_path(g, start, end)), True


def _grid_path(g: _Ground, start: int, end: int) -> list[tuple[int, int]]:
    """Shortest eight-way path over land (integer costs 10 and 14), start to end."""
    best = {start: 0}
    previous: dict[int, int] = {}
    heap = [(0, start)]
    while heap:
        cost, cell = heapq.heappop(heap)
        if cell == end:
            break
        if cost > best[cell]:
            continue
        row, column = divmod(cell, GRID_CELLS)
        for dr, dc in D8_OFFSETS:
            r, c = row + dr, column + dc
            if not (0 <= r < GRID_CELLS and 0 <= c < GRID_CELLS) or not g.land[r, c]:
                continue
            step = 14 if dr and dc else 10
            neighbour = r * GRID_CELLS + c
            if cost + step < best.get(neighbour, 1 << 62):
                best[neighbour] = cost + step
                previous[neighbour] = cell
                heapq.heappush(heap, (cost + step, neighbour))
    if end not in best:
        raise ValueError("no land path joins two transport nodes on the main island")
    path = [end]
    while path[-1] != start:
        path.append(previous[path[-1]])
    return [divmod(cell, GRID_CELLS) for cell in reversed(path)]


def _simplify(g: _Ground, path: list[tuple[int, int]]) -> list[tuple[int, int]]:
    """Keep only the vertices needed for every straight piece to stay off the sea."""
    vertices = [path[0]]
    index = 0
    while index < len(path) - 1:
        reach = len(path) - 1
        while reach > index + 1 and _crosses_sea(g, path[index], path[reach]):
            reach -= 1
        vertices.append(path[reach])
        index = reach
    return vertices


# --- Nodes and attributes -------------------------------------------------------------------


def _make_nodes(
    layer: Layer, siter: _Siter, ground: _Ground, stream: np.random.Generator
) -> list[Node]:
    grid = ground.terrain.grid
    largest = ground.cities[0].cell_count
    nodes = []
    for number, sited in enumerate(siter.sited[layer], start=1):
        row, column = divmod(sited.cell, GRID_CELLS)
        x_m, y_m = cell_centre_m(row, column, grid)
        longitude, latitude = to_lonlat(x_m, y_m)
        city = ground.city_of(sited.cell)
        share = city.cell_count / largest
        runway = None
        if sited.runway is not None:
            runway = (
                cell_centre_m(*divmod(sited.runway[0], GRID_CELLS), grid),
                cell_centre_m(*divmod(sited.runway[1], GRID_CELLS), grid),
            )
        nodes.append(
            Node(
                node_id=f"SWM-{LAYER_CODES[layer]}-{number:04d}",
                layer=layer,
                node_class=sited.node_class,
                row=row,
                column=column,
                x_m=x_m,
                y_m=y_m,
                longitude=longitude,
                latitude=latitude,
                city_id=city.city_id,
                attributes=_attributes(layer, sited, share, ground, stream),
                runway=runway,
            )
        )
    return nodes


def _attributes(
    layer: Layer, sited: _Sited, share: float, ground: _Ground, stream: np.random.Generator
) -> tuple[tuple[str, AttributeValue], ...]:
    """Observed attributes, scaled by the served city's size relative to the largest city."""
    # CHOICE: the served city is the city the node lies in, or else the nearest city.
    node_class = sited.node_class
    values: dict[str, AttributeValue] = {"status": OPERATIONAL}
    for name, (low, high) in ATTRIBUTE_RANGES.get(node_class, {}).items():
        size = share
        if node_class == NodeClass.BRIDGE:
            size = min(1.0, math.sqrt(sited.river_accumulation) / 100.0)
        scaled = low + (high - low) * (0.7 * size + 0.3 * float(stream.random()))
        values[name] = _round_attribute(name, scaled)
    if node_class == NodeClass.GENERATION:
        values["fuel_type"] = "hydro" if sited.dam_of is not None else _draw_fuel(stream)
    if node_class == NodeClass.TRANSMISSION_SUBSTATION:
        values["voltage_kv"] = _by_share(TRANSMISSION_VOLTAGES_KV, share)
    if node_class == NodeClass.DISTRIBUTION_SUBSTATION:
        values["voltage_kv"] = _by_share(DISTRIBUTION_VOLTAGES_KV, share)
    if node_class == NodeClass.AIRPORT:
        values["size_class"] = _by_share(AIRPORT_SIZES, share)
    if node_class == NodeClass.SEAPORT:
        values["size_class"] = _by_share(SEAPORT_SIZES, share)
    if node_class == NodeClass.BRIDGE:
        values["deck_class"] = "road"
    if layer == Layer.TELECOM:
        values["operator"] = TELECOM_OPERATORS[int(stream.integers(0, len(TELECOM_OPERATORS)))]
    if layer in (Layer.TELECOM, Layer.WATER, Layer.TRANSPORT, Layer.FUEL):
        values["type"] = node_class.value
    if layer == Layer.HEALTHCARE:
        values["facility_class"] = node_class.value
    return tuple(sorted(values.items()))


def _round_attribute(name: str, value: float) -> AttributeValue:
    if name in ("capacity_mw",):
        return round(value, 1)
    if name.endswith(("_m3", "_m3_per_day", "_m2")):
        return int(round(value, -2))
    return round(value)


def _by_share[T](table: tuple[tuple[float, T], ...], share: float) -> T:
    for threshold, value in table:
        if share >= threshold:
            return value
    return table[-1][1]


def _draw_fuel(stream: np.random.Generator) -> str:
    return FUEL_TYPES[_draw_index(stream, [weight for _, weight in FUEL_TYPES])][0]


# --- Links ----------------------------------------------------------------------------------


class _LinkBuilder:
    """Builds one layer's links: its signature first, then nearest-first to the recipe value."""

    def __init__(
        self,
        layer: Layer,
        nodes: list[Node],
        siter: _Siter,
        ground: _Ground,
        links_per_node: float,
    ) -> None:
        self.layer = layer
        self.nodes = nodes
        self.siter = siter
        self.ground = ground
        self.links_per_node = links_per_node
        self.pairs: list[tuple[int, int]] = []
        self.notes: list[str] = []

    def build(self) -> list[Link]:
        count = len(self.nodes)
        self._signature()
        self._join_components()
        target = self._target(count)
        if self.layer not in TREE_LAYERS:
            self._preferred_extras(target)
            self._nearest_extras(target)
        realised = 2 * len(self.pairs) / count if count else 0.0
        if count and abs(realised - self.links_per_node) > 0.5:
            self.notes.append(
                f"links per node {realised:.2f} against the recipe's {self.links_per_node:.2f}: "
                + self._why_not(count)
            )
        return [self._link(number, pair) for number, pair in enumerate(self.pairs, start=1)]

    def _why_not(self, count: int) -> str:
        if self.layer in TREE_LAYERS:
            return "the layer keeps its tree signature, n - 1 links"
        if 2 * len(self.pairs) / count > self.links_per_node:
            return "a connected layer needs at least n - 1 links"
        return "a layer this small cannot hold more links"

    def _target(self, count: int) -> int:
        wanted = int(count * self.links_per_node / 2 + 0.5)
        most = count - 1 if self.layer in TREE_LAYERS else count * (count - 1) // 2
        return max(count - 1, min(wanted, most))

    def _of(self, *classes: NodeClass) -> list[int]:
        return [i for i, node in enumerate(self.nodes) if node.node_class in classes]

    def _distance2(self, i: int, j: int) -> int:
        a, b = self.nodes[i], self.nodes[j]
        return (a.row - b.row) ** 2 + (a.column - b.column) ** 2

    def _nearest(self, i: int, candidates: list[int]) -> int | None:
        others = [j for j in candidates if j != i]
        return min(others, key=lambda j: (self._distance2(i, j), j)) if others else None

    def _add(self, i: int | None, j: int | None) -> None:
        if i is None or j is None or i == j:
            return
        if (i, j) in self.pairs or (j, i) in self.pairs:
            return
        self.pairs.append((i, j))

    def _chain(self, stages: list[list[NodeClass]]) -> None:
        """Link each node to the nearest node of the nearest earlier stage that has nodes."""
        for position, stage in enumerate(stages):
            upstream = [
                j for earlier in reversed(stages[:position]) for j in [self._of(*earlier)] if j
            ]
            for i in self._of(*stage):
                if upstream:
                    self._add(self._nearest(i, upstream[0]), i)

    def _chain_within(self, *classes: NodeClass) -> None:
        members = self._of(*classes)
        for index, i in enumerate(members[1:], start=1):
            self._add(self._nearest(i, members[:index]), i)

    def _signature(self) -> None:
        c = NodeClass
        if self.layer == Layer.POWER:
            self._chain_within(c.TRANSMISSION_SUBSTATION)
            self._chain([[c.GENERATION], [c.TRANSMISSION_SUBSTATION], [c.DISTRIBUTION_SUBSTATION]])
        elif self.layer == Layer.TELECOM:
            self._chain_within(c.EXCHANGE)
            self._chain([[c.EXCHANGE], [c.MAST, c.DATA_CENTRE, c.CABLE_LANDING]])
        elif self.layer == Layer.WATER:
            self._chain([[c.RESERVOIR], [c.TREATMENT], [c.PUMPING], [c.STORAGE]])
        elif self.layer == Layer.FUEL:
            self._chain([[c.IMPORT_TERMINAL], [c.TANK_FARM, c.REFINERY], [c.DEPOT]])
        elif self.layer == Layer.HEALTHCARE:
            self._chain_within(c.TERTIARY)
            self._chain([[c.TERTIARY], [c.REGIONAL], [c.CLINIC]])
            self._chain([[c.TERTIARY], [c.BLOOD_BANK]])
        else:
            self._transport_signature()

    def _transport_signature(self) -> None:
        """Join each bridge to the two ends of the road it sits on; the rest join nearest-first."""
        for i in self._of(NodeClass.BRIDGE):
            node = self.nodes[i]
            road = self.siter.bridge_roads.get(node.row * GRID_CELLS + node.column)
            others = [j for j in range(len(self.nodes)) if j != i]
            if road is None or not others:
                continue
            ends = []
            for end in road:
                row, column = divmod(end, GRID_CELLS)
                nearest = min(
                    (j for j in others if j not in ends),
                    key=lambda j: (
                        (self.nodes[j].row - row) ** 2 + (self.nodes[j].column - column) ** 2,
                        j,
                    ),
                    default=None,
                )
                if nearest is not None:
                    ends.append(nearest)
                    self._add(i, nearest)

    def _join_components(self) -> None:
        """Join components by their closest pair until the layer is one component."""
        count = len(self.nodes)
        parent = list(range(count))

        def root(i: int) -> int:
            while parent[i] != i:
                parent[i] = parent[parent[i]]
                i = parent[i]
            return i

        for i, j in self.pairs:
            parent[root(i)] = root(j)
        candidates = sorted(
            ((self._distance2(i, j), i, j) for i in range(count) for j in range(i + 1, count)),
        )
        for _, i, j in candidates:
            if root(i) != root(j):
                parent[root(i)] = root(j)
                self._add(i, j)

    def _preferred_extras(self, target: int) -> None:
        """Healthcare: the blood bank links to the hospitals it serves before other extras."""
        if self.layer != Layer.HEALTHCARE:
            return
        for bank in self._of(NodeClass.BLOOD_BANK):
            for hospital in self._of(NodeClass.TERTIARY, NodeClass.REGIONAL):
                if len(self.pairs) < target:
                    self._add(bank, hospital)

    def _nearest_extras(self, target: int) -> None:
        count = len(self.nodes)
        ordered = sorted(
            (self._distance2(i, j), i, j) for i in range(count) for j in range(i + 1, count)
        )
        for _, i, j in ordered:
            if len(self.pairs) >= target:
                break
            self._add(i, j)

    def _link(self, number: int, pair: tuple[int, int]) -> Link:
        a, b = self.nodes[pair[0]], self.nodes[pair[1]]
        start, end = (a.row, a.column), (b.row, b.column)
        g = self.ground
        if self.layer == Layer.TRANSPORT:
            vertices, on_grid = self.siter.road(
                start[0] * GRID_CELLS + start[1], end[0] * GRID_CELLS + end[1]
            )
            if on_grid:
                self.notes.append(
                    f"road {a.node_id}-{b.node_id}: no single land waypoint avoids the sea; "
                    "routed on the land grid"
                )
        else:
            vertices = [start, end]
        cells = _polyline_cells(vertices)
        points = tuple(cell_centre_m(r, c, g.terrain.grid) for r, c in vertices)
        return Link(
            link_id=f"SWM-{LAYER_CODES[self.layer]}-L{number:04d}",
            layer=self.layer,
            from_id=a.node_id,
            to_id=b.node_id,
            points=points,
            length_km=round(_polyline_length_m(points) / 1000, 3),
            river_crossings=_river_crossings(g, cells),
            crosses_sea=any(g.sea.flat[c] for c in cells),
        )


def _polyline_length_m(points: Sequence[tuple[float, float]]) -> float:
    pieces = [
        math.sqrt((x1 - x0) * (x1 - x0) + (y1 - y0) * (y1 - y0))
        for (x0, y0), (x1, y1) in pairwise(points)
    ]
    return math.fsum(pieces)


def _river_crossings(g: _Ground, cells: list[int]) -> int:
    """River runs the link crosses, not counting a river cell at either end (a bridge)."""
    inner = cells[1:-1]
    crossings = 0
    previous = False
    for cell in inner:
        on_river = bool(g.river.flat[cell])
        if on_river and not previous:
            crossings += 1
        previous = on_river
    return crossings


# --- Statistics -----------------------------------------------------------------------------


def _statistics(
    layer: Layer,
    settings: LayerSettings,
    nodes: list[Node],
    links: list[Link],
    notes: list[str],
) -> LayerStatistics:
    counts = {cls.value: 0 for cls in LAYER_NODE_CLASSES[layer]}
    for node in nodes:
        counts[node.node_class.value] += 1
    spacing = [
        min(
            math.sqrt((a.x_m - b.x_m) ** 2 + (a.y_m - b.y_m) ** 2)
            for b in nodes
            if b.node_id != a.node_id
        )
        for a in nodes
        if len(nodes) > 1
    ]
    covered = {cls for source in settings.sources for cls in SOURCE_SCOPES[source].classes}
    # Real but unemitted: present in the world, carried by no switched-on source (E2).
    uncovered = tuple(
        cls
        for cls, count in counts.items()
        if count and settings.state == LayerState.EMITTED and NodeClass(cls) not in covered
    )
    return LayerStatistics(
        layer=layer,
        state=settings.state,
        class_counts=counts,
        link_count=len(links),
        mean_links_per_node=round(2 * len(links) / len(nodes), 3) if nodes else 0.0,
        mean_spacing_km=round(math.fsum(spacing) / len(spacing) / 1000, 3) if spacing else 0.0,
        classes_without_source=uncovered,
        notes=tuple(notes),
    )
