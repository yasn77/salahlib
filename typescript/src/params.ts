export type LatAdjust = "NONE" | "MIDDLE_OF_THE_NIGHT" | "ONE_SEVENTH" | "ANGLE_BASED";
export type Midnight = "STANDARD" | "JAFARI";
export type Unreached = "CLAMP" | "NAN";

export interface Offsets {
  Imsak: number; Fajr: number; Sunrise: number; Dhuhr: number; Asr: number;
  Maghrib: number; Sunset: number; Isha: number; Midnight: number;
}

export const zeroOffsets: Offsets = {
  Imsak: 0, Fajr: 0, Sunrise: 0, Dhuhr: 0, Asr: 0,
  Maghrib: 0, Sunset: 0, Isha: 0, Midnight: 0,
};

export interface Params {
  fajrAngle: number; isha: number; ishaIsMinutes: boolean;
  maghrib: number; maghribIsMinutes: boolean;
  imsakMins: number; dhuhrMins: number; asrFactor: number;
  latAdjust: LatAdjust; midnightMode: Midnight; unreachedPolicy: Unreached;
  offsets: Offsets; timezoneOffsetHours: number;
}
