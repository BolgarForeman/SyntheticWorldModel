"""The OpenStreetMap features of an island, before they are written in any form (E1-E3).

One set of features serves every OpenStreetMap view: the PBF extract and its XML copy, the
Geofabrik-style shapefiles and the Overpass-style GeoJSON. Each switched-on OpenStreetMap
source contributes the features in its scope:
- a point class is a tagged node; an area class is a closed way round a rectangle centred on
  the true location, with an untagged anchor node at the centre that links end on;
- a power line is a way through its tower nodes; a main, pipeline, communication line or road
  is a way along its route; nodes-only layers have none;
- every town is a ``place=town`` node.

Ids start at 9,000,000,000,000 and are assigned in the sorted order of the world's own ids,
nodes and ways each counting from there. Every object is version 1 with one fixed timestamp,
user and changeset.

Spec: structure v0.10 §4.6; Work Order 8, A1-A3; Emission ruling sheet v0.2, E1-E3.
"""

from collections.abc import Mapping
from dataclasses import dataclass, field

from swm.emit.observed import LonLat, ObservedLink, ObservedNode, ObservedWorld
from swm.emit.osm_tags import PORT_PIECE_SHARE, PORT_PIECE_TAGS, link_tags, node_tags
from swm.recipe.schema import SOURCE_SCOPES, Layer, NodeClass, Source

FIRST_ID = 9_000_000_000_000
"""Far above any real OpenStreetMap id, so a synthetic object is never taken for a real one."""
TIMESTAMP = "2026-01-01T00:00:00Z"
TIMESTAMP_S = 1_767_225_600
"""2026-01-01T00:00:00Z in seconds since 1970, the one timestamp every object carries."""
USER = "swm"
UID = 1
CHANGESET = 1

OSM_SOURCES: Mapping[Layer, Source] = {
    Layer.POWER: Source.OSM_POWER,
    Layer.TELECOM: Source.OSM_TELECOM,
    Layer.WATER: Source.OSM_WATER,
    Layer.TRANSPORT: Source.OSM_TRANSPORT,
    Layer.FUEL: Source.OSM_FUEL,
    Layer.HEALTHCARE: Source.OSM_HEALTH,
}
"""Each layer's OpenStreetMap source."""


@dataclass(frozen=True)
class OsmNode:
    """One OpenStreetMap node."""

    osm_id: int
    location: LonLat
    tags: tuple[tuple[str, str], ...] = ()


@dataclass(frozen=True)
class OsmWay:
    """One OpenStreetMap way: an outline (first node repeated) or a line."""

    osm_id: int
    refs: tuple[int, ...]
    tags: tuple[tuple[str, str], ...] = ()


@dataclass(frozen=True)
class OsmElement:
    """Which OpenStreetMap objects one true element became (for the truth manifest)."""

    element_id: str
    kind: str
    """node (a point), area (a closed way), line (a way) or town."""
    node: int | None = None
    way: int | None = None
    corners: tuple[int, ...] = ()
    anchor: int | None = None
    towers: tuple[int, ...] = ()


@dataclass(frozen=True)
class OsmData:
    """Every OpenStreetMap object of the island, nodes and ways each sorted by id."""

    nodes: tuple[OsmNode, ...]
    ways: tuple[OsmWay, ...]
    elements: tuple[OsmElement, ...]

    def bounds(self) -> tuple[float, float, float, float]:
        """Return (min lon, min lat, max lon, max lat) over every node."""
        lons = [n.location[0] for n in self.nodes]
        lats = [n.location[1] for n in self.nodes]
        return min(lons), min(lats), max(lons), max(lats)


@dataclass
class _Builder:
    nodes: list[OsmNode] = field(default_factory=list)
    ways: list[OsmWay] = field(default_factory=list)
    elements: list[OsmElement] = field(default_factory=list)
    endpoints: dict[str, int] = field(default_factory=dict)
    """A facility's node a link ends on: its point node, or its outline's anchor."""

    def node(self, location: LonLat, tags: Mapping[str, str] | None = None) -> int:
        osm_id = FIRST_ID + len(self.nodes)
        self.nodes.append(OsmNode(osm_id, location, tuple((tags or {}).items())))
        return osm_id

    def way(self, refs: tuple[int, ...], tags: Mapping[str, str]) -> int:
        osm_id = FIRST_ID + len(self.ways)
        self.ways.append(OsmWay(osm_id, refs, tuple(tags.items())))
        return osm_id


