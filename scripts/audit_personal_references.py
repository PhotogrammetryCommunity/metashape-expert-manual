#!/usr/bin/env python3
"""Audit articles for personal-name references in body text.

The rule: personal names (Alexey Pasumansky, James, Heinrich, etc.)
must NOT appear in body text of the published manual. They are
permitted only in:

- Blockquote attribution lines: `> ... — Author Name, YYYY-MM-DD, Cite-as`
- The article's References section (final `## References` block)
- URL anchor text or `[Forum thread, ...]` link labels
- The Article-info admonition (rendered from frontmatter)

This script flags every other occurrence.

Usage:
    audit_personal_references.py [docs/path...]
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

# Names that appear in our forum sources. Add more as needed.
NAMES = [
    "Alexey Pasumansky",
    "Pasumansky",
    "Alexey",            # standalone "Alexey" (often refers to Pasumansky)
    "Dmitry Semyonov",
    "Semyonov",
    "James",
    "Heinrich",
    "andyroo",
    "Yoann Courtois",
    "Yoann",
    "ThomasVD",
    "BobvdMeij",
    "Bzuco",
    "JMR",
    "Paulo",
    "PROBERT1968",
    "Wishgranter",
    "ps10",
    "fermanrique",
    "Davier",
    "HMArnold",
    "StormingPython",
    "nickponline",
    "yangjie",
    "jseinturier",
    "3create",
    "B_Free42",
    "tpeachey",
    "an198317",
    "David Cockey",
    "Cockey",
    "JedFrechette",
    "jedfrechette",
    "Patribus",
    "Geert",            # Geert / gEEvEE — 2012 gradual-selection workflow
    "gEEvEE",
    "Ilia",             # Ilia / ilia — incremental-matching follow-up
    "ilia",
    "GrinGEO",          # BigTIFF caveat
    "Rockflower",       # orthomosaic shift report
    "Duncan Bourne",    # orthomosaic shift report
    "llas",             # no-camera-deduplication thread participant
]

# Compile a single regex that matches any of these as a whole word.
NAME_PATTERN = re.compile(
    r"\b(" + "|".join(re.escape(n) for n in NAMES) + r")\b"
)


def is_attribution_line(line: str) -> bool:
    """A blockquote attribution line. Examples:
        > — Alexey Pasumansky, 2017-05-04, PhotoScan 1.3
        > — James, 2017-11-28, PhotoScan 1.3
        > "...quote text." — Alexey Pasumansky, 2014-11-12, PhotoScan 1.0
        > Build Texture." — David Cockey, 2014-07-08, PhotoScan 1.0
        > ([permalink](url))   — continuation
        > Pasumansky, 2020-01-25, Metashape 1.5   — continuation when
        the dash-name pair was on the previous line and only the
        date-version tail spilled to this line.
        > "..." — Alexey   — multi-line attribution where the name
        spans two lines (the date is on the next line).
    """
    s = line.strip()
    if not s.startswith(">"):
        return False
    inner = s.lstrip("> ").lstrip()
    # Form 1: ` — Author Name [(parenthetical)], YYYY-MM-DD, Cite-as` anywhere on the line.
    # Allow lowercase first letter for forum handles like `andyroo`, `ps10`.
    # Allow parenthetical inserts between name and comma (e.g.
    # `— Paulo (relaying Agisoft Support), 2022-05-11, ...`).
    if re.search(r"[—–-]\s+[A-Za-z][\w\s'.\-()]*,\s*\d{4}", line):
        return True
    # Form 2: ` — Author Name` at end of line — multi-line attribution where
    # the date spilled to the next line. Allow trailing punctuation
    # and parenthetical inserts (e.g. `— Paulo (relaying Agisoft
    # Support),` ends a line whose date is on the next line).
    if re.search(r"[—–-]\s+[A-Za-z][\w\s'.\-()]*[,.\s]*$", line.rstrip()):
        return True
    # Form 3: continuation of the preceding-line attribution where
    # only the date-version tail spilled onto this line.
    # Form 3: continuation line containing `Name [(extra)], YYYY-...`
    # preceded by an attribution-end on the previous line.
    if re.match(r"^[A-Za-z][\w\s'.\-()]*,\s*\d{4}-\d{2}-\d{2},\s*[A-Za-z]", inner):
        return True
    if re.match(r"^[A-Za-z][\w\s'.\-()]*,\s*\d{4},\s*[A-Za-z]", inner):
        return True
    # Form 4: permalink-only continuation
    if re.match(r"^>\s*\(\[permalink\]", line):
        return True
    if re.match(r"^>\s*\(https?://", line):
        return True
    return False


def is_link_label(line: str, name_match_start: int, name_match_end: int) -> bool:
    """Is the matched name inside a markdown link label?
    Example: [Forum thread, *Cesium tiles*, 2017](url)
    """
    # Find the [...](...) span containing this position
    # Look backward for [, forward for ], then check the next char is (
    before = line[:name_match_start]
    after = line[name_match_end:]
    open_bracket = before.rfind("[")
    if open_bracket < 0:
        return False
    # Make sure no closing bracket between
    if "]" in before[open_bracket:]:
        return False
    close_bracket = after.find("]")
    if close_bracket < 0:
        return False
    rest = after[close_bracket + 1:]
    return rest.startswith("(")


def section_is_references(section_heading: str) -> bool:
    """Is this section the article's References section?"""
    s = section_heading.lower().strip("# ").strip()
    if s in ("references", "see also", "related", "sources", "citation"):
        return True
    # Forum-thread / source listings (feature-encyclopedia pages)
    if "forum threads worth reading" in s:
        return True
    if s.startswith("forum threads") or s.startswith("further reading"):
        return True
    return False


