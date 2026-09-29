"""The dependency table: which node classes depend on which supplier layer, on what, and how.

This is structure v0.5 §4.3a encoded as one immutable table. It is the authority for which
nodes depend on which. Rows are neither added, dropped nor retyped here; a row that looks wrong
is raised with the design side. Every row cites its evidence in
``docs/design/evidence/Dependency_Table_Evidence_v0_1.md``: the lane section and its source
keys, and review findings (F1-F19) where they shaped the row.

CHOICE: the whole table, placeholder (open decision: realism ranges).
"""

from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum

from swm.recipe.schema import DEFAULT_COUPLINGS, LAYER_NODE_CLASSES, Layer, NodeClass


class Dependency(StrEnum):
    """Whether a consumer takes the dependency: always, by density, or never."""

    CORE = "core"
    OPTIONAL = "optional"
    NONE = "none"


class DependencyType(StrEnum):
    """The dissertation's four dependency types."""

    PHYSICAL_FLOW = "physical_flow"
    LOGISTIC = "logistic"
    CONTROL = "control"
    SERVICE = "service"


class Role(StrEnum):
    """What an edge does: primary supply, or resupply of a backup generator's fuel (rule 2)."""

    PRIMARY_SUPPLY = "primary_supply"
    BUFFER_RESUPPLY = "buffer_resupply"


class Grade(StrEnum):
    """Evidence grade: a standard, literature or a government report, or judgment."""

    S = "S"
    L = "L"
    J = "J"


class SupplierWhen(StrEnum):
    """Conditions on a supplier option that the couplings stage decides from the world."""

    INLAND = "inland"
    OUTLYING_ISLAND = "outlying_island"
    HAS_JETTY = "has_jetty"
    HAS_TRUCK_RACK = "has_truck_rack"


COMMODITIES: Mapping[Layer, str] = {
    Layer.POWER: "electricity",
    Layer.TELECOM: "communications",
    Layer.WATER: "water",
    Layer.TRANSPORT: "transport access",
    Layer.FUEL: "fuel",
}
"""The commodity each supplier layer carries (§4.3a headings). Healthcare supplies nothing."""


@dataclass(frozen=True)
class SupplierOption:
    """A supplier class a row allows, with any product restriction or world condition."""

    node_class: NodeClass
    product: str | None = None
    when: SupplierWhen | None = None


Clause = tuple[str, tuple[object, ...]]


@dataclass(frozen=True)
class Condition:
    """A predicate on a consumer's subtype attributes.

    It holds when every all_of clause holds and, if any are given, at least one any_of clause.
    A clause holds when the attribute's value is one of those listed.
    """

    all_of: tuple[Clause, ...] = ()
    any_of: tuple[Clause, ...] = ()

    def matches(self, subtype: Mapping[str, object]) -> bool:
        """Return whether a consumer with these subtype attributes meets the condition.

        Parameters
        ----------
        subtype : Mapping[str, object]
            The consumer's subtype attributes; a missing attribute meets no clause.

        Returns
        -------
        bool
            True if the condition holds.

        Spec: Work Order 4, A2.
        """
        if not all(_holds(clause, subtype) for clause in self.all_of):
            return False
        return not self.any_of or any(_holds(clause, subtype) for clause in self.any_of)

    def label(self) -> str:
        """Return the condition as text, for row keys."""
        parts = [f"{name}={'|'.join(str(v) for v in values)}" for name, values in self.all_of]
        if self.any_of:
            alternatives = [
                f"{name}={'|'.join(str(v) for v in values)}" for name, values in self.any_of
            ]
            parts.append("(" + " or ".join(alternatives) + ")")
        return ",".join(parts)


def _holds(clause: Clause, subtype: Mapping[str, object]) -> bool:
    name, values = clause
    return name in subtype and subtype[name] in values


ALWAYS = Condition()


