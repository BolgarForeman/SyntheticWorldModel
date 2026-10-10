"""Geofabrik-style free shapefiles of the island: the layers the pipeline lands (answer 2).

All 18 layers of Geofabrik's ``<region>-<date>-free`` set are written, with the real set's file
names, field layouts, ``.prj`` and ``.cpg``, empty where no feature qualifies. A feature goes
where Geofabrik's rules put its tags ("OpenStreetMap Data in Layered GIS Format", free
shapefiles), and only the classes the free set carries appear: power, harbours, masts, pumping
stations, storage tanks and blood banks are not in it. Points of a class go in the point layer;
closed ways in its ``_a`` polygon layer.

Schema recorded from the real set on disk: ``OSM/TWN/geofabrik_taiwan-251128-free`` (data as of
2025-11-28T21:20:48Z). The one departure: ``osm_id`` is C(13), not C(12), because the ruled ids
start at 9,000,000,000,000 (E3), one digit wider than the real field.

Spec: structure v0.10 §4.6 (corrected); Work Order 8 answers, 2.
"""

from collections.abc import Mapping
from dataclasses import dataclass

from swm.emit.osm_model import OsmData
from swm.emit.shapefile import POINT, POLYGON, POLYLINE, Field, Shape, shapefile

PREFIX = "gis_osm_"
SUFFIX = "_free_1"
PRJ = (
    'GEOGCS["GCS_WGS_1984",DATUM["D_WGS_1984",SPHEROID["WGS_1984",6378137,298.257223563]],'
    'PRIMEM["Greenwich",0],UNIT["Degree",0.017453292519943295]]\n'
).encode("ascii")
CPG = b"UTF-8\n"

ROAD_CODE = (5113, "primary")
"""Geofabrik's code and fclass for highway=primary (Geofabrik free-layer documentation)."""
ROAD_FLAGS = ("", "B", 0, 0, "F", "F")
"""ref, oneway, maxspeed, layer, bridge, tunnel. CHOICE: no ref, both ways, speed unknown (0),
on the ground, no bridge or tunnel: the world carries none of these."""
PLACE_POPULATION = 0
"""CHOICE: population unknown (0, as Geofabrik writes it when the tag is missing): towns carry
no observed population."""
OSM_ID = Field("osm_id", "C", 13)
"""C(12) in the real set; one wider for the reserved 13-digit ids (declared departure)."""
BASE = (OSM_ID, Field("code", "N", 4), Field("fclass", "C", 28), Field("name", "C", 100))

LAYERS: Mapping[str, tuple[int, tuple[Field, ...]]] = {
    "buildings_a": (POLYGON, (*BASE, Field("type", "C", 20))),
    "landuse_a": (POLYGON, BASE),
    "natural_a": (POLYGON, BASE),
    "natural": (POINT, BASE),
    "places_a": (POLYGON, (*BASE[:3], Field("population", "N", 10), BASE[3])),
    "places": (POINT, (*BASE[:3], Field("population", "N", 10), BASE[3])),
    "pofw_a": (POLYGON, BASE),
    "pofw": (POINT, BASE),
    "pois_a": (POLYGON, BASE),
    "pois": (POINT, BASE),
    "railways": (POLYLINE, (*BASE, Field("layer", "N", 12), Field("bridge", "C", 1),
                            Field("tunnel", "C", 1))),
    "roads": (POLYLINE, (*BASE, Field("ref", "C", 20), Field("oneway", "C", 1),
                         Field("maxspeed", "N", 3), Field("layer", "N", 12),
                         Field("bridge", "C", 1), Field("tunnel", "C", 1))),
    "traffic_a": (POLYGON, BASE),
    "traffic": (POINT, BASE),
    "transport_a": (POLYGON, BASE),
    "transport": (POINT, BASE),
    "water_a": (POLYGON, BASE),
    "waterways": (POLYLINE, (*BASE[:3], Field("width", "N", 5), BASE[3])),
}  # fmt: skip
"""The real set's 18 layers: geometry type and fields, in the real order."""