def audit_file(path: Path) -> list[tuple[int, str, str]]:
    """Return list of (line_no, name, line_text) findings."""
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    findings: list[tuple[int, str, str]] = []

    in_yaml = False
    in_admonition = False
    admonition_indent = 0
    in_code_block = False
    in_blockquote_attribution_block = False
    current_section_is_refs = False
    current_section_heading = ""

    for i, line in enumerate(lines, start=1):
        # Track YAML frontmatter (skip).
        if i == 1 and line.strip() == "---":
            in_yaml = True
            continue
        if in_yaml:
            if line.strip() == "---":
                in_yaml = False
            continue

        # Track code blocks (skip).
        if line.strip().startswith("```"):
            in_code_block = not in_code_block
            continue
        if in_code_block:
            continue

        # Track section headings; flag names found in heading text too.
        if line.startswith("#"):
            current_section_heading = line
            current_section_is_refs = section_is_references(line)
            # Headings can be References/etc. (skip) or content headings
            # (audit them — section titles must not contain personal names).
            if not current_section_is_refs:
                # Audit the heading text (after the #'s) for names.
                heading_text = line.lstrip("#").strip()
                for m in NAME_PATTERN.finditer(heading_text):
                    name = m.group(0)
                    findings.append((i, name, line.rstrip()))
            continue

        # Skip everything in References / Sources / See also / Related sections.
        if current_section_is_refs:
            continue

        # Skip blockquote attribution lines (— Author, date, version).
        if is_attribution_line(line):
            continue

        # Skip lines inside an Article-info admonition (handled by hook;
        # any name in our YAML metadata wouldn't be a person anyway).
        # Already handled by skipping admonition content via indentation
        # heuristic; but our hook only renders status/applies_to/etc., no
        # personal names. Skip safely.
        if re.match(r'^!!!\s*\w', line):
            in_admonition = True
            admonition_indent = len(line) - len(line.lstrip())
            continue
        if in_admonition:
            if line.strip() == "" or line.startswith(" " * (admonition_indent + 4)):
                continue
            in_admonition = False

        # Find name matches.
        for m in NAME_PATTERN.finditer(line):
            name = m.group(1)
            # Skip if inside a link label (i.e., inside [...]( ... )).
            if is_link_label(line, m.start(), m.end()):
                continue
            findings.append((i, name, line.rstrip()))

    return findings


def main():
    paths = sys.argv[1:] or ["docs"]
    all_findings: dict[Path, list[tuple[int, str, str]]] = {}
    for p in paths:
        path_obj = Path(p)
        if path_obj.is_file():
            findings = audit_file(path_obj)
            if findings:
                all_findings[path_obj] = findings
            continue
        for f in path_obj.rglob("*.md"):
            findings = audit_file(f)
            if findings:
                all_findings[f] = findings

    total = sum(len(v) for v in all_findings.values())
    print(f"# Personal-name references in body text\n")
    print(f"**Total findings:** {total} occurrences across "
          f"{len(all_findings)} files.\n")

    if not all_findings:
        print("(All clean.)")
        return 0

    print("| File | Line | Name | Context |")
    print("|------|-----:|------|---------|")
    for f, findings in sorted(all_findings.items()):
        rel = f.relative_to(".")
        for line_no, name, text in findings:
            # Truncate text for the table.
            if len(text) > 80:
                idx = text.find(name)
                start = max(0, idx - 25)
                end = min(len(text), idx + len(name) + 30)
                text = ("..." if start > 0 else "") + text[start:end] + \
                       ("..." if end < len(text) else "")
            text = text.replace("|", "⏐").replace("\n", " ")
            print(f"| `{rel}` | {line_no} | {name} | {text} |")

    return 1 if total > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
