# GLM-5.3 Review (v2) — SalahLib clean-room reimplementation

Reviewer: GLM-5.3 (`llmgateway/glm-5.3`) · 2026-09-25 · **Supersedes GLM5-3-REVIEW.md (v1)**

**Scope of this review.** The project goal changed: Apache-2.0 via **clean-room reimplementation**, not a
GPL derivative port. I therefore re-reviewed `RESEARCH.md`, `PLAN.md`, `shared/SPEC.md` plus the new
artifacts (`LICENSE`, `NOTICE`, `shared/methods.json`, `shared/methods.schema.json`,
`shared/vectors/parity_inputs.json`, `.mise.toml`) on two axes: **(1) is the technical implementation still
sound, (2) what is the likelihood of GPL violation, and where are the concerns.**

**Method.** I re-verified every load-bearing claim against primary sources: ~45 live AlAdhan API calls
cross-checked against a from-SPEC oracle implementation I wrote from `SPEC.md` alone (which doubled as a
test of the SPEC's implementability), fresh-cache probes at never-before-queried coordinates, the published
formula pages (praytimes.org/calculation, praytimes.org/manual, USNO), and the upstream PHP/`adhan` sources
(for research analysis only — appropriate here, see §2.5).

---

## Verdict

**Technically sound — proceed, with amendments below. The clean-room approach is viable and the GPL risk
is low, but not yet at its floor.** The design correctly separates what is safe (published formulas, facts,
black-box behaviour) from what is not (GPL expression). However:

1. **One new parity-critical discovery** (§1.2): AlAdhan's Asr is **server-clock-dependent**. The SPEC's
   static `jd_asr = +1.0` is the right deterministic normalisation, but the docs' parity claims
   ("AlAdhan reproduces the bug exactly", "1,483/1,485 exact") are underspecified without it, and the
   Moonsighting "residual" is explained and closable by the same mechanism.
2. **One factual error in the plan** (§1.3): `aladhanOffsets` are **not hidden from `meta`** — the API
   surfaces them in `meta.offset`. The facade spec and schema descriptions must be corrected.
3. **GPL exposure is real but enumerable** (§2.3): the SPEC currently *instructs copying two pieces of GPL
   expression* (the dead `fix` branch; the `p1/p2/cosRange` identifiers), and the repo ships no clean-room
   *protocol*. Both are cheap to fix now, expensive to fix after three ports exist.
4. **One retraction** (§2.6): my v1 review recommended vendoring upstream snapshots into `shared/upstream/`.
   Under Apache-2.0 that would itself be a license violation. The updated docs correctly dropped it —
   this review formally withdraws the recommendation.

---

## Part 1 — Technical implementation

### 1.1 Independent verification summary

| # | Claim in docs | Verdict | Evidence |
|---|---|---|---|
| 1 | AlAdhan applies per-method offsets for TURKEY/DUBAI/MOROCCO/PORTUGAL | **Confirmed exactly** | Oracle (no offsets) vs live API differ by exactly the offset sets; applying them at the tune stage reproduces **all** timings string-exact (Ankara TURKEY 2024-04-24: 8/8 timings incl. Midnight; DUBAI/MOROCCO/PORTUGAL 7/7 each) |
| 2 | Offset values (TURKEY −7/+5/+4/+7/+7, DUBAI +3/+3/+3, MOROCCO +5/+5, PORTUGAL +5) | **Confirmed** | Differencing + `meta.offset` (see §1.3) |
| 3 | MAKKAH Ramadan bump: Isha = Maghrib + 120 min in Ramadan, +90 otherwise, via `meta.offset.Isha = +30` | **Confirmed** | Makkah 2024-02-20 gap 90 / 2024-03-11 & 2024-04-08 gap 120, `meta.offset.Isha = 30` only on Ramadan dates; my oracle with +30 matches string-exact |
| 4 | Ramadan bump is MAKKAH-only | **Confirmed** | GULF & QATAR stay at 90 min in Ramadan, `meta.offset.Isha = 0` |
| 5 | TEHRAN `Midnight: JAFARI` overridden to STANDARD by default; honoured when explicit | **Confirmed** | Default → Midnight 00:03 (STANDARD); `midnightMode=1` → 23:17 (JAFARI); `meta.midnightMode` echoes accordingly |
| 6 | Moonsighting `dyy` = PHP semantics; adhan's breaks parity (Sydney 2024-01-01: 04:04 vs 04:05) | **Confirmed** | API Fajr 04:04; dyy 192/193 → 04:04, adhan's 194 → 04:05. `meta.latitudeAdjustmentMethod = NONE` also confirmed |
| 7 | Asr quirk worth "up to ~16 min at 64°" | **Confirmed, underspecified** | Full-year daily scan at 64°N: 10.1 min at lng 0, 17.8 min at lng 180 (STANDARD; HANAFI 5.9–9.3). Longitude-dependent — state the longitude in the docs |
| 8 | London 51.5°N: 18° unreachable on 59 days/year (16.2%) | **Confirmed** | 59/366 = 16.1% by independent count |
| 9 | `MoonSightingTest.php` asserts `dyy == 2` for Dec 24 (3 calendar days after Dec 21) | **Confirmed** | File read: `assertEquals(2, …)` with comment "2 days afer dec 21" — clock-dependent truncation artefact |
| 10 | `parity_inputs.json` JD values | **Confirmed** | All 8 `jd_date`/`jd_asr` pairs equal `julianDate(y,m,d)` / `+1.0` exactly |
| 11 | No API key needed for `/timings` | **Confirmed** | ~45 unauthenticated calls, no auth/rate-limit issues |
| 12 | praytimes.org/calculation publishes the formulas | **Confirmed, and stronger than claimed** | The USNO solar algorithm is reprinted verbatim (constants identical); the high-latitude methods (½-night, 1/7, angle/60) are all published; **and the Makkah "90 min, 120 during Ramadan" rule is published there too** — the Ramadan rule is a *published convention fact*, not merely fork behaviour. Only the fork's *mechanism* (`meta.offset` +30, on by default) is fork-specific |
| 13 | Sun-Approx vs Meeus accuracy table | **Confirmed previously** (v1 review, reproduced to the rounding digit) — unchanged |
| 14 | "1,483/1,485 exact" (OPUS5 matrix) | **Not re-runnable** (matrix not committed yet) — but see §1.2: the number is a *snapshot*; Asr cells are fetch-time-dependent |

Also verified in v1 and unchanged by the clean-room pivot: method registry/ids/locations vs live
`/v1/methods`; the clamp at `PrayerTimes.php:572–578` vs PrayTimes.js NaN; `riseSetAngle` formula;
LFC page contents; adhan's `methodAdjustments` (incl. Moonsighting dhuhr+5/maghrib+3).

### 1.2 NEW: AlAdhan's Asr is server-clock-dependent ("now-fill")

This is the most important technical finding of this review. The docs model the fork's Asr quirk as a
static `jd_asr = julianDate(y,m,d) + 1.0`. That is what `gregorianToJulianDate()` yields **only for a
DateTime normalised to midnight**. The live API does not normalise: it parses the request date with
PHP's `createFromFormat`, and **PHP fills missing time fields from *now*** — so the fork's Asr Julian day
carries the *query-time* time-of-day:

```
jd_asr(now) = jd_midnight + 0.5 + (H/24 − 0.5)   if H ≥ 12   (H = server clock hours)
jd_asr(now) = jd_midnight + 1.0 + H/24           if H < 12
```

**Evidence (all fresh-cache probes, never-before-queried coordinates to defeat the API cache):**

- 64°N, longitudes 61–66, 2024-01-22, queried at 17:22 UTC: API Asr matched the **now-fill** model **6/6**,
  the static `+1.0` model **0/6** (static was 3 min early on every cell).
- Lisbon (PORTUGAL) 2024-04-24: API Asr 17:21 at both 17:11 and 17:22 UTC = now-fill; static `+1.0`
  predicts 17:20. The `timings/{timestamp}` endpoint at local-midnight and local-noon timestamps **both**
  still served the now-fill value — the fill cannot be pinned via the API at all.
- Legacy date, live API: London ISNA 2014-04-24 — the API serves Asr **16:55** today (queried 17:23 UTC),
  while the PHP library's own published test asserts **16:54** (midnight semantics). The two "oracles"
  disagree with each other on the same request.
- Everything except Asr is unaffected (all other prayers use date-only components), consistent with every
  non-Asr timing matching string-exact in all my tests.

**Measured impact:** the now-fill term moves Asr by up to **8.4 min/day at 64°N** (1.6 min at 51.5°N,
0.8 min at 38.7°N) as the server clock sweeps H ∈ [0,24).

**Required amendments:**

1. **Keep the SPEC's static `+1.0`** — it is the correct *deterministic normalisation* (identical in kind
   to the already-documented `getTimesFor_today` midnight normalisation, RESEARCH §4.7 #3). But re-word
   §4.2/§12.2: "AlAdhan reproduces the bug exactly" → "AlAdhan reproduces the bug **with a server-clock
   time-of-day fill**; SalahLib pins the clock at midnight, which matches the released PHP library's
   published test values. Live-API Asr can differ from this by up to the now-fill envelope (≤8.4 min at
   64°N, ≤1.6 min at 51.5°N)."
2. **Fixture policy for Asr** (PLAN §9.1 asserts string equality): each golden vector already records its
   fetch timestamp — use it. Assert Asr exactly when the now-fill envelope for that cell doesn't cross a
   rounding boundary (the common case); otherwise assert `API ∈ {static_pred, nowfill_pred(fetch_ts)}` and
   annotate. Without this, golden Asr cells will flake depending on when the fixtures were fetched.
3. **Add a reproducible black-box probe test**: fetch N fresh coordinates (never-queried) and assert
   `API Asr == nowfill(query_time)` — this pins the now-fill model itself as observed behaviour, exactly
   the kind of evidence the clean-room story wants (§2.4).
4. **The two-profile model gains a cleaner story**: `PHP_LIB` = midnight clock (matches the released
   package's published test values), `ALADHAN` = midnight clock for determinism, matching the live API
   within the documented envelope. Optionally expose an `asr_clock` facade parameter to reproduce any
   specific API response bit-exactly (the kernel already takes `jd_asr`, so this is free).

### 1.3 The `aladhanOffsets` are NOT hidden from `meta` — plan must be corrected

PLAN §1.1/§4.1 and `methods.schema.json` say the fork offsets are "**never emitted in meta** /
hidden from `meta`". **False.** The live API returns them, verbatim, in `meta.offset`:

```
TURKEY : {Imsak:0, Fajr:0, Sunrise:-7, Dhuhr:5, Asr:4, Maghrib:7, Sunset:7, Isha:0, Midnight:0}
DUBAI  : {…, Dhuhr:3, Maghrib:3, Sunset:3, …}      MOROCCO: {…, Dhuhr:5, Maghrib:5, …}
PORTUGAL: {…, Dhuhr:5, …}                           MAKKAH (Ramadan): {…, Isha:30, …}
```

They are invisible in `GET /v1/methods` and `meta.method` (that part of the docs is right) — but they are
plainly visible in `meta.offset`. Additional mechanism details now pinned by experiment:

- **Injection point = the tune stage**, after night times: TURKEY's `Sunrise −7` does **not** shift
  Midnight (API Midnight 00:47 = no-offset prediction, not 00:43.5). My oracle applying them at tuneTimes
  matched all timings.
- **User `tune` merges per-key with method offsets (user wins)**: `tune=0,0,3,0,…` on TURKEY → Sunrise
  06:01 (base 05:58 + 3), other keys keep method offsets; `meta.offset.Sunrise` becomes `'3'`.
- **`tune` with all zeros does not clear method offsets** (timings unchanged).
- **Type inconsistency in the API** (fork artefact): method offsets are integers, user-tuned keys are
  *strings* (`'3'`, `'10'`). For byte-parity, `to_aladhan_response()` must reproduce this. Pin it in SPEC §11.

**Amendments:** correct PLAN §1.1/§4.1/§6 and the schema's two `aladhanOffsets`/`ramadanOffsets`
descriptions; SPEC §11 must specify: `meta.offset = {**method_offsets, **user_tune}` (user per-key
precedence), integer-valued for method offsets, string-valued for user-tuned keys; `ramadanOffsets`
likewise visible (they *are* the `meta.offset.Isha = 30` the docs already cite — the "hidden" wording
introduced the contradiction).

### 1.4 Moonsighting residual — explained and closable

The docs' "disclosed residual" (2/1,485 cells, southern MOONSIGHTING ±2 days of the June solstice) is, I
believe, a *construction mismatch*, now resolvable:

- The **API** parses both the request date and the solstice anchor with now-filled times → the times
  **cancel** → `dyy` = plain whole-calendar-day difference (deterministic).
- The **PHP library** at runtime uses a midnight user date vs a now-filled anchor → after-anchor dates
  truncate by one day (clock-dependent; this is exactly why `MoonSightingTest` asserts `dyy == 2` for
  Dec 24 — 3 calendar days after Dec 21).
- Therefore: `dyy_ALADHAN = calendarDayDifference(anchor, date)`; `dyy_PHP_LIB = that, minus 1 on
  after-anchor dates` (the truncation at any non-midnight clock). I verified this rule reproduces all four
  published `MoonSightingTest` values (2, 338, 2, 337) plus Sydney's 193, and that the *minutes* assertions
  (88, 87, 90, 89) pass under **both** constructions — so the legacy vectors are safe either way.

**Amendment:** SPEC §10 should define both rules explicitly (deterministic each), note that the original
lib's `dyy` was clock-dependent, and port the *minutes* assertions from `MoonSightingTest` (the
observable behaviour) rather than the internal `dyy == 2` value — which is a test-harness artefact of a
specific clock. The residual should then be re-run; I expect it to close.

### 1.5 Smaller technical items

1. **PLAN §4.1 is stale vs `methods.json`**: the plan's MAKKAH example puts `Isha: 30` under
   `aladhanOffsets`; the shipped `methods.json`/schema correctly split it into `ramadanOffsets`. Sync the
   plan text.
2. **RESEARCH §4.3B wording nit**: "TURKEY matches `adhan`'s Turkey set exactly" — adhan has no
   `Sunset` offset; AlAdhan's TURKEY set is adhan's **plus** `Sunset +7`. Also "The offsets are invisible
   via `GET /v1/methods` and `meta.method`" — true, but add "visible in `meta.offset`" (§1.3).
3. **`methods.schema.json` gap**: `windows[].isha` may be an object per the LFC example, but the schema
   doesn't constrain that object's shape (`{angle: number}`).
4. **iso8601 edge**: the formatter adds `floor(time·60)` minutes to the request date, which under the
   API's now-fill carries a time-of-day. Include `iso8601` format cells in the fixture matrix (the plan
   already lists "all five output formats" — keep it, and pin expected behaviour in SPEC §9).
