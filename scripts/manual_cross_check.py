"""Cross-check forum-derived claims against official Metashape manuals.

Greps the official-manual PDFs in `corpus/official/` for keywords
extracted from an insight card or text snippet, and reports which
of those keywords appear in the manual. Used to gauge whether a
forum-derived insight adds value beyond what's already documented
officially.

Usage:
    # Audit a single insight card
    python scripts/manual_cross_check.py insights/insight-0086-exif-focal-length-estimation.md

    # Audit ad-hoc text
    python scripts/manual_cross_check.py --text "FocalPlaneXResolution"

    # Audit all recent insights (range)
    python scripts/manual_cross_check.py --insight-range 0073 0087
"""
import argparse
import re
import subprocess
from pathlib import Path


# Stopwords to filter from auto-extracted keywords
STOPWORDS = {
    "the", "and", "or", "but", "if", "then", "else", "for", "while",
    "from", "to", "with", "on", "at", "by", "in", "of", "a", "an",
    "is", "are", "was", "were", "be", "been", "being",
    "this", "that", "these", "those", "it", "its", "their", "his", "her",
    "you", "your", "they", "them", "we", "us", "i", "me", "my",
    "do", "does", "did", "have", "has", "had", "can", "could", "should", "would",
    "metashape", "photoscan", "agisoft", "forum", "thread", "topic", "post",
    "alexey", "pasumansky", "user", "version", "issue", "problem", "error",
    "use", "used", "using", "uses", "see", "also", "may", "might", "will",
    "yes", "no", "not", "as", "so", "what", "when", "how", "where", "why",
    "py", "python", "code", "select", "import",
}


def extract_keywords(text: str, min_length: int = 4) -> list[str]:
    """Heuristic keyword extraction from insight body.

    Picks up:
    - Code-formatted identifiers (e.g. `Chunk.matchPhotos`, `filter_stationary_points`)
    - CamelCase identifiers (e.g. `FocalPlaneXResolution`, `OrthoProjection`)
    - Multi-word phrases in quotes
    """
    keywords: set[str] = set()

    # Backticked identifiers
    for m in re.finditer(r"`([^`]+)`", text):
        kw = m.group(1).strip()
        if len(kw) >= min_length and any(c.isalnum() for c in kw):
            keywords.add(kw)

    # CamelCase identifiers
    for m in re.finditer(r"\b([A-Z][a-z]+(?:[A-Z][a-z]+){1,})\b", text):
        kw = m.group(1)
        if len(kw) >= min_length:
            keywords.add(kw)

    # Quoted phrases (often verbatim manual text or feature names)
    for m in re.finditer(r'"([^"]{6,80})"', text):
        kw = m.group(1).strip()
        if len(kw) >= min_length:
            keywords.add(kw)

    # snake_case identifiers
    for m in re.finditer(r"\b([a-z]+(?:_[a-z]+){1,})\b", text):
        kw = m.group(1)
        if len(kw) >= min_length and kw.lower() not in STOPWORDS:
            keywords.add(kw)

    return sorted(keywords)


def grep_manuals(keyword: str, manual_texts: dict[str, str]) -> list[tuple[str, int]]:
    """Return (manual_name, hit_count) for each manual containing the keyword."""
    results = []
    kw_lower = keyword.lower()
    for name, text in manual_texts.items():
        count = text.count(kw_lower)
        if count > 0:
            results.append((name, count))
    return results


def load_manuals(manuals: list[Path]) -> dict[str, str]:
    """Extract text from each PDF once, cache in lower case for fast contains()."""
    cache: dict[str, str] = {}
    for manual in manuals:
        try:
            proc = subprocess.run(
                ["pdftotext", "-layout", str(manual), "-"],
                capture_output=True, text=True, timeout=120,
            )
            if proc.returncode == 0:
                cache[manual.name] = proc.stdout.lower()
        except (subprocess.TimeoutExpired, FileNotFoundError):
            continue
    return cache


def audit_one(path_or_text: str, *, is_text: bool = False, manual_texts: dict[str, str]) -> dict:
    """Run the cross-check for one insight or one text blob."""
    if is_text:
        text = path_or_text
        name = "<text>"
    else:
        path = Path(path_or_text)
        text = path.read_text()
        name = path.name

    keywords = extract_keywords(text)
    hits = []
    for kw in keywords:
        manual_hits = grep_manuals(kw, manual_texts)
        if manual_hits:
            hits.append((kw, manual_hits))

    # Score: number of keywords found in manual, weighted by total hits
    novelty_signal = len(keywords) - len(hits)  # higher = more novel
    return {
        "name": name,
        "n_keywords": len(keywords),
        "n_in_manual": len(hits),
        "novelty_signal": novelty_signal,
        "hits": hits,
        "all_keywords": keywords,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("paths", nargs="*", help="Insight card paths or text")
    parser.add_argument("--text", help="Audit ad-hoc text instead of a file")
    parser.add_argument("--insight-range", nargs=2, type=int,
                        help="Audit insight-NNNN through insight-MMMM")
    parser.add_argument("--brief", action="store_true",
                        help="Only print summary line per insight")
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parent.parent
    manuals = sorted((repo_root / "corpus" / "official").glob("*.pdf"))
    if not manuals:
        print("ERROR: no PDFs in corpus/official/")
        return

    # Load and cache all manual texts ONCE (fast contains() afterwards)
    print(f"Loading {len(manuals)} PDFs into memory...", end=" ", flush=True)
    manual_texts = load_manuals(manuals)
    print(f"done ({sum(len(t) for t in manual_texts.values()) // 1024} KB cached).")

    targets = []
    if args.text:
        targets.append((args.text, True))
    if args.insight_range:
        lo, hi = args.insight_range
        for n in range(lo, hi + 1):
            for p in (repo_root / "insights").glob(f"insight-{n:04d}-*.md"):
                targets.append((str(p), False))
    for p in args.paths:
        targets.append((p, False))

    if not targets:
        parser.print_help()
        return

    for path_or_text, is_text in targets:
        result = audit_one(path_or_text, is_text=is_text, manual_texts=manual_texts)
        print(f"\n=== {result['name']} ===")
        print(f"  Keywords extracted: {result['n_keywords']}")
        print(f"  Found in manual:    {result['n_in_manual']}")
        print(f"  Novelty signal:     {result['novelty_signal']:+d} "
              f"({'mostly novel' if result['novelty_signal'] > result['n_keywords']*0.6 else 'overlaps with manual'})")
        if not args.brief and result["hits"]:
            print(f"  Manual matches:")
            for kw, manual_hits in result["hits"][:10]:
                hit_str = ", ".join(f"{m}({c})" for m, c in manual_hits)
                print(f"    {kw!r:<40}  → {hit_str}")
            if len(result["hits"]) > 10:
                print(f"    ... and {len(result['hits']) - 10} more")


if __name__ == "__main__":
    main()
