"""Check the recorded source headers against the real files, once, on this machine (WO 8, B1).

Offline only. Reads ``data_root`` from ``machine.toml`` (gitignored) and compares each header in
``swm.emit.headers`` with the first row of the real file it was copied from: a CSV's first line
(byte-order mark dropped) or, for the institution register, the spreadsheet's first row. Where
a header records its coordinate precision, the script also counts the decimal places of every
coordinate in the file and reports the most common count. Only the headers and the counts are
printed; no row of real data is copied anywhere.

Run: ``uv run python tools/check_source_headers.py`` (from the repository root).

Spec: Work Order 8, B1 and answer 1; WO-08 PR answers, item 2; CLAUDE.md §9.
"""

import collections
import csv
import io
import sys
import tomllib
import zipfile
from dataclasses import replace
from pathlib import Path
from xml.etree.ElementTree import iterparse

from swm.emit.headers import HOSPITAL_LISTS, RECORDED, RecordedHeader

MACHINE = Path(__file__).resolve().parents[1] / "machine.toml"
TABLE = "{urn:oasis:names:tc:opendocument:xmlns:table:1.0}"
TEXT = "{urn:oasis:names:tc:opendocument:xmlns:text:1.0}"
SAME_HEADER = (
    "TW_GOV/NHIA/H3_39281_nhi_regional_hospitals/raw/A21030000I-D21002-005.csv",
    "TW_GOV/NHIA/H4_39282_nhi_district_hospitals/raw/A21030000I-D21003-003.csv",
)
"""H3 and H4, which carry H2's header (recorded once, as HOSPITAL_LISTS)."""


def say(line: str) -> None:
    """Print one line of the report."""
    print(line)  # noqa: T201 - the script's output is its report


def real_header(path: Path) -> tuple[str, ...]:
    """Return a real file's header: a CSV's first line or a spreadsheet's first row."""
    if path.suffix == ".ods":
        return _ods_first_row(path)
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return tuple(next(csv.reader(handle)))


def _ods_first_row(path: Path) -> tuple[str, ...]:
    with zipfile.ZipFile(path) as archive, archive.open("content.xml") as content:
        for _, element in iterparse(io.BufferedReader(content)):
            if element.tag == f"{TABLE}table-row":
                cells = []
                for cell in element.iter(f"{TABLE}table-cell"):
                    value = "".join(p.text or "" for p in cell.iter(f"{TEXT}p"))
                    repeat = int(cell.get(f"{TABLE}number-columns-repeated", "1"))
                    cells.extend([value] * min(repeat, 64))
                while cells and not cells[-1]:
                    cells.pop()
                return tuple(cells)
    return ()


def decimal_counts(path: Path, columns: tuple[str, ...]) -> collections.Counter[int]:
    """Count the decimal places of every value in the given columns of a CSV."""
    counts: collections.Counter[int] = collections.Counter()
    with path.open(encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            for column in columns:
                value = row[column]
                if value:
                    counts[len(value.split(".")[1]) if "." in value else 0] += 1
    return counts


def check_decimals(header: RecordedHeader, data_root: Path) -> bool:
    """Print a header's measured coordinate precision; return whether it is the recorded one."""
    counts = decimal_counts(data_root / header.real_file, header.coordinate_columns)
    common = counts.most_common(1)[0][0]
    status = "MATCH  " if common == header.coordinate_decimals else "DIFFERS"
    say(f"{status}  decimals {header.real_file}: most common {common} (recorded "
        f"{header.coordinate_decimals}); counts {dict(sorted(counts.items()))}")  # fmt: skip
    return common == header.coordinate_decimals


def check(header: RecordedHeader, data_root: Path) -> bool:
    """Print one header's result; return whether it matches the real file exactly."""
    path = data_root / header.real_file
    if not path.exists():
        say(f"MISSING  {header.real_file}")
        return False
    real = real_header(path)
    if real == header.columns:
        say(f"MATCH    {header.real_file}  ({len(real)} columns)")
        return True
    say(f"DIFFERS  {header.real_file}")
    say(f"  recorded: {header.columns}")
    say(f"  real:     {real}")
    return False


def main() -> int:
    """Check every recorded header; return 0 when all match."""
    if not MACHINE.exists():
        say("machine.toml not found: copy machine.example.toml and set data_root")
        return 2
    data_root = Path(tomllib.loads(MACHINE.read_text(encoding="utf-8"))["data_root"])
    results = [check(header, data_root) for header in RECORDED]
    results += [check(replace(HOSPITAL_LISTS, real_file=path), data_root) for path in SAME_HEADER]
    results += [check_decimals(h, data_root) for h in RECORDED if h.coordinate_decimals is not None]
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main())
