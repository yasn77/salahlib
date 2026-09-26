import json
from datetime import date
from pathlib import Path

from salahlib import PrayerTimes

VECTORS = Path(__file__).resolve().parent.parent.parent.parent / "shared" / "vectors" / "aladhan"


def _date(meta_date):
    d, m, y = meta_date["gregorian"]["date"].split("-")
    return date(int(y), int(m), int(d))


def _to_min(hhmm):
    h, m = hhmm.split(":")
    return int(h) * 60 + int(m)


def test_golden_vectors():
    for f in sorted(VECTORS.glob("*.json")):
        data = json.loads(f.read_text())
        meta = data["meta"]
        pt = PrayerTimes(meta["method"]["id"], school=meta.get("school", "STANDARD"))
        times = pt.get_times(
            _date(data["date"]), meta["latitude"], meta["longitude"],
            tz=meta["timezone"], is_ramadan=(f.stem == "makkah_ramadan"),
        )
        expected = data["timings"]
        for k in ("Fajr", "Sunrise", "Dhuhr", "Sunset", "Maghrib", "Isha", "Imsak"):
            assert times[k] == expected[k], f"{f.stem} {k}: {times[k]} != {expected[k]}"
        assert abs(_to_min(times["Asr"]) - _to_min(expected["Asr"])) <= 1, f"{f.stem} Asr"
