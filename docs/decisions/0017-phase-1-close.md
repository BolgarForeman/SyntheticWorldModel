# 0017 — Phase 1 close: the trace game and its rulings

- **Date:** opened 2026-10-19; completed with PR 9c
- **Decided by:** the author (Foreman)
- **Recorded by:** Work Order 9 (PRs 9a, 9g, 9b, 9c). Further entries are added as each is ruled.

## Crew order among distribution substations (WO-09g answers, answer 1; structure v0.13 §4.5)

**Context.** Rule card 9 printed that the crew takes the substation feeding the hospital first. The engine ranked a distribution substation by its own Lifeline weight, which every distribution substation shares, so the nearer one went first.

**Decision.**
- **The ranking.** In group 2 of the default crew order, a distribution substation ranks by the highest Lifeline weight among the end uses it supplies, its own weight included. Ties go to the shortest trip, then the lowest id. Power feeds to end uses keep their key.
- **"Supplies."** It means the electricity couplings to end-use nodes that the engine plays, both switched on and hidden.
- **Registry.** The ranking is recorded as `dynamics.substation_crew_rank`: chosen "highest supplied weight"; alternatives "own weight only" and "sum of supplied weights"; grade J; ruled 2026-10-19. It appears in the Theta List.
- **Alternatives.** The engine reads the rule. The two alternatives are recorded, not yet selectable; naming one stops the run with a message.
- **Later.** Foreman's standing requirement: each dynamics rule with recorded alternatives becomes a recipe setting and an interface choice, built with the answer-key solver (Phase 2) or the interface (Phase 7), whichever comes first.

**Effect.** The 8 pilot reference runs are unchanged apart from the registry stamp. No pilot scenario gives a crew a distribution-substation job: every job is a line or a power feed. Rule card 9's printed answer now holds, and its drill checks the engine.

## Crew travel along a line (WO-09g answers 2; structure v0.14 §4.5)

**Context.** The design side's sealed hand trace of scenario 7 agreed with the engine everywhere except one point: how a crew travels from one failure point of a line to the next. The spec never said. The engine walked back to the nearest road, drove, and walked back in, which took 6.7 h for 2 km between two breaks on the same telecom line.

**Decision (option C).**
- **Between failure points of the same line:** the crew walks along the line, the distance between the two points, at the off-road speed, with no new preparation.
- **Between different jobs:** as before, via the road.
- **Registry.** The rule is recorded as `dynamics.line_point_travel`: chosen "along the line within a job; via the road between jobs"; alternatives "always via the road" and "whichever way is shorter"; grade J; ruled 2026-10-19.
- **Alternatives.** As for the substation ranking, an alternative named in the registry stops the run.

**Effect.** Only scenario 7 has a line job with more than one failure point, so only its run changes:
- TEL-L0002 done at 17.9986 h; TEL-0003 back at 18.00 h;
- crew 2 travels 8.245 h to TEL-L0001, which is done at 34.2437 h; TEL-0002 back at 34.25 h;
- 52.25 weighted service-hours lost.

This matches the design side's recomputed trace on every point. Rule card 10's drill now answers 18.8 h.

## Teaching text approved (REVIEW_LOG.md)

Foreman approved all twelve rule cards, the field manual and the debrief on 2026-10-19. The game prints them without DRAFT marks. Card 2's floor line still carries a CONFIRM marker; the engine's answer is reported for a ruling, and the card is unchanged.

## Hidden couplings in the truth manifest (WO-09b answers, review)

**Context.** Work Order 9, B3 asks the manifest to list a hidden layer's couplings under hidden couplings. The manifest listed only couplings that were not switched on.

**Decision (accepted as built; a `CHOICE:` in `swm/manifest/truth.py`).**
- A coupling is listed as hidden when it is switched off, or when either end's layer is hidden.
- Each row keeps its `switched_on` flag, so the two kinds stay distinct.
- A new `withheld_links` key lists the links that nodes-only sources withhold.

**Effect.** The change touches the manifest only; no world changes. The pilot hides no layer, so its hidden couplings are unchanged. Its manifest gains `withheld_links`, listing its 6 nodes-only fuel and healthcare links.

## The area a file says it covers (WO-09b answers, answer 2; structure v0.15 §4.6)

**Context.** The OpenStreetMap extract's bounds and every Overpass query's search area were the extent of what was emitted. Hiding telecom therefore shrank the box, which hinted at where the hidden objects were not.

