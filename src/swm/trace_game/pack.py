"""Assemble the trace game: the player's ``game/`` and the sealed ``answer/`` (WO 9, H1).

``game/`` is built from the world, the scenario's damage and the registry alone; it never
reads the reference run, so the same run or another leaves it byte for byte the same (H10).
Every rule card's drill is played by the engine before the cards are printed; a printed answer
the engine does not reproduce stops the build (H3).

Spec: Work Order 9, H1-H10; Trace pack ruling sheet v0.2.
"""

from dataclasses import dataclass

from swm.trace_game.content import answer_events, answer_outages, answer_score, node_cards
from swm.trace_game.drills import verify
from swm.trace_game.render import (
    answer_pdf,
    board_pdf,
    briefing_pdf,
    node_cards_pdf,
    rule_cards_pdf,
    sheets_pdf,
    text_pdf,
    tokens_pdf,
)
from swm.trace_game.text import DEBRIEF, FIELD_MANUAL, pages_of, rule_cards
from swm.trace_pack import TraceInputs

BOARD_CHOICES = ("11x17", "tiled-letter", "24x36", "36x48")
DEFAULT_BOARD = "11x17"


@dataclass(frozen=True)
class TraceGame:
    """The player's files and the sealed answer's, by file name."""

    game: dict[str, bytes]
    answer: dict[str, bytes]
    answer_tables: dict[str, list[dict[str, object]]]


def trace_game(inputs: TraceInputs, board_size: str = DEFAULT_BOARD) -> TraceGame:
    """Build the trace game for one scenario.

    Parameters
    ----------
    inputs : TraceInputs
        The world, the scenario's storm and damage, the registry and the reference run.
    board_size : str
        One of ``BOARD_CHOICES``.

    Returns
    -------
    TraceGame
        ``game/`` and ``answer/`` files, and the answer's tables for CSV.

    Raises
    ------
    swm.trace_game.drills.DrillError
        If a rule card prints a drill answer the engine does not reproduce.

    Spec: Work Order 9, H1-H9.
    """
    return TraceGame(game_files(inputs, board_size), *_answer(inputs))


def game_files(inputs: TraceInputs, board_size: str = DEFAULT_BOARD) -> dict[str, bytes]:
    """Return everything a player gets; built without the reference run (H10)."""
    cards = rule_cards(inputs.rules)
    for card in cards:
        verify(card.name, card.expected, inputs.rules)
    manual_draft, manual = pages_of(FIELD_MANUAL, "Field manual", inputs.rules)
    return {
        "field_manual.pdf": text_pdf(manual, manual_draft),
        "rule_cards.pdf": rule_cards_pdf(cards),
        "node_cards.pdf": node_cards_pdf(node_cards(inputs)),
        "board.pdf": board_pdf(inputs, board_size),
        "briefing.pdf": briefing_pdf(inputs, inputs.scenario),
        "sheets.pdf": sheets_pdf(inputs),
        "tokens.pdf": tokens_pdf(inputs),
    }


def _answer(inputs: TraceInputs) -> tuple[dict[str, bytes], dict[str, list[dict[str, object]]]]:
    debrief_draft, debrief = pages_of(DEBRIEF, "Debrief", inputs.rules)
    files = {"answer.pdf": answer_pdf(inputs), "debrief.pdf": text_pdf(debrief, debrief_draft)}
    score = answer_score(inputs.run, inputs.world)
    tables: dict[str, list[dict[str, object]]] = {
        "events": answer_events(inputs.run),
        "outages": answer_outages(inputs.run, inputs.world),
        "score": [dict(score)],
    }
    return files, tables
