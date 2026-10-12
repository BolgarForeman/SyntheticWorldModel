"""The game's printed pages: cards, board, briefing, sheets, tokens and the sealed answer.

Every page is US letter unless it is the board; nothing is set under 9 pt (ruling P1). Cards
come 9 to a sheet with cut lines. The board is drawn once, in fractions of its own size, and
printed at 11x17, on two joined letter sheets, or at 24x36 or 36x48 (H1). PDFs are written
with a fixed producer, no date and no compression, so they are identical on every platform.

Spec: Work Order 9, H1-H9; Trace pack ruling sheet v0.2, P1-P8.
"""

import textwrap
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING

from swm.recipe.schema import Layer
from swm.trace_game.content import (
    LEGEND,
    SHEETS,
    NodeCard,
    answer_events,
    answer_outages,
    answer_score,
    briefing,
    number,
    outage_rows,
    short,
    tokens,
    travel_hours,
)
from swm.trace_game.text import RuleCard, value_text
from swm.trace_pack import (
    INSET_MARGIN_KM,
    LAYER_COLOURS,
    MARKERS,
    TraceInputs,
    _island_frame,
    _km,
    _land,
    clusters,
    crowded,
    damage_line_rows,
    pdf_pages,
)

if TYPE_CHECKING:
    from matplotlib.axes import Axes
    from matplotlib.figure import Figure

LETTER_IN = (8.5, 11.0)
MIN_PT = 9.0
"""Nothing is set smaller (ruling P1)."""
MONO = "DejaVu Sans Mono"
CARD_IN = (2.5, 3.5)
"""A card: poker size, 9 to a letter sheet in 3 x 3."""
CARD_COLUMNS = 30
"""Characters per card line at 9 pt monospace within the card's margins."""
CARD_LINES = 21
"""Lines per card at 9 pt with 1.2 line spacing."""
BOARD_IN = (17.0, 11.0)
"""The board's own size: 11x17, landscape; every other size is drawn from it (H1)."""
BOARD_MIN_PT = 10.0
"""The board's smallest type at 11x17, so the tiled board (at 16/17) stays at 9 pt or more."""
BOARD_SIZES: Mapping[str, tuple[float, float]] = {
    "11x17": (17.0, 11.0),
    "24x36": (36.0, 24.0),
    "36x48": (48.0, 36.0),
}
"""Single-sheet board sizes in inches, landscape (H1)."""
TILE_PRINTABLE_IN = (8.0, 10.5)
"""A letter sheet's printable area, quarter-inch margins, for the tiled board."""
DRAFT_MARK = "DRAFT"
ROWS_PER_SHEET = 24
LABEL_ALONG = 0.65
"""Where an illustration arrow's label sits, as a share of the way to its head (layout)."""
"""Blank rows on a log sheet."""


@dataclass(frozen=True)
class Game:
    """The game's PDFs by file name, and the sealed answer's."""

    game: dict[str, bytes]
    answer: dict[str, bytes]


# --- Shared page helpers --------------------------------------------------------------------


def _letter() -> "Figure":
    from matplotlib.figure import Figure

    return Figure(figsize=LETTER_IN)


def _text(figure: "Figure", x: float, y: float, text: str, size: float = MIN_PT,
          **style: object) -> None:  # fmt: skip
    figure.text(x / figure.get_figwidth(), y / figure.get_figheight(), text, fontsize=size,
                va="top", **style)  # type: ignore[arg-type]  # fmt: skip


def _wrap(text: str, width: int = CARD_COLUMNS, indent: str = "") -> list[str]:
    return textwrap.wrap(text, width, subsequent_indent=indent, break_long_words=True) or [""]


def _cut_lines(figure: "Figure") -> None:
    """Draw the 3 x 3 grid of cut lines for 9 cards on a letter sheet."""
    from matplotlib.lines import Line2D

    width, height = LETTER_IN
    left, bottom = (width - 3 * CARD_IN[0]) / 2, (height - 3 * CARD_IN[1]) / 2
    for i in range(4):
        x = (left + i * CARD_IN[0]) / width
        y = (bottom + i * CARD_IN[1]) / height
        for line in (((x, x), (0.0, 1.0)), ((0.0, 1.0), (y, y))):
            figure.add_artist(Line2D(*line, color="#999999", linewidth=0.5, linestyle=(0, (4, 3))))


def _card_origin(slot: int, mirrored: bool = False) -> tuple[float, float]:
    """Return a card slot's top-left corner in inches; a back sheet mirrors its columns."""
    width, height = LETTER_IN
    left, bottom = (width - 3 * CARD_IN[0]) / 2, (height - 3 * CARD_IN[1]) / 2
    row, column = divmod(slot, 3)
    if mirrored:
        column = 2 - column
    return left + column * CARD_IN[0], bottom + (3 - row) * CARD_IN[1]


