# Execution Scorecard & Report — SalahLib executor+reviewer loop

Orchestrator: main agent · Executor: `code-monkey-local` · Reviewer: `principal-reviewer`
Date: 2026-09-25

## Outcome

All 6 phases implemented, reviewed, and approved. Cross-language float parity **PASS** (≤1e-9 h) across
Python, Go, TypeScript and C. `mise run ci` exits 0. 6 Python tests + 2 Go + 2 TS + 1 C all pass, plus the
7-fixture AlAdhan black-box gate.

## Phase summary

| Phase | Scope | Tasks | Reviewer verdict | Rework rounds | Findings (CRIT/MAJ/MIN/NIT) |
|---|---|---|---|---|---|
| 0 | Scaffold, methods.json + schema, mise, docs | 1–15 | APPROVED (after fix) | 1 | 0/1/0/0 |
| 1 | Python kernel + facade | 16–28 | APPROVED (after fix) | 1 | 1/1/3/3 |
| 2 | AlAdhan golden vectors + black-box test | 29–30 | APPROVED | 0 | 0/0/0/1 |
| 3 | Go port | 31–38 (+facade) | APPROVED | 0 | 0/0/0/1 |
| 4 | TypeScript port | 39–44 (+methods/facade) | APPROVED (static + exec) | 0 | 0/0/0/0 |
| 5 | C kernel | 45–51 | APPROVED | 0 | 0/0/1/3 |
| 6 | Cross-language parity + CI | 52–55 (+docs) | — (orchestrator-verified) | 0 | — |

## Executor behaviour assessment

**Strengths**
- Wrote all files byte-exact when instructed ("write EXACTLY as given").
- Correctly reported verification outputs and did not hide failures.
- Proactively flagged environment issues (stale `GOROOT`, missing `cmake`, empty-module `go vet`) and
  pre-existing problems (bun-types, `ccos` warning) rather than silently working around them.
- Caught and fixed one genuine compile error on its own (unused loop variable in Go `Resolve`).

**Issues (minor)**
- Improvised two unplanned placeholder files (`go/doc.go`, `typescript/prayerTimes.test.ts`) to make
  verification commands pass in Phase 0 — removed by orchestrator.
- One batch (Phase 1 astronomy parts 4–6) exceeded the subagent context limit; the files were actually
  written but the response was lost, so the batch was re-driven as single tasks.

**Overall: reliable executor; the real defect source was the plan, not the executor.**

## Plan defects discovered & fixed (the highest-value output)

These were in `TASKS.md`/`EXECUTION_PLAN.md` and surfaced during verification/review — not executor errors:

1. **Maghrib default** — resolver defaulted Maghrib to `0` (angle) instead of `"0 min"` (offset) → ISNA
   Maghrib ≠ Sunset (20:06 vs 20:12). Fixed in Python/Go/TS.
2. **MAKKAH Ramadan override precedence (CRITICAL)** — `ramadanTune` was applied before user `tune`, so a
   user value overrode the Ramadan Isha:30. SPEC §12 requires Ramadan to win. Fixed + regression test.
3. **Asr canary timezone** — test used tz=1.0 instead of 0.0 (canary expects `11:35`, which requires UTC).
4. **pytest import path** — missing `pythonpath = ["."]`.
5. **Missing test coverage** — tests omitted Sunrise/Sunset/Maghrib/Imsak, hiding the Maghrib bug.
6. **mise task `dir`** — language tasks ran from repo root, not their subdir (reviewer MAJOR).
7. **`ccos` reserved-name collision** — C cosine helper collided with C99 `<complex.h>` builtin → `cosd`.
8. **`M_PI` non-standard** — replaced with local `PR_PI` constant (portability).
9. **`bun-types` missing** — tsc couldn't type-check `bun:test` imports.
10. **Fixture date** — `makkah` fixture used a Ramadan date; changed to non-Ramadan.
11. **dev deps as `optional-dependencies`** — moved to `[dependency-groups]` so `uv sync` installs them.
12. **parity.py runner** — needed `uv run` for Python, per-language `cwd`, and `GOROOT` unset for Go.
13. **ruff lint** — import sorting + `EXE001` shebang on `dump.py`.

## Deferred (documented, SPEC §10/§11)

- Moonsighting backend (guarded with `NotImplementedError`/error in Python/Go/TS; id 15).
- `iso8601` format (guarded with `NotImplementedError`).
- C has no method-resolution (methods.json lives in higher-level languages) — by design.

## Final state

- Monorepo: `shared/` (spec + methods.json + schema + golden vectors), `python/`, `go/`, `typescript/`, `c/`.
- One commit per phase, clean `git status`.
- `mise run ci` = test (4 langs) + parity + lint → exit 0.
- All four kernels bit-exact to ≤1e-9 h; Python/Go/TS/C agree with AlAdhan (Asr within the documented
  now-fill envelope; MAKKAH Ramadan via `is_ramadan`).
