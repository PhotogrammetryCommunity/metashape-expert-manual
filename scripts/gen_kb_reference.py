#!/usr/bin/env python3
"""Regenerate docs/reference/agisoft-knowledge-base.md.

Each article line carries a 1-3 sentence summary, hand-written from each
article's full body and stored in scripts/data/kb_summaries.tsv. The article
inventory (folder, modified date, title, URL) is in scripts/data/kb_master.tsv.
Both are tracked, so the page regenerates from a fresh clone.

For any article missing a summary, falls back to a trimmed extract of the
article's own intro (og:description) read from the gitignored crawl cache
corpus/freshdesk/articles/<id>.html — used only if that cache is present and a
summary is absent (which is not the case for the current 183 articles).

Run: ./.venv/bin/python scripts/gen_kb_reference.py
"""
import csv, html, re
from collections import defaultdict
from datetime import date
from pathlib import Path

DATA = Path("scripts/data")          # tracked inputs (regenerate from a fresh clone)
FD = Path("corpus/freshdesk")        # optional gitignored crawl cache (intro fallback only)
ROWS = list(csv.DictReader(open(DATA / "kb_master.tsv", encoding="utf-8"), delimiter="\t"))
SUM = {}
sp = DATA / "kb_summaries.tsv"
if sp.exists():
    SUM = {r["id"]: r["summary"].strip() for r in
           csv.DictReader(open(sp, encoding="utf-8"), delimiter="\t") if r["summary"].strip()}

def intro_fallback(aid):
    p = FD / "articles" / f"{aid}.html"
    if not p.exists():
        return ""
    h = p.read_text(encoding="utf-8", errors="ignore")
    m = re.search(r'property="og:description"\s+content="([^"]*)"', h)
    s = re.sub(r"\s+", " ", html.unescape(m.group(1) if m else "")).strip()
    s = re.split(r"\bThis article (?:describes|covers|explains) the following\b", s, flags=re.I)[0].strip()
    out = ""
    for sent in re.split(r'(?<=[.!?])\s+', s):
        if not re.search(r'[.!?]$', sent) or (out and len(out) + len(sent) > 260):
            break
        out = (out + " " + sent).strip()
        if out.count(".") >= 2 and len(out) >= 90:
            break
    return out or (re.sub(r"\s+\S*$", "", s[:200]).strip() + "…" if s else "")

def summary(aid):
    return SUM.get(aid) or intro_fallback(aid)

RANK = {f: 2 for f in ["License purchase", "Licensing terms", "Node-locked license activation",
       "(Metashape 2.x) Floating license activation", "(Metashape 1.x) Floating license activation",
       "Regarding activation server issues"]}
RANK.update({f: 3 for f in ["Agisoft Cloud", "Agisoft Viewer", "Other languages"]})
RANK.update({f: 1 for f in ["Agisoft Metashape 2.3.x release", "Agisoft Metashape 2.2.x release",
       "Agisoft Metashape 2.1 release"]})

by = defaultdict(list)
for r in ROWS:
    by[r["folder"]].append(r)
folders = sorted(by, key=lambda f: (RANK.get(f, 0), f))

done = sum(1 for r in ROWS if r["id"] in SUM)
out = ["# Agisoft Knowledge Base (Freshdesk) — article index\n",
       "The [Agisoft Knowledge Base](https://agisoft.freshdesk.com/support/solutions) "
       "is Agisoft's official support library: tutorials, troubleshooting notes, "
       "licensing/activation guides, and feature explanations. This manual is a "
       "community *expert overlay* on top of it — where the Knowledge Base already "
       "explains a topic well, our articles link here rather than duplicating it.\n",
       f"This index lists all **{len(ROWS)} articles** across **{len(folders)} folders**, "
       "captured on " + date.today().isoformat() + ". The date shown is each article's "
       "*Modified on* date; each summary describes what the article covers.\n",
       "> The Knowledge Base is the property of Agisoft LLC. Only titles, dates, summaries, "
       "and links are reproduced here, for navigation.\n"]
for f in folders:
    out.append(f"## {html.unescape(f)}\n")
    for r in sorted(by[f], key=lambda r: html.unescape(r["title"]).lower()):
        # Titles are reproduced VERBATIM from the Agisoft KB (only HTML
        # entities are unescaped, and []->() so Markdown links don't break).
        # Some are cramped or quirky (e.g. "Orthomosaic&DEM",
        # "processing(SenseFly eBee)"); do NOT "fix" them — link text in
        # docs/ is matched against these exact titles, so edits break that.
        title = html.unescape(r["title"]).replace("[", "(").replace("]", ")")
        s = summary(r["id"])
        out.append(f"- [{title}]({r['url']}) — *modified {r['date_iso'] or 'date unknown'}*"
                   + (f"  \n  {s}" if s else ""))
    out.append("")
Path("docs/reference/agisoft-knowledge-base.md").write_text("\n".join(out) + "\n", encoding="utf-8")
print(f"regenerated: {done}/{len(ROWS)} real summaries, rest intro-fallback")
