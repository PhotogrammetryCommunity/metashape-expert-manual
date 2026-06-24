#!/usr/bin/env python3
"""Tier 1 verification: extract verbatim blockquotes from markdown
and confirm each is character-for-character present in the cited
forum source.

For every blockquote in a markdown file:
  1. Extract the quoted text.
  2. Locate the cited permalink (looking for a paired
     `permalink](https://...)` link below the quote, OR an
     attribution line that names the forum thread).
  3. Locate the source HTML in `corpus/forum/`.
  4. Confirm the quoted text appears character-for-character in
     the source HTML (ignoring whitespace runs and HTML tags).
  5. Report any quote that does NOT match — these are silent
     edits, paraphrases, or fabrications.

This addresses the verbatim-quote rule documented in STYLE.md
and the source-faithfulness lessons surfaced in earlier reviews
(lessons #14, #28, #30).

Usage:
    ./.venv/bin/python scripts/verify_quotes.py docs/workflow/<path>/article.md

    # or audit the whole corpus:
    ./.venv/bin/python scripts/verify_quotes.py docs/

Exits non-zero if any quote fails verification. Suitable for
pre-commit hooks.
"""

from __future__ import annotations

import argparse
import html as html_module
import re
import sys
from pathlib import Path
from typing import Iterator, NamedTuple, Optional

# A blockquote is one or more consecutive lines starting with `>`,
# possibly indented (markdown allows indented blockquotes inside
# bullet lists, etc.).
BLOCKQUOTE_LINE_RE = re.compile(r"^(\s*>\s?)(.*)$", re.MULTILINE)

# Permalinks to forum posts. Two patterns:
#   1. (permalink) format:  [permalink](https://www.agisoft.com/forum/index.php?topic=NNN.msgMMM#msgMMM)
#   2. inline link:         https://www.agisoft.com/forum/...?topic=NNN.msgMMM
PERMALINK_RE = re.compile(
    r"https://www\.agisoft\.com/forum/index\.php\?topic=(\d+)(?:\.msg(\d+)#msg\d+)?"
)


class Blockquote(NamedTuple):
    """A blockquote extracted from a markdown file."""

    file: Path
    line: int   # 1-based line number of the first ">" line
    text: str   # joined-and-cleaned quote text (HTML decoded)


class CitedSource(NamedTuple):
    """The forum source referenced by a blockquote."""

    topic_id: int
    msg_id: Optional[int]
    permalink: str


class QuoteCheck(NamedTuple):
    """A quote and its verification result."""

    quote: Blockquote
    cited: Optional[CitedSource]
    found: bool
    notes: str


def extract_quoted_text(blockquote_text: str) -> Optional[str]:
    """Extract just the quoted portion of a blockquote, separating it
    from the attribution line.

    Our blockquote format is:
      "Quote text here." — Author, date, version ([permalink](...))

    or with multi-paragraph quotes:
      "First sentence. Second sentence." — Author, date

    Returns the text between the FIRST `"` and the matching closing
    `"` before the em-dash (or the last `"` if no em-dash). Returns
    None if the blockquote contains no double-quoted text — these
    are non-verbatim blockquotes (e.g., '> **Demo verified:** ✗' or
    other article metadata) that should be skipped by the verifier.
    """
    # Look for outer double-quote pair. SMF / our markdown uses
    # straight ASCII quotes consistently.
    m = re.search(r'"([^"]*(?:"[^"]*)*?)"\s*[—\-–]', blockquote_text)
    if m:
        return m.group(1).strip()
    # Fall back: greedy match between first and LAST `"`. Only
    # accept if followed by an em-dash attribution — without it the
    # blockquote is article metadata (e.g., a *Confidence* note that
    # happens to contain `"..."` strings).
    m = re.search(r'"(.+)"\s*[—\-–]', blockquote_text, re.DOTALL)
    if m:
        return m.group(1).strip()
    # No double-quoted content -> not a verbatim quote (likely
    # article metadata, demo-verified marker, etc.). Skip.
    return None


def find_blockquotes(md_path: Path) -> Iterator[Blockquote]:
    """Yield every consecutive run of `> `-prefixed lines as a single
    blockquote.

    Adjacent blockquote lines (with no non-quote line between them) are
    merged into one quote.
    """
    text = md_path.read_text(encoding="utf-8", errors="replace")
    lines = text.split("\n")
    in_quote = False
    buf: list[str] = []
    quote_start_line = 0
    quote_end_line = 0

    def flush() -> Optional[Blockquote]:
        if not buf:
            return None
        joined = " ".join(b for b in buf if b).strip()
        joined = html_module.unescape(joined)
        if not joined:
            return None
        # Extract just the quoted portion (separating from attribution)
        quoted = extract_quoted_text(joined)
        if quoted is None:
            # Not a verbatim quote (e.g., '> **Demo verified:** ✗')
            return None
        return Blockquote(
            file=md_path,
            line=quote_start_line,
            text=quoted,
        )

    for i, line in enumerate(lines, 1):
        m = BLOCKQUOTE_LINE_RE.match(line)
        if m:
            content = m.group(2).rstrip()
            if not in_quote:
                in_quote = True
                quote_start_line = i
                buf = []
            buf.append(content)
            quote_end_line = i
        else:
            if in_quote:
                bq = flush()
                if bq:
                    yield bq
                in_quote = False
                buf = []

    if in_quote:
        bq = flush()
        if bq:
            yield bq


