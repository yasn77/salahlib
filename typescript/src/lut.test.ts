import { test, expect } from "bun:test";
import { readFileSync } from "node:fs";
import { PrayerTimes } from "./facade.js";

const FIXTURE = JSON.parse(
  readFileSync(new URL("../../shared/vectors/lut/lut.json", import.meta.url), "utf8"),
);

const WITHIN_1 = ["Sunrise", "Dhuhr", "Maghrib"] as const;
const WITHIN_5 = ["Asr", "Fajr", "Isha"] as const;

function toMin(s: string): number {
  const [h, m] = s.split(":").map(Number);
  return h * 60 + m;
}

test("LUT blackbox (published times)", () => {
  const pt = new PrayerTimes("LUT");
  for (const c of FIXTURE.cases) {
    const [y, m, d] = c.date.split("-").map(Number);
    const got = pt.getTimes(new Date(Date.UTC(y, m - 1, d)), FIXTURE.latitude, FIXTURE.longitude, FIXTURE.timezone);
    for (const k of WITHIN_1) {
      expect(Math.abs(toMin(got[k]) - toMin(c.timings[k])), `${c.date} ${k}`).toBeLessThanOrEqual(1);
    }
    for (const k of WITHIN_5) {
      expect(Math.abs(toMin(got[k]) - toMin(c.timings[k])), `${c.date} ${k}`).toBeLessThanOrEqual(5);
    }
  }
});
