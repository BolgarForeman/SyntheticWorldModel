"""Face-validity previews for the author's eyes. Not part of the identity check.

Needs the optional ``preview`` dependencies (matplotlib): ``uv sync --extra preview``.
"""

import io
from typing import TYPE_CHECKING

import numpy as np
from numpy.typing import NDArray

from swm import rng
from swm.coordinates import domain_origin_m
from swm.recipe.dependencies import Role
from swm.recipe.schema import Layer, NodeClass
from swm.stages import couplings as couplings_stage
from swm.stages.couplings import CouplingEdge, CouplingsResult, FeedConfiguration
from swm.stages.layers import LayersResult
from swm.stages.terrain import D8_OFFSETS, CoverClass, TerrainResult

if TYPE_CHECKING:
    from matplotlib.artist import Artist
    from matplotlib.axes import Axes
    from matplotlib.figure import Figure

    from swm.stages.storm import StormResult

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
LABEL_BACKGROUND = {"facecolor": "white", "alpha": 0.85, "edgecolor": "none", "pad": 1.5}
"""Schematic node labels sit on the page colour, nearly opaque, above the arrows."""
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


def world_preview_png(
    terrain: TerrainResult,
    layers: LayersResult,
    title: str,
    couplings: CouplingsResult | None = None,
) -> bytes:
    """Render the terrain preview with every node and link of every layer drawn over it.

    Nodes are coloured by layer and shaped by class; the caption gives per-layer statistics.
    Coupling edges, when given, are thin straight lines coloured by supplier layer; those of
    switched-off pairs are faint and dotted.

    Parameters
    ----------
    terrain : TerrainResult
        The terrain stage's output.
    layers : LayersResult
        The layers stage's output.
    title : str
        Title printed above the map.
    couplings : CouplingsResult or None
        The couplings stage's output, or None to leave coupling edges off.

    Returns
    -------
    bytes
        A PNG image.

    Spec: Work Order 3, C2; Work Order 4, F4.
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
    for edge in couplings.edges if couplings is not None else ():
        (x0, y0), (x1, y1) = edge.points
        axes.plot(
            [(x0 - west_m) / 1000, (x1 - west_m) / 1000],
            [(y0 - south_m) / 1000, (y1 - south_m) / 1000],
            color=LAYER_COLOURS[edge.supplier_layer], linewidth=0.6 if edge.switched_on else 0.4,
            alpha=0.8 if edge.switched_on else 0.3, linestyle="-" if edge.switched_on else ":",
        )  # fmt: skip
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
    caption = _layers_caption(layers)
    if couplings is not None:
        hidden = len(couplings.edges) - couplings.switched_on_edges
        caption += (
            f"\ncouplings: {couplings.switched_on_edges} switched-on edges (thin), {hidden} "
            f"hidden (faint, dotted); total edges {couplings.total_edges}"
        )
    figure.text(0.02, 0.02, caption, fontsize=8, family="monospace", va="bottom")
    figure.subplots_adjust(bottom=0.2, right=0.78)
    return _png(figure)


def couplings_preview_png(layers: LayersResult, couplings: CouplingsResult, title: str) -> bytes:
    """Render the switched-on couplings as a schematic for the hand trace, not a map.

    Six rows, one per layer, with nodes labelled by id and class. Arrows run from supplier to
    consumer, coloured by supplier layer: solid for single and two-full feeds (two-full drawn
    heavier), dashed for two-half feeds, dotted for buffer resupply, dash-dot for transport
    access. Mutual pairs are marked with a ring at the arrow's middle. Node labels sit on a pale
    background so arrows never hide them. Every switched-on edge is printed as a table beside the
    schematic, and the caption gives per-pair counts.

    Parameters
    ----------
    layers : LayersResult
        The layers stage's output.
    couplings : CouplingsResult
        The couplings stage's output.
    title : str
        Title printed above the schematic.

    Returns
    -------
    bytes
        A PNG image.

    Spec: Work Order 4, F3; Work Order 4 review, answer 3 (decision 0008).
    """
    from matplotlib.figure import Figure
    from matplotlib.patches import FancyArrowPatch

    figure = Figure(figsize=(22, 12))
    axes = figure.add_axes((0.02, 0.2, 0.46, 0.74))
    rows = _schematic_rows(layers)
    positions = _schematic_positions(layers, rows)
    edges = [edge for edge in couplings.edges if edge.switched_on]
    widest = max((sum(n.layer == layer for n in layers.nodes) for layer in rows), default=1)
    # Limits first: the arcs and their midpoints are laid out in display space.
    axes.set_xlim(-1.3, widest + 0.1)
    axes.set_ylim(-0.8, len(rows) - 0.3)
    for edge in edges:
        start, end = positions[edge.supplier_id], positions[edge.consumer_id]
        style, width = _schematic_style(edge)
        # Arrows bend to alternate sides by feed group, so parallel feeds stay apart.
        bend = 0.12 if edge.feed_group % 2 else -0.12
        axes.add_patch(
            FancyArrowPatch(
                start, end, arrowstyle="-|>", mutation_scale=12, shrinkA=14, shrinkB=14,
                connectionstyle=f"arc3,rad={bend}", color=LAYER_COLOURS[edge.supplier_layer],
                linestyle=style, linewidth=width, alpha=0.9,
            )
        )  # fmt: skip
        if edge.mutual_partner is not None:
            axes.plot(*_arc_point(axes, start, end, bend), marker="o", markersize=9,
                      markerfacecolor="none", markeredgecolor="black", linestyle="",
                      zorder=6)  # fmt: skip
    for node in layers.nodes:
        x, y = positions[node.node_id]
        axes.plot(x, y, marker=CLASS_MARKERS.get(node.node_class, "o"), markersize=13,
                  markerfacecolor=LAYER_COLOURS[node.layer], markeredgecolor="black",
                  linestyle="")  # fmt: skip
        label = node.node_id.removeprefix("SWM-") + "\n" + node.node_class.value.replace("_", " ")
        axes.text(x, y - 0.24, label, ha="center", va="top", fontsize=7, zorder=5,
                  bbox=LABEL_BACKGROUND)  # fmt: skip
    for layer, row in rows.items():
        axes.text(-0.2, row, layer.value, ha="right", va="center", fontsize=10,
                  color=LAYER_COLOURS[layer], fontweight="bold")  # fmt: skip
    axes.set_axis_off()
    axes.set_title(title)
    axes.legend(handles=_schematic_legend(edges), loc="upper left", bbox_to_anchor=(1.0, 1.0),
                fontsize=8)  # fmt: skip
    figure.text(
        0.02, 0.02, _couplings_caption(couplings), fontsize=8, family="monospace", va="bottom"
    )
    figure.text(0.585, 0.95, _edge_table_text(couplings_stage.switched_on_edge_summary(
        couplings, layers)), fontsize=7, family="monospace", va="top")  # fmt: skip
    return _png(figure)


def _edge_table_text(rows: list[dict[str, object]]) -> str:
    """Lay the switched-on edges out as a fixed-width table for the hand trace."""
    header = ("edge", "supplier", "consumer", "type", "feed", "role")
    lines = [
        (
            str(row["edge_id"]).removeprefix("SWM-"),
            f"{str(row['supplier_id']).removeprefix('SWM-')} {row['supplier_class']}",
            f"{str(row['consumer_id']).removeprefix('SWM-')} {row['consumer_class']}",
            str(row["dependency_type"]),
            str(row["feed_configuration"]),
            str(row["role"]),
        )
        for row in rows
    ]
    widths = [max(len(cells[i]) for cells in [header, *lines]) for i in range(len(header))]
    return "\n".join(
        "  ".join(cell.ljust(width) for cell, width in zip(cells, widths, strict=True)).rstrip()
        for cells in [header, *lines]
    )


MUTUAL_MARK_AT = 0.75
"""Where a mutual pair's ring sits along each arrow: near the consumer, clear of labels."""


