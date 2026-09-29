"""Couplings stage: every cross-layer dependency and the coupling edges that serve it.

From the resolved recipe's couplings section, the terrain, the layers result and the
``couplings/*`` streams, the stage resolves each consumer's rows of the dependency table
(structure v0.5 §4.3a), decides which dependencies exist, gives each a feed configuration, and
chooses its suppliers. A dependency is one consumer node's need for one supplier layer's
commodity; a coupling edge is one supplier node serving that need. Edges are straight lines:
dependencies, not routes.

Spec: structure v0.5 §4.3 and §4.3a; Work Order 4, Part E; decision 0008.
"""

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field, replace
from enum import StrEnum

import numpy as np
from numpy.typing import NDArray

from swm import rng
from swm.recipe.dependencies import (
    Dependency,
    DependencyRow,
    Role,
    SupplierOption,
    SupplierWhen,
    resolve_row,
)
from swm.recipe.schema import (
    DEFAULT_COUPLINGS,
    Couplings,
    Layer,
    LayerState,
    NodeClass,
    SwitchedOffHandling,
    TransferForms,
)
from swm.rules.registry import Registry
from swm.stages.layers import LayersResult, Node, _segment_cells
from swm.stages.requirements import RequirementsResult
from swm.stages.terrain import TerrainResult, _dilate, _label_land

Pair = tuple[Layer, Layer]


class FeedConfiguration(StrEnum):
    """How a dependency is fed (structure v0.5 §4.3; Work Order 4, E4 and E5)."""

    SINGLE = "single"
    TWO_FULL = "two_full"
    """Two distinct supplier nodes; either covers the need."""
    TWO_HALF = "two_half"
    """Two distinct supplier nodes; both are needed."""
    ANY_REACHABLE = "any_reachable"
    """Transport (rule 3): every eligible origin that reaches the consumer; any one serves."""
    NONE = "none"
    """No edge: a buffer-resupply dependency with no standby generator (decision 0008)."""


WEIGHT_RESOLUTION = 1_000_000
"""Distance weights are quantised to integers at this resolution, so draws are exact."""

CAPACITY_ATTRIBUTES = ("capacity_mw", "capacity_mva", "capacity_m3_per_day", "storage_m3")
"""Observed attributes that give a supplier's capacity, for the hub draw (Work Order 4, E7)."""

CAPACITY_WEIGHT_PER_UNIT = 100
"""Capacities are quantised to hundredths of their unit for the hub draw."""

PUBLIC_SHARE_FIELDS: Mapping[NodeClass, str] = {
    NodeClass.GENERATION: "generation_pct",
    NodeClass.TRANSMISSION_SUBSTATION: "transmission_pct",
    NodeClass.DISTRIBUTION_SUBSTATION: "distribution_pct",
}
"""Power consumer classes and their public telecom share setting (§4.3a rule 1)."""

PUBLIC_SHARE_LAYERS: Mapping[Layer, str] = {
    Layer.WATER: "water_pct",
    Layer.FUEL: "pipelines_pct",
}
"""Other consumer layers with control edges, and their public telecom share setting."""

NO_STANDBY = "none"
"""The standby_fuel value of a consumer with no standby generator."""


@dataclass(frozen=True)
class CouplingEdge:
    """One supplier node serving one dependency. Real but unobserved: never emitted."""

    edge_id: str
    supplier_id: str
    consumer_id: str
    supplier_layer: Layer
    consumer_layer: Layer
    commodity: str
    dependency_type: str
    role: Role
    transfer_form: str
    feed_configuration: FeedConfiguration
    feed_group: int
    """Edges of one dependency in the same group are all needed; any one group serves."""
    dependency_id: str
    backs_dependency: str | None
    """For buffer resupply: the consumer's power dependency this edge backs (rule 2)."""
    public_share_pct: int | None
    """For control edges on power, water and pipeline consumers (rule 1)."""
    switched_on: bool
    is_nearest: bool
    is_hub: bool
    mutual_partner: str | None
    sea_leg: bool
    """Transport to an outlying island by coastal tanker or ferry (decision 0008, answer 6)."""
    points: tuple[tuple[float, float], tuple[float, float]]
    length_km: float
    crosses_sea: bool


@dataclass(frozen=True)
class CouplingDependency:
    """One consumer node's need for one supplier layer's commodity."""

    dependency_id: str
    consumer_id: str
    supplier_layer: Layer
    consumer_layer: Layer
    row_key: str
    dependency: Dependency
    role: Role
    feed_configuration: FeedConfiguration
    edge_ids: tuple[str, ...]
    switched_on: bool
    notes: tuple[str, ...]


@dataclass(frozen=True)
class PairStatistics:
    """Realised statistics of one supplier-to-consumer pair."""

    supplier: Layer
    consumer: Layer
    switched_on: bool
    dependencies: int
    absent: int
    edges: int
    feed_counts: dict[str, int]
    feed_shares: dict[str, float]
    non_nearest_share: float
    hub: str | None
    hub_share: float
    mutual_pairs_allowed: int
    mutual_pairs: int
    notes: tuple[str, ...]


@dataclass(frozen=True)
class CouplingsResult:
    """The couplings stage's output."""

    edges: tuple[CouplingEdge, ...]
    dependencies: tuple[CouplingDependency, ...]
    pairs: tuple[PairStatistics, ...]
    intra_layer_links: int

    @property
    def switched_on_edges(self) -> int:
        """Coupling edges of switched-on pairs."""
        return sum(edge.switched_on for edge in self.edges)

    @property
    def total_edges(self) -> int:
        """Intra-layer links plus switched-on coupling edges (Work Order 4, G)."""
        return self.intra_layer_links + self.switched_on_edges


