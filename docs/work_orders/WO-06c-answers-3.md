# Work Order 6c: third answers to PR 14

*2026-10-09 · ruled by Foreman (the author) · applies to branch `wo6c/power-lines` at commit 2db9776 · closes PR 14's questions*

1. **Isolation condition (b) failing alone (question 1).** Leave it as built. Both of the code's conditions stay as separate tests. Because H is measured from the lowest ground upwind, (b) never fails without (a). The test proving that stays in place of the one answer 4 asked for. Redefining H would move the factor everywhere for little effect, since the ceiling binds on 78–90% of the land with any speed-up.
2. **The ceiling's precision (question 2).** Keep 1.17, stored to 2 decimals. The pilot's highest gust is then 95.27 m/s against the 95.2 m/s record; the 0.07 m/s difference is below anemometer resolution.

Spec §4.3b is updated on the branch with the ceiling's value, the calibrated median (163.69 m/s) and the achieved line-loss shares (pilot 7.8%, severity 70 32.1%). No code change is needed. PR 14 is clear to merge once CI passes on this commit.
