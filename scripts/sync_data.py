#!/usr/bin/env python3
"""Copy shared/methods.json into each language tree (committed copies).

Also flattens the `extends` composition: a method with `"extends": "MOONSIGHTING"`
inherits the base method's `params` (its own `params`, if any, override the base per-key).
The resolvers in each language read only the flattened form.
"""
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "shared" / "methods.json"
TARGETS = [
    ROOT / "python" / "prayer_times" / "data" / "methods.json",
    ROOT / "go" / "pkg" / "prayertimes" / "methods.json",
    ROOT / "typescript" / "src" / "methods.json",
]


def flatten(methods):
    """Expand `extends` into fully-resolved `params` (base first, child overrides)."""

    def base_params(key, stack):
        entry = methods[key]
        base = entry.get("extends")
        params = {}
        if base:
            if base not in methods:
                raise ValueError(f"unknown 'extends': {base} (in {key})")
            if base in stack:
                raise ValueError("'extends' cycle: " + " -> ".join(stack + [base]))
            params = base_params(base, stack + [key])
        params.update(entry.get("params", {}))
        return params

    out = {}
    for key, entry in methods.items():
        e = dict(entry)
        if "extends" in e:
            e.pop("extends")
            e["params"] = base_params(key, [key])
        out[key] = e
    return out


def main():
    methods = flatten(json.loads(SRC.read_text()))
    for t in TARGETS:
        t.parent.mkdir(parents=True, exist_ok=True)
        t.write_text(json.dumps(methods, indent=2, ensure_ascii=False) + "\n")
        print(f"synced -> {t.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
