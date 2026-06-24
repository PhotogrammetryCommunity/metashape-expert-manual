---
title: "Reprojection error analysis: per-camera and per-tie-point"
status: unverified
applies_to: Metashape Pro 2.x — and PhotoScan 1.x via the same API (with `chunk.point_cloud` instead of `chunk.tie_points`)
edition: Pro
last_reviewed: 2026-05-28
diataxis: how-to
confidence: high
---

# Reprojection error analysis: per-camera and per-tie-point

> **Confidence:** *high.* All API references
> (`Camera.error`, `Camera.project`, `chunk.tie_points.projections`,
> `Marker.projections`) are introspection-confirmed on Metashape
> 2.2; the recipes are forum-attested with permalinks.

## Problem

The chunk-info dialog reports a single aggregate **RMS reprojection
error** value for the whole project. When that number is concerning
(> 1.0 px on a typical aerial dataset), the next question is *where*
the error is concentrated — is one camera dragging the average up?
Are tie points in a specific region badly triangulated? Are the
GCPs themselves the problem?

Three queries, each a short Python recipe:

1. **Per-camera average reprojection error** — find problem cameras.
2. **Per-tie-point reprojection error** — visualise spatial error
   patterns; export for QGIS / ParaView.
3. **Marker errors** (three distinct meanings) — distinguish
   GCP-position error in metres from per-camera reprojection error
   in pixels.

## Solution

### 1. Per-camera average reprojection error

> **Demo verified:** ✗ — pending Tier 3 reproduction on a real Metashape install.

```python
import math
import Metashape

chunk = Metashape.app.document.chunk
tps = chunk.tie_points  # 1.x: chunk.point_cloud
points = tps.points

# Build track_id → point_id lookup (for O(1) lookup later)
point_ids = [-1] * len(tps.tracks)
for pid, p in enumerate(points):
    point_ids[p.track_id] = pid

photo_errors = []
for camera in chunk.cameras:
    if not camera.transform:
        continue
    sum_sq = 0.0
    n = 0
    for proj in tps.projections[camera]:
        pid = point_ids[proj.track_id]
        if pid < 0 or not points[pid].valid:
            continue
        # Camera.error applies Brown-distortion correction; using
        # camera.project(...) - proj.coord skips it and produces a
        # slightly different number that won't match the chunk-info
        # dialog. See keypoint-size-error-metric.md Caveats.
        residual = camera.error(points[pid].coord, proj.coord)
        if residual is None:
            continue
        sum_sq += residual.norm() ** 2
        n += 1
    if n > 0:
        photo_errors.append((camera.label, math.sqrt(sum_sq / n), n))

# Print worst cameras first
photo_errors.sort(key=lambda r: -r[1])
print(f"{'Camera':<30}  {'RMS (px)':>10}  {'Projections':>12}")
for label, rms, n in photo_errors[:20]:
    print(f"{label:<30}  {rms:>10.3f}  {n:>12}")
```

Cameras with RMS > 2× the chunk average are candidates for
masking, removal, or a separate calibration group.

