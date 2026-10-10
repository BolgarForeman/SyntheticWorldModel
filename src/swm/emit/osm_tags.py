"""OpenStreetMap tags per class, following the OpenStreetMap wiki (Work Order 8, A2).

The tag set is this module's CHOICE, reported as a table with the wiki page for each. Each
feature carries the attributes the real tags carry (scored: class, location, capacity, voltage;
context: name, operator) and no others. Names follow OpenStreetMap's short style ("Corvan
Substation"); a minor element left unnamed carries no name tag.

Spec: structure v0.10 §4.6; Work Order 8, A2 and A4; Emission ruling sheet v0.2, E2, E4, E6.
"""

from collections.abc import Mapping

from swm.emit.observed import ObservedLink, ObservedNode
from swm.recipe.schema import Layer, NodeClass

C = NodeClass
WIKI = "https://wiki.openstreetmap.org/wiki/"

CLASS_TAGS: Mapping[NodeClass, tuple[tuple[tuple[str, str], ...], str, str]] = {
    C.GENERATION: ((("power", "plant"),), "Power Station", "Tag:power=plant"),
    C.TRANSMISSION_SUBSTATION: (
        (("power", "substation"), ("substation", "transmission")),
        "Substation",
        "Tag:power=substation",
    ),
    C.DISTRIBUTION_SUBSTATION: (
        (("power", "substation"), ("substation", "distribution")),
        "Substation",
        "Tag:power=substation",
    ),
    C.EXCHANGE: ((("telecom", "exchange"),), "Telephone Exchange", "Key:telecom"),
    C.MAST: (
        (("man_made", "mast"), ("tower:type", "communication")),
        "Mast",
        "Tag:man_made=mast",
    ),
    C.DATA_CENTRE: ((("telecom", "data_center"),), "Data Centre", "Key:telecom"),
    # CHOICE: OpenStreetMap has no landing-station value; a cable landing is a connection point.
    C.CABLE_LANDING: (
        (("telecom", "connection_point"),),
        "Cable Landing Station",
        "Key:telecom",
    ),
    C.RESERVOIR: (
        (("natural", "water"), ("water", "reservoir")),
        "Reservoir",
        "Tag:water=reservoir",
    ),
    C.TREATMENT: ((("man_made", "water_works"),), "Water Works", "Tag:man_made=water_works"),
    C.PUMPING: (
        (("man_made", "pumping_station"), ("substance", "water")),
        "Pumping Station",
        "Tag:man_made=pumping_station",
    ),
    C.STORAGE: (
        (("man_made", "storage_tank"), ("content", "water")),
        "Water Tank",
        "Tag:man_made=storage_tank",
    ),
    C.AIRPORT: ((("aeroway", "aerodrome"),), "Airport", "Tag:aeroway=aerodrome"),
    # Taiwan's commercial ports are named landuse=harbour areas (the pipeline's ports check).
    C.SEAPORT: ((("landuse", "harbour"),), "Port", "Tag:landuse=harbour"),
    C.FREIGHT_YARD: (
        (("landuse", "industrial"), ("industrial", "logistics")),
        "Freight Yard",
        "Key:industrial",
    ),
    C.BRIDGE: ((("man_made", "bridge"),), "Bridge", "Tag:man_made=bridge"),
    C.RAIL_NODE: ((("railway", "station"),), "Station", "Tag:railway=station"),
    C.ROAD_JUNCTION: (
        (("highway", "motorway_junction"),),
        "Junction",
        "Tag:highway=motorway_junction",
    ),
    C.REFINERY: (
        (("landuse", "industrial"), ("industrial", "refinery")),
        "Refinery",
        "Tag:industrial=refinery",
    ),
    C.TANK_FARM: (
        (("landuse", "industrial"), ("industrial", "oil")),
        "Oil Terminal",
        "Key:industrial",
    ),
    # The product (LNG or oil) is unobserved, so the tags cannot say which.
    C.IMPORT_TERMINAL: (
        (("landuse", "industrial"), ("industrial", "oil")),
        "Fuel Terminal",
        "Key:industrial",
    ),
    C.DEPOT: ((("amenity", "fuel"), ("fuel:HGV_diesel", "yes")), "Fuel Depot", "Tag:amenity=fuel"),
    C.TERTIARY: (
        (("amenity", "hospital"), ("healthcare", "hospital")),
        "Hospital",
        "Tag:amenity=hospital",
    ),
    C.REGIONAL: (
        (("amenity", "hospital"), ("healthcare", "hospital")),
        "Hospital",
        "Tag:amenity=hospital",
    ),
    C.CLINIC: ((("amenity", "clinic"), ("healthcare", "clinic")), "Clinic", "Tag:amenity=clinic"),
    C.BLOOD_BANK: ((("healthcare", "blood_bank"),), "Blood Bank", "Key:healthcare"),
}
"""Per class: the tags, the class word in its OpenStreetMap name, and its wiki page."""

