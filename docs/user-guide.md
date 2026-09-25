# SalahLib — User Guide

Installation and usage for end users.

## Install

Build and test tooling is managed by [mise](https://mise.jdx.dev):

```sh
mise install
```

## Python

```python
from datetime import date
from prayer_times import PrayerTimes

pt = PrayerTimes("ISNA")
times = pt.get_times(date(2024, 4, 24), 51.508515, -0.1254872, tz="Europe/London")
print(times["Fajr"])  # "03:57"
```

## Supported calculation methods

The method registry (`shared/methods.json`) defines 23 named methods plus `CUSTOM`, each with its depression
angles / minutes and (where AlAdhan applies them) default tune values. Methods are referenced by name
(`"ISNA"`, `"MWL"`, …) or by AlAdhan id (`2`, `3`, …).

## Summary

- Python: `pip install prayer-times` → `from prayer_times import PrayerTimes`.
- Go: `go get github.com/yasn77/salahlib/go` → `prayertimes.New("ISNA", "STANDARD")`.
- TypeScript: `npm install prayer-times` → `new PrayerTimes("ISNA")`.
- C: link `libprayer_times` and call `pt_calculate`.

All four produce byte-identical `HH:MM` strings for the same inputs, validated against the AlAdhan API.
See `shared/methods.json` for the supported calculation methods.

<!-- NEXT -->