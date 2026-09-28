import tomllib
from pathlib import Path

import pytest

import swm
from swm.cli import main

PYPROJECT = Path(__file__).resolve().parents[2] / "pyproject.toml"


def test_version_matches_pyproject_and_cli_reports_it(capsys: pytest.CaptureFixture[str]) -> None:
    declared = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))["project"]["version"]
    assert swm.__version__ == declared

    with pytest.raises(SystemExit) as exit_info:
        main(["--version"])
    assert exit_info.value.code == 0
    assert capsys.readouterr().out == f"swm {declared}\n"

    assert main([]) == 0
