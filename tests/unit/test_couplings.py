import ast
from pathlib import Path
from typing import Any

import numpy as np
import pytest

from couplings_helpers import (
    World,
    couple,
    first_feeds,
    nodes_by_id,
    pair_edges,
    requirements_of,
    rich_world,
    touched_by_two_way,
)
from layers_helpers import build_world
from swm import rng
from swm.recipe.dependencies import Dependency, Role, resolve_row
from swm.recipe.io import load_recipe
from swm.recipe.resolve import resolve
from swm.recipe.schema import DEFAULT_COUPLINGS, Layer, NodeClass
from swm.rules.registry import load_registry
from swm.stages import couplings as stage
from swm.stages.couplings import (
    CouplingsResult,
    FeedConfiguration,
    build_couplings,
    couplings_streams,
    dependency_table,
    edge_table,
)
from swm.stages.layers import build_layers, layers_streams, link_table, node_table
from swm.stages.terrain import array_hashes, build_terrain, terrain_streams

SRC = Path(__file__).resolve().parents[2] / "src" / "swm"


@pytest.fixture(scope="module")
def pilot_world() -> World:
    pilot = Path(__file__).resolve().parents[1] / "fixtures" / "pilot_hand_check.yaml"
    recipe = resolve(load_recipe(pilot)).recipe
    terrain = build_terrain(
        recipe.terrain, terrain_streams(recipe.root_seed, recipe.terrain.terrain_seed)
    )
    return recipe, terrain, build_layers(recipe.layers, terrain, layers_streams(recipe.root_seed))


@pytest.fixture(scope="module")
def pilot(pilot_world: World) -> CouplingsResult:
    recipe, terrain, _ = pilot_world
    requirements = requirements_of(pilot_world)
    return build_couplings(
        recipe.couplings,
        recipe.dynamics.transfer_forms,
        terrain,
        requirements.layers,
        requirements,
        load_registry(),
        couplings_streams(recipe.root_seed),
    )


@pytest.fixture(scope="module")
def rich() -> World:
    return rich_world()


# --- The pilot ------------------------------------------------------------------------------


def test_pilot_total_edge_count_is_links_plus_switched_on_coupling_edges(
    pilot: CouplingsResult,
) -> None:
    assert pilot.intra_layer_links == 23
    assert pilot.switched_on_edges == 27
    assert pilot.total_edges == 50  # within the pilot range 40-50 (decision 0007)


def test_pilot_builds_its_seven_couplings_and_hides_the_other_fourteen(
    pilot: CouplingsResult,
) -> None:
    switched = {(s.supplier, s.consumer) for s in pilot.pairs if s.switched_on}
    assert switched == {
        (Layer.FUEL, Layer.POWER), (Layer.POWER, Layer.TELECOM), (Layer.TELECOM, Layer.POWER),
        (Layer.POWER, Layer.WATER), (Layer.WATER, Layer.HEALTHCARE),
        (Layer.POWER, Layer.HEALTHCARE), (Layer.TRANSPORT, Layer.FUEL),
    }  # fmt: skip
    assert len(pilot.pairs) == 21


def test_pilot_fuel_to_power_runs_from_the_lng_terminal(
    pilot: CouplingsResult, pilot_world: World
) -> None:
    nodes = nodes_by_id(pilot_world[2])
    (edge,) = pair_edges(pilot, Layer.FUEL, Layer.POWER)
    assert nodes[edge.supplier_id].node_class == NodeClass.IMPORT_TERMINAL
    assert dict(nodes[edge.supplier_id].subtype)["product"] == "lng"
    assert nodes[edge.consumer_id].node_class == NodeClass.GENERATION


def test_ids_are_sequential_in_canonical_order(pilot: CouplingsResult) -> None:
    numbers = [int(edge.edge_id.removeprefix("SWM-CPL-")) for edge in pilot.edges]
    assert numbers == list(range(1, len(numbers) + 1))
    order = [DEFAULT_COUPLINGS.index((e.supplier_layer, e.consumer_layer)) for e in pilot.edges]
    assert order == sorted(order)


