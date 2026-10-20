"""Phase 1 records error settings but does not apply them (Work Order 9, C2, ruled 2026-10-11).

``swm build`` and ``swm emit`` print one warning naming every source whose settings are above
zero; the manifest declares the departure; the resolved recipe carries the same note beside its
errors section; and the sources equal a zero-rate build's byte for byte.
"""

import io
import sys
from pathlib import Path

import pytest
import yaml

from swm.cli import main
from swm.recipe.io import load_recipe, write_resolved_recipe
from swm.recipe.resolve import resolve
from swm.recipe.schema import RECORDED_NOT_APPLIED, Errors, Source, SourceErrors, errors_above_zero

PILOT = Path(__file__).resolve().parents[1] / "fixtures" / "pilot_hand_check.yaml"
ZERO = SourceErrors(coverage_pct=100, snapshot_age_y=0, phantom_pct=0, missing_pct=0,
                    merged_pct=0, location_pct=0, attributes_pct=0, links_pct=0,
                    labels_pct=0)  # fmt: skip
"""Settings that plant nothing: full coverage, a current snapshot, every rate zero."""
PILOT_SOURCES = (
    "facility_register", "osm_fuel", "osm_health", "osm_power", "osm_telecom", "osm_transport",
    "osm_water", "ourairports", "wri_gppd",
)  # fmt: skip
WARNING = f"warning: {RECORDED_NOT_APPLIED}: {', '.join(PILOT_SOURCES)}\n"


def zero_rate_recipe(out_dir: Path) -> Path:
    """The pilot with every switched-on source's error settings at zero."""
    data = yaml.safe_load(PILOT.read_text(encoding="utf-8"))
    data["errors"]["sources"] = {source: ZERO.model_dump(mode="json") for source in PILOT_SOURCES}
    path = out_dir / "pilot_zero_rate.yaml"
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8", newline="\n")
    return path


def tree(folder: Path) -> dict[str, bytes]:
    return {
        p.relative_to(folder).as_posix(): p.read_bytes() for p in folder.rglob("*") if p.is_file()
    }


@pytest.fixture(scope="module")
def builds(tmp_path_factory: pytest.TempPathFactory) -> dict[str, tuple[Path, str]]:
    """The pilot (defaults above zero) and its zero-rate twin, built, with what each printed."""
    root = tmp_path_factory.mktemp("errors")
    out: dict[str, tuple[Path, str]] = {}
    for name, recipe in (("pilot", PILOT), ("zero", zero_rate_recipe(root))):
        out_dir = root / name
        with pytest.MonkeyPatch.context() as patch:
            printed = io.StringIO()
            patch.setattr(sys, "stderr", printed)
            assert main(["build", str(recipe), "-o", str(out_dir)]) == 0
        out[name] = (out_dir, printed.getvalue())
    return out


# --- Which settings are above zero ----------------------------------------------------------


def test_the_resolved_pilot_has_every_source_above_zero() -> None:
    assert errors_above_zero(resolve(load_recipe(PILOT)).recipe.errors) == PILOT_SOURCES


def test_settings_that_plant_nothing_are_not_above_zero() -> None:
    assert errors_above_zero(Errors(sources={Source.OSM_POWER: ZERO})) == ()
    assert errors_above_zero(Errors()) == ()


@pytest.mark.parametrize(
    ("field", "value"),
    [("coverage_pct", 99), ("snapshot_age_y", 1), ("phantom_pct", 1), ("missing_pct", 1),
     ("merged_pct", 1), ("location_pct", 1), ("attributes_pct", 1), ("links_pct", 1),
     ("labels_pct", 1)],
)  # fmt: skip
def test_any_one_setting_off_zero_puts_its_source_above_zero(field: str, value: int) -> None:
    errors = Errors(sources={
        Source.OSM_POWER: ZERO.model_copy(update={field: value}), Source.WRI_GPPD: ZERO,
    })  # fmt: skip
    assert errors_above_zero(errors) == (Source.OSM_POWER,)


# --- The ruled behaviour --------------------------------------------------------------------


def test_build_warns_once_naming_every_source_above_zero(
    builds: dict[str, tuple[Path, str]],
) -> None:
    assert builds["pilot"][1] == WARNING
    assert builds["zero"][1] == ""


def test_emit_warns_the_same(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["emit", str(PILOT), "-o", str(tmp_path)]) == 0
    assert capsys.readouterr().err == WARNING


def test_the_sources_equal_the_zero_rate_build_byte_for_byte(
    builds: dict[str, tuple[Path, str]],
) -> None:
    pilot, zero = tree(builds["pilot"][0] / "sources"), tree(builds["zero"][0] / "sources")
    assert pilot
    assert pilot == zero


def test_the_manifest_declares_the_departure(builds: dict[str, tuple[Path, str]]) -> None:
    def departures(name: str) -> list[str]:
        manifest = (builds[name][0] / "truth" / "manifest.yaml").read_text(encoding="utf-8")
        listed: list[str] = yaml.safe_load(manifest)["declared_departures"]
        return listed

    notice = f"{RECORDED_NOT_APPLIED[0].upper()}{RECORDED_NOT_APPLIED[1:]}"
    assert departures("pilot") == [*departures("zero"), f"{notice}: {', '.join(PILOT_SOURCES)}."]


def test_the_resolved_recipe_notes_it_beside_the_errors_section(
    builds: dict[str, tuple[Path, str]],
) -> None:
    lines = (builds["pilot"][0] / "resolved_recipe.yaml").read_text(encoding="utf-8").splitlines()
    note = lines.index(f"# {RECORDED_NOT_APPLIED}: {', '.join(PILOT_SOURCES)}")
    assert lines[note + 1] == "errors:"
    zero = (builds["zero"][0] / "resolved_recipe.yaml").read_text(encoding="utf-8")
    assert RECORDED_NOT_APPLIED not in zero


def test_the_noted_resolved_recipe_loads_as_the_same_recipe(tmp_path: Path) -> None:
    recipe = resolve(load_recipe(PILOT)).recipe
    assert load_recipe(write_resolved_recipe(recipe, tmp_path)) == recipe
