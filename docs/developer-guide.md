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
  python/salahlib/         #   Python package (kernel + facade)
  go/pkg/prayertimes/      #   Go package (module github.com/yasn77/salahlib/langs/go)
  typescript/src/          #   TypeScript (kernel + facade)
  c/                       #   C static library (kernel + method resolution)
scripts/                   # fixture generator, data sync, C-header generator
tests/parity.py            # cross-language float-parity harness
docs/                      # user-guide.md, developer-guide.md
.github/workflows/       # ci.yml + per-language release-*..yml (tag-triggered)
```

## Getting started

```sh
mise install        # install the pinned toolchains (python, go, node, uv, bun, cmake)
mise run ci         # test (4 languages) + parity + lint, sequentially
```

Useful tasks: `mise run test` (the four suites), `mise run parity` (float parity), `mise run lint`
(`ruff` + `gofmt` + `tsc`), `mise run check-sync` (generated data in sync), `mise run sync-data` (fan out
`methods.json`), `mise run bump` (set a language's version), `mise run gen-fixtures` (manual — fetch
golden vectors from AlAdhan).

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
  - `mise run sync-data` — fans it out to `langs/python/salahlib/data/methods.json`,
    `langs/go/pkg/prayertimes/methods.json`, and `langs/typescript/src/methods.generated.ts` (a generated
    TS module, so the build output is runtime-valid ESM).
  - rebuild C — `langs/c/CMakeLists.txt` regenerates `langs/c/include/methods_generated.h` at build time.
  - `mise run check-sync` — fails if any of those generated files is stale (wired into `mise run ci`).
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
4. Add a `dump` CLI and wire it into `tests/parity.py` and `mise.toml`.
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
- Each language releases independently under its own tag prefix:

  | Tag | Workflow | Publishes to |
  |---|---|---|
  | `python/vX.Y.Z` | `release-python.yml` | PyPI (`salahlib`) + GitHub Release |
  | `typescript/vX.Y.Z` | `release-typescript.yml` | npm (`salahlib`) + GitHub Release |
  | `langs/go/vX.Y.Z` | `release-go.yml` | the Go module proxy (tag-only) + GitHub Release |
  | `c/vX.Y.Z` | `release-c.yml` | GitHub Release (static-lib + source tarballs) |

  (The Go tag prefix **must** be the submodule's path, `langs/go/`, for
  `proxy.golang.org` to serve it.)

- **When `shared/` changes, all four languages need a release** (the fanned-out
  `methods.json` lives in every language tree). A change under one `langs/<x>/` is an
  independent release of that language only. Keep the four versions in sync when a
  `shared/` change forces everyone to move.

### Release procedure

1. Set the declared version: `mise run bump python 1.2.0` (python/typescript/c write it
   into `pyproject.toml` + `__init__.py`, `package.json`, `CMakeLists.txt`; Go has no
   version file — its version is the tag alone, so `bump go` is a no-op).
2. Commit, tag, push: `git tag python/v1.2.0 && git push origin python/v1.2.0`.
3. The matching workflow runs its guards (tag == declared version; npm also checks the
   version isn't already on the registry), then the **full `mise run ci`** (four test
   suites + parity + lint), then builds, smoke-tests the artifact, publishes via **OIDC
   trusted publishing** (no long-lived tokens), and files a GitHub Release.

### One-time registry setup (trusted publishing)

Both registries authenticate with the workflow's GitHub OIDC identity — no secrets.

- **Repository visibility is part of the security model**: npm generates provenance **only for
  publishes from a public repository** (npm verifies the signing certificate's
  repository-visibility extension; a provenanced publish from a private repo is rejected), and
  `proxy.golang.org` can only serve a public repo. PyPI works either way. Keep the repo public
  before releasing TypeScript or Go.
- **PyPI** (`salahlib`): done — a *pending* trusted publisher (account → Publishing → GitHub
  Actions: `yasn77` / `salahlib` / `release-python.yml` / environment `pypi` / project
  `salahlib`) **created the project on first CI publish** and was promoted to a normal publisher.
  No manual first upload is ever needed on PyPI.
- **npm** (`salahlib`): trusted publishing cannot create a package, so 0.1.0 was bootstrapped
  once manually (`bun run build && npm publish --no-provenance` — the flag is needed because a
  workstation has no OIDC identity for `publishConfig.provenance`; `Automatic provenance
  generation not supported for provider: null`). Trusted publisher registered (owner `yasn77`,
  repository `salahlib`, workflow `release-typescript.yml`, environment `npm`, permission
  `publish`) — done from the CLI with `npm trust github salahlib --repo yasn77/salahlib
  --file release-typescript.yml --env npm --allow-publish`; the first call demands web 2FA:
  run it under a TTY (`script -qec "…" /dev/null`), open the printed
  `npmjs.com/auth/cli/…` URL in a logged-in browser, and the CLI completes the registration.
  All later versions publish from CI with provenance attached automatically
  (`npm audit signatures` verifies it).
- GitHub **environments** `pypi` and `npm` exist; optionally add required-reviewer protection
  for a manual approval gate.

- **Never regenerate the golden vectors in CI**, and never hand-edit the fanned-out
  method data (`langs/python/salahlib/data/methods.json`, `langs/go/pkg/prayertimes/methods.json`,
  `langs/typescript/src/methods.generated.ts`) — edit `shared/methods.json` and run
  `mise run sync-data`.

## Licensing / provenance

Apache-2.0. The kernel is derived from PrayTimes v3 (MIT) + the public-domain USNO "Sun Approx" formula +
published method data + black-box AlAdhan observation. See `THIRD-PARTY-NOTICES.md` and `NOTICE`.
Do not vendor or port from GPL sources.
