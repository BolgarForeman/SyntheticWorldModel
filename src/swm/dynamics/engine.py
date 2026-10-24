"""The engine: plays one scenario out over time, step by step (structure v0.9 §4.5).

A node's state is its condition x its supply level, and its supply level is the lowest of its
responses across the commodities it needs (D2):
- **received share R** of a commodity: as the strength stage reads a dependency, feed groups
  summed and the edges within a group all needed, each edge delivering κ x g_δ(supplier
  state), linear for physical flow and service and the threshold θ for logistic and control
  (D3). A power feed on a failed line delivers nothing (D4). Telecom is served or not, so a
  telecom edge delivers g_δ alone; κ deepens the tolerance instead (§4.4a).
- **own layer:** links inside power, water, fuel and telecom carry that layer's commodity from
  the first stage of its signature down (D4). Each pass recomputes it from nothing, so a ring of
  links can never keep itself supplied.
- **stocks** cover their own commodity's shortfall while they last (D5); a hospital on
  generator steps to its floor.
- **telecom tolerance** acts first where a class has a row: full function for T hours, then
  d_eff.
- **response:** throttle (R), trip (1 while R ≥ the trip point, else 0) or step to a floor.

Each 15-minute step: apply what completes, settle the cascade (recompute until nothing changes,
up to the cap; a step that hits it is recorded), record, then advance the stocks, clocks,
deliveries and crews by one step. Only +, -, x, / and sqrt; states are compared exactly; nodes
are visited in id order.

Spec: structure v0.9 §4.5; Work Order 7, D1-D8; rulings D2-D7 and D11.
"""

import math
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field

from swm.dynamics.records import (
    AddReserve,
    AddStock,
    Completion,
    CrewEntry,
    Delivery,
    Protect,
    Run,
    RunRequest,
)
from swm.dynamics.travel import Legs, Site
from swm.dynamics.world import (
    SUBSTATIONS,
    Damage,
    EngineDependency,
    EngineWorld,
    FacilityRepair,
    QuickPath,
    Settings,
    Stock,
)
from swm.recipe.schema import Layer, NodeClass

FULL = 1.0
ADDED_STOCK = "added reserve"
"""The kind (and rule label) of a stock an answer key's reserve creates (Work Order 10, E2)."""
HOURS_OF_FULL_DRAW = 1.0
"""An added stock is counted in hours of the node's full draw, so it draws one per hour."""


def simulate(world: EngineWorld, request: RunRequest) -> Run:
    """Play one scenario out over its horizon.

    Parameters
    ----------
    world : EngineWorld
        The world the engine plays out.
    request : RunRequest
        The scenario's damage, the actions, the horizon, the relaxed limits and the removed
        dependencies.

    Returns
    -------
    Run
        Every node's state and every stock's level at every step, the crews' jobs, the
        completions, the deliveries, the passes each step took and the hours out.

    Raises
    ------
    ValueError
        If an action or a removed dependency names nothing in the world.

    Spec: structure v0.9 §4.5; Work Order 7, D1.
    """
    return _Engine(world, request).run()


@dataclass
class _Job:
    """A crew job: a node's repair, a line's repair, or a manual switching trip (D4, D5)."""

    job_id: str
    kind: str
    element_id: str
    priority: tuple[int, float]
    sites: tuple[Site, ...]
    work_h: tuple[float, ...]
    lead_h: float
    parts_ready_h: float
    crew_id: str | None = None
    along_km: tuple[float, ...] = ()
    """A line job's failure points, km along the line: the crew walks between them."""


@dataclass
class _Crew:
    crew_id: str
    site: Site
    free_at: float
    log: list[CrewEntry] = field(default_factory=list)