def _arc_point(
    axes: "Axes", start: tuple[float, float], end: tuple[float, float], bend: float
) -> tuple[float, float]:
    """Return a point on an arc3 arrow in data units, so a marker sits on the arrow itself.

    Matplotlib bends arc3 connections in display space: the control point is the chord's
    middle offset by bend times the chord turned a quarter clockwise, and the arrow is
    the quadratic curve through it, evaluated here at MUTUAL_MARK_AT.
    """
    (x1, y1), (x2, y2) = axes.transData.transform([start, end])
    control_x = (x1 + x2) / 2 + bend * (y2 - y1)
    control_y = (y1 + y2) / 2 - bend * (x2 - x1)
    t = MUTUAL_MARK_AT
    x = (1 - t) * (1 - t) * x1 + 2 * t * (1 - t) * control_x + t * t * x2
    y = (1 - t) * (1 - t) * y1 + 2 * t * (1 - t) * control_y + t * t * y2
    data_x, data_y = axes.transData.inverted().transform((x, y))
    return float(data_x), float(data_y)


def _schematic_rows(layers: LayersResult) -> dict[Layer, int]:
    present = [layer for layer in Layer if any(node.layer == layer for node in layers.nodes)]
    return {layer: len(present) - 1 - index for index, layer in enumerate(present)}


