package prayertimes

import (
	"encoding/json"
	"os"
	"path/filepath"
	"testing"
	"time"
)

type lutVector struct {
	Latitude  float64 `json:"latitude"`
	Longitude float64 `json:"longitude"`
	Timezone  string  `json:"timezone"`
	Cases     []struct {
		Date    string            `json:"date"`
		Timings map[string]string `json:"timings"`
	} `json:"cases"`
}

func TestLutBlackbox(t *testing.T) {
	data, err := os.ReadFile(filepath.Join("..", "..", "..", "..", "shared", "vectors", "lut", "lut.json"))
	if err != nil {
		t.Fatalf("read lut fixture: %v", err)
	}
	var v lutVector
	if err := json.Unmarshal(data, &v); err != nil {
		t.Fatalf("parse lut fixture: %v", err)
	}
	pt := New("LUT", "STANDARD")
	for _, c := range v.Cases {
		d, err := time.Parse("2006-01-02", c.Date)
		if err != nil {
			t.Fatalf("date %s: %v", c.Date, err)
		}
		got := pt.GetTimes(d, v.Latitude, v.Longitude, v.Timezone)
		for _, k := range []string{"Sunrise", "Dhuhr", "Maghrib"} {
			if diff := hhmmToMin(got[k]) - hhmmToMin(c.Timings[k]); diff > 1 || diff < -1 {
				t.Errorf("%s %s: got %s want %s", c.Date, k, got[k], c.Timings[k])
			}
		}
		for _, k := range []string{"Asr", "Fajr", "Isha"} {
			if diff := hhmmToMin(got[k]) - hhmmToMin(c.Timings[k]); diff > 5 || diff < -5 {
				t.Errorf("%s %s: got %s want %s", c.Date, k, got[k], c.Timings[k])
			}
		}
	}
}
