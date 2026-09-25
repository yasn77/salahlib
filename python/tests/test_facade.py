"""Facade / method-resolution regression tests (SPEC §12 envelope + guards)."""
from datetime import date

from prayer_times import PrayerTimes
from prayer_times.methods import resolve


def test_makkah_ramadan_override():
    # Ramadan: MAKKAH Isha:30 overrides even a user value (SPEC §12).
    r = PrayerTimes("MAKKAH").to_aladhan_response(
        date(2024, 3, 20), 21.3890824, 39.8579118, tz="Asia/Riyadh",
        is_ramadan=True, tune={"Isha": 5},
    )
    assert r["meta"]["offset"]["Isha"] == 30  # int, not "5"
    assert r["timings"]["Isha"] == "20:32"  # Maghrib + 120 min, not +5


def test_turkey_default_tune():
    r = PrayerTimes("TURKEY").to_aladhan_response(
        date(2024, 4, 24), 39.9333635, 32.8597419, tz="Europe/Istanbul",
    )
    off = r["meta"]["offset"]
    assert off["Sunrise"] == -7
    assert off["Dhuhr"] == 5
    assert off["Asr"] == 4
    assert off["Sunset"] == 7
    assert off["Maghrib"] == 7


def test_moonsighting_resolves():
    # MOONSIGHTING resolves (SPEC §11); shafaq defaults to "general".
    p = resolve("MOONSIGHTING")
    assert p.shafaq == "general"


def test_moonsighting_times():
    # London, method 15, 2024-10-15 (away from solstices) — matches AlAdhan.
    t = PrayerTimes(15).get_times(date(2024, 10, 15), 51.508515, -0.1254872, tz="Europe/London")
    assert t["Fajr"] == "05:50"
    assert t["Isha"] == "19:28"


def test_iso8601():
    t = PrayerTimes("ISNA").get_times(date(2014, 4, 24), 51.508515, -0.1254872, tz="Europe/London", fmt="iso8601")
    assert t["Fajr"] == "2014-04-24T03:57:00+01:00"
    assert t["Midnight"] == "2014-04-25T00:59:00+01:00"  # next-day rollover
