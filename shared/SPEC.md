# SPEC — the calculation kernel

Executable specification of the prayer-times calculation.

> **Provenance.** The kernel is derived from **PrayTimes v3.2** (`zarrabi/praytime`, © 2007–2025
> Hamid Zarrabi-Zadeh), which is **MIT-licensed**, together with the published solar-position reference
> (USNO "Sun Approx", a work of the US federal government and therefore public domain), the published
> method data (factual depression angles / minutes per organisation), and **black-box observation** of the
> AlAdhan Prayer Times API. No GPL-licensed source was used to write this specification. Where the target
> output differs from PrayTimes v3, the difference is recorded in §13 as an **observed target behaviour**
> with its black-box evidence.

**The kernel is a pure function of numbers and enums.** It receives a calendar date, numeric coordinates,
elevation, and a fully-resolved `Params` object. It never sees method names, date objects, timezone
*identifiers*, or `"90 min"` string literals. Each language port chooses its own module/function structure;
this document specifies the mathematics, not the decomposition.

---

## 1. Contract

```
calculate(y, m, d, latitude, longitude, elevation, params) -> RawTimes

RawTimes keys (AlAdhan casing and order):
  Fajr, Sunrise, Dhuhr, Asr, Sunset, Maghrib, Isha, Imsak, Midnight, Firstthird, Lastthird
  (all float "hours of day"; e.g. 5.0 = 05:00, 18.5 = 18:30)
```

- **Dates are calendar days (midnight-normalised).** Supporting arbitrary time-of-day is out of contract
  (§13.2). The facade normalises every input date to local midnight.
- **Timezone** enters the kernel only as a numeric offset (`timezone_offset_hours`, including DST for that
  date), applied in §8.2 as `+ tz − longitude/15`. DST is the timezone offset for that date.
- `computeTimes` performs **exactly one pass** of the per-prayer computation. Do not iterate to a fixpoint.

## 2. Numerics

- All angles are **degrees**; trig helpers accept degrees and return degrees for inverse functions.
- **Positive modulo:** `mod(a, b) = ((a % b) + b) % b` (always in `[0, b)`). Used for angle and hour
  wrapping. (There is deliberately **no** negative-branch special case; the formula is already total.)
- **Round-half-away-from-zero** is used for minutes-to-integer (Moonsighting, §11):
  `round_away(x) = (x >= 0) ? floor(x + 0.5) : ceil(x - 0.5)`. PHP/Go `round()` match; Python `round()`
  (half-even) and JS `Math.round()` (half-toward-+∞) do **not** — every port implements this helper.
- The time formatter's minute rounding is **not** `round()` — it is `floor(mod(time + 0.5/60, 24) … )` (§10).

## 3. Degree-based trigonometry

```
dtr(d)    = d · π / 180
rtd(r)    = r · 180 / π
sin(d)    = sin(dtr(d))            ; cos(d), tan(d) analogous
arcsin(x) = rtd(asin(x))           ; arccos(x), arctan(x) analogous
arccot(x) = rtd(atan(1/x))
arctan2(y, x) = rtd(atan2(y, x))
```

## 4. Julian day

```
julianDay(y, m, d):
  if m ≤ 2: y ← y−1; m ← m+12
  A = floor(y/100)
  B = 2 − A + floor(A/4)
  return floor(365.25·(y+4716)) + floor(30.6001·(m+1)) + d + B − 1524.5
```

The meridian correction `− longitude/(15·24)` is applied **once**, inside `solarPosition` (§5), and nowhere
else. The Asr computation uses a distinct epoch (§6.3, §13.2).

## 5. Solar position — "Sun Approx" (USNO, public domain)

```
solarPosition(y, m, d, time, longitude):
  jd = julianDay(y, m, d) + time/24 − longitude/(15·24)
  D  = jd − 2451545.0
  g  = mod(357.529 + 0.98560028·D, 360)
  q  = mod(280.459 + 0.98564736·D, 360)
  L  = mod(q + 1.915·sin(g) + 0.020·sin(2g), 360)
  e  = 23.439 − 0.00000036·D
  RA = mod(arctan2(cos(e)·sin(L), cos(L)) / 15, 24)
  decl = arcsin(sin(e)·sin(L))
  eqt  = q/15 − RA
  return { declination: decl, equation: eqt }
```

