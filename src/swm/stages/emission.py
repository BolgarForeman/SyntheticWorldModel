"""Emission stage: the observed world every source is written from (structure v0.10 §4.6).

Projects the built world onto what a source could see, and draws the three things emission
adds to it, each on its own stream so nothing else moves:
- **town names:** plain, pronounceable invented names from the registry's syllables, one per
  urban area (E4);
- **footprints:** a rectangle centred on the true location for each area class, its sides
  drawn per node between the registry's lengths (E2);
- **the unnamed share** of masts, pumping stations and distribution substations (E4).

Only observed quantities pass through: subtypes, requirements, reserves, couplings and feeds
never reach the result (CLAUDE.md §3).

Spec: structure v0.10 §4.6; Work Order 8, A3-A4; Emission ruling sheet v0.2, E2 and E4.
"""

import math
from collections.abc import Mapping, Sequence

from swm import rng
from swm.coordinates import cell_centre_m, to_lonlat
from swm.emit.observed import (
    LonLat,
    ObservedLink,
    ObservedNode,
    ObservedTown,
    ObservedWorld,
)
from swm.recipe.schema import Layer, Layers, LayerState, NodeClass
from swm.rules.registry import Registry
from swm.stages.couplings import _percent_of, _permutation
from swm.stages.layers import LayersResult, Node
from swm.stages.terrain import TerrainResult

C = NodeClass
AREA_CLASSES = frozenset({
    C.GENERATION, C.TRANSMISSION_SUBSTATION, C.DISTRIBUTION_SUBSTATION, C.TERTIARY, C.REGIONAL,
    C.TREATMENT, C.RESERVOIR, C.SEAPORT, C.AIRPORT, C.TANK_FARM, C.REFINERY,
})  # fmt: skip
"""Classes real mapping draws as areas: plants, substations, hospitals, water works,
reservoirs, ports, airports, tank farms and refineries (E2)."""


def build_observed(
    settings: Layers, terrain: TerrainResult, layers: LayersResult, rules: Registry, root_seed: int
) -> ObservedWorld:
    """Return the observed world every source is written from.

    Parameters
    ----------
    settings : Layers
        The recipe's layers: states, sources and nodes-only switches.
    terrain : TerrainResult
        The terrain: the towns and the grid.
    layers : LayersResult
        The layers, power sized: nodes, links and mapped power lines.
    rules : Registry
        The modeling rules in force (``emission.*``).
    root_seed : int
        The recipe's root seed, for the emission streams.

    Returns
    -------
    ObservedWorld
        Nodes of emitted layers, links of emitted layers that are not nodes-only, and towns.

    Spec: structure v0.10 §4.6; Work Order 8, A3-A4.
    """
    towns = _towns(terrain, rules, root_seed)
    by_id = {town.town_id: town for town in towns}
    emitted = [layer for layer in Layer if settings.get(layer).state == LayerState.EMITTED]
    unnamed = _unnamed(layers.nodes, emitted, rules, root_seed)
    kept = [n for n in sorted(layers.nodes, key=lambda n: n.node_id) if n.layer in emitted]
    qualifiers = repeat_qualifiers(kept, terrain, rules)
    nodes = tuple(
        _node(
            node,
            by_id[node.city_id],
            node.node_id not in unnamed,
            rules,
            root_seed,
            qualifiers.get(node.node_id, (None, None)),
        )
        for node in kept
    )
    nodes_only = frozenset(layer for layer in emitted if settings.get(layer).nodes_only)
    return ObservedWorld(
        nodes=nodes,
        links=_links(layers, emitted, nodes_only),
        towns=towns,
        sources=tuple((layer, tuple(settings.get(layer).sources)) for layer in emitted),
        nodes_only=nodes_only,
    )


# --- Towns (E4) -----------------------------------------------------------------------------


def _towns(terrain: TerrainResult, rules: Registry, root_seed: int) -> tuple[ObservedTown, ...]:
    syllables = rules.value("emission.names.syllables")
    place_share = rules.number("emission.names.place_word_share")
    taken: set[str] = set()
    towns = []
    for city in sorted(terrain.cities, key=lambda c: c.city_id):
        stream = rng.element_stream(root_seed, "emission/names", f"town-{city.city_id}")
        name = town_name(syllables, place_share, stream, taken)
        taken.add(name)
        x_m, y_m = cell_centre_m(city.centre_row, city.centre_column, terrain.grid)
        towns.append(ObservedTown(city.city_id, name, f"XS-{city.city_id + 1:02d}",
                                  to_lonlat(x_m, y_m)))  # fmt: skip
    return tuple(towns)


