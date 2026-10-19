<!-- Trace game rule card 09. Drafted by the design side, 2026-10-11; approved by Foreman, 2026-10-19 (REVIEW_LOG.md). {rule:<id>} is replaced at build with the registry value. Nothing here may name the mission's nodes or lines. -->

# 9. Which job a crew takes next

## Front

A free crew takes the waiting job that comes first in this order:
1. towered power lines and transmission substations;
2. distribution substations and power feeds to end uses, highest weight first (a substation counts the highest weight among what it supplies, its own included);
3. everything else.

Ties go to the shortest trip from where the crew stands, then the lowest id. Crews never go back to base between jobs.

**Value:** none

**Example:** A damaged pumping station close by and a transmission substation farther away are both waiting. The crew takes the transmission substation.

## Back

**Drill:** Two crews are free at the base. Three jobs wait: a damaged pumping station 1 h away, a distribution substation feeding a hospital (weight 10) 3 h away, and a distribution substation feeding a clinic (weight 3) 2 h away. Which job does each crew take first?

**Answer:** Crew 1 takes the **substation feeding the hospital** (group 2, highest weight). Crew 2 takes the **substation feeding the clinic** (group 2). The pumping station waits (group 3), though it is closest.

## Drill world (for the engine test, not printed)

Two crews; jobs: pumping station P (1 h), distribution substation S_h feeding an end use of weight 10 (3 h), distribution substation S_c feeding weight 3 (2 h). Expect first assignments S_h and S_c.