**SolarModel seam contract:** `equation` is only meaningful **modulo 24 h** (it wraps via `mod`). A pluggable
`SolarModel` (e.g. Meeus) must normalise its `equationOfTime` to `(−12, +12]` hours, or expose `noon`
directly — otherwise it differs from SunApprox by exactly 24 h in any non-`mod` consumer.

## 6. Per-prayer times

### 6.1 `solarNoon(y, m, d, time, longitude)`

```
eqt  = solarPosition(y, m, d, time, longitude).equation
return mod(12 − eqt, 24)
```

### 6.2 `depressionTime(angle, y, m, d, time, latitude, longitude, direction)`

```
decl      = solarPosition(y, m, d, time, longitude).declination
noon      = solarNoon(y, m, d, time, longitude)
numerator = −sin(angle) − sin(latitude)·sin(decl)
denominator = cos(latitude)·cos(decl)
ratio     = numerator / denominator
reached   = (ratio ∈ [−1, 1])
ratio     = clamp(ratio, −1, 1)      # policy-dependent — see §13.1
t         = arccos(ratio) / 15
return { time: noon + direction·t, reached }
```

`direction = −1` for "before noon" (Fajr/Sunrise), `+1` for "after noon" (Sunset/Maghrib/Isha/Asr).
The kernel returns `{time, reached}`; the clamp is applied per `params.unreached_policy` (§13.1).

### 6.3 Asr — `asrShadowAngle(factor, …)`. Uses a distinct Julian epoch (§13.2).

```
jd_asr = julianDay(y, m, d) + asr_jd_offset     # asr_jd_offset = 1.0 (midnight-normalised; §13.2)
decl   = solarPositionAt(jd_asr + time/24).declination       # NO meridian correction
angle  = −arccot(factor + tan(|latitude − decl|))
return depressionTime(angle, …)
```

### 6.4 `asrFactor()`

```
if asrShadowFactor != null: return asrShadowFactor
if school == STANDARD:      return 1      // Shafi/Maliki/Hanbali/Jafari
if school == HANAFI:        return 2
return 0
```

### 6.5 `horizonAngle(elevation)`

```
return 0.833 + 0.0347·sqrt(elevation)
```

`0.833` ≈ refraction (0.567°) + solar semi-diameter (0.267°). The `0.0347·√h` term is the standard
geometric horizon-dip approximation (≈ 2.08′·√h where h is in metres) from navigational astronomy; it is a
published formula, and it is **not** a parity target (AlAdhan ignores `elevation` — §13.6).

## 7. Orchestration

Seed times (hours): `fajr=5, sunrise=6, dhuhr=12, asr=13, sunset=18, maghrib=18, isha=18`.

```
process(times):
  fajr    = depressionTime(params.fajr,    times.fajr,    −1)
  sunrise = depressionTime(horizon,        times.sunrise, −1)
  dhuhr   = solarNoon(times.dhuhr)
  asr     = depressionTime(asrShadowAngle(params.asr, times.asr), times.asr, +1)
  sunset  = depressionTime(horizon,        times.sunset, +1)
  maghrib = depressionTime(params.maghrib, times.maghrib, +1)
  isha    = depressionTime(params.isha,    times.isha,    +1)
```

`value(str)` is numeric-prefix coercion: `"90 min" → 90.0`, `"4.5" → 4.5`, `"JAFARI" → 0.0`. The numeric
value is used as a **depression angle regardless** of any "min" flag (the flag only selects §8.2
post-processing). `isMin(str)` is a substring test for `"min"`.

## 8. Adjustment

### 8.1 High-latitude fallback (runs before §8.2)

```
night = mod(sunrise − sunset, 24)        # night length in hours
portion(method, angle, night):
  NIGHT_MIDDLE:  night / 2
  ONE_SEVENTH:   night / 7
  ANGLE_BASED:   (value(angle) / 60) · night
fallback(time, base, portion, direction):
  d = (time − base) · direction
  if not reached or d > portion: time = base + portion·direction
```

Applied to Fajr (toward Sunrise, `direction=−1`), Isha and Maghrib (toward Sunset, `direction=+1`).

**Target behaviour (§13.4):** `portion` uses `value(angle)` even when the param is `"90 min"`, so
MAKKAH/GULF/QATAR at high latitude get `portion = 90/60 · night` — the Isha override is unreachable. Keep.

### 8.2 Post-processing (minutes, timezone, Dhuhr)