class _Engine:
    def __init__(self, world: EngineWorld, request: RunRequest) -> None:
        self.world = world
        self.request = request
        self.settings = world.settings
        self.relaxed = frozenset(request.relaxed)
        self.horizon = (
            request.horizon_h if request.horizon_h is not None else world.settings.horizon_h
        )
        self.step = world.settings.step_h
        self.nodes = {n.node_id: n for n in world.nodes}
        self.dependencies = _without(world.dependencies, request.removed)
        self.by_consumer: dict[str, list[EngineDependency]] = {}
        for dependency in self.dependencies:
            self.by_consumer.setdefault(dependency.consumer_id, []).append(dependency)
        self.in_links: dict[str, list[tuple[str, str | None]]] = {}
        for link in world.links:
            line = link.link_id if link.line else None
            self.in_links.setdefault(link.downstream_id, []).append((link.upstream_id, line))
        self.stocks = {s.stock_id: s for s in world.stocks}
        self.capacity = {s.stock_id: s.capacity for s in world.stocks}
        self._actions()
        self.level = dict(self.capacity)
        self.by_cover: dict[tuple[str, Layer], list[Stock]] = {}
        for stock in sorted(self.stocks.values(), key=lambda s: (s.generator, s.stock_id)):
            self.by_cover.setdefault((stock.node_id, stock.covers), []).append(stock)
        self.generators = {g.node_id: g for g in world.generators}
        self.run_h: dict[str, float] = {}
        self.stopped: set[str] = set()
        protected = {a.element_id for a in request.actions if isinstance(a, Protect)}
        damage = request.damage
        self.condition = {n: FULL for n in self.nodes}
        for node_id in damage.nodes:
            if node_id not in protected:
                self.condition[node_id] = 0.0
        self.down_lines = {line for line in damage.lines if line not in protected}
        self.points = [p for p in damage.failure_points if p.line_id in self.down_lines]
        self.x = {n: FULL for n in self.nodes}
        self.elapsed: dict[str, float] = {}
        self.loss: dict[str, float | None] = {r.edge_id: None for r in world.resupply}
        self.due: dict[str, float | None] = {r.edge_id: None for r in world.resupply}
        self.deenergized: set[str] = set()
        self.switching: dict[str, _Job] = {}
        self.jobs: dict[str, _Job] = {}
        self.pending: list[tuple[float, str]] = []
        self.completed_priority: tuple[int, float] | None = None
        self.crews = [_Crew(c.crew_id, Site(c.site), 0.0) for c in world.crews]
        self.completions: list[Completion] = []
        self.deliveries: list[Delivery] = []
        self.plan = {crew: list(jobs) for crew, jobs in request.plan or ()}
        _check_ruled_dynamics(self.settings)

    # --- Set-up ---------------------------------------------------------------------------

    def _actions(self) -> None:
        for action in self.request.actions:
            if isinstance(action, AddStock):
                self._add_stock(action)
            elif isinstance(action, AddReserve):
                if action.stock_id not in self.stocks:
                    raise ValueError(f"add reserve: no stock {action.stock_id}")
                stock = self.stocks[action.stock_id]
                self.capacity[action.stock_id] += action.hours * stock.draw_per_h
            elif (
                action.element_id not in self.nodes
                and not any(
                    p.line_id == action.element_id for p in self.request.damage.failure_points
                )
                and action.element_id not in self.request.damage.lines
            ):
                raise ValueError(f"protect: no element {action.element_id}")

    def _add_stock(self, action: AddStock) -> None:
        """Create a new stock, in hours of full draw, where the node has none (WO 10, E2)."""
        if action.node_id not in self.nodes:
            raise ValueError(f"add stock: no node {action.node_id}")
        if any(
            s.node_id == action.node_id and s.covers == action.covers for s in self.stocks.values()
        ):
            raise ValueError(f"add stock: {action.node_id} already holds a {action.covers} stock")
        stock_id = f"{action.node_id}:{ADDED_STOCK}:{action.covers}"
        self.stocks[stock_id] = Stock(
            stock_id, action.node_id, ADDED_STOCK, action.covers, action.hours,
            HOURS_OF_FULL_DRAW, "none", ADDED_STOCK,
        )  # fmt: skip
        self.capacity[stock_id] = action.hours

    # --- The run ----------------------------------------------------------------------------

    def run(self) -> Run:
        steps = int(self.horizon / self.step + 0.5)
        self._open_jobs()
        self._check_plan()
        self._dispatch_units()
        times, states, levels, passes, capped = [], [], [], [], []
        crew_at: list[tuple[tuple[str, str], ...]] = []
        for k in range(steps + 1):
            t = k * self.step
            self._complete(t)
            used = self._settle_with_switching(t)
            # A delivery needs the depot's settled state; fuel that arrives refills the tank
            # in this step, so the cascade settles again.
            if self._deliver(t):
                used = max(used, self._settle_with_switching(t))
            passes.append(used)
            if used > self.settings.settling_cap:
                capped.append(t)
            times.append(t)
            states.append(tuple(self.x[n] for n in self.nodes))
            levels.append(tuple(self._level(s) for s in self.stocks))
            if k == steps:
                crew_at.append(self._crew_positions(t))
                break
            self._assign(t)
            crew_at.append(self._crew_positions(t))
            self._advance(t)
        return Run.build(
            request=self.request,
            horizon_h=self.horizon,
            step_h=self.step,
            node_ids=tuple(self.nodes),
            stock_ids=tuple(self.stocks),
            times=tuple(times),
            states=tuple(states),
            levels=tuple(levels),
            passes=tuple(min(p, self.settings.settling_cap) for p in passes),
            capped=tuple(capped),
            crews=tuple((c.crew_id, tuple(c.log)) for c in self.crews),
            crew_positions=tuple(crew_at),
            completions=tuple(self.completions),
            deliveries=tuple(self.deliveries),
            end_use={n.node_id: n.end_use_weight for n in self.world.nodes},
        )

    def _level(self, stock_id: str) -> float:
        return math.inf if self._unlimited(self.stocks[stock_id]) else self.level[stock_id]

    def _unlimited(self, stock: Stock) -> bool:
        return stock.rule_id in self.relaxed

    # --- Settling (D6) ------------------------------------------------------------------------

    def _settle_with_switching(self, t: float) -> int:
        """Settle; then switch substations by remote or open manual trips, and settle again."""
        total = 0
        for _ in range(len(self.nodes) + 1):
            total += self._settle()
            if not self._switching(t):
                return total
        return total

    def _settle(self) -> int:
        cap = self.settings.settling_cap
        for count in range(1, cap + 1):
            new = self._states(self.x)
            if new == self.x:
                return count
            self.x = new
        return cap + 1

    def _states(self, x: Mapping[str, float]) -> dict[str, float]:
        other = {n: self._other(n, x) for n in self.nodes}
        own = self._own_levels(x, other)
        return {
            n: self.condition[n] * min(other[n], self._own_response(n, own.get(n)))
            for n in self.nodes
        }

    def _other(self, node_id: str, x: Mapping[str, float]) -> float:
        responses = [self._response(d, x) for d in self.by_consumer.get(node_id, ())]
        return min(responses, default=FULL)

    def _own_levels(self, x: Mapping[str, float], other: Mapping[str, float]) -> dict[str, float]:
        """Each non-source node's received share of its own layer, from the sources down."""
        level = {n: 0.0 for n, node in self.nodes.items() if not node.source}
        for _ in range(len(self.nodes) + 1):
            out = {
                n: self.condition[n] * min(other[n], self._own_response(n, level.get(n)))
                for n in self.nodes
            }
            new = {n: self._delivered(n, out) for n in level}
            if new == level:
                break
            level = new
        return level

    def _delivered(self, node_id: str, out: Mapping[str, float]) -> float:
        best = 0.0
        for upstream, line in self.in_links.get(node_id, ()):
            if line is not None and line in self.down_lines:
                continue
            best = max(best, out[upstream])
        return min(FULL, best)

    def _own_response(self, node_id: str, received: float | None) -> float:
        node = self.nodes[node_id]
        if received is None or node.own_mode is None:
            return FULL
        if node_id in self.deenergized:
            received = 0.0
        return self._respond(node_id, node.layer, received, node.own_mode, None)

    def _received(self, dependency: EngineDependency, x: Mapping[str, float]) -> float:
        total = 0.0
        telecom = dependency.supplier_layer == Layer.TELECOM
        for group in dependency.groups:
            delivered = []
            for edge in group:
                if edge.line_id is not None and edge.line_id in self.down_lines:
                    delivered.append(0.0)
                    continue
                g = self._transfer(edge.transfer_form, x[edge.supplier_id])
                delivered.append(g if telecom else edge.kappa * g)
            total += min(delivered)
        return min(FULL, total)

    def _transfer(self, form: str, state: float) -> float:
        if form == "linear":
            return state
        if form == "threshold":
            return FULL if state >= self.settings.threshold else 0.0
        raise ValueError(f"the {form} transfer form is not built in Phase 1")

    def _response(self, dependency: EngineDependency, x: Mapping[str, float]) -> float:
        received = self._received(dependency, x)
        tolerance = dependency.tolerance
        if tolerance is not None and received < FULL:
            held = self._tolerance_level(dependency)
            received = received + (FULL - received) * held
        return self._respond(
            dependency.consumer_id,
            dependency.supplier_layer,
            received,
            dependency.mode,
            dependency.floor,
        )

    def _tolerance_level(self, dependency: EngineDependency) -> float:
        """Full function for T hours after telecom is lost, then d_eff (§4.4a)."""
        tolerance = dependency.tolerance
        assert tolerance is not None
        if tolerance.rule_id in self.relaxed:
            return FULL
        elapsed = self.elapsed.get(dependency.dependency_id, 0.0)
        if elapsed < tolerance.t_h:
            return FULL
        ramp = tolerance.ramp_to_h
        if ramp is not None and elapsed < ramp:
            share = (elapsed - tolerance.t_h) / (ramp - tolerance.t_h)
            return FULL - share * (FULL - tolerance.d_eff)
        return tolerance.d_eff

    def _respond(
        self, node_id: str, layer: Layer, received: float, mode: str, floor: float | None
    ) -> float:
        if received >= FULL:
            return FULL
        cover = self._cover(node_id, layer)
        if cover is not None:
            if mode == "step_to_floor" and cover.generator and floor is not None:
                return floor
            return FULL
        if mode == "throttle":
            return received
        if mode == "step_to_floor" and self.settings.floor_after_generator_stops != TRIP:
            raise ValueError(
                "dynamics.floor_after_generator_stops is "
                f"'{self.settings.floor_after_generator_stops}': its alternatives are recorded "
                "but become selectable only in a later phase"
            )
        # A trip, or a step to the floor with no generator to step onto (spec v0.16 §4.5).
        return FULL if received >= self.settings.trip_point else 0.0

    def _cover(self, node_id: str, layer: Layer) -> Stock | None:
        for stock in self.by_cover.get((node_id, layer), ()):
            if stock.generator and not self._generator_runs(node_id):
                continue
            if self._unlimited(stock) or self.level[stock.stock_id] > 0.0:
                return stock
        return None

    def _generator_runs(self, node_id: str) -> bool:
        generator = self.generators.get(node_id)
        if generator is None or generator.fails_to_start:
            return False
        return node_id not in self.stopped

    # --- Manual switching (D5) ------------------------------------------------------------------

    def _switching(self, t: float) -> bool:
        """Mark substations that lose all power in; switch those whose power returns."""
        changed = False
        other = {n: self._other(n, self.x) for n in self.nodes}
        locked, self.deenergized = self.deenergized, set()
        raw = self._own_levels(self.x, other)
        self.deenergized = locked
        for node_id in sorted(self.nodes):
            if self.nodes[node_id].node_class not in SUBSTATIONS or node_id not in raw:
                continue
            if raw[node_id] <= 0.0:
                self.deenergized.add(node_id)
                continue
            if node_id not in self.deenergized:
                continue
            if self._telecom_up(node_id) or self.condition[node_id] < FULL:
                self._clear_mark(node_id)
                changed = True
            elif node_id not in self.switching:
                self._open_switching(node_id, t)
        return changed

    def _telecom_up(self, node_id: str) -> bool:
        for dependency in self.by_consumer.get(node_id, ()):
            if (
                dependency.supplier_layer == Layer.TELECOM
                and self._received(dependency, self.x) < FULL
            ):
                return False
        return True

    def _open_switching(self, node_id: str, t: float) -> None:
        job_id = f"switch:{node_id}:{t:g}"
        on_site = (
            0.0 if "repair.manual_switching_h" in self.relaxed else self.settings.manual_switching_h
        )
        priority = self.completed_priority or self._priority(node_id)
        job = _Job(
            job_id,
            "switching",
            node_id,
            priority,
            (Site(self.nodes[node_id].site),),
            (on_site,),
            0.0,
            t,
        )
        self.switching[node_id] = job
        self.jobs[job_id] = job

    def _clear_mark(self, node_id: str) -> None:
        """Clear a substation's de-energised mark and cancel its trip still waiting for a crew.

        Only an unassigned trip is cancelled: an assigned one is still travelled and worked.
        Either way the trip leaves the index, so a newer trip for the node is never left behind
        in the job list (sheet E1; Work Order 11, A1).
        """
        self.deenergized.discard(node_id)
        job = self.switching.pop(node_id, None)
        if job is not None and job.crew_id is None:
            del self.jobs[job.job_id]

    # --- Jobs and crews (D4) ----------------------------------------------------------------------

    def _open_jobs(self) -> None:
        unrepairable = set(self.world.unrepairable)
        lead = (
            0.0 if "repair.crew_bound_lead_h" in self.relaxed else self.settings.crew_bound_lead_h
        )
        parts_relaxed = "repair.parts_lead_time" in self.relaxed
        for node_id in sorted(n for n, c in self.condition.items() if c < FULL):
            repair = facility_repair(self.world, self.request.damage, node_id)
            if node_id in unrepairable or repair is None:
                continue
            parts = 0.0 if parts_relaxed else repair.parts_lead_h
            self.jobs[f"repair:{node_id}"] = _Job(
                f"repair:{node_id}",
                "facility",
                node_id,
                self._priority(node_id),
                (Site(self.nodes[node_id].site),),
                (repair.crew_work_h,),
                lead,
                parts,
            )
        self._open_quick_paths(lead)
        for line_id in sorted(self.down_lines):
            points = sorted((p for p in self.points if p.line_id == line_id), key=lambda p: p.km)
            # A crew works a line's failure points in order along the line (ruled, decision
            # 0014 second addendum).
            self.jobs[f"repair:{line_id}"] = _Job(
                f"repair:{line_id}",
                "line",
                line_id,
                self._priority(line_id),
                tuple(Site(p.site, on_line=True) for p in points),
                tuple(p.crew_work_h for p in points),
                lead,
                0.0,
                along_km=tuple(p.km for p in points),
            )

    def _open_quick_paths(self, lead: float) -> None:
        """Open a quick-path job, at hour 0, for each heavily damaged node whose class has one.

        It is a crew job, worked in the default crew order with the node's own key: travel, the
        assessment, then the quick-path work; on completion the node gives its restored share.
        The node's rebuild job stays, and once open brings it to full (Work Order 11, B3-B4).
        """
        for path in quick_paths(self.world, self.request.damage):
            if self.condition[path.node_id] >= FULL:
                continue
            job_id = f"{QUICK}:{path.node_id}"
            self.jobs[job_id] = _Job(
                job_id, QUICK, path.node_id, self._priority(path.node_id),
                (Site(self.nodes[path.node_id].site),), (path.crew_work_h,), lead, 0.0,
            )  # fmt: skip

    def _quick_share(self, node_id: str) -> float:
        return next(p.restored_share for p in self.world.quick_paths if p.node_id == node_id)

    def _priority(self, element_id: str) -> tuple[int, float]:
        return crew_order(self.world, element_id)

    def _dispatch_units(self) -> None:
        """Send each mobile unit to an eligible damaged node, in the crew order (§4.4a)."""
        available = dict(self.world.units)
        eligible = sorted(
            (e for e in self.world.emergencies if self.condition.get(e.node_id, FULL) < FULL),
            key=lambda e: (self._priority(e.node_id), e.node_id),
        )
        for emergency in eligible:
            if available.get(emergency.unit_kind, 0) <= 0:
                continue
            available[emergency.unit_kind] -= 1
            self.pending.append((emergency.arrival_h, f"unit:{emergency.node_id}"))
        self.pending.sort()

    def _check_plan(self) -> None:
        """Check that a plan names distinct crews and every repair job once (Work Order 10, C1)."""
        if self.request.plan is None:
            return
        crews = {c.crew_id for c in self.crews}
        named = [crew for crew, _ in self.request.plan]
        if len(set(named)) != len(named) or not set(named) <= crews:
            raise ValueError(f"crew plan: crews {named} are not distinct crews of the world")
        planned = sorted(e for jobs in self.plan.values() for e in jobs)
        repairs = sorted(plan_token(j) for j in self.jobs.values() if j.kind != "switching")
        if planned != repairs:
            raise ValueError(f"crew plan: plans {planned}, but the repair jobs are {repairs}")

    def _assign(self, t: float) -> None:
        """Give each crew free before the step ends the best open job, from where it stands."""
        if "crews.pilot" in self.relaxed:
            self._assign_unlimited(t)
            return
        if self.request.plan is not None:
            self._assign_planned(t)
            return
        end = t + self.step
        while True:
            free = [c for c in self.crews if c.free_at < end]
            open_jobs = [j for j in self.jobs.values() if j.crew_id is None and _open(j, t)]
            if not free or not open_jobs:
                return
            crew = min(free, key=lambda c: (c.free_at, c.crew_id))
            start = max(crew.free_at, t)
            job = min(
                open_jobs, key=lambda j: (j.priority, self._hours(crew.site, j.sites[0]), j.job_id)
            )
            self._work(crew, job, start)

    def _assign_planned(self, t: float) -> None:
        """Give each crew free before the step ends its next planned job (Work Order 10, C2).

        A switching trip is never planned. A free crew weighs any open one against its next
        planned job by the default rule's key, so a trip goes to crews as the default order
        sends it.
        """
        end = t + self.step
        waiting = {c.crew_id for c in self.crews}
        while True:
            free = [c for c in self.crews if c.free_at < end and c.crew_id in waiting]
            if not free:
                return
            crew = min(free, key=lambda c: (c.free_at, c.crew_id))
            # CHOICE: a free crew chooses between its next planned job and the open switching
            # trips by the default rule's key (priority, hours from where it stands, job id).
            options = [j for j in self.jobs.values() if j.crew_id is None and j.kind == "switching"]
            planned = self.plan.get(crew.crew_id, [])
            # CHOICE: a crew whose next planned job is not yet open takes only open switching
            # trips until it opens (WO-11 answers, 2).
            if planned and _open(self.jobs[plan_job_id(planned[0])], t):
                options.append(self.jobs[plan_job_id(planned[0])])
            if not options:
                waiting.discard(crew.crew_id)
                continue
            job = min(
                options, key=lambda j: (j.priority, self._hours(crew.site, j.sites[0]), j.job_id)
            )
            if job.kind != "switching":
                planned.pop(0)
            self._work(crew, job, max(crew.free_at, t))

    def _assign_unlimited(self, t: float) -> None:
        """Every job gets its own crew at once, from the nearest crew start (D8)."""
        for job in [j for j in self.jobs.values() if j.crew_id is None and _open(j, t)]:
            start = min(
                self.world.crews, key=lambda c: (self._hours(Site(c.site), job.sites[0]), c.crew_id)
            )
            crew = _Crew(f"{start.crew_id}+{job.job_id}", Site(start.site), t)
            self.crews.append(crew)
            self._work(crew, job, t)

    def _work(self, crew: _Crew, job: _Job, start: float) -> None:
        """Lay out a job's travel, crew-bound lead and work; queue its end."""
        job.crew_id = crew.crew_id
        clock = start
        site = crew.site
        for index, (target, work_h) in enumerate(zip(job.sites, job.work_h, strict=True)):
            trip = (
                self._along_line_hours(job, index) if index > 0 and job.along_km
                else self._hours(site, target)
            )  # fmt: skip
            crew.log.append(CrewEntry(crew.crew_id, job.job_id, "travel", clock, clock + trip))
            clock += trip
            if index == 0 and job.lead_h > 0.0:
                crew.log.append(
                    CrewEntry(crew.crew_id, job.job_id, "assess", clock, clock + job.lead_h)
                )
                clock += job.lead_h
            activity = "switch" if job.kind == "switching" else "repair"
            crew.log.append(CrewEntry(crew.crew_id, job.job_id, activity, clock, clock + work_h))
            clock += work_h
            site = target
        crew.site = site
        crew.free_at = clock
        self.pending.append((clock, job.job_id))
        self.pending.sort()

    def _along_line_hours(self, job: _Job, index: int) -> float:
        """Walk from one failure point of a line to the next, along the line (spec v0.14 §4.5)."""
        if self.settings.line_point_travel != ALONG_THE_LINE:
            raise ValueError(
                f"dynamics.line_point_travel is '{self.settings.line_point_travel}': its "
                "alternatives are recorded but become selectable only in a later phase"
            )
        if "crews.offroad_speed_kmh" in self.relaxed:
            return 0.0
        walk_km = abs(job.along_km[index] - job.along_km[index - 1])
        return walk_km / self.settings.offroad_kmh

    def _hours(self, start: Site, end: Site) -> float:
        return self._trip_hours(self.world.legs(start, end))

    def _trip_hours(self, legs: Legs) -> float:
        return trip_hours(legs, self.settings, self.relaxed)

    def _crew_positions(self, t: float) -> tuple[tuple[str, str], ...]:
        positions = []
        for crew in self.crews:
            doing = next((e for e in crew.log if e.start_h <= t < e.end_h), None)
            positions.append(
                (crew.crew_id, "idle" if doing is None else f"{doing.activity} {doing.job_id}")
            )
        return tuple(positions)

    def _complete(self, t: float) -> None:
        """Apply every job and unit that finished by this step (effects land on the step)."""
        self.completed_priority = None
        while self.pending and self.pending[0][0] <= t + 1e-12:
            _, key = self.pending.pop(0)
            if key.startswith("unit:"):
                node_id = key[len("unit:") :]
                share = next(
                    e.restored_share for e in self.world.emergencies if e.node_id == node_id
                )
                if self.condition[node_id] < share:
                    self.condition[node_id] = share
                    self.completions.append(Completion(node_id, "emergency", t))
                continue
            job = self.jobs.pop(key)
            self._finish(job, t)

    def _finish(self, job: _Job, t: float) -> None:
        if job.kind == "line":
            self.down_lines.discard(job.element_id)
        elif job.kind == "facility":
            self.condition[job.element_id] = FULL
            # The crew is at the substation it repaired, so it switches it on site (D5).
            self._clear_mark(job.element_id)
        elif job.kind == QUICK:
            share = self._quick_share(job.element_id)
            if self.condition[job.element_id] < share:
                self.condition[job.element_id] = share
            self._clear_mark(job.element_id)
        else:
            # A finished trip leaves the index only if it is the node's indexed trip; a newer
            # trip there stays until its own mark clears (Work Order 11, A1).
            if self.switching.get(job.element_id) is job:
                del self.switching[job.element_id]
            self._clear_mark(job.element_id)
        first = self.completed_priority is None or job.priority < self.completed_priority
        if job.kind != "switching" and first:
            self.completed_priority = job.priority
        self.completions.append(Completion(job.element_id, job.kind, t))

    # --- Deliveries (D5) ------------------------------------------------------------------------

    def _deliver(self, t: float) -> bool:
        """Make every delivery due by this step whose depot is up; say whether any came."""
        made = False
        for resupply in self.world.resupply:
            due = self.due[resupply.edge_id]
            if due is None or due > t + 1e-12:
                continue
            tank = self.stocks[resupply.stock_id]
            room = self.capacity[tank.stock_id] - self.level[tank.stock_id]
            # A delivery the depot cannot make goes out at the first step the depot is up (roads
            # are not damaged in Phase 1, so a road reaches the consumer); the schedule then
            # runs every interval from that delivery (PR 7b answers, 2).
            if self._transfer(resupply.transfer_form, self.x[resupply.depot_id]) <= 0.0:
                continue
            if room > 0.0:
                amount = (
                    room
                    if "reserves.fuel_resupply.delivery_h" in self.relaxed
                    else min(room, resupply.delivery * resupply.kappa)
                )
                self.level[tank.stock_id] += amount
                self.deliveries.append(Delivery(resupply.edge_id, resupply.consumer_id, t, amount))
                made = True
            full = self.level[tank.stock_id] >= self.capacity[tank.stock_id]
            # Deliveries stop once the tank is full and power is back.
            self.due[resupply.edge_id] = (
                None
                if full and self.loss[resupply.edge_id] is None
                else t + self.settings.delivery_interval_h
            )
        return made

    # --- Advancing one step ---------------------------------------------------------------------

    def _advance(self, t: float) -> None:
        dt = self.step
        drawing: set[str] = set()
        for node_id in self.nodes:
            for layer, received, floor_draw in self._needs(node_id):
                if received < FULL:
                    self._draw(node_id, layer, received, floor_draw, dt, drawing)
        for stock in self.world.stocks:
            if stock.stock_id not in drawing:
                self._refill(stock, dt)
        self._clocks(dt)
        self._losses(t)

    def _needs(self, node_id: str) -> Iterable[tuple[Layer, float, bool]]:
        for dependency in self.by_consumer.get(node_id, ()):
            if dependency.supplier_layer == Layer.TELECOM:
                continue
            received = self._received(dependency, self.x)
            yield dependency.supplier_layer, received, dependency.mode == "step_to_floor"
        node = self.nodes[node_id]
        if node.own_mode is not None:
            other = {n: self._other(n, self.x) for n in self.nodes}
            own = self._own_levels(self.x, other).get(node_id, FULL)
            yield node.layer, own, False

    def _draw(
        self, node_id: str, layer: Layer, received: float, floor_draw: bool, dt: float,
        drawing: set[str],
    ) -> None:  # fmt: skip
        """Draw the shortfall from the node's stocks in order, battery before generator.

        A stock that covers only part of the step's need passes on the rest: the next stock is
        charged the uncovered share at its own draw rate (sheet E2; Work Order 11, A2).
        """
        # CHOICE: the remainder passes as the uncovered share of the step's need, so each stock
        # is charged at its own draw rate (WO-11 answers, 2).
        uncovered = FULL
        for stock in self.by_cover.get((node_id, layer), ()):
            if stock.generator and not self._generator_runs(node_id):
                continue
            share = FULL if (floor_draw and stock.generator) else FULL - received
            need = stock.draw_per_h * share * dt * uncovered
            drawing.add(stock.stock_id)
            if stock.generator:
                self.run_h[node_id] = self.run_h.get(node_id, 0.0) + dt
                if self.run_h[node_id] >= self.generators[node_id].run_hours_to_failure:
                    self.stopped.add(node_id)
            if self._unlimited(stock):
                return
            taken = min(need, self.level[stock.stock_id])
            self.level[stock.stock_id] -= taken
            if taken >= need:
                return
            uncovered *= (need - taken) / need

    def _refill(self, stock: Stock, dt: float) -> None:
        room = self.capacity[stock.stock_id] - self.level[stock.stock_id]
        if room <= 0.0 or not self._supplied(stock.node_id, stock.covers):
            return
        if stock.refill == "battery":
            rate = (
                room / dt
                if "reserves.battery_recharge_h" in self.relaxed
                else self.capacity[stock.stock_id] / self.settings.battery_recharge_h
            )
        elif stock.refill == "main":
            # Water from the main refills a stock at a fraction of the rate it drains (Work
            # Order 8, Part 0); relaxed, at once.
            rate = (
                room / dt
                if "reserves.main_refill_rate_fraction" in self.relaxed
                else self.settings.main_refill_fraction * stock.draw_per_h
            )
        elif stock.refill == "pumps":
            rate = self._spare_pumping(stock)
        else:
            return
        self.level[stock.stock_id] += min(room, rate * dt)

    def _supplied(self, node_id: str, layer: Layer) -> bool:
        for covered, received, _ in self._needs(node_id):
            if covered == layer and received < FULL:
                return False
        return True

    def _spare_pumping(self, stock: Stock) -> float:
        """Return what a storage node's pumps deliver beyond the demand it serves (D5)."""
        if "reserves.pumping.capacity" in self.relaxed:
            return math.inf
        inflow = 0.0
        for upstream, _ in self.in_links.get(stock.node_id, ()):
            capacity = self.world.pump_capacity_m3_per_h.get(upstream)
            if capacity is None:
                continue
            # A pump's capacity is shared pro rata by the demand of the nodes it feeds (§4.5,
            # links inside a layer; PR 7b answers, 2).
            fed = [link.downstream_id for link in self.world.links if link.upstream_id == upstream]
            total = math.fsum(self._demand(node_id) for node_id in fed)
            share = self._demand(stock.node_id) / total if total > 0.0 else FULL / len(fed)
            inflow += self.x[upstream] * capacity * share
        return max(0.0, inflow - stock.draw_per_h)

    def _demand(self, node_id: str) -> float:
        """Return the water a node fed by pumps draws: its storage's downstream draw (m³/h)."""
        return math.fsum(
            s.draw_per_h for s in self.world.stocks if s.node_id == node_id and s.refill == "pumps"
        )

    def _clocks(self, dt: float) -> None:
        for dependency in self.dependencies:
            if dependency.tolerance is None:
                continue
            if self._received(dependency, self.x) < FULL:
                self.elapsed[dependency.dependency_id] = (
                    self.elapsed.get(dependency.dependency_id, 0.0) + dt
                )
            else:
                self.elapsed.pop(dependency.dependency_id, None)

    def _losses(self, t: float) -> None:
        """Start a delivery schedule when a consumer with a tank first loses power (D5)."""
        lead = (
            0.0
            if "reserves.fuel_resupply.lead_time_h" in self.relaxed
            else self.settings.delivery_lead_h
        )
        for resupply in self.world.resupply:
            lost = not self._supplied(resupply.consumer_id, Layer.POWER)
            if lost and self.loss[resupply.edge_id] is None:
                self.loss[resupply.edge_id] = t
                if self.due[resupply.edge_id] is None:
                    self.due[resupply.edge_id] = t + lead
            elif not lost:
                self.loss[resupply.edge_id] = None


