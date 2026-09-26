#include "prayer_times.h"
#include <math.h>
#include <stdio.h>
#include <string.h>

/* Verify pt_resolve_method maps methods.json (via methods_generated.h) into pt_params. */

static void format(double t, char *buf) {
    double x = fmod(t, 24.0);
    if (x < 0) x += 24.0;
    x += 0.5 / 60.0;
    while (x >= 24) x -= 24;
    int h = (int)floor(x);
    int mm = (int)floor((x - h) * 60.0);
    sprintf(buf, "%02d:%02d", h, mm);
}

int main(void) {
    int fail = 0;
    pt_params p;
    char buf[8];

    /* ISNA by name and by id */
    if (pt_resolve_method("ISNA", 0, 0, &p) != 0) { printf("FAIL: ISNA not resolved\n"); return 1; }
    if (p.fajr_angle != 15.0 || p.isha != 15.0) { printf("FAIL: ISNA fajr/isha\n"); fail |= 1; }
    if (p.isha_is_minutes || !p.maghrib_is_minutes) { printf("FAIL: ISNA minutes flags\n"); fail |= 1; }
    if (pt_resolve_method("2", 0, 0, &p) != 0 || p.fajr_angle != 15.0) { printf("FAIL: ISNA by id\n"); fail |= 1; }

    /* HANAFI school -> Asr factor 2 */
    if (pt_resolve_method("ISNA", 1, 0, &p) != 0 || p.asr_factor != 2.0) { printf("FAIL: hanafi asr\n"); fail |= 1; }

    /* TURKEY default tune offsets */
    if (pt_resolve_method("TURKEY", 0, 0, &p) != 0) { printf("FAIL: TURKEY\n"); return 1; }
    if (p.offset[2] != -7.0 || p.offset[3] != 5.0 || p.offset[4] != 4.0 || p.offset[5] != 7.0 || p.offset[6] != 7.0) {
        printf("FAIL: TURKEY default tune\n"); fail |= 1;
    }

    /* MAKKAH Ramadan -> Isha offset +30 */
    if (pt_resolve_method("MAKKAH", 0, 0, &p) != 0 || p.offset[7] != 0.0) { printf("FAIL: MAKKAH non-ramadan\n"); fail |= 1; }
    if (pt_resolve_method("MAKKAH", 0, 1, &p) != 0 || p.offset[7] != 30.0) { printf("FAIL: MAKKAH ramadan\n"); fail |= 1; }

    /* MOONSIGHTING -> shafaq general */
    if (pt_resolve_method("15", 0, 0, &p) != 0 || strcmp(p.shafaq, "general") != 0) { printf("FAIL: moonsighting shafaq\n"); fail |= 1; }

    /* Unknown method */
    if (pt_resolve_method("NOPE", 0, 0, &p) == 0) { printf("FAIL: unknown method should fail\n"); fail |= 1; }

    /* Full calculation via resolve: London ISNA 2014-04-24 (BST = UTC+1) */
    if (pt_resolve_method("ISNA", 0, 0, &p) != 0) { printf("FAIL: ISNA\n"); return 1; }
    p.tz_offset_hours = 1.0;
    pt_times t;
    pt_calculate(2014, 4, 24, 51.508515, -0.1254872, 0, &p, &t);
    format(t.fajr, buf); if (strcmp(buf, "03:57")) { printf("FAIL: fajr %s\n", buf); fail |= 1; }
    format(t.isha, buf); if (strcmp(buf, "22:02")) { printf("FAIL: isha %s\n", buf); fail |= 1; }

    if (fail) return 1;
    printf("methods ok\n");
    return 0;
}
