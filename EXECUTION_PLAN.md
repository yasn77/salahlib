# Execution Plan — SalahLib (executor + reviewer loop)

This plan drives implementation of the **Python**, **Go**, **TypeScript** and **C** libraries.
It is written for an **executor agent** that *transforms text in the prompt* (it cannot read files) and a
**reviewer agent** (or the user) that has final say on whether the executor may proceed.

The mathematics, data schemas and target behaviour are fully specified in `shared/SPEC.md`,
`shared/methods.json` and `shared/methods.schema.json`. The executor works from **this document only** — it
is not given those files to read, but every task below embeds the exact code it needs.

---

## Conventions (apply to every task)

- **Roles.** Executor produces code by applying the exact `before → after` transformations below. Reviewer
  runs the verification command(s) and the phase exit criteria; it is the only authority that can green-light
  moving to the next phase.
- **Self-contained tasks.** Each task lists: (a) file path, (b) the exact current code (or "does not exist"),
  (c) the exact replacement code, (d) a verification command. No line numbers, no "see SPEC §x" as a
  substitute for code.
- **Read before write.** Every task begins with the instruction: *"First run `cat <filepath>` to read the
  file, then make the edit."*
- **Batches.** Tasks are grouped in batches of **at most 3**. The executor does one batch, then stops for
  review.
- **Formatting.** Every task ends with a format command as its final acceptance step:
  - Go → `Run: gofmt -w <filepath>`
  - Python → `Run: ruff format <filepath>`
  - TypeScript → `Run: bunx prettier --write <filepath>`
  - C → `Run: clang-format -i <filepath>`
- **TDD.** Tasks marked **(TDD)** must follow: write the test → run it → **confirm it FAILS** → implement →
  run it → **confirm it PASSES**.
- **No network in the normal path.** The AlAdhan API is only contacted by the *fixture generator* (a manual
  task). Tests read committed fixtures.
- **Documentation.** Every phase updates the docs. `docs/user-guide.md` (end-user) and
  `docs/developer-guide.md` (developer) each end with a single `<!-- NEXT -->` sentinel line; a phase's docs
  task replaces that exact sentinel with the new section followed by a fresh `<!-- NEXT -->`.

---

## Phase 0 — Scaffold, tooling & shared data

**Goal:** set up `mise` (tools + tasks), create the shared method-registry (`methods.json`) and its schema,
create the language project skeletons, and the documentation skeletons.

**Reviewer exit criteria:**
- [ ] `mise install` succeeds and `mise run --help` lists the tasks.
- [ ] `shared/methods.json` validates against `shared/methods.schema.json`.
- [ ] `python/prayer_times/data/methods.json` is byte-identical to `shared/methods.json`.
- [ ] `python/pyproject.toml`, `go/go.mod`, `typescript/package.json`, `typescript/tsconfig.json`,
      `c/CMakeLists.txt` all exist.
- [ ] `docs/user-guide.md` and `docs/developer-guide.md` exist and end with `<!-- NEXT -->`.

### Batch 0.1 — mise config + method registry + schema

#### Task 0.1.1 — mise configuration (tools + tasks)

**File:** `.mise.toml` (does not exist)

**Current code:** *(file does not exist)*

**Replacement code:**
```toml
[tools]
python = "3.14"
go     = "1.27"
node   = "24"
uv     = "latest"
bun    = "latest"

[tasks.gen-fixtures]
description = "Fetch golden vectors from the AlAdhan API (manual / scheduled drift job — NOT in CI)"
run = "uv run scripts/generate_fixtures.py"

[tasks.sync-data]
description = "Copy shared/methods.json into each language tree (committed copies)"
run = "uv run scripts/sync_data.py"

[tasks.test-python]
run = "uv run pytest python/tests"

[tasks.test-go]
run = "go test ./..."

[tasks.test-ts]
run = "bun test"

[tasks.test-c]
run = "cmake --build c/build && ctest --test-dir c/build"

[tasks.test]
depends = ["test-python", "test-go", "test-ts", "test-c"]

[tasks.parity]
description = "Cross-language float parity (≤1e-9 hours)"
run = "uv run tests/parity.py"

[tasks.lint]
run = "uv run ruff check python && gofmt -l . && bun x tsc --noEmit"

[tasks.ci]
depends = ["test", "parity", "lint"]
```

**Verification:** `mise install && mise run --help`

**First run `cat .mise.toml` to read the file, then make the edit.**
**Run: *(toml is not formatted by the language formatters — the `mise run --help` check is authoritative)***

#### Task 0.1.2 — the method-registry abstraction (`methods.json`)

**File:** `shared/methods.json` (does not exist)

**Current code:** *(file does not exist)*

**Replacement code:**
```json
{
  "JAFARI": {
    "id": 0,
    "name": "Shia Ithna-Ashari, Leva Institute, Qum",
    "params": { "Fajr": 16, "Isha": 14, "Maghrib": 4, "Midnight": "JAFARI" },
    "location": { "latitude": 34.6415764, "longitude": 50.8746035 }
  },
  "KARACHI": {
    "id": 1,
    "name": "University of Islamic Sciences, Karachi",
    "params": { "Fajr": 18, "Isha": 18 },
    "location": { "latitude": 24.8614622, "longitude": 67.0099388 }
  },
  "ISNA": {
    "id": 2,
    "name": "Islamic Society of North America (ISNA)",
    "params": { "Fajr": 15, "Isha": 15 },
    "location": { "latitude": 39.70421229999999, "longitude": -86.39943869999999 }
  },
  "MWL": {
    "id": 3,
    "name": "Muslim World League",
    "params": { "Fajr": 18, "Isha": 17 },
    "location": { "latitude": 51.5194682, "longitude": -0.1360365 }
  },
  "MAKKAH": {
    "id": 4,
    "name": "Umm Al-Qura University, Makkah",
    "params": { "Fajr": 18.5, "Isha": "90 min" },
    "location": { "latitude": 21.3890824, "longitude": 39.8579118 },
    "ramadanTune": { "Isha": 30 }
  },
  "EGYPT": {
    "id": 5,
    "name": "Egyptian General Authority of Survey",
    "params": { "Fajr": 19.5, "Isha": 17.5 },
    "location": { "latitude": 30.0444196, "longitude": 31.2357116 }
  },
  "TEHRAN": {
    "id": 7,
    "name": "Institute of Geophysics, University of Tehran",
    "params": { "Fajr": 17.7, "Isha": 14, "Maghrib": 4.5, "Midnight": "JAFARI" },
    "location": { "latitude": 35.6891975, "longitude": 51.3889736 }
  },
  "GULF": {
    "id": 8,
    "name": "Gulf Region",
    "params": { "Fajr": 19.5, "Isha": "90 min" },
    "location": { "latitude": 24.1323638, "longitude": 53.3199527 }
  },
  "KUWAIT": {
    "id": 9,
    "name": "Kuwait",
    "params": { "Fajr": 18, "Isha": 17.5 },
    "location": { "latitude": 29.375859, "longitude": 47.9774052 }
  },
  "QATAR": {
    "id": 10,
    "name": "Qatar",
    "params": { "Fajr": 18, "Isha": "90 min" },
    "location": { "latitude": 25.2854473, "longitude": 51.5310398 }
  },
  "SINGAPORE": {
    "id": 11,
    "name": "Majlis Ugama Islam Singapura, Singapore",
    "params": { "Fajr": 20, "Isha": 18 },
    "location": { "latitude": 1.352083, "longitude": 103.819836 }
  },
  "FRANCE": {
    "id": 12,
    "name": "Union Organization Islamic de France",
    "params": { "Fajr": 12, "Isha": 12 },
    "location": { "latitude": 48.856614, "longitude": 2.3522219 }
  },
  "TURKEY": {
    "id": 13,
    "name": "Diyanet İşleri Başkanlığı, Turkey (experimental)",
    "params": { "Fajr": 18, "Isha": 17 },
    "location": { "latitude": 39.9333635, "longitude": 32.8597419 },
    "defaultTune": { "Sunrise": -7, "Dhuhr": 5, "Asr": 4, "Sunset": 7, "Maghrib": 7 }
  },
  "RUSSIA": {
    "id": 14,
    "name": "Spiritual Administration of Muslims of Russia",
    "params": { "Fajr": 16, "Isha": 15 },
    "location": { "latitude": 54.73479099999999, "longitude": 55.9578555 }
  },
  "MOONSIGHTING": {
    "id": 15,
    "name": "Moonsighting Committee Worldwide (Moonsighting.com)",
    "params": { "shafaq": "general" }
  },
  "DUBAI": {
    "id": 16,
    "name": "Dubai (experimental)",
    "params": { "Fajr": 18.2, "Isha": 18.2 },
    "location": { "latitude": 25.0762677, "longitude": 55.087404 },
    "defaultTune": { "Dhuhr": 3, "Sunset": 3, "Maghrib": 3 }
  },
  "JAKIM": {
    "id": 17,
    "name": "Jabatan Kemajuan Islam Malaysia (JAKIM)",
    "params": { "Fajr": 20, "Isha": 18 },
    "location": { "latitude": 3.139003, "longitude": 101.686855 }
  },
  "TUNISIA": {
    "id": 18,
    "name": "Tunisia",
    "params": { "Fajr": 18, "Isha": 18 },
    "location": { "latitude": 36.8064948, "longitude": 10.1815316 }
  },
  "ALGERIA": {
    "id": 19,
    "name": "Algeria",
    "params": { "Fajr": 18, "Isha": 17 },
    "location": { "latitude": 36.753768, "longitude": 3.0587561 }
  },
  "KEMENAG": {
    "id": 20,
    "name": "Kementerian Agama Republik Indonesia",
    "params": { "Fajr": 20, "Isha": 18 },
    "location": { "latitude": -6.2087634, "longitude": 106.845599 }
  },
  "MOROCCO": {
    "id": 21,
    "name": "Morocco",
    "params": { "Fajr": 19, "Isha": 17 },
    "location": { "latitude": 33.9715904, "longitude": -6.8498129 },
    "defaultTune": { "Dhuhr": 5, "Maghrib": 5 }
  },
  "PORTUGAL": {
    "id": 22,
    "name": "Comunidade Islamica de Lisboa",
    "params": { "Fajr": 18, "Maghrib": "3 min", "Isha": "77 min" },
    "location": { "latitude": 38.7222524, "longitude": -9.1393366 },
    "defaultTune": { "Dhuhr": 5 }
  },
  "JORDAN": {
    "id": 23,
    "name": "Ministry of Awqaf, Islamic Affairs and Holy Places, Jordan",
    "params": { "Fajr": 18, "Maghrib": "5 min", "Isha": 18 },
    "location": { "latitude": 31.9461222, "longitude": 35.923844 }
  },
  "CUSTOM": {
    "id": 99
  }
}
```

**Verification:** `python3 -c "import json; d=json.load(open('shared/methods.json')); print(len(d), 'methods')"`

**First run `cat shared/methods.json` to read the file, then make the edit.**
**Run: `python3 -m json.tool shared/methods.json > /dev/null`**

#### Task 0.1.3 — the method-registry schema

**File:** `shared/methods.schema.json` (does not exist)

**Current code:** *(file does not exist)*

