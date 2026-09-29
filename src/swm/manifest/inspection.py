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
from swm.recipe.schema import Layer
from swm.stages.layers import AttributeValue, LayersResult, Node
from swm.stages.terrain import TerrainResult

Column = tuple[NDArray[np.generic], NDArray[np.bool_] | None]
"""A typed column and its null mask (None when no row is null)."""

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
    """Write the combined nodes table, then one typed table per layer (Work Order 4, D)."""
    _write_layer(
        package, "nodes", _points(layers.nodes), _common_columns(layers.nodes), "Point",
        "Every node, with the columns all layers share. " + SYNTHETIC_NOTICE,
    )  # fmt: skip
    for layer in Layer:
        nodes = [node for node in layers.nodes if node.layer == layer]
        if not nodes:
            continue
        observed = _typed_columns([dict(node.attributes) for node in nodes])
        truth = _typed_columns([dict(node.subtype) for node in nodes])
        description = (
            f"Nodes of the {layer} layer. Columns {', '.join(observed) or 'none'} are observed "
            f"attributes; columns {', '.join(truth) or 'none'} are subtype attributes: "
            "unobserved truth, for inspection only, never emitted. " + SYNTHETIC_NOTICE
        )
        columns = {**_common_columns(nodes), **observed, **truth}
        _write_layer(package, f"nodes_{layer}", _points(nodes), columns, "Point", description)


def _points(nodes: Sequence[Node]) -> NDArray[np.object_]:
    import shapely

    return np.array([shapely.to_wkb(shapely.Point(n.x_m, n.y_m)) for n in nodes])


def _common_columns(nodes: Sequence[Node]) -> dict[str, Column]:
    return _typed_columns(
        [
            {
                "node_id": n.node_id,
                "layer": n.layer.value,
                "class": n.node_class.value,
                "city_id": n.city_id,
                "longitude": n.longitude,
                "latitude": n.latitude,
            }
            for n in nodes
        ]
    )


def _typed_columns(rows: Sequence[Mapping[str, AttributeValue]]) -> dict[str, Column]:
    """Turn rows of values into typed columns, with a null mask where a row lacks a value."""
    names = list(dict.fromkeys(name for row in rows for name in row))
    return {name: _column([row.get(name) for row in rows]) for name in names}


def _column(values: Sequence[AttributeValue | None]) -> Column:
    present = [value for value in values if value is not None]
    mask = np.array([value is None for value in values])
    if all(isinstance(value, bool) for value in present):
        data: NDArray[np.generic] = np.array([bool(v) for v in values], dtype=bool)
    elif all(isinstance(value, int) for value in present):
        data = np.array([0 if v is None else int(v) for v in values], dtype=np.int64)
    elif all(isinstance(value, int | float) for value in present):
        data = np.array([0.0 if v is None else float(v) for v in values], dtype=np.float64)
    else:
        data = np.array(["" if v is None else str(v) for v in values], dtype=object)
    return data, (mask if mask.any() else None)


def _write_links(package: Path, layers: LayersResult) -> None:
    import shapely

    geometry = np.array([shapely.to_wkb(shapely.LineString(link.points)) for link in layers.links])
    columns = _typed_columns(
        [
            {
                "link_id": link.link_id,
                "layer": link.layer.value,
                "from_id": link.from_id,
                "to_id": link.to_id,
                "length_km": link.length_km,
                "river_crossings": link.river_crossings,
                "crosses_sea": link.crosses_sea,
            }
            for link in layers.links
        ]
    )
    description = "Intra-layer links as straight or dog-leg polylines. " + SYNTHETIC_NOTICE
    _write_layer(package, "links", geometry, columns, "LineString", description)


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
    columns = {field: _column(identifiers)}
    _write_layer(package, name, geometry, columns, "Polygon", SYNTHETIC_NOTICE)


def _write_layer(
    package: Path,
    name: str,
    geometry: NDArray[np.object_],
    columns: Mapping[str, Column],
    geometry_type: str,
    description: str,
) -> None:
    from pyogrio.raw import write

    names = list(columns)
    masks = [columns[column][1] for column in names]
    write(
        str(package),
        geometry,
        [columns[column][0] for column in names],
        names,
        field_mask=masks if any(mask is not None for mask in masks) else None,
        layer=name,
        driver="GPKG",
        crs=WORKING_CRS,
        geometry_type=geometry_type,
        append=package.exists(),
        dataset_metadata=_metadata(),
        layer_metadata=_metadata(),
        layer_options={"DESCRIPTION": description},
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
