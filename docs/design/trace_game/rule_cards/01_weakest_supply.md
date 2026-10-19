<!-- Trace game rule card 01. Drafted by the design side, 2026-10-11; approved by Foreman, 2026-10-19 (REVIEW_LOG.md). {rule:<id>} is replaced at build with the registry value. Nothing here may name the mission's nodes or lines. -->

# 1. Weakest supply wins

## Front

A facility's level is the **lowest** of its responses across everything it needs, times its condition (1 if intact, 0 if damaged and not yet repaired). Full power does not make up for missing water.

**Value:** none

**Example:** B needs power and water. Power arrives in full. Water arrives at 50%, and B throttles on water. B runs at **0.5**.

## Back

**Drill:** B needs power (response: throttle) and water (response: trip). Power arrives at 100%. Water arrives at 85%. What level is B at?

**Answer:** **0.** Water is below the trip point ({rule:dynamics.trip_point}), so the water response is 0, and the lowest response sets B's level.

## Drill world (for the engine test, not printed)

Nodes A_power, A_water, B. A_power → B electricity, κ 1, linear; B power response throttle. A_water → B water, κ 0.85 (single group), linear; B water response trip. No damage. Expect B state 0 at hour 0.
