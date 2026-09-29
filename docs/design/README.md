# Design inputs

These documents are the specification the code is built against. They are maintained in the design conversation and updated here at phase boundaries.

| File | What it is | Version |
|---|---|---|
| `World_Generator_Structure.md` | The specification: stages, the three kinds of quantity, answer keys, checks, open decisions | v0.6 |
| `Build_Game_Plan.md` | The phased build plan | v0.1 |
| `Pilot_Spec.md` | The first job the generator has to do | v0.5 |
| `Working_Protocol.md` | How work orders, reports and review flow | v0.1 |
| `Repository_Rules_DRAFT.md` | Draft of the repository's `CLAUDE.md`; installed by Work Order 0 | v0.1 |
| `Interface_Mockup_v0_5.dc.html` | Source of the clickable interface mockup. Every control and the recipe fields are defined in its script block. It renders only inside its design tool; read it as a reference, not a page | v0.5 |
| `evidence/` | Evidence bundles and ruling sheets for the dependency table (v0.1) and the design targets (v0.2) | — |

## Changing a modeling rule

Every rule and number that shapes a world lives in the modeling rules registry, `src/swm/rules/modeling_rules.yaml`, with its source, grade, reasoning, status and ruling (decision 0009). `swm rules -o rules.html` renders it as the Modeling Rules page. A rule changes only by a reviewed pull request that:

1. edits the rule's entry in `modeling_rules.yaml`;
2. moves the old value into the entry's `history`, with its units, the date and the decision that changed it;
3. cites the new source (citation, URL, the verbatim quote where one exists, and whether it was verified);
4. adds a decision record in `docs/decisions/`.

The registry's hash is stamped on every world, so the pull request also regenerates the golden files and explains the change.
