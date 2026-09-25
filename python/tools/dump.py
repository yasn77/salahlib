#!/usr/bin/env python3
"""Print raw float hours for parity. usage: dump.py y m d lat lng elev fajr isha isha_min dhuhr asr"""
import sys

from prayer_times.astronomy import calculate
from prayer_times.params import Params, LatAdjust, Midnight, Unreached, Offsets

args = [float(x) for x in sys.argv[1:]]
y, m, d = int(args[0]), int(args[1]), int(args[2])
lat, lng, elev = args[3], args[4], args[5]
p = Params(
    fajr_angle=args[6], isha=args[7], isha_is_minutes=bool(args[8]),
    maghrib=0.0, maghrib_is_minutes=False, imsak_mins=10.0, dhuhr_mins=args[9],
    asr_factor=args[10], lat_adjust=LatAdjust.ANGLE_BASED,
    midnight_mode=Midnight.STANDARD, unreached_policy=Unreached.CLAMP,
    offsets=Offsets(), timezone_offset_hours=0.0,
)
t = calculate(y, m, d, lat, lng, elev, p)
print(" ".join(f"{t[k]:.17g}" for k in
      ["Fajr", "Sunrise", "Dhuhr", "Asr", "Sunset", "Maghrib", "Isha", "Imsak",
       "Midnight", "Firstthird", "Lastthird"]))
