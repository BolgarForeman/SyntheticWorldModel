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