@dataclass(frozen=True)
class DependencyRow:
    """One row of §4.3a: a consumer class's dependency on one supplier layer."""

    supplier_layer: Layer
    consumer_class: NodeClass
    condition: Condition
    dependency: Dependency
    dependency_type: DependencyType | None
    role: Role | None
    commodity: str | None
    suppliers: tuple[SupplierOption, ...]
    large_load_supplier: NodeClass | None
    rule: str | None
    grade: Grade | None
    us: bool
    source: str

    @property
    def key(self) -> str:
        """Return a stable key: supplier layer, consumer class and condition."""
        condition = self.condition.label()
        suffix = f"[{condition}]" if condition else ""
        return f"{self.supplier_layer}>{self.consumer_class}{suffix}"


C = NodeClass
_Opt = SupplierOption


def _row(
    supplier: Layer,
    consumers: tuple[NodeClass, ...],
    dependency: Dependency,
    suppliers: tuple[SupplierOption, ...] = (),
    *,
    kind: DependencyType | None = None,
    role: Role | None = Role.PRIMARY_SUPPLY,
    condition: Condition = ALWAYS,
    large_load: NodeClass | None = None,
    rule: str | None = None,
    grade: Grade | None,
    us: bool = False,
    source: str,
) -> tuple[DependencyRow, ...]:
    active = dependency != Dependency.NONE
    return tuple(
        DependencyRow(
            supplier_layer=supplier,
            consumer_class=consumer,
            condition=condition,
            dependency=dependency,
            dependency_type=kind if active else None,
            role=role if active else None,
            commodity=COMMODITIES[supplier] if active else None,
            suppliers=suppliers if active else (),
            large_load_supplier=large_load if active else None,
            rule=rule,
            grade=grade,
            us=us,
            source=source,
        )
        for consumer in consumers
    )


def _when(name: str, *values: object) -> Condition:
    return Condition(all_of=((name, values),))


def _all(*clauses: Clause) -> Condition:
    return Condition(all_of=clauses)


CORE, OPTIONAL, NONE = Dependency.CORE, Dependency.OPTIONAL, Dependency.NONE
PF, LOG, CTL, SVC = (
    DependencyType.PHYSICAL_FLOW,
    DependencyType.LOGISTIC,
    DependencyType.CONTROL,
    DependencyType.SERVICE,
)
P, B = Role.PRIMARY_SUPPLY, Role.BUFFER_RESUPPLY
S, L, J = Grade.S, Grade.L, Grade.J
PHASE_1_TRANSPORT_NODES = (C.BRIDGE, C.ROAD_JUNCTION, C.RAIL_NODE)
FUEL_FIRED = ("lng", "oil", "coal")
DIST, TRANS = C.DISTRIBUTION_SUBSTATION, C.TRANSMISSION_SUBSTATION
RULE_7 = "§4.3a rule 7: Phase 1 transport nodes consume nothing"

