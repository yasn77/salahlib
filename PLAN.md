# Plan — SalahLib

Detailed implementation plan. **Reference `RESEARCH.md` for the "why"; this document is the "what/how".**

> **Status:** updated after three independent reviews (KIM3, OPUS5, GLM5-3). The review's core correction is
> embedded throughout: **the parity target is a fork of the PHP library, not the released package**, so the
> plan defines a single parity target (AlAdhan) and a target-behaviour register (§5). See RESEARCH.md §1.1 and §4.8.

---

## 1. Goals & scope

- Multi-language library for Islamic prayer times: **Python, Go, TypeScript**, extensible to more.
- **Separate maths from inputs**: the kernel is a pure function of numbers/enums only.
- **Accuracy target**: full output parity (`timings` + `meta`) with the
  [AlAdhan API](https://aladhan.com/prayer-times-api).
- **Method coverage**: all 23 named methods + `CUSTOM` + Moonsighting, **+ a composite/seasonal capability
  (`LFC` shipped `experimental`)**.
- **Out of scope**: Hijri/Gregorian calendar conversion. **Exception:** a minimal `is_ramadan` facade hint
  (see below), because the Umm al-Qura Ramadan rule (RESEARCH §4.8) makes full `MAKKAH` parity otherwise
  impossible.

### 1.1 Parity target

AlAdhan runs a fork of the PHP library. SalahLib targets **AlAdhan's behaviour** directly (there is no separate
"reproduce the released package" profile — that was dropped in the v2 review as low-value, since its ground
truth is only observable by running the GPL package):

- Per-method **default tune** (TURKEY/DUBAI/MOROCCO/PORTUGAL) — applied, **visible in `meta.offset`**.
- MAKKAH Ramadan rule — Isha +120 min in Ramadan, gated by the **`is_ramadan: bool = False`** facade hint
  (default `False`; the caller must pass it for MAKKAH Ramadan parity).
- Midnight mode defaults to STANDARD (AlAdhan overrides any method `Midnight: JAFARI`).
- Moonsighting `dyy` = PHP semantics (server-clock-dependent on the live API — see SPEC §13.10).

### 1.2 Licensing — decided: Apache-2.0, kernel from PrayTimes v3 (MIT)

Upstream is GPL-3.0-or-later (PHP) / LGPL-3.0 (PrayTimes.js v2). A line-annotated 1:1 port is a **derivative
work**, so a permissive release requires not porting from GPL code. Two facts make that clean:

1. **PrayTimes v3.0+ (`zarrabi/praytime`) is MIT** — the author relicensed the algorithm from LGPL-3.0 to MIT
   on 2025-03-25, so the kernel mathematics can be sourced from MIT code.
2. The **USNO "Sun Approx" formula is public domain** (US federal government work).

**Therefore:** SalahLib is licensed **Apache-2.0**. `SPEC.md` is derived from PrayTimes v3 (MIT) + the
public-domain USNO formula + the published method data (facts); every AlAdhan-specific behaviour is derived
black-box and recorded in SPEC §13 with its evidence. GPL sources are not vendored and not a porting source.
See PROVENANCE.md, CLEANROOM.md, THIRD-PARTY-NOTICES.md and RESEARCH.md §2.3.

---

## 2. Architecture

Four tiers, split at the seams identified in research:

```
┌─────────────────────────────────────────────────────────────────┐
│ Tier 3 — Facade (per language, idiomatic)                        │
│   method name/id → Params; date/tz → julianDay + tzOffset;        │
│   output formatting; getMeta(); toAlAdhanResponse(); is_ramadan    │
│   toAlAdhanResponse(); is_ramadan hint; midnight-mode policy       │
├─────────────────────────────────────────────────────────────────┤
│ Tier 2 — Method backends (pluggable)                              │
│   AngleBased (default) · Moonsighting · Composite (LFC, experim.) │
├─────────────────────────────────────────────────────────────────┤
│ Tier 1 — Astronomy kernel (pure, identical across languages)      │
│   Solar model strategy: SunApprox (v1) | Meeus | NREL SPA (v2)    │
│   julianDate · sunPosition · midDay · sunAngleTime(+reached) ·      │
│   asrTime · riseSetAngle · adjustTimes · adjustHighLatitudes …    │
├─────────────────────────────────────────────────────────────────┤
│ Tier 0 — Shared data (language-agnostic, single source of truth)  │
│   methods.json · methods.schema.json · SPEC.md · vectors/         │
└─────────────────────────────────────────────────────────────────┘
```

**The abstraction seam (core requirement):** `Params` — a fully-resolved, string-free input model. The kernel
consumes only `Params` + numeric coordinates + a Julian day. It never sees method names, date objects, timezone
strings, or `"90 min"` literals.

**Two extension seams (interfaces), designed now:**

1. **Solar model** — `declination(jd)` + `equationOfTime(jd)`. **Contract:** `equationOfTime` is normalised to
   (−12, +12] hours (RESEARCH §4.1 caveat). `SunApprox` (v1) · `Meeus` · `NREL SPA` (v2).
2. **Method backend** — `AngleBased` (v1) · `Moonsighting` (v1) · `Composite` (v1, `LFC` experimental).

---

## 3. Repository layout (monorepo)

```
salahlib/
├── .mise.toml                    # tool pins + tasks (§8)
├── .gitignore
├── LICENSE                       # Apache-2.0
├── NOTICE                        # provenance + attribution
├── PROVENANCE.md                 # honest source-of-truth record
├── CLEANROOM.md                  # the wall + originality check
├── THIRD-PARTY-NOTICES.md        # PrayTimes v3 (MIT) + adhan (MIT) notices
├── RESEARCH.md                   # analysis-side artifact (NOT an implementation source)
├── PLAN.md
├── shared/
│   ├── methods.json              # 23 methods + CUSTOM: params + location + defaultTune + composite rules (§4)
│   ├── methods.schema.json       # JSON Schema for methods.json (validated by every language)
│   ├── SPEC.md                   # kernel mathematics + target-behaviour register (from PrayTimes v3 MIT + USNO)
│   └── vectors/
│       ├── aladhan/*.json        # golden vectors fetched from AlAdhan (COMMITTED — §9)
│       ├── legacy/*.json         # expected test values (factual outputs) from published tests
│       ├── lfc/*.json            # hand-transcribed LFC PDF values (experimental)
│       └── parity_inputs.json    # deterministic kernel inputs for cross-language float parity
├── scripts/
│   ├── generate_fixtures.py      # hits AlAdhan; MANUAL / scheduled drift job — NOT in CI (§8)
│   └── sync_data.py              # copies methods.json into each language tree (§8)
├── python/
│   ├── pyproject.toml            # uv; runtime deps = none; dev = pytest, ruff
│   ├── prayer_times/
│   │   ├── __init__.py
│   │   ├── params.py             # Params + enums (§4.3)
│   │   ├── methods.py            # load methods.json → Params; "90 min" parsing; composite rules
│   │   ├── astronomy.py          # kernel (§5) — SunApprox solar model
│   │   ├── facade.py             # PrayerTimes, getMeta(), to_aladhan_response(), is_ramadan hint
│   │   ├── data/methods.json     # synced copy (committed) for wheel packaging
│   │   └── plugins/
│   │       ├── __init__.py       # MethodBackend + SolarModel protocols
│   │       ├── moonsighting.py   # DY-day kernel (§7.1)
│   │       └── composite.py      # date-window/fallback rule engine (§7.2)
│   └── tests/                    # test_kernel, test_legacy, test_aladhan, test_parity_data, test_lfc
├── go/
│   ├── go.mod                    # module path TBD (§11 decision 7)
│   └── pkg/prayertimes/
│       ├── params.go  methods.go  astronomy.go  facade.go  aladhan.go
│       ├── methods.json          # synced copy (committed) for go:embed
│       └── moonsighting/  composite/
├── typescript/
│   ├── package.json  tsconfig.json
│   └── src/
│       ├── index.ts  params.ts  methods.ts  astronomy.ts  facade.ts  aladhan.ts
│       ├── methods.json          # synced copy (committed) for npm packaging
│       └── plugins/{moonsighting.ts, composite.ts}
└── tests/
    └── parity.py                 # runs 3 dump-CLIs, asserts float equality ≤1e-9 (§9.3)
```

