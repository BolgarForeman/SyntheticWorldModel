"""Emission (Work Order 8): the OpenStreetMap extract and its views, the other sources, the
names, the recorded headers, the cross-source correspondence and the separation of truth.
"""

import ast
import csv
import functools
import io
import json
import re
import zipfile
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import yaml

from swm import rng
from swm.cli import _built, _observed
from swm.coordinates import from_lonlat
from swm.emit.headers import BEDS, HOSPITAL_LISTS, INSTITUTION_REGISTER, OURAIRPORTS, WRI_GPPD
from swm.emit.osm_model import FIRST_ID, OSM_SOURCES
from swm.emit.osm_tags import LINK_TAGS, PORT_PIECE_SHARE, tag_table
from swm.emit.sources import EmittedSources, emit_sources
from swm.manifest.truth import TruthInputs, truth_manifest
from swm.recipe.io import parse_recipe
from swm.recipe.resolve import resolve
from swm.recipe.schema import SOURCE_SCOPES, Layer, NodeClass, Source
from swm.rng import stream_record
from swm.rules.registry import load_registry
from swm.stages.emission import AREA_CLASSES, _unnamed, build_observed, side, town_name

TESTS = Path(__file__).resolve().parents[1]
SRC = TESTS.parent / "src" / "swm"
PILOT = TESTS / "fixtures" / "pilot_hand_check.yaml"
C = NodeClass
FIXTURES = TESTS / "fixtures"
METRES_PER_DEGREE = 111_320.0
"""A degree of latitude, about; a degree of longitude here is shorter, so this bounds both."""


def rounding_deg(decimals: int) -> float:
    """Half a unit in the last decimal place: a source's own rounding (section 4.1a)."""
    return 0.5 * 10.0**-decimals


OSM_ROUNDING_M = rounding_deg(7) * METRES_PER_DEGREE
"""OpenStreetMap's 7-decimal rounding in metres, about 6 mm."""


@functools.cache
def world(recipe_text: str) -> Any:
    resolution = resolve(parse_recipe(recipe_text))
    built = _built(resolution)
    observed = _observed(resolution, built)
    return SimpleNamespace(resolution=resolution, built=built, observed=observed,
                           sources=emit_sources(observed))  # fmt: skip


def pilot() -> Any:
    return world(PILOT.read_text(encoding="utf-8"))


@functools.cache
def rich() -> Any:
    """The 10-node-per-layer world of the couplings tests, emitted (no storm needed)."""
    from couplings_helpers import rich_world

    recipe, terrain, layers = rich_world()
    observed = build_observed(recipe.layers, terrain, layers, load_registry(), recipe.root_seed)
    return SimpleNamespace(observed=observed, sources=emit_sources(observed))


def nodes_only_pilot() -> Any:
    recipe = yaml.safe_load(PILOT.read_text(encoding="utf-8"))
    for layer in ("power", "telecom", "water"):
        recipe["layers"][layer]["nodes_only"] = True
    return world(yaml.safe_dump(recipe, sort_keys=False))


@functools.cache
def manifest() -> dict[str, Any]:
    p = pilot()
    recipe, b = p.resolution.recipe, p.built
    streams = stream_record(recipe.root_seed, recipe.terrain.terrain_seed)
    return truth_manifest(TruthInputs(
        recipe, b.rules, b.requirements.layers, b.requirements, b.couplings, b.strength,
        b.buffers, b.crews, b.repair, p.observed, p.sources, streams,
    ))  # fmt: skip


def text(sources: EmittedSources, path: str) -> str:
    return sources.files[path].decode("utf-8-sig")


def rows(sources: EmittedSources, path: str) -> list[list[str]]:
    return list(csv.reader(io.StringIO(text(sources, path), newline="")))


# --- OpenStreetMap (A1-A3) ------------------------------------------------------------------


def test_every_feature_is_in_its_sources_scope() -> None:
    p = pilot()
    by_id = {n.node_id: n for n in p.observed.nodes}
    for element in p.sources.osm.elements:
        if element.kind in ("node", "area") and ":" not in element.element_id:
            node = by_id[element.element_id]
            assert node.node_class in SOURCE_SCOPES[OSM_SOURCES[node.layer]].classes


