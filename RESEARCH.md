# Research — SalahLib

A record of everything learned while researching how Islamic prayer times are calculated,
prior to building this multi-language library.

> **Status:** reviewed by three independent agents (KIM3, OPUS5, GLM5-3). Their findings were
> cross-checked against the live AlAdhan API and the primary sources; every load-bearing claim below
> has been validated. The review deltas are recorded in the companion `*.md` review files.

---

## 1. Intent & motivation

Build a **multi-language library/module** for Islamic prayer times, initially targeting **Python**, **Go**
and **TypeScript**, structured so new languages can be added cheaply.

> **Licensing note (decided):** this is a **clean-room reimplementation** from the published calculation
> formulas and published method data, released under **Apache-2.0**. It is *not* a derivative port of any
> GPL-licensed source — the GPL `islamic-network/prayer-times` (PHP) library was analysed **only** as research
> to learn the problem space and to derive the parity targets; its code is not incorporated. See §2.3.

Core design goals:

- **Separate the calculation maths from its inputs.** The astronomy/calculation kernel must be a pure
  function of numbers/enums only — it must not know method names, date objects, timezone strings,
  or `"90 min"` string literals.
- **Validate accuracy** by comparing against the [AlAdhan Prayer Times API](https://aladhan.com/prayer-times-api).
- **Easy extension** — new languages and calculation methods/backends must not require touching the kernel.
- **Full output parity** with AlAdhan (scope: `timings` + `meta`).

### 1.1 The parity target is a fork — not the released PHP package

The single most important finding of the review process (and the one that invalidates the original
assumption "AlAdhan is built on the same PHP library, so parity is trivial"):

> **AlAdhan runs a *fork* of the PHP library** with behaviour the released package does not have.

Four verified divergences between the released PHP package and the AlAdhan API are listed in §4.8.
Three of them move results by up to 30 minutes. "Replicate the PHP library" and "match AlAdhan" are
therefore **two different targets**, and the plan handles them as two explicit `compat` profiles
(`ALADHAN`, the default). See PLAN.md §1.

---

## 2. Source material

| Source | What it is | Link |
|---|---|---|
| `islamic-network/prayer-times` (PHP) | GPL reference implementation — analysed **for research only**, NOT ported from | <https://1x.ax/islamic-network/libraries/prayer-times> (v1.0.29, commit `8e1bff8`) |
| `islamic-network/prayer-times-moonsighting` (PHP) | GPL Moonsighting dependency — analysed **for research only** | <https://1x.ax/islamic-network/libraries/prayer-times-moonsighting> (commit `f8a8ea4`) |
| **PrayTimes v3.2** (`zarrabi/praytime`) | **MIT** — the implementation source for the kernel | <https://github.com/zarrabi/praytime> · formulas <http://praytimes.org/calculation> |
| USNO "Sun Approx" | Published solar-position reference (**public domain**, US federal work) — the implementation source | <https://aa.usno.navy.mil/faq/sun_approx> |
| AlAdhan | Accuracy/comparison target (black-box API + method list) | <https://aladhan.com/prayer-times-api> · <https://aladhan.com/calculation-methods> |
| `adhan` (Batoul Apps) | MIT reference for the Moonsighting coefficients | <https://github.com/batoulapps/adhan-js> |

> **Note on mirrors:** the `github.com/islamic-network/*` mirrors now 404 (the org hosts only a `.github`
> repo). The canonical source is the self-hosted git behind `1x.ax`. The GPL sources were cloned **only** for
> the validation/research described in this document; they are **not** vendored into the repo and are **not**
> a porting source. `SPEC.md` is written from the **MIT-licensed PrayTimes v3** plus the published USNO formulas
> and the observed AlAdhan behaviour (§12). See PROVENANCE.md and CLEANROOM.md.

### 2.1 The PHP library — what it contains

- `src/PrayerTimes/PrayerTimes.php` — orchestration: `computeTimes` → `computePrayerTimes` → `adjustTimes` →
  `adjustHighLatitudes` → `tuneTimes` → `modifyFormats`. Also `getMeta()`.
- `src/PrayerTimes/DMath.php` — degree-based trig helpers (`dtr/rtd/sin/cos/tan/arcsin/arccos/arctan/arccot/arctan2/fixAngle/fixHour/fix`).
- `src/PrayerTimes/Method.php` — the method registry (`getMethods()`, `getMethodCodes()`) and a `Method` builder for custom methods.
- Tests: `tests/TimingsTest.php` (ISNA/London/ISO-8601 edge cases), `tests/TimingsMoonSightingTest.php`.

### 2.2 The Moonsighting dependency — what it contains

A **separate algorithm** (not angle-based) that overrides Fajr/Isha:

- `Fajr`/`Isha` compute minutes-before-sunrise / minutes-after-sunset from a **seasonal DY-day table**
  (`dyy` = days since solstice, hemisphere-dependent) with coefficients `a/b/c/d` per latitude and `shafaq`.
- Used only by the `MOONSIGHTING` method; it plugs in *after* the angle maths run.

### 2.3 Licensing — decided: Apache-2.0, clean-room reimplementation

The upstream chain is:

- PrayTimes.js v2.5 — **LGPL-3.0**
- **PrayTimes v3.0+ (`zarrabi/praytime`) — MIT** (relicensed from LGPL-3.0 on 2025-03-25)
- `islamic-network/prayer-times` and `-moonsighting` — **GPL-3.0-or-later** (per `composer.json`)
- `adhan-js` — **MIT**

**Why clean-room / rebase:** a line-annotated translation of GPL code is a **derivative work**, and GPL's
copyleft would force the ports to be GPL. Two facts make a permissive release clean:

1. The **math is not copyrightable** — only its specific expression. The USNO "Sun Approx" formula is US
   federal government work (public domain, 17 U.S.C. §105).
2. PrayTimes' author **relicensed the algorithm to MIT in v3.0.0**, so the kernel mathematics can be sourced
   from MIT code rather than from the GPL PHP port.

**Decision:** SalahLib is **Apache-2.0**. The implementation:

- Sourced its kernel from **PrayTimes v3 (MIT)** + the **public-domain USNO formula** + the published method
  data (facts) — see `SPEC.md` provenance and `THIRD-PARTY-NOTICES.md`.
- Sources the Moonsighting coefficients from the MIT `adhan` library.
- Derives every AlAdhan-specific behaviour (the §4.7/§4.8 quirks) from **black-box observation** of the
  AlAdhan API, not from GPL code.
- Records the honest "dirty-room research, clean-room implementation" position in `PROVENANCE.md` and the
  enforcement protocol in `CLEANROOM.md`.

The GPL sources referenced in this research document were read **only** to understand the problem and derive
parity targets; they are not incorporated into the code. See NOTICE for attribution.

---

## 3. How the algorithm works (the standard)

The core is a **pure, deterministic float function**:

```
calculate(julianDay, latitude, longitude, elevation, params) → times (hours-of-day floats)
```

Key facts that drive the design:

1. **The maths never touches dates or timezones.** It works on a Julian day (float) and returns hours-as-floats
   (`5.0` = 05:00, `18.5` = 18:30). Timezone is applied afterwards as a pure additive offset:
   `tzOffsetHours − longitude/15`. DST is simply the timezone offset for that date.
2. **Three layers exist implicitly** in the PHP code:
   - `DMath` — degree trig helpers (~30 lines).
   - **Astronomy kernel** — `julianDate`, `sunPosition`, `midDay`, `sunAngleTime`, `asrTime`, `riseSetAngle`,
     `dayPortion`, `computePrayerTimes`, `adjustTimes`, `adjustHighLatitudes`, `nightPortion`, `timeDiff`, `tuneTimes`.
   - **Inputs/config** — the method registry, school (Asr factor), latitude-adjustment method, midnight mode, offsets, format.
3. **Two astronomy "engines" exist** (see §4.1), and the fiqh method list (§4.2) is identical on top of either.
4. `computeTimes` does **one pass** (PrayTimes.js `numIterations = 1`); PHP calls `computePrayerTimes` exactly
   once. A "fixpoint iteration" refactor would silently break parity.

---

## 4. Findings

### 4.1 Two astronomy engines, both legitimate

**A. "Sun Approx" (USNO)** — used by PrayTimes.org, the PHP lib, and AlAdhan.
A ~30-line simplified solar position (`g`, `q`, `L`, `e`, `RA`, `eqt`, `decl`) from the USNO Sun Approx reference.

**B. "Meeus" (Astronomical Algorithms)** — used by the `adhan` library.
Full method: mean solar/lunar longitude, equation of centre, apparent longitude with **nutation**, obliquity of
the ecliptic, **mean sidereal time**, and **3-point interpolation of RA/declination across prev/today/next day**.

**Measured difference** (computed directly during research; independently reproduced by two reviewers):

| date | declination Δ | equation-of-time Δ |
|---|---|---|
| 2024-03-20 | 0.0005° | 0.035 min |
| 2024-06-20 | 0.0028° | 0.027 min |
| 2024-12-21 | 0.0029° | 0.022 min |
| 2024-01-15 | 0.0025° | 0.028 min |

**Max deviation ≈ 0.003° declination, ~2 s equation of time → prayer times differ by a few seconds at most**
(OPUS5 measured ≤2.69 s EoT over a 10-year sample; ≈1.1–1.5 s in prayer times at 51.5°N). Sun Approx is *not*
crude — it is accurate to well within AlAdhan's 1-minute rounding. A third, gold-standard tier exists:
**NREL SPA** (VSOP87, arcsecond accuracy) — demonstrably overkill for prayer times.

**Caveat (review):** `sunPosition()`'s `equation` is only meaningful **modulo 24 h** (`eqt = q/15 − fixHour(RA)`
wraps — measured 23.878 h where the true value is −0.122 h). `fixHour` inside `midDay()` absorbs it. The
`SolarModel` seam must therefore specify its `equationOfTime` contract as "normalised to (−12, +12] hours"
(or return `noon` directly), or a Meeus impl will differ from SunApprox by exactly 24 h in any non-`fixHour` consumer.

