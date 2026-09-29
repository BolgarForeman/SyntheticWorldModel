"""Face-validity previews for the author's eyes. Not part of the identity check.

Needs the optional ``preview`` dependencies (matplotlib): ``uv sync --extra preview``.
"""

import io
from typing import TYPE_CHECKING

import numpy as np
from numpy.typing import NDArray

from swm.coordinates import domain_origin_m
from swm.recipe.schema import Layer, NodeClass
from swm.stages.layers import LayersResult
from swm.stages.terrain import D8_OFFSETS, CoverClass, TerrainResult

if TYPE_CHECKING:
    from matplotlib.artist import Artist
    from matplotlib.axes import Axes
    from matplotlib.figure import Figure

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
LAYER_COLOURS = {
    Layer.POWER: "#d62728",
    Layer.TELECOM: "#9467bd",
    Layer.WATER: "#1f77b4",
    Layer.TRANSPORT: "#ff7f0e",
    Layer.FUEL: "#8c564b",
    Layer.HEALTHCARE: "#e377c2",
}
CLASS_MARKERS = {
    NodeClass.GENERATION: "^",
    NodeClass.TRANSMISSION_SUBSTATION: "s",
    NodeClass.DISTRIBUTION_SUBSTATION: "o",
    NodeClass.EXCHANGE: "s",
    NodeClass.MAST: "^",
    NodeClass.DATA_CENTRE: "D",
    NodeClass.CABLE_LANDING: "v",
    NodeClass.RESERVOIR: "v",
    NodeClass.TREATMENT: "s",
    NodeClass.PUMPING: "o",
    NodeClass.STORAGE: "D",
    NodeClass.SEAPORT: "P",
    NodeClass.AIRPORT: "X",
    NodeClass.FREIGHT_YARD: "s",
    NodeClass.BRIDGE: "h",
    NodeClass.ROAD_JUNCTION: "o",
    NodeClass.IMPORT_TERMINAL: "P",
    NodeClass.TANK_FARM: "s",
    NodeClass.DEPOT: "o",
    NodeClass.REFINERY: "^",
    NodeClass.TERTIARY: "*",
    NodeClass.REGIONAL: "p",
    NodeClass.CLINIC: "o",
    NodeClass.BLOOD_BANK: "D",
}


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

    figure = Figure(figsize=(10, 9.5))
    axes = figure.add_subplot()
    legend = _draw_terrain(axes, result, title)
    axes.legend(handles=legend, loc="upper left", bbox_to_anchor=(1.02, 1.0), fontsize=8)
    figure.text(0.02, 0.02, _caption(result), fontsize=8, family="monospace", va="bottom")
    figure.subplots_adjust(bottom=0.2, right=0.8)
    return _png(figure)


