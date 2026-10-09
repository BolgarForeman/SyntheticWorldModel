import itertools

import pytest

from swm.recipe.dependencies import (
    DEPENDENCY_TABLE,
    SUBTYPE_VALUES,
    Dependency,
    DependencyType,
    Grade,
    Role,
    SupplierWhen,
    consumer_classes,
    coupling_pairs,
    resolve_row,
    rows_for,
)
from swm.recipe.schema import LAYER_NODE_CLASSES, Layer, NodeClass

C = NodeClass


def combinations(node_class: NodeClass) -> list[dict[str, object]]:
    domains = SUBTYPE_VALUES.get(node_class, {})
    names = sorted(domains)
    return [
        dict(zip(names, values, strict=True))
        for values in itertools.product(*(domains[n] for n in names))
    ]


def test_there_are_21_couplings() -> None:
    assert len(coupling_pairs()) == 21
    assert all(supplier != Layer.HEALTHCARE for supplier, _ in coupling_pairs())


def test_every_pair_resolves_to_exactly_one_row_for_every_subtype() -> None:
    checked = 0
    for supplier, consumer in coupling_pairs():
        for node_class in consumer_classes(consumer):
            for subtype in combinations(node_class):
                row = resolve_row(supplier, node_class, subtype)
                assert row.supplier_layer == supplier
                assert row.consumer_class == node_class
                checked += 1
    assert checked > 87


def test_no_row_exists_outside_the_21_couplings() -> None:
    allowed = set(coupling_pairs())
    for row in DEPENDENCY_TABLE:
        consumer = next(layer for layer, classes in LAYER_NODE_CLASSES.items()
                        if row.consumer_class in classes)  # fmt: skip
        assert (row.supplier_layer, consumer) in allowed, row.key


def test_row_keys_are_unique() -> None:
    keys = [row.key for row in DEPENDENCY_TABLE]
    assert len(keys) == len(set(keys))


def test_an_unmatched_subtype_is_an_error() -> None:
    with pytest.raises(LookupError, match="matches 0 rows"):
        resolve_row(Layer.FUEL, C.GENERATION, {"fuel_kind": "wood"})


def test_active_rows_are_complete_and_none_rows_are_empty() -> None:
    for row in DEPENDENCY_TABLE:
        if row.dependency == Dependency.NONE:
            assert row.suppliers == ()
            assert row.dependency_type is None
            assert row.role is None
        else:
            assert row.suppliers, row.key
            assert row.dependency_type is not None
            assert row.role is not None
            assert row.commodity
            assert row.grade is not None
        assert row.source
        if row.us:
            assert row.grade == Grade.S


def test_suppliers_belong_to_the_supplier_layer() -> None:
    for row in DEPENDENCY_TABLE:
        for option in row.suppliers:
            assert option.node_class in LAYER_NODE_CLASSES[row.supplier_layer], row.key
            if option.product is not None:
                assert option.node_class == C.IMPORT_TERMINAL
                assert option.product in SUBTYPE_VALUES[C.IMPORT_TERMINAL]["product"]
        if row.large_load_supplier is not None:
            assert row.large_load_supplier == C.TRANSMISSION_SUBSTATION
            assert row.rule == "rule 4"


def test_an_lng_or_coal_terminal_never_supplies_bunkers_jet_fuel_or_diesel() -> None:
    for row in rows_for(Layer.FUEL, C.SEAPORT) + rows_for(Layer.FUEL, C.AIRPORT):
        for option in row.suppliers:
            if option.node_class == C.IMPORT_TERMINAL:
                assert option.product == "oil"


def test_buffer_resupply_rows_are_fuel_rows_under_rule_2() -> None:
    buffer_rows = [row for row in DEPENDENCY_TABLE if row.role == Role.BUFFER_RESUPPLY]
    assert {row.consumer_class for row in buffer_rows} == {
        C.EXCHANGE, C.DATA_CENTRE, C.CABLE_LANDING, C.MAST, C.TREATMENT, C.PUMPING,
        C.TERTIARY, C.REGIONAL, C.CLINIC, C.BLOOD_BANK,
    }  # fmt: skip
    for row in buffer_rows:
        assert row.supplier_layer == Layer.FUEL
        assert row.dependency_type == DependencyType.LOGISTIC
        assert row.rule == "rule 2"


