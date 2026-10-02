"""World check: with no storm, nothing is damaged in any scenario.

Spec: Work Order 6, G1.
"""

from swm.stages.scenarios import ScenariosResult
from swm.stages.storm import StormResult


def calm_world_problems(storm: StormResult, scenarios: ScenariosResult) -> list[str]:
    """Return every element damaged in a world with no storm; an empty list passes.

    Parameters
    ----------
    storm : StormResult
        The storm stage's output.
    scenarios : ScenariosResult
        The scenarios stage's output.

    Returns
    -------
    list of str
        One line per damaged element when the severity is 0 (or the storm is off); always
        empty when there is a storm, since then damage is expected.

    Spec: Work Order 6, G1.
    """
    if storm.severity > 0:
        return []
    problems = []
    for scenario in scenarios.scenarios:
        for line in scenario.failed_lines:
            problems.append(f"scenario {scenario.index}: line {line.line_id} failed with no storm")
        for damage in scenario.facilities:
            problems.append(
                f"scenario {scenario.index}: facility {damage.node_id} damaged with no storm"
            )
    return problems
