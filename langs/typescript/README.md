# salahlib

AlAdhan-compatible Islamic prayer times — the TypeScript implementation of
[SalahLib](https://github.com/yasn77/salahlib).

```sh
npm install salahlib   # or: bun add salahlib
```

```ts
import { PrayerTimes } from "salahlib";

const pt = new PrayerTimes("ISNA");
const times = pt.getTimes(new Date(Date.UTC(2024, 3, 24)), 51.508515, -0.1254872, "Europe/London");
console.log(times.Fajr); // "03:57"
```

Full documentation: [User Guide](https://github.com/yasn77/salahlib/blob/main/docs/user-guide.md) ·
calculation spec: [SPEC.md](https://github.com/yasn77/salahlib/blob/main/shared/SPEC.md).

Apache-2.0. This package is built from the same pure kernel that is validated to
float-parity (≤1e-9 h) with the Python, Go and C implementations.
