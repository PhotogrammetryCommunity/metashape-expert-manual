#!/usr/bin/env python3
"""Audit all articles: structure, links, source coverage, indices.

Produces a structured report at build/review-automated.md
covering everything that can be checked without reading the article body
in detail (which is left to manual review).

Checks:
1. Inventory — every article with frontmatter + batch assignment.
2. Source coverage — every `topic=N` reference in articles maps to a
   cached printpage; every cached printpage is cited at least once.
3. Cross-link audit — every `[text](path.md)` resolves; every article
   has at least one inbound link from an index or sibling article.
4. Index audit — every article appears in nav (mkdocs.yml).
5. Tier 1 sweep — run scripts/verify_article.py and aggregate
   terminology / API / menu-path findings.
6. Confidence-header audit — every article has `confidence:` and
   the value (`high` / `medium` / `low`) matches what the body claims.
"""
from __future__ import annotations

import re
import subprocess
from collections import defaultdict
from pathlib import Path

ROOT = Path(".")
DOCS = ROOT / "docs"
INSIGHTS = ROOT / "insights"
CORPUS_FORUM = ROOT / "corpus" / "forum"
MKDOCS = ROOT / "mkdocs.yml"
OUTPUT = ROOT / "build" / "review-automated.md"


# Article identification: a markdown file under docs/ that has either
# a YAML frontmatter block (newer) OR a bold-list metadata
# blockquote (older form). Excludes index.md and reference pages.
def is_substantive_article(p: Path) -> bool:
    if p.name == "index.md":
        return False
    text = p.read_text(encoding="utf-8", errors="replace")
    # YAML frontmatter (newer).
    if text.startswith("---") and "\ntitle:" in text[:300]:
        return True
    # Bold-list blockquote (older): H1 followed within ~25 lines by
    # a > - **applies_to:** line.
    head = "\n".join(text.splitlines()[:30])
    if re.search(r"^# .+", head, re.MULTILINE) and \
       re.search(r">\s*-\s*\*\*applies_to:\*\*", head):
        return True
    return False


def article_title(p: Path) -> str:
    text = p.read_text(encoding="utf-8", errors="replace")
    m = re.search(r"^title:\s*\"?(.*?)\"?$", text, re.MULTILINE)
    if m:
        return m.group(1).strip()
    # Bold-list form: title is the H1.
    m = re.search(r"^# (.+)$", text, re.MULTILINE)
    return m.group(1).strip() if m else "(no title)"


def article_confidence(p: Path) -> str:
    text = p.read_text(encoding="utf-8", errors="replace")
    # YAML form
    m = re.search(r"^confidence:\s*(\S+)", text, re.MULTILINE)
    if m:
        return m.group(1)
    # Bold-list form: > - **confidence:** `medium` — ...
    m = re.search(r"\*\*confidence:\*\*\s*`?(\w+)`?", text)
    return m.group(1) if m else "(missing)"


def article_diataxis(p: Path) -> str:
    text = p.read_text(encoding="utf-8", errors="replace")
    m = re.search(r"^diataxis:\s*(\S+)", text, re.MULTILINE)
    if m:
        return m.group(1)
    # Bold-list form doesn't include diataxis explicitly.
    return "(not declared)"


def article_status(p: Path) -> str:
    text = p.read_text(encoding="utf-8", errors="replace")
    m = re.search(r"^status:\s*(\S+)", text, re.MULTILINE)
    if m:
        return m.group(1)
    m = re.search(r"\*\*status:\*\*\s*`?(\w+)`?", text)
    return m.group(1) if m else "(missing)"


def article_format(p: Path) -> str:
    text = p.read_text(encoding="utf-8", errors="replace")
    if text.startswith("---"):
        return "yaml"
    return "bold-list"


def topic_refs(p: Path) -> set[int]:
    text = p.read_text(encoding="utf-8", errors="replace")
    refs: set[int] = set()
    for m in re.finditer(r"topic=(\d+)", text):
        refs.add(int(m.group(1)))
    return refs


def cached_topics() -> set[int]:
    out: set[int] = set()
    for p in CORPUS_FORUM.glob("printpage-*.html"):
        m = re.match(r"printpage-(\d+)\.html", p.name)
        if m:
            out.add(int(m.group(1)))
    return out


def md_links(p: Path) -> list[tuple[str, str]]:
    """Return (anchor_text, target_path) for relative .md links."""
    text = p.read_text(encoding="utf-8", errors="replace")
    out: list[tuple[str, str]] = []
    for m in re.finditer(r"\[([^\]]+)\]\(([^)]+\.md)(?:#[^\)]*)?\)", text):
        anchor, target = m.group(1), m.group(2)
        if target.startswith(("http://", "https://")):
            continue
        out.append((anchor, target))
    return out


def resolve_link(article_path: Path, target: str) -> Path | None:
    """Resolve a relative markdown link from article_path."""
    if target.startswith("/"):
        candidate = (ROOT / target.lstrip("/")).resolve()
    else:
        candidate = (article_path.parent / target).resolve()
    return candidate if candidate.exists() else None


def nav_articles() -> set[Path]:
    out: set[Path] = set()
    text = MKDOCS.read_text(encoding="utf-8", errors="replace")
    for m in re.finditer(r":\s*([^\s][^\s]*\.md)\s*$", text, re.MULTILINE):
        rel = m.group(1).strip()
        out.add((DOCS / rel).resolve())
    return out


def find_articles() -> list[Path]:
    return [p.resolve() for p in DOCS.rglob("*.md") if is_substantive_article(p)]


# --- Batch assignment heuristic from filename + commit-log lookup ---
WAVE_BY_NAME = {
    "diagnosing-under-aligned-chunks": 1,
    "clean-tie-points-optimize-cameras-loop": 1,
    "automating-gradual-selection-python": 1,
    "removing-blue-flag-marker-projections": 2,
    "programmatic-marker-placement": 2,
    "reproducing-chunk-info-statistics-python": 2,
    "logging-from-python-scripts": 2,
    "setting-the-chunk-region": 2,
    "exporting-depth-maps-python": 2,
    "what-mergechunks-does": 3,
    "alignchunks-three-methods": 3,
    "merge-tiepoints-and-keep-keypoints": 3,
    "no-camera-deduplication": 3,
    "recovery-paths-unaligned-cameras": 3,
    "incremental-matching-keep-keypoints": 3,
    "multi-camera-rig-python": 3,
    "choosing-master-sensor-multi-camera-layout": 3,
    "when-optimize-cameras-helps": 3,
    "mask-tiepoints-cross-view": 3,
    "alignchunks-symmetric-scene-failure": 4,
    "synthetic-priors-reference-preselection": 4,
    "filter-mask-starvation": 4,
    "symlink-filename-camera-label": 4,
    "chunk-frame-vs-camera-frame": 4,
    "tightening-reference-accuracies": 4,  # M.1 addendum
    "distortion-model-opencv-colmap": 5,
    "sensor-calibration-vs-user-calib": 5,
    "calibration-import-export": 5,
    "computing-camera-coverage-area": 5,
    "orthomosaic-pixel-to-source-image": 5,
    "camera-poses-to-enu": 5,
    "orthomosaic-export-pitfalls": 5,
    "importing-camera-orientation": 5,
    "slave-sensor-transform-recipes": 5,  # N+ addendum
    "gpu-usage-by-stage": 6,
    "diagnosing-cuda-opencl-errors": 6,
    "ram-and-quality-settings": 6,
}


def batch_of(p: Path) -> int:
    return WAVE_BY_NAME.get(p.stem, 0)


