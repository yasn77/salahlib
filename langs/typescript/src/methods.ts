import { Params, LatAdjust, Midnight, Unreached, Offsets } from "./params.js";
import methodsJson from "./methods.json";

interface MethodEntry {
  id: number;
  name?: string;
  params?: Record<string, string | number>;
  location?: { latitude: number; longitude: number };
  defaultTune?: Record<string, number>;
  ramadanTune?: Record<string, number>;
}

const methods = methodsJson as Record<string, MethodEntry>;
const byId = new Map(Object.entries(methods).map(([k, v]) => [String(v.id), k]));

const value = (x: unknown): number => {
  const m = String(x).match(/^[0-9.+\-]+/);
  return m ? parseFloat(m[0]) : 0.0;
};

const isMin = (x: unknown): boolean => String(x).includes("min");

export function methodCodes(): string[] {
  return Object.keys(methods);
}

export function resolve(
  method: string | number, school = "STANDARD", asrFactor?: number | null,
  latAdjust: LatAdjust = "ANGLE_BASED", midnightMode: Midnight = "STANDARD",
  unreachedPolicy: Unreached = "CLAMP", isRamadan = false,
  offsets?: Record<string, number> | null, timezoneOffsetHours = 0.0,
): Params {
  const key = methods[String(method)] ? String(method) : byId.get(String(method));
  if (!key) throw new Error(`unknown method: ${method}`);
  const entry = methods[key];
  const p = entry.params ?? {};
  const shafaq = typeof p.shafaq === "string" ? p.shafaq : undefined;
  const af = asrFactor ?? (school === "HANAFI" ? 2.0 : 1.0);

  const off: Record<string, number> = { ...(entry.defaultTune ?? {}) };
  if (offsets) {
    for (const [k, v] of Object.entries(offsets)) {
      if (v !== 0) off[k] = v;
    }
  }
  // ramadanTune applied last: in Ramadan MAKKAH Isha:30 overrides even a user value (SPEC §12).
  if (isRamadan) Object.assign(off, entry.ramadanTune ?? {});

  const imsak = p.Imsak ?? "10 min";
  const dhuhr = p.Dhuhr ?? "0 min";
  const maghrib = p.Maghrib ?? "0 min";

  return {
    fajrAngle: value(p.Fajr ?? 0),
    isha: value(p.Isha ?? 0),
    ishaIsMinutes: isMin(p.Isha ?? 0),
    maghrib: value(maghrib),
    maghribIsMinutes: isMin(maghrib),
    imsakMins: value(imsak),
    dhuhrMins: value(dhuhr),
    asrFactor: af,
    latAdjust,
    midnightMode,
    unreachedPolicy,
    offsets: {
      Imsak: off.Imsak ?? 0, Fajr: off.Fajr ?? 0, Sunrise: off.Sunrise ?? 0,
      Dhuhr: off.Dhuhr ?? 0, Asr: off.Asr ?? 0, Maghrib: off.Maghrib ?? 0,
      Sunset: off.Sunset ?? 0, Isha: off.Isha ?? 0, Midnight: off.Midnight ?? 0,
    } satisfies Offsets,
    timezoneOffsetHours,
    shafaq,
  };
}