# --- Table fidelity -------------------------------------------------------------------------


@pytest.mark.parametrize("density", [0, 100])
def test_every_edge_is_eligible_for_its_row(rich: World, density: int) -> None:
    result = couple(rich, density=density)
    nodes = nodes_by_id(rich[2])
    for edge in result.edges:
        supplier, consumer = nodes[edge.supplier_id], nodes[edge.consumer_id]
        row = resolve_row(edge.supplier_layer, consumer.node_class, dict(consumer.subtype))
        assert row.dependency != Dependency.NONE, edge.edge_id
        options = _large(rich).suppliers(row, consumer)
        allowed = [
            option
            for option in options
            if option.node_class == supplier.node_class
            and (option.product is None or dict(supplier.subtype)["product"] == option.product)
        ]
        assert allowed, edge.edge_id


def test_every_core_row_exists_for_every_generated_pair(rich: World) -> None:
    result = couple(rich, density=0)
    present = {(d.supplier_layer, d.consumer_id) for d in result.dependencies}
    for supplier, consumer in DEFAULT_COUPLINGS:
        for node in rich[2].nodes:
            if node.layer != consumer:
                continue
            row = resolve_row(supplier, node.node_class, dict(node.subtype))
            if row.dependency == Dependency.CORE:
                assert (supplier, node.node_id) in present, (supplier, node.node_id)


def test_no_none_row_produces_a_dependency(rich: World) -> None:
    nodes = nodes_by_id(rich[2])
    for dependency in couple(rich, density=100).dependencies:
        consumer = nodes[dependency.consumer_id]
        row = resolve_row(dependency.supplier_layer, consumer.node_class, dict(consumer.subtype))
        assert row.dependency != Dependency.NONE
        assert row.key == dependency.row_key


# --- Density (E3) ---------------------------------------------------------------------------


def _optional_allowed(result: CouplingsResult) -> int:
    return sum(
        1
        for d in result.dependencies
        if d.dependency == Dependency.OPTIONAL and d.feed_configuration != FeedConfiguration.NONE
    )


def test_density_0_takes_core_dependencies_only(rich: World) -> None:
    result = couple(rich, density=0)
    assert _optional_allowed(result) == 0


def test_density_100_takes_every_dependency_the_table_allows(rich: World) -> None:
    result = couple(rich, density=100)
    nodes = nodes_by_id(rich[2])
    allowed = 0
    for supplier, consumer in DEFAULT_COUPLINGS:
        for node in nodes.values():
            if node.layer != consumer:
                continue
            row = resolve_row(supplier, node.node_class, dict(node.subtype))
            no_standby = dict(node.subtype).get("standby_fuel") == "none"
            if row.dependency == Dependency.OPTIONAL and not (
                row.role == Role.BUFFER_RESUPPLY and no_standby
            ):
                allowed += 1
    assert allowed > 0
    assert _optional_allowed(result) == allowed


def test_the_dependency_count_rises_with_density(rich: World) -> None:
    counts = [len(couple(rich, density=d).dependencies) for d in (0, 20, 40, 60, 80, 100)]
    assert counts == sorted(counts)
    assert counts[0] < counts[-1]


# --- Feed configuration (E4) ----------------------------------------------------------------


def test_realised_feed_counts_equal_the_largest_remainder_counts(rich: World) -> None:
    result = couple(rich, feed_mix={"single_feed_pct": 40, "two_full_feeds_pct": 35,
                                    "two_half_feeds_pct": 25})  # fmt: skip
    _check_feed_mix(result, (40, 35, 25))


