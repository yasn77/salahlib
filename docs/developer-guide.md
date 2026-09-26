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
  vectors/                 #   committed fixtures: aladhan/, lut/, parity_inputs.json
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

`shared/vectors/` holds three kinds of committed fixture: two **accuracy oracles** (the blackbox tests) and
one **consistency input** (the parity harness).

### `aladhan/` — the AlAdhan accuracy oracle

Eight `*.json` files, each the full AlAdhan API response `data` object (`{timings, date, meta}`), fetched once
by `scripts/generate_fixtures.py` and committed:

| File | Method (id) | Location · date | What it pins |
|---|---|---|---|
| `london_isna.json` | ISNA (2) | London · 2014-04-24 | baseline timings |
| `london_mwl.json` | MWL (3) | London · 2014-04-24 | 18°/17° angles |
| `makkah.json` | Umm al-Qura (4) | Makkah · 2024-02-20 | Isha = Maghrib +90 min |
| `makkah_ramadan.json` | Umm al-Qura (4) | Makkah · 2024-03-11 | Ramadan Isha = Maghrib +120 min (`ramadanTune` +30) |
| `ankara_turkey.json` | Diyanet (13) | Ankara · 2024-04-24 | `"90 min"` Isha string + default tune |
| `sydney_south.json` | MWL (3) | Sydney · 2024-06-20 | southern-hemisphere sign handling |
| `high_lat_65n.json` | MWL (3) | 65°N · 2024-06-20 | unreached-angle clamp |
| `london_moonsighting.json` | Moonsighting (15) | London · 2024-10-15 | DY-day table + `shafaq` |

Each language has a blackbox test that loads these and asserts **string-equality** with its own facade
output — except Asr, which is allowed ±1 minute (the API's Asr is server-clock-dependent).

### `lut/lut.json` — the London Unified regional oracle

`LUT` is not an AlAdhan method, so it has no `aladhan/` vector. Its oracle is `lut.json`, a small table of
published [londonsalahtimes.com](https://londonsalahtimes.com/technical/) times with the shape
`{name, latitude, longitude, timezone, note, cases: [{date, timings}]}`. Tolerances are wider than the
AlAdhan oracle (the published timetable uses Meeus solar and a refined Hizbul-Ulama chart): Sunrise, Dhuhr,
Sunset and Maghrib match exactly; Asr ±3 min; Fajr/Isha ±5 min.

### `parity_inputs.json` — the cross-language consistency input

Unlike the two oracles above, this file is **not** a golden vector. It is the input set for `tests/parity.py`:
eight fully-resolved kernel cases (`schema_version: 2`, `tolerance_hours: 1e-9`), each a numeric `date` plus
`latitude`/`longitude`/`elevation` plus a resolved `params` object (no method names, no timezone strings, no
date objects). Each case targets one SPEC edge:

- `london_isna_2014` — ISNA baseline.
- `high_lat_asr_canary` — the Asr Julian-epoch canary (SPEC §13.2).
- `not_reached_mwl_65n_june` — Fajr/Isha angle not reached → clamp (SPEC §13.1).
- `makkah_90min_isha` — Isha as minutes (`"90 min"` flag).
- `tehran_jafari_midnight` — JAFARI midnight, `NONE` high-lat handling.
- `sydney_south_hanafi` — southern hemisphere + Hanafi Asr factor 2.
- `equator_zero_elevation` — degenerate-path coverage.
- `elevation_nonzero` — horizon-dip term (SPEC §6.5).

`tests/parity.py` runs each language's `dump` CLI over this file and asserts the four kernels agree to
≤1e-9 h (≈3.6 µs).

**Never regenerate the committed vectors in CI** — `mise run gen-fixtures` is a manual, network task used only
when AlAdhan behaviour changes.

## CI & releasing

- CI (`.github/workflows/ci.yml`) runs `mise run ci` on every push.
- Tag each language with its own prefix — `python/vX.Y.Z`, `go/vX.Y.Z`, `typescript/vX.Y.Z`, `c/vX.Y.Z` — and
  keep semver in sync.

## Licensing / provenance

Apache-2.0. The kernel is derived from PrayTimes v3 (MIT) + the public-domain USNO "Sun Approx" formula +
published method data + black-box AlAdhan observation. See `THIRD-PARTY-NOTICES.md` and `NOTICE`.
Do not vendor or port from GPL sources.
