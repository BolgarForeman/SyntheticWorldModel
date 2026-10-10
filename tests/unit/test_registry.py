import ast
import copy
import importlib.util
from pathlib import Path
from typing import Any

import pytest
import yaml
from pydantic import ValidationError

from swm.recipe.dependencies import DEPENDENCY_TABLE
from swm.recipe.resolve import resolve
from swm.recipe.schema import Recipe
from swm.rules.page import rules_page_html
from swm.rules.registry import Registry, load_registry, parse_registry, registry_bytes

ROOT = Path(__file__).resolve().parents[2]
STAGES = ROOT / "src" / "swm" / "stages"

VALID_RULE: dict[str, Any] = {
    "id": "requirements.example_mw",
    "title": "Example",
    "stage": "requirements",
    "value": 1.0,
    "units": "MW",
    "grade": "J",
    "sources": [{"citation": "A source"}],
    "reasoning": "Why this value.",
    "status": "ruled",
    "theta_role": "world_content",
}


def registry_with(**changes: Any) -> Registry:
    rule = {**copy.deepcopy(VALID_RULE), **changes}
    return Registry.model_validate({"version": "test", "rules": [rule]})


# --- Validation (A3, A5) --------------------------------------------------------------------


def test_the_shipped_registry_validates_with_unique_ids() -> None:
    registry = load_registry()
    ids = [rule.id for rule in registry.rules]
    assert len(ids) == len(set(ids))
    assert registry.version
    assert len(registry.sha256) == 64


def test_a_valid_entry_passes() -> None:
    assert registry_with().number("requirements.example_mw") == 1.0


@pytest.mark.parametrize(
    ("changes", "message"),
    [
        ({"reasoning": ""}, "reasoning"),
        ({"sources": []}, "at least one source"),
        ({"units": None}, "needs units"),
        ({"grade": None}, "needs a grade"),
        ({"id": "no_dots"}, "id"),
        ({"stage": "weather"}, "stage"),
    ],
)
def test_an_incomplete_entry_fails_validation(changes: dict[str, Any], message: str) -> None:
    with pytest.raises(ValidationError, match=message):
        registry_with(**changes)


def test_a_placeholder_needs_reasoning_but_no_source() -> None:
    registry_with(sources=[], status="placeholder")
    with pytest.raises(ValidationError, match="reasoning"):
        registry_with(sources=[], status="placeholder", reasoning="")


def test_repeated_ids_fail_validation() -> None:
    with pytest.raises(ValidationError, match="repeated"):
        Registry.model_validate({"version": "t", "rules": [VALID_RULE, VALID_RULE]})


def test_the_hash_is_the_file_bytes_hash() -> None:
    import hashlib

    content = registry_bytes()
    assert parse_registry(content).sha256 == hashlib.sha256(content).hexdigest()


# --- What the registry holds (A2) -----------------------------------------------------------


def test_the_dependency_table_lives_in_the_registry_with_its_99_rows() -> None:
    rows = [r for r in load_registry().rules if r.id.startswith("dependencies.table.")]
    assert len(rows) == 99
    assert len(DEPENDENCY_TABLE) == 99


@pytest.mark.parametrize(
    "rule_id",
    [
        "requirements.electricity.tertiary_kw_per_bed",
        "requirements.water.tertiary_m3_per_bed_day",
        "requirements.fuel.lng_gj_per_mwh",
        "requirements.peak_factor",
        "dependencies.rule_4.transmission_threshold_mw",
        "reserves.hospital.generator_fuel_h",
        "reserves.lng.days",
        "reserves.fuel_resupply.lead_time_h",
        "tolerance.generation",
        "tolerance.hospital_records_hosted",
        "failure_modes.defaults",
        "repair.hazus_restoration_days",
        "repair.emergency.mobile_substation",
        "crews.pilot",
        "sizing.power.reserve_margin",
        "layers.subtypes.thermal_fuel",
        "layers.attributes.tertiary",
        "draws.quantile_table",
    ],
)
def test_section_4_4a_and_the_migrated_constants_are_present(rule_id: str) -> None:
    assert load_registry().has(rule_id)