def crew_order(world: EngineWorld, element_id: str) -> tuple[int, float]:
    """Return an element's key in the default crew order (D6): tier, then -Lifeline weight.

    Tier 0: towered lines and transmission substations. Tier 1: distribution substations and
    power feeds to end-use nodes, the highest Lifeline weight first; a distribution substation
    ranks by ``substation_weight``. Tier 2: everything else.

    Parameters
    ----------
    world : EngineWorld
        The world played out.
    element_id : str
        A node or line id.

    Returns
    -------
    tuple of (int, float)
        The tier and the negated weight; a smaller key is served first.

    Spec: structure v0.13 §4.5 (repair and crews); ruling D6; WO-09g answers, 1.
    """
    if element_id in world.towered:
        return (0, 0.0)
    node = next((n for n in world.nodes if n.node_id == element_id), None)
    if node is not None and node.node_class == NodeClass.TRANSMISSION_SUBSTATION:
        return (0, 0.0)
    if node is not None and node.node_class == NodeClass.DISTRIBUTION_SUBSTATION:
        return (1, -substation_weight(world, element_id))
    if element_id in world.feeds_to_end_use:
        return (1, -world.feeds_to_end_use[element_id])
    return (2, 0.0)


def substation_weight(world: EngineWorld, node_id: str) -> float:
    """Return the weight a distribution substation ranks by in crew-order group 2.

    The highest Lifeline weight among the end uses it supplies, its own included: it supplies an
    end use through an electricity coupling the engine plays, switched on or hidden.

    Parameters
    ----------
    world : EngineWorld
        The world played out.
    node_id : str
        A distribution substation.

    Returns
    -------
    float
        The weight; 0 if neither it nor anything it supplies is an end use.

    Raises
    ------
    ValueError
        If the registry names an alternative not yet selectable (WO-09g answers, recorded for
        later).

    Spec: structure v0.13 §4.5 (default crew order); WO-09g answers, 1.
    """
    if world.settings.substation_rank != HIGHEST_SUPPLIED_WEIGHT:
        raise ValueError(
            f"dynamics.substation_crew_rank is '{world.settings.substation_rank}': its "
            "alternatives are recorded but become selectable only in a later phase"
        )
    weights = {n.node_id: n.end_use_weight for n in world.nodes}
    supplied = [
        weights[d.consumer_id]
        for d in world.dependencies
        if d.supplier_layer == Layer.POWER
        and any(e.supplier_id == node_id for group in d.groups for e in group)
    ]
    return max((w for w in (weights[node_id], *supplied) if w is not None), default=0.0)