def _card_text(figure: "Figure", slot: int, lines: Sequence[tuple[str, bool]],
               mirrored: bool = False) -> None:  # fmt: skip
    """Set a card's lines (text, bold) from its top-left corner."""
    x, top = _card_origin(slot, mirrored)
    for index, (line, bold) in enumerate(lines[:CARD_LINES]):
        _text(figure, x + 0.12, top - 0.12 - index * MIN_PT * 1.2 / 72, line, MIN_PT,
              family=MONO, fontweight="bold" if bold else "normal")  # fmt: skip


# --- Node cards (H2) ------------------------------------------------------------------------


def card_lines(card: NodeCard) -> list[list[tuple[str, bool]]]:
    """Return a node card's lines, split over as many cards as it needs (marked cont.)."""
    body: list[tuple[str, bool]] = []
    for title, lines in (("Needs", card.needs), ("Back-up", card.backup),
                         ("Supplies", card.supplies)):  # fmt: skip
        body.append((title, True))
        for line in lines:
            body += [(w, False) for w in _wrap(line, CARD_COLUMNS, "   ")]
    head = [(card.header[0], True), *((w, False) for line in card.header[1:]
                                      for w in _wrap(line))]  # fmt: skip
    room = CARD_LINES - len(head) - 1
    pages = [body[i : i + room] for i in range(0, len(body), room)] or [[]]
    result = []
    for index, page in enumerate(pages):
        mark = [] if index == 0 else [(f"(cont. {index + 1}/{len(pages)})", False)]
        result.append([*head, *mark, *page])
    return result


def legend_lines() -> list[tuple[str, bool]]:
    """Return the legend card: the symbols and what each means."""
    lines: list[tuple[str, bool]] = [("Legend", True)]
    for symbol, meaning in LEGEND:
        lines += [(w, False) for w in _wrap(f"{symbol} {meaning}", CARD_COLUMNS, "  ")]
    lines += [("", False), *((w, False) for w in _wrap(
        "κ: the share of the need the supplier covers. (hidden): a real coupling no source "
        "shows; the engine plays it.", CARD_COLUMNS))]  # fmt: skip
    return lines


def node_cards_pdf(cards: Sequence[NodeCard]) -> bytes:
    """Return the node-card sheets: the legend card first, then one card per node (H2)."""
    faces = [legend_lines()] + [face for card in cards for face in card_lines(card)]
    figures = []
    for start in range(0, len(faces), 9):
        figure = _letter()
        _cut_lines(figure)
        for slot, face in enumerate(faces[start : start + 9]):
            _card_text(figure, slot, face)
        figures.append(figure)
    return pdf_pages(figures)


# --- Rule cards (H3) ------------------------------------------------------------------------


def rule_front(card: RuleCard, values: Sequence[tuple[str, str]]) -> list[tuple[str, bool]]:
    """Return a rule card's front: title, the rule, and its registry values with their ids."""
    lines: list[tuple[str, bool]] = [(w, True) for w in _wrap(card.title)]
    if card.draft:
        lines.append((f"{DRAFT_MARK} wording", False))
    lines += [(w, False) for w in _wrap(card.rule)]
    if values:
        lines.append(("Registry", True))
    for rule_id, value in values:
        if value:
            lines += [(w, False) for w in _wrap(f"= {value}", CARD_COLUMNS, "  ")]
        lines += [(w, False) for w in id_lines(rule_id)]
    return lines


def id_lines(rule_id: str, width: int = CARD_COLUMNS) -> list[str]:
    """Return a registry id over as many lines as it needs, broken only after a dot."""
    lines, line = [], "  ["
    for part in rule_id.split("."):
        piece = part if line.endswith("[") else f".{part}"
        if len(line) + len(piece) + 1 > width and not line.endswith("["):
            lines.append(line)
            line = "    "
            piece = piece
        line += piece
    return [*lines, line + "]"]


def rule_back(card: RuleCard) -> list[tuple[str, bool]]:
    """Return a rule card's back: the drill and its answer."""
    lines: list[tuple[str, bool]] = [(w, True) for w in _wrap(f"Drill: {card.title}")]
    if card.draft:
        lines.append((f"{DRAFT_MARK} wording", False))
    lines += [(w, False) for w in _wrap(card.drill)]
    lines += [("", False), ("Answer", True), *((w, False) for w in _wrap(card.answer))]
    return lines