For a **dimensionless variant** (residual normalised by each
projection's keypoint size), accumulate
`(error_pix / proj.size) ** 2` alongside `err_sq`. The kps
form is invariant to image resolution and is what Metashape's
chunk-info dialog reports as the first number in the
`RMS reprojection error  0.13  (0.36 pix)` line. See
[Keypoint-size-normalised reprojection error: the `kps` metric](keypoint-size-error-metric.md)
for the full explanation.

### 2. Per-tie-point reprojection error (export for visualisation)

> **Demo verified:** ✗ — pending Tier 3 reproduction on a real Metashape install.

```python
import math
import Metashape

chunk = Metashape.app.document.chunk
tps = chunk.tie_points
T = chunk.transform.matrix
crs = chunk.crs

# Pre-build per-camera projection index for O(1) lookup
proj_by_track = {}
for camera in chunk.cameras:
    if not camera.transform:
        continue
    for proj in tps.projections[camera]:
        proj_by_track.setdefault(proj.track_id, []).append((camera, proj.coord))

with open("/tmp/tie_point_errors.txt", "w") as out:
    out.write("point_index\tX\tY\tZ\treproj_error_px\n")
    for pid, point in enumerate(tps.points):
        if not point.valid:
            continue
        cam_projs = proj_by_track.get(point.track_id, [])
        if not cam_projs:
            continue
        sum_sq, n = 0.0, 0
        for camera, observed in cam_projs:
            projected = camera.project(point.coord)
            if projected is None:
                continue
            residual = projected - observed
            sum_sq += residual.norm() ** 2
            n += 1
        if n == 0:
            continue
        rms = math.sqrt(sum_sq / n)
        # Emit in CRS coordinates if georeferenced
        coord_world = (crs.project(T.mulp(point.coord))
                       if crs else T.mulp(point.coord))
        out.write(f"{pid}\t{coord_world[0]:.6f}\t{coord_world[1]:.6f}"
                  f"\t{coord_world[2]:.6f}\t{rms:.3f}\n")
```

Open the resulting `.txt` in QGIS as a delimited-text layer and
colour points by `reproj_error_px` to see where the bundle is
struggling. High-error clusters typically indicate poor coverage,
moving objects, or repetitive features.

### 3. Marker errors — three distinct meanings

When asked "what's my marker error?", clarify which one:

| Value | Unit | Meaning |
|-------|------|---------|
| **Total error** | metres | Distance between estimated marker position and reference (GCP) position |
| **Per-axis error** | metres (X/Y/Z) | The 3 components of the total-error vector |
| **Reprojection error** | pixels | Per-camera residual on each marker projection |

> **Demo verified:** ✗ — pending Tier 3 reproduction on a real Metashape install.

```python
import Metashape

chunk = Metashape.app.document.chunk

# Total + per-axis error (metres)
print(f"{'Marker':<10}  {'total (m)':>10}  {'dx':>8}  {'dy':>8}  {'dz':>8}")
for marker in chunk.markers:
    if not marker.position or not marker.reference.location:
        continue
    est = chunk.crs.project(chunk.transform.matrix.mulp(marker.position))
    ref = marker.reference.location
    delta = est - ref
    total = delta.norm()
    print(f"{marker.label:<10}  {total:>10.3f}  "
          f"{delta[0]:>+8.3f}  {delta[1]:>+8.3f}  {delta[2]:>+8.3f}")

# Per-camera reprojection error (pixels)
for marker in chunk.markers:
    if not marker.position:
        continue
    for camera, projection in marker.projections.items():
        if not camera.transform:
            continue
        # Camera.error returns the 2D residual Vector
        residual = camera.error(marker.position, projection.coord)
        if residual is not None:
            rms = residual.norm()
            print(f"  {marker.label}  on  {camera.label}: {rms:.2f} px")
```

## Caveats

- **API name change between 1.x and 2.x.** The tie-point store
  was renamed from `chunk.point_cloud` to `chunk.tie_points` in
  Metashape 2.0. The sub-attributes (`points`, `tracks`,
  `projections`) keep the same names. Adapt 1.x scripts by
  global search-and-replace.
- **`Camera.project()` may return `None`** for points outside
  the camera's view frustum. Always guard.
- **`marker.position` is in chunk-local coordinates**, not in
  the CRS. Convert with `chunk.crs.project(chunk.transform.matrix.mulp(...))`
  before comparing to `marker.reference.location`.
- **Reprojection error in pixels is not directly comparable
  across cameras with different resolutions.** A 0.5 px error on
  an 8 MP image represents a different physical extent than the
  same error on a 60 MP image.
- **Pre-build per-camera projection indexes** for the
  per-tie-point recipe — without the `proj_by_track` dict, the
  algorithm is O(N²) and unusable on projects with > ~500K tie
  points.

## When to use each recipe

| Question | Recipe | Output |
|----------|--------|--------|
| Which cameras have bad alignment? | Recipe 1 | Sorted list, worst first |
| Where in the scene is error concentrated? | Recipe 2 | Spatial heatmap export |
| Is my GCP placement accurate? | Recipe 3 (total error) | Per-marker metres |
| Are my GCP image-pinnings accurate? | Recipe 3 (reprojection) | Per-camera pixels |

## References

- *Metashape Pro User Manual* (2.3), ch. 4 *Improving camera
  alignment* — describes the Reference pane's aggregate-error
  view (this article documents the per-camera and per-point
  decomposition).
- *Metashape Python API Reference* (2.3.1):
  `Camera.project`, `Camera.error`, `Marker.projections`,
  `TiePoints.projections`, `chunk.transform.matrix`,
  `chunk.crs.project`.
- Forum thread, [*export projections & error (pix) for every cam*, 2016](https://www.agisoft.com/forum/index.php?topic=5255.msg26266#msg26266)
  — the per-camera average-RMS recipe.
- Forum thread, [*Export reprojection errors for each tie points*, 2016](https://www.agisoft.com/forum/index.php?topic=5267.msg26529#msg26529)
  — the per-tie-point error export recipe.
- Forum thread, [*How to get markers errors*, 2017](https://www.agisoft.com/forum/index.php?topic=8019.msg37947#msg37947)
  — the clarification of the three distinct
  marker-error meanings; community marker-error script.

## See also

- [Mesh and point-cloud editing recipes](../scripting/mesh-pointcloud-editing-recipes.md)
- [Diagnosing under-aligned chunks](../../workflow/alignment/diagnosing-under-aligned-chunks.md)
- [Reproducing chunk-info statistics in Python](reproducing-chunk-info-statistics-python.md)
- [Keypoint-size-normalised reprojection error: the kps metric](keypoint-size-error-metric.md)
  — the dimensionless variant of the per-camera residual; what
  Metashape's bundle adjustment actually minimises.
- [Tie-point multiplicity: track length, distribution, and what it tells you](tie-point-multiplicity.md)
  — the per-track-overlap measure that complements the
  per-projection RMS.