```
for each t in times: t ← t + timezone_offset_hours − longitude/15
if isMin(maghrib): times.maghrib = times.sunset + value(maghrib)/60
if isMin(isha):    times.isha    = times.maghrib + value(isha)/60
times.dhuhr += value(dhuhr)/60
times.imsak = times.fajr − value(imsak)/60      # Imsak is always a minutes offset in practice
```

### 8.3 Night times

```
diff = (midnight_mode == JAFARI) ? mod(fajr − sunset, 24) : mod(sunrise − sunset, 24)
midnight   = sunset + diff/2
firstthird = sunset + diff/3
lastthird  = sunset + 2·(diff/3)
```

`Firstthird`/`Lastthird` follow `midnight_mode` (same `diff`).

### 8.4 Offsets (`tune`)

```
for each i where offset[i] is set: times[i] += offset[i]/60
```

`offset` has exactly **9** keys (Imsak…Midnight; **no** Firstthird/Lastthird). `tune()` parameter order is
`imsak, fajr, sunrise, dhuhr, asr, maghrib, sunset, isha, midnight` (**Maghrib before Sunset**, not display
order).

## 9. Backend hook

Moonsighting is applied via a **backend hook** invoked after §8.3 and before §8.4 (§11). The kernel does not
branch on a method name; a `post_night_hook` supplied by the method backend runs between the night times and
the offsets. The hook may recompute Fajr/Isha/Imsak.

## 10. Output formatting

```
if isNaN(time): return '-----'                 # reachable only under unreached_policy = NAN (§13.1)
if format == Float: return time
time     = time + 0.5/60                       # rounding: add half a minute, then truncate
fixTime  = mod(time, 24)
hours    = floor(fixTime)
minutes  = floor((fixTime − hours) · 60)
suffix   = (format == '12h') ? (hours < 12 ? 'am' : 'pm') : ''      # lowercase, with leading space in output
hour     = (format == '24h') ? twoDigits(hours) : ((hours + 11) % 12) + 1
if format == 'iso8601': return dateAtMidnight + time·60 min (rolled)  # floor for +, ceil for −
return hour + ':' + twoDigits(minutes) + (suffix ? ' ' + suffix : '')
```

ISO-8601 rollover uses `floor(time·60)` for positive and `ceil(−time·60)` for negative (asymmetric — port
exactly), applied to the **un-wrapped** time; clock fields use `mod`. `twoDigits(n) = n < 10 ? '0'+n : n`.

## 11. Moonsighting override

Coefficients sourced from the Moonsighting Committee's published method via the MIT-licensed `adhan` library
(see THIRD-PARTY-NOTICES.md).

```
dyy(y, m, d, latitude):                        # deterministic; see §13.5
  anchor = (latitude > 0) ? (12, 21) : (6, 21)   # solstice anchor (month, day), same year
  n = calendarDays(anchor → date)                # signed whole-day difference
  return n ≥ 2 ? n − 1 : (n ≥ 0 ? 365 : 365 + n)

Fajr coefficients: a = 75 + 28.65/55·|lat|   b = 75 + 19.44/55·|lat|
                   c = 75 + 32.74/55·|lat|   d = 75 + 48.10/55·|lat|
Isha shafaq:
  ahmer:   a=62+17.4/55|lat|  b=62−7.16/55|lat|  c=62+5.12/55|lat|  d=62+19.44/55|lat|
  abyad:   a=75+25.6/55|lat|  b=75+7.16/55|lat|  c=75+36.84/55|lat| d=75+81.84/55|lat|
  general: a=75+25.6/55|lat|  b=75+2.05/55|lat|  c=75−9.21/55|lat|  d=75+6.14/55|lat|

minutes(dyy):                                    # piecewise interpolation over dyy
  <91   : a + (b−a)/91 · dyy
  <137  : b + (c−b)/46 · (dyy−91)
  <183  : c + (d−c)/46 · (dyy−137)
  <229  : d + (c−d)/46 · (dyy−183)
  <275  : c + (b−c)/46 · (dyy−229)
  else  : b + (a−b)/91 · (dyy−275)

Fajr:  sunrise − round_away(minutes)/60
Isha:  sunset   + round_away(minutes)/60        # round-half-away-from-zero (§2)
Imsak: fajr − value(imsak)/60
```

Moonsighting feeds the angle kernel `Fajr=0°, Isha=0°` (defaults) then overwrites. `round_away` (§2) is
applied **before** the `/60`.

## 12. AlAdhan meta envelope and default tune

