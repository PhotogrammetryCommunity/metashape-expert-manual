#!/usr/bin/env python3
"""Triage harvested forum-index TSVs into a tiered candidate list.

Tiers:
    A  All threads where last_by == "Alexey Pasumansky" or
       "Dmitry Semyonov" (Agisoft staff).
    B  Threads where last_by is one of the named "major non-staff
       contributors" AND views >= MIN_TIER_B_VIEWS.
    C  Other threads with views >= MIN_TIER_C_VIEWS AND replies >=
       MIN_TIER_C_REPLIES (excluding stickies that are pre-release
       announcements).

Usage:
    triage_threads.py corpus/forum/index/parsed/*.tsv \\
        --already-cached corpus/forum/printpage-*.html \\
        --already-covered docs/workflow docs/topics \\
        --output corpus/forum/index/candidates.md
"""
from __future__ import annotations

import argparse
import csv
import re
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

STAFF = {"Alexey Pasumansky", "Dmitry Semyonov"}

# Major non-staff contributors based on frequency analysis of
# last_by across the 6-board harvest.
MAJOR_CONTRIBUTORS = {
    "Paulo", "SAV", "James", "Wishgranter", "JMR", "andyroo",
    "PROBERT1968", "Kiesel", "bigben", "stihl", "olihar", "wojtek",
    "dpitman", "CheeseAndJamSandwich", "RalfH", "Bzuco",
    "bisenberger", "Yoann Courtois", "Infinite", "Steve003",
    "ThomasVD", "JoshuaSkelton",
}

MIN_TIER_B_VIEWS = 1000      # Major contributor threads with low views are skipped
MIN_TIER_C_VIEWS = 5000      # General threshold
MIN_TIER_C_REPLIES = 3       # Filter out single-question dead threads


# Skip pre-release / announcement stickies — they're version-history
# artefacts already covered by reference/version-timeline.
ANNOUNCEMENT_TITLE_RE = re.compile(
    r"(pre-release|build \d|^Agisoft (Metashape|PhotoScan) \d)",
    re.IGNORECASE,
)


def parse_date(s: str) -> datetime | None:
    """Parse 'February 28, 2020, 11:05:37 PM' style date."""
    s = s.strip()
    if not s:
        return None
    try:
        return datetime.strptime(s, "%B %d, %Y, %I:%M:%S %p")
    except ValueError:
        return None


def load_tsv(path: Path) -> list[dict]:
    rows: list[dict] = []
    with path.open(encoding="utf-8", errors="replace") as f:
        for r in csv.DictReader(f, delimiter="\t"):
            r["topic_id"] = int(r["topic_id"])
            r["views"] = int(r["views"])
            r["replies"] = int(r["replies"])
            r["sticky"] = r["sticky"] == "1"
            r["last_dt"] = parse_date(r["last_date"])
            rows.append(r)
    return rows


def discover_already_cached(forum_dir: Path) -> set[int]:
    cached: set[int] = set()
    for p in forum_dir.glob("printpage-*.html"):
        m = re.match(r"printpage-(\d+)\.html", p.name)
        if m:
            cached.add(int(m.group(1)))
    return cached


def discover_already_covered(article_dirs: list[Path]) -> set[int]:
    """Find topic IDs that articles or cards already reference."""
    covered: set[int] = set()
    pattern = re.compile(r"topic=(\d+)")
    for d in article_dirs:
        for p in d.rglob("*.md"):
            text = p.read_text(encoding="utf-8", errors="replace")
            for m in pattern.finditer(text):
                covered.add(int(m.group(1)))
    return covered


