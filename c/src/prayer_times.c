#include "prayer_times.h"
#include <math.h>

#define PR_PI 3.14159265358979323846

static double mod(double a, double b) {
    double r = fmod(a, b);
    if (r < 0) r += b;
    return r;
}

static double dtr(double d) { return d * PR_PI / 180.0; }
static double rtd(double r) { return r * 180.0 / PR_PI; }
static double ssin(double d) { return sin(dtr(d)); }
static double cosd(double d) { return cos(dtr(d)); }
static double ttan(double d) { return tan(dtr(d)); }
static double aasin(double x) { return rtd(asin(x)); }
static double aacos(double x) { return rtd(acos(x)); }
static double aacot(double x) { return rtd(atan(1.0 / x)); }
static double aatan2(double y, double x) { return rtd(atan2(y, x)); }

static double julian_day(int y, int m, int d) {
    if (m <= 2) { y -= 1; m += 12; }
    int A = (int)floor(y / 100.0);
    double B = 2 - A + (int)floor(A / 4.0);
    return floor(365.25 * (y + 4716)) + floor(30.6001 * (m + 1)) + d + B - 1524.5;
}

static void solar_position_at(double jd, double *decl, double *eqt) {
    double D = jd - 2451545.0;
    double g = mod(357.529 + 0.98560028 * D, 360.0);
    double q = mod(280.459 + 0.98564736 * D, 360.0);
    double L = mod(q + 1.915 * ssin(g) + 0.020 * ssin(2 * g), 360.0);
    double e = 23.439 - 0.00000036 * D;
    double RA = mod(aatan2(cosd(e) * ssin(L), cosd(L)) / 15.0, 24.0);
    *decl = aasin(ssin(e) * ssin(L));
    *eqt = q / 15.0 - RA;
}

static double solar_noon(int y, int m, int d, double time, double lng) {
    double jd = julian_day(y, m, d) + time / 24.0 - lng / (15.0 * 24.0);
    double decl, eqt;
    solar_position_at(jd, &decl, &eqt);
    return mod(12.0 - eqt, 24.0);
}

static double horizon_angle(double elevation) {
    return 0.833 + 0.0347 * sqrt(elevation);
}

static double asr_shadow_angle(const pt_params *p, int y, int m, int d, double time, double lat) {
    double jd = julian_day(y, m, d) + 1.0 + time / 24.0;
    double decl, eqt;
    solar_position_at(jd, &decl, &eqt);
    return -aacot(p->asr_factor + ttan(fabs(lat - decl)));
}

static double depression_time(double angle, int y, int m, int d, double time,
                              double lat, double lng, int direction, int policy, int *reached_out) {
    double jd = julian_day(y, m, d) + time / 24.0 - lng / (15.0 * 24.0);
    double decl, eqt;
    solar_position_at(jd, &decl, &eqt);
    double noon = solar_noon(y, m, d, time, lng);
    double numerator = -ssin(angle) - ssin(lat) * ssin(decl);
    double denominator = cosd(lat) * cosd(decl);
    double ratio = numerator / denominator;
    int reached = (ratio >= -1.0 && ratio <= 1.0);
    if (policy == 0) {
        if (ratio > 1.0) ratio = 1.0;
        if (ratio < -1.0) ratio = -1.0;
    } else if (!reached) {
        *reached_out = 0;
        return NAN;
    }
    double t = aacos(ratio) / 15.0;
    *reached_out = reached;
    return noon + direction * t;
}

static double night_fraction(int la, double angle, double night) {
    if (la == 1) return night / 2.0;
    if (la == 2) return night / 7.0;
    return (angle / 60.0) * night;
}

void pt_calculate(int y, int m, int d, double lat, double lng, double elevation,
                  const pt_params *p, pt_times *out) {
    double horizon = horizon_angle(elevation);
    int reached = 1;

    double fajr = depression_time(p->fajr_angle, y, m, d, 5.0, lat, lng, -1, p->unreached_policy, &reached);
    int fajr_reached = reached;
    double sunrise = depression_time(horizon, y, m, d, 6.0, lat, lng, -1, p->unreached_policy, &reached);
    double dhuhr = solar_noon(y, m, d, 12.0, lng);
    double asr_angle = asr_shadow_angle(p, y, m, d, 13.0, lat);
    double asr = depression_time(asr_angle, y, m, d, 13.0, lat, lng, 1, p->unreached_policy, &reached);
    double sunset = depression_time(horizon, y, m, d, 18.0, lat, lng, 1, p->unreached_policy, &reached);
    double maghrib = depression_time(p->maghrib, y, m, d, 18.0, lat, lng, 1, p->unreached_policy, &reached);
    int maghrib_reached = reached;
    double isha = depression_time(p->isha, y, m, d, 18.0, lat, lng, 1, p->unreached_policy, &reached);
    int isha_reached = reached;

    if (p->lat_adjust != 0) {
        double night = mod(sunrise - sunset, 24.0);
        double fajr_p = night_fraction(p->lat_adjust, p->fajr_angle, night);
        double isha_p = night_fraction(p->lat_adjust, p->isha, night);
        double mag_p = night_fraction(p->lat_adjust, p->maghrib, night);
        if (!fajr_reached || (fajr - sunrise) * -1 > fajr_p) fajr = sunrise - fajr_p;
        if (!isha_reached || (isha - sunset) > isha_p) isha = sunset + isha_p;
        if (!maghrib_reached || (maghrib - sunset) > mag_p) maghrib = sunset + mag_p;
    }

    double tz = p->tz_offset_hours - lng / 15.0;
    fajr += tz; sunrise += tz; dhuhr += tz; asr += tz; sunset += tz; maghrib += tz; isha += tz;

    if (p->maghrib_is_minutes) maghrib = sunset + p->maghrib / 60.0;
    if (p->isha_is_minutes) isha = maghrib + p->isha / 60.0;
    dhuhr += p->dhuhr_mins / 60.0;
    double imsak = fajr - p->imsak_mins / 60.0;

    double diff = (p->midnight_mode == 1) ? mod(fajr - sunset, 24.0) : mod(sunrise - sunset, 24.0);
    double midnight = sunset + diff / 2.0;
    double firstthird = sunset + diff / 3.0;
    double lastthird = sunset + 2.0 * diff / 3.0;

    out->fajr = fajr + p->offset[1] / 60.0;
    out->sunrise = sunrise + p->offset[2] / 60.0;
    out->dhuhr = dhuhr + p->offset[3] / 60.0;
    out->asr = asr + p->offset[4] / 60.0;
    out->sunset = sunset + p->offset[6] / 60.0;
    out->maghrib = maghrib + p->offset[5] / 60.0;
    out->isha = isha + p->offset[7] / 60.0;
    out->imsak = imsak + p->offset[0] / 60.0;
    out->midnight = midnight + p->offset[8] / 60.0;
    out->firstthird = firstthird;
    out->lastthird = lastthird;
}
