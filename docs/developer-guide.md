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

<!-- NEXT -->