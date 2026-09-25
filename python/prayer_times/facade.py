"""Public API: PrayerTimes facade."""
from datetime import datetime
from zoneinfo import ZoneInfo

from .astronomy import calculate, format_time
from .methods import method_meta, resolve
from .params import Offsets


def _tz_offset_hours(y, m, d, tz):
    return datetime(y, m, d, tzinfo=ZoneInfo(tz)).utcoffset().total_seconds() / 3600.0


def _fmt(t, fmt):
    if fmt == "Float":
        return t
    if fmt == "24h":
        return format_time(t)
    if fmt == "12h":
        s = format_time(t)
        h = int(s.split(":")[0])
        suffix = "am" if h < 12 else "pm"
        return f"{((h + 11) % 12) + 1}:{s.split(':')[1]} {suffix}"
    if fmt == "12hNS":
        s = format_time(t)
        return f"{((int(s.split(':')[0]) + 11) % 12) + 1}:{s.split(':')[1]}"
    raise ValueError(f"unknown format: {fmt}")


class PrayerTimes:
    def __init__(self, method, school="STANDARD", asr_shadow_factor=None):
        self.method = method
        self.school = school
        self.asr_shadow_factor = asr_shadow_factor

    def get_times(self, dt, latitude, longitude, elevation=0.0,
                  lat_adjust="ANGLE_BASED", midnight_mode=None, tz="UTC",
                  fmt="24h", is_ramadan=False, tune=None):
        y, m, d = dt.year, dt.month, dt.day
        midnight = midnight_mode or "STANDARD"
        params = resolve(
            self.method, school=self.school, asr_factor=self.asr_shadow_factor,
            lat_adjust=lat_adjust, midnight_mode=midnight,
            is_ramadan=is_ramadan, offsets=tune,
            timezone_offset_hours=_tz_offset_hours(y, m, d, tz),
        )
        raw = calculate(y, m, d, latitude, longitude, elevation, params)
        return {k: _fmt(v, fmt) for k, v in raw.items()}

    def to_aladhan_response(self, dt, latitude, longitude, elevation=0.0,
                            lat_adjust="ANGLE_BASED", midnight_mode=None, tz="UTC",
                            is_ramadan=False, tune=None):
        y, m, d = dt.year, dt.month, dt.day
        midnight = midnight_mode or "STANDARD"
        _, entry = method_meta(self.method)
        params = resolve(
            self.method, school=self.school, asr_factor=self.asr_shadow_factor,
            lat_adjust=lat_adjust, midnight_mode=midnight,
            is_ramadan=is_ramadan, offsets=tune,
            timezone_offset_hours=_tz_offset_hours(y, m, d, tz),
        )
        raw = calculate(y, m, d, latitude, longitude, elevation, params)
        timings = {k: format_time(v) for k, v in raw.items()}
        off = dict(entry.get("defaultTune", {}))
        if is_ramadan:
            off.update(entry.get("ramadanTune", {}))
        offset_meta = {}
        for k in Offsets.__dataclass_fields__:
            keyname = k.capitalize()
            offset_meta[k] = int(off.get(keyname, 0))
        if tune:
            for k, v in tune.items():
                if v != 0:
                    offset_meta[k.lower()] = str(v)
        meta = {
            "latitude": latitude, "longitude": longitude, "timezone": tz,
            "method": {
                "id": entry["id"], "name": entry.get("name", ""),
                "params": entry.get("params", {}),
                "location": entry.get("location"),
            },
            "latitudeAdjustmentMethod": lat_adjust,
            "midnightMode": midnight,
            "school": self.school,
            "offset": {k.capitalize(): v for k, v in offset_meta.items()},
        }
        if str(self.method) == "15" or self.method == "MOONSIGHTING":
            meta["latitudeAdjustmentMethod"] = "NONE"
        return {"timings": timings, "meta": meta}
