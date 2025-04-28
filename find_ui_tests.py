#!/usr/bin/env python3
# HOW TO RUN: python find_ui_tests.py [--github-base-url GITHUB_BASE_URL]

import os
import re
from pathlib import Path

def find_ui_test_files(root_dir='.'):
    """
    Recursively find Kotlin and Java test files under src/*test*/ directories that contain UI test imports and have at least one @Test annotation.
    """
    matches = []
    ui_import_pattern = re.compile(r"androidx\.compose\.ui\.test|androidx\.test\.espresso")
    test_annotation_pattern = re.compile(r"@Test")

    for dirpath, dirnames, filenames in os.walk(root_dir):
        # Skip hidden directories
        dirnames[:] = [d for d in dirnames if not d.startswith('.')]
        for filename in filenames:
            if not filename.endswith(('.kt', '.java')):
                continue
            full_path = Path(dirpath) / filename
            # Check if path contains 'src/...test'
            if not re.search(rf"{re.escape(os.sep)}src{re.escape(os.sep)}.*test", str(full_path)):
                continue
            try:
                content = full_path.read_text(encoding='utf-8', errors='ignore')
            except Exception as e:
                print(f"Warning: could not read {full_path}: {e}")
                continue
            # Check both UI test imports and at least one @Test
            if ui_import_pattern.search(content) and test_annotation_pattern.search(content):
                matches.append(full_path)
    return sorted(matches)


def extract_test_names(file_path):
    """
    Extract test method display names (text inside backticks or method name) from a test file.
    """
    test_names = []
    lines = file_path.read_text(encoding='utf-8', errors='ignore').splitlines()
    for idx, line in enumerate(lines):
        if line.strip().startswith('@Test'):
            # Look ahead for the function definition
            for next_line in lines[idx+1:]:
                m = re.search(r"fun\s+`([^`]+)`", next_line)
                if m:
                    test_names.append(m.group(1))
                    break
                m2 = re.search(r"fun\s+(\w+)", next_line)
                if m2:
                    test_names.append(m2.group(1))
                    break
    return test_names


def extract_package_name(file_path):
    """
    Read the Kotlin/Java file to find its package declaration.
    Returns the package name (e.g., com.x8bit.bitwarden.ui) or None if not found.
    """
    for line in file_path.read_text(encoding='utf-8', errors='ignore').splitlines():
        m = re.match(r"\s*package\s+([\w\.]+)", line)
        if m:
            return m.group(1)
    return None


def write_hyperlinks_and_tests(test_files, root_dir, output_path, github_base_url):
    """
    Write an output file with a hyperlink header and test names per test file.
    """
    root = Path(root_dir).resolve()
    with open(output_path, 'w', encoding='utf-8') as out:
        for file_path in test_files:
            abs_path = file_path.resolve()
            try:
                rel_path = abs_path.relative_to(root)
            except ValueError:
                rel_path = abs_path
            url = f"{github_base_url.rstrip('/')}/{rel_path.as_posix()}" if github_base_url else rel_path.as_posix()
            basename = file_path.name
            test_names = extract_test_names(file_path)
            count = len(test_names)
            out.write(f'=HYPERLINK("{url}", "{basename} ({count})")\n')
            for name in test_names:
                out.write(f"{name}\n")
            out.write("\n")


def write_fully_qualified_names(test_files, output_path):
    """
    Write a file listing the fully qualified class names of each test file, one per line.
    """
    with open(output_path, 'w', encoding='utf-8') as out:
        for file_path in test_files:
            pkg = extract_package_name(file_path) or ''
            class_name = file_path.stem
            if pkg:
                out.write(f"{pkg}.{class_name}\n")
            else:
                out.write(f"{class_name}\n")


def main():
    import argparse
    parser = argparse.ArgumentParser(
        description='Find UI test files and generate reports with hyperlinks, test names, and fully qualified class names'
    )
    parser.add_argument(
        '--github-base-url',
        help='Base URL for GitHub repository (e.g., https://github.com/owner/repo/blob/main)'
    )
    args = parser.parse_args()

    # Always use current directory as root
    root_dir = '.'
    files = find_ui_test_files(root_dir)
    if not files:
        print("No UI test files found.")
        return

    report_path = 'ui_test_report.txt'
    fqn_path = 'ui_test_fqns.txt'
    write_hyperlinks_and_tests(
        files, root_dir, report_path, args.github_base_url
    )
    write_fully_qualified_names(files, fqn_path)
    print(f"Reports generated for {len(files)} files. See {report_path} and {fqn_path}")

if __name__ == '__main__':
    main()
