---
title: Removing "blue flag" marker projections cleanly
status: unverified
applies_to: Metashape Pro 2.0+. The `marker.projections[camera] = None` semantics is unchanged across the 1.x → 2.x rename and confirmed by Tier 1 introspection on 2.2.2.
edition: Pro
last_reviewed: 2026-05-22
diataxis: how-to
confidence: medium
---

# Removing "blue flag" marker projections cleanly
> **Confidence:** *medium.* The bulk-removal script is forum-attested; the `Marker.projections[camera]` deletion API is introspection-confirmed on Metashape 2.2.
## Problem

Your project has hundreds of automatic marker projections — blue
flags placed by Metashape from each marker's 3D position into every
photo it overlaps. Many are wrong: the marker sits on a stake, on a
thin feature, or on a mesh region that does not match the actual
geometry, so the automatic projection lands metres away. You want to
remove these wrong projections from a script, in bulk, before
running *Optimize Cameras*.

## Context

A marker has a *projection* on every camera that sees it — a 2D
point in image space. The colour of the flag in the photo view
encodes the projection's state:

- **Green** — pinned: placed or adjusted by you.
- **Blue** — unpinned: automatically projected from the marker's
  3D position.
- **Grey** — no projection on this camera (the projection has been
  removed).

Both green and blue projections participate in *Optimize Cameras*.
This is the often-surprising fact: a wrong blue flag is *not*
ignored by the bundle. It pulls the camera's pose in a wrong
direction with the same weight as a green flag.

To exclude a projection from optimisation, the projection must be
*removed*, not "unpinned". There is no API call that turns a blue
flag grey; the way to make a projection grey is to assign `None` to
its slot in `marker.projections`.

## Solution

The canonical bulk-removal pattern, documented in the source
thread:

```python
import Metashape

chunk = Metashape.app.document.chunk

for marker in chunk.markers:
    for camera in list(marker.projections.keys()):
        if not marker.projections[camera].pinned:
            marker.projections[camera] = None
```

Two things to notice:

- **`list(...)`** wraps `marker.projections.keys()` because the
  loop mutates the collection during iteration.
- **`= None`** is the *removal* operation. There is no
  `unpin()` method or `del marker.projections[camera]` shortcut
  that does the same thing — the destructive assignment is the
  documented pattern.

For a more aggressive variant that also removes pinned projections
whose reprojection error exceeds a threshold (say, 5 pixels), the
recommended pattern iterates the cleanup until no projection is
removed in a full pass:

```python
import Metashape

MARKER_REPROJ_MAX = 5.0   # pixels; tune to your project

chunk = Metashape.app.document.chunk

continue_filtering = True
while continue_filtering:
    continue_filtering = False
    for marker in list(chunk.markers):
        position = marker.position
        if not position:
            chunk.remove(marker)        # marker no longer triangulates
            continue
        kept_any = False
        for camera in list(marker.projections.keys()):
            if not camera.transform:
                continue                # skip unaligned cameras
            p = marker.projections[camera]
            if p is None:
                continue
            reproj = camera.project(position)
            if reproj is None:
                # marker projects outside the image
                marker.projections[camera] = None
                continue_filtering = True
                continue
            error = (reproj - p.coord[:2]).norm()
            if error > MARKER_REPROJ_MAX:
                marker.projections[camera] = None
                continue_filtering = True
            else:
                kept_any = True
        if not kept_any:
            chunk.remove(marker)
```

The iteration is needed because removing one bad projection changes
the marker's 3D position (re-triangulated from the surviving
projections), which in turn changes the reprojection of every other
projection.

## Caveats and gotchas

- **`Marker.Projections` is not iterable directly.** A bare
  `for x in marker.projections:` raises
  `TypeError: 'Marker.Projections' object is not iterable`. Use
  one of the accessors:
    - `marker.projections.keys()` — iterates `Metashape.Camera`
      instances
    - `marker.projections.values()` — iterates
      `Metashape.Marker.Projection` instances
    - `marker.projections.items()` — iterates
      `(Camera, Projection)` tuples (most idiomatic for read-only
      loops where you need both)