def rule_cards_pdf(cards: Sequence[RuleCard], values: Mapping[str, Sequence[tuple[str, str]]]
                   ) -> bytes:  # fmt: skip
    """Return the rule-card sheets: fronts, then their backs mirrored for long-edge duplex."""
    figures = []
    for start in range(0, len(cards), 9):
        batch = cards[start : start + 9]
        front, back = _letter(), _letter()
        for figure in (front, back):
            _cut_lines(figure)
        for slot, card in enumerate(batch):
            lines = rule_front(card, values[card.name])
            _card_text(front, slot, lines)
            _illustration(front, slot, card, len(lines))
            _card_text(back, slot, rule_back(card), mirrored=True)
        figures += [front, back]
    return pdf_pages(figures)


def _illustration(figure: "Figure", slot: int, card: RuleCard, used: int) -> None:
    """Draw the card's generic nodes (A, B, C ...) round a circle, with labelled arrows."""
    from matplotlib.patches import FancyArrowPatch

    names: list[str] = []
    for edge in card.illustration:
        for name in (edge.start, edge.end):
            if name not in names:
                names.append(name)
    if not names:
        return
    x, top = _card_origin(slot)
    room = top - 0.12 - used * MIN_PT * 1.2 / 72 - 0.1
    height = min(1.2, room - (top - CARD_IN[1]) - 0.1)
    if height < 0.5:
        return
    width, page_h = LETTER_IN
    axes = figure.add_axes(((x + 0.15) / width, (room - height) / page_h,
                            (CARD_IN[0] - 0.3) / width, height / page_h))  # fmt: skip
    axes.set_axis_off()
    axes.set_xlim(-1.4, 1.4)
    axes.set_ylim(-1.0, 1.0)
    count = len(names)
    # Nodes sit evenly on a line, two up and one down, so straight arrows never cross a node.
    spots = {name: (-1.0 + 2.0 * i / max(1, count - 1), 0.5 if i % 2 == 0 else -0.5)
             for i, name in enumerate(names)}  # fmt: skip
    for edge in card.illustration:
        axes.add_patch(FancyArrowPatch(spots[edge.start], spots[edge.end], arrowstyle="-|>",
                                       mutation_scale=10, shrinkA=12, shrinkB=12,
                                       color="#444444"))  # fmt: skip
        (sx, sy), (ex, ey) = spots[edge.start], spots[edge.end]
        mx, my = sx + LABEL_ALONG * (ex - sx), sy + LABEL_ALONG * (ey - sy)
        # Labels sit toward the arrow's head and alternate above and below, so two arrows
        # from one node keep their labels apart.
        above = card.illustration.index(edge) % 2 == 0
        axes.text(mx, my + (0.12 if above else -0.28), edge.label, fontsize=MIN_PT,
                  ha="center", family=MONO)  # fmt: skip
    for name, (nx, ny) in spots.items():
        axes.text(nx, ny, name, fontsize=MIN_PT + 2, ha="center", va="center",
                  fontweight="bold", bbox={"boxstyle": "circle", "facecolor": "white"})  # fmt: skip


# --- The board (H4) -------------------------------------------------------------------------


def network_order(inputs: TraceInputs) -> dict[Layer, list[str]]:
    """Order each layer column's nodes to cut crossings (H4).

    CHOICE: the barycentre method. Start in id order; then sweep the columns left to right and
    back, three times, placing each node at the mean position of its switched-on neighbours in
    the other columns (a node with none keeps its place); ties keep the earlier order, then
    the lower id. Only +, / and comparisons, so the order is the same on every platform.

    Parameters
    ----------
    inputs : TraceInputs
        The world.

    Returns
    -------
    dict
        Each layer's node ids, top to bottom.

    Spec: Work Order 9, H4.
    """
    columns = {layer: sorted(n.node_id for n in inputs.world.nodes if n.layer == layer)
               for layer in Layer}  # fmt: skip
    neighbours: dict[str, list[str]] = {n.node_id: [] for n in inputs.world.nodes}
    for edge in inputs.couplings.edges:
        if edge.switched_on:
            neighbours[edge.supplier_id].append(edge.consumer_id)
            neighbours[edge.consumer_id].append(edge.supplier_id)
    for _ in range(BARYCENTRE_SWEEPS):
        for layer in [*Layer, *reversed(Layer)]:
            place = {node_id: i / max(1, len(c) - 1) for c in columns.values()
                     for i, node_id in enumerate(c)}  # fmt: skip
            keys = {}
            for index, node_id in enumerate(columns[layer]):
                near = [place[m] for m in neighbours[node_id]]
                keys[node_id] = (sum(near) / len(near) if near else place[node_id], index,
                                 node_id)  # fmt: skip
            columns[layer] = sorted(columns[layer], key=lambda n: keys[n])
    return columns


BARYCENTRE_SWEEPS = 3


class _Board:
    """Places the board's parts on a figure, from fractions of the board's own size."""

    def __init__(self, figure: "Figure", origin_in: tuple[float, float],
                 size_in: tuple[float, float]) -> None:  # fmt: skip
        self.figure = figure
        self.origin = origin_in
        self.size = size_in
        self.scale = min(size_in[0] / BOARD_IN[0], size_in[1] / BOARD_IN[1])

    def rect(self, x: float, y: float, w: float, h: float) -> tuple[float, float, float, float]:
        fw, fh = self.figure.get_figwidth(), self.figure.get_figheight()
        return ((self.origin[0] + x * self.size[0]) / fw, (self.origin[1] + y * self.size[1]) / fh,
                w * self.size[0] / fw, h * self.size[1] / fh)  # fmt: skip

    def pt(self, size: float) -> float:
        return size * self.scale


def _draw_board(figure: "Figure", origin_in: tuple[float, float], size_in: tuple[float, float],
                inputs: TraceInputs) -> None:  # fmt: skip
    board = _Board(figure, origin_in, size_in)
    title = figure.add_axes(board.rect(0.01, 0.94, 0.98, 0.05))
    title.set_axis_off()
    title.text(0.0, 0.5, f"Board: scenario world, {len(inputs.world.nodes)} nodes. Place damage "
               "markers from the briefing; nothing on the board marks damage.",
               fontsize=board.pt(BOARD_MIN_PT + 2), va="center")  # fmt: skip
    _network(figure.add_axes(board.rect(0.01, 0.13, 0.55, 0.80)), inputs, board)
    _map_side(figure, inputs, board)
    _hour_track(figure.add_axes(board.rect(0.01, 0.02, 0.98, 0.08)), inputs, board)


def _network(axes: "Axes", inputs: TraceInputs, board: _Board) -> None:
    from matplotlib.patches import FancyArrowPatch

    columns = network_order(inputs)
    spots: dict[str, tuple[float, float]] = {}
    for c, layer in enumerate(Layer):
        nodes = columns[layer]
        for r, node_id in enumerate(nodes):
            spots[node_id] = (c, -(r + 0.5) * (1.0 / max(1, len(nodes))) * NETWORK_ROWS)
    for link in inputs.layers.links:
        a, b = spots[link.from_id], spots[link.to_id]
        axes.add_patch(FancyArrowPatch(a, b, arrowstyle="-", linewidth=board.pt(1.2),
                                       color=LAYER_COLOURS[link.layer],
                                       connectionstyle="arc3,rad=0.35"))  # fmt: skip
    for edge in inputs.couplings.edges:
        if not edge.switched_on:
            continue
        # Couplings bow, so one between two nodes on a row never runs behind a third.
        axes.add_patch(FancyArrowPatch(
            spots[edge.supplier_id], spots[edge.consumer_id], arrowstyle="-|>",
            mutation_scale=board.pt(10), linewidth=board.pt(0.8), alpha=0.75, shrinkA=14,
            shrinkB=14, color=LAYER_COLOURS[edge.supplier_layer],
            connectionstyle="arc3,rad=0.18"))  # fmt: skip
    classes = {n.node_id: n.node_class.value.replace("_", " ") for n in inputs.world.nodes}
    for node_id, (x, y) in spots.items():
        axes.text(x, y, f"{short(node_id)}\n{classes[node_id]}", ha="center", va="center",
                  fontsize=board.pt(BOARD_MIN_PT), family=MONO, bbox=NODE_BOX)  # fmt: skip
    for c, layer in enumerate(Layer):
        axes.text(c, 0.3, layer.value, ha="center", fontsize=board.pt(BOARD_MIN_PT + 2),
                  fontweight="bold", color=LAYER_COLOURS[layer])  # fmt: skip
    axes.set_xlim(-0.6, len(Layer) - 0.4)
    axes.set_ylim(-NETWORK_ROWS - 0.2, 0.7)
    axes.set_axis_off()


NODE_BOX = {"boxstyle": "round", "facecolor": "white", "edgecolor": "#555555"}
NETWORK_ROWS = 6.0
"""The network side's height in row units (layout only)."""


def _map_side(figure: "Figure", inputs: TraceInputs, board: _Board) -> None:
    """Draw the map: the island whole, and its crowded clusters again at a larger scale."""
    from matplotlib.patches import Rectangle

    groups = clusters(inputs)
    in_insets = {node_id for group in groups for node_id in group}
    whole = figure.add_axes(board.rect(0.58, 0.40, 0.41, 0.53))
    _map_panel(whole, inputs, board, in_insets, crowded(inputs, BOARD_CLEARANCE_KM))
    west, east, south, north = _island_frame(inputs.terrain)
    whole.set_xlim(west, east)
    whole.set_ylim(south, north)
    whole.set_title("Map: travel hours from the crew base", fontsize=board.pt(BOARD_MIN_PT + 2))
    km = _km(inputs.terrain)
    sites = {n.node_id: km(n.site) for n in inputs.world.nodes}
    width = 0.41 / max(1, len(groups))
    for index, group in enumerate(groups):
        xs, ys = [sites[n][0] for n in group], [sites[n][1] for n in group]
        box = (min(xs) - INSET_MARGIN_KM, max(xs) + INSET_MARGIN_KM,
               min(ys) - INSET_MARGIN_KM, max(ys) + INSET_MARGIN_KM)  # fmt: skip
        name = "AB"[index]
        whole.add_patch(Rectangle((box[0], box[2]), box[1] - box[0], box[3] - box[2],
                                  fill=False, linestyle=":", linewidth=board.pt(1.0)))  # fmt: skip
        whole.annotate(name, (box[0], box[3]), fontsize=board.pt(BOARD_MIN_PT), xytext=(0, 2),
                       textcoords="offset points")  # fmt: skip
        rect = board.rect(0.58 + index * width + 0.005, 0.13, width - 0.01, 0.24)
        inset = figure.add_axes(rect)
        _map_panel(inset, inputs, board, set(), crowded(inputs))
        shape = (rect[2] * figure.get_figwidth()) / (rect[3] * figure.get_figheight())
        x0, x1, y0, y1 = fitted(box, shape)
        inset.set_xlim(x0, x1)
        inset.set_ylim(y0, y1)
        inset.set_title(f"{name}: larger scale", fontsize=board.pt(BOARD_MIN_PT))


def fitted(box: tuple[float, float, float, float], shape: float) -> tuple[float, ...]:
    """Widen a view to its panel's shape (width / height), leaving room each side for labels."""
    x0, x1, y0, y1 = box
    room = LABEL_ROOM * (x1 - x0)
    x0, x1 = x0 - room, x1 + room
    width, height = x1 - x0, y1 - y0
    if width / height < shape:
        extra = (shape * height - width) / 2
        return x0 - extra, x1 + extra, y0, y1
    extra = (width / shape - height) / 2
    return x0, x1, y0 - extra, y1 + extra


BOARD_CLEARANCE_KM = 1.5
"""On the whole-island map, two nodes this close label on opposite sides (layout only)."""
LABEL_ROOM = 0.6
"""Room added each side of an inset's nodes for their labels, as a share of its width."""


def _map_panel(axes: "Axes", inputs: TraceInputs, board: _Board, unlabelled: set[str],
               flipped: set[str]) -> None:  # fmt: skip
    km = _km(inputs.terrain)
    _land(axes, inputs.terrain)
    for link in inputs.layers.links:
        if link.layer == Layer.TRANSPORT:
            points = [km(p) for p in link.points]
            axes.plot([p[0] for p in points], [p[1] for p in points], color="#777777",
                      linewidth=board.pt(1.0))  # fmt: skip
    hours = travel_hours(inputs)
    for node in inputs.world.nodes:
        x, y = km(node.site)
        axes.plot([x], [y], marker=MARKERS[node.layer], color=LAYER_COLOURS[node.layer],
                  markersize=board.pt(7), markeredgecolor="black")  # fmt: skip
        if node.node_id not in unlabelled:
            # Of two close nodes, the higher id labels to the left and below.
            left = node.node_id in flipped
            axes.annotate(f"{short(node.node_id)} {number(hours[node.node_id])} h", (x, y),
                          fontsize=board.pt(BOARD_MIN_PT), xytext=(-4, -10) if left else (4, 3),
                          ha="right" if left else "left", textcoords="offset points",
                          clip_on=True)  # fmt: skip
    for row in damage_line_rows(inputs):
        point = next(p for p in inputs.engine_damage.failure_points
                     if p.line_id == row["line"] and p.km == row["km_along_line"])  # fmt: skip
        x, y = km(point.site)
        axes.plot([x], [y], marker="o", color="#777777", markersize=board.pt(4))
        axes.annotate(f"{number(float(str(row['travel_h_from_base'])))} h", (x, y),
                      fontsize=board.pt(BOARD_MIN_PT), color="#555555", xytext=(4, -10),
                      textcoords="offset points", clip_on=True)  # fmt: skip
    for site in sorted({crew.site for crew in inputs.world.crews}):
        x, y = km(site)
        axes.plot([x], [y], marker="*", color="black", markersize=board.pt(14))
        axes.annotate("crew base", (x, y), fontsize=board.pt(BOARD_MIN_PT), xytext=(6, -12),
                      textcoords="offset points", clip_on=True)  # fmt: skip
    axes.set_aspect("equal")
    axes.set_xticks([])
    axes.set_yticks([])


