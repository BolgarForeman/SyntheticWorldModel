# 0001 — Foundations

- **Date:** 2026-09-28
- **Decided by:** Foreman, with the design conversation
- **Recorded by:** Work Order 0

## Context

Before any generator code, the build needed its foundations fixed: the language, the recipe contract, the build order, how buffers are treated until their typology is ruled on, licensing, how changes reach `main`, where development and CI run, and how the generator relates to the analysis pipeline. See `docs/design/Build_Game_Plan.md` §2 and `docs/design/World_Generator_Structure.md` §10.

## Decisions

1. **Language is Python.**
2. **The recipe schema is a typed pydantic schema, versioned from the start.** Old recipes either load or fail with a clear message.
3. **The engine is built first.** The interface is a later front end that writes recipes. The recipe file is the contract between them.
4. **Buffers are stock-only for now.** Every buffer is a reserve, and buffer time = reserve ÷ draw, computed in the run. This holds until the buffer typology ruling (structure §10, item 7).
5. **No licence file,** by the author's decision (`CLAUDE.md` §9a).
6. **Foreman merges every pull request.** Nothing reaches `main` except by pull request.
7. **Development runs locally on Foreman's Windows laptop; CI checks Windows and Linux.**
8. **The analysis pipeline lives in its own repository.** The generator and the pipeline share nothing but files on disk: the generator's emitted sources, truth manifest and answer keys.
