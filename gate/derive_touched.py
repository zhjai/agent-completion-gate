#!/usr/bin/env python3
"""derive_touched.py — compute which surfaces a change set TOUCHED, from the PROTECTED
inventory's per-surface `paths` globs + a list of changed files. This is TRUSTED input for
check_acceptance.py's --touched, so the "unknowns fail closed" rule need not trust the
worker's self-reported touched_surfaces.

Changed files come from:
  --changed-files-from FILE   NUL- or newline-separated paths ('-' or omitted = stdin)
  --git-diff BASE             run `git diff --no-renames --name-only -z BASE...HEAD`

Output: matched surface ids, one per line, to stdout.

Notes / honest limits:
  - Globs use fnmatch semantics: `*` matches across `/` too (so `artifacts/*` matches
    `artifacts/runs/x.json`). Conservative — it tends to OVER-detect a touch, which fails
    toward blocking, not toward granting.
  - `--no-renames` makes a rename show as delete(OLD)+add(NEW) so renaming a file out of a
    surface's path still flags that surface; `-z` keeps paths raw (newlines/special chars),
    which git would otherwise quote and break matching. Both were real bypasses, now closed.
  - A changed file matching NO surface path maps to NO surface. So this is only as complete
    as your `paths` globs: keep them complete for every user-visible surface, or fall back to
    check_acceptance.py --strict-surfaces (which requires ALL user-visible surfaces covered
    regardless of what was touched).
  - Run it hermetically (`python3 -E`) from a trusted context, same as the gate.
"""
from __future__ import annotations
import argparse, fnmatch, subprocess, sys
from pathlib import Path

try:
    import yaml
except ImportError:
    print("ERROR: pyyaml required", file=sys.stderr); sys.exit(2)


def changed_files(a) -> list[str]:
    if a.git_diff:
        try:
            out = subprocess.run(
                # --no-renames: a rename shows as delete(old) + add(new), so the OLD path is
                #   NOT elided (rename detection would hide it, hiding a touched surface).
                # -z: NUL-separated, RAW unquoted paths — paths with newlines / special chars
                #   stay intact (git's default quoting would break glob matching + line parsing).
                ["git", "diff", "--no-renames", "--name-only", "-z", f"{a.git_diff}...HEAD"],
                capture_output=True, encoding="utf-8", errors="surrogateescape", check=True,
            ).stdout  # surrogateescape: a non-UTF-8 byte in a path round-trips instead of crashing
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            print(f"ERROR: git diff failed: {e} (fail closed)", file=sys.stderr); sys.exit(2)
        return [p for p in out.split("\0") if p]   # do NOT strip: paths are raw
    # file / stdin input (convenience for tests): accept NUL- or newline-separated.
    # Read as bytes + surrogateescape so non-UTF-8 paths round-trip instead of crashing (matches
    # the --git-diff path).
    if a.changed_files_from and a.changed_files_from != "-":
        data = Path(a.changed_files_from).read_bytes().decode("utf-8", "surrogateescape")
    else:
        data = sys.stdin.buffer.read().decode("utf-8", "surrogateescape")
    parts = data.split("\0") if "\0" in data else data.splitlines()
    return [p.strip() for p in parts if p.strip()]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--inventory", required=True, help="protected surface_inventory.yaml (with per-surface paths globs)")
    ap.add_argument("--changed-files-from", metavar="FILE", help="NUL- or newline-separated changed paths ('-' or omit = stdin)")
    ap.add_argument("--git-diff", metavar="BASE", help="run `git diff --no-renames --name-only -z BASE...HEAD` to get changed paths")
    a = ap.parse_args()

    inv = yaml.safe_load(Path(a.inventory).read_text()) or {}
    files = changed_files(a)

    for s in inv.get("surfaces", []):
        globs = s.get("paths") or []
        if any(fnmatch.fnmatchcase(f, g) for f in files for g in globs):
            print(s["id"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
