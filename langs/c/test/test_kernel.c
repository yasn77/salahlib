#include "prayer_times.h"
#include <math.h>
#include <stdio.h>
#include <string.h>

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

int main(void) {
    pt_params p = {0};
    p.fajr_angle = 15; p.isha = 15; p.maghrib_is_minutes = 1; p.imsak_mins = 10; p.asr_factor = 1;
    p.lat_adjust = 3; p.tz_offset_hours = 1.0;
    pt_times t;
    char buf[8];

    pt_calculate(2014, 4, 24, 51.508515, -0.1254872, 0, &p, &t);
    format(t.fajr, buf);     if (strcmp(buf, "03:57")) return 1;
    format(t.sunrise, buf);  if (strcmp(buf, "05:46")) return 2;
    format(t.dhuhr, buf);    if (strcmp(buf, "12:59")) return 3;
    format(t.asr, buf);      if (strcmp(buf, "16:54")) return 4;
    format(t.sunset, buf);   if (strcmp(buf, "20:12")) return 5;
    format(t.maghrib, buf);  if (strcmp(buf, "20:12")) return 6;
    format(t.isha, buf);     if (strcmp(buf, "22:02")) return 7;
    format(t.imsak, buf);    if (strcmp(buf, "03:47")) return 8;
    format(t.midnight, buf); if (strcmp(buf, "00:59")) return 9;

    p.tz_offset_hours = 0.0;
    pt_calculate(2024, 1, 22, 64.0, 20.0, 0, &p, &t);
    format(t.asr, buf);      if (strcmp(buf, "11:35")) return 10;

    printf("ok\n");
    return 0;
}