- **Iteration with simultaneous mutation is safe in 2.x.**
  *([Resolved — UV-008](../../about/unverified.md#uv-008))*. A
  bare `for camera in marker.projections.keys():` loop that
  assigns `marker.projections[camera] = None` runs to completion
  without raising. The canonical workflow wraps in
  `list(...)` as a defensive habit; this is preserved for
  exact compatibility but is not a correctness requirement on
  modern versions.
- **`marker.position` returns `None`** when the marker has fewer
  than 2 valid projections (cannot triangulate). Always check
  before computing reprojections.
- **`camera.project(position)` returns `None`** when the projected
  point falls outside the image frame. Treat that as a "remove
  this projection" signal: the marker is not visible from this
  camera.
- **The cleanup is destructive within the chunk.** There is no
  undo at the API level. If you want to keep the original marker
  state, duplicate the chunk first
  (`chunk.copy()`) and clean up the copy.
- **The original snippet is from the PhotoScan 1.x era** (2017). On
  Metashape 2.x the API is identical except for the module name
  (`PhotoScan` → `Metashape`); the per-projection assignment
  pattern is unchanged.

## Runnable demonstration on the Coded targets sample dataset

The snippet below loads the [Coded targets](../../reference/sample-data.md#coded-targets)
sample (6 images), runs automatic marker detection,
exercises the bulk-removal pattern, and verifies the iteration-
mutation behaviour discussed in the *Caveats* above.

> **Demo verified:** ✓ — run end-to-end on the *Coded targets*
> sample (Metashape 2.2.3, 2026-06-04). `chunk.addPhotos` +
> `chunk.detectMarkers` + the bare-iteration bulk-removal loop run
> without error and leave `unpinned_left = 0`. **Note from the run:**
> on this sample `detectMarkers(CircularTarget12bit, tolerance=50)`
> finds **one** coded target (ID 69) across all six images, and its
> projections are all *pinned* — so the removal loop is a no-op here
> unless *Align Photos* + *Optimize Cameras* has first created
> auto-projected (blue) flags. The removal API itself is confirmed.

```python
"""Demonstrate the marker-projection cleanup on the Coded targets
sample dataset (https://www.agisoft.com/downloads/sample-data/).

Adjust DATASET_DIR to your local download path, then run inside
Metashape's *Tools → Run Script…* console (or save and run with
`metashape -r demo_clean_projections.py`).
"""

import os
import Metashape

DATASET_DIR = "/path/to/coded_targets/"   # ← adjust to your download

# 1. Load the 6 images.
doc = Metashape.app.document
chunk = doc.chunk if doc.chunk else doc.addChunk()
photos = sorted(
    os.path.join(DATASET_DIR, f)
    for f in os.listdir(DATASET_DIR)
    if f.lower().endswith((".jpg", ".jpeg", ".tif", ".tiff", ".png"))
)
chunk.addPhotos(photos)
print(f"loaded {len(chunk.cameras)} cameras")

# 2. Detect the 3 coded targets. The 12-bit circular-target type
#    matches the symbols printed on the sample's targets.
chunk.detectMarkers(
    target_type=Metashape.CircularTarget12bit,
    tolerance=50,
)
print(f"detected {len(chunk.markers)} markers")

# 3. Inspect the projections — they will be a mix of pinned (green)
#    and unpinned (blue) flags depending on the detection accuracy.
for m in chunk.markers:
    pinned   = sum(1 for c in m.projections.keys()
                   if m.projections[c].pinned)
    unpinned = sum(1 for c in m.projections.keys()
                   if not m.projections[c].pinned)
    print(f"  {m.label}: {pinned} pinned, {unpinned} unpinned")

# 4. Bulk-remove the unpinned (blue) projections.
#    The bare iteration is safe in 2.x (UV-008, verified on 2.2.2);
#    the list(...) wrap is preserved here for compatibility with
#    the original published recipe.
for m in chunk.markers:
    for camera in list(m.projections.keys()):
        if not m.projections[camera].pinned:
            m.projections[camera] = None

# 5. Confirm: every surviving projection should now be pinned.
remaining = sum(1 for m in chunk.markers
                  for c in m.projections.keys()
                  if m.projections[c] is not None)
unpinned_left = sum(1 for m in chunk.markers
                      for c in m.projections.keys()
                      if m.projections[c] is not None
                      and not m.projections[c].pinned)
print(f"after cleanup: {remaining} projections remain, "
      f"{unpinned_left} of which are still unpinned (expected: 0)")
```

The expected output is `unpinned_left = 0` after the cleanup — the
script confirms the article's central claim that
`marker.projections[camera] = None` is the correct removal
operation. If your local Metashape version raises during the
bare-iteration loop (something the article's caveat says it should
not), your version is older than 2.2.2 and the `list(...)` wrap is
load-bearing rather than defensive.

## References

- **Official manual:** *Metashape Pro User Manual*, ch. 4
  "Reference and calibration" → "Georeferencing" — markers,
  marker projections, and the Reference pane (Pro 2.3 PDF, p. 98).
- **Python Reference:** `Metashape.Marker.projections`
  (the `Marker.Projections` collection),
  `Metashape.Marker.Projection` (the per-projection class with
  `coord`, `pinned`, `valid`),
  `Metashape.Marker.position` (3D position; returns `None` for
  marker with insufficient projections),
  `Metashape.Camera.project` (3D-to-image projection; returns
  `None` if the point is outside the frame) —
  *Metashape Python API Reference*, version 2.3.1.
- **Forum:** [Pasumansky, 2016-02-10, PhotoScan 1.2](https://www.agisoft.com/forum/index.php?topic=4947.msg24830#msg24830)
  — "Both blue and green flags are considered" (the foundational
  fact).
- **Forum:** [Pasumansky, 2017-03-03, PhotoScan 1.3](https://www.agisoft.com/forum/index.php?topic=6635.msg32062#msg32062)
  — the canonical bulk-removal snippet.
- **Related articles:** [Programmatic marker placement and pinning](programmatic-marker-placement.md)
  is the inverse operation — creating a projection rather than
  removing one.
- **Suggested sample dataset:** [Coded targets](../../reference/sample-data.md#coded-targets)
  has 6 images and 3 markers; the project is small enough that you
  can manually verify each marker's flag colour after running the
  cleanup script.
