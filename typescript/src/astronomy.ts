import type { Params, Unreached } from "./params.js";

export interface RawTimes {
  Fajr: number; Sunrise: number; Dhuhr: number; Asr: number;
  Sunset: number; Maghrib: number; Isha: number; Imsak: number;
  Midnight: number; Firstthird: number; Lastthird: number;
}

export const mod = (a: number, b: number): number => ((a % b) + b) % b;

const dtr = (d: number) => (d * Math.PI) / 180.0;
const rtd = (r: number) => (r * 180.0) / Math.PI;
const sin = (d: number) => Math.sin(dtr(d));
const cos = (d: number) => Math.cos(dtr(d));
const tan = (d: number) => Math.tan(dtr(d));
const arcsin = (x: number) => rtd(Math.asin(x));
const arccos = (x: number) => rtd(Math.acos(x));
const arccot = (x: number) => rtd(Math.atan(1.0 / x));
const arctan2 = (y: number, x: number) => rtd(Math.atan2(y, x));

export function julianDay(y: number, m: number, d: number): number {
  if (m <= 2) { y -= 1; m += 12; }
  const a = Math.floor(y / 100);
  const b = 2 - a + Math.floor(a / 4);
  return Math.floor(365.25 * (y + 4716)) + Math.floor(30.6001 * (m + 1)) + d + b - 1524.5;
}

export function solarPositionAt(jd: number): [number, number] {
  const d = jd - 2451545.0;
  const g = mod(357.529 + 0.98560028 * d, 360.0);
  const q = mod(280.459 + 0.98564736 * d, 360.0);
  const l = mod(q + 1.915 * sin(g) + 0.020 * sin(2 * g), 360.0);
  const e = 23.439 - 0.00000036 * d;
  const ra = mod(arctan2(cos(e) * sin(l), cos(l)) / 15.0, 24.0);
  return [arcsin(sin(e) * sin(l)), q / 15.0 - ra];
}

export function solarNoon(y: number, m: number, d: number, time: number, longitude: number): number {
  const jd = julianDay(y, m, d) + time / 24.0 - longitude / (15.0 * 24.0);
  const [, eqt] = solarPositionAt(jd);
  return mod(12.0 - eqt, 24.0);
}

export function horizonAngle(elevation: number): number {
  return 0.833 + 0.0347 * Math.sqrt(elevation);
}

export function asrShadowAngle(p: Params, y: number, m: number, d: number, time: number, latitude: number): number {
  const jd = julianDay(y, m, d) + 1.0 + time / 24.0;
  const [decl] = solarPositionAt(jd);
  return -arccot(p.asrFactor + tan(Math.abs(latitude - decl)));
}

export function depressionTime(
  angle: number, y: number, m: number, d: number, time: number,
  latitude: number, longitude: number, direction: number, policy: Unreached,
): [number, boolean] {
  const jd = julianDay(y, m, d) + time / 24.0 - longitude / (15.0 * 24.0);
  const [decl] = solarPositionAt(jd);
  const noon = solarNoon(y, m, d, time, longitude);
  const numerator = -sin(angle) - sin(latitude) * sin(decl);
  const denominator = cos(latitude) * cos(decl);
  let ratio = numerator / denominator;
  const reached = ratio >= -1.0 && ratio <= 1.0;
  if (policy === "CLAMP") {
    ratio = Math.max(-1.0, Math.min(1.0, ratio));
  } else if (!reached) {
    return [NaN, false];
  }
  const t = arccos(ratio) / 15.0;
  return [noon + direction * t, reached];
}

function nightFraction(la: Params["latAdjust"], angle: number, night: number): number {
  if (la === "MIDDLE_OF_THE_NIGHT") return night / 2.0;
  if (la === "ONE_SEVENTH") return night / 7.0;
  return (angle / 60.0) * night;
}

export function calculate(
  y: number, m: number, d: number, latitude: number, longitude: number,
  elevation: number, p: Params,
): RawTimes {
  const horizon = horizonAngle(elevation);
  const ang = (angle: number, time: number, dir: number): [number, boolean] =>
    depressionTime(angle, y, m, d, time, latitude, longitude, dir, p.unreachedPolicy);

  let fajr: number; let fajrReached: boolean;
  [fajr, fajrReached] = ang(p.fajrAngle, 5.0, -1);
  const [sunrise] = ang(horizon, 6.0, -1);
  const dhuhr = solarNoon(y, m, d, 12.0, longitude);
  const asrAngle = asrShadowAngle(p, y, m, d, 13.0, latitude);
  const [asr] = ang(asrAngle, 13.0, 1);
  const [sunset] = ang(horizon, 18.0, 1);
  let maghrib: number; let maghribReached: boolean;
  [maghrib, maghribReached] = ang(p.maghrib, 18.0, 1);
  let isha: number; let ishaReached: boolean;
  [isha, ishaReached] = ang(p.isha, 18.0, 1);

  if (p.latAdjust !== "NONE") {
    const night = mod(sunrise - sunset, 24.0);
    const fallback = (t: number, base: number, angle: number, dir: number, reached: boolean): number => {
      const portion = nightFraction(p.latAdjust, angle, night);
      if (!reached || (t - base) * dir > portion) return base + portion * dir;
      return t;
    };
    fajr = fallback(fajr, sunrise, p.fajrAngle, -1, fajrReached);
    isha = fallback(isha, sunset, p.isha, 1, ishaReached);
    maghrib = fallback(maghrib, sunset, p.maghrib, 1, maghribReached);
  }

  const tz = p.timezoneOffsetHours - longitude / 15.0;
  fajr += tz;
  const sunrise2 = sunrise + tz;
  const dhuhr2 = dhuhr + tz;
  const asr2 = asr + tz;
  const sunset2 = sunset + tz;
  maghrib += tz;
  isha += tz;

  let maghribF = maghrib;
  if (p.maghribIsMinutes) maghribF = sunset2 + p.maghrib / 60.0;
  let ishaF = isha;
  if (p.ishaIsMinutes) ishaF = maghribF + p.isha / 60.0;
  const dhuhrF = dhuhr2 + p.dhuhrMins / 60.0;
  const imsak = fajr - p.imsakMins / 60.0;

  const diff = p.midnightMode === "JAFARI" ? mod(fajr - sunset2, 24.0) : mod(sunrise2 - sunset2, 24.0);
  const midnight = sunset2 + diff / 2.0;
  const firstthird = sunset2 + diff / 3.0;
  const lastthird = sunset2 + (2.0 * diff) / 3.0;

  const o = p.offsets;
  return {
    Fajr: fajr + o.Fajr / 60.0,
    Sunrise: sunrise2 + o.Sunrise / 60.0,
    Dhuhr: dhuhrF + o.Dhuhr / 60.0,
    Asr: asr2 + o.Asr / 60.0,
    Sunset: sunset2 + o.Sunset / 60.0,
    Maghrib: maghribF + o.Maghrib / 60.0,
    Isha: ishaF + o.Isha / 60.0,
    Imsak: imsak + o.Imsak / 60.0,
    Midnight: midnight + o.Midnight / 60.0,
    Firstthird: firstthird,
    Lastthird: lastthird,
  };
}

export function formatTime(t: number): string {
  if (Number.isNaN(t)) return "-----";
  const x = mod(t + 0.5 / 60.0, 24.0);
  const h = Math.floor(x);
  const mm = Math.floor((x - h) * 60.0);
  return `${String(h).padStart(2, "0")}:${String(mm).padStart(2, "0")}`;
}
