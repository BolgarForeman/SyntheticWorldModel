WORK ORDER 5, PR 5a follow-up (#8) — ANSWERS (design side, 2026-09-29, confirmed by Foreman)

PR #8 is merged. Record these in PR 5b as an addendum to docs/decisions/0010.

1. Port and airport sizing: confirmed. Compare the city's absolute urban footprint in km² with Taiwan-anchored thresholds from the registry, not a rank among the world's cities.

2. Power factor: confirmed. It applies where MW becomes MVA, in transmission substation sizing. Generation stays in MW.

3. The terrain edge case (a 1 km² world asked for one outlying island produced none).
   - The spec says the outlying-island count is exact.
   - The terrain must deliver the requested count. Where it truly cannot, the build stops with a clear error naming the setting; never fewer islands in silence.
   - This is a small separate fix. It does not block PR 5b and must not change the pilot. Do it as its own pull request (branch terrain/island-count from main) after PR 5b, and state in it that the pilot terrain goldens are unchanged.
