import copy
from typing import Any

import pytest
import yaml
from pydantic import ValidationError

from swm.cli import main
from swm.recipe.resolve import resolve
from swm.recipe.schema import Recipe
from swm.rules.registry import (
    Relaxed,
    ThetaDomain,
    ThetaRole,
    load_registry,
    parse_registry,
    registry_bytes,
)
from swm.rules.theta import classification_counts, theta_list, theta_text

RULES = load_registry()


def registry_with_rule(**changes: Any) -> Any:
    data = yaml.safe_load(registry_bytes().decode("utf-8"))
    rule = copy.deepcopy(data["rules"][0])
    rule.update(id="test.rule", **changes)
    data["rules"].append(rule)
    return parse_registry(yaml.safe_dump(data, allow_unicode=True).encode("utf-8"))


# --- Limits: ranges and relaxed values (B1) -------------------------------------------------


def test_every_limit_has_a_range_or_is_marked_range_open() -> None:
    limits = [rule for rule in RULES.rules if rule.is_limit]
    assert len(limits) >= 40
    for rule in limits:
        assert rule.range is not None or rule.range_open, rule.id
    assert all(r.range is None and not r.range_open for r in RULES.rules if not r.is_limit)


@pytest.mark.parametrize(
    ("rule_id", "value", "bounds", "relaxed"),
    [
        ("reserves.generation.purified_water_h", 24.0, [6.0, 48.0], Relaxed.UNLIMITED),
        ("reserves.data_centre.makeup_water_h", 12.0, [0.0, 48.0], Relaxed.UNLIMITED),
        ("reserves.seaport.backup_power_h", 0.0, [0.0, 48.0], Relaxed.UNLIMITED),
        ("repair.manual_switching_h", 1.0, [0.5, 2.0], Relaxed.ZERO),
    ],
)
def test_the_ruled_ranges(
    rule_id: str, value: float, bounds: list[float], relaxed: Relaxed
) -> None:
    rule = RULES.rule(rule_id)
    assert rule.value == value
    assert rule.range == bounds
    assert not rule.range_open
    assert rule.relaxed == relaxed


@pytest.mark.parametrize(
    ("rule_id", "value", "relaxed"),
    [
        ("reserves.battery_recharge_h", 12.0, Relaxed.ZERO),
        ("repair.crew_bound_lead_h", 2.0, Relaxed.ZERO),
        ("reserves.hospital.generator_fuel_h", 72.0, Relaxed.UNLIMITED),
        ("crews.road_speed_kmh", 40.0, Relaxed.UNLIMITED),
    ],
)
def test_unruled_ranges_are_default_to_default_and_open(
    rule_id: str, value: float, relaxed: Relaxed
) -> None:
    rule = RULES.rule(rule_id)
    assert rule.value == value
    assert rule.range == [value, value]
    assert rule.range_open
    assert rule.relaxed == relaxed


def test_every_shipped_limit_lies_within_its_range() -> None:
    # A recipe may override a limit outside its range for a sensitivity run; the shipped
    # default always lies within it.
    for rule in RULES.rules:
        if rule.range is None:
            continue
        if isinstance(rule.value, dict):
            for key, (low, high) in rule.range.items():
                assert low <= rule.value[key] <= high, (rule.id, key)
        else:
            low, high = rule.range
            assert low <= rule.value <= high, rule.id


def test_every_tolerance_row_relaxes_to_zero_loss() -> None:
    rows = [r for r in RULES.rules if r.id.startswith("tolerance.")]
    assert len(rows) == 17
    assert all(r.relaxed == Relaxed.ZERO for r in rows)


@pytest.mark.parametrize(
    ("rule_id", "value"),
    [
        ("dynamics.trip_point", 0.9),
        ("dynamics.threshold", 0.5),
        ("dynamics.step_min", 15.0),
        ("dynamics.settling_cap_passes", 100.0),
        ("dynamics.horizon_h", 72.0),
        ("reserves.hospital.essential_load_fraction", 0.6),
    ],
)
def test_the_dynamics_rules(rule_id: str, value: float) -> None:
    assert RULES.value(rule_id) == value
    assert RULES.rule(rule_id).ruling is not None