QUICK = "quick"
"""The kind and job-id prefix of a quick-path job (Work Order 11, B4).

CHOICE: ``quick:`` sorts before ``repair:`` and ``switch:``, so where the crew-order key ties, a
crew takes the node's quick path before its rebuild (WO-11 answers, 2)."""
QUICK_PATH_STATES = ("extensive", "complete")
"""CHOICE: a quick path applies at extensive and complete damage only; slight and moderate
rebuilds open at hour 0 and are short (ruling R3; WO-11 answers, 2)."""


def _open(job: "_Job", t: float) -> bool:
    """Return whether a job is open at a step: from the first step at or after its open hour.

    CHOICE: a rebuild job opens at the first 15-minute step at or after its parts-ready hour,
    as effects land on steps (WO-11 answers, 2).
    """
    return job.parts_ready_h <= t + 1e-12


def plan_job_id(token: str) -> str:
    """Return the job a plan token names: ``quick:<node>`` as it is, an element id's repair.

    CHOICE: a plan lists quick-path jobs by their job id beside the element ids of repairs
    (WO-11 answers, 2).
    """
    return token if token.startswith(f"{QUICK}:") else f"repair:{token}"


def plan_token(job: "_Job") -> str:
    """Return how a plan names a job: its job id for a quick path, else its element id."""
    return job.job_id if job.kind == QUICK else job.element_id


