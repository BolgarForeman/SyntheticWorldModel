"""Delimited text in a real source's own idiom: byte order mark, line ending and quoting.

Real files differ in small ways the pipeline reads through: WRI is unquoted except where a
value holds a comma, with CRLF; OurAirports quotes every non-empty text value and leaves
numbers bare, with LF; the health insurance lists carry a byte order mark. Each writer names
its idiom, so the emitted bytes look like the real file's.

Spec: Work Order 8, B1 and B5; answer 1.
"""

from collections.abc import Sequence
from dataclasses import dataclass

Cell = str | int | float | None
BOM = "\ufeff"
"""The UTF-8 byte order mark some real files begin with."""


@dataclass(frozen=True)
class Idiom:
    """How a real file writes its rows."""

    line_ending: str
    bom: bool
    quote_text: bool
    """True: every non-empty text cell is quoted (OurAirports); False: only where needed."""


def delimited(header: Sequence[str], rows: Sequence[Sequence[Cell]], idiom: Idiom) -> bytes:
    """Return a header and rows as comma-separated text in a source's idiom.

    Parameters
    ----------
    header : sequence of str
        The real file's column names, in order.
    rows : sequence of sequences
        One value per column; None is an empty cell, a str is text, a number is bare.
    idiom : Idiom
        The real file's line ending, byte order mark and quoting.

    Returns
    -------
    bytes
        UTF-8, ending with a line ending.

    Spec: Work Order 8, B1 and B5.
    """
    lines = [",".join(_cell(name, idiom) for name in header)]
    for row in rows:
        if len(row) != len(header):
            raise ValueError(f"a row has {len(row)} cells for {len(header)} columns")
        lines.append(",".join(_cell(value, idiom) for value in row))
    text = idiom.line_ending.join(lines) + idiom.line_ending
    return (BOM if idiom.bom else "").encode("utf-8") + text.encode("utf-8")


def _cell(value: Cell, idiom: Idiom) -> str:
    if value is None or value == "":
        return ""
    if not isinstance(value, str):
        return str(value)
    needs = any(c in value for c in ',"\r\n')
    if idiom.quote_text or needs:
        return '"' + value.replace('"', '""') + '"'
    return value