def test_public_telecom_share_marks_the_control_rows_of_power_water_and_pipelines() -> None:
    marked = {row.consumer_class for row in DEPENDENCY_TABLE if row.rule == "rule 1"}
    assert marked == {
        C.GENERATION, C.TRANSMISSION_SUBSTATION, C.DISTRIBUTION_SUBSTATION, C.TREATMENT,
        C.PUMPING, C.RESERVOIR, C.TANK_FARM, C.IMPORT_TERMINAL,
    }  # fmt: skip
    for row in DEPENDENCY_TABLE:
        if row.rule == "rule 1":
            assert row.supplier_layer == Layer.TELECOM
            assert row.dependency_type == DependencyType.CONTROL


def test_transport_rows_list_origins_under_rule_3() -> None:
    origins = {C.SEAPORT, C.AIRPORT, C.FREIGHT_YARD}
    for row in DEPENDENCY_TABLE:
        if row.supplier_layer == Layer.TRANSPORT and row.dependency != Dependency.NONE:
            assert row.rule == "rule 3"
            assert {option.node_class for option in row.suppliers} <= origins


@pytest.mark.parametrize(
    ("supplier", "node_class", "subtype", "dependency", "suppliers"),
    [
        (Layer.FUEL, C.GENERATION, {"fuel_kind": "lng"}, Dependency.CORE, [C.IMPORT_TERMINAL]),
        (Layer.FUEL, C.GENERATION, {"fuel_kind": "coal"}, Dependency.CORE, [C.IMPORT_TERMINAL]),
        (Layer.FUEL, C.GENERATION, {"fuel_kind": "hydro"}, Dependency.NONE, []),
        (Layer.POWER, C.RESERVOIR, {}, Dependency.NONE, []),
        # Decision 0013: any substation can supply any power consumer.
        (
            Layer.POWER,
            C.FREIGHT_YARD,
            {},
            Dependency.OPTIONAL,
            [C.DISTRIBUTION_SUBSTATION, C.TRANSMISSION_SUBSTATION],
        ),
        (Layer.TELECOM, C.STORAGE, {}, Dependency.NONE, []),
        (Layer.TELECOM, C.AIRPORT, {"towered": True}, Dependency.CORE, [C.EXCHANGE]),
        (Layer.WATER, C.BLOOD_BANK, {}, Dependency.OPTIONAL, [C.STORAGE, C.PUMPING]),
        (Layer.TRANSPORT, C.CLINIC, {}, Dependency.CORE, [C.FREIGHT_YARD]),
        (Layer.POWER, C.BRIDGE, {}, Dependency.NONE, []),
        # Decision 0008, answer 1: supplier lists narrowed to what the research lanes found.
        (Layer.FUEL, C.CABLE_LANDING, {}, Dependency.CORE, [C.DEPOT]),
        (Layer.FUEL, C.REGIONAL, {}, Dependency.CORE, [C.DEPOT]),
        (Layer.FUEL, C.TERTIARY, {}, Dependency.CORE, [C.DEPOT, C.TANK_FARM]),
        (Layer.TELECOM, C.TRANSMISSION_SUBSTATION, {}, Dependency.CORE, [C.EXCHANGE]),
        (Layer.TELECOM, C.BLOOD_BANK, {}, Dependency.CORE, [C.EXCHANGE, C.DATA_CENTRE]),
        (Layer.TELECOM, C.REFINERY, {}, Dependency.CORE, [C.EXCHANGE]),
        (Layer.TELECOM, C.DISTRIBUTION_SUBSTATION, {}, Dependency.CORE, [C.EXCHANGE, C.MAST]),
    ],
)
def test_rows_say_what_section_4_3a_says(
    supplier: Layer,
    node_class: NodeClass,
    subtype: dict[str, object],
    dependency: Dependency,
    suppliers: list[NodeClass],
) -> None:
    row = resolve_row(supplier, node_class, subtype)
    assert row.dependency == dependency
    assert [option.node_class for option in row.suppliers] == suppliers


def test_rule_conditions_on_suppliers_are_kept() -> None:
    water_generation = resolve_row(
        Layer.WATER, C.GENERATION, {"fuel_kind": "lng", "makeup_water": "municipal"}
    )
    assert any(o.when == SupplierWhen.INLAND for o in water_generation.suppliers)
    depot = resolve_row(Layer.TRANSPORT, C.DEPOT, {})
    assert any(o.when == SupplierWhen.OUTLYING_ISLAND for o in depot.suppliers)
    tertiary = resolve_row(Layer.POWER, C.TERTIARY, {})
    assert tertiary.rule == "rule 5"
    lng_terminal = resolve_row(Layer.POWER, C.IMPORT_TERMINAL, {"product": "lng"})
    # Decision 0013: either class; rule 4 still sends a large load to transmission.
    assert [o.node_class for o in lng_terminal.suppliers] == [
        C.DISTRIBUTION_SUBSTATION,
        C.TRANSMISSION_SUBSTATION,
    ]