- `meta.offset` = the method's **default tune** merged with the user's `tune`, per key. A **non-zero** user
  value **replaces** the default for that key; a **zero** user value keeps the default; the user's non-zero
  values are emitted as **strings**, method defaults as **integers** (a fork artefact — reproduce for
  byte-parity). In Ramadan, MAKKAH's `Isha: 30` overrides even a user value.
- The default tune values (integers, in `meta.offset`) are: TURKEY `{Sunrise:−7, Dhuhr:5, Asr:4, Maghrib:7,
  Sunset:7}`, DUBAI `{Dhuhr:3, Maghrib:3, Sunset:3}`, MOROCCO `{Dhuhr:5, Maghrib:5}`, PORTUGAL `{Dhuhr:5}`,
  and MAKKAH `{Isha:30}` during Ramadan only (gated by the `is_ramadan` hint).
- `meta.method.location` present for every method except MOONSIGHTING/CUSTOM.
- MOONSIGHTING meta: `latitudeAdjustmentMethod` reports `NONE`; `shafaq` appears in `meta.method.params`.
- `CUSTOM` after `setCustomMethod()`: `meta.method` has **no `id`** (the builder exposes only
  Fajr/Maghrib/Isha).
- Midnight mode defaults to STANDARD (AlAdhan always passes an explicit value, overriding any method's
  `Midnight: JAFARI`).

## 13. Target-behaviour register (each item is black-box derived; evidence below)

Non-obvious behaviours the implementation must reproduce. Each is pinned by a dedicated test and derived from
**observation of the AlAdhan API**, not from any source's internals.

1. **The clamp (unreached angle).** When the sun never reaches the requested depression angle, the reference
   clamps the `arccos` argument to `[−1,1]` (finite time) rather than propagating NaN. `params.unreached_policy`
   ∈ {`CLAMP`, `NAN`}; default `CLAMP`. The clamp is applied **inside** `depressionTime`, before the
   high-latitude fallback (§8.1), because the fallback compares the clamped value. Composite methods set `NAN`
   and read `reached`. Evidence: London MWL 2024-06-20, `NIGHT_MIDDLE`, Fajr = Isha = 01:02 (solar midnight).
2. **Asr Julian epoch.** Asr samples declination one day ahead and without the meridian correction
   (`asr_jd_offset = 1.0` for midnight-normalised dates). Evidence: 64°N 2024-01-22 Asr 11:35 (quirk) vs
   11:44 (self-consistent). **The live API is additionally non-deterministic here**: its server fills the
   missing time-of-day from the query clock, moving Asr by up to ~8.4 min/day at 64°N (~1.6 min at 51.5°N,
   ~0.8 min at 38.7°N). SalahLib pins the clock at midnight (deterministic, matches the published reference
   test values). Optional `asr_clock` facade parameter reproduces any specific API response.
3. **Moonsighting `dyy` derivation.** Whole-day difference from the hemisphere solstice anchor with the
   `n ≥ 2 ? n−1 : …` rule (§11); `>` → southern at the equator; `365` wrap. Do not use a leap-aware
   day-of-year formulation.
4. **Night-portion with minute-parameters.** `portion` uses `value(angle)` even for `"90 min"` params.
5. **`Firstthird`/`Lastthird` follow `midnight_mode`** and are **not** tunable.
6. **`value()` doubles as an angle** regardless of the "min" flag.
7. **`tune()` order** is `…, maghrib, sunset, …` (not display order).
8. **Formatter rounding** is `floor(t + 0.5/60)` (round-half-up), distinct from Moonsighting's `round()`.
9. **`getTimesForToday()` uses "now"** in the reference; the facade normalises to local midnight
   (deterministic, matches AlAdhan) — a deliberate divergence.
10. **Moonsighting near-anchor dates are non-deterministic** in the API (server-clock fill on the solstice
    anchor; the same request returns different minutes at different times of day). Exclude Moonsighting dates
    within ±2 days of either solstice from the golden gate — do not allow-list them; they are not a port bug.

## 14. Cross-language float parity

The kernel must produce identical float-hours in Python, Go and TypeScript. Tolerance **≤ 1e-9 h** (≈3.6 µs;
cross-libm drift after this arithmetic chain is ~1e-13 h). `dump` CLIs must serialise at 17 significant
digits (shortest round-trip: Python `repr`, Go `strconv.FormatFloat(f,'g',-1,64)`, JS `JSON.stringify`).
`parity_inputs.json` must include the **64°N Asr case** (the canary) and a not-reached input.