**Decision (option A, ruled by Foreman 2026-10-19).**
- **Fixed by the terrain, never by what is emitted.** The `.osm` `<bounds>`, the `.pbf` header box and every Overpass search area are the world's whole map area: the smallest latitude and longitude box holding the terrain grid's four corners, at 7 decimals.
- **Format-defined boxes are unchanged.** A shapefile's header box and an Overpass element's own `bounds` stay the extent of what that file or element holds, as the real formats define them.
- **Alternatives recorded:** the island's land plus a margin; the extent of what was emitted, which was the earlier behaviour.

**Effect.** The pilot's bounds and query areas change once, and nothing in the world moves. Hiding a layer or withholding links now moves no other file's stated area.

## Error settings in Phase 1: recorded, not applied (WO-09 C2, ruled 2026-10-11)

**Decision.** Phase 1 does not apply error settings. Every source is emitted with zero error, whatever the recipe says.
- **Recorded:** the settings are kept in the resolved recipe, with a note beside its errors section saying they are not applied.
- **Warned:** `swm build` and `swm emit` print one warning naming every source whose settings are above zero.
- **Declared:** the truth manifest lists the departure.
- **Tested:** a recipe with non-zero rates produces sources byte-equal to those of a zero-rate build.

Error induction arrives in Phase 3.

## Golden worlds (WO-09 B; PR 23)

**Decision.** Besides the pilot, Phase 1 closes with two golden worlds, each the pilot with one change:
- `pilot_hidden_telecom`: telecom hidden;
- `pilot_power_nodes_only`: power reporting nodes only.

Both builds are checked in with hashes. Each equals the pilot in every stage hash, the manifest's true world and all 8 reference runs, and every file that differs has a stated reason.

## The hand-trace acceptance test (WO-09c answers, F0; ruled by Foreman 2026-10-19)

**Context.** Work Order 9 named Foreman's son's play-test of the trace game as the Phase 1 hand-trace acceptance test. Foreman ruled the play-test a nice-to-have, not needed before the proposal: "having the hand drawn test available is the thing to show".

**Decision.**
- **The acceptance test** is the design side's sealed hand trace of scenario 7 against the engine.
  - It was written on 2026-10-11, before any engine result was seen.
  - It was compared on 2026-10-19 and agreed on every point but one rule, travel along a line, which was then ruled (above).
  - The engine matches the recomputed trace exactly.
- **The play-test and a clean-agent trace** stay optional. If either is run later, its differences are logged and ruled like any other.

**The fixture.** `tests/fixtures/hand_trace_scenario_7.yaml` was written by hand by the design side and is never regenerated from the engine. It holds:
- each crew's arrival, preparation and completion;
- each repair's back-in-service hour;
- hours out for every end-use node, and the score;
- the state of named nodes at named hours;
- the three things that did not happen.

**The test.** `tests/unit/test_hand_trace.py` compares the engine's run with the fixture at the engine's 15-minute step, exactly.
- An event's step hour is the first step at or after it, where the engine applies its effect.
- `null` means not within the 72-hour horizon.
- All 12 comparisons pass with the fixture as sent. A future mismatch is reported (CLAUDE.md §10), never fixed in the fixture.

## A hospital after its generator stops (WO-09c answers 2; structure v0.16 §4.5)

**Context.** The spec said a hospital on its generator runs at its essential fraction, but not what it does once the generator stops. The engine treated it as a trip; rule card 2's draft said it runs at what arrives. The card's CONFIRM note stood open.

**Decision (option A, ruled by Foreman 2026-10-19).**
- **The rule.** Once the generator stops (no fuel, or it fails to run), a hospital responds as a trip on the power that arrives: fully while it receives at least the trip point, otherwise out. This is the engine as built.
- **Registry.** It is recorded as `dynamics.floor_after_generator_stops`, with grade J:
  - chosen: "trip on what arrives";
  - alternatives: "throttle: runs at what arrives" (card 2's draft) and "the essential fraction while at least that share arrives, else out".
- **Theta List.** The entry appears there.
- **Alternatives.** As for the other dynamics entries, naming an alternative stops the run.
- **Card 2.** The design side has reworded the card and removed its CONFIRM note (REVIEW_LOG). No card prints a CONFIRM note.

**Effect.**
- **Engine:** no change.
- **Goldens:** only the registry stamp, the manifests' new Theta List entry and card 2's printed text change.

## Phase 1 closes

Phase 1 closes on recipe schema version 3 and structure spec v0.16, as `0.1.0` (CHANGELOG; `docs/trace/phase-1.md`). The `v0.1.0` tag waits for Foreman's word after PR 9c merges.
