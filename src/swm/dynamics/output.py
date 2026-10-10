"""A run as plain tables and text: the reference-run files and the trajectory printout.

Numbers are rounded to six decimals so the files are identical on every platform; a stock
relaxed to unlimited reads ``inf``. Writing the files is ``swm.recipe.io``'s.

Spec: structure v0.9 §4.5 (saved reference runs); Work Order 7, E1-E3.
"""

import math
from collections.abc import Mapping, Sequence

from swm.dynamics.records import Run

PLACES = 6


def _number(value: float) -> float | str:
    return "inf" if math.isinf(value) else round(value, PLACES)


def state_rows(run: Run) -> list[dict[str, object]]:
    """Return every node's state at every step, one row per step.

    Parameters
    ----------
    run : Run
        The run.

    Returns
    -------
    list of dict
        ``hour`` then one column per node, in node order.

    Spec: Work Order 7, E2.
    """
    return [
        {"hour": _number(t), **{n: _number(v) for n, v in zip(run.node_ids, row, strict=True)}}
        for t, row in zip(run.times, run.states, strict=True)
    ]


def stock_rows(run: Run) -> list[dict[str, object]]:
    """Return every stock's level at every step, one row per step (Work Order 7, E2)."""
    return [
        {"hour": _number(t), **{s: _number(v) for s, v in zip(run.stock_ids, row, strict=True)}}
        for t, row in zip(run.times, run.levels, strict=True)
    ]


def crew_rows(run: Run) -> list[dict[str, object]]:
    """Return every stretch of every crew's time: job, activity, start and end (E2)."""
    return [
        {
            "crew": entry.crew_id,
            "job": entry.job_id,
            "activity": entry.activity,
            "start_h": _number(entry.start_h),
            "end_h": _number(entry.end_h),
        }
        for _, entries in run.crews
        for entry in entries
    ]


def run_record(run: Run, stamp: Mapping[str, object]) -> dict[str, object]:
    """Return a run's record: its stamp, summary, completions, deliveries and hours out.

    Parameters
    ----------
    run : Run
        The run.
    stamp : Mapping
        The θ* stamp of the world it ran on (registry, overrides, relaxed limits).

    Returns
    -------
    dict
        Plain data for canonical YAML.

    Spec: structure v0.9 §4.5 (stamped with the horizon and the policy); Work Order 7, E2.
    """
    request = run.request
    return {
        "modeling_rules": dict(stamp),
        "scenario": request.scenario,
        "horizon_h": _number(run.horizon_h),
        "step_h": _number(run.step_h),
        "policy": request.policy,
        "relaxed_limits": sorted(request.relaxed),
        "removed_dependencies": list(request.removed),
        "actions": [repr(action) for action in request.actions],
        "summary": run.summary(),
        "hours_out": {n: _number(h) for n, h in sorted(run.hours_out.items())},
        "completions": [
            {"element": c.element_id, "kind": c.kind, "hour": _number(c.time_h)}
            for c in run.completions
        ],
        "deliveries": [
            {
                "edge": d.edge_id,
                "consumer": d.consumer_id,
                "hour": _number(d.time_h),
                "amount": _number(d.amount),
            }
            for d in run.deliveries
        ],
        "passes": {"most": max(run.passes, default=0), "capped_steps": list(run.capped)},
    }


def trajectory_text(run: Run, end_use: Sequence[str], node_id: str | None = None) -> str:
    """Return the hourly trajectory table: end-use states and the stocks that are draining.

    Parameters
    ----------
    run : Run
        The run.
    end_use : sequence of str
        The end-use nodes, in the order to print.
    node_id : str or None
        If given, print this one node at every step instead.

    Returns
    -------
    str
        A plain-text table.

    Spec: Work Order 7, E1.
    """
    if node_id is not None:
        rows = [f"{'hour':>7} {node_id}"]
        rows += [f"{t:7.2f} {s:.4f}" for t, s in zip(run.times, run.state(node_id), strict=True)]
        return "\n".join(rows) + "\n"
    per_hour = int(1.0 / run.step_h + 0.5)
    header = f"{'hour':>5} " + " ".join(f"{n[-8:]:>8}" for n in end_use) + "  draining"
    rows = [header]
    for index in range(0, len(run.times), per_hour):
        states = " ".join(f"{run.state(n)[index]:8.3f}" for n in end_use)
        draining = _draining(run, index)
        rows.append(f"{run.times[index]:5.0f} {states}  {draining}")
    return "\n".join(rows) + "\n"


def _draining(run: Run, index: int) -> str:
    if index == 0:
        return ""
    names = [
        stock_id
        for column, stock_id in enumerate(run.stock_ids)
        if run.levels[index][column] < run.levels[index - 1][column]
    ]
    return ", ".join(names)