def test_every_in_scope_element_appears_in_the_extract() -> None:
    p = pilot()
    elements = {e.element_id for e in p.sources.osm.elements}
    for node in p.observed.nodes:
        source = OSM_SOURCES[node.layer]
        if source in p.observed.sources_of(node.layer):
            assert (node.node_class in SOURCE_SCOPES[source].classes) == (node.node_id in elements)
    assert {link.link_id for link in p.observed.links} <= elements


def test_nodes_only_layers_have_no_ways() -> None:
    p = nodes_only_pilot()
    lines = [e for e in p.sources.osm.elements if e.kind == "line"]
    assert lines
    for element in lines:
        assert not element.element_id.startswith(("SWM-POW", "SWM-TEL", "SWM-WAT"))
    tags = {k for way in p.sources.osm.ways for k, _ in way.tags}
    assert "power" not in {k for way in p.sources.osm.ways for k, v in way.tags if v == "line"}
    assert "communication" not in tags


def test_outlines_are_closed_and_centred_on_the_true_location() -> None:
    p = pilot()
    nodes = {n.osm_id: n for n in p.sources.osm.nodes}
    ways = {w.osm_id: w for w in p.sources.osm.ways}
    by_id = {n.node_id: n for n in p.observed.nodes}
    areas = [e for e in p.sources.osm.elements if e.kind == "area"]
    exact_m = {n.node_id: (n.x_m, n.y_m) for n in p.built.requirements.layers.nodes}
    assert {by_id[e.element_id].node_class for e in areas if e.element_id in by_id} <= AREA_CLASSES
    for element in areas:
        refs = ways[element.way].refs
        assert refs[0] == refs[-1]
        assert len(refs) == 5
        node_id, _, piece = element.element_id.partition(":")
        true = by_id[node_id].location
        if piece:
            # The port's cargo piece is its harbour outline scaled by half about the true point,
            # in degrees: its centre lies halfway from the true point to the outline's.
            harbour = ways[next(e.way for e in areas if e.element_id == node_id)].refs[:-1]
            for axis in (0, 1):
                outer = sum(nodes[r].location[axis] for r in harbour) / 4
                inner = sum(nodes[r].location[axis] for r in refs[:-1]) / 4
                halfway = true[axis] + (outer - true[axis]) * PORT_PIECE_SHARE
                assert abs(inner - halfway) <= rounding_deg(7)
            continue
        # A footprint is centred in metres (EPSG:32710): its corners, each rounded to 7
        # decimals, average to the true point within that rounding.
        corners = [from_lonlat(*nodes[r].location) for r in refs[:-1]]
        x_m, y_m = exact_m[node_id]
        assert abs(sum(c[0] for c in corners) / 4 - x_m) <= OSM_ROUNDING_M
        assert abs(sum(c[1] for c in corners) / 4 - y_m) <= OSM_ROUNDING_M


def test_each_line_passes_through_its_towers_in_order() -> None:
    p = pilot()
    nodes = {n.osm_id: n for n in p.sources.osm.nodes}
    ways = {w.osm_id: w for w in p.sources.osm.ways}
    links = {link.link_id: link for link in p.observed.links}
    towered = [e for e in p.sources.osm.elements if e.towers]
    assert towered
    for element in towered:
        assert ways[element.way].refs[1:-1] == element.towers
        assert [nodes[t].location for t in element.towers] == list(
            links[element.element_id].towers[1:-1]
        )
        assert all(dict(nodes[t].tags) == {"power": "tower"} for t in element.towers)


def test_osm_ids_are_reserved_unique_and_sorted() -> None:
    osm = pilot().sources.osm
    for objects in (osm.nodes, osm.ways):
        ids = [o.osm_id for o in objects]
        assert ids == sorted(set(ids))
        assert ids[0] >= FIRST_ID == 900_000_000_000
        # 12 digits: Geofabrik's C(12) osm_id field holds every id.
        assert ids[-1] < 10**12
    facilities = [e for e in osm.elements if e.kind != "town"]
    keys = [e.element_id for e in facilities]
    assert keys == sorted(keys)