def _check_feed_mix(result: CouplingsResult, shares: tuple[int, int, int]) -> None:
    by_pair: dict[tuple[Layer, Layer], list[Any]] = {}
    for d in result.dependencies:
        by_pair.setdefault((d.supplier_layer, d.consumer_layer), []).append(d)
    touched = touched_by_two_way(result)
    for (supplier, consumer), dependencies in by_pair.items():
        mixed = [
            d
            for d in dependencies
            if supplier != Layer.TRANSPORT
            and d.role == Role.PRIMARY_SUPPLY
            and not d.row_key.startswith("power>tertiary")
        ]
        if any(d.dependency_id in touched or d.notes for d in mixed):
            continue  # a single eligible supplier or a two-way change is noted instead
        realised = [
            sum(d.feed_configuration == c for d in mixed)
            for c in (FeedConfiguration.SINGLE, FeedConfiguration.TWO_FULL,
                      FeedConfiguration.TWO_HALF)
        ]  # fmt: skip
        assert realised == stage._largest_remainder(len(mixed), shares), (supplier, consumer)


def test_two_feed_dependencies_have_two_distinct_suppliers(rich: World) -> None:
    result = couple(rich, density=100)
    edges = {edge.edge_id: edge for edge in result.edges}
    for d in result.dependencies:
        if d.feed_configuration in (FeedConfiguration.TWO_FULL, FeedConfiguration.TWO_HALF):
            suppliers = [edges[e].supplier_id for e in d.edge_ids]
            assert len(suppliers) == 2, d.dependency_id
            assert len(set(suppliers)) == 2, d.dependency_id
            groups = [edges[e].feed_group for e in d.edge_ids]
            expected = [1, 1] if d.feed_configuration == FeedConfiguration.TWO_HALF else [1, 2]
            assert groups == expected


def test_a_dependency_with_one_eligible_supplier_stays_single_with_a_note() -> None:
    # Every mixed dependency is drawn two full feeds; those with one eligible supplier node
    # (for example an LNG terminal on the world's only transmission substation) stay single.
    world = build_world(layers={"fuel": {"node_count": 3}})
    result = couple(world, two_way_pct=100, feed_mix={"single_feed_pct": 0,
                    "two_full_feeds_pct": 100, "two_half_feeds_pct": 0})  # fmt: skip
    single = [
        d
        for d in result.dependencies
        if d.role == Role.PRIMARY_SUPPLY
        and d.supplier_layer != Layer.TRANSPORT
        and not d.row_key.startswith("power>tertiary")
        and d.feed_configuration == FeedConfiguration.SINGLE
        and d.edge_ids
        and d.dependency_id not in touched_by_two_way(result)
    ]
    assert single
    for d in single:
        assert any("only one eligible supplier node" in note for note in d.notes), d.row_key


def test_tertiary_second_feed_is_all_or_nothing_at_its_bounds(rich: World) -> None:
    for pct, expected in ((0, FeedConfiguration.SINGLE), (100, FeedConfiguration.TWO_FULL)):
        share = {"dependencies.rule_5.tertiary_second_feed_share": pct / 100}
        result = couple(rich, share, two_way_pct=100)
        tertiary = [d for d in result.dependencies if d.row_key == "power>tertiary"]
        assert tertiary
        for d in tertiary:
            # A tertiary hospital large enough for rule 4 may have one eligible substation.
            single_supplier = any("only one eligible supplier" in note for note in d.notes)
            assert d.feed_configuration == expected or single_supplier, d.dependency_id


# --- Supplier choice (E7) -------------------------------------------------------------------


def test_at_concentration_100_the_hub_carries_every_dependency_it_is_eligible_for(
    rich: World,
) -> None:
    result = couple(rich, concentration=100, supplier_not_nearest_pct=0, two_way_pct=100)
    firsts = first_feeds(result)
    touched = touched_by_two_way(result)
    hubs = {(s.supplier, s.consumer): s.hub for s in result.pairs}
    for d in result.dependencies:
        pair = (d.supplier_layer, d.consumer_layer)
        if d.supplier_layer == Layer.TRANSPORT or not d.edge_ids or d.dependency_id in touched:
            continue
        eligible = {n.node_id for n in _eligible_of(rich, d)}
        if hubs[pair] in eligible:
            assert firsts[d.dependency_id].supplier_id == hubs[pair], d.dependency_id
            assert firsts[d.dependency_id].is_hub


