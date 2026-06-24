"""Extract structured text from SMF printpage HTML.

SMF's `?action=printpage` view emits a clean structure:
  - Top header with topic title and forum path
  - One block per post: Title / Post by / Date / Body
  - Footer with SMF branding

We strip HTML to text and try to preserve post boundaries so the result
is readable and citable.

Usage:
    python scripts/parse_printpage.py corpus/forum/printpage-NNNNN.html
"""
from __future__ import annotations
import argparse
import html
import re
import sys
from pathlib import Path


def html_to_text(s: str) -> str:
    # Remove script and style blocks entirely.
    s = re.sub(r"<(script|style)[^>]*>.*?</\1>", "", s, flags=re.DOTALL | re.IGNORECASE)
    # Convert common block-level tags to newlines so structure survives stripping.
    s = re.sub(r"<br\s*/?>", "\n", s, flags=re.IGNORECASE)
    s = re.sub(r"</(p|div|li|tr|h[1-6])>", "\n", s, flags=re.IGNORECASE)
    s = re.sub(r"<li[^>]*>", "  - ", s, flags=re.IGNORECASE)
    # Strip remaining tags.
    s = re.sub(r"<[^>]+>", "", s)
    # Decode HTML entities.
    s = html.unescape(s)
    # Collapse whitespace conservatively — preserve paragraph breaks but
    # drop runs of blank lines.
    s = re.sub(r"[ \t]+", " ", s)
    s = re.sub(r"\n[ \t]+", "\n", s)
    s = re.sub(r"\n{3,}", "\n\n", s)
    return s.strip()


def split_posts(text: str) -> list[str]:
    """Split the page text on the SMF printpage post-header pattern.

    Each post starts with a line like:
        Title: <subject>
    followed by:
        Post by: <author> on <date>
    We use the "Post by:" anchor as the most reliable separator.
    """
    parts = re.split(r"(?=Post by:\s)", text)
    return [p.strip() for p in parts if p.strip()]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("path", type=Path)
    args = ap.parse_args()

    raw = args.path.read_text(encoding="utf-8", errors="replace")
    text = html_to_text(raw)
    posts = split_posts(text)

    print(f"=== {args.path.name} ({len(posts)} chunk(s)) ===\n")
    for i, p in enumerate(posts, 1):
        print(f"--- chunk {i} ---")
        print(p)
        print()


if __name__ == "__main__":
    main()