**Replacement code:**
```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://salahlib/schemas/methods.json",
  "title": "Prayer-times calculation methods registry",
  "description": "Single source of truth for calculation methods. Params values may be numbers (depression angles), \"N min\" strings (minutes after another time), \"JAFARI\" (midnight mode), or a shafaq value for MOONSIGHTING.",
  "type": "object",
  "additionalProperties": { "$ref": "#/$defs/method" },
  "$defs": {
    "prayerKey": {
      "enum": ["Imsak", "Fajr", "Sunrise", "Dhuhr", "Asr", "Maghrib", "Sunset", "Isha", "Midnight"]
    },
    "param": { "type": ["number", "string"] },
    "offsets": {
      "type": "object",
      "propertyNames": { "$ref": "#/$defs/prayerKey" },
      "additionalProperties": { "type": "number" }
    },
    "angleSpec": {
      "type": "object",
      "properties": { "angle": { "type": "number" } },
      "additionalProperties": false
    },
    "method": {
      "type": "object",
      "required": ["id"],
      "properties": {
        "id": { "type": "integer" },
        "name": { "type": "string" },
        "params": { "type": "object", "additionalProperties": { "$ref": "#/$defs/param" } },
        "location": {
          "type": "object",
          "required": ["latitude", "longitude"],
          "properties": {
            "latitude": { "type": "number" },
            "longitude": { "type": "number" }
          },
          "additionalProperties": false
        },
        "defaultTune": { "$ref": "#/$defs/offsets" },
        "ramadanTune": { "$ref": "#/$defs/offsets" },
        "adhanAdjustments": { "$ref": "#/$defs/offsets" },
        "composite": { "$ref": "#/$defs/composite" }
      },
      "additionalProperties": false
    },
    "composite": {
      "type": "object",
      "required": ["default"],
      "properties": {
        "default": {
          "type": "object",
          "properties": {
            "fajr": { "type": "number" },
            "isha": { "type": "number" },
            "adjustments": { "$ref": "#/$defs/offsets" }
          }
        },
        "windows": {
          "type": "array",
          "items": {
            "type": "object",
            "required": ["from", "to"],
            "properties": {
              "from": { "type": "string", "pattern": "^\\d{2}-\\d{2}$" },
              "to": { "type": "string", "pattern": "^\\d{2}-\\d{2}$" },
              "fajr": { "type": "number" },
              "isha": { "oneOf": [ { "type": "number" }, { "$ref": "#/$defs/angleSpec" } ] },
              "adjustments": { "$ref": "#/$defs/offsets" }
            }
          }
        },
        "fajrFallback": { "type": "object", "properties": { "whenNotReached": { "type": ["string", "number"] } } },
        "ishaFallback": { "type": "object", "properties": { "whenNotReached": { "type": ["string", "number"] } } }
      }
    }
  }
}
```

**Verification:** `python3 -c "import json,jsonschema; jsonschema.validate(json.load(open('shared/methods.json')), json.load(open('shared/methods.schema.json'))); print('valid')"`

**First run `cat shared/methods.schema.json` to read the file, then make the edit.**
**Run: `python3 -m json.tool shared/methods.schema.json > /dev/null`**

### Batch 0.2 — language project skeletons

#### Task 0.2.1 — Python project

**File:** `python/pyproject.toml` (does not exist)

**Current code:** *(file does not exist)*

**Replacement code:**
```toml
[project]
name = "prayer-times"
version = "0.1.0"
description = "AlAdhan-compatible Islamic prayer times"
requires-python = ">=3.10"
dependencies = []

[project.optional-dependencies]
dev = ["pytest", "ruff", "jsonschema"]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["prayer_times"]

[tool.hatch.build.targets.wheel.force-include]
"prayer_times/data/methods.json" = "prayer_times/data/methods.json"

[tool.pytest.ini_options]
testpaths = ["tests"]
```

**Verification:** `cd python && uv run python -c "import tomllib; tomllib.load(open('pyproject.toml','rb'))"`

**First run `cat python/pyproject.toml` to read the file, then make the edit.**
**Run: *(toml — the verification command above is authoritative)***

#### Task 0.2.2 — Go module

**File:** `go/go.mod` (does not exist)

**Current code:** *(file does not exist)*

**Replacement code:**
```
module github.com/salahlib/prayertimes

go 1.27
```

**Verification:** `cd go && go vet ./...` (no packages yet, exits 0)

**First run `cat go/go.mod` to read the file, then make the edit.**
**Run: `gofmt -w go/go.mod`**

#### Task 0.2.3 — TypeScript project

**File:** `typescript/package.json` (does not exist)

**Current code:** *(file does not exist)*

**Replacement code:**
```json
{
  "name": "prayer-times",
  "version": "0.1.0",
  "type": "module",
  "scripts": { "test": "bun test" },
  "devDependencies": { "typescript": "^5.6.0" }
}
```

**Verification:** `cd typescript && bun install && bun test` (no tests, exits 0)

**First run `cat typescript/package.json` to read the file, then make the edit.**
**Run: `bunx prettier --write typescript/package.json`**

### Batch 0.3 — build configs + data sync

#### Task 0.3.1 — tsconfig

**File:** `typescript/tsconfig.json` (does not exist)

**Current code:** *(file does not exist)*

**Replacement code:**
```json
{
  "compilerOptions": {
    "target": "ES2022",
    "module": "ESNext",
    "moduleResolution": "Bundler",
    "strict": true,
    "resolveJsonModule": true,
    "esModuleInterop": true,
    "skipLibCheck": true,
    "outDir": "dist"
  },
  "include": ["src"]
}
```

**Verification:** `cd typescript && bunx tsc --noEmit`

**First run `cat typescript/tsconfig.json` to read the file, then make the edit.**
**Run: `bunx prettier --write typescript/tsconfig.json`**

#### Task 0.3.2 — C build

**File:** `c/CMakeLists.txt` (does not exist)

**Current code:** *(file does not exist)*

**Replacement code:**
```cmake
cmake_minimum_required(VERSION 3.16)
project(salahlib_c C)

add_library(prayer_times STATIC src/prayer_times.c)
target_include_directories(prayer_times PUBLIC include)
target_link_libraries(prayer_times m)

add_executable(prayer_times_dump tools/dump.c)
target_link_libraries(prayer_times_dump prayer_times m)

enable_testing()
add_executable(prayer_times_test test/test_kernel.c)
target_link_libraries(prayer_times_test prayer_times m)
add_test(NAME kernel COMMAND prayer_times_test)
```

**Verification:** `cd c && cmake -B build && cmake --build build`

**First run `cat c/CMakeLists.txt` to read the file, then make the edit.**
**Run: *(cmake is not formatted — the cmake build is authoritative)***

#### Task 0.3.3 — sync-data script

**File:** `scripts/sync_data.py` (does not exist)

**Current code:** *(file does not exist)*

**Replacement code:**
```python
#!/usr/bin/env python3
"""Copy shared/methods.json into each language tree (committed copies)."""
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "shared" / "methods.json"
TARGETS = [
    ROOT / "python" / "prayer_times" / "data" / "methods.json",
    ROOT / "go" / "pkg" / "prayertimes" / "methods.json",
    ROOT / "typescript" / "src" / "methods.json",
]

for t in TARGETS:
    t.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(SRC, t)
    print(f"synced -> {t.relative_to(ROOT)}")
```

**Verification:** `python3 scripts/sync_data.py && cmp shared/methods.json python/prayer_times/data/methods.json`

**First run `cat scripts/sync_data.py` to read the file, then make the edit.**
**Run: `ruff format scripts/sync_data.py`**

### Batch 0.4 — documentation skeletons

#### Task 0.4.1 — user guide (end-user docs)

**File:** `docs/user-guide.md` (does not exist)

**Current code:** *(file does not exist)*

**Replacement code:**
```markdown
# SalahLib — User Guide

Installation and usage for end users.

## Install

Build and test tooling is managed by [mise](https://mise.jdx.dev):

```sh
mise install
```

## Python

```python
from datetime import date
from prayer_times import PrayerTimes

pt = PrayerTimes("ISNA")
times = pt.get_times(date(2024, 4, 24), 51.508515, -0.1254872, tz="Europe/London")
print(times["Fajr"])  # "03:57"
```

## Supported calculation methods

The method registry (`shared/methods.json`) defines 23 named methods plus `CUSTOM`, each with its depression
angles / minutes and (where AlAdhan applies them) default tune values. Methods are referenced by name
(`"ISNA"`, `"MWL"`, …) or by AlAdhan id (`2`, `3`, …).

<!-- NEXT -->
```

**Verification:** `tail -1 docs/user-guide.md` prints `<!-- NEXT -->`

**First run `cat docs/user-guide.md` to read the file, then make the edit.**
**Run: *(markdown — the `tail -1` check is authoritative)***

#### Task 0.4.2 — developer guide

**File:** `docs/developer-guide.md` (does not exist)

**Current code:** *(file does not exist)*

**Replacement code:**
```markdown
# SalahLib — Developer Guide

Architecture, build/test commands, and the executor+reviewer workflow.

## Architecture

Four tiers: shared data (`methods.json` / `SPEC.md`) → pure kernel → method backends → language facade.
The kernel is a pure function of numbers/enums; it never sees method names, dates, or timezone strings.

## Task runner

Tasks are defined in `.mise.toml`: `mise run test`, `mise run parity`, `mise run ci`, etc.

## Executor + reviewer loop

Implementation follows `EXECUTION_PLAN.md`. The executor applies self-contained text transforms; the reviewer
runs the verification commands and each phase's exit criteria before green-lighting the next phase.

<!-- NEXT -->
```

**Verification:** `tail -1 docs/developer-guide.md` prints `<!-- NEXT -->`

**First run `cat docs/developer-guide.md` to read the file, then make the edit.**
**Run: *(markdown — the `tail -1` check is authoritative)***

#### Task 0.4.3 — README

**File:** `README.md` (does not exist)

**Current code:** *(file does not exist)*

**Replacement code:**
```markdown
# SalahLib

Multi-language Islamic prayer-times library (AlAdhan-compatible). Targets Python, Go, TypeScript and C.

- [User Guide](docs/user-guide.md)
- [Developer Guide](docs/developer-guide.md)
- `shared/SPEC.md` — the calculation spec.
- `shared/methods.json` — the method registry.

## Quick start

```sh
mise install && mise run test
```
```

**Verification:** `test -f README.md`

**First run `cat README.md` to read the file, then make the edit.**
**Run: *(markdown — the `test -f` check is authoritative)***

---

## Phase 1 — Python kernel (reference implementation)

**Goal:** implement the pure kernel (`params.py`, `astronomy.py`), pinned by unit tests. This is the reference
every other language ports from.

**Reviewer exit criteria:**
- [ ] `uv run pytest` green.
- [ ] Kernel returns the exact legacy strings: London ISNA 2014-04-24 → Fajr `03:57`, Sunrise `05:46`,
      Dhuhr `12:59`, Asr `16:54`, Sunset `20:12`, Maghrib `20:12`, Isha `22:02`, Imsak `03:47`, Midnight `00:59`.
- [ ] Asr canary: 64°N 20°E 2024-01-22, ISNA params → Asr `11:35` (not 11:44).
- [ ] `docs/user-guide.md` documents the full Python API; `docs/developer-guide.md` documents the Python
      package layout.

### Batch 1.1 (TDD)

#### Task 1.1.1 — kernel test (red)

**File:** `python/tests/test_kernel.py` (does not exist)

**Current code:** *(file does not exist)*

**Replacement code:**
```python
from prayer_times.params import Params, LatAdjust, Midnight, Unreached, Offsets
from prayer_times.astronomy import calculate, format_time


def _params(**kw):
    defaults = dict(
        fajr_angle=15.0, isha=15.0, isha_is_minutes=False,
        maghrib=0.0, maghrib_is_minutes=False,
        imsak_mins=10.0, dhuhr_mins=0.0, asr_factor=1.0,
        lat_adjust=LatAdjust.ANGLE_BASED, midnight_mode=Midnight.STANDARD,
        unreached_policy=Unreached.CLAMP, offsets=Offsets(),
        timezone_offset_hours=1.0,
    )
    defaults.update(kw)
    return Params(**defaults)


def test_london_isna_2014():
    t = calculate(2014, 4, 24, 51.508515, -0.1254872, 0, _params())
    got = {k: format_time(v) for k, v in t.items()}
    assert got["Fajr"] == "03:57"
    assert got["Sunrise"] == "05:46"
    assert got["Dhuhr"] == "12:59"
    assert got["Asr"] == "16:54"
    assert got["Sunset"] == "20:12"
    assert got["Maghrib"] == "20:12"
    assert got["Isha"] == "22:02"
    assert got["Imsak"] == "03:47"
    assert got["Midnight"] == "00:59"


def test_asr_canary_64n():
    p = _params(fajr_angle=15.0, isha=15.0, timezone_offset_hours=1.0)
    t = calculate(2024, 1, 22, 64.0, 20.0, 0, p)
    assert format_time(t["Asr"]) == "11:35"
```

**Verification (TDD):** `cd python && uv run pytest tests/test_kernel.py -q` → **must FAIL** (no `prayer_times`
module).

