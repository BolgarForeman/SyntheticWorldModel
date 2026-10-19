# The hand-trace pack as a teaching game: ruling sheet v0.2

*2026-10-11 · design side, for Foreman · **all items ruled by Foreman, 2026-10-11** · replaces the data-dump pack of PR 18 as the thing a person uses; PR 18's tables stay as the data appendix*

## What this is

**Purpose.** The pack lets a person play one storm scenario forward by hand and reach the engine's answer without seeing it. It serves two purposes:
- **Test:** the Phase 1 hand-trace check.
- **Show:** explain the work to the committee and other readers.

**Ruled 2026-10-11.**
- It teaches the **mechanics, never the solution**.
- **Paper first, interactive later.**
- **First audience:** the committee, with Foreman's son as play-tester.

**Standing rules for every page:**
- Every number and rule is generated from the world and the rules registry by code, never typed by hand.
- No teaching material names or describes any node, line or event of the mission scenario.
- The engine's answer is sealed: printed separately and opened only after play.

## Items to rule

**P1. Format: print-and-play on letter paper.**
- **Rule cards and node cards:** 9 to a sheet, cut along the lines.
- **Board:** one 11×17 sheet, or two letter sheets that join.
- **Token sheet:** damage, crew pawns, an "out" marker, and stock clocks.
- **Log sheets.**
- **Sealed answer:** a separate file and envelope.
- Large type throughout: nothing under 9 pt.
- **Ruled A.** Letter paper; board on 11×17, or two joined sheets. The board is also generated at larger sizes: tiled letter sheets with trim marks, or a single plotter sheet (24×36 or 36×48), all from one layout.

**P2. Time: play by events, not by the 15-minute step.**
- The clock jumps from one event to the next:
  - a crew arrives;
  - preparation ends;
  - a repair finishes;
  - a stock runs out;
  - a telecom fallback period ends;
  - a delivery lands.
- Each event is written on the log with its exact time. A rule card states how the engine rounds to its 15-minute steps, so the player can convert at the end.
- This is the same model as the engine, at a pace a person can follow.
- **Ruled A.** Event-driven play.

**P3. Node cards.**
- One card per node:
  - its name, class and end-use weight;
  - **Needs:** each supply, with its source and share, how the supply arrives, and the node's response if it is cut;
  - **Back-up:** stocks in hours, and telecom fallback;
  - **Supplies:** who depends on it.
- A small symbol set: trip ⚡, throttle ◐, floor ▁, fallback ⏳, stock ▮.
- Damaged elements are not marked on the cards. Damage tokens are placed during setup from the mission briefing. That way the cards can be reused for any scenario.
- **Ruled A.** Neutral cards; damage is marked with markers at setup.

**P4. Rule cards and drills (the teaching).**
- **One rule card per mechanic:**
  - weakest supply wins;
  - throttle, trip and floor;
  - telecom fallback;
  - stocks drain and refill;
  - fuel deliveries;
  - two supplies into one node;
  - the crew sequence;
  - the crew priority order;
  - manual switching;
  - time steps and rounding.
- Each card has the rule in one or two sentences, the registry value printed from the registry, and a tiny illustration built on generic nodes A, B and C.
- **One drill per card,** with its answer on the back.
- Nothing on a rule card refers to the mission.
- **Ruled A.** About 12 rule cards, each with a drill.

**P5. The board.**
- **Network side:** every node in its layer column, every switched-on link and dependency, laid out to keep crossings low. It is neutral: no highlighting of what the damage reaches, since that would lead the player.
- **Map side:** the island, the crew base, every node, and the roads, with travel times from the base printed on them.
- **Hour track:** 0 to 72 h along the edge.
- **Ruled A.** Complete, neutral board laid out to cut crossings; no damage-centred panel. Sizes as P1.

**P6. Mission briefing, log sheets and the sealed answer.**
- **Briefing:** the storm, what failed and where (failure points with km and travel time), the crews and the horizon. What failed, never what it causes.
- **Log sheets:** crew sheet, event log, outage sheet listing every end-use node, decision log.
- **Sealed answer:** the engine's event timeline, hours out per end-use node, and the score.
- **Ruled A.** Briefing, four log sheets (the outage sheet lists every end-use node), sealed answer.

**P7. Score and debrief.**
- **Score:** service-hours lost = Σ end-use weight × hours out. This is the dissertation's metric with Lifeline weights.
- **Debrief page** (read after opening the answer):
  - what the score means;
  - why a planner cares;
  - how to compare your trace with the engine's, line by line.
- The decision log is what makes differences explainable.
- **Ruled C.** Weighted service-hours lost is the headline score, with unweighted hours out beside it; the debrief page is read after the envelope is opened.

**P8. Field manual, about 4 pages.**
- The island and its six networks.
- What a dependency between networks is.
- Why sources show the facilities but rarely the dependencies.
- What the game asks of you.
- Purpose and context only: no mechanics shortcuts, no mission content.
- Design side drafts it; Foreman rules on it.
- **Ruled A.** Four pages, context and purpose only; the design side drafts, Foreman rules, the coder typesets.

**P9. Generated, for any world and scenario.**
- `swm trace-pack --scenario N` writes the whole pack: cards, board, tokens, briefing, log sheets, rule cards with registry values, and the sealed answer.
- **Fixed text** (field manual, rule-card wording, drills, debrief) lives as text files in the repository, reviewed like the spec.
- The pack must be byte-identical across platforms, as before.
- **Ruled A.** Generated by `swm trace-pack`; teaching wording kept as reviewed text files; byte-identical output.

**P10. Play-test protocol.**
- **First play-test:** your son, with the pack only, and no help beyond the field manual and rule cards. Record:
  - time taken;
  - every question he had to ask (each one is a pack defect);
  - where he got stuck;
  - his score against the engine's.
- **Then the committee.**
- Every question and difference goes in a feedback log, and pack fixes are ruled like any other.
- **Ruled A.** Hands-off play-test with a printed feedback sheet; every question is a pack defect; differences are sorted as player error, unclear pack, or engine departs from the spec.

**P11. What closes Phase 1, and what comes next.**
- **Phase 1 needs** the pieces that make a hand trace possible: node cards, rule cards with registry values, board, briefing, log sheets and the sealed answer. These rebuild the pack in PR 9a; PR 18's tables stay as the data appendix.
- **The next work order brings** the field manual, drills, debrief and token sheet.
- **Interactive version:** Phase 7, with the interface.
- **Ruled B.** The whole paper game, field manual and debrief included, is built in Phase 1. The son's play-test is the Phase 1 hand-trace acceptance test, and v0.1.0 waits on it. Interactive version: Phase 7.
