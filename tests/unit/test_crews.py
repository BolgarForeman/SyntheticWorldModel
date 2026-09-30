import math

import numpy as np
import pytest

from couplings_helpers import World, requirements_of, rich_world
from repair_helpers import crews_of, pilot_world
from swm.recipe.schema import Layer
from swm.stages.crews import RoadNetwork, crews_tables
from swm.stages.terrain import _label_land


@pytest.fixture(scope="module")
def rich() -> World:
    return rich_world()


@pytest.fixture(scope="module")
def pilot() -> World:
    return pilot_world()


def network_of(world: World) -> RoadNetwork:
    return RoadNetwork(world[1], requirements_of(world).layers)


def total_road_km(world: World, bases: list[tuple[int, int]]) -> float:
    """Total over the nodes the roads reach of the road distance from the nearest base."""
    network = network_of(world)
    total = []
    for node in requirements_of(world).layers.nodes:
        joins = network.access(node.row, node.column)
        if joins is None:
            continue
        options = []
        for row, column in bases:
            start, start_km = network.access(row, column)  # type: ignore[misc]
            road = network.road_km(start.node_id)
            if joins[0].node_id in road:
                options.append(start_km + road[joins[0].node_id] + joins[1])
        if options:
            total.append(min(options))
    return math.fsum(total)


# --- Crew bases (H2) ------------------------------------------------------------------------


def test_the_pilot_has_one_base_two_crews_and_one_unit_of_each_kind(pilot: World) -> None:
    result = crews_of(pilot, crews=2, crew_base=1)
    assert len(result.bases) == 1
    assert result.bases[0].crews == 2
    assert [crew.base_id for crew in result.crews] == ["CRB-0001", "CRB-0001"]
    assert sorted(unit.kind for unit in result.units) == ["mobile_cell_site", "mobile_substation"]
    assert all(unit.base_id == "CRB-0001" for unit in result.units)


def test_bases_sit_at_distinct_town_centres_on_the_main_roads(rich: World) -> None:
    result = crews_of(rich, crews=3, crew_base=3)
    cities = {city.city_id: city for city in rich[1].cities}
    assert len({base.city_id for base in result.bases}) == 3
    network = network_of(rich)
    for base in result.bases:
        city = cities[base.city_id]
        assert (base.row, base.column) == (city.centre_row, city.centre_column)
        node, km = network.access(base.row, base.column)  # type: ignore[misc]
        assert (node.node_id, km) == (base.access_node_id, base.access_km)
        assert np.asarray(rich[1].urban_id)[base.row, base.column] == base.city_id


def test_one_base_goes_to_the_town_with_the_least_total_road_distance(rich: World) -> None:
    chosen = crews_of(rich, crew_base=1).bases[0]
    chosen_km = total_road_km(rich, [(chosen.row, chosen.column)])
    for city in rich[1].cities:
        assert chosen_km <= total_road_km(rich, [(city.centre_row, city.centre_column)]) + 1e-9


def test_a_second_base_shortens_the_total_road_distance(rich: World) -> None:
    one = crews_of(rich, crew_base=1).bases
    two = crews_of(rich, crew_base=2).bases
    assert two[0].city_id == one[0].city_id
    assert total_road_km(rich, [(b.row, b.column) for b in two]) < total_road_km(
        rich, [(one[0].row, one[0].column)]
    )


def test_more_bases_than_towns_stops_naming_the_setting(rich: World) -> None:
    towns = len(rich[1].cities)
    with pytest.raises(ValueError, match=rf"unobserved\.crew_base = {towns + 1}: .* {towns} towns"):
        crews_of(rich, crew_base=towns + 1)


def test_crews_are_dealt_to_the_bases_in_turn(rich: World) -> None:
    result = crews_of(rich, crews=5, crew_base=2)
    assert [base.crews for base in result.bases] == [3, 2]
    assert [crew.base_id for crew in result.crews] == [
        "CRB-0001", "CRB-0002", "CRB-0001", "CRB-0002", "CRB-0001",
    ]  # fmt: skip


def test_the_emergency_pool_comes_from_the_registry(rich: World) -> None:
    pool = {"repair.emergency.pool": {"mobile_substation": 2, "mobile_cell_site": 0}}
    result = crews_of(rich, overrides=pool)
    assert [unit.unit_id for unit in result.units] == ["MSS-0001", "MSS-0002"]


def test_the_tables_list_every_base_crew_and_unit(pilot: World) -> None:
    tables = crews_tables(crews_of(pilot))
    assert list(tables) == ["crew_bases", "crews", "mobile_units"]
    assert [len(rows) for rows in tables.values()] == [1, 2, 2]


# --- The road network (G3) ------------------------------------------------------------------


def test_road_distances_are_symmetric_and_obey_the_triangle_inequality(rich: World) -> None:
    network = network_of(rich)
    ids = sorted(network.neighbours)
    for a in ids:
        for b in ids:
            if b not in network.road_km(a):
                continue
            assert network.road_km(a)[b] == pytest.approx(network.road_km(b)[a])
            for c in network.road_km(a):
                through = network.road_km(a)[c] + network.road_km(c).get(b, math.inf)
                assert network.road_km(a)[b] <= through + 1e-9


def test_a_cell_joins_the_roads_at_the_nearest_transport_node_on_its_landmass(
    rich: World,
) -> None:
    network = network_of(rich)
    labels, _ = _label_land(np.asarray(rich[1].land))
    for node in requirements_of(rich).layers.nodes:
        joins, km = network.access(node.row, node.column)  # type: ignore[misc]
        assert labels[joins.row, joins.column] == labels[node.row, node.column]
        assert joins.layer == Layer.TRANSPORT
        for other in network.transport:
            if labels[other.row, other.column] == labels[node.row, node.column]:
                assert km <= network.leg_km(node.row, node.column, other.row, other.column)


def test_a_cell_on_a_landmass_without_roads_does_not_join_them(rich: World) -> None:
    labels, sizes = _label_land(np.asarray(rich[1].land))
    network = network_of(rich)
    roadless = set(range(1, len(sizes) + 1)) - {
        int(labels[n.row, n.column]) for n in network.transport
    }
    assert roadless
    rows, columns = np.nonzero(labels == min(roadless))
    assert network.access(int(rows[0]), int(columns[0])) is None
