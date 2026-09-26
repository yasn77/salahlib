"""Blackbox test for the London Unified Prayer Timetable against published times.

Tolerances reflect real, documented differences between SalahLib and the LUT:
- Sunrise/Dhuhr/Maghrib: ±1 min (Sun Approx vs Meeus rounding).
- Asr: ±5 min (the +2 min LUT adjustment, plus SalahLib's Asr "+1-day declination" quirk — SPEC §13.2 —
  which the LUT does not reproduce).
- Fajr/Isha: ±5 min (LUT's refined Hizbul-Ulama chart vs the standard Moonsighting model).
"""
import json
from datetime import date
from pathlib import Path

from prayer_times import PrayerTimes

FIXTURE = Path(__file__).resolve().parent.parent.parent.parent / "shared" / "vectors" / "lut" / "lut.json"

WITHIN_1 = ("Sunrise", "Dhuhr", "Maghrib")
WITHIN_5 = ("Asr", "Fajr", "Isha")


def _min(hhmm):
    h, m = hhmm.split(":")
    return int(h) * 60 + int(m)


def test_lut_blackbox():
    data = json.loads(FIXTURE.read_text())
    pt = PrayerTimes("LUT")
    for case in data["cases"]:
        d = date.fromisoformat(case["date"])
        got = pt.get_times(d, data["latitude"], data["longitude"], tz=data["timezone"])
        expected = case["timings"]
        for k in WITHIN_1:
            assert abs(_min(got[k]) - _min(expected[k])) <= 1, f"{case['date']} {k}: {got[k]} vs {expected[k]}"
        for k in WITHIN_5:
            assert abs(_min(got[k]) - _min(expected[k])) <= 5, f"{case['date']} {k}: {got[k]} vs {expected[k]}"