_POWER = Layer.POWER
_POWER_ROWS: tuple[DependencyRow, ...] = (
    *_row(_POWER, (C.EXCHANGE,), CORE, (_Opt(DIST),), kind=PF, grade=L,
          source="lane_power power→telecom: S-FCC07 (never in force), S-CPUC, S-DOE; review F9"),
    *_row(_POWER, (C.MAST,), CORE, (_Opt(DIST),), kind=PF, grade=L,
          source="lane_power power→telecom: S-GAO, S-CPUC D.20-07-011"),
    *_row(_POWER, (C.CABLE_LANDING,), CORE, (_Opt(DIST),), kind=PF, grade=J,
          source="lane_power power→telecom: S-NECPFE (mechanism only)"),
    *_row(_POWER, (C.DATA_CENTRE,), CORE, (_Opt(DIST),), kind=PF, large_load=TRANS,
          rule="rule 4", grade=L, source="lane_power power→telecom: S-NERC, S-UPTIME"),
    *_row(_POWER, (C.TREATMENT,), CORE, (_Opt(DIST),), kind=PF, large_load=TRANS,
          rule="rule 4", grade=S, us=True,
          source="lane_power power→water: S-10SS §2.6, S-EPAPWR, S-AWWA"),
    *_row(_POWER, (C.PUMPING,), CORE, (_Opt(DIST),), kind=PF, grade=S, us=True,
          source="lane_power power→water: S-10SS §6.3.4-6.3.5, S-EPAPWR"),
    *_row(_POWER, (C.RESERVOIR, C.STORAGE), NONE, grade=J,
          source="lane_power power→water: gravity; storage is the buffer (S-10SS); review F19"),
    *_row(_POWER, (C.SEAPORT,), CORE, (_Opt(DIST),), kind=PF, large_load=TRANS,
          rule="rule 4", grade=L, source="lane_power power→transport: S-EPRIPORT"),
    *_row(_POWER, (C.AIRPORT,), CORE, (_Opt(DIST),), kind=PF, grade=S, us=True,
          source="lane_power power→transport: S-FAA30J §9.4, S-FAA6950; review F8"),
    *_row(_POWER, (C.FREIGHT_YARD,), OPTIONAL, (_Opt(DIST),), kind=PF, grade=J,
          source="lane_power power→transport: judgment, no source"),
    *_row(_POWER, PHASE_1_TRANSPORT_NODES, NONE, rule="rule 7", grade=None, source=RULE_7),
    *_row(_POWER, (C.REFINERY,), CORE, (_Opt(TRANS),), kind=PF, grade=L,
          source="lane_power power→fuel: S-NPC66 (1966; modern source still needed)"),
    *_row(_POWER, (C.TANK_FARM,), CORE, (_Opt(DIST),), kind=PF, grade=L,
          source="lane_power power→fuel: S-NPC66, S-FL526; review F9"),
    *_row(_POWER, (C.DEPOT,), CORE, (_Opt(DIST),), kind=PF, grade=L,
          source="lane_power power→fuel: S-NPC66, S-FL526"),
    *_row(_POWER, (C.IMPORT_TERMINAL,), CORE, (_Opt(DIST),), kind=PF,
          condition=_when("product", "oil", "coal"), grade=L,
          source="lane_power power→fuel: S-LNG, S-NPC66 (oil); ruling R5 (coal)"),
    *_row(_POWER, (C.IMPORT_TERMINAL,), CORE, (_Opt(TRANS),), kind=PF,
          condition=_when("product", "lng"), grade=L,
          source="lane_power power→fuel: S-LNG (LNG send-out and seawater pumps)"),
    *_row(_POWER, (C.TERTIARY,), CORE, (_Opt(DIST),), kind=PF, rule="rule 5", grade=S,
          us=True, source="lane_power power→healthcare: S-CMS, S-NFPA, S-TW-HOSP; ruling R4, "
          "review F4"),
    *_row(_POWER, (C.REGIONAL,), CORE, (_Opt(DIST),), kind=PF, grade=S, us=True,
          source="lane_power power→healthcare: S-CMS, S-NFPA"),
    *_row(_POWER, (C.CLINIC,), CORE, (_Opt(DIST),), kind=PF, grade=L,
          source="lane_power power→healthcare: S-DOE"),
    *_row(_POWER, (C.BLOOD_BANK,), CORE, (_Opt(DIST),), kind=PF, grade=L,
          source="lane_power power→healthcare: S-ACHC"),
)  # fmt: skip