def world_preview_png(terrain: TerrainResult, layers: LayersResult, title: str) -> bytes:
    """Render the terrain preview with every node and link of every layer drawn over it.

    Nodes are coloured by layer and shaped by class; the caption gives per-layer statistics.

    Parameters
    ----------
    terrain : TerrainResult
        The terrain stage's output.
    layers : LayersResult
        The layers stage's output.
    title : str
        Title printed above the map.

    Returns
    -------
    bytes
        A PNG image.

    Spec: Work Order 3, C2.
    """
    from matplotlib.collections import LineCollection
    from matplotlib.figure import Figure
    from matplotlib.lines import Line2D

    figure = Figure(figsize=(12, 10.5))
    axes = figure.add_subplot()
    terrain_legend = _draw_terrain(axes, terrain, title)
    west_m, south_m = domain_origin_m(terrain.grid)
    for layer in Layer:
        paths = [
            [((x - west_m) / 1000, (y - south_m) / 1000) for x, y in link.points]
            for link in layers.links
            if link.layer == layer
        ]
        axes.add_collection(
            LineCollection(paths, colors=[LAYER_COLOURS[layer]], linewidths=1.6, alpha=0.85)
        )
    for node in layers.nodes:
        if node.runway is not None:
            (x0, y0), (x1, y1) = node.runway
            axes.plot(
                [(x0 - west_m) / 1000, (x1 - west_m) / 1000],
                [(y0 - south_m) / 1000, (y1 - south_m) / 1000],
                color="black", linewidth=3, solid_capstyle="butt",
            )  # fmt: skip
        axes.plot(
            (node.x_m - west_m) / 1000, (node.y_m - south_m) / 1000,
            marker=CLASS_MARKERS.get(node.node_class, "o"), markersize=8,
            markerfacecolor=LAYER_COLOURS[node.layer], markeredgecolor="black", linestyle="",
        )  # fmt: skip
    layer_legend = [
        Line2D([], [], color=LAYER_COLOURS[layer], linewidth=2, label=layer.value)
        for layer in Layer
    ]
    present = sorted({node.node_class for node in layers.nodes}, key=lambda c: c.value)
    class_legend = [
        Line2D([], [], marker=CLASS_MARKERS.get(c, "o"), color="grey", markeredgecolor="black",
               linestyle="", label=c.value.replace("_", " "))
        for c in present
    ]  # fmt: skip
    first = axes.legend(
        handles=terrain_legend + layer_legend, loc="upper left", bbox_to_anchor=(1.02, 1.0),
        fontsize=8, title="cover and layers",
    )  # fmt: skip
    axes.add_artist(first)
    axes.legend(
        handles=class_legend, loc="upper left", bbox_to_anchor=(1.02, 0.45), fontsize=8,
        title="node class",
    )  # fmt: skip
    figure.text(0.02, 0.02, _layers_caption(layers), fontsize=8, family="monospace", va="bottom")
    figure.subplots_adjust(bottom=0.2, right=0.78)
    return _png(figure)


def _draw_terrain(axes: "Axes", result: TerrainResult, title: str) -> list["Artist"]:
    """Draw the shaded ground, rivers, city outlines and scale bar; return legend entries."""
    from matplotlib.collections import LineCollection
    from matplotlib.lines import Line2D
    from matplotlib.patches import Patch

    side_km = result.grid.cells * result.grid.cell_size_m / 1000
    axes.imshow(_shaded_cover(result), extent=(0, side_km, 0, side_km), interpolation="nearest")
    # Rivers are drawn as lines above the cover, each reach joined to its downstream cell.
    axes.add_collection(
        LineCollection(_river_segments(result, side_km), colors=[RIVER_COLOUR], linewidths=1.1)
    )
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
    legend: list[Artist] = [Patch(color=COVER_COLOURS[c], label=c.name.lower()) for c in CoverClass]
    legend.append(Line2D([], [], color=RIVER_COLOUR, label="river"))
    return legend


def _png(figure: "Figure") -> bytes:
    buffer = io.BytesIO()
    figure.savefig(buffer, format="png", dpi=PREVIEW_DPI)
    return buffer.getvalue()


def _layers_caption(layers: LayersResult) -> str:
    lines = [
        f"{s.layer.value:<11} {sum(s.class_counts.values()):>3} nodes  {s.link_count:>3} links  "
        f"{s.mean_links_per_node:.2f} links/node  spacing {s.mean_spacing_km:.2f} km  "
        f"notes {len(s.notes)}"
        for s in layers.statistics
    ]
    return "\n".join(lines)


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
    return shaded


def _river_segments(result: TerrainResult, side_km: float) -> list[list[tuple[float, float]]]:
    cell_km = result.grid.cell_size_m / 1000
    segments = []
    for row, column in zip(*np.nonzero(result.river), strict=True):
        dr, dc = D8_OFFSETS[int(result.flow_direction[row, column])]
        start = ((column + 0.5) * cell_km, side_km - (row + 0.5) * cell_km)
        end = ((column + dc + 0.5) * cell_km, side_km - (row + dr + 0.5) * cell_km)
        segments.append([start, end])
    return segments


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
