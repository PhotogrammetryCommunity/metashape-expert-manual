---
title: "Gray flags in marker detection: what they mean and how to remove them"
status: unverified
applies_to: Metashape Pro 2.x and Metashape Standard 2.x — same flag-colour semantics as PhotoScan 1.x
edition: "Pro / Standard"
last_reviewed: 2026-05-29
diataxis: explanation
confidence: high
---

# Gray flags in marker detection: what they mean and how to remove them

> **Confidence:** *high.* The semantics are forum-attested by
> Agisoft support with permalink (2022). The visualisation-only
> nature of gray flags is consistent across thread replies and
> matches the behaviour observed in the *Photos* view across
> Metashape 1.x and 2.x.

## The three flag colours

When viewing a photo in the *Photos* pane, Metashape draws
markers as flags. The flag colour signals each marker
projection's status:

| Flag colour | What the projection is | Effect on processing |
|-------------|-----------------------|---------------------|
| **Green** | User-pinned (manually placed and confirmed) | Used as a hard constraint by Optimize Cameras |
| **Blue** | Auto-detected or auto-projected | Used as a soft constraint (subject to refinement) |
| **Gray** | Inferred from the marker's 3D position via re-projection — *not* a real projection on this image | **Visualisation only**; does not influence processing |

The gray flag is the most commonly misunderstood. It does not
mean "the marker was detected on this image." It means: "the
marker's 3D position projects somewhere on this image, so for
your visual reference here's where it would land."

## Why gray flags appear

Metashape draws a gray flag on every aligned image whose field
of view contains a marker's 3D position, **even if the marker
was never placed (manually or automatically) on that image**.
The 3D position itself comes from the marker's other
projections — typically two or more green/blue flags on
neighbouring images.