def test_the_extract_carries_fixed_metadata() -> None:
    body = text(pilot().sources, "sources/osm/island.osm")
    assert set(re.findall(r'timestamp="([^"]+)"', body)) == {"2026-01-01T00:00:00Z"}
    assert set(re.findall(r'version="([^"]+)"', body)) == {"0.6", "1"}
    assert set(re.findall(r'changeset="([^"]+)"', body)) == {"1"}
    assert set(re.findall(r'user="([^"]+)"', body)) == {"swm"}


def test_the_pbf_blobs_are_stored_raw() -> None:
    body = pilot().sources.files["sources/osm/island.osm.pbf"]
    assert b"OSMHeader" in body
    assert b"OSMData" in body
    assert b"DenseNodes" in body
    assert b"zlib_data" not in body


def test_ports_are_harbour_areas_with_a_port_piece_inside() -> None:
    p = pilot()
    ways = {w.osm_id: dict(w.tags) for w in p.sources.osm.ways}
    elements = {e.element_id: e for e in p.sources.osm.elements}
    ports = [n for n in p.observed.nodes if n.node_class == C.SEAPORT]
    assert ports
    for port in ports:
        assert ways[elements[port.node_id].way]["landuse"] == "harbour"
        assert ways[elements[f"{port.node_id}:cargo"].way]["industrial"] == "port"


# --- The two views: Geofabrik and Overpass (answer 2) ---------------------------------------


def test_the_geofabrik_set_has_all_eighteen_layers_with_a_fixed_date() -> None:
    files = pilot().sources.files
    dbfs = sorted(p for p in files if p.endswith(".dbf"))
    assert len(dbfs) == 18
    for path in dbfs:
        assert files[path][1:4] == bytes((126, 1, 1))
        stem = path[: -len(".dbf")]
        assert {f"{stem}{s}" for s in (".shp", ".shx", ".prj", ".cpg")} <= set(files)


def test_every_shapefile_and_overpass_record_is_an_extract_object() -> None:
    p = pilot()
    nodes = {n.osm_id for n in p.sources.osm.nodes}
    ways = {w.osm_id for w in p.sources.osm.ways}
    for record in p.sources.geofabrik:
        assert record.osm_id in (nodes if record.osm_type == "node" else ways)
    for hit in p.sources.overpass:
        assert hit.osm_id in (nodes if hit.osm_type == "node" else ways)


def test_the_overpass_responses_parse_and_name_their_objects() -> None:
    files = pilot().sources.files
    responses = [p for p in files if p.endswith((".geojson", ".json"))]
    assert len(responses) == 4
    for path in responses:
        body = json.loads(files[path])
        assert {"features", "elements"} & set(body)
        assert not files[path].endswith(b"\n")
        assert (path[: path.rindex(".")] + ".overpassql") in files


# --- Identifiers (A1, B2) -------------------------------------------------------------------


def test_no_icao_or_iata_and_every_country_field_is_reserved() -> None:
    sources = pilot().sources
    airports = rows(sources, "sources/ourairports/airports.csv")
    header = airports[0]
    for row in airports[1:]:
        record = dict(zip(header, row, strict=True))
        assert record["icao_code"] == record["iata_code"] == record["gps_code"] == ""
        assert record["iso_country"] == "XS"
        assert record["iso_region"].startswith("XS-")
        assert re.fullmatch(r"XS-\d{4}", record["ident"])
    plants = rows(sources, "sources/wri_gppd/global_power_plant_database.csv")
    for row in plants[1:]:
        record = dict(zip(plants[0], row, strict=True))
        assert record["country"] == "XSW"
        assert re.fullmatch(r"XSW\d{7}", record["gppd_idnr"])
    for code in sources.register:
        assert re.fullmatch(r"XS\d{8}", code.code)


# --- Names (A4) -----------------------------------------------------------------------------

SCREENED = frozenset((
    "the", "and", "for", "are", "but", "not", "you", "all", "any", "can", "her", "was", "one",
    "our", "out", "day", "get", "has", "him", "his", "how", "man", "new", "now", "old", "see",
    "two", "way", "who", "boy", "did", "its", "let", "put", "say", "she", "too", "use", "bay",
    "vale", "cove", "head", "point", "london", "paris", "rome", "berlin", "madrid", "tokyo",
    "delhi", "cairo", "lima", "quito", "oslo", "bern", "dublin", "vienna", "sydney", "perth",
    "darwin", "hobart", "auckland", "nelson", "wellington", "taipei", "manila", "jakarta",
    "lagos", "accra", "dakar", "nairobi", "denver", "boston", "dallas", "austin", "chicago",
    "sale", "dale", "brook", "mere", "hull", "bath", "york", "chester", "lincoln", "durham",
    "kent", "devon", "cornwall", "wales", "ireland", "china", "india", "japan", "peru",
    "chile", "malta", "cuba", "iran", "iraq", "oman", "yemen",
))  # fmt: skip
"""Common English words and well-known world place names a generated name must not be."""


def test_names_are_deterministic_and_screened() -> None:
    rules = load_registry()
    syllables = rules.value("emission.names.syllables")
    share = rules.number("emission.names.place_word_share")
    names = []
    for town in range(200):
        stream = rng.element_stream(0, "emission/names", f"town-{town}")
        names.append(town_name(syllables, share, stream, set()))
        again = rng.element_stream(0, "emission/names", f"town-{town}")
        assert town_name(syllables, share, again, set()) == names[-1]
    for name in names:
        assert name.split()[0].lower() not in SCREENED, name


def test_the_pilot_towns_are_unique_and_every_name_is_english() -> None:
    p = pilot()
    towns = [t.name for t in p.observed.towns]
    assert len(set(towns)) == len(towns)
    names = [v for n in p.sources.osm.nodes for k, v in n.tags if k == "name"]
    names += [v for w in p.sources.osm.ways for k, v in w.tags if k == "name"]
    assert names
    assert all(name.isascii() for name in names)


def test_the_unnamed_share_is_a_fifth_of_ten_minor_nodes_within_rounding() -> None:
    nodes = [SimpleNamespace(node_id=f"SWM-TEL-{i:04d}", layer=Layer.TELECOM, node_class=C.MAST)
             for i in range(1, 11)]  # fmt: skip
    unnamed = _unnamed(nodes, [Layer.TELECOM], load_registry(), 0)  # type: ignore[arg-type]
    assert len(unnamed) == 2
    assert _unnamed(nodes, [Layer.TELECOM], load_registry(), 0) == unnamed  # type: ignore[arg-type]


def test_only_the_unnamed_classes_go_unnamed_in_the_pilot() -> None:
    for node in pilot().observed.nodes:
        if not node.named:
            assert node.node_class.value in load_registry().value("emission.names.unnamed_classes")


# --- Headers (B1, answer 1) -----------------------------------------------------------------


def test_every_csv_header_matches_the_recorded_one() -> None:
    sources = pilot().sources
    expected = {
        "sources/wri_gppd/global_power_plant_database.csv": WRI_GPPD,
        "sources/ourairports/airports.csv": OURAIRPORTS,
        "sources/facility_register/A21030000I-D02001-018.csv": BEDS,
        "sources/facility_register/A21030000I-D21001-003.csv": HOSPITAL_LISTS,
        "sources/facility_register/A21030000I-D21002-005.csv": HOSPITAL_LISTS,
        "sources/facility_register/A21030000I-D21003-003.csv": HOSPITAL_LISTS,
    }
    for path, header in expected.items():
        assert tuple(rows(sources, path)[0]) == header.columns, path


def test_the_register_spreadsheet_header_matches_the_recorded_one() -> None:
    body = pilot().sources.files["sources/facility_register/medical_institution_register.ods"]
    with zipfile.ZipFile(io.BytesIO(body)) as archive:
        assert archive.namelist()[0] == "mimetype"
        content = archive.read("content.xml").decode("utf-8")
    first_row = content.split("</table:table-row>")[0]
    assert tuple(re.findall(r"<text:p>([^<]*)</text:p>", first_row)) == (
        INSTITUTION_REGISTER.columns
    )


