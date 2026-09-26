#!/usr/bin/env python3
"""Set (or check) the declared version of one language implementation.

usage: python3 scripts/set_version.py <python|go|typescript|c> <X.Y.Z> [--check]

Go has no version file — its version lives in the `go/vX.Y.Z` tag alone.
For python/typescript/c the tooling (and CI's tag guard) verifies the tag
version matches these declarations. With --check nothing is written; the
script exits 1 on any mismatch (or missing declaration).
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SEMVER = re.compile(r"^\d+\.\d+\.\d+([.\-+].*)?$")
VERSION_FILES = {
    "python": [ROOT / "langs/python/pyproject.toml", ROOT / "langs/python/salahlib/__init__.py"],
    "typescript": [ROOT / "langs/typescript/package.json"],
    "c": [ROOT / "langs/c/CMakeLists.txt"],
    "go": [],
}


def declared(path):
    text = path.read_text()
    if path.name == "package.json":
        return json.loads(text)["version"]
    if path.name == "__init__.py":
        return re.search(r'__version__ = "([^"]*)"', text).group(1)
    if path.name == "CMakeLists.txt":
        return re.search(r"project\(salahlib_c VERSION (\S+)", text).group(1)
    if path.name == "pyproject.toml":
        return re.search(r'name = "salahlib"\nversion = "([^"]*)"', text).group(1)
    raise SystemExit(f"no version rule for {path}")


def substitute(path, version):
    text = path.read_text()
    if path.name == "package.json":
        pkg = json.loads(text)
        pkg["version"] = version
        out = json.dumps(pkg, indent=2) + "\n"
    elif path.name == "__init__.py":
        out = re.sub(r'__version__ = "[^"]*"', f'__version__ = "{version}"', text)
    elif path.name == "CMakeLists.txt":
        out = re.sub(r"(project\(salahlib_c VERSION )\S+", rf"\g<1>{version}", text)
    elif path.name == "pyproject.toml":
        out = re.sub(r'(name = "salahlib"\nversion = ")[^"]+"', rf'\g<1>{version}"', text)
    else:
        raise SystemExit(f"no version rule for {path}")
    if out == text:
        print(f"  unchanged  {path.relative_to(ROOT)}")
    else:
        path.write_text(out)
        print(f"  updated    {path.relative_to(ROOT)}")


def main():
    argv = [a for a in sys.argv[1:] if a != "--check"]
    check = "--check" in sys.argv
    if len(argv) != 2:
        raise SystemExit(__doc__)
    lang, version = argv[0], argv[1]
    if lang not in VERSION_FILES:
        raise SystemExit(f"unknown language: {lang} (want python|go|typescript|c)")
    if not SEMVER.match(version):
        raise SystemExit(f"not a semver version: {version}")
    files = VERSION_FILES[lang]
    if not files:
        print(f"{lang}: version lives in the git tag (go/v{version}); nothing to update")
        return
    if check:
        bad = [f for f in files if declared(f) != version]
        for f in files:
            print(f"  {f.relative_to(ROOT)}: {declared(f)}")
        if bad:
            raise SystemExit(f"MISMATCH: {lang} declarations must all be {version}")
        print(f"check: {lang} == {version}  OK")
        return
    print(f"{lang} -> {version}")
    for f in files:
        substitute(f, version)


if __name__ == "__main__":
    main()
