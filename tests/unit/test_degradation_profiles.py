"""Each degradation profile (Degradation Profiles v0.3) as a one-node test (Work Order 7, F2).

Each test isolates the node, cuts one supply at hour 0 by damaging its source, runs 72 h with
no repair, and compares the node's state with the profile; each limit is also run at its relaxed
value. A stock of H hours empties at hour H, so the node holds 1 through the step before.
"""

import pytest

from dynamics_helpers import RULES, TARGET, OneNode, cut, first_change, supplier_id
from swm.recipe.schema import Layer, NodeClass

C = NodeClass
P, T, W, F, R = Layer.POWER, Layer.TELECOM, Layer.WATER, Layer.FUEL, Layer.TRANSPORT


def states_from(run: object, hour: float) -> set[float]:
    """Every state the target takes from an hour to the end of the run."""
    return {s for t, s in zip(run.times, run.state(TARGET), strict=True) if t >= hour}  # type: ignore[attr-defined]


def settles(run: object, hour: float) -> float:
    """The one state the target holds from an hour to the end of the run."""
    values = states_from(run, hour)
    assert len(values) == 1, values
    return values.pop()


def held(run: object, until: float) -> bool:
    """Whether the target holds 1 at every step before an hour."""
    return all(s == 1.0 for t, s in zip(run.times, run.state(TARGET), strict=True) if t < until)  # type: ignore[attr-defined]


# --- Power ----------------------------------------------------------------------------------

GENERATION = {"fuel_kind": "coal", "makeup_water": "municipal"}


@pytest.mark.parametrize("fuel_kind", ["lng", "oil"])
def test_generation_fuel_cut_trips_an_lng_or_oil_plant(fuel_kind: str) -> None:
    # Their stocks are held upstream, at the terminal and the tank farms (Profiles v0.3).
    node = OneNode(C.GENERATION, P, {**GENERATION, "fuel_kind": fuel_kind}, end_use=False)
    node.needs(F)
    assert node.dependencies[0].mode == "trip"
    assert states_from(cut(node.world(), [supplier_id(F)]), 0.0) == {0.0}


def test_generation_fuel_cut_the_coal_stock_covers_far_beyond_the_window() -> None:
    node = OneNode(C.GENERATION, P, GENERATION, end_use=False)
    node.stock("coal", F, 30 * 24.0, "reserves.coal.days").needs(F)
    run = cut(node.world(), [supplier_id(F)])
    assert held(run, 72.0)
    assert run.at(TARGET, 72.0) == 1.0


def test_generation_water_cut_runs_on_purified_water_for_24_h_then_trips() -> None:
    node = OneNode(C.GENERATION, P, GENERATION, end_use=False)
    node.stock("purified_water", W, 24.0, "reserves.generation.purified_water_h", "main").needs(W)
    run = cut(node.world(), [supplier_id(W)])
    assert held(run, 24.0)
    assert states_from(run, 24.0) == {0.0}
    relaxed = cut(node.world(), [supplier_id(W)], ["reserves.generation.purified_water_h"])
    assert held(relaxed, 72.25)


def test_generation_telecom_cut_holds_12_h_then_0_99_at_a_20_percent_public_share() -> None:
    node = OneNode(C.GENERATION, P, GENERATION, end_use=False)
    node.needs(T, kappa=0.2, form="threshold", tolerance="tolerance.generation")
    run = cut(node.world(), [supplier_id(T)])
    assert held(run, 12.0)
    assert settles(run, 12.0) == pytest.approx(1.0 - 0.2 * 0.05)
    assert held(cut(node.world(), [supplier_id(T)], ["tolerance.generation"]), 72.25)


@pytest.mark.parametrize("node_class", [C.TRANSMISSION_SUBSTATION, C.DISTRIBUTION_SUBSTATION])
def test_a_substation_throttles_at_the_power_it_receives(node_class: NodeClass) -> None:
    node = OneNode(node_class, P, end_use=False).fed_by_own_layer()
    run = cut(node.world(), ["UP-0"])
    assert states_from(run, 0.0) == {0.0}


def test_a_distribution_substation_on_two_lines_holds_until_both_fail() -> None:
    node = OneNode(C.DISTRIBUTION_SUBSTATION, P).fed_by_own_layer(sources=2)
    assert held(cut(node.world(), ["UP-0"]), 72.25)
    assert states_from(cut(node.world(), ["UP-0", "UP-1"]), 0.0) == {0.0}