def town_name(
    syllables: Mapping[str, Sequence[str]], place_share: float, stream: object, taken: set[str]
) -> str:
    """Draw one invented town name, drawn again until it differs from every name taken.

    A first syllable, an optional middle vowel and a last syllable, and sometimes a place word.

    Parameters
    ----------
    syllables : Mapping
        The registry's ``first``, ``middle``, ``last`` and ``places`` lists.
    place_share : float
        The share of names that take a place word.
    stream : numpy.random.Generator
        The town's own stream.
    taken : set of str
        Names already given.

    Returns
    -------
    str
        The name, such as "Corvan" or "Brenna Point".

    Spec: Work Order 8, A4; Emission ruling sheet v0.2, E4.
    """
    while True:
        first = _pick(syllables["first"], stream)
        middle = _pick(syllables["middle"], stream)
        last = _pick(syllables["last"], stream)
        name = first + middle + last
        if float(stream.random()) < place_share:  # type: ignore[attr-defined]
            name = f"{name} {_pick(syllables['places'], stream)}"
        if name not in taken:
            return name


def _pick(options: Sequence[str], stream: object) -> str:
    return options[int(stream.integers(len(options)))]  # type: ignore[attr-defined]


# --- Names and outlines ---------------------------------------------------------------------


def _unnamed(
    nodes: Sequence[Node], emitted: Sequence[Layer], rules: Registry, root_seed: int
) -> set[str]:
    """Leave the ruled share of each minor class unnamed, chosen on its layer's stream."""
    share = rules.number("emission.names.unnamed_share")
    minor = [NodeClass(value) for value in rules.value("emission.names.unnamed_classes")]
    unnamed: set[str] = set()
    for layer in emitted:
        stream = rng.stream(root_seed, f"emission/unnamed/{layer}")
        for node_class in minor:
            members = sorted(
                n.node_id for n in nodes if n.layer == layer and n.node_class == node_class
            )
            if not members:
                continue
            order = _permutation(stream, len(members))
            count = _percent_of(int(share * 100 + 0.5), len(members))
            unnamed |= {members[i] for i in order[:count]}
    return unnamed


def repeat_qualifiers(
    nodes: Sequence[Node], terrain: TerrainResult, rules: Registry
) -> dict[str, tuple[str, int | None]]:
    """Tell apart facilities of one name group in one town by direction word, then number.

    Every class is unique by name within its town unless it is on the shared-name list; classes
    that share a name word (``name_groups``) count as one group, every other class as its own.
    The first of a group in sorted world-id order keeps the plain name; each repeat takes the
    word for its side of the town centre, and repeats that share a side are numbered from 2 in
    world-id order.

    Parameters
    ----------
    nodes : sequence of Node
        The emitted nodes, sorted by id.
    terrain : TerrainResult
        The terrain, for the town centres.
    rules : Registry
        The modeling rules in force (``emission.names.name_groups``, ``shared_name_classes``,
        ``direction_words``).

    Returns
    -------
    dict
        Per repeated node id, its direction word and its number (None unless another repeat in
        its town shares the side).

    Spec: structure v0.12 §4.6 (names); WO-08 PR answers, item 4, and answers 2, item 2.
    """
    shared = {NodeClass(c) for c in rules.value("emission.names.shared_name_classes")}
    group_of = {NodeClass(c): group for group, classes in
                rules.value("emission.names.name_groups").items() for c in classes}  # fmt: skip
    words = rules.value("emission.names.direction_words")
    centres = {c.city_id: cell_centre_m(c.centre_row, c.centre_column, terrain.grid)
               for c in terrain.cities}  # fmt: skip
    members: dict[tuple[int, str], list[Node]] = {}
    for node in nodes:
        if node.node_class not in shared:
            group = group_of.get(node.node_class, node.node_class.value)
            members.setdefault((node.city_id, group), []).append(node)
    qualifiers: dict[str, tuple[str, int | None]] = {}
    for (city_id, _), group in sorted(members.items()):
        # CHOICE: the lowest world id keeps the plain name; numbering of a shared side starts at 2.
        seen: dict[str, int] = {}
        for node in group[1:]:
            cx, cy = centres[city_id]
            word = words[side(node.x_m - cx, node.y_m - cy)]
            seen[word] = seen.get(word, 0) + 1
            qualifiers[node.node_id] = (word, seen[word] if seen[word] > 1 else None)
    return qualifiers


