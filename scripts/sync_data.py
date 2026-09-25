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