_TEL = Layer.TELECOM
_EX_MAST = (_Opt(C.EXCHANGE), _Opt(C.MAST))
_EX_MAST_DC = (_Opt(C.EXCHANGE), _Opt(C.MAST), _Opt(C.DATA_CENTRE))
_TELECOM_ROWS: tuple[DependencyRow, ...] = (
    *_row(_TEL, (C.GENERATION, C.TRANSMISSION_SUBSTATION, C.DISTRIBUTION_SUBSTATION), CORE,
          _EX_MAST, kind=CTL, rule="rule 1", grade=L,
          source="lane_telecom telecom→power: S1, S2, S3, S13; ruling R1 (DOE 2023, "
          "台電月刊 Vol. 700); review F1, F11"),
    *_row(_TEL, (C.TREATMENT, C.PUMPING), CORE, _EX_MAST, kind=CTL, rule="rule 1", grade=L,
          source="lane_telecom telecom→water: S4, S5; ruling R1"),
    *_row(_TEL, (C.RESERVOIR,), OPTIONAL, (_Opt(C.MAST), _Opt(C.EXCHANGE)), kind=CTL,
          rule="rule 1", grade=J, source="lane_telecom telecom→water: S5"),
    *_row(_TEL, (C.STORAGE,), NONE, grade=J,
          source="lane_telecom telecom→water: level telemetry folds into pumping; review F17"),
    *_row(_TEL, (C.AIRPORT,), CORE, (_Opt(C.EXCHANGE),), kind=CTL,
          condition=_when("towered", True), grade=L,
          source="lane_telecom telecom→transport: S6, S7, S8; review F16"),
    *_row(_TEL, (C.AIRPORT,), OPTIONAL, _EX_MAST, kind=SVC, condition=_when("towered", False),
          grade=J, source="lane_telecom telecom→transport, condition C1; review F16"),
    *_row(_TEL, (C.SEAPORT,), CORE, _EX_MAST_DC, kind=SVC, grade=L,
          source="lane_telecom telecom→transport: S9 (Kramek; review F10)"),
    *_row(_TEL, (C.FREIGHT_YARD,), CORE, _EX_MAST_DC, kind=SVC, grade=J,
          source="lane_telecom telecom→transport: S9 by analogy"),
    *_row(_TEL, PHASE_1_TRANSPORT_NODES, NONE, rule="rule 7", grade=None,
          source=RULE_7 + "; ruling R7"),
    *_row(_TEL, (C.REFINERY,), CORE, _EX_MAST_DC, kind=SVC, grade=J,
          source="lane_telecom telecom→fuel: S10 (scope only)"),
    *_row(_TEL, (C.DEPOT,), CORE, _EX_MAST_DC, kind=SVC, grade=J,
          source="lane_telecom telecom→fuel: S10"),
    *_row(_TEL, (C.TANK_FARM,), CORE, _EX_MAST, kind=CTL, rule="rule 1",
          condition=_when("pipeline_connected", True), grade=S, us=True,
          source="lane_telecom telecom→fuel: S11 (49 CFR 195.446), S10; condition C2"),
    *_row(_TEL, (C.TANK_FARM,), OPTIONAL, _EX_MAST, kind=SVC,
          condition=_when("pipeline_connected", False), grade=J,
          source="lane_telecom telecom→fuel, condition C2"),
    *_row(_TEL, (C.IMPORT_TERMINAL,), CORE, _EX_MAST, kind=CTL, rule="rule 1", grade=S,
          us=True, source="lane_telecom telecom→fuel: S11, S12 (49 CFR 193.2519), S10"),
    *_row(_TEL, (C.TERTIARY, C.REGIONAL), CORE, _EX_MAST_DC, kind=SVC, grade=L,
          source="lane_telecom telecom→healthcare: S14, S15, S16, S17; ruling R6; review F6"),
    *_row(_TEL, (C.CLINIC,), CORE, _EX_MAST_DC, kind=SVC, grade=J,
          source="lane_telecom telecom→healthcare: S17; ruling R6; review F6"),
    *_row(_TEL, (C.BLOOD_BANK,), CORE, _EX_MAST_DC, kind=SVC, grade=J,
          source="lane_telecom telecom→healthcare: S18 (IT outage); ruling R6; review F10"),
)  # fmt: skip