CLASSES: tuple[tuple[str, tuple[tuple[str, str], ...], int, str], ...] = (
    ("pois", (("amenity", "hospital"),), 2110, "hospital"),
    ("pois", (("amenity", "clinic"),), 2111, "clinic"),
    ("pois", (("man_made", "water_works"),), 2964, "water_works"),
    ("pois", (("man_made", "tower"), ("tower:type", "communication")), 2951, "comms_tower"),
    ("pois", (("man_made", "water_tower"),), 2952, "water_tower"),
    ("transport", (("aeroway", "aerodrome"),), 5651, "airport"),
    ("traffic", (("amenity", "fuel"),), 5250, "fuel"),
    ("traffic", (("highway", "motorway_junction"),), 5206, "motorway_junction"),
    ("landuse", (("landuse", "industrial"),), 7204, "industrial"),
    ("water", (("natural", "water"), ("water", "reservoir")), 8201, "reservoir"),
    ("places", (("place", "town"),), 1002, "town"),
)
"""Geofabrik's rule for each class this world's tags can meet: its layer family, the tags it
needs, and its code and fclass (as on disk)."""


@dataclass(frozen=True)
class GeofabrikRecord:
    """Where one OpenStreetMap object landed in the shapefiles."""

    osm_id: int
    layer: str
    fclass: str


def geofabrik_files(data: OsmData) -> tuple[dict[str, bytes], tuple[GeofabrikRecord, ...]]:
    """Return every layer's five files, and where each object landed.

    Parameters
    ----------
    data : OsmData
        The island's OpenStreetMap objects.

    Returns
    -------
    files : dict of str to bytes
        ``gis_osm_<layer>_free_1.<ext>`` for ext in shp, shx, dbf, prj and cpg.
    records : tuple of GeofabrikRecord
        Each object's layer and class, in layer then id order.

    Spec: Work Order 8 answers, 2.
    """
    rows: dict[str, list[tuple[Shape, list[object]]]] = {layer: [] for layer in LAYERS}
    records: list[GeofabrikRecord] = []
    locations = {node.osm_id: node.location for node in data.nodes}
    for node in data.nodes:
        _place(rows, records, node.osm_id, dict(node.tags), Shape(((node.location,),)), False)
    for way in data.ways:
        ring = tuple(locations[ref] for ref in way.refs)
        closed = len(ring) > 3 and way.refs[0] == way.refs[-1]
        # Shapefile outer rings run clockwise.
        shape = Shape((tuple(reversed(ring)),)) if closed else Shape((ring,))
        _place(rows, records, way.osm_id, dict(way.tags), shape, closed)
    files: dict[str, bytes] = {}
    for layer, (shape_type, fields) in LAYERS.items():
        written = shapefile(shape_type, fields, rows[layer])
        stem = f"{PREFIX}{layer}{SUFFIX}"
        for ext in ("shp", "shx", "dbf"):
            files[f"{stem}.{ext}"] = written[ext]
        files[f"{stem}.prj"] = PRJ
        files[f"{stem}.cpg"] = CPG
    ordered = sorted(records, key=lambda r: (r.layer, r.osm_id))
    return files, tuple(ordered)


def _place(
    rows: dict[str, list[tuple[Shape, list[object]]]],
    records: list[GeofabrikRecord],
    osm_id: int,
    tags: Mapping[str, str],
    shape: Shape,
    closed: bool,
) -> None:
    """Put an object in the layer Geofabrik's rules give its tags, if any."""
    if not closed and len(shape.parts[0]) > 1:
        if tags.get("highway") == "primary":
            values: list[object] = [str(osm_id), *ROAD_CODE, tags.get("name", ""), *ROAD_FLAGS]
            rows["roads"].append((shape, values))
            records.append(GeofabrikRecord(osm_id, "roads", "primary"))
        return
    for family, needed, code, fclass in CLASSES:
        if not all(tags.get(k) == v for k, v in needed):
            continue
        layer = _layer(family, closed)
        if layer is None:
            return
        name = tags.get("name", "")
        values = [str(osm_id), code, fclass, name]
        if family == "places":
            values = [str(osm_id), code, fclass, PLACE_POPULATION, name]
        rows[layer].append((shape, values))
        records.append(GeofabrikRecord(osm_id, layer, fclass))
        return


def _layer(family: str, closed: bool) -> str | None:
    """Return the point or polygon layer of a family; landuse and water have polygons only."""
    if family in ("landuse", "water"):
        return f"{family}_a" if closed else None
    return f"{family}_a" if closed else family