### 4.2 The fiqh method list is standard — no "newer" set of angles

The registry is fixed by convention/fiqh and is exactly what AlAdhan exposes. **Precise count: 23 named
methods + `CUSTOM` (id 99); ids in use are 0–5, 7–23, 99; id 6 is unused.** (MOONSIGHTING is id 15, already
in the 23.)

MWL (18/17), ISNA (15/15), Egypt (19.5/17.5), Umm al-Qura (18.5/"90 min"), Karachi (18/18), Tehran (17.7),
Jafari (16), Gulf (19.5/"90 min"), Kuwait (18/17.5), Qatar (18/"90 min"), Singapore (20/18), France (12/12),
Turkey (18/17), Russia (16/15), Moonsighting (shafaq), Dubai (18.2/18.2), JAKIM (20/18), Tunisia (18/18),
Algeria (18/17), KEMENAG (20/18), Morocco (19/17), Portugal (18/"77 min"), Jordan (18/"5 min"/18), Custom.

The `id` field in `Method.php` **already matches AlAdhan's `method` parameter** (MWL=3, ISNA=2, Makkah=4,
Egypt=5, Karachi=1, Tehran=7, Jafari=0, …), and every method also carries a static `location` block that
AlAdhan surfaces in `meta.method.location` (except MOONSIGHTING and CUSTOM).

