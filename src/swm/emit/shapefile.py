"""A small ESRI shapefile writer: points, polylines and polygons with a dBASE III table.

Written so the bytes are the same on every platform: the ``.dbf`` header's date is fixed, the
records are in the order given, and numbers are formatted by rule. The layout follows the ESRI
Shapefile Technical Description (1998) and dBASE III as Geofabrik writes it (version 0x03, no
language driver, field terminator 0x0D, end of file 0x1A).

Spec: Work Order 8 answers, 2 (fix the ``.dbf`` header date for byte identity).
"""

import struct
from collections.abc import Sequence
from dataclasses import dataclass

POINT, POLYLINE, POLYGON = 1, 3, 5
DBF_DATE = (126, 1, 1)
"""The ``.dbf`` header date, fixed at 2026-01-01 (years since 1900, month, day)."""

LonLat = tuple[float, float]


@dataclass(frozen=True)
class Field:
    """A dBASE field: name (up to 10 characters), type C or N, length and decimals."""

    name: str
    kind: str
    length: int
    decimals: int = 0


@dataclass(frozen=True)
class Shape:
    """One record's geometry: a point, or the parts of a polyline or polygon."""

    parts: tuple[tuple[LonLat, ...], ...]


def shapefile(
    shape_type: int, fields: Sequence[Field], records: Sequence[tuple[Shape, Sequence[object]]]
) -> dict[str, bytes]:
    """Return a shapefile's ``.shp``, ``.shx`` and ``.dbf`` bytes.

    Parameters
    ----------
    shape_type : int
        1 (point), 3 (polyline) or 5 (polygon).
    fields : sequence of Field
        The table's fields, in order.
    records : sequence of (Shape, values)
        Each record's geometry and field values, in order.

    Returns
    -------
    dict of str to bytes
        ``{"shp": ..., "shx": ..., "dbf": ...}``.

    Spec: Work Order 8, answer 2.
    """
    contents = [_content(shape_type, shape) for shape, _ in records]
    box = _box([p for shape, _ in records for part in shape.parts for p in part])
    shp_body, shx_body, offset = b"", b"", 50
    for number, content in enumerate(contents, start=1):
        shp_body += struct.pack(">ii", number, len(content) // 2) + content
        shx_body += struct.pack(">ii", offset, len(content) // 2)
        offset += 4 + len(content) // 2
    return {
        "shp": _header(shape_type, 50 + len(shp_body) // 2, box) + shp_body,
        "shx": _header(shape_type, 50 + len(shx_body) // 2, box) + shx_body,
        "dbf": _dbf(fields, [values for _, values in records]),
    }


def _header(shape_type: int, length_words: int, box: tuple[float, float, float, float]) -> bytes:
    return (
        struct.pack(">i", 9994)
        + b"\x00" * 20
        + struct.pack(">i", length_words)
        + struct.pack("<ii", 1000, shape_type)
        + struct.pack("<4d", *box)
        + struct.pack("<4d", 0.0, 0.0, 0.0, 0.0)
    )


def _box(points: Sequence[LonLat]) -> tuple[float, float, float, float]:
    if not points:
        return (0.0, 0.0, 0.0, 0.0)
    xs, ys = [p[0] for p in points], [p[1] for p in points]
    return (min(xs), min(ys), max(xs), max(ys))


def _content(shape_type: int, shape: Shape) -> bytes:
    if shape_type == POINT:
        x, y = shape.parts[0][0]
        return struct.pack("<idd", POINT, x, y)
    points = [p for part in shape.parts for p in part]
    starts, total = [], 0
    for part in shape.parts:
        starts.append(total)
        total += len(part)
    return (
        struct.pack("<i", shape_type)
        + struct.pack("<4d", *_box(points))
        + struct.pack("<ii", len(shape.parts), len(points))
        + struct.pack(f"<{len(starts)}i", *starts)
        + b"".join(struct.pack("<dd", x, y) for x, y in points)
    )


def _dbf(fields: Sequence[Field], rows: Sequence[Sequence[object]]) -> bytes:
    record_length = 1 + sum(f.length for f in fields)
    header_length = 32 + 32 * len(fields) + 1
    head = struct.pack("<B3BIHH20x", 0x03, *DBF_DATE, len(rows), header_length, record_length)
    descriptors = b"".join(
        f.name.encode("ascii").ljust(11, b"\x00")
        + f.kind.encode("ascii")
        + b"\x00" * 4
        + bytes([f.length, f.decimals])
        + b"\x00" * 14
        for f in fields
    )
    body = b"".join(
        b" " + b"".join(_cell(f, value) for f, value in zip(fields, row, strict=True))
        for row in rows
    )
    return head + descriptors + b"\x0d" + body + b"\x1a"


def _cell(field: Field, value: object) -> bytes:
    """Left-justify text and right-justify numbers, blank-padded, as Geofabrik writes them."""
    if field.kind == "N":
        text = "" if value is None else f"{value:.{field.decimals}f}"
        encoded = text.encode("ascii").rjust(field.length, b" ")
    else:
        encoded = ("" if value is None else str(value)).encode("utf-8").ljust(field.length, b" ")
    if len(encoded) > field.length:
        raise ValueError(f"{field.name}: {value!r} is wider than {field.length} bytes")
    return encoded
