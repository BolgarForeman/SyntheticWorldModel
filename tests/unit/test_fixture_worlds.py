"""Golden worlds: the pilot with telecom hidden, and the pilot with power reporting nodes only.

Hiding or thinning a source changes what is emitted, never what exists. Each fixture is the
pilot with one change; every stage hash, the manifest's true world and all 8 reference runs equal
the pilot's, and only files that carry emitted content differ from the pilot's goldens, each for
a stated reason (Work Order 9, B1 to B3).
"""

import hashlib
import struct
import xml.etree.ElementTree as ElementTree
from collections.abc import Iterator
from pathlib import Path

import pytest
import yaml

from swm.cli import main

TESTS = Path(__file__).resolve().parents[1]
FIXTURES = TESTS / "fixtures"
PILOT = FIXTURES / "pilot_hand_check.yaml"
PILOT_BUILD = TESTS / "golden" / "pilot_build"
PILOT_STAGES = TESTS / "golden" / "pilot_hand_check"
PILOT_RUNS = TESTS / "golden" / "pilot_reference_runs"
WORLDS = ("pilot_hidden_telecom", "pilot_power_nodes_only")
STAGE_COMMANDS = (
    "terrain", "layers", "requirements", "couplings", "buffers", "strength", "repair", "storm",
    "scenarios",
)  # fmt: skip
TRUE_WORLD = ("modeling_rules", "planted_errors", "geometry", "unobserved", "scored_and_context",
              "theta", "seeds")  # fmt: skip
"""The manifest's sections that record what exists; neither change may move them."""

OSM = "sources/osm/"
GEOFABRIK = OSM + "geofabrik_island-260101-free/gis_osm_"
OVERPASS = OSM + "overpass/"
RENUMBERED = "OpenStreetMap ids are numbered in emission order; fewer emitted objects renumber"
EXTENT = "the extract's bounds are the emitted objects' extent, which the change moves"
SHARED_DIFFERENCES = {
    "resolved_recipe.yaml": "the one change, and the Phase 1 note lists the error settings",
    "truth/manifest.yaml": "correspondence (renumbered ids) and the hidden section; the true "
    "world is unchanged",
    OSM + "island.osm": f"the change's objects are gone; {RENUMBERED}; {EXTENT}",
    OSM + "island.osm.pbf": f"the change's objects are gone; {RENUMBERED}; {EXTENT}",
    **{
        f"{GEOFABRIK}{layer}_free_1.dbf": f"{RENUMBERED} (the osm_id field)"
        for layer in ("landuse_a", "places", "pois_a", "roads", "transport_a", "water_a")
    },
    OVERPASS + "TWN_Hospital.overpassql": f"the query's polygon: {EXTENT}",
    OVERPASS + "TWN_Industrial.overpassql": f"the query's polygon: {EXTENT}",
    OVERPASS + "TWN_Industrial.geojson": RENUMBERED,
    OVERPASS + "TWN_Telecom_OSM_Overpass.overpassql": f"the query's polygon: {EXTENT}",
    OVERPASS + "query_families_ports.overpassql": f"the query's polygon: {EXTENT}",
    OVERPASS + "query_families_ports.json": RENUMBERED,
}
DIFFERENCES = {
    "pilot_hidden_telecom": {
        **SHARED_DIFFERENCES,
        OVERPASS + "TWN_Telecom_OSM_Overpass.geojson": "no telecom feature: the result is empty",
    },
    "pilot_power_nodes_only": {
        **SHARED_DIFFERENCES,
        OVERPASS + "TWN_Telecom_OSM_Overpass.geojson": RENUMBERED,
    },
}
"""Every file in which a fixture's golden build differs from the pilot's, and why (B3)."""

TELECOM_TAGS = {("telecom", None), ("communication", None), ("tower:type", "communication"),
                ("man_made", "mast"), ("man_made", "communications_tower"),
                ("office", "telecommunication")}  # fmt: skip
"""The tags the emitter gives telecom nodes and links, and Overpass's telecom query asks for."""
POWER_LINK_TAGS = {("power", "line"), ("power", "minor_line"), ("power", "cable"),
                   ("power", "tower"), ("power", "pole")}  # fmt: skip
POWER_NODE_TAGS = {("power", "plant"), ("power", "substation")}


def golden(world: str) -> Path:
    return TESTS / "golden" / f"{world}_build"


def recorded_hashes(folder: Path) -> dict[str, str]:
    lines = (folder / "SHA256SUMS").read_text(encoding="utf-8").splitlines()
    return {name: digest for digest, name in (line.split("  ") for line in lines)}