@dataclass(frozen=True)
class CouplingsStreams:
    """The couplings streams, one set per pair. The stage can reach no other stream."""

    density: Mapping[Pair, np.random.Generator]
    feed_configuration: Mapping[Pair, np.random.Generator]
    hub: Mapping[Pair, np.random.Generator]
    concentration: Mapping[Pair, np.random.Generator]
    supplier_not_nearest: Mapping[Pair, np.random.Generator]
    tertiary_second_feed: np.random.Generator
    two_way: Mapping[Pair, np.random.Generator]


def couplings_streams(root_seed: int) -> CouplingsStreams:
    """Return the ``couplings/*`` streams the stage draws from.

    Parameters
    ----------
    root_seed : int
        The recipe's root seed.

    Returns
    -------
    CouplingsStreams
        Per-pair streams for each purpose, and one two-way stream per couple of layers.

    Spec: structure v0.4 §3 (independent random streams); Work Order 4, E2.
    """

    def per_pair(purpose: str) -> dict[Pair, np.random.Generator]:
        return {
            pair: rng.stream(root_seed, f"couplings/{purpose}/{rng.pair_label(*pair)}")
            for pair in DEFAULT_COUPLINGS
        }

    return CouplingsStreams(
        density=per_pair("density"),
        feed_configuration=per_pair("feed_configuration"),
        hub=per_pair("hub"),
        concentration=per_pair("concentration"),
        supplier_not_nearest=per_pair("supplier_not_nearest"),
        tertiary_second_feed=rng.stream(
            root_seed, "couplings/tertiary_second_feed/power-healthcare"
        ),
        two_way={
            couple: rng.stream(root_seed, f"couplings/two_way/{rng.pair_label(*couple)}")
            for couple in rng.mutual_couples()
        },
    )


def build_couplings(
    couplings: Couplings,
    transfer_forms: TransferForms,
    terrain: TerrainResult,
    layers: LayersResult,
    requirements: RequirementsResult,
    rules: Registry,
    streams: CouplingsStreams,
) -> CouplingsResult:
    """Build every dependency and coupling edge of the world.

    Every pair whose layers are both present is built in full, switched on or not, so that
    switching a pair never moves another pair's edges; pairs switched off under not_generated
    are then left out.

    Parameters
    ----------
    couplings : Couplings
        The resolved recipe's couplings section.
    transfer_forms : TransferForms
        The transfer form per dependency type (the dynamics section).
    terrain : TerrainResult
        The terrain stage's output.
    layers : LayersResult
        The layers stage's output.
    requirements : RequirementsResult
        The requirements stage's output; peak loads decide the supplying substation (rule 4).
    rules : Registry
        The modeling rules in force, with the recipe's overrides.
    streams : CouplingsStreams
        The couplings streams.

    Returns
    -------
    CouplingsResult
        Edges, dependencies and per-pair statistics.

    Spec: structure v0.6 §4.3 and §4.3a; Work Order 4, E1-E11; Work Order 5, Part C.
    """
    world = _World(terrain, layers, rules)
    # CHOICE: every pair of present layers is built, then pairs switched off under
    # not_generated are dropped. Density, two-way and numbering therefore never depend on which
    # pairs are switched, as E2 and the Part G stream tests require.
    pairs = [
        pair
        for pair in DEFAULT_COUPLINGS
        if layers.states[pair[0]] != LayerState.OFF and layers.states[pair[1]] != LayerState.OFF
    ]
    large = _LargeLoads.from_rules(requirements, rules, couplings.distribution_voltage_kv)
    needs = {pair: _needs_of(pair, world, large) for pair in pairs}
    _apply_density(needs, couplings.density, streams.density)
    notes: dict[Pair, list[str]] = {pair: [] for pair in pairs}
    hubs: dict[Pair, Node | None] = {}
    for pair in pairs:
        if pair[0] == Layer.TRANSPORT:
            _reach(needs[pair], world)
            hubs[pair] = None
            continue
        _configure_feeds(pair, needs[pair], couplings, streams, large.second_feed_pct)
        hubs[pair] = _choose_suppliers(pair, needs[pair], couplings, streams, notes[pair])
    mutual = _two_way(needs, couplings.two_way_pct, streams.two_way, notes)
    switched = {(p.supplier, p.consumer) for p in couplings.switched_on}
    kept = [
        pair
        for pair in pairs
        if pair in switched
        or couplings.switched_off_handling == SwitchedOffHandling.GENERATE_AND_HIDE
    ]
    builder = _Builder(world, couplings, transfer_forms, needs, hubs, switched, set(kept))
    builder.build(pairs)
    statistics = [
        _pair_statistics(pair, needs[pair], hubs[pair], builder, mutual, notes[pair], switched)
        for pair in kept
    ]
    return CouplingsResult(
        edges=tuple(builder.edges),
        dependencies=tuple(builder.dependencies),
        pairs=tuple(statistics),
        intra_layer_links=len(layers.links),
    )


