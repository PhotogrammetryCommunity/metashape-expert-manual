"""Normalize insight files to frontmatter format.

Three input formats:
1. h1-yaml-block: `# Insight: title\\n\\n```yaml\\n...\\n````
   (insights 0001-0045)
2. h1-with-id: `# insight-NNNN — title\\n\\n**Source:** ...`
   (insights 0046-0060)
3. frontmatter (target): `---\\nid: "NNNN"\\ntitle: ...\\n---`
   (insights 0061-0087)

Run from project root: ./.venv/bin/python scripts/normalize_insights.py
"""
import re
import sys
from pathlib import Path

import yaml


def parse_h1_yaml_block(text, n):
    """Format 1: # Insight: title\n\n```yaml\n...\n```"""
    first_line = text.split("\n", 1)[0]
    m = re.match(r"^# Insight:\s*(.+?)$", first_line)
    title = m.group(1).strip() if m else ""

    yaml_match = re.search(r"```yaml\n(.*?)```", text, re.DOTALL)
    if not yaml_match:
        return None
    yaml_content = yaml_match.group(1)

    try:
        data = yaml.safe_load(yaml_content)
    except yaml.YAMLError as e:
        print(f"  WARN: insight-{n}: yaml parse error: {e}")
        return None

    fm = {
        "id": f'"{n}"',
        "title": title,
    }
    if isinstance(data, dict):
        if "source" in data and isinstance(data["source"], dict):
            ft = data["source"].get("forum_thread")
            if ft:
                fm["source_threads"] = [ft]
        if "created" in data:
            fm["date_mined"] = data["created"]
        if "status" in data:
            fm["status"] = data["status"]

    after_yaml_idx = yaml_match.end()
    body = text[after_yaml_idx:].lstrip("\n")
    return fm, title, body


def parse_h1_with_id(text, n):
    """Format 2: # insight-NNNN — title\n\n**Source:** ..."""
    first_line = text.split("\n", 1)[0]
    m = re.match(r"^# insight-\d+\s*[—–-]+\s*(.+?)$", first_line)
    title = m.group(1).strip() if m else ""

    body_start = text.find("\n## ")
    if body_start < 0:
        body_start = text.find("\n# ", 1)
    if body_start < 0:
        return None

    metadata_block = text[len(first_line):body_start]
    body = text[body_start + 1:]

    fm = {"id": f'"{n}"', "title": title}

    m = re.search(
        r"\*\*Source:\*\*\s*\[[^\]]+\]\(([^)]+)\)", metadata_block
    )
    if m:
        fm["source_threads"] = [m.group(1)]

    m = re.search(
        r"\*\*Date:\*\*\s*(?:drafted\s*)?([\d-]+)", metadata_block
    )
    fm["date_mined"] = m.group(1) if m else "2026-05-23"

    m = re.search(r"\*\*Status:\*\*\s*(\w+)", metadata_block)
    fm["status"] = m.group(1) if m else "reviewed"

    return fm, title, body


def make_frontmatter_text(fm, title, body, n):
    """Produce the normalized file content."""
    out = ["---"]
    for key in ["id", "title", "source_threads", "date_mined", "status"]:
        if key not in fm:
            continue
        v = fm[key]
        if key == "source_threads":
            out.append(f"{key}:")
            for url in v:
                out.append(f"  - {url}")
        elif key == "title":
            # Title might contain quotes/colons; quote it always
            t = str(v).replace('"', '\\"')
            out.append(f'title: "{t}"')
        else:
            out.append(f"{key}: {v}")
    out.append("---")
    out.append("")

    body = body.lstrip("\n")
    # Keep an H1 in the body for consistency with the frontmatter style
    if not re.match(r"^#\s+", body):
        out.append(f"# Insight {n} — {title}")
        out.append("")
    out.append(body)
    return "\n".join(out)


def normalize_one(fp: Path, *, dry_run: bool = False):
    text = fp.read_text()
    if text.startswith("---\n"):
        return None  # already frontmatter

    n_match = re.match(r"insight-(\d{4})-", fp.name)
    if not n_match:
        return None
    n = n_match.group(1)

    if text.startswith("# Insight:"):
        result = parse_h1_yaml_block(text, n)
        fmt = "h1-yaml"
    elif text.startswith("# insight-"):
        result = parse_h1_with_id(text, n)
        fmt = "h1-id"
    else:
        return None

    if result is None:
        return ("PARSE_FAIL", fmt, n)

    fm, title, body = result
    new_text = make_frontmatter_text(fm, title, body, n)
    if not dry_run:
        fp.write_text(new_text)
    return ("CONVERTED", fmt, n)


def main(args):
    dry_run = "--dry-run" in args
    insights_dir = Path("insights")
    converted, skipped, failed = 0, 0, 0
    for fp in sorted(insights_dir.glob("insight-*.md")):
        result = normalize_one(fp, dry_run=dry_run)
        if result is None:
            skipped += 1
            continue
        status, fmt, n = result
        if status == "CONVERTED":
            converted += 1
            print(f"  {'[dry] ' if dry_run else ''}CONVERTED insight-{n} ({fmt})")
        else:
            failed += 1
            print(f"  FAILED insight-{n} ({fmt})")

    print(
        f"\nSummary: converted={converted}, "
        f"skipped (already frontmatter)={skipped}, failed={failed}"
    )


if __name__ == "__main__":
    main(sys.argv[1:])
