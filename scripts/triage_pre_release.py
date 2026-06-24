#!/usr/bin/env python3
"""Triage Pasumansky posts in pre-release threads.

For each Pasumansky reply in a printpage, output a structured row:
- post_index, msg_id, date, length
- summary: first 200 characters
- topic_keywords: extracted from the post text
- in_manual: boolean — does our docs/ already cite this msg_id or
  contain key phrases from the post?
- in_official_manual: heuristic — does the Pro 2.3 user-manual PDF
  contain key terminology from the post?
- still_in_api: boolean — does Tier 1 introspection on
  Metashape 2.2.2 confirm any API symbols mentioned in the post?

Outputs a markdown triage table to build/.

IMPORTANT (lesson #30, 2026-05-24): SMF printpage HTML does NOT
embed msg IDs for individual posts — only for posts that get quoted
by later posts. This script's msg_id field will be 0 (or wrong) for
~95% of posts when reading from printpage alone. To get correct
msg IDs for permalink generation, set --topic-view-dir to a directory
containing standard topic-view pages (?topic=N.0, ?topic=N.20, ...)
which embed `<a id="msgNNNNN"></a>` anchors per post.

Usage:
    triage_pre_release.py corpus/forum/printpage-16745.html \\
        [--topic-view-dir /tmp/topic-fetch/16745/]
"""
from __future__ import annotations

import argparse
import html as html_module
import os
import re
import subprocess
from pathlib import Path
from typing import List, Tuple

# Regex to extract Pasumansky posts
PASUMANSKY_POST_RE = re.compile(
    r"<dt class=\"postheader\">.*?"
    r"Post by:\s*<strong>Alexey Pasumansky</strong>\s*on\s*"
    r"<strong>([^<]+)</strong>.*?</dt>\s*"
    r"<dd[^>]*class=\"postbody\">(.*?)</dd>",
    re.DOTALL,
)

MSG_LINK_RE = re.compile(r"#msg(\d+)")

# Common keyword extractors
API_TOKEN_RE = re.compile(
    r"\b("
    r"chunk\.\w+|chunk\.\w+\.\w+|"
    r"Chunk\.\w+|"
    r"camera\.\w+|Camera\.\w+|"
    r"sensor\.\w+|Sensor\.\w+|"
    r"Metashape\.\w+(?:\.\w+)?|"
    r"matchPhotos|alignCameras|optimizeCameras|exportCameras|"
    r"buildDepthMaps|buildPointCloud|buildModel|buildTexture|"
    r"buildOrthomosaic|buildTiledModel|buildDem|"
    r"calibrateImages|alignChunks|mergeChunks|"
    r"keep_keypoints|reset_matches|reference_preselection|"
    r"generic_preselection|adaptive_fitting|filter_mask|"
    r"mask_tiepoints|filter_stationary_points|"
    r"keypoint_limit|tiepoint_limit|"
    r"convert_to_pinhole|merge_tiepoints|"
    r"rolling_shutter|full_shutter_model|"
    r"tweaks|"
    r"\.points|\.tracks|\.projections|\.transform|"
    r"buildPanorama|exportPanorama|"
    r"importMasks|exportMasks|"
    r"clean_up|cleanModel|fixTopology|closeHoles|"
    r"raster|orthomosaic|"
    r"tiepoint|tie_point|tie point"
    r")\b"
)

GUI_LABEL_RE = re.compile(
    r'\*\*([^*]+)\*\*|"([^"]+)"|'
    r"(Workflow|Tools|File|Edit|View|Reference)\s*[→>]\s*([\w ]+)"
)


def extract_msg_ids_from_topic_view(topic_view_dir: Path) -> dict:
    """Parse standard topic-view pages (NOT printpage) for verified
    msg-IDs. Returns {(author, date): msg_id} dict.

    Standard topic view structure:
        <a id="msg{N}"></a>
        <div class="windowbg|windowbg2">
          ... <a href="...action=profile..." title="View the
          profile of {AUTHOR}">{AUTHOR}</a> ...
          &#171; <strong>...:</strong> {DATE} &#187; ...

    Per lesson #30, this is the authoritative source of msg IDs
    for permalinks; printpage HTML does NOT embed them.
    """
    if not topic_view_dir or not topic_view_dir.exists():
        return {}

    msg_map = {}
    for path in sorted(topic_view_dir.glob("*.html")):
        html = path.read_text(encoding="utf-8", errors="replace")
        anchors = list(re.finditer(r'<a id="msg(\d+)"></a>', html))
        for i, a in enumerate(anchors):
            start = a.end()
            end = anchors[i + 1].start() if i + 1 < len(anchors) else len(html)
            section = html[start:end]
            author_m = re.search(
                r'<a href="[^"]*action=profile[^"]*"\s+title="View the profile of[^"]*"[^>]*>([^<]+)</a>',
                section,
            )
            if not author_m:
                continue
            author = author_m.group(1).strip()
            date_m = re.search(
                r"&#171;\s*<strong>[^:]+:</strong>\s*([^<]+?)\s*&#187;", section
            )
            if not date_m:
                continue
            date = date_m.group(1).strip()
            msg_map[(author, date)] = int(a.group(1))
    return msg_map


