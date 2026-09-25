# OPUS5-REVIEW (rev. 2): clean-room / Apache-2.0 review

Reviews the updated `RESEARCH.md`, `PLAN.md` and `shared/SPEC.md` (plus `NOTICE`, `methods.json`,
`parity_inputs.json`). It covers two questions:

1. Is the technical plan still sound?
2. How likely is it that this "clean-room" implementation infringes the GPL? Where are the concerns?

> **Not legal advice.** This is an engineering assessment of copyright and provenance risk. If the licence
> matters commercially, have a lawyer read §B. You are in the UK, so I cite UK/EU law first.

**Method.** Every new claim here was checked against a primary source today (2026-09-25): the live AlAdhan
API, the PrayTimes.org calculation page and changelog, the **PrayTimes v3 source (MIT)**, `adhan-js`, and the
repo files as they are on disk. Section §C lists three places where **my previous review was wrong**.

---

## Verdict

**Technically, the plan is still sound.** The architecture, the two-Julian-day kernel, the compat profiles,
the committed golden vectors and string-equality gates are all correct. I found **four real defects**:

- a double-applied meridian correction (T1)
- a Moonsighting `dyy` formula that fails the project's own legacy vector (T2)
- a wrong `meta.offset`/`tune` model that breaks parity for four methods whenever a user tunes (T3)
- AlAdhan itself being non-deterministic (T2)

All four are cheap to fix now.

**On licensing:**

- **Legal risk is low.** Nothing you need is copyrightable expression. What you need is maths, facts and
  observable behaviour.
- **Process and provenance risk is high.** The documents *claim* a clean room that did not happen:
  - `SPEC.md` says it is "not derived from any GPL-licensed source code", yet it is a close pseudocode
    rendering of `PrayerTimes.php`.
  - `RESEARCH.md` in the same repo records reading, line-citing and transliterating that source.
  - A clean-room claim that the repo's own history contradicts is worse than no claim. It turns a defensible
    "we only took unprotectable ideas" position into an apparent misrepresentation.

**The biggest de-risking step costs nothing.** PrayTimes' author relicensed it **from LGPL-3.0 to MIT in
v3.0.0 (2025-03-25)**. v3 contains the same core algorithm. Rebase `SPEC.md` on it:

- **Kernel expression:** use PrayTimes v3 (MIT).
- **Everything AlAdhan does differently:** derive it genuinely black-box from the API.

That leaves almost nothing that depends on the GPL source.

| Area | Grade | Change since rev. 1 |
|---|---|---|
| Architecture / seams | **A−** | two-JD kernel, compat profiles, `reached` all adopted correctly |
| Parity target definition | **B** | right shape; the `tune`/`meta.offset` model is wrong (T3) |
| Spec correctness | **B−** | T1, T2, T4 and T5 are all spec-level bugs |
| Test strategy | **A−** | string equality, committed vectors, allow-list: all good |
| Legal exposure (substance) | **Low** | only maths, facts and behaviour are needed |
| Provenance / clean-room integrity | **D** | claims contradicted by the repo's own documents (§B.2) |

---

## A. Technical soundness

### A.1 What is sound (keep it)

- **Architecture.** Four tiers, the `Params` seam, and the `SolarModel` contract normalising EoT to (−12, +12] h.
- **Two-Julian-day kernel.** `jd_asr = julianDate + 1.0` with no meridian correction is correct for dates
  normalised to midnight. It matches AlAdhan: 64°N 2024-01-22 gives Asr 11:35, against 11:44 for a
  self-consistent kernel.
- **Compat profiles.** `ALADHAN` and `PHP_LIB` resolve the conflict between the two targets.
- **Test process.** String-equality gates, committed golden vectors, `gen-fixtures` out of CI, a `sync-data`
  staleness check, and `depends=` in mise.
- **Midnight-mode override under `ALADHAN`.** Re-verified.
- **Umm al-Qura Ramadan rule.** Re-verified. It applies to MAKKAH only; GULF and QATAR stay at +90 in Ramadan.
  AlAdhan's `calendarMethod` did not move the boundary on 2024-03-10/11 or 2024-04-09/10.
- **Round-half-away-from-zero helper** and the 17-significant-digit float serialisation.
- **LFC.** Demoted to experimental, given a non-AlAdhan id, and its lat-adjust interaction set to `NONE`.