def test_the_csv_idioms_follow_the_real_files() -> None:
    files = pilot().sources.files
    wri = files["sources/wri_gppd/global_power_plant_database.csv"]
    assert not wri.startswith(b"\xef\xbb\xbf")
    assert b"\r\n" in wri
    airports = files["sources/ourairports/airports.csv"]
    assert airports.startswith(b'"id","ident"')
    assert b"\r" not in airports
    beds = files["sources/facility_register/A21030000I-D02001-018.csv"]
    assert beds.startswith(b"\xef\xbb\xbf")
    assert b"\r\n" in beds
    lists = files["sources/facility_register/A21030000I-D21001-003.csv"]
    assert lists.startswith(b"\xef\xbb\xbf")
    assert b"\r" not in lists


def test_the_register_files_join_on_the_institution_code() -> None:
    sources = pilot().sources
    hospitals = [n for n in pilot().observed.nodes if n.node_class in (C.TERTIARY, C.REGIONAL)]
    assert hospitals
    by_node = {r.node_id: r for r in sources.register}
    folder = "sources/facility_register/"
    beds = {row[0] for row in rows(sources, folder + "A21030000I-D02001-018.csv")[1:]}
    for node in hospitals:
        record = by_node[node.node_id]
        assert "medical_institution_register.ods" in record.files
        assert record.code in beds
        (listed,) = [f for f in record.files if "D21" in f]
        assert record.code in {row[0] for row in rows(sources, folder + listed)[1:]}


# --- Correspondence (C1) --------------------------------------------------------------------


def test_every_record_maps_to_exactly_one_true_element() -> None:
    p = pilot()
    owners: dict[tuple[str, int], str] = {}
    for element in p.sources.osm.elements:
        objects = [("node", n) for n in (element.node, element.anchor, *element.corners,
                                         *element.towers) if n is not None]  # fmt: skip
        if element.way is not None:
            objects.append(("way", element.way))
        for key in objects:
            assert key not in owners, key
            owners[key] = element.element_id
    for record in p.sources.geofabrik:
        assert (record.osm_type, record.osm_id) in owners
    for records in (p.sources.wri, p.sources.airports, p.sources.register):
        ids = [r.node_id for r in records]
        assert len(ids) == len(set(ids))


def test_every_in_scope_element_is_in_the_manifests_correspondence() -> None:
    p = pilot()
    listed = {entry["element"]: entry for entry in manifest()["correspondence"]}
    for node in p.observed.nodes:
        for source in p.observed.sources_of(node.layer):
            if source in OSM_SOURCES.values() or node.node_class not in (
                SOURCE_SCOPES[source].classes
            ):
                continue
            assert source.value in listed[node.node_id], (node.node_id, source)
    plants = [n for n in p.observed.nodes if n.node_class == C.GENERATION]
    assert all(Source.WRI_GPPD.value in listed[n.node_id] for n in plants)


def test_the_manifest_declares_a_zero_error_emission() -> None:
    planted = manifest()["planted_errors"]
    assert planted == {"status": "zero-error emission (Phase 1)", "errors": []}
    assert manifest()["theta"]["registry_sha256"] == pilot().built.rules.sha256


# --- Separation (E2, C3) --------------------------------------------------------------------


def _imports(path: Path) -> set[str]:
    names: set[str] = set()
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            names |= {alias.name for alias in node.names}
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module)
    return names


def test_no_writer_reaches_unobserved_fields_the_dynamics_or_error_induction() -> None:
    for path in (SRC / "emit").rglob("*.py"):
        reached = {n for n in _imports(path) if n.startswith("swm.")}
        assert reached <= {"swm.recipe.schema"} | {
            n for n in reached if n.startswith("swm.emit")
        }, path


