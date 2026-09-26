package prayertimes

type LatAdjust string

const (
	LatNone          LatAdjust = "NONE"
	LatMiddleOfNight LatAdjust = "MIDDLE_OF_THE_NIGHT"
	LatOneSeventh    LatAdjust = "ONE_SEVENTH"
	LatAngleBased    LatAdjust = "ANGLE_BASED"
)

type Midnight string

const (
	MidStandard Midnight = "STANDARD"
	MidJafari   Midnight = "JAFARI"
)

type Unreached string

const (
	UnreachedClamp Unreached = "CLAMP"
	UnreachedNaN   Unreached = "NAN"
)

type Offsets struct {
	Imsak, Fajr, Sunrise, Dhuhr, Asr, Maghrib, Sunset, Isha, Midnight float64
}

type Params struct {
	FajrAngle           float64
	Isha                float64
	IshaIsMinutes       bool
	Maghrib             float64
	MaghribIsMinutes    bool
	ImsakMins           float64
	DhuhrMins           float64
	AsrFactor           float64
	LatAdjust           LatAdjust
	MidnightMode        Midnight
	UnreachedPolicy     Unreached
	Offsets             Offsets
	TimezoneOffsetHours float64
	Shafaq              string // "general"/"ahmer"/"abyad" for MOONSIGHTING, else ""
}
