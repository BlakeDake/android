#!/usr/bin/env python3
"""
sync_ui_tests_v2.py
~~~~~~~~~~~~~~~~
Copy each UI-test source file from an older Git ref onto a newer one **and
remove any @Test functions that aren’t listed in *ui_test_fqns.txt*.**

Typical usage
-------------
> python sync_ui_tests_v2.py ^
      --repo "C:\\Projects\\MyAndroidApp" ^
      --old MYv2025.1.2 ^
      --new MYv2025.2.0 ^
      --fqns app/ui_test_fqns.txt

After it finishes you’ll be on *MYv2025.2.0* with all changed files **staged**.
Verify with `git diff --staged` and commit when ready.

Assumptions & customisation
---------------------------
* Tests live under **app/src/test/java/** by default.  Override with
  `--test-root`.
* Source files are Kotlin “*.kt*” or Java “*.java*”.
* `@Test` precedes every test function.  Add/alter regexes below if you use
  `@ParameterizedTest`, Spock, etc.
"""
from __future__ import annotations

import argparse
import collections
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Dict, Iterable, List, Set

# --------------------------------------------------------------------------- #
# Git helpers
# --------------------------------------------------------------------------- #


def run_git(repo: Path, *args: str, check: bool = True, decode: bool = True) -> str | bytes:
    """Run *git* with given *args* inside *repo*."""
    result = subprocess.run(
        ["git", *args],
        cwd=repo,
        capture_output=True,
        check=False,
    )
    if check and result.returncode:
        sys.stderr.buffer.write(result.stderr)
        raise RuntimeError(f"git {' '.join(args)} failed (exit {result.returncode})")

    return result.stdout.decode("utf-8", "replace") if decode else result.stdout


def file_exists_in_commit(repo: Path, commit: str, rel_path: str) -> bool:
    try:
        run_git(repo, "cat-file", "-e", f"{commit}:{rel_path}", check=True)
        return True
    except RuntimeError:
        return False


def read_file_from_commit(repo: Path, commit: str, rel_path: str) -> str:
    return run_git(repo, "show", f"{commit}:{rel_path}")  # type: ignore[return-value]


def stage_file(repo: Path, rel_path: str) -> None:
    run_git(repo, "add", rel_path)


def checkout(repo: Path, ref: str) -> None:
    run_git(repo, "checkout", ref)


# --------------------------------------------------------------------------- #
# Core logic
# --------------------------------------------------------------------------- #

def parse_fqns(raw: str) -> Dict[str, Set[str]]:
    """
    Return { fully-qualified-class-name : { wanted-method-name, … } }.

    Lines beginning “#” or blank lines are ignored.
    """
    wanted: Dict[str, Set[str]] = collections.defaultdict(set)
    for raw_line in raw.splitlines():
        if not raw_line.strip() or raw_line.lstrip().startswith("#"):
            continue
        cls, meth = raw_line.rsplit(".", 1)
        wanted[cls].add(meth.strip())
    return wanted


def fqcn_to_candidate_paths(fqcn: str, test_root: str) -> List[str]:
    """Map a fully-qualified class name to possible *.kt* / *.java* paths."""
    pkg, cls = fqcn.rsplit(".", 1)
    rel_dir = pkg.replace(".", "/")
    base = f"{rel_dir}/{cls}"
    return [
        f"{test_root}/{base}.kt",
        f"{test_root}/{base}.java",
    ]


# ---------- regexes that recognise @Test-annotated functions ---------------- #

_KT_RE = re.compile(
    r"""
    (                               # 1: annotations block (one-plus lines)
        (?:^[ \t]*@\w+[^\n]*\n)+
    )
    [ \t]*fun[ \t]+                 #   'fun '
    (`[^`]+`|\w+)[ \t]*\([^)]*\)[ \t]*\{   # 2: method name
    """,
    re.MULTILINE | re.VERBOSE,
)

_JAVA_RE = re.compile(
    r"""
    (                               # 1: annotations block
        (?:^[ \t]*@\w+[^\n]*\n)+
    )
    [ \t]*(?:public[ \t]+)?void[ \t]+
    (\w+)[ \t]*\([^)]*\)[ \t]*\{    # 2: method name
    """,
    re.MULTILINE | re.VERBOSE,
)