def test_at_concentration_0_and_not_nearest_0_every_first_feed_is_the_nearest(
    rich: World,
) -> None:
    result = couple(rich, concentration=0, supplier_not_nearest_pct=0, two_way_pct=100)
    touched = touched_by_two_way(result)
    for dependency_id, edge in first_feeds(result).items():
        if dependency_id not in touched:
            assert edge.is_nearest, dependency_id


@pytest.mark.parametrize(("concentration", "not_nearest"), [(0, 25), (40, 25), (20, 60)])
def test_the_not_nearest_share_is_met_or_noted(
    rich: World, concentration: int, not_nearest: int
) -> None:
    result = couple(rich, concentration=concentration, supplier_not_nearest_pct=not_nearest,
                    two_way_pct=100)  # fmt: skip
    firsts = first_feeds(result)
    for stats in result.pairs:
        if stats.supplier == Layer.TRANSPORT:
            continue
        chosen = [
            d
            for d in result.dependencies
            if (d.supplier_layer, d.consumer_layer) == (stats.supplier, stats.consumer)
            and d.edge_ids
        ]
        far = sum(not firsts[d.dependency_id].is_nearest for d in chosen)
        target = stage._percent_of(not_nearest, len(chosen))
        noted = any("supplier_not_nearest" in note for note in stats.notes)
        changed = any(d.dependency_id in touched_by_two_way(result) for d in chosen)
        assert far == target or noted or changed, (stats.supplier, stats.consumer, far, target)


def test_a_second_feed_goes_to_the_nearest_supplier_other_than_the_first(rich: World) -> None:
    result = couple(rich, two_way_pct=100)
    edges = {edge.edge_id: edge for edge in result.edges}
    touched = touched_by_two_way(result)
    for d in result.dependencies:
        if (
            len(d.edge_ids) != 2
            or d.supplier_layer == Layer.TRANSPORT
            or d.dependency_id in touched
        ):
            continue
        eligible = _eligible_of(rich, d)
        first, second = (edges[e].supplier_id for e in d.edge_ids)
        assert second == next(n.node_id for n in eligible if n.node_id != first)


# --- Two-way (E9) ---------------------------------------------------------------------------


def _mutual_pairs(result: CouplingsResult) -> int:
    served = {(e.supplier_id, e.consumer_id) for e in result.edges}
    return sum(1 for s, c in served if (c, s) in served) // 2


def _kept_mutual(result: CouplingsResult) -> set[str]:
    """Dependencies that keep a mutual pair so they are not left without a supplier."""
    return {
        d.dependency_id
        for d in result.dependencies
        if any(note.startswith("mutual pair kept") for note in d.notes)
    }


def test_two_way_0_leaves_only_mutual_pairs_kept_for_a_core_dependency(rich: World) -> None:
    result = couple(rich, two_way_pct=0, density=100)
    kept = _kept_mutual(result)
    for edge in result.edges:
        if edge.mutual_partner is not None:
            partner = next(e for e in result.edges if e.edge_id == edge.mutual_partner)
            assert kept & {edge.dependency_id, partner.dependency_id}, edge.edge_id
    assert _mutual_pairs(result) == len(kept)


@pytest.mark.parametrize("density", [0, 100])
def test_two_way_0_never_leaves_a_core_dependency_without_a_supplier(
    rich: World, density: int
) -> None:
    for concentration in (0, 40, 100):
        result = couple(rich, two_way_pct=0, density=density, concentration=concentration)
        for d in result.dependencies:
            if d.dependency != Dependency.CORE or d.feed_configuration == FeedConfiguration.NONE:
                continue
            eligible = _eligible_of(rich, d)
            if eligible and d.supplier_layer != Layer.TRANSPORT:
                assert d.edge_ids, d.dependency_id