def test_the_emission_stage_never_reaches_the_dynamics_or_error_induction() -> None:
    for path in (SRC / "stages" / "emission.py", SRC / "manifest" / "truth.py"):
        assert not {n for n in _imports(path) if n.startswith(("swm.dynamics", "swm.errors"))}


def test_no_source_file_carries_a_value_only_the_manifest_holds() -> None:
    p = pilot()
    secret = {n.node_id for n in p.built.requirements.layers.nodes}
    secret |= {link.link_id for link in p.built.requirements.layers.links}
    secret |= {edge.edge_id for edge in p.built.couplings.edges}
    secret |= {crew.crew_id for crew in p.built.crews.crews}
    unobserved_words = {
        str(v) for n in p.built.requirements.layers.nodes for _, v in n.subtype
        if isinstance(v, str) and len(v) > 3
    }  # fmt: skip
    # A word of the tag vocabulary (such as "pipeline") names an observed class, not a value.
    vocabulary = {w for row in tag_table() for w in re.findall(r"[A-Za-z_]+", row["tags"])}
    vocabulary |= {w for tags in LINK_TAGS.values() for kv in tags for w in kv}
    unobserved_words -= vocabulary
    assert secret
    assert unobserved_words
    for path, body in p.sources.files.items():
        for token in secret:
            assert token.encode("utf-8") not in body, (path, token)
        if path.endswith((".csv", ".osm", ".geojson", ".json", ".overpassql")):
            words = set(re.findall(r"[A-Za-z_]+", body.decode("utf-8-sig")))
            assert not unobserved_words & words, (path, unobserved_words & words)


# --- Coordinates at each source's precision (PR 17 answers, item 2) -------------------------


def _decimals(value: str) -> int:
    return len(value.split(".")[1]) if "." in value else 0


def test_wri_writes_four_decimals_within_its_rounding() -> None:
    p = pilot()
    by_id = {n.node_id: n for n in p.observed.nodes}
    plants = rows(p.sources, "sources/wri_gppd/global_power_plant_database.csv")
    assert p.sources.wri
    for record, row in zip(p.sources.wri, plants[1:], strict=True):
        values = dict(zip(plants[0], row, strict=True))
        true = by_id[record.node_id].location
        assert _decimals(values["latitude"]) == 4
        assert _decimals(values["longitude"]) == 4
        assert abs(float(values["latitude"]) - true[1]) <= rounding_deg(4)
        assert abs(float(values["longitude"]) - true[0]) <= rounding_deg(4)


def test_ourairports_writes_six_decimals_within_its_rounding() -> None:
    p = pilot()
    by_id = {n.node_id: n for n in p.observed.nodes}
    airports = rows(p.sources, "sources/ourairports/airports.csv")
    assert p.sources.airports
    for record, row in zip(p.sources.airports, airports[1:], strict=True):
        values = dict(zip(airports[0], row, strict=True))
        true = by_id[record.node_id].location
        assert _decimals(values["latitude_deg"]) <= 6
        assert abs(float(values["latitude_deg"]) - true[1]) <= rounding_deg(6)
        assert abs(float(values["longitude_deg"]) - true[0]) <= rounding_deg(6)


def test_the_register_writes_six_decimals_within_its_rounding() -> None:
    p = pilot()
    by_id = {n.node_id: n for n in p.observed.nodes}
    codes = {r.code: r.node_id for r in p.sources.register}
    lists = rows(p.sources, "sources/facility_register/A21030000I-D21001-003.csv")
    assert lists[1:]
    for row in lists[1:]:
        values = dict(zip(lists[0], row, strict=True))
        latitude, longitude = values["地址"].split(",")
        true = by_id[codes[values["醫事機構代碼"]]].location
        assert _decimals(latitude) == 6
        assert _decimals(longitude) == 6
        assert abs(float(latitude) - true[1]) <= rounding_deg(6)
        assert abs(float(longitude) - true[0]) <= rounding_deg(6)