def _hour_track(axes: "Axes", inputs: TraceInputs, board: _Board) -> None:
    from matplotlib.patches import Rectangle

    horizon = int(inputs.rules.number("dynamics.horizon_h"))
    for hour in range(horizon + 1):
        axes.add_patch(Rectangle((hour, 0.0), 1.0, 1.0, fill=False, linewidth=board.pt(0.6),
                                 edgecolor="#444444"))  # fmt: skip
        if hour % HOUR_LABEL_EVERY == 0:
            axes.text(hour + 0.5, 1.15, str(hour), ha="center", fontsize=board.pt(BOARD_MIN_PT))
    axes.set_xlim(-0.5, horizon + 1.5)
    axes.set_ylim(-0.2, 1.8)
    axes.set_axis_off()


HOUR_LABEL_EVERY = 6


def board_pdf(inputs: TraceInputs, size: str) -> bytes:
    """Return the board at one size: a single sheet, or tiled on joined letter sheets (H1, H4).

    Parameters
    ----------
    inputs : TraceInputs
        The world and the scenario's failure points.
    size : str
        ``11x17``, ``tiled-letter``, ``24x36`` or ``36x48``.

    Returns
    -------
    bytes
        The PDF.

    Spec: Work Order 9, H1 and H4.
    """
    from matplotlib.figure import Figure

    if size != "tiled-letter":
        width, height = BOARD_SIZES[size]
        figure = Figure(figsize=(width, height))
        _draw_board(figure, (0.0, 0.0), (width, height), inputs)
        return pdf_pages([figure])
    # CHOICE: two portrait letter sheets, the board at 16/17 of 11x17, so each sheet holds half
    # within quarter-inch margins; trim marks at the printable edge and a join mark on the seam.
    print_w = TILE_PRINTABLE_IN[0]
    board_w = 2 * print_w
    board_h = board_w * BOARD_IN[1] / BOARD_IN[0]
    margin_x, margin_y = (LETTER_IN[0] - print_w) / 2, (LETTER_IN[1] - board_h) / 2
    figures = []
    for column in range(2):
        figure = Figure(figsize=LETTER_IN)
        _draw_board(figure, (margin_x - column * print_w, margin_y), (board_w, board_h), inputs)
        _tile_marks(figure, margin_x, margin_y, print_w, board_h, column)
        figures.append(figure)
    return pdf_pages(figures)


def _tile_marks(figure: "Figure", margin_x: float, margin_y: float, print_w: float,
                board_h: float, column: int) -> None:  # fmt: skip
    """Mask the margins, mark the trim corners and the join edge of one tile."""
    from matplotlib.lines import Line2D
    from matplotlib.patches import Rectangle

    width, height = LETTER_IN
    masks = ((0, 0, margin_x, height), (margin_x + print_w, 0, width, height),
             (0, 0, width, margin_y), (0, margin_y + board_h, width, height))  # fmt: skip
    for x0, y0, x1, y1 in masks:
        figure.add_artist(Rectangle((x0 / width, y0 / height), (x1 - x0) / width,
                                    (y1 - y0) / height, facecolor="white", edgecolor="none",
                                    zorder=10))  # fmt: skip
    for x in (margin_x, margin_x + print_w):
        for y in (margin_y, margin_y + board_h):
            for dx, dy in ((0.15, 0), (0, 0.15)):
                figure.add_artist(Line2D([(x - dx) / width, (x + dx) / width],
                                         [(y - dy) / height, (y + dy) / height],
                                         color="black", linewidth=0.6, zorder=11))  # fmt: skip
    seam = margin_x + print_w if column == 0 else margin_x
    side = "right" if column == 0 else "left"
    figure.text(seam / width, (margin_y - 0.05) / height,
                f"sheet {column + 1} of 2: join on the {side} edge", ha=side, va="top",
                fontsize=MIN_PT, zorder=12)  # fmt: skip


# --- Briefing, sheets, tokens (H5-H7) -------------------------------------------------------


