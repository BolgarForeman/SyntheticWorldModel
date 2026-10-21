# Work Order 10c: answers, PR 30 (apply on this branch before merge)

*2026-10-21 · question 1 ruled by Foreman (the author), option A; question 2 follows from it · apply on `wo10c/defensive`, push to PR 30 · add to decision 0018 · spec now v0.18*

## Review

- Accepted as built:
  - the defensive model;
  - the new stock;
  - the skips;
  - the CI split and the key checks;
  - the slow re-solve (every hash matched);
  - stopping budget 4 at its projection (step 3c).
- Every `CHOICE:` listed in the report stands.
- **Budget 3 reads correctly.** Protect SWM-TEL-L0002: 2.625 against 8.594 with no action. No reserve changes any run, because in these storms only masts lose service, through cut telecom lines, and every power cut has a second feed.

## Answers

1. **Reserves on telecom dependencies (ruled by Foreman, option A): none.**
   - Telecom cannot be stored. A telecom site's battery is a reserve on its power, which stays allowed. Telecom outages keep their own fallback rule (rule card 5).
   - Reserves go only on dependencies whose commodity can be stored: power, water, fuel, and transport (as stockpiled supplies).
   - In the pilot that leaves 31 reservable dependencies of the 47.
   - Record it in the registry: the storable commodities, with the alternative "every dependency, telecom included" (the earlier build), grade J, ruled 2026-10-21, decision 0018.
   - Spec v0.18 §5 and Pilot Spec v0.8 carry it, both committed on this branch.

2. **Budget 4: yes, tonight, under the new action set.** It should be about a quarter of the earlier size: about 65,000 answers at budget 4 and about 6,800 at budget 3.

## Apply

- **Now (light; don't run any search during the day):**
  - the registry entry;
  - the change to which dependencies take reserves;
  - the tests, including one that no telecom dependency is offered a reserve;
  - the answer counts at both budgets;
  - the records.
  
  Push.
- **Tonight, as the last thing on the machine:**
  1. re-solve budget 3, and commit its keys and answers file;
  2. time budget 4. Foreman approves in advance up to 10 hours in total for budget 3, budget 4's main search and its nearest-supplier search together. Run what fits; report the rest as not run, with its projection;
  3. commit budget 4's keys and answers file;
  4. run the slow re-solve on every key except budget 4's;
  5. push, and report in the §11 format with every time.
- **Goldens:** the defensive keys and answers files change, because of the smaller action set; the registry stamp moves everywhere. Nothing else moves. Explain each change.
