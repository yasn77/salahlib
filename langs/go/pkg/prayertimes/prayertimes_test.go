package prayertimes

import "testing"

func testParams() Params {
	return Params{
		FajrAngle: 15, Isha: 15, MaghribIsMinutes: true, ImsakMins: 10, AsrFactor: 1,
		LatAdjust: LatAngleBased, MidnightMode: MidStandard,
		UnreachedPolicy: UnreachedClamp, TimezoneOffsetHours: 1.0,
	}
}

func TestLondonIsna2014(t *testing.T) {
	got := Calculate(2014, 4, 24, 51.508515, -0.1254872, 0, testParams())
	want := map[string]string{
		"Fajr": "03:57", "Sunrise": "05:46", "Dhuhr": "12:59", "Asr": "16:54",
		"Sunset": "20:12", "Maghrib": "20:12", "Isha": "22:02", "Imsak": "03:47",
		"Midnight": "00:59",
	}
	gotStr := map[string]string{
		"Fajr": FormatTime(got.Fajr), "Sunrise": FormatTime(got.Sunrise),
		"Dhuhr": FormatTime(got.Dhuhr), "Asr": FormatTime(got.Asr),
		"Sunset": FormatTime(got.Sunset), "Maghrib": FormatTime(got.Maghrib),
		"Isha": FormatTime(got.Isha), "Imsak": FormatTime(got.Imsak),
		"Midnight": FormatTime(got.Midnight),
	}
	for k, w := range want {
		if gotStr[k] != w {
			t.Fatalf("%s = %s, want %s", k, gotStr[k], w)
		}
	}
}

func TestAsrCanary64N(t *testing.T) {
	p := testParams()
	p.TimezoneOffsetHours = 0.0
	got := Calculate(2024, 1, 22, 64.0, 20.0, 0, p)
	if s := FormatTime(got.Asr); s != "11:35" {
		t.Fatalf("Asr = %s, want 11:35", s)
	}
}
