# SalahLib — User Guide

SalahLib is a **multi-language Islamic prayer-times library** — the same calculation, implemented in
**Python, Go, TypeScript and C**, validated for **output parity with the
[AlAdhan API](https://aladhan.com/prayer-times-api)**.

## Calculation methods

The method registry (`shared/methods.json`) is the single source of truth. It defines **24 named methods plus
`CUSTOM`**, each with its depression angles / minutes and (where AlAdhan applies them) default tune values.
Methods are referenced by name (`"ISNA"`, `"MWL"`, …) or by AlAdhan id (`2`, `3`, …).

A full list: MWL, ISNA, Egypt, Makkah (Umm al-Qura), Karachi, Tehran, Jafari, Gulf, Kuwait, Qatar, Singapore,
France (UOIF), Turkey, Russia, Moonsighting, Dubai, JAKIM, Tunisia, Algeria, KEMENAG, Morocco, Portugal,
Jordan, and `CUSTOM`.

### Regional method — `LUT`

- **`LUT`** — the [London Unified Prayer Timetable](https://londonsalahtimes.com/technical/). Its seasonal
  Fajr/Isha use the Moonsighting Committee model, plus the LUT's per-prayer adjustments (Sunrise −3, Dhuhr +5,
  Asr +2, Sunset/Maghrib +3). These adjustments match the published timetable exactly; Fajr/Isha are within
  ~2–5 minutes of the published times (the LUT uses a *refined* Hizbul-Ulama observation chart). Valid for the
  London region (Charing Cross, 51.5073°N 0.12755°W).

## Installation

Tooling is managed by [mise](https://mise.jdx.dev). The language packages themselves are published
independently:

| Language | Install |
|---|---|
| Python | `pip install salahlib` |
| Go | `go get github.com/yasn77/salahlib/langs/go` |
| TypeScript | `npm install salahlib` (or `bun add`) |
| C | build the static library (see below) |

## Usage

### Python

```python
from datetime import date
from salahlib import PrayerTimes

pt = PrayerTimes("ISNA")                       # or method id 2, or school="HANAFI"
times = pt.get_times(
    date(2024, 4, 24), 51.508515, -0.1254872,
    elevation=0.0, lat_adjust="ANGLE_BASED",
    tz="Europe/London", fmt="24h",             # 24h | 12h | 12hNS | Float | iso8601
    is_ramadan=False, tune=None,               # tune={"Fajr": 3}
)
print(times["Fajr"])                            # "03:57"

# Full AlAdhan {timings, meta} envelope:
response = pt.to_aladhan_response(date(2024, 4, 24), 51.508515, -0.1254872, tz="Europe/London")
```

- `school` — `"STANDARD"` (Asr factor 1) or `"HANAFI"` (factor 2).
- `fmt` — `"24h"`, `"12h"`, `"12hNS"`, `"Float"`, `"iso8601"`.
- `is_ramadan` — enable the MAKKAH Ramadan rule (Isha = Maghrib +120 min).
- `tune` — per-prayer minute offsets, e.g. `{"Fajr": 3}`.

### Go

```go
import (
    "time"
    prayertimes "github.com/yasn77/salahlib/langs/go/pkg/prayertimes"
)

pt := prayertimes.New("ISNA", "STANDARD")
times := pt.GetTimes(time.Date(2024, 4, 24, 0, 0, 0, 0, time.UTC), 51.508515, -0.1254872, "Europe/London")
fmt.Println(times["Fajr"])                      // "03:57"
```

Lower-level API: `Resolve`, `Calculate`, `FormatTime`, and `FormatISO8601` (for an ISO-8601 string on a
date/location).

### TypeScript

```ts
import { PrayerTimes } from "salahlib";

const pt = new PrayerTimes("ISNA");             // or "ISNA", "HANAFI"
const times = pt.getTimes(new Date(Date.UTC(2024, 3, 24)), 51.508515, -0.1254872, "Europe/London");
console.log(times.Fajr);                        // "03:57"

const iso = pt.getTimesISO8601(new Date(Date.UTC(2024, 3, 24)), 51.508515, -0.1254872, "Europe/London");
console.log(iso.Fajr);                          // "2014-04-24T03:57:00+01:00"
```

### C

C is the low-level kernel (no method registry of its own — it resolves the same `methods.json` data via a
generated header). Link `libprayer_times` and `-lm`:

```c
#include "prayer_times.h"

pt_params p;
pt_resolve_method("ISNA", 0 /* STANDARD */, 0 /* not Ramadan */, &p);
p.tz_offset_hours = 1.0;                        // Europe/London, BST

pt_times t;
pt_calculate(2014, 4, 24, 51.508515, -0.1254872, 0, &p, &t);
/* t.fajr ≈ 3.958 hours = 03:57 */

char buf[32];
pt_format_iso8601(t.fajr, 2014, 4, 24, 1.0, buf, sizeof(buf));  // "2014-04-24T03:57:00+01:00"
```

## Accuracy

All four languages produce byte-identical `HH:MM` strings for the same inputs, validated against the AlAdhan
API (string-equality, with Asr within ±1 minute — the API's Asr is server-clock-dependent). See
`shared/SPEC.md` for the calculation spec and the documented "target behaviours".
