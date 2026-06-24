#!/usr/bin/env python3
"""Apply systematic personal-name cleanup to docs/ articles.

Rule: names allowed only in:
- Citation blockquote attribution lines `> ... — Name, YYYY-MM-DD, ...`
- Markdown link labels `[Name, date, version](url)`
- Reference-features Author column tables

Everything else: replace possessive / "X on Y" / "(X YYYY)" / etc.
with neutral phrasings.
"""
from __future__ import annotations
import re
import sys
from pathlib import Path

NAMES_RAW = [
    "Alexey Pasumansky", "Pasumansky", "Alexey", "Dmitry Semyonov", "Semyonov",
    "Yoann Courtois", "Yoann", "Heinrich", "James", "Paulo", "ThomasVD",
    "BobvdMeij", "Bzuco", "JMR", "PROBERT1968", "Wishgranter", "ps10",
    "fermanrique", "Davier", "HMArnold", "StormingPython", "nickponline",
    "yangjie", "jseinturier-utln", "jseinturier", "3create", "B_Free42",
    "tpeachey", "an198317", "David Cockey", "Cockey", "JedFrechette",
    "jedfrechette", "Patribus", "Geert", "gEEvEE", "Ilia", "ilia",
    "GrinGEO", "Rockflower", "Duncan Bourne", "llas", "andyroo",
    "jetdog6", "foxx1", "Marburg", "ajam13", "daxils", "michaldolnik",
    "varadg", "mauchi", "frmgsft", "PhotogrammetryUser",
]
# Sort longest-first so multi-word names match before single-word
NAMES = sorted(NAMES_RAW, key=lambda n: -len(n))
NAME_GROUP = "(?:" + "|".join(re.escape(n) for n in NAMES) + ")"