def _schematic_positions(
    layers: LayersResult, rows: dict[Layer, int]
) -> dict[str, tuple[float, float]]:
    positions: dict[str, tuple[float, float]] = {}
    for layer, row in rows.items():
        nodes = [node for node in layers.nodes if node.layer == layer]
        for index, node in enumerate(nodes):
            positions[node.node_id] = (index + 0.5, float(row))
    return positions


def _schematic_style(edge: CouplingEdge) -> tuple[str, float]:
    if edge.role == Role.BUFFER_RESUPPLY:
        return ":", 1.4
    if edge.feed_configuration == FeedConfiguration.TWO_HALF:
        return "--", 1.4
    if edge.feed_configuration == FeedConfiguration.ANY_REACHABLE:
        return "-.", 1.2
    if edge.feed_configuration == FeedConfiguration.TWO_FULL:
        return "-", 2.2
    return "-", 1.0


def _schematic_legend(edges: list[CouplingEdge]) -> list["Artist"]:
    from matplotlib.lines import Line2D

    legend: list[Artist] = [
        Line2D([], [], color="black", linewidth=1.0, label="single feed"),
        Line2D([], [], color="black", linewidth=2.2, label="two full feeds"),
        Line2D([], [], color="black", linewidth=1.4, linestyle="--", label="two half feeds"),
        Line2D([], [], color="black", linewidth=1.4, linestyle=":", label="buffer resupply"),
        Line2D([], [], color="black", linewidth=1.2, linestyle="-.", label="transport access"),
        Line2D([], [], marker="o", markerfacecolor="none", markeredgecolor="black",
               linestyle="", label="mutual pair"),
    ]  # fmt: skip
    legend += [
        Line2D([], [], color=LAYER_COLOURS[layer], linewidth=2, label=f"from {layer.value}")
        for layer in Layer
        if any(edge.supplier_layer == layer for edge in edges)
    ]
    return legend


def _couplings_caption(couplings: CouplingsResult) -> str:
    lines = [
        f"{rng.pair_label(s.supplier, s.consumer):<22} {s.dependencies:>3} dependencies  "
        f"{s.edges:>3} edges  hub {s.hub_share:.2f}  not nearest {s.non_nearest_share:.2f}  "
        f"mutual {s.mutual_pairs}"
        for s in couplings.pairs
        if s.switched_on
    ]
    hidden = len(couplings.edges) - couplings.switched_on_edges
    lines.append(
        f"switched-on coupling edges {couplings.switched_on_edges} + intra-layer links "
        f"{couplings.intra_layer_links} = {couplings.total_edges} edges; {hidden} hidden "
        "coupling edges not drawn"
    )
    return "\n".join(lines)


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


