"""Every source file of a world, and which record in each is which true element (§4.6).

One writer per real source format; this module only gathers their files under ``sources/`` and
keeps each writer's records, from which the truth manifest builds the cross-source
correspondence. It is given the observed world and nothing else (CLAUDE.md §3).

Spec: structure v0.11 §4.6; Work Order 8, Parts A-B and E1.
"""

from dataclasses import dataclass

from swm.emit.geofabrik import GeofabrikRecord, geofabrik_files
from swm.emit.observed import ObservedWorld
from swm.emit.osm_model import OsmData, osm_data
from swm.emit.osm_xml import osm_xml_bytes
from swm.emit.ourairports import FILE as AIRPORTS_FILE
from swm.emit.ourairports import AirportRecord, ourairports_file
from swm.emit.overpass import OverpassRecord, overpass_files
from swm.emit.pbf import pbf_bytes
from swm.emit.register import RegisterRecord, register_files
from swm.emit.wri import FILE as WRI_FILE
from swm.emit.wri import WriRecord, wri_file
from swm.recipe.schema import Layer, Source

OSM_DIR = "sources/osm"
GEOFABRIK_DIR = f"{OSM_DIR}/geofabrik_island-260101-free"
"""Named as Geofabrik names a free set: region, the extract's date (the fixed timestamp), free."""
OVERPASS_DIR = f"{OSM_DIR}/overpass"


@dataclass(frozen=True)
class EmittedSources:
    """A world's source files by path, and each writer's records."""

    files: dict[str, bytes]
    osm: OsmData
    geofabrik: tuple[GeofabrikRecord, ...]
    overpass: tuple[OverpassRecord, ...]
    wri: tuple[WriRecord, ...]
    airports: tuple[AirportRecord, ...]
    register: tuple[RegisterRecord, ...]


def emit_sources(world: ObservedWorld) -> EmittedSources:
    """Write every switched-on source of the observed world.

    Parameters
    ----------
    world : ObservedWorld
        What the sources may carry.

    Returns
    -------
    EmittedSources
        The files under ``sources/``, sorted by path, and each writer's records.

    Spec: structure v0.11 §4.6; Work Order 8, E1.
    """
    files: dict[str, bytes] = {}
    data = osm_data(world)
    geofabrik: tuple[GeofabrikRecord, ...] = ()
    overpass: tuple[OverpassRecord, ...] = ()
    if data.nodes:
        files[f"{OSM_DIR}/island.osm.pbf"] = pbf_bytes(data)
        files[f"{OSM_DIR}/island.osm"] = osm_xml_bytes(data)
        shapefiles, geofabrik = geofabrik_files(data)
        files |= {f"{GEOFABRIK_DIR}/{name}": body for name, body in shapefiles.items()}
        responses, overpass = overpass_files(data)
        files |= {f"{OVERPASS_DIR}/{name}": body for name, body in responses.items()}
    wri: tuple[WriRecord, ...] = ()
    if Source.WRI_GPPD in world.sources_of(Layer.POWER):
        body, wri = wri_file(world)
        files[f"sources/wri_gppd/{WRI_FILE}"] = body
    airports: tuple[AirportRecord, ...] = ()
    if Source.OURAIRPORTS in world.sources_of(Layer.TRANSPORT):
        body, airports = ourairports_file(world)
        files[f"sources/ourairports/{AIRPORTS_FILE}"] = body
    register_bytes, register = register_files(world)
    files |= {f"sources/facility_register/{name}": b for name, b in register_bytes.items()}
    return EmittedSources(dict(sorted(files.items())), data, geofabrik, overpass, wri, airports,
                          register)  # fmt: skip