def edge_table(result: CouplingsResult) -> list[dict[str, object]]:
    """Return the edge table as plain data in a fixed key order, for canonical output.

    Parameters
    ----------
    result : CouplingsResult
        The couplings stage's output.

    Returns
    -------
    list of dict
        One row per coupling edge, its end points rounded to the centimetre.

    Spec: Work Order 4, E11 and F1.
    """
    return [
        {
            "id": edge.edge_id,
            "supplier": edge.supplier_id,
            "consumer": edge.consumer_id,
            "supplier_layer": edge.supplier_layer.value,
            "consumer_layer": edge.consumer_layer.value,
            "commodity": edge.commodity,
            "dependency_type": edge.dependency_type,
            "role": edge.role.value,
            "transfer_form": edge.transfer_form,
            "feed_configuration": edge.feed_configuration.value,
            "feed_group": edge.feed_group,
            "dependency": edge.dependency_id,
            "backs_dependency": edge.backs_dependency,
            "public_share_pct": edge.public_share_pct,
            "switched_on": edge.switched_on,
            "is_nearest": edge.is_nearest,
            "is_hub": edge.is_hub,
            "mutual_partner": edge.mutual_partner,
            "sea_leg": edge.sea_leg,
            "length_km": edge.length_km,
            "crosses_sea": edge.crosses_sea,
            "points_m": [[round(x, 2), round(y, 2)] for x, y in edge.points],
        }
        for edge in result.edges
    ]


def dependency_table(result: CouplingsResult) -> list[dict[str, object]]:
    """Return the dependency table as plain data in a fixed key order, for canonical output.

    Parameters
    ----------
    result : CouplingsResult
        The couplings stage's output.

    Returns
    -------
    list of dict
        One row per dependency.

    Spec: Work Order 4, E11 and F1.
    """
    return [
        {
            "id": dependency.dependency_id,
            "consumer": dependency.consumer_id,
            "supplier_layer": dependency.supplier_layer.value,
            "consumer_layer": dependency.consumer_layer.value,
            "row": dependency.row_key,
            "dependency": dependency.dependency.value,
            "role": dependency.role.value,
            "feed_configuration": dependency.feed_configuration.value,
            "edges": list(dependency.edge_ids),
            "switched_on": dependency.switched_on,
            "notes": list(dependency.notes),
        }
        for dependency in result.dependencies
    ]


def switched_on_edge_summary(
    result: CouplingsResult, layers: LayersResult
) -> list[dict[str, object]]:
    """Return every switched-on coupling edge as one line of the hand-trace table.

    Parameters
    ----------
    result : CouplingsResult
        The couplings stage's output.
    layers : LayersResult
        The layers stage's output, for node classes.

    Returns
    -------
    list of dict
        One row per switched-on edge, sorted by edge id: edge id, supplier and consumer (id and
        class), dependency type, feed configuration and role.

    Spec: Work Order 4 review, answer 3 (decision 0008).
    """
    classes = {node.node_id: node.node_class.value for node in layers.nodes}
    return [
        {
            "edge_id": edge.edge_id,
            "supplier_id": edge.supplier_id,
            "supplier_class": classes[edge.supplier_id],
            "consumer_id": edge.consumer_id,
            "consumer_class": classes[edge.consumer_id],
            "dependency_type": edge.dependency_type,
            "feed_configuration": edge.feed_configuration.value,
            "role": edge.role.value,
        }
        for edge in sorted(result.edges, key=lambda e: e.edge_id)
        if edge.switched_on
    ]


def statistics_record(result: CouplingsResult) -> dict[str, object]:
    """Return the per-pair and overall statistics in a fixed order.

    Parameters
    ----------
    result : CouplingsResult
        The couplings stage's output.

    Returns
    -------
    dict
        Plain data ready for canonical YAML.

    Spec: Work Order 4, E11 and F1.
    """
    return {
        "pairs": {
            rng.pair_label(stats.supplier, stats.consumer): {
                "switched_on": stats.switched_on,
                "dependencies": stats.dependencies,
                "absent": stats.absent,
                "edges": stats.edges,
                "feed_counts": dict(stats.feed_counts),
                "feed_shares": dict(stats.feed_shares),
                "non_nearest_share": stats.non_nearest_share,
                "hub": stats.hub,
                "hub_share": stats.hub_share,
                "mutual_pairs_allowed": stats.mutual_pairs_allowed,
                "mutual_pairs": stats.mutual_pairs,
                "notes": list(stats.notes),
            }
            for stats in result.pairs
        },
        "totals": {
            "coupling_edges": len(result.edges),
            "switched_on_coupling_edges": result.switched_on_edges,
            "intra_layer_links": result.intra_layer_links,
            "total_edges": result.total_edges,
        },
    }


# --- The world the stage reads --------------------------------------------------------------


class _World:
    """Nodes by layer, and what the table's conditions and rule 3 read from the ground."""

    def __init__(self, terrain: TerrainResult, layers: LayersResult, rules: Registry) -> None:
        self.rules = rules
        land = np.asarray(terrain.land)
        labels, sizes = _label_land(land)
        self.labels = labels
        self.main_label = 1 + max(range(len(sizes)), key=lambda i: (sizes[i], -i))
        self.coast: NDArray[np.bool_] = land & _dilate(~land)
        self.sea: NDArray[np.bool_] = ~land
        self.nodes = {layer: [n for n in layers.nodes if n.layer == layer] for layer in Layer}
        self.by_id = {node.node_id: node for node in layers.nodes}
        self.road_components = _components(
            self.nodes[Layer.TRANSPORT],
            [(link.from_id, link.to_id) for link in layers.links if link.layer == Layer.TRANSPORT],
        )

    def island(self, node: Node) -> int:
        return int(self.labels[node.row, node.column])

    def outlying(self, node: Node) -> bool:
        return self.island(node) != self.main_label

    def inland(self, node: Node) -> bool:
        return not bool(self.coast[node.row, node.column])

    def crosses_sea(self, a: Node, b: Node) -> bool:
        cells = _segment_cells((a.row, a.column), (b.row, b.column))
        return any(bool(self.sea.flat[cell]) for cell in cells)

    def main_road_component(self) -> set[str]:
        """Return the transport component with the most nodes; ties go to the lowest node id."""
        if not self.road_components:
            return set()
        return min(self.road_components, key=lambda c: (-len(c), min(c)))