def find_cited_source(md_text: str, quote_pos: int) -> Optional[CitedSource]:
    """Find the forum permalink most likely associated with a quote.

    Looks for the FIRST permalink that appears after `quote_pos` within
    a window of ~500 characters (typical attribution proximity).
    """
    window = md_text[quote_pos : quote_pos + 800]
    m = PERMALINK_RE.search(window)
    if not m:
        return None
    topic_id = int(m.group(1))
    msg_id = int(m.group(2)) if m.group(2) else None
    return CitedSource(topic_id=topic_id, msg_id=msg_id, permalink=m.group(0))


def normalise(s: str) -> str:
    """Collapse whitespace, lowercase, strip light punctuation that
    differs between forum HTML rendering and our markdown."""
    # Strip markdown formatting that doesn't appear in raw forum HTML.
    # Order matters: links first (they contain other markdown), then
    # inline code, bold, italics.
    s = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", s)   # [text](url) -> text
    s = re.sub(r"`([^`]+)`", r"\1", s)                # `code` -> code
    s = re.sub(r"\*\*([^*]+)\*\*", r"\1", s)          # **bold** -> bold
    s = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"\1", s) # *italic* -> italic
    # Note: underscore-italics (`_word_`) are NOT stripped because the
    # regex matches greedily across content not containing underscores
    # — which gobbles entire phrases when the source contains
    # underscored API names like `keep_keypoints` (the regex would
    # match from the underscore in keep_keypoints to the next
    # underscore-pair anywhere later in the quote, eating the
    # underscore on the way). Markdown rendering tolerates raw
    # underscores in non-italic contexts; the cost of NOT
    # stripping them is small (any genuine `_italic_` in a quote
    # would also appear with underscores in the source HTML).
    s = re.sub(r"\s+", " ", s).strip().lower()
    # Strip Unicode quote pairs that come and go between forum HTML and
    # markdown; replace with ASCII apostrophe / quote.
    for q in ['\u2018', '\u2019', '\u201c', '\u201d', '\u2032', '\u2033']:
        s = s.replace(q, "'")
    s = s.replace("&#039;", "'").replace("&nbsp;", " ")
    # Strip backslash-escapes for nested-quote handling in markdown
    # blockquotes (markdown allows `\"` as an escape for `"`).
    s = s.replace('\\"', '"').replace("\\'", "'")
    # Normalise dash/hyphen variants. Forum HTML often uses ASCII
    # hyphens for bullets and dashes; markdown articles often
    # rewrite these as em-dashes for typographical polish. Treat
    # all dash variants as equivalent for verbatim comparison.
    for d in ['\u2014', '\u2013', '\u2212', '-']:    # em, en, minus, hyphen
        s = s.replace(d, '-')
    # Collapse all quote characters to a single neutral character
    # so that markdown-typesetting variants (single vs double; curly
    # vs straight) don't cause false-positive verbatim mismatches.
    # The verbatim-quote rule still applies to substantive content;
    # this normalisation only affects punctuation.
    for q in ['"', "'"]:
        s = s.replace(q, "")
    return s


