#include "prayer_times.h"
#include <math.h>
#include <stdio.h>
#include <string.h>

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

static double round_away(double x) {
    return x >= 0 ? floor(x + 0.5) : ceil(x - 0.5);
}

static int dyy(int y, int m, int d, double lat) {
    int am = 12, ad = 21;
    if (lat <= 0) { am = 6; ad = 21; }
    int n = (int)(julian_day(y, m, d) - julian_day(y, am, ad));
    if (n >= 2) return n - 1;
    if (n >= 0) return 365;
    return 365 + n;
}

static double interpolate(double a, double b, double c, double d, int dy) {
    if (dy < 91) return a + (b - a) / 91.0 * dy;
    if (dy < 137) return b + (c - b) / 46.0 * (dy - 91);
    if (dy < 183) return c + (d - c) / 46.0 * (dy - 137);
    if (dy < 229) return d + (c - d) / 46.0 * (dy - 183);
    if (dy < 275) return c + (b - c) / 46.0 * (dy - 229);
    return b + (a - b) / 91.0 * (dy - 275);
}

static double fajr_minutes(double lat, int dy) {
    double a = 75 + 28.65 / 55.0 * fabs(lat);
    double b = 75 + 19.44 / 55.0 * fabs(lat);
    double c = 75 + 32.74 / 55.0 * fabs(lat);
    double d = 75 + 48.10 / 55.0 * fabs(lat);
    return interpolate(a, b, c, d, dy);
}

static double isha_minutes(double lat, int dy, const char *shafaq) {
    double a, b, c, d;
    if (strcmp(shafaq, "ahmer") == 0) {
        a = 62 + 17.4 / 55.0 * fabs(lat); b = 62 - 7.16 / 55.0 * fabs(lat);
        c = 62 + 5.12 / 55.0 * fabs(lat); d = 62 + 19.44 / 55.0 * fabs(lat);
    } else if (strcmp(shafaq, "abyad") == 0) {
        a = 75 + 25.6 / 55.0 * fabs(lat); b = 75 + 7.16 / 55.0 * fabs(lat);
        c = 75 + 36.84 / 55.0 * fabs(lat); d = 75 + 81.84 / 55.0 * fabs(lat);
    } else {
        a = 75 + 25.6 / 55.0 * fabs(lat); b = 75 + 2.05 / 55.0 * fabs(lat);
        c = 75 - 9.21 / 55.0 * fabs(lat); d = 75 + 6.14 / 55.0 * fabs(lat);
    }
    return interpolate(a, b, c, d, dy);
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

    /* Moonsighting override (SPEC §11): after night times, before offsets. */
    if (p->shafaq && p->shafaq[0] != '\0') {
        int dy = dyy(y, m, d, lat);
        fajr = sunrise - round_away(fajr_minutes(lat, dy)) / 60.0;
        isha = sunset + round_away(isha_minutes(lat, dy, p->shafaq)) / 60.0;
        imsak = fajr - p->imsak_mins / 60.0;
    }

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

static long days_from_civil(int y, unsigned m, unsigned d) {
    y -= m <= 2;
    int era = (y >= 0 ? y : y - 399) / 400;
    unsigned yoe = (unsigned)(y - era * 400);
    unsigned doy = (153 * (m + (m > 2 ? -3 : 9)) + 2) / 5 + d - 1;
    unsigned doe = yoe * 365 + yoe / 4 - yoe / 100 + doy;
    return era * 146097 + (long)doe - 719468;
}

static void civil_from_days(long z, int *y, unsigned *m, unsigned *d) {
    z += 719468;
    long era = (z >= 0 ? z : z - 146096) / 146097;
    unsigned doe = (unsigned)(z - era * 146097);
    unsigned yoe = (doe - doe / 1460 + doe / 36524 - doe / 146096) / 365;
    *y = (int)(yoe) + (int)(era * 400);
    unsigned doy = doe - (365 * yoe + yoe / 4 - yoe / 100);
    unsigned mp = (5 * doy + 2) / 153;
    *d = doy - (153 * mp + 2) / 5 + 1;
    *m = mp + (mp < 10 ? 3 : -9);
    *y += (int)(*m <= 2);
}

void pt_format_iso8601(double t, int y, int m, int d, double tz_offset_hours, char *buf, size_t buflen) {
    double t2 = t + 0.5 / 60.0;
    double mins = t2 > 0 ? floor(t2 * 60) : -ceil(-t2 * 60);
    double jd = julian_day(y, m, d) + mins / 1440.0;
    double unix_days = jd - 2440587.5;
    long day = (long)floor(unix_days);
    double frac = unix_days - day;
    int yy, hh, mm, ss;
    unsigned mo, dd;
    civil_from_days(day, &yy, &mo, &dd);
    long total_sec = (long)round(frac * 86400.0);
    hh = (int)(total_sec / 3600);
    mm = (int)((total_sec % 3600) / 60);
    ss = (int)(total_sec % 60);
    int oh = (int)fabs(tz_offset_hours);
    int om = (int)round((fabs(tz_offset_hours) - oh) * 60);
    snprintf(buf, buflen, "%04d-%02u-%02uT%02d:%02d:%02d%c%02d:%02d",
             yy, mo, dd, hh, mm, ss, tz_offset_hours >= 0 ? '+' : '-', oh, om);
}
