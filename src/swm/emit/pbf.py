"""A small OpenStreetMap PBF writer with uncompressed blobs (Work Order 8, A5).

The PBF format allows a blob's data to be stored raw. zlib's output can differ between zlib
builds, so every blob here is raw, and the file is identical on every platform (a declared
departure from Geofabrik's compressed extracts). The file holds one header block, one block of
dense nodes and one block of ways, each sorted by id (``Sort.Type_then_ID``); coordinates in
units of 100 nanodegrees; one fixed timestamp, user and changeset.

Format: https://wiki.openstreetmap.org/wiki/PBF_Format (fileformat.proto, osmformat.proto).

Spec: Work Order 8, A1 and A5; Emission ruling sheet v0.2, E1.
"""

import struct
from collections.abc import Iterable, Sequence

from swm.emit.osm_model import CHANGESET, TIMESTAMP_S, UID, USER, OsmData, OsmNode, OsmWay

NANO = 1_000_000_000
GRANULARITY = 100
"""Nanodegrees per coordinate unit (the format's default)."""
WRITING_PROGRAM = "swm"


def pbf_bytes(data: OsmData) -> bytes:
    """Return the island as an OpenStreetMap PBF file.

    Parameters
    ----------
    data : OsmData
        The island's nodes and ways.

    Returns
    -------
    bytes
        The file: a header blob, then a node blob and a way blob, all stored raw.

    Spec: Work Order 8, A1 and A5.
    """
    blobs = [("OSMHeader", _header(data))]
    if data.nodes:
        blobs.append(("OSMData", _block(data, nodes=data.nodes)))
    if data.ways:
        blobs.append(("OSMData", _block(data, ways=data.ways)))
    return b"".join(_framed(kind, payload) for kind, payload in blobs)


# --- Protocol buffer encoding ---------------------------------------------------------------


def _varint(value: int) -> bytes:
    out = bytearray()
    while True:
        byte = value & 0x7F
        value >>= 7
        if value:
            out.append(byte | 0x80)
        else:
            out.append(byte)
            return bytes(out)


def _zigzag(value: int) -> int:
    return (value << 1) ^ (value >> 63)


def _key(number: int, wire: int) -> bytes:
    return _varint(number << 3 | wire)


def _int(number: int, value: int) -> bytes:
    return _key(number, 0) + _varint(value)


def _sint(number: int, value: int) -> bytes:
    return _key(number, 0) + _varint(_zigzag(value))


def _bytes(number: int, value: bytes) -> bytes:
    return _key(number, 2) + _varint(len(value)) + value


def _packed(number: int, values: Iterable[int], signed: bool) -> bytes:
    body = b"".join(_varint(_zigzag(v) if signed else v) for v in values)
    return _bytes(number, body)


def _deltas(values: Sequence[int]) -> list[int]:
    previous, result = 0, []
    for value in values:
        result.append(value - previous)
        previous = value
    return result


def _framed(kind: str, payload: bytes) -> bytes:
    blob = _bytes(1, payload) + _int(2, len(payload))
    header = _bytes(1, kind.encode("ascii")) + _int(3, len(blob))
    return struct.pack(">I", len(header)) + header + blob


# --- Blocks ---------------------------------------------------------------------------------


def _units(degrees: float) -> int:
    """Degrees (7 decimals) in units of 100 nanodegrees, exactly."""
    return round(degrees * 10_000_000)


def _header(data: OsmData) -> bytes:
    west, south, east, north = data.bounds()
    bbox = (
        _sint(1, _units(west) * GRANULARITY)
        + _sint(2, _units(east) * GRANULARITY)
        + _sint(3, _units(north) * GRANULARITY)
        + _sint(4, _units(south) * GRANULARITY)
    )
    return (
        _bytes(1, bbox)
        + _bytes(4, b"OsmSchema-V0.6")
        + _bytes(4, b"DenseNodes")
        + _bytes(5, b"Sort.Type_then_ID")
        + _bytes(16, WRITING_PROGRAM.encode("ascii"))
    )


class _Strings:
    """A block's string table: index 0 is the empty string, then strings in first use."""

    def __init__(self) -> None:
        self.table: list[str] = [""]
        self.index: dict[str, int] = {"": 0}

    def of(self, text: str) -> int:
        if text not in self.index:
            self.index[text] = len(self.table)
            self.table.append(text)
        return self.index[text]

    def encoded(self) -> bytes:
        return b"".join(_bytes(1, s.encode("utf-8")) for s in self.table)


def _block(data: OsmData, nodes: Sequence[OsmNode] = (), ways: Sequence[OsmWay] = ()) -> bytes:
    strings = _Strings()
    user = strings.of(USER)
    group = (
        _dense(nodes, strings, user)
        if nodes
        else b"".join(_bytes(3, _way(way, strings, user)) for way in ways)
    )
    return _bytes(1, strings.encoded()) + _bytes(2, group) + _int(17, GRANULARITY) + _int(18, 1000)


def _dense(nodes: Sequence[OsmNode], strings: _Strings, user: int) -> bytes:
    keys_vals: list[int] = []
    for node in nodes:
        for key, value in node.tags:
            keys_vals += [strings.of(key), strings.of(value)]
        keys_vals.append(0)
    count = len(nodes)
    info = (
        _packed(1, [1] * count, signed=False)
        + _packed(2, _deltas([TIMESTAMP_S] * count), signed=True)
        + _packed(3, _deltas([CHANGESET] * count), signed=True)
        + _packed(4, _deltas([UID] * count), signed=True)
        + _packed(5, _deltas([user] * count), signed=True)
    )
    body = (
        _packed(1, _deltas([n.osm_id for n in nodes]), signed=True)
        + _bytes(5, info)
        + _packed(8, _deltas([_units(n.location[1]) for n in nodes]), signed=True)
        + _packed(9, _deltas([_units(n.location[0]) for n in nodes]), signed=True)
        + _packed(10, keys_vals, signed=False)
    )
    return _bytes(2, body)


def _way(way: OsmWay, strings: _Strings, user: int) -> bytes:
    info = _int(1, 1) + _int(2, TIMESTAMP_S) + _int(3, CHANGESET) + _int(4, UID) + _int(5, user)
    return (
        _int(1, way.osm_id)
        + _packed(2, [strings.of(k) for k, _ in way.tags], signed=False)
        + _packed(3, [strings.of(v) for _, v in way.tags], signed=False)
        + _bytes(4, info)
        + _packed(8, _deltas(list(way.refs)), signed=True)
    )
