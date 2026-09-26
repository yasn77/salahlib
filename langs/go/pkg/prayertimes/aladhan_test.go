package prayertimes

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"strconv"
	"strings"
	"testing"
	"time"
)

type vectorData struct {
	Date struct {
		Gregorian struct {
			Date string `json:"date"`
		} `json:"gregorian"`
	} `json:"date"`
	Meta struct {
		Method struct {
			ID int `json:"id"`
		} `json:"method"`
		Latitude  float64 `json:"latitude"`
		Longitude float64 `json:"longitude"`
		Timezone  string  `json:"timezone"`
		School    string  `json:"school"`
	} `json:"meta"`
	Timings map[string]string `json:"timings"`
}

func tzOffsetHours(y, m, d int, tz string) float64 {
	loc, err := time.LoadLocation(tz)
	if err != nil {
		loc = time.UTC
	}
	_, offset := time.Date(y, time.Month(m), d, 0, 0, 0, 0, loc).Zone()
	return float64(offset) / 3600.0
}

func hhmmToMin(s string) int {
	var h, m int
	fmt.Sscanf(s, "%d:%d", &h, &m)
	return h*60 + m
}

func TestAlAdhanGoldenVectors(t *testing.T) {
	matches, err := filepath.Glob("../../../../shared/vectors/aladhan/*.json")
	if err != nil || len(matches) == 0 {
		t.Fatalf("no golden vectors found: %v", err)
	}
	for _, f := range matches {
		data, err := os.ReadFile(f)
		if err != nil {
			t.Fatalf("read %s: %v", f, err)
		}
		var v vectorData
		if err := json.Unmarshal(data, &v); err != nil {
			t.Fatalf("parse %s: %v", f, err)
		}
		var d, mo, y int
		if _, err := fmt.Sscanf(v.Date.Gregorian.Date, "%d-%d-%d", &d, &mo, &y); err != nil {
			t.Fatalf("date %s: %v", v.Date.Gregorian.Date, err)
		}
		school := v.Meta.School
		if school == "" {
			school = "STANDARD"
		}
		isRamadan := strings.Contains(f, "makkah_ramadan")
		params, err := Resolve(strconv.Itoa(v.Meta.Method.ID), school, nil, LatAngleBased, MidStandard, UnreachedClamp, isRamadan, nil, tzOffsetHours(y, mo, d, v.Meta.Timezone))
		if err != nil {
			t.Fatalf("resolve %s: %v", f, err)
		}
		raw := Calculate(y, mo, d, v.Meta.Latitude, v.Meta.Longitude, 0, params)
		got := map[string]string{
			"Fajr": FormatTime(raw.Fajr), "Sunrise": FormatTime(raw.Sunrise),
			"Dhuhr": FormatTime(raw.Dhuhr), "Asr": FormatTime(raw.Asr),
			"Sunset": FormatTime(raw.Sunset), "Maghrib": FormatTime(raw.Maghrib),
			"Isha": FormatTime(raw.Isha), "Imsak": FormatTime(raw.Imsak),
		}
		for _, k := range []string{"Fajr", "Sunrise", "Dhuhr", "Sunset", "Maghrib", "Isha", "Imsak"} {
			if got[k] != v.Timings[k] {
				t.Errorf("%s %s: got %s want %s", filepath.Base(f), k, got[k], v.Timings[k])
			}
		}
		// Asr: allow ±1 minute (now-fill envelope, SPEC §13.2)
		diff := hhmmToMin(got["Asr"]) - hhmmToMin(v.Timings["Asr"])
		if diff > 1 || diff < -1 {
			t.Errorf("%s Asr: got %s want %s", filepath.Base(f), got["Asr"], v.Timings["Asr"])
		}
	}
}
