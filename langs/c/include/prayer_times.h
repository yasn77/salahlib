#ifndef PRAYER_TIMES_H
#define PRAYER_TIMES_H

#include <stddef.h>

typedef struct {
    double fajr_angle;
    double isha;
    int isha_is_minutes;
    double maghrib;
    int maghrib_is_minutes;
    double imsak_mins;
    double dhuhr_mins;
    double asr_factor;
    int lat_adjust;       /* 0 NONE, 1 MIDDLE_OF_THE_NIGHT, 2 ONE_SEVENTH, 3 ANGLE_BASED */
    int midnight_mode;    /* 0 STANDARD, 1 JAFARI */
    int unreached_policy; /* 0 CLAMP, 1 NAN */
    double tz_offset_hours;
    const char *shafaq;   /* "general"/"ahmer"/"abyad" for MOONSIGHTING, else NULL */
    double offset[9];     /* imsak,fajr,sunrise,dhuhr,asr,maghrib,sunset,isha,midnight */
} pt_params;

typedef struct {
    double fajr, sunrise, dhuhr, asr, sunset, maghrib, isha, imsak;
    double midnight, firstthird, lastthird;
} pt_times;

void pt_calculate(int y, int m, int d, double lat, double lng, double elevation,
                  const pt_params *p, pt_times *out);

/* Format a float hour as ISO8601 (e.g. "2014-04-24T03:57:00+01:00") for date y/m/d and UTC offset (hours). */
void pt_format_iso8601(double t, int y, int m, int d, double tz_offset_hours, char *buf, size_t buflen);

/* Resolve a method (by id string "3" or name "MWL") into pt_params. Returns 0 on success, -1 if unknown. */
int pt_resolve_method(const char *method, int school_hanafi, int is_ramadan, pt_params *out);

#endif