def briefing_pdf(inputs: TraceInputs, scenario: int) -> bytes:
    """Return the one-page mission briefing: what failed, never what it causes (H5)."""
    brief = briefing(inputs)
    lines: list[tuple[str, bool]] = [(f"Mission briefing: scenario {scenario}", True), ("", False),
                                     ("The storm", True)]  # fmt: skip
    lines += [(w, False) for w in _wrap(str(brief["storm"]), 80)]
    lines += [("", False), ("What failed: lines", True)]
    ends: dict[str, tuple[str, str, str]] = brief["line_ends"]  # type: ignore[assignment]
    for line_id, (start, end, structure) in sorted(ends.items()):
        lines.append((f"{short(line_id)}: from {short(start)} to {short(end)}, on {structure}s",
                      False))  # fmt: skip
    failed: list[dict[str, object]] = brief["lines"]  # type: ignore[assignment]
    if failed:
        lines += [("", False), (_columns(BRIEF_COLUMNS, BRIEF_WIDTHS), False)]
        lines += [(_columns([short(str(row["line"])), *(number(float(str(row[key])))
                                                      for key in BRIEF_KEYS)], BRIEF_WIDTHS),
                   False) for row in failed]  # fmt: skip
    else:
        lines.append(("no line failed", False))
    lines += [("", False), ("What failed: facilities", True)]
    facilities: list[dict[str, object]] = brief["facilities"]  # type: ignore[assignment]
    lines += [(f"{short(str(row['node']))}: {row['damage_state']}", False) for row in facilities]
    if not facilities:
        lines.append(("no facility damaged", False))
    bases = ", ".join(brief["base"])  # type: ignore[arg-type]
    lines += [("", False), ("Crews", True),
              (f"{brief['crews']} crew(s) at base {bases}; travel hours from the base are on the "
               "board's map", False),
              ("", False), ("Horizon", True)]  # fmt: skip
    lines.append((f"Play from hour 0 to hour {number(float(str(brief['horizon_h'])))}.", False))
    figure = _letter()
    for index, (line, bold) in enumerate(lines):
        _text(figure, 0.6, 10.4 - index * 0.22, line, MIN_PT + 2 if bold else MIN_PT + 1,
              family=MONO, fontweight="bold" if bold else "normal")  # fmt: skip
    return pdf_pages([figure])


BRIEF_COLUMNS = ("line", "km along", "road km", "off-road km", "travel h", "crew work h")
BRIEF_KEYS = ("km_along_line", "road_km", "offroad_km", "travel_h_from_base", "crew_work_h")
BRIEF_WIDTHS = (10, 9, 8, 12, 9, 12)


def _columns(values: Sequence[str], widths: Sequence[int]) -> str:
    """Return values in fixed-width columns: the first left-aligned, the rest right-aligned."""
    cells = [values[0].ljust(widths[0])]
    cells += [v.rjust(w) for v, w in zip(values[1:], widths[1:], strict=True)]
    return " ".join(cells)


def sheets_pdf(inputs: TraceInputs) -> bytes:
    """Return the log sheets (H6).

    The crew sheet, event log, outage sheet (every end-use node listed with its weight),
    decision log and play-test feedback sheet.
    """
    end_uses = outage_rows(inputs.world)
    figures = []
    for title, columns in SHEETS.items():
        figure = _letter()
        _text(figure, 0.5, 10.6, title, MIN_PT + 5, fontweight="bold")
        rows = len(end_uses) if title == "Outage sheet" else ROWS_PER_SHEET
        height = min(0.36, 9.4 / (rows + 1))
        width = 7.5 / len(columns)
        _grid(figure, len(columns), rows + 1, width, height)
        for index, column in enumerate(columns):
            _text(figure, 0.55 + index * width, SHEET_TOP - 0.06, column, MIN_PT,
                  fontweight="bold")  # fmt: skip
        if title == "Outage sheet":
            for r, (node_id, weight) in enumerate(end_uses):
                y = SHEET_TOP - (r + 1) * height - 0.06
                _text(figure, 0.55, y, short(node_id), MIN_PT, family=MONO)
                _text(figure, 0.55 + width, y, number(weight), MIN_PT, family=MONO)
        figures.append(figure)
    return pdf_pages(figures)


SHEET_TOP = 10.1
"""The top of a log sheet's grid, in inches from the page's foot."""


def _grid(figure: "Figure", columns: int, rows: int, width: float, height: float) -> None:
    from matplotlib.lines import Line2D

    page_w, page_h = LETTER_IN
    left, right = 0.5, 0.5 + columns * width
    bottom = SHEET_TOP - rows * height
    for r in range(rows + 1):
        y = (SHEET_TOP - r * height) / page_h
        figure.add_artist(Line2D([left / page_w, right / page_w], [y, y], color="#666666",
                                 linewidth=0.5))  # fmt: skip
    for c in range(columns + 1):
        x = (left + c * width) / page_w
        figure.add_artist(Line2D([x, x], [SHEET_TOP / page_h, bottom / page_h], color="#666666",
                                 linewidth=0.5))  # fmt: skip


