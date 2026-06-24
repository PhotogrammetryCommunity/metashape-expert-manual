#!/usr/bin/env python3
"""Fix Mermaid diagrams that contain HTML tags inside unquoted labels.

The mkdocs-mermaid2-plugin (v1.2.x) wraps the diagram source in
`<pre class="mermaid"><code>...</code></pre>` without escaping HTML
entities. The browser parses HTML inside `<code>`, so:

    A[Label with <br/> break]

becomes (in textContent that mermaid sees):

    A[Label with  break]

— the `<br/>` is consumed as an HTML BR element. Worse: literal
parentheses inside `[...]` (or `{...}`) are valid Mermaid syntax
errors because they look like alternate shape modifiers.

The fix:
1. Wrap label content in double quotes — `[Label]` → `["Label"]`.
2. HTML-escape any `<...>` tags inside labels — `<br/>` → `&lt;br/&gt;`.

This script applies both transformations to every fenced
`mermaid` block in the markdown files passed as arguments.

Idempotent: running it twice on the same file yields the same
result (already-quoted labels are not re-quoted; already-escaped
entities are not re-escaped).
"""
from __future__ import annotations
import re
import sys
from pathlib import Path

# Tags that need escaping inside Mermaid quoted labels.
TAGS_TO_ESCAPE = ["br", "br/", "i", "/i", "b", "/b", "code", "/code"]


def transform_label(label: str) -> str:
    """Transform a Mermaid label (the contents inside [...] or {...})
    so it survives the mkdocs-mermaid2 + browser pipeline.

    The label may or may not already be quoted with " characters.
    """
    # If already quoted, the contents inside the quotes still need
    # tag-escaping (in case we missed it earlier).
    inner = label
    already_quoted = label.startswith('"') and label.endswith('"')
    if already_quoted:
        inner = label[1:-1]

    # Escape HTML tags (browser-strips these when extracting
    # textContent from <code>).
    for tag in TAGS_TO_ESCAPE:
        inner = inner.replace(f"<{tag}>", f"&lt;{tag}&gt;")

    # Re-quote.
    return f'"{inner}"'


def transform_block(source: str) -> str:
    """Transform one Mermaid block."""
    # Match unquoted square-bracket labels: A[...] or A[Anything];
    # do not touch ["..."] (already quoted; just recurse to escape
    # inner tags).
    def square_replacer(m):
        prefix = m.group(1)   # the node id (no `[`)
        body = m.group(2)
        return f"{prefix}[{transform_label(body)}]"

    # Square-bracket labels (A[...] or B[...]).
    # The label body cannot contain unescaped `]`. Allow `&rpar;`
    # entities inside.
    source = re.sub(
        r"(\b\w+)\[([^\]]+)\]",
        square_replacer,
        source,
    )

    # Curly-brace labels (A{...} for diamond/decision shapes).
    def curly_replacer(m):
        prefix = m.group(1)   # the node id (no `{`)
        body = m.group(2)
        return f"{prefix}{{{transform_label(body)}}}"

    source = re.sub(
        r"(\b\w+)\{([^{}]+)\}",
        curly_replacer,
        source,
    )

    return source


# Match ```mermaid ... ``` blocks; capture the body.
MERMAID_BLOCK_RE = re.compile(
    r"^(```mermaid\s*\n)(.*?)(\n```)$",
    re.DOTALL | re.MULTILINE,
)


def transform_file(path: Path) -> bool:
    """Returns True if the file changed."""
    text = path.read_text(encoding="utf-8")

    def block_replacer(m):
        before = m.group(1)
        body = m.group(2)
        after = m.group(3)
        new_body = transform_block(body)
        return f"{before}{new_body}{after}"

    new_text = MERMAID_BLOCK_RE.sub(block_replacer, text)
    if new_text != text:
        path.write_text(new_text, encoding="utf-8")
        return True
    return False


def main():
    args = sys.argv[1:]
    if not args:
        print("usage: fix_mermaid_labels.py <path...>", file=sys.stderr)
        sys.exit(2)

    files = []
    for arg in args:
        p = Path(arg)
        if p.is_file() and p.suffix == ".md":
            files.append(p)
        elif p.is_dir():
            files.extend(p.rglob("*.md"))

    changed = 0
    for f in files:
        if transform_file(f):
            print(f"  modified: {f}")
            changed += 1
    print(f"\n{changed} file(s) modified out of {len(files)} scanned.")


if __name__ == "__main__":
    main()
