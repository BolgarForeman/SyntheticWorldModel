"""The WRI Global Power Plant Database file of the island (Work Order 8, B2).

Generation nodes only, in the real header's columns and the real file's idiom (UTF-8, no byte
order mark, CRLF, quoted only where a value holds a comma; ``capacity_mw`` always with a decimal
point). Country ``XSW`` "Synthetic World"; ``gppd_idnr`` ``XSW0000001`` … in the order of the
world's ids; formal plant names. Columns the world has no value for stay empty, as the real
file leaves them.

Spec: structure v0.10 §4.6; Work Order 8, B2 and B5; Emission ruling sheet v0.2, E3 and E4.
"""

from dataclasses import dataclass

from swm.emit.delimited import Idiom, delimited
from swm.emit.headers import WRI_GPPD
from swm.emit.observed import ObservedNode, ObservedWorld
from swm.recipe.schema import Layer, NodeClass, Source

IDIOM = Idiom(line_ending="\r\n", bom=False, quote_text=False)
FILE = "global_power_plant_database.csv"
COUNTRY, COUNTRY_LONG = "XSW", "Synthetic World"
PRIMARY_FUEL = {"gas": "Gas", "coal": "Coal", "oil": "Oil"}
"""World fuel types as WRI's ``primary_fuel`` values."""


@dataclass(frozen=True)
class WriRecord:
    """One plant's row: its world id and ``gppd_idnr``."""

    node_id: str
    gppd_idnr: str


def wri_file(world: ObservedWorld) -> tuple[bytes, tuple[WriRecord, ...]]:
    """Return the WRI file and each row's world id.

    Parameters
    ----------
    world : ObservedWorld
        The observed world.

    Returns
    -------
    bytes
        The CSV.
    tuple of WriRecord
        One per row, in row order.

    Spec: Work Order 8, B2.
    """
    if Source.WRI_GPPD not in world.sources_of(Layer.POWER):
        return delimited(WRI_GPPD.columns, [], IDIOM), ()
    plants = [n for n in world.nodes if n.node_class == NodeClass.GENERATION]
    records = tuple(WriRecord(n.node_id, f"XSW{i:07d}") for i, n in enumerate(plants, start=1))
    rows = [_row(node, record.gppd_idnr) for node, record in zip(plants, records, strict=True)]
    return delimited(WRI_GPPD.columns, rows, IDIOM), records


def _row(node: ObservedNode, gppd_idnr: str) -> list[str | float | None]:
    values: dict[str, str | float | None] = dict.fromkeys(WRI_GPPD.columns)
    capacity = node.attribute("capacity_mw")
    fuel = node.attribute("fuel_type")
    values |= {
        "country": COUNTRY,
        "country_long": COUNTRY_LONG,
        # CHOICE: a formal name in WRI's style, the town and the kind of plant.
        "name": f"{node.town} Thermal Power Station",
        "gppd_idnr": gppd_idnr,
        "capacity_mw": None if capacity is None else f"{float(capacity):.1f}",
        "latitude": node.location[1],
        "longitude": node.location[0],
        "primary_fuel": PRIMARY_FUEL.get(str(fuel), None if fuel is None else str(fuel)),
    }
    return [values[column] for column in WRI_GPPD.columns]