def test_the_pilot_keeps_the_substation_exchange_loop(pilot: CouplingsResult) -> None:
    (control,) = [
        d
        for d in pilot.dependencies
        if d.consumer_id == "SWM-POW-0003" and d.supplier_layer == Layer.TELECOM
    ]
    assert control.edge_ids
    assert any(note.startswith("mutual pair kept") for note in control.notes)
    power_telecom = next(s for s in pilot.pairs if (s.supplier, s.consumer) ==
                         (Layer.POWER, Layer.TELECOM))  # fmt: skip
    assert power_telecom.mutual_pairs == 1
    assert "1 kept so a core dependency keeps a supplier" in " ".join(power_telecom.notes)


def test_two_way_100_builds_every_allowed_mutual_pair(rich: World) -> None:
    result = couple(rich, two_way_pct=100, density=100)
    allowed = sum(s.mutual_pairs_allowed for s in result.pairs) // 2
    assert allowed > 0
    assert _mutual_pairs(result) == allowed
    for edge in result.edges:
        if edge.mutual_partner is not None:
            partner = next(e for e in result.edges if e.edge_id == edge.mutual_partner)
            assert (partner.supplier_id, partner.consumer_id) == (
                edge.consumer_id,
                edge.supplier_id,
            )


def test_mutual_pairs_rise_with_two_way(rich: World) -> None:
    counts = [_mutual_pairs(couple(rich, two_way_pct=p, density=100)) for p in (0, 25, 50, 100)]
    assert counts == sorted(counts)
    assert counts[0] < counts[-1]


# --- Transport (E5) and outlying islands (decision 0008, answer 6) --------------------------


def test_every_listed_origin_reaches_its_consumer(rich: World) -> None:
    result = couple(rich, density=100)
    world = stage._World(rich[1], rich[2], load_registry())
    nodes = nodes_by_id(rich[2])
    for edge in result.edges:
        if edge.supplier_layer != Layer.TRANSPORT:
            continue
        origin, consumer = nodes[edge.supplier_id], nodes[edge.consumer_id]
        assert edge.feed_configuration == FeedConfiguration.ANY_REACHABLE
        if edge.sea_leg:
            assert world.outlying(consumer)
            assert origin.node_class == NodeClass.SEAPORT
            continue
        island = [
            n for n in world.nodes[Layer.TRANSPORT] if world.island(n) == world.island(consumer)
        ]
        access = min(island, key=lambda n: (stage._distance2(n, consumer), n.node_id))
        assert any(origin.node_id in c and access.node_id in c for c in world.road_components)


def test_an_unreachable_consumer_keeps_its_dependency_with_a_note() -> None:
    # One transport node: the seaport. A clinic's only origin is a freight yard.
    world = build_world(layers={"transport": {"node_count": 1}})
    result = couple(world)
    clinics = [d for d in result.dependencies if d.row_key == "transport>clinic"]
    assert clinics
    for d in clinics:
        assert d.edge_ids == ()
        assert any("no eligible origin reaches it" in note for note in d.notes)


def test_generation_takes_no_reservoir_water_on_the_coast(rich: World) -> None:
    result = couple(rich, density=100)
    nodes = nodes_by_id(rich[2])
    for edge in pair_edges(result, Layer.WATER, Layer.POWER):
        assert nodes[edge.supplier_id].node_class != NodeClass.RESERVOIR


# --- Buffer resupply (E6) and standby fuel (decision 0008, answer 3) ------------------------


def test_every_buffer_edge_backs_a_power_dependency_of_its_consumer(rich: World) -> None:
    result = couple(rich, density=100)
    dependencies = {d.dependency_id: d for d in result.dependencies}
    buffers = [e for e in result.edges if e.role == Role.BUFFER_RESUPPLY]
    assert buffers
    for edge in buffers:
        assert edge.backs_dependency is not None, edge.edge_id
        backed = dependencies[edge.backs_dependency]
        assert backed.supplier_layer == Layer.POWER
        assert backed.consumer_id == edge.consumer_id