def manifest(folder: Path) -> dict[str, object]:
    loaded: dict[str, object] = yaml.safe_load(
        (folder / "truth" / "manifest.yaml").read_text(encoding="utf-8")
    )
    return loaded


GOLDEN_FILES = tuple(
    (world, name) for world in WORLDS for name in sorted(recorded_hashes(golden(world)))
)


@pytest.fixture(scope="module")
def built(tmp_path_factory: pytest.TempPathFactory) -> dict[str, Path]:
    out = {}
    for world in WORLDS:
        out_dir = tmp_path_factory.mktemp(world)
        assert main(["build", str(FIXTURES / f"{world}.yaml"), "-o", str(out_dir)]) == 0
        out[world] = out_dir
    return out


# --- The goldens ----------------------------------------------------------------------------


def test_each_fixture_is_the_pilot_with_one_change() -> None:
    pilot = yaml.safe_load(PILOT.read_text(encoding="utf-8"))
    hidden = yaml.safe_load((FIXTURES / "pilot_hidden_telecom.yaml").read_text(encoding="utf-8"))
    thinned = yaml.safe_load((FIXTURES / "pilot_power_nodes_only.yaml").read_text(encoding="utf-8"))
    pilot["layers"]["telecom"]["state"] = "hidden"
    assert hidden == pilot
    pilot["layers"]["telecom"]["state"] = "emitted"
    pilot["layers"]["power"]["nodes_only"] = True
    assert thinned == pilot


@pytest.mark.parametrize("world", WORLDS)
def test_the_golden_files_match_their_recorded_hashes(world: str) -> None:
    for name, digest in recorded_hashes(golden(world)).items():
        assert hashlib.sha256((golden(world) / name).read_bytes()).hexdigest() == digest, name


@pytest.mark.parametrize("world", WORLDS)
def test_the_build_writes_exactly_the_golden_tree(world: str, built: dict[str, Path]) -> None:
    out_dir = built[world]
    written = sorted(p.relative_to(out_dir).as_posix() for p in out_dir.rglob("*") if p.is_file())
    assert written == sorted(recorded_hashes(golden(world)))


@pytest.mark.parametrize(("world", "name"), GOLDEN_FILES)
def test_the_build_reproduces_each_golden_file(
    world: str, name: str, built: dict[str, Path]
) -> None:
    assert (built[world] / name).read_bytes() == (golden(world) / name).read_bytes()


@pytest.mark.parametrize("world", WORLDS)
def test_every_difference_from_the_pilot_is_explained(world: str) -> None:
    ours, pilot = recorded_hashes(golden(world)), recorded_hashes(PILOT_BUILD)
    assert set(ours) == set(pilot)
    assert {name for name in ours if ours[name] != pilot[name]} == set(DIFFERENCES[world])


# --- Same world -----------------------------------------------------------------------------


@pytest.mark.parametrize("world", WORLDS)
def test_every_stage_hash_equals_the_pilots(world: str, tmp_path: Path) -> None:
    recipe = str(FIXTURES / f"{world}.yaml")
    for command in STAGE_COMMANDS:
        assert main([command, recipe, "-o", str(tmp_path)]) == 0
        name = f"{command}_sha256.txt"
        assert (tmp_path / name).read_bytes() == (PILOT_STAGES / name).read_bytes(), name


@pytest.mark.parametrize("world", WORLDS)
def test_all_eight_reference_runs_equal_the_pilots(world: str, tmp_path: Path) -> None:
    assert main(["simulate", str(FIXTURES / f"{world}.yaml"), "-o", str(tmp_path)]) == 0
    names = sorted(recorded_hashes(PILOT_RUNS))
    assert len(names) == 32
    assert sorted(p.name for p in tmp_path.iterdir()) == names
    for name in names:
        assert (tmp_path / name).read_bytes() == (PILOT_RUNS / name).read_bytes(), name


@pytest.mark.parametrize("world", WORLDS)
def test_the_manifests_true_world_equals_the_pilots(world: str) -> None:
    ours, pilot = manifest(golden(world)), manifest(PILOT_BUILD)
    for section in TRUE_WORLD:
        assert ours[section] == pilot[section], section
    our_hidden, pilot_hidden = ours["hidden"], pilot["hidden"]
    assert isinstance(our_hidden, dict)
    assert isinstance(pilot_hidden, dict)
    assert our_hidden["dependencies"] == pilot_hidden["dependencies"]
    assert sorted_edges(our_hidden) == sorted_edges(pilot_hidden)


