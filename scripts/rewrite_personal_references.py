#!/usr/bin/env python3
"""Bulk-rewrite personal-name references in body text.

The rule (STYLE.md "Things not to do"): personal names appear only in
citations / blockquote attributions / References section. This script
applies common-pattern substitutions to body text.

Strategy:

1. Skip code blocks, blockquote attribution lines (single- and
   multi-line), References sections, YAML frontmatter, and admonitions.
2. Apply ordered list of regex substitutions (longer/more-specific first).
3. Apply a cleanup pass that fixes known awkward output patterns.
4. Report per-file before/after counts.

Usage:
    rewrite_personal_references.py [--dry-run] PATH [PATH ...]
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

# --- Substitution patterns (order matters — longer/more-specific first) ---

# Each entry: (regex, replacement). Replacements use \g<...> backrefs.
SUBS: list[tuple[re.Pattern, str]] = [
    # ----- Stage 1: Multi-word attributive phrasings -----
    (re.compile(r"\bAs\s+Pasumansky\s+(observed|noted|wrote|stated|said|put it)\b",
                re.IGNORECASE), "As documented"),
    (re.compile(r"\bAs\s+Alexey\s+Pasumansky\s+(observed|noted|wrote|stated|said|put it)\b",
                re.IGNORECASE), "As documented"),
    (re.compile(r"\bPer\s+Pasumansky\b"), "Per the canonical thread"),
    (re.compile(r"\bAccording\s+to\s+Pasumansky\b"), "Per the canonical thread"),
    (re.compile(r"\bFollowing\s+Pasumansky['\u2018\u2019]s\b"), "Following the canonical"),

    # ----- Stage 2: Possessive + collision-prone successor words -----
    (re.compile(r"\b(?:Alexey\s+)?Pasumansky['\u2018\u2019]s\s+canonical\b"), "the canonical"),
    (re.compile(r"\b(?:Alexey\s+)?Pasumansky['\u2018\u2019]s\s+documented\b"), "the documented"),
    (re.compile(r"\b(?:Alexey\s+)?Pasumansky['\u2018\u2019]s\s+(\d{4})\s+sample\s+script\b"),
                r"the \g<1> forum sample script"),
    (re.compile(r"\b(?:Alexey\s+)?Pasumansky['\u2018\u2019]s\s+(\d{4})\s+(script|recipe|enumeration|diagnostic|documentation|statement)\b"),
                r"the \g<1> forum \g<2>"),
    (re.compile(r"\b(?:Alexey\s+)?Pasumansky['\u2018\u2019]s\s+diagnostic\b"), "the documented diagnostic"),
    (re.compile(r"\b(?:Alexey\s+)?Pasumansky['\u2018\u2019]s\s+observability\b"), "the documented observability"),
    (re.compile(r"\b(?:Alexey\s+)?Pasumansky['\u2018\u2019]s\s+recommendation\b"), "the documented recommendation"),
    (re.compile(r"\b(?:Alexey\s+)?Pasumansky['\u2018\u2019]s\s+recipe\b"), "the canonical recipe"),
    (re.compile(r"\b(?:Alexey\s+)?Pasumansky['\u2018\u2019]s\s+enumeration\b"), "the canonical enumeration"),
    (re.compile(r"\b(?:Alexey\s+)?Pasumansky['\u2018\u2019]s\s+statement\b"), "the canonical statement"),
    (re.compile(r"\b(?:Alexey\s+)?Pasumansky['\u2018\u2019]s\s+sample\s+script\b"), "the canonical sample script"),
    (re.compile(r"\b(?:Alexey\s+)?Pasumansky['\u2018\u2019]s\s+script\b"), "the canonical script"),
    (re.compile(r"\b(?:Alexey\s+)?Pasumansky['\u2018\u2019]s\s+subsequent\b"), "the subsequent"),
    (re.compile(r"\b(?:Alexey\s+)?Pasumansky['\u2018\u2019]s\s+(\d{4})\b"), r"the \g<1> forum"),
    (re.compile(r"\b(?:Alexey\s+)?Pasumansky['\u2018\u2019]s\b"), "the canonical thread's"),

    # James / Heinrich / others — possessive forms
    (re.compile(r"\bJames['\u2018\u2019]s\s+enumeration\b"), "the canonical enumeration"),
    (re.compile(r"\bJames['\u2018\u2019]s\s+(\d{4})\b"), r"the \g<1> forum"),
    (re.compile(r"\bJames['\u2018\u2019]s\b"), "the canonical thread's"),
    (re.compile(r"\bDavid\s+Cockey['\u2018\u2019]s\s+(\d{4})\b"), r"the \g<1> community"),
    (re.compile(r"\bDavid\s+Cockey['\u2018\u2019]s\b"), "the community"),
    (re.compile(r"\bCockey['\u2018\u2019]s\b"), "the community"),
    (re.compile(r"\bHeinrich['\u2018\u2019]s\s+caveat\b"), "the repetitive-features caveat"),
    (re.compile(r"\bHeinrich['\u2018\u2019]s\b"), "the documented"),
    (re.compile(r"\bandyroo['\u2018\u2019]s\b"), "the canonical"),
    (re.compile(r"\bYoann\s+Courtois['\u2018\u2019]s\b"), "the source thread's"),
    (re.compile(r"\bThomasVD['\u2018\u2019]s\b"), "the source thread's"),
    (re.compile(r"\bBobvdMeij['\u2018\u2019]s\b"), "the source thread's"),
    (re.compile(r"\bps10['\u2018\u2019]s\b"), "the source thread's"),
    (re.compile(r"\bfermanrique['\u2018\u2019]s\b"), "the source thread's"),
    (re.compile(r"\bDavier['\u2018\u2019]s\b"), "the source thread's"),

    # ----- Stage 3: Hyphenated forms -----
    (re.compile(r"\b(?:Alexey\s+)?Pasumansky-attested\b"), "forum-attested"),
    (re.compile(r"\bPasumansky-stated\b"), "forum-stated"),
    (re.compile(r"\bPasumansky-recommended\b"), "the documented"),
    (re.compile(r"\bPasumansky-cited\b"), "forum-cited"),
    (re.compile(r"\bPasumansky-confirmed\b"), "forum-confirmed"),
    (re.compile(r"\bPasumansky-described\b"), "forum-documented"),
    (re.compile(r"\bPasumansky-flagged\b"), "forum-flagged"),
    (re.compile(r"\bPasumansky-attributed\b"), "forum-documented"),

    # ----- Stage 4: Date references -----
    (re.compile(r"\bPasumansky\s+(\d{4}-\d{2}-\d{2})\b"), r"(forum, \g<1>)"),
    (re.compile(r"\bPasumansky\s+(\d{4}):"), r"the \g<1> forum statement:"),
    (re.compile(r"\bPasumansky\s+(\d{4})\s+statement\b"), r"the \g<1> forum statement"),
    (re.compile(r"\bPasumansky\s+(\d{4})\b"), r"the \g<1> forum statement"),
    (re.compile(r"\bAlexey\s+Pasumansky\s+(\d{4}-\d{2}-\d{2})\b"), r"(forum, \g<1>)"),
    (re.compile(r"\bAlexey\s+Pasumansky\s+(\d{4})\b"), r"the \g<1> forum statement"),
    (re.compile(r"\bDavid\s+Cockey\s+(\d{4})\b"), r"the \g<1> community enumeration"),
    (re.compile(r"\bCockey\s+(\d{4})\b"), r"the \g<1> community enumeration"),
    (re.compile(r"\bJames\s+(\d{4}-\d{2}-\d{2})\b"), r"(forum, \g<1>)"),
    (re.compile(r"\bJames\s+(\d{4})\b"), r"the \g<1> forum"),

    # ----- Stage 5: Specific verb-followed phrasings -----
    (re.compile(r"\bPasumansky\s+(observed|noted|wrote|stated|said|put it|recommends|recommended|warned|warns|confirmed|confirms|emphasised|emphasized|describes|described)\b"),
                r"the canonical thread \g<1>"),
    (re.compile(r"\bPasumansky\s+himself\b"), "the canonical thread"),
    (re.compile(r"\bPasumansky\s+concurrence\b"), "forum concurrence"),
    (re.compile(r"\bPasumansky\s+statements\b"), "forum statements"),
    (re.compile(r"\bAlexey\s+(observed|noted|wrote|stated|said|put it)\b"),
                r"the canonical thread \g<1>"),
    (re.compile(r"\bAlexey['\u2018\u2019]s\b"), "the canonical thread's"),

    # ----- Stage 6: Standalone names — last resort -----
    (re.compile(r"\bAlexey\s+Pasumansky\b"), "the canonical thread"),
    (re.compile(r"\bPasumansky\b"), "the canonical thread"),
    (re.compile(r"\bAlexey\b(?!\s+Pasumansky)"), "the canonical thread"),
    (re.compile(r"\bJames\s+enumerated\b"), "the forum enumerated"),
    (re.compile(r"\bJames\s+enumeration\b"), "the canonical enumeration"),
    (re.compile(r"\bJames\b"), "the source thread"),
    (re.compile(r"\bHeinrich\b"), "the source thread"),
    (re.compile(r"\bandyroo\b"), "the canonical thread"),
    (re.compile(r"\bps10\b"), "the source thread"),
    (re.compile(r"\bfermanrique\b"), "the source thread"),
    (re.compile(r"\bDavier\b"), "the source thread"),
    (re.compile(r"\bBobvdMeij\b"), "the source thread"),
    (re.compile(r"\bYoann\s+Courtois\b"), "the source thread"),
    (re.compile(r"\bYoann\b"), "the source thread"),
    (re.compile(r"\bThomasVD\b"), "the source thread"),
    (re.compile(r"\bDavid\s+Cockey\b"), "the community"),
    (re.compile(r"\bCockey\b"), "the community"),
    (re.compile(r"\bDmitry\s+Semyonov\b"), "Agisoft"),
    (re.compile(r"\bSemyonov\b"), "Agisoft"),
    (re.compile(r"\bPaulo\b"), "the source thread"),
]

# --- Cleanup substitutions (after main pass) ---
CLEANUP_SUBS: list[tuple[re.Pattern, str]] = [
    (re.compile(r"\bthe\s+canonical\s+canonical\b"), "the canonical"),
    (re.compile(r"\bthe\s+canonical\s+thread['\u2018\u2019]s\s+canonical\b"), "the canonical"),
    (re.compile(r"\bthe\s+community\s+(\d{4})\s+community\s+enumeration\b"),
                r"the \g<1> community enumeration"),
    (re.compile(r"\bverbatim\s+the\s+canonical\s+thread\s+(\w+)\b"),
                r"verbatim \g<1>"),
    (re.compile(r"\bverbatim\s+the\s+source\s+thread\s+(\w+)\b"),
                r"verbatim \g<1>"),
    (re.compile(r"\bforum-attested\s+forum-attested\b"), "forum-attested"),
    (re.compile(r"\b(the\s+canonical\s+thread)\s+(the\s+canonical\s+thread)\b"),
                r"\g<1>"),
    (re.compile(r"\bwith\s+the\s+canonical\s+thread\s+concurrence\b"),
                "with forum concurrence"),
    (re.compile(r"\blater\s+the\s+canonical\s+thread\s+statements\b"),
                "later forum statements"),
    (re.compile(r"\bthe\s+the\s+"), "the "),
    (re.compile(r"\bthe\s+(\d{4})\s+forum\s+statement\s+statement\b"),
                r"the \g<1> forum statement"),
    # "the canonical thread same-thread statement" — original was
    # "Pasumansky's same-thread statement"
    (re.compile(r"\bthe\s+canonical\s+thread['\u2018\u2019]s\s+same-thread\b"),
                "the same-thread"),
    # "the source thread the source thread" — collapse
    (re.compile(r"\b(the\s+source\s+thread)\s+(the\s+source\s+thread)\b"),
                r"\g<1>"),
]


def in_attribution_block(prev_line, line: str) -> bool:
    """Detect blockquote attribution: this line OR a multi-line
    continuation. Conservative: prefer false-positive (skip) over
    false-negative (rewrite a real attribution).
    """
    if not line.lstrip().startswith(">"):
        return False
    s_inner = line.lstrip("> \t").lstrip()
    # Form 1: ` — Author Name, ... YYYY` anywhere on the line
    if re.search(r"[\u2014\u2013-]\s+[A-Z][\w\s'.\-]+,\s*\d{4}", line):
        return True
    # Form 2: ` — Author Name` at end of line (multi-line attribution where
    # the date spilled to the next line). Match em-dash + name(s).
    if re.search(r"[\u2014\u2013-]\s+[A-Z][\w\s'.\-]+\s*$", line.rstrip()):
        return True
    # Form 3: continuation line containing `Name, YYYY-...` preceded by
    # an attribution-end on the previous line.
    if (re.match(r"^[A-Z][\w\s'.\-]+,\s*\d{4}", s_inner)
            and prev_line is not None
            and re.search(r"[\u2014\u2013-]\s+[A-Z][\w\s'.\-]+\s*$", prev_line.rstrip())):
        return True
    # Form 4: standalone `Name, YYYY-MM-DD, Cite-as` continuation
    if re.match(r"^[A-Z][\w\s'.\-]+,\s*\d{4}-\d{2}-\d{2},\s*[A-Za-z]", s_inner):
        return True
    if re.match(r"^[A-Z][\w\s'.\-]+,\s*\d{4},\s*[A-Za-z]", s_inner):
        return True
    # Form 5: permalink-only continuation
    if re.match(r"^>\s*\(\[permalink\]", line):
        return True
    if re.match(r"^>\s*\(https?://", line):
        return True
    return False


def rewrite_file(path: Path, dry_run: bool = False) -> tuple[int, int]:
    """Returns (n_lines_changed, n_subs_applied)."""
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines(keepends=True)
    new_lines: list[str] = []

    in_yaml = False
    in_code_block = False
    current_section_is_refs = False
    in_admonition = False
    admonition_indent = 0

    n_lines_changed = 0
    n_subs_applied = 0
    prev_line = None

    for i, raw_line in enumerate(lines):
        line = raw_line.rstrip("\n")
        # Frontmatter
        if i == 0 and line.strip() == "---":
            in_yaml = True
            new_lines.append(raw_line)
            prev_line = line
            continue
        if in_yaml:
            if line.strip() == "---":
                in_yaml = False
            new_lines.append(raw_line)
            prev_line = line
            continue

        # Code blocks
        if line.strip().startswith("```"):
            in_code_block = not in_code_block
            new_lines.append(raw_line)
            prev_line = line
            continue
        if in_code_block:
            new_lines.append(raw_line)
            prev_line = line
            continue

        # Section headings — track References/Sources
        if line.startswith("#"):
            heading = line.strip("# ").strip().lower()
            current_section_is_refs = heading in (
                "references", "see also", "related", "sources", "citation",
            )
            new_lines.append(raw_line)
            prev_line = line
            continue

        # Skip the References section
        if current_section_is_refs:
            new_lines.append(raw_line)
            prev_line = line
            continue

        # Skip blockquote attribution lines (and multi-line continuations)
        if in_attribution_block(prev_line, line):
            new_lines.append(raw_line)
            prev_line = line
            continue

        # Admonitions
        if re.match(r"^!!!\s*\w", line):
            in_admonition = True
            admonition_indent = len(line) - len(line.lstrip())
            new_lines.append(raw_line)
            prev_line = line
            continue
        if in_admonition:
            if line.strip() == "" or line.startswith(" " * (admonition_indent + 4)):
                new_lines.append(raw_line)
                prev_line = line
                continue
            in_admonition = False

        # Apply substitutions
        new_line = line
        for pat, repl in SUBS:
            new_line, n = pat.subn(repl, new_line)
            if n > 0:
                n_subs_applied += n
        # Cleanup pass
        for pat, repl in CLEANUP_SUBS:
            new_line, n = pat.subn(repl, new_line)
            if n > 0:
                n_subs_applied += n

        if new_line != line:
            n_lines_changed += 1
        new_lines.append(new_line + ("\n" if raw_line.endswith("\n") else ""))
        prev_line = new_line

    new_text = "".join(new_lines)
    if dry_run:
        if n_subs_applied > 0:
            print(f"  {path}: would apply {n_subs_applied} substitutions "
                  f"on {n_lines_changed} line(s)")
    else:
        if n_subs_applied > 0:
            path.write_text(new_text, encoding="utf-8")
            print(f"  {path}: {n_subs_applied} substitutions on "
                  f"{n_lines_changed} line(s)")

    return n_lines_changed, n_subs_applied


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("paths", nargs="+")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    total_lines = 0
    total_subs = 0
    files_touched = 0

    for arg in args.paths:
        p = Path(arg)
        targets: list[Path] = []
        if p.is_dir():
            targets.extend(p.rglob("*.md"))
        elif p.is_file():
            targets.append(p)

        for f in targets:
            if "insights" in f.parts:
                continue
            n_lines, n_subs = rewrite_file(f, args.dry_run)
            if n_subs > 0:
                files_touched += 1
                total_lines += n_lines
                total_subs += n_subs

    action = "would apply" if args.dry_run else "applied"
    print(f"\n{action} {total_subs} substitutions across "
          f"{total_lines} lines in {files_touched} files.")


if __name__ == "__main__":
    main()
