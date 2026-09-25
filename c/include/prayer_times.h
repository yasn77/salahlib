#ifndef PRAYER_TIMES_H
#define PRAYER_TIMES_H

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
    double offset[9];     /* imsak,fajr,sunrise,dhuhr,asr,maghrib,sunset,isha,midnight */
} pt_params;

typedef struct {
    double fajr, sunrise, dhuhr, asr, sunset, maghrib, isha, imsak;
    double midnight, firstthird, lastthird;
} pt_times;

void pt_calculate(int y, int m, int d, double lat, double lng, double elevation,
                  const pt_params *p, pt_times *out);

#endif
