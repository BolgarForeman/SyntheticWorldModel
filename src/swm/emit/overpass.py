"""Overpass-style views of the island: one file per query the pipeline runs (answer 2).

The pipeline lands three Overpass pulls as overpass-turbo GeoJSON (hospitals, industrial,
telecom) and its ports check saves raw Overpass JSON. The three landed pulls kept no query
text, so their queries here are inferred from the tags the real files hold (stated in each
query's comment); the ports query is the pipeline's own (``osm_ports_check.py``, the six port
families, ``out geom``). Each file holds the features whose tags the query's filter matches.

Layouts recorded from the real files:
- overpass-turbo GeoJSON (``OSM/TWN/overpass_2025-11/TWN_Hospital.geojson`` and its siblings):
  ``type, generator, copyright, timestamp, features``; each feature ``type, properties (@id
  then tags, flat strings), geometry, id``; 2-space indent, LF, raw UTF-8, no final newline;
  ``out center`` features are points with ``"@geometry": "center"`` on ways;
- raw Overpass JSON (the ports check's responses): ``version, generator, osm3s, elements``,
  ways with ``bounds``, ``nodes`` and ``geometry`` under ``out geom``.

Spec: structure v0.10 §4.6 (corrected); Work Order 8 answers, 2.
"""

import json
from collections.abc import Callable, Mapping
from dataclasses import dataclass

from swm.emit.osm_model import TIMESTAMP, OsmData

COPYRIGHT = (
    "The data included in this document is from www.openstreetmap.org. The data is made "
    "available under ODbL."
)
OVERPASS_GENERATOR = "Overpass API 0.7.62.11 87bfad18"
"""The server the pipeline's saved responses name."""

Tags = Mapping[str, str]


@dataclass(frozen=True)
class Query:
    """One Overpass query: its file stem, text, tag filter, output form and file layout."""

    name: str
    statements: tuple[str, ...]
    matches: Callable[[Tags], bool]
    out: str
    """geom or center."""
    layout: str
    """turbo (overpass-turbo GeoJSON) or raw (Overpass API JSON)."""
    note: str


def _hospital(tags: Tags) -> bool:
    return tags.get("amenity") == "hospital" or tags.get("healthcare") == "hospital"


def _industrial(tags: Tags) -> bool:
    return tags.get("landuse") == "industrial"


def _telecom(tags: Tags) -> bool:
    return (
        tags.get("man_made") in ("mast", "tower", "communications_tower")
        or tags.get("office") == "telecommunication"
        or "telecom" in tags
        or tags.get("tower:type") == "communication"
    )


PORT_FAMILIES = (
    ("landuse", "port"), ("industrial", "port"), ("landuse", "harbour"),
    ("harbour", None), ("port", None), ("seamark:type", "harbour"),
)  # fmt: skip
"""The ports check's six port families (``osm_ports_check.py``, FAMILY_STATEMENTS "ports")."""


def _ports(tags: Tags) -> bool:
    return any(
        (key in tags) if value is None else tags.get(key) == value for key, value in PORT_FAMILIES
    )


QUERIES = (
    Query("TWN_Hospital", ('nwr["amenity"="hospital"]', 'nwr["healthcare"="hospital"]'),
          _hospital, "geom", "turbo",
          "Inferred from the landed file: every feature carries amenity=hospital or "
          "healthcare=hospital; no query text was saved."),
    Query("TWN_Industrial", ('nwr["landuse"="industrial"]',), _industrial, "geom", "turbo",
          "Inferred from the landed file: its features carry landuse=industrial; no query "
          "text was saved."),
    Query("TWN_Telecom_OSM_Overpass", (
        'nwr["man_made"~"^(mast|tower|communications_tower)$"]',
        'nwr["office"="telecommunication"]', 'nwr["telecom"]',
        'nwr["tower:type"="communication"]'), _telecom, "center", "turbo",
          "Inferred from the landed file: masts and towers, telecommunication offices, any "
          "telecom=* and communication towers, written out center; no query text was saved."),
    Query("query_families_ports", tuple(
        f'nwr["{k}"]' if v is None else f'nwr["{k}"="{v}"]' for k, v in PORT_FAMILIES),
          _ports, "geom", "raw",
          "The pipeline's ports check (osm_ports_check.py, the six port families)."),
)  # fmt: skip


@dataclass(frozen=True)
class OverpassRecord:
    """Which OpenStreetMap object a query's file holds."""

    query: str
    osm_type: str
    osm_id: int