def test_no_standby_generator_means_no_buffer_edge_and_a_note(
    pilot: CouplingsResult, pilot_world: World
) -> None:
    nodes = nodes_by_id(pilot_world[2])
    absent = [d for d in pilot.dependencies if d.feed_configuration == FeedConfiguration.NONE]
    # Masts and clinics hold no diesel set (decision 0010), nor does one pumping station.
    assert {d.consumer_id for d in absent} == {
        "SWM-TEL-0002", "SWM-TEL-0003", "SWM-TEL-0004", "SWM-HLT-0003", "SWM-WAT-0003",
    }  # fmt: skip
    for d in absent:
        assert dict(nodes[d.consumer_id].subtype)["standby_fuel"] == "none"
        assert d.edge_ids == ()
        assert d.role == Role.BUFFER_RESUPPLY
        assert any("answer 3" in note for note in d.notes)


# --- Rules 1 and 4 --------------------------------------------------------------------------


def test_control_edges_carry_the_public_telecom_share(rich: World) -> None:
    result = couple(rich, public_telecom_share={"generation_pct": 11, "transmission_pct": 22,
                                                "distribution_pct": 33, "water_pct": 44,
                                                "pipelines_pct": 55})  # fmt: skip
    nodes = nodes_by_id(rich[2])
    expected = {
        NodeClass.GENERATION: 11, NodeClass.TRANSMISSION_SUBSTATION: 22,
        NodeClass.DISTRIBUTION_SUBSTATION: 33, NodeClass.TREATMENT: 44, NodeClass.PUMPING: 44,
        NodeClass.RESERVOIR: 44, NodeClass.TANK_FARM: 55, NodeClass.IMPORT_TERMINAL: 55,
    }  # fmt: skip
    shared = 0
    for edge in result.edges:
        consumer = nodes[edge.consumer_id]
        if edge.dependency_type == "control" and consumer.node_class in expected:
            assert edge.public_share_pct == expected[consumer.node_class], edge.edge_id
            shared += 1
        else:  # a towered airport's control edge is not a rule 1 edge
            assert edge.public_share_pct is None, edge.edge_id
    assert shared


@pytest.mark.parametrize(("voltage_kv", "threshold_mw"), [(11.4, 5.0), (22.8, 10.0)])
def test_rule_4_sends_large_loads_to_transmission(
    rich: World, voltage_kv: float, threshold_mw: float
) -> None:
    result = couple(rich, density=100, distribution_voltage_kv=voltage_kv)
    peaks = {n.node_id: n.peak_mw for n in requirements_of(rich).nodes}
    nodes = nodes_by_id(rich[2])
    edges = {edge.edge_id: edge for edge in result.edges}
    large = small = 0
    for d in result.dependencies:
        if d.supplier_layer != Layer.POWER or not d.edge_ids:
            continue
        peak = peaks[d.consumer_id]
        assert peak is not None
        classes = {nodes[edges[e].supplier_id].node_class for e in d.edge_ids}
        noted = any(note.startswith("rule 4:") for note in d.notes)
        row = _row_of(rich, d)
        row_says_transmission = {o.node_class for o in row.suppliers} == {
            NodeClass.TRANSMISSION_SUBSTATION
        }
        if peak >= threshold_mw:
            large += 1
            assert classes == {NodeClass.TRANSMISSION_SUBSTATION}, d.dependency_id
            assert noted or row_says_transmission
        else:
            small += 1
            assert classes <= {option.node_class for option in row.suppliers}, d.dependency_id
            assert not noted
    assert large
    assert small


def test_rule_4_threshold_is_inclusive() -> None:
    from swm.recipe.dependencies import SupplierOption

    row = resolve_row(Layer.POWER, NodeClass.CLINIC, {"standby_fuel": "diesel"})
    world = rich_world()
    clinic = next(n for n in world[2].nodes if n.node_class == NodeClass.CLINIC)
    for peak, expected in ((5.0, NodeClass.TRANSMISSION_SUBSTATION),
                           (4.999999, NodeClass.DISTRIBUTION_SUBSTATION)):  # fmt: skip
        loads = stage._LargeLoads({clinic.node_id: peak}, 5.0, 50)
        assert loads.suppliers(row, clinic) == (SupplierOption(expected),)


