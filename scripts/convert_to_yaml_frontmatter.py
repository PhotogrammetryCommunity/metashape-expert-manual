#!/usr/bin/env python3
"""Convert older articles from bold-list blockquote frontmatter
to YAML frontmatter, matching the newer format.

Source format (older):
    # Article Title

    > - **edition:** `Standard` *(comment)*
    > - **tags:** `tag1`, `tag2`
    > - **applies_to:** Metashape ...
    > - **status:** `unverified` ...
    > - **confidence:** `medium` — ...
    > - **last_reviewed:** YYYY-MM-DD by `the assistant`

    ## Problem
    ...

Target format (newer):
    ---
    title: Article Title
    status: unverified
    applies_to: Metashape ...
    edition: Standard
    last_reviewed: YYYY-MM-DD
    diataxis: how-to | explanation | reference
    confidence: medium | high | low
    ---

    # Article Title

    ## Problem
    ...

Usage:
    convert_to_yaml_frontmatter.py PATH [PATH ...] [--dry-run] \
        [--diataxis VALUE]
"""
from __future__ import annotations
import argparse
import re
import sys
from pathlib import Path


def parse_bold_list(text: str) -> tuple[dict[str, str], int]:
    """Extract bold-list metadata and return (fields, end_offset).

    end_offset is the character position after the metadata block.
    """
    # Find the H1 line.
    h1_match = re.search(r"^# (.+)$", text, re.MULTILINE)
    if not h1_match:
        return {}, 0
    title = h1_match.group(1).strip()

    # Find the metadata block (lines starting with > -).
    after_h1 = text[h1_match.end():]
    # Lines starting with > - or > with continuation.
    block_match = re.match(
        r"\n+(?:>\s*-?\s*\*\*[^*]+\*\*[^\n]*\n?)+(?:>\s+[^\n]*\n?)*",
        after_h1,
    )
    if not block_match:
        return {"title": title}, h1_match.end()

    fields: dict[str, str] = {"title": title}
    block = block_match.group(0)
    # Each `> - **key:** value` produces a field.
    for m in re.finditer(
        r">\s*-?\s*\*\*([^:]+):\*\*\s*(.+?)(?=\n>\s*-|\n\n|\Z)",
        block,
        re.DOTALL,
    ):
        key = m.group(1).strip().lower().replace(" ", "_")
        # Clean up the value: remove backticks, italics, quotes.
        value = m.group(2).strip()
        # Strip backticks around simple identifier values.
        value = re.sub(r"^`([^`]+)`(\s|$)", r"\1\2", value)
        # For confidence / status etc., trim the explanatory part after "—" or "*("
        # Keep only the first segment up to the first " — " or " *(".
        for sep in (" — ", " *(", " *—*"):
            if sep in value:
                value = value.split(sep)[0].strip()
                break
        # Strip backticks again (in case stripping the segment exposed them).
        value = re.sub(r"^`([^`]+)`$", r"\1", value)
        fields[key] = value

    end_offset = h1_match.end() + block_match.end()
    return fields, end_offset


def to_yaml_frontmatter(fields: dict[str, str], diataxis: str) -> str:
    """Render the YAML frontmatter block + H1 title."""
    title = fields.get("title", "")
    yaml_lines = ["---", f"title: {title}"]

    # Standard order matching the article template.
    for key in ("status", "applies_to", "edition", "last_reviewed",
                "diataxis", "confidence"):
        if key == "diataxis":
            yaml_lines.append(f"diataxis: {diataxis}")
            continue
        if key == "last_reviewed":
            value = fields.get(key, "")
            # Strip 'by `the assistant`' suffix.
            value = re.sub(r"\s*by\s*`?\w+`?\s*$", "", value)
            yaml_lines.append(f"last_reviewed: {value}")
            continue
        value = fields.get(key, "")
        if value:
            yaml_lines.append(f"{key}: {value}")
    yaml_lines.append("---")
    yaml_lines.append("")
    yaml_lines.append(f"# {title}")
    return "\n".join(yaml_lines)


# Diataxis assignments per article (manually determined from content).
DIATAXIS = {
    "diagnosing-under-aligned-chunks": "how-to",
    "clean-tie-points-optimize-cameras-loop": "how-to",
    "automating-gradual-selection-python": "how-to",
    "removing-blue-flag-marker-projections": "how-to",
    "programmatic-marker-placement": "how-to",
    "reproducing-chunk-info-statistics-python": "how-to",
    "logging-from-python-scripts": "how-to",
    "setting-the-chunk-region": "how-to",
    "exporting-depth-maps-python": "how-to",
}


def convert(path: Path, dry_run: bool = False) -> bool:
    text = path.read_text(encoding="utf-8")
    if text.startswith("---"):
        print(f"  {path}: already YAML; skipping")
        return False
    fields, end_offset = parse_bold_list(text)
    if not fields:
        print(f"  {path}: could not parse; skipping")
        return False

    diataxis_value = DIATAXIS.get(path.stem, "how-to")
    new_frontmatter = to_yaml_frontmatter(fields, diataxis_value)
    body = text[end_offset:].lstrip("\n")
    new_text = new_frontmatter + "\n\n" + body

    if dry_run:
        print(f"--- {path} (dry-run) ---")
        print(new_text[:600])
        print("...")
    else:
        path.write_text(new_text, encoding="utf-8")
        print(f"  {path}: converted")
    return True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("paths", nargs="+", type=Path)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    n = 0
    for p in args.paths:
        if convert(p, args.dry_run):
            n += 1
    print(f"{'would convert' if args.dry_run else 'converted'} {n} files")


if __name__ == "__main__":
    main()