def quick_paths(world: EngineWorld, damage: Damage) -> tuple[QuickPath, ...]:
    """Return the quick paths a damage opens, in node order.

    A quick path opens for a damaged node at extensive or complete damage whose class has one.

    Parameters
    ----------
    world : EngineWorld
        The world played out.
    damage : Damage
        The damage, with each damaged node's state.

    Returns
    -------
    tuple of QuickPath
        One per node a quick-path job opens for.

    Spec: structure v0.19 §4.4a; ruling R3; Work Order 11, B3.
    """
    damaged = set(damage.nodes)
    return tuple(
        p for p in sorted(world.quick_paths, key=lambda p: p.node_id)
        if p.node_id in damaged and damage.state_of(p.node_id) in QUICK_PATH_STATES
    )  # fmt: skip


def facility_repair(world: EngineWorld, damage: Damage, node_id: str) -> FacilityRepair | None:
    """Return the repair a damaged node takes: the record for the damage state it was given.

    A storm-damaged facility takes the record for the state its scenario drew; a strike takes
    complete damage, named in the damage (ruling Q4). A constructed world may hold one record per
    node with no state, which serves whatever the state.

    Parameters
    ----------
    world : EngineWorld
        The world played out.
    damage : Damage
        The damage, with each damaged node's state.
    node_id : str
        A damaged node.

    Returns
    -------
    FacilityRepair or None
        The record, or None if the world holds no repair for the node.

    Raises
    ------
    ValueError
        If the node has several records and the damage names no state, or names one the world
        holds no record for.

    Spec: structure v0.7 §4.4a (repair by damage state); decision 0019.
    """
    records = [r for r in world.repairs if r.node_id == node_id]
    if not records:
        return None
    state = damage.state_of(node_id)
    if state is None:
        if len(records) == 1:
            return records[0]
        raise ValueError(f"{node_id} is damaged, but the damage names no damage state")
    for record in records:
        if record.damage_state in (state, None):
            return record
    raise ValueError(f"{node_id}: no repair record for damage state {state}")