@pytest.mark.parametrize("node_class", [C.TRANSMISSION_SUBSTATION, C.DISTRIBUTION_SUBSTATION])
def test_substation_telecom_loss_has_no_supply_effect(node_class: NodeClass) -> None:
    node = OneNode(node_class, P, end_use=False)
    node.needs(T, kappa=0.2, form="threshold", tolerance="tolerance.substation")
    assert held(cut(node.world(), [supplier_id(T)]), 72.25)


# --- Telecom --------------------------------------------------------------------------------


def exchange(fails_to_start: bool = False) -> OneNode:
    node = OneNode(C.EXCHANGE, T, end_use=False)
    node.stock("battery", P, 4.0, "reserves.exchange.battery_h", "battery", draw_per_h=50.0)
    node.generator(24.0, "reserves.exchange.fuel_h", fails_to_start=fails_to_start)
    return node.needs(P)


def test_exchange_power_cut_battery_then_generator_then_deliveries_hold_it_at_1() -> None:
    node = exchange().deliveries_from()
    run = cut(node.world(), [supplier_id(P)])
    assert held(run, 72.25)
    assert [d.time_h for d in run.deliveries] == [12.0, 36.0, 60.0]


def test_exchange_trips_when_its_generator_fails_to_start_and_the_battery_runs_out() -> None:
    run = cut(exchange(fails_to_start=True).world(), [supplier_id(P)])
    assert held(run, 4.0)
    assert states_from(run, 4.0) == {0.0}


def test_exchange_trips_when_the_fuel_chain_breaks() -> None:
    node = exchange().deliveries_from()
    run = cut(node.world(), [supplier_id(P), "DEPOT"])
    assert held(run, 28.0)
    assert states_from(run, 28.0) == {0.0}
    assert run.deliveries == ()


def mast() -> OneNode:
    return OneNode(C.MAST, T).stock("battery", P, 4.0, "reserves.mast.battery_h", "battery")


def test_mast_power_cut_4_h_battery_then_trip() -> None:
    node = mast().needs(P)
    run = cut(node.world(), [supplier_id(P)])
    assert held(run, 4.0)
    assert states_from(run, 4.0) == {0.0}
    assert held(cut(node.world(), [supplier_id(P)], ["reserves.mast.battery_h"]), 72.25)


def test_mast_backhaul_cut_is_0_at_once() -> None:
    node = mast().needs(P).fed_by_own_layer()
    assert states_from(cut(node.world(), ["UP-0"]), 0.0) == {0.0}


def test_mast_battery_recharges_empty_to_full_in_12_h() -> None:
    from swm.dynamics.world import FacilityRepair

    node = mast().needs(P)
    node.repairs.append(FacilityRepair(supplier_id(P), 0.0, 0.0))
    world = node.world()
    from dataclasses import replace

    from swm.dynamics.world import CrewStart

    world = replace(world, crews=(CrewStart("CREW", (0.0, 0.0)),))
    run = cut(world, [supplier_id(P)])
    level = run.level(f"{TARGET}:battery")
    # The crew-bound lead time (2 h) restores power at hour 2; 2 h of battery are gone.
    assert run.at(supplier_id(P), 2.0) == 1.0
    assert level[8] == pytest.approx(20.0)
    capacity = level[0]
    per_step = capacity / 12.0 / 4.0
    assert level[9] - level[8] == pytest.approx(per_step)
    assert level[8 + 24] == pytest.approx(capacity)


def test_data_centre_power_cut_its_72_h_of_fuel_hold_it() -> None:
    node = OneNode(C.DATA_CENTRE, T, {"cooling": "evaporative"}, end_use=False)
    node.generator(72.0, "reserves.data_centre.fuel_h").needs(P)
    assert held(cut(node.world(), [supplier_id(P)]), 72.0)


def test_data_centre_water_cut_runs_on_make_up_water_for_12_h_then_trips() -> None:
    node = OneNode(C.DATA_CENTRE, T, {"cooling": "evaporative"}, end_use=False)
    node.stock("makeup_water", W, 12.0, "reserves.data_centre.makeup_water_h", "main").needs(W)
    run = cut(node.world(), [supplier_id(W)])
    assert held(run, 12.0)
    assert states_from(run, 12.0) == {0.0}
    relaxed = cut(node.world(), [supplier_id(W)], ["reserves.data_centre.makeup_water_h"])
    assert held(relaxed, 72.25)


