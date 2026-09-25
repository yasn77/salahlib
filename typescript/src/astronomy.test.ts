import { test, expect } from "bun:test";
import { calculate, formatTime } from "./astronomy.js";
import { Params, zeroOffsets } from "./params.js";

function p(over: Partial<Params> = {}): Params {
  return {
    fajrAngle: 15, isha: 15, ishaIsMinutes: false,
    maghrib: 0, maghribIsMinutes: true,
    imsakMins: 10, dhuhrMins: 0, asrFactor: 1,
    latAdjust: "ANGLE_BASED", midnightMode: "STANDARD",
    unreachedPolicy: "CLAMP", offsets: zeroOffsets,
    timezoneOffsetHours: 1.0,
    ...over,
  };
}

test("London ISNA 2014-04-24", () => {
  const t = calculate(2014, 4, 24, 51.508515, -0.1254872, 0, p());
  expect(formatTime(t.Fajr)).toBe("03:57");
  expect(formatTime(t.Sunrise)).toBe("05:46");
  expect(formatTime(t.Dhuhr)).toBe("12:59");
  expect(formatTime(t.Asr)).toBe("16:54");
  expect(formatTime(t.Sunset)).toBe("20:12");
  expect(formatTime(t.Maghrib)).toBe("20:12");
  expect(formatTime(t.Isha)).toBe("22:02");
  expect(formatTime(t.Imsak)).toBe("03:47");
  expect(formatTime(t.Midnight)).toBe("00:59");
});

test("Asr canary 64N", () => {
  const t = calculate(2024, 1, 22, 64.0, 20.0, 0, p({ timezoneOffsetHours: 0 }));
  expect(formatTime(t.Asr)).toBe("11:35");
});
