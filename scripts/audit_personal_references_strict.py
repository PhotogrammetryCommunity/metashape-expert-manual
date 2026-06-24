#!/usr/bin/env python3
"""Strengthened audit: find name occurrences ANYWHERE in published docs
except in genuine citation forms (blockquote attributions, link labels,
reference-table author columns).

Stricter than scripts/audit_personal_references.py — flags possessives
and attributions in References-section descriptive text.

Usage:
    audit_personal_references_strict.py [docs/path...]
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

NAMES = [
    "Alexey Pasumansky", "Pasumansky", "Alexey", "Dmitry Semyonov", "Semyonov",
    "James", "Heinrich", "andyroo", "Yoann Courtois", "Yoann", "ThomasVD",
    "BobvdMeij", "Bzuco", "JMR", "Paulo", "PROBERT1968", "Wishgranter", "ps10",
    "fermanrique", "Davier", "HMArnold", "StormingPython", "nickponline",
    "yangjie", "jseinturier", "3create", "B_Free42", "tpeachey", "an198317",
    "David Cockey", "Cockey", "JedFrechette", "jedfrechette", "Patribus",
    "Geert", "gEEvEE", "Ilia", "ilia", "GrinGEO", "Rockflower",
    "Duncan Bourne", "llas", "jetdog6", "foxx1", "Marburg", "ajam13",
    "daxils", "michaldolnik", "varadg", "mauchi", "frmgsft", "PhotogrammetryUser",
]
NAME_PATTERN = re.compile(r"\b(" + "|".join(re.escape(n) for n in NAMES) + r")\b")


def is_in_link_label(line: str, start: int, end: int) -> bool:
    """Is the name inside a [...](url) link label?"""
    before = line[:start]
    after = line[end:]
    open_bracket = before.rfind("[")
    if open_bracket < 0:
        return False
    if "]" in before[open_bracket:]:
        return False
    close_bracket = after.find("]")
    if close_bracket < 0:
        return False
    rest = after[close_bracket + 1:]
    return rest.startswith("(")


def is_in_reference_table_cell(line: str, in_table: bool) -> bool:
    """Is the line a structured citation table row in reference/features/?
    Format: | date | version | Author | [link](url) | takeaway |
    The Author column IS the citation; permitted."""
    if not in_table:
        return False
    # Must be a markdown table row with at least 4 pipes
    if line.count("|") < 4:
        return False
    return True


def is_in_blockquote_attribution(line: str) -> bool:
    """Citation blockquote attribution — names allowed."""
    s = line.strip()
    if not s.startswith(">"):
        return False
    if re.search(r"[—–-]\s+[A-Za-z][\w\s'.\-()]*,\s*\d{4}", line):
        return True
    if re.search(r"[—–-]\s+[A-Za-z][\w\s'.\-()]*[,.\s]*$", line.rstrip()):
        return True
    # Continuation line: the > line starts with a name and date, no dash
    # (the dash was on the previous line).
    inner = s.lstrip("> ").lstrip()
    if re.match(r"^[A-Za-z][\w\s'.\-()]*,\s*\d{4}", inner):
        return True
    # Citation forms using "same thread" / "same post" / "ibid" instead of date
    if re.search(r"[—–-]\s+[A-Za-z][\w\s'.\-()]*,\s*(same\s+thread|same\s+post|ibid|earlier\s+in\s+this\s+thread)\b", line, re.IGNORECASE):
        return True
    return False


def is_in_bullet_citation_attribution(line: str, prev_line: str) -> bool:
    """Bullet-list citation attribution: the indented `  — Author Name, date, version` line
    immediately following a `- Forum thread, [...](url)` line."""
    # The line must start with whitespace then "— Name, ..."
    if not re.match(r"^\s+[—–-]\s+[A-Za-z][\w\s'.\-()]*,\s*\d{4}", line):
        return False
    # Look at the previous line — should be a Forum-thread bullet
    return bool(re.search(r"^\s*-\s+(Forum thread|Forum:)|\[.*\]\(http", prev_line or ""))


def audit_file(path: Path) -> list[tuple[int, str, str, str]]:
    """Return findings: (line_no, name, line_text, reason)."""
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    findings = []

    in_yaml = False
    in_code_block = False
    in_table = False  # reference-features citation tables
    in_html_comment = False
    prev_line = ""

    for i, line in enumerate(lines, start=1):
        if i == 1 and line.strip() == "---":
            in_yaml = True
            prev_line = line
            continue
        if in_yaml:
            if line.strip() == "---":
                in_yaml = False
            prev_line = line
            continue

        if line.strip().startswith("```"):
            in_code_block = not in_code_block
            prev_line = line
            continue
        if in_code_block:
            prev_line = line
            continue

        if "<!--" in line and "-->" not in line:
            in_html_comment = True
        if in_html_comment:
            if "-->" in line:
                in_html_comment = False
            prev_line = line
            continue
        if "<!--" in line and "-->" in line:
            prev_line = line
            continue

        if "| Date | Version | Author |" in line or "| Date  | Version" in line:
            in_table = True
            prev_line = line
            continue
        if in_table and not line.strip().startswith("|"):
            in_table = False

        if is_in_blockquote_attribution(line):
            prev_line = line
            continue

        if is_in_bullet_citation_attribution(line, prev_line):
            prev_line = line
            continue

        for m in NAME_PATTERN.finditer(line):
            if is_in_link_label(line, m.start(), m.end()):
                continue
            if is_in_reference_table_cell(line, in_table):
                continue
            findings.append((i, m.group(0), line.rstrip()[:140], "body or descriptive text"))

        prev_line = line

    return findings


def main():
    paths = sys.argv[1:] or ["docs"]
    targets = []
    for p in paths:
        p = Path(p)
        if p.is_file():
            targets.append(p)
        else:
            targets.extend(sorted(p.rglob("*.md")))

    total_findings = 0
    files_with_findings = []
    for path in targets:
        findings = audit_file(path)
        if findings:
            files_with_findings.append((path, findings))
            total_findings += len(findings)

    print(f"# Strict personal-name audit\n")
    print(f"**Total findings:** {total_findings} occurrences across "
          f"{len(files_with_findings)} files.\n")

    if not files_with_findings:
        print("(All clean.)")
        return 0

    print("| File | Line | Name | Context |")
    print("|------|-----:|------|---------|")
    for path, findings in files_with_findings:
        for lineno, name, snippet, reason in findings:
            snippet_display = snippet.replace("|", "\\|")
            print(f"| `{path}` | {lineno} | {name} | {snippet_display} |")

    return 1


if __name__ == "__main__":
    sys.exit(main())
