# AGENTS.md

Guidance for AI coding agents (and humans) working in this repository.

## What this is

SalahLib is a **multi-language Islamic prayer-times library** — the same calculation, implemented in
**Python, Go, TypeScript and C**, validated for **output parity with the AlAdhan API**
(`https://aladhan.com/prayer-times-api`). The mathematics and the list of calculation methods are defined
once in `shared/` and shared across every language.

## Repository layout

```
shared/
  methods.json             # SINGLE SOURCE OF TRUTH for calculation methods
  methods.schema.json      # JSON Schema for methods.json
  SPEC.md                  # the calculation spec (incl. the "target-behaviour register")
  vectors/aladhan/*.json   # committed golden vectors fetched from AlAdhan
python/prayer_times/       # Python package (kernel + facade)
go/pkg/prayertimes/        # Go package (kernel + facade; module github.com/yasn77/salahlib/go)
typescript/src/            # TypeScript (kernel + facade)
c/                         # C static library + dump CLI (kernel + method resolution)
scripts/                   # fixture generator, data sync, C-header generator
tests/parity.py            # cross-language float-parity harness
```

## Architecture

Four tiers, and a hard invariant:

1. **Shared data** — `methods.json` (factual method registry) + `SPEC.md` (the formulas).
2. **Pure kernel** — `calculate(date, lat, lng, elevation, params)` → float hours. **No I/O, no dates, no
   timezone strings, no method names.** It is identical in all four languages.
3. **Method resolution** — maps a method name/id → a resolved `Params` (parses `"90 min"`, `"JAFARI"`,
   `shafaq`, per-method `defaultTune`/`ramadanTune`).
4. **Facade** — idiomatic public API, timezone/DST handling, output formatting (`24h`, `12h`, `12hNS`,
   `Float`, `iso8601`), and the AlAdhan `{timings, meta}` envelope.

**The kernel is the contract.** Any change to a kernel in one language must be mirrored in the other three.

## How to build and test

Tooling is managed by [mise](https://mise.jdx.dev) (`.mise.toml`):

```sh
mise install        # install pinned toolchains (python, go, node, uv, bun, cmake)
mise run ci         # test (4 languages) + parity + lint, sequentially
mise run test       # run the four language test suites
mise run parity     # assert all four kernels agree to ≤1e-9 hours
mise run lint       # ruff (py) + gofmt + tsc --noEmit
```

CI runs `mise run ci` on every push (`.github/workflows/ci.yml`).

## Critical invariants — do NOT break these

- **`methods.json` is the single source of truth.** To add or change a calculation method, edit
  `shared/methods.json`, then:
  - `mise run sync-data` → copies it into `python/…/data/`, `go/…/`, `typescript/src/`.
  - rebuild C → `c/CMakeLists.txt` regenerates `c/include/methods_generated.h` at build time.
- **Composition via `extends`.** A method may declare `"extends": "BASE"` to inherit the base method's
  `params` (e.g. `LUT` extends `MOONSIGHTING`, inheriting `shafaq: "general"`). This is an *authoring*
  convenience: `sync-data` and `generate_c_methods.py` flatten `extends` into fully-resolved `params` at
  fan-out time, so the language resolvers never see it.
- **The kernels must stay float-identical** (≤1e-9 h). After any kernel change, run `mise run parity`.
- **Do not "fix" the quirks** in `SPEC.md`'s target-behaviour register. These are *observed AlAdhan
  behaviours* that must be reproduced, notably:
  - **Asr** samples declination one day ahead (`julian_day + 1.0`, no meridian correction).
  - **Unreached-angle clamp** (`unreached_policy = CLAMP`, default) vs `NAN` for composite methods.
  - **Moonsighting** is a DY-day table applied *after* night-times and *before* offsets.
  - **Maghrib defaults to `"0 min"`** (not an angle of 0) — so Maghrib == Sunset for methods without a
    Maghrib param.
  - **MAKKAH Ramadan rule** — Isha = Maghrib +120 min during Ramadan, gated by `is_ramadan`.
  - **Rounding** is `round-half-away-from-zero` (Python's `round()` is half-even — use `round_away`), and
    the time formatter uses `floor(t + 0.5/60)`.

## Golden vectors & black-box testing

- `shared/vectors/aladhan/*.json` are **committed** and are the accuracy oracle (string-equality, with Asr
  within ±1 min — the API's Asr is server-clock-dependent).
- **Never regenerate them in CI.** `mise run gen-fixtures` is a manual task (network) used only when AlAdhan
  behaviour changes.

## Adding a new language or method

- **New method**: edit `shared/methods.json` (respect `methods.schema.json`), run `mise run sync-data`, add
  it to the fixture generator, regenerate fixtures, and confirm all four languages pass.
- **New language**: implement the kernel (1:1 with `SPEC.md`), a `Params` equivalent, method resolution, a
  facade, and a parity `dump` CLI; wire it into `tests/parity.py` and `.mise.toml`.

## Licensing / provenance

Apache-2.0. The kernel is derived from PrayTimes v3 (MIT) + the public-domain USNO "Sun Approx" formula +
published method data + black-box AlAdhan observation. See `PROVENANCE.md`, `CLEANROOM.md`,
`THIRD-PARTY-NOTICES.md` and `NOTICE`. Do not vendor or port from GPL sources.