def tokens_pdf(inputs: TraceInputs) -> bytes:
    """Return the token sheet: damage markers, crew pawns, out markers, the clock, stock clocks."""
    from matplotlib.patches import Circle

    figure = _letter()
    _text(figure, 0.5, 10.6, "Tokens: cut out", MIN_PT + 5, fontweight="bold")
    counts = tokens(inputs)
    y = 10.0
    diameter = 0.7
    labels = {"damage marker": "X", "out marker": "OUT", "clock": "h", "stock clock": "▮ h"}
    for kind, count in counts.items():
        _text(figure, 0.5, y, f"{kind} ({count})", MIN_PT + 1, fontweight="bold")
        y -= 0.3
        for i in range(count):
            column, row = i % 10, i // 10
            cx, cy = 0.9 + column * (diameter + 0.05), y - 0.35 - row * (diameter + 0.05)
            figure.add_artist(Circle((cx / 8.5, cy / 11), diameter / 2 / 8.5, fill=False,
                                     edgecolor="black", linewidth=0.6,
                                     transform=figure.transFigure))  # fmt: skip
            label = f"crew {i + 1}" if kind == "crew pawn" else labels[kind]
            figure.text(cx / 8.5, cy / 11, label, ha="center", va="center", fontsize=MIN_PT)
        y -= ((count + 9) // 10) * (diameter + 0.05) + 0.2
    return pdf_pages([figure])


def text_pdf(lines: Sequence[str], draft: bool) -> bytes:
    """Return a typeset text document: the field manual or the debrief (H9)."""
    figures = []
    per_page = 44
    body = [w for line in lines for w in (_wrap(line, 86) if line else [""])]
    for start in range(0, max(1, len(body)), per_page):
        figure = _letter()
        if draft:
            figure.text(0.5, 0.5, DRAFT_MARK, fontsize=96, color="#dddddd", ha="center",
                        va="center", rotation=30)  # fmt: skip
        for index, line in enumerate(body[start : start + per_page]):
            heading = line.startswith("#")
            _text(figure, 0.6, 10.4 - index * 0.22, line.lstrip("# "), MIN_PT + 3 if heading
                  else MIN_PT + 1, fontweight="bold" if heading else "normal")  # fmt: skip
        figures.append(figure)
    return pdf_pages(figures)


# --- The sealed answer (H8) -----------------------------------------------------------------


def answer_pdf(inputs: TraceInputs) -> bytes:
    """Return the sealed answer: the score, each end-use node's outages, the event timeline."""
    run, world = inputs.run, inputs.world
    score = answer_score(run, world)
    lines: list[tuple[str, bool]] = [
        (f"Sealed answer: scenario {inputs.scenario}. Open after play.", True), ("", False),
        ("Score", True),
        ("weighted service-hours lost (Lifeline): "
         f"{number(score['weighted_service_hours_lost'])}", False),
        (f"hours out, unweighted: {number(score['hours_out'])}", False), ("", False),
        ("Outages per end-use node", True),
        (_columns(OUTAGE_COLUMNS, OUTAGE_WIDTHS), False),
    ]  # fmt: skip
    for row in answer_outages(run, world):
        cells = [str(row["node"]), number(float(str(row["weight"]))),
                 str(row["out_intervals_h"]) or "-", number(float(str(row["hours_out"]))),
                 number(float(str(row["weighted_hours"])))]  # fmt: skip
        lines.append((_columns(cells, OUTAGE_WIDTHS), False))
    lines += [("", False), ("Events (exact time, the step it takes effect)", True)]
    for event in answer_events(run):
        exact, step = number(float(str(event["exact_h"]))), number(float(str(event["step_h"])))
        lines.append((f"{exact:>8} h  step {step:>6}  {event['event']}", False))
    figures = []
    per_page = 46
    for start in range(0, len(lines), per_page):
        figure = _letter()
        for index, (line, bold) in enumerate(lines[start : start + per_page]):
            _text(figure, 0.5, 10.5 - index * 0.215, line, MIN_PT, family=MONO,
                  fontweight="bold" if bold else "normal")  # fmt: skip
        figures.append(figure)
    return pdf_pages(figures)


OUTAGE_COLUMNS = ("node", "weight", "out (h)", "hours out", "weighted")
OUTAGE_WIDTHS = (10, 7, 28, 10, 10)


def rule_values(cards: Sequence[RuleCard], lookup: object) -> dict[str, list[tuple[str, str]]]:
    """Return each card's registry values as (id, value with units), read from the registry."""
    from swm.rules.registry import Registry

    assert isinstance(lookup, Registry)
    result: dict[str, list[tuple[str, str]]] = {}
    for card in cards:
        pairs = []
        for rule_id in card.value_ids:
            units = lookup.rule(rule_id).units
            value = lookup.value(rule_id)
            # A rule given in words is already in the card's sentence; only its id is added.
            text = "" if isinstance(value, str | list) else value_text(value)
            pairs.append((rule_id, f"{text} {units}" if text and units else text))
        result[card.name] = pairs
    return result
