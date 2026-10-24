# 0021 — Phase 2 close: brute force, the MIP held, and three deferrals

- **Date:** 2026-10-24
- **Decided by:** the author (Foreman), 2026-10-22 to 2026-10-24
- **Recorded by:** Work Order 12
- **Spec:** structure v0.20 §4.5 and §5; Pilot Spec v0.9; Build Game Plan, Phase 2; CLAUDE.md §7

## The MIP cross-check is held for after the proposal (Foreman, 2026-10-23)

**Context.** Every pilot answer key is found by brute force over every affordable answer, reports its spread, rules of thumb and criticality, and is checked byte for byte in CI on both platforms (Work Orders 10 and 11). Brute force is already exact at pilot size; the MIP is needed only for worlds too large for it. CLAUDE.md §7, the Build Game Plan, WO-10, the structure spec and the Pilot Spec still required MIP agreement.

**Decision.**
- Phase 2 closes on brute force. The time-expanded MIP cross-check (HiGHS) is held for after the proposal.
- The crew-rules sheet v0.2 (`docs/design/evidence/MIP_Crew_Rules_Ruling_Sheet_v0_2.md`) and its item 11 stand. Items 1–10 wait with PR 10d, whose WO-10 Part F stays as the outline.
- If everything else finishes before the proposal, the MIP may be picked up then.
- The documents that required MIP agreement are amended to say so (WO-12 G2).

## Black start (Foreman, 2026-10-24, option A)

**Context.** A loop of mutually dependent nodes that collapses completely, with no outside supply, cannot restart in the engine: each step settles from the last, and nothing in the loop can start on its own.

**Decision.**
- **A stated limitation.** Such a loop stays down for the window. In the pilot this is the power, fuel and water loop: a struck transmission substation or pumping station is repaired by its quick path but gives no service.
- **Later.** A black-start rule is to be ruled after the proposal.
- **Effect.** No answer key's optimum depends on it. Structure v0.20 §4.5 states the limitation.

## The rules-justification review is binned until this build iteration is done (Foreman, 2026-10-22 and 2026-10-23)

**Decision.**
- The review in `docs/design/evidence/Rules_Justification_Plan_v0_1.md` waits until this build iteration is done.
- Then every rule must assert at least one part of Curtin's three-part test, and a limitation.
- The comparison-bias test is tagged for Phase 5.

## Phase 2 closes

Phase 2 closes on recipe schema version 4 and structure spec v0.20, as `0.2.0` (CHANGELOG; `docs/trace/phase-2.md`). The `v0.2.0` tag waits for Foreman's word after the Work Order 12 pull request merges.