# --- States (E2) ----------------------------------------------------------------------------


def test_an_off_layer_has_no_couplings() -> None:
    world = build_world(layers={"water": {"state": "off"}})
    result = couple(world)
    assert result.edges
    for edge in result.edges:
        assert Layer.WATER not in (edge.supplier_layer, edge.consumer_layer)
    assert all(Layer.WATER not in (s.supplier, s.consumer) for s in result.pairs)


def test_a_hidden_layer_couples_in_full() -> None:
    emitted = couple(build_world(layers={"telecom": {"state": "emitted"}}))
    hidden = couple(build_world(layers={"telecom": {"state": "hidden"}}))
    assert edge_table(hidden) == edge_table(emitted)


def _without_flag(result: CouplingsResult) -> list[dict[str, object]]:
    return [{k: v for k, v in row.items() if k != "switched_on"} for row in edge_table(result)]


def test_generate_and_hide_differs_from_switched_on_only_in_the_flag(rich: World) -> None:
    every = couple(rich)
    some = couple(rich, switched_on=[{"supplier": "fuel", "consumer": "power"}],
                  switched_off_handling="generate_and_hide")  # fmt: skip
    assert _without_flag(some) == _without_flag(every)
    assert {e.switched_on for e in some.edges} == {True, False}
    for edge in some.edges:
        assert edge.switched_on == ((edge.supplier_layer, edge.consumer_layer) ==
                                    (Layer.FUEL, Layer.POWER))  # fmt: skip


# --- Streams (E2) ---------------------------------------------------------------------------


@pytest.mark.parametrize("dropped", [(Layer.POWER, Layer.TELECOM), (Layer.FUEL, Layer.WATER)])
def test_leaving_one_pair_out_leaves_every_other_pair_byte_identical(
    rich: World, dropped: tuple[Layer, Layer]
) -> None:
    every = couple(rich, density=60, two_way_pct=40)
    kept = [
        {"supplier": s.value, "consumer": c.value}
        for s, c in DEFAULT_COUPLINGS
        if (s, c) != dropped
    ]
    fewer = couple(rich, density=60, two_way_pct=40, switched_on=kept,
                   switched_off_handling="not_generated")  # fmt: skip
    assert not pair_edges(fewer, *dropped)
    others = [
        row for row, e in zip(edge_table(every), every.edges, strict=True)
        if (e.supplier_layer, e.consumer_layer) != dropped
    ]  # fmt: skip
    gone = {d.dependency_id for d in every.dependencies} - {
        d.dependency_id for d in fewer.dependencies
    }
    # The one allowed difference: a buffer edge no longer names a power dependency that is gone.
    for row in others:
        if row["backs_dependency"] in gone:
            row["backs_dependency"] = None
    assert edge_table(fewer) == others
    kept_dependencies = [
        row for row in dependency_table(every)
        if (Layer(str(row["supplier_layer"])), Layer(str(row["consumer_layer"]))) != dropped
    ]  # fmt: skip
    assert [_without_notes(r) for r in dependency_table(fewer)] == [
        _without_notes(r) for r in kept_dependencies
    ]


def _without_notes(row: dict[str, object]) -> dict[str, object]:
    return {k: v for k, v in row.items() if k != "notes"}


def test_couplings_settings_never_move_terrain_or_layers() -> None:
    _, terrain, layers = build_world(couplings={"density": 0})
    _, other_terrain, other_layers = build_world(
        couplings={"density": 100, "two_way_pct": 100, "concentration": 90}
    )
    assert array_hashes(other_terrain) == array_hashes(terrain)
    assert node_table(other_layers) == node_table(layers)
    assert link_table(other_layers) == link_table(layers)


