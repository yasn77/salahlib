"""Public API: PrayerTimes facade."""
import math
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from .astronomy import calculate, format_time
from .methods import method_meta, resolve
from .params import Offsets


def _tz_offset_hours(y, m, d, tz):
    return datetime(y, m, d, tzinfo=ZoneInfo(tz)).utcoffset().total_seconds() / 3600.0


def _fmt(t, fmt, base=None):
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
    if fmt == "iso8601":
        # floor(time·60) for positive, ceil(−time·60) for negative, on the rounded un-wrapped time (SPEC §10).
        t2 = t + 0.5 / 60.0
        if t2 > 0:
            return (base + timedelta(minutes=math.floor(t2 * 60))).isoformat()
        return (base - timedelta(minutes=math.ceil(-t2 * 60))).isoformat()
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
        midnight_mode_resolved = midnight_mode or "STANDARD"
        params = resolve(
            self.method, school=self.school, asr_factor=self.asr_shadow_factor,
            lat_adjust=lat_adjust, midnight_mode=midnight_mode_resolved,
            is_ramadan=is_ramadan, offsets=tune,
            timezone_offset_hours=_tz_offset_hours(y, m, d, tz),
        )
        raw = calculate(y, m, d, latitude, longitude, elevation, params)
        base = datetime(y, m, d, tzinfo=ZoneInfo(tz))
        return {k: _fmt(v, fmt, base) for k, v in raw.items()}

    def to_aladhan_response(self, dt, latitude, longitude, elevation=0.0,
                            lat_adjust="ANGLE_BASED", midnight_mode=None, tz="UTC",
                            is_ramadan=False, tune=None):
        y, m, d = dt.year, dt.month, dt.day
        midnight_mode_resolved = midnight_mode or "STANDARD"
        key, entry = method_meta(self.method)
        params = resolve(
            self.method, school=self.school, asr_factor=self.asr_shadow_factor,
            lat_adjust=lat_adjust, midnight_mode=midnight_mode_resolved,
            is_ramadan=is_ramadan, offsets=tune,
            timezone_offset_hours=_tz_offset_hours(y, m, d, tz),
        )
        raw = calculate(y, m, d, latitude, longitude, elevation, params)
        timings = {k: format_time(v) for k, v in raw.items()}
        # meta.offset precedence: ramadanTune > user tune > defaultTune (SPEC §12).
        default = entry.get("defaultTune", {})
        ramadan = entry.get("ramadanTune", {}) if is_ramadan else {}
        user = {k: v for k, v in (tune or {}).items() if v != 0}
        offset_meta = {}
        for k in Offsets.__dataclass_fields__:
            keyname = k.capitalize()
            if keyname in ramadan:
                offset_meta[k] = int(ramadan[keyname])
            elif keyname in user:
                offset_meta[k] = str(user[keyname])
            elif keyname in default:
                offset_meta[k] = int(default[keyname])
            else:
                offset_meta[k] = 0
        method_obj = {
            "name": entry.get("name", ""),
            "params": entry.get("params", {}),
            "location": entry.get("location"),
        }
        if key != "CUSTOM":
            method_obj = {"id": entry["id"], **method_obj}
        meta = {
            "latitude": latitude, "longitude": longitude, "timezone": tz,
            "method": method_obj,
            "latitudeAdjustmentMethod": lat_adjust,
            "midnightMode": midnight_mode_resolved,
            "school": self.school,
            "offset": {k.capitalize(): v for k, v in offset_meta.items()},
        }
        if key == "MOONSIGHTING":
            meta["latitudeAdjustmentMethod"] = "NONE"
        return {"timings": timings, "meta": meta}
