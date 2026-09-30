import sys
from pathlib import Path

import pytest

from swm.cli import main


def test_terrain_writes_statistics_and_hashes(pilot_path: Path, tmp_path: Path) -> None:
    assert main(["terrain", str(pilot_path), "-o", str(tmp_path)]) == 0
    stats = (tmp_path / "terrain_stats.yaml").read_text(encoding="utf-8")
    assert stats.startswith("grid_cells: 256\n")
    hashes = (tmp_path / "terrain_sha256.txt").read_text(encoding="utf-8").splitlines()
    assert [line.split("  ")[1] for line in hashes][:2] == ["elevation_dm", "land"]


def test_terrain_refuses_a_map_type_not_built(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    recipe = tmp_path / "archipelago.yaml"
    recipe.write_text("recipe_version: 1\nterrain:\n  map_type: archipelago\n", encoding="utf-8")
    assert main(["terrain", str(recipe), "-o", str(tmp_path / "out")]) == 1
    assert "arrives in Phase 5" in capsys.readouterr().err
    assert not (tmp_path / "out").exists()


def test_layers_writes_statistics_tables_and_hashes(
    pilot_path: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main(["layers", str(pilot_path), "-o", str(tmp_path)]) == 0
    for name in ("layers_stats.yaml", "layers_nodes.yaml", "layers_links.yaml"):
        assert (tmp_path / name).read_bytes()
    hashes = (tmp_path / "layers_sha256.txt").read_text(encoding="utf-8").splitlines()
    assert [line.split("  ")[1] for line in hashes] == ["layers_nodes.yaml", "layers_links.yaml"]


def test_couplings_writes_statistics_and_hashes_and_prints_the_total(
    pilot_path: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main(["couplings", str(pilot_path), "-o", str(tmp_path)]) == 0
    stats = (tmp_path / "couplings_stats.yaml").read_text(encoding="utf-8")
    assert stats.startswith("modeling_rules:\n  registry_version:")
    assert "\npairs:\n  power-telecom:\n" in stats
    assert "  total_edges: 50\n" in stats
    table = (tmp_path / "couplings_edges.csv").read_bytes()
    assert b"\r" not in table
    lines = table.decode("utf-8").splitlines()
    assert lines[0] == (
        "edge_id,supplier_id,supplier_class,consumer_id,consumer_class,dependency_type,"
        "feed_configuration,role"
    )
    assert len(lines) == 1 + 27  # every switched-on coupling edge
    assert [line.split(",")[0] for line in lines[1:]] == sorted(
        line.split(",")[0] for line in lines[1:]
    )
    hashes = (tmp_path / "couplings_sha256.txt").read_text(encoding="utf-8").splitlines()
    assert [line.split("  ")[1] for line in hashes] == ["edges", "dependencies"]
    assert "total edges 50: 23 intra-layer links and 27 switched-on" in capsys.readouterr().out


def test_requirements_writes_statistics_and_a_hash(
    pilot_path: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main(["requirements", str(pilot_path), "-o", str(tmp_path)]) == 0
    stats = (tmp_path / "requirements_stats.yaml").read_text(encoding="utf-8")
    assert stats.startswith("modeling_rules:\n  registry_version:")
    assert "\nelectricity_mw:\n" in stats
    hashes = (tmp_path / "requirements_sha256.txt").read_text(encoding="utf-8").splitlines()
    assert [line.split("  ")[1] for line in hashes] == ["requirements"]
    assert "\npower_sizing:\n" in stats


def test_rules_renders_the_modeling_rules_page_without_a_recipe(tmp_path: Path) -> None:
    from swm.rules.registry import load_registry

    page = tmp_path / "rules.html"
    assert main(["rules", "-o", str(page)]) == 0
    text = page.read_text(encoding="utf-8")
    assert text.startswith("<!doctype html>")
    assert "<title>Modeling Rules</title>" in text
    assert load_registry().sha256 in text


def test_buffers_and_strength_write_statistics_and_hashes(
    pilot_path: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main(["buffers", str(pilot_path), "-o", str(tmp_path)]) == 0
    stats = (tmp_path / "buffers_stats.yaml").read_text(encoding="utf-8")
    assert "\nreserves:\n" in stats
    assert "\nfailure_modes:\n" in stats
    hashes = (tmp_path / "buffers_sha256.txt").read_text(encoding="utf-8").splitlines()
    assert [line.split("  ")[1] for line in hashes] == [
        "reserves", "backups", "resupply", "tolerance", "failure_modes",
    ]  # fmt: skip
    assert main(["strength", str(pilot_path), "-o", str(tmp_path)]) == 0
    stats = (tmp_path / "strength_stats.yaml").read_text(encoding="utf-8")
    assert "\ndependencies_short: 0\n" in stats
    assert "every consumer is fully supplied" in capsys.readouterr().out


def test_repair_writes_statistics_and_hashes(pilot_path: Path, tmp_path: Path) -> None:
    assert main(["repair", str(pilot_path), "-o", str(tmp_path)]) == 0
    stats = (tmp_path / "repair_stats.yaml").read_text(encoding="utf-8")
    assert stats.startswith("modeling_rules:\n  registry_version:")
    assert "\ncrew_bases:\n- base_id: CRB-0001\n" in stats
    assert "\ncrews: 2\n" in stats
    hashes = (tmp_path / "repair_sha256.txt").read_text(encoding="utf-8").splitlines()
    assert [line.split("  ")[1] for line in hashes] == [
        "crew_bases", "crews", "mobile_units",
        "travel", "permanent_repair", "emergency_repair", "unrepairable",
    ]  # fmt: skip


def test_more_crew_bases_than_towns_exits_1_naming_the_setting(
    pilot_path: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    recipe = tmp_path / "bases.yaml"
    recipe.write_text(
        pilot_path.read_text(encoding="utf-8").replace("  crew_base: 1 ", "  crew_base: 9 "),
        encoding="utf-8",
    )
    assert main(["repair", str(recipe), "-o", str(tmp_path)]) == 1
    assert "unobserved.crew_base = 9" in capsys.readouterr().err


@pytest.mark.parametrize("crews", [1, 2, 3])
def test_the_crew_sensitivity_recipes_differ_from_the_pilot_only_in_crews(
    crews: int, pilot_path: Path, tmp_path: Path
) -> None:
    from swm.recipe.io import load_recipe

    fixture = pilot_path.parent / "crew_sensitivity" / f"pilot_crews_{crews}.yaml"
    recipe = load_recipe(fixture)
    pilot = load_recipe(pilot_path)
    assert recipe.unobserved.crews == crews
    assert recipe.model_copy(update={"unobserved": pilot.unobserved}) == pilot
    assert main(["repair", str(fixture), "-o", str(tmp_path)]) == 0
    stats = (tmp_path / "repair_stats.yaml").read_text(encoding="utf-8")
    assert f"\ncrews: {crews}\n" in stats


@pytest.mark.parametrize(("name", "gap"), [("plus_20", 20), ("minus_20", -20)])
def test_the_repair_sensitivity_recipes_differ_from_the_pilot_only_in_the_gap(
    name: str, gap: int, pilot_path: Path, tmp_path: Path
) -> None:
    from swm.recipe.io import load_recipe

    fixture = pilot_path.parent / "repair_sensitivity" / f"pilot_repair_gap_{name}.yaml"
    recipe = load_recipe(fixture)
    pilot = load_recipe(pilot_path)
    assert recipe.unobserved.repair_rates.compliance_gap_pct == gap
    assert recipe.unobserved.repair_rates.heterogeneity_pct is None
    unobserved = recipe.unobserved.model_copy(
        update={"repair_rates": pilot.unobserved.repair_rates}
    )
    assert recipe.model_copy(update={"unobserved": unobserved}) == pilot
    assert main(["repair", str(fixture), "-o", str(tmp_path)]) == 0


def test_repair_defaults_to_the_hazus_centre_and_spread_with_a_pool_of_one_each() -> None:
    from swm.recipe.schema import Unobserved

    unobserved = Unobserved()
    assert unobserved.repair_rates.compliance_gap_pct == 0
    assert unobserved.repair_rates.heterogeneity_pct is None
    assert (unobserved.mobile_substations, unobserved.mobile_cell_sites) == (1, 1)


def test_a_recipe_can_lower_the_share_of_well_maintained_generators(
    pilot_path: Path, tmp_path: Path
) -> None:
    recipe = tmp_path / "poorly_maintained.yaml"
    recipe.write_text(
        pilot_path.read_text(encoding="utf-8")
        + "modeling_rules:\n  overrides:\n"
        + "    reserves.generator_availability.well_maintained_share: 0.0\n",
        encoding="utf-8",
    )
    assert main(["buffers", str(recipe), "-o", str(tmp_path)]) == 0
    stats = (tmp_path / "buffers_stats.yaml").read_text(encoding="utf-8")
    assert "reserves.generator_availability.well_maintained_share: 0.0" in stats
    assert "\n  well_maintained: 0\n" in stats


def test_check_passes_the_pilot_and_stops_a_short_world(
    pilot_path: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main(["check", str(pilot_path)]) == 0
    assert "every consumer is fully supplied" in capsys.readouterr().out
    short = tmp_path / "short.yaml"
    short.write_text(
        "recipe_version: 1\n"
        "modeling_rules:\n"
        "  overrides:\n"
        "    layers.attributes.distribution_substation: {capacity_mva: [0.0, 0.0]}\n",
        encoding="utf-8",
    )
    assert main(["check", str(short)]) == 1
    err = capsys.readouterr().err
    assert "undisturbed supply:" in err
    assert "power: R = 0.0000" in err


def test_preview_couplings_writes_a_png(pilot_path: Path, tmp_path: Path) -> None:
    pytest.importorskip("matplotlib")
    image = tmp_path / "couplings.png"
    assert main(["preview-couplings", str(pilot_path), "-o", str(image)]) == 0
    assert image.read_bytes().startswith(b"\x89PNG\r\n\x1a\n")


def test_layers_prints_its_siting_notes(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    recipe = tmp_path / "dry.yaml"
    recipe.write_text(
        "recipe_version: 1\nterrain:\n  character:\n    river_density: 0\n", encoding="utf-8"
    )
    assert main(["layers", str(recipe), "-o", str(tmp_path / "out")]) == 0
    assert "transport: bridge: the island has no river" in capsys.readouterr().out


def test_export_gis_writes_a_readable_geopackage_and_geotiffs(
    pilot_path: Path, tmp_path: Path
) -> None:
    pytest.importorskip("rasterio")
    import pyogrio
    import rasterio

    from swm.manifest.inspection import SYNTHETIC_NOTICE

    assert main(["export-gis", str(pilot_path), "-o", str(tmp_path)]) == 0
    package = str(tmp_path / "world.gpkg")
    expected = {"nodes": 24, "links": 23, "couplings": 72}
    for layer in ("power", "telecom", "water", "transport", "fuel", "healthcare"):
        expected[f"nodes_{layer}"] = 4
    for layer, count in expected.items():
        info = pyogrio.read_info(package, layer=layer)
        assert info["features"] == count
        assert info["crs"] == "EPSG:32710"
        assert SYNTHETIC_NOTICE in info["layer_metadata"]["DESCRIPTION"]
    assert pyogrio.read_info(package, layer="cities")["features"] == 3
    assert pyogrio.read_info(package, layer="coastline")["features"] == 3
    nodes_bounds = pyogrio.read_info(package, layer="nodes")["total_bounds"]
    with rasterio.open(tmp_path / "elevation_m.tif") as raster:
        assert raster.crs.to_epsg() == 32710
        assert raster.tags()["DESCRIPTION"] == SYNTHETIC_NOTICE
        bounds = raster.bounds
        assert bounds.left <= nodes_bounds[0]
        assert nodes_bounds[2] <= bounds.right
        assert bounds.bottom <= nodes_bounds[1]
        assert nodes_bounds[3] <= bounds.top
        assert raster.read(1).max() == pytest.approx(2440.0)
    for name in ("land_cover.tif", "rivers.tif"):
        with rasterio.open(tmp_path / name) as raster:
            assert raster.crs.to_epsg() == 32710
            assert raster.bounds == bounds


def test_export_gis_writes_typed_tables(pilot_path: Path, tmp_path: Path) -> None:
    pytest.importorskip("pyogrio")
    import pyogrio

    assert main(["export-gis", str(pilot_path), "-o", str(tmp_path)]) == 0
    package = str(tmp_path / "world.gpkg")

    def columns(layer: str) -> dict[str, str]:
        info = pyogrio.read_info(package, layer=layer)
        return dict(zip(info["fields"], info["dtypes"], strict=True))

    common = {
        "node_id": "object",
        "layer": "object",
        "class": "object",
        "city_id": "int64",
        "longitude": "float64",
        "latitude": "float64",
    }
    assert columns("nodes") == common
    power = columns("nodes_power")
    assert power["capacity_mw"] == "float64"
    assert power["capacity_mva"] == "int64"
    assert power["voltage_kv"] == "float64"
    assert power["fuel_kind"] == "object"
    assert columns("nodes_transport")["towered"] == "bool"
    assert columns("nodes_fuel")["pipeline_connected"] == "bool"
    assert columns("nodes_healthcare")["bed_count"] == "int64"
    assert columns("links")["crosses_sea"] == "bool"
    assert columns("links")["river_crossings"] == "int64"
    couplings = columns("couplings")
    assert couplings["switched_on"] == "bool"
    assert couplings["feed_group"] == "int64"
    assert couplings["length_km"] == "float64"
    assert couplings["public_share_pct"] == "int64"
    assert couplings["dependency_type"] == "object"
    info = pyogrio.read_info(package, layer="couplings")
    assert "unobserved truth" in info["layer_metadata"]["DESCRIPTION"]
    assert info["geometry_type"] == "LineString"
    assert "attributes" not in columns("nodes_power")
    description = pyogrio.read_info(package, layer="nodes_power")["layer_metadata"]["DESCRIPTION"]
    assert "fuel_kind" in description
    assert "unobserved truth" in description
    _, _, _, fields = pyogrio.raw.read(package, layer="nodes_power")
    names = pyogrio.read_info(package, layer="nodes_power")["fields"].tolist()
    capacity_mw = fields[names.index("capacity_mw")]
    classes = fields[names.index("class")]
    for node_class, value in zip(classes, capacity_mw, strict=True):
        assert (node_class == "generation") == (value == value)  # NaN is null elsewhere


def test_preview_world_writes_a_png_with_or_without_couplings(
    pilot_path: Path, tmp_path: Path
) -> None:
    pytest.importorskip("matplotlib")
    with_couplings, without = tmp_path / "world.png", tmp_path / "bare.png"
    assert main(["preview-world", str(pilot_path), "-o", str(with_couplings)]) == 0
    assert main(["preview-world", str(pilot_path), "-o", str(without), "--no-couplings"]) == 0
    for image in (with_couplings, without):
        assert image.read_bytes().startswith(b"\x89PNG\r\n\x1a\n")
    assert with_couplings.read_bytes() != without.read_bytes()


def test_export_and_preview_say_how_to_install_what_they_need(
    pilot_path: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setitem(sys.modules, "swm.manifest.inspection", None)
    monkeypatch.setitem(sys.modules, "swm.preview", None)
    assert main(["export-gis", str(pilot_path), "-o", str(tmp_path)]) == 1
    assert main(["preview-world", str(pilot_path), "-o", str(tmp_path / "w.png")]) == 1
    assert main(["preview-couplings", str(pilot_path), "-o", str(tmp_path / "c.png")]) == 1
    err = capsys.readouterr().err
    assert "uv sync --extra export" in err
    assert "uv sync --extra preview" in err


def test_preview_terrain_writes_a_png(pilot_path: Path, tmp_path: Path) -> None:
    pytest.importorskip("matplotlib")
    image = tmp_path / "pilot.png"
    assert main(["preview-terrain", str(pilot_path), "-o", str(image)]) == 0
    assert image.read_bytes().startswith(b"\x89PNG\r\n\x1a\n")


def test_preview_terrain_without_matplotlib_says_how_to_install(
    pilot_path: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setitem(sys.modules, "swm.preview", None)
    assert main(["preview-terrain", str(pilot_path), "-o", str(tmp_path / "p.png")]) == 1
    assert "uv sync --extra preview" in capsys.readouterr().err


def test_resolve_writes_both_files_and_a_second_run_gives_identical_bytes(
    pilot_path: Path, tmp_path: Path
) -> None:
    assert main(["resolve", str(pilot_path), "-o", str(tmp_path / "first")]) == 0
    assert main(["resolve", str(pilot_path), "-o", str(tmp_path / "second")]) == 0
    for name in ("resolved_recipe.yaml", "stream_record.yaml"):
        first = (tmp_path / "first" / name).read_bytes()
        assert first
        assert first == (tmp_path / "second" / name).read_bytes()


def test_check_recipe_prints_notes_and_buildability(
    pilot_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main(["check-recipe", str(pilot_path)]) == 0
    out = capsys.readouterr().out
    assert "Validation notes:\n" in out
    assert "  - errors.sources.osm_fuel.links_pct is ignored" in out
    assert "Not yet buildable:\n" in out
    assert "  - tier:exact: Phase 1\n" in out
    assert "map_type:spine_island" not in out


def test_check_recipe_reports_none_when_nothing_to_say(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    recipe = tmp_path / "quiet.yaml"
    recipe.write_text(
        "recipe_version: 1\nlayers:\n"
        + "".join(
            f"  {layer}:\n    state: off\n    sources: []\n"
            for layer in ("power", "telecom", "water", "transport", "fuel", "healthcare")
        )
        + "answer_key_requests: []\n",
        encoding="utf-8",
    )
    assert main(["check-recipe", str(recipe)]) == 0
    assert "Validation notes:\n  none\n" in capsys.readouterr().out


def test_invalid_recipe_names_the_field_and_exits_1(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    bad = tmp_path / "bad.yaml"
    bad.write_text("recipe_version: 1\nunobserved:\n  crews: 0\n", encoding="utf-8")
    assert main(["check-recipe", str(bad)]) == 1
    assert "unobserved.crews" in capsys.readouterr().err


def test_unknown_version_exits_1(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    bad = tmp_path / "old.yaml"
    bad.write_text("recipe_version: 0\n", encoding="utf-8")
    assert main(["resolve", str(bad), "-o", str(tmp_path / "out")]) == 1
    assert "this code reads version 1, 2" in capsys.readouterr().err
    assert not (tmp_path / "out").exists()
