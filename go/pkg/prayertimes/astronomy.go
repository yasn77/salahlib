package prayertimes

import (
	"fmt"
	"math"
)

func mod(a, b float64) float64 {
	r := math.Mod(a, b)
	if r < 0 {
		r += b
	}
	return r
}

func dtr(d float64) float64 { return d * math.Pi / 180.0 }
func rtd(r float64) float64 { return r * 180.0 / math.Pi }

func sin(d float64) float64 { return math.Sin(dtr(d)) }
func cos(d float64) float64 { return math.Cos(dtr(d)) }
func tan(d float64) float64 { return math.Tan(dtr(d)) }

func arcsin(x float64) float64 { return rtd(math.Asin(x)) }
func arccos(x float64) float64 { return rtd(math.Acos(x)) }
func arccot(x float64) float64 { return rtd(math.Atan(1.0 / x)) }
func arctan2(y, x float64) float64 {
	return rtd(math.Atan2(y, x))
}

func julianDay(y, m, d int) float64 {
	if m <= 2 {
		y--
		m += 12
	}
	a := math.Floor(float64(y) / 100)
	b := 2 - a + math.Floor(a/4)
	return math.Floor(365.25*float64(y+4716)) + math.Floor(30.6001*float64(m+1)) + float64(d) + b - 1524.5
}

func solarPositionAt(jd float64) (decl, eqt float64) {
	d := jd - 2451545.0
	g := mod(357.529+0.98560028*d, 360.0)
	q := mod(280.459+0.98564736*d, 360.0)
	l := mod(q+1.915*sin(g)+0.020*sin(2*g), 360.0)
	e := 23.439 - 0.00000036*d
	ra := mod(arctan2(cos(e)*sin(l), cos(l))/15.0, 24.0)
	return arcsin(sin(e) * sin(l)), q/15.0 - ra
}

func solarNoon(y, m, d int, time, longitude float64) float64 {
	jd := julianDay(y, m, d) + time/24.0 - longitude/(15.0*24.0)
	_, eqt := solarPositionAt(jd)
	return mod(12.0-eqt, 24.0)
}

func horizonAngle(elevation float64) float64 {
	return 0.833 + 0.0347*math.Sqrt(elevation)
}

func asrShadowAngle(p Params, y, m, d int, time, latitude float64) float64 {
	jd := julianDay(y, m, d) + 1.0 + time/24.0
	decl, _ := solarPositionAt(jd)
	return -arccot(p.AsrFactor + tan(math.Abs(latitude-decl)))
}

func depressionTime(angle float64, y, m, d int, time, latitude, longitude float64, direction int, policy Unreached) (float64, bool) {
	jd := julianDay(y, m, d) + time/24.0 - longitude/(15.0*24.0)
	decl, _ := solarPositionAt(jd)
	noon := solarNoon(y, m, d, time, longitude)
	numerator := -sin(angle) - sin(latitude)*sin(decl)
	denominator := cos(latitude) * cos(decl)
	ratio := numerator / denominator
	reached := ratio >= -1.0 && ratio <= 1.0
	if policy == UnreachedClamp {
		ratio = math.Max(-1.0, math.Min(1.0, ratio))
	} else if !reached {
		return math.NaN(), false
	}
	t := arccos(ratio) / 15.0
	return noon + float64(direction)*t, reached
}

func nightFraction(la LatAdjust, angle, night float64) float64 {
	switch la {
	case LatMiddleOfNight:
		return night / 2.0
	case LatOneSeventh:
		return night / 7.0
	default:
		return angle / 60.0 * night
	}
}

// RawTimes holds float "hours of day" for every prayer.
type RawTimes struct {
	Fajr, Sunrise, Dhuhr, Asr, Sunset, Maghrib, Isha, Imsak float64
	Midnight, Firstthird, Lastthird                         float64
}

// Calculate is the pure kernel.
func Calculate(y, m, d int, latitude, longitude, elevation float64, p Params) RawTimes {
	horizon := horizonAngle(elevation)
	ang := func(angle, time float64, dir int) (float64, bool) {
		return depressionTime(angle, y, m, d, time, latitude, longitude, dir, p.UnreachedPolicy)
	}

	fajr, fajrReached := ang(p.FajrAngle, 5.0, -1)
	sunrise, _ := ang(horizon, 6.0, -1)
	dhuhr := solarNoon(y, m, d, 12.0, longitude)
	asrAngle := asrShadowAngle(p, y, m, d, 13.0, latitude)
	asr, _ := ang(asrAngle, 13.0, 1)
	sunset, _ := ang(horizon, 18.0, 1)
	maghrib, maghribReached := ang(p.Maghrib, 18.0, 1)
	isha, ishaReached := ang(p.Isha, 18.0, 1)

	if p.LatAdjust != LatNone {
		night := mod(sunrise-sunset, 24.0)
		fallback := func(t, base, angle float64, dir int, reached bool) float64 {
			portion := nightFraction(p.LatAdjust, angle, night)
			if !reached || (t-base)*float64(dir) > portion {
				return base + portion*float64(dir)
			}
			return t
		}
		fajr = fallback(fajr, sunrise, p.FajrAngle, -1, fajrReached)
		isha = fallback(isha, sunset, p.Isha, 1, ishaReached)
		maghrib = fallback(maghrib, sunset, p.Maghrib, 1, maghribReached)
	}

	tz := p.TimezoneOffsetHours - longitude/15.0
	fajr += tz
	sunrise += tz
	dhuhr += tz
	asr += tz
	sunset += tz
	maghrib += tz
	isha += tz

	if p.MaghribIsMinutes {
		maghrib = sunset + p.Maghrib/60.0
	}
	if p.IshaIsMinutes {
		isha = maghrib + p.Isha/60.0
	}
	dhuhr += p.DhuhrMins / 60.0
	imsak := fajr - p.ImsakMins/60.0

	var diff float64
	if p.MidnightMode == MidJafari {
		diff = mod(fajr-sunset, 24.0)
	} else {
		diff = mod(sunrise-sunset, 24.0)
	}
	midnight := sunset + diff/2.0
	firstthird := sunset + diff/3.0
	lastthird := sunset + 2.0*diff/3.0

	o := p.Offsets
	imsak += o.Imsak / 60.0
	fajr += o.Fajr / 60.0
	sunrise += o.Sunrise / 60.0
	dhuhr += o.Dhuhr / 60.0
	asr += o.Asr / 60.0
	maghrib += o.Maghrib / 60.0
	sunset += o.Sunset / 60.0
	isha += o.Isha / 60.0
	midnight += o.Midnight / 60.0

	return RawTimes{
		Fajr: fajr, Sunrise: sunrise, Dhuhr: dhuhr, Asr: asr,
		Sunset: sunset, Maghrib: maghrib, Isha: isha, Imsak: imsak,
		Midnight: midnight, Firstthird: firstthird, Lastthird: lastthird,
	}
}

// FormatTime renders a float hour as 24h "HH:MM".
func FormatTime(t float64) string {
	if math.IsNaN(t) {
		return "-----"
	}
	x := mod(t+0.5/60.0, 24.0)
	h := int(math.Floor(x))
	mm := int(math.Floor((x - float64(h)) * 60.0))
	return fmt.Sprintf("%02d:%02d", h, mm)
}
