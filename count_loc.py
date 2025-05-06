#!/usr/bin/env python3
"""
count_loc.py  –  Count modified LOCs between two Git branches.
              The script now specifically targets files within 'app/src/main/java'.

Usage examples
--------------
# Compare 'main' and your feature branch, using defaults (path fixed to 'app/src/main/java'):
python count_loc.py main my-feature

# Ignore whitespace-only edits (path fixed to 'app/src/main/java'):
python count_loc.py main my-feature -i

# Only look at Kotlin and Java files (path fixed to 'app/src/main/java'):
python count_loc.py main my-feature -e .kt .java
"""
import argparse
import subprocess
import sys
from pathlib import Path
from typing import List, Tuple


def run_git_numstat(
    base: str,
    compare: str,
    paths: List[str] | None,
    ignore_ws: bool,
) -> List[str]:
    """Return the lines of `git diff --numstat` between two branches."""
    cmd = ["git", "diff", base, compare, "--numstat"]
    if ignore_ws:
        cmd.insert(3, "-w")          # git diff -w …
    if paths:
        cmd.extend(paths)

    try:
        completed = subprocess.run(
            cmd, capture_output=True, text=True, check=True
        )
    except subprocess.CalledProcessError as err:
        print("Git command failed:\n", err.stderr or err.stdout, file=sys.stderr)
        sys.exit(err.returncode)

    return completed.stdout.splitlines()


def tally(lines: List[str], exts: List[str]) -> Tuple[int, int]:
    added = deleted = 0
    for line in lines:
        parts = line.split("\t")
        if len(parts) < 3:
            continue  # skip unexpected lines
        add, delete, filename = parts
        if add == "-" or delete == "-":        # binary file
            continue
        if exts and not any(filename.endswith(ext) for ext in exts):
            continue
        added += int(add)
        deleted += int(delete)
    return added, deleted


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Count modified lines (added + deleted) between two Git branches, within 'app/src/main/java'."
    )
    parser.add_argument("base", help="Base branch (e.g. main, develop)")
    parser.add_argument("compare", help="Branch to compare against base")
    parser.add_argument(
        "-e",
        "--ext",
        nargs="*",
        #default=[".java", ".kt", ".xml", ".gradle", ".groovy"],
        default=[".kt"],
        help="File extensions to include (default: Android-typical)",
    )
    parser.add_argument(
        "-i",
        "--ignore-whitespace",
        action="store_true",
        help="Ignore whitespace-only changes (-w flag to git diff)",
    )
    # The -p/--path argument is removed as the path is now fixed.

    args = parser.parse_args()

    fixed_path = "app/src/main/java"
    lines = run_git_numstat(
        args.base,
        args.compare,
        paths=[fixed_path],
        ignore_ws=args.ignore_whitespace,
    )
    added, deleted = tally(lines, args.ext)
    print(f"\n{args.base}  →  {args.compare} (in {fixed_path})")
    print("-" * (40 + len(fixed_path) + 6))  # Adjust line length
    print(f"Added lines   : {added:,}")
    print(f"Deleted lines : {deleted:,}")
    print(f"Total modified: {added + deleted:,}")


if __name__ == "__main__":
    main()
