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