def _check_ruled_dynamics(settings: Settings) -> None:
    """Stop a run whose registry names a recorded alternative of a ruled dynamics rule.

    Each ruled rule's alternatives are recorded for a later phase, not yet selectable, so a run
    that names one stops before it starts (Work Order 10, C4).

    Parameters
    ----------
    settings : Settings
        The engine's settings, read from the registry.

    Raises
    ------
    ValueError
        If any of the three rules names an alternative.

    Spec: structure v0.16 §4.5; decision 0017; Work Order 10, C4.
    """
    ruled = (
        ("dynamics.substation_crew_rank", settings.substation_rank, HIGHEST_SUPPLIED_WEIGHT),
        ("dynamics.line_point_travel", settings.line_point_travel, ALONG_THE_LINE),
        ("dynamics.floor_after_generator_stops", settings.floor_after_generator_stops, TRIP),
    )
    for rule_id, value, chosen in ruled:
        if value != chosen:
            raise ValueError(
                f"{rule_id} is '{value}': its alternatives are recorded but become selectable "
                "only in a later phase"
            )


ALONG_THE_LINE = "along the line within a job; via the road between jobs"
"""The ruled value of ``dynamics.line_point_travel`` (WO-09g answers 2)."""
HIGHEST_SUPPLIED_WEIGHT = "highest supplied weight"
"""The ruled value of ``dynamics.substation_crew_rank`` (WO-09g answers, 1)."""
TRIP = "trip on what arrives"
"""The ruled value of ``dynamics.floor_after_generator_stops`` (WO-09c answers 2)."""