def assign_tier(row: dict, pasumansky_topics: set[int] | None = None) -> str | None:
    if row["sticky"] and ANNOUNCEMENT_TITLE_RE.search(row["title"]):
        return None
    # Tier A — staff-touched. Catches both:
    #   (a) Pasumansky as last_by, AND
    #   (b) Pasumansky posted but someone else replied last (e.g.,
    #       a 'thanks' or a follow-up question). The pasumansky_topics
    #       set is built from his showposts crawl and contains his
    #       full thread membership across all boards.
    if pasumansky_topics is not None and row["topic_id"] in pasumansky_topics:
        return "A"
    if row["last_by"] in STAFF:
        return "A"
    if row["last_by"] in MAJOR_CONTRIBUTORS and row["views"] >= MIN_TIER_B_VIEWS:
        return "B"
    if row["views"] >= MIN_TIER_C_VIEWS and row["replies"] >= MIN_TIER_C_REPLIES:
        return "C"
    return None


def load_pasumansky_topics(path: Path) -> set[int]:
    topics: set[int] = set()
    if not path.exists():
        return topics
    with path.open(encoding="utf-8") as f:
        next(f, None)  # skip header
        for line in f:
            tid = line.split("\t", 1)[0].strip()
            if tid.isdigit():
                topics.add(int(tid))
    return topics


