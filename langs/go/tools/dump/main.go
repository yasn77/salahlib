package main

import (
	"fmt"
	"os"
	"strconv"

	prayertimes "github.com/yasn77/salahlib/langs/go/pkg/prayertimes"
)

func main() {
	a := os.Args[1:]
	f := func(i int) float64 { v, _ := strconv.ParseFloat(a[i], 64); return v }
	ii := func(i int) int { v, _ := strconv.Atoi(a[i]); return v }
	p := prayertimes.Params{
		FajrAngle: f(6), Isha: f(7), IshaIsMinutes: ii(8) != 0,
		ImsakMins: 10, DhuhrMins: f(9), AsrFactor: f(10),
		LatAdjust: prayertimes.LatAngleBased, MidnightMode: prayertimes.MidStandard,
		UnreachedPolicy: prayertimes.UnreachedClamp,
	}
	t := prayertimes.Calculate(ii(0), ii(1), ii(2), f(3), f(4), f(5), p)
	fmt.Printf("%.17g %.17g %.17g %.17g %.17g %.17g %.17g %.17g %.17g %.17g %.17g\n",
		t.Fajr, t.Sunrise, t.Dhuhr, t.Asr, t.Sunset, t.Maghrib, t.Isha, t.Imsak,
		t.Midnight, t.Firstthird, t.Lastthird)
}
