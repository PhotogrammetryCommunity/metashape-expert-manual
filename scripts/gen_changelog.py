#!/usr/bin/env python3
"""Generate the *list* of "What's new" entries from git history, while
preserving the hand-written one-line description of each entry.

Division of labour (by project decision):
- **Generated:** the dated list of which articles were created / updated,
  grouped by month, newest first, linked by title. This comes from git.
- **Hand-written:** the short sentence describing *what* changed in each
  entry. The generator never writes these; it copies forward whatever a
  human has already put after an entry and leaves new entries
  description-less for a human to fill in.

So a normal edit cycle is: make a content change, run this script to add
the new entry to the list, then hand-write the sentence after it. Running
the script again keeps your sentence.

Usage:
    ./.venv/bin/python scripts/gen_changelog.py          # rewrite the page
    ./.venv/bin/python scripts/gen_changelog.py --check   # fail if the LIST is stale

Entry line format (the sentence is everything after the em dash):
    - [Article title](../path/to/article.md) — hand-written sentence.
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DOCS = REPO_ROOT / "docs"
OUTPUT = DOCS / "about" / "changelog.md"

# Lists longer than this collapse into a <details> block (keeps the
# one-time initial-import month from dominating the page).
COLLAPSE_THRESHOLD = 12

MONTHS = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
]


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=REPO_ROOT, check=True,
        capture_output=True, text=True,
    ).stdout


def _is_tracked(path: str) -> bool:
    if not path.startswith("docs/") or not path.endswith(".md"):
        return False
    name = path.rsplit("/", 1)[-1]
    return name != "index.md" and path != "docs/about/changelog.md"


def _title_of(path: str) -> str:
    fp = REPO_ROOT / path
    if fp.exists():
        text = fp.read_text(encoding="utf-8", errors="replace")
        if text.startswith("---"):
            end = text.find("\n---", 3)
            block = text[3:end] if end != -1 else text[3:]
            m = re.search(r"^title:\s*(.+?)\s*$", block, re.MULTILINE)
            if m:
                return m.group(1).strip().strip('"').strip("'")
    stem = path.rsplit("/", 1)[-1][:-3]
    return stem.replace("-", " ").replace("_", " ").capitalize()


def _rel_link(path: str) -> str:
    return "../" + path[len("docs/"):]


def _path_from_link(rel: str) -> str:
    return "docs/" + rel[len("../"):] if rel.startswith("../") else rel


def collect() -> dict[str, dict[str, set[str]]]:
    """{month_key: {"new": {paths}, "updated": {paths}}} from git history."""
    log = _git(
        "log", "--reverse", "--no-merges", "-M",
        "--name-status", "--date=short", "--pretty=format:\x01%ad",
        "--", "docs/",
    )
    seen: set[str] = set()
    by_month: dict[str, dict[str, set[str]]] = defaultdict(
        lambda: {"new": set(), "updated": set()}
    )
    cur = ""
    for line in log.splitlines():
        if line.startswith("\x01"):
            cur = line[1:].strip()
            continue
        if not line.strip() or not cur:
            continue
        parts = line.split("\t")
        status, path = parts[0], parts[-1]      # rename -> new path
        if not _is_tracked(path):
            continue
        month = cur[:7]
        if status.startswith("D"):
            seen.discard(path)
            continue
        if path not in seen:
            seen.add(path)
            by_month[month]["new"].add(path)
        elif path not in by_month[month]["new"]:
            by_month[month]["updated"].add(path)
    return by_month


def parse_sentences(text: str) -> dict[tuple[str, str], str]:
    """Recover hand-written sentences from an existing page.

    Keyed by (month_key, article_path). A sentence is whatever follows the
    ' — ' on an entry line (works for both plain and indented/collapsed
    bullets).
    """
    preserved: dict[tuple[str, str], str] = {}
    month_key: str | None = None
    for raw in text.splitlines():
        line = raw.strip()
        mh = re.match(r"^##\s+([A-Za-z]+)\s+(\d{4})\s*$", line)
        if mh and mh.group(1) in MONTHS:
            month_key = f"{mh.group(2)}-{MONTHS.index(mh.group(1)) + 1:02d}"
            continue
        bm = re.match(r"^-\s+\[[^\]]*\]\((\.\./[^)]+)\)(?:\s+—\s+(.*))?$", line)
        if bm and month_key:
            sentence = (bm.group(2) or "").strip()
            if sentence:
                preserved[(month_key, _path_from_link(bm.group(1)))] = sentence
    return preserved


def _render_list(month_key: str, label: str, paths: set[str],
                 preserved: dict[tuple[str, str], str]) -> list[str]:
    if not paths:
        return []
    rows = sorted(
        ((_title_of(p), _rel_link(p), preserved.get((month_key, p), ""))
         for p in paths),
        key=lambda t: t[0].lower(),
    )
    bullets = []
    for title, link, sentence in rows:
        line = f"- [{title}]({link})"
        if sentence:
            line += f" — {sentence}"
        bullets.append(line)
    if len(bullets) > COLLAPSE_THRESHOLD:
        block = [f'??? note "{label} — {len(bullets)} articles"', ""]
        block += [f"    {b}" for b in bullets]
        block += [""]
        return block
    return [f"**{label}**", "", *bullets, ""]


def _fmt_month(month_key: str) -> str:
    y, m = month_key.split("-")
    return f"{MONTHS[int(m) - 1]} {y}"


def render(by_month: dict[str, dict[str, set[str]]],
           preserved: dict[tuple[str, str], str]) -> str:
    lines = [
        "---",
        "title: What's new",
        "---",
        "",
        "# What's new",
        "",
        "A reader-facing history of changes to the manual, newest first.",
        "The list of entries is generated from the manual's revision",
        "history (`scripts/gen_changelog.py`); the one-line description",
        "after each entry is written by hand and preserved when the list",
        "is regenerated.",
        "",
    ]
    for month_key in sorted(by_month, reverse=True):
        b = by_month[month_key]
        section = _render_list(month_key, "New articles", b["new"], preserved)
        section += _render_list(month_key, "Updated", b["updated"], preserved)
        if not section:
            continue
        lines.append(f"## {_fmt_month(month_key)}")
        lines.append("")
        lines += section
    out = "\n".join(lines).rstrip() + "\n"
    return re.sub(r"\n{3,}", "\n\n", out)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true",
                    help="exit non-zero if the entry LIST is stale")
    args = ap.parse_args()

    existing = OUTPUT.read_text(encoding="utf-8") if OUTPUT.exists() else ""
    preserved = parse_sentences(existing)
    content = render(collect(), preserved)

    if args.check:
        if existing != content:
            print("changelog list is stale — run scripts/gen_changelog.py",
                  file=sys.stderr)
            return 1
        print("changelog list is up to date")
        return 0

    OUTPUT.write_text(content, encoding="utf-8")
    print(f"wrote {OUTPUT.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