def _components(nodes: Sequence[Node], links: Sequence[tuple[str, str]]) -> list[set[str]]:
    neighbours: dict[str, set[str]] = {node.node_id: set() for node in nodes}
    for a, b in links:
        neighbours[a].add(b)
        neighbours[b].add(a)
    components: list[set[str]] = []
    for node in nodes:
        if any(node.node_id in component for component in components):
            continue
        component = {node.node_id}
        frontier = [node.node_id]
        while frontier:
            for other in sorted(neighbours[frontier.pop()]):
                if other not in component:
                    component.add(other)
                    frontier.append(other)
        components.append(component)
    return components


def _distance2(a: Node, b: Node) -> int:
    """Squared straight-line distance in cells: exact, and ordered like distance in metres."""
    return (a.row - b.row) ** 2 + (a.column - b.column) ** 2


# --- Which dependencies exist (E3) ----------------------------------------------------------


@dataclass
class _Need:
    """One dependency while it is being built."""

    pair: Pair
    consumer: Node
    row: DependencyRow
    eligible: list[Node]
    absent: bool = False
    feed: FeedConfiguration = FeedConfiguration.SINGLE
    suppliers: list[Node] = field(default_factory=list)
    sea_leg: set[str] = field(default_factory=set)
    hub_assigned: bool = False
    locked: bool = False
    notes: list[str] = field(default_factory=list)

    @property
    def transport(self) -> bool:
        return self.pair[0] == Layer.TRANSPORT


@dataclass(frozen=True)
class _LargeLoads:
    """What rule 4 and rule 5 read: peak loads, the threshold and the second-feed chance."""

    peak_mw: Mapping[str, float]
    threshold_mw: float
    second_feed_pct: int

    @classmethod
    def from_rules(
        cls, requirements: RequirementsResult, rules: Registry, voltage_kv: float
    ) -> "_LargeLoads":
        table = rules.value("dependencies.rule_4.transmission_threshold_mw")
        share = rules.number("dependencies.rule_5.tertiary_second_feed_share")
        return cls(
            peak_mw={n.node_id: n.peak_mw for n in requirements.nodes if n.peak_mw is not None},
            threshold_mw=float(table[f"{voltage_kv:g}"]),
            second_feed_pct=int(share * 100 + 0.5),
        )

    def suppliers(self, row: DependencyRow, consumer: Node) -> tuple[SupplierOption, ...]:
        """Return the row's suppliers, or a transmission substation for a large power consumer."""
        peak = self.peak_mw.get(consumer.node_id)
        # CHOICE: rule 4 moves a large consumer onto transmission; a smaller one keeps its row's
        # suppliers, so rows that already name a transmission substation (refinery, LNG
        # terminal) are not moved down to distribution.
        if row.supplier_layer != Layer.POWER or peak is None or peak < self.threshold_mw:
            return row.suppliers
        return (SupplierOption(NodeClass.TRANSMISSION_SUBSTATION),)


def _needs_of(pair: Pair, world: _World, large: _LargeLoads) -> list[_Need]:
    """Every dependency a pair's consumers could take: core, optional, and absent buffers."""
    supplier, consumer = pair
    needs = []
    for node in world.nodes[consumer]:
        subtype = dict(node.subtype)
        row = resolve_row(supplier, node.node_class, subtype, world.rules)
        if row.dependency == Dependency.NONE:
            continue
        options = large.suppliers(row, node)
        need = _Need(pair, node, row, _eligible(row.supplier_layer, options, node, world))
        # CHOICE: an absent buffer is recorded whether its row is core or optional, and is
        # not counted among the optional dependencies density draws from.
        if row.role == Role.BUFFER_RESUPPLY and subtype.get("standby_fuel") == NO_STANDBY:
            need.absent = True
            need.feed = FeedConfiguration.NONE
            need.notes.append(
                "no standby generator (standby_fuel none): no buffer-resupply edge "
                "(decision 0008, answer 3)"
            )
        if options != row.suppliers:
            need.notes.append(
                f"rule 4: peak load {large.peak_mw[node.node_id]:.3f} MW is at or above "
                f"{large.threshold_mw:g} MW, so a transmission substation supplies it"
            )
        needs.append(need)
    return needs


def _eligible(
    supplier_layer: Layer, options: Sequence[SupplierOption], consumer: Node, world: _World
) -> list[Node]:
    """Supplier nodes the options allow for this consumer, nearest first, ties by node id."""
    nodes = [
        node
        for node in world.nodes[supplier_layer]
        if any(_allows(option, node, consumer, world) for option in options)
    ]
    return sorted(nodes, key=lambda node: (_distance2(node, consumer), node.node_id))


def _allows(option: SupplierOption, supplier: Node, consumer: Node, world: _World) -> bool:
    if supplier.node_class != option.node_class:
        return False
    if option.product is not None and dict(supplier.subtype).get("product") != option.product:
        return False
    if option.when == SupplierWhen.INLAND:
        return world.inland(consumer)
    if option.when == SupplierWhen.OUTLYING_ISLAND:
        return world.outlying(consumer)
    if option.when == SupplierWhen.HAS_JETTY:
        return dict(consumer.subtype).get("has_jetty") is True
    if option.when == SupplierWhen.HAS_TRUCK_RACK:
        return dict(consumer.subtype).get("has_truck_rack") is True
    return True