**Data distribution** (review correction): `shared/methods.json` is the *authoritative* copy, but `go:embed`,
Python wheels and npm `files` cannot reference `shared/` at publish time. `scripts/sync_data.py` copies it into
each language tree; the copies are **committed**, and a CI check fails if they are stale (checksum vs `shared/`).

---

## 4. Shared data schemas

### 4.1 `methods.json`

Mirrors the PHP registry exactly (ids match AlAdhan), **plus** the per-method `location` block and the AlAdhan
fork offsets. `params` values may be numbers, `"N min"` strings, `"JAFARI"` (midnight), or `"shafaq"`.

```json
{
  "ISNA": { "id": 2, "name": "Islamic Society of North America (ISNA)",
            "params": { "Fajr": 15, "Isha": 15 },
            "location": { "latitude": 39.70421229999999, "longitude": -86.39943869999999 } },
  "MAKKAH": { "id": 4, "name": "Umm Al-Qura University, Makkah",
              "params": { "Fajr": 18.5, "Isha": "90 min" },
              "location": { "latitude": 21.3890824, "longitude": 39.8579118 },
              "ramadanTune": { "Isha": 30 } },
  "TURKEY": { "id": 13, "name": "…", "params": { "Fajr": 18, "Isha": 17 },
              "defaultTune": { "Sunrise": -7, "Dhuhr": 5, "Asr": 4, "Sunset": 7, "Maghrib": 7 } },
  "DUBAI":  { "id": 16, "name": "…", "params": { "Fajr": 18.2, "Isha": 18.2 },
              "defaultTune": { "Dhuhr": 3, "Sunset": 3, "Maghrib": 3 } },
  "MOROCCO":{ "id": 21, "name": "…", "params": { "Fajr": 19, "Isha": 17 },
              "defaultTune": { "Dhuhr": 5, "Maghrib": 5 } },
  "PORTUGAL":{ "id": 22, "name": "…", "params": { "Fajr": 18, "Maghrib": "3 min", "Isha": "77 min" },
              "defaultTune": { "Dhuhr": 5 } },
  "MOONSIGHTING": { "id": 15, "name": "…", "params": { "shafaq": "general" } },
  "CUSTOM": { "id": 99 }
}
```

Two offset fields, distinct and explicit (RESEARCH §4.3):

- **`defaultTune`** — AlAdhan's per-method default tune. **Applied by default, and visible in `meta.offset`**
  (a non-zero user `tune` value *replaces* the default per key; method defaults are integers, user values
  strings — SPEC §12).
- **`ramadanTune`** — conditional default tune applied only during Ramadan (MAKKAH `Isha: 30`), gated by the
  `is_ramadan` hint; it overrides even a user value.
- **`adhanAdjustments`** — `adhan`'s opt-in `methodAdjustments` (MWL/Egypt/Karachi/ISNA/Singapore `dhuhr+1`,
  Moonsighting `dhuhr+5/maghrib+3`, etc.). **Off by default**, for users who want `adhan`-compatible output.
  (Not shown above; default empty.)

### 4.2 Composite method schema (`LFC`, experimental)

A rule engine over date windows + fallbacks. Schema fixes from review:

