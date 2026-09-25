#include "prayer_times.h"
#include "methods_generated.h"

#include <stdlib.h>
#include <string.h>

static int is_all_digits(const char *s) {
    if (!s || !*s) return 0;
    for (; *s; s++)
        if (*s < '0' || *s > '9') return 0;
    return 1;
}

/* Resolve a method (by id string, e.g. "3", or name, e.g. "MWL") into pt_params.
 * school_hanafi: 0 = STANDARD (Asr factor 1), 1 = HANAFI (Asr factor 2).
 * is_ramadan: apply the method's ramadanTune (MAKKAH Isha +30) on top of defaultTune.
 * Returns 0 on success, -1 if the method is unknown. */
int pt_resolve_method(const char *method, int school_hanafi, int is_ramadan, pt_params *out) {
    const pt_method *m = NULL;

    if (is_all_digits(method)) {
        int id = atoi(method);
        for (int i = 0; i < PT_METHOD_COUNT; i++) {
            if (pt_methods[i].id == id) { m = &pt_methods[i]; break; }
        }
    } else {
        for (int i = 0; i < PT_METHOD_COUNT; i++) {
            if (strcmp(pt_methods[i].key, method) == 0) { m = &pt_methods[i]; break; }
        }
    }
    if (!m) return -1;

    memset(out, 0, sizeof(*out));
    out->fajr_angle = m->fajr;
    out->isha = m->isha;
    out->isha_is_minutes = m->isha_is_minutes;
    out->maghrib = m->maghrib;
    out->maghrib_is_minutes = m->maghrib_is_minutes;
    out->imsak_mins = m->imsak;
    out->dhuhr_mins = m->dhuhr;
    out->asr_factor = school_hanafi ? 2.0 : 1.0;
    out->lat_adjust = 3;   /* ANGLE_BASED */
    out->midnight_mode = m->midnight_jafari;
    out->unreached_policy = 0; /* CLAMP */
    out->shafaq = m->shafaq;
    for (int i = 0; i < 9; i++) out->offset[i] = m->default_tune[i];
    if (is_ramadan) {
        for (int i = 0; i < 9; i++)
            if (m->ramadan_tune[i] != 0.0) out->offset[i] = m->ramadan_tune[i];
    }
    return 0;
}
