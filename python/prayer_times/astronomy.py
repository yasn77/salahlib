"""Pure calculation kernel. Numbers and enums in, float hours out."""
import math
from datetime import date

from .params import LatAdjust, Midnight, Params, Unreached


def mod(a: float, b: float) -> float:
    return (a % b + b) % b


def dtr(d: float) -> float:
    return d * math.pi / 180.0


def rtd(r: float) -> float:
    return r * 180.0 / math.pi


def sin(d: float) -> float:
    return math.sin(dtr(d))


def cos(d: float) -> float:
    return math.cos(dtr(d))


def tan(d: float) -> float:
    return math.tan(dtr(d))


def arcsin(x: float) -> float:
    return rtd(math.asin(x))


def arccos(x: float) -> float:
    return rtd(math.acos(x))


def arccot(x: float) -> float:
    return rtd(math.atan(1.0 / x))


def arctan2(y: float, x: float) -> float:
    return rtd(math.atan2(y, x))


def julian_day(y: int, m: int, d: int) -> float:
    if m <= 2:
        y -= 1
        m += 12
    a = math.floor(y / 100)
    b = 2 - a + math.floor(a / 4)
    return math.floor(365.25 * (y + 4716)) + math.floor(30.6001 * (m + 1)) + d + b - 1524.5


def solar_position_at(jd: float):
    """Return (declination, equation_of_time) at a Julian day."""
    d = jd - 2451545.0
    g = mod(357.529 + 0.98560028 * d, 360.0)
    q = mod(280.459 + 0.98564736 * d, 360.0)
    l = mod(q + 1.915 * sin(g) + 0.020 * sin(2 * g), 360.0)
    e = 23.439 - 0.00000036 * d
    ra = mod(arctan2(cos(e) * sin(l), cos(l)) / 15.0, 24.0)
    decl = arcsin(sin(e) * sin(l))
    eqt = q / 15.0 - ra
    return decl, eqt


def solar_noon(y: int, m: int, d: int, time: float, longitude: float) -> float:
    jd = julian_day(y, m, d) + time / 24.0 - longitude / (15.0 * 24.0)
    _, eqt = solar_position_at(jd)
    return mod(12.0 - eqt, 24.0)


def horizon_angle(elevation: float) -> float:
    return 0.833 + 0.0347 * math.sqrt(elevation)


def asr_shadow_angle(params: Params, y: int, m: int, d: int, time: float, latitude: float) -> float:
    # Asr samples declination one day ahead, no meridian correction (SPEC §13.2).
    jd = julian_day(y, m, d) + 1.0 + time / 24.0
    decl, _ = solar_position_at(jd)
    return -arccot(params.asr_factor + tan(abs(latitude - decl)))


def depression_time(angle, y, m, d, time, latitude, longitude, direction, policy):
    jd = julian_day(y, m, d) + time / 24.0 - longitude / (15.0 * 24.0)
    decl, _ = solar_position_at(jd)
    noon = solar_noon(y, m, d, time, longitude)
    numerator = -sin(angle) - sin(latitude) * sin(decl)
    denominator = cos(latitude) * cos(decl)
    ratio = numerator / denominator
    reached = -1.0 <= ratio <= 1.0
    if policy == Unreached.CLAMP:
        ratio = max(-1.0, min(1.0, ratio))
    elif not reached:
        return float("nan"), False
    t = arccos(ratio) / 15.0
    return noon + direction * t, reached


def _night_fraction(lat_adjust, angle, night):
    if lat_adjust == LatAdjust.MIDDLE_OF_THE_NIGHT:
        return night / 2.0
    if lat_adjust == LatAdjust.ONE_SEVENTH:
        return night / 7.0
    return (angle / 60.0) * night


def round_away(x: float) -> float:
    """Round half away from zero (PHP/Go round(); Python round() is half-even)."""
    return math.floor(x + 0.5) if x >= 0 else math.ceil(x - 0.5)


def _dyy(y: int, m: int, d: int, latitude: float) -> int:
    """Days since the hemisphere's solstice anchor (SPEC §11)."""
    anchor_m, anchor_d = (12, 21) if latitude > 0 else (6, 21)
    n = (date(y, m, d) - date(y, anchor_m, anchor_d)).days
    if n >= 2:
        return n - 1
    if n >= 0:
        return 365
    return 365 + n


def _interpolate(a: float, b: float, c: float, d: float, dyy: int) -> float:
    if dyy < 91:
        return a + (b - a) / 91 * dyy
    if dyy < 137:
        return b + (c - b) / 46 * (dyy - 91)
    if dyy < 183:
        return c + (d - c) / 46 * (dyy - 137)
    if dyy < 229:
        return d + (c - d) / 46 * (dyy - 183)
    if dyy < 275:
        return c + (b - c) / 46 * (dyy - 229)
    return b + (a - b) / 91 * (dyy - 275)


