"""One-node worlds for the degradation-profile tests (Work Order 7, F2).

Each test isolates one node: every commodity it needs comes from its own source node, which the
storm can damage at hour 0, and nothing repairs it. The node's failure modes, tolerance and
stocks are set from the registry as the generator sets them, so a test checks the registry and
the engine together against the profile.
"""

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field, replace
from typing import Any

from swm.dynamics.engine import simulate
from swm.dynamics.records import Run, RunRequest
from swm.dynamics.world import (
    Damage,
    EngineDependency,
    EngineEdge,
    EngineNode,
    EngineWorld,
    FacilityRepair,
    Generator,
    IntraLink,
    Resupply,
    Stock,
    Tolerance,
    own_layer_mode,
    settings_from,
)
from swm.recipe.dependencies import resolve_row
from swm.recipe.schema import Layer, NodeClass
from swm.rules.registry import load_registry

RULES = load_registry()
TARGET = "NODE"


def supplier_id(layer: Layer) -> str:
    """The id of the source node that supplies a commodity in a one-node world."""
    return f"SUP-{layer.value}"


def mode_for(
    node_class: NodeClass,
    supplier: Layer,
    subtype: Mapping[str, object],
    has_generator: bool = False,
) -> tuple[str, float | None]:
    """The failure mode and floor the buffers stage would give this node and commodity."""
    row = resolve_row(supplier, node_class, subtype, RULES)
    kind = row.dependency_type.value if row.dependency_type else "physical_flow"
    mode = str(RULES.value("failure_modes.defaults")[kind])
    for departure in RULES.value("failure_modes.class_departures"):
        if departure["node_class"] != node_class:
            continue
        if departure["supplier"] is not None and departure["supplier"] != supplier.value:
            continue
        when = departure["when"]
        if when == "has_generator" and not has_generator:
            continue
        if when == "towered" and subtype.get("towered") is not True:
            continue
        mode = str(departure["mode"])
    floor = RULES.number("reserves.hospital.essential_load_fraction")
    return mode, floor if mode == "step_to_floor" else None


def tolerance_of(rule_id: str, kappa: float) -> Tolerance:
    """A tolerance row from the registry, deepened by the public share (§4.4a)."""
    value = RULES.value(rule_id)
    d = float(value["d"])
    ramp = value.get("ramp_to_h")
    return Tolerance(rule_id, float(value["t_h"]), 1.0 - kappa * (1.0 - d),
                     None if ramp is None else float(ramp))  # fmt: skip


