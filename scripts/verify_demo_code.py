#!/usr/bin/env python3
"""Tier 1 verification: extract Python code blocks from markdown and
test every Metashape.* API reference against the local install.

This check verifies:

    "Build a scripts/verify_demo_code.py that extracts every Python
    code block from a markdown file, parses every Metashape.X.method
    and obj.attribute reference, and tests each via hasattr against
    the local install."

For each Python code block found, this script:

  1. Parses the block as Python AST (silently skips blocks that
     don't parse — they are typically pseudo-code or partial
     snippets, which is acceptable for documentation).
  2. Walks the AST collecting every Attribute and Name reference
     that starts with `Metashape.` or matches a known
     instance-method pattern (e.g. `chunk.matchPhotos`).
  3. Resolves each reference against the local Metashape install
     via `hasattr` chain.
  4. Reports any reference that doesn't resolve.

Usage:

    ./.venv/bin/python scripts/verify_demo_code.py docs/workflow/<path>/<article>.md

    # or audit the whole corpus:
    ./.venv/bin/python scripts/verify_demo_code.py docs/

Exits non-zero if any reference fails to resolve. Suitable for
pre-commit hooks.

Output is markdown; paste into PR descriptions or commit messages.
"""

from __future__ import annotations

import argparse
import ast
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Iterator, NamedTuple

DEFAULT_PYTHON = os.environ.get(
    "METASHAPE_PYTHON",
    os.path.expanduser("~/.pyenv/versions/Metashape-2.2/bin/python"),
)

# Match fenced code blocks tagged ```python or ```py
PYTHON_FENCE_RE = re.compile(
    r"^```(?:python|py)\s*\n(.*?)^```\s*$",
    re.DOTALL | re.MULTILINE,
)


class CodeBlock(NamedTuple):
    """A Python code block extracted from a markdown file."""

    file: Path
    line: int  # 1-based line number where the ``` opener sits
    source: str


class Reference(NamedTuple):
    """An API reference parsed out of a code block."""

    block: CodeBlock
    line_in_block: int  # 1-based line within the block's source
    dotted_path: str    # e.g. "Metashape.Chunk.matchPhotos" or "chunk.matchPhotos"


def find_code_blocks(md_path: Path) -> Iterator[CodeBlock]:
    """Yield every Python code block in a markdown file."""
    text = md_path.read_text(encoding="utf-8", errors="replace")
    for m in PYTHON_FENCE_RE.finditer(text):
        # Compute the 1-based line of the ``` opener
        line = text[: m.start()].count("\n") + 1
        yield CodeBlock(file=md_path, line=line, source=m.group(1))


# Common instance-name → class mapping. When a code block writes
# `chunk.matchPhotos(...)` we need to know that `chunk` is a
# `Metashape.Chunk` so we can introspect `Metashape.Chunk.matchPhotos`.
INSTANCE_TO_CLASS = {
    "chunk": "Chunk",
    "doc": "Document",
    "document": "Document",
    "camera": "Camera",
    "cam": "Camera",
    "sensor": "Sensor",
    "marker": "Marker",
    "shape": "Shape",
    "polygon": "Shape",
    "model": "Model",
    "tiled_model": "TiledModel",
    "point_cloud": "PointCloud",
    "depth_map": "DepthMap",
    "raster": "Raster",
    "orthomosaic": "Orthomosaic",
    "dem": "Elevation",
    "image": "Image",
}


def collect_references(block: CodeBlock) -> list[Reference]:
    """Walk a Python code block AST and collect Metashape.* references.

    For an Attribute chain like `chunk.region.center`, we only collect
    the FIRST attribute (`chunk.region`) — checking deeper into the
    chain would require type-tracking through return values, which is
    out of scope for a static introspection check. The first attribute
    is the most useful regression sentinel: it catches renamed or
    removed methods without false-positive on legitimate instance
    attribute chains.

    Returns a list of references with their dotted paths. References
    that cannot be parsed (because the block isn't valid Python) are
    silently skipped — the block is usually pseudo-code in that case.
    """
    refs: list[Reference] = []
    seen_in_block: set[str] = set()
    try:
        tree = ast.parse(block.source)
    except SyntaxError:
        return refs

    for node in ast.walk(tree):
        if not isinstance(node, ast.Attribute):
            continue
        # Build the dotted path bottom-up
        parts: list[str] = []
        cur: ast.AST = node
        while isinstance(cur, ast.Attribute):
            parts.append(cur.attr)
            cur = cur.value
        if not isinstance(cur, ast.Name):
            continue
        parts.append(cur.id)
        parts.reverse()

        # Truncate to first attribute access:
        #   chunk.region.center            -> chunk.region
        #   Metashape.Chunk.matchPhotos    -> Metashape.Chunk.matchPhotos (depth 3 unchanged)
        #   Metashape.app.document.chunk   -> Metashape.app
        if parts[0] == "Metashape":
            # Keep up to depth 3 for Metashape.Class.method patterns.
            # `Metashape.app.document.chunk` becomes `Metashape.app`
            # because `app` is an instance attribute on the Metashape
            # module, not a class.
            if len(parts) >= 3 and parts[1][0].isupper():
                # Metashape.Chunk.matchPhotos — class.method
                truncated = ".".join(parts[:3])
            else:
                # Metashape.app — module attribute
                truncated = ".".join(parts[:2])
        elif parts[0] in INSTANCE_TO_CLASS:
            # chunk.region or chunk.matchPhotos — instance.method/attr
            truncated = ".".join(parts[:2])
        else:
            continue

        if truncated in seen_in_block:
            continue
        seen_in_block.add(truncated)

        refs.append(
            Reference(
                block=block,
                line_in_block=node.lineno,
                dotted_path=truncated,
            )
        )
    return refs


def normalise_to_metashape(dotted: str) -> str:
    """Map an instance-name reference to its Metashape.* equivalent.

    `chunk.matchPhotos` → `Metashape.Chunk.matchPhotos`
    `Metashape.Chunk.matchPhotos` → unchanged
    """
    parts = dotted.split(".")
    if parts[0] == "Metashape":
        return dotted
    cls = INSTANCE_TO_CLASS.get(parts[0])
    if cls is None:
        return dotted
    return ".".join(["Metashape", cls] + parts[1:])


def check_references(
    refs: list[Reference],
    metashape_python: str = DEFAULT_PYTHON,
) -> dict[str, bool]:
    """Run an out-of-process Python child to check every reference.

    Returns {dotted_path: alive} dict. Failures (reference doesn't
    resolve) are False; successes are True.
    """
    if not refs:
        return {}

    # De-duplicate while preserving order
    seen: set[str] = set()
    unique_paths: list[str] = []
    for r in refs:
        normalised = normalise_to_metashape(r.dotted_path)
        if normalised not in seen:
            seen.add(normalised)
            unique_paths.append(normalised)

    code_lines = [
        "import Metashape",
        "import sys",
        "results = []",
    ]
    for path in unique_paths:
        # Walk the dotted path with hasattr; first failure → False
        code_lines.append(
            f"try:\n"
            f"    obj = Metashape\n"
            f"    for part in {path.split('.')[1:]!r}:\n"
            f"        obj = getattr(obj, part)\n"
            f"    results.append(({path!r}, True))\n"
            f"except AttributeError:\n"
            f"    results.append(({path!r}, False))"
        )
    code_lines.append('for r in results: print(f"{r[0]}\\t{r[1]}")')

    code = "\n".join(code_lines)
    try:
        proc = subprocess.run(
            [metashape_python, "-c", code],
            capture_output=True,
            text=True,
            timeout=30,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired) as e:
        sys.stderr.write(f"  ERROR: cannot run introspection: {e}\n")
        return {p: False for p in unique_paths}

    out: dict[str, bool] = {}
    for line in proc.stdout.strip().split("\n"):
        if "\t" in line:
            path, status = line.split("\t", 1)
            out[path] = status == "True"
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("paths", nargs="+", type=Path,
                    help="Markdown files or directories to scan")
    ap.add_argument("--metashape-python", default=DEFAULT_PYTHON,
                    help="Path to a Python interpreter with Metashape importable")
    ap.add_argument("--quiet", action="store_true",
                    help="Suppress the per-file summary; print only failures")
    args = ap.parse_args()

    # Resolve paths to a flat list of .md files
    files: list[Path] = []
    for p in args.paths:
        if p.is_file() and p.suffix == ".md":
            files.append(p)
        elif p.is_dir():
            files.extend(sorted(p.rglob("*.md")))

    total_blocks = 0
    total_refs = 0
    failed_refs: list[tuple[Reference, str]] = []

    for md in files:
        blocks = list(find_code_blocks(md))
        if not blocks:
            continue
        all_refs: list[Reference] = []
        for block in blocks:
            all_refs.extend(collect_references(block))
        if not all_refs:
            if not args.quiet:
                print(f"  {md}: {len(blocks)} block(s), 0 references")
            continue
        results = check_references(all_refs, args.metashape_python)
        file_failures: list[Reference] = []
        for ref in all_refs:
            normalised = normalise_to_metashape(ref.dotted_path)
            if not results.get(normalised, False):
                file_failures.append(ref)
                failed_refs.append((ref, normalised))
        total_blocks += len(blocks)
        total_refs += len(all_refs)
        if not args.quiet:
            print(
                f"  {md}: {len(blocks)} block(s), {len(all_refs)} ref(s), "
                f"{len(file_failures)} unresolved"
            )

    print()
    print(f"# verify_demo_code.py summary")
    print()
    print(f"- Files scanned: {len(files)}")
    print(f"- Code blocks found: {total_blocks}")
    print(f"- API references parsed: {total_refs}")
    print(f"- Unresolved references: {len(failed_refs)}")

    if failed_refs:
        print()
        print("## Unresolved references")
        print()
        print("| File | Line | Reference | Normalised |")
        print("|------|-----:|-----------|------------|")
        for ref, normalised in failed_refs:
            print(
                f"| `{ref.block.file}` | "
                f"{ref.block.line + ref.line_in_block} | "
                f"`{ref.dotted_path}` | `{normalised}` |"
            )
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
