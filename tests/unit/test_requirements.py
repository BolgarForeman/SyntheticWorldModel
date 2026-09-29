from typing import Any

import pytest

from couplings_helpers import World, requirements_of, rich_world
from layers_helpers import build_world
from swm import rng
from swm.recipe.schema import ContinuousDrawnQuantity, Layer, NodeClass
from swm.rules.registry import load_registry
from swm.stages.requirements import (
    build_requirements,
    requirement_table,
    requirements_streams,
    statistics_record,
)

RULES = load_registry()


@pytest.fixture(scope="module")
def rich() -> World:
    return rich_world()


def exact(world: World) -> Any:
    """Requirements at heterogeneity 0 and gap 0: every element on its target."""
    recipe, _, layers = world
    return build_requirements(
        ContinuousDrawnQuantity(heterogeneity_pct=0, compliance_gap_pct=0),
        layers,
        RULES,
        requirements_streams(recipe.root_seed),
    )


def test_at_zero_levers_every_requirement_is_its_section_4_4a_target(rich: World) -> None:
    result = exact(rich)
    nodes = {n.node_id: n for n in rich[2].nodes}
    n = RULES.number
    checked = set()
    for req in result.nodes:
        node = nodes[req.node_id]
        attributes = dict(node.attributes)
        c = node.node_class
        if c == NodeClass.TERTIARY:
            beds = float(attributes["bed_count"])
            assert req.electricity_mw == pytest.approx(beds * 2.5 / 1000)
            assert req.water_m3_per_day == pytest.approx(beds * 1.0)
        elif c == NodeClass.REGIONAL:
            beds = float(attributes["bed_count"])
            assert req.electricity_mw == pytest.approx(beds * 2.0 / 1000)
            assert req.water_m3_per_day == pytest.approx(beds * 0.5)
        elif c == NodeClass.CLINIC:
            assert req.electricity_mw == pytest.approx(0.027)
        elif c == NodeClass.MAST:
            assert req.electricity_mw == pytest.approx(0.006)
        elif c == NodeClass.TREATMENT:
            flow = float(attributes["capacity_m3_per_day"])
            assert req.electricity_mw == pytest.approx(0.37 * flow / 24 / 1000)
        elif c == NodeClass.DATA_CENTRE:
            it_mw = n("requirements.electricity.data_centre_it_load_mw")
            assert req.electricity_mw == pytest.approx(it_mw * 1.57)
        elif c == NodeClass.GENERATION and dict(node.subtype)["fuel_kind"] != "hydro":
            heat = n(f"requirements.fuel.{dict(node.subtype)['fuel_kind']}_gj_per_mwh")
            factor = n("requirements.fuel.generation_capacity_factor")
            expected = float(attributes["capacity_mw"]) * factor * 24 * heat
            assert req.fuel_gj_per_day == pytest.approx(expected)
        else:
            continue
        checked.add(c)
        if req.electricity_mw is not None:
            assert req.peak_mw == pytest.approx(req.electricity_mw * 1.3)
    assert {NodeClass.TERTIARY, NodeClass.CLINIC, NodeClass.MAST, NodeClass.TREATMENT} <= checked


def test_seaport_and_airport_loads_follow_their_size_class(rich: World) -> None:
    result = exact(rich)
    nodes = {n.node_id: n for n in rich[2].nodes}
    for req in result.nodes:
        node = nodes[req.node_id]
        size = dict(node.attributes).get("size_class")
        if node.node_class == NodeClass.SEAPORT:
            teu = RULES.value("requirements.throughput.seaport_teu_per_year")[size]
            assert req.electricity_mw == pytest.approx(teu / 1.6 * 25 / 8760 / 1000)
        if node.node_class == NodeClass.AIRPORT:
            passengers = RULES.value("requirements.throughput.airport_passengers_per_year")[size]
            assert req.electricity_mw == pytest.approx(passengers * 3.0 / 8760 / 1000)


