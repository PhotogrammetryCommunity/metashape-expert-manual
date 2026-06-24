#!/usr/bin/env python3
"""Build the master per-thread table with auto-relevance scores.

Output:
    corpus/forum/index/threads.tsv

Columns:
    topic_id, board_id, title, views, replies, last_by, last_date,
    pasumansky_touched, pasumansky_post_count,
    cached, covered,
    processed,
    auto_relevance, manual_relevance, relevance_basis,
    topic_cluster, notes, intended_article

Run after harvest + showposts crawl; rerun after each batch to refresh
the `covered` and `cached` columns.
"""
from __future__ import annotations

import csv
import re
from collections import Counter
from pathlib import Path

CORPUS = Path("corpus/forum")
INDEX = CORPUS / "index" / "parsed"
OUT_DIR = CORPUS / "index"
OUT = OUT_DIR / "threads.tsv"

PASUMANSKY_TOPICS_TSV = INDEX / "pasumansky-touched-topics.tsv"
PASUMANSKY_USER_POSTS = CORPUS / "user-posts" / "u-5"
PRINTPAGE_GLOB = "printpage-*.html"
ARTICLE_DIRS = [Path("docs"), Path("insights")]

STAFF = {"Alexey Pasumansky", "Dmitry Semyonov"}
MAJOR_CONTRIBUTORS = {
    "Paulo", "SAV", "James", "Wishgranter", "JMR", "andyroo",
    "PROBERT1968", "Kiesel", "bigben", "stihl", "olihar", "wojtek",
    "dpitman", "CheeseAndJamSandwich", "RalfH", "Bzuco",
    "bisenberger", "Yoann Courtois", "Infinite", "Steve003",
    "ThomasVD",
}

ANNOUNCEMENT_RE = re.compile(
    r"(pre-release|build \d|^Agisoft (Metashape|PhotoScan) \d)",
    re.IGNORECASE,
)
SOLVED_RE = re.compile(r"\[(SOLVED|RESOLVED|FIXED)\]", re.IGNORECASE)


# Topic-cluster keyword rules — order matters (first match wins).
CLUSTER_RULES: list[tuple[str, re.Pattern]] = [
    ("calibration",     re.compile(r"calib|distort|fisheye|principal|focal|lens|sensor", re.I)),
    ("alignment",       re.compile(r"align|match\s*photos|tie\s*point|chunk\s*align", re.I)),
    ("orthomosaic",     re.compile(r"ortho", re.I)),
    ("dem",             re.compile(r"\bDEM\b|elevation", re.I)),
    ("mesh",            re.compile(r"\bmesh\b|model\b|hole|topology", re.I)),
    ("texture",         re.compile(r"texture", re.I)),
    ("point-cloud",     re.compile(r"point\s*cloud|dense\s*cloud|tie\s*points|sparse", re.I)),
    ("depth-map",       re.compile(r"depth\s*map", re.I)),
    ("masks",           re.compile(r"mask", re.I)),
    ("markers-gcps",    re.compile(r"marker|gcp|control\s*point", re.I)),
    ("chunks-merging",  re.compile(r"chunk|merge", re.I)),
    ("python-api",      re.compile(r"python|script|api|metashape\.", re.I)),
    ("performance",     re.compile(r"gpu|cuda|memory|performance|crash|hang|stuck|bench", re.I)),
    ("export-import",   re.compile(r"export|import|\.xml|\.fbx|\.obj|\.las", re.I)),
    ("multispectral",   re.compile(r"multispectr|reflectance|micasense|sentera|altum|RedEdge", re.I)),
    ("rolling-shutter", re.compile(r"rolling\s*shutter", re.I)),
    ("rig-multicamera", re.compile(r"\brig\b|stereo|multi.?camera|multiplane|cubemap", re.I)),
    ("laser-scan",      re.compile(r"laser|TLS|riegl|leica", re.I)),
    ("license-install", re.compile(r"licen[sc]e|install|activation|trial", re.I)),
    ("misc",            re.compile(r".*")),  # catchall
]


def detect_cluster(title: str) -> str:
    for name, pattern in CLUSTER_RULES:
        if pattern.search(title):
            return name
    return "misc"


def load_pasumansky_post_counts() -> dict[int, int]:
    """Count how many distinct posts Pasumansky made per thread."""
    counts: Counter[int] = Counter()
    if not PASUMANSKY_USER_POSTS.exists():
        # Fall back to topic membership only (1 per thread).
        if PASUMANSKY_TOPICS_TSV.exists():
            with PASUMANSKY_TOPICS_TSV.open() as f:
                next(f, None)
                for line in f:
                    tid = line.split("\t", 1)[0].strip()
                    if tid.isdigit():
                        counts[int(tid)] = 1
        return dict(counts)

    # Use the parser to get one row per post (not deduplicated by topic).
    import sys
    sys.path.insert(0, "scripts")
    from parse_user_posts import parse  # type: ignore

    for p in sorted(PASUMANSKY_USER_POSTS.glob("p*.html")):
        html = p.read_text(encoding="utf-8", errors="replace")
        for topic_id, _msg, _board, _date, _subj in parse(html):
            counts[topic_id] += 1
    return dict(counts)


