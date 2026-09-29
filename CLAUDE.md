# SyntheticWorldModel — rules for working in this repository

This file is read at the start of every coding session. It is the standing agreement for how code in this repository is written, tested and recorded. The code is published with the dissertation. Someone else must be able to read it, rerun it and get the same worlds, and it must do what the dissertation says it does.

## 1. What this code is

A generator of constructed worlds: synthetic six-layer interdependent infrastructure systems on synthetic terrain, emitted as source files in the real structure of real sources, with a truth manifest. A separate solver computes answer keys against each world. The specification is `docs/design/World_Generator_Structure.md`, and the interface mockup defines every control. **The specification governs.** If code and specification disagree, the code is wrong or the specification needs a decision. Neither is fixed silently.

## 2. Scope discipline

- Build what the current work order asks, and nothing else. No speculative features, no switches "for later", no general frameworks for one use.
- **Small implementation choices are yours:** internal names, data structures, how a function is split.
- **Anything that changes the world or its meaning is not.** That covers what the world contains, what is emitted, what a number means, or what a check accepts. When the specification is silent or ambiguous on one of these, stop and put the question in your report. Do not guess and carry on.
- When a choice isn't in the specification but has to be made to proceed, mark it `# CHOICE:` in the code with a one-line reason and list it in your report. The design side decides whether it stands.

## 3. The three kinds of quantity are enforced in code

- **Observed:** emitted to sources, with source error.
- **Real but unobserved:** in the true world and the manifest, never emitted.
- **Rules:** the world's dynamics.

These are separate types. Emission code receives only observed quantities and cannot reach unobserved ones. A test proves no unobserved field reaches any emitted file.

The answer-key solver never imports error induction, and the generator never imports the solver.

## 4. Reproducibility

