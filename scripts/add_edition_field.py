#!/usr/bin/env python3
"""Add `edition: Pro` (or specified value) after `applies_to:` in articles
that lack the `edition:` frontmatter field.

Usage:
    add_edition_field.py PATH [PATH ...]   # add `edition: Pro`
"""
from __future__ import annotations
import re
import sys
from pathlib import Path


def add_edition(path: Path, edition: str = "Pro") -> bool:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---"):
        print(f"  {path}: not YAML frontmatter; skipping")
        return False
    # Already has edition?
    if re.search(r"^edition:", text, re.MULTILINE):
        print(f"  {path}: already has edition; skipping")
        return False
    # Insert after `applies_to:` line.
    pattern = re.compile(r"(^applies_to:.*$)", re.MULTILINE)
    new_text, n = pattern.subn(rf"\1\nedition: {edition}", text, count=1)
    if n == 0:
        print(f"  {path}: no applies_to: line; skipping")
        return False
    path.write_text(new_text, encoding="utf-8")
    print(f"  {path}: added edition: {edition}")
    return True


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    n = 0
    for arg in sys.argv[1:]:
        if add_edition(Path(arg)):
            n += 1
    print(f"updated {n} files")


if __name__ == "__main__":
    main()
