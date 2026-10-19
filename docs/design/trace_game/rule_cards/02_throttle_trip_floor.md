<!-- Trace game rule card 02. Drafted by the design side, 2026-10-11; approved by Foreman, 2026-10-19 (REVIEW_LOG.md). {rule:<id>} is replaced at build with the registry value. Nothing here may name the mission's nodes or lines. -->

# 2. Throttle, trip, floor

## Front

When a supply falls short, the facility responds in one of three ways (shown on its card):
- ◐ **throttle**: runs at the share it receives;
- ⚡ **trip**: runs fully while it receives at least the trip point, otherwise shuts off;
- ▁ **floor**: a hospital whose power falls short runs at its essential level ({rule:reserves.hospital.essential_load_fraction}) on its generator, as long as the generator runs and has fuel. When the fuel runs out, its power response falls to what actually arrives. [CONFIRM WITH ENGINE: keep this sentence only if the engine does exactly this; otherwise state what it does and report the difference.]

**Value:** trip point {rule:dynamics.trip_point}; floor {rule:reserves.hospital.essential_load_fraction}

**Example:** Supply arrives at 70%. Throttle: 0.7. Trip: 0 (70% is below the trip point). Floor: {rule:reserves.hospital.essential_load_fraction}.

## Back

**Drill:** C trips on power. Power arrives at 92%. What level is C at? What if it arrives at 89%?

**Answer:** At 92%, **1** (at or above the trip point). At 89%, **0**.

## Drill world (for the engine test, not printed)

A → C electricity, linear, κ 0.92 then κ 0.89 (two runs); C power response trip. Expect 1, then 0.