def test_osm_point_nodes_carry_the_true_location_at_seven_decimals() -> None:
    p = pilot()
    nodes = {n.osm_id: n for n in p.sources.osm.nodes}
    by_id = {n.node_id: n for n in p.observed.nodes}
    points = [e for e in p.sources.osm.elements if e.kind == "node"]
    assert points
    for element in points:
        assert element.node is not None
        assert nodes[element.node].location == by_id[element.element_id].location


def test_the_measured_precision_is_recorded_beside_each_header() -> None:
    assert WRI_GPPD.coordinate_decimals == 4
    assert OURAIRPORTS.coordinate_decimals == 6
    for header in (WRI_GPPD, OURAIRPORTS):
        assert header.decimals_measured
        assert set(header.coordinate_columns) <= set(header.columns)


# --- Columns the world does not hold (item 3) ------------------------------------------------


def test_wri_year_and_owner_are_empty_and_declared() -> None:
    plants = rows(pilot().sources, "sources/wri_gppd/global_power_plant_database.csv")
    for row in plants[1:]:
        values = dict(zip(plants[0], row, strict=True))
        assert values["commissioning_year"] == ""
        assert values["owner"] == ""
    assert any("commissioning_year and owner" in d for d in manifest()["declared_departures"])


# --- Names are unique within their town unless shared (item 4; answers 2, item 2) -----------

NAMED_COLUMNS = {
    "sources/wri_gppd/global_power_plant_database.csv": "name",
    "sources/ourairports/airports.csv": "name",
    "sources/facility_register/A21030000I-D21001-003.csv": "醫事機構名稱",
    "sources/facility_register/A21030000I-D21002-005.csv": "醫事機構名稱",
    "sources/facility_register/A21030000I-D21003-003.csv": "醫事機構名稱",
}
"""Delimited files whose every row is outside the shared-name list, and their name column."""
REGISTER_ODS = "sources/facility_register/medical_institution_register.ods"


def _shared() -> set[NodeClass]:
    return {NodeClass(c) for c in load_registry().value("emission.names.shared_name_classes")}


def _register_names(emitted: Any) -> list[str]:
    with zipfile.ZipFile(io.BytesIO(emitted.sources.files[REGISTER_ODS])) as archive:
        content = archive.read("content.xml").decode("utf-8")
    cell = r"<table:table-cell[^>]*?(?:/>|><text:p>([^<]*)</text:p></table:table-cell>)"
    table = [re.findall(cell, row) for row in content.split("</table:table-row>")[:-1]]
    column = table[0].index("機構名稱")
    return [row[column] for row in table[1:]]


def _assert_unshared_names_unique(emitted: Any) -> None:
    shared = _shared()
    elements = {e.element_id: e for e in emitted.sources.osm.elements}
    # Node and way ids are separate spaces in OpenStreetMap, and here they overlap.
    node_tags = {o.osm_id: dict(o.tags) for o in emitted.sources.osm.nodes}
    way_tags = {o.osm_id: dict(o.tags) for o in emitted.sources.osm.ways}
    seen: set[tuple[str, str]] = set()
    checked = 0
    for node in emitted.observed.nodes:
        element = elements.get(node.node_id)
        if node.node_class in shared or element is None:
            continue
        tags = way_tags[element.way] if element.way is not None else node_tags[element.node]
        key = (node.town, tags["name"])
        assert key not in seen, key
        seen.add(key)
        checked += 1
    assert checked
    for path, column in NAMED_COLUMNS.items():
        if path in emitted.sources.files:
            table = rows(emitted.sources, path)
            names = [dict(zip(table[0], row, strict=True))[column] for row in table[1:]]
            assert len(names) == len(set(names)), path
    names = _register_names(emitted)
    assert names
    assert len(names) == len(set(names)), REGISTER_ODS


def test_no_two_unshared_elements_share_a_name_within_a_town_in_any_source() -> None:
    _assert_unshared_names_unique(pilot())
    _assert_unshared_names_unique(rich())


def test_the_rich_world_tells_its_repeats_apart_by_side() -> None:
    repeats = [n for n in rich().observed.nodes if n.direction is not None]
    assert {n.node_class for n in repeats} >= {C.CLINIC, C.GENERATION}
    for node in repeats:
        assert node.node_class not in _shared()
        assert node.direction in {"North", "South", "East", "West"}
        assert node.name("Clinic").startswith(f"{node.town} {node.direction} ")