def osm_data(world: ObservedWorld) -> OsmData:
    """Return the OpenStreetMap objects of every switched-on OpenStreetMap source.

    Parameters
    ----------
    world : ObservedWorld
        The observed world.

    Returns
    -------
    OsmData
        Nodes and ways, with each true element's objects for the manifest.

    Spec: Work Order 8, A1-A3.
    """
    builder = _Builder()
    in_scope = {n.node_id: n for n in world.nodes if _carried(world, n)}
    links = {link.link_id: link for link in world.links if _link_carried(world, link)}
    keyed: list[tuple[str, str]] = [(i, "node") for i in in_scope] + [(i, "link") for i in links]
    for element_id, kind in sorted(keyed):
        if kind == "node":
            _facility(builder, in_scope[element_id])
        else:
            _link(builder, links[element_id])
    for town in world.towns:
        tags = {"name": town.name, "place": "town"}
        osm_id = builder.node(town.centre, tags)
        builder.elements.append(OsmElement(f"town-{town.town_id}", "town", node=osm_id))
    return OsmData(tuple(builder.nodes), tuple(builder.ways), tuple(builder.elements))


def _carried(world: ObservedWorld, node: ObservedNode) -> bool:
    source = OSM_SOURCES[node.layer]
    if source not in world.sources_of(node.layer):
        return False
    return node.node_class in SOURCE_SCOPES[source].classes


def _link_carried(world: ObservedWorld, link: ObservedLink) -> bool:
    return OSM_SOURCES[link.layer] in world.sources_of(link.layer) and (
        link.layer not in world.nodes_only
    )


def _facility(builder: _Builder, node: ObservedNode) -> None:
    tags = node_tags(node)
    if node.outline is None:
        osm_id = builder.node(node.location, tags)
        builder.endpoints[node.node_id] = osm_id
        builder.elements.append(OsmElement(node.node_id, "node", node=osm_id))
        return
    corners = tuple(builder.node(corner) for corner in node.outline[:-1])
    anchor = builder.node(node.location)
    builder.endpoints[node.node_id] = anchor
    way = builder.way((*corners, corners[0]), tags)
    builder.elements.append(
        OsmElement(node.node_id, "area", way=way, corners=corners, anchor=anchor)
    )
    if node.node_class == NodeClass.SEAPORT:
        _port_piece(builder, node)


def _port_piece(builder: _Builder, node: ObservedNode) -> None:
    """Map a port's cargo area as an industrial=port outline inside its harbour."""
    assert node.outline is not None
    cx, cy = node.location
    inner = tuple(
        (round(cx + (x - cx) * PORT_PIECE_SHARE, 7), round(cy + (y - cy) * PORT_PIECE_SHARE, 7))
        for x, y in node.outline[:-1]
    )
    corners = tuple(builder.node(corner) for corner in inner)
    way = builder.way((*corners, corners[0]), dict(PORT_PIECE_TAGS))
    builder.elements.append(OsmElement(f"{node.node_id}:cargo", "area", way=way, corners=corners))


def _link(builder: _Builder, link: ObservedLink) -> None:
    points = link.towers if link.towers else link.route
    first = _end(builder, link.from_id, points[0])
    last = _end(builder, link.to_id, points[-1])
    tower_tags = {"power": "tower"} if link.towers else None
    inner = tuple(builder.node(point, tower_tags) for point in points[1:-1])
    refs = (first, *inner, last)
    way = builder.way(refs, link_tags(link))
    builder.elements.append(
        OsmElement(link.link_id, "line", way=way, towers=inner if link.towers else ())
    )


def _end(builder: _Builder, facility_id: str, location: LonLat) -> int:
    """Return the node a link ends on: the facility's own, or a new one if it is not mapped."""
    if facility_id in builder.endpoints:
        return builder.endpoints[facility_id]
    return builder.node(location)
