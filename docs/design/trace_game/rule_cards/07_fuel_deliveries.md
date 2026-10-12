<!-- Trace game rule card 07. Draft v0.1, design side, 2026-10-11, for Foreman's ruling. {rule:<id>} is replaced at build with the registry value. Nothing here may name the mission's nodes or lines. -->

# 7. Fuel deliveries

## Front

A generator's tank is refilled only by truck. The first delivery arrives {rule:reserves.fuel_resupply.lead_time_h} h after the facility loses power; then one every {rule:reserves.fuel_resupply.delivery_h} h. Each delivery carries 24 h of fuel. Deliveries come only while the fuel depot is working and a road reaches the facility.

**Value:** lead time {rule:reserves.fuel_resupply.lead_time_h} h; interval {rule:reserves.fuel_resupply.delivery_h} h

**Example:** Facility C, with 20 h of generator fuel, loses power at hour 0. Its first delivery arrives at hour {rule:reserves.fuel_resupply.lead_time_h}, before the tank is empty.

## Back

**Drill:** B's generator holds 10 h of fuel. B loses power at hour 0, and the power stays off. Is B ever out, and when?

**Answer:** Out from hour **10** to hour **12**, when the first delivery arrives. From then on each delivery lands before the tank empties.

## Drill world (for the engine test, not printed)

Depot D → B fuel resupply edge; B generator fuel 10 h; damage B's power supply at 0 for 72 h. Expect B out 10–12, then 1.
