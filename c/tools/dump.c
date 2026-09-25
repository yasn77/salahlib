#include "prayer_times.h"
#include <stdio.h>
#include <stdlib.h>

int main(int argc, char **argv) {
    if (argc < 12) { fprintf(stderr, "usage: dump y m d lat lng elev fajr isha isha_min dhuhr asr\n"); return 1; }
    int y = atoi(argv[1]), m = atoi(argv[2]), d = atoi(argv[3]);
    double lat = atof(argv[4]), lng = atof(argv[5]), elev = atof(argv[6]);
    pt_params p = {0};
    p.fajr_angle = atof(argv[7]);
    p.isha = atof(argv[8]);
    p.isha_is_minutes = atoi(argv[9]);
    p.dhuhr_mins = atof(argv[10]);
    p.asr_factor = atof(argv[11]);
    p.imsak_mins = 10;
    p.lat_adjust = 3;
    pt_times t;
    pt_calculate(y, m, d, lat, lng, elev, &p, &t);
    printf("%.17g %.17g %.17g %.17g %.17g %.17g %.17g %.17g %.17g %.17g %.17g\n",
           t.fajr, t.sunrise, t.dhuhr, t.asr, t.sunset, t.maghrib, t.isha, t.imsak,
           t.midnight, t.firstthird, t.lastthird);
    return 0;
}
