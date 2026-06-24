#!/bin/bash
#
# Bulk-fetch full printpages for all Tier A threads.
# Resume-safe: skips files that already exist on disk.
#
# Usage:
#     scripts/bulk_fetch_tier_a.sh [N_THREADS]
#
# With N_THREADS, fetches up to that many additional threads then stops
# (useful for chunked execution). Without, runs to completion.
#
# Per-printpage delay: 10 seconds (full thread content; more polite
# than index pages where we use 5 s).

set -uo pipefail

UA="Metashape-Expert-Manual/0.1 (https://github.com/PhotogrammetryCommunity/metashape-expert-manual; +project research, no redistribution)"
TIER_A_TSV="corpus/forum/index/candidates-tier-A.tsv"
PRINTPAGE_DIR="corpus/forum"
DELAY=10
LIMIT="${1:-}"

if [ ! -f "$TIER_A_TSV" ]; then
    echo "ERROR: $TIER_A_TSV not found; run scripts/triage_threads.py first" >&2
    exit 1
fi

mkdir -p "$PRINTPAGE_DIR"

fetched=0
skipped=0
failed=0
start_time=$(date +%s)

# Iterate Tier A in views-descending order (which is how the TSV is sorted).
while IFS=$'\t' read -r board topic_id views replies last_by last_date cached covered alex_touched title; do
    # Skip header
    [ "$board" = "board" ] && continue

    out="$PRINTPAGE_DIR/printpage-$(printf '%05d' "$topic_id").html"
    if [ -f "$out" ]; then
        skipped=$((skipped+1))
        continue
    fi

    # Stop if we hit the per-call limit.
    if [ -n "$LIMIT" ] && [ "$fetched" -ge "$LIMIT" ]; then
        break
    fi

    url="https://www.agisoft.com/forum/index.php?action=printpage;topic=${topic_id}.0"
    curl -sS --user-agent "$UA" "$url" -o "$out"
    size=$(wc -c < "$out" 2>/dev/null || echo 0)

    # Single retry on transient small response.
    if [ "$size" -lt 1000 ]; then
        echo "  ? t=$topic_id returned $size B; retrying once after 15 s"
        sleep 15
        curl -sS --user-agent "$UA" "$url" -o "$out"
        size=$(wc -c < "$out" 2>/dev/null || echo 0)
    fi

    if [ "$size" -lt 1000 ]; then
        echo "  ! t=$topic_id failed after retry ($size B); marking failed"
        rm -f "$out"
        failed=$((failed+1))
    else
        fetched=$((fetched+1))
        if [ "$((fetched % 20))" -eq 0 ]; then
            elapsed=$(( $(date +%s) - start_time ))
            echo "  ... $fetched fetched, $skipped skipped, $failed failed; "\
"${elapsed}s elapsed; current t=$topic_id ($views views)"
        fi
    fi

    sleep "$DELAY"
done < "$TIER_A_TSV"

echo ""
echo "bulk fetch session done: $fetched newly fetched, $skipped skipped, $failed failed"
ls "$PRINTPAGE_DIR"/printpage-*.html | wc -l | xargs echo "total printpages now cached:"
