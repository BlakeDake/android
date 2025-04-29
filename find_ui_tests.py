#!/usr/bin/env python3
"""
find_ui_tests.py — enumerate Android UI‑test source files (Kotlin/Java) and
produce two reports:
  • ui_test_report.txt      – hyperlink + **only UI‑test** @Test methods
  • ui_test_fqns.txt        – fully‑qualified **method** names (package.Class.method)

Console output now also prints the **total number of UI‑test methods** found.

Run:  python find_ui_tests.py [--github-base-url URL]
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import List, Tuple

# ──────────────────────────────
# Heuristics for detecting UI calls inside a test method
# ──────────────────────────────
_COMPOSE_CALLS = re.compile(
    r"""\b(
        compose(Test)?Rule              |  # rule variables / composeTestRule
        on(Node|AllNodes)\s*\(         |  # onNode()/onAllNodes()
        has(Text|ContentDescription|TestTag)\s*\( |
        perform(Click|Scroll|TextInput)\s*\( |
        assert(Exists|IsDisplayed|HasText)
    )""",
    re.X,
)
_ESPRESSO_CALLS = re.compile(
    r"""\b(
        on(View|Data|WebView)\s*\(     |  # onView(), onData(), ...
        with(Id|Text|ContentDescription)\s*\( |
        pressBack\s*\( |
        ViewActions|ViewAssertions          # common static imports
    )""",
    re.X,
)

def _looks_like_ui_test(body: str) -> bool:
    """Return True if method *body* contains Compose or Espresso calls."""
    return bool(_COMPOSE_CALLS.search(body) or _ESPRESSO_CALLS.search(body))

# ──────────────────────────────
# File-level discovery
# ──────────────────────────────

def find_ui_test_files(root_dir: str = ".") -> List[Path]:
    """Return *.kt / *.java files under src/**test**/ that import UI-test APIs."""
    matches: List[Path] = []
    ui_import_pattern = re.compile(r"androidx\.compose\.ui\.test|androidx\.test\.espresso")
    test_annotation_pattern = re.compile(r"@Test")

    for dirpath, dirnames, filenames in os.walk(root_dir):
        dirnames[:] = [d for d in dirnames if not d.startswith(".")]
        for filename in filenames:
            if not filename.endswith((".kt", ".java")):
                continue
            full_path = Path(dirpath) / filename
            if not re.search(rf"{re.escape(os.sep)}src{re.escape(os.sep)}.*test", str(full_path)):
                continue
            try:
                content = full_path.read_text(encoding="utf-8", errors="ignore")
            except Exception as exc:
                print(f"Warning: could not read {full_path}: {exc}")
                continue
            if ui_import_pattern.search(content) and test_annotation_pattern.search(content):
                matches.append(full_path)
    return sorted(matches)

# ──────────────────────────────
# Method-level helpers
# ──────────────────────────────

def _collect_method_body(lines: List[str], start_idx: int) -> Tuple[str, int]:
    """Return (method_body, next_index) for method starting at *start_idx*."""
    body_parts: List[str] = []
    open_braces = 0
    i = start_idx
    while i < len(lines):
        line = lines[i]
        body_parts.append(line)
        open_braces += line.count("{") - line.count("}")
        i += 1
        if open_braces <= 0:
            if i < len(lines) and (
                lines[i].lstrip().startswith("@Test") or re.match(r"\s*fun\s", lines[i])
            ):
                break
    return "\n".join(body_parts), i

_METHOD_DECL_RE_BACKTICK = re.compile(r"fun\s+`([^`]+)`")
_METHOD_DECL_RE_ID = re.compile(r"fun\s+(\w+)")


def extract_ui_test_names(file_path: Path) -> List[str]:
    """Return list of UI‑test method names in *file_path*."""
    ui_test_names: List[str] = []
    lines = file_path.read_text(encoding="utf-8", errors="ignore").splitlines()
    idx = 0
    while idx < len(lines):
        line = lines[idx]
        if line.lstrip().startswith("@Test"):
            j = idx + 1
            method_name: str | None = None
            while j < len(lines):
                m = _METHOD_DECL_RE_BACKTICK.search(lines[j])
                if m:
                    method_name = m.group(1)
                    break
                m2 = _METHOD_DECL_RE_ID.search(lines[j])
                if m2:
                    method_name = m2.group(1)
                    break
                if lines[j].lstrip().startswith("@Test"):
                    break
                j += 1
            if method_name is None:
                idx += 1
                continue
            body, next_idx = _collect_method_body(lines, j)
            if _looks_like_ui_test(body):
                ui_test_names.append(method_name)
            idx = next_idx
        else:
            idx += 1
    return ui_test_names

# ──────────────────────────────
# Package helper
# ──────────────────────────────

def extract_package_name(file_path: Path) -> str | None:
    for line in file_path.read_text(encoding="utf-8", errors="ignore").splitlines():
        m = re.match(r"\s*package\s+([\w\.]+)", line)
        if m:
            return m.group(1)
    return None

# ──────────────────────────────
# Report writers
# ──────────────────────────────

def write_hyperlinks_and_tests(
    test_files: List[Path],
    root_dir: str,
    output_path: str,
    github_base_url: str | None,
) -> int:
    """Write ui_test_report.txt and return **total UI‑test method count**."""
    root = Path(root_dir).resolve()
    total_methods = 0
    with open(output_path, "w", encoding="utf-8") as out:
        for file_path in test_files:
            ui_methods = extract_ui_test_names(file_path)
            if not ui_methods:
                continue  # skip files without UI tests
            total_methods += len(ui_methods)
            abs_path = file_path.resolve()
            rel_path = (
                abs_path.relative_to(root) if abs_path.is_relative_to(root) else abs_path
            )
            url = (
                f"{github_base_url.rstrip('/')}/{rel_path.as_posix()}"
                if github_base_url
                else rel_path.as_posix()
            )
            out.write(f'=HYPERLINK("{url}", "{file_path.name} ({len(ui_methods)})")\n')
            for name in ui_methods:
                out.write(f"{name}\n")
            out.write("\n")
    return total_methods


def write_fully_qualified_method_names(test_files: List[Path], output_path: str) -> None:
    """Write package.Class.method for every UI‑test method, one per line."""
    with open(output_path, "w", encoding="utf-8") as out:
        for file_path in test_files:
            pkg = extract_package_name(file_path) or ""
            class_name = file_path.stem
            for method in extract_ui_test_names(file_path):
                fqmn = f"{pkg + '.' if pkg else ''}{class_name}.{method}"
                out.write(fqmn + "\n")

# ──────────────────────────────
# CLI entry point
# ──────────────────────────────

def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(
        description="Generate per‑method UI‑test reports for Android projects",
    )
    parser.add_argument(
        "--github-base-url",
        required=True,
        help="Base URL for GitHub repo, e.g. https://github.com/org/repo/blob/main",
    )
    args = parser.parse_args()

    root_dir = "."
    files = find_ui_test_files(root_dir)
    if not files:
        print("No UI test files found.")
        return

    report_path = "ui_test_report.txt"
    fqn_path = "ui_test_fqns.txt"

    total_methods = write_hyperlinks_and_tests(
        files, root_dir, report_path, args.github_base_url
    )
    write_fully_qualified_method_names(files, fqn_path)

    print(
        f"Reports generated: {report_path} (hyperlinks) and {fqn_path} (Gradle patterns)"
    )
    print(f"Total UI‑test methods found: {total_methods}")


if __name__ == "__main__":
    main()