def sorted_edges(hidden: dict[str, list[dict[str, object]]]) -> list[dict[str, object]]:
    """Every coupling, hidden or shown: the couplings that exist."""
    return sorted(hidden["couplings"] + hidden["switched_on_couplings"], key=lambda r: str(r["id"]))


# --- Hidden layer ---------------------------------------------------------------------------


def test_no_telecom_feature_reaches_any_source() -> None:
    hidden, pilot = golden("pilot_hidden_telecom"), PILOT_BUILD
    assert telecom_names(pilot), "the pilot emits telecom, so the check can see it"
    for name in recorded_hashes(hidden):
        if not name.startswith("sources/") or name.endswith(".overpassql"):
            continue  # an Overpass query names what it asks for; it holds no feature
        body = (hidden / name).read_bytes()
        for telecom in telecom_names(pilot):
            assert telecom.encode("utf-8") not in body, (name, telecom)
    assert not [
        tags for tags in osm_tags(hidden) if tags & TELECOM_TAGS or has_key(tags, "telecom")
    ]
    assert overpass_features(hidden, "TWN_Telecom_OSM_Overpass.geojson") == []


def test_the_manifest_lists_telecom_and_its_couplings_as_hidden() -> None:
    record = manifest(golden("pilot_hidden_telecom"))["hidden"]
    assert isinstance(record, dict)
    assert record["layers"] == ["telecom"]
    touching = [
        edge
        for edge in sorted_edges(record)
        if "telecom" in (edge["supplier_layer"], edge["consumer_layer"])
    ]
    assert touching
    assert all(edge in record["couplings"] for edge in touching)
    assert not [
        edge
        for edge in record["switched_on_couplings"]
        if "telecom" in (edge["supplier_layer"], edge["consumer_layer"])
    ]
    correspondence = manifest(golden("pilot_hidden_telecom"))["correspondence"]
    assert isinstance(correspondence, list)
    assert not [row for row in correspondence if str(row["element"]).startswith("SWM-TEL-")]


# --- Nodes only -----------------------------------------------------------------------------


def test_no_power_line_tower_or_link_in_any_openstreetmap_form() -> None:
    thinned = golden("pilot_power_nodes_only")
    assert [tags for tags in osm_tags(PILOT_BUILD) if tags & POWER_LINK_TAGS], "the pilot has some"
    assert not [tags for tags in osm_tags(thinned) if tags & POWER_LINK_TAGS]
    for name in recorded_hashes(thinned):
        if name.startswith(GEOFABRIK) or name.startswith(OVERPASS):
            body = (thinned / name).read_bytes()
            for tag in (b"minor_line", b"power=line", b'"power": "line"', b'"power":"line"'):
                assert tag not in body, (name, tag)
    correspondence = manifest(thinned)["correspondence"]
    assert isinstance(correspondence, list)
    assert not [row for row in correspondence if str(row["element"]).startswith("SWM-POW-L")]


def test_power_nodes_are_still_emitted() -> None:
    def power_nodes(folder: Path) -> list[frozenset[tuple[str, str]]]:
        return [tags for tags in osm_tags(folder) if tags & POWER_NODE_TAGS]

    assert power_nodes(golden("pilot_power_nodes_only")) == power_nodes(PILOT_BUILD)
    assert power_nodes(PILOT_BUILD)


def test_the_manifest_records_the_withheld_power_links() -> None:
    thinned = manifest(golden("pilot_power_nodes_only"))["hidden"]
    pilot = manifest(PILOT_BUILD)["hidden"]
    assert isinstance(thinned, dict)
    assert isinstance(pilot, dict)
    power = [row for row in thinned["withheld_links"] if row["layer"] == "power"]
    assert power
    assert all(str(row["link"]).startswith("SWM-POW-L") for row in power)
    assert [row for row in thinned["withheld_links"] if row["layer"] != "power"] == pilot[
        "withheld_links"
    ]
    links = yaml.safe_load((PILOT_STAGES / "layers_links.yaml").read_text(encoding="utf-8"))
    assert {row["link"] for row in power} == {
        link["id"] for link in links_of(links) if link["layer"] == "power"
    }


def links_of(record: object) -> list[dict[str, object]]:
    """The links in the layers stage's link listing."""
    assert isinstance(record, dict | list)
    rows = record if isinstance(record, list) else record["links"]
    assert isinstance(rows, list)
    return rows


# --- Reading the OpenStreetMap forms --------------------------------------------------------