def _fajr_minutes(latitude: float, dyy: int) -> float:
    a = 75 + 28.65 / 55 * abs(latitude)
    b = 75 + 19.44 / 55 * abs(latitude)
    c = 75 + 32.74 / 55 * abs(latitude)
    d = 75 + 48.10 / 55 * abs(latitude)
    return _interpolate(a, b, c, d, dyy)


def _isha_minutes(latitude: float, dyy: int, shafaq: str) -> float:
    if shafaq == "ahmer":
        a, b, c, d = 62 + 17.4 / 55 * abs(latitude), 62 - 7.16 / 55 * abs(latitude), 62 + 5.12 / 55 * abs(latitude), 62 + 19.44 / 55 * abs(latitude)
    elif shafaq == "abyad":
        a, b, c, d = 75 + 25.6 / 55 * abs(latitude), 75 + 7.16 / 55 * abs(latitude), 75 + 36.84 / 55 * abs(latitude), 75 + 81.84 / 55 * abs(latitude)
    else:  # general
        a, b, c, d = 75 + 25.6 / 55 * abs(latitude), 75 + 2.05 / 55 * abs(latitude), 75 - 9.21 / 55 * abs(latitude), 75 + 6.14 / 55 * abs(latitude)
    return _interpolate(a, b, c, d, dyy)


def calculate(y: int, m: int, d: int, latitude: float, longitude: float,
              elevation: float, params: Params) -> dict:
    horizon = horizon_angle(elevation)

    def ang(angle, time, direction):
        return depression_time(angle, y, m, d, time, latitude, longitude, direction,
                               params.unreached_policy)

    fajr, fajr_reached = ang(params.fajr_angle, 5.0, -1)
    sunrise, _ = ang(horizon, 6.0, -1)
    dhuhr = solar_noon(y, m, d, 12.0, longitude)
    asr_angle = asr_shadow_angle(params, y, m, d, 13.0, latitude)
    asr, _ = ang(asr_angle, 13.0, 1)
    sunset, _ = ang(horizon, 18.0, 1)
    maghrib, maghrib_reached = ang(params.maghrib, 18.0, 1)
    isha, isha_reached = ang(params.isha, 18.0, 1)

    if params.lat_adjust != LatAdjust.NONE:
        night = mod(sunrise - sunset, 24.0)

        def fallback(t, base, angle, direction, reached):
            p = _night_fraction(params.lat_adjust, angle, night)
            if (not reached) or ((t - base) * direction > p):
                return base + p * direction
            return t

        fajr = fallback(fajr, sunrise, params.fajr_angle, -1, fajr_reached)
        isha = fallback(isha, sunset, params.isha, 1, isha_reached)
        maghrib = fallback(maghrib, sunset, params.maghrib, 1, maghrib_reached)

    tz = params.timezone_offset_hours - longitude / 15.0
    fajr += tz
    sunrise += tz
    dhuhr += tz
    asr += tz
    sunset += tz
    maghrib += tz
    isha += tz

    if params.maghrib_is_minutes:
        maghrib = sunset + params.maghrib / 60.0
    if params.isha_is_minutes:
        isha = maghrib + params.isha / 60.0
    dhuhr += params.dhuhr_mins / 60.0
    imsak = fajr - params.imsak_mins / 60.0

    diff = mod(fajr - sunset, 24.0) if params.midnight_mode == Midnight.JAFARI else mod(sunrise - sunset, 24.0)
    midnight = sunset + diff / 2.0
    firstthird = sunset + diff / 3.0
    lastthird = sunset + 2.0 * diff / 3.0

    # Moonsighting override (SPEC §11): runs after night times, before offsets.
    if params.shafaq is not None:
        dyy = _dyy(y, m, d, latitude)
        fajr = sunrise - round_away(_fajr_minutes(latitude, dyy)) / 60.0
        isha = sunset + round_away(_isha_minutes(latitude, dyy, params.shafaq)) / 60.0
        imsak = fajr - params.imsak_mins / 60.0

    o = params.offsets
    imsak += o.imsak / 60.0
    fajr += o.fajr / 60.0
    sunrise += o.sunrise / 60.0
    dhuhr += o.dhuhr / 60.0
    asr += o.asr / 60.0
    maghrib += o.maghrib / 60.0
    sunset += o.sunset / 60.0
    isha += o.isha / 60.0
    midnight += o.midnight / 60.0

    return {
        "Fajr": fajr, "Sunrise": sunrise, "Dhuhr": dhuhr, "Asr": asr,
        "Sunset": sunset, "Maghrib": maghrib, "Isha": isha, "Imsak": imsak,
        "Midnight": midnight, "Firstthird": firstthird, "Lastthird": lastthird,
    }


def format_time(time: float) -> str:
    if math.isnan(time):
        return "-----"
    t = mod(time + 0.5 / 60.0, 24.0)
    hours = math.floor(t)
    minutes = math.floor((t - hours) * 60.0)
    return f"{hours:02d}:{minutes:02d}"