def side(east_m: float, north_m: float) -> str:
    """Return the side of a point from a centre: east, west, north or south.

    Comparisons only, no trigonometry (CLAUDE.md §4): the larger absolute offset decides the
    axis and its sign the side.

    Parameters
    ----------
    east_m, north_m : float
        The point's offsets from the centre, in m.

    Returns
    -------
    str
        ``east``, ``west``, ``north`` or ``south``.

    Spec: WO-08 PR answers, item 4.
    """
    # CHOICE: a point exactly on a diagonal counts as east or west.
    if abs(east_m) >= abs(north_m):
        return "east" if east_m >= 0 else "west"
    return "north" if north_m >= 0 else "south"


def _node(
    node: Node,
    town: ObservedTown,
    named: bool,
    rules: Registry,
    root_seed: int,
    qualifier: tuple[str | None, int | None],
) -> ObservedNode:
    return ObservedNode(
        node_id=node.node_id,
        layer=node.layer,
        node_class=node.node_class,
        location=(node.longitude, node.latitude),
        attributes=node.attributes,
        town=town.name,
        named=named,
        outline=_outline(node, rules, root_seed) if node.node_class in AREA_CLASSES else None,
        runway=None
        if node.runway is None
        else (to_lonlat(*node.runway[0]), to_lonlat(*node.runway[1])),
        district=town.district,
        direction=qualifier[0],
        number=qualifier[1],
    )


def _outline(node: Node, rules: Registry, root_seed: int) -> tuple[LonLat, ...]:
    """Return the area class's closed rectangle in WGS 84 (E2)."""
    ring = [to_lonlat(x, y) for x, y in outline_m(node, rules, root_seed)]
    return (*ring, ring[0])


def outline_m(node: Node, rules: Registry, root_seed: int) -> tuple[tuple[float, float], ...]:
    """Return an area class's rectangle corners, centred on its true location.

    Parameters
    ----------
    node : Node
        A node of an area class.
    rules : Registry
        The modeling rules in force (``emission.footprint_m``).
    root_seed : int
        The recipe's root seed.

    Returns
    -------
    tuple of (float, float)
        The four corners in EPSG:32710 metres, anticlockwise from the south-west.

    Spec: Work Order 8, A3; Emission ruling sheet v0.2, E2.
    """
    low, high = rules.value("emission.footprint_m")[node.node_class.value]
    stream = rng.element_stream(root_seed, f"emission/footprint/{node.layer}", node.node_id)
    half_w = (low + (high - low) * float(stream.random())) / 2.0
    half_h = (low + (high - low) * float(stream.random())) / 2.0
    corners = ((-half_w, -half_h), (half_w, -half_h), (half_w, half_h), (-half_w, half_h))
    return tuple((node.x_m + dx, node.y_m + dy) for dx, dy in corners)


# --- Links ----------------------------------------------------------------------------------


def _links(
    layers: LayersResult, emitted: Sequence[Layer], nodes_only: frozenset[Layer]
) -> tuple[ObservedLink, ...]:
    lines = {line.link_id: line for line in layers.power_lines}
    result = []
    for link in sorted(layers.links, key=lambda link: link.link_id):
        if link.layer not in emitted or link.layer in nodes_only:
            continue
        route = tuple(to_lonlat(x, y) for x, y in link.points)
        line = lines.get(link.link_id)
        if line is None:
            result.append(ObservedLink(link.link_id, link.layer, link.from_id, link.to_id, route))
            continue
        towers = tuple(to_lonlat(x, y) for x, y in line.tower_points)
        result.append(ObservedLink(link.link_id, link.layer, link.from_id, link.to_id, route,
                                   line.voltage_kv, line.circuits, towers))  # fmt: skip
    return tuple(result)


def degrees_apart(a: LonLat, b: LonLat) -> float:
    """Return the straight distance between two WGS 84 points in degrees (for tests)."""
    return math.sqrt((b[0] - a[0]) * (b[0] - a[0]) + (b[1] - a[1]) * (b[1] - a[1]))