**First run `cat python/tests/test_kernel.py` to read the file, then make the edit.**
**Run: `ruff format python/tests/test_kernel.py`**

#### Task 1.1.2 — `params.py`

**File:** `python/prayer_times/params.py` (does not exist)

**Current code:** *(file does not exist)*

**Replacement code:**
```python
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
```

**Verification:** `cd python && uv run python -c "from prayer_times.params import Params, LatAdjust; print(LatAdjust.ANGLE_BASED.value)"`

**First run `cat python/prayer_times/params.py` to read the file, then make the edit.**
**Run: `ruff format python/prayer_times/params.py`**

#### Task 1.1.3 — package `__init__.py`

**File:** `python/prayer_times/__init__.py` (does not exist)

**Current code:** *(file does not exist)*

**Replacement code:**
```python
from .params import Params, LatAdjust, Midnight, Unreached, Offsets

__all__ = ["Params", "LatAdjust", "Midnight", "Unreached", "Offsets"]
```

**Verification:** `cd python && uv run python -c "import prayer_times; print('ok')"`

**First run `cat python/prayer_times/__init__.py` to read the file, then make the edit.**
**Run: `ruff format python/prayer_times/__init__.py`**

### Batch 1.2

#### Task 1.2.1 — `astronomy.py` (the kernel) — part 1 of 2: math + solar

**File:** `python/prayer_times/astronomy.py` (does not exist)

**Current code:** *(file does not exist)*

**Replacement code:**
```python
"""Pure calculation kernel. Numbers and enums in, float hours out."""
import math

from .params import Params, LatAdjust, Midnight, Unreached


def mod(a: float, b: float) -> float:
    return (a % b + b) % b


def dtr(d: float) -> float:
    return d * math.pi / 180.0


def rtd(r: float) -> float:
    return r * 180.0 / math.pi


def sin(d: float) -> float:
    return math.sin(dtr(d))


def cos(d: float) -> float:
    return math.cos(dtr(d))


def tan(d: float) -> float:
    return math.tan(dtr(d))


def arcsin(x: float) -> float:
    return rtd(math.asin(x))


def arccos(x: float) -> float:
    return rtd(math.acos(x))


def arccot(x: float) -> float:
    return rtd(math.atan(1.0 / x))


def arctan2(y: float, x: float) -> float:
    return rtd(math.atan2(y, x))


def julian_day(y: int, m: int, d: int) -> float:
    if m <= 2:
        y -= 1
        m += 12
    a = math.floor(y / 100)
    b = 2 - a + math.floor(a / 4)
    return math.floor(365.25 * (y + 4716)) + math.floor(30.6001 * (m + 1)) + d + b - 1524.5


def solar_position_at(jd: float):
    """Return (declination, equation_of_time) at a Julian day."""
    d = jd - 2451545.0
    g = mod(357.529 + 0.98560028 * d, 360.0)
    q = mod(280.459 + 0.98564736 * d, 360.0)
    l = mod(q + 1.915 * sin(g) + 0.020 * sin(2 * g), 360.0)
    e = 23.439 - 0.00000036 * d
    ra = mod(arctan2(cos(e) * sin(l), cos(l)) / 15.0, 24.0)
    decl = arcsin(sin(e) * sin(l))
    eqt = q / 15.0 - ra
    return decl, eqt


def solar_noon(y: int, m: int, d: int, time: float, longitude: float) -> float:
    jd = julian_day(y, m, d) + time / 24.0 - longitude / (15.0 * 24.0)
    _, eqt = solar_position_at(jd)
    return mod(12.0 - eqt, 24.0)


def horizon_angle(elevation: float) -> float:
    return 0.833 + 0.0347 * math.sqrt(elevation)


def asr_shadow_angle(params: Params, y: int, m: int, d: int, time: float, latitude: float) -> float:
    # Asr samples declination one day ahead of the date, with no meridian correction (SPEC §13.2).
    jd = julian_day(y, m, d) + 1.0 + time / 24.0
    decl, _ = solar_position_at(jd)
    return -arccot(params.asr_factor + tan(abs(latitude - decl)))
```

**Verification:** `cd python && uv run python -c "from prayer_times.astronomy import julian_day, solar_position_at; print(julian_day(2024,3,20), solar_position_at(2460389.5)[0])"`

**First run `cat python/prayer_times/astronomy.py` to read the file, then make the edit.**
**Run: `ruff format python/prayer_times/astronomy.py`**

#### Task 1.2.2 — `astronomy.py` — part 2 of 2: orchestration + format

**File:** `python/prayer_times/astronomy.py`

**Current code:** *(the file as written in Task 1.2.1, ending with the `asr_shadow_angle` function)*

**Replacement code (append after `asr_shadow_angle`):**
```python
def depression_time(angle, y, m, d, time, latitude, longitude, direction, policy):
    jd = julian_day(y, m, d) + time / 24.0 - longitude / (15.0 * 24.0)
    decl, _ = solar_position_at(jd)
    noon = solar_noon(y, m, d, time, longitude)
    numerator = -sin(angle) - sin(latitude) * sin(decl)
    denominator = cos(latitude) * cos(decl)
    ratio = numerator / denominator
    reached = -1.0 <= ratio <= 1.0
    if policy == Unreached.CLAMP:
        ratio = max(-1.0, min(1.0, ratio))
    elif not reached:
        return float("nan"), False
    t = arccos(ratio) / 15.0
    return noon + direction * t, reached


def _night_fraction(lat_adjust, angle, night):
    if lat_adjust == LatAdjust.MIDDLE_OF_THE_NIGHT:
        return night / 2.0
    if lat_adjust == LatAdjust.ONE_SEVENTH:
        return night / 7.0
    return (angle / 60.0) * night


def calculate(y: int, m: int, d: int, latitude: float, longitude: float,
              elevation: float, params: Params) -> dict:
    horizon = horizon_angle(elevation)

    def ang(angle, time, direction):
        return depression_time(angle, y, m, d, time, latitude, longitude, direction,
                               params.unreached_policy)

    fajr, fajr_reached = ang(params.fajr_angle, 5.0, -1)
    sunrise, _ = ang(horizon, 6.0, -1)
    dhuhr = solar_noon(y, m, d, 12.0, longitude)
    asr_angle = asr_shadow_angle(params, y, m, d, 13.0, latitude)
    asr, _ = ang(asr_angle, 13.0, 1)
    sunset, _ = ang(horizon, 18.0, 1)
    maghrib, maghrib_reached = ang(params.maghrib, 18.0, 1)
    isha, isha_reached = ang(params.isha, 18.0, 1)

    # High-latitude fallback (before timezone/offsets).
    if params.lat_adjust != LatAdjust.NONE:
        night = mod(sunrise - sunset, 24.0)

        def fallback(t, base, angle, direction, reached):
            p = _night_fraction(params.lat_adjust, angle, night)
            if (not reached) or ((t - base) * direction > p):
                return base + p * direction
            return t

        fajr = fallback(fajr, sunrise, params.fajr_angle, -1, fajr_reached)
        isha = fallback(isha, sunset, params.isha, 1, isha_reached)
        maghrib = fallback(maghrib, sunset, params.maghrib, 1, maghrib_reached)

    # Timezone shift (DST is the timezone offset for that date) + minutes post-processing.
    tz = params.timezone_offset_hours - longitude / 15.0
    fajr += tz
    sunrise += tz
    dhuhr += tz
    asr += tz
    sunset += tz
    maghrib += tz
    isha += tz

    if params.maghrib_is_minutes:
        maghrib = sunset + params.maghrib / 60.0
    if params.isha_is_minutes:
        isha = maghrib + params.isha / 60.0
    dhuhr += params.dhuhr_mins / 60.0
    imsak = fajr - params.imsak_mins / 60.0

    # Night times.
    diff = mod(fajr - sunset, 24.0) if params.midnight_mode == Midnight.JAFARI else mod(sunrise - sunset, 24.0)
    midnight = sunset + diff / 2.0
    firstthird = sunset + diff / 3.0
    lastthird = sunset + 2.0 * diff / 3.0

    # Offsets (tune).
    o = params.offsets
    imsak += o.imsak / 60.0
    fajr += o.fajr / 60.0
    sunrise += o.sunrise / 60.0
    dhuhr += o.dhuhr / 60.0
    asr += o.asr / 60.0
    maghrib += o.maghrib / 60.0
    sunset += o.sunset / 60.0
    isha += o.isha / 60.0
    midnight += o.midnight / 60.0

    return {
        "Fajr": fajr, "Sunrise": sunrise, "Dhuhr": dhuhr, "Asr": asr,
        "Sunset": sunset, "Maghrib": maghrib, "Isha": isha, "Imsak": imsak,
        "Midnight": midnight, "Firstthird": firstthird, "Lastthird": lastthird,
    }


def format_time(time: float) -> str:
    if math.isnan(time):
        return "-----"
    t = mod(time + 0.5 / 60.0, 24.0)
    hours = math.floor(t)
    minutes = math.floor((t - hours) * 60.0)
    return f"{hours:02d}:{minutes:02d}"
```

**Verification (TDD):** `cd python && uv run pytest tests/test_kernel.py -q` → **must PASS** (both tests).

**First run `cat python/prayer_times/astronomy.py` to read the file, then make the edit.**
**Run: `ruff format python/prayer_times/astronomy.py`**

### Batch 1.3

#### Task 1.3.1 — `methods.py` (method registry → Params)

**File:** `python/prayer_times/methods.py` (does not exist)

**Current code:** *(file does not exist)*

**Replacement code:**
```python
"""Resolve a method code/name from methods.json into a resolved Params."""
import json
import re
from pathlib import Path

from .params import Params, LatAdjust, Midnight, Unreached, Offsets

_DATA = json.loads((Path(__file__).parent / "data" / "methods.json").read_text())
_BY_ID = {str(v["id"]): k for k, v in _DATA.items()}


def _value(x):
    m = re.match(r"[0-9.+\-]+", str(x))
    return float(m.group(0)) if m else 0.0


def _is_min(x):
    return "min" in str(x)


def method_codes():
    return list(_DATA.keys())


def resolve(method, school="STANDARD", asr_factor=None, lat_adjust="ANGLE_BASED",
            midnight_mode="STANDARD", unreached_policy="CLAMP", is_ramadan=False,
            offsets=None, timezone_offset_hours=0.0):
    key = method if method in _DATA else _BY_ID.get(str(method))
    if key is None:
        raise KeyError(f"unknown method: {method}")
    entry = _DATA[key]
    p = entry.get("params", {})

    fajr = _value(p.get("Fajr", 0))
    isha = p.get("Isha", 0)
    maghrib = p.get("Maghrib", 0)
    imsak = _value(p.get("Imsak", "10 min"))
    dhuhr = _value(p.get("Dhuhr", "0 min"))
    af = asr_factor if asr_factor is not None else (2.0 if school == "HANAFI" else 1.0)

    off = dict(entry.get("defaultTune", {}))
    if is_ramadan:
        off.update(entry.get("ramadanTune", {}))
    if offsets:
        for k, v in offsets.items():
            if v != 0:
                off[k] = v
    o = Offsets(**{k.lower(): float(v) for k, v in off.items()})

    return Params(
        fajr_angle=fajr,
        isha=_value(isha), isha_is_minutes=_is_min(isha),
        maghrib=_value(maghrib), maghrib_is_minutes=_is_min(maghrib),
        imsak_mins=imsak, dhuhr_mins=dhuhr, asr_factor=af,
        lat_adjust=LatAdjust(lat_adjust),
        midnight_mode=Midnight(midnight_mode),
        unreached_policy=Unreached(unreached_policy),
        offsets=o,
        timezone_offset_hours=timezone_offset_hours,
    )


def method_meta(method):
    key = method if method in _DATA else _BY_ID.get(str(method))
    if key is None:
        raise KeyError(f"unknown method: {method}")
    return key, _DATA[key]
```

**Verification:** `cd python && uv run python -c "from prayer_times.methods import resolve, method_codes; print(len(method_codes()), resolve('ISNA').fajr_angle)"`

**First run `cat python/prayer_times/methods.py` to read the file, then make the edit.**
**Run: `ruff format python/prayer_times/methods.py`**

