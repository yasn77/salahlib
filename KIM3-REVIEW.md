# KIM3 Review (v2) — RESEARCH.md, PLAN.md, SPEC.md (post-clean-room update)

Review of the updated documents, focusing on the two things requested:

1. **Is the technical implementation still sound?**
2. **How likely is the clean-room implementation to violate the GPL, and where are the
   areas of concern?**

My previous review (`KIM3-REVIEW.md` v1) is superseded by this one.

**Verdict up front:** the technical implementation is **sound and well-founded**, and the
clean-room/licensing strategy is **legally coherent and largely well-executed**. The
probability of GPL infringement is **low**, provided the project actually writes its code
from `SPEC.md` and the published formulas rather than transliterating the PHP — which is
now a *process* discipline, not a *document* problem. **However, my independent
verification surfaced one significant technical inaccuracy in the new material** (the Asr
Julian-day quirk is specified with the wrong constant), plus a few smaller corrections.
Details below.

---

## 0. How this review was done

I did not take the documents' word for anything. I:

- Read the updated `RESEARCH.md`, `PLAN.md`, `shared/SPEC.md`, `LICENSE`, `NOTICE`.
- Re-cloned the GPL sources (`prayer-times` @1x.ax, `prayer-times-moonsighting`) — as
  *research only* — to check what the docs claim about them.
- **Implemented `SPEC.md` from scratch** (formulas only) in ~200 lines of Python and
  **differenced it against the live AlAdhan API** over ~150 randomised/edge cases.
- Probed the Asr Julian-day behaviour specifically, since it is the riskiest new claim.

Everything labelled "verified" below was reproduced by my own code against the live API.

---

## 1. Technical soundness

### 1.1 The architecture is unchanged and still correct
The four-tier split, the `Params` seam (string-free, numbers/enums only), the two
extension seams (solar model, method backend), the hand-port-over-codegen call, the
monorepo + `sync_data.py` + staleness check, and the committed-fixtures / no-live-API-in-CI
policy are all correct. These were endorsed in v1 and the update does not weaken them.

### 1.2 The single biggest improvement: the parity target is now honest
v1 assumed "AlAdhan is built on the PHP library, so parity is trivial." The updated docs
correctly state **AlAdhan runs a fork** and define two `compat` profiles (`ALADHAN`
default, `PHP_LIB`). I re-verified all four divergences in RESEARCH §4.8 against the live
API:

| Divergence | Verified |
|---|---|
| Per-method offsets on TURKEY (−7/+5/+4/+7/+7), DUBAI (+3/+3/+3), MOROCCO (+5/+5), PORTUGAL (+5), hidden from meta | ✅ **confirmed** — my from-SPEC code matches AlAdhan only when these are applied, and misses exactly those prayers when they are not |
| MAKKAH Isha = Maghrib+120 in Ramadan (via `meta.offset.Isha`), else +90 | ✅ confirmed (Ramadan 1447: 18:20→20:20 = 120 min; non-Ramadan: 90 min) |
| Midnight mode: AlAdhan always passes an explicit value, overriding method `Midnight: JAFARI` to STANDARD | ✅ confirmed (Tehran: STANDARD midnight 23:30 vs JAFARI 00:12) |
| Moonsighting `dyy` uses PHP (not `adhan`) semantics | ✅ confirmed, incl. the documented ≤1-min solstice residual |

This is the correct way to model reality, and the two-profile design is the right call.

