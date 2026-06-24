#!/usr/bin/env python3
"""Parse an SMF 2.x board index page (Agisoft forum) into structured rows.

Extracts: topic_id, title, started_by, replies, views, last_post_date,
last_post_by, sticky_flag.

Usage:
    parse_board_index.py path/to/board.html
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

# Each thread row is bracketed by <tr>...</tr> inside the threads <table>.
# Order of cells: icon1, icon2, subject, stats, lastpost.

ROW_RE = re.compile(r"<tr>\s*<td class=\"icon1 windowbg\">.+?</tr>", re.DOTALL)
TOPIC_RE = re.compile(
    r'<a href="https://www\.agisoft\.com/forum/index\.php\?topic=(\d+)\.0">([^<]+)</a>'
)
STARTED_RE = re.compile(
    r'Started by\s*<a [^>]*?title="View the profile of ([^"]+)"[^>]*>'
)
STATS_RE = re.compile(r"(\d+) Replies\s*<br />\s*(\d+) Views", re.DOTALL)
LASTPOST_DATE_RE = re.compile(
    r'<img src="[^"]*last_post\.gif"[^>]*/></a>\s*([A-Z][a-z]+ \d+, \d+, \d+:\d+:\d+ [AP]M)<br />\s*by <a [^>]*>([^<]+)</a>'
)
STICKY_RE = re.compile(r'(stick|sticky_post|veryhot_post)\.gif')


def parse(html: str) -> list[dict]:
    rows: list[dict] = []
    for m in ROW_RE.finditer(html):
        row_html = m.group(0)
        topic_m = TOPIC_RE.search(row_html)
        if not topic_m:
            continue
        topic_id = int(topic_m.group(1))
        title = topic_m.group(2).strip()
        started_m = STARTED_RE.search(row_html)
        started_by = started_m.group(1) if started_m else ""
        stats_m = STATS_RE.search(row_html)
        replies = int(stats_m.group(1)) if stats_m else -1
        views = int(stats_m.group(2)) if stats_m else -1
        lp_m = LASTPOST_DATE_RE.search(row_html)
        last_date = lp_m.group(1) if lp_m else ""
        last_by = lp_m.group(2) if lp_m else ""
        sticky = bool(STICKY_RE.search(row_html))
        rows.append({
            "topic_id": topic_id,
            "title": title,
            "started_by": started_by,
            "replies": replies,
            "views": views,
            "last_date": last_date,
            "last_by": last_by,
            "sticky": sticky,
        })
    return rows


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("html_path", type=Path)
    ap.add_argument("--format", choices=("table", "tsv"), default="table")
    args = ap.parse_args()

    html = args.html_path.read_text(encoding="utf-8", errors="replace")
    rows = parse(html)

    if args.format == "tsv":
        print("topic_id\tviews\treplies\tstarted_by\tlast_by\tlast_date\tsticky\ttitle")
        for r in rows:
            print(
                f"{r['topic_id']}\t{r['views']}\t{r['replies']}\t"
                f"{r['started_by']}\t{r['last_by']}\t{r['last_date']}\t"
                f"{int(r['sticky'])}\t{r['title']}"
            )
    else:
        print(f"# {len(rows)} thread row(s) parsed from {args.html_path}")
        for r in rows:
            sticky = "★" if r["sticky"] else " "
            print(
                f"{sticky} t={r['topic_id']:>5}  v={r['views']:>7}  r={r['replies']:>4}  "
                f"by={r['started_by']:<25.25s}  last={r['last_date'][:12]:<12}  "
                f"{r['title'][:70]}"
            )
    return 0


if __name__ == "__main__":
    sys.exit(main())