def strip_unwanted_tests(src: str, keep: set[str], ext: str) -> str:
    pat = _KT_RE if ext == ".kt" else _JAVA_RE
    out, last = [], 0

    for m in pat.finditer(src):
        annotations_block, raw_name = m.group(1), m.group(2)
        
        # ──────────────────────────────────────────────────────────────
        # NEW: skip anything whose annotations DON’T contain @Test (or
        #      @ParameterizedTest).  @Before / @BeforeEach / helpers stay.
        # ──────────────────────────────────────────────────────────────
        if ("@Test" not in annotations_block
                and "@ParameterizedTest" not in annotations_block):
            continue            # not a test → leave it untouched
        # ──────────────────────────────────────────────────────────────

        name = raw_name.strip("`").strip()          # Kotlin back-tick names → plain
        if name in keep:
            continue                        # wanted test – keep it

        # …brace-counting deletion exactly as before…
        depth, i = 1, src.find("{", m.end() - 1) + 1
        while depth and i < len(src):
            if src[i] == "{":   depth += 1
            elif src[i] == "}": depth -= 1
            i += 1
        out.append(src[last:m.start()])
        last = i

    out.append(src[last:])
    return "".join(out)



# --------------------------------------------------------------------------- #

def sync_tests(
    repo: Path,
    old_ref: str,
    new_ref: str,
    fqns_file: str,
    test_root: str,
) -> None:
    # 1. Parse the wanted list from the *old* branch (no checkout required)
    print(f"Reading list of tests from {old_ref}:{fqns_file} …")
    raw_fqns = read_file_from_commit(repo, old_ref, fqns_file)
    wanted_by_class = parse_fqns(raw_fqns)  # {class → {method,…}}
    print(f"→ {sum(len(v) for v in wanted_by_class.values())} FQNs "
          f"in {len(wanted_by_class)} classes")

    # 2. Build { file-path → wanted-method-set }
    per_file: Dict[str, Set[str]] = collections.defaultdict(set)
    for fqcn, methods in wanted_by_class.items():
        for rel_path in fqcn_to_candidate_paths(fqcn, test_root):
            if file_exists_in_commit(repo, old_ref, rel_path):
                per_file[rel_path].update(methods)
                break
        else:
            print(f"  ⚠  NOT FOUND in {old_ref}: {fqcn}")

    if not per_file:
        print("No matching test files to copy – nothing to do.")
        return

    # 3. Switch to the *new* branch
    print(f"\nChecking out {new_ref} …")
    checkout(repo, new_ref)

    # 4. Overwrite, strip unwanted tests, stage
    for rel_path, wanted_methods in sorted(per_file.items()):
        ext = Path(rel_path).suffix
        content = read_file_from_commit(repo, old_ref, rel_path)
        content = strip_unwanted_tests(content, wanted_methods, ext)
        abs_path = repo / rel_path
        abs_path.parent.mkdir(parents=True, exist_ok=True)
        abs_path.write_text(content, encoding="utf-8")
        stage_file(repo, rel_path)
        print(f"  ✓ copied & pruned {rel_path} "
              f"({len(wanted_methods)} tests kept)")

    print(
        f"\nDone.  {len(per_file)} file(s) are staged on {new_ref}.\n"
        "Double-check with ‘git diff --staged’ and commit when ready."
    )


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #

def main(argv: Iterable[str] | None = None) -> None:
    p = argparse.ArgumentParser(description="Sync UI test files between branches")
    p.add_argument("--repo", required=True, help="Path to the Git repository")
    p.add_argument("--old", required=True, help="Older branch / tag / commit")
    p.add_argument("--new", required=True, help="Newer branch / tag / commit")
    p.add_argument(
        "--fqns",
        required=True,
        help="Path to ui_test_fqns.txt *within* the repo",
    )
    p.add_argument(
        "--test-root",
        default="app/src/test/java",
        help="Root directory inside the repo that holds UI tests",
    )
    args = p.parse_args(argv)

    repo_path = Path(args.repo).expanduser().resolve()
    if not (repo_path / ".git").is_dir():
        sys.exit(f"{repo_path} does not look like a Git repository")

    # Bail if the working tree is dirty
    if run_git(repo_path, "status", "--porcelain").strip():
        sys.exit("Working tree has uncommitted changes — commit or stash first.")

    try:
        sync_tests(
            repo=repo_path,
            old_ref=args.old,
            new_ref=args.new,
            fqns_file=args.fqns,
            test_root=args.test_root,
        )
    except RuntimeError as exc:
        sys.exit(str(exc))


if __name__ == "__main__":
    main()
