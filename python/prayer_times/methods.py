"""Resolve a method code/name from methods.json into a resolved Params."""
import json
import re
from pathlib import Path

from .params import LatAdjust, Midnight, Offsets, Params, Unreached

_DATA = json.loads((Path(__file__).parent / "data" / "methods.json").read_text())
_BY_ID = {str(v["id"]): k for k, v in _DATA.items()}


def _value(x):
    """Numeric-prefix coercion (SPEC §7): "90 min" -> 90.0, "4.5" -> 4.5, "JAFARI" -> 0.0."""
    m = re.match(r"[0-9.+\-]+", str(x))
    return float(m.group(0)) if m else 0.0


def _is_min(x):
    return "min" in str(x)


def method_codes():
    return list(_DATA.keys())


def method_meta(method):
    key = method if method in _DATA else _BY_ID.get(str(method))
    if key is None:
        raise KeyError(f"unknown method: {method}")
    return key, _DATA[key]


def resolve(method, school="STANDARD", asr_factor=None, lat_adjust="ANGLE_BASED",
            midnight_mode="STANDARD", unreached_policy="CLAMP", is_ramadan=False,
            offsets=None, timezone_offset_hours=0.0):
    key = method if method in _DATA else _BY_ID.get(str(method))
    if key is None:
        raise KeyError(f"unknown method: {method}")
    entry = _DATA[key]
    if key == "MOONSIGHTING":
        raise NotImplementedError("MOONSIGHTING backend is deferred (SPEC §11); not yet implemented")
    p = entry.get("params", {})

    fajr = _value(p.get("Fajr", 0))
    isha = p.get("Isha", 0)
    maghrib = p.get("Maghrib", "0 min")
    imsak = _value(p.get("Imsak", "10 min"))
    dhuhr = _value(p.get("Dhuhr", "0 min"))
    af = asr_factor if asr_factor is not None else (2.0 if school == "HANAFI" else 1.0)

    off = dict(entry.get("defaultTune", {}))
    if offsets:
        for k, v in offsets.items():
            if v != 0:
                off[k] = v
    # ramadanTune applied last: in Ramadan MAKKAH's Isha:30 overrides even a user value (SPEC §12).
    if is_ramadan:
        off.update(entry.get("ramadanTune", {}))
    o = Offsets(**{k.lower(): float(v) for k, v in off.items()})

    return Params(
        fajr_angle=fajr,
        isha=_value(isha), isha_is_minutes=_is_min(isha),
        maghrib=_value(maghrib), maghrib_is_minutes=_is_min(maghrib),
        imsak_mins=imsak, dhuhr_mins=dhuhr, asr_factor=af,
        lat_adjust=LatAdjust(lat_adjust),
        midnight_mode=Midnight(midnight_mode),
        unreached_policy=Unreached(unreached_policy),
        offsets=o,
        timezone_offset_hours=timezone_offset_hours,
    )