def test_cable_landing_power_cut_48_h_of_fuel_then_trips() -> None:
    node = OneNode(C.CABLE_LANDING, T, end_use=False)
    node.generator(48.0, "reserves.cable_landing.fuel_h").needs(P)
    run = cut(node.world(), [supplier_id(P)])
    assert held(run, 48.0)
    assert states_from(run, 48.0) == {0.0}


# --- Water ----------------------------------------------------------------------------------


def test_reservoir_telecom_cut_has_no_effect_inside_72_h() -> None:
    node = OneNode(C.RESERVOIR, W, end_use=False)
    node.needs(T, kappa=0.5, form="threshold", tolerance="tolerance.reservoir")
    assert held(cut(node.world(), [supplier_id(T)]), 72.0)


def test_treatment_power_cut_48_h_of_fuel_then_throttles_to_what_it_receives() -> None:
    node = OneNode(C.TREATMENT, W, end_use=False)
    node.generator(48.0, "reserves.treatment.fuel_h").needs(P)
    run = cut(node.world(), [supplier_id(P)])
    assert held(run, 48.0)
    assert states_from(run, 48.0) == {0.0}


def test_treatment_telecom_cut_24_h_then_0_95() -> None:
    node = OneNode(C.TREATMENT, W, end_use=False)
    node.needs(T, kappa=0.5, form="threshold", tolerance="tolerance.treatment")
    run = cut(node.world(), [supplier_id(T)])
    assert held(run, 24.0)
    assert settles(run, 24.0) == pytest.approx(0.95)


def test_pumping_power_cut_throttles_at_the_share_received() -> None:
    node = OneNode(C.PUMPING, W, end_use=False).needs(P, feeds=2)
    run = cut(node.world(), [supplier_id(P)])
    # Two full feeds: one gone still delivers all; both gone, nothing.
    assert held(run, 72.25)
    both = cut(node.world(), [supplier_id(P), supplier_id(P) + "-1"])
    assert states_from(both, 0.0) == {0.0}


def test_pumping_telecom_cut_12_h_then_0_9() -> None:
    node = OneNode(C.PUMPING, W, end_use=False)
    node.needs(T, kappa=0.5, form="threshold", tolerance="tolerance.pumping")
    run = cut(node.world(), [supplier_id(T)])
    assert held(run, 12.0)
    assert settles(run, 12.0) == pytest.approx(0.9)


def test_storage_drains_at_the_downstream_draw_then_its_consumers_lose_water() -> None:
    node = OneNode(C.STORAGE, W).fed_by_own_layer(line=False)
    node.stock("distribution_water", W, 12.0, "reserves.storage.peak_day_h", "pumps")
    run = cut(node.world(), ["UP-0"])
    assert held(run, 12.0)
    assert states_from(run, 12.0) == {0.0}
    relaxed = cut(node.world(), ["UP-0"], ["reserves.storage.peak_day_h"])
    assert held(relaxed, 72.25)


# --- Transport ------------------------------------------------------------------------------


def test_seaport_power_cut_no_power_no_cargo() -> None:
    node = OneNode(C.SEAPORT, R).needs(P)
    assert states_from(cut(node.world(), [supplier_id(P)]), 0.0) == {0.0}


def test_seaport_with_backup_power_works_cargo_for_its_hours() -> None:
    node = OneNode(C.SEAPORT, R)
    node.stock("backup_power", P, 48.0, "reserves.seaport.backup_power_h").needs(P)
    run = cut(node.world(), [supplier_id(P)])
    assert held(run, 48.0)
    assert states_from(run, 48.0) == {0.0}
    relaxed = cut(node.world(), [supplier_id(P)], ["reserves.seaport.backup_power_h"])
    assert held(relaxed, 72.25)


@pytest.mark.parametrize("node_class", [C.SEAPORT, C.FREIGHT_YARD])
def test_seaport_and_freight_yard_telecom_cut_24_h_then_0_5(node_class: NodeClass) -> None:
    node = OneNode(node_class, R).needs(T, tolerance="tolerance.seaport_freight_yard")
    run = cut(node.world(), [supplier_id(T)])
    assert held(run, 24.0)
    assert states_from(run, 24.0) == {0.5}
    assert held(cut(node.world(), [supplier_id(T)], ["tolerance.seaport_freight_yard"]), 72.25)


