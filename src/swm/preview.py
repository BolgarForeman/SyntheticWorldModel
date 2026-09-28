"""Face-validity previews for the author's eyes. Not part of the identity check.

Needs the optional ``preview`` dependencies (matplotlib): ``uv sync --extra preview``.
"""

import io
from typing import TYPE_CHECKING

import numpy as np
from numpy.typing import NDArray

from swm.stages.terrain import CoverClass, TerrainResult

if TYPE_CHECKING:
    from matplotlib.axes import Axes

COVER_COLOURS = {
    CoverClass.SEA: (0.72, 0.83, 0.89),
    CoverClass.OPEN: (0.84, 0.82, 0.62),
    CoverClass.URBAN: (0.55, 0.52, 0.52),
    CoverClass.FOREST: (0.33, 0.52, 0.33),
    CoverClass.WETLAND: (0.55, 0.70, 0.62),
    CoverClass.BARREN: (0.70, 0.62, 0.52),
}
RIVER_COLOUR = (0.12, 0.35, 0.75)
PREVIEW_DPI = 150


def terrain_preview_png(result: TerrainResult, title: str) -> bytes:
    """Render a shaded map of the ground as PNG bytes.

    Shows sea, relief shading, land cover, rivers, city outlines, a scale bar and the realised
    statistics.

    Parameters
    ----------
    result : TerrainResult
        The terrain stage's output.
    title : str
        Title printed above the map.

    Returns
    -------
    bytes
        A PNG image.

    Spec: Work Order 2, A10.
    """
    from matplotlib.figure import Figure
    from matplotlib.patches import Patch

    side_km = result.grid.cells * result.grid.cell_size_m / 1000
    figure = Figure(figsize=(8, 9.5))
    axes = figure.add_subplot()
    axes.imshow(_shaded_cover(result), extent=(0, side_km, 0, side_km), interpolation="nearest")
    for city in result.cities:
        footprint = np.where(result.urban_id == city.city_id, 1.0, 0.0)
        axes.contour(
            footprint, levels=[0.5], colors="black", linewidths=0.8, extent=(0, side_km, side_km, 0)
        )
    west, east, south, north = _land_window(result, side_km)
    axes.set_xlim(west, east)
    axes.set_ylim(south, north)
    axes.set_xlabel("km east of the domain origin")
    axes.set_ylabel("km north of the domain origin")
    axes.set_title(title)
    _scale_bar(axes, west, east, south, north)
    legend = [Patch(color=COVER_COLOURS[c], label=c.name.lower()) for c in CoverClass]
    legend.append(Patch(color=RIVER_COLOUR, label="river"))
    axes.legend(handles=legend, loc="upper right", fontsize=8)
    figure.text(0.02, 0.02, _caption(result), fontsize=8, family="monospace", va="bottom")
    figure.subplots_adjust(bottom=0.2)
    buffer = io.BytesIO()
    figure.savefig(buffer, format="png", dpi=PREVIEW_DPI)
    return buffer.getvalue()


def _shaded_cover(result: TerrainResult) -> NDArray[np.float64]:
    colours = np.zeros((*result.land_cover.shape, 3))
    for cover, rgb in COVER_COLOURS.items():
        colours[result.land_cover == cover] = rgb
    elevation = result.elevation_dm / 10
    gradient_y, gradient_x = np.gradient(elevation, result.grid.cell_size_m)
    # Light from the north-west; preview only, so ordinary floating point is fine here.
    shade = np.clip(1.0 - 0.8 * (gradient_x - gradient_y), 0.55, 1.15)
    shaded: NDArray[np.float64] = np.clip(
        colours * np.where(result.land, shade, 1.0)[..., None], 0.0, 1.0
    )
    shaded[result.river] = RIVER_COLOUR
    return shaded


def _land_window(result: TerrainResult, side_km: float) -> tuple[float, float, float, float]:
    rows, columns = np.nonzero(result.land)
    cell_km = result.grid.cell_size_m / 1000
    margin = 6
    west = max(0, int(columns.min()) - margin) * cell_km
    east = min(result.grid.cells, int(columns.max()) + 1 + margin) * cell_km
    north = side_km - max(0, int(rows.min()) - margin) * cell_km
    south = side_km - min(result.grid.cells, int(rows.max()) + 1 + margin) * cell_km
    return west, east, south, north


def _scale_bar(axes: "Axes", west: float, east: float, south: float, north: float) -> None:
    length_km = _round_length((east - west) / 5)
    x0, y0 = west + (east - west) * 0.05, south + (north - south) * 0.04
    axes.plot([x0, x0 + length_km], [y0, y0], color="black", linewidth=3)
    axes.text(x0, y0 + (north - south) * 0.015, f"{length_km:g} km", fontsize=9)


def _round_length(approximate_km: float) -> float:
    magnitude = 10.0 ** np.floor(np.log10(approximate_km))
    for step in (1, 2, 5, 10):
        if approximate_km <= step * magnitude:
            return float(step * magnitude)
    return float(10 * magnitude)


def _caption(result: TerrainResult) -> str:
    stats = result.statistics
    shares = ", ".join(f"{name} {share:.1%}" for name, share in stats.cover_shares.items())
    return (
        f"land {stats.land_area_km2:g} km²   max elevation {stats.max_elevation_m:g} m   "
        f"rivers {stats.river_length_km:g} km\n"
        f"islands {stats.island_count}   cities {stats.city_count}   "
        f"cell {result.grid.cell_size_m:.1f} m, grid {result.grid.cells} x {result.grid.cells}\n"
        f"cover: {shares}"
    )