def storm_preview_png(
    terrain: TerrainResult,
    layers: LayersResult,
    storm: "StormResult",
    scenario: int,
    title: str,
) -> bytes:
    """Render one storm scenario: the wind field, the track, flooded land and every facility.

    Wind is the 10-minute speed in m/s. Flooded land cells are hatched blue, the lee of the
    spine is outlined, and each node is coloured by layer and shaped by class, with its wind.

    Parameters
    ----------
    terrain : TerrainResult
        The terrain stage's output.
    layers : LayersResult
        The layers stage's output.
    storm : StormResult
        The storm stage's output.
    scenario : int
        Which scenario to draw.
    title : str
        Title printed above the map.

    Returns
    -------
    bytes
        A PNG image.

    Spec: Work Order 6, C1.
    """
    from matplotlib.figure import Figure
    from matplotlib.lines import Line2D
    from matplotlib.patches import Patch

    field = storm.scenarios[scenario]
    side_km = terrain.grid.cells * terrain.grid.cell_size_m / 1000
    figure = Figure(figsize=(12, 10.5))
    axes = figure.add_subplot()
    image = axes.imshow(
        field.wind_m_per_s, extent=(0, side_km, 0, side_km), cmap="viridis",
        interpolation="nearest", vmin=0.0,
    )  # fmt: skip
    figure.colorbar(image, ax=axes, shrink=0.7, label="10-minute wind (m/s)")
    extent = (0, side_km, side_km, 0)
    axes.contour(terrain.land.astype(float), levels=[0.5], colors="white", linewidths=1.0,
                 extent=extent)  # fmt: skip
    if field.lee.any():
        axes.contour(field.lee.astype(float), levels=[0.5], colors="orange", linewidths=0.8,
                     linestyles="--", extent=extent)  # fmt: skip
    flooded = np.asarray(field.flood_depth_m) > 0.0
    overlay = np.zeros((*flooded.shape, 4))
    overlay[flooded] = (0.0, 0.75, 1.0, 0.9)
    axes.imshow(overlay, extent=(0, side_km, 0, side_km), interpolation="nearest")
    if field.track is not None:
        (x, y), (east, south) = field.track.point_km, field.track.direction
        reach = 2 * side_km
        axes.plot([x - reach * east, x + reach * east],
                  [side_km - (y - reach * south), side_km - (y + reach * south)],
                  color="red", linewidth=1.6)  # fmt: skip
        axes.annotate(
            "", xy=(x + 2 * east, side_km - (y + 2 * south)), xytext=(x, side_km - y),
            arrowprops={"arrowstyle": "-|>", "color": "red", "linewidth": 1.6,
                        "mutation_scale": 22},
        )  # fmt: skip
    west_m, south_m = domain_origin_m(terrain.grid)
    for node in layers.nodes:
        x_km, y_km = (node.x_m - west_m) / 1000, (node.y_m - south_m) / 1000
        axes.plot(
            x_km, y_km, marker=CLASS_MARKERS.get(node.node_class, "o"), markersize=8,
            markerfacecolor=LAYER_COLOURS[node.layer], markeredgecolor="black", linestyle="",
        )  # fmt: skip
        wind = float(field.wind_m_per_s[node.row, node.column])
        axes.text(x_km + 0.3, y_km + 0.3, f"{node.node_id[4:]} {wind:.0f}", fontsize=6,
                  bbox=LABEL_BACKGROUND)  # fmt: skip
    west, east, south, north = _land_window(terrain, side_km)
    axes.set_xlim(west, east)
    axes.set_ylim(south, north)
    axes.set_xlabel("km east of the domain origin")
    axes.set_ylabel("km north of the domain origin")
    axes.set_title(title)
    legend = [
        Line2D([], [], color="red", linewidth=1.6, label="track (direction of travel)"),
        Line2D([], [], color="orange", linestyle="--", label="lee of the spine"),
        Patch(facecolor=(0.0, 0.75, 1.0), label="flooded land (depth > 0)"),
        *[Line2D([], [], color=LAYER_COLOURS[layer], linewidth=2, label=layer.value)
          for layer in Layer],
    ]  # fmt: skip
    axes.legend(handles=legend, loc="upper left", bbox_to_anchor=(1.25, 1.0), fontsize=8)
    figure.text(0.02, 0.02, _storm_caption(storm, scenario), fontsize=8, family="monospace",
                va="bottom")  # fmt: skip
    figure.subplots_adjust(bottom=0.16, right=0.72)
    return _png(figure)


def _storm_caption(storm: "StormResult", scenario: int) -> str:
    field = storm.scenarios[scenario]
    head = (
        f"severity {storm.severity} ({storm.storm_class or 'no storm'}), anchor "
        f"{storm.anchor_m_per_s:.1f} m/s at sea, rain {storm.rain_mm:g} mm, flood stage "
        f"{storm.flood_stage_m:g} m"
    )
    if field.track is None:
        return head
    return (
        f"{head}\npeak wind at sea {field.track.peak_wind_m_per_s:.1f} m/s; land inside the "
        f"radius of maximum wind {field.inside_radius_share:.0%}; lee cells "
        f"{int(np.count_nonzero(field.lee))}; node labels give the wind at the node (m/s)"
    )