# === Replacement patterns (applied in order) ===
PATTERNS: list[tuple[re.Pattern, str]] = [
    # Multi-word quoted-phrase possessive: `Pasumansky's "driver failure" diagnosis`
    (re.compile(rf"\b{NAME_GROUP}'s\s+(\"[^\"]+\")\s+(\w+)"), r"the \1 \2"),

    # Possessive forms: "Pasumansky's clarification" → "the clarification"
    (re.compile(rf"\b{NAME_GROUP}'s\s+(\w+(?:-\w+)*)"), r"the \1"),

    # "(Pasumansky 2014)" → "(the 2014 forum thread)"
    (re.compile(rf"\(\s*{NAME_GROUP}\s+(\d{{4}})\s*\)"), r"(the \1 forum thread)"),

    # "(per Pasumansky)" → "(per the source thread)"
    (re.compile(rf"\(\s*per\s+{NAME_GROUP}\s*\)"), "(per the source thread)"),

    # "(Pasumansky msg N, YYYY-MM-DD)" or "(Pasumansky msg N)" or "(Pasumansky, msg N)" or "(Pasumansky, YYYY-MM-DD, msg N)"
    (re.compile(rf"\(\s*{NAME_GROUP},?\s+msg\s+(\d+)(?:,\s*\d{{4}}-\d{{2}}-\d{{2}})?\s*\)"), r"(msg \1)"),
    (re.compile(rf"\(\s*{NAME_GROUP},\s+(\d{{4}}-\d{{2}}-\d{{2}}),\s+msg\s+(\d+)\s*\)"), r"(msg \2, \1)"),

    # "(Pasumansky msg N, YYYY)" — without final ) match too greedy if multiple, handle inline
    # Done inline below.

    # "(Pasumansky 2018-04-27 + 2021-04-14; some text 2021-04-15)" — inside parens but not just at start
    # Handled by removing the leading "Pasumansky " before the date inside any parenthetical
    (re.compile(rf"\b{NAME_GROUP}\s+(\d{{4}}-\d{{2}}-\d{{2}})"), r"the \1 thread"),

    # "Pasumansky-attested" → "forum-attested"
    (re.compile(rf"\b{NAME_GROUP}-attested\b"), "forum-attested"),

    # "(Author Name) " or "(Author Name." — bare name in parens
    (re.compile(rf"\(\s*{NAME_GROUP}\s*\)([\s.,;])"), r"\1"),

    # "Pasumansky relaying Agisoft Support" → "Agisoft Support"
    (re.compile(rf"\b{NAME_GROUP}\s+relaying\s+Agisoft\s+Support"), "Agisoft Support"),

    # "with multiple Pasumansky posts" / "X scripts" / "X confirmation" — name as modifier
    (re.compile(rf"\bmultiple\s+{NAME_GROUP}\s+posts"), "multiple posts in the source thread"),
    (re.compile(rf"\b{NAME_GROUP}\s+scripts\b"), "the scripts"),
    (re.compile(rf"\b{NAME_GROUP}\s+confirmation\b"), "the confirmation"),
    (re.compile(rf"\b{NAME_GROUP}\s+msgs?\s+(\d+(?:[, ]+\d+)*)"), r"msgs \1"),
    (re.compile(rf"\b{NAME_GROUP}\s+posts\b"), "the posts"),

    # Multi-word: "— Author Name (Agisoft support)," → "— Agisoft support,"
    (re.compile(rf"—\s+(?:Alexey\s+)?Pasumansky\s+\(Agisoft support\),"), "— Agisoft support,"),

    # Multi-word: "— Author Name (community forum user)," → "— a community forum user,"
    (re.compile(rf"—\s+{NAME_GROUP}\s+\(community forum user\),"), "— a community forum user,"),

    # "— X on Y" → "— Y" or "— discussion of Y"
    (re.compile(rf"—\s+{NAME_GROUP}\s+on\s+the\s+(\w+)"), r"— the \1"),
    (re.compile(rf"—\s+{NAME_GROUP}\s+on\s+(\w+)"), r"— discussion of \1"),

    # "Pasumansky on" mid-sentence → "discussion of"
    (re.compile(rf"\b{NAME_GROUP}\s+on\s+the\s+"), "the "),
    (re.compile(rf"\b{NAME_GROUP}\s+on\s+"), "discussion of "),

    # "— X explained / clarified / etc."
    (re.compile(rf"—\s+{NAME_GROUP}\s+(explain|clarif|describ|provid|confirm|recommend|advis|state|sugges|repli|writ|ask|note)e?(s|d)?\s+"), r"— "),

    # "by X" attributions in description
    (re.compile(rf"\bby\s+{NAME_GROUP}\b"), "by the source"),

    # Trailing standalone "(NAME)." or "(NAME);" or "(NAME),"
    (re.compile(rf"\(\s*{NAME_GROUP}\s*\)([.,;])"), r"\1"),

    # "Also the X" or "the X" where X is a username
    (re.compile(rf"\bAlso\s+the\s+{NAME_GROUP}\b"), "Also the source-thread user"),
    (re.compile(rf"\bthe\s+{NAME_GROUP}\b"), "the source-thread user"),

    # Multi-name in parens: "(jetdog6 msg N, Pasumansky msg M)" → "(msgs N and M)"
    (re.compile(rf"\(\s*{NAME_GROUP}\s+msg\s+(\d+),\s+{NAME_GROUP}\s+msg\s+(\d+)\s*\)"), r"(msgs \1 and \2)"),

    # "(NAME, YYYY-MM-DD, msg N)" — inverse order
    (re.compile(rf"\(\s*{NAME_GROUP},\s+(\d{{4}}-\d{{2}}-\d{{2}}),\s+msg\s+(\d+)\s*\)"), r"(\1, msg \2)"),

    # "Yoann's" / "Heinrich's" (already covered by 's pattern but italic versions)
    (re.compile(rf"\*{NAME_GROUP}\*"), "the source-thread user"),

    # Insights-specific patterns:
    # "(NAME, YYYY)" → "(YYYY)"
    (re.compile(rf"\(\s*{NAME_GROUP},\s+(\d{{4}})\s*\)"), r"(\1)"),

    # "(NAME topic=N msg M)" / "(NAME topic=N)"
    (re.compile(rf"\(\s*{NAME_GROUP}\s+topic=(\d+)\s+msg\s+(\d+)\s*\)"), r"(topic=\1 msg \2)"),
    (re.compile(rf"\(\s*{NAME_GROUP}\s+topic=(\d+)\s*\)"), r"(topic=\1)"),

    # "user NAME" / "user X" — keep just "user"
    (re.compile(rf"\buser\s+{NAME_GROUP}\b"), "user"),

    # "from NAME"
    (re.compile(rf"\bfrom\s+{NAME_GROUP}\b"), "from the source thread"),

    # "NAME-stated" / "NAME-cited"
    (re.compile(rf"\b{NAME_GROUP}-(stated|cited)\b"), "forum-attested"),

    # "direct from NAME" (with date)
    (re.compile(rf"\bdirect\s+from\s+{NAME_GROUP}\s+\((\d{{4}}-\d{{2}}-\d{{2}})\)"), r"forum-attested (\1)"),

    # "single NAME" / "a single NAME message"
    (re.compile(rf"\bsingle\s+{NAME_GROUP}\b"), "single source-thread"),

    # Bare action verbs: "NAME shipped", "NAME debugged", "NAME suggested", "NAME wrote"
    (re.compile(rf"\b{NAME_GROUP}\s+(shipped|debugged|suggested|wrote|noted|confirmed|recommended)\b"), r"the source thread \1"),

    # "X's NAME" possessive after another word
    (re.compile(rf"\b(of|by|from|with)\s+{NAME_GROUP}\b"), r"\1 the source"),

    # NAME-only at start of sentence (e.g., "Alexey requested...")
    (re.compile(rf"(?:^|\.\s+){NAME_GROUP}\s+(requested|asked|reports?|stated)\b", re.MULTILINE),
     "the source thread \\1"),

    # "NAME's" generic possessive (catch-all for any leftover)
    (re.compile(rf"\b{NAME_GROUP}'s\b"), "the source thread's"),

    # === Additional aggressive patterns for insights ===

    # "NAME YYYY reported X" — bare name + year in narrative prose
    (re.compile(rf"\b{NAME_GROUP}\s+(\d{{4}})\s+(reported|noted|confirmed|stated|wrote|asked)\b"), r"the \1 thread \2"),

    # "(NAME, t=NNNN msg N, YYYY-MM-DD)" — name in footnote citation
    (re.compile(rf"\(\s*{NAME_GROUP},\s+t=(\d+)\s+msg\s+(\d+),\s+(\d{{4}}-\d{{2}}-\d{{2}})\s*\)"), r"(t=\1 msg \2, \3)"),
    # "(NAME, t=NNNN ...)" simpler form
    (re.compile(rf"\(\s*{NAME_GROUP},\s+t=(\d+)([^)]*)\)"), r"(t=\1\2)"),

    # "NAME-recommended" / "NAME-stated" / "NAME-cited" / "NAME-authored"
    (re.compile(rf"\b{NAME_GROUP}-(recommended|stated|cited|authored|attested|adjusted)\b"), r"forum-\1"),

    # "(NAME-X)" or "[NAME-X]"
    (re.compile(rf"\(\s*{NAME_GROUP}-(\w+)\s*\)"), r"(forum-\1)"),

    # "older NAME reply" → "older reply"
    (re.compile(rf"\bolder\s+{NAME_GROUP}\s+(reply|post|response)\b"), r"older \1"),

    # "NAME reply" / "NAME reply." / "NAME post"
    (re.compile(rf"\b{NAME_GROUP}\s+(reply|post|response|message|thread|script|recipe|pattern|workflow)s?\b(?!\s+is)"), r"the source thread's \1"),

    # "NAME debugged X" / "NAME shipped X" / "NAME directly authored X" / "NAME made X" / "NAME confirmed X"
    (re.compile(rf"\b{NAME_GROUP}\s+(debugged|shipped|suggested|directly authored|wrote|noted|confirmed|recommended|requested|made|asked|cited|reported)\b"),
     r"the source thread's author \1"),

    # "(per NAME in the source thread)"
    (re.compile(rf"\(\s*per\s+{NAME_GROUP}\s+in\s+the\s+source\s+thread\s*\)"), "(per the source thread)"),

    # "(quoted by X from an older NAME reply)" — already covered but tighten
    (re.compile(rf"\bquoted\s+by\s+\w+\s+from\s+an?\s+older\s+{NAME_GROUP}\s+reply\b"), "quoted from an older reply"),

    # "Quoted by NAME"
    (re.compile(rf"\bQuoted\s+by\s+{NAME_GROUP}\b"), "Quoted by a community user"),
    (re.compile(rf"\bquoted\s+by\s+{NAME_GROUP}\b"), "quoted by a community user"),

    # Bare "NAME-" prefix forms
    (re.compile(rf"\b{NAME_GROUP}-"), "forum-"),

    # "by NAME directly" or "directly by NAME"
    (re.compile(rf"\bdirectly\s+by\s+{NAME_GROUP}\b"), "directly by the source"),

    # "the NAME claims" / "the NAME enumeration"
    (re.compile(rf"\bthe\s+{NAME_GROUP}\s+(claims?|enumeration|message|reply|post)\b"), r"the \1"),

    # "NAME claims" → "the source thread's claims"
    (re.compile(rf"\b{NAME_GROUP}\s+claims?\b"), "the source thread's claims"),

    # Final catch: standalone "NAME" still left somewhere — comment-out only if in clear narrative context
    # (handled by manual review)

    # Multi-line continuation: line ends with "(NAME," — the next line continues the citation
    # Match "(NAME," at end of line
    (re.compile(rf"\(\s*{NAME_GROUP},\s*$"), "(forum thread,"),

    # "NAME attestation" / "NAME confirmations"
    (re.compile(rf"\b{NAME_GROUP}\s+attestation"), "forum attestation"),
    (re.compile(rf"\b{NAME_GROUP}\s+confirmations?"), "forum confirmations"),

    # "direct NAME" → "direct forum"
    (re.compile(rf"\bdirect\s+{NAME_GROUP}\b"), "direct forum"),

    # "(multi-post NAME ...)"
    (re.compile(rf"\(\s*multi-post\s+{NAME_GROUP}\s+(\w+)"), r"(multi-post forum \1"),

    # "the canonical NAME explanation"
    (re.compile(rf"\bthe\s+canonical\s+{NAME_GROUP}\s+(\w+)"), r"the canonical \1"),

    # "the NAME forum post"
    (re.compile(rf"\bthe\s+cited\s+{NAME_GROUP}\s+forum\s+post"), "the cited forum post"),

    # "NAME maintained" — "maintained" verb
    (re.compile(rf"\b{NAME_GROUP}\s+maintained\b"), "the source thread's author maintained"),

    # Multi-user-list inside parens like "(NAME 2019, NAME 2020, NAME 2025)"
    (re.compile(rf"\(\s*{NAME_GROUP}\s+(\d{{4}}),\s*{NAME_GROUP}\s+(\d{{4}}),\s*{NAME_GROUP}\s+(\d{{4}})\s*\)"),
     r"(reports spanning \1, \2, \3)"),
    # Two-name list:
    (re.compile(rf"\(\s*{NAME_GROUP}\s+(\d{{4}}),\s*{NAME_GROUP}\s+(\d{{4}})\s*\)"),
     r"(reports in \1 and \2)"),

    # "NAME YYYY: text" (start of bullet item)
    (re.compile(rf"\b{NAME_GROUP}\s+(\d{{4}}):"), r"the \1 thread:"),

    # "NAME YYYY)." or "NAME YYYY," (closing parens with name+year)
    (re.compile(rf"\b{NAME_GROUP}\s+(\d{{4}})\)"), r"\1)"),
    (re.compile(rf"\b{NAME_GROUP}\s+(\d{{4}}),\s+"), r"the \1 thread, "),

    # "the X (NAME confirmations" — match pattern that doesn't close
    (re.compile(rf"\(\s*multi-post\s+{NAME_GROUP}\b"), "(multi-post forum"),

    # Single bare name at start of a sentence (".X. NAME maintained...")
    (re.compile(rf"(\.\s+){NAME_GROUP}\s+(maintained|debugged|noted|stated|confirmed|reported|asked)"),
     r"\1The source thread's author \2"),

    # Bare name + "[possessive form]" — already covered, but with longer hyphenated phrases
    (re.compile(rf"\bthe\s+{NAME_GROUP}\s+(\w+)\s+is\s+\w+"), r"the source thread's \1 is"),

    # "—[NAME]" or "(NAME)" trailing (no possessive)
    (re.compile(rf"\(\s*{NAME_GROUP}\s*\)"), "(forum)"),
]