def test_section_4_4a_targets_hold_their_ruled_values() -> None:
    rules = load_registry()
    assert rules.number("requirements.electricity.tertiary_kw_per_bed") == 2.5
    assert rules.number("requirements.electricity.regional_kw_per_bed") == 2.0
    assert rules.number("requirements.electricity.clinic_mw") == 0.027
    assert rules.number("requirements.electricity.mast_mw") == 0.006
    assert rules.number("requirements.electricity.treatment_kwh_per_m3") == 0.37
    assert rules.number("requirements.electricity.refinery_kwh_per_barrel") == 7.0
    assert rules.number("requirements.electricity.data_centre_pue") == 1.57
    assert rules.number("requirements.water.tertiary_m3_per_bed_day") == 1.0
    assert rules.number("requirements.water.regional_m3_per_bed_day") == 0.5
    heat = [rules.number(f"requirements.fuel.{k}_gj_per_mwh") for k in ("lng", "oil", "coal")]
    assert heat == [8.0, 11.8, 11.4]
    assert rules.value("dependencies.rule_4.transmission_threshold_mw") == {
        "11.4": 5.0,
        "22.8": 10.0,
    }
    assert rules.number("requirements.peak_factor") == 1.3
    assert rules.value("tolerance.generation") == {"t_h": 12.0, "d": 0.95}
    assert rules.value("repair.crew_work_h") == {
        "slight": 8.0, "moderate": 24.0, "extensive": 72.0, "complete": 168.0,
    }  # fmt: skip


# --- Overrides and stamping (A3) ------------------------------------------------------------


def test_any_rule_may_be_overridden_by_a_value_of_its_kind() -> None:
    rules = load_registry()
    changed = rules.with_overrides(
        {
            "dependencies.rule_5.tertiary_second_feed_share": 0.8,
            "sizing.power.reserve_margin": 1.5,
            "layers.attributes.airport_size_class": [[0.0, "large_airport"]],
        }
    )
    assert changed.number("dependencies.rule_5.tertiary_second_feed_share") == 0.8
    assert changed.number("sizing.power.reserve_margin") == 1.5
    assert changed.value("layers.attributes.airport_size_class") == [[0.0, "large_airport"]]
    assert rules.number("sizing.power.reserve_margin") == 1.3
    assert [rule_id for rule_id, _ in changed.overrides] == sorted(
        [
            "dependencies.rule_5.tertiary_second_feed_share",
            "sizing.power.reserve_margin",
            "layers.attributes.airport_size_class",
        ]
    )
    assert changed.sha256 == rules.sha256
    with pytest.raises(ValueError, match="holds a number; the override is a text"):
        rules.with_overrides({"sizing.power.reserve_margin": "high"})
    with pytest.raises(KeyError, match="no modeling rule"):
        rules.with_overrides({"requirements.nothing": 1.0})


def test_an_override_reaches_the_layers_and_the_dependency_table() -> None:
    from layers_helpers import build_world
    from swm.recipe.dependencies import resolve_row
    from swm.recipe.schema import Layer, NodeClass
    from swm.stages.layers import build_layers, layers_streams

    recipe, terrain, _ = build_world()
    rules = load_registry().with_overrides(
        {"layers.attributes.airport_size_class": [[0.0, "large_airport"]]}
    )
    overridden = build_layers(recipe.layers, terrain, layers_streams(recipe.root_seed), rules)
    airport = next(n for n in overridden.nodes if n.node_class == NodeClass.AIRPORT)
    assert dict(airport.attributes)["size_class"] == "large_airport"
    row_id = "dependencies.table.power.clinic"
    row = load_registry().value(row_id)
    rules = load_registry().with_overrides({row_id: {**row, "dependency": "optional"}})
    assert resolve_row(Layer.POWER, NodeClass.CLINIC, {}, rules).dependency == "optional"
    assert resolve_row(Layer.POWER, NodeClass.CLINIC, {}).dependency == "core"


def test_the_resolved_recipe_carries_the_registry_hash_and_the_overrides() -> None:
    overrides = {"requirements.peak_factor": 1.5}
    recipe = resolve(Recipe.model_validate({"modeling_rules": {"overrides": overrides}})).recipe
    rules = recipe.modeling_rules
    assert rules.registry_sha256 == load_registry().sha256
    assert rules.registry_version == load_registry().version
    assert rules.overrides == overrides


def test_a_recipe_resolved_against_another_registry_is_refused() -> None:
    other = Recipe.model_validate({"modeling_rules": {"registry_sha256": "0" * 64}})
    with pytest.raises(ValueError, match="resolved against registry"):
        resolve(other)


def test_a_bad_override_is_refused_on_resolution() -> None:
    bad = Recipe.model_validate({"modeling_rules": {"overrides": {"layers.siting.runway_km": "x"}}})
    with pytest.raises(ValueError, match="the override is a text"):
        resolve(bad)


# --- The page (A4, A5) ----------------------------------------------------------------------