FUEL_SOURCE = {"gas": "gas", "coal": "coal", "oil": "oil", "lng": "gas", "diesel": "oil"}
"""World fuel types as OpenStreetMap ``plant:source`` values (Tag:power=plant)."""

LINK_TAGS: Mapping[Layer, tuple[tuple[str, str], ...]] = {
    Layer.POWER: (("power", "line"),),
    Layer.TELECOM: (("communication", "line"),),
    Layer.WATER: (("man_made", "pipeline"), ("substance", "water"), ("location", "underground")),
    Layer.FUEL: (("man_made", "pipeline"), ("substance", "oil"), ("location", "underground")),
    Layer.TRANSPORT: (("highway", "primary"),),
}
"""Links on emitted layers that are not nodes-only (E2). CHOICE: roads are highway=primary."""


def node_tags(node: ObservedNode) -> dict[str, str]:
    """Return a node's OpenStreetMap tags in key order.

    Parameters
    ----------
    node : ObservedNode
        The observed asset.

    Returns
    -------
    dict of str to str
        Its tags, sorted by key.

    Spec: Work Order 8, A2 and A4.
    """
    tags, word, _ = CLASS_TAGS[node.node_class]
    result = dict(tags)
    if node.named:
        result["name"] = f"{node.town} {word}"
    result |= _attribute_tags(node)
    return dict(sorted(result.items()))


def _attribute_tags(node: ObservedNode) -> dict[str, str]:
    """Return the observed attributes real tags carry: capacity, voltage, beds, operator."""
    tags: dict[str, str] = {}
    capacity = node.attribute("capacity_mw")
    if capacity is not None:
        tags["plant:output:electricity"] = f"{capacity} MW"
        tags["plant:method"] = "combustion"
    fuel = node.attribute("fuel_type")
    if isinstance(fuel, str):
        tags["plant:source"] = FUEL_SOURCE.get(fuel, fuel)
    voltage = node.attribute("voltage_kv")
    if voltage is not None:
        tags["voltage"] = str(round(float(voltage) * 1000))
    beds = node.attribute("bed_count")
    if beds is not None:
        tags["beds"] = str(beds)
    operator = node.attribute("operator")
    if isinstance(operator, str):
        tags["operator"] = operator
    return tags


PORT_PIECE_TAGS = (("industrial", "port"), ("landuse", "industrial"))
"""A port's cargo area inside its harbour outline, as Taiwan's ports are mapped (the pipeline's
ports check, 2026-10-09: named landuse=harbour areas with industrial=port pieces inside)."""
PORT_PIECE_SHARE = 0.5
"""The cargo area's sides as a share of the harbour outline's. CHOICE: half, centred."""


def link_tags(link: ObservedLink) -> dict[str, str]:
    """Return a link's OpenStreetMap tags: a line, main, pipeline or road (E2)."""
    result = dict(LINK_TAGS[link.layer])
    if link.voltage_kv is not None:
        result["voltage"] = str(link.voltage_kv * 1000)
        circuits = link.circuits or 1
        result["circuits"] = str(circuits)
        # Three-phase AC: three cables per circuit (Tag:power=line, cables).
        result["cables"] = str(3 * circuits)
    return dict(sorted(result.items()))


def tag_table() -> list[dict[str, str]]:
    """Return the tag table for the report: class, tags, name style and wiki page."""
    return [
        {
            "class": node_class.value,
            "tags": "; ".join(f"{k}={v}" for k, v in tags),
            "name": f"<Town> {word}",
            "wiki": WIKI + page,
        }
        for node_class, (tags, word, page) in CLASS_TAGS.items()
    ]