### A.2 Defects

#### T1 — `jd_date` is defined two different ways, so the meridian correction is applied twice (high)

- `PLAN.md:261` defines `jd_date = julianDate(y,m,d) − longitude/(15·24)`.
- `SPEC.md:103` and `SPEC.md:111` subtract `longitude/(15·24)` again inside `midDay` and `sunAngleTime`.
- `parity_inputs.json` passes `jd_date = 2456771.5`, i.e. **without** the correction.

An implementer following PLAN double-counts it: about 0.5 days of solar drift at ±180°. That is minutes of
error at mid-latitudes, and it would *also* pass the float-parity gate as long as all three ports make the
same mistake.

**Fix:** use one definition. I recommend: `jd_date` is the plain `julianDate(y,m,d)`, and the kernel applies
the longitude term internally. Update PLAN §5.

#### T2 — Moonsighting `dyy`: the spec fails its own legacy vector, and the oracle is non-deterministic (high)

`SPEC.md:278` says "whole-day difference from `12-21-<year>`". Read literally, 2020-12-24 gives **3**.
`MoonSightingTest` asserts **2**, and so does AlAdhan's effective behaviour. The PHP anchor carries the
*current wall-clock time*, so a truncated `diff` loses a day after the anchor.

The effective behaviour, with `n` = calendar days from anchor to date:

```
dyy = n ≥ 2 ? n − 1  :  (n ≥ 0 ? 365 : 365 + n)
```

This means the anchor day and the day after it are **both 365**. Specify this formula explicitly.

**New finding — AlAdhan itself is non-deterministic here.** The same request (Sydney, 2024-06-20, method 15)
returned:

- Fajr **05:28** during my rev. 1 sweep;
- Fajr **05:27** today at 16:57 UTC.

So the "≤1-minute residual" in RESEARCH §4.4 and SPEC §12.11 is **not a porting bug**. The oracle's output
depends on when you call it: the time of day, and probably the server timezone versus the request timezone.

Consequences:

- Stop budgeting an "investigation task" for it.
- Exclude Moonsighting dates within ±2 days of each anchor from the golden gate. Do not allow-list them.
- Record the fetch timestamp in each vector (PLAN already says to).

#### T3 — The `meta.offset` and `tune` model is wrong for 4 methods, and for MAKKAH in Ramadan (high)

`PLAN.md:29`, `:331` and `:343`, and RESEARCH §4.3, say the four per-method offsets are "hidden from meta" and
that `meta.offset` is always zeroed. **Both claims are false. That was my error in rev. 1** (see §C). Verified
live:

| Request | `meta.offset` | Result |
|---|---|---|
| TURKEY, no `tune` | `{Sunrise:-7, Dhuhr:5, Asr:4, Maghrib:7, Sunset:7, …0}` | offsets visible |
| DUBAI / MOROCCO / PORTUGAL, no `tune` | their sets are visible likewise | |
| TURKEY, `tune=0,0,0,2,0,0,0,0,0` | `{Sunrise:-7, Dhuhr:'2', Asr:4, …}` | Dhuhr 13:00, not 13:03+2 |
| MAKKAH, Ramadan, no `tune` | `Isha: 30` | Isha = Maghrib + 120 |
| MAKKAH, Ramadan, `tune=…,Isha=5,…` | `Isha: 30` | Isha unchanged; the user's value is discarded |

So these are **default `tune` values**, and the observable rules are:

1. `meta.offset` = the method defaults, merged with the user's `tune`.
2. A **non-zero** user value **replaces** the default for that key. It does not add to it.
3. A zero user value keeps the default.
4. User-supplied values come back as strings.
5. In Ramadan, MAKKAH's `Isha: 30` overrides even a user value.

**Fix:**

- Rename `aladhanOffsets` to `defaultTune`.
- Emit it in `meta.offset`.
- Implement the merge in rules 1–5.
- Delete "never emitted in meta" and "excluded from meta" from PLAN §1.1, §4.1, §6 and §11.2, and from
  RESEARCH §4.3 and §4.8.

This also *helps* the clean-room story: the offsets are directly observable in the API response, so no
"differencing a port" is needed (§B.3).

