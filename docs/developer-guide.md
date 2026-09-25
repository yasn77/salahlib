# SalahLib — Developer Guide

Architecture, build/test commands, and the executor+reviewer workflow.

## Architecture

Four tiers: shared data (`methods.json` / `SPEC.md`) → pure kernel → method backends → language facade.
The kernel is a pure function of numbers/enums; it never sees method names, dates, or timezone strings.

## Task runner

Tasks are defined in `.mise.toml`: `mise run test`, `mise run parity`, `mise run ci`, etc.

## Executor + reviewer loop

Implementation follows `EXECUTION_PLAN.md` and `TASKS.md`. The executor applies self-contained text
transforms in a fresh context; the reviewer runs the acceptance commands and each phase's exit criteria.

## Cross-language float parity

`tests/parity.py` runs each language's dump CLI on shared inputs and asserts ≤1e-9 h agreement (≈3.6 µs).

```sh
mise run parity
```

## CI

`mise run ci` = `test` (all four languages) + `parity` + `lint`. Golden vectors are committed; regeneration
is manual (`mise run gen-fixtures`) and must never run in CI.

## Releasing

Tag each language `python/vX.Y.Z`, `go/vX.Y.Z`, `typescript/vX.Y.Z`, `c/vX.Y.Z`; keep semver in sync.

<!-- NEXT -->