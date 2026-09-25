package prayertimes

import (
	_ "embed"
	"encoding/json"
	"fmt"
	"regexp"
	"strconv"
)

//go:embed methods.json
var methodsJSON []byte

type methodEntry struct {
	ID          int                    `json:"id"`
	Name        string                 `json:"name"`
	Params      map[string]interface{} `json:"params"`
	Location    map[string]float64     `json:"location"`
	DefaultTune map[string]float64     `json:"defaultTune"`
	RamadanTune map[string]float64     `json:"ramadanTune"`
}

var methods map[string]methodEntry

func init() {
	methods = map[string]methodEntry{}
	if err := json.Unmarshal(methodsJSON, &methods); err != nil {
		panic(err)
	}
}

var numRe = regexp.MustCompile(`^[0-9.+\-]+`)
var minRe = regexp.MustCompile(`min`)

func value(x interface{}) float64 {
	m := numRe.FindString(fmt.Sprint(x))
	if m == "" {
		return 0
	}
	f, _ := strconv.ParseFloat(m, 64)
	return f
}

func isMin(x interface{}) bool {
	return minRe.MatchString(fmt.Sprint(x))
}

// Resolve converts a method code/name into a resolved Params.
func Resolve(method, school string, asrFactor *float64, latAdjust LatAdjust, midnight Midnight, policy Unreached, isRamadan bool, tune map[string]float64, tzOffset float64) (Params, error) {
	entry, ok := methods[method]
	if !ok {
		for _, v := range methods {
			if strconv.Itoa(v.ID) == method {
				entry, ok = v, true
				break
			}
		}
	}
	if !ok {
		return Params{}, fmt.Errorf("unknown method %s", method)
	}
	if entry.ID == 15 {
		return Params{}, fmt.Errorf("MOONSIGHTING backend is deferred (SPEC §11); not yet implemented")
	}
	p := entry.Params
	af := 1.0
	if asrFactor != nil {
		af = *asrFactor
	} else if school == "HANAFI" {
		af = 2.0
	}
	offsets := map[string]float64{}
	for k, v := range entry.DefaultTune {
		offsets[k] = v
	}
	if tune != nil {
		for k, v := range tune {
			if v != 0 {
				offsets[k] = v
			}
		}
	}
	// ramadanTune applied last: in Ramadan MAKKAH Isha:30 overrides even a user value (SPEC §12).
	if isRamadan {
		for k, v := range entry.RamadanTune {
			offsets[k] = v
		}
	}
	imsak := p["Imsak"]
	if imsak == nil {
		imsak = "10 min"
	}
	dhuhr := p["Dhuhr"]
	if dhuhr == nil {
		dhuhr = "0 min"
	}
	maghrib := p["Maghrib"]
	if maghrib == nil {
		maghrib = "0 min"
	}
	return Params{
		FajrAngle:        value(p["Fajr"]),
		Isha:             value(p["Isha"]),
		IshaIsMinutes:    isMin(p["Isha"]),
		Maghrib:          value(maghrib),
		MaghribIsMinutes: isMin(maghrib),
		ImsakMins:        value(imsak),
		DhuhrMins:        value(dhuhr),
		AsrFactor:        af,
		LatAdjust:        latAdjust,
		MidnightMode:     midnight,
		UnreachedPolicy:  policy,
		Offsets: Offsets{
			Imsak: offsets["Imsak"], Fajr: offsets["Fajr"], Sunrise: offsets["Sunrise"],
			Dhuhr: offsets["Dhuhr"], Asr: offsets["Asr"], Maghrib: offsets["Maghrib"],
			Sunset: offsets["Sunset"], Isha: offsets["Isha"], Midnight: offsets["Midnight"],
		},
		TimezoneOffsetHours: tzOffset,
	}, nil
}