def test_seaport_fuel_cut_throttles() -> None:
    node = OneNode(C.SEAPORT, R).needs(F, form="threshold")
    assert states_from(cut(node.world(), [supplier_id(F)]), 0.0) == {0.0}
    assert node.dependencies[0].mode == "throttle"


@pytest.mark.parametrize(
    ("supplier", "receipt", "mode"),
    [(P, "pipeline", "trip"), (F, "pipeline", "trip"), (F, "truck", "throttle")],
)
def test_airport_power_or_fuel_cut_puts_it_out(supplier: Layer, receipt: str, mode: str) -> None:
    # A pipeline-fed airport trips on fuel (physical flow); a truck-fed one throttles
    # (logistic), which a full cut also takes to 0.
    node = OneNode(C.AIRPORT, R, {"towered": True, "fuel_receipt": receipt}).needs(supplier)
    assert states_from(cut(node.world(), [supplier_id(supplier)]), 0.0) == {0.0}
    assert node.dependencies[0].mode == mode


def test_towered_airport_telecom_cut_trips_at_once() -> None:
    node = OneNode(C.AIRPORT, R, {"towered": True}).needs(T, tolerance="tolerance.towered_airport")
    assert states_from(cut(node.world(), [supplier_id(T)]), 0.0) == {0.0}


def test_airport_not_towered_telecom_cut_24_h_then_0_8() -> None:
    node = OneNode(C.AIRPORT, R, {"towered": False})
    node.needs(T, tolerance="tolerance.airport_not_towered")
    run = cut(node.world(), [supplier_id(T)])
    assert held(run, 24.0)
    assert settles(run, 24.0) == pytest.approx(0.8)


# --- Fuel -----------------------------------------------------------------------------------


def test_import_terminal_power_cut_trips() -> None:
    node = OneNode(C.IMPORT_TERMINAL, F, {"product": "lng"}, end_use=False).needs(P)
    assert states_from(cut(node.world(), [supplier_id(P)]), 0.0) == {0.0}


def test_import_terminal_telecom_cut_12_h_then_0_8_scaled_by_the_public_share() -> None:
    node = OneNode(C.IMPORT_TERMINAL, F, {"product": "lng"}, end_use=False)
    node.needs(T, kappa=0.2, form="threshold", tolerance="tolerance.import_terminal")
    run = cut(node.world(), [supplier_id(T)])
    assert held(run, 12.0)
    assert settles(run, 12.0) == pytest.approx(1.0 - 0.2 * 0.2)


def test_import_terminal_seaport_cut_is_covered_by_its_lng_stock() -> None:
    node = OneNode(C.IMPORT_TERMINAL, F, {"product": "lng"}, end_use=False)
    node.stock("lng", R, 11 * 24.0, "reserves.lng.days").needs(R, form="threshold")
    assert held(cut(node.world(), [supplier_id(R)]), 72.25)
    no_stock = OneNode(C.IMPORT_TERMINAL, F, {"product": "lng"}, end_use=False)
    no_stock.needs(R, form="threshold")
    assert no_stock.dependencies[0].mode == "throttle"
    assert states_from(cut(no_stock.world(), [supplier_id(R)]), 0.0) == {0.0}


def test_tank_farm_power_cut_trips() -> None:
    node = OneNode(C.TANK_FARM, F, {"pipeline_connected": True}, end_use=False).needs(P)
    assert states_from(cut(node.world(), [supplier_id(P)]), 0.0) == {0.0}


@pytest.mark.parametrize(
    ("connected", "rule_id", "t_h", "d"),
    [(True, "tolerance.tank_farm_pipeline", 1.0, 0.5),
     (False, "tolerance.tank_farm_not_connected", 12.0, 0.6)],
)  # fmt: skip
def test_tank_farm_telecom_cut(connected: bool, rule_id: str, t_h: float, d: float) -> None:
    node = OneNode(C.TANK_FARM, F, {"pipeline_connected": connected}, end_use=False)
    node.needs(T, tolerance=rule_id)
    run = cut(node.world(), [supplier_id(T)])
    assert held(run, t_h)
    assert settles(run, t_h) == pytest.approx(d)


