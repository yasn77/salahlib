from salahlib.astronomy import calculate, format_time
from salahlib.params import LatAdjust, Midnight, Offsets, Params, Unreached


def _params(**kw):
    defaults = {
        "fajr_angle": 15.0, "isha": 15.0, "isha_is_minutes": False,
        "maghrib": 0.0, "maghrib_is_minutes": True,
        "imsak_mins": 10.0, "dhuhr_mins": 0.0, "asr_factor": 1.0,
        "lat_adjust": LatAdjust.ANGLE_BASED, "midnight_mode": Midnight.STANDARD,
        "unreached_policy": Unreached.CLAMP, "offsets": Offsets(),
        "timezone_offset_hours": 1.0,
    }
    defaults.update(kw)
    return Params(**defaults)


def test_london_isna_2014():
    t = calculate(2014, 4, 24, 51.508515, -0.1254872, 0, _params())
    got = {k: format_time(v) for k, v in t.items()}
    assert got["Fajr"] == "03:57"
    assert got["Sunrise"] == "05:46"
    assert got["Dhuhr"] == "12:59"
    assert got["Asr"] == "16:54"
    assert got["Sunset"] == "20:12"
    assert got["Maghrib"] == "20:12"
    assert got["Isha"] == "22:02"
    assert got["Imsak"] == "03:47"
    assert got["Midnight"] == "00:59"


def test_asr_canary_64n():
    # tz=0 (UTC): the Asr Julian-epoch quirk yields 11:35; a "cleaned" kernel yields 11:44.
    p = _params(timezone_offset_hours=0.0)
    t = calculate(2024, 1, 22, 64.0, 20.0, 0, p)
    assert format_time(t["Asr"]) == "11:35"
