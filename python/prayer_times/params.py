"""Fully-resolved, string-free input model for the calculation kernel."""
from dataclasses import dataclass, field
from enum import Enum


class LatAdjust(Enum):
    NONE = "NONE"
    MIDDLE_OF_THE_NIGHT = "MIDDLE_OF_THE_NIGHT"
    ONE_SEVENTH = "ONE_SEVENTH"
    ANGLE_BASED = "ANGLE_BASED"


class Midnight(Enum):
    STANDARD = "STANDARD"
    JAFARI = "JAFARI"


class Unreached(Enum):
    CLAMP = "CLAMP"
    NAN = "NAN"


@dataclass(frozen=True)
class Offsets:
    imsak: float = 0.0
    fajr: float = 0.0
    sunrise: float = 0.0
    dhuhr: float = 0.0
    asr: float = 0.0
    maghrib: float = 0.0
    sunset: float = 0.0
    isha: float = 0.0
    midnight: float = 0.0


@dataclass(frozen=True)
class Params:
    fajr_angle: float
    isha: float
    isha_is_minutes: bool
    maghrib: float
    maghrib_is_minutes: bool
    imsak_mins: float
    dhuhr_mins: float
    asr_factor: float
    lat_adjust: LatAdjust
    midnight_mode: Midnight
    unreached_policy: Unreached
    offsets: Offsets = field(default_factory=Offsets)
    timezone_offset_hours: float = 0.0
    shafaq: str | None = None  # "general"/"ahmer"/"abyad" for MOONSIGHTING, else None