def test_a_limit_without_a_range_or_a_range_without_a_limit_is_refused() -> None:
    with pytest.raises(ValidationError, match="needs a range"):
        registry_with_rule(relaxed="zero", theta_role="dynamics", theta_domain="truth",
                           theta_symbol="R")  # fmt: skip
    with pytest.raises(ValidationError, match="belongs to a limit"):
        registry_with_rule(range=[1, 2], theta_role="dynamics", theta_domain="truth",
                           theta_symbol="R")  # fmt: skip


# --- The Theta List (C1-C4) -----------------------------------------------------------------


def test_every_rule_is_classified() -> None:
    counts = classification_counts(RULES)
    assert sum(counts.values()) == len(RULES.rules)
    assert counts == {"construction": 169, "dynamics": 112, "stopping": 1, "analysis": 0,
                      "world_content": 89}  # fmt: skip
    for rule in RULES.rules:
        if rule.theta_role == ThetaRole.WORLD_CONTENT:
            assert rule.theta_domain is None
        else:
            assert rule.theta_domain == ThetaDomain.TRUTH


def test_a_rule_without_a_theta_role_is_refused() -> None:
    data = yaml.safe_load(registry_bytes().decode("utf-8"))
    del data["rules"][0]["theta_role"]
    with pytest.raises(ValidationError, match="theta_role"):
        parse_registry(yaml.safe_dump(data, allow_unicode=True).encode("utf-8"))


def test_the_numberless_choices_have_their_own_entries() -> None:
    ids = {e.theta_id for e in theta_list(RULES)}
    assert {"theta.minimum_rule", "theta.transfer_forms", "theta.recovery_form",
            "theta.pro_rata_sharing", "theta.crew_order", "theta.time_step_and_settling",
            "theta.window"} <= ids  # fmt: skip
    window = next(e for e in theta_list(RULES) if e.theta_id == "theta.window")
    assert window.sub_type == ThetaRole.STOPPING
    # A rule a standalone entry covers has no entry of its own.
    assert "dynamics.crew_order" not in ids
    assert "dynamics.horizon_h" not in ids


def test_every_theta_entry_is_complete() -> None:
    entries = theta_list(RULES)
    assert len(entries) == 285
    for e in entries:
        assert e.chosen
        assert e.registry_ids or e.theta_id.startswith("theta.")
        assert e.sensitivity == "none planned" or e.sensitivity.startswith(("planned: ", "run: "))
        assert e.domain == ThetaDomain.TRUTH


def test_swm_rules_theta_is_deterministic_and_keeps_objectives_outside(
    capsysbinary: pytest.CaptureFixture[bytes],
) -> None:
    assert main(["rules", "--theta"]) == 0
    first = capsysbinary.readouterr().out
    assert main(["rules", "--theta"]) == 0
    assert capsysbinary.readouterr().out == first
    text = first.decode("utf-8")
    assert text == theta_text(RULES)
    body, objectives = text.split("== objectives, outside Θ (3) ==")
    for name in ("metric", "acceptability threshold", "service weights"):
        assert f"- {name}:" in objectives
        assert f"\n{name} [" not in body
    sections = [line for line in body.splitlines() if line.startswith("==")]
    assert sections == ["== dynamics (114) ==", "== stopping (1) ==", "== analysis (1) ==",
                        "== construction choices (169) =="]  # fmt: skip


def test_a_relaxed_limit_is_marked_in_the_list() -> None:
    text = theta_text(RULES, ["repair.manual_switching_h"])
    marked = [line for line in text.splitlines() if "relaxed in this run" in line]
    assert len(marked) == 1
    assert "registry: repair.manual_switching_h" in marked[0]


