"""The trace game (Work Order 9, Part H): every printed number from its source, no reference-run
value in the player's pack, no world id in the teaching text, each drill reproduced by the
engine, the sealed score the reference run's, and the board identical at every size.
"""

import functools
import hashlib
import math
import re
from pathlib import Path
from typing import Any

import pytest
import yaml

from swm.cli import _built, _engine
from swm.dynamics.engine import simulate
from swm.dynamics.records import Protect, RunRequest
from swm.recipe.io import load_recipe
from swm.recipe.resolve import resolve
from swm.trace_game.content import (
    SHEETS,
    answer_events,
    answer_outages,
    answer_score,
    briefing,
    node_cards,
    outage_rows,
    short,
    step_of,
    tokens,
)
from swm.trace_game.drills import (
    DRILLS,
    DrillError,
    first_jobs,
    travel_between_jobs,
    verify,
)
from swm.trace_game.pack import BOARD_CHOICES, game_files, trace_game
from swm.trace_game.render import board_pdf, network_order
from swm.trace_game.text import (
    DEBRIEF,
    FIELD_MANUAL,
    PLACEHOLDER,
    RULE_CARD_DIR,
    fill,
    lookup,
    pages_of,
    rule_cards,
    value_text,
)
from swm.trace_pack import TraceInputs, damage_line_rows

TESTS = Path(__file__).resolve().parents[1]
PILOT = TESTS / "fixtures" / "pilot_hand_check.yaml"
RUNS = TESTS / "golden" / "pilot_reference_runs"
BOARDS = TESTS / "golden" / "pilot_board_sizes"
SCENARIO = 7


@functools.cache
def pilot() -> Any:
    resolution = resolve(load_recipe(PILOT))
    built = _built(resolution)
    return built, _engine(resolution, built)


def inputs(actions: tuple[Any, ...] = ()) -> TraceInputs:
    built, engine = pilot()
    damage = engine.damage[SCENARIO]
    run = simulate(engine.world, RunRequest(damage, actions=actions, scenario=SCENARIO))
    return TraceInputs(
        SCENARIO, built.terrain, built.requirements.layers, built.requirements, built.couplings,
        built.strength, built.buffers, built.crews, built.repair,
        built.storm.scenarios[SCENARIO], built.scenarios.scenarios[SCENARIO],
        built.scenarios.lines, engine.world, damage, built.rules, run,
    )  # fmt: skip


@functools.cache
def base_inputs() -> TraceInputs:
    return inputs()


# --- Drills (H3) ----------------------------------------------------------------------------


def test_there_is_a_rule_card_and_a_drill_for_every_mechanic_in_order() -> None:
    cards = rule_cards(pilot()[0].rules)
    assert [c.name for c in cards] == list(DRILLS)
    assert [c.number for c in cards] == list(range(1, 13))


@pytest.mark.parametrize("card", rule_cards(pilot()[0].rules), ids=lambda c: c.name)
def test_each_drill_is_reproduced_by_the_engine(card: Any) -> None:
    answer = verify(card.name, card.expected, pilot()[0].rules)
    assert answer == pytest.approx(card.expected)


def test_a_drill_the_engine_does_not_reproduce_stops_the_build() -> None:
    with pytest.raises(DrillError, match=r"the weakest_supply drill prints 0\.7"):
        verify("weakest_supply", (0.7,), pilot()[0].rules)


def test_the_crew_order_drill_sends_both_crews_to_the_substations_first() -> None:
    first = first_jobs(pilot()[0].rules)
    assert set(first.values()) == {"S_h", "S_c"}
    # The engine ranks a distribution substation by its own Lifeline weight; both are equal, so
    # the nearer goes to the first crew (reported against the card's printed answer).
    assert first == {"crew 1": "S_c", "crew 2": "S_h"}


def test_the_travel_drill_is_timed_from_where_the_crew_stands() -> None:
    # Card 10: B on the road 8 km east, then line L's two points 1 km off it at 12 and 14 km.
    rules = pilot()[0].rules
    lead, work = rules.number("repair.crew_bound_lead_h"), rules.number("storm.line_crew_work_h")
    road, foot = rules.number("crews.road_speed_kmh"), rules.number("crews.offroad_speed_kmh")
    b_done = 8.0 / road + lead + 1.0
    first_done = b_done + 4.0 / road + 1.0 / foot + lead + work
    # Between a line's points the crew walks off, drives and walks back on; no new preparation.
    line_done = first_done + 1.0 / foot + 2.0 / road + 1.0 / foot + work
    assert travel_between_jobs(rules) == pytest.approx((line_done,))
    card = next(c for c in rule_cards(rules) if c.name == "travel_between_jobs")
    assert card.expected == pytest.approx((line_done,))