@dataclass
class OneNode:
    """Builds a one-node world: the target, its suppliers, stocks and backup."""

    node_class: NodeClass
    layer: Layer
    subtype: dict[str, object] = field(default_factory=dict)
    end_use: bool = True
    dependencies: list[EngineDependency] = field(default_factory=list)
    stocks: list[Stock] = field(default_factory=list)
    generators: list[Generator] = field(default_factory=list)
    resupply: list[Resupply] = field(default_factory=list)
    links: list[IntraLink] = field(default_factory=list)
    nodes: list[EngineNode] = field(default_factory=list)
    repairs: list[FacilityRepair] = field(default_factory=list)
    own_upstream: list[str] = field(default_factory=list)

    def needs(
        self,
        supplier: Layer,
        kappa: float = 1.0,
        form: str = "linear",
        tolerance: str | None = None,
        feeds: int = 1,
    ) -> "OneNode":
        """Add a dependency on a commodity, served by one source (or ``feeds`` sources)."""
        has_generator = bool(self.generators)
        mode, floor = mode_for(self.node_class, supplier, self.subtype, has_generator)
        edges = []
        for index in range(feeds):
            source = supplier_id(supplier) + ("" if index == 0 else f"-{index}")
            self._source(source, supplier)
            edges.append(EngineEdge(f"E-{source}", source, kappa, form, None))
        groups = tuple((edge,) for edge in edges)
        row = None if tolerance is None else tolerance_of(tolerance, kappa)
        self.dependencies.append(
            EngineDependency(f"D-{supplier.value}", TARGET, supplier, groups, mode, floor, row)
        )
        return self

    def fed_by_own_layer(self, sources: int = 1, line: bool = True) -> "OneNode":
        """Give the node its own layer's commodity over links from upstream sources."""
        for index in range(sources):
            source = f"UP-{index}"
            self._source(source, self.layer)
            self.links.append(IntraLink(f"L-{index}", source, TARGET, line))
            self.own_upstream.append(source)
        return self

    def stock(self, kind: str, covers: Layer, hours: float, rule_id: str, refill: str = "none",
              draw_per_h: float = 10.0, generator: bool = False) -> "OneNode":  # fmt: skip
        """Add a stock of so many hours at its draw."""
        self.stocks.append(Stock(f"{TARGET}:{kind}", TARGET, kind, covers, hours * draw_per_h,
                                 draw_per_h, refill, rule_id, generator))  # fmt: skip
        return self

    def generator(self, hours: float, rule_id: str, fails_to_start: bool = False,
                  run_hours: float = 1.0e6) -> "OneNode":  # fmt: skip
        """Add a diesel standby set with so many hours of fuel (it must precede ``needs``)."""
        self.generators.append(Generator(TARGET, fails_to_start, run_hours))
        return self.stock("generator_fuel", Layer.POWER, hours, rule_id, "delivery",
                          generator=True)  # fmt: skip

    def deliveries_from(self, depot: str = "DEPOT") -> "OneNode":
        """Resupply the generator tank from a depot, 24 h of fuel per delivery (D5)."""
        self._source(depot, Layer.FUEL)
        tank = next(s for s in self.stocks if s.generator)
        delivery = RULES.number("reserves.fuel_resupply.delivery_h") * tank.draw_per_h
        self.resupply.append(Resupply("R-1", depot, TARGET, tank.stock_id, delivery, 1.0,
                                      "threshold"))  # fmt: skip
        return self

    def _source(self, node_id: str, layer: Layer) -> None:
        if all(n.node_id != node_id for n in self.nodes):
            self.nodes.append(EngineNode(node_id, layer, NodeClass.GENERATION, (0.0, 0.0), True,
                                         None, None))  # fmt: skip

    def world(self, **settings: Any) -> EngineWorld:
        """Return the one-node world; ``settings`` override the registry's engine settings."""
        target = EngineNode(
            TARGET, self.layer, self.node_class, (0.0, 0.0), not self.own_upstream,
            own_layer_mode(self.node_class, self.layer, RULES) if self.own_upstream else None,
            1.0 if self.end_use else None,
        )  # fmt: skip
        return EngineWorld(
            nodes=(target, *sorted(self.nodes, key=lambda n: n.node_id)),
            dependencies=tuple(self.dependencies),
            links=tuple(self.links),
            stocks=tuple(self.stocks),
            generators=tuple(self.generators),
            resupply=tuple(self.resupply),
            repairs=tuple(self.repairs),
            unrepairable=(),
            emergencies=(),
            units={},
            crews=(),
            feeds_to_end_use={},
            towered=frozenset(),
            settings=replace(settings_from(RULES), **settings),
        )


def cut(world: EngineWorld, damaged: Iterable[str], relaxed: Iterable[str] = (),
        horizon_h: float = 72.0) -> Run:  # fmt: skip
    """Damage the named suppliers at hour 0 and run the world for the horizon."""
    request = RunRequest(Damage(tuple(damaged), (), ()), horizon_h=horizon_h,
                         relaxed=frozenset(relaxed))  # fmt: skip
    return simulate(world, request)


def hours_at(run: Run, value: float, node_id: str = TARGET) -> list[float]:
    """The hours at which the node's state equals a value."""
    return [t for t, s in zip(run.times, run.state(node_id), strict=True) if s == value]


def first_change(run: Run, node_id: str = TARGET) -> float | None:
    """The first hour the node's state differs from 1."""
    for t, s in zip(run.times, run.state(node_id), strict=True):
        if s != 1.0:
            return t
    return None
