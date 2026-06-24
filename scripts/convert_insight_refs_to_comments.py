#!/usr/bin/env python3
"""Convert insight references in docs/*.md to HTML comments.

Insight cards are internal authoring notes (one per source-thread cluster).
They live in `insights/` and are excluded from the published mkdocs site.
However, ~60 published articles in `docs/` reference insight files by name,
typically as bullet points in a `## References` or `## See also` section like:

    - Insight card: `insights/insight-0059-vertex-normal-computation`.
    - Insight: `insights/insight-0058-reduce-overlap`
    - **Internal insight cards:** `insights/insight-0001`,
      `insights/insight-0006`, `insights/insight-0008`.

This script converts each such bullet to an HTML comment so the reference is:

* INVISIBLE in the rendered article (mkdocs Material strips HTML comments).
* VISIBLE in the markdown source (tech writers and reviewers see them when
  reading the file).

Bullet lines are detected as starting with ``- `` (bullet prefix) and containing
``insights/insight-``. Multi-line bullets are gathered via continuation-indent
detection (lines indented further than the bullet). Each bullet (single-line or
multi-line) becomes a single HTML comment.

After running, manually inspect any `## References` or `## See also` sections
that may have been left with no bullet content and remove the empty section
header if appropriate.

Usage::

    ./.venv/bin/python scripts/convert_insight_refs_to_comments.py [--dry-run]
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


BULLET_INSIGHT_RE = re.compile(r'^(\s*)- .*insights/insight-')


def is_continuation(line: str, bullet_indent: str) -> bool:
    """Lines indented further than the bullet's `-` are continuations."""
    if not line:
        return False
    # Bullet continuation lines start with bullet_indent + at least 2 spaces
    # (the markdown convention for continuing a bullet's content).
    return line.startswith(bullet_indent + "  ")


def convert_text(text: str) -> tuple[str, int]:
    """Convert insight-bullet blocks to HTML comments. Return (new_text, count)."""
    lines = text.splitlines(keepends=False)
    new_lines: list[str] = []
    i = 0
    converted = 0
    while i < len(lines):
        line = lines[i]
        m = BULLET_INSIGHT_RE.match(line)
        if not m:
            new_lines.append(line)
            i += 1
            continue
        # Found a bullet starting an insight reference. Gather any
        # continuation lines (indented further than the bullet).
        bullet_indent = m.group(1)
        block = [line]
        j = i + 1
        while j < len(lines) and is_continuation(lines[j], bullet_indent):
            block.append(lines[j])
            j += 1
        # Strip the bullet prefix from the first line; keep continuation
        # lines as-is (they're already part of the comment content).
        first_inner = block[0][len(bullet_indent) + 2:]  # drop "- "
        rest = block[1:]
        if rest:
            inner_lines = [first_inner] + [
                l[len(bullet_indent) + 2:] for l in rest
            ]
            comment_inner = "\n".join(inner_lines)
            new_lines.append(f"{bullet_indent}<!-- Internal: {comment_inner} -->")
        else:
            new_lines.append(f"{bullet_indent}<!-- Internal: {first_inner} -->")
        converted += 1
        i = j
    return "\n".join(new_lines) + ("\n" if text.endswith("\n") else ""), converted


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true",
                        help="report changes but do not write files")
    parser.add_argument("--root", default="docs", type=Path,
                        help="docs root (default: docs)")
    args = parser.parse_args()

    files_changed = 0
    bullets_converted = 0
    for md in sorted(args.root.rglob("*.md")):
        text = md.read_text()
        new_text, n = convert_text(text)
        if n > 0:
            files_changed += 1
            bullets_converted += n
            print(f"  {md}: {n} insight reference(s)")
            if not args.dry_run:
                md.write_text(new_text)

    if args.dry_run:
        print(f"\n[dry-run] Would update {files_changed} file(s), "
              f"converting {bullets_converted} insight bullet(s).")
    else:
        print(f"\nUpdated {files_changed} file(s), "
              f"converting {bullets_converted} insight bullet(s).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