def is_attribution_line(line: str) -> bool:
    """Citation blockquote attribution — names allowed."""
    s = line.strip()
    if not s.startswith(">"):
        return False
    if re.search(r"[—–-]\s+[A-Za-z][\w\s'.\-()]*,\s*\d{4}", line):
        return True
    if re.search(r"[—–-]\s+[A-Za-z][\w\s'.\-()]*[,.\s]*$", line.rstrip()):
        return True
    return False


def is_table_row(line: str, in_table: bool) -> bool:
    """Reference-features citation table row."""
    return in_table and line.count("|") >= 4


def is_link_label_position(line: str, start: int, end: int) -> bool:
    """Is the matched name inside a [...](url) link label?"""
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


def clean_line(line: str) -> str:
    """Apply name-stripping replacements to one line, preserving link labels."""
    # Find all name positions; replace only outside link labels.
    # Strategy: find each pattern match; if any of its name occurrences fall
    # inside a link label, skip the replacement.

    new_line = line
    # Iterate patterns; for each, find matches and decide whether to apply
    for pat, repl in PATTERNS:
        # Build match list
        out = []
        last = 0
        for m in pat.finditer(new_line):
            # Check whether the match span intersects any link label
            span_text = new_line[m.start():m.end()]
            # Find any name within the span and check link-label state
            name_safe = True
            # Check each name reference inside the matched span
            name_pat = re.compile(rf"\b{NAME_GROUP}\b")
            for nm in name_pat.finditer(span_text):
                nm_start = m.start() + nm.start()
                nm_end = m.start() + nm.end()
                if is_link_label_position(new_line, nm_start, nm_end):
                    name_safe = False
                    break
            if name_safe:
                out.append(new_line[last:m.start()])
                # Use re.sub to apply the replacement on this match (handles backrefs)
                replaced = pat.sub(repl, m.group(0), count=1)
                out.append(replaced)
                last = m.end()
            else:
                # Skip this match — leave as-is
                out.append(new_line[last:m.end()])
                last = m.end()
        out.append(new_line[last:])
        new_line = "".join(out)
    return new_line


