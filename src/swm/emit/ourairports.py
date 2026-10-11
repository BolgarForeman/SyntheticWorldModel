"""The OurAirports file of the island (Work Order 8, B3).

Airports only, in the real header's columns and the real file's idiom (UTF-8, LF, every
non-empty text value quoted, numbers bare). ``ident`` ``XS-0001`` … (OurAirports' own form for
an airfield with no ICAO code); no ICAO, IATA, GPS or local codes; ``iso_country`` ``XS`` and
``iso_region`` the airport's district, ``XS-01`` ….

Spec: structure v0.11 §4.6; Work Order 8, B3 and B5; Emission ruling sheet v0.2, E3.
"""

from dataclasses import dataclass

from swm.emit.delimited import Idiom, delimited
from swm.emit.headers import OURAIRPORTS
from swm.emit.observed import ObservedNode, ObservedWorld
from swm.recipe.schema import Layer, NodeClass, Source

IDIOM = Idiom(line_ending="\n", bom=False, quote_text=True)
FILE = "airports.csv"
DECIMALS = OURAIRPORTS.coordinate_decimals
"""The real file's precision (§4.1a): written as the shortest float, trailing zeros dropped, as
the real file writes them."""
CONTINENT = "OC"
"""CHOICE: the world sits at Point Nemo, in the South Pacific: Oceania."""
SCHEDULED = {"small_airport": "no", "medium_airport": "yes", "large_airport": "yes"}
"""CHOICE: scheduled service follows the airport's observed size class, as OurAirports' types
largely do; the world carries no separate schedule."""


@dataclass(frozen=True)
class AirportRecord:
    """One airport's row: its world id, numeric id and ident."""

    node_id: str
    row_id: int
    ident: str


def ourairports_file(world: ObservedWorld) -> tuple[bytes, tuple[AirportRecord, ...]]:
    """Return the OurAirports file and each row's world id.

    Parameters
    ----------
    world : ObservedWorld
        The observed world.

    Returns
    -------
    bytes
        The CSV.
    tuple of AirportRecord
        One per row, in row order.

    Spec: Work Order 8, B3.
    """
    if Source.OURAIRPORTS not in world.sources_of(Layer.TRANSPORT):
        return delimited(OURAIRPORTS.columns, [], IDIOM), ()
    airports = [n for n in world.nodes if n.node_class == NodeClass.AIRPORT]
    records = tuple(
        AirportRecord(n.node_id, i, f"XS-{i:04d}") for i, n in enumerate(airports, start=1)
    )
    rows = [_row(node, record) for node, record in zip(airports, records, strict=True)]
    return delimited(OURAIRPORTS.columns, rows, IDIOM), records


def _row(node: ObservedNode, record: AirportRecord) -> list[str | int | float | None]:
    # CHOICE: the type is the airport's observed size class, already in OurAirports' terms;
    # the tower that would also suggest it is unobserved.
    kind = str(node.attribute("size_class") or "small_airport")
    values: dict[str, str | int | float | None] = dict.fromkeys(OURAIRPORTS.columns)
    values |= {
        "id": record.row_id,
        "ident": record.ident,
        "type": kind,
        "name": node.name("Airport"),
        # Numbers are bare in the real file; coordinates are WGS 84 at 7 decimals (§4.1a).
        "latitude_deg": round(node.location[1], DECIMALS),
        "longitude_deg": round(node.location[0], DECIMALS),
        "continent": CONTINENT,
        "iso_country": "XS",
        "iso_region": node.district,
        "municipality": node.town,
        "scheduled_service": SCHEDULED.get(kind, "no"),
    }
    return [values[column] for column in OURAIRPORTS.columns]
