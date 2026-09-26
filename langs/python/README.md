# salahlib (Python)

AlAdhan-compatible Islamic prayer times — the Python implementation of
[SalahLib](https://github.com/yasn77/salahlib).

```python
from datetime import date
from salahlib import PrayerTimes

pt = PrayerTimes("ISNA")
times = pt.get_times(date(2024, 4, 24), 51.508515, -0.1254872, tz="Europe/London")
print(times["Fajr"])  # "03:57"
```

Full documentation: [User Guide](https://github.com/yasn77/salahlib/blob/main/docs/user-guide.md) ·
calculation spec: [SPEC.md](https://github.com/yasn77/salahlib/blob/main/shared/SPEC.md).

Apache-2.0. This package is generated from the same pure kernel that is validated to
float-parity (≤1e-9 h) with the Go, TypeScript and C implementations.