def clean_file(path: Path, dry_run: bool = False) -> tuple[int, int]:
    """Returns (lines_changed, total_lines)."""
    lines = path.read_text(encoding="utf-8").splitlines(keepends=False)
    new_lines = []
    in_yaml = False
    in_code_block = False
    in_table = False
    in_html_comment = False
    changed = 0

    for i, line in enumerate(lines):
        original = line

        # Track YAML
        if i == 0 and line.strip() == "---":
            in_yaml = True
            new_lines.append(line)
            continue
        if in_yaml:
            if line.strip() == "---":
                in_yaml = False
            new_lines.append(line)
            continue

        # Track code blocks
        if line.strip().startswith("```"):
            in_code_block = not in_code_block
            new_lines.append(line)
            continue
        if in_code_block:
            new_lines.append(line)
            continue

        # HTML comment block
        if "<!--" in line and "-->" not in line:
            in_html_comment = True
        if in_html_comment:
            if "-->" in line:
                in_html_comment = False
            new_lines.append(line)
            continue
        if "<!--" in line and "-->" in line:
            new_lines.append(line)
            continue

        # Track citation tables
        if "| Date | Version | Author |" in line or "| Date  | Version" in line:
            in_table = True
            new_lines.append(line)
            continue
        if in_table and not line.strip().startswith("|"):
            in_table = False

        if in_table:
            new_lines.append(line)
            continue

        # Skip blockquote attribution lines
        if is_attribution_line(line):
            new_lines.append(line)
            continue

        # Apply cleanup
        cleaned = clean_line(line)
        if cleaned != original:
            changed += 1
        new_lines.append(cleaned)

    if not dry_run and changed > 0:
        new_text = "\n".join(new_lines) + ("\n" if path.read_text(encoding="utf-8").endswith("\n") else "")
        path.write_text(new_text, encoding="utf-8")

    return changed, len(lines)


def main():
    dry_run = "--dry-run" in sys.argv
    args = [a for a in sys.argv[1:] if a != "--dry-run"]
    paths = args or ["docs"]
    targets = []
    for p in paths:
        p = Path(p)
        if p.is_file():
            targets.append(p)
        else:
            targets.extend(sorted(p.rglob("*.md")))

    total_changed = 0
    files_touched = 0
    for path in targets:
        changed, total = clean_file(path, dry_run=dry_run)
        if changed > 0:
            print(f"{'[DRY] ' if dry_run else ''}{path}: {changed} lines changed (of {total})")
            files_touched += 1
            total_changed += changed
    print(f"\n{'(DRY RUN) ' if dry_run else ''}{files_touched} files touched, {total_changed} lines changed")


if __name__ == "__main__":
    main()