def test_depot_power_cut_trips_and_its_road_cut_throttles() -> None:
    node = OneNode(C.DEPOT, F).needs(P)
    assert states_from(cut(node.world(), [supplier_id(P)]), 0.0) == {0.0}
    road = OneNode(C.DEPOT, F).needs(R, form="threshold")
    assert road.dependencies[0].mode == "throttle"
    assert states_from(cut(road.world(), [supplier_id(R)]), 0.0) == {0.0}


def test_depot_telecom_cut_12_h_then_0_6() -> None:
    node = OneNode(C.DEPOT, F).needs(T, tolerance="tolerance.depot")
    run = cut(node.world(), [supplier_id(T)])
    assert held(run, 12.0)
    assert settles(run, 12.0) == pytest.approx(0.6)


@pytest.mark.parametrize("supplier", [P, W])
def test_refinery_power_or_water_cut_trips(supplier: Layer) -> None:
    node = OneNode(C.REFINERY, F, end_use=False).needs(supplier)
    assert states_from(cut(node.world(), [supplier_id(supplier)]), 0.0) == {0.0}


def test_refinery_telecom_cut_has_no_effect_inside_72_h() -> None:
    node = OneNode(C.REFINERY, F, end_use=False).needs(T, tolerance="tolerance.refinery")
    assert held(cut(node.world(), [supplier_id(T)]), 72.0)


# --- Healthcare -----------------------------------------------------------------------------

HOSPITAL = {"records_hosted": False, "standby_fuel": "diesel"}


def hospital(fails_to_start: bool = False) -> OneNode:
    node = OneNode(C.TERTIARY, Layer.HEALTHCARE, HOSPITAL)
    node.generator(72.0, "reserves.hospital.generator_fuel_h", fails_to_start=fails_to_start)
    return node.needs(P)


def test_hospital_power_cut_steps_to_0_6_and_deliveries_hold_it_there() -> None:
    node = hospital().deliveries_from()
    run = cut(node.world(), [supplier_id(P)])
    assert states_from(run, 0.0) == {0.6}
    assert node.dependencies[0].mode == "step_to_floor"
    assert [d.time_h for d in run.deliveries] == [12.0, 36.0, 60.0]


def test_hospital_power_cut_runs_its_fuel_dry_at_72_h_without_deliveries() -> None:
    run = cut(hospital().world(), [supplier_id(P)], horizon_h=80.0)
    assert {s for t, s in zip(run.times, run.state(TARGET), strict=True) if t < 72.0} == {0.6}
    assert run.at(TARGET, 72.0) == 0.0


def test_hospital_whose_generator_fails_to_start_is_out() -> None:
    assert states_from(cut(hospital(fails_to_start=True).world(), [supplier_id(P)]), 0.0) == {0.0}


def test_the_floor_after_the_generator_stops_is_ruled_with_its_two_alternatives() -> None:
    rule = RULES.rule("dynamics.floor_after_generator_stops")
    assert rule.value == "trip on what arrives"
    assert rule.theta_alternatives == (
        "throttle: runs at what arrives",
        "the essential fraction while at least that share arrives, else out",
    )
    assert rule.grade == "J"
    assert rule.ruling is not None
    assert rule.ruling.date == "2026-10-19"


def test_a_hospital_trips_on_what_arrives_once_its_generator_stops() -> None:
    trip_point = RULES.number("dynamics.trip_point")
    for kappa, expected in ((trip_point + 0.01, 1.0), (trip_point - 0.01, 0.0)):
        node = OneNode(C.TERTIARY, Layer.HEALTHCARE, HOSPITAL)
        node.generator(72.0, "reserves.hospital.generator_fuel_h", fails_to_start=True)
        run = cut(node.needs(P, kappa).world(), [])
        assert node.dependencies[0].mode == "step_to_floor"
        assert run.at(TARGET, 0.0) == expected, kappa


def test_an_alternative_floor_after_the_generator_stops_is_not_yet_selectable() -> None:
    world = hospital(fails_to_start=True).world(
        floor_after_generator_stops="throttle: runs at what arrives"
    )
    with pytest.raises(ValueError, match="selectable only in a later phase"):
        cut(world, [supplier_id(P)])


def test_hospital_water_cut_runs_on_stored_water_about_72_h_then_trips() -> None:
    node = OneNode(C.TERTIARY, Layer.HEALTHCARE, HOSPITAL)
    node.stock("water", W, 72.0, "reserves.hospital.water_h").needs(W)
    run = cut(node.world(), [supplier_id(W)], horizon_h=80.0)
    assert held(run, 72.0)
    assert run.at(TARGET, 72.0) == 0.0


