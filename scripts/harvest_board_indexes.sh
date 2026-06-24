#!/bin/bash
#
# Harvest SMF board-index pages from agisoft.com/forum.
# Skips files that already exist (resume support).
#
# Usage:
#     scripts/harvest_board_indexes.sh BOARD_ID [BOARD_ID ...]
#
# Per-page crawl delay: 5 seconds (index pages are lightweight metadata,
# distinct from full printpages where we use 10s).

set -euo pipefail

UA="Metashape-Expert-Manual/0.1 (https://github.com/PhotogrammetryCommunity/metashape-expert-manual; +project research, no redistribution)"
INDEX_DIR="corpus/forum/index/raw"
DELAY=5

mkdir -p "$INDEX_DIR"

for bid in "$@"; do
    # Probe to find largest START offset (= last page).
    if [ ! -f "/tmp/board${bid}-probe.html" ]; then
        curl -sS --user-agent "$UA" \
            "https://www.agisoft.com/forum/index.php?board=${bid}.0" \
            -o "/tmp/board${bid}-probe.html"
        sleep "$DELAY"
    fi
    largest=$(grep -oE "board=${bid}\.[0-9]+" "/tmp/board${bid}-probe.html" \
              | grep -oE '\.[0-9]+$' | tr -d '.' | sort -n | tail -1)
    largest=${largest:-0}

    echo "=== Board $bid: harvesting through START=$largest ==="
    fetched=0
    skipped=0
    for ((start=0; start<=largest; start+=30)); do
        out="$INDEX_DIR/board-${bid}-p$(printf '%05d' "$start").html"
        if [ -f "$out" ]; then
            skipped=$((skipped+1))
            continue
        fi
        url="https://www.agisoft.com/forum/index.php?board=${bid}.${start}"
        curl -sS --user-agent "$UA" "$url" -o "$out"
        size=$(wc -c < "$out")
        # If the fetch returned an unexpectedly tiny page, abort.
        if [ "$size" -lt 5000 ]; then
            echo "  ! board=$bid start=$start returned $size B; aborting board"
            rm -f "$out"
            break
        fi
        fetched=$((fetched+1))
        if [ "$((fetched % 10))" -eq 0 ]; then
            echo "  ... board $bid progress: $fetched fetched, $skipped skipped, at START=$start"
        fi
        sleep "$DELAY"
    done
    echo "Board $bid done: $fetched fetched, $skipped skipped"
done
