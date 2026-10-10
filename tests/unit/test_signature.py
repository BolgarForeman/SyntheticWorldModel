import functools
from dataclasses import replace
from pathlib import Path

import pytest

from couplings_helpers import rich_world
from swm.checks.signature import link_signature_problems
from swm.cli import _layers, _terrain
from swm.recipe.io import load_recipe
from swm.recipe.resolve import resolve
from swm.recipe.schema import Layer, NodeClass
from swm.stages.layers import LayersResult, signature_allows

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"
C = NodeClass
ALL = frozenset(NodeClass)


@functools.cache
def fixture_layers(name: str) -> LayersResult:
    resolution = resolve(load_recipe(FIXTURES / name))
    return _layers(resolution, _terrain(resolution))


@pytest.mark.parametrize(
    "name",
    sorted(str(p.relative_to(FIXTURES)) for p in FIXTURES.rglob("*.yaml")),
)
def test_no_fixture_world_builds_a_link_its_signature_forbids(name: str) -> None:
    assert link_signature_problems(fixture_layers(name)) == []


def test_the_rich_world_obeys_every_signature_and_stays_connected() -> None:
    layers = rich_world()[2]
    assert link_signature_problems(layers) == []
    for layer in Layer:
        members = {n.node_id for n in layers.nodes if n.layer == layer}
        links = [link for link in layers.links if link.layer == layer]
        reached, frontier = set(), [min(members)]
        while frontier:
            node = frontier.pop()
            if node in reached:
                continue
            reached.add(node)
            frontier += [link.to_id for link in links if link.from_id == node]
            frontier += [link.from_id for link in links if link.to_id == node]
        assert reached == members, layer


@pytest.mark.parametrize(
    ("layer", "a", "b", "allowed"),
    [
        (Layer.TELECOM, C.MAST, C.MAST, False),
        (Layer.TELECOM, C.EXCHANGE, C.MAST, True),
        (Layer.TELECOM, C.EXCHANGE, C.EXCHANGE, True),
        (Layer.TELECOM, C.MAST, C.DATA_CENTRE, False),
        (Layer.WATER, C.RESERVOIR, C.RESERVOIR, False),
        (Layer.WATER, C.RESERVOIR, C.TREATMENT, True),
        (Layer.WATER, C.STORAGE, C.PUMPING, True),
        (Layer.WATER, C.RESERVOIR, C.PUMPING, False),
        (Layer.POWER, C.GENERATION, C.GENERATION, False),
        (Layer.POWER, C.GENERATION, C.DISTRIBUTION_SUBSTATION, True),
        (Layer.POWER, C.DISTRIBUTION_SUBSTATION, C.DISTRIBUTION_SUBSTATION, True),
        (Layer.FUEL, C.TANK_FARM, C.REFINERY, False),
        (Layer.FUEL, C.REFINERY, C.DEPOT, True),
        (Layer.HEALTHCARE, C.CLINIC, C.CLINIC, False),
        (Layer.HEALTHCARE, C.BLOOD_BANK, C.REGIONAL, True),
        (Layer.HEALTHCARE, C.REGIONAL, C.REGIONAL, False),
        (Layer.TRANSPORT, C.BRIDGE, C.BRIDGE, True),
    ],
)
def test_the_signature_table(layer: Layer, a: NodeClass, b: NodeClass, allowed: bool) -> None:
    assert signature_allows(layer, a, b, ALL) is allowed
    assert signature_allows(layer, b, a, ALL) is allowed


def test_a_chain_skips_a_stage_only_where_that_stage_has_no_nodes() -> None:
    without_treatment = ALL - {C.TREATMENT}
    assert signature_allows(Layer.WATER, C.RESERVOIR, C.PUMPING, without_treatment)
    assert not signature_allows(Layer.WATER, C.RESERVOIR, C.PUMPING, ALL)
    without_regional = ALL - {C.REGIONAL}
    assert signature_allows(Layer.HEALTHCARE, C.TERTIARY, C.CLINIC, without_regional)


def test_the_check_names_a_forbidden_link() -> None:
    layers = rich_world()[2]
    masts = [n.node_id for n in layers.nodes if n.node_class == C.MAST]
    forged = replace(layers.links[0], link_id="SWM-TEL-L9999", layer=Layer.TELECOM,
                     from_id=masts[0], to_id=masts[1])  # fmt: skip
    problems = link_signature_problems(replace(layers, links=(*layers.links, forged)))
    assert problems == ["SWM-TEL-L9999: mast to mast is outside the telecom signature"]
