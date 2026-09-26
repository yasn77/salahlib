#include "prayer_times.h"
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
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

static int check_within(double t, const char *want, int tol_min) {
    char buf[8];
    int got_h, got_m, want_h, want_m;
    format(t, buf);
    sscanf(buf, "%d:%d", &got_h, &got_m);
    sscanf(want, "%d:%d", &want_h, &want_m);
    int got = got_h * 60 + got_m;
    int w = want_h * 60 + want_m;
    if (abs(got - w) > tol_min) {
        printf("FAIL(within %d min): got %s want %s\n", tol_min, buf, want);
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
    /* Case 4: London Moonsighting 2024-10-15 (shafaq=general) */
    {
        pt_params p = {0};
        p.shafaq = "general"; p.imsak_mins = 10; p.asr_factor = 1;
        p.lat_adjust = 3; p.tz_offset_hours = 1.0;
        pt_calculate(2024, 10, 15, 51.508515, -0.1254872, 0, &p, &t);
        fail |= check(t.fajr, "05:50");
        fail |= check(t.isha, "19:28");
    }
    /* Case 5: ISO8601 formatting (London ISNA 2014-04-24) */
    {
        char buf[32];
        pt_params p = {0};
        p.fajr_angle = 15; p.isha = 15; p.maghrib_is_minutes = 1; p.imsak_mins = 10; p.asr_factor = 1;
        p.lat_adjust = 3; p.tz_offset_hours = 1.0;
        pt_calculate(2014, 4, 24, 51.508515, -0.1254872, 0, &p, &t);
        pt_format_iso8601(t.fajr, 2014, 4, 24, 1.0, buf, sizeof(buf));
        if (strcmp(buf, "2014-04-24T03:57:00+01:00") != 0) { printf("FAIL iso8601 fajr: got %s\n", buf); fail |= 1; }
        pt_format_iso8601(t.midnight, 2014, 4, 24, 1.0, buf, sizeof(buf));
        if (strcmp(buf, "2014-04-25T00:59:00+01:00") != 0) { printf("FAIL iso8601 midnight: got %s\n", buf); fail |= 1; }
    }

    /* Case 6: London Unified Prayer Timetable 2026-09-26 (Charing Cross, BST) */
    {
        pt_params p = {0};
        if (pt_resolve_method("LUT", 0, 0, &p) != 0) { printf("FAIL LUT resolve\n"); fail |= 1; }
        else {
            p.tz_offset_hours = 1.0;
            pt_calculate(2026, 9, 26, 51.5073, -0.12755, 0, &p, &t);
            fail |= check_within(t.sunrise, "06:50", 1);
            fail |= check_within(t.dhuhr, "12:57", 1);
            fail |= check_within(t.maghrib, "18:53", 1);
            fail |= check_within(t.asr, "16:05", 5);
            fail |= check_within(t.fajr, "05:22", 5);
            fail |= check_within(t.isha, "20:10", 5);
        }
    }

    if (fail) return 1;
    printf("aladhan ok\n");
    return 0;
}
