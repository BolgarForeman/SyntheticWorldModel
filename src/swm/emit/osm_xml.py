"""The island's OpenStreetMap features as ``.osm`` XML, for reading by eye (E1).

Spec: Work Order 8, A1; Emission ruling sheet v0.2, E1.
"""

from xml.sax.saxutils import quoteattr

from swm.emit.osm_model import CHANGESET, TIMESTAMP, UID, USER, OsmData


def osm_xml_bytes(data: OsmData) -> bytes:
    """Return the island as OpenStreetMap XML (API 0.6), nodes then ways, each sorted by id.

    Parameters
    ----------
    data : OsmData
        The island's nodes and ways.

    Returns
    -------
    bytes
        UTF-8 XML with LF line endings.

    Spec: Work Order 8, A1.
    """
    west, south, east, north = data.bounds()
    meta = f'version="1" timestamp="{TIMESTAMP}" uid="{UID}" user="{USER}" changeset="{CHANGESET}"'
    lines = [
        "<?xml version='1.0' encoding='UTF-8'?>",
        '<osm version="0.6" generator="swm">',
        f'  <bounds minlat="{south:.7f}" minlon="{west:.7f}" maxlat="{north:.7f}" '
        f'maxlon="{east:.7f}"/>',
    ]
    for node in data.nodes:
        head = (
            f'  <node id="{node.osm_id}" {meta} lat="{node.location[1]:.7f}" '
            f'lon="{node.location[0]:.7f}"'
        )
        if not node.tags:
            lines.append(head + "/>")
            continue
        lines.append(head + ">")
        lines += [f"    <tag k={quoteattr(k)} v={quoteattr(v)}/>" for k, v in node.tags]
        lines.append("  </node>")
    for way in data.ways:
        lines.append(f'  <way id="{way.osm_id}" {meta}>')
        lines += [f'    <nd ref="{ref}"/>' for ref in way.refs]
        lines += [f"    <tag k={quoteattr(k)} v={quoteattr(v)}/>" for k, v in way.tags]
        lines.append("  </way>")
    lines.append("</osm>")
    return ("\n".join(lines) + "\n").encode("utf-8")
