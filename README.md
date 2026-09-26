# SalahLib

Multi-language Islamic prayer-times library, validated for **output parity with the
[AlAdhan API](https://aladhan.com/prayer-times-api)**. Targets **Python, Go, TypeScript and C**.

- [User Guide](docs/user-guide.md) — install and use each language.
- [Developer Guide](docs/developer-guide.md) — architecture, build/test, invariants.
- `shared/SPEC.md` — the calculation spec.
- `shared/methods.json` — the method registry (single source of truth).

## Languages

| Language | Package | Import |
|---|---|---|
| Python | `prayer-times` (PyPI) | `from prayer_times import PrayerTimes` |
| Go | `github.com/yasn77/salahlib/langs/go` | `prayertimes.New("ISNA", "STANDARD")` |
| TypeScript | `prayer-times` (npm) | `new PrayerTimes("ISNA")` |
| C | `libprayer_times` (static) | `pt_resolve_method` / `pt_calculate` |

## Repository layout

```
shared/   methods.json + schema + SPEC + golden vectors (single source of truth)
langs/    python/ · go/ · typescript/ · c/   (the four implementations)
scripts/  fixture generator, data sync, C-header generator
tests/    cross-language float-parity harness
```

## Quick start

```sh
mise install && mise run test
```

## License

Apache-2.0. See NOTICE and THIRD-PARTY-NOTICES.md.
