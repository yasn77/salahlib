#!/usr/bin/env python3
"""Run all four dump CLIs on shared inputs and assert float agreement (<=1e-9 h)."""
import os
import subprocess
from pathlib import Path

ROOT = str(Path(__file__).resolve().parent.parent)
CASES = [
    ["2014", "4", "24", "51.508515", "-0.1254872", "0", "15", "15", "0", "0", "1"],
    ["2024", "1", "22", "64.0", "20.0", "0", "15", "15", "0", "0", "1"],
    ["2024", "6", "20", "65.0", "0.0", "0", "18", "17", "0", "0", "1"],
    ["2024", "3", "20", "21.3890824", "39.8579118", "0", "18.5", "90", "1", "0", "1"],
]


def run(cmd, cwd):
    env = dict(os.environ)
    env.pop("GOROOT", None)
    out = subprocess.run(cmd, capture_output=True, text=True, cwd=cwd, env=env)
    if out.returncode != 0:
        raise SystemExit(f"{' '.join(cmd)} failed: {out.stderr}")
    return [float(x) for x in out.stdout.split()]


def main():
    commands = {
        "python": (["uv", "run", "python", "tools/dump.py"], ROOT + "/langs/python"),
        "go": (["go", "run", "./tools/dump"], ROOT + "/langs/go"),
        "ts": (["bun", "src/dump.ts"], ROOT + "/langs/typescript"),
        "c": (["langs/c/build/prayer_times_dump"], ROOT),
    }
    for case in CASES:
        results = {lang: run(cmd + case, cwd) for lang, (cmd, cwd) in commands.items()}
        ref = results["python"]
        for lang, vals in results.items():
            assert len(vals) == len(ref), f"{lang} returned {len(vals)}, want {len(ref)}"
            for i, (a, b) in enumerate(zip(ref, vals)):
                assert abs(a - b) <= 1e-9, f"MISMATCH case={case} lang={lang} idx={i}: {a} vs {b}"
        print("ok", case)
    print("parity: PASS")


if __name__ == "__main__":
    main()