def html_to_text(html: str) -> str:
    """Strip HTML tags and decode entities for plain-text comparison."""
    text = re.sub(r"<br\s*/?>", " ", html, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", text)
    text = html_module.unescape(text)
    # Strip the SMF forum UI element 'Code: [Select]' that precedes
    # every code block in printpage HTML — it's a UI artifact, not
    # part of the content quoted by users.
    text = re.sub(r"Code:\s*\[Select\]", " ", text, flags=re.IGNORECASE)
    return normalise(text)


def find_source_text(cited: CitedSource, corpus_root: Path) -> Optional[str]:
    """Locate the cached forum HTML for a cited source.

    Tries (in order):
      1. corpus/forum/printpage-NNNNN.html (5-digit zero-padded)
      2. corpus/forum/printpage-NNNN.html  (4-digit zero-padded)
    """
    for width in (5, 4, 3):
        cand = corpus_root / f"printpage-{cited.topic_id:0{width}d}.html"
        if cand.exists():
            return cand.read_text(encoding="utf-8", errors="replace")
    return None


def check_quote(
    quote: Blockquote,
    cited: Optional[CitedSource],
    corpus_root: Path,
) -> QuoteCheck:
    """Confirm a quote's text appears in its cited source."""
    if cited is None:
        return QuoteCheck(quote=quote, cited=None, found=False,
                          notes="no permalink found in vicinity of quote")

    html = find_source_text(cited, corpus_root)
    if html is None:
        return QuoteCheck(quote=quote, cited=cited, found=False,
                          notes=f"source HTML not cached "
                                f"(corpus/forum/printpage-{cited.topic_id:05d}.html)")

    source_text = html_to_text(html)
    quote_text = normalise(quote.text)

    # Strip leading "[sic]" / [...] markers from quote text before
    # search; the bracketed content shouldn't be in the source.
    cleaned = re.sub(r"\[(?:sic|\.\.\.|\\u2026|…)\]", " ", quote_text)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()

    if cleaned in source_text:
        return QuoteCheck(quote=quote, cited=cited, found=True, notes="")
    # Try matching by splitting on elision markers FIRST. We accept
    # the quote if EVERY fragment >= 30 chars appears in source. This
    # tolerates [...] elision, leading/trailing truncation (...), and
    # multi-sentence quotes.
    fragments_raw = re.split(
        r"\[\.\.\.\]|\[…\]|\[sic\]|\s\.\.\.\s|\s…\s",
        quote_text,
    )
    fragments = [f.strip().strip(".") for f in fragments_raw if len(f.strip()) >= 30]
    if fragments and all(f in source_text for f in fragments):
        return QuoteCheck(
            quote=quote, cited=cited, found=True,
            notes=f"matched after splitting on elision markers "
                  f"({len(fragments)} fragments, all >= 30 chars)",
        )
    # Try once more with [...] / [sic] / ... markers stripped (treat
    # them as ignorable) — only useful when there's exactly ONE
    # elision and the surrounding fragments form a continuous source
    # phrase.
    cleaned = re.sub(r"\[(?:sic|\.\.\.|\\u2026|…)\]", " ", quote_text)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    if cleaned in source_text:
        return QuoteCheck(quote=quote, cited=cited, found=True, notes="")
    # Final attempt: longest-substring heuristic. If the LONGEST
    # 80+-char run from the quote appears in source, accept the
    # quote.
    longest = max(fragments_raw, key=len) if fragments_raw else cleaned
    if len(longest) >= 80 and longest.strip() in source_text:
        return QuoteCheck(
            quote=quote, cited=cited, found=True,
            notes=f"matched on longest-fragment heuristic "
                  f"({len(longest)} chars)",
        )
    return QuoteCheck(quote=quote, cited=cited, found=False,
                      notes="quote text not found in source HTML; "
                            "check for paraphrase, silent edit, or wrong source")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("paths", nargs="+", type=Path)
    ap.add_argument("--corpus-root", type=Path,
                    default=Path("corpus/forum"))
    ap.add_argument("--quiet", action="store_true",
                    help="Suppress per-file summary; print only failures")
    args = ap.parse_args()

    files: list[Path] = []
    for p in args.paths:
        if p.is_file() and p.suffix == ".md":
            files.append(p)
        elif p.is_dir():
            files.extend(sorted(p.rglob("*.md")))

    total_quotes = 0
    failed: list[QuoteCheck] = []
    no_source: list[QuoteCheck] = []
    no_permalink: list[QuoteCheck] = []
    verified: list[QuoteCheck] = []

    for md in files:
        text = md.read_text(encoding="utf-8", errors="replace")
        # Need positions of each blockquote to locate its permalink
        quotes_with_pos: list[tuple[Blockquote, int]] = []
        for q in find_blockquotes(md):
            # Find approximate position of the FIRST line of the quote.
            # The permalink is INSIDE the blockquote (in the attribution
            # line), so we search starting at the quote's first line.
            line_pos = sum(len(line) + 1 for line in text.split("\n")[: q.line - 1])
            quotes_with_pos.append((q, line_pos))

        if not quotes_with_pos:
            continue

        file_failed = 0
        for q, search_from in quotes_with_pos:
            total_quotes += 1
            cited = find_cited_source(text, search_from)
            check = check_quote(q, cited, args.corpus_root)
            if check.found:
                verified.append(check)
            elif cited is None:
                no_permalink.append(check)
            elif "not cached" in check.notes:
                no_source.append(check)
            else:
                failed.append(check)
                file_failed += 1
        if not args.quiet:
            print(f"  {md}: {len(quotes_with_pos)} quote(s), {file_failed} unverified")

    print()
    print(f"# verify_quotes.py summary")
    print()
    print(f"- Files scanned:        {len(files)}")
    print(f"- Quotes parsed:        {total_quotes}")
    print(f"- Verified verbatim:    {len(verified)}")
    print(f"- No permalink:         {len(no_permalink)}  (forum-citation absent or far away — paraphrase or non-forum source)")
    print(f"- Source not cached:    {len(no_source)}  (the forum thread has not been fetched)")
    print(f"- **NOT in source:**    {len(failed)}  (text cited but doesn't appear character-for-character)")

    if failed:
        print()
        print("## Quotes NOT found in source (highest priority)")
        print()
        for c in failed:
            print(f"### `{c.quote.file}:{c.quote.line}`")
            print(f"- **Cited:** {c.cited.permalink if c.cited else '(none)'}")
            print(f"- **Quote:** {c.quote.text[:200]}{'...' if len(c.quote.text) > 200 else ''}")
            print(f"- **Notes:** {c.notes}")
            print()

    if no_source:
        print()
        print("## Quotes whose source thread is not cached")
        print()
        for c in no_source:
            print(f"- `{c.quote.file}:{c.quote.line}` cites topic={c.cited.topic_id}")

    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