def osm_tags(folder: Path) -> list[frozenset[tuple[str, str]]]:
    """Every node's and way's tags, from the XML extract and the PBF extract (which must agree)."""
    root = ElementTree.parse(folder / OSM / "island.osm").getroot()
    from_xml = sorted(
        frozenset((tag.get("k", ""), tag.get("v", "")) for tag in element.iter("tag"))
        for element in root
        if element.tag in ("node", "way") and element.find("tag") is not None
    )  # fmt: skip
    from_pbf = sorted(
        tags for tags in pbf_tags((folder / OSM / "island.osm.pbf").read_bytes()) if tags
    )
    assert [sorted(t) for t in from_xml] == [sorted(t) for t in from_pbf]
    return from_xml


def has_key(tags: frozenset[tuple[str, str]], key: str) -> bool:
    return any(k == key for k, _ in tags)


def telecom_names(folder: Path) -> list[str]:
    """The names of the telecom objects a build emits to OpenStreetMap."""
    root = ElementTree.parse(folder / OSM / "island.osm").getroot()
    names = []
    for element in root:
        tags = {tag.get("k", ""): tag.get("v", "") for tag in element.iter("tag")}
        if "name" in tags and (set(tags.items()) & TELECOM_TAGS or "telecom" in tags):
            names.append(tags["name"])
    return sorted(names)


def overpass_features(folder: Path, name: str) -> list[object]:
    loaded = yaml.safe_load((folder / OVERPASS / name).read_text(encoding="utf-8"))
    features = loaded["features"]
    assert isinstance(features, list)
    return features


def pbf_tags(body: bytes) -> Iterator[frozenset[tuple[str, str]]]:
    """Yield each node's and way's tags from an uncompressed OpenStreetMap PBF file."""
    at = 0
    while at < len(body):
        (header_length,) = struct.unpack(">I", body[at : at + 4])
        header = dict(fields(body[at + 4 : at + 4 + header_length]))
        blob_start = at + 4 + header_length
        blob_length = header[3]
        assert isinstance(blob_length, int)
        blob = dict(fields(body[blob_start : blob_start + blob_length]))
        at = blob_start + blob_length
        if header[1] == b"OSMData":
            raw = blob[1]  # the writer stores blobs raw (field 1), never zlib
            assert isinstance(raw, bytes)
            yield from block_tags(raw)


def block_tags(block: bytes) -> Iterator[frozenset[tuple[str, str]]]:
    parts = list(fields(block))
    table = dict(parts)[1]
    assert isinstance(table, bytes)
    strings = [bytes(value).decode("utf-8") for _, value in fields(table)]  # type: ignore[arg-type]
    for number, group in parts:
        if number != 2 or not isinstance(group, bytes):
            continue
        for kind, body in fields(group):
            assert isinstance(body, bytes)
            if kind == 2:  # dense nodes: key and value indices interleaved, each node ends in 0
                keys_vals = packed(dict(fields(body)).get(10, b""))
                tags: list[tuple[str, str]] = []
                i = 0
                while i < len(keys_vals):
                    if keys_vals[i] == 0:
                        yield frozenset(tags)
                        tags, i = [], i + 1
                    else:
                        tags.append((strings[keys_vals[i]], strings[keys_vals[i + 1]]))
                        i += 2
            elif kind == 3:  # a way: packed key indices, packed value indices
                way = dict(fields(body))
                keys, values = packed(way.get(2, b"")), packed(way.get(3, b""))
                yield frozenset((strings[k], strings[v]) for k, v in zip(keys, values, strict=True))


def fields(message: bytes) -> Iterator[tuple[int, int | bytes]]:
    """Yield a protobuf message's (field number, value): varints as int, the rest as bytes."""
    at = 0
    while at < len(message):
        key, at = varint(message, at)
        number, wire = key >> 3, key & 7
        if wire == 0:
            value, at = varint(message, at)
            yield number, value
        elif wire == 2:
            length, at = varint(message, at)
            yield number, message[at : at + length]
            at += length
        else:
            raise AssertionError(f"wire type {wire} is not written")


def packed(value: int | bytes) -> list[int]:
    assert isinstance(value, bytes)
    out, at = [], 0
    while at < len(value):
        number, at = varint(value, at)
        out.append(number)
    return out


def varint(data: bytes, at: int) -> tuple[int, int]:
    value, shift = 0, 0
    while True:
        byte = data[at]
        value |= (byte & 0x7F) << shift
        at += 1
        if byte < 0x80:
            return value, at
        shift += 7
