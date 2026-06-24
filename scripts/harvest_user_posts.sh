#!/bin/bash
#
# Harvest a forum user's showposts pages from agisoft.com/forum.
# Resumable: skips pages already on disk.
#
# Usage:
#     scripts/harvest_user_posts.sh USER_ID [START_OFFSET] [END_OFFSET]
#
# SMF's showposts paginates 15 posts per page; offsets advance by 15
# (e.g., 0, 15, 30, ..., 15660 for ~15,675 posts). Output lands in
# corpus/forum/user-posts/u-<id>/p<offset>.html.

set -euo pipefail

UA="Metashape-Expert-Manual/0.1 (https://github.com/PhotogrammetryCommunity/metashape-expert-manual; +project research, no redistribution)"
DELAY=5

uid="${1:?usage: $0 USER_ID [START] [END]}"
start="${2:-0}"
end="${3:-}"

dir="corpus/forum/user-posts/u-${uid}"
mkdir -p "$dir"

# Probe to find largest START offset if END not provided.
if [ -z "$end" ]; then
    if [ ! -f "/tmp/showposts-u${uid}-probe.html" ]; then
        curl -sS --user-agent "$UA" \
            "https://www.agisoft.com/forum/index.php?action=profile;u=${uid};area=showposts" \
            -o "/tmp/showposts-u${uid}-probe.html"
        sleep "$DELAY"
    fi
    end=$(grep -oE "u=${uid};area=showposts;start=[0-9]+" "/tmp/showposts-u${uid}-probe.html" \
          | grep -oE 'start=[0-9]+' | tr -d 'start=' | sort -n | tail -1)
    end=${end:-0}
fi

echo "=== User $uid: harvesting START=$start through END=$end ==="
fetched=0
skipped=0
for ((s=start; s<=end; s+=15)); do
    out="$dir/p$(printf '%05d' "$s").html"
    if [ -f "$out" ]; then
        skipped=$((skipped+1))
        continue
    fi
    url="https://www.agisoft.com/forum/index.php?action=profile;u=${uid};area=showposts;start=${s}"
    curl -sS --user-agent "$UA" "$url" -o "$out"
    size=$(wc -c < "$out")
    # Single retry on transient small response (sometimes the forum
    # returns ~300 B for a moment under load).
    if [ "$size" -lt 5000 ]; then
        echo "  ? u=$uid start=$s returned $size B; retrying once after 15s"
        sleep 15
        curl -sS --user-agent "$UA" "$url" -o "$out"
        size=$(wc -c < "$out")
    fi
    if [ "$size" -lt 5000 ]; then
        echo "  ! u=$uid start=$s returned $size B after retry; aborting"
        rm -f "$out"
        break
    fi
    fetched=$((fetched+1))
    if [ "$((fetched % 25))" -eq 0 ]; then
        echo "  ... u=$uid: $fetched fetched, $skipped skipped, at start=$s"
    fi
    sleep "$DELAY"
done
echo "User $uid done: $fetched fetched, $skipped skipped"
