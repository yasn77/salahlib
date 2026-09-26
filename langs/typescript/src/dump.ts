import { calculate } from "./astronomy.js";
import { Params, zeroOffsets } from "./params.js";

const a = process.argv.slice(2).map(Number);
const p: Params = {
  fajrAngle: a[6], isha: a[7], ishaIsMinutes: a[8] !== 0,
  maghrib: 0, maghribIsMinutes: false, imsakMins: 10, dhuhrMins: a[9],
  asrFactor: a[10], latAdjust: "ANGLE_BASED", midnightMode: "STANDARD",
  unreachedPolicy: "CLAMP", offsets: zeroOffsets, timezoneOffsetHours: 0,
};
const t = calculate(a[0], a[1], a[2], a[3], a[4], a[5], p);
const keys = ["Fajr", "Sunrise", "Dhuhr", "Asr", "Sunset", "Maghrib", "Isha", "Imsak", "Midnight", "Firstthird", "Lastthird"] as const;
console.log(keys.map((k) => (t[k] as number).toPrecision(17)).join(" "));