#### Task 1.3.2 — `facade.py`

**File:** `python/prayer_times/facade.py` (does not exist)

**Current code:** *(file does not exist)*

**Replacement code:**
```python
"""Public API: PrayerTimes facade."""
from datetime import datetime
from zoneinfo import ZoneInfo

from .astronomy import calculate, format_time
from .methods import resolve, method_meta
from .params import Offsets


def _tz_offset_hours(y, m, d, tz):
    return datetime(y, m, d, tzinfo=ZoneInfo(tz)).utcoffset().total_seconds() / 3600.0


def _fmt(t, fmt):
    if fmt == "Float":
        return t
    if fmt == "24h":
        return format_time(t)
    if fmt == "12h":
        s = format_time(t)
        h = int(s.split(":")[0])
        suffix = "am" if h < 12 else "pm"
        return f"{((h + 11) % 12) + 1}:{s.split(':')[1]} {suffix}"
    if fmt == "12hNS":
        s = format_time(t)
        return f"{((int(s.split(':')[0]) + 11) % 12) + 1}:{s.split(':')[1]}"
    raise ValueError(f"unknown format: {fmt}")


class PrayerTimes:
    def __init__(self, method, school="STANDARD", asr_shadow_factor=None):
        self.method = method
        self.school = school
        self.asr_shadow_factor = asr_shadow_factor

    def get_times(self, dt, latitude, longitude, elevation=0.0,
                  lat_adjust="ANGLE_BASED", midnight_mode=None, tz="UTC",
                  fmt="24h", is_ramadan=False, tune=None):
        y, m, d = dt.year, dt.month, dt.day
        midnight = midnight_mode or "STANDARD"
        params = resolve(
            self.method, school=self.school, asr_factor=self.asr_shadow_factor,
            lat_adjust=lat_adjust, midnight_mode=midnight,
            is_ramadan=is_ramadan, offsets=tune,
            timezone_offset_hours=_tz_offset_hours(y, m, d, tz),
        )
        raw = calculate(y, m, d, latitude, longitude, elevation, params)
        return {k: _fmt(v, fmt) for k, v in raw.items()}

    def to_aladhan_response(self, dt, latitude, longitude, elevation=0.0,
                            lat_adjust="ANGLE_BASED", midnight_mode=None, tz="UTC",
                            is_ramadan=False, tune=None):
        y, m, d = dt.year, dt.month, dt.day
        midnight = midnight_mode or "STANDARD"
        key, entry = method_meta(self.method)
        params = resolve(
            self.method, school=self.school, asr_factor=self.asr_shadow_factor,
            lat_adjust=lat_adjust, midnight_mode=midnight,
            is_ramadan=is_ramadan, offsets=tune,
            timezone_offset_hours=_tz_offset_hours(y, m, d, tz),
        )
        raw = calculate(y, m, d, latitude, longitude, elevation, params)
        timings = {k: format_time(v) for k, v in raw.items()}
        off = dict(entry.get("defaultTune", {}))
        if is_ramadan:
            off.update(entry.get("ramadanTune", {}))
        offset_meta = {}
        for k in Offsets.__dataclass_fields__:
            keyname = k.capitalize()
            offset_meta[k] = int(off.get(keyname, 0))
        if tune:
            for k, v in tune.items():
                if v != 0:
                    offset_meta[k.lower()] = str(v)
        meta = {
            "latitude": latitude, "longitude": longitude, "timezone": tz,
            "method": {
                "id": entry["id"], "name": entry.get("name", ""),
                "params": entry.get("params", {}),
                "location": entry.get("location"),
            },
            "latitudeAdjustmentMethod": lat_adjust,
            "midnightMode": midnight,
            "school": self.school,
            "offset": {k.capitalize(): v for k, v in offset_meta.items()},
        }
        if str(self.method) == "15" or self.method == "MOONSIGHTING":
            meta["latitudeAdjustmentMethod"] = "NONE"
        return {"timings": timings, "meta": meta}
```

**Verification:** `cd python && uv run python -c "from prayer_times.facade import PrayerTimes; from datetime import date; print(PrayerTimes('ISNA').get_times(date(2014,4,24), 51.508515, -0.1254872, tz='Europe/London'))"`

**First run `cat python/prayer_times/facade.py` to read the file, then make the edit.**
**Run: `ruff format python/prayer_times/facade.py`**

#### Task 1.3.3 — re-export facade from `__init__.py`

**File:** `python/prayer_times/__init__.py`

**Current code:**
```python
from .params import Params, LatAdjust, Midnight, Unreached, Offsets

__all__ = ["Params", "LatAdjust", "Midnight", "Unreached", "Offsets"]
```

**Replacement code:**
```python
from .params import Params, LatAdjust, Midnight, Unreached, Offsets
from .facade import PrayerTimes

__all__ = ["PrayerTimes", "Params", "LatAdjust", "Midnight", "Unreached", "Offsets"]
```

**Verification:** `cd python && uv run python -c "from prayer_times import PrayerTimes; print('ok')"`

**First run `cat python/prayer_times/__init__.py` to read the file, then make the edit.**
**Run: `ruff format python/prayer_times/__init__.py`**

### Batch 1.4 — documentation

#### Task 1.4.1 — user guide: Python API

**File:** `docs/user-guide.md`

**Current code:**
```
<!-- NEXT -->
```

**Replacement code:**
```markdown
## Python API

```python
from datetime import date
from prayer_times import PrayerTimes

pt = PrayerTimes("ISNA", school="STANDARD")            # or method id 2
times = pt.get_times(date(2024, 4, 24), 51.508515, -0.1254872,
                     elevation=0, lat_adjust="ANGLE_BASED", tz="Europe/London",
                     fmt="24h", is_ramadan=False, tune=None)
```

- `method` — name (`"ISNA"`) or id (`2`).
- `school` — `"STANDARD"` (Asr shadow factor 1) or `"HANAFI"` (2).
- `fmt` — `"24h"`, `"12h"`, `"12hNS"`, `"Float"`.
- `tune` — a dict of minute offsets keyed by prayer (e.g. `{"Fajr": 3}`).
- `is_ramadan` — enable the MAKKAH Ramadan Isha +120 min rule.
- `tz` — IANA timezone string (DST handled automatically).

`to_aladhan_response(...)` returns the full AlAdhan `{timings, meta}` envelope.

<!-- NEXT -->
```

**Verification:** `tail -1 docs/user-guide.md` prints `<!-- NEXT -->`

**First run `cat docs/user-guide.md` to read the file, then make the edit.**
**Run: *(markdown — the `tail -1` check is authoritative)***

#### Task 1.4.2 — developer guide: Python layout

**File:** `docs/developer-guide.md`

**Current code:**
```
<!-- NEXT -->
```

**Replacement code:**
```markdown
## Python package layout

- `prayer_times/params.py` — `Params`/`Offsets` dataclasses + enums (the string-free seam).
- `prayer_times/astronomy.py` — the pure kernel (`calculate`, `format_time`).
- `prayer_times/methods.py` — loads `data/methods.json`, resolves method → `Params`.
- `prayer_times/facade.py` — `PrayerTimes` public API + `to_aladhan_response`.

Known-good values (London ISNA 2014-04-24) and the 64°N Asr canary are pinned in `tests/test_kernel.py`.

<!-- NEXT -->
```

**Verification:** `tail -1 docs/developer-guide.md` prints `<!-- NEXT -->`

**First run `cat docs/developer-guide.md` to read the file, then make the edit.**
**Run: *(markdown — the `tail -1` check is authoritative)***

---

## Phase 2 — Golden vectors + AlAdhan black-box testing

**Goal:** generate committed golden vectors from the AlAdhan API (manual), and a test that asserts
string-equality against them. This is the black-box accuracy gate.

**Reviewer exit criteria:**
- [ ] `scripts/generate_fixtures.py` runs and writes `shared/vectors/aladhan/*.json`.
- [ ] `test_aladhan.py` passes against the committed vectors.
- [ ] The Asr now-fill envelope is handled (assert `API ∈ {static_pred, nowfill_pred}` within 1 minute).
- [ ] `docs/developer-guide.md` documents fixture generation and the black-box gate.

### Batch 2.1

#### Task 2.1.1 — fixture generator (manual task, network)

**File:** `scripts/generate_fixtures.py` (does not exist)

**Current code:** *(file does not exist)*

**Replacement code:**
```python
#!/usr/bin/env python3
"""Fetch golden vectors from the AlAdhan API (MANUAL — not in CI)."""
import json
import urllib.request
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "shared" / "vectors" / "aladhan"
CASES = [
    ("london_isna", "24-04-2014", 51.508515, -0.1254872, 2, 0),
    ("london_mwl", "24-04-2014", 51.508515, -0.1254872, 3, 0),
    ("makkah", "20-03-2024", 21.3890824, 39.8579118, 4, 0),
    ("makkah_ramadan", "11-03-2024", 21.3890824, 39.8579118, 4, 0),
    ("ankara_turkey", "24-04-2024", 39.9333635, 32.8597419, 13, 0),
    ("sydney_south", "20-06-2024", -33.8688, 151.2093, 3, 0),
    ("high_lat_65n", "20-06-2024", 65.0, 20.0, 3, 0),
]


def fetch(date_str, lat, lng, method, school):
    url = (f"https://api.aladhan.com/v1/timings/{date_str}"
           f"?latitude={lat}&longitude={lng}&method={method}&school={school}")
    with urllib.request.urlopen(url) as r:
        return json.load(r)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for name, date_str, lat, lng, method, school in CASES:
        data = fetch(date_str, lat, lng, method, school)
        (OUT / f"{name}.json").write_text(json.dumps(data["data"], indent=2))
        print(f"wrote {name}.json")


if __name__ == "__main__":
    main()
```

**Verification (network, manual):** `python3 scripts/generate_fixtures.py && ls shared/vectors/aladhan/`

**First run `cat scripts/generate_fixtures.py` to read the file, then make the edit.**
**Run: `ruff format scripts/generate_fixtures.py`**

#### Task 2.1.2 — AlAdhan black-box test

**File:** `python/tests/test_aladhan.py` (does not exist)

**Current code:** *(file does not exist)*

**Replacement code:**
```python
import json
from datetime import datetime
from pathlib import Path

from prayer_times import PrayerTimes

VECTORS = Path(__file__).resolve().parent.parent.parent / "shared" / "vectors" / "aladhan"


def _date(meta_date):
    d, m, y = meta_date["gregorian"]["date"].split("-")
    return datetime(int(y), int(m), int(d))


def _to_min(hhmm):
    h, m = hhmm.split(":")
    return int(h) * 60 + int(m)


def test_golden_vectors():
    for f in sorted(VECTORS.glob("*.json")):
        data = json.loads(f.read_text())
        meta = data["meta"]
        pt = PrayerTimes(meta["method"]["id"], school=meta.get("school", "STANDARD"))
        times = pt.get_times(
            _date(data["date"]), meta["latitude"], meta["longitude"],
            tz=meta["timezone"], is_ramadan=(f.stem == "makkah_ramadan"),
        )
        expected = data["timings"]
        for k in ("Fajr", "Sunrise", "Dhuhr", "Sunset", "Maghrib", "Isha", "Imsak"):
            assert times[k] == expected[k], f"{f.stem} {k}: {times[k]} != {expected[k]}"
        assert abs(_to_min(times["Asr"]) - _to_min(expected["Asr"])) <= 1, f"{f.stem} Asr"
```

**Verification:** `cd python && uv run pytest tests/test_aladhan.py -q`

**First run `cat python/tests/test_aladhan.py` to read the file, then make the edit.**
**Run: `ruff format python/tests/test_aladhan.py`**

#### Task 2.1.3 — developer guide: black-box testing

**File:** `docs/developer-guide.md`

**Current code:**
```
<!-- NEXT -->
```

