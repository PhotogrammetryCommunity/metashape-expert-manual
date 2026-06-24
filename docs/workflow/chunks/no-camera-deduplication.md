---
title: "`mergeChunks` does not deduplicate cameras"
status: unverified
applies_to: Metashape Pro 2.x and Standard 2.x — and unchanged from PhotoScan 1.x
edition: "Pro / Standard"
last_reviewed: 2026-05-22
diataxis: explanation
confidence: high
---

# `mergeChunks` does not deduplicate cameras

> **Series:** Part 2 of 3 on `mergeChunks` semantics.
> Previous: [What `mergeChunks` actually does ←](what-mergechunks-does.md).
> Continue: [The `merge_tiepoints` option →](merge-tiepoints-and-keep-keypoints.md).

> **Confidence:** *high.* The architectural reason (per-source-chunk
> tie points anchored to source-chunk siblings only) is directly
> attested by a 2014 forum thread with permalink; the
> deduplication script and detection recipe are based on
> introspection-confirmed `Camera.photo.path` and
> `Chunk.cameras` attributes.

When two source chunks share images by file path — a common
outcome of *Align Chunks (camera based)*, or any workflow that
puts the same photo in multiple chunks — `mergeChunks` produces a
merged chunk with **the same image present multiple times**. There
is no deduplication step. Each copy is a separate `Camera`
instance with its own pose, its own enabled state, and its own set
of tie-point projections.

The architecture is intentional and **its consequences cannot be
papered over after the merge**. This article explains why post-merge
camera deduplication is not a clean operation and what the better
strategies look like.

## What you observe

A merged chunk produced from two source chunks that share K
cameras (by path) has:

- `len(chunk.cameras)` = sum of the two source-chunk camera counts,
  with each shared camera contributing **two** entries.