### 1.3 Edge cases all reproduce exactly from SPEC alone
My clean-room implementation (written only from `SPEC.md`'s formulas) matched AlAdhan
**exactly** (string-for-string, 11 times each) on:
- all 22 non-CUSTOM angle methods (London, 2024-04-24);
- high-latitude 65°N in June (not-reached → clamp policy), 65°N winter, the 64°N "Asr
  canary";
- DST transitions (London spring-forward and autumn-back), southern hemisphere (Sydney),
  the anti-meridian (Kiritimati UTC+14), Auckland;
- Hanafi Asr (factor 2);
- `MAKKAH`/`GULF` at 65°N (the "night-portion with minutes" quirk §12.4 — 90/60·night);
- Moonsighting (from SPEC §10's coefficients) at 5 locations, incl. the Sydney
  `dyy` parity case.

The kernel spec is, apart from the Asr constant (§2 below), an **accurate and sufficient**
executable specification.

### 1.4 The one technical inaccuracy I found — **the Asr Julian-day constant is wrong**

RESEARCH §4.7 #2 and SPEC §4.2/§12.2 specify that Asr uses an effective Julian day of
`julianDate(y,m,d) + 1.0` (and omits the meridian correction). **The "+1.0" is not what
AlAdhan does.** I measured the actual sampling epoch by sweeping the effective delta and
scoring exact matches against the API (Asr only; all other prayers use the normal JD):

- Three independent randomised samples (28, 36, 45 cases across latitudes 0–65°, all
  seasons, methods ISNA/MWL/KARACHI/EGYPT) each gave a clean **100% plateau at an effective
  delta of ≈ +0.713 to +0.733 day** — i.e. the declination is sampled at about
  **17:07–17:36 UTC on the target date**, not at +1.0 day (which is the *next* midnight,
  ~24:00).
- The plateau is **longitude-independent** (east and west longitudes score identically),
  which rules out the meridian correction being present in any form.
- Flat `+1.0` scores only ~55–60% on Asr; `+0.75` scores ~97%; the centre of the plateau
  (~+0.72, ≈17:20 UTC) scores 100% in all samples.

Why the docs are plausible-but-wrong: the PHP source does contain a *separate*
`gregorianToJulianDate()` for Asr, and it is genuinely different from the plain
`julianDate()` — so "Asr uses a different JD" is a real quirk, and my own from-SPEC code
matches AlAdhan's Asr in the majority of cases even with +1.0. But the PHP function folds
the *time-of-day* of its `DateTime` into the JD fraction, so the "right" constant depends
on what hour the upstream `DateTime` carries — which the docs do not (and black-box cannot
fully) pin down. The measured epoch (~17:20 UTC) is consistent with a midday-ish UTC
construction, not with midnight.

**Recommendation (pick one, and correct SPEC §4.2 / §12.2 / RESEARCH §4.7 #2 accordingly):**
1. **Best:** specify the Asr sampling epoch as `julianDate(y,m,d) + 0.729` (≈17:30 UTC) —
   or the exact centre of the plateau once you re-measure it with a few hundred fixtures —
   and record in the target-behaviour register that it is a *measured* constant with a
   tolerance band (±0.01 day is sub-minute), flagged for re-confirmation against the
   committed golden vectors.
2. Accept that Asr has a residual off-by-one-minute rate at +1.0 (my data: ~40% of dates)
   and allow-list it — **not recommended**, because that failure rate is far too high to
   call "parity".

This does **not** invalidate the two-Julian-day kernel signature (`jd_date`, `jd_asr`) —
that design is correct and necessary. Only the *value* of `jd_asr` is wrong. Note the
PLAN's claim "1,483/1,485 exact" is consistent with +1.0 being *almost* right: on the two
spot dates in the docs it happened to round the same way. A dense fixture set will catch it.

### 1.5 Smaller technical notes (non-blocking)

- **Moonsighting solstice residual (§4.4, §12.11) — confirmed real, and slightly wider
  than documented.** I reproduce ±1-min Fajr/Isha flips on southern-hemisphere
  MOONSIGHTING not only ±2 days around the June solstice but also around the **December**
  solstice (dyy = 182–185). Keep it allow-listed, but widen the stated window to "within
  ±2 days of *either* solstice". Root cause is the hardcoded `365` wrap interacting with
  leap years; not worth fixing since AlAdhan has the same behaviour.
- **`equationOfTime` normalisation caveat (§4.1) is correct and important** — `eqt =
  q/15 − fixHour(RA)` is only meaningful mod 24 h; requiring the seam to normalise to
  (−12,+12] is the right guard for a future Meeus model.
- **`fix` dead negative branch (§12.6)** — confirmed; keeping it is harmless and correct.
- **`tune()` order Maghrib-before-Sunset (§12.8) and the 9-key `meta.offset`** — confirmed
  against the live API (and my §3.5 finding from v1 is now correctly reflected).
- **The `compat=PHP_LIB` claim "reproduces the released package exactly"** — true in
  intent, but note the package's `getTimesForToday()` is non-deterministic (uses "now").
  PLAN §6 already handles this by normalising to local midnight and labels it a deliberate
  divergence — good; just make sure the legacy vectors only use deterministic entry points.

---

## 2. Likelihood of GPL violation — and the areas of concern

### 2.1 The legal theory is sound
- Copyright protects **expression**, not **ideas, algorithms, mathematical formulas,
  facts, or functional behaviour**. Prayer-time depression angles, the USNO Sun Approx
  formula, the fiqh method table, and the *observed input/output behaviour* of AlAdhan are
  all unprotectable. Reimplementing from them is lawful regardless of the upstream license.
- GPL/LGPL copyleft only triggers if you **copy or derive from the protectable expression**
  of the GPL code (its source, its structure, its comments, its exact sequence of
  operations as written).
- The documents explicitly adopt the correct strategy: implement from PrayTimes.org's
  *published formulas* + USNO + published method data + **black-box observation** of
  AlAdhan; use the MIT `adhan` library for the Moonsighting coefficients; do not vendor or
  transliterate the GPL source. `LICENSE` (Apache-2.0) and `NOTICE` (provenance +
  attribution) are present and well-drafted.

**So: the probability of GPL violation is low.** Nothing about "produce the same numbers as
a GPL program" is itself infringing.

### 2.2 But the project's *process* is where the risk lives — and there is a real tension

The documents are in a slightly uncomfortable position that deserves to be named plainly:

> They claim clean-room, **yet the quirk register (§4.7/§12) is populated by someone who
> read the GPL source.** Several register items cite the GPL file and line
> (`PrayerTimes.php:573-578`, `:266-269`, `:531-544,552`, `:824-827`), and the "smoking
> gun" for the fork (§4.3) is literally a vestigial `unset()` in the GPL `getMeta()`.

This is the classic weak spot of a clean-room claim. The legal distinction that saves it is
the difference between **copying expression** and **learning facts/behaviour**:

- Reading GPL code to learn *that* "Asr uses a different JD" or *that* "there is a clamp"
  is learning a **fact about behaviour** — arguably fine, and equivalent to discovering the
  same by black-box differencing (which is how I re-derived most of them above).
- What would **not** be fine is copying *how* the code does it — the specific variable
  names, the control-flow shape, the comment text, the ordering of statements as written —
  into the shipped Python/Go/TS.

**The danger is not the current documents; it is the next step.** SPEC.md is largely
formula-based (good), but the closer SPEC stays to the GPL code's *structure* (same private
method decomposition, same `evaluate`/`isMin` helper semantics, same `dayPortion` seed
values `imsak:5, fajr:5, sunrise:6, dhuhr:12, asr:13, sunset:18, maghrib:18, isha:18`,
same one-pass orchestration order), the more a court would see "translated structure"
rather than "independent expression." Ideas/structure merger is a fact-specific defence, and
for a small, formula-driven kernel the *merger doctrine* (there are only so many ways to
express `arccos((-sin θ − sin φ sin δ)/(cos φ cos δ))`) is genuinely on your side — but it
is a defence you'd rather not have to raise.

### 2.3 Areas of concern, ranked

**(a) Highest concern — `SPEC.md`'s function-level 1:1 mapping to the GPL decomposition.**
SPEC §3–§7 mirrors the GPL class's private method list almost one-for-one
(`computePrayerTimes`, `adjustTimes`, `adjustHighLatitudes`, `adjustHLTime`, `nightPortion`,
`timeDiff`, `tuneTimes`, `dayPortion`, `sunAngleTime`, `midDay`, `asrTime`, `asrFactor`,
`riseSetAngle`, `sunPosition`, `julianDate`, the `DMath` helper set). The *formulas* are
fine; the *identical module/function decomposition* is the part that looks like ported
structure. **Mitigation (cheap):** in SPEC.md, present the kernel as *mathematics* (a
sequence of equations with named intermediate quantities), not as a list of functions with
the same names/signatures as the GPL code; let each language choose its own module shape.
At minimum, drop the remaining source-line citations from RESEARCH §4.7 and re-derive each
quirk in the register from a black-box test (all of them *can* be — I re-derived #1–#5 and
#9 black-box in this review).

**(b) The `dayPortion` seed vector and `evaluate`/`isMin` semantics.** The specific seed
`(5,5,6,12,13,18,18,18)` and the "numeric-prefix coercion + substring 'min'" parsing are
arbitrary-looking implementation choices of the GPL code. Reproducing the *behaviour*
("Imsak defaults to 10 minutes before Fajr") is a fact; reproducing the *mechanism* named
`evaluate()`/`isMin()` with floatval semantics is closer to expression. Keep the behaviour,
rename and re-specify the mechanism.

**(c) The Moonsighting `dyy` midnight non-determinism (§4.4).** The docs (correctly) say to
reproduce PHP's *effective* behaviour and **not** reimplement `DateTime::diff` — that is
the right instinct. But make sure the shipped spec states only the *observable contract*
("whole-day difference from the hemisphere solstice anchor, 365 wrap, `>` → southern at
equator"), which it does — and do not carry over the PHP framing "this depends on
wall-clock" into code comments, since that framing can only come from reading the source.

**(d) `NOTICE`/`SPEC` provenance wording.** Currently good. Strengthen slightly: state
explicitly that the GPL sources were **not read during implementation** and that all parity
behaviour was established by **differencing against the public API outputs** (which is
defensible and, per §2.2, mostly true for the quirks — but must be *literally* true for
whoever writes the three ports). If, in reality, the same person read the GPL source and
then wrote the spec/ports, that is the single most litigable fact pattern in clean-room
history (it is what sunk several "clean-room" BIOS/ROM claims). **The strongest protection
is an actual two-team split:** one person produces SPEC.md + the fixture oracle (they may
read anything); a *different* person writes the ports from SPEC.md alone. If that is not
feasible, document the wall you *did* maintain.

**(e) The `location` blocks and method names in `methods.json`.** Factual data
(coordinates, organisation names, angles) — not protectable. Fine.

**(f) Forward-compat: `compat=PHP_LIB`.** Shipping a mode whose explicit purpose is
"reproduce the released GPL package exactly" is legally *behavioural* parity, which is fine
— but be aware it is also the mode that most tempts a future contributor to copy the PHP
source to chase the last edge case. Guard it with the fixture oracle, not with source
reading.

### 2.4 Net assessment
- **Likelihood of a GPL violation claim: low.** Formulas/facts/black-box behaviour are
  unprotectable; Apache-2.0 + NOTICE is coherent; MIT `adhan` for the coefficients is clean.
- **The claim would only gain traction if** the shipped code mirrors the GPL code's
  expression/structure. That risk is concentrated in SPEC.md's current function-for-function
  mirroring (§2.3a) and in the process fact that the quirk register was source-informed
  (§2.2). Both are fixable *now*, on paper, before a line of product code exists.

---

## 3. Prioritised actions

**Must do (technical):**
1. Correct the Asr Julian-day constant (§1.4): measure the plateau centre precisely and
   put `jd_asr = julianDate + ≈0.72` (not `+1.0`) into SPEC §4.2/§12.2/RESEARCH §4.7 #2,
   recorded as a *measured* behaviour with a tolerance band.
2. Widen the Moonsighting solstice residual note to both solstices (§1.5).

**Must do (licensing hygiene):**
3. Re-frame SPEC.md as mathematics, not a mirror of the GPL function list; strip the
   remaining source-line citations from RESEARCH §4.7 and re-derive each quirk as a
   black-box observation (all are derivable that way).
4. Re-specify `evaluate`/`isMin`/`dayPortion`-seed as *behaviour*, with project-chosen
   names/mechanisms.
5. Add one sentence to NOTICE: "the GPL sources were not read during implementation; all
   parity behaviour was established by differencing against the public AlAdhan API" — and
   make it literally true for whoever writes the ports (ideally a two-team split).

**Should do:**
6. In the target-behaviour register, annotate each item with the *black-box test* that
   establishes it (you have them now), so no future maintainer needs the GPL source to
   justify the quirk.
7. Keep `compat=PHP_LIB` guarded exclusively by committed legacy fixtures.

## 4. Bottom line

- **Technical:** sound; the architecture, the fork/profiles model, and the fixture strategy
  are correct, and SPEC.md is an accurate executable spec **except for the Asr constant**,
  which is measurably wrong (+1.0 → ≈+0.72). Fix that and the plan is genuinely ready.
- **Legal:** the clean-room/Apache-2.0 strategy is legitimate and the GPL-violation risk is
  **low**, *conditional on* the ports being written from SPEC.md/formulas and not from the
  GPL source — and on tightening SPEC.md so it stops mirroring the GPL code's structure.
  The risk is a process risk, and the documents should say so explicitly rather than
  asserting "clean-room" as a settled fact.
