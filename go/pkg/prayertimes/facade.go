package prayertimes

import "time"

// PrayerTimes is the public facade.
type PrayerTimes struct {
	Method string
	School string
}

// New constructs a facade for a method name/id.
func New(method, school string) *PrayerTimes {
	if school == "" {
		school = "STANDARD"
	}
	return &PrayerTimes{Method: method, School: school}
}

// GetTimes computes 24h strings for a date/location/timezone.
func (p *PrayerTimes) GetTimes(date time.Time, latitude, longitude float64, tz string) map[string]string {
	loc, err := time.LoadLocation(tz)
	if err != nil {
		loc = time.UTC
	}
	_, offset := date.In(loc).Zone()
	offsetHours := float64(offset) / 3600.0
	params, err := Resolve(p.Method, p.School, nil, LatAngleBased, MidStandard, UnreachedClamp, false, nil, offsetHours)
	if err != nil {
		return nil
	}
	raw := Calculate(date.Year(), int(date.Month()), date.Day(), latitude, longitude, 0, params)
	return map[string]string{
		"Fajr": FormatTime(raw.Fajr), "Sunrise": FormatTime(raw.Sunrise),
		"Dhuhr": FormatTime(raw.Dhuhr), "Asr": FormatTime(raw.Asr),
		"Sunset": FormatTime(raw.Sunset), "Maghrib": FormatTime(raw.Maghrib),
		"Isha": FormatTime(raw.Isha), "Imsak": FormatTime(raw.Imsak),
		"Midnight":   FormatTime(raw.Midnight),
		"Firstthird": FormatTime(raw.Firstthird), "Lastthird": FormatTime(raw.Lastthird),
	}
}