def test_the_stage_draws_only_couplings_streams(monkeypatch: pytest.MonkeyPatch) -> None:
    drawn: list[str] = []
    original = rng.stream

    def recording(root_seed: int, path: str, *args: Any, **kwargs: Any) -> np.random.Generator:
        drawn.append(path)
        return original(root_seed, path, *args, **kwargs)

    monkeypatch.setattr(rng, "stream", recording)
    couplings_streams(7)
    assert drawn
    assert all(path.startswith("couplings/") for path in drawn)
    assert set(drawn) <= set(rng.STREAM_REGISTRY)


def test_the_work_order_1_couplings_streams_are_retired() -> None:
    for path in ("couplings/edges", "couplings/supplier_not_nearest",
                 "couplings/feed_configuration", "couplings/two_way"):  # fmt: skip
        assert path not in rng.STREAM_REGISTRY


def test_stream_paths_are_per_pair_and_no_existing_stream_moved() -> None:
    for supplier, consumer in DEFAULT_COUPLINGS:
        assert f"couplings/density/{supplier}-{consumer}" in rng.STREAM_REGISTRY
    assert "couplings/two_way/power-telecom" in rng.STREAM_REGISTRY
    assert "layers/power/siting" in rng.STREAM_REGISTRY
    assert rng.spawn_key("layers/power/siting") == (
        rng.stable_id("layers"),
        rng.stable_id("power"),
        rng.stable_id("siting"),
    )


# --- Geometry (E10) -------------------------------------------------------------------------


def test_edges_are_straight_lines_with_their_length(pilot: CouplingsResult) -> None:
    for edge in pilot.edges:
        (x0, y0), (x1, y1) = edge.points
        assert edge.length_km == round(((x1 - x0) ** 2 + (y1 - y0) ** 2) ** 0.5 / 1000, 3)


# --- Separation (CLAUDE.md §3) --------------------------------------------------------------


def _imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names |= {alias.name for alias in node.names}
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module)
    return names


def test_emission_and_error_code_cannot_reach_the_couplings_output() -> None:
    forbidden = {
        "swm.stages.couplings",
        "swm.stages.requirements",
        "swm.stages.buffers",
        "swm.stages.strength",
        "swm.stages.crews",
        "swm.stages.repair",
        "swm.stages.storm",
        "swm.recipe.dependencies",
    }
    for folder in ("emit", "errors"):
        for path in (SRC / folder).rglob("*.py"):
            assert not _imports(path) & forbidden, path


def test_no_coupling_field_is_an_observed_attribute(pilot_world: World) -> None:
    fields = set(stage.CouplingEdge.__dataclass_fields__) | set(
        stage.CouplingDependency.__dataclass_fields__
    )
    fields |= set(edge_table(couple(pilot_world))[0]) | set(
        dependency_table(couple(pilot_world))[0]
    )
    for node in pilot_world[2].nodes:
        assert not fields & {name for name, _ in node.attributes}, node.node_id


# --- Exact counting -------------------------------------------------------------------------


def test_largest_remainder_and_apportion_are_exact() -> None:
    assert stage._largest_remainder(4, (60, 25, 15)) == [2, 1, 1]
    assert stage._largest_remainder(1, (60, 25, 15)) == [1, 0, 0]
    assert stage._apportion(50, [3, 1, 1]) == [2, 1, 0]
    assert stage._percent_of(40, 4) == 2
    assert stage._percent_of(50, 1) == 1


def _large(world: World) -> Any:
    rules = load_registry()
    return stage._LargeLoads.from_rules(requirements_of(world), rules, 11.4)


def _eligible_of(world: World, d: Any) -> Any:
    """The dependency's eligible suppliers, rule 4 applied, nearest first."""
    row = _row_of(world, d)
    consumer = _node(world, d.consumer_id)
    options = _large(world).suppliers(row, consumer)
    return stage._eligible(
        row.supplier_layer, options, consumer, stage._World(world[1], world[2], load_registry())
    )


def _row_of(world: World, d: Any) -> Any:
    node = _node(world, d.consumer_id)
    return resolve_row(d.supplier_layer, node.node_class, dict(node.subtype))


def _node(world: World, node_id: str) -> Any:
    return nodes_by_id(world[2])[node_id]