def trip_hours(legs: Legs, settings: Settings, relaxed: frozenset[str] = frozenset()) -> float:
    """Return a trip's hours by road, off road and, for a sea trip, mobilisation.

    Road km at road speed, off-road km at off-road speed, plus the outlying-island mobilisation
    delay for a sea trip; a relaxed part counts as zero (D11).

    Parameters
    ----------
    legs : Legs
        The trip's road km, off-road km and whether it crosses the sea.
    settings : Settings
        The engine's settings (speeds in km/h, mobilisation in h).
    relaxed : frozenset of str
        Relaxed rule ids.

    Returns
    -------
    float
        Hours.

    Spec: structure v0.9 §4.5 (repair and crews); ruling D6.
    """
    hours = 0.0
    if "crews.road_speed_kmh" not in relaxed:
        hours += legs.road_km / settings.road_kmh
    if "crews.offroad_speed_kmh" not in relaxed:
        hours += legs.offroad_km / settings.offroad_kmh
    if legs.by_sea and "crews.outlying_island_mobilisation_h" not in relaxed:
        hours += settings.mobilisation_h
    return hours


def _without(
    dependencies: tuple[EngineDependency, ...], removed: Iterable[str]
) -> tuple[EngineDependency, ...]:
    """Delete removed coupling edges before the run; a dependency left with none is gone (D8)."""
    gone = set(removed)
    known = {e.edge_id for d in dependencies for g in d.groups for e in g}
    unknown = sorted(gone - known)
    if unknown:
        raise ValueError(f"removed dependencies name no coupling edge: {', '.join(unknown)}")
    result = []
    for dependency in dependencies:
        groups = tuple(
            tuple(e for e in group if e.edge_id not in gone) for group in dependency.groups
        )
        groups = tuple(g for g in groups if g)
        if groups:
            result.append(
                EngineDependency(
                    dependency.dependency_id,
                    dependency.consumer_id,
                    dependency.supplier_layer,
                    groups,
                    dependency.mode,
                    dependency.floor,
                    dependency.tolerance,
                )
            )
    return tuple(result)