# --- The recipe's relaxed limits (B2-B3) ----------------------------------------------------


def test_relaxing_a_rule_that_is_not_a_limit_is_refused() -> None:
    recipe = Recipe.model_validate({"modeling_rules": {"relaxed_limits": ["dynamics.trip_point"]}})
    with pytest.raises(ValueError, match="is not a limit"):
        resolve(recipe)


def test_relaxed_limits_are_sorted_in_the_resolved_recipe() -> None:
    recipe = Recipe.model_validate(
        {"modeling_rules": {"relaxed_limits": ["repair.manual_switching_h", "crews.pilot"]}}
    )
    resolved = resolve(recipe).recipe
    assert resolved.modeling_rules.relaxed_limits == ("crews.pilot", "repair.manual_switching_h")


# --- PR 15 answers --------------------------------------------------------------------------


def test_the_symbols_follow_appendix_a() -> None:
    by_stage: dict[str, set[str]] = {}
    for rule in RULES.rules:
        if rule.theta_symbol is not None:
            by_stage.setdefault(rule.stage.value, set()).add(rule.theta_symbol.value)
    assert by_stage["failure_modes"] == {"g_δ"}
    assert by_stage["tolerance"] == {"g_δ"}
    assert by_stage["storm"] == {"none"}
    assert by_stage["repair"] == {"R"}
    assert RULES.rule("reserves.hospital.essential_load_fraction").theta_symbol == "g_δ"
    assert RULES.rule("dynamics.trip_point").theta_symbol == "g_δ"
    assert {r.theta_symbol for r in RULES.rules if r.stage.value == "reserves"} == {"h_φ", "g_δ"}


def test_performance_is_the_one_analysis_entry() -> None:
    analysis = [e for e in theta_list(RULES) if e.sub_type == ThetaRole.ANALYSIS]
    assert [e.theta_id for e in analysis] == ["theta.performance"]
    assert analysis[0].symbol == "χ"
    assert "service-hours" in analysis[0].chosen


def test_pump_capacity_is_an_unlimited_limit_with_an_open_range() -> None:
    rule = RULES.rule("reserves.pumping.capacity")
    assert rule.relaxed == Relaxed.UNLIMITED
    assert rule.range_open
    assert rule.range is None
    assert "capacity_m3_per_day" in rule.value


@pytest.mark.parametrize(
    "rule_id",
    [
        "reserves.data_centre.makeup_water_h",
        "reserves.generation.purified_water_h",
        "reserves.seaport.backup_power_h",
    ],
)
def test_the_new_stocks_cite_verified_sources(rule_id: str) -> None:
    first = RULES.rule(rule_id).sources[0]
    assert first.verified is True
    assert first.url is not None
    assert first.url.startswith("https://")
    assert first.quote


def test_an_override_outside_a_ruled_range_is_noted_but_allowed() -> None:
    recipe = Recipe.model_validate(
        {
            "modeling_rules": {
                "overrides": {"repair.manual_switching_h": 3.0, "reserves.hospital.water_h": 200.0}
            }
        }
    )
    rules = resolve(recipe).recipe.modeling_rules
    assert rules.out_of_range == (
        "repair.manual_switching_h = 3 lies outside its ruled range 0.5-2",
    )
    crews = Recipe.model_validate(
        {"modeling_rules": {"overrides": {"crews.pilot": {"crews": 5, "pools": 1, "crew_bases": 1,
                                                          "mobile_substations": 1,
                                                          "mobile_cell_sites": 1}}}}
    )  # fmt: skip
    # crews.pilot's range is open (only the crew count was ruled), so nothing is noted.
    assert resolve(crews).recipe.modeling_rules.out_of_range == ()
    inside = Recipe.model_validate(
        {"modeling_rules": {"overrides": {"repair.manual_switching_h": 2.0}}}
    )
    assert resolve(inside).recipe.modeling_rules.out_of_range == ()
