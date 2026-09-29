"""Inspection export: the true world as a GeoPackage and GeoTIFFs, for ArcGIS, QGIS and PostGIS.

Needs the optional ``export`` dependencies (pyogrio, shapely, rasterio): ``uv sync --extra
export``. These files sit outside the identity check, because their containers embed timestamps
and database internals (structure v0.4 §4.1a).
"""

import os
from collections.abc import Mapping, Sequence
from pathlib import Path

import numpy as np
from numpy.typing import NDArray

from swm.coordinates import WORKING_CRS, domain_origin_m
from swm.stages.layers import LayersResult
from swm.stages.terrain import TerrainResult

GEODATA_VARIABLES = ("PROJ_LIB", "PROJ_DATA", "GDAL_DATA", "GDAL_DRIVER_PATH")
"""Environment variables that point GDAL and PROJ at another installation's data."""

# rasterio and pyogrio ship their own PROJ and GDAL data. A machine-wide variable pointing at
# another installation gives them a database of the wrong version, so this process drops them
# before either library loads. The machine's own settings are untouched.
for _variable in GEODATA_VARIABLES:
    os.environ.pop(_variable, None)

SYNTHETIC_NOTICE = "SYNTHETIC — not a real place; anchored at Point Nemo"
"""Written into every exported file's metadata (Work Order 3, C1)."""

GEOPACKAGE_FILE = "world.gpkg"
RASTER_FILES = {
    "elevation": "elevation_m.tif",
    "land_cover": "land_cover.tif",
    "rivers": "rivers.tif",
}


def export_gis(terrain: TerrainResult, layers: LayersResult, out_dir: Path) -> list[Path]:
    """Write world.gpkg (nodes, links, cities, coastline) and three GeoTIFFs in EPSG:32710.

    Parameters
    ----------
    terrain : TerrainResult
        The terrain stage's output.
    layers : LayersResult
        The layers stage's output.
    out_dir : Path
        The folder to write into; created if absent.

    Returns
    -------
    list of Path
        The files written.

    Spec: structure v0.4 §4.1a (inspection export); Work Order 3, C1.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    package = out_dir / GEOPACKAGE_FILE
    if package.exists():
        package.unlink()
    _write_nodes(package, layers)
    _write_links(package, layers)
    _write_polygons(
        package, "cities", terrain, (np.asarray(terrain.urban_id) + 1).astype(np.int32), "city_id"
    )
    _write_polygons(
        package, "coastline", terrain, np.asarray(terrain.land).astype(np.int32), "land"
    )
    written = [package]
    rasters: dict[str, NDArray[np.generic]] = {
        "elevation": (np.asarray(terrain.elevation_dm) / 10).astype(np.float32),
        "land_cover": np.asarray(terrain.land_cover).astype(np.uint8),
        "rivers": np.asarray(terrain.river).astype(np.uint8),
    }
    for name, array in rasters.items():
        path = out_dir / RASTER_FILES[name]
        _write_raster(path, array, terrain, name)
        written.append(path)
    return written


def _metadata() -> dict[str, str]:
    return {"DESCRIPTION": SYNTHETIC_NOTICE, "NOTICE": SYNTHETIC_NOTICE}


def _write_nodes(package: Path, layers: LayersResult) -> None:
    import shapely

    geometry = np.array([shapely.to_wkb(shapely.Point(n.x_m, n.y_m)) for n in layers.nodes])
    attributes = [dict(n.attributes) for n in layers.nodes]
    fields: dict[str, Sequence[object]] = {
        "node_id": [n.node_id for n in layers.nodes],
        "layer": [n.layer.value for n in layers.nodes],
        "class": [n.node_class.value for n in layers.nodes],
        "city_id": [n.city_id for n in layers.nodes],
        "longitude": [n.longitude for n in layers.nodes],
        "latitude": [n.latitude for n in layers.nodes],
        "attributes": [
            "; ".join(f"{key}={value}" for key, value in row.items()) for row in attributes
        ],
    }
    _write_layer(package, "nodes", geometry, fields, "Point")


def _write_links(package: Path, layers: LayersResult) -> None:
    import shapely

    geometry = np.array([shapely.to_wkb(shapely.LineString(link.points)) for link in layers.links])
    fields: dict[str, Sequence[object]] = {
        "link_id": [link.link_id for link in layers.links],
        "layer": [link.layer.value for link in layers.links],
        "from_id": [link.from_id for link in layers.links],
        "to_id": [link.to_id for link in layers.links],
        "length_km": [link.length_km for link in layers.links],
        "river_crossings": [link.river_crossings for link in layers.links],
        "crosses_sea": [int(link.crosses_sea) for link in layers.links],
    }
    _write_layer(package, "links", geometry, fields, "LineString")


def _write_polygons(
    package: Path, name: str, terrain: TerrainResult, values: NDArray[np.int32], field: str
) -> None:
    import shapely
    from rasterio.features import shapes

    transform = _transform(terrain)
    pieces = [
        (shapely.geometry.shape(geometry), int(value))
        for geometry, value in shapes(values.astype(np.int32), mask=values > 0, transform=transform)
    ]
    geometry = np.array([shapely.to_wkb(polygon) for polygon, _ in pieces])
    identifiers = [value - 1 if field == "city_id" else value for _, value in pieces]
    _write_layer(package, name, geometry, {field: identifiers}, "Polygon")


def _write_layer(
    package: Path,
    name: str,
    geometry: NDArray[np.object_],
    fields: Mapping[str, Sequence[object]],
    geometry_type: str,
) -> None:
    from pyogrio.raw import write

    columns = list(fields)
    write(
        str(package),
        geometry,
        [np.array(fields[column]) for column in columns],
        columns,
        layer=name,
        driver="GPKG",
        crs=WORKING_CRS,
        geometry_type=geometry_type,
        append=package.exists(),
        dataset_metadata=_metadata(),
        layer_metadata=_metadata(),
    )


def _transform(terrain: TerrainResult) -> object:
    from rasterio.transform import from_origin

    west_m, south_m = domain_origin_m(terrain.grid)
    side_m = terrain.grid.cells * terrain.grid.cell_size_m
    return from_origin(west_m, south_m + side_m, terrain.grid.cell_size_m, terrain.grid.cell_size_m)


def _write_raster(
    path: Path, array: NDArray[np.generic], terrain: TerrainResult, name: str
) -> None:
    import rasterio

    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        height=array.shape[0],
        width=array.shape[1],
        count=1,
        dtype=array.dtype,
        crs=WORKING_CRS,
        transform=_transform(terrain),
    ) as raster:
        raster.write(array, 1)
        raster.update_tags(**_metadata(), LAYER=name)