def _apply_density(
    needs: dict[Pair, list[_Need]], density: int, streams: Mapping[Pair, np.random.Generator]
) -> None:
    """Keep round(density/100 x optional count) optional dependencies across the world.

    The world's count is shared among the pairs by largest remainder, and each pair picks its
    own by draw from its own stream (Work Order 4, E3).
    """
    pairs = list(needs)
    optional = {
        pair: [n for n in needs[pair] if n.row.dependency == Dependency.OPTIONAL and not n.absent]
        for pair in pairs
    }
    counts = _apportion(density, [len(optional[pair]) for pair in pairs])
    for pair, count in zip(pairs, counts, strict=True):
        order = _permutation(streams[pair], len(optional[pair]))
        taken = {id(optional[pair][i]) for i in order[:count]}
        needs[pair] = [
            n
            for n in needs[pair]
            if n.row.dependency == Dependency.CORE or n.absent or id(n) in taken
        ]


# --- Feed configuration (E4) and transport (E5) --------------------------------------------


def _configure_feeds(
    pair: Pair,
    needs: list[_Need],
    couplings: Couplings,
    streams: CouplingsStreams,
    second_feed_pct: int,
) -> None:
    """Apply the feed mix with exact largest-remainder counts; rule 5 and buffers apart."""
    mixed = [
        n
        for n in needs
        if not n.absent and n.row.role == Role.PRIMARY_SUPPLY and n.row.rule != "rule 5"
    ]
    mix = couplings.feed_mix
    single, two_full, two_half = _largest_remainder(
        len(mixed), (mix.single_feed_pct, mix.two_full_feeds_pct, mix.two_half_feeds_pct)
    )
    order = _permutation(streams.feed_configuration[pair], len(mixed))
    drawn = [mixed[i] for i in order]
    # CHOICE: two-feed configurations go first to dependencies that have two eligible supplier
    # nodes, so the realised counts meet the mix wherever the world allows.
    ranked = [n for n in drawn if len(n.eligible) >= 2] + [n for n in drawn if len(n.eligible) < 2]
    configurations = (
        [FeedConfiguration.TWO_FULL] * two_full
        + [FeedConfiguration.TWO_HALF] * two_half
        + [FeedConfiguration.SINGLE] * single
    )
    for need, configuration in zip(ranked, configurations, strict=True):
        _set_feed(need, configuration)
    for need in needs:
        if need.absent or need.row.rule != "rule 5":
            continue
        second = int(streams.tertiary_second_feed.integers(0, 100)) < second_feed_pct
        _set_feed(need, FeedConfiguration.TWO_FULL if second else FeedConfiguration.SINGLE)
        if second:
            need.notes.append("tertiary second feed drawn (rule 5): two full feeds")
    for need in needs:
        if not need.absent and not need.eligible:
            need.notes.append(f"no eligible {pair[0]} supplier node in the world")


def _set_feed(need: _Need, configuration: FeedConfiguration) -> None:
    if configuration != FeedConfiguration.SINGLE and len(need.eligible) < 2:
        if need.eligible:
            need.notes.append(
                f"drawn {configuration} but only one eligible supplier node: stays single"
            )
        configuration = FeedConfiguration.SINGLE
    need.feed = configuration


def _reach(needs: list[_Need], world: _World) -> None:
    """List every eligible origin that reaches each consumer (rule 3; decision 0008, answer 6).

    A consumer on a landmass with transport nodes reaches the origins in its nearest transport
    node's component over the road links. A consumer on an outlying island is reached by sea
    from any seaport in the main road component.
    """
    main = world.main_road_component()
    for need in needs:
        need.feed = FeedConfiguration.ANY_REACHABLE
        island = world.island(need.consumer)
        # CHOICE: a consumer joins the roads at the nearest transport node on its own landmass.
        access = [n for n in world.nodes[Layer.TRANSPORT] if world.island(n) == island]
        if access:
            nearest = min(access, key=lambda n: (_distance2(n, need.consumer), n.node_id))
            component = next(c for c in world.road_components if nearest.node_id in c)
            need.suppliers = [n for n in need.eligible if n.node_id in component]
            how = "over the transport links"
        else:
            need.suppliers = [
                n for n in need.eligible if n.node_class == NodeClass.SEAPORT and n.node_id in main
            ]
            need.sea_leg = {n.node_id for n in need.suppliers}
            how = "over the transport links, nor by sea from a main-island seaport"
        need.eligible = list(need.suppliers)
        if not need.suppliers:
            need.notes.append(f"no eligible origin reaches it {how}")


# --- Supplier choice (E7) -------------------------------------------------------------------


def _choose_suppliers(
    pair: Pair,
    needs: list[_Need],
    couplings: Couplings,
    streams: CouplingsStreams,
    notes: list[str],
) -> Node | None:
    """Draw the pair's hub, assign first feeds by concentration and not-nearest, then seconds."""
    active = [n for n in needs if not n.absent and n.eligible]
    candidates = sorted(
        {node.node_id: node for n in active for node in n.eligible}.values(),
        key=lambda node: node.node_id,
    )
    hub = _draw_hub(streams.hub[pair], candidates)
    first: dict[int, Node] = {}
    carried = [n for n in active if hub is not None and hub in n.eligible]
    order = _permutation(streams.concentration[pair], len(carried))
    for i in order[: _percent_of(couplings.concentration, len(carried))]:
        carried[i].hub_assigned = True
        if hub is not None:
            first[id(carried[i])] = hub
    target = _percent_of(couplings.supplier_not_nearest_pct, len(active))
    from_hub = sum(1 for n in active if n.hub_assigned and first[id(n)] is not n.eligible[0])
    wanted = target - from_hub
    pool = [n for n in active if not n.hub_assigned and len(n.eligible) >= 2]
    stream = streams.supplier_not_nearest[pair]
    planted = 0
    for i in _permutation(stream, len(pool)):
        if planted >= wanted:
            break
        need = pool[i]
        others = need.eligible[1:]
        weights = [_inverse_distance(other, need) for other in others]
        first[id(need)] = others[_weighted_index(stream, weights)]
        planted += 1
    if wanted < 0:
        notes.append(
            f"concentration puts {from_hub} first feeds off the nearest supplier, above the "
            f"{target} supplier_not_nearest asks for; concentration wins"
        )
    elif planted < wanted:
        notes.append(
            f"supplier_not_nearest asks for {target} first feeds off the nearest supplier; only "
            f"{from_hub + planted} could be (too few dependencies with two eligible suppliers)"
        )
    for need in active:
        chosen = first.get(id(need), need.eligible[0])
        need.suppliers = [chosen]
        if need.feed in (FeedConfiguration.TWO_FULL, FeedConfiguration.TWO_HALF):
            need.suppliers.append(next(n for n in need.eligible if n is not chosen))
    return hub


