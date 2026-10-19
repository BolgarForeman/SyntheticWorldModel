"""The same recipe gives the same bytes (CLAUDE.md §4 and §7).

For any root and terrain seed, emitting the pilot twice in one process writes identical source
trees. The golden worlds prove the same across processes and on Windows and Linux.
"""

from pathlib import Path
from tempfile import TemporaryDirectory

import yaml
from hypothesis import given, settings
from hypothesis import strategies as st

from swm.cli import main

PILOT = Path(__file__).resolve().parents[1] / "fixtures" / "pilot_hand_check.yaml"


def emitted(recipe: Path, out_dir: Path) -> tuple[int, dict[str, bytes]]:
    code = main(["emit", str(recipe), "-o", str(out_dir)])
    files = {p.relative_to(out_dir).as_posix(): p.read_bytes() for p in out_dir.rglob("*")
             if p.is_file()}  # fmt: skip
    return code, files


@settings(max_examples=4, deadline=None)
@given(
    root_seed=st.integers(min_value=0, max_value=2**32 - 1),
    terrain_seed=st.integers(min_value=0, max_value=2**32 - 1),
)
def test_the_same_recipe_gives_the_same_bytes(root_seed: int, terrain_seed: int) -> None:
    data = yaml.safe_load(PILOT.read_text(encoding="utf-8"))
    data["root_seed"] = root_seed
    data["terrain"]["terrain_seed"] = terrain_seed
    with TemporaryDirectory() as folder:
        root = Path(folder)
        recipe = root / "recipe.yaml"
        recipe.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8", newline="\n")
        first = emitted(recipe, root / "first")
        second = emitted(recipe, root / "second")
    assert first[0] == 0
    assert first[1]
    assert first == second
