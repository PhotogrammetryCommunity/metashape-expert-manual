#!/usr/bin/env python3
r"""Add Wikipedia-style archived-companion links after markdown links that
target a cited Agisoft KB/forum URL with a LIVE, content-verified Wayback
snapshot. Links point at the SPECIFIC verified snapshot (immutable), and the
label carries that snapshot's capture date: [archived YYYY-MM-DD](url).

Two forms, idempotent:
  * link wrapped in parens  (\[label](URL))          -> (\[label](URL), [archived DATE](WB))   [flat]
  * bare link               ...](URL)                -> ...](URL) ([archived DATE](WB))

Mapping: scripts/data/archive-wayback.tsv (status LIVE, non-empty wayback url).

Usage:
  python scripts/add_archive_links.py --file docs/x.md   # pilot
  python scripts/add_archive_links.py --all              # whole manual
  python scripts/add_archive_links.py --all --check      # report only (no write)
"""
import argparse, re, sys
from pathlib import Path

MAP=Path("scripts/data/archive-wayback.tsv")
TS=re.compile(r"/web/(\d{8})\d*/")
def load_map():
    m={}
    for ln in MAP.read_text().splitlines()[1:]:
        p=ln.split("\t")
        if len(p)>=4 and p[3]=="LIVE" and p[2].startswith("http"):
            ts=TS.search(p[2]); date=f"{ts.group(1)[:4]}-{ts.group(1)[4:6]}-{ts.group(1)[6:8]}" if ts else ""
            m[p[0]]=(p[2],date)
    return m

AG=r'https://(?:www\.agisoft\.com/forum|agisoft\.freshdesk\.com)[^)\s]+'
def rewrite(text, mp, stats):
    # Pass 1: parenthesis-wrapped single link -> flat form
    def wrapped(m):
        label,url=m.group(1),m.group(2)
        if url not in mp: stats["unmapped"]+=1; return m.group(0)
        wb,date=mp[url]
        stats["added"]+=1
        return f"([{label}]({url}), [archived {date}]({wb}))"
    text=re.sub(r'\(\[([^\]]*)\]\((%s)\)\)'%AG, wrapped, text)
    # Pass 2: remaining bare links -> append companion (skip if already archived-followed)
    def bare(m):
        url=m.group(1); end=m.end()
        tail=text[end:end+14]
        if url not in mp: stats["unmapped"]+=1; return m.group(0)
        ls=tail.lstrip()
        if ls.startswith("([archived") or ls.startswith(", [archived"): stats["already"]+=1; return m.group(0)
        wb,date=mp[url]; stats["added"]+=1
        return f'{m.group(0)} ([archived {date}]({wb}))'
    text=re.sub(r'\]\((%s)\)'%AG, bare, text)
    return text

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--file"); ap.add_argument("--all",action="store_true"); ap.add_argument("--check",action="store_true")
    a=ap.parse_args()
    mp=load_map()
    # Generic root/landing links are references to the sites themselves,
    # not citations of specific content — they are never archived.
    ALLOW_UNARCHIVED = {
        "https://www.agisoft.com/forum/",
        "https://agisoft.freshdesk.com/support/solutions",
    }
    files=[Path(a.file)] if a.file else sorted(Path("docs").rglob("*.md"))
    st=dict(added=0,already=0,unmapped=0,files=0)
    for f in files:
        if f.name=="changelog.md": continue
        t=f.read_text(); nt=rewrite(t,mp,st)
        if nt!=t:
            st["files"]+=1
            if not a.check: f.write_text(nt)
    print(f"mapped-live urls: {len(mp)}")
    print(f"files changed: {st['files']} | added: {st['added']} | already: {st['already']} | unmapped-skipped: {st['unmapped']}")
    if a.check:
        linkre=re.compile(r'\]\((%s)\)'%AG)
        gaps=set()
        for f in files:
            if f.name=="changelog.md": continue
            for m in linkre.finditer(f.read_text()):
                u=m.group(1)
                if u not in mp and u not in ALLOW_UNARCHIVED:
                    gaps.add(u)
        if st["files"]>0:
            print("STALE: some forum/KB links are missing an [archived ...] companion.")
            print("  run: python scripts/add_archive_links.py --all")
            sys.exit(1)
        if gaps:
            print(f"MISSING ARCHIVE ({len(gaps)}): cited forum/KB URLs with no verified Wayback snapshot:")
            for u in sorted(gaps): print("   ",u)
            print("  archive them (Wayback Save Page Now), add rows to scripts/data/archive-wayback.tsv, re-run --all")
            sys.exit(1)
        print("OK: every cited forum/KB link has an archived companion.")
if __name__=="__main__": main()
