# 0002 — Scaffold review

- **Date:** 2026-09-28
- **Decided by:** Foreman, with the design conversation
- **Recorded by:** Work Order 1

## Context

The report on Work Order 0 (pull request #1) raised three questions about the scaffold. A fourth ruling, on how much of the recipe schema v1 covers, was made at the same review.

## Decisions

1. **The `CLAUDE.md` title stays as it is.**
2. **`docs/work_orders/` joins the layout** in `CLAUDE.md` §5.
3. **The 90% coverage floor stays enforced in CI.**
4. **The v1 recipe schema covers the full recipe.** Features from later phases are accepted in a recipe and refused at build time, naming the phase they arrive in (ruling (a) of 2026-09-28).