_WAT = Layer.WATER
_STORE_PUMP = (_Opt(C.STORAGE), _Opt(C.PUMPING))
_WATER_ROWS: tuple[DependencyRow, ...] = (
    *_row(_WAT, (C.GENERATION,), CORE,
          (*_STORE_PUMP, _Opt(C.RESERVOIR, when=SupplierWhen.INLAND)), kind=PF,
          condition=_all(("fuel_kind", FUEL_FIRED), ("makeup_water", ("municipal",))),
          grade=L, source="lane_water water→power: S1, S2, S3, S4; J for Taiwan; review F7"),
    *_row(_WAT, (C.GENERATION,), NONE,
          condition=_all(("fuel_kind", FUEL_FIRED), ("makeup_water", ("own_intake",))),
          grade=L, source="lane_water water→power: S3 (on-site desalting); review F7"),
    *_row(_WAT, (C.GENERATION,), NONE, condition=_when("fuel_kind", "hydro"), grade=L,
          source="lane_water water→power: S6, S7 (Feitsui)"),
    *_row(_WAT, (C.TRANSMISSION_SUBSTATION, C.DISTRIBUTION_SUBSTATION), NONE, grade=J,
          source="lane_water water→power: judgment"),
    *_row(_WAT, (C.EXCHANGE, C.MAST, C.CABLE_LANDING), NONE, grade=J,
          source="lane_water water→telecom: judgment (data-centre subset only)"),
    *_row(_WAT, (C.DATA_CENTRE,), CORE, _STORE_PUMP, kind=PF,
          condition=_when("cooling", "evaporative"), grade=L,
          source="lane_water water→telecom: S8, S9; review F13 (Appendix B default)"),
    *_row(_WAT, (C.DATA_CENTRE,), NONE, condition=_when("cooling", "dry"), grade=L,
          source="lane_water water→telecom, condition C2: dry cooling uses low to none (S8); "
          "the complement of the evaporative row"),
    *_row(_WAT, (C.REFINERY,), CORE, (*_STORE_PUMP, _Opt(C.RESERVOIR)), kind=PF, grade=L,
          source="lane_water water→fuel: S10, S11; review F18"),
    *_row(_WAT, (C.TANK_FARM, C.IMPORT_TERMINAL, C.DEPOT), OPTIONAL, _STORE_PUMP, kind=PF,
          grade=J, source="lane_water water→fuel: S11, S12, S13; review F9"),
    *_row(_WAT, (C.TERTIARY, C.REGIONAL), CORE, _STORE_PUMP, kind=PF, grade=S, us=True,
          source="lane_water water→healthcare: S14, S15, S16, S17"),
    *_row(_WAT, (C.CLINIC,), CORE, _STORE_PUMP, kind=PF, grade=L,
          source="lane_water water→healthcare: S14, S18 (not fetched)"),
    *_row(_WAT, (C.BLOOD_BANK,), OPTIONAL, _STORE_PUMP, kind=PF, grade=J,
          source="lane_water water→healthcare: judgment"),
)  # fmt: skip

