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
    expected = {"nodes": 24, "links": 23}
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


def test_preview_world_writes_a_png(pilot_path: Path, tmp_path: Path) -> None:
    pytest.importorskip("matplotlib")
    image = tmp_path / "world.png"
    assert main(["preview-world", str(pilot_path), "-o", str(image)]) == 0
    assert image.read_bytes().startswith(b"\x89PNG\r\n\x1a\n")


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
    assert "this code reads version 1" in capsys.readouterr().err
    assert not (tmp_path / "out").exists()
