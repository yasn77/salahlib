# SalahLib — Developer Guide

How the project is structured, how to build and test it, and the invariants you must not break.

## Architecture

Four tiers, and one hard invariant:

1. **Shared data** — `shared/methods.json` (the factual method registry) and `shared/SPEC.md` (the formulas
   and the "target-behaviour register").
2. **Pure kernel** — `calculate(date, lat, lng, elevation, params)` → float hours. **No I/O, no date objects,
   no timezone strings, no method names.** It is identical in all four languages.
3. **Method resolution** — maps a method name/id → a resolved `Params` (parses `"90 min"`, `"JAFARI"`,
   `shafaq`, and per-method `defaultTune`/`ramadanTune`).
4. **Facade** — idiomatic public API, timezone/DST handling, output formatting (`24h`, `12h`, `12hNS`,
   `Float`, `iso8601`), and the AlAdhan `{timings, meta}` envelope.

**The kernel is the contract.** Any change to a kernel in one language must be mirrored in the other three.

## Repository layout

```
shared/                    # single source of truth
  methods.json             #   the method registry (24 methods + CUSTOM + LUT)
  methods.schema.json      #   JSON Schema
  SPEC.md                  #   the calculation spec + target-behaviour register
  vectors/                 #   committed golden vectors (aladhan/, lut/)
langs/                     # one directory per language implementation
  python/prayer_times/     #   Python package (kernel + facade)
  go/pkg/prayertimes/      #   Go package (module github.com/yasn77/salahlib/langs/go)
  typescript/src/          #   TypeScript (kernel + facade)
  c/                       #   C static library (kernel + method resolution)
scripts/                   # fixture generator, data sync, C-header generator
tests/parity.py            # cross-language float-parity harness
docs/                      # user-guide.md, developer-guide.md
.github/workflows/ci.yml   # GitHub Actions (mise run ci)
```

## Getting started

```sh
mise install        # install the pinned toolchains (python, go, node, uv, bun, cmake)
mise run ci         # test (4 languages) + parity + lint, sequentially
```

Useful tasks: `mise run test` (the four suites), `mise run parity` (float parity), `mise run lint`
(`ruff` + `gofmt` + `tsc`), `mise run sync-data` (fan out `methods.json`), `mise run gen-fixtures`
(manual — fetch golden vectors from AlAdhan).

## The kernel contract

- **Float-identical across languages** (≤1e-9 h). `tests/parity.py` runs each language's `dump` CLI on the
  same inputs and asserts agreement. Run it after any kernel change.
- **Do not "fix" the quirks** in `SPEC.md`'s target-behaviour register — they are *observed AlAdhan
  behaviours* that must be reproduced:
  - **Asr** samples declination one day ahead (`julian_day + 1.0`, no meridian correction).
  - **Unreached-angle clamp** (`unreached_policy = CLAMP`, default) vs `NAN` for composite methods.
  - **Moonsighting** is a DY-day table applied *after* night-times and *before* offsets.
  - **Maghrib defaults to `"0 min"`** (not an angle of 0), so Maghrib == Sunset for methods without a Maghrib
    param.
  - **MAKKAH Ramadan rule** — Isha = Maghrib +120 min during Ramadan, gated by `is_ramadan`.
  - **Rounding** is round-half-away-from-zero (Python's `round()` is half-even — use `round_away`), and the
    time formatter uses `floor(t + 0.5/60)`.

## `methods.json` — the single source of truth

- Edit `shared/methods.json` (respecting `methods.schema.json`) to add or change a method, then:
  - `mise run sync-data` — copies it into `langs/python/…/data/`, `langs/go/…/`, `langs/typescript/src/`.
  - rebuild C — `langs/c/CMakeLists.txt` regenerates `langs/c/include/methods_generated.h` at build time.
- **Composition via `extends`.** A method may declare `"extends": "BASE"` to inherit the base method's
  `params` (e.g. `LUT` extends `MOONSIGHTING`, inheriting `shafaq: "general"`). This is an *authoring*
  convenience: `sync-data` and `generate_c_methods.py` flatten it into resolved `params` at fan-out time, so
  the language resolvers never see it.
- Per-method `defaultTune` (applied, visible in `meta.offset`) and `ramadanTune` (conditional, gated by
  `is_ramadan`) hold minute offsets.

## Adding a new method

1. Add it to `shared/methods.json` (or `extends` an existing base).
2. Run `mise run sync-data` and rebuild C.
3. If it's an AlAdhan method, add it to `scripts/generate_fixtures.py` and regenerate the golden vectors
   (manual). If it's a regional method, add a fixture under `shared/vectors/`.
4. Add a test in each language; confirm `mise run ci` is green.

## Adding a new language

1. Implement the kernel 1:1 with `SPEC.md` (a `Params` equivalent, the pure `calculate`, `format_time`).
2. Implement method resolution (reading the fanned-out `methods.json`).
3. Implement the facade (`get_times`/`to_aladhan_response` equivalents).
4. Add a `dump` CLI and wire it into `tests/parity.py` and `.mise.toml`.
5. Add a directory under `langs/`.

## Testing

- **Golden vectors** — `shared/vectors/aladhan/*.json` (AlAdhan) and `shared/vectors/lut/lut.json` (London
  Unified) are **committed** and are the accuracy oracle. Each language has a blackbox test that reads them.
  **Never regenerate them in CI** — `mise run gen-fixtures` is a manual, network task.
- **Cross-language float parity** — `tests/parity.py` asserts the four kernels agree to ≤1e-9 h.

## CI & releasing

- CI (`.github/workflows/ci.yml`) runs `mise run ci` on every push.
- Tag each language with its own prefix — `python/vX.Y.Z`, `go/vX.Y.Z`, `typescript/vX.Y.Z`, `c/vX.Y.Z` — and
  keep semver in sync.

## Licensing / provenance

Apache-2.0. The kernel is derived from PrayTimes v3 (MIT) + the public-domain USNO "Sun Approx" formula +
published method data + black-box AlAdhan observation. See `PROVENANCE.md`, `CLEANROOM.md`,
`THIRD-PARTY-NOTICES.md` and `NOTICE`. Do not vendor or port from GPL sources.