def load_cached_topic_ids() -> set[int]:
    cached: set[int] = set()
    for p in CORPUS.glob(PRINTPAGE_GLOB):
        m = re.match(r"printpage-(\d+)\.html", p.name)
        if m:
            cached.add(int(m.group(1)))
    return cached


def load_covered_topic_ids() -> set[int]:
    covered: set[int] = set()
    pat = re.compile(r"topic=(\d+)")
    for d in ARTICLE_DIRS:
        if not d.exists():
            continue
        for p in d.rglob("*.md"):
            text = p.read_text(encoding="utf-8", errors="replace")
            for m in pat.finditer(text):
                covered.add(int(m.group(1)))
    return covered


def auto_score(row: dict, alex_count: int) -> tuple[int, str]:
    """Return (score, basis) where score is in [0, 10] from metadata signals.

    The score is unsaturated (max 10); content-derived signals can refine
    after Phase C bulk-fetch lands the printpages.
    """
    score = 0
    basis = []

    if alex_count > 0:
        score += 3
        basis.append(f"alex+{alex_count}")
    if row["last_by"] in STAFF:
        score += 1
        basis.append("staff-last")
    elif row["last_by"] in MAJOR_CONTRIBUTORS:
        score += 1
        basis.append(f"contrib:{row['last_by']}")

    views = row["views"]
    if views >= 100_000:
        score += 2
        basis.append(f"views:{views // 1000}k+")
    elif views >= 30_000:
        score += 1
        basis.append(f"views:{views // 1000}k")

    if row["replies"] >= 10:
        score += 1
        basis.append(f"replies:{row['replies']}")

    if row["sticky"] and ANNOUNCEMENT_RE.search(row["title"]):
        score = 0
        basis = ["sticky-announcement"]
    elif SOLVED_RE.search(row["title"]):
        score -= 1
        basis.append("[SOLVED]-tag")

    score = max(0, min(10, score))
    return score, ";".join(basis) if basis else "no-signal"


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    cached = load_cached_topic_ids()
    covered = load_covered_topic_ids()
    pas_counts = load_pasumansky_post_counts()

    rows: list[dict] = []
    for tsv in sorted(INDEX.glob("board-*.tsv")):
        m = re.search(r"board-(\d+)", tsv.name)
        if not m:
            continue
        board_id = int(m.group(1))
        with tsv.open(encoding="utf-8", errors="replace") as f:
            for r in csv.DictReader(f, delimiter="\t"):
                tid = int(r["topic_id"])
                row = {
                    "topic_id": tid,
                    "board_id": board_id,
                    "title": r["title"],
                    "views": int(r["views"]),
                    "replies": int(r["replies"]),
                    "last_by": r["last_by"],
                    "last_date": r["last_date"],
                    "sticky": r["sticky"] == "1",
                }
                rows.append(row)

    # Compute scores and emit.
    print(f"# threads loaded             : {len(rows):,}")
    print(f"# Pasumansky-touched topics  : {len(pas_counts):,}")
    print(f"# locally cached printpages  : {len(cached):,}")
    print(f"# covered (cited in articles): {len(covered):,}")

    cluster_hist: Counter[str] = Counter()
    score_hist: Counter[int] = Counter()

    with OUT.open("w", encoding="utf-8") as f:
        w = csv.writer(f, delimiter="\t")
        w.writerow([
            "topic_id", "board_id", "title", "views", "replies",
            "last_by", "last_date", "pasumansky_touched",
            "pasumansky_post_count", "cached", "covered", "processed",
            "auto_relevance", "manual_relevance", "relevance_basis",
            "topic_cluster", "notes", "intended_article",
        ])
        # Sort by auto_relevance desc, then by views desc.
        scored = []
        for row in rows:
            tid = row["topic_id"]
            alex_count = pas_counts.get(tid, 0)
            score, basis = auto_score(row, alex_count)
            cluster = detect_cluster(row["title"])
            cluster_hist[cluster] += 1
            score_hist[score] += 1

            cached_flag = tid in cached
            covered_flag = tid in covered
            processed = (
                "covered" if covered_flag
                else "examined" if cached_flag
                else "unread"
            )
            scored.append((row, alex_count, cached_flag, covered_flag,
                           processed, score, basis, cluster))

        scored.sort(key=lambda x: (-x[5], -x[0]["views"]))

        for row, alex_count, cached_flag, covered_flag, processed, score, basis, cluster in scored:
            w.writerow([
                row["topic_id"], row["board_id"], row["title"],
                row["views"], row["replies"], row["last_by"],
                row["last_date"], int(alex_count > 0), alex_count,
                int(cached_flag), int(covered_flag), processed,
                score, "", basis, cluster, "", "",
            ])

    print(f"\n# wrote {OUT}")
    print()
    print("auto_relevance distribution:")
    for s in range(10, -1, -1):
        bar = "█" * min(60, score_hist[s] // max(1, max(score_hist.values()) // 60))
        print(f"  {s:>2}: {score_hist[s]:>6}  {bar}")
    print()
    print("topic_cluster distribution:")
    for cluster, n in sorted(cluster_hist.items(), key=lambda x: -x[1]):
        print(f"  {cluster:<22} {n:>6}")


if __name__ == "__main__":
    main()