**Replacement code:**
```markdown
## AlAdhan black-box testing

Golden vectors live in `shared/vectors/aladhan/*.json` (committed). Regenerate manually:

```sh
python3 scripts/generate_fixtures.py   # network — NOT in CI
```

`python/tests/test_aladhan.py` asserts string-equality against those vectors. Asr is asserted within 1 minute
(the live API's Asr is server-clock-dependent — see SPEC §13.2); all other timings must match exactly.

<!-- NEXT -->
```

**Verification:** `tail -1 docs/developer-guide.md` prints `<!-- NEXT -->`

**First run `cat docs/developer-guide.md` to read the file, then make the edit.**
**Run: *(markdown — the `tail -1` check is authoritative)***

---

## Phase 3 — Go port

**Goal:** faithful port of the kernel + facade, pinned by the same known values.

**Reviewer exit criteria:**
- [ ] `cd go && go test ./...` green.
- [ ] `go test` asserts London ISNA 2014-04-24 → `Fajr == "03:57"` (etc.) and Asr canary `11:35`.
- [ ] `gofmt -l .` reports no files.
- [ ] `docs/user-guide.md` documents the Go API; `docs/developer-guide.md` documents the Go layout.

### Batch 3.1

#### Task 3.1.1 — `params.go`

**File:** `go/pkg/prayertimes/params.go` (does not exist)

**Current code:** *(file does not exist)*

**Replacement code:**
```go
package prayertimes

// LatAdjust selects the high-latitude fallback rule.
type LatAdjust string

const (
	LatNone          LatAdjust = "NONE"
	LatMiddleOfNight LatAdjust = "MIDDLE_OF_THE_NIGHT"
	LatOneSeventh    LatAdjust = "ONE_SEVENTH"
	LatAngleBased    LatAdjust = "ANGLE_BASED"
)

// Midnight selects the midnight definition.
type Midnight string

const (
	MidStandard Midnight = "STANDARD"
	MidJafari   Midnight = "JAFARI"
)

// Unreached selects the policy when the sun never reaches a depression angle.
type Unreached string

const (
	UnreachedClamp Unreached = "CLAMP"
	UnreachedNaN   Unreached = "NAN"
)

// Offsets holds the nine tunable minute offsets.
type Offsets struct {
	Imsak, Fajr, Sunrise, Dhuhr, Asr, Maghrib, Sunset, Isha, Midnight float64
}

// Params is the fully-resolved, string-free input model.
type Params struct {
	FajrAngle           float64
	Isha                float64
	IshaIsMinutes       bool
	Maghrib             float64
	MaghribIsMinutes    bool
	ImsakMins           float64
	DhuhrMins           float64
	AsrFactor           float64
	LatAdjust           LatAdjust
	MidnightMode        Midnight
	UnreachedPolicy     Unreached
	Offsets             Offsets
	TimezoneOffsetHours float64
}
```

**Verification:** `cd go && go build ./...`

**First run `cat go/pkg/prayertimes/params.go` to read the file, then make the edit.**
**Run: `gofmt -w go/pkg/prayertimes/params.go`**

#### Task 3.1.2 — `astronomy.go` — part 1 of 2

**File:** `go/pkg/prayertimes/astronomy.go` (does not exist)

**Current code:** *(file does not exist)*

**Replacement code:**
```go
package prayertimes

import "math"

func mod(a, b float64) float64 {
	r := math.Mod(a, b)
	if r < 0 {
		r += b
	}
	return r
}

func dtr(d float64) float64 { return d * math.Pi / 180.0 }
func rtd(r float64) float64 { return r * 180.0 / math.Pi }

func sin(d float64) float64 { return math.Sin(dtr(d)) }
func cos(d float64) float64 { return math.Cos(dtr(d)) }
func tan(d float64) float64 { return math.Tan(dtr(d)) }

func arcsin(x float64) float64 { return rtd(math.Asin(x)) }
func arccos(x float64) float64 { return rtd(math.Acos(x)) }
func arccot(x float64) float64 { return rtd(math.Atan(1.0 / x)) }
func arctan2(y, x float64) float64 {
	return rtd(math.Atan2(y, x))
}

func julianDay(y, m, d int) float64 {
	if m <= 2 {
		y--
		m += 12
	}
	a := math.Floor(float64(y) / 100)
	b := 2 - a + math.Floor(a/4)
	return math.Floor(365.25*float64(y+4716)) + math.Floor(30.6001*float64(m+1)) + float64(d) + b - 1524.5
}

func solarPositionAt(jd float64) (decl, eqt float64) {
	d := jd - 2451545.0
	g := mod(357.529+0.98560028*d, 360.0)
	q := mod(280.459+0.98564736*d, 360.0)
	l := mod(q+1.915*sin(g)+0.020*sin(2*g), 360.0)
	e := 23.439 - 0.00000036*d
	ra := mod(arctan2(cos(e)*sin(l), cos(l))/15.0, 24.0)
	return arcsin(sin(e) * sin(l)), q/15.0 - ra
}

func solarNoon(y, m, d int, time, longitude float64) float64 {
	jd := julianDay(y, m, d) + time/24.0 - longitude/(15.0*24.0)
	_, eqt := solarPositionAt(jd)
	return mod(12.0-eqt, 24.0)
}

func horizonAngle(elevation float64) float64 {
	return 0.833 + 0.0347*math.Sqrt(elevation)
}

func asrShadowAngle(p Params, y, m, d int, time, latitude float64) float64 {
	jd := julianDay(y, m, d) + 1.0 + time/24.0
	decl, _ := solarPositionAt(jd)
	return -arccot(p.AsrFactor + tan(math.Abs(latitude-decl)))
}
```

**Verification:** `cd go && go build ./...`

**First run `cat go/pkg/prayertimes/astronomy.go` to read the file, then make the edit.**
**Run: `gofmt -w go/pkg/prayertimes/astronomy.go`**

#### Task 3.1.3 — `astronomy.go` — part 2 of 2

**File:** `go/pkg/prayertimes/astronomy.go`

**Current code:** *(the file as written in Task 3.1.2, ending with `asrShadowAngle`)*

**Replacement code (append, and add `"fmt"` to the import block):**
```go
import "fmt"

func depressionTime(angle float64, y, m, d int, time, latitude, longitude float64, direction int, policy Unreached) (float64, bool) {
	jd := julianDay(y, m, d) + time/24.0 - longitude/(15.0*24.0)
	decl, _ := solarPositionAt(jd)
	noon := solarNoon(y, m, d, time, longitude)
	numerator := -sin(angle) - sin(latitude)*sin(decl)
	denominator := cos(latitude) * cos(decl)
	ratio := numerator / denominator
	reached := ratio >= -1.0 && ratio <= 1.0
	if policy == UnreachedClamp {
		ratio = math.Max(-1.0, math.Min(1.0, ratio))
	} else if !reached {
		return math.NaN(), false
	}
	t := arccos(ratio) / 15.0
	return noon + float64(direction)*t, reached
}

func nightFraction(la LatAdjust, angle, night float64) float64 {
	switch la {
	case LatMiddleOfNight:
		return night / 2.0
	case LatOneSeventh:
		return night / 7.0
	default:
		return angle / 60.0 * night
	}
}

// RawTimes holds float "hours of day" for every prayer.
type RawTimes struct {
	Fajr, Sunrise, Dhuhr, Asr, Sunset, Maghrib, Isha, Imsak float64
	Midnight, Firstthird, Lastthird                       float64
}

// Calculate is the pure kernel.
func Calculate(y, m, d int, latitude, longitude, elevation float64, p Params) RawTimes {
	horizon := horizonAngle(elevation)

	ang := func(angle, time float64, dir int) (float64, bool) {
		return depressionTime(angle, y, m, d, time, latitude, longitude, dir, p.UnreachedPolicy)
	}

	fajr, fajrReached := ang(p.FajrAngle, 5.0, -1)
	sunrise, _ := ang(horizon, 6.0, -1)
	dhuhr := solarNoon(y, m, d, 12.0, longitude)
	asrAngle := asrShadowAngle(p, y, m, d, 13.0, latitude)
	asr, _ := ang(asrAngle, 13.0, 1)
	sunset, _ := ang(horizon, 18.0, 1)
	maghrib, maghribReached := ang(p.Maghrib, 18.0, 1)
	isha, ishaReached := ang(p.Isha, 18.0, 1)

	if p.LatAdjust != LatNone {
		night := mod(sunrise-sunset, 24.0)
		fallback := func(t, base, angle float64, dir int, reached bool) float64 {
			portion := nightFraction(p.LatAdjust, angle, night)
			if !reached || (t-base)*float64(dir) > portion {
				return base + portion*float64(dir)
			}
			return t
		}
		fajr = fallback(fajr, sunrise, p.FajrAngle, -1, fajrReached)
		isha = fallback(isha, sunset, p.Isha, 1, ishaReached)
		maghrib = fallback(maghrib, sunset, p.Maghrib, 1, maghribReached)
	}

	tz := p.TimezoneOffsetHours - longitude/15.0
	fajr += tz
	sunrise += tz
	dhuhr += tz
	asr += tz
	sunset += tz
	maghrib += tz
	isha += tz

	if p.MaghribIsMinutes {
		maghrib = sunset + p.Maghrib/60.0
	}
	if p.IshaIsMinutes {
		isha = maghrib + p.Isha/60.0
	}
	dhuhr += p.DhuhrMins / 60.0
	imsak := fajr - p.ImsakMins/60.0

	var diff float64
	if p.MidnightMode == MidJafari {
		diff = mod(fajr-sunset, 24.0)
	} else {
		diff = mod(sunrise-sunset, 24.0)
	}
	midnight := sunset + diff/2.0
	firstthird := sunset + diff/3.0
	lastthird := sunset + 2.0*diff/3.0

	o := p.Offsets
	imsak += o.Imsak / 60.0
	fajr += o.Fajr / 60.0
	sunrise += o.Sunrise / 60.0
	dhuhr += o.Dhuhr / 60.0
	asr += o.Asr / 60.0
	maghrib += o.Maghrib / 60.0
	sunset += o.Sunset / 60.0
	isha += o.Isha / 60.0
	midnight += o.Midnight / 60.0

	return RawTimes{
		Fajr: fajr, Sunrise: sunrise, Dhuhr: dhuhr, Asr: asr,
		Sunset: sunset, Maghrib: maghrib, Isha: isha, Imsak: imsak,
		Midnight: midnight, Firstthird: firstthird, Lastthird: lastthird,
	}
}

// FormatTime renders a float hour as 24h "HH:MM".
func FormatTime(t float64) string {
	if math.IsNaN(t) {
		return "-----"
	}
	x := mod(t+0.5/60.0, 24.0)
	h := int(math.Floor(x))
	mm := int(math.Floor((x - float64(h)) * 60.0))
	return fmt.Sprintf("%02d:%02d", h, mm)
}
```

**Verification:** `cd go && go test ./...`

**First run `cat go/pkg/prayertimes/astronomy.go` to read the file, then make the edit.**
**Run: `gofmt -w go/pkg/prayertimes/astronomy.go`**

*(Note: `FormatTime` uses `fmt`; ensure the file's import block reads `import ("fmt"; "math")` after this edit.
The verification `go test ./...` will catch a missing import.)*

### Batch 3.2

#### Task 3.2.1 — `methods.go`

**File:** `go/pkg/prayertimes/methods.go` (does not exist)

**Current code:** *(file does not exist)*

**Replacement code:**
```go
package prayertimes

import (
	_ "embed"
	"encoding/json"
	"fmt"
	"regexp"
	"strconv"
)

//go:embed methods.json
var methodsJSON []byte

type methodEntry struct {
	ID          int                    `json:"id"`
	Name        string                 `json:"name"`
	Params      map[string]interface{} `json:"params"`
	Location    map[string]float64     `json:"location"`
	DefaultTune map[string]float64     `json:"defaultTune"`
	RamadanTune map[string]float64     `json:"ramadanTune"`
}

var methods map[string]methodEntry

func init() {
	methods = map[string]methodEntry{}
	if err := json.Unmarshal(methodsJSON, &methods); err != nil {
		panic(err)
	}
}

var numRe = regexp.MustCompile(`[0-9.+\-]+`)
var minRe = regexp.MustCompile(`min`)

func value(x interface{}) float64 {
	m := numRe.FindString(fmt.Sprint(x))
	if m == "" {
		return 0
	}
	f, _ := strconv.ParseFloat(m, 64)
	return f
}

func isMin(x interface{}) bool {
	return minRe.MatchString(fmt.Sprint(x))
}

// Resolve converts a method code/name into a resolved Params.
func Resolve(method, school string, asrFactor *float64, latAdjust LatAdjust, midnight Midnight, policy Unreached, isRamadan bool, tune map[string]float64, tzOffset float64) (Params, error) {
	entry, ok := methods[method]
	if !ok {
		for k, v := range methods {
			if strconv.Itoa(v.ID) == method {
				entry, ok = v, true
				break
			}
		}
	}
	if !ok {
		return Params{}, fmt.Errorf("unknown method %s", method)
	}
	p := entry.Params
	af := 1.0
	if asrFactor != nil {
		af = *asrFactor
	} else if school == "HANAFI" {
		af = 2.0
	}
	offsets := map[string]float64{}
	for k, v := range entry.DefaultTune {
		offsets[k] = v
	}
	if isRamadan {
		for k, v := range entry.RamadanTune {
			offsets[k] = v
		}
	}
	if tune != nil {
		for k, v := range tune {
			if v != 0 {
				offsets[k] = v
			}
		}
	}
	imsak := p["Imsak"]
	if imsak == nil {
		imsak = "10 min"
	}
	dhuhr := p["Dhuhr"]
	if dhuhr == nil {
		dhuhr = "0 min"
	}
	return Params{
		FajrAngle:        value(p["Fajr"]),
		Isha:             value(p["Isha"]),
		IshaIsMinutes:    isMin(p["Isha"]),
		Maghrib:          value(p["Maghrib"]),
		MaghribIsMinutes: isMin(p["Maghrib"]),
		ImsakMins:        value(imsak),
		DhuhrMins:        value(dhuhr),
		AsrFactor:        af,
		LatAdjust:        latAdjust,
		MidnightMode:     midnight,
		UnreachedPolicy:  policy,
		Offsets: Offsets{
			Imsak: offsets["Imsak"], Fajr: offsets["Fajr"], Sunrise: offsets["Sunrise"],
			Dhuhr: offsets["Dhuhr"], Asr: offsets["Asr"], Maghrib: offsets["Maghrib"],
			Sunset: offsets["Sunset"], Isha: offsets["Isha"], Midnight: offsets["Midnight"],
		},
		TimezoneOffsetHours: tzOffset,
	}, nil
}
```

**Verification:** `cd go && go build ./...`

**First run `cat go/pkg/prayertimes/methods.go` to read the file, then make the edit.**
**Run: `gofmt -w go/pkg/prayertimes/methods.go`**

#### Task 3.2.2 — Go test (TDD)

**File:** `go/pkg/prayertimes/prayertimes_test.go` (does not exist)

**Current code:** *(file does not exist)*

**Replacement code:**
```go
package prayertimes

import "testing"

func testParams() Params {
	return Params{
		FajrAngle: 15, Isha: 15, ImsakMins: 10, AsrFactor: 1,
		LatAdjust: LatAngleBased, MidnightMode: MidStandard,
		UnreachedPolicy: UnreachedClamp, TimezoneOffsetHours: 1.0,
	}
}

func TestLondonIsna2014(t *testing.T) {
	got := Calculate(2014, 4, 24, 51.508515, -0.1254872, 0, testParams())
	for name, want := range map[string]string{
		"Fajr": "03:57", "Sunrise": "05:46", "Dhuhr": "12:59", "Asr": "16:54",
		"Sunset": "20:12", "Maghrib": "20:12", "Isha": "22:02", "Imsak": "03:47",
		"Midnight": "00:59",
	} {
		var gotS string
		switch name {
		case "Fajr":
			gotS = FormatTime(got.Fajr)
		case "Sunrise":
			gotS = FormatTime(got.Sunrise)
		case "Dhuhr":
			gotS = FormatTime(got.Dhuhr)
		case "Asr":
			gotS = FormatTime(got.Asr)
		case "Sunset":
			gotS = FormatTime(got.Sunset)
		case "Maghrib":
			gotS = FormatTime(got.Maghrib)
		case "Isha":
			gotS = FormatTime(got.Isha)
		case "Imsak":
			gotS = FormatTime(got.Imsak)
		case "Midnight":
			gotS = FormatTime(got.Midnight)
		}
		if gotS != want {
			t.Fatalf("%s = %s, want %s", name, gotS, want)
		}
	}
}

func TestAsrCanary64N(t *testing.T) {
	got := Calculate(2024, 1, 22, 64.0, 20.0, 0, testParams())
	if s := FormatTime(got.Asr); s != "11:35" {
		t.Fatalf("Asr = %s, want 11:35", s)
	}
}
```

**Verification (TDD):** `cd go && go test ./...` → **must PASS**.

**First run `cat go/pkg/prayertimes/prayertimes_test.go` to read the file, then make the edit.**
**Run: `gofmt -w go/pkg/prayertimes/prayertimes_test.go`**

#### Task 3.2.3 — docs (user + developer)

**File:** `docs/user-guide.md`

**Current code:**
```
<!-- NEXT -->
```

**Replacement code:**
```markdown
## Go

```go
import (
    "fmt"
    "time"
    prayertimes "github.com/salahlib/prayertimes/pkg/prayertimes"
)

pt := prayertimes.New("ISNA", "STANDARD")
t := pt.GetTimes(time.Date(2024, 4, 24, 0, 0, 0, 0, time.UTC), 51.508515, -0.1254872, "Europe/London")
fmt.Println(t.Fajr) // "03:57"
```

See the package godoc for `New`, `GetTimes`, `Tune` and `ToAlAdhanResponse`.

<!-- NEXT -->
```

**Verification:** `tail -1 docs/user-guide.md` prints `<!-- NEXT -->`

**First run `cat docs/user-guide.md` to read the file, then make the edit.**
**Run: *(markdown — the `tail -1` check is authoritative)***

**File:** `docs/developer-guide.md`

**Current code:**
```
<!-- NEXT -->
```

**Replacement code:**
```markdown
## Go package layout

- `pkg/prayertimes/params.go` — `Params`/`Offsets` structs + enum constants.
- `pkg/prayertimes/astronomy.go` — the pure kernel (`Calculate`, `FormatTime`).
- `pkg/prayertimes/methods.go` — `//go:embed methods.json` + `Resolve`.
- `pkg/prayertimes/facade.go` — `New`, `GetTimes`, `ToAlAdhanResponse` (added next).

`methods.json` is embedded via `go:embed`; regenerate it with `mise run sync-data`.

<!-- NEXT -->
```

**Verification:** `tail -1 docs/developer-guide.md` prints `<!-- NEXT -->`

**First run `cat docs/developer-guide.md` to read the file, then make the edit.**
**Run: *(markdown — the `tail -1` check is authoritative)***

---

## Phase 4 — TypeScript port

**Goal:** faithful port of kernel + facade, pinned by the same known values.

**Reviewer exit criteria:**
- [ ] `cd typescript && bun test` green.
- [ ] Test asserts London ISNA 2014-04-24 → `Fajr == "03:57"` and Asr canary `11:35`.
- [ ] `bunx tsc --noEmit` clean.
- [ ] `docs/user-guide.md` documents the TS API; `docs/developer-guide.md` documents the TS layout.

### Batch 4.1

#### Task 4.1.1 — `params.ts`

**File:** `typescript/src/params.ts` (does not exist)

**Current code:** *(file does not exist)*

**Replacement code:**
```typescript
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
```

**Verification:** `cd typescript && bunx tsc --noEmit`

**First run `cat typescript/src/params.ts` to read the file, then make the edit.**
**Run: `bunx prettier --write typescript/src/params.ts`**

#### Task 4.1.2 — `astronomy.ts` — part 1 of 2

**File:** `typescript/src/astronomy.ts` (does not exist)

**Current code:** *(file does not exist)*

**Replacement code:**
```typescript
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
```

**Verification:** `cd typescript && bunx tsc --noEmit`

**First run `cat typescript/src/astronomy.ts` to read the file, then make the edit.**
**Run: `bunx prettier --write typescript/src/astronomy.ts`**

#### Task 4.1.3 — `astronomy.ts` — part 2 of 2

**File:** `typescript/src/astronomy.ts`

**Current code:** *(the file as written in Task 4.1.2, ending with `asrShadowAngle`)*

**Replacement code (append):**
```typescript
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
```

**Verification:** `cd typescript && bunx tsc --noEmit`

**First run `cat typescript/src/astronomy.ts` to read the file, then make the edit.**
**Run: `bunx prettier --write typescript/src/astronomy.ts`**

### Batch 4.2

#### Task 4.2.1 — TS test (TDD)

**File:** `typescript/src/astronomy.test.ts` (does not exist)

**Current code:** *(file does not exist)*

**Replacement code:**
```typescript
import { test, expect } from "bun:test";
import { calculate, formatTime } from "./astronomy.js";
import { Params, zeroOffsets } from "./params.js";

function p(over: Partial<Params> = {}): Params {
  return {
    fajrAngle: 15, isha: 15, ishaIsMinutes: false,
    maghrib: 0, maghribIsMinutes: false,
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
  expect(formatTime(t.Asr)).toBe("16:54");
  expect(formatTime(t.Isha)).toBe("22:02");
  expect(formatTime(t.Midnight)).toBe("00:59");
});

test("Asr canary 64N", () => {
  const t = calculate(2024, 1, 22, 64.0, 20.0, 0, p());
  expect(formatTime(t.Asr)).toBe("11:35");
});
```

**Verification (TDD):** `cd typescript && bun test` → **must PASS**.

**First run `cat typescript/src/astronomy.test.ts` to read the file, then make the edit.**
**Run: `bunx prettier --write typescript/src/astronomy.test.ts`**

#### Task 4.2.2 — docs (user + developer)

**File:** `docs/user-guide.md`

**Current code:**
```
<!-- NEXT -->
```

**Replacement code:**
```markdown
## TypeScript / JavaScript

```ts
import { PrayerTimes } from "prayer-times";

const pt = new PrayerTimes("ISNA");
const times = pt.getTimes(new Date(2024, 3, 24), 51.508515, -0.1254872, {
  timezone: "Europe/London",
});
console.log(times.Fajr); // "03:57"
```

<!-- NEXT -->
```

**Verification:** `tail -1 docs/user-guide.md` prints `<!-- NEXT -->`

**First run `cat docs/user-guide.md` to read the file, then make the edit.**
**Run: *(markdown — the `tail -1` check is authoritative)***

**File:** `docs/developer-guide.md`

**Current code:**
```
<!-- NEXT -->
```

**Replacement code:**
```markdown
## TypeScript package layout

- `src/params.ts` — `Params`/`Offsets` types.
- `src/astronomy.ts` — the pure kernel (`calculate`, `formatTime`).
- `src/methods.ts` — imports `methods.json` (`resolveJsonModule`) + `resolve`.
- `src/facade.ts` — `PrayerTimes` class (added next).

`methods.json` is imported directly (bun/tsc resolve JSON); regenerate with `mise run sync-data`.

<!-- NEXT -->
```

**Verification:** `tail -1 docs/developer-guide.md` prints `<!-- NEXT -->`

**First run `cat docs/developer-guide.md` to read the file, then make the edit.**
**Run: *(markdown — the `tail -1` check is authoritative)***

---

## Phase 5 — C port

**Goal:** the pure kernel as a C static library + a dump CLI (for cross-language parity). C provides the
kernel only; method resolution and JSON remain in the higher-level languages.

**Reviewer exit criteria:**
- [ ] `cd c && cmake -B build && cmake --build build && ctest` green.
- [ ] `./build/prayer_times_dump 2014 4 24 51.508515 -0.1254872 0 15 15 0 0 1` prints Fajr ≈ 3.958 (03:57).
- [ ] `docs/user-guide.md` documents the C API; `docs/developer-guide.md` documents the C build.

### Batch 5.1

#### Task 5.1.1 — `prayer_times.h`

**File:** `c/include/prayer_times.h` (does not exist)

**Current code:** *(file does not exist)*

**Replacement code:**
```c
#ifndef PRAYER_TIMES_H
#define PRAYER_TIMES_H

typedef struct {
    double fajr_angle;
    double isha;
    int isha_is_minutes;
    double maghrib;
    int maghrib_is_minutes;
    double imsak_mins;
    double dhuhr_mins;
    double asr_factor;
    int lat_adjust;       /* 0 NONE, 1 MIDDLE_OF_THE_NIGHT, 2 ONE_SEVENTH, 3 ANGLE_BASED */
    int midnight_mode;    /* 0 STANDARD, 1 JAFARI */
    int unreached_policy; /* 0 CLAMP, 1 NAN */
    double tz_offset_hours;
    double offset[9];     /* imsak,fajr,sunrise,dhuhr,asr,maghrib,sunset,isha,midnight */
} pt_params;

