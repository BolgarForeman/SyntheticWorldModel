<!-- Trace game rule card 06. Draft v0.1, design side, 2026-10-11, for Foreman's ruling. {rule:<id>} is replaced at build with the registry value. Nothing here may name the mission's nodes or lines. -->

# 6. Stocks drain and refill

## Front

▮ A stock covers its own supply while it lasts: a battery or generator covers power, a water tank covers water. The card shows hours at full draw. A hospital on its generator draws only its essential load, so its fuel lasts longer than the card's figure.

A generator that fails to start never covers. One that fails to run stops at its time on the generator card. Battery and generator hours add.

**Refill once the supply returns:**
- battery: empty to full in {rule:reserves.battery_recharge_h} h;
- water storage: from the pumps' spare capacity;
- purified water, make-up water and hospital water: from the main, at {rule:reserves.main_refill_rate_fraction} × the rate it drained;
- generator fuel: only by delivery (fuel card);
- national fuel stocks: never, inside the 72 hours.

**Value:** battery recharge {rule:reserves.battery_recharge_h} h; main refill {rule:reserves.main_refill_rate_fraction} × drain rate

**Example:** Facility C, with a 5 h battery, loses power at hour 0. It goes out at hour 5 unless power returns first.

## Back

**Drill:** B has a 4 h battery. Power is lost at hour 0 and returns at hour 3. Does B go out? When is its battery full again?

**Answer:** B **never goes out.** It used 3 of 4 hours, and refills at a full charge per {rule:reserves.battery_recharge_h} h, so it is full again at hour **12**.

## Drill world (for the engine test, not printed)

A → B electricity, trip; B battery 4 h; damage A's supply 0–3 h. Expect B state 1 throughout; battery full at hour 12.