@pytest.mark.parametrize(
    ("hosted", "rule_id"),
    [(False, "tolerance.hospital_records_on_site"), (True, "tolerance.hospital_records_hosted")],
)
def test_hospital_telecom_cut(hosted: bool, rule_id: str) -> None:
    node = OneNode(C.TERTIARY, Layer.HEALTHCARE, {**HOSPITAL, "records_hosted": hosted})
    node.needs(T, tolerance=rule_id)
    run = cut(node.world(), [supplier_id(T)])
    if not hosted:
        assert held(run, 24.0)
        assert settles(run, 24.0) == pytest.approx(0.85)
        return
    assert held(run, 0.5)
    assert run.at(TARGET, 2.25) == pytest.approx(1.0 - (2.25 - 0.5) / 3.5 * 0.35)
    assert settles(run, 4.0) == pytest.approx(0.65)


def test_hospital_supplies_cut_72_h_of_stock_then_throttles() -> None:
    node = OneNode(C.TERTIARY, Layer.HEALTHCARE, HOSPITAL)
    node.stock("supplies", R, 72.0, "reserves.hospital.supplies_h").needs(R, form="threshold")
    run = cut(node.world(), [supplier_id(R)], horizon_h=80.0)
    assert held(run, 72.0)
    assert node.dependencies[0].mode == "throttle"
    assert run.at(TARGET, 72.0) == 0.0


@pytest.mark.parametrize("supplier", [P, W])
def test_clinic_power_or_water_cut_trips(supplier: Layer) -> None:
    node = OneNode(C.CLINIC, Layer.HEALTHCARE, {"standby_fuel": "none"}).needs(supplier)
    assert states_from(cut(node.world(), [supplier_id(supplier)]), 0.0) == {0.0}


def test_clinic_telecom_cut_24_h_then_0_8() -> None:
    node = OneNode(C.CLINIC, Layer.HEALTHCARE, {"standby_fuel": "none"})
    node.needs(T, tolerance="tolerance.clinic")
    run = cut(node.world(), [supplier_id(T)])
    assert held(run, 24.0)
    assert settles(run, 24.0) == pytest.approx(0.8)


def test_clinic_supplies_cut_throttles() -> None:
    node = OneNode(C.CLINIC, Layer.HEALTHCARE, {"standby_fuel": "none"}).needs(R, form="threshold")
    assert node.dependencies[0].mode == "throttle"
    assert states_from(cut(node.world(), [supplier_id(R)]), 0.0) == {0.0}


def test_blood_bank_power_cut_72_h_of_fuel_then_trips_unless_resupplied() -> None:
    node = OneNode(C.BLOOD_BANK, Layer.HEALTHCARE, {"standby_fuel": "diesel"})
    node.generator(72.0, "reserves.blood_bank.generator_fuel_h").needs(P)
    run = cut(node.world(), [supplier_id(P)], horizon_h=80.0)
    assert held(run, 72.0)
    assert run.at(TARGET, 72.0) == 0.0
    supplied = node.deliveries_from()
    assert held(cut(supplied.world(), [supplier_id(P)], horizon_h=80.0), 80.25)


def test_blood_bank_blood_stock_covers_7_days() -> None:
    node = OneNode(C.BLOOD_BANK, Layer.HEALTHCARE, {"standby_fuel": "diesel"})
    node.stock("blood", R, 7 * 24.0, "reserves.blood_bank.blood_stock_days").needs(
        R, form="threshold"
    )
    assert held(cut(node.world(), [supplier_id(R)]), 72.25)


def test_blood_bank_telecom_cut_24_h_then_0_7() -> None:
    node = OneNode(C.BLOOD_BANK, Layer.HEALTHCARE, {"standby_fuel": "diesel"})
    node.needs(T, tolerance="tolerance.blood_bank")
    run = cut(node.world(), [supplier_id(T)])
    assert held(run, 24.0)
    assert settles(run, 24.0) == pytest.approx(0.7)


def test_first_change_helper_reads_the_first_hour_off_1() -> None:
    run = cut(mast().needs(P).world(), [supplier_id(P)])
    assert first_change(run) == 4.0