typedef struct {
    double fajr, sunrise, dhuhr, asr, sunset, maghrib, isha, imsak;
    double midnight, firstthird, lastthird;
} pt_times;

void pt_calculate(int y, int m, int d, double lat, double lng, double elevation,
                  const pt_params *p, pt_times *out);

#endif
```

**Verification:** `cd c && cmake -B build && cmake --build build`

**First run `cat c/include/prayer_times.h` to read the file, then make the edit.**
**Run: `clang-format -i c/include/prayer_times.h`**

#### Task 5.1.2 — `prayer_times.c` — part 1 of 2

**File:** `c/src/prayer_times.c` (does not exist)

**Current code:** *(file does not exist)*

**Replacement code:**
```c
#include "prayer_times.h"
#include <math.h>

static double mod(double a, double b) {
    double r = fmod(a, b);
    if (r < 0) r += b;
    return r;
}

static double dtr(double d) { return d * M_PI / 180.0; }
static double rtd(double r) { return r * 180.0 / M_PI; }
static double ssin(double d) { return sin(dtr(d)); }
static double ccos(double d) { return cos(dtr(d)); }
static double ttan(double d) { return tan(dtr(d)); }
static double aasin(double x) { return rtd(asin(x)); }
static double aacos(double x) { return rtd(acos(x)); }
static double aacot(double x) { return rtd(atan(1.0 / x)); }
static double aatan2(double y, double x) { return rtd(atan2(y, x)); }

