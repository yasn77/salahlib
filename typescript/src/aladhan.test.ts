import { test, expect } from "bun:test";
import { readdirSync, readFileSync } from "node:fs";
import { join } from "node:path";
import { calculate, formatTime } from "./astronomy.js";
import { resolve } from "./methods.js";

const VECTORS = new URL("../../shared/vectors/aladhan/", import.meta.url).pathname;

function tzOffsetHours(y: number, m: number, d: number, tz: string): number {
  const dt = new Date(Date.UTC(y, m - 1, d));
  const parts = new Intl.DateTimeFormat("en-US", {
    timeZone: tz, year: "numeric", month: "2-digit", day: "2-digit",
    hour: "2-digit", minute: "2-digit", second: "2-digit", hour12: false,
  }).formatToParts(dt);
  const get = (t: string) => Number(parts.find((p) => p.type === t)?.value ?? 0);
  const asUTC = Date.UTC(get("year"), get("month") - 1, get("day"), get("hour") % 24, get("minute"), get("second"));
  return (asUTC - dt.getTime()) / 3600000;
}

function toMin(s: string): number {
  const [h, m] = s.split(":").map(Number);
  return h * 60 + m;
}

test("AlAdhan golden vectors", () => {
  const files = readdirSync(VECTORS).filter((f) => f.endsWith(".json"));
  expect(files.length).toBeGreaterThan(0);
  for (const f of files) {
    const data = JSON.parse(readFileSync(join(VECTORS, f), "utf8"));
    const meta = data.meta;
    const [d, m, y] = data.date.gregorian.date.split("-").map(Number);
    const isRamadan = f === "makkah_ramadan.json";
    const params = resolve(meta.method.id, meta.school ?? "STANDARD", null, "ANGLE_BASED", "STANDARD", "CLAMP", isRamadan, null, tzOffsetHours(y, m, d, meta.timezone));
    const raw = calculate(y, m, d, meta.latitude, meta.longitude, 0, params);
    const got: Record<string, string> = {
      Fajr: formatTime(raw.Fajr), Sunrise: formatTime(raw.Sunrise),
      Dhuhr: formatTime(raw.Dhuhr), Asr: formatTime(raw.Asr),
      Sunset: formatTime(raw.Sunset), Maghrib: formatTime(raw.Maghrib),
      Isha: formatTime(raw.Isha), Imsak: formatTime(raw.Imsak),
    };
    for (const k of ["Fajr", "Sunrise", "Dhuhr", "Sunset", "Maghrib", "Isha", "Imsak"]) {
      expect(got[k], `${f} ${k}`).toBe(data.timings[k]);
    }
    expect(Math.abs(toMin(got.Asr) - toMin(data.timings.Asr)), `${f} Asr`).toBeLessThanOrEqual(1);
  }
});
