#include "prayer_times.h"
#include <math.h>
#include <stdio.h>
#include <string.h>

/* Golden values from shared/vectors/aladhan/*.json (AlAdhan API).
 * C is kernel-only, so params are resolved manually from methods.json. */

static double mod_impl(double a) {
    double r = fmod(a, 24.0);
    if (r < 0) r += 24.0;
    return r;
}

static void format(double t, char *buf) {
    double x = mod_impl(t) + 0.5 / 60.0;
    while (x >= 24) x -= 24;
    int h = (int)floor(x);
    int mm = (int)floor((x - h) * 60.0);
    sprintf(buf, "%02d:%02d", h, mm);
}

static int check(double t, const char *want) {
    char buf[8];
    format(t, buf);
    if (strcmp(buf, want) != 0) {
        printf("FAIL: got %s want %s\n", buf, want);
        return 1;
    }
    return 0;
}

int main(void) {
    int fail = 0;
    pt_times t;

    /* Case 1: London ISNA 2014-04-24 (BST = UTC+1) */
    {
        pt_params p = {0};
        p.fajr_angle = 15; p.isha = 15; p.maghrib_is_minutes = 1; p.imsak_mins = 10; p.asr_factor = 1;
        p.lat_adjust = 3; p.tz_offset_hours = 1.0;
        pt_calculate(2014, 4, 24, 51.508515, -0.1254872, 0, &p, &t);
        fail |= check(t.fajr, "03:57");
        fail |= check(t.sunrise, "05:46");
        fail |= check(t.dhuhr, "12:59");
        fail |= check(t.sunset, "20:12");
        fail |= check(t.maghrib, "20:12");
        fail |= check(t.isha, "22:02");
        fail |= check(t.imsak, "03:47");
        fail |= check(t.midnight, "00:59");
    }
    /* Case 2: London MWL 2014-04-24 (BST = UTC+1) */
    {
        pt_params p = {0};
        p.fajr_angle = 18; p.isha = 17; p.maghrib_is_minutes = 1; p.imsak_mins = 10; p.asr_factor = 1;
        p.lat_adjust = 3; p.tz_offset_hours = 1.0;
        pt_calculate(2014, 4, 24, 51.508515, -0.1254872, 0, &p, &t);
        fail |= check(t.fajr, "03:28");
        fail |= check(t.isha, "22:21");
        fail |= check(t.imsak, "03:18");
    }
    /* Case 3: Sydney MWL 2024-06-20 (AEST = UTC+10, southern hemisphere) */
    {
        pt_params p = {0};
        p.fajr_angle = 18; p.isha = 17; p.maghrib_is_minutes = 1; p.imsak_mins = 10; p.asr_factor = 1;
        p.lat_adjust = 3; p.tz_offset_hours = 10.0;
        pt_calculate(2024, 6, 20, -33.8688, 151.2093, 0, &p, &t);
        fail |= check(t.fajr, "05:30");
        fail |= check(t.sunrise, "07:00");
        fail |= check(t.dhuhr, "11:57");
        fail |= check(t.sunset, "16:54");
        fail |= check(t.isha, "18:18");
        fail |= check(t.imsak, "05:20");
        fail |= check(t.midnight, "23:57");
    }

    if (fail) return 1;
    printf("aladhan ok\n");
    return 0;
}