static double julian_day(int y, int m, int d) {
    if (m <= 2) { y -= 1; m += 12; }
    int A = (int)floor(y / 100.0);
    double B = 2 - A + (int)floor(A / 4.0);
    return floor(365.25 * (y + 4716)) + floor(30.6001 * (m + 1)) + d + B - 1524.5;
}

static void solar_position_at(double jd, double *decl, double *eqt) {
    double D = jd - 2451545.0;
    double g = mod(357.529 + 0.98560028 * D, 360.0);
    double q = mod(280.459 + 0.98564736 * D, 360.0);
    double L = mod(q + 1.915 * ssin(g) + 0.020 * ssin(2 * g), 360.0);
    double e = 23.439 - 0.00000036 * D;
    double RA = mod(aatan2(ccos(e) * ssin(L), ccos(L)) / 15.0, 24.0);
    *decl = aasin(ssin(e) * ssin(L));
    *eqt = q / 15.0 - RA;
}

static double solar_noon(int y, int m, int d, double time, double lng) {
    double jd = julian_day(y, m, d) + time / 24.0 - lng / (15.0 * 24.0);
    double decl, eqt;
    solar_position_at(jd, &decl, &eqt);
    return mod(12.0 - eqt, 24.0);
}

static double horizon_angle(double elevation) {
    return 0.833 + 0.0347 * sqrt(elevation);
}

static double asr_shadow_angle(const pt_params *p, int y, int m, int d, double time, double lat) {
    double jd = julian_day(y, m, d) + 1.0 + time / 24.0;
    double decl, eqt;
    solar_position_at(jd, &decl, &eqt);
    return -aacot(p->asr_factor + ttan(fabs(lat - decl)));
}
```

**Verification:** `cd c && cmake -B build && cmake --build build`

**First run `cat c/src/prayer_times.c` to read the file, then make the edit.**
**Run: `clang-format -i c/src/prayer_times.c`**

#### Task 5.1.3 — `prayer_times.c` — part 2 of 2

**File:** `c/src/prayer_times.c`

**Current code:** *(the file as written in Task 5.1.2, ending with `asr_shadow_angle`)*

**Replacement code (append):**
```c
static double depression_time(double angle, int y, int m, int d, double time,
                              double lat, double lng, int direction, int policy, int *reached_out) {
    double jd = julian_day(y, m, d) + time / 24.0 - lng / (15.0 * 24.0);
    double decl, eqt;
    solar_position_at(jd, &decl, &eqt);
    double noon = solar_noon(y, m, d, time, lng);
    double numerator = -ssin(angle) - ssin(lat) * ssin(decl);
    double denominator = ccos(lat) * ccos(decl);
    double ratio = numerator / denominator;
    int reached = (ratio >= -1.0 && ratio <= 1.0);
    if (policy == 0) {
        if (ratio > 1.0) ratio = 1.0;
        if (ratio < -1.0) ratio = -1.0;
    } else if (!reached) {
        *reached_out = 0;
        return NAN;
    }
    double t = aacos(ratio) / 15.0;
    *reached_out = reached;
    return noon + direction * t;
}

static double night_fraction(int la, double angle, double night) {
    if (la == 1) return night / 2.0;
    if (la == 2) return night / 7.0;
    return (angle / 60.0) * night;
}

void pt_calculate(int y, int m, int d, double lat, double lng, double elevation,
                  const pt_params *p, pt_times *out) {
    double horizon = horizon_angle(elevation);
    int reached = 1;

    double fajr = depression_time(p->fajr_angle, y, m, d, 5.0, lat, lng, -1, p->unreached_policy, &reached);
    int fajr_reached = reached;
    double sunrise = depression_time(horizon, y, m, d, 6.0, lat, lng, -1, p->unreached_policy, &reached);
    double dhuhr = solar_noon(y, m, d, 12.0, lng);
    double asr_angle = asr_shadow_angle(p, y, m, d, 13.0, lat);
    double asr = depression_time(asr_angle, y, m, d, 13.0, lat, lng, 1, p->unreached_policy, &reached);
    double sunset = depression_time(horizon, y, m, d, 18.0, lat, lng, 1, p->unreached_policy, &reached);
    double maghrib = depression_time(p->maghrib, y, m, d, 18.0, lat, lng, 1, p->unreached_policy, &reached);
    int maghrib_reached = reached;
    double isha = depression_time(p->isha, y, m, d, 18.0, lat, lng, 1, p->unreached_policy, &reached);
    int isha_reached = reached;

    if (p->lat_adjust != 0) {
        double night = mod(sunrise - sunset, 24.0);
        double fajr_p = night_fraction(p->lat_adjust, p->fajr_angle, night);
        double isha_p = night_fraction(p->lat_adjust, p->isha, night);
        double mag_p = night_fraction(p->lat_adjust, p->maghrib, night);
        if (!fajr_reached || (fajr - sunrise) * -1 > fajr_p) fajr = sunrise - fajr_p;
        if (!isha_reached || (isha - sunset) > isha_p) isha = sunset + isha_p;
        if (!maghrib_reached || (maghrib - sunset) > mag_p) maghrib = sunset + mag_p;
    }

    double tz = p->tz_offset_hours - lng / 15.0;
    fajr += tz; sunrise += tz; dhuhr += tz; asr += tz; sunset += tz; maghrib += tz; isha += tz;

    if (p->maghrib_is_minutes) maghrib = sunset + p->maghrib / 60.0;
    if (p->isha_is_minutes) isha = maghrib + p->isha / 60.0;
    dhuhr += p->dhuhr_mins / 60.0;
    double imsak = fajr - p->imsak_mins / 60.0;

    double diff = (p->midnight_mode == 1) ? mod(fajr - sunset, 24.0) : mod(sunrise - sunset, 24.0);
    double midnight = sunset + diff / 2.0;
    double firstthird = sunset + diff / 3.0;
    double lastthird = sunset + 2.0 * diff / 3.0;

    out->fajr = fajr + p->offset[1] / 60.0;
    out->sunrise = sunrise + p->offset[2] / 60.0;
    out->dhuhr = dhuhr + p->offset[3] / 60.0;
    out->asr = asr + p->offset[4] / 60.0;
    out->sunset = sunset + p->offset[6] / 60.0;
    out->maghrib = maghrib + p->offset[5] / 60.0;
    out->isha = isha + p->offset[7] / 60.0;
    out->imsak = imsak + p->offset[0] / 60.0;
    out->midnight = midnight + p->offset[8] / 60.0;
    out->firstthird = firstthird;
    out->lastthird = lastthird;
}
```

**Verification:** `cd c && cmake --build build && ctest`

**First run `cat c/src/prayer_times.c` to read the file, then make the edit.**
**Run: `clang-format -i c/src/prayer_times.c`**

### Batch 5.2

#### Task 5.2.1 — dump CLI (for parity)

**File:** `c/tools/dump.c` (does not exist)

**Current code:** *(file does not exist)*

**Replacement code:**
```c
#include "prayer_times.h"
#include <stdio.h>
#include <stdlib.h>

/* usage: dump y m d lat lng elev fajr isha isha_min dhuhr asr */
int main(int argc, char **argv) {
    if (argc < 12) { fprintf(stderr, "usage: dump y m d lat lng elev fajr isha isha_min dhuhr asr\n"); return 1; }
    int y = atoi(argv[1]), m = atoi(argv[2]), d = atoi(argv[3]);
    double lat = atof(argv[4]), lng = atof(argv[5]), elev = atof(argv[6]);
    pt_params p = {0};
    p.fajr_angle = atof(argv[7]);
    p.isha = atof(argv[8]);
    p.isha_is_minutes = atoi(argv[9]);
    p.dhuhr_mins = atof(argv[10]);
    p.asr_factor = atof(argv[11]);
    p.imsak_mins = 10;
    p.lat_adjust = 3; /* ANGLE_BASED */
    pt_times t;
    pt_calculate(y, m, d, lat, lng, elev, &p, &t);
    printf("%.17g %.17g %.17g %.17g %.17g %.17g %.17g %.17g %.17g %.17g %.17g\n",
           t.fajr, t.sunrise, t.dhuhr, t.asr, t.sunset, t.maghrib, t.isha, t.imsak,
           t.midnight, t.firstthird, t.lastthird);
    return 0;
}
```

**Verification:** `cd c && cmake --build build && ./build/prayer_times_dump 2014 4 24 51.508515 -0.1254872 0 15 15 0 0 1`

**First run `cat c/tools/dump.c` to read the file, then make the edit.**
**Run: `clang-format -i c/tools/dump.c`**

#### Task 5.2.2 — C test (TDD)

**File:** `c/test/test_kernel.c` (does not exist)

**Current code:** *(file does not exist)*

**Replacement code:**
```c
#include "prayer_times.h"
#include <math.h>
#include <stdio.h>
#include <string.h>

static void format(double t, char *buf) {
    double x = mod_impl(t);
    x += 0.5 / 60.0;
    while (x >= 24) x -= 24;
    int h = (int)floor(x);
    int mm = (int)floor((x - h) * 60.0);
    sprintf(buf, "%02d:%02d", h, mm);
}

static double mod_impl(double a) {
    double r = fmod(a, 24.0);
    if (r < 0) r += 24.0;
    return r;
}

int main(void) {
    pt_params p = {0};
    p.fajr_angle = 15; p.isha = 15; p.imsak_mins = 10; p.asr_factor = 1;
    p.lat_adjust = 3; /* ANGLE_BASED */
    p.tz_offset_hours = 1.0;

    pt_times t;
    char buf[8];

    pt_calculate(2014, 4, 24, 51.508515, -0.1254872, 0, &p, &t);
    format(t.fajr, buf);     if (strcmp(buf, "03:57")) return 1;
    format(t.asr, buf);      if (strcmp(buf, "16:54")) return 2;
    format(t.isha, buf);     if (strcmp(buf, "22:02")) return 3;
    format(t.midnight, buf); if (strcmp(buf, "00:59")) return 4;

    pt_calculate(2024, 1, 22, 64.0, 20.0, 0, &p, &t);
    format(t.asr, buf);      if (strcmp(buf, "11:35")) return 5;

    printf("ok\n");
    return 0;
}
```

**Verification (TDD):** `cd c && cmake --build build && ctest` → **must PASS**.

**First run `cat c/test/test_kernel.c` to read the file, then make the edit.**
**Run: `clang-format -i c/test/test_kernel.c`**

#### Task 5.2.3 — docs (user + developer)

**File:** `docs/user-guide.md`

**Current code:**
```
<!-- NEXT -->
```

**Replacement code:**
```markdown
## C

