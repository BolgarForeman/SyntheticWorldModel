"""The Theta List: every modelling choice behind the constructed world's truth, θ*.

Each registry rule that is not world content is one entry, and each choice that carries no
number of its own (the minimum rule, the transfer forms, the recovery form, pro rata sharing,
the crew order, the time step and settling, the window) is a standalone entry in the registry's
``theta`` list. A rule named by a standalone entry is covered by it and has no entry of its
own. The objectives are listed apart: they are the questions posed of a world, outside Θ.

Spec: structure v0.9 §4.5 (the Theta List); Work Order 7, Part C; ruling D10.
"""

from collections.abc import Iterable
from dataclasses import dataclass

from swm.rules.registry import (
    Flattened,
    Registry,
    Relaxed,
    Rule,
    Ruling,
    ThetaDomain,
    ThetaRole,
    ThetaSymbol,
)

TRUTH_SUB_TYPES = (ThetaRole.DYNAMICS, ThetaRole.STOPPING, ThetaRole.ANALYSIS)
"""The truth domain's sub-types, printed in this order; construction has its own section."""


@dataclass(frozen=True)
class Entry:
    """One Theta List entry (C2)."""

    theta_id: str
    domain: ThetaDomain
    sub_type: ThetaRole
    symbol: ThetaSymbol
    chosen: str
    alternatives: tuple[str, ...]
    registry_ids: tuple[str, ...]
    relaxed: Relaxed | None
    carried_vs_flattened: Flattened
    sensitivity: str
    ruling: Ruling | None


def theta_list(registry: Registry) -> tuple[Entry, ...]:
    """Return every Theta entry of the truth domain, ordered by sub-type then id.

    Parameters
    ----------
    registry : Registry
        The modeling rules registry.

    Returns
    -------
    tuple of Entry
        The standalone entries and one entry per rule that is neither world content nor
        covered by a standalone entry.

    Spec: Work Order 7, C2-C3.
    """
    covered = {rule_id for entry in registry.theta for rule_id in entry.registry_ids}
    entries = [
        Entry(e.theta_id, e.domain, e.sub_type, e.symbol, e.chosen, e.alternatives,
              e.registry_ids, e.relaxed, e.carried_vs_flattened, e.sensitivity, e.ruling)
        for e in registry.theta
    ]  # fmt: skip
    entries += [
        _from_rule(rule)
        for rule in registry.rules
        if rule.theta_role != ThetaRole.WORLD_CONTENT and rule.id not in covered
    ]
    order = {role: i for i, role in enumerate((*TRUTH_SUB_TYPES, ThetaRole.CONSTRUCTION))}
    return tuple(sorted(entries, key=lambda e: (order[e.sub_type], e.theta_id)))


def _from_rule(rule: Rule) -> Entry:
    # The registry guarantees a Theta entry's domain and symbol (Rule._theta).
    return Entry(
        theta_id=rule.id,
        domain=rule.theta_domain or ThetaDomain.TRUTH,
        sub_type=rule.theta_role,
        symbol=rule.theta_symbol or ThetaSymbol.NONE,
        chosen=f"{rule.title}: {_value_text(rule)}.",
        alternatives=rule.theta_alternatives,
        registry_ids=(rule.id,),
        relaxed=rule.relaxed,
        carried_vs_flattened=Flattened.KEEPS,
        sensitivity=rule.theta_sensitivity,
        ruling=rule.ruling,
    )


def _value_text(rule: Rule) -> str:
    value = rule.value
    if isinstance(value, bool):
        return "yes" if value else "no"
    if isinstance(value, int | float):
        return f"{value:g} {rule.units}" if rule.units else f"{value:g}"
    if isinstance(value, str):
        return value
    if isinstance(value, list) and all(isinstance(item, str) for item in value):
        return "; ".join(value)
    return "the table in the registry"


def theta_text(registry: Registry, relaxed_limits: Iterable[str] = ()) -> str:
    """Return the Theta List as text: the truth domain by sub-type, construction, objectives.

    Parameters
    ----------
    registry : Registry
        The modeling rules registry.
    relaxed_limits : iterable of str
        Rule ids a run relaxed; their entries are marked (D11).

    Returns
    -------
    str
        The list, deterministic for a given registry.

    Spec: Work Order 7, C4.
    """
    relaxed = frozenset(relaxed_limits)
    entries = theta_list(registry)
    lines = [f"Theta List, truth domain (θ*): registry {registry.version}, {registry.sha256}"]
    for sub_type in TRUTH_SUB_TYPES:
        lines += _section(sub_type.value, [e for e in entries if e.sub_type == sub_type], relaxed)
    construction = [e for e in entries if e.sub_type == ThetaRole.CONSTRUCTION]
    lines += _section("construction choices", construction, relaxed)
    lines += ["", f"== objectives, outside Θ ({len(registry.objectives)}) =="]
    lines += [f"- {o.name}: {o.description}" for o in registry.objectives]
    return "\n".join(lines) + "\n"


def _section(title: str, entries: list[Entry], relaxed: frozenset[str]) -> list[str]:
    lines = ["", f"== {title} ({len(entries)}) =="]
    for e in entries:
        lines.append(f"{e.theta_id} [{e.symbol.value}]: {e.chosen}")
        mark = " (relaxed in this run)" if relaxed & set(e.registry_ids) else ""
        ruling = f"decision {e.ruling.decision}, {e.ruling.date}" if e.ruling else "none"
        lines.append(
            "    alternatives: " + ("; ".join(e.alternatives) or "none recorded")
            + f" | relaxed: {e.relaxed.value if e.relaxed else 'not a limit'}{mark}"
            + f" | flattened run: {e.carried_vs_flattened.value}"
            + f" | sensitivity: {e.sensitivity} | ruling: {ruling}"
            + f" | registry: {', '.join(e.registry_ids) or 'none'}"
        )  # fmt: skip
    return lines


def classification_counts(registry: Registry) -> dict[str, int]:
    """Return how many rules each Theta role holds, world content included (C3).

    Parameters
    ----------
    registry : Registry
        The modeling rules registry.

    Returns
    -------
    dict of str to int
        Rules per role, in the role order.

    Spec: Work Order 7, C3.
    """
    return {
        role.value: sum(1 for rule in registry.rules if rule.theta_role == role)
        for role in ThetaRole
    }
