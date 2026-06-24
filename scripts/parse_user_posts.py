#!/usr/bin/env python3
"""Parse SMF showposts pages into (topic_id, msg_id, board_id, post_date) rows.

Each page contains up to 15 post entries; each entry links to the
specific message inside its thread. Multiple posts can be in the same
thread, so the unique topic_id set is typically <= page count × 15.

Usage:
    parse_user_posts.py corpus/forum/user-posts/u-5/*.html

Output: TSV on stdout with columns:
    topic_id  msg_id  board_id  post_date  post_subject
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

# Each post is bracketed by <div class="content"> ... </div> with a
# header that looks like:
#   <a href=".../forum/index.php?board=17.0">Python and Java API</a> /
#   <a href=".../forum/index.php?topic=14276.msg63571#msg63571">SUBJECT</a>
# followed by date metadata.

POST_RE = re.compile(
    r'<a href="https?://www\.agisoft\.com/forum/index\.php\?board=(\d+)\.\d+">[^<]+</a>\s*/?'
    r'\s*<a href="https?://www\.agisoft\.com/forum/index\.php\?topic=(\d+)\.msg(\d+)#msg\d+">'
    r'([^<]+)</a>',
    re.DOTALL,
)
DATE_RE = re.compile(r'on:\s*([A-Z][a-z]+ \d+, \d+, \d+:\d+:\d+ [AP]M)')


def parse(html: str):
    rows = []
    # Walk through and pair (board, topic, msg, subject) headers with the
    # next « on: DATE » that appears after each header.
    pos = 0
    for m in POST_RE.finditer(html):
        board = int(m.group(1))
        topic = int(m.group(2))
        msg = int(m.group(3))
        subject = m.group(4).strip()
        # Find the date that appears within ~500 chars of this match.
        nearby = html[m.end(): m.end() + 500]
        date_m = DATE_RE.search(nearby)
        date = date_m.group(1) if date_m else ""
        rows.append((topic, msg, board, date, subject))
    return rows


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("paths", type=Path, nargs="+")
    ap.add_argument("--unique-topics", action="store_true",
                    help="Output one row per unique topic_id (earliest "
                         "post per topic).")
    args = ap.parse_args()

    all_rows = []
    for p in sorted(args.paths):
        html = p.read_text(encoding="utf-8", errors="replace")
        all_rows.extend(parse(html))

    if args.unique_topics:
        seen = {}
        for topic, msg, board, date, subject in all_rows:
            if topic not in seen or msg < seen[topic][0]:
                seen[topic] = (msg, board, date, subject)
        print("topic_id\tearliest_msg_id\tboard_id\tdate\tsubject")
        for topic, (msg, board, date, subject) in sorted(seen.items()):
            print(f"{topic}\t{msg}\t{board}\t{date}\t{subject}")
    else:
        print("topic_id\tmsg_id\tboard_id\tdate\tsubject")
        for topic, msg, board, date, subject in all_rows:
            print(f"{topic}\t{msg}\t{board}\t{date}\t{subject}")

    print(f"# total post rows: {len(all_rows)}", file=sys.stderr)
    if args.unique_topics:
        unique = len({r[0] for r in all_rows})
        print(f"# unique topics : {unique}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