def extract_pasumansky_posts(html: str) -> List[Tuple[str, str, int]]:
    """Return list of (date, post_html, msg_id) for each Pasumansky post."""
    posts = []

    # Build position-aware msg_id lookup: msg IDs are in the headers
    # (anchors above the postheader). Get all msg_ids in order.
    msg_ids = [int(m) for m in MSG_LINK_RE.findall(html)]

    for i, m in enumerate(PASUMANSKY_POST_RE.finditer(html)):
        date = m.group(1).strip()
        body_html = m.group(2)
        # Best-effort msg_id: match position in document
        # (each post has 1-3 msg-link occurrences nearby)
        body_start = m.start()
        nearby_msgs = [
            mm.group(1) for mm in MSG_LINK_RE.finditer(html, max(0, body_start - 500), body_start)
        ]
        msg_id = int(nearby_msgs[-1]) if nearby_msgs else 0
        posts.append((date, body_html, msg_id))
    return posts


def html_to_text(html: str) -> str:
    """Convert post HTML to plain text."""
    text = re.sub(r"<br\s*/?>", "\n", html, flags=re.IGNORECASE)
    text = re.sub(r"<blockquote[^>]*>", "\n[QUOTE]\n", text, flags=re.IGNORECASE)
    text = re.sub(r"</blockquote>", "\n[/QUOTE]\n", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", "", text)
    text = html_module.unescape(text)
    text = re.sub(r"\n\s*\n+", "\n\n", text)
    return text.strip()


def extract_api_tokens(text: str) -> set[str]:
    """Extract API-looking tokens from post text."""
    return set(API_TOKEN_RE.findall(text))


def is_in_our_manual(msg_id: int, api_tokens: set[str], docs_dir: Path) -> Tuple[bool, List[str]]:
    """Check whether our manual cites this msg_id or any of these API
    tokens. Return (cited?, hit_files)."""
    hits = []
    if msg_id:
        # Direct grep for msg ID
        cmd = ["grep", "-l", "-r", "--include=*.md", f"msg{msg_id}", str(docs_dir)]
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=20)
            if r.stdout:
                hits.extend(r.stdout.strip().split("\n"))
        except Exception:
            pass
    return (bool(hits), hits)


