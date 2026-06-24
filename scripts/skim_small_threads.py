"""Skim the small (≤15KB) forum threads in batches and produce
a lightweight reference index of those worth referring to.

Unlike the full triage, this script:
- Outputs a one-line entry per thread to a markdown reference file
- Flags threads as 'reference' (worth linking from articles) or
  'skip' (no value), based on a stricter heuristic
- Does NOT generate full insight cards

Usage:
    python scripts/skim_small_threads.py --batch-size 50 --batch-num 1
"""
import argparse
import glob
import html
import os
import re
from pathlib import Path

REFERENCE_KEYWORDS = [
    # Concrete API patterns
    "chunk.matchPhotos", "chunk.alignCameras", "chunk.optimizeCameras",
    "chunk.buildModel", "chunk.buildOrthomosaic", "chunk.buildDem",
    "chunk.exportPoints", "chunk.exportModel", "chunk.exportOrthomosaic",
    "chunk.tie_points", "chunk.point_cloud", "chunk.transform",
    "chunk.region", "chunk.crs", "chunk.shapes",
    "camera.transform", "camera.calibration", "camera.project",
    "Metashape.Vector", "Metashape.Matrix", "Metashape.Tasks",
    "Metashape.Utils", "Metashape.app.settings",
    # Concrete tweaks
    "main/", "tweak", "settings.setValue",
    # Specific concepts
    "MultiplaneLayout", "MultiframeLayout", "BlendingMode",
    "PointClass", "Sensor.Type",
]

STAFF_NAMES = ["Alexey Pasumansky", "Dmitry Semyonov"]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--max-size", type=int, default=15_000)
    parser.add_argument("--min-size", type=int, default=5_000)
    parser.add_argument("--batch-size", type=int, default=200)
    parser.add_argument("--batch-num", type=int, default=1)
    parser.add_argument("--out", default=None)
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parent.parent

    # Already-mined / already-skipped sets
    referenced: set[int] = set()
    for pattern in ("insights/insight-*.md", "docs/**/*.md"):
        for f in repo_root.glob(pattern):
            referenced.update(int(m.group(1)) for m in re.finditer(r"topic=(\d+)", f.read_text()))

    skip_list: set[int] = set()
    skip_file = repo_root / "insights" / ".mining_skip_list.txt"
    if skip_file.exists():
        for line in skip_file.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and line.split()[0].isdigit():
                skip_list.add(int(line.split()[0]))

    # Collect candidate files in size range, sorted by size descending
    files = []
    for f in (repo_root / "corpus" / "forum").glob("printpage-*.html"):
        size = f.stat().st_size
        if size < args.min_size or size >= args.max_size:
            continue
        topic_id = int(re.search(r"printpage-(\d+)", f.name).group(1).lstrip("0") or "0")
        if topic_id in referenced or topic_id in skip_list:
            continue
        files.append((size, topic_id, f))
    files.sort(key=lambda t: -t[0])

    # Apply batching
    start = (args.batch_num - 1) * args.batch_size
    end = start + args.batch_size
    batch = files[start:end]

    print(f"Skimming batch {args.batch_num}: threads {start+1}-{end} of {len(files)} candidates", flush=True)

    rows = []
    for size, topic_id, f in batch:
        text = f.read_text()
        title_m = re.search(r"<title>(.*?)</title>", text[:2000])
        title = title_m.group(1).replace("Print Page - ", "").strip() if title_m else "?"
        if "pre-release" in title.lower():
            continue

        staff_count = sum(text.count(name) for name in STAFF_NAMES)
        code_count = text.count("Code: [Select]")
        kw_hits = sum(1 for kw in REFERENCE_KEYWORDS if kw in text)
        n_posts = text.count('<dt class="postheader"')

        # Classification
        title_lower = title.lower()
        if any(t in title_lower for t in ["error", "crash", "failed", "cant ", "can't ", "cannot ", "help!", "urgent", "won't"]):
            cls = "skip-error"
        elif any(t in title_lower for t in ["license", "activation", "subscription", "demo", "pricing", "edu"]):
            cls = "skip-marketing"
        elif staff_count == 0:
            cls = "skip-no-staff"
        elif code_count >= 1 and staff_count >= 1 and kw_hits >= 2:
            cls = "REFERENCE"  # has code + staff + concrete keywords
        elif staff_count >= 2 and kw_hits >= 3:
            cls = "REFERENCE"  # multi-staff discussion of concrete topic
        else:
            cls = "skip-low-signal"

        rows.append({
            "size": size,
            "topic_id": topic_id,
            "title": title,
            "staff_count": staff_count,
            "code_count": code_count,
            "kw_hits": kw_hits,
            "n_posts": n_posts,
            "classification": cls,
        })

    # Write report
    out_path = repo_root / "insights" / (args.out or f".skim_batch{args.batch_num}.md")
    with out_path.open("w") as fh:
        ref = [r for r in rows if r["classification"] == "REFERENCE"]
        skip = [r for r in rows if r["classification"] != "REFERENCE"]
        fh.write(f"# Forum-thread skim batch {args.batch_num}\n\n")
        fh.write(f"Range: {args.min_size}-{args.max_size} bytes, "
                 f"sorted by size, threads {start+1}-{end} of {len(files)}.\n\n")
        fh.write(f"**REFERENCE candidates: {len(ref)}.** ")
        fh.write(f"Skipped: {len(skip)}.\n\n")

        fh.write("## REFERENCE candidates (worth linking from articles)\n\n")
        fh.write("| Size | Topic ID | Title | staff | code | kw |\n")
        fh.write("|---:|---:|---|---:|---:|---:|\n")
        for r in sorted(ref, key=lambda x: -x["size"]):
            fh.write(f"| {r['size']//1024}KB | {r['topic_id']} | {r['title'][:70]} "
                     f"| {r['staff_count']} | {r['code_count']} | {r['kw_hits']} |\n")

        fh.write("\n## Skipped\n\n")
        fh.write(f"| Size | Topic ID | Title | reason |\n|---:|---:|---|---|\n")
        for r in sorted(skip, key=lambda x: -x["size"])[:50]:
            fh.write(f"| {r['size']//1024}KB | {r['topic_id']} | {r['title'][:60]} | {r['classification']} |\n")
        if len(skip) > 50:
            fh.write(f"\n*({len(skip) - 50} more skipped — see full data in script output.)*\n")

    print(f"Wrote {out_path}")
    print(f"  REFERENCE candidates: {sum(1 for r in rows if r['classification'] == 'REFERENCE')}")
    print(f"  Skipped: {sum(1 for r in rows if r['classification'] != 'REFERENCE')}")
    print()
    print("Top REFERENCE candidates:")
    for r in sorted([r for r in rows if r["classification"] == "REFERENCE"], key=lambda x: -x["staff_count"] - x["code_count"])[:10]:
        print(f"  t={r['topic_id']:<6d} {r['size']//1024}KB  staff={r['staff_count']} code={r['code_count']} | {r['title'][:55]}")


if __name__ == "__main__":
    main()