- **Id:** use a clearly non-AlAdhan id (e.g. `1000`), not `24` (AlAdhan's namespace is 0–5, 7–23, 99).
- **Window semantics:** `from`/`to` are year-agnostic `MM-DD`, inclusive; define wrap-around for windows
  crossing 1 Jan.
- **Inheritance:** a window **merges over `default`** (explicit override), so conditional adjustments like
  LFC's Fajr −1 (which applies *inside* 18°-reachable windows too) survive.
- **Fallback chain is normative:** `try angle A → if not reached, try angle B (if any) → if not reached, tansif`.
  `window.isha.angle` is unconditional within the window; `*Fallback` is the not-reached path only.
- **`tansif` definition:** `sunset + ½·timeDiff(sunset, sunrise)` — identical to `MIDDLE_OF_THE_NIGHT` midnight.
- **Interaction with the latitude-adjustment layer:** a composite method must run with
  `latitudeAdjustmentMethod = NONE`, or the two fallback mechanisms fight (verified: `MIDDLE_OF_THE_NIGHT`
  is a no-op when the angle isn't reached, because the clamp lands `arccos(-1)` = solar midnight).

```json
"LFC": {
  "id": 1000, "name": "London Fatwa Council (experimental)",
  "composite": {
    "default": { "fajr": 18, "isha": 18, "adjustments": { "Fajr": -1, "Dhuhr": 1 } },
    "windows": [
      { "from": "04-23", "to": "05-22", "isha": { "angle": 12 } },
      { "from": "07-21", "to": "08-19", "isha": { "angle": 12 } }
    ],
    "fajrFallback": { "whenNotReached": "tansif" },
    "ishaFallback":  { "whenNotReached": 12 }
  }
}
```

**LFC caveats (do not encode as offsets):** "additional minutes on Maghrib" and sunrise/zenith tweaks are
unquantified on the page (in the PDF only); the "5-minute wait after Fajr" is fiqh guidance, not an offset.
Ship only the unambiguous adjustments (Fajr −1, Dhuhr +1) and mark the rest TBD.

### 4.3 `Params` (the seam — identical across languages)

```python
class LatAdjust(Enum):  NONE=0; MIDDLE_OF_THE_NIGHT=1; ONE_SEVENTH=2; ANGLE_BASED=3
class Midnight(Enum):   STANDARD; JAFARI
class Shafaq(Enum):     GENERAL; AHMER; ABYAD

@dataclass(frozen=True)
class Offsets:                  # FIXED 9-field struct (matches tune() exactly; no Firstthird/Lastthird)
    imsak: float = 0; fajr: float = 0; sunrise: float = 0; dhuhr: float = 0; asr: float = 0
    maghrib: float = 0; sunset: float = 0; isha: float = 0; midnight: float = 0

@dataclass(frozen=True)
class Params:
    fajr_angle: float
    isha: float                 # angle OR minutes (isha_is_minutes disambiguates)
    isha_is_minutes: bool
    maghrib: float
    maghrib_is_minutes: bool
    imsak_mins: float
    dhuhr_mins: float
    asr_factor: float           # 1 standard (Shafi/Maliki/Hanbali/Jafari), 2 hanafi, or custom
    lat_adjust: LatAdjust
    midnight_mode: Midnight
    unreached_policy: Unreached # CLAMP (default, AlAdhan parity) | NAN (composite methods read `reached`)
    offsets: Offsets            # fixed struct, not dict[str,float]
    timezone_offset_hours: float # precomputed by facade (incl. DST); mirrors the reference, not a layering violation
```

Notes (review):
- `shafaq` lives on the Moonsighting backend (`ctx`), not `Params` — the angle kernel never sees it; the
  facade exposes `set_shafaq()`.
- `timezone_offset_hours` is deliberately inside `Params` to mirror PHP's `adjustTimes` (a kernel function in
  the 1:1 mapping). Document this so nobody "purifies" it to the facade and reorders the arithmetic.
- The numeric param value is used as a **depression angle regardless of the `*_is_minutes` flag** (RESEARCH
  §4.7 #7); the flag only selects the minutes-vs-angle *post-processing* in `adjustTimes`.

---

## 5. Kernel (`astronomy.*`)

Signature (identical across languages) — takes date parts; the kernel derives both Julian epochs internally
(the Asr target behaviour makes a single JD insufficient, RESEARCH §4.7 #2):

```
calculate(y, m, d, latitude, longitude, elevation, params: Params) -> RawTimes
# The kernel derives julianDay(y,m,d) once; solar position applies −longitude/(15·24) internally.
# Asr uses a distinct epoch = julianDay(y,m,d) + 1.0 (SPEC §6.3, RESEARCH §4.7 #2).
# RawTimes keys (AlAdhan casing/order): Fajr, Sunrise, Dhuhr, Asr, Sunset, Maghrib, Isha, Imsak,
#                                        Midnight, Firstthird, Lastthird — all float hours
```

**Contract on dates:** the facade accepts calendar days only (midnight-normalised). Supporting arbitrary
time-of-day is out of contract (RESEARCH §4.7 #2/#3) — document "dates are calendar days" as the contract.

Functions are specified formula-by-formula in `SPEC.md` (derived from PrayTimes v3 (MIT) + USNO; no
source-line annotations). The mathematics: degree trig, positive modulo, Julian day, solar position (Sun
Approx), solar noon, depression time, Asr angle, horizon angle, high-latitude fallback, night times, offsets,
Moonsighting override.

**Kernel design decisions:**

1. **`reached` flag + `unreached_policy`** — `depressionTime` returns `{time, reached}`; the raw `arccos` is
   preserved and the clamp is applied per `params.unreached_policy` (`CLAMP` default for AlAdhan parity; `NAN`
   for composite methods that read `reached`), **before** the high-latitude fallback.
2. **`equationOfTime` normalisation** — the `SolarModel` seam contract is "normalised to (−12, +12] hours".
3. **Backend hook** — Moonsighting is applied via a `post_night_hook` (no method-name branch in the kernel).

**Target-behaviour register** (RESEARCH §4.7 / SPEC.md §13) — every item is reproduced and pinned by a
dedicated test, each with its black-box evidence. The register is the single most important document for
future maintainers (it is the thing they will otherwise "fix").

**Rounding helper:** `SPEC.md` pins a single round-half-away-from-zero helper (PHP/Go semantics) because Python
(`round()` = half-even) and JS (`Math.round` = half-toward-+∞) differ. Used by Moonsighting minutes.

Per-language notes:
- Python: `math` only; `frozen dataclass` for `SunPosition`/`RawTimes`; `zoneinfo` (stdlib) in facade only.
- Go: `math` only; `RawTimes` as a fixed struct (key order matters — RESEARCH §4.7 #10); `time`+`time/tzdata`
  in facade only.
- TypeScript: `Math` only; `number` (float64); `Intl` in facade only.

---

## 6. Facade (per language, idiomatic)

Public API mirrors the PHP surface + AlAdhan envelope:

- `PrayerTimes(method, school, asr_shadow_factor?)`
- `get_times(date, lat, lng, elevation=None, lat_adjust=ANGLE_BASED, midnight_mode=None, fmt="24h")`
- `get_times_for_today(...)` · `tune(...)` · `set_custom_method(...)` · `set_shafaq(...)` · `get_meta()`
- Formats: `24h`, `12h`, `12hNS`, `Float`, `iso8601`
- **`to_aladhan_response()`** — full parity envelope (corrected per review):

```json
{
  "timings": { "Fajr":"03:57", "Sunrise":"05:46", "Dhuhr":"12:59", "Asr":"16:54",
               "Sunset":"20:12", "Maghrib":"20:12", "Isha":"22:02", "Imsak":"03:47",
               "Midnight":"00:59", "Firstthird":"…", "Lastthird":"…" },
  "meta": {
    "latitude": 51.5, "longitude": -0.12, "timezone": "Europe/London",
    "method": { "id": 2, "name": "Islamic Society of North America (ISNA)",
                "params": { "Fajr": 15, "Isha": 15 },
                "location": { "latitude": 39.70421229999999, "longitude": -86.39943869999999 } },
    "latitudeAdjustmentMethod": "ANGLE_BASED", "midnightMode": "STANDARD",
    "school": "STANDARD",
    "offset": { "Imsak":0, "Fajr":0, "Sunrise":0, "Dhuhr":0, "Asr":0,
                "Maghrib":0, "Sunset":0, "Isha":0, "Midnight":0 }
  }
}
```

Facade responsibilities and parity details (review-verified):

- Resolve method name/id → `Params` (parse `"90 min"`, `"Midnight":"JAFARI"`, `"shafaq"`); convert date +
  IANA timezone → Julian day + `timezone_offset_hours`.
- **`meta.offset` = the method's `defaultTune` merged with the user's `tune`, per key** (never `{}`): a
  non-zero user value **replaces** the default; a zero user value keeps the default; method defaults are
  integers, user non-zero values are strings (SPEC §12). `Firstthird`/`Lastthird` are **not** in it.
- **`meta.method.location`** present for every method except MOONSIGHTING/CUSTOM.
- **Moonsighting meta overrides**: `latitudeAdjustmentMethod` reports `NONE`; `shafaq` appears in
  `method.params` (observed behaviour, verified live).
- **`CUSTOM` loses its `id` after `setCustomMethod()`** — `meta.method` then has only `name` + `params`
  (the builder exposes only Fajr/Maghrib/Isha setters).
- **Midnight-mode policy:** midnight defaults to STANDARD (AlAdhan always passes an explicit value, so any
  method `Midnight: JAFARI` is overridden).
- **`get_times_for_today()` normalises to local midnight** (deterministic; matches AlAdhan; diverges from the
  reference's "now" — RESEARCH §4.7 #3).
- `is_ramadan` / `hijri_month` hint gates the MAKKAH Ramadan bump (default `False`).
- `defaultTune` is applied and **visible in `meta.offset`**; `adhanAdjustments` are opt-in.
- Dict-level comparison for parity asserts (JSON key order is not semantically meaningful).

---

## 7. Plugins

### 7.1 Moonsighting (DY-day) — "AlAdhan-compatible Moonsighting"

`MethodBackend` hook (`post_night_hook`) — implements `dyy`, Fajr `a/b/c/d`, Isha `shafaq`
(`general`/`ahmer`/`abyad`).

- **`dyy` formula (deterministic; RESEARCH §4.4):** `n` = signed whole calendar days from the hemisphere's
  solstice anchor (north `12-21`, south `06-21`, `>` → south at the equator) to the date;
  `dyy = n ≥ 2 ? n − 1 : (n ≥ 0 ? 365 : 365 + n)`. Do **not** use a leap-aware day-of-year formulation.
- **Round at the minutes point:** `round_away(minutes)` before `/60` (round-half-away-from-zero helper).
- Moonsighting feeds the angle kernel `Fajr=0°, Isha=0°` (defaults) then overwrites.
- **Non-determinism in the API (not a port bug):** the live API's Moonsighting is server-clock-dependent
  (now-fill on the anchor). Moonsighting dates within ±2 days of **either** solstice are excluded from the
  golden gate — not allow-listed (RESEARCH §4.4).
- **Document as "AlAdhan-compatible Moonsighting"** — it is AlAdhan's implementation, not the Moonsighting
  Committee's own published rules (which use 18°-seasonal Fajr and 1/7-night above 55°; `adhan` implements
  those). UK/NA users comparing against moonsighting.com timetables would otherwise file bugs (OPUS5 T8).

### 7.2 Composite (`LFC`, experimental)

`CompositeBackend` interprets `methods.json` `composite` blocks (§4.2): resolve regime → build `Params` →
run kernel → read `reached` → apply fallback chain + conditional adjustments, with
`latitudeAdjustmentMethod = NONE`.

**Status:** shipped `experimental`. The only oracle is the annual LFC PDF (North London); until it is parsed
into `shared/vectors/lfc/`, `test_lfc.py` asserts against hand-transcribed values and the unquantified
adjustments are set to zero and documented. Not part of the v1.0 parity milestone.

---

## 8. Tooling & tasks (mise)

```toml
[tools]
python = "3.14"
go     = "1.27"
node   = "24"
uv     = "latest"
bun    = "latest"

[tasks.gen-fixtures]  run = "uv run scripts/generate_fixtures.py"   # MANUAL / scheduled drift job — NOT in CI
[tasks.sync-data]     run = "uv run scripts/sync_data.py"           # copies methods.json into each language
[tasks.test-python]   run = "uv run pytest python/tests"
[tasks.test-go]       run = "go test ./..."
[tasks.test-ts]       run = "bun test"
[tasks.test]          depends = ["test-python", "test-go", "test-ts"]
[tasks.parity]        run = "uv run tests/parity.py"
[tasks.lint]          run = "uv run ruff check python && gofmt -l . && bun x tsc --noEmit"
[tasks.ci]            depends = ["test", "parity", "lint"]
```

Review corrections:

- **No AlAdhan API key is needed** for `/timings` — drop the key machinery.
- **`gen-fixtures` is not in `ci`.** Golden vectors are generated **once, reviewed, and committed**; CI reads
  only committed files. Regeneration is a manual task (or a *scheduled* drift job that opens a diff PR, so a
  silent AlAdhan behaviour change surfaces as a diff, not a broken build). Each vector file embeds its request
  params + fetch timestamp for provenance.
- Use `depends = [...]` for task ordering (mise treats `run = [...]` entries as shell commands).
- Add a **staleness CI check**: `sync-data` must produce no diff (guards the committed per-language copies).

---

## 9. Testing & accuracy

Four gates, driven by shared fixtures:

1. **Golden vs AlAdhan** (`shared/vectors/aladhan/`) — generated by `scripts/generate_fixtures.py`. **Assert
   string equality**, not ±1 minute: AlAdhan rounds to the minute, so a correct port is bit-exact on the
   string, and a ±1-minute tolerance would hide the Asr quirk and the moonsighting behaviour. Maintain an
   explicit, annotated allow-list of known deviations.
   **Asr policy:** the live API's Asr is server-clock-dependent (now-fill). Each golden vector records its
   fetch timestamp; assert Asr **exactly** when the now-fill envelope for that cell does not cross a rounding
   boundary, otherwise assert `API ∈ {static_pred, nowfill_pred(fetch_ts)}` and annotate. Optionally pin the
   exact value via the `asr_clock` facade parameter.
   **Matrix:** 23 methods × both schools × latitudes (0°, mid, **southern-hemisphere**, high-lat 65°+) × dates
   (equinox, solstices, a Ramadan day — MAKKAH with `is_ramadan=True`) **plus**: DST transition days (northern
   and southern zones), anti-meridian longitudes (±179°), a not-reached case (65°N June), MAKKAH at high
   latitude, JAFARI/Tehran (covers Firstthird/Lastthird-follow-midnightMode), non-zero elevation, all five
   output formats, and `meta` parity (offset object incl. `defaultTune`, method passthrough, Moonsighting
   overrides). **Exclude** Moonsighting dates within ±2 days of either solstice (non-deterministic — §7.1).
2. **Legacy vectors** (`shared/vectors/legacy/`) — transcribe the **expected values** (facts) from the
   published test expectations (ISNA/London/ISO-8601 edge cases and Moonsighting north/south minutes);
   **assert exact strings/ints**. Test *values* are facts; test *code* is not reproduced.
3. **Cross-language float parity** (`tests/parity.py`) — `parity_inputs.json` matrix; each language ships a
   `dump` CLI printing raw float times as JSON; compare all three to **≤1e-9 hours** (≈3.6 µs; cross-libm
   drift after this arithmetic is ~1e-13 h, so four orders of margin). **Serialization must be specified:**
   shortest round-trip / 17 significant digits (Python `repr`, Go `strconv.FormatFloat(f,'g',-1,64)`,
   JS `JSON.stringify` on a finite number). Include the **64°N Asr case** (the canary) and a not-reached input.
   Run on Linux **and macOS** (different libm / JS engine).
4. **Kernel unit tests** — high-latitude, prev/next-day, `reached`-flag + `unreached_policy`, Asr Julian-epoch
   quirk, night-portion-with-minutes, elevation formula (unit-tested against the formula — not a parity
   target), `is_ramadan`, composite (LFC) behaviour.

The two oracles are: (1) the committed AlAdhan golden vectors and (2) the published/legacy test values
(factual outputs). No GPL-derived transliteration is kept in the repo (see §1.2, PROVENANCE.md, CLEANROOM.md).

---

## 10. Milestones

1. **Scaffold** — git init; `.mise.toml`; `methods.json` + `methods.schema.json`
   + `SPEC.md` (from PrayTimes v3 MIT + USNO, with target-behaviour register); `parity_inputs.json`;
   `PROVENANCE.md` + `CLEANROOM.md` + `THIRD-PARTY-NOTICES.md`; **license: Apache-2.0** (§1.2).
2. **Python kernel + facade** — `params.py`, `astronomy.py` (date-parts signature, `reached`-flag +
   `unreached_policy`), `facade.py`; kernel unit tests mirror the target-behaviour register items.
3. **Fixture generator + Python golden/legacy tests** green vs AlAdhan.
4. **TypeScript** kernel + facade + tests green.
5. **Go** kernel + facade + tests green.
6. **Moonsighting plugin** in all three; legacy Moonsighting vectors pass (near-anchor dates excluded).
7. **Cross-language parity runner + CI** wiring; `sync-data` staleness check; README. **→ tag v1.0.**
8. **Composite method + `LFC` (experimental)** in all three, validated against a hand-transcribed PDF fixture.
   **→ ship as v1.1** (kept out of the parity milestone).

---

## 11. Decisions (for review / user)

1. **Meeus / NREL SPA backends**: defer to v2, design seam now (with `equationOfTime` normalisation contract). — *agree*
2. **Per-method offsets**: model as **`defaultTune`** (visible in `meta.offset`, user replaces per key) vs `adhanAdjustments` (off, opt-in). — *agree (was incorrectly "hidden" pre-review; corrected by API verification)*
3. **`tamkin` toggle**: **defer to v2** (formula unspecified). — *agree (changed from "include")*
4. **Composite tier in v1, `LFC` demoted to `experimental`** (non-AlAdhan id, `NONE` lat-adjust interaction, PDF oracle). — *agree*
5. **Kernel `reached`-flag + `unreached_policy` (CLAMP|NAN)** refactor. — *adopt*
6. **Licensing** — **Apache-2.0**, kernel from **PrayTimes v3 (MIT)** + public-domain USNO + published method
   data; AlAdhan behaviours derived black-box. *Decided.*
7. **`PHP_LIB` profile** — **dropped** (low value; ground truth only from the GPL package). *Decided.*
8. **Naming/packaging** — **placeholder for now** (repo to be created later; Go module path uses a placeholder
   until the GitHub repo exists). Settle one product name and the final Go module path at repo-creation time;
   monorepo release-tag convention (`python/v1.0.0`, `go/v1.0.0`); sync semver across the three packages.