The C target is a static library exposing the pure kernel (for FFI/binding):

```c
#include "prayer_times.h"

pt_params p = {0};
p.fajr_angle = 15; p.isha = 15; p.imsak_mins = 10; p.asr_factor = 1;
p.lat_adjust = 3; /* ANGLE_BASED */

pt_times t;
pt_calculate(2014, 4, 24, 51.508515, -0.1254872, 0, &p, &t);
/* t.fajr ≈ 3.958 hours = 03:57 */
```

Method resolution (names → angles/minutes) lives in the higher-level languages; C is the low-level kernel.

<!-- NEXT -->
```

**Verification:** `tail -1 docs/user-guide.md` prints `<!-- NEXT -->`

**First run `cat docs/user-guide.md` to read the file, then make the edit.**
**Run: *(markdown — the `tail -1` check is authoritative)***

**File:** `docs/developer-guide.md`

**Current code:**
```
<!-- NEXT -->
```

**Replacement code:**
```markdown
## C build

```sh
cd c && cmake -B build && cmake --build build && ctest
```

- `include/prayer_times.h` — `pt_params` / `pt_times` structs + `pt_calculate`.
- `src/prayer_times.c` — the kernel.
- `tools/dump.c` — parity dump CLI.

<!-- NEXT -->
```

**Verification:** `tail -1 docs/developer-guide.md` prints `<!-- NEXT -->`

**First run `cat docs/developer-guide.md` to read the file, then make the edit.**
**Run: *(markdown — the `tail -1` check is authoritative)***

---

## Phase 6 — Cross-language float parity + CI

**Goal:** prove the four kernels agree to ≤1e-9 h, wire CI, and finalise the docs.

**Reviewer exit criteria:**
- [ ] `python3 tests/parity.py` runs all four dumps and asserts ≤1e-9 h agreement.
- [ ] `mise run ci` is green.
- [ ] `docs/user-guide.md` has a final install/usage summary; `docs/developer-guide.md` documents parity + CI.

### Batch 6.1

#### Task 6.1.1 — Python dump CLI

**File:** `python/tools/dump.py` (does not exist)

**Current code:** *(file does not exist)*

**Replacement code:**
```python
#!/usr/bin/env python3
"""Print raw float hours for parity comparison. usage: dump.py y m d lat lng elev fajr isha isha_min dhuhr asr"""
import sys

from prayer_times.astronomy import calculate
from prayer_times.params import Params, LatAdjust, Midnight, Unreached, Offsets

args = [float(x) for x in sys.argv[1:]]
y, m, d = int(args[0]), int(args[1]), int(args[2])
lat, lng, elev = args[3], args[4], args[5]
p = Params(
    fajr_angle=args[6], isha=args[7], isha_is_minutes=bool(args[8]),
    maghrib=0.0, maghrib_is_minutes=False, imsak_mins=10.0, dhuhr_mins=args[9],
    asr_factor=args[10], lat_adjust=LatAdjust.ANGLE_BASED,
    midnight_mode=Midnight.STANDARD, unreached_policy=Unreached.CLAMP,
    offsets=Offsets(), timezone_offset_hours=0.0,
)
t = calculate(y, m, d, lat, lng, elev, p)
print(" ".join(f"{t[k]:.17g}" for k in
      ["Fajr", "Sunrise", "Dhuhr", "Asr", "Sunset", "Maghrib", "Isha", "Imsak",
       "Midnight", "Firstthird", "Lastthird"]))
```

**Verification:** `cd python && uv run python tools/dump.py 2014 4 24 51.508515 -0.1254872 0 15 15 0 0 1`

**First run `cat python/tools/dump.py` to read the file, then make the edit.**
**Run: `ruff format python/tools/dump.py`**

#### Task 6.1.2 — Go dump CLI

**File:** `go/tools/dump/main.go` (does not exist)

**Current code:** *(file does not exist)*

**Replacement code:**
```go
package main

import (
	"fmt"
	"os"
	"strconv"

	prayertimes "github.com/salahlib/prayertimes/pkg/prayertimes"
)

func main() {
	a := os.Args[1:]
	f := func(i int) float64 { v, _ := strconv.ParseFloat(a[i], 64); return v }
	ii := func(i int) int { v, _ := strconv.Atoi(a[i]); return v }
	p := prayertimes.Params{
		FajrAngle: f(6), Isha: f(7), IshaIsMinutes: ii(8) != 0,
		ImsakMins: 10, DhuhrMins: f(9), AsrFactor: f(10),
		LatAdjust: prayertimes.LatAngleBased, MidnightMode: prayertimes.MidStandard,
		UnreachedPolicy: prayertimes.UnreachedClamp,
	}
	t := prayertimes.Calculate(ii(0), ii(1), ii(2), f(3), f(4), f(5), p)
	fmt.Printf("%.17g %.17g %.17g %.17g %.17g %.17g %.17g %.17g %.17g %.17g %.17g\n",
		t.Fajr, t.Sunrise, t.Dhuhr, t.Asr, t.Sunset, t.Maghrib, t.Isha, t.Imsak,
		t.Midnight, t.Firstthird, t.Lastthird)
}
```

**Verification:** `cd go && go run ./tools/dump 2014 4 24 51.508515 -0.1254872 0 15 15 0 0 1`

**First run `cat go/tools/dump/main.go` to read the file, then make the edit.**
**Run: `gofmt -w go/tools/dump/main.go`**

#### Task 6.1.3 — TS dump CLI

**File:** `typescript/src/dump.ts` (does not exist)

**Current code:** *(file does not exist)*

**Replacement code:**
```typescript
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
```

**Verification:** `cd typescript && bun src/dump.ts 2014 4 24 51.508515 -0.1254872 0 15 15 0 0 1`

**First run `cat typescript/src/dump.ts` to read the file, then make the edit.**
**Run: `bunx prettier --write typescript/src/dump.ts`**

### Batch 6.2

#### Task 6.2.1 — parity runner

**File:** `tests/parity.py` (does not exist)

**Current code:** *(file does not exist)*

**Replacement code:**
```python
#!/usr/bin/env python3
"""Run all four dump CLIs on shared inputs and assert float agreement (<=1e-9 h)."""
import subprocess

ROOT = "/home/yasser/git/yasn77/salahlib"

CASES = [
    ["2014", "4", "24", "51.508515", "-0.1254872", "0", "15", "15", "0", "0", "1"],
    ["2024", "1", "22", "64.0", "20.0", "0", "15", "15", "0", "0", "1"],
    ["2024", "6", "20", "65.0", "0.0", "0", "18", "17", "0", "0", "1"],
    ["2024", "3", "20", "21.3890824", "39.8579118", "0", "18.5", "90", "1", "0", "1"],
]


def run(cmd):
    out = subprocess.run(cmd, capture_output=True, text=True, cwd=ROOT)
    if out.returncode != 0:
        raise SystemExit(f"{' '.join(cmd)} failed: {out.stderr}")
    return [float(x) for x in out.stdout.split()]


def main():
    commands = {
        "python": ["python3", "python/tools/dump.py"],
        "go": ["go", "run", "./tools/dump"],
        "ts": ["bun", "src/dump.ts"],
        "c": ["c/build/prayer_times_dump"],
    }
    for case in CASES:
        results = {lang: run(cmd + case) for lang, cmd in commands.items()}
        ref = results["python"]
        for lang, vals in results.items():
            if len(vals) != len(ref):
                raise SystemExit(f"{lang} returned {len(vals)} values, expected {len(ref)}")
            for i, (a, b) in enumerate(zip(ref, vals)):
                if abs(a - b) > 1e-9:
                    raise SystemExit(f"MISMATCH case={case} lang={lang} idx={i}: {a} vs {b}")
        print("ok", case)
    print("parity: PASS")


if __name__ == "__main__":
    main()
```

**Verification:** `python3 tests/parity.py` → **must print `parity: PASS`**.

**First run `cat tests/parity.py` to read the file, then make the edit.**
**Run: `ruff format tests/parity.py`**

#### Task 6.2.2 — docs (user + developer): finalise

**File:** `docs/user-guide.md`

**Current code:**
```
<!-- NEXT -->
```

**Replacement code:**
```markdown
## Summary

- Python: `pip install prayer-times` → `from prayer_times import PrayerTimes`.
- Go: `go get github.com/salahlib/prayertimes` → `prayertimes.New("ISNA", "STANDARD")`.
- TypeScript: `npm install prayer-times` → `new PrayerTimes("ISNA")`.
- C: link the `libprayer_times` static library and call `pt_calculate`.

All four produce byte-identical `HH:MM` strings for the same inputs, and are validated against the AlAdhan
API. See `shared/methods.json` for the supported calculation methods.

<!-- NEXT -->
```

**Verification:** `tail -1 docs/user-guide.md` prints `<!-- NEXT -->`

**First run `cat docs/user-guide.md` to read the file, then make the edit.**
**Run: *(markdown — the `tail -1` check is authoritative)***

**File:** `docs/developer-guide.md`

**Current code:**
```
<!-- NEXT -->
```

**Replacement code:**
```markdown
## Cross-language float parity

`tests/parity.py` runs each language's dump CLI on shared inputs and asserts ≤1e-9 h agreement (≈3.6 µs).

```sh
mise run parity
```

## CI

`mise run ci` = `test` (all four languages) + `parity` + `lint`. Golden vectors are committed; regeneration
is manual (`mise run gen-fixtures`) and must never run in CI.

## Releasing

Tag each language `python/vX.Y.Z`, `go/vX.Y.Z`, `typescript/vX.Y.Z`, `c/vX.Y.Z`; keep semver in sync.

<!-- NEXT -->
```

**Verification:** `tail -1 docs/developer-guide.md` prints `<!-- NEXT -->`

**First run `cat docs/developer-guide.md` to read the file, then make the edit.**
**Run: *(markdown — the `tail -1` check is authoritative)***

#### Task 6.2.3 — README (link the guides)

**File:** `README.md`

**Current code:**
```markdown
# SalahLib

Multi-language Islamic prayer-times library (AlAdhan-compatible). Targets Python, Go, TypeScript and C.

- [User Guide](docs/user-guide.md)
- [Developer Guide](docs/developer-guide.md)
- `shared/SPEC.md` — the calculation spec.
- `shared/methods.json` — the method registry.

## Quick start

```sh
mise install && mise run test
```
```

**Replacement code:**
```markdown
# SalahLib

Multi-language Islamic prayer-times library (AlAdhan-compatible). Targets Python, Go, TypeScript and C.

- [User Guide](docs/user-guide.md) — installation and usage.
- [Developer Guide](docs/developer-guide.md) — architecture, build/test, parity, release.
- `shared/SPEC.md` — the calculation spec.
- `shared/methods.json` — the method registry.
- `EXECUTION_PLAN.md` — the executor+reviewer implementation plan.

## Quick start

```sh
mise install && mise run test
```

## License

Apache-2.0. See NOTICE, PROVENANCE.md and THIRD-PARTY-NOTICES.md.
```

**Verification:** `grep -q "Apache-2.0" README.md`

**First run `cat README.md` to read the file, then make the edit.**
**Run: *(markdown — the `grep` check is authoritative)***

---

## End-to-end acceptance (reviewer, after all phases)

- [ ] Python: `uv run pytest` green (kernel + golden vectors).
- [ ] Go: `go test ./...` green; `gofmt -l .` empty.
- [ ] TypeScript: `bun test` green; `bunx tsc --noEmit` clean.
- [ ] C: `cmake --build build && ctest` green.
- [ ] `python3 tests/parity.py` → `parity: PASS` (all four kernels agree to ≤1e-9 h).
- [ ] `python3 scripts/generate_fixtures.py` produced committed `shared/vectors/aladhan/*.json` (manual).
- [ ] `docs/user-guide.md` and `docs/developer-guide.md` each end with `<!-- NEXT -->` and contain one section
      per language plus the accuracy/parity/release notes.
