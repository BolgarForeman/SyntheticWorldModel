"""The dependency table: which node classes depend on which supplier layer, on what, and how.

This is structure v0.6 §4.3a as one immutable table, read from the modeling rules registry
(``dependencies.table.*``; Work Order 5, A2). It is the authority for which nodes depend on
which. Rows are neither added, dropped nor retyped here; a row that looks wrong is raised with
the design side. Every row cites its evidence in
``docs/design/evidence/Dependency_Table_Evidence_v0_1.md``.
"""

from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from swm.recipe.schema import DEFAULT_COUPLINGS, LAYER_NODE_CLASSES, Layer, NodeClass
from swm.rules.registry import RULES, Registry, Rule

TABLE_PREFIX = "dependencies.table."
"""Registry ids of the table's rows start with this."""


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
    """What an edge does: primary supply, or resupply of a backup generator's fuel (rule 2).

    A buffer-resupply row applies only where there is a generator to refuel. A consumer whose
    ``standby_fuel`` is ``none`` gets no buffer-resupply edge; the couplings stage records the
    absence with a note, not as an error (decision 0008, answer 3).
    """

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
    Layer(layer): commodity for layer, commodity in RULES.value("dependencies.commodities").items()
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


def _row(rule: Rule, commodities: Mapping[Layer, str]) -> DependencyRow:
    """Build one table row from its registry entry."""
    value: dict[str, Any] = rule.value
    condition = value["condition"]
    return DependencyRow(
        supplier_layer=Layer(value["supplier_layer"]),
        consumer_class=NodeClass(value["consumer_class"]),
        condition=Condition(
            all_of=tuple((name, tuple(values)) for name, values in condition["all_of"]),
            any_of=tuple((name, tuple(values)) for name, values in condition["any_of"]),
        ),
        dependency=Dependency(value["dependency"]),
        dependency_type=None
        if value["dependency_type"] is None
        else DependencyType(value["dependency_type"]),
        role=None if value["role"] is None else Role(value["role"]),
        commodity=None
        if value["dependency"] == Dependency.NONE
        else commodities[Layer(value["supplier_layer"])],
        suppliers=tuple(
            SupplierOption(
                node_class=NodeClass(option["node_class"]),
                product=option["product"],
                when=None if option["when"] is None else SupplierWhen(option["when"]),
            )
            for option in value["suppliers"]
        ),
        large_load_supplier=None
        if value["large_load_supplier"] is None
        else NodeClass(value["large_load_supplier"]),
        rule=value["rule"],
        grade=None if rule.grade is None else Grade(rule.grade.value),
        us=rule.jurisdiction is not None and rule.jurisdiction.value == "US",
        source=rule.sources[0].citation,
    )


_TABLES: dict[tuple[str, str], tuple[DependencyRow, ...]] = {}


def dependency_table(rules: Registry = RULES) -> tuple[DependencyRow, ...]:
    """Return the dependency table a registry holds, built once per registry and overrides.

    Parameters
    ----------
    rules : Registry
        The modeling rules in force, with any recipe overrides.

    Returns
    -------
    tuple of DependencyRow
        Structure v0.6 §4.3a, in registry order.

    Spec: structure v0.6 §4.3a; Work Order 5, A2 and A3.
    """
    key = (rules.sha256, rules.overrides_key)
    if key not in _TABLES:
        commodities = {
            Layer(layer): commodity
            for layer, commodity in rules.value("dependencies.commodities").items()
        }
        _TABLES[key] = tuple(
            _row(rule, commodities) for rule in rules.rules if rule.id.startswith(TABLE_PREFIX)
        )
    return _TABLES[key]


DEPENDENCY_TABLE = dependency_table()
"""The shipped §4.3a table, in registry order. Placeholder (open decision: realism ranges)."""


SUBTYPE_VALUES: Mapping[NodeClass, Mapping[str, tuple[object, ...]]] = {
    NodeClass(node_class): {name: tuple(values) for name, values in attributes.items()}
    for node_class, attributes in RULES.value("dependencies.subtype_attributes").items()
}
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


def rows_for(
    supplier: Layer, consumer_class: NodeClass, rules: Registry = RULES
) -> tuple[DependencyRow, ...]:
    """Return every row for one supplier layer and one consumer class.

    Parameters
    ----------
    supplier : Layer
        The supplier layer.
    consumer_class : NodeClass
        The consumer node class.
    rules : Registry
        The modeling rules in force.

    Returns
    -------
    tuple of DependencyRow
        The rows, in table order.

    Spec: structure v0.5 §4.3a.
    """
    return tuple(
        row
        for row in dependency_table(rules)
        if row.supplier_layer == supplier and row.consumer_class == consumer_class
    )


def resolve_row(
    supplier: Layer,
    consumer_class: NodeClass,
    subtype: Mapping[str, object],
    rules: Registry = RULES,
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
    rules : Registry
        The modeling rules in force.

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
    rows = rows_for(supplier, consumer_class, rules)
    matching = [row for row in rows if row.condition.matches(subtype)]
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
