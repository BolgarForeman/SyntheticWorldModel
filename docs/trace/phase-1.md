# Phase 1 — notes toward the TRACE entry

*Notes kept as Phase 1 is built; the entry is completed when the phase closes (`v0.1.0`).*

## The dynamics engine (Work Order 7, PRs 7a and 7b; decision 0014)

**What was built.**
- **Engine:** `src/swm/dynamics/` plays one storm scenario out over time.
  - A node's state is its condition × the lowest of its responses across its commodities.
  - Edges deliver κ × g_δ(supplier state), linear or at the threshold θ.
  - Links inside power, telecom, water and fuel carry their layer's commodity from the signature's first stage down.
  - Stocks cover their own commodity, refill as ruled, and take fuel deliveries.
  - Telecom tolerance acts first.
  - Crews work through repairs in the default order, with a 2 h crew-bound lead per job and parts lead time running in parallel.
  - A substation whose telecom is down needs a manual switching trip.
  - Steps are 15 minutes, settled within each step up to 100 passes.
- **Commands:** `swm simulate` prints the hourly trajectory and plots a timeline. `swm check` runs the calm-world run on every world.
- **Isolation:** the engine is pure. It never imports error induction or emission, and the generator never imports it.

**How it was tested.**
- **Degradation profiles:** one test per profile in Degradation Profiles v0.3, each limit also at its relaxed value. All pass.
- **Calm world:** with no damage, every node holds 1 and nothing moves on the pilot and the severity-70 copy.
- **Properties on the pilot:** relaxing any single limit, or protecting any damaged element, never raises any node's hours out.
- **Constructed cases:**
  - removal versus relaxing;
  - crew-bound lead per job, parallel parts and the crew order;
  - manual switching only when telecom is down and the repair is elsewhere;
  - a step that hits the settling cap is reported;
  - a ring of links cannot keep itself supplied;
  - pump capacity pro rata by demand;
  - a missed delivery made when the depot returns;
  - hospital water refilled from the main.
- **Reference runs:** the pilot's 8 scenarios are saved as goldens (`tests/golden/pilot_reference_runs/`) and must reproduce byte for byte on Windows and Linux.

**Departures from the design.**
- **Line-loss calibration:** the targets were moved from one realized draw to the expected share. The realized share depended on the draws, which changed when storm damage moved to one stream per element (PR 15 answers; PR 7b answers).
- **Degradation profiles:** v0.2 said LNG and oil plants ride out a fuel cut on their own stocks. The world holds those stocks upstream, so v0.3 corrects the profile to the world as built.
- **Delivery timing:** a fuel delivery waits for the depot's settled state within its step.
