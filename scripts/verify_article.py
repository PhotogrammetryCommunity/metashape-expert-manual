"""Tier 1 verification helper.

Runs the Tier 1 automated-verification pass:

  1. Find every `Metashape.Class.method` reference in the article and
     print its signature/docstring from the local Metashape Python API
     so the author can confirm kwargs, defaults, and return types.
     Cross-check each reference against the *Python API Change Log*
     (chapter 3 of the Python API PDF) so renames are surfaced even
     when the current name introspects fine.
  2. Find suspected GUI menu paths (heuristic regex) and search them in
     the locally mirrored Pro user-manual PDF, reporting matched lines
     and obvious mismatches. Cross-check each menu leaf against the
     GUI changelog so historical renames are surfaced.
  3. Sweep for forum-era terminology that has shifted in the current
     version (e.g. "dense cloud", "gradual selection") and warn.

The output is markdown formatted to drop directly into a PR
description's *Automated verification log* section.

Usage:
    ./.venv/bin/python scripts/verify_article.py docs/workflow/<path>/article.md

Optional flags:
    --metashape-python <path>     # default: ~/.pyenv/versions/Metashape-2.2/bin/python
    --manual <path>               # default: corpus/official/metashape-pro-2_3_en.pdf
    --api-changelog <path>        # default: corpus/official/metashape-python-api-2_3_1.pdf
                                  # (the Python API PDF includes the API change log
                                  # as chapter 3)
    --gui-changelog <path>        # default: corpus/official/metashape-changelog.pdf
    --no-introspect               # skip step 1 (faster smoke test)
    --no-pdf                      # skip steps 2-3 (when manual PDF is missing)
    --no-changelog                # skip changelog cross-checks

The script reads but does not modify the article.
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

# ────────────────────────────────────────────────────────────────────────
# Patterns
# ────────────────────────────────────────────────────────────────────────

# Match Metashape.Class.method or Metashape.Class.method.thing references.
# We strip trailing punctuation when used in prose. Lower-cased starts (like
# `Metashape.app.document`) are filtered out below — they are properties on
# singletons, not methods to introspect.
API_RE = re.compile(r"\bMetashape\.[A-Z][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*){1,3}")

# Match GUI menu paths in the form  *Foo → Bar*  or  *Foo → Bar → Baz*
# (italic wrapper, Unicode arrow, two-to-four segments). We deliberately
# require the `→` character to keep false positives low; ASCII `->` style
# is rare in this manual but easy to add if it shows up.
MENU_RE = re.compile(
    r"\*\s*"
    r"([A-Z][A-Za-z0-9 '/-]+"
    r"(?:\s*→\s*[A-Za-z0-9 '/-]+){1,3}"
    r"(?:…|\.\.\.)?)"
    r"\s*\*"
)

# Forum-era terms that have moved in 2.x. Flag for the author.
TERMINOLOGY_SHIFTS = {
    "dense cloud": "point cloud",
    "Build Dense Cloud": "Build Point Cloud",
    "Gradual Selection": "Clean Tie Points",
    "sparse cloud": "tie point cloud",
    "PhotoScan": "Metashape (post-2019)",
}

# ────────────────────────────────────────────────────────────────────────
# Helpers
# ────────────────────────────────────────────────────────────────────────


def heading(s: str, char: str = "—") -> str:
    return f"\n## {s}\n"


def code_block(content: str, lang: str = "text") -> str:
    return f"```{lang}\n{content.rstrip()}\n```"


def collapse_whitespace(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


def _pdf_text(pdf_path: Path) -> str | None:
    """Extract text from a PDF using pdftotext -layout. Cached at the
    module level via lru_cache below."""
    if not pdf_path.exists():
        return None
    if shutil.which("pdftotext") is None:
        return None
    return subprocess.run(
        ["pdftotext", "-layout", str(pdf_path), "-"],
        capture_output=True,
        text=True,
        check=False,
    ).stdout


# Cache: pdftotext is non-trivial; we call it many times per article.
import functools
_pdf_text = functools.lru_cache(maxsize=8)(_pdf_text)


# Match changelog mention of a term (with version context). The
# version context is found by walking backwards to the nearest
# `version X.Y` (or similar) header.
_CHANGELOG_VERB_RE = re.compile(
    r"\b(?:Renamed|Removed|Added|Moved|Replaced|Deprecated)\b"
)
_CHANGELOG_VERSION_RE = re.compile(
    r"(?:Metashape\s+)?version\s+(\d+\.\d+(?:\.\d+)?)|^Version\s+(\d+\.\d+(?:\.\d+)?)",
    re.IGNORECASE | re.MULTILINE,
)


def changelog_history(term: str, pdf_text: str | None, *, max_hits: int = 5) -> list[tuple[str, str]]:
    """Find changelog lines mentioning `term` together with a verb
    like Renamed/Removed/Added/Moved. Returns a list of
    (version, line) tuples, most recent first by source order
    in the changelog (latest versions appear first).
    """
    if not pdf_text:
        return []
    lines = pdf_text.splitlines()
    term_re = re.compile(r"\b" + re.escape(term) + r"\b", re.IGNORECASE)
    out: list[tuple[str, str]] = []
    for i, line in enumerate(lines):
        if not term_re.search(line):
            continue
        if not _CHANGELOG_VERB_RE.search(line):
            continue
        # Walk backwards up to 400 lines for a 'version X.Y(.Z)' anchor.
        version = "?"
        for j in range(i, max(0, i - 400), -1):
            m = _CHANGELOG_VERSION_RE.search(lines[j])
            if m:
                version = m.group(1) or m.group(2) or "?"
                break
        out.append((version, collapse_whitespace(line)))
        if len(out) >= max_hits:
            break
    return out


def _parse_version(s: str) -> tuple[int, int, int]:
    """Parse 'X', 'X.Y' or 'X.Y.Z' into a 3-tuple. Missing components
    pad with 0 so that ``2.0`` and ``2.0.0`` compare equal."""
    parts = re.findall(r"\d+", s)[:3]
    while len(parts) < 3:
        parts.append("0")
    return tuple(int(p) for p in parts)


def applies_to_floor(article_text: str) -> str | None:
    """Extract the minimum Metashape version from the article's
    `applies_to:` line. Returns the version string or None.

    Tolerates the markdown bold-list form
    ``> - **applies_to:** Metashape Pro 2.2.1+ — …`` as well as a
    plain ``applies_to: 2.2.1+`` style.
    """
    pattern = re.compile(
        # the field name, possibly bracketed by asterisks
        r"applies[_ ]?to"
        # any mix of asterisks / whitespace, then a colon or dash
        r"[\*\s]*[:\-]"
        # the value, optionally still inside bold markers
        r"[\*\s]*(.+)",
        re.IGNORECASE,
    )
    for line in article_text.splitlines():
        m = pattern.search(line)
        if not m:
            continue
        # Stop the value at the first sentence-ending mark to avoid
        # picking up later "Components view requires version 1.7" tail
        # text as a primary version constraint.
        value = re.split(r"\.\s|\—|—", m.group(1), maxsplit=1)[0]
        versions = re.findall(r"\b(\d+\.\d+(?:\.\d+)?)\b", value)
        if versions:
            return min(versions, key=_parse_version)
    return None


def find_introduction_version(ref: str, pdf_text: str | None) -> str | None:
    """Given a reference like 'Metashape.Chunk.cleanTiePoints', find the
    most recent version where that name was introduced — either by
    'Added' or by 'Renamed <old> to <ref>'. Returns version string or
    None if no introduction event is recorded.

    The *most recent* introduction is what bounds the lower edge of the
    name's lifetime. (e.g. if X was renamed to Y in 1.6 and Y was
    renamed again to Z in 2.0, then Z only exists since 2.0.)

    Matching is deliberately strict to avoid false positives:

    - ``Added <qualifier?>.<leaf>(()? )(method|class|attribute|enum)``
      counts — the `Added` action introduces leaf as the subject.
    - ``Renamed <old> to <qualifier?>.<leaf>(())?`` counts — leaf is
      the rename's destination.
    - ``Added <X> argument to <Y>.<leaf>() method`` does **not** count
      for leaf — only `<X>` is being added; `<leaf>` is the target.
    """
    if not pdf_text:
        return None

    parts = ref.split(".")
    qualified = ".".join(parts[-2:]) if len(parts) >= 3 else parts[-1]
    leaf = parts[-1]

    def _scan(needle: str, *, expected_parent: str | None = None) -> list[str]:
        # Patterns for an introduction event of `needle`:
        #   `Added <…>needle<…>` — needle is the subject of an Added.
        #   `Renamed <old> to <…>needle` — needle is the destination
        #     of a Renamed.
        # Reject when `needle` is the **target** of a "to <needle>"
        # phrase in an "Added" line (e.g. "Added X argument to
        # Chunk.alignCameras() method" — leaf X is being added,
        # `alignCameras` is the target, not the subject).
        #
        # When `expected_parent` is provided (leaf-fallback mode), three
        # additional rejection rules guard against unrelated classes
        # whose attributes happen to share the leaf name:
        #
        #   1. Reject when `to <OtherClass> class` appears (this is an
        #      addition to a different class, not to expected_parent).
        #   2. Reject when `to <expected_parent>.<word>` appears (the
        #      addition is to a method/class on parent, not to parent
        #      directly — e.g. "Added crs argument to
        #      Chunk.importCameras() method" should not introduce
        #      Chunk.crs).
        #   3. Reject when `<OtherClass>.<leaf>` appears with
        #      OtherClass != expected_parent (e.g. "Added Model.crs"
        #      should not introduce Chunk.crs).
        #
        # Matched **case-sensitively** because Python identifiers are
        # case-sensitive. `Chunk.alignCameras` (method) and
        # `Tasks.AlignCameras` (class) are different things.
        needle_re = re.compile(r"\b" + re.escape(needle) + r"(?:\(\))?\b")
        renamed_to_re = re.compile(
            r"\bRenamed\b\s.*?\bto\b\s+(?:[A-Za-z_][A-Za-z0-9_]*\.)*"
            + re.escape(needle)
            + r"(?:\(\))?\b"
        )
        # `to <maybe-qualifier>.needle` — needle is a target, not subject.
        to_target_re = re.compile(
            r"\bto\b\s+(?:[A-Za-z_][A-Za-z0-9_]*\.)*"
            + re.escape(needle)
            + r"\b"
        )
        # Leaf-fallback parent-context guards.
        to_class_re = re.compile(r"\bto\s+([A-Z]\w*)\s+class\b") if expected_parent else None
        to_parent_method_re = (
            re.compile(r"\bto\s+" + re.escape(expected_parent) + r"\.\w+")
            if expected_parent else None
        )
        other_qualified_re = (
            re.compile(r"\b([A-Z]\w*)\." + re.escape(needle) + r"\b")
            if expected_parent else None
        )

        introductions: list[str] = []
        lines = pdf_text.splitlines()
        for i, line in enumerate(lines):
            if not needle_re.search(line):
                continue

            renamed_to_hit = bool(renamed_to_re.search(line))
            added_intro_hit = (
                "Added " in line
                and not renamed_to_hit
                and not to_target_re.search(line)
            )

            if not (renamed_to_hit or added_intro_hit):
                continue

            # Leaf-fallback parent-context guards.
            if expected_parent is not None:
                # Rule 1: "to <Other> class" with Other != parent
                m = to_class_re.search(line)
                if m and m.group(1) != expected_parent:
                    continue
                # Rule 2: "to <parent>.<word>" — leaf added to a method on parent
                if to_parent_method_re.search(line):
                    continue
                # Rule 3: "<Other>.<leaf>" with Other != parent
                rejected = False
                for qm in other_qualified_re.finditer(line):
                    if qm.group(1) != expected_parent:
                        rejected = True
                        break
                if rejected:
                    continue

            for j in range(i, max(0, i - 400), -1):
                m = _CHANGELOG_VERSION_RE.search(lines[j])
                if m:
                    introductions.append(m.group(1) or m.group(2))
                    break
        return introductions

    # For longer refs (e.g. Metashape.TiePoints.Filter.Criterion), the
    # changelog often refers to the class via a *different* qualifier
    # (here: TiePoints.Criterion, not Filter.Criterion). Try several
    # qualified forms before falling back to the leaf alone.
    candidates: list[tuple[str, str | None]] = [(qualified, None)]
    if len(parts) >= 4:
        candidates.append((f"{parts[-3]}.{leaf}", None))
    if leaf != qualified.split(".")[-1] or len(parts) <= 2:
        # Only fall back to leaf with parent-context guards.
        candidates.append((leaf, parts[-2] if len(parts) >= 2 else None))
    elif len(parts) >= 3:
        # Standard case: leaf fallback with parent-context guard.
        candidates.append((leaf, parts[-2]))

    for needle, parent_guard in candidates:
        intros = _scan(needle, expected_parent=parent_guard)
        if intros:
            return max(intros, key=_parse_version)
    return None


# ────────────────────────────────────────────────────────────────────────
# Step 1 — Python API introspection
# ────────────────────────────────────────────────────────────────────────


def introspect_api(article_text: str, py_path: str, api_changelog_pdf: Path | None) -> str:
    refs = sorted(set(API_RE.findall(article_text)))
    if not refs:
        return "\n*No `Metashape.X.Y` references found in the article.*\n"

    out: list[str] = []
    out.append(f"\nFound **{len(refs)}** unique `Metashape.*` reference(s).\n")
    out.append(f"Introspecting against: `{py_path}`\n")

    # Build a small Python program that imports each ref and prints
    # signature + docstring. Run it in one subprocess for efficiency.
    program = (
        "import inspect, sys, importlib\n"
        "import Metashape\n"
        "refs = [\n"
        + "\n".join(f"    {ref!r}," for ref in refs)
        + "\n]\n"
        "for ref in refs:\n"
        "    parts = ref.split('.')\n"
        "    obj = Metashape\n"
        "    try:\n"
        "        for p in parts[1:]:\n"
        "            obj = getattr(obj, p)\n"
        "    except AttributeError as e:\n"
        "        print(f'### {ref}')\n"
        "        print(f'  ❌ NOT FOUND ({e})')\n"
        "        print()\n"
        "        continue\n"
        "    print(f'### {ref}')\n"
        "    try:\n"
        "        sig = str(inspect.signature(obj))\n"
        "        print(f'  signature: {sig}')\n"
        "    except (TypeError, ValueError):\n"
        "        pass\n"
        "    doc = inspect.getdoc(obj) or ''\n"
        "    if doc:\n"
        "        for line in doc.splitlines()[:8]:\n"
        "            print(f'  doc: {line}')\n"
        "    print()\n"
    )

    try:
        result = subprocess.run(
            [py_path, "-"],
            input=program,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
    except FileNotFoundError:
        return f"\n❌ **Metashape Python not found at `{py_path}`.**\n\nSkipping introspection. Use `--no-introspect` or `--metashape-python <path>`.\n"

    out.append(code_block((result.stdout + result.stderr).strip()))

    # Changelog cross-check: for each ref, look up the leaf identifier
    # (the last dotted segment) in the Python API change log. Surfaces
    # rename history *even when introspection succeeded* — useful for
    # the article's caveats.
    if api_changelog_pdf is not None:
        api_text = _pdf_text(api_changelog_pdf)
        if api_text is None:
            out.append(f"\n_API change log not available at `{api_changelog_pdf}`; skipping cross-check._\n")
        else:
            out.append("\n#### Python API change-log cross-check\n")
            any_hits = False
            for ref in refs:
                leaf = ref.rsplit(".", 1)[-1]
                hits = changelog_history(leaf, api_text)
                if hits:
                    any_hits = True
                    out.append(f"- **`{ref}`** — change-log mentions of `{leaf}`:")
                    for version, line in hits:
                        out.append(f"    - `[v{version}]` {line[:140]}")
            if not any_hits:
                out.append("\n_No rename/remove entries in the Python API change log for any reference in the article._\n")

            # applies_to consistency check: warn when a reference was
            # introduced (Added or Renamed-to its current name) at a
            # version *later* than the article's applies_to floor.
            article_floor = applies_to_floor(article_text)
            out.append("\n#### `applies_to` consistency check\n")
            if article_floor is None:
                out.append("\n_Could not parse an `applies_to:` floor from the article preamble; skipping._\n")
            else:
                out.append(f"\nArticle's declared `applies_to` floor: **{article_floor}**\n")
                violations: list[tuple[str, str]] = []
                ok: list[tuple[str, str | None]] = []
                for ref in refs:
                    intro_v = find_introduction_version(ref, api_text)
                    if intro_v and _parse_version(intro_v) > _parse_version(article_floor):
                        violations.append((ref, intro_v))
                    else:
                        ok.append((ref, intro_v))
                if violations:
                    out.append("\n⚠️ **Mismatch — these references require a later version than the article claims:**\n")
                    for ref, intro_v in violations:
                        out.append(
                            f"- `{ref}` was introduced in **{intro_v}**, "
                            f"but `applies_to` lists {article_floor} as the floor. "
                            f"Either bump `applies_to` to {intro_v}+, or note "
                            f"the version constraint in the article and provide "
                            f"a fallback for older versions."
                        )
                else:
                    out.append("\n✓ All `Metashape.*` references are consistent with the article's "
                               f"`applies_to: {article_floor}+` floor (or the change log records no "
                               "introduction event for them, meaning they predate the recorded history).\n")

    return "\n".join(out)


# ────────────────────────────────────────────────────────────────────────
# Step 2 — GUI menu-path verification against the local PDF
# ────────────────────────────────────────────────────────────────────────


def verify_menu_paths(article_text: str, pdf_path: Path, gui_changelog_pdf: Path | None) -> str:
    if not pdf_path.exists():
        return f"\n❌ **Manual PDF not found at `{pdf_path}`.**\n\nSkipping menu-path verification.\n"

    if shutil.which("pdftotext") is None:
        return "\n❌ **`pdftotext` not on PATH.**\n\nInstall via `brew install poppler` or skip with `--no-pdf`.\n"

    paths = sorted({collapse_whitespace(m) for m in MENU_RE.findall(article_text)})
    if not paths:
        return "\n*No GUI menu paths found in the article.*\n"

    text = _pdf_text(pdf_path)
    out: list[str] = [f"\nFound **{len(paths)}** suspected GUI menu path(s) in the article.\n"]
    out.append(f"Searching: `{pdf_path}`\n")

    leaves: list[str] = []
    for path in paths:
        leaf = re.split(r"\s*[→>]\s*", path)[-1].rstrip(". …")
        if not leaf or len(leaf) < 3:
            continue
        leaves.append(leaf)
        pattern = re.escape(leaf)
        hits = [ln for ln in (text or "").splitlines() if re.search(pattern, ln, re.IGNORECASE)]
        out.append(f"\n#### `{path}`")
        if not hits:
            out.append("  - ❌ no hits in the user manual — verify the menu label is correct")
        else:
            out.append(f"  - ✓ {len(hits)} hit(s); first 3:")
            for ln in hits[:3]:
                out.append(f"    > `{collapse_whitespace(ln)[:140]}`")

    # Changelog cross-check: surfaces historical renames of these
    # menu labels (e.g. *Gradual Selection* → *Clean Tie Points*).
    if gui_changelog_pdf is not None:
        gui_text = _pdf_text(gui_changelog_pdf)
        if gui_text is None:
            out.append(f"\n_GUI changelog not available at `{gui_changelog_pdf}`; skipping cross-check._\n")
        else:
            out.append("\n#### GUI change-log cross-check\n")
            any_hits = False
            for leaf in leaves:
                hits = changelog_history(leaf, gui_text)
                if hits:
                    any_hits = True
                    out.append(f"- **`{leaf}`** — change-log mentions:")
                    for version, line in hits:
                        out.append(f"    - `[v{version}]` {line[:140]}")
            if not any_hits:
                out.append("\n_No rename/remove entries in the GUI changelog for any menu leaf in the article._\n")

    return "\n".join(out) + "\n"


# ────────────────────────────────────────────────────────────────────────
# Step 3 — Terminology-shift sweep
# ────────────────────────────────────────────────────────────────────────


def terminology_sweep(article_text: str) -> str:
    out: list[str] = []
    flagged: list[tuple[str, str, int]] = []
    for old, new in TERMINOLOGY_SHIFTS.items():
        # Count case-insensitive occurrences, but preserve original
        # casing in the report.
        matches = [m.group(0) for m in re.finditer(re.escape(old), article_text, re.IGNORECASE)]
        if matches:
            flagged.append((old, new, len(matches)))
    if not flagged:
        return "\n*No forum-era terminology detected — terminology looks current.*\n"
    out.append("\nForum-era terminology detected. Confirm each is intentional (a quotation or historical note) or update to the current term.\n")
    out.append("| Old term | Current term | Occurrences |")
    out.append("|----------|--------------|-------------|")
    for old, new, n in flagged:
        out.append(f"| `{old}` | `{new}` | {n} |")
    return "\n".join(out) + "\n"


# ────────────────────────────────────────────────────────────────────────
# Main
# ────────────────────────────────────────────────────────────────────────


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("article", type=Path, help="path to the article markdown file")
    ap.add_argument(
        "--metashape-python",
        default=os.path.expanduser("~/.pyenv/versions/Metashape-2.2/bin/python"),
        help="path to the Metashape Python venv binary",
    )
    ap.add_argument(
        "--manual",
        type=Path,
        default=Path("corpus/official/metashape-pro-2_3_en.pdf"),
        help="path to the local Pro user-manual PDF",
    )
    ap.add_argument(
        "--api-changelog",
        type=Path,
        default=Path("corpus/official/metashape-python-api-2_3_1.pdf"),
        help="path to the Python API PDF (its chapter 3 is the change log)",
    )
    ap.add_argument(
        "--gui-changelog",
        type=Path,
        default=Path("corpus/official/metashape-changelog.pdf"),
        help="path to the GUI changelog PDF",
    )
    ap.add_argument("--no-introspect", action="store_true", help="skip Python API introspection")
    ap.add_argument("--no-pdf", action="store_true", help="skip PDF menu-path and terminology checks")
    ap.add_argument("--no-changelog", action="store_true", help="skip the changelog cross-checks")
    args = ap.parse_args()

    if not args.article.exists():
        print(f"error: article not found: {args.article}", file=sys.stderr)
        return 2
    text = args.article.read_text()

    print(f"# Tier 1 automated verification log")
    print(f"\n**Article:** `{args.article}`")
    print(f"**Run by:** `scripts/verify_article.py`")
    print(f"**Article size:** {len(text)} chars / {len(text.splitlines())} lines\n")

    api_changelog = None if args.no_changelog else args.api_changelog
    gui_changelog = None if args.no_changelog else args.gui_changelog

    print(heading("Step 1 — Python API introspection"))
    if args.no_introspect:
        print("\n*Skipped (`--no-introspect`).*\n")
    else:
        print(introspect_api(text, args.metashape_python, api_changelog))

    print(heading("Step 2 — GUI menu-path verification"))
    if args.no_pdf:
        print("\n*Skipped (`--no-pdf`).*\n")
    else:
        print(verify_menu_paths(text, args.manual, gui_changelog))

    print(heading("Step 3 — Terminology-shift sweep"))
    if args.no_pdf:
        print("\n*Skipped (`--no-pdf`).*\n")
    else:
        print(terminology_sweep(text))

    print(heading("Author action items"))
    print(
        "\n- Review the introspection output above. Confirm every kwarg / "
        "method name in the article matches what the local API reports.\n"
        "- Review the *Python API change-log cross-check* — if any of "
        "your references were renamed in earlier versions, mention the "
        "rename in the article's caveats so 1.x-script readers can "
        "port their code.\n"
        "- For each menu path with **0 hits**, confirm the label against "
        "the GUI or correct the article. Consult the *GUI change-log "
        "cross-check* for any historical rename of the same label.\n"
        "- For each terminology hit, confirm it is intentional (a "
        "verbatim quotation) or update to the current term.\n"
        "- Paste the steps above (or a curated subset) into the PR's "
        "*Automated verification log* section.\n"
    )

    return 0


if __name__ == "__main__":
    sys.exit(main())