### 4.3 Per-method adjustments: two distinct things (the review corrected this section)

There are **two** independent offset mechanisms, previously conflated. The key review correction:
**AlAdhan applies its own per-method offsets** (unlike the released PHP package and the original PrayTimes.js).

**A. `adhan`'s `methodAdjustments` (opt-in, off by default).** Present in `adhan-js/src/CalculationMethod.ts`,
*not* in PrayTimes/PHP/AlAdhan:

- MWL / Egyptian / Karachi / ISNA / Singapore: `dhuhr +1 min`
- Turkey: `sunrise −7, dhuhr +5, asr +4, maghrib +7`
- Dubai: `sunrise −3, dhuhr +3, asr +3, maghrib +3`
- Singapore: rounds **up**
- MoonsightingCommittee: `dhuhr +5, maghrib +3`

**B. AlAdhan's own per-method `defaultTune` (ON by default, needed for parity, visible in `meta.offset`).**
Recovered by differencing a validated port against the live API (OPUS5), and **re-verified here** against
`/v1/timings` (London, 2024-04-24, all Sunrise/Dhuhr/Asr/Maghrib/Sunset compared method-by-method):

| Method | AlAdhan offsets vs released PHP library |
|---|---|
| `TURKEY` (13) | Sunrise **−7**, Dhuhr **+5**, Asr **+4**, Sunset **+7**, Maghrib **+7** |
| `DUBAI` (16) | Dhuhr **+3**, Sunset **+3**, Maghrib **+3** |
| `MOROCCO` (21) | Dhuhr **+5**, Maghrib **+5** |
| `PORTUGAL` (22) | Dhuhr **+5** |

