# 0019 — A damaged facility is repaired at the state it was given

- **Date:** 2026-10-20
- **Decided by:** the design side, applying structure §4.4a (WO-10a answers, 5); a fix of a departure, not a new rule
- **Found by:** the coder while building PR 10a (PR 26, question 5)
- **Spec:** structure v0.7 §4.4a (permanent repair at each damage state); Phase 2 ruling Q4

## Context

The repair stage records each facility's permanent repair at all four Hazus damage states, and the engine's world carried all four. The engine looked records up by node id alone, so the last one listed won. That was always *complete*: every damaged facility took complete damage's crew work and parts lead time, whatever state its scenario drew. The trace pack's damaged-facility table read the same way.

No pilot scenario damages a facility, so no pilot golden showed it.

## Decision

- **Records by state.** Repair records are kept by (node, damage state).
- **Storm damage.** A storm-damaged facility takes the record for the state its scenario drew; the scenario's damage now carries each facility's state.
- **Strikes.** A strike takes complete damage explicitly (ruling Q4), named in the damage, not by falling through. A strike on a node a scenario already damaged raises it to complete.
- **No fall-through.** A node with several records and no named state stops the run with a message. A constructed world that holds one record per node with no state still serves any state.

## Effect

- **The pilot and its fixture worlds:** unchanged, since no pilot scenario damages a facility. Every reference run, the hand-trace test and every golden are byte-identical.
- **The severity-70 copy:** one facility is flood-damaged in its eight scenarios, SWM-POW-0001 at *slight* in scenario 5.
  - **Old repair:** parts lead 1,428.4 h and crew work 168 h (the complete record).
  - **New repair:** parts lead 2.1 h and crew work 8 h.
  - **Its runs do not move,** byte for byte. Both crews spend the whole 72-hour window on two collapsed tower lines (SWM-POW-L0005 and SWM-POW-L0001, crew-order tier 0), so the plant's repair never starts under either record.
