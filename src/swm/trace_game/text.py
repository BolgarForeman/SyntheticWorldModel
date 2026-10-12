"""The game's fixed wording: rule cards, field manual and debrief, read from reviewed text files.

The wording lives in ``docs/design/trace_game/`` and is reviewed like the spec (ruling P9). A
rule card's text holds registry placeholders, ``{rule.id}`` or ``{rule.id.key}``, that are
filled at build from the registry, so no rule value is typed (WO 9, H3). Until the design side
supplies its wording, a file opens with ``DRAFT`` and every page printed from it says so; the
field manual and debrief print a DRAFT placeholder page while their files are absent (H9).

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
PLACEHOLDER = re.compile(r"\{([a-z0-9_.]+)\}")


@dataclass(frozen=True)
class Edge:
    """One arrow of a rule card's illustration: from, to and its label."""

    start: str
    end: str
    label: str


@dataclass(frozen=True)
class RuleCard:
    """One rule card: the rule, its registry values, its illustration and its drill."""

    name: str
    title: str
    value_ids: tuple[str, ...]
    rule: str
    illustration: tuple[Edge, ...]
    drill: str
    answer: str
    expect: float
    draft: bool


def rule_cards(rules: Registry, folder: Path = RULE_CARD_DIR) -> tuple[RuleCard, ...]:
    """Read every rule card, in file order, with its placeholders filled from the registry.

    Parameters
    ----------
    rules : Registry
        The modeling rules in force.
    folder : Path
        The folder of card text files.

    Returns
    -------
    tuple of RuleCard
        The cards in the order of their file names.

    Spec: Work Order 9, H3.
    """
    cards = []
    for path in sorted(folder.glob("*.txt")):
        body = path.read_text(encoding="utf-8")
        fields = _fields(body)
        cards.append(RuleCard(
            name=path.stem.split("_", 1)[1],
            title=fields["title"],
            value_ids=tuple(v.strip() for v in fields["values"].split(";") if v.strip()),
            rule=fill(fields["rule"], rules),
            illustration=tuple(_edge(e) for e in fields["illustration"].split(";") if e.strip()),
            drill=fill(fields["drill"], rules),
            answer=fill(fields["answer"], rules),
            expect=float(fields["expect"]),
            draft=body.startswith(DRAFT),
        ))  # fmt: skip
    return tuple(cards)


def _fields(body: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    for line in body.splitlines()[1:] if body.startswith(DRAFT) else body.splitlines():
        key, _, value = line.partition(":")
        if key.strip():
            fields[key.strip()] = value.strip()
    return fields


def _edge(text: str) -> Edge:
    start, _, rest = text.strip().partition("->")
    end, _, label = rest.strip().partition(" ")
    return Edge(start.strip(), end.strip(), label.strip())


def fill(text: str, rules: Registry) -> str:
    """Replace every ``{rule.id}`` or ``{rule.id.key}`` with the registry's value."""
    return PLACEHOLDER.sub(lambda match: value_text(lookup(match.group(1), rules)), text)


def lookup(path: str, rules: Registry) -> Any:
    """Return a registry value by rule id, or a key inside a rule's value (``rule.id.key``)."""
    if rules.has(path):
        return rules.value(path)
    rule_id, _, key = path.rpartition(".")
    if not rules.has(rule_id):
        raise KeyError(f"no registry rule for the placeholder {{{path}}}")
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


def pages_of(path: Path, title: str) -> tuple[bool, list[str]]:
    """Return a text file's lines and whether it is DRAFT; a missing file is a DRAFT placeholder.

    Parameters
    ----------
    path : Path
        The Markdown file.
    title : str
        What the page is, for the placeholder.

    Returns
    -------
    tuple of (bool, list of str)
        Whether it is DRAFT, and its lines.

    Spec: Work Order 9, H9.
    """
    if not path.exists():
        return True, [
            f"{DRAFT}: {title}",
            "",
            "This page is a placeholder. The design side writes this text and Foreman rules on",
            f"it; the build then typesets it from {_shown(path)}.",
        ]
    lines = path.read_text(encoding="utf-8").splitlines()
    return bool(lines) and lines[0].startswith(DRAFT), lines


def _shown(path: Path) -> str:
    """Return a path as the repository names it, the same on every platform."""
    root = TEXT_DIR.parents[2]
    return path.relative_to(root).as_posix() if path.is_relative_to(root) else path.name
