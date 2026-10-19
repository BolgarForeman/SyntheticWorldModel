"""The game's fixed wording: rule cards, field manual and debrief, read from reviewed text files.

The wording lives in ``docs/design/trace_game/`` as Markdown and is reviewed like the spec
(ruling P9); the design side drafts it and Foreman rules on it. A ``{rule:<id>}`` placeholder
(or ``{rule:<id>.<key>}``) is filled at build from the registry, so no rule value is typed
(WO 9, H3). A file whose opening comment says ``Draft`` prints marked DRAFT; a missing file
prints a DRAFT placeholder page (H9).

A rule card's file holds a ``# N. Title``, a ``## Front``, a ``## Back`` and a ``## Drill world``
section; the drill world is the engine test's specification and is not printed.

Spec: Work Order 9, H3 and H9; Trace pack ruling sheet v0.2, P4, P8 and P9.
"""

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from swm.rules.registry import Registry

TEXT_DIR = Path(__file__).resolve().parents[3] / "docs" / "design" / "trace_game"
"""The reviewed wording, beside the spec (ruling P9)."""
RULE_CARD_DIR = TEXT_DIR / "rule_cards"
FIELD_MANUAL = TEXT_DIR / "field_manual.md"
DEBRIEF = TEXT_DIR / "debrief.md"
DRAFT = "DRAFT"
DRILL_WORLD = "Drill world (for the engine test, not printed)"
PLACEHOLDER = re.compile(r"\{rule:([a-z0-9_.]+)\}")
COMMENT = re.compile(r"<!--(.*?)-->", re.DOTALL)
BOLD_NUMBER = re.compile(r"\*\*([0-9]+(?:\.[0-9]+)?)\b")


@dataclass(frozen=True)
class RuleCard:
    """One rule card: its title, front and back as printable lines, and its drill world."""

    number: int
    name: str
    title: str
    front: tuple[str, ...]
    back: tuple[str, ...]
    answer: str
    """The back's answer, as written: its bold numbers are what the engine must reproduce."""
    drill_world: str
    draft: bool

    @property
    def expected(self) -> tuple[float, ...]:
        """Return the answer's bold numbers, in order: the drill's printed results."""
        return tuple(float(n) for n in BOLD_NUMBER.findall(self.answer))


def rule_cards(rules: Registry, folder: Path = RULE_CARD_DIR) -> tuple[RuleCard, ...]:
    """Read every rule card, in file order, with its placeholders filled from the registry.

    Parameters
    ----------
    rules : Registry
        The modeling rules in force.
    folder : Path
        The folder of card files.

    Returns
    -------
    tuple of RuleCard
        The cards in the order of their file names.

    Spec: Work Order 9, H3.
    """
    cards = []
    for path in sorted(folder.glob("*.md")):
        raw = path.read_text(encoding="utf-8")
        sections = _sections(COMMENT.sub("", raw))
        number, _, title = sections["title"].partition(". ")
        back = fill(sections["Back"], rules)
        cards.append(RuleCard(
            number=int(number),
            name=path.stem.split("_", 1)[1],
            title=title.strip(),
            front=tuple(printable(fill(sections["Front"], rules))),
            back=tuple(printable(back)),
            answer=_answer(back),
            drill_world=sections.get(DRILL_WORLD, ""),
            draft=_is_draft(raw),
        ))  # fmt: skip
    return tuple(cards)


def _sections(text: str) -> dict[str, str]:
    """Split a card into its ``# title`` and ``## section`` bodies."""
    sections: dict[str, list[str]] = {}
    current = ""
    for line in text.splitlines():
        if line.startswith("# "):
            sections["title"] = [line[2:].strip()]
            current = ""
        elif line.startswith("## "):
            current = line[3:].strip()
            sections[current] = []
        elif current:
            sections[current].append(line)
    return {name: "\n".join(lines).strip() for name, lines in sections.items()}


def _answer(back: str) -> str:
    for line in back.splitlines():
        if line.startswith("**Answer:**"):
            return line.removeprefix("**Answer:**").strip()
    return ""


def _is_draft(raw: str) -> bool:
    """Return whether a file's opening comment marks it a draft ("Drafted by" does not)."""
    match = COMMENT.search(raw)
    return match is not None and DRAFT_WORD.search(match.group(1)) is not None


DRAFT_WORD = re.compile(r"\bdraft\b", re.IGNORECASE)


GLYPHS = {"⏳": "◷"}
"""CHOICE: the bundled font (DejaVu) has no ⏳ (U+23F3), which would print as a box; the cards
print ◷ (U+25F7), the fallback symbol of the node cards and the legend, in its place."""


def printable(markdown: str) -> list[str]:
    """Return Markdown as plain printed lines: no emphasis marks, list items bulleted."""
    lines = []
    for line in markdown.splitlines():
        line = line.replace("**", "")
        for missing, shown in GLYPHS.items():
            line = line.replace(missing, shown)
        if line.startswith("- "):
            line = "• " + line[2:]
        lines.append(line.rstrip())
    return lines


def fill(text: str, rules: Registry) -> str:
    """Replace every ``{rule:<id>}`` or ``{rule:<id>.<key>}`` with the registry's value."""
    return PLACEHOLDER.sub(lambda match: value_text(lookup(match.group(1), rules)), text)


def lookup(path: str, rules: Registry) -> Any:
    """Return a registry value by rule id, or a key inside a rule's value (``rule.id.key``)."""
    if rules.has(path):
        return rules.value(path)
    rule_id, _, key = path.rpartition(".")
    if not rules.has(rule_id):
        raise KeyError(f"no registry rule for the placeholder {{rule:{path}}}")
    return rules.value(rule_id)[key]


def value_text(value: Any) -> str:
    """Print a registry value as a card shows it: 24 not 24.0, lists joined, text as it is."""
    if isinstance(value, bool):
        return "yes" if value else "no"
    if isinstance(value, float):
        return f"{value:g}"
    if isinstance(value, list | tuple):
        return "; ".join(value_text(v) for v in value)
    if isinstance(value, dict):
        return ", ".join(f"{k} {value_text(v)}" for k, v in value.items())
    return str(value)


def pages_of(path: Path, title: str, rules: Registry | None = None) -> tuple[bool, list[str]]:
    """Return a document's printable lines and whether it is DRAFT.

    A missing file is a DRAFT placeholder page.

    Parameters
    ----------
    path : Path
        The Markdown file.
    title : str
        What the document is, for the placeholder.
    rules : Registry or None
        The registry, to fill any ``{rule:<id>}`` placeholders.

    Returns
    -------
    tuple of (bool, list of str)
        Whether it is DRAFT, and its lines (headings keep their ``#``).

    Spec: Work Order 9, H9.
    """
    if not path.exists():
        return True, [
            f"{DRAFT}: {title}",
            "",
            "This page is a placeholder. The design side writes this text and Foreman rules on",
            f"it; the build then typesets it from {_shown(path)}.",
        ]
    raw = path.read_text(encoding="utf-8")
    body = COMMENT.sub("", raw).strip()
    if rules is not None:
        body = fill(body, rules)
    return _is_draft(raw), printable(body)


def _shown(path: Path) -> str:
    """Return a path as the repository names it, the same on every platform."""
    root = TEXT_DIR.parents[2]
    return path.relative_to(root).as_posix() if path.is_relative_to(root) else path.name