def write_candidates_md(
    rows: list[dict],
    cached: set[int],
    covered: set[int],
    pasumansky_topics: set[int],
    out: Path,
    board_label: dict[int, str],
) -> None:
    by_tier: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        tier = assign_tier(r, pasumansky_topics)
        if tier is None:
            continue
        r["tier"] = tier
        r["already_cached"] = r["topic_id"] in cached
        r["already_covered"] = r["topic_id"] in covered
        r["pasumansky_touched"] = r["topic_id"] in pasumansky_topics
        by_tier[tier].append(r)

    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8") as f:
        f.write("# Forum-thread candidates — triage list\n\n")
        f.write(f"Generated by `scripts/triage_threads.py` from a 6-board "
                f"harvest of agisoft.com/forum and a full Pasumansky-"
                f"showposts crawl (u=5).\n\n")
        f.write(f"**Total threads harvested:** {len(rows):,}\n")
        f.write(f"**Pasumansky-touched threads (full showposts crawl):** "
                f"{len(pasumansky_topics):,}\n")
        f.write(f"**Already cached locally:** {len(cached)} threads "
                f"(`corpus/forum/printpage-*.html`)\n")
        f.write(f"**Already cited in articles / cards:** {len(covered)} threads\n\n")

        # Tier counts.
        f.write("## Summary by tier\n\n")
        f.write("| Tier | Count | Filter |\n")
        f.write("|------|-------|--------|\n")
        f.write(f"| **A** — Pasumansky-touched (showposts) ∪ Semyonov last_by | {len(by_tier['A']):,} | regardless of views |\n")
        f.write(f"| **B** — major-contributor last_by + views ≥ {MIN_TIER_B_VIEWS} | {len(by_tier['B']):,} | named contributors only |\n")
        f.write(f"| **C** — other threads with views ≥ {MIN_TIER_C_VIEWS} and replies ≥ {MIN_TIER_C_REPLIES} | {len(by_tier['C']):,} | broad-interest fallback |\n\n")
        f.write(f"Major non-staff contributors counted in Tier B: "
                + ", ".join(f"`{c}`" for c in sorted(MAJOR_CONTRIBUTORS))
                + ".\n\n")

        # Top of each tier — sorted by views desc.
        for tier in ("A", "B", "C"):
            tier_rows = sorted(by_tier[tier], key=lambda r: -r["views"])
            f.write(f"## Tier {tier} — top 100 by views\n\n")
            f.write("| board | topic | views | replies | last_by | last_date | status | title |\n")
            f.write("|-------|-------|-------|---------|---------|-----------|--------|-------|\n")
            for r in tier_rows[:100]:
                status = []
                if r["already_cached"]:
                    status.append("cached")
                if r["already_covered"]:
                    status.append("**covered**")
                if tier == "A" and r.get("pasumansky_touched") and r["last_by"] not in STAFF:
                    status.append("alex+other-last")
                board = board_label.get(int(r["board"]), str(r["board"]))
                f.write(
                    f"| {board} "
                    f"| [{r['topic_id']}](https://www.agisoft.com/forum/index.php?topic={r['topic_id']}.0) "
                    f"| {r['views']:,} "
                    f"| {r['replies']} "
                    f"| {r['last_by']} "
                    f"| {r['last_date'][:12] if r['last_date'] else '?':<12} "
                    f"| {' '.join(status) or '—'} "
                    f"| {r['title'].replace('|', '⏐')} |\n"
                )
            if len(tier_rows) > 100:
                f.write(f"\n*({len(tier_rows) - 100:,} more in this tier; "
                        f"see `corpus/forum/index/candidates-tier-{tier}.tsv`)*\n\n")
            else:
                f.write("\n")

        f.write("## Next steps\n\n")
        f.write("- Cluster Tier A by topic keyword (in title) to identify "
                "coherent themes for the next batch.\n")
        f.write("- The `alex+other-last` status flags Tier A rows that the "
                "old (last_by-only) heuristic would have missed — "
                "Pasumansky posted but someone replied 'thanks' / asked "
                "a follow-up afterwards.\n")
        f.write("- Tier B is supplemental — cite when a major contributor "
                "has a particularly clear answer; don't fetch all "
                "blindly.\n")
        f.write("- Tier C is a fallback — high-interest user discussion "
                "not necessarily resolved by staff. Useful for "
                "diagnostic-pattern articles.\n")
        f.write("- Mark `**covered**` rows as already-resolved in this "
                "manual; re-fetch only if a batch brief specifically "
                "extends an existing article.\n")

    # Also dump full per-tier TSVs for downstream tooling.
    for tier in ("A", "B", "C"):
        tsv_out = out.parent / f"candidates-tier-{tier}.tsv"
        with tsv_out.open("w", encoding="utf-8") as f:
            f.write("board\ttopic_id\tviews\treplies\tlast_by\tlast_date\tcached\tcovered\talex_touched\ttitle\n")
            for r in sorted(by_tier[tier], key=lambda r: -r["views"]):
                f.write(
                    f"{r['board']}\t{r['topic_id']}\t{r['views']}\t"
                    f"{r['replies']}\t{r['last_by']}\t{r['last_date']}\t"
                    f"{int(r['already_cached'])}\t{int(r['already_covered'])}\t"
                    f"{int(r.get('pasumansky_touched', False))}\t{r['title']}\n"
                )


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("tsvs", type=Path, nargs="+",
                    help="Per-board TSVs from parse_board_index.py")
    ap.add_argument("--cached-dir", type=Path,
                    default=Path("corpus/forum"),
                    help="Directory of cached printpage-*.html files")
    ap.add_argument("--covered-dirs", type=Path, nargs="+",
                    default=[Path("docs"), Path("insights")],
                    help="Directories where existing articles / cards live")
    ap.add_argument("--output", type=Path,
                    default=Path("corpus/forum/index/candidates.md"))
    ap.add_argument("--pasumansky-topics", type=Path,
                    default=Path("corpus/forum/index/parsed/pasumansky-touched-topics.tsv"),
                    help="TSV of topic IDs Pasumansky has posted in "
                         "(from parse_user_posts.py --unique-topics).")
    args = ap.parse_args()

    BOARD_LABEL = {
        7: "general", 8: "bugs", 11: "features",
        13: "calib", 17: "py-api", 18: "face-body",
    }

    rows: list[dict] = []
    for tsv in args.tsvs:
        m = re.search(r"board-(\d+)", tsv.name)
        if not m:
            continue
        board_id = int(m.group(1))
        for r in load_tsv(tsv):
            r["board"] = board_id
            rows.append(r)

    cached = discover_already_cached(args.cached_dir)
    covered = discover_already_covered(args.covered_dirs)
    pasumansky_topics = load_pasumansky_topics(args.pasumansky_topics)

    write_candidates_md(rows, cached, covered, pasumansky_topics, args.output, BOARD_LABEL)
    print(f"wrote {args.output}")
    print(f"  ({len(pasumansky_topics):,} Pasumansky-touched topics loaded "
          f"from {args.pasumansky_topics})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