def test_shared_name_classes_may_repeat_and_only_three_go_unnamed() -> None:
    rules = load_registry()
    shared = set(rules.value("emission.names.shared_name_classes"))
    unnamed = set(rules.value("emission.names.unnamed_classes"))
    assert unnamed == {"mast", "pumping", "distribution_substation"}
    assert unnamed < shared
    assert all(n.direction is None for n in rich().observed.nodes if n.node_class.value in shared)
    assert any(not n.named for n in rich().observed.nodes)
    for node in rich().observed.nodes:
        if not node.named:
            assert node.node_class.value in unnamed


def test_the_side_is_found_by_comparisons_alone() -> None:
    assert side(10.0, 3.0) == "east"
    assert side(-10.0, 3.0) == "west"
    assert side(3.0, 10.0) == "north"
    assert side(3.0, -10.0) == "south"
    assert side(5.0, 5.0) == "east"
    assert side(-5.0, -5.0) == "west"


def test_a_name_reads_town_direction_word_number() -> None:
    node = next(n for n in pilot().observed.nodes if n.node_class == C.TRANSMISSION_SUBSTATION)
    numbered = replace(node, direction="North", number=2)
    assert numbered.name("Substation") == f"{node.town} North Substation 2"
    assert node.name("Substation") == f"{node.town} Substation"


# --- Every world writes the same files (item 5) ---------------------------------------------


EXPECTED_VALUES = "hand_trace_"
"""Fixtures of expected values, not recipes (the hand trace, WO-09 F1)."""


def test_every_fixture_world_writes_the_same_source_files() -> None:
    expected = set(pilot().sources.files)
    assert "sources/facility_register/A21030000I-D21003-003.csv" in expected
    for path in sorted(FIXTURES.rglob("*.yaml")):
        if path.name.startswith(EXPECTED_VALUES):
            continue
        assert set(world(path.read_text(encoding="utf-8")).sources.files) == expected, path


def test_an_empty_hospital_level_is_its_header_alone() -> None:
    body = pilot().sources.files["sources/facility_register/A21030000I-D21003-003.csv"]
    assert body.decode("utf-8-sig") == ",".join(HOSPITAL_LISTS.columns) + "\n"


# --- Overpass queries rebuilt from landed tags (verification items) -------------------------


def test_the_inferred_overpass_queries_say_so() -> None:
    files = pilot().sources.files
    for name in ("TWN_Hospital", "TWN_Industrial", "TWN_Telecom_OSM_Overpass"):
        first = files[f"sources/osm/overpass/{name}.overpassql"].decode("utf-8").splitlines()[0]
        assert first.startswith("// inferred from landed tags, query text not saved:")
    ports = files["sources/osm/overpass/query_families_ports.overpassql"].decode("utf-8")
    assert "inferred" not in ports


def test_the_manifest_matches_each_view_by_type_and_id() -> None:
    # Node and way ids overlap, so a match on the id alone would give an element another's row.
    p = pilot()
    node_tags = {n.osm_id: dict(n.tags) for n in p.sources.osm.nodes}
    way_tags = {w.osm_id: dict(w.tags) for w in p.sources.osm.ways}
    elements = {e.element_id: e for e in p.sources.osm.elements}
    fclass = {"hospital": "amenity", "clinic": "amenity", "fuel": "amenity",
              "airport": "aeroway", "reservoir": "water", "water_works": "man_made",
              "industrial": "landuse", "primary": "highway", "town": "place"}  # fmt: skip
    checked = 0
    for entry in manifest()["correspondence"]:
        view = entry.get("openstreetmap", {}).get("geofabrik")
        if view is None:
            continue
        element = elements[entry["element"]]
        tags = way_tags[element.way] if element.way is not None else node_tags[element.node]
        assert fclass[view["fclass"]] in tags, (entry["element"], view, tags)
        checked += 1
    assert checked
