"""Triage forum threads to identify mining candidates.

For each unmined, unskipped thread in a given size range, extracts:
  - Title
  - Number of Alexey Pasumansky / Dmitry Semyonov posts (Agisoft staff)
  - Total post count
  - Number of `Code: [Select]` code blocks
  - Topical keywords found in the thread (alignment, GPU, marker, etc.)
  - First Alexey post snippet (signal of substance)

Outputs a CSV-ish report sorted by a heuristic signal score.

Usage:
    python scripts/triage_forum_threads.py --min-size 15000 --max-size 30000 --limit 200
    python scripts/triage_forum_threads.py --min-size 5000 --max-size 15000 --limit 50
"""
import argparse
import glob
import html
import os
import re
from pathlib import Path

KEYWORDS = [
    # Workflow stages
    "alignment", "matching", "matchphotos", "alignchunks", "mergechunks",
    "depth map", "buildpointcloud", "dense cloud", "buildmesh", "buildmodel",
    "buildtexture", "buildtiledmodel", "buildorthomosaic", "builddem",
    # Calibration / sensors
    "calibration", "user_calib", "sensor", "fisheye", "spherical", "rolling shutter",
    "sensor.master", "sensor.fixed", "multi-camera", "multispectral",
    # Markers / GCPs
    "marker", "gcp", "ground control", "rtk", "ppk", "georefer",
    # Performance / hardware
    "gpu", "cuda", "opencl", "vulkan", "tcc mode", "memtest", "ram",
    "xeon", "ryzen", "threadripper", "i9-13", "i9-14", "linux vs windows",
    # Coordinate / projection
    "crs", "epsg", "coordinate", "projection", "geoid", "utm", "wgs84",
    # Python API surface
    "api", "python", "tasks.", "chunk.transform", "camera.transform",
    "tie_points", "point_cloud.points", "projections",
    # Bugs / undocumented
    "tweak", "undocumented", "settings.setvalue", "main/", "depth_filter",
]

STAFF_NAMES = ["Alexey Pasumansky", "Dmitry Semyonov"]


def signal_score(title: str, staff_posts: int, n_posts: int, code_blocks: int,
                 keywords_found: list[str], first_staff_snippet: str) -> int:
    """Heuristic score — higher means more likely to yield an insight."""
    score = 0
    score += staff_posts * 10  # staff engagement is the strongest signal
    score += code_blocks * 5  # code samples = actionable
    score += min(n_posts, 20) * 1  # discussion depth (capped)
    score += len(keywords_found) * 2  # topical density
    # Penalise pure error/crash threads (common but rarely actionable)
    if any(t in title.lower() for t in ["crash", "error", "assertion", "bug report"]):
        score -= 10
    # Boost titles indicating a "how to" / explanation
    if any(t in title.lower() for t in ["how to", "best practice", "what is", "explain", "difference"]):
        score += 15
    # Boost if first staff post has substantive content (>500 chars)
    if len(first_staff_snippet) > 500:
        score += 5
    return score


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--min-size", type=int, default=15_000)
    parser.add_argument("--max-size", type=int, default=30_000)
    parser.add_argument("--limit", type=int, default=200)
    parser.add_argument("--offset", type=int, default=0)
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parent.parent

    # Mined / skipped sets
    referenced: set[int] = set()
    for pattern in ("insights/insight-*.md", "docs/**/*.md"):
        for f in repo_root.glob(pattern):
            text = f.read_text()
            referenced.update(int(m.group(1)) for m in re.finditer(r"topic=(\d+)", text))

    skip_list: set[int] = set()
    skip_file = repo_root / "insights" / ".mining_skip_list.txt"
    if skip_file.exists():
        for line in skip_file.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and line.split()[0].isdigit():
                skip_list.add(int(line.split()[0]))

    # Collect candidate threads
    candidates = []
    for f in sorted((repo_root / "corpus" / "forum").glob("printpage-*.html")):
        size = f.stat().st_size
        if size < args.min_size or size >= args.max_size:
            continue
        topic_m = re.search(r"printpage-(\d+)", f.name)
        topic_id = int(topic_m.group(1).lstrip("0") or "0")
        if topic_id in referenced or topic_id in skip_list:
            continue
        candidates.append((size, topic_id, f))

    print(f"Triaging {len(candidates)} threads in size [{args.min_size}, {args.max_size})", flush=True)

    rows = []
    for size, topic_id, f in candidates[args.offset:args.offset + args.limit]:
        text = f.read_text()
        # Skip pre-release threads (already mined for new-feature articles)
        title_m = re.search(r"<title>(.*?)</title>", text[:2000])
        title = title_m.group(1).replace("Print Page - ", "").strip() if title_m else "?"
        if "pre-release" in title.lower():
            continue

        # Count metrics
        staff_posts = sum(text.count(name) for name in STAFF_NAMES)
        post_blocks = re.split(r'<dt class="postheader"', text)
        n_posts = max(0, len(post_blocks) - 1)
        code_blocks = text.count("Code: [Select]")

        # Find keywords (case-insensitive, in plain text)
        plain = re.sub(r"<[^>]+>", " ", text)
        plain = html.unescape(plain).lower()
        keywords_found = [k for k in KEYWORDS if k in plain]

        # First staff post snippet
        first_snip = ""
        for name in STAFF_NAMES:
            m = re.search(re.escape(name) + r".*?(?=Title:)", text, re.DOTALL)
            if m:
                snip = re.sub(r"<[^>]+>", " ", m.group(0))
                snip = html.unescape(snip)
                snip = re.sub(r"\s+", " ", snip).strip()
                first_snip = snip[:600]
                break

        score = signal_score(title, staff_posts, n_posts, code_blocks, keywords_found, first_snip)
        rows.append({
            "score": score,
            "size_kb": size // 1024,
            "topic_id": topic_id,
            "title": title,
            "staff_posts": staff_posts,
            "n_posts": n_posts,
            "code_blocks": code_blocks,
            "keywords": keywords_found,
            "first_snip": first_snip,
        })

    rows.sort(key=lambda r: -r["score"])

    out_path = repo_root / "insights" / f".triage_{args.min_size}_{args.max_size}.txt"
    with out_path.open("w") as fh:
        fh.write(f"# Triage report: threads {args.min_size}-{args.max_size} bytes\n")
        fh.write(f"# Total candidates: {len(rows)} (offset {args.offset}, limit {args.limit})\n")
        fh.write(f"# Sorted by signal score (descending)\n\n")
        for r in rows:
            fh.write(f"## score={r['score']}  size={r['size_kb']}KB  t={r['topic_id']}  staff={r['staff_posts']}  posts={r['n_posts']}  code={r['code_blocks']}\n")
            fh.write(f"   {r['title']}\n")
            if r['keywords']:
                fh.write(f"   keywords: {', '.join(r['keywords'][:8])}\n")
            if r['first_snip']:
                fh.write(f"   first staff post: {r['first_snip'][:300]}\n")
            fh.write("\n")
    print(f"Wrote {out_path}")
    print(f"Top 10 by score:")
    for r in rows[:10]:
        print(f"  score={r['score']:3d}  t={r['topic_id']:<6d} {r['title'][:60]}")


if __name__ == "__main__":
    main()