All other methods: zero. (`TURKEY` is `adhan`'s Turkey set **plus** `Sunset +7`; `DUBAI` differs from `adhan`'s
Dubai — AlAdhan has no sunrise/asr offset.) These are **default `tune` values**: they appear verbatim in
`meta.offset` (integers), and a **non-zero** user `tune` value **replaces** (does not add to) the default for
that key. They are invisible in `GET /v1/methods` and `meta.method`, but plainly visible in `meta.offset` —
see SPEC §12.

### 4.4 Moonsighting: coefficients identical to `adhan`, but the `dyy` derivation is **not**

The `a/b/c/d` coefficients and the six-branch (91/137/183/229/275-day) interpolation **match exactly**
between the PHP Moonsighting package and `adhan`'s `seasonAdjustedMorningTwilight`/`seasonAdjustedEveningTwilight`.

**But `dyy` differs:**

| | PHP (`MoonSighting/PrayerTimes.php`) | `adhan` (`Astronomical.ts`) |
|---|---|---|
| derivation | `DateTime::diff` from `12-21`/`06-21` (same year) | `dayOfYear + 10` (north) / `− 172/173` (south) |
| leap years | none — hardcoded `365 + diff` wrap | leap-aware |
| equator (lat = 0) | `> 0` → **southern** | `>= 0` → **northern** |
| determinism | depends on wall-clock (below) | deterministic |