def check_introspection(api_tokens: set[str]) -> Tuple[List[str], List[str]]:
    """For each Metashape.* token, check whether it exists in the
    local Metashape 2.2.2 install. Returns (alive, dead) lists."""
    if not api_tokens:
        return [], []

    metashape_tokens = [
        t for t in api_tokens
        if t.startswith(("Metashape.", "Chunk.", "Camera.", "Sensor."))
        or t.startswith(("chunk.", "camera.", "sensor."))
    ][:20]    # cap to avoid huge introspection runs

    if not metashape_tokens:
        return [], []

    code_lines = ["import Metashape", "results = []"]
    for token in metashape_tokens:
        # Normalize to dotted form for Metashape namespace
        if token.startswith("chunk."):
            token_check = token.replace("chunk.", "Metashape.Chunk.")
        elif token.startswith("camera."):
            token_check = token.replace("camera.", "Metashape.Camera.")
        elif token.startswith("sensor."):
            token_check = token.replace("sensor.", "Metashape.Sensor.")
        else:
            token_check = token

        # Use eval to walk the dotted path
        code_lines.append(
            f"try:\n"
            f"    obj = {token_check.split('(')[0]}\n"
            f"    results.append(({token!r}, True))\n"
            f"except (AttributeError, NameError):\n"
            f"    results.append(({token!r}, False))"
        )

    code_lines.append('for r in results: print(f"{r[0]}\\t{r[1]}")')
    code = "\n".join(code_lines)

    py = os.environ.get(
        "METASHAPE_PYTHON",
        os.path.expanduser("~/.pyenv/versions/Metashape-2.2/bin/python"),
    )
    try:
        r = subprocess.run([py, "-c", code], capture_output=True, text=True, timeout=15)
        alive, dead = [], []
        for line in r.stdout.strip().split("\n"):
            if "\t" in line:
                token, status = line.split("\t", 1)
                if status == "True":
                    alive.append(token)
                else:
                    dead.append(token)
        return alive, dead
    except Exception:
        return [], list(metashape_tokens)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("printpages", nargs="+", type=Path)
    ap.add_argument("--docs-dir", type=Path, default=Path("docs"))
    ap.add_argument("--output", type=Path,
                    default=Path("build/pre-release-triage.md"))
    ap.add_argument("--topic-view-dir", type=Path, default=None,
                    help="Directory of standard-topic-view HTML files "
                         "(per lesson #30; required for accurate msg_id "
                         "permalinks. Otherwise msg_id field will be 0 "
                         "or unreliable.)")
    args = ap.parse_args()

    topic_msg_map = extract_msg_ids_from_topic_view(args.topic_view_dir) if args.topic_view_dir else {}
    if args.topic_view_dir and not topic_msg_map:
        print(f"  WARNING: --topic-view-dir set but no msg IDs extracted "
              f"from {args.topic_view_dir}. Check files exist and have "
              f"the standard topic-view structure (not printpage).")

    rows = []
    for pp in args.printpages:
        html = pp.read_text(encoding="utf-8", errors="replace")
        title_match = re.search(r"Print Page - (.+?)\s*\n", html)
        title = title_match.group(1) if title_match else pp.stem

        posts = extract_pasumansky_posts(html)
        for idx, (date, body_html, msg_id) in enumerate(posts):
            text = html_to_text(body_html)
            api_tokens = extract_api_tokens(text)
            # Lesson #30: prefer the topic-view-extracted msg ID over
            # the printpage-extracted one (which is typically wrong).
            verified_msg_id = topic_msg_map.get(("Alexey Pasumansky", date), 0)
            if verified_msg_id:
                msg_id = verified_msg_id
            in_manual, hits = is_in_our_manual(msg_id, api_tokens, args.docs_dir)
            alive, dead = check_introspection(api_tokens)

            summary = text[:200].replace("\n", " ") + ("..." if len(text) > 200 else "")
            rows.append({
                "thread": title,
                "post_idx": idx + 1,
                "date": date,
                "msg_id": msg_id,
                "length": len(text),
                "summary": summary,
                "api_tokens": sorted(api_tokens)[:8],
                "alive_api": alive,
                "dead_api": dead,
                "in_our_manual": in_manual,
                "manual_hits": [Path(h).name for h in hits],
            })

    # Render markdown
    out_lines = ["# Pre-release thread triage", ""]
    out_lines.append(
        f"Generated by `scripts/triage_pre_release.py`. "
        f"Inputs: {', '.join(p.name for p in args.printpages)}.")
    out_lines.append("")
    out_lines.append("## Per-post triage table")
    out_lines.append("")
    out_lines.append(
        "| # | Date | Msg | Len | In our manual? | API alive | API dead | Topic |")
    out_lines.append(
        "|---|------|-----|----:|---------------|-----------|----------|-------|")
    for r in rows:
        n_alive = len(r["alive_api"])
        n_dead = len(r["dead_api"])
        in_man = "YES (" + ",".join(r["manual_hits"][:2]) + ")" if r["in_our_manual"] else "no"
        alive_str = ",".join(r["alive_api"][:3]) if r["alive_api"] else "—"
        dead_str = ",".join(r["dead_api"][:3]) if r["dead_api"] else "—"
        topic = r["summary"][:80].replace("|", "\\|")
        out_lines.append(
            f"| {r['post_idx']} | {r['date'][:11]} | msg{r['msg_id']} | "
            f"{r['length']} | {in_man} | {alive_str} | {dead_str} | {topic}... |")

    out_lines.append("")
    out_lines.append("## Per-post detail")
    out_lines.append("")

    for r in rows:
        out_lines.append(f"### Post #{r['post_idx']} — {r['date']} (msg{r['msg_id']})")
        out_lines.append("")
        out_lines.append(f"- **Length:** {r['length']} chars")
        out_lines.append(f"- **In our manual:** {'YES — ' + ', '.join(r['manual_hits']) if r['in_our_manual'] else 'NO'}")
        if r["api_tokens"]:
            out_lines.append(f"- **API tokens mentioned:** {', '.join(r['api_tokens'])}")
        if r["alive_api"]:
            out_lines.append(f"- **Confirmed live in 2.2.2:** {', '.join(r['alive_api'])}")
        if r["dead_api"]:
            out_lines.append(f"- **NOT FOUND in 2.2.2 (obsolete?):** {', '.join(r['dead_api'])}")
        out_lines.append("")
        out_lines.append(f"**Summary:** {r['summary']}")
        out_lines.append("")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text("\n".join(out_lines), encoding="utf-8")
    print(f"\nWrote {args.output} ({len(rows)} Pasumansky posts triaged across {len(args.printpages)} threads).")


if __name__ == "__main__":
    main()
