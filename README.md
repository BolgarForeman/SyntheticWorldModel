# SyntheticWorldModel

A generator of constructed worlds for the MCIN dissertation: synthetic six-layer interdependent infrastructure systems on synthetic terrain, emitted as source files in the real structure of real sources, with a truth manifest. A separate solver computes answer keys on each world, so an analysis run on the emitted sources can be scored against a known optimum.

## Install

Install [uv](https://docs.astral.sh/uv/), then from the repository root:

```
uv sync
```

This installs Python 3.12 if needed, and the locked runtime and development dependencies. The terrain preview (`swm preview-terrain`) also needs matplotlib, in the optional `preview` group:

```
uv sync --extra preview
```

## Run the checks

```
uv run ruff check
uv run ruff format --check
uv run mypy src
uv run pytest
```

CI runs the same checks, with the `preview` extra installed, on Linux and Windows for every pull request and every push to `main`.

## Where things are

- `docs/design/`: the specification the code is built against. Start with `docs/design/README.md`.
- `CLAUDE.md`: the rules for working in this repository.
- `docs/decisions/`: the decision log.
- `docs/trace/`: the TRACE log, one entry per phase.
- `docs/work_orders/`: the work orders, as issued.
- `machine.example.toml`: copy to `machine.toml` to set where real source data lives on this machine.
