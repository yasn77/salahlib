#!/usr/bin/env python3
"""Fail if the fanned-out method data is stale vs shared/methods.json.

Snapshots the generated files, re-runs the generators, and compares contents —
unlike `git diff`, this is unaffected by unrelated uncommitted work.
"""
import hashlib
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GENERATED = [
    ROOT / "langs/python/salahlib/data/methods.json",
    ROOT / "langs/go/pkg/prayertimes/methods.json",
    ROOT / "langs/typescript/src/methods.generated.ts",
    ROOT / "langs/c/include/methods_generated.h",
]


def digests():
    return {p: hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else None for p in GENERATED}


def main():
    before = digests()
    for script in ("sync_data.py", "generate_c_methods.py"):
        subprocess.run([sys.executable, str(ROOT / "scripts" / script)], check=True, stdout=subprocess.DEVNULL)
    after = digests()
    stale = [p.relative_to(ROOT) for p in GENERATED if before[p] != after[p]]
    if stale:
        for p in stale:
            print(f"stale: {p}")
        raise SystemExit("fanned-out data is stale vs shared/methods.json — run `mise run sync-data` and commit")
    print("check-sync: in sync")


if __name__ == "__main__":
    main()
