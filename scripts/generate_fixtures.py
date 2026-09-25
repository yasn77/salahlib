#!/usr/bin/env python3
"""Fetch golden vectors from the AlAdhan API (MANUAL — not in CI)."""
import json
import urllib.request
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "shared" / "vectors" / "aladhan"
CASES = [
    ("london_isna", "24-04-2014", 51.508515, -0.1254872, 2, 0),
    ("london_mwl", "24-04-2014", 51.508515, -0.1254872, 3, 0),
    ("makkah", "20-02-2024", 21.3890824, 39.8579118, 4, 0),
    ("makkah_ramadan", "11-03-2024", 21.3890824, 39.8579118, 4, 0),
    ("ankara_turkey", "24-04-2024", 39.9333635, 32.8597419, 13, 0),
    ("sydney_south", "20-06-2024", -33.8688, 151.2093, 3, 0),
    ("high_lat_65n", "20-06-2024", 65.0, 20.0, 3, 0),
]


def fetch(date_str, lat, lng, method, school):
    url = (f"https://api.aladhan.com/v1/timings/{date_str}"
           f"?latitude={lat}&longitude={lng}&method={method}&school={school}")
    with urllib.request.urlopen(url, timeout=30) as r:
        return json.load(r)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for name, date_str, lat, lng, method, school in CASES:
        data = fetch(date_str, lat, lng, method, school)
        (OUT / f"{name}.json").write_text(json.dumps(data["data"], indent=2))
        print(f"wrote {name}.json")


if __name__ == "__main__":
    main()
