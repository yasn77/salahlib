# Provenance

This document records, honestly, where SalahLib's code and data come from and what was and was not read
during its development.

## What the implementation is derived from

| Source | Licence | What it provides |
|---|---|---|
| **PrayTimes v3.2** (`zarrabi/praytime`, © 2007–2025 Hamid Zarrabi-Zadeh) | **MIT** | The core kernel mathematics (Sun Approx, solar noon, depression-time, Asr angle, high-latitude fallback, `value`/`isMin` coercion, seed times). |
| **USNO "Sun Approx"** (`aa.usno.navy.mil/faq/sun_approx`) | **Public domain** (US federal government work, 17 U.S.C. §105) | The solar-position formula. |
| **PrayTimes.org calculation page** | Published documentation | The calculation formulas and the published method conventions. |
| **`adhan`** (`batoulapps/adhan-js`) | **MIT** | The Moonsighting seasonal-twilight coefficients. |
| **AlAdhan Prayer Times API** (`aladhan.com`) | Public API output (facts) | Method data (`id`/`name`/`params`/`location`), and the **black-box target behaviour** for every AlAdhan-specific behaviour recorded in SPEC §12–§13. |

## What was read during research, and is not used

During the research phase the following **GPL-licensed** sources were read to understand the problem space:

- `islamic-network/prayer-times` (PHP, GPL-3.0-or-later)
- `islamic-network/prayer-times-moonsighting` (PHP, GPL-3.0-or-later)
- PrayTimes.js v2.5 (LGPL-3.0)

**No code from these sources was copied into SalahLib.** The specification (`shared/SPEC.md`) was re-derived
from the MIT-licensed PrayTimes v3, the published formulas, and black-box observation of the AlAdhan API.
Every AlAdhan-specific behaviour is specified as an **observed target behaviour** with its black-box evidence
(SPEC §13), never as copied implementation.

This is a "dirty-room research, clean-room implementation" position: the analysis phase examined many sources
(including GPL ones) to learn what behaviour is required; the implementation phase uses only the MIT,
public-domain, factual, and black-box-observed inputs listed above.

## Attribution

See `NOTICE` for acknowledgements and `THIRD-PARTY-NOTICES.md` for the retained MIT notices.
