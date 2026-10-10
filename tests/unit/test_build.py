"""Identity check (golden): ``swm build`` writes the pilot's whole tree, the same bytes on every
platform: the resolved recipe, ``sources/``, ``truth/`` and ``trace_pack/`` (Work Order 8, E1).

The hand-trace pack's timeline is the reference run's own: each hour's states equal the saved
reference run 7 (Part D).
"""

import csv
import hashlib
from pathlib import Path

import pytest
import yaml

from swm.cli import main

TESTS = Path(__file__).resolve().parents[1]
GOLDEN = TESTS / "golden" / "pilot_build"
RUNS = TESTS / "golden" / "pilot_reference_runs"
PILOT = TESTS / "fixtures" / "pilot_hand_check.yaml"


def recorded_hashes() -> dict[str, str]:
    lines = (GOLDEN / "SHA256SUMS").read_text(encoding="utf-8").splitlines()
    return {name: digest for digest, name in (line.split("  ") for line in lines)}


FILES = tuple(sorted(recorded_hashes()))


@pytest.fixture(scope="module")
def built(tmp_path_factory: pytest.TempPathFactory) -> Path:
    out_dir = tmp_path_factory.mktemp("build")
    assert main(["build", str(PILOT), "-o", str(out_dir)]) == 0
    return out_dir


def test_the_build_writes_exactly_the_golden_tree(built: Path) -> None:
    written = sorted(p.relative_to(built).as_posix() for p in built.rglob("*") if p.is_file())
    assert written == list(FILES)
    assert {name.split("/")[0] for name in FILES} == {
        "resolved_recipe.yaml", "sources", "truth", "trace_pack"}  # fmt: skip


def test_the_golden_files_match_their_recorded_hashes() -> None:
    for name, digest in recorded_hashes().items():
        assert hashlib.sha256((GOLDEN / name).read_bytes()).hexdigest() == digest, name


@pytest.mark.parametrize("name", FILES)
def test_the_pilot_build_reproduces_each_golden_file(name: str, built: Path) -> None:
    assert (built / name).read_bytes() == (GOLDEN / name).read_bytes()


def test_emit_writes_the_sources_alone(tmp_path: Path, built: Path) -> None:
    assert main(["emit", str(PILOT), "-o", str(tmp_path)]) == 0
    written = sorted(p.relative_to(tmp_path).as_posix() for p in tmp_path.rglob("*") if p.is_file())
    assert written == [name for name in FILES if name.startswith("sources/")]
    for name in written:
        assert (tmp_path / name).read_bytes() == (built / name).read_bytes()


def test_the_timeline_equals_reference_run_7() -> None:
    with (GOLDEN / "trace_pack" / "timeline.csv").open(encoding="utf-8", newline="") as handle:
        timeline = list(csv.DictReader(handle))
    with (RUNS / "run_7_states.csv").open(encoding="utf-8", newline="") as handle:
        states = {row["hour"]: row for row in csv.DictReader(handle)}
    assert len(timeline) == 73
    for row in timeline:
        saved = states[row["hour"]]
        assert {k: row[k] for k in saved} == saved


def test_the_timeline_crews_follow_the_saved_crew_jobs() -> None:
    with (GOLDEN / "trace_pack" / "timeline.csv").open(encoding="utf-8", newline="") as handle:
        timeline = list(csv.DictReader(handle))
    with (RUNS / "run_7_crews.csv").open(encoding="utf-8", newline="") as handle:
        jobs = list(csv.DictReader(handle))
    for row in timeline:
        hour = float(row["hour"])
        for crew in {job["crew"] for job in jobs}:
            doing = [f"{j['activity']} {j['job']}" for j in jobs if j["crew"] == crew
                     and float(j["start_h"]) <= hour < float(j["end_h"])]  # fmt: skip
            if doing:
                assert row[crew] == doing[0], (hour, crew)


def test_the_trace_pdfs_carry_a_fixed_producer_and_no_date_or_compression() -> None:
    for name in ("map.pdf", "tables.pdf"):
        body = (GOLDEN / "trace_pack" / name).read_bytes()
        assert b"/Producer (swm trace-pack)" in body
        assert b"/CreationDate" not in body
        assert b"/FlateDecode" not in body


def test_the_manifest_records_every_seed_and_the_zero_error_emission() -> None:
    manifest = yaml.safe_load((GOLDEN / "truth" / "manifest.yaml").read_text(encoding="utf-8"))
    assert manifest["planted_errors"]["status"] == "zero-error emission (Phase 1)"
    assert manifest["seeds"]["spawn_tree"]
    assert manifest["theta"]["theta_list"]


def test_the_trace_pack_command_takes_a_scenario(tmp_path: Path) -> None:
    assert main(["trace-pack", str(PILOT), "--scenario", "4", "-o", str(tmp_path)]) == 0
    assert (tmp_path / "trace_pack" / "map.pdf").exists()
    assert main(["trace-pack", str(PILOT), "--scenario", "99", "-o", str(tmp_path)]) != 0