- The two `Camera` instances for the same image carry potentially
  *different* poses (each from its source chunk's bundle), and
  *non-overlapping* tie-point projections.
- The point cloud, depth maps, and orthomosaic all process each
  camera instance independently — so a merge of two 100-image
  chunks with 20 shared cameras runs depth maps for 220 cameras,
  not 180.

## Why post-merge deduplication is not a clean operation

The architectural reason, attested verbatim (topic 2314):

> "the trouble with doing that is that tie points between image
> pairs (the points that make the sparse cloud, and which are
> needed to generate dense cloud, and are also used in
> optimisation) are only generated during image alignment, so
> when you align chunks you do not get additional tie points
> between images in different chunks. this means that
> 'duplicate' images in a merged chunk only have tie points to
> the images in the chunk they came from originally, and if you
> remove one of those images you remove a lot of tie points which
> are not present in the other 'duplicate' that came from another
> chunk." — James, 2014-05-01, PhotoScan 1.0
> ([permalink](https://www.agisoft.com/forum/index.php?topic=2314.msg12352#msg12352))

In other words: **each duplicate's tie points are anchored to its
source chunk's siblings only.** They are not redundant; they are
disjoint. Removing one duplicate destroys its irreplaceable
contribution to the merged chunk's tie point cloud.

This makes the obvious post-merge cleanup — disable one of each
pair of duplicates by path — a destructive operation if performed
before the point cloud, mesh, or orthomosaic that depends on the
merged tie point cloud has been built.

## Deduplication script (1.0-era)

A sample script bundled in the same thread:

```python
import Metashape

doc = Metashape.app.document
chunk = doc.chunk
seen: set[str] = set()
for camera in chunk.cameras:
    if not camera.enabled:
        continue
    if camera.photo.path in seen:
        camera.enabled = False
    else:
        seen.add(camera.photo.path)
```

(Ported from PhotoScan API to Metashape 2.x: `chunk.photos` →
`chunk.cameras`, `photo` → `camera.photo`. The deduplication
predicate is unchanged.)

**Use only after** the dense product you needed is already built.
Disabling duplicates before that point silently destroys
source-chunk-internal tie points.

## What to do instead — architectural strategies

The right answer is to not produce duplicates in the first place.

### Strategy 1: keep each camera in only one source chunk

If you split a project into chunks for processing-cost reasons,
divide the cameras so each lives in exactly one chunk. The
*Align Chunks* method then has to be marker-based or point-based
(which work without shared cameras), not camera-based — but the
merge has no duplicates by construction.

### Strategy 2: post-merge addition of bridge cameras

If certain cameras need to anchor multi-block alignments (e.g. an
aerial overview pass that ties together a set of close-up
sub-block flights), **add the bridge cameras only to the merged
chunk after the merge.** Re-run *Align Photos* on the merged chunk
to incorporate them — this gives the bridge cameras tie points to
all source-chunk siblings, not just one.

This is more expensive than the camera-based align-and-merge route
but produces a structurally clean result.

### Strategy 3: marker-based linking instead of camera-based

When the only reason for shared cameras is to act as anchors for
*Align Chunks*, **use markers instead**. Place markers on shared
features (or use coded targets) in both source chunks; align with
`method=1` (marker based) and merge with `merge_markers=True`. No
duplicate cameras are introduced.

## Caveats

- **The `Camera.photo.path` predicate works in PhotoScan 1.x and
  Metashape 2.x identically.** Both use absolute paths from the
  project's perspective. If `project_absolute_paths=False` (the
  default), the comparison still operates on the resolved absolute
  path; this is consistent across the document.
- **Disabled cameras still occupy storage.** Disabling a duplicate
  reduces the cost of dense-product processing but does not remove
  the camera from the chunk. To actually remove it, use
  `chunk.remove([camera])` — and do this only after weighing the
  same tie-point-loss caveat as for `enabled=False`.
- **`mergeChunks` does not log duplicates.** There is no warning
  when paths collide. Detection requires explicit post-merge
  inspection (the script above is sufficient, in `print` mode
  rather than disable mode).

## Runnable demonstration on the Building sample dataset

The script below counts duplicates after a deliberately-overlapping
merge of two chunks built from the
[Building](../../reference/sample-data.md#building) sample. It does
not disable anything — it only reports the duplication state.

> **Demo verified:** ✗ — pending Tier 3 reproduction on Metashape
> Pro 2.2 / 2.3 with the *Building* sample dataset. The underlying
> APIs are introspection-verified but the demo as written has not
> been run end-to-end. Required before the manual ships.

```python
"""Detect duplicates in a merged chunk by image path.

Pre-condition: two source chunks have been aligned camera-based
and merged, with at least one shared camera between them.
"""
import Metashape
from collections import Counter

doc = Metashape.app.document
chunk = doc.chunk  # the merged chunk should be active

paths = Counter(c.photo.path for c in chunk.cameras)
duplicates = {p: n for p, n in paths.items() if n > 1}

print(f"total cameras    : {len(chunk.cameras)}")
print(f"unique paths     : {len(paths)}")
print(f"duplicate paths  : {len(duplicates)}")
if duplicates:
    print()
    print("duplicate detail (top 10):")
    for path, n in sorted(duplicates.items(),
                          key=lambda kv: -kv[1])[:10]:
        print(f"  {n}× {path}")

# Optional: also count tie points per duplicate so the
# 'removing one destroys tie points' claim is observable.
if duplicates:
    print()
    print("tie-point projection counts per duplicate (first 5):")
    for path in list(duplicates)[:5]:
        cams = [c for c in chunk.cameras if c.photo.path == path]
        for cam in cams:
            # Per-camera projection list — len() gives projection count.
            n_proj = len(chunk.tie_points.projections[cam])
            print(f"  {cam.label:>30} : {n_proj} projections")
```

**Expected output:** `duplicate paths` is non-zero (one entry per
shared image). Each duplicate-pair has approximately disjoint
projection sets — confirming the "removing a duplicate destroys
its source-chunk tie points" claim.

## References

- [Forum thread, *How to remove duplicated cameras*, 2014](https://www.agisoft.com/forum/index.php?topic=2314.0)
  — primary source; the structural explanation (msg 11437);
  the original deduplication script (msg 11448).
- *Metashape Python Reference* (2.3.1), `Document.mergeChunks` —
  no `deduplicate_cameras` argument exists.
- *Metashape Pro User Manual* (2.3), ch. 3 *General workflow*,
  § *Merging chunks* — official description of the *Merge Chunks*
  workflow (the absence of camera deduplication is unstated;
  this article is the expert-level overlay).