def test_the_page_renders_every_rule_and_the_hash() -> None:
    registry = load_registry()
    page = rules_page_html(registry).decode("utf-8")
    for rule in registry.rules:
        assert f'<div class="id">{rule.id}</div>' in page, rule.id
    assert registry.sha256 in page
    assert page.count('<article class="rule"') == len(registry.rules)
    assert 'value="grade-J"' in page
    assert 'value="status-open"' in page


def test_the_page_is_deterministic() -> None:
    assert rules_page_html(load_registry()) == rules_page_html(load_registry())


# --- The draw tables stay in sync with their builder (B3) -----------------------------------


def test_the_quantile_tables_match_the_offline_builder() -> None:
    spec = importlib.util.spec_from_file_location(
        "build_quantile_table", ROOT / "tools" / "build_quantile_table.py"
    )
    assert spec is not None
    assert spec.loader is not None
    builder = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(builder)
    stored = load_registry().value("draws.quantile_table")
    assert tuple(stored["knots"]) == builder.KNOTS
    for table in stored["tables"][::5]:
        rebuilt = builder.solve(table["spread"])
        for kept, fresh in zip(table["quantiles"], rebuilt, strict=True):
            assert kept == pytest.approx(fresh, rel=1e-8, abs=1e-9)


# --- No world-shaping number in the stages (A2) ---------------------------------------------

ALLOWED_LITERALS: dict[str, dict[float, str]] = {
    "layers.py": {
        0: "zero",
        1: "one",
        2: "halves, doubles and pairs",
        -1: "a missing index",
        0.5: "the middle of a line or a range",
        3: "rounding to metres and to three decimals",
        64: "cap on a distance transform (cells)",
        10: "grid step cost of a straight move; decimetres per metre",
        14: "grid step cost of a diagonal move",
        62: "a sentinel beyond any path cost",
        1000: "metres per kilometre",
        1_000_000: "integer quantisation of siting weights",
        -2: "rounding to hundreds",
        4: "the four runway directions",
        0.1: "a floor on the peak height, so relative height never divides by zero (m)",
    },
    "couplings.py": {
        0: "zero",
        1: "one",
        2: "halves, doubles and pairs",
        100: "percent",
        200: "twice percent, for rounding halves up",
        3: "rounding decimals",
        4: "the quadratic formula",
        6: "a two-point cross moment",
        1000: "metres per kilometre",
        1_000_000: "integer quantisation of distance weights",
        0.5: "rounding halves up",
        -1: "a missing index",
        1e-9: "floating tolerance",
    },
    "buffers.py": {
        0: "zero",
        1: "one",
        24.0: "hours per day",
        1000.0: "kWh per MWh; L per m³",
        100.0: "percent",
        0.5: "half a two-half feed; rounding halves up",
        3: "rounding decimals",
        6: "rounding decimals",
    },
    "strength.py": {
        0: "zero",
        1: "one",
        2: "half a two-half feed",
        24.0: "hours per day",
        1000.0: "L per m³",
        100: "percent",
        6: "rounding decimals",
    },
    "requirements.py": {
        0: "zero",
        1: "one",
        24.0: "hours per day",
        8760.0: "hours per year",
        86400.0: "seconds per day",
        365.0: "days per year",
        1000.0: "kW per MW",
        0.158987294928: "m³ per barrel",
        6: "rounding decimals",
        100: "percent",
        0.5: "rounding halves up",
    },
}
"""Every numeric literal a stage may hold, with why it is not a modeling rule (0 and 0.0, 1 and
1.0 are the same key). Terrain's index
mappings stay in code for now (Work Order 5, A2) and are not scanned."""


@pytest.mark.parametrize("module", sorted(ALLOWED_LITERALS))
def test_stages_read_every_world_shaping_number_from_the_registry(module: str) -> None:
    tree = ast.parse((STAGES / module).read_text(encoding="utf-8"))
    allowed = ALLOWED_LITERALS[module]
    bare = sorted(
        {
            (node.lineno, node.value)
            for node in ast.walk(tree)
            if isinstance(node, ast.Constant)
            and isinstance(node.value, int | float)
            and not isinstance(node.value, bool)
            and node.value not in allowed
        }
    )
    assert bare == [], f"numbers in {module} that belong in the registry: {bare}"


def test_the_registry_file_is_valid_yaml_with_a_header() -> None:
    text = registry_bytes().decode("utf-8")
    assert text.startswith("# The modeling rules registry")
    assert yaml.safe_load(text)["version"] == load_registry().version