def _draw_hub(stream: np.random.Generator, candidates: list[Node]) -> Node | None:
    """Draw the hub, weighted by capacity where every candidate carries the same capacity."""
    if not candidates:
        return None
    capacities = [_capacity(node) for node in candidates]
    names = {name for name, _ in capacities}
    # CHOICE: suppliers of different kinds (storage against throughput) are not comparable, so
    # a mixed candidate set is drawn uniformly.
    if len(names) == 1 and None not in names:
        weights = [max(1, int(value * CAPACITY_WEIGHT_PER_UNIT + 0.5)) for _, value in capacities]
    else:
        weights = [1] * len(candidates)
    return candidates[_weighted_index(stream, weights)]


def _capacity(node: Node) -> tuple[str | None, float]:
    attributes = dict(node.attributes)
    for name in CAPACITY_ATTRIBUTES:
        value = attributes.get(name)
        if isinstance(value, int | float) and not isinstance(value, bool):
            return name, float(value)
    return None, 0.0


def _inverse_distance(supplier: Node, need: _Need) -> int:
    distance = math.sqrt(max(1, _distance2(supplier, need.consumer)))
    return max(1, int(WEIGHT_RESOLUTION / distance + 0.5))


# --- Two-way (E9) ---------------------------------------------------------------------------


@dataclass(frozen=True)
class _Mutual:
    """Allowed and realised mutual node pairs of one couple of layers."""

    allowed: int
    built: int


def _two_way(
    needs: dict[Pair, list[_Need]],
    two_way_pct: int,
    streams: Mapping[Pair, np.random.Generator],
    notes: dict[Pair, list[str]],
) -> dict[Pair, _Mutual]:
    """Build round(two_way_pct/100 x allowed) mutual pairs per couple; break every other one.

    An allowed pair is two nodes where one already serves the other and could be served back
    by it, each dependency taking part in at most one. Where a mutual pair must be broken, the
    later edge in canonical order (the reverse pair's) takes the next eligible supplier. Failing
    that, an optional dependency's feed is dropped with a note, but a core dependency is never
    left without a supplier: the mutual pair is kept, with a note (decision 0008, review 1).
    """
    # CHOICE: allowed pairs start from edges already chosen, so at 100 every one can be built.
    # Pairs among hidden couplings count too, so hiding a pair changes only its flag (decision
    # 0008, review 2).
    realised: dict[Pair, _Mutual] = {}
    for couple in rng.mutual_couples():
        reverse = (couple[1], couple[0])
        if couple not in needs or reverse not in needs:
            continue
        candidates = _mutual_candidates(needs[couple], needs[reverse])
        count = _percent_of(two_way_pct, len(candidates))
        selected = [candidates[i] for i in _permutation(streams[couple], len(candidates))[:count]]
        for need, _supplier, other in selected:
            if need.consumer not in other.suppliers:
                other.notes.append(
                    f"two-way: first feed {other.suppliers[0].node_id} replaced by "
                    f"{need.consumer.node_id}, its mutual partner"
                )
                other.suppliers[0] = need.consumer
        keep = {frozenset((n.consumer.node_id, s.node_id)) for n, s, _ in selected}
        kept = _break_mutual(needs[couple], needs[reverse], keep)
        built = len(_mutual_keys(needs[couple], needs[reverse]))
        realised[couple] = realised[reverse] = _Mutual(len(candidates), built)
        for pair in (couple, reverse):
            notes[pair].append(
                f"two-way with {rng.pair_label(*(reverse if pair == couple else couple))}: "
                f"{len(candidates)} allowed mutual pairs, {count} wanted, {built} built"
                + (f" ({kept} kept so a core dependency keeps a supplier)" if kept else "")
            )
    return realised


def _mutual_candidates(
    forward: list[_Need], backward: list[_Need]
) -> list[tuple[_Need, Node, _Need]]:
    candidates = []
    seen: set[frozenset[str]] = set()
    for these, those in ((forward, backward), (backward, forward)):
        served = {n.consumer.node_id: n for n in those if not n.absent}
        for need in these:
            for supplier in list(need.suppliers):
                other = served.get(supplier.node_id)
                if other is None or need.consumer not in other.eligible:
                    continue
                key = frozenset((need.consumer.node_id, supplier.node_id))
                if key in seen or need.locked or other.locked:
                    continue
                seen.add(key)
                candidates.append((need, supplier, other))
                need.locked = not need.transport
                other.locked = not other.transport
    return candidates


def _served_pairs(needs: list[_Need]) -> set[tuple[str, str]]:
    return {(s.node_id, n.consumer.node_id) for n in needs for s in n.suppliers}


def _mutual_keys(forward: list[_Need], backward: list[_Need]) -> set[frozenset[str]]:
    served = _served_pairs(forward)
    return {frozenset(pair) for pair in _served_pairs(backward) if (pair[1], pair[0]) in served}