5. **USNO citation is dead**: `aa.usno.navy.mil/faq/docs/SunApprox.php` now 404s; the page lives at
   `https://aa.usno.navy.mil/faq/sun_approx` (constants verified verbatim, including `EqT = q/15 − RA`).
   Update RESEARCH §2, SPEC §provenance, and NOTICE.
6. **Quirk magnitude wording**: "16.3 min at 64°" should carry the longitude ("up to 17.8 min at 64°N,
   longitude-dependent; 10.1 min at lng 0" — STANDARD school; roughly half that for HANAFI).
7. **`parity_inputs.json`**: correct as written; add one sentence noting `jd_asr = +1.0` is the
   midnight-normalised semantics (per §1.2), so future readers don't "re-derive" it from live API probes.
8. Fixture matrix (DST both hemispheres, anti-meridian, not-reached, MAKKAH-high-lat, JAFARI night times,
   elevation, Hanafi row): unchanged from v1 recommendations, all still valid.

Everything else — the four-tier architecture, `Params` seam, two-JD kernel signature, `reached`-flag +
clamp-in-adjustment-layer, `Offsets` fixed 9-field struct, `equationOfTime` normalisation contract,
committed-fixture CI policy (no live API in CI), sync-data staleness check, parity ≤1e-9 h with
17-digit serialisation, `equator > 0 → southern` trivia, rounding-helper pinning — **re-verified as sound**.
My from-SPEC oracle (written only from SPEC.md) hit string-exact parity on every non-Asr timing across
7 methods and 3 hemispheres, which is direct evidence the SPEC is complete enough to implement from.

---

## Part 2 — GPL risk assessment

*Engineering analysis, not legal advice. "GPL violation" here means: would a court find the Apache-2.0
code a copy of protectable expression from the GPL/LGPL upstreams, such that the GPL's terms apply.*

### 2.1 The framework, briefly

Copyright protects **expression**, not ideas, procedures, methods of operation, or facts (17 U.S.C. §102(b);
*Baker v. Selden*; *Lotus v. Borland*; *Feist* for facts; *Google v. Oracle* found even 11,500 lines of
declaring code a fair use). Clean-room reimplementation — observe behaviour, write a functional spec,
implement from the spec — is the long-established legitimate technique (Phoenix BIOS, and every
interoperable reimplementation since). Consequences for this project:

- Reproducing **behaviour** (including bugs/quirks like the clamp or the Asr JD offset) is not copying
  expression. Behaviour is unprotectable, however discovered.
- Reproducing **facts** (angles, minutes, ids, coefficients, timetable values, test expectations) is not
  infringement.
- The **solar algorithm itself is public domain**: it is published by USNO, a US Navy body — works of the
  US government are not subject to copyright (17 U.S.C. §105). praytimes.org additionally publishes it,
  the high-latitude methods, and the convention table.
- What remains protectable in the GPL/LGPL upstreams is **the code's expression**: literal source, and
  its expressive structure — function decomposition, naming, comments, and non-functional artefacts.

### 2.2 Provenance map — what each piece of SalahLib rests on

| Artifact | Provenance category | Risk |
|---|---|---|
| SPEC §3–§6 (trig, JD, SunApprox, midDay/sunAngleTime/asrTime maths, riseSetAngle) | Published formulas (USNO = public domain; praytimes.org reprints them) | **None** |
| SPEC §7.3 concept (½-night, 1/7, angle/60 high-lat rules) | Published on praytimes.org/calculation | **None** |
| `methods.json` (ids, names, angles, minutes, locations) | Factual data (organisational conventions; also published by praytimes.org + AlAdhan) | **None** |
| Moonsighting coefficients + interpolation | MIT `adhan` (permissive, with attribution) + facts | **None** (with NOTICE fix, §2.3.6) |
| Ramadan +120 rule | **Published** convention (praytimes.org table: "90 minutes after Maghrib, 120 minutes during Ramadan") — fork adds only the mechanism (`meta.offset`, on by default) | **None** |
| SPEC §7.2/§7.5/§9 orchestration order, minutes post-processing, formatting, `tune` order; §12 register | Behaviour — verified black-box against the live API (my probes are independent evidence) | **Low** |
| Legacy vectors | Published test values (facts) | **None** |
| SPEC §3/§12.6 **dead `fix` branch**; §6.2 **`p1`/`p2`/`cosRange` names** | **GPL-source expression** | **Fix** |
| Function inventory/naming (`midDay`, `sunAngleTime`, `nightPortion`, `adjustTimes`, `dayPortion`, `tuneTimes`, …) | LGPL PrayTimes.js structure (not on praytimes.org) | **Mitigate** (§2.3.3) |

The good news: praytimes.org's published pages cover **far more** of the SPEC than the docs claim
(§1.1 #12) — the formulas, the conventions, the high-lat methods, even the Ramadan rule. The parts that
are *not* published are all **behaviour**, which is both unprotectable and independently verified against
the API. The clean-room story is genuinely strong — it just needs the expression-level residue removed.

### 2.3 Areas of concern (ranked, with required remediations)

**1. The SPEC instructs copying GPL expression: the dead `fix` branch (SPEC §3, §12.6).**
"keep it — it costs nothing" is the single clearest copying instruction in the repo: a **non-functional**
branch (the `floor` already guarantees `a ≥ 0`) whose only reason to exist in SalahLib is that the GPL
source has it. Copying non-functional expression is the worst kind of copying — it can't be defended as
necessary (merger/scène à faire) because it does nothing. **Fix: remove it from SPEC §3 and §12.6;**
implement `fix(a,b) = a − b·floor(a/b)`; RESEARCH §4.7 #6 "copy verbatim" → delete. Outputs are
provably identical; add a one-line property test if desired. This costs nothing technically (§1.1 shows
parity doesn't depend on it) and removes the highest-risk item.

**2. GPL-source identifiers in the SPEC: `p1`, `p2`, `cosRange` (SPEC §6.2).**
These are the PHP's variable names (PrayTimes.js inlines the expression without them). Identifiers are
thin protection, but this is literal, lineable copying with zero benefit. **Fix: rename in the SPEC
pseudocode** (`numerator`, `denominator`, `ratio`) — a 2-minute edit.

**3. Structural/naming lineage.**
PLAN §5's function inventory is PrayTimes.js's decomposition, name-for-name. Names of methods-of-
operation are weakly protectable (*Lotus*, *Google v. Oracle*), and the math must stay exactly as
specified — but simultaneously copying **names + decomposition + ordering** is the "non-literal copying"
a plaintiff would plead under the abstraction test. Mitigation is cheap and preserves parity: **rename
the shipped functions** (e.g. `solarNoon`, `timeAtDepression`, `nightFraction`, `applyHighLatitudeFallback`,
`applyOffsets`) with a SPEC↔code mapping table; keep the SPEC's math untouched. Don't ship a `DMath`
lookalike; degree-trig helpers are three-line stdlib wrappers under any names.

**4. No clean-room protocol is written down.**
The repo's story is "GPL sources read for research only, not incorporated" — but nothing *enforces or
describes* it, and the same agents (and humans) who read the GPL clones will write the ports. In any
dispute, process evidence matters as much as the code. **Fix: add `CLEANROOM.md`** — short and
enforceable:
- The wall: implementation code is written **only** from `SPEC.md` + `methods.json` + vectors. The GPL/LGPL
  sources (both `islamic-network` repos, `PrayTimes.js`) are never open while writing/reviewing
  implementation code; `RESEARCH.md` is the analysis-phase artifact and stays on the research side.
- This repo's agent-driven workflow makes the wall *literally implementable*: coding-subagent prompts
  should include SPEC + data only. (The one deviation already sanctioned: SPEC §12's observed behaviours,
  each with its API-derived test.)
- An **originality check** in CI (or the scheduled job): token n-gram / identifier-overlap diff of
  `python|go|typescript` against the upstream sources (fetched to the runner, never committed). Catches
  accidental transliteration — the realistic failure mode, since the algorithm is small and familiar.

**5. Normative language still points at GPL source.**
PLAN §6 "Moonsighting meta overrides (mirror `PrayerTimes.php:824-827`)" and similar: fine in
`RESEARCH.md` (analysis), wrong in `PLAN.md`/`SPEC.md` (normative). **Fix: restate as observed
behaviour** ("`meta.latitudeAdjustmentMethod` reports `NONE` for MOONSIGHTING; `shafaq` appears in
`meta.method.params`" — verified live, §1.1 #6). Same for RESEARCH §4.7 #6's "copy verbatim".

**6. NOTICE/LICENSE details.**
(a) The USNO URL is dead (§1.5 #5) — update. (b) USNO works are **public domain** (17 U.S.C. §105) — the
NOTICE can say so explicitly, which strengthens the provenance story. (c) The Moonsighting coefficients
are taken from MIT-licensed `adhan`: MIT requires retention of its copyright/license notice for the
copied portion — add a `THIRD-PARTY-NOTICES.md` carrying adhan's MIT text (Apache NOTICE alone is not the
standard vehicle for third-party license text). (d) NOTICE's "fair attribution rather than any license
obligation" is right for PrayTimes.org; keep it.

### 2.4 What is *not* a concern (and shouldn't be "fixed" into weakness)

- **String-exact output parity with AlAdhan.** Reproducing a program's observable outputs is not
  copying its expression; it's the definition of interoperability. Every quirk in the §12 register is now
  (after this review) backed by independent black-box evidence against the live API.
- **The `PHP_LIB` profile.** "Reproduces the released package" is behaviour parity, justified by
  published test values (facts). Keep it — it's real user value (drop-in migration) — just describe it
  in behaviour terms, not "port the tests verbatim" (PLAN §9.2 wording: "transcribe the expected values").
- **`RESEARCH.md` quoting GPL line numbers / describing internals.** Describing what a program does,
  even precisely, is factual documentation. Keep it as the analysis-side artifact (per §2.3.4's wall).
- **Vendored clones in `/tmp`.** Not in the repo; correct. Keep it that way (see retraction below).

### 2.5 Why the now-fill discovery *helps* the licensing position

Every §12 behaviour is now specified with a **reproducible black-box test** (live-API probes with fresh
cache entries, fetch timestamps recorded). That is exactly what a clean-room defence wants: the spec
says "observed target behaviour, validated against the public API", and the repo *demonstrates* the
observation protocol rather than asking anyone to take the discovery story on faith.

### 2.6 Retraction of v1 advice

My v1 review (GPL-era framing) recommended vendoring upstream snapshots under `shared/upstream/` for
line-number stability. **Under Apache-2.0 that would be a direct license violation** (GPL code cannot be
distributed inside an Apache-2.0 project). The updated docs correctly removed it; this review formally
retracts it. If line-number referents are wanted for SPEC annotations, keep them in `RESEARCH.md`
(analysis side) only — and per §2.3.5, prefer behaviour language in SPEC anyway.

### 2.7 Net likelihood

With the §2.3 remediations applied: **low** — the implementation rests on public-domain formulas,
published conventions, permissively-licensed (MIT) coefficient data, factual method tables, and
behaviour verified against a public API; the remaining overlap with the GPL sources would be
unprotectable ideas/behaviour plus renamed structure, and the repo documents the protocol and the
evidence. Without them: **moderate** — not because any single item is dispositive, but because the
dead-branch instruction + GPL-source identifiers + missing protocol would let a motivated plaintiff
argue process contamination, and "the spec told us to copy the dead code" is a bad sentence to have to
explain. The remediations are a day of work, mostly edits to SPEC/PLAN/NOTICE; do them before
Milestone 2, not after three ports exist.

---

## Part 3 — Amendment checklist

**Technical (must):**
- [ ] SPEC §4.2/§12.2 + RESEARCH §4.7 #2: reword Asr quirk as server-clock now-fill; pin SalahLib to the
      midnight clock; document the envelope (≤8.4 min at 64°N) — §1.2
- [ ] PLAN §9.1: Asr assertion policy for golden vectors (envelope / fetch-timestamp rule) — §1.2
- [ ] Add the fresh-coordinate now-fill probe test (pins the behaviour register with black-box evidence) — §1.2
- [ ] Correct the "hidden from meta" claim in PLAN §1.1/§4.1/§6 + schema descriptions; specify
      `meta.offset = {**method_offsets, **user_tune}`, user-wins, int/string types; tune-stage injection
      (already evidenced) — §1.3
- [ ] SPEC §10: two deterministic `dyy` rules (ALADHAN = calendar-day diff; PHP_LIB = that, −1 on
      after-anchor dates); port minutes assertions, not `dyy == 2`; re-run the residual — §1.4
- [ ] PLAN §4.1 sync with `methods.json` (`ramadanOffsets` split) — §1.5 #1
- [ ] Update the USNO URL everywhere; note its public-domain status in NOTICE — §1.5 #5, §2.3.6

**Technical (should):**
- [ ] Quirk magnitude wording (longitude-dependent; 17.8 max at 64°N) — §1.5 #6
- [ ] Schema: constrain `windows[].isha` object shape — §1.5 #3
- [ ] iso8601 fixtures including the now-fill date edge — §1.5 #4
- [ ] `parity_inputs.json`: one sentence on midnight semantics for `jd_asr` — §1.5 #7

**Licensing (must, before Milestone 2):**
- [ ] Remove the dead `fix` branch instruction from SPEC §3/§12.6; delete RESEARCH §4.7 #6 "copy
      verbatim" — §2.3.1
- [ ] Rename `p1`/`p2`/`cosRange` in SPEC §6.2 — §2.3.2
- [ ] Rename shipped functions; ship a SPEC↔code mapping table; no `DMath` lookalike — §2.3.3
- [ ] Add `CLEANROOM.md` (the wall; agent-prompt policy; originality check in CI/scheduled) — §2.3.4
- [ ] Replace normative PHP-line references in PLAN/SPEC with observed-behaviour wording — §2.3.5
- [ ] `THIRD-PARTY-NOTICES.md` with adhan's MIT text; USNO public-domain note in NOTICE — §2.3.6
- [ ] PLAN §9.2: "transcribe the expected values" (not "port … verbatim") — §2.4

---

*Verification artifacts: ~45 live AlAdhan API calls (incl. fresh-cache probes at 64°N lng 61–66,
Lisbon/Makkah/Tehran/Ankara/Sydney/Dubai/Rabat matrices), a from-SPEC oracle implementation
(`/tmp/opencode/fork_verify.py`, `final_checks*.py`, `asr_probe.py`, `fill_probe.py`, `decisive.py`,
`legacy_asr.py`, `quirk_scan.py`), full-year daily scans, and fetches of praytimes.org/calculation,
praytimes.org/manual, and USNO's `faq/sun_approx` (constants verified verbatim).*