The PHP version has a subtle non-determinism: `DateTime::createFromFormat('m-d-Y', '12-21-2020')` supplies
**no time**, so PHP fills the missing fields from *now* and `diff(...)->format('%r%a')` truncates to whole
days. This is baked into the library's own test (`MoonSightingTest.php` asserts `dyy == 2` for Dec 24, which
is 3 days after Dec 21 — 2 at most clock values, 3 at exactly midnight). Porting `adhan`'s cleaner
leap-aware `daysSinceSolstice` instead **breaks AlAdhan parity** (Sydney 2024-01-01 method 15: AlAdhan Fajr
04:04 = PHP `dyy` semantics, but 04:05 with `adhan`'s). **PHP's is the parity target.**

**Deterministic `dyy` formula** (SPEC §11): with `n` = signed whole calendar days from the hemisphere's
solstice anchor to the date, `dyy = n ≥ 2 ? n − 1 : (n ≥ 0 ? 365 : 365 + n)`.

**Rounding point:** `Fajr::getMinutesBeforeSunrise()` uses `round()` (half-away-from-zero) and
`Isha::getMinutesAfterSunset()` uses `(int) round()` — rounding to whole minutes happens **before** `/60`.
Round at exactly that point or sub-minute drift flips displayed minutes.

**Non-determinism in the API itself (not a port bug):** AlAdhan's Moonsighting is **server-clock-dependent**
— the solstice anchor is now-filled, so the same request returns different minutes at different times of day
(e.g. Sydney 2024-06-20 method 15 returned Fajr 05:28 in one sweep and 05:27 later). The "≤1-minute residual"
is this oracle non-determinism, **not** an off-by-one to investigate. Moonsighting dates within ±2 days of
**either** solstice are excluded from the golden gate (they are not allow-listed).

### 4.5 Academic literature

| Work | Contribution | Reference |
|---|---|---|
| **"The Accuracy of Approximate Solar Coordinates (USNO) in calculating prayer times"** | Validates the Sun Approx algorithm vs. ephemeris data for prayer-time use | <https://www.semanticscholar.org/paper/52307b14c227846d6392976817f7d9147ae38c2e> |
| **Acaroğlu (2025), PhD, Humboldt University — "The Calculation of Islamic Prayer Times According to the Four Sunnī Schools"** | Definitive recent work. Introduces the **tamkīn** framework (corrections converting *geocentric* → *apparent* altitude: refraction, parallax, semi-diameter, horizon dip); collates 400+ historical astronomers' opinions on Fajr/Isha altitude | <https://doi.org/10.18452/32885> |
| **Sultan (2004), "Salattim / Prayer Times"** | Foundational astronomical definitions of the five prayers | <https://astronomycenter.net/pdf/sultan_2004.pdf> |
| **"Fifteen or Eighteen Degrees" (Fiqh Council of North America)** | Documents the 15° vs 18° dispute (astronomical twilight = 18°, ISNA's 15° calibrated to NA mid-latitudes) | <https://fiqhcouncil.org/fifteen-or-eighteen-degrees-calculating-prayer-fasting-times-in-islam/> |
| **PrayCalc / DPC ("Dynamic PrayCalc")** | Cutting edge: **NREL SPA** + **dynamic (adaptive) depression angles** varying with latitude/season/elevation, back-calibrated by ML from human sightings | <https://praycalc.org/science/twilight-angles> · <https://github.com/acamarata/pray-calc-ml> |
| **"Islamic Prayer Time Calculation in High-Latitude Summer"** | Midnight-sun / persistent-twilight problem; fallback rules are physically unsatisfying | <https://journal.walisongo.ac.id/index.php/al-hilal/article/download/29337/7557/92766> |

Key academic takeaways:

- **tamkīn** is the academically-significant refinement that materially moves results. PrayTimes already carries a
  *partial* tamkīn (its `riseSetAngle()` = `0.833° + 0.0347√elevation`, where `0.833°` ≈ refraction 0.567° +
  semi-diameter 0.267°), but Fajr/Isha depression angles are applied geometrically with no refraction correction.
  The ISNA-15°/MWL-18°/Egypt-19.5° spread is, in effect, organisations absorbing tamkīn into their chosen angle.
- **The depression-angle debate is live fiqh + observational research**, not settled: medieval astronomers used
  16–20°; modern proposals suggest 15°; the angle varies physically with latitude, season, humidity, elevation.
- **The chosen angle dominates**: differences between methods (15° vs 18° vs 19.5°) are *larger* than the entire
  tamkīn/solar-model uncertainty — which is why Sun Approx is more than sufficient.

### 4.6 The London Fatwa Council method (composite/seasonal)

<https://londonfatwacouncil.org/salah-timing> — the LFC timetable is a **composite method**, not a fixed angle set:

| Window | Fajr | Isha |
|---|---|---|
| 20 Aug – 22 Apr | 18° | 18° |
| 23 Apr – 22 May & 21 Jul – 19 Aug | 18° (where reached) | **12°** (nautical — *Ṣahibayn & Imam Shafiʿī*) |
| Summer nights when 18° is never reached | **Tansif-ul-Layl** = sunset + ½(sunset→sunrise) | 12° |

Astronomically motivated: London (51.5°N) never reaches 18° depression around the summer solstice (OPUS5
measured the unreachable case on **59 days/year = 16.2%** at London's latitude). Local adjustments: Fajr −1 min
(18° periods only), Dhuhr +1 min, "additional minutes on Maghrib", and a **5-minute wait after Fajr** —
the last of which is *fiqh guidance about when to pray*, **not** a redefinition of when Fajr begins, so it is
**not** modelled as an offset. **"Additional minutes on Maghrib" and the sunrise/zenith tweaks are not
quantified on the page** — the published annual PDF timetable carries the numbers; until it is parsed, LFC is
shipped as an `experimental` reference (see PLAN.md §7.2).

**Architectural consequence:** such methods cannot be a static `Params` object — they need a *rule engine*
(date windows, a runtime "does the sun reach −N° tonight?" check, fallbacks, conditional adjustments).
See PLAN.md §3 for the "composite method" tier.

### 4.7 Target-behaviour register — quirks that are part of the parity contract

This is the highest-value list in this document: the implementation must **reproduce** these behaviours
(they are specified as *observed target behaviour* in `SPEC.md` §12), and a future maintainer must be told
not to "fix" them. Each is pinned by a dedicated test. They were identified during research by differencing
a validated reference calculation against the live AlAdhan API; in the shipped code they are derived from
black-box observation, not from any GPL source.

1. **The clamping divergence.** PrayTimes (v2/v3) computes `arccos(...)` with **no clamping** — when the sun
   never reaches the requested angle it returns `NaN`, which the high-latitude fallback detects. The PHP port
   (and therefore AlAdhan) **clamps** the ratio to `[−1,1]`, producing a finite time. Resolution: the kernel
   returns `{time, reached}` and applies `params.unreached_policy` (`CLAMP` default for AlAdhan parity, `NAN`
   for composite methods that read `reached`). The clamp is applied **before** the high-latitude fallback.
   Consequence: `-----` is effectively unreachable under the clamp policy.

2. **The Asr Julian-epoch quirk (parity-critical, worth up to ~16 min at high latitude).** Asr samples solar
   declination one day ahead of the other prayers, and without the meridian correction — i.e. the Asr epoch is
   `julianDay + 1.0` for a midnight-normalised date. AlAdhan reproduces this (64°N 2024-01-22 Asr 11:35 vs
   11:44 for a self-consistent kernel). **The live API is additionally non-deterministic here**: its server
   fills the missing time-of-day from the query clock, moving Asr by up to ~8.4 min/day at 64°N (~1.6 min at
   51.5°N). SalahLib pins the clock at midnight (deterministic, matches the published reference test values);
   an optional `asr_clock` facade parameter reproduces any specific API response. The kernel contract carries
   both Julian epochs (or date parts) — see SPEC §6.3.

3. **`getTimesForToday()` is non-deterministic.** The reference uses *now*, so Asr varies with the call hour.
   The facade's `get_times_for_today()` **normalises to local midnight** — deterministic, and matches AlAdhan.

4. **Night-portion with minute-parameters.** The high-latitude fallback passes the raw param as an *angle*
   even when the param is `"90 min"` — so MAKKAH/GULF/QATAR at high latitude get `portion = 90/60 · night`,
   making the Isha override unreachable. Port as-is; add a 65°N + MAKKAH fixture.

5. **`Firstthird`/`Lastthird` follow `midnightMode`** — they use the same `diff` as Midnight. JAFARI midnight
   mode changes them too. `tune()` does **not** cover them (9 keys only).

6. **Positive modulo.** The reference uses `mod(a,b) = ((a % b) + b) % b` (always in `[0,b)`); there is no
   negative-branch special case. (PrayTimes v3 expresses this cleanly; the older PHP had a vestigial dead
   branch, which we deliberately do not reproduce.)

7. **`evaluate()` is PHP `floatval` semantics** (`"90 min"` → 90.0, `"JAFARI"` → 0.0) and `isMin()` is a
   substring check for `"min"`. The value doubles as a depression angle in `computePrayerTimes` *and* the
   `nightPortion` angle — the numeric value is used as an angle **regardless** of the minutes flag.

8. **`tune()` parameter order** (PHP signature and AlAdhan CSV) is `imsak, fajr, sunrise, dhuhr, asr,
   maghrib, sunset, isha, midnight` — **Maghrib before Sunset**, *not* display order.

9. **Rounding is `floor(t + 0.5/60)` for formatter minutes** (round-half-up), **but** Moonsighting minutes use
   `round()` (half-away-from-zero). PHP/Go `round` match; Python (`half-even`) and JS (`Math.round`,
   half-toward-+∞) do **not** — a shared round-half-away-from-zero helper is pinned in `SPEC.md`.

10. **JSON key order** — AlAdhan's `timings` order is `Fajr, Sunrise, Dhuhr, Asr, Sunset, Maghrib, Isha,
    Imsak, Midnight, Firstthird, Lastthird`. Byte-parity requires a fixed struct (Go maps randomise;
    Python dicts are insertion-ordered).

### 4.8 The four AlAdhan-vs-PHP divergences (summary)

| # | Divergence | AlAdhan behaviour | Released PHP library | Impact |
|---|---|---|---|---|
| 1 | Per-method default tune | TURKEY/DUBAI/MOROCCO/PORTUGAL offsets applied, **visible in `meta.offset`** (§4.3 B) | none | up to 7 min |
| 2 | Umm al-Qura Ramadan rule | MAKKAH Isha = Maghrib + **120 min** in Ramadan (else +90), via `meta.offset.Isha` = +30 | none | **30 min** |
| 3 | Midnight mode | always passes explicit value → method `Midnight: JAFARI` (Tehran/Jafari) overridden to STANDARD | honours `Midnight: JAFARI` | up to 137 min |
| 4 | Moonsighting `dyy` | PHP semantics, **server-clock-dependent** (now-fill on the anchor) | PHP semantics | ≤1 min, ±2 days of either solstice |

The Umm al-Qura Ramadan rule is **re-verified here**: Makkah 2024-02-20 (Rajab) Isha = Maghrib + 90 min;
2024-03-11 (Ramaḍān 1) and 2024-04-08 (Ramaḍān 29) Isha = Maghrib + 120 min. This collides with "Hijri out of
scope": full MAKKAH parity requires knowing whether the date is in Ramadan. Resolution in PLAN.md §1 — a
minimal `is_ramadan` facade hint (**default `False`**, so MAKKAH Ramadan parity requires the caller to pass
it), with a tabular Umm-al-Qura "is-Ramadan?" helper as a v2 follow-up.

---

## 5. Decisions made so far

1. **Monorepo** (single repo, per-language subprojects + shared data) — best for cross-language parity testing.
2. **Hand-port, not codegen.** Kernel ≈260 lines, stable astronomy; method data is the only thing that changes
   and it lives in shared JSON. Parity tests are the real safety net. (The *data* still needs a sync step into
   each language tree — see PLAN.md §3 — because `go:embed`/wheel/npm cannot reference `shared/` at publish time.)
3. **Scope A** for AlAdhan parity: `timings` + `meta` (no Hijri/Gregorian *calendar* block; a minimal
   `is_ramadan` hint is the one Hijri-adjacent exception — §4.8).
4. **All 23 named methods + CUSTOM + Moonsighting** in v1.
5. **Minimal dependencies** (stdlib-only kernels; timezone via stdlib in each language).
6. **Build order**: Python → TypeScript → Go.
7. **Tooling**: `mise` for tools, environments, tasks.
8. **One parity profile** (`ALADHAN`, the default — full API parity; the low-value `PHP_LIB` profile was
   dropped in the v2 review) — see PLAN.md §1.

## 6. Decisions pending confirmation

(Resolutions from the review are recorded here; recommendations given.)

1. **Meeus / NREL SPA backends** — defer to v2, design the solar-model seam now (with the `equationOfTime`
   normalisation contract from §4.1). *Recommend: agree.*
2. **Per-method offsets** — model as **`defaultTune`** (visible in `meta.offset`, on by default, user replaces
   per key) vs `adhanAdjustments` (off by default, opt-in). *Recommend: agree.*
3. **`tamkin` correction toggle** — **defer to v2** (the exact formula — which corrections at which altitude —
   is not yet specified; v1's job is parity). *Recommend: defer.*
4. **Composite tier in v1; `LFC` demoted to `experimental`** (unquantified adjustments, PDF-only oracle),
   shipped behind the parity milestone. *Recommend: agree.*
5. **Kernel `reached`-flag + `unreached_policy` (CLAMP|NAN)** refactor. *Recommend: adopt.*
6. **Licensing** — **decided: Apache-2.0**, kernel sourced from **PrayTimes v3 (MIT)** + public-domain USNO +
   published method data, AlAdhan behaviours derived black-box. See §2.3, PROVENANCE.md, CLEANROOM.md.
7. **`PHP_LIB` profile** — **dropped** (low value; ground truth only from the GPL package). *Decided.*

---

## 7. What the reviews confirmed unchanged

The three reviewers, working independently against the primary sources, confirmed the following as correct
and not to be revisited: the four-tier architecture and `Params` seam; Sun-Approx-sufficiency (reproduced
within rounding error); the clamp-vs-NaN divergence and the `reached`-flag resolution; the method registry
and its AlAdhan id mapping; the hand-port-over-codegen call for the kernel; the Python→TS→Go build order;
and the cross-language float-parity idea at ≤1e-9 h. The defects found were enumerable amendments, not
architectural.