def _break_mutual(forward: list[_Need], backward: list[_Need], keep: set[frozenset[str]]) -> int:
    """Break every mutual pair not kept; return how many had to stay for a core dependency."""
    served = _served_pairs(forward)
    kept = 0
    for need in backward:
        index = 0
        while index < len(need.suppliers):
            supplier = need.suppliers[index]
            key = frozenset((supplier.node_id, need.consumer.node_id))
            if (need.consumer.node_id, supplier.node_id) not in served or key in keep:
                index += 1
                continue
            replacement = None
            if not need.transport:
                replacement = next(
                    (
                        n
                        for n in need.eligible
                        if n not in need.suppliers
                        and (need.consumer.node_id, n.node_id) not in served
                    ),
                    None,
                )
            if replacement is not None:
                need.notes.append(
                    f"two-way off: {supplier.node_id} would make a mutual pair; "
                    f"{replacement.node_id} serves instead"
                )
                need.suppliers[index] = replacement
                index += 1
                continue
            if need.row.dependency == Dependency.CORE and len(need.suppliers) == 1:
                need.notes.append(
                    f"mutual pair kept: no other eligible supplier than {supplier.node_id}, and a "
                    "core dependency is never left without one (decision 0008, review 1)"
                )
                kept += 1
                index += 1
                continue
            need.notes.append(
                f"two-way off: {supplier.node_id} would make a mutual pair and no other eligible "
                "supplier avoids one; that feed is dropped"
            )
            del need.suppliers[index]
            need.sea_leg.discard(supplier.node_id)
        if len(need.suppliers) < 2 and need.feed in (
            FeedConfiguration.TWO_FULL,
            FeedConfiguration.TWO_HALF,
        ):
            need.feed = FeedConfiguration.SINGLE
    return kept


# --- Edges and dependencies (E6, E8, E10, E11) ----------------------------------------------


class _Builder:
    """Numbers every dependency and edge in canonical order, then keeps the generated pairs."""

    def __init__(
        self,
        world: _World,
        couplings: Couplings,
        transfer_forms: TransferForms,
        needs: dict[Pair, list[_Need]],
        hubs: dict[Pair, Node | None],
        switched: set[Pair],
        kept: set[Pair],
    ) -> None:
        self.world = world
        self.couplings = couplings
        self.transfer_forms = transfer_forms
        self.needs = needs
        self.hubs = hubs
        self.switched = switched
        self.kept = kept
        self.edges: list[CouplingEdge] = []
        self.dependencies: list[CouplingDependency] = []
        self.dependency_ids: dict[int, str] = {}

    def build(self, pairs: list[Pair]) -> None:
        # CHOICE: numbering runs over every pair built, kept or not, so leaving a pair out
        # never renumbers another pair's edges; ids of a left-out pair are gaps.
        number = 0
        for pair in pairs:
            for need in self.needs[pair]:
                number += 1
                self.dependency_ids[id(need)] = f"SWM-DEP-{number:04d}"
        edge_number = 0
        drafts: list[tuple[_Need, list[CouplingEdge]]] = []
        for pair in pairs:
            for need in self.needs[pair]:
                edges = []
                for index, supplier in enumerate(need.suppliers):
                    edge_number += 1
                    edges.append(self._edge(edge_number, need, index, supplier))
                drafts.append((need, edges))
        partner = {(e.supplier_id, e.consumer_id): e.edge_id for _, es in drafts for e in es}
        for need, edges in drafts:
            if need.pair not in self.kept:
                continue
            edges = [_with_partner(e, partner.get((e.consumer_id, e.supplier_id))) for e in edges]
            self.edges.extend(edges)
            self.dependencies.append(self._dependency(need, edges))

    def _edge(self, number: int, need: _Need, index: int, supplier: Node) -> CouplingEdge:
        row, consumer = need.row, need.consumer
        dependency_type = row.dependency_type
        if dependency_type is None or row.role is None or row.commodity is None:
            raise ValueError(f"row {row.key} is active but incomplete")
        hub = self.hubs.get(need.pair)
        dx, dy = supplier.x_m - consumer.x_m, supplier.y_m - consumer.y_m
        length_m = math.sqrt(dx * dx + dy * dy)
        return CouplingEdge(
            edge_id=f"SWM-CPL-{number:04d}",
            supplier_id=supplier.node_id,
            consumer_id=consumer.node_id,
            supplier_layer=need.pair[0],
            consumer_layer=need.pair[1],
            commodity=row.commodity,
            dependency_type=dependency_type.value,
            role=row.role,
            transfer_form=getattr(self.transfer_forms, dependency_type.value).value,
            feed_configuration=need.feed,
            feed_group=_feed_group(need.feed, index),
            dependency_id=self.dependency_ids[id(need)],
            backs_dependency=self._backs(need),
            public_share_pct=self._public_share(need),
            switched_on=need.pair in self.switched,
            is_nearest=bool(need.eligible) and supplier is need.eligible[0],
            is_hub=hub is not None and supplier is hub and not need.transport,
            mutual_partner=None,
            sea_leg=supplier.node_id in need.sea_leg,
            points=((supplier.x_m, supplier.y_m), (consumer.x_m, consumer.y_m)),
            length_km=round(length_m / 1000, 3),
            crosses_sea=self.world.crosses_sea(supplier, consumer),
        )

    def _backs(self, need: _Need) -> str | None:
        if need.row.role != Role.BUFFER_RESUPPLY:
            return None
        power = (Layer.POWER, need.pair[1])
        if power not in self.kept:
            return None
        backed = next(
            (n for n in self.needs[power] if n.consumer is need.consumer and not n.absent), None
        )
        return None if backed is None else self.dependency_ids[id(backed)]

    def _public_share(self, need: _Need) -> int | None:
        if need.row.rule != "rule 1":
            return None
        consumer = need.consumer
        name = PUBLIC_SHARE_FIELDS.get(consumer.node_class) or PUBLIC_SHARE_LAYERS.get(
            consumer.layer
        )
        if name is None:
            return None
        share: int = getattr(self.couplings.public_telecom_share, name)
        return share

    def _dependency(self, need: _Need, edges: list[CouplingEdge]) -> CouplingDependency:
        notes = list(need.notes)
        if need.row.role == Role.BUFFER_RESUPPLY and edges and edges[0].backs_dependency is None:
            notes.append("the power dependency it backs is not generated")
        if not need.absent and not edges and need.eligible:
            notes.append("no supplier remains")
        role = need.row.role
        if role is None:
            raise ValueError(f"row {need.row.key} is active but has no role")
        return CouplingDependency(
            dependency_id=self.dependency_ids[id(need)],
            consumer_id=need.consumer.node_id,
            supplier_layer=need.pair[0],
            consumer_layer=need.pair[1],
            row_key=need.row.key,
            dependency=need.row.dependency,
            role=role,
            feed_configuration=need.feed,
            edge_ids=tuple(edge.edge_id for edge in edges),
            switched_on=need.pair in self.switched,
            notes=tuple(notes),
        )