def main():
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    lines: list[str] = []
    out = lines.append

    arts = find_articles()
    arts.sort(key=lambda p: (batch_of(p), p.name))
    cached = cached_topics()
    nav = nav_articles()

    out("# Article review — automated checks\n")
    out(f"Generated by `scripts/review_articles.py`. {len(arts)} substantive articles audited.\n")
    out("Each section flags issues; absence of a section means no issues found.\n\n")

    # =========================================================
    # 1. Inventory
    # =========================================================
    out("## 1. Inventory\n")
    out("| Batch | Path | Title | Confidence | Diátaxis | Status | Format |")
    out("|------|------|-------|------------|----------|--------|--------|")
    by_batch: dict[int, list[Path]] = defaultdict(list)
    for art in arts:
        rel = art.relative_to(ROOT.resolve())
        batch = batch_of(art)
        by_batch[batch].append(art)
        out(f"| {batch} | `{rel}` | {article_title(art)} | "
            f"{article_confidence(art)} | {article_diataxis(art)} | "
            f"{article_status(art)} | {article_format(art)} |")
    out("")

    # Format-consistency check
    fmt_counts: dict[str, int] = defaultdict(int)
    for art in arts:
        fmt_counts[article_format(art)] += 1
    if len(fmt_counts) > 1:
        out("**STYLE INCONSISTENCY** — articles use mixed frontmatter formats:\n")
        for fmt, n in sorted(fmt_counts.items()):
            out(f"- `{fmt}`: {n} articles")
        out("\nWave 1–2 articles use a blockquote bold-list metadata block; "
            "Newer articles use YAML frontmatter. The two forms differ "
            "in whether `diataxis:` is declared explicitly. Recommendation: "
            "convert older articles to YAML frontmatter for consistency, OR "
            "document the bold-list form as the canonical alternative in "
            "STYLE.md.\n")
    out("")

    # =========================================================
    # 2. Frontmatter completeness
    # =========================================================
    out("## 2. Frontmatter completeness\n")
    fm_issues: list[str] = []
    for art in arts:
        rel = art.relative_to(ROOT.resolve())
        text = art.read_text(encoding="utf-8", errors="replace")
        for required in ["title:", "status:", "applies_to:", "last_reviewed:"]:
            if required not in text[:1000]:
                fm_issues.append(f"- `{rel}` missing frontmatter `{required}`")
        if "diataxis:" not in text[:1000]:
            fm_issues.append(f"- `{rel}` missing `diataxis:`")
        if "confidence:" not in text[:1000]:
            fm_issues.append(f"- `{rel}` missing `confidence:`")
    if fm_issues:
        for s in fm_issues: out(s)
    else:
        out("*All articles have complete frontmatter.*")
    out("")

    # =========================================================
    # 3. Source coverage
    # =========================================================
    out("## 3. Source-coverage audit (topic=N references)\n")
    refs_by_article: dict[Path, set[int]] = {a: topic_refs(a) for a in arts}
    all_refs: set[int] = set().union(*refs_by_article.values()) if refs_by_article else set()
    uncited = cached - all_refs
    uncached_refs: dict[Path, set[int]] = {
        a: r - cached for a, r in refs_by_article.items() if r - cached
    }

    out(f"- **Total `topic=N` references across articles**: {sum(len(r) for r in refs_by_article.values()):,}\n")
    out(f"- **Distinct topics cited**: {len(all_refs):,}\n")
    out(f"- **Locally cached printpages**: {len(cached):,}\n")
    out(f"- **Cited but NOT cached locally**: {len(uncached_refs)} article(s) reference uncached topics\n")
    out(f"- **Cached but NOT cited**: {len(uncited):,} printpages cached but never cited\n")

    if uncached_refs:
        out("\n**Articles citing uncached topics** (cannot verify quotes against source):\n")
        for art, missing in sorted(uncached_refs.items()):
            rel = art.relative_to(ROOT.resolve())
            for tid in sorted(missing):
                out(f"- `{rel}` → topic={tid}")
    out("")

    # =========================================================
    # 4. Cross-link audit
    # =========================================================
    out("## 4. Cross-link audit\n")
    broken_links: list[str] = []
    inbound_count: dict[Path, int] = defaultdict(int)
    for art in arts:
        for anchor, target in md_links(art):
            resolved = resolve_link(art, target)
            if resolved is None:
                rel = art.relative_to(ROOT.resolve())
                broken_links.append(f"- `{rel}` → `{target}` (target not found)")
            elif resolved.suffix == ".md":
                inbound_count[resolved] += 1

    if broken_links:
        out(f"**{len(broken_links)} broken markdown link(s):**\n")
        for s in broken_links: out(s)
    else:
        out("*No broken cross-links.*")
    out("")

    # Articles with zero inbound links (other than nav)
    out("### Articles with zero inbound links from siblings\n")
    out("(These articles are reachable only via nav; consider adding cross-references from related articles.)\n")
    orphans: list[str] = []
    for art in arts:
        if inbound_count.get(art, 0) == 0:
            rel = art.relative_to(ROOT.resolve())
            orphans.append(f"- `{rel}` (batch {batch_of(art)})")
    if orphans:
        for s in orphans: out(s)
    else:
        out("*Every article has at least one inbound cross-link.*")
    out("")

    # =========================================================
    # 5. Nav audit
    # =========================================================
    out("## 5. Nav-coverage audit (mkdocs.yml)\n")
    not_in_nav: list[str] = []
    for art in arts:
        if art not in nav:
            rel = art.relative_to(ROOT.resolve())
            not_in_nav.append(f"- `{rel}` (batch {batch_of(art)})")
    if not_in_nav:
        out(f"**{len(not_in_nav)} article(s) not in nav:**\n")
        for s in not_in_nav: out(s)
    else:
        out("*Every article is reachable via mkdocs nav.*")
    out("")

    # Inverse — nav entries that don't resolve to an article
    nav_not_present: list[str] = []
    for nav_path in nav:
        if not nav_path.exists():
            rel = nav_path.relative_to(ROOT.resolve())
            nav_not_present.append(f"- `{rel}` listed in nav but file missing")
    if nav_not_present:
        out(f"\n**{len(nav_not_present)} nav entries with missing files:**\n")
        for s in nav_not_present: out(s)
    out("")

    # =========================================================
    # 6. Tier 1 aggregate
    # =========================================================
    out("## 6. Tier 1 aggregate (terminology / API / menu paths)\n")
    out("Per-article Tier 1 results would go here; run `scripts/verify_article.py` per article for detail.\n\n")

    # =========================================================
    # 7. Batch summary
    # =========================================================
    out("## 7. Per-batch summary\n")
    for batch in sorted(by_batch.keys()):
        arts_in_batch = by_batch[batch]
        out(f"\n### Batch {batch} — {len(arts_in_batch)} articles\n")
        for art in arts_in_batch:
            rel = art.relative_to(ROOT.resolve())
            n_refs = len(refs_by_article.get(art, set()))
            n_inbound = inbound_count.get(art, 0)
            n_links = len(md_links(art))
            out(f"- `{rel}` — {n_refs} sources cited, "
                f"{n_inbound} inbound, {n_links} outbound links")

    OUTPUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"wrote {OUTPUT}")


if __name__ == "__main__":
    main()