def test_no_rule_card_still_asks_for_the_engine() -> None:
    for card in rule_cards(pilot()[0].rules):
        text = "\n".join((*card.front, *card.back))
        assert "CONFIRM WITH ENGINE" not in text, card.name
        assert "[To be written" not in text, card.name


def test_the_rule_cards_say_draft_while_their_files_do() -> None:
    for path in sorted(RULE_CARD_DIR.glob("*.md")):
        opening = path.read_text(encoding="utf-8").split("-->", 1)[0].lower()
        card = next(c for c in rule_cards(pilot()[0].rules) if path.stem.endswith(c.name))
        assert card.draft == ("draft" in opening)


# --- Every number equals its source (H10) ---------------------------------------------------


def test_each_rule_card_value_is_read_from_the_registry() -> None:
    rules = pilot()[0].rules
    for path in sorted(RULE_CARD_DIR.glob("*.md")):
        raw = path.read_text(encoding="utf-8")
        card = next(c for c in rule_cards(rules) if path.stem.endswith(c.name))
        printed = "\n".join((*card.front, *card.back))
        assert "{rule:" not in printed
        for rule_id in PLACEHOLDER.findall(raw.split("## Drill world")[0]):
            assert value_text(lookup(rule_id, rules)) in printed, (card.name, rule_id)


def test_a_placeholder_must_name_a_registry_rule() -> None:
    with pytest.raises(KeyError):
        fill("{rule:no.such.rule}", pilot()[0].rules)


def test_each_node_card_is_the_engines_node() -> None:
    world = pilot()[1].world
    cards = {c.node_id: c for c in node_cards(base_inputs())}
    assert set(cards) == {n.node_id for n in world.nodes}
    for dependency in world.dependencies:
        needs = "\n".join(cards[dependency.consumer_id].needs)
        for group in dependency.groups:
            for edge in group:
                assert short(edge.supplier_id) in needs
    for stock in world.stocks:
        hours = round(stock.capacity / stock.draw_per_h, 3)
        assert f"{hours:g} h" in "\n".join(cards[stock.node_id].backup)
    for dependency in world.dependencies:
        tolerance = dependency.tolerance
        if tolerance is not None:
            text = "\n".join(cards[dependency.consumer_id].backup)
            assert f"full {tolerance.t_h:g} h, then {round(tolerance.d_eff, 3):g}" in text


def test_a_node_card_lists_only_switched_on_consumers_and_its_downstream_links() -> None:
    built, engine = pilot()
    for card in node_cards(base_inputs()):
        listed = {name for line in card.supplies for name in line.split(", ") if name != "none"}
        expected = {short(e.consumer_id) for e in built.couplings.edges
                    if e.supplier_id == card.node_id and e.switched_on}  # fmt: skip
        expected |= {short(link.downstream_id) for link in engine.world.links
                     if link.upstream_id == card.node_id}  # fmt: skip
        assert listed == expected


def test_the_cards_carry_no_damage_and_no_scenario() -> None:
    plain = node_cards(base_inputs())
    assert plain == node_cards(inputs((Protect("SWM-POW-L0004"),)))
    damaged = set(base_inputs().engine_damage.lines)
    for card in plain:
        assert not any(short(line) in text for line in damaged
                       for text in (*card.needs, *card.backup, *card.supplies))  # fmt: skip


def test_the_briefing_is_the_scenarios_damage_and_states_no_consequence() -> None:
    brief = briefing(base_inputs())
    assert brief["lines"] == damage_line_rows(base_inputs())
    assert brief["horizon_h"] == pilot()[0].rules.number("dynamics.horizon_h")
    assert set(brief["line_ends"]) == set(base_inputs().engine_damage.lines)  # type: ignore[arg-type]
    assert brief["crews"] == len(pilot()[1].world.crews)


def test_the_outage_sheet_lists_every_end_use_node_with_its_weight() -> None:
    world = pilot()[1].world
    rows = outage_rows(world)
    assert rows == [(n.node_id, n.end_use_weight) for n in world.nodes
                    if n.end_use_weight is not None]  # fmt: skip
    assert set(SHEETS) == {"Crew sheet", "Event log", "Outage sheet", "Decision log",
                           "Play-test feedback"}  # fmt: skip


def test_the_token_sheet_holds_one_pawn_per_crew_and_one_out_marker_per_end_use() -> None:
    counts = tokens(base_inputs())
    assert counts["crew pawn"] == len(pilot()[1].world.crews)
    assert counts["out marker"] == len(outage_rows(pilot()[1].world))
    assert counts["stock clock"] == len(pilot()[1].world.stocks)


# --- The player's pack holds no reference-run value (H10) -----------------------------------


