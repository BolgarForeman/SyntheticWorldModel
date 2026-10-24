# 0020 — Repair timing: service restored and rebuilt

- **Date:** 2026-10-23
- **Decided by:** the author (Foreman), 2026-10-22 and 2026-10-23
- **Source:** `docs/design/evidence/Repair_Timing_Ruling_Sheet_v0_1.md` (R1–R5); `docs/design/evidence/MIP_Crew_Rules_Ruling_Sheet_v0_2.md`, Part 3 (E1, E2) and item 11; Work Order 11
- **Spec:** structure v0.19 §4.4a and §4.5, "Repair and crews"

## Context

Writing the crew rules as equations, for the MIP cross-check, found two engine bugs and a spec ambiguity. Ruling the ambiguity showed that the world's one repair time, Hazus's time to rebuild, is the wrong quantity for a 72-hour window: service comes back much sooner through workarounds.

## Decisions

- **E1, a bug fix.** A cancelled switching trip no longer strands a newer one. Only a substation's unassigned trip is cancelled when its mark clears, and the node-to-trip index stays consistent, including when a facility's own repair clears the mark.
- **E2, a bug fix.** A stock that runs out passes on the remainder: the next stock is charged the uncovered share of the step's need, at its own draw rate, not the full need again.
- **Item 11 (2026-10-22).** A rebuild job is not open until its parts are ready. No crew is sent and none waits on site; the "wait for parts" activity is gone.
- **R1 (2026-10-22).** Two quantities: the rebuild (Hazus, kept in the true world and the manifest) and service restored. Whichever finishes first sets the node's state.
- **R2 (2026-10-23).** Slight and moderate damage have no parts wait. Repairs use stocked spares, so the job opens at hour 0.
- **R3 (2026-10-23).** At extensive and complete damage, a node comes back inside the window only by a quick path its class has. The table is `repair.service_restore.quick_paths` (J, placeholders), which replaces `repair.emergency.other_classes` (ruling T11).
- **R4 (2026-10-23).** A crew quick path is a crew job in the default crew order. Widespread delay comes from crew and unit contention alone; no new pools.
- **R5 (2026-10-23).** This reopens ruling T6, ruling T11 and decision 0011's split of the Hazus time. The pilot storm stays at slight and moderate facility damage; only T6's reason is restated.

## Registry

- `repair.parts_lead_time`: a rebuild job opens at the parts-ready hour; there is no wait at slight and moderate damage.
- `repair.service_restore.quick_paths`: new. It replaces `repair.emergency.other_classes`, whose value moves to its history.
- `repair.pilot_damage_states`: the value is unchanged and only its reasoning is restated, so its old value is in its history.

## The coder's choices, accepted (WO-11 answers, 2)

- A job opens at the first 15-minute step at or after its parts-ready hour.
- The quick-path job id is `quick:<node>`, which sorts before `repair:` and `switch:`, so a tied crew takes the quick path first.
- A planned crew whose next job is not yet open takes only open switching trips until it opens.
- Quick paths apply at extensive and complete damage only.
- Restorative plans name quick-path jobs by `quick:<node>`, beside element ids.
- E2 passes on the uncovered share of the step's need, at the next stock's own draw rate.
- The trace game's "has parts for" text goes with the removed activity.

## Rule card 8 (WO-11 answers, 1)

Rule card 8 is reworded and approved by Foreman (2026-10-23). The drill now answers 16 h: the job opens at hour 5 when the parts arrive, then 1 h of travel, the 2 h assessment and 8 h of work.