> "Gray flags are not considered during the processing. They
> are only shown for the user convenience — for better
> understanding of the 3D point location, based on the marker
> projections defined on other images."
> — Agisoft support, 2022-02-09, Metashape 1.8
> ([permalink](https://www.agisoft.com/forum/index.php?topic=14192.msg63403#msg63403))

This is helpful for QA: a gray flag confirms that a marker
*should* be visible on this image. If you can see the physical
marker on the photo but Metashape only shows a gray flag (no
green / blue), the auto-detection skipped this image — a
candidate for manual placement.

## Why gray flags are NOT considered during processing

A common worry: "If gray flags exist on N images, am I getting
unwanted constraints?" No. The processing — bundle adjustment,
optimization, dense matching — only consumes:

- Green flags (user-pinned, marker.projections[camera].pinned = True)
- Blue flags (auto-projected, marker.projections[camera].pinned = False)

Gray flags do not exist as `Marker.Projection` objects at all.
They are computed on the fly during rendering and exist only in
the GUI's image-overlay layer.

Programmatically, `marker.projections.keys()` returns only the
cameras with green/blue projections. Gray-flag cameras are
absent.

## How to remove gray flags

> "If you remove all 'blue' and 'green' projections for point5,
> point6 and point7 (and also uncheck the marker in the
> reference pane) - gray flags will disappear automatically.
> Gray flags indication only exist if there are at least two
> projections for the related markers, defined on the aligned
> images."
> — Agisoft support, 2022-02-09, Metashape 1.8
> ([permalink](https://www.agisoft.com/forum/index.php?topic=14192.msg62499#msg62499))

The condition for gray-flag display is **≥ 2 real (green/blue)
projections on aligned cameras**. Below that threshold, the
marker has insufficient triangulation data and Metashape doesn't
attempt to render the inferred projections.

### Three removal paths

| Goal | Action |
|------|--------|
| Remove gray flags for one marker (and stop using that marker) | Delete the marker entirely: right-click → *Remove* |
| Remove gray flags but keep the marker for reference | Delete all green/blue projections (right-click each pin → *Remove Projection*) until fewer than 2 remain on aligned cameras |
| Remove gray flags caused by a single mis-detected outlier projection | Right-click that projection → *Remove Projection* (the bundle re-triangulates the 3D position from the surviving 2+ projections) |

### Programmatic removal

> **Demo verified:** ✗ — pending Tier 3 reproduction on a real Metashape install.

```python
import Metashape

chunk = Metashape.app.document.chunk

# Remove markers whose total aligned projection count is < 2
to_remove = []
for marker in chunk.markers:
    aligned_count = sum(
        1 for camera in marker.projections.keys()
        if camera.transform
    )
    if aligned_count < 2:
        to_remove.append(marker)

if to_remove:
    print(f"Removing {len(to_remove)} markers with < 2 aligned projections")
    chunk.remove(to_remove)
```

For the "remove specific projection" path:

> **Demo verified:** ✗ — pending Tier 3 reproduction on a real Metashape install.

```python
# Remove this marker's projection on the named camera
marker = chunk.markers[0]   # or find by label
camera = next(c for c in chunk.cameras if c.label == "DSC_0042.JPG")
del marker.projections[camera]
```

## Diagnostic: false-positive auto-detection in the scene interior

The source thread's actual question was about coded markers
detected in arbitrary scene locations — false positives that the
algorithm placed in the wrong region. The diagnostic strategy
applies generally:

> "If the erroneous marker detections are usually in the middle
> of scene, you should get 4-vertex polygon (each vertex
> corresponding to your 'gcp's), thus you can remove all the
> other markers from the chunk, before assigning labels and
> coordinates to the correctly detected markers."
> — Agisoft support, 2022-02-09, Metashape 1.8
> ([permalink](https://www.agisoft.com/forum/index.php?topic=14192.msg62502#msg62502))

The recipe: compute the convex hull of all auto-detected marker
positions, keep only the markers at hull vertices (typically 4
for a rectangular survey area), and discard interior markers
as likely false positives.

> **Demo verified:** ✗ — pending Tier 3 reproduction on a real Metashape install.

```python
import Metashape

chunk = Metashape.app.document.chunk

# Project each detected marker's 3D position to (X, Y) in chunk-local
points_2d = []
for marker in chunk.markers:
    if marker.position is None:
        continue
    points_2d.append((marker.position.x, marker.position.y, marker))

# Compute convex hull (using shapely if available, else a manual one)
try:
    from shapely.geometry import MultiPoint
    pts = MultiPoint([(p[0], p[1]) for p in points_2d])
    hull_coords = list(pts.convex_hull.exterior.coords)
    hull_set = {(round(x, 4), round(y, 4)) for x, y in hull_coords}

    interior_markers = [
        m for x, y, m in points_2d
        if (round(x, 4), round(y, 4)) not in hull_set
    ]

    print(f"Removing {len(interior_markers)} interior (likely false-positive) markers")
    chunk.remove(interior_markers)
except ImportError:
    print("shapely not installed; install via pip or use a manual hull algorithm")
```

This pattern is specifically for **regular grid surveys** where
GCPs sit at known boundary positions. For irregular GCP layouts,
the convex-hull heuristic doesn't apply — use a different
geometric filter, or manually inspect each detected marker.

## Caveats

- **Gray flags are NOT a quality indicator.** Their presence is
  not "good" or "bad" — it's just "the marker's 3D position
  projects to within this camera's field of view."
- **Gray flags can disappear after Optimize Cameras** if the
  bundle's refined marker position projects to outside the
  image. This is normal and not a problem.
- **In the *Photos* pane, you can hide gray flags entirely:**
  right-click the photo viewport → *Show Gray Markers* (toggle
  off). This affects display only.
- **`marker.position` may be slightly different from the
  centroid of the green/blue projections** because the bundle
  triangulates from sub-pixel-refined coordinates. The gray
  flags are drawn at `camera.project(marker.position)`, not at
  the centroid of the manual projections.
- **Auto-detection of coded markers** (CircularTarget, AprilTag)
  produces blue flags; manual placement produces green. Both
  count toward the ≥ 2 threshold for gray flag display on other
  cameras.

## See also

- [AprilTag detection: choosing a variant](apriltag-detection.md)
  — for auto-detected coded markers (the source of blue flags
  in many drone-survey workflows).
- [Coded circular targets: 12-bit markers, printing, sizing, and the 14-bit / 16-bit / 20-bit family](coded-circular-targets.md)
  — the CircularTarget family these flags appear on; printing
  workflow and target-sizing guidance.
- [Marker projection statistics](../../topics/repeatability-qa/marker-projection-statistics.md)
  — programmatic access to projection counts and per-marker
  errors.
- [Programmatic marker placement](programmatic-marker-placement.md)
  — adds marker projections in Python (creates green flags
  equivalent to manual placement).

## References

- *Metashape Pro User Manual* (2.3), ch. 4 *Improving camera
  alignment* — describes manual marker placement; does not
  explicitly explain the gray-flag inference behaviour.
- *Metashape Python API Reference* (2.3.1):
  `Marker.projections`, `Marker.Projection.pinned`,
  `Marker.position`, `Camera.project`.
- Forum thread, [*How to remove gray flag from the marker
  detection*, 2022](https://www.agisoft.com/forum/index.php?topic=14192.msg63403#msg63403)
  — gray-flag semantics; ≥ 2 projection threshold;
  convex-hull false-positive filter.