_TRN = Layer.TRANSPORT
_TRANSPORT_ROWS: tuple[DependencyRow, ...] = (
    *_row(_TRN, (C.IMPORT_TERMINAL,), CORE, (_Opt(C.SEAPORT),), kind=LOG, rule="rule 3",
          grade=L, source="lane_transport transport→fuel: S1, S4, S7"),
    *_row(_TRN, (C.REFINERY,), CORE, (_Opt(C.SEAPORT),), kind=LOG, rule="rule 3",
          condition=_when("crude_receipt", "marine"), grade=L,
          source="lane_transport transport→fuel: S1, S2; condition 1"),
    *_row(_TRN, (C.REFINERY,), NONE, condition=_when("crude_receipt", "pipeline"), grade=J,
          source="lane_transport transport→fuel, condition 1; review F11"),
    *_row(_TRN, (C.TANK_FARM,), OPTIONAL,
          (_Opt(C.SEAPORT, when=SupplierWhen.HAS_JETTY),
           _Opt(C.FREIGHT_YARD, when=SupplierWhen.HAS_TRUCK_RACK)), kind=LOG, rule="rule 3",
          condition=Condition(any_of=(("has_jetty", (True,)), ("has_truck_rack", (True,)))),
          grade=L, source="lane_transport transport→fuel: S3, S4; condition 2"),
    *_row(_TRN, (C.TANK_FARM,), NONE,
          condition=_all(("has_jetty", (False,)), ("has_truck_rack", (False,))),
          grade=L, source="lane_transport transport→fuel, condition 2: pipeline-only tank "
          "farms; the complement of the jetty-or-rack row"),
    *_row(_TRN, (C.DEPOT,), CORE,
          (_Opt(C.FREIGHT_YARD), _Opt(C.SEAPORT, when=SupplierWhen.OUTLYING_ISLAND)), kind=LOG,
          rule="rule 3", grade=L,
          source="lane_transport transport→fuel: S3, S4, S7; review F12 (delivered fuel)"),
    *_row(_TRN, (C.TERTIARY, C.REGIONAL), CORE,
          (_Opt(C.FREIGHT_YARD), _Opt(C.SEAPORT), _Opt(C.AIRPORT)), kind=LOG, rule="rule 3",
          grade=L, source="lane_transport transport→healthcare: S7, S8, S9, S11; ruling R3, "
          "review F3"),
    *_row(_TRN, (C.CLINIC,), CORE, (_Opt(C.FREIGHT_YARD),), kind=LOG, rule="rule 3",
          grade=L, source="lane_transport transport→healthcare: S7, S11"),
    *_row(_TRN, (C.BLOOD_BANK,), CORE, (_Opt(C.FREIGHT_YARD), _Opt(C.AIRPORT)), kind=LOG,
          rule="rule 3", grade=L,
          source="lane_transport transport→healthcare: S7, S12; ruling R3"),
)  # fmt: skip

