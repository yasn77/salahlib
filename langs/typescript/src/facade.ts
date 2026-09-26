import { calculate, formatTime, RawTimes } from "./astronomy.js";
import { resolve } from "./methods.js";

export class PrayerTimes {
  constructor(
    private method: string | number,
    private school = "STANDARD",
  ) {}

  getTimes(dt: Date, latitude: number, longitude: number, tz = "UTC"): Record<string, string> {
    const params = resolve(this.method, this.school, null, "ANGLE_BASED", "STANDARD", "CLAMP", false, null, this.tzOffset(dt, tz));
    const raw = calculate(dt.getFullYear(), dt.getMonth() + 1, dt.getDate(), latitude, longitude, 0, params);
    return this.toMap(raw);
  }

  getTimesISO8601(dt: Date, latitude: number, longitude: number, tz = "UTC"): Record<string, string> {
    const params = resolve(this.method, this.school, null, "ANGLE_BASED", "STANDARD", "CLAMP", false, null, this.tzOffset(dt, tz));
    const raw = calculate(dt.getFullYear(), dt.getMonth() + 1, dt.getDate(), latitude, longitude, 0, params);
    const out: Record<string, string> = {};
    for (const [k, v] of Object.entries(raw)) out[k] = this.formatISO8601(v, dt, tz);
    return out;
  }

  private formatISO8601(t: number, dt: Date, tz: string): string {
    const offsetHours = this.tzOffset(dt, tz);
    const offsetMs = offsetHours * 3600000;
    const baseUTC = Date.UTC(dt.getFullYear(), dt.getMonth(), dt.getDate());
    const t2 = t + 0.5 / 60; // round, same as formatTime
    const mins = t2 > 0 ? Math.floor(t2 * 60) : -Math.ceil(-t2 * 60);
    const ts = baseUTC - offsetMs + mins * 60000;
    const local = new Date(ts + offsetMs);
    const pad = (n: number) => String(n).padStart(2, "0");
    const oh = Math.abs(offsetHours);
    const sign = offsetHours >= 0 ? "+" : "-";
    const offsetStr = `${sign}${pad(Math.floor(oh))}:${pad(Math.round((oh - Math.floor(oh)) * 60))}`;
    return `${local.getUTCFullYear()}-${pad(local.getUTCMonth() + 1)}-${pad(local.getUTCDate())}T${pad(local.getUTCHours())}:${pad(local.getUTCMinutes())}:${pad(local.getUTCSeconds())}${offsetStr}`;
  }

  private toMap(raw: RawTimes): Record<string, string> {
    return {
      Fajr: formatTime(raw.Fajr), Sunrise: formatTime(raw.Sunrise),
      Dhuhr: formatTime(raw.Dhuhr), Asr: formatTime(raw.Asr),
      Sunset: formatTime(raw.Sunset), Maghrib: formatTime(raw.Maghrib),
      Isha: formatTime(raw.Isha), Imsak: formatTime(raw.Imsak),
      Midnight: formatTime(raw.Midnight),
      Firstthird: formatTime(raw.Firstthird), Lastthird: formatTime(raw.Lastthird),
    };
  }

  private tzOffset(dt: Date, tz: string): number {
    const parts = new Intl.DateTimeFormat("en-US", {
      timeZone: tz, year: "numeric", month: "2-digit", day: "2-digit",
      hour: "2-digit", minute: "2-digit", second: "2-digit", hour12: false,
    }).formatToParts(dt);
    const get = (t: string) => Number(parts.find((p) => p.type === t)?.value ?? 0);
    const asUTC = Date.UTC(get("year"), get("month") - 1, get("day"), get("hour") % 24, get("minute"), get("second"));
    return (asUTC - dt.getTime()) / 3600000;
  }
}