- **All randomness comes from the spawn tree.** There is one root seed. Every stage, source and drawn quantity gets its own child stream, keyed by a **stable name**: `SeedSequence(root, spawn_key=(stable_id(name),))`, where `stable_id` is a fixed hash (not Python's `hash()`). Adding a stage must not move any existing stream.
- **No other randomness:**
  - no global RNG, `np.random.seed` or `random` module;
  - no wall-clock time, UUIDs, or unordered iteration (sets, dict order from external input) affecting output.
- **Byte-identical output.** Sort before writing, use fixed float formatting, and fix timestamps and metadata inside emitted files (PBF, GeoPackage and CSV headers included).
- **Only two inputs:** the recipe and the per-machine data-path file (`machine.toml`, gitignored, with `machine.example.toml` checked in). Defaults live in the recipe schema. The resolved recipe, with every default filled in, is written beside every world.
- **Pinned environment:** Python version pinned, dependencies locked with `uv`.
- **Same bytes on every platform.** Development runs on Windows; CI runs on Windows and Linux. Use pathlib for every path, write text with newline='\n' and explicit UTF-8, and never let output depend on the operating system, locale or path separator. The identity check must pass on both.
- **Cross-platform arithmetic.** World-building arithmetic uses only +, −, ×, ÷ and sqrt: no sin, cos, exp or log; no `numpy.random` distributions beyond uniform integers and doubles; no `dot`, `matmul` or other library reductions whose order can vary. If a transcendental function is unavoidable, quantise its result and say so in the report. CI on both platforms is the proof.

## 5. Structure

```
src/swm/
  recipe/      schema (pydantic), loading, versioning, resolution of defaults
  rng.py       spawn tree
  coordinates.py  Point Nemo anchor, EPSG:32710, latitude and longitude
  stages/      one module per stage, named as in the specification
  emit/        one writer per real source format
  errors/      error induction, one module per mechanism
  manifest/    truth manifest, and the GIS inspection export
  solve/       answer-key solver (separate; reads the true world only)
  checks/      the world checks and request checks
  cli.py       swm resolve | check-recipe | terrain | preview-terrain | layers | export-gis |
               preview-world | build | solve | check
  preview.py   face-validity previews (optional `preview` extra; not part of the identity check)
tests/
  unit/  property/  fixtures/  golden/
docs/
  design/  decisions/  trace/  work_orders/
```

- **Stages are pure functions:** `(recipe section, upstream outputs, rng) -> stage output` (a frozen dataclass). No stage reads another stage's stream. Only `emit/`, `manifest/` and `recipe/io` write files; stages never do.
- **One job per function.** A function that needs a comment to explain its sections should be split.

## 6. Style

- `ruff` for lint and format. `mypy --strict` on `src/`. Type hints everywhere.
- **Vocabulary:** names use the dissertation's words: carried run, flattened run, optimization member-class, reserve, requirement, coupling strength. Never "baseline" or "ablation". Plain words over abbreviations.
- **Units in names:** `area_km2`, `window_h`, `capacity_mw`.
- **Docstrings** (NumPy style) on every public function and class: what it does, parameters with units, what it returns, and a `Spec:` line naming the section it implements.
- **Comments say why, not what.**
- **Constants:** every constant has a name, units and a source: a citation, or `placeholder (open decision: <name>)`. No magic numbers.
- **No dead code.** No commented-out code, no TODO without a linked issue, and no print debugging left in.
- Clarity over cleverness. A reader of the dissertation should be able to follow any stage without running it.

## 7. Verification and validation

**Verification** — the code does what the specification says:

- **Unit tests** for every stage.
- **The checks from the specification** are automated tests:
  - identity;
  - realized error;
  - uniqueness;
  - quiet planting;
  - realism, from Phase 5.
- **Property tests** (`hypothesis`) for invariants:
  - the feed shares always total 100%;
  - nodes = area × density within rounding;
  - zero error reproduces the clean emission exactly;
  - the same recipe gives the same bytes;
  - changing the error seed never moves terrain or infrastructure.
- **Golden worlds.** A few fixture recipes (the pilot world, a hidden-layer world, a nodes-only world) with checked-in output hashes. A hash change must be explained in the pull request.
- **Answer keys** are found by brute force and must agree with the MIP.
- **Hand trace.** The pilot scenario traced by hand is stored as expected values, and the code must match it.
- **Tests assert behaviour, not just coverage.** Target at least 90% line coverage on `src/`, but a test that only executes lines doesn't count.

**Validation** — the world resembles what it claims to:

- realism ranges measured from the real corpus;
- face validity review by the author;
- expert review;
- docking against an independent minimal reimplementation written from the specification alone, without sight of this code.

**A failed check is reported, never silently regenerated.**

## 8. Process

- **Never push to `main`.** Every change goes on a branch for its work order and reaches `main` only by pull request. Foreman merges; nobody else does. Keep pull requests small.
- **The pull request description:**
  - what was built;
  - the specification sections;
  - the tests added;
  - every `CHOICE:`;
  - open questions.
- **CI** (GitHub Actions) runs lint, type check and tests on every push. Nothing merges while CI is failing.
- **Commit messages** are imperative and say why, and end with the attribution trailers set for the session.
- **Decision log:** `docs/decisions/NNNN-short-title.md`. Each entry gives the context, the decision, who decided, and the date. Short.
- **TRACE log:** `docs/trace/phase-N.md`, written when each phase closes. It records what was built, how it was tested, and what departed from the design.
- **Versions:** `CHANGELOG.md` and a version tag per phase (`v0.1.0` closes Phase 1). The recipe schema carries its own version. Old recipes either load or fail with a clear message.

## 9. Data

- **No real source data in the repository, ever.** Real data is reached through `machine.toml` only.
- **Synthetic identifiers** follow real code-list formats, with values from a reserved range. No real place, airport, port or wiki codes.
- **Replayed error** uses statistics measured from real sources, never real records.

## 9a. Licence

The repository carries no licence file, by the author's decision. Do not add a `LICENSE`, licence headers, or licence metadata in `pyproject.toml`. Dependencies must still be permissive open-source (MIT, BSD, Apache 2.0 or similar); flag anything else before adding it.

## 10. When to stop and ask

Stop and raise it in the report instead of proceeding when:

- the specification is silent or ambiguous on anything in §2's second bullet;
- a test from the specification can't pass without changing what it tests;
- a golden hash changes and you can't explain why;
- a dependency would need real data, network access at build time, or is not under a permissive open-source licence;
- the work order and this file disagree.

## 11. End-of-task report (fixed format)

1. **Built:** what, in two or three lines.
2. **Spec sections:** which ones this implements.
3. **Tests:** what was added, and what they prove.
4. **Choices made:** every `CHOICE:` in the code, one line each.
5. **Questions:** for the design side, numbered.
6. **Deviations:** anything that departs from the work order or the specification, and why.
7. **Next:** what the next work order should cover, as the coder sees it.