#### T4 — The clamp is in the wrong place (medium)

`SPEC.md:118` clamps inside `sunAngleTime`. PLAN §5 says clamping "moves to the adjustment layer". Neither
works as stated:

- The clamp must happen **before** `adjustHighLatitudes`, which is inside the kernel pipeline. The HL rule
  compares the clamped value, not NaN.
- If it runs after, results change for every not-reached day. That is 16% of days in London.

**Fix:** keep the raw value plus `reached` inside `sunAngleTime`, and apply `Params.unreached_policy`
(`CLAMP` | `NAN`) immediately, before `adjustTimes`. Composite methods set `NAN` and read `reached`.

#### T5 — The kernel branches on the method name (low)

`SPEC.md:238` has `if method == MOONSIGHTING …`, which breaks the core contract ("the kernel never sees method
names").

**Fix:** make it a backend hook (`post_night_hook`) that runs between the night times and `tune`, and
recomputes Imsak when Imsak is a minutes value.

#### T6 — The elevation term has no target and no clean source (low)

- AlAdhan ignores `elevation` (verified in rev. 1), so it cannot be a parity target.
- `0.0347·√h` appears only in LGPL/GPL *code*. The PrayTimes calculation page says the constant is "in practice
  … the same regardless of elevation".

**Fix:** either cite a standard horizon-dip formula from the literature (≈ 2.08′·√h, geometric dip) in your
own words, or drop elevation from v1. See also B.2.

#### T7 — `PHP_LIB` profile: poor value for its cost (medium; recommendation)

It exists to reproduce a package with no direct users. It differs from `ALADHAN` in only three behaviours (no
default tune, JAFARI midnight honoured, no Ramadan rule), and it is the one part whose ground truth is only
observable **by running the GPL package** (§B.3).

**Recommendation:** drop it from v1, or defer it. The London/ISNA legacy vector reproduces under `ALADHAN`
anyway, because ISNA has no default tune and standard midnight.

#### T8 — `MOONSIGHTING` is AlAdhan's version, not Moonsighting Committee's own method (documentation)

moonsighting.com publishes rules that AlAdhan does not implement:

- take the later of Fajr (18°, seasonal) and the earlier of Isha;
- apply 1/7-night rules above 55°;
- slide to 60° beyond that.

`adhan` implements those rules. Document the method as "AlAdhan-compatible Moonsighting", or users in the UK
and North America will compare it with moonsighting.com timetables and file bugs.

#### T9 — Minor

- `RESEARCH.md:117` still describes "`tzOffsetHours − longitude/15` (`PrayerTimes.php:398`)". Fine
  technically, but see B.2.
- `is_ramadan` defaults to `False` under `ALADHAN`, so the *default* profile is not AlAdhan parity for MAKKAH
  in Ramadan. Say so plainly in the API docs, and always pass the hint in fixtures.

---

## B. GPL / clean-room assessment

### B.1 Legal frame (short)

**What copyright protects.** Expression, not ideas, algorithms, mathematical formulas or program
functionality:

- UK CDPA 1988 and the EU Software Directive art. 1(2);
- *SAS Institute v World Programming*: CJEU C-406/10, and [2013] EWCA Civ 1482;
- *Navitaire v easyJet* [2004] EWHC 3487 (Ch) — non-literal copying of business logic was not protected;
- US 17 USC §102(b).

**What the GPL covers.** Its obligations attach only to a "work based on the Program", i.e. something that
copies protected expression. Having *read* GPL code does not by itself make your code GPL.

**Observing and testing is lawful.** Under CDPA **s.50BA**, a lawful user may observe, study and test a
program to learn its underlying ideas, and a contract cannot override this. That covers probing AlAdhan, and
running the PHP package locally, which the GPL also expressly permits.

**The cautionary part of *SAS v WPL*.** WPL *won* on functionality, but was **liable for copying SAS's manual
text** into its own documentation. The equivalent risk here is *documentation and pseudocode that closely
tracks the expression of the source*, which is exactly what `SPEC.md` is today.

**Clean room is evidence, not a legal requirement.** Its value is in proving independent creation, so it only
has value if it is true.

### B.2 Risk register

| # | Concern | Evidence | Legal risk | Integrity risk |
|---|---|---|---|---|
| L1 | **Provenance claims contradicted by the repo** | `SPEC.md:74` says "not derived from any source's internal function"; `SPEC.md:315` says "derived from AlAdhan observation, not from source". Meanwhile `RESEARCH.md:295` names `gregorianToJulianDate()` (`PrayerTimes.php:531-544, 552`), `RESEARCH.md:282` says the quirks were found "by differencing a validated reference", and `parity_inputs.json`'s `note` field names `gregorianToJulianDate()`. | Low | **High** |
| L2 | **SPEC is a pseudocode rendering of `PrayerTimes.php` / PrayTimes v2** | Same function decomposition and names (`dayPortion`, `adjustHLTime`, `nightPortion`, `riseSetAngle`, `tuneTimes`, `modifyFormats`); same seed times; `twoDigits`; `((hours+11)%12)+1` (`:266`); `value`/`isMin`; the `"12-21-<year>"` m-d-Y anchor string (`:278`); the ISO floor/ceil asymmetry. This is the *SAS*-manual pattern. | **Low–Medium** | High |
| L3 | **Instructions to copy artefacts that cannot be observed** | `RESEARCH.md:316`: "`DMath::fix` carries a dead negative branch — **copy verbatim**". `SPEC.md:56` and `:332` say "keep it". A dead branch has **no observable behaviour**; you can only know it from the source, and keeping it serves no purpose except fidelity to the source's expression. | Low | **High** (a smoking gun) |
| L4 | **GPL line references and snippets inside the repo** | 13 `*.php` references in RESEARCH/PLAN (e.g. `PLAN.md:334`: "mirror `PrayerTimes.php:824-827`"). Review files: KIM3 (3 line refs), GLM5-3 (7 line refs + code), OPUS5 rev. 1 (5 line refs + `$dayfrac` snippets). Short quotations for review are fair dealing (CDPA s.30), but they **put GPL internals into the implementers' context**. | Low | **High** |
| L5 | **Legacy tests "ported verbatim"** | `PLAN.md:424`: port `TimingsTest.php` + `…` **verbatim**. Expected values are facts; test *code* is expression. | Low | Medium |
| L6 | **`PHP_LIB` behaviours are only knowable from GPL internals** | e.g. the Moonsighting "now" clock, and JAFARI midnight being honoured. | Low | Medium |
| L7 | **Moonsighting provenance mismatch** | `NOTICE` says it was implemented "with reference to MIT `adhan`", but SPEC §10's `dyy` follows **PHP** semantics, which `adhan` does *not* use. | Low | Medium |
| L8 | **Elevation formula** | `0.0347·√h` is sourced only from LGPL/GPL code (T6). It is a formula, so not protectable, but it has no clean citation. | Very low | Low |
| L9 | **`methods.json` fingerprints** | `39.70421229999999` etc. are byte-identical to `Method.php`. They are also served by `GET /v1/methods`, so source them from there and record that. Facts; the UK database right is negligible for 24 records. | Very low | Low |
| L10 | **Upstream licence ambiguity** | The PHP file header says "License: GNU LGPL v3.0"; `composer.json` says GPL-3.0-or-later. Either way it is copyleft, so the strategy does not change. Record both. | — | Low |
| L11 | **My rev. 1 transliteration** | `/tmp/opencode/salahlib-research/php_port.py` is a line-by-line translation, so it **is** a GPL derivative. Rev. 1 recommended committing it as `scripts/reference_php.py`. **Retracted: never commit it.** Keeping it privately is permitted by the GPL. It is not in the repo (verified). | — | — |
| L12 | **LLM implementers** | Your implementers are agents. If they are given RESEARCH.md or the review files, the "room" is contaminated regardless of what SPEC says. Separately, models may have seen the GPL code in training. You can't eliminate that, but you can avoid prompting with GPL-internal names. | Low | Medium |

**Bottom line on likelihood.**

- **Copyleft attaching to the finished Python/Go/TS code:** unlikely, provided it is written from a rewritten
  spec (below) and not from the PHP.
- **Being accused of a false clean-room claim if the repo ships as it is today:** likely. Anyone who reads
  RESEARCH.md next to NOTICE will notice the contradiction.

### B.3 The fix: make the provenance claim true

**1. Rebase the kernel on PrayTimes v3 (MIT, © Hamid Zarrabi-Zadeh, 2025).** The changelog for v3.0.0 says
"Change license from LGPL v3.0 to MIT". I read `src/praytime.js` (398 lines). It already contains, under MIT:

- Sun Approx with `mod`-normalised `g`, `q`, `L` and `RA`;
- `midDay`, and `angleTime` (≡ `sunAngleTime`), with the same `numerator / (cos·cos)` form;
- the Asr `−arccot(factor + tan|lat − decl|)`;
- the seed times 5/6/12/13/18/18/18 and one iteration;
- `value()` numeric-prefix coercion and `isMin()` substring test;
- high-latitude factors ½, 1/7 and `value(angle)/60`. That last one means **register item #4
  ("night-portion with minute params") comes from MIT code, not GPL code.**

Where v3 differs from AlAdhan, each difference becomes a **black-box-derived** register item:

| Item | v3 (MIT) | AlAdhan target | Black-box evidence |
|---|---|---|---|
| Unreached angle | NaN | clamp | London MWL 2024-06-20, MIDDLE_OF_THE_NIGHT: Fajr = Isha = 01:02 (solar midnight) |
| Asr declination | consistent | `jd + 1`, no longitude term | fit hypotheses {0, +0.5, +1 day} × {±lng term} to AlAdhan Asr; only `+1 / no-lng` fits (64°N 01-22 → 11:35) |
| Imsak | absent | Fajr − 10 min | any response |
| JAFARI midnight | next-day Fajr | same-day Fajr, wrapped | `midnightMode=1` responses |
| Firstthird/Lastthird | absent | sunset + diff/3, 2diff/3 | any response |
| Default tune, Ramadan +30 | absent | visible in `meta.offset` (T3) | any response |
| Moonsighting | absent | seasonal minutes with coefficients from `adhan` (MIT); `dyy` fitted from AlAdhan outputs | fitted: e.g. Sydney 2024-01-01 needs PHP-style `dyy`; flag the non-determinism (T2) |
| Formatter | `Math.round` on ms | floor(t + ½ min) | equivalent for t > 0; ISO asymmetry from `iso8601=true` on the ±day ISO cases |

Put the black-box probes in the repo (e.g. `scripts/probes/*.py`, AlAdhan-only), each emitting the evidence
for one register item. Then SPEC §12's "derived from AlAdhan observation" becomes literally true, and
reproducible.

**2. Rewrite `SPEC.md` in your own structure and vocabulary.**

- Adopt v3 names (`angleTime`, `adjustTime`, `asrAngle`) or your own. Do not use PHP/v2 names
  (`dayPortion`, `adjustHLTime`, `modifyFormats`, `twoDigits`, `getFormattedTime`).
- Replace the m-d-Y anchor string with "the December/June solstice anchor date".
- **Delete the dead-branch item** (`SPEC.md:56`, `:332`; `RESEARCH.md:316`). `fix` is
  `a − b·floor(a/b)`, which is never negative for finite floats, so dropping the branch changes no output.
- Remove every `.php:NNN` reference and every PHP identifier from SPEC, PLAN, `parity_inputs.json` and
  `methods.schema.json`.

**3. Split the rooms.**

- Move `RESEARCH.md` and the three `*-REVIEW.md` files out of the implementation repo: into a private repo, or
  a `research/` directory that is **excluded from the release artefacts and from implementer prompts**.
- Give implementer agents **only** `SPEC.md`, `methods.json`, the schema and the vectors.
- Keep an honest `PROVENANCE.md` stating the truth, e.g.:

  > "The GPL `islamic-network/prayer-times` source was read during research. The specification was then
  > re-derived from PrayTimes v3 (MIT), the PrayTimes.org calculation page, USNO, `adhan` (MIT) and black-box
  > AlAdhan probes. No GPL code or its structure was used in the implementation."

  That is a defensible "dirty-room research, clean-room implementation" position. The current "never read" framing is not.

**4. Legacy and PHP-lib vectors.** Either drop them with `PHP_LIB` (T7), or generate them by **running** the
released PHP package in a podman container and recording (input → output) as JSON. Don't port the test files.
Running GPL software is unrestricted, and it is lawful observation under s.50BA. Use `faketime` for the
Moonsighting clock effect.

**5. NOTICE.**

- Add the PrayTimes v3 MIT copyright and permission notice. If you adapt v3's code expression this is a
  **licence obligation**, so drop "rather than any license obligation" for that entry.
- Add `adhan-js`'s MIT notice. It is not strictly required for bare coefficients, but it is cheap.
- Cite `GET /v1/methods` as the source of the method data.
- Add a one-line licence note recording L10 (the LGPL-header / GPL-composer mismatch).

**6. Optional, and the cheapest way to remove all doubt:** email Islamic Network (Meezaan) describing the
project. Ask either for a written "no objection to an Apache-2.0 reimplementation", or for a relicence of the
small AlAdhan-specific behaviours. They benefit from a well-tested multi-language port.

### B.4 Low-risk items (no action beyond provenance notes)

- AlAdhan golden vectors. API output is factual data, not GPL code.
- Method angles, names, ids and locations. These are facts.
- The LFC timetable: hand-transcribing a handful of values as test facts is fine. Don't redistribute the PDF.
- `adhan`'s Moonsighting coefficients (MIT) and the Umm al-Qura Ramadan rule. The Ramadan rule is also
  published on the PrayTimes.org calculation page: "90 minutes after Maghrib, 120 minutes during Ramadan".

---

## C. Corrections to my rev. 1 review

1. **"AlAdhan's per-method offsets are hidden from `meta`" was wrong.** They appear in `meta.offset`. I only
   checked `/v1/methods` and `meta.method`. It also missed the rule that a user's `tune` replaces them (T3).
   PLAN and RESEARCH inherited this error.
2. **"Keep `php_port.py` in the repo as `scripts/reference_php.py`" is retracted.** It is a GPL derivative and
   incompatible with the Apache-2.0 decision (L11).
3. **The ≤1-minute Moonsighting residual is oracle non-determinism, not an off-by-one to investigate** (T2).

---

## D. Actions, in order

**Before milestone 1 (licensing):**

1. Rebase SPEC on PrayTimes v3 (MIT) and your own vocabulary. Delete the dead-branch item. Strip all PHP
   identifiers and line refs, including from `parity_inputs.json` (B.3.1–2).
2. Move RESEARCH and the review files out of the implementation context. Write an honest `PROVENANCE.md`
   (B.3.3).
3. Add AlAdhan-only probe scripts that evidence each register item (B.3.1).
4. Update NOTICE (B.3.5). Optionally, contact Islamic Network (B.3.6).

**Before milestone 2 (technical):**

5. T1: one `jd_date` definition.
6. T3: replace `aladhanOffsets` with `defaultTune`, using the replace-merge rules, visible in `meta.offset`,
   and the Ramadan override.
7. T2: the explicit `dyy` formula; exclude near-anchor Moonsighting dates from the golden gate.
8. T4: `unreached_policy` in `Params`, applied before high-latitude adjustment.
9. T5: a Moonsighting backend hook instead of a method-name branch.
10. T6/T7: decide on elevation and `PHP_LIB` (I recommend deferring both).

**Docs:**

11. T8: document "AlAdhan-compatible Moonsighting".
12. T9: document that `is_ramadan` defaults to off.

---

## E. Reproduction

Probes run for this revision, against the live API on 2026-09-25:

- MAKKAH on 2024-02-20 and 2024-03-20: `meta.offset.Isha` is 0 and 30.
- MAKKAH Ramadan boundaries under `calendarMethod` ∈ {UAQ, HJCoSA, MATHEMATICAL}.
- MAKKAH in Ramadan with `tune` Isha=5: overridden to 30.
- GULF and QATAR in Ramadan: +90, no bump.
- `meta.offset` for methods 13, 16, 21, 22 and 3 without `tune`.
- TURKEY with `tune` Dhuhr=2: replaces the default.
- Sydney Moonsighting on 2024-06-20: returned 05:27 now, versus 05:28 in rev. 1.

Sources:

- `github.com/zarrabi/praytime` (v3.2, MIT);
- praytimes.org `/docs/calculation` and `/docs/changelog`;
- the repo files at the line numbers cited above.

Research clones and scratch scripts are in `/tmp/opencode/salahlib-research/`. They include the GPL-derivative
`php_port.py`: **do not copy anything from that directory into the repo.**