def overpass_files(data: OsmData) -> tuple[dict[str, bytes], tuple[OverpassRecord, ...]]:
    """Return each query's text and response, and which objects each response holds.

    Parameters
    ----------
    data : OsmData
        The island's OpenStreetMap objects.

    Returns
    -------
    files : dict of str to bytes
        ``<name>.overpassql`` and ``<name>.geojson`` (turbo) or ``<name>.json`` (raw).
    records : tuple of OverpassRecord
        Each response's objects, in query then type then id order.

    Spec: Work Order 8 answers, 2.
    """
    files: dict[str, bytes] = {}
    records: list[OverpassRecord] = []
    area = _poly(data)
    for query in QUERIES:
        files[f"{query.name}.overpassql"] = _query_text(query, area)
        nodes = [n for n in data.nodes if n.tags and query.matches(dict(n.tags))]
        ways = [w for w in data.ways if query.matches(dict(w.tags))]
        records += [OverpassRecord(query.name, "node", n.osm_id) for n in nodes]
        records += [OverpassRecord(query.name, "way", w.osm_id) for w in ways]
        if query.layout == "turbo":
            files[f"{query.name}.geojson"] = _turbo(query, nodes, ways, data)
        else:
            files[f"{query.name}.json"] = _raw(nodes, ways, data)
    return files, tuple(records)


def _poly(data: OsmData) -> str:
    west, south, east, north = data.bounds()
    corners = ((south, west), (north, west), (north, east), (south, east))
    return 'poly:"' + " ".join(f"{lat:.7f} {lon:.7f}" for lat, lon in corners) + '"'


def _query_text(query: Query, area: str) -> bytes:
    body = "\n".join(f"  {statement}({area});" for statement in query.statements)
    text = f"// {query.note}\n[out:json][timeout:300];\n(\n{body}\n);\nout {query.out};\n"
    return text.encode("utf-8")


def _locations(data: OsmData) -> dict[int, tuple[float, float]]:
    return {node.osm_id: node.location for node in data.nodes}


def _turbo(query: Query, nodes: list, ways: list, data: OsmData) -> bytes:  # type: ignore[type-arg]
    locations = _locations(data)
    features = []
    for node in nodes:
        features.append(_feature("node", node.osm_id, dict(node.tags), {
            "type": "Point", "coordinates": list(node.location)}))  # fmt: skip
    for way in ways:
        ring = [list(locations[ref]) for ref in way.refs]
        tags = dict(way.tags)
        if query.out == "center":
            tags = {**tags, "@geometry": "center"}
            geometry = {"type": "Point", "coordinates": _centre(ring)}
        elif way.refs[0] == way.refs[-1]:
            geometry = {"type": "Polygon", "coordinates": [ring]}
        else:
            geometry = {"type": "LineString", "coordinates": ring}
        features.append(_feature("way", way.osm_id, tags, geometry))
    document = {
        "type": "FeatureCollection",
        "generator": "overpass-turbo",
        "copyright": COPYRIGHT,
        "timestamp": TIMESTAMP,
        "features": features,
    }
    return json.dumps(document, indent=2, ensure_ascii=False).encode("utf-8")


def _feature(
    kind: str, osm_id: int, tags: dict[str, str], geometry: Mapping[str, object]
) -> dict[str, object]:
    ident = f"{kind}/{osm_id}"
    return {"type": "Feature", "properties": {"@id": ident, **tags}, "geometry": geometry,
            "id": ident}  # fmt: skip


def _centre(ring: list[list[float]]) -> list[float]:
    """Return the centre of a way's bounds, as ``out center`` gives it, at 7 decimals."""
    lons, lats = [p[0] for p in ring], [p[1] for p in ring]
    return [round((min(lons) + max(lons)) / 2, 7), round((min(lats) + max(lats)) / 2, 7)]


def _raw(nodes: list, ways: list, data: OsmData) -> bytes:  # type: ignore[type-arg]
    locations = _locations(data)
    elements: list[dict[str, object]] = []
    for node in nodes:
        elements.append({"type": "node", "id": node.osm_id, "lat": node.location[1],
                         "lon": node.location[0], "tags": dict(node.tags)})  # fmt: skip
    for way in ways:
        points = [locations[ref] for ref in way.refs]
        lats, lons = [p[1] for p in points], [p[0] for p in points]
        elements.append({
            "type": "way", "id": way.osm_id,
            "bounds": {"minlat": min(lats), "minlon": min(lons), "maxlat": max(lats),
                       "maxlon": max(lons)},
            "nodes": list(way.refs),
            "geometry": [{"lat": p[1], "lon": p[0]} for p in points],
            "tags": dict(way.tags),
        })  # fmt: skip
    document = {
        "version": 0.6,
        "generator": OVERPASS_GENERATOR,
        "osm3s": {"timestamp_osm_base": TIMESTAMP, "copyright": COPYRIGHT},
        "elements": elements,
    }
    return json.dumps(document, indent=2, ensure_ascii=False).encode("utf-8")