def test_only_consumers_carry_requirements(rich: World) -> None:
    result = exact(rich)
    by_class = {r.node_class: r for r in result.nodes}
    assert by_class[NodeClass.DISTRIBUTION_SUBSTATION].electricity_mw is None
    assert by_class[NodeClass.STORAGE].water_m3_per_day is None
    assert by_class[NodeClass.MAST].water_m3_per_day is None
    assert by_class[NodeClass.TERTIARY].fuel_gj_per_day is None  # backup fuel is not a draw
    assert by_class[NodeClass.TERTIARY].telecom
    assert by_class[NodeClass.TERTIARY].transport
    assert not by_class[NodeClass.STORAGE].telecom


def test_backup_burn_is_a_rate_only_for_diesel_standby(rich: World) -> None:
    result = exact(rich)
    nodes = {n.node_id: n for n in rich[2].nodes}
    for req in result.nodes:
        diesel = dict(nodes[req.node_id].subtype).get("standby_fuel") == "diesel"
        if diesel and req.electricity_mw is not None:
            assert req.backup_burn_l_per_h == pytest.approx(req.electricity_mw * 269.0)
        else:
            assert req.backup_burn_l_per_h is None


def test_open_fuel_targets_are_noted_not_drawn(rich: World) -> None:
    result = exact(rich)
    seaport = next(r for r in result.nodes if r.node_class == NodeClass.SEAPORT)
    assert seaport.fuel_gj_per_day is None
    assert any("seaport: fuel draw has no target" in note for note in result.notes)


def test_realised_requirements_scale_with_the_levers(rich: World) -> None:
    recipe, _, layers = rich
    ratios = []
    for _ in range(1):
        drawn = build_requirements(
            ContinuousDrawnQuantity(heterogeneity_pct=40, compliance_gap_pct=20),
            layers,
            RULES,
            requirements_streams(recipe.root_seed),
        )
        base = exact(rich)
        for a, b in zip(drawn.nodes, base.nodes, strict=True):
            if b.electricity_mw:
                ratios.append(a.electricity_mw / b.electricity_mw)
    ratios.sort()
    median = ratios[len(ratios) // 2]
    # About 60 elements: the median sits near 1 - gap, the spread near h / (1 - gap).
    assert median == pytest.approx(0.8, rel=0.2)
    assert all(r > 0 for r in ratios)


def test_overrides_reach_the_requirements(rich: World) -> None:
    base = requirements_of(rich)
    raised = requirements_of(rich, {"requirements.peak_factor": 2.0})
    for a, b in zip(base.nodes, raised.nodes, strict=True):
        if a.electricity_mw is not None:
            assert b.electricity_mw == a.electricity_mw
            assert b.peak_mw == pytest.approx(a.electricity_mw * 2.0)


def test_requirements_draw_only_requirement_streams(monkeypatch: pytest.MonkeyPatch) -> None:
    drawn: list[str] = []
    original = rng.stream

    def recording(root_seed: int, path: str, *args: Any, **kwargs: Any) -> Any:
        drawn.append(path)
        return original(root_seed, path, *args, **kwargs)

    monkeypatch.setattr(rng, "stream", recording)
    requirements_streams(1)
    assert sorted(drawn) == sorted(f"requirements/{layer}" for layer in Layer)


def test_each_layer_draws_from_its_own_stream() -> None:
    # Healthcare is sited last, so switching it off moves no other node; each layer's
    # requirements come from its own stream, so none of theirs may move either.
    every = requirements_of(build_world())
    fewer = requirements_of(build_world(layers={"healthcare": {"state": "off"}}))
    kept = [r for r in requirement_table(every) if not str(r["id"]).startswith("SWM-HLT")]
    assert requirement_table(fewer) == kept


def test_statistics_total_every_commodity(rich: World) -> None:
    record = statistics_record(requirements_of(rich))
    assert set(record) >= {"levers", "electricity_mw", "peak_mw", "water_m3_per_day", "notes"}