_FUE = Layer.FUEL
_DEPOT_TANK = (_Opt(C.DEPOT), _Opt(C.TANK_FARM))
_FUEL_ROWS: tuple[DependencyRow, ...] = (
    *_row(_FUE, (C.GENERATION,), CORE, (_Opt(C.IMPORT_TERMINAL, product="lng"),), kind=PF,
          condition=_when("fuel_kind", "lng"), grade=L,
          source="lane_fuel fuel→power: S20, S21, S22"),
    *_row(_FUE, (C.GENERATION,), CORE, (_Opt(C.TANK_FARM), _Opt(C.REFINERY)), kind=PF,
          condition=_when("fuel_kind", "oil"), grade=J,
          source="lane_fuel fuel→power: no source; review F15"),
    *_row(_FUE, (C.GENERATION,), CORE, (_Opt(C.IMPORT_TERMINAL, product="coal"),), kind=LOG,
          condition=_when("fuel_kind", "coal"), grade=L,
          source="lane_fuel fuel→power: S20, S24; ruling R5, review F5"),
    *_row(_FUE, (C.GENERATION,), NONE, condition=_when("fuel_kind", "hydro"), grade=J,
          source="lane_fuel fuel→power: S20 (hydro burns no fuel)"),
    *_row(_FUE, (C.TRANSMISSION_SUBSTATION, C.DISTRIBUTION_SUBSTATION), NONE, grade=J,
          source="lane_fuel fuel→power: station batteries, judgment"),
    *_row(_FUE, (C.EXCHANGE,), CORE, _DEPOT_TANK, kind=LOG, role=B, rule="rule 2", grade=L,
          source="lane_fuel fuel→telecom: S8, S6 (never in force); ruling R2, review F2, F9"),
    *_row(_FUE, (C.DATA_CENTRE,), CORE, _DEPOT_TANK, kind=LOG, role=B, rule="rule 2",
          grade=L, source="lane_fuel fuel→telecom: S10, S19; ruling R2, review F9"),
    *_row(_FUE, (C.CABLE_LANDING,), CORE, _DEPOT_TANK, kind=LOG, role=B, rule="rule 2",
          grade=J, source="lane_fuel fuel→telecom: S11; ruling R2"),
    *_row(_FUE, (C.MAST,), OPTIONAL, (_Opt(C.DEPOT),), kind=LOG, role=B, rule="rule 2",
          grade=L, source="lane_fuel fuel→telecom: S7, S6, S9; ruling R2"),
    *_row(_FUE, (C.TREATMENT,), CORE, _DEPOT_TANK, kind=LOG, role=B, rule="rule 2", grade=S,
          us=True, source="lane_fuel fuel→water: S12 §2.6, S13; ruling R2"),
    *_row(_FUE, (C.PUMPING,), OPTIONAL, (_Opt(C.DEPOT),), kind=LOG, role=B, rule="rule 2",
          grade=L, source="lane_fuel fuel→water: S12 §6.3.4, S13; ruling R2"),
    *_row(_FUE, (C.RESERVOIR, C.STORAGE), NONE, grade=J,
          source="lane_fuel fuel→water: gravity, judgment"),
    *_row(_FUE, (C.SEAPORT,), CORE,
          (_Opt(C.TANK_FARM), _Opt(C.IMPORT_TERMINAL, product="oil"), _Opt(C.REFINERY),
           _Opt(C.DEPOT)), kind=LOG, grade=L,
          source="lane_fuel fuel→transport: S15, S18; review F14"),
    *_row(_FUE, (C.AIRPORT,), CORE,
          (_Opt(C.REFINERY), _Opt(C.TANK_FARM), _Opt(C.IMPORT_TERMINAL, product="oil")),
          kind=PF, condition=_when("fuel_receipt", "pipeline"), grade=L,
          source="lane_fuel fuel→transport: S16, S17, S15; review F16"),
    *_row(_FUE, (C.AIRPORT,), CORE, (_Opt(C.DEPOT),), kind=LOG,
          condition=_when("fuel_receipt", "truck"), grade=L,
          source="lane_fuel fuel→transport: S15, S17; review F16"),
    *_row(_FUE, (C.FREIGHT_YARD,), CORE, _DEPOT_TANK, kind=LOG, grade=L,
          source="lane_fuel fuel→transport: S19, S15"),
    *_row(_FUE, PHASE_1_TRANSPORT_NODES, NONE, rule="rule 7", grade=None, source=RULE_7),
    *_row(_FUE, (C.TERTIARY, C.REGIONAL), CORE, _DEPOT_TANK, kind=LOG, role=B,
          rule="rule 2", grade=S, us=True,
          source="lane_fuel fuel→healthcare: S1, S2 (NFPA 110 as reported); ruling R2, "
          "review F9"),
    *_row(_FUE, (C.CLINIC,), OPTIONAL, (_Opt(C.DEPOT),), kind=LOG, role=B, rule="rule 2",
          grade=J, source="lane_fuel fuel→healthcare: S3 (no requirement); review F9"),
    *_row(_FUE, (C.BLOOD_BANK,), CORE, (_Opt(C.DEPOT),), kind=LOG, role=B, rule="rule 2",
          grade=L, source="lane_fuel fuel→healthcare: S4 (WHO 2005 §4.7.2)"),
)  # fmt: skip

DEPENDENCY_TABLE: tuple[DependencyRow, ...] = (
    _POWER_ROWS + _TELECOM_ROWS + _WATER_ROWS + _TRANSPORT_ROWS + _FUEL_ROWS
)
"""Structure v0.5 §4.3a. CHOICE: placeholder (open decision: realism ranges)."""


