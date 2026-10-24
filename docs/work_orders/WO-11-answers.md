# Work Order 11: answers to the coder's stop (ModelGenerator_Prompt_05)

*2026-10-23 · design side · ruled by Foreman, 2026-10-23*

## 1. Rule card 8 is reworded (approved by Foreman, 2026-10-23)

The coder stopped correctly under CLAUDE.md §10. WO-11 B1 changes the timing that card 8's drill teaches, and the build plays every drill through the engine. The reword also applies ruling R2: slight and moderate repairs have no parts wait.

Apply to `docs/design/trace_game/rule_cards/08_crew_sequence.md`.

**Front, step 3**, replacing "repairs once the parts are in. Parts lead time runs from hour 0, in parallel, with no crew.":

> works. At slight or moderate damage the parts are on hand, so work starts after preparation. A heavier rebuild needs parts, which take their lead time from hour 0, with no crew. The job opens only when they arrive; then the crew travels, prepares and works.

**Back:**

> **Drill:** A crew is free at hour 0, 1 h from a facility being rebuilt. Its parts arrive at hour 5, and the crew work is 8 h. When is the facility back?
>
> **Answer:** The job opens at hour 5. The crew arrives at 6, is prepared at 8, and works 8–16. Back at hour **16**.

**Drill world:**

> One crew; facility F being rebuilt, parts lead 5 h, crew work 8 h, travel 1 h. Expect F restored at 16 (before step rounding; see time card).

The front's example (a line back at hour 9.5) is unchanged; lines never wait for parts. Update the `crew_sequence` drill's docstring to match.

Append to `docs/design/trace_game/REVIEW_LOG.md`:

> - 2026-10-23 — Rule card 8 changed by ruling (Work Order 11; repair timing R2 and MIP sheet item 11): slight and moderate repairs need no parts wait; a heavier rebuild's job opens only when its parts arrive. The drill's answer is now 16 h.

## 2. The coder's proposed choices: accepted

Each is marked `CHOICE:` in the code and listed in the report:
- a job opens at the first 15-minute step at or after its parts-ready hour;
- the quick-path job id is `quick:<node>`, which sorts before `repair:` and `switch:`, so a tied crew takes the quick path first;
- a planned crew whose next job is not open takes only open switching trips until it opens;
- quick paths apply at extensive and complete damage only (R3);
- the restorative plan tokens `quick:<node>` sit beside element ids;
- A2 passes on the uncovered share of the step's need, at the next stock's own draw rate;
- the trace game's "has parts for" text goes with the removed activity.

A1 as proposed: only an unassigned trip is cancelled, and the index stays consistent, including when a facility's own repair clears the mark.

## 3. Go ahead

Merge this branch into `wo11/repair-timing` and restart ModelGenerator_Prompt_05 at step 2.