def _with_partner(edge: CouplingEdge, partner: str | None) -> CouplingEdge:
    return replace(edge, mutual_partner=partner)


def _feed_group(configuration: FeedConfiguration, index: int) -> int:
    """Two half feeds are one group (both needed); otherwise each feed is its own group."""
    # CHOICE: the feed group numbers what the dynamics needs: edges in one group are all
    # needed, and any one group serves.
    return 1 if configuration == FeedConfiguration.TWO_HALF else index + 1


# --- Statistics -----------------------------------------------------------------------------


def _pair_statistics(
    pair: Pair,
    needs: list[_Need],
    hub: Node | None,
    builder: _Builder,
    mutual: Mapping[Pair, _Mutual],
    notes: list[str],
    switched: set[Pair],
) -> PairStatistics:
    counts = {configuration.value: 0 for configuration in FeedConfiguration}
    for need in needs:
        counts[need.feed.value] += 1
    mixed = [
        n
        for n in needs
        if not n.absent and n.row.role == Role.PRIMARY_SUPPLY and n.row.rule != "rule 5"
        and not n.transport
    ]  # fmt: skip
    shares = {
        configuration.value: _ratio(sum(1 for n in mixed if n.feed == configuration), len(mixed))
        for configuration in (
            FeedConfiguration.SINGLE,
            FeedConfiguration.TWO_FULL,
            FeedConfiguration.TWO_HALF,
        )
    }
    chosen = [n for n in needs if not n.transport and n.suppliers]
    edges = sum(len(n.suppliers) for n in needs)
    return PairStatistics(
        supplier=pair[0],
        consumer=pair[1],
        switched_on=pair in switched,
        dependencies=len(needs),
        absent=sum(n.absent for n in needs),
        edges=edges,
        feed_counts=counts,
        feed_shares=shares,
        non_nearest_share=_ratio(
            sum(n.suppliers[0] is not n.eligible[0] for n in chosen), len(chosen)
        ),
        hub=None if hub is None else hub.node_id,
        hub_share=_ratio(sum(n.suppliers[0] is hub for n in chosen), len(chosen)),
        mutual_pairs_allowed=mutual[pair].allowed if pair in mutual else 0,
        mutual_pairs=mutual[pair].built if pair in mutual else 0,
        notes=tuple(notes),
    )


def _ratio(part: int, whole: int) -> float:
    return round(part / whole, 3) if whole else 0.0


# --- Exact counting and drawing -------------------------------------------------------------


def _percent_of(percent: int, count: int) -> int:
    """round(percent/100 x count), halves up, in integers."""
    return (2 * percent * count + 100) // 200


def _largest_remainder(count: int, percents: Sequence[int]) -> list[int]:
    """Split count by percentages totalling 100: floors, then largest remainders, ties by order."""
    floors = [count * p // 100 for p in percents]
    remainders = [count * p % 100 for p in percents]
    order = sorted(range(len(percents)), key=lambda i: (-remainders[i], i))
    for i in order[: count - sum(floors)]:
        floors[i] += 1
    return floors


def _apportion(percent: int, sizes: Sequence[int]) -> list[int]:
    """Share round(percent/100 x total) among groups by largest remainder, ties by order."""
    floors = [percent * size // 100 for size in sizes]
    remainders = [percent * size % 100 for size in sizes]
    extra = _percent_of(percent, sum(sizes)) - sum(floors)
    order = sorted(range(len(sizes)), key=lambda i: (-remainders[i], i))
    for i in order[:extra]:
        floors[i] += 1
    return floors


def _permutation(stream: np.random.Generator, count: int) -> list[int]:
    """Shuffle range(count) by Fisher-Yates, drawing uniform integers only."""
    order = list(range(count))
    for i in range(count - 1, 0, -1):
        j = int(stream.integers(0, i + 1))
        order[i], order[j] = order[j], order[i]
    return order


def _weighted_index(stream: np.random.Generator, weights: Sequence[int]) -> int:
    """Draw an index with probability proportional to its integer weight."""
    pick = int(stream.integers(0, sum(weights)))
    for index, weight in enumerate(weights):
        if pick < weight:
            return index
        pick -= weight
    raise AssertionError("unreachable: the pick lies below the total weight")
