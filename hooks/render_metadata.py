"""MkDocs hook that renders article frontmatter as a visible
bullet list right after the H1.

Configured in mkdocs.yml as:
    hooks:
      - hooks/render_metadata.py

Renders the following frontmatter fields (when present) as a
plain bullet list with bold labels (the older form, which
loses no information but does not add a Material admonition
icon or any other decorative chrome):

    status, applies_to, edition, last_reviewed, diataxis, confidence

Only acts on substantive articles (those with `title:` AND
`status:` in frontmatter). Index pages and reference pages
without those fields are left untouched.

Output example after `# Title`:

    - **Status:** unverified
    - **Applies to:** Metashape Pro 2.x — and unchanged from PhotoScan 1.x
    - **Edition:** Pro
    - **Diátaxis:** how-to
    - **Confidence:** medium
    - **Last reviewed:** 2026-05-23
"""
from __future__ import annotations

import re

# Fields to render and their display order / human label.
DISPLAY_FIELDS: list[tuple[str, str]] = [
    ("status", "Status"),
    ("applies_to", "Applies to"),
    ("edition", "Edition"),
    ("diataxis", "Diátaxis"),
    ("confidence", "Confidence"),
    ("last_reviewed", "Last reviewed"),
]


def on_page_markdown(markdown: str, *, page, config, files):
    """Insert an Article-info bullet list after the page's H1."""
    meta = page.meta or {}

    # Only render for substantive articles — those with both
    # `status` and `applies_to` in frontmatter.
    if "status" not in meta or "applies_to" not in meta:
        return markdown

    # Build the bullet list.
    rows: list[str] = []
    for key, label in DISPLAY_FIELDS:
        value = meta.get(key)
        if value is None or str(value).strip() == "":
            continue
        # MkDocs may parse `applies_to:` as a string with newlines;
        # collapse whitespace.
        value_str = str(value).strip()
        value_str = re.sub(r"\s+", " ", value_str)
        rows.append(f"- **{label}:** {value_str}")

    if not rows:
        return markdown

    block = "\n".join(["", *rows, ""])

    # Insert right after the first `# Title` line.
    h1_match = re.search(r"^# .+$", markdown, re.MULTILINE)
    if not h1_match:
        return markdown

    insert_at = h1_match.end()
    return markdown[:insert_at] + "\n" + block + markdown[insert_at:]