def test_game_files_do_not_depend_on_the_run() -> None:
    plain = game_files(base_inputs())
    other = game_files(inputs((Protect("SWM-POW-L0004"),)))
    assert plain == other


def test_no_teaching_text_names_a_node_or_line_of_the_world() -> None:
    built, engine = pilot()
    ids = {n.node_id for n in engine.world.nodes} | {
        link.link_id for link in built.requirements.layers.links
    }
    ids |= {line.line_id for line in built.scenarios.lines} | {
        c.crew_id for c in engine.world.crews
    }
    names = ids | {short(i) for i in ids}
    texts = []
    for card in rule_cards(built.rules):
        texts += [card.title, *card.front, *card.back]
    texts += pages_of(FIELD_MANUAL, "Field manual")[1] + pages_of(DEBRIEF, "Debrief")[1]
    for text in texts:
        assert not {name for name in names if re.search(rf"\b{re.escape(name)}\b", text)}, text
        assert "SWM-" not in text


# --- The sealed answer (H8) -----------------------------------------------------------------


def test_the_score_is_the_reference_runs() -> None:
    record = yaml.safe_load((RUNS / f"run_{SCENARIO}.yaml").read_text(encoding="utf-8"))
    hours = {node: float(h) for node, h in record["hours_out"].items()}
    weights = dict(outage_rows(pilot()[1].world))
    score = answer_score(base_inputs().run, pilot()[1].world)
    assert score["hours_out"] == pytest.approx(math.fsum(hours.values()), abs=1e-6)
    assert score["weighted_service_hours_lost"] == pytest.approx(
        math.fsum(weights[n] * h for n, h in hours.items()), abs=1e-6)  # fmt: skip


def test_each_event_takes_effect_at_the_first_step_at_or_after_it() -> None:
    events = answer_events(base_inputs().run)
    assert events
    for event in events:
        exact, step = float(event["exact_h"]), float(event["step_h"])  # type: ignore[arg-type]
        assert exact - 1e-6 <= step < exact + 0.25
    assert step_of(5.2, 0.25) == 5.25
    assert step_of(5.25, 0.25) == 5.25
    keys = [(float(e["step_h"]), float(e["exact_h"])) for e in events]  # type: ignore[arg-type]
    assert keys == sorted(keys)


def test_the_outages_match_the_runs_hours_out() -> None:
    run = base_inputs().run
    for row in answer_outages(run, pilot()[1].world):
        assert row["hours_out"] == round(run.hours_out[f"SWM-{row['node']}"], 6)


def test_the_sealed_answer_holds_the_score_and_the_debrief() -> None:
    game = trace_game(base_inputs())
    assert set(game.answer) == {"answer.pdf", "debrief.pdf"}
    assert set(game.answer_tables) == {"events", "outages", "score"}
    assert set(game.game) == {"field_manual.pdf", "rule_cards.pdf", "node_cards.pdf",
                              "board.pdf", "briefing.pdf", "sheets.pdf", "tokens.pdf"}  # fmt: skip


# --- The board (H1, H4) ---------------------------------------------------------------------


def test_the_network_order_is_a_deterministic_permutation_of_each_layer() -> None:
    first = network_order(base_inputs())
    assert first == network_order(base_inputs())
    for layer, nodes in first.items():
        assert sorted(nodes) == sorted(n.node_id for n in pilot()[1].world.nodes
                                       if n.layer == layer)  # fmt: skip


def recorded_boards() -> dict[str, str]:
    lines = (BOARDS / "SHA256SUMS").read_text(encoding="utf-8").splitlines()
    return {name: digest for digest, name in (line.split("  ") for line in lines)}


@pytest.mark.parametrize("size", [s for s in BOARD_CHOICES if s != "11x17"])
def test_the_board_is_identical_at_every_size(size: str) -> None:
    body = board_pdf(base_inputs(), size)
    assert hashlib.sha256(body).hexdigest() == recorded_boards()[f"board_{size}.pdf"]


def test_a_missing_text_prints_a_draft_placeholder(tmp_path: Path) -> None:
    draft, lines = pages_of(tmp_path / "absent.md", "Field manual")
    assert draft
    assert lines[0] == "DRAFT: Field manual"
    ruled = tmp_path / "ruled.md"
    ruled.write_text("# Field manual\n\nText.\n", encoding="utf-8")
    assert pages_of(ruled, "Field manual") == (False, ["# Field manual", "", "Text."])
    drafted = tmp_path / "drafted.md"
    drafted.write_text("<!-- Draft v0.1 -->\n# Debrief\n- **one**\n", encoding="utf-8")
    assert pages_of(drafted, "Debrief") == (True, ["# Debrief", "• one"])
