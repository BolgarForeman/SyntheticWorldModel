<!-- Trace game: field manual. Draft v0.1, design side, 2026-10-11. For Foreman's ruling. Context and purpose only: no mechanics shortcuts, nothing about any mission. -->

# Field manual

## 1. The island

You are looking at a constructed island. It is not a real place, but it is built to behave like one.

The generator built the land first: mountains, rivers, coast and towns. Then it built six networks on top, sited by the same rules real planners and engineers use:
- **Fuel.** Import terminals, tank farms and fuel depots.
- **Power.** A generating plant, substations, and the overhead lines between them.
- **Telecom.** An exchange, cell masts, and the lines that join them.
- **Water.** A reservoir, a treatment works, pumping stations and storage.
- **Transport.** A seaport, an airport, a freight yard and the roads.
- **Healthcare.** Hospitals, a clinic and a blood bank.

Every facility on the island has a card. Every number on that card was drawn by the generator from rules taken from real standards and real data, most of them from Taiwan.

We built an island instead of studying a real one for one reason: **here we know the truth.** Every facility, every connection and every back-up is recorded. When we test a method for finding what matters, we can check it against the right answer. In the real world there is no answer sheet.

## 2. What a dependency is

No network stands alone.
- A hospital needs power, water and telecom to work, and roads to receive supplies.
- A power plant needs fuel to burn, water for its boilers, and telecom to control the grid.
- A water pump needs power. A cell mast needs power.

Each of those needs is a **dependency**: one facility relies on another, often in a different network. When a facility fails, its failure travels along those dependencies. Sometimes it travels at once: a pump stops the moment its power does. Sometimes it travels slowly: a hospital runs on its generator until the fuel runs out. Sometimes it doesn't travel at all, because there is a second supply or the back-up outlasts the outage.

How far and how fast a failure travels is the question this game is about.

## 3. Why this is hard in the real world

Public sources tell you a great deal about where things are:
- maps of every substation and line;
- registers of every hospital and its beds;
- lists of power plants, airports and ports.

They tell you very little about **who depends on whom**:
- which substation feeds which hospital;
- how many hours of fuel a generator holds;
- what a water plant does when its telecom goes down.

A planner can usually see the facilities, but rarely the connections between them.

That gap matters. Two facilities that look equally important on a map can be very different when a storm hits. One may have a second supply and three days of fuel. The other may have a single line and four hours of battery. Telling them apart takes the dependencies, and the dependencies are the part the sources leave out.

## 4. What the game asks of you

You will play one storm forward through 72 hours, with **everything known**: every dependency, every back-up, every rule. You play the world as it truly is.

**Your job:**
1. **Set up.** Read the mission briefing. Place a damage marker on everything the storm broke. Place the crew pawns at the base. Put the clock at hour 0.
2. **Follow the failures.** From each damage marker, follow the arrows on the board to the facilities it supplies. Pick up each one's card and decide, using the rule cards, whether it keeps running, runs on reduced service, runs on back-up, or goes out, and when.
3. **Run the clock.** Time moves from event to event: a crew arrives, a repair finishes, a battery runs out. Find the next event, move the clock to it, and apply it.
4. **Keep the log.**
   - Crew sheet: what each crew does and when.
   - Event log: every event, at its exact time.
   - Outage sheet: every end-use facility, affected or not, and why.
   - Decision log: every place a rule could be read two ways, and the reading you chose.
5. **Score it.** Add up the hours each end-use facility was out, then weight them by how much each facility matters. The scoring sheet shows how.

The rule cards teach every mechanic you need. Each has a short drill on the back; do the drills before you start.

**When you finish,** open the sealed envelope. Inside is the answer the computer model reached for the same storm. Read the debrief page and compare.

If your answer differs, that is not failure. A difference is the most useful thing this game produces. It shows either a step to recheck, a rule that needs clearer words, or a place where the model itself needs a second look. Your decision log is how we tell which.