SUBTYPE_VALUES: Mapping[NodeClass, Mapping[str, tuple[object, ...]]] = {
    C.GENERATION: {"fuel_kind": ("lng", "oil", "coal", "hydro"),
                   "makeup_water": ("municipal", "own_intake")},
    C.IMPORT_TERMINAL: {"product": ("oil", "lng", "coal")},
    C.AIRPORT: {"towered": (True, False), "fuel_receipt": ("pipeline", "truck")},
    C.DATA_CENTRE: {"cooling": ("evaporative", "dry"), "standby_fuel": ("diesel", "none")},
    C.REFINERY: {"crude_receipt": ("marine", "pipeline")},
    C.TANK_FARM: {"pipeline_connected": (True, False), "has_jetty": (True, False),
                  "has_truck_rack": (True, False)},
    C.TERTIARY: {"records_hosted": (True, False), "standby_fuel": ("diesel", "none")},
    C.REGIONAL: {"records_hosted": (True, False), "standby_fuel": ("diesel", "none")},
    C.CLINIC: {"records_hosted": (True, False), "standby_fuel": ("diesel", "none")},
    C.BLOOD_BANK: {"records_hosted": (True, False), "standby_fuel": ("diesel", "none")},
    C.EXCHANGE: {"standby_fuel": ("diesel", "none")},
    C.MAST: {"standby_fuel": ("diesel", "none")},
    C.CABLE_LANDING: {"standby_fuel": ("diesel", "none")},
    C.TREATMENT: {"standby_fuel": ("diesel", "none")},
    C.PUMPING: {"standby_fuel": ("diesel", "none")},
}  # fmt: skip
"""The subtype attributes of §4.3a and their values. Real but unobserved (decision 0007)."""


def coupling_pairs() -> tuple[tuple[Layer, Layer], ...]:
    """Return the 21 modeled couplings, supplier first.

    Returns
    -------
    tuple of (Layer, Layer)
        The couplings §4.3a covers.

    Spec: structure v0.5 §4.3 and §4.3a.
    """
    return DEFAULT_COUPLINGS


def rows_for(supplier: Layer, consumer_class: NodeClass) -> tuple[DependencyRow, ...]:
    """Return every row for one supplier layer and one consumer class.

    Parameters
    ----------
    supplier : Layer
        The supplier layer.
    consumer_class : NodeClass
        The consumer node class.

    Returns
    -------
    tuple of DependencyRow
        The rows, in table order.

    Spec: structure v0.5 §4.3a.
    """
    return tuple(
        row
        for row in DEPENDENCY_TABLE
        if row.supplier_layer == supplier and row.consumer_class == consumer_class
    )


def resolve_row(
    supplier: Layer, consumer_class: NodeClass, subtype: Mapping[str, object]
) -> DependencyRow:
    """Return the one row that applies to a consumer with these subtype attributes.

    Parameters
    ----------
    supplier : Layer
        The supplier layer.
    consumer_class : NodeClass
        The consumer node class.
    subtype : Mapping[str, object]
        The consumer's subtype attributes.

    Returns
    -------
    DependencyRow
        The matching row.

    Raises
    ------
    LookupError
        If no row, or more than one, matches: the table would then be incomplete or
        ambiguous for this consumer.

    Spec: structure v0.5 §4.3a; Work Order 4, A2.
    """
    matching = [row for row in rows_for(supplier, consumer_class) if row.condition.matches(subtype)]
    if len(matching) != 1:
        raise LookupError(
            f"{supplier} → {consumer_class} with {dict(subtype)} matches {len(matching)} rows"
        )
    return matching[0]


def consumer_classes(consumer: Layer) -> tuple[NodeClass, ...]:
    """Return the node classes of a consumer layer.

    Parameters
    ----------
    consumer : Layer
        The consumer layer.

    Returns
    -------
    tuple of NodeClass
        Its classes.

    Spec: structure v0.4 §4.2.
    """
    return LAYER_NODE_CLASSES[consumer]
