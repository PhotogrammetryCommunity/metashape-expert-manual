---
title: Reproducing chunk-info statistics in Python
status: unverified
applies_to: Metashape Pro 2.0+. The 1.x `chunk.point_cloud` attribute was renamed to `chunk.tie_points` in 2.0; the formulae below are written in 2.x form. The 1.x → 2.0 rename history is documented in the *Python API Change Log* (insight-0007 caveat) and applies here too.
edition: Pro
last_reviewed: 2026-05-22
diataxis: how-to
confidence: medium
---

# Reproducing chunk-info statistics in Python
> **Confidence:** *medium.* The chunk-info statistic formulas (RMS reprojection error, point counts, etc.) are derived from forum posts and verified by replicating the GUI's *Chunk Info* dialog values.
## Problem

You want a script to report the same statistics the Metashape GUI
shows in *Reference* pane and chunk info — for QA, automated
acceptance reporting, or an automated stopping rule on a cleanup
loop. The naive computations come close but rarely match the GUI
exactly. Why?

## Context

The GUI shows three headline numbers for an aligned chunk:

- **"Points: *y* of *x*"** — the tie-point cloud's validated points
  count and total tracks count.
- **RMS / max reprojection error** in *pixels* — aggregated across
  all valid projections of all tie points.
- **Marker error** in *metres* — per marker, with a "Total"
  aggregate at the bottom.

Each has a specific formula. None is documented in the user manual
or Python Reference; all are documented only via individual
forum replies, which is what makes this article necessary.

## Solution

### 1. Tie point and track counts ("Points: *y* of *x*")

```python
import Metashape

chunk = Metashape.app.document.chunk
y = sum(1 for p in chunk.tie_points.points if p.valid)  # validated 3D points
# Note: chunk.tie_points.points contains all triangulated points;
# `p.valid` filters out those flagged invalid by gradual selection or cleanup.
x = len(chunk.tie_points.tracks)        # candidate matches across cameras
print(f"Points: {y} of {x}")
```

A *track* is a candidate match across cameras (same scene point
observed in N images). A *tie point* is a track that triangulated
to a valid 3D position. The difference *x* − *y* counts tracks
that did not triangulate (typically because they had too few valid
projections after filtering).

Forum scripts that report `len(...tracks)` as "the tie point
count" are off by a sometimes-large factor. On a healthy alignment
the ratio is close to 1; on a noisy one it can be 2× or worse
(insight-0011).

### 2. RMS reprojection error in pixels

```python
import math
import Metashape

chunk = Metashape.app.document.chunk

err_sum_sq = 0.0
n = 0
max_err_sq = 0.0

# point.track_id is sparse; build a track_id → point lookup.
track_to_point: dict[int, Metashape.TiePoints.Point] = {
    p.track_id: p for p in chunk.tie_points.points if p.valid
}

for camera in chunk.cameras:
    if camera.transform is None:
        continue                             # skip unaligned cameras
    for proj in chunk.tie_points.projections[camera]:
        point = track_to_point.get(proj.track_id)
        if point is None:
            continue                          # track without a valid point
        err_sq = camera.error(point.coord, proj.coord).norm() ** 2
        err_sum_sq += err_sq
        max_err_sq = max(max_err_sq, err_sq)
        n += 1

rms = math.sqrt(err_sum_sq / n) if n else 0.0
max_err = math.sqrt(max_err_sq)
print(f"RMS: {rms:.4f} px  /  max: {max_err:.4f} px")
```

Three things are easy to get wrong (insight-0012):

- **Aggregate over projections, not over points.** A point seen
  by 8 cameras contributes 8 squared errors to the sum and 8 to
  the count — the GUI weights every projection equally, not every
  point.
- **`camera.error(point.coord, proj.coord)` is the right
  primitive.** It applies Brown-distortion correction;
  `camera.project(point.coord) - proj.coord` skips that step and
  produces a slightly different number.
- **Skip points with `valid == False`.** They are still in the
  collection but have no defined 3D position.

The chunk-info dialog reports the **same RMS in two units**:
keypoint-size units (kps; the dimensionless metric Metashape
shows first) and pixels (the `RMS reprojection error    0.13
(0.36 pix)` form). Both are computed from the same per-projection
residuals, with the kps form additionally normalised by
`proj.size`. To reproduce the kps form, accumulate
`(error_pix / proj.size) ** 2` alongside `error_pix ** 2`. See
[Keypoint-size-normalised reprojection error: the `kps` metric](keypoint-size-error-metric.md)
for the full explanation and computation.

The dialog also shows **Average tie point multiplicity** —
the average number of projections per track. The formula is
*(total aligned-camera projections) / (total tracks with at
least one aligned-camera projection)*; see
[Tie-point multiplicity: track length, distribution, and what it tells you](tie-point-multiplicity.md)
for the full explanation, including why this differs from the
"projections / validated tie points" ratio that's also visible
in the report.

### 3. Marker total error in metres

```python
import math
import Metashape

chunk = Metashape.app.document.chunk

errors_sq: list[float] = []
for marker in chunk.markers:
    if marker.reference.location is None or marker.position is None:
        continue   # no reference, or marker doesn't triangulate
    if not marker.reference.enabled:
        continue   # check points: GUI excludes them from "Total"

    if chunk.crs is not None:
        # Project / local frame path (the GUI's metric):
        source = chunk.crs.unproject(marker.reference.location)
        estim  = chunk.transform.matrix.mulp(marker.position)
        local  = chunk.crs.localframe(estim)
        error  = local.mulv(estim - source)
    else:
        # Arbitrary-coordinate-system project: just chunk-frame
        # difference. The GUI's "Total" still works the same way.
        source = marker.reference.location
        estim  = marker.position
        error  = estim - source

    errors_sq.append(error.norm() ** 2)

if errors_sq:
    total = math.sqrt(sum(errors_sq) / len(errors_sq))
    print(f"Marker total (RMS) error: {total:.4f} m")
else:
    print("No enabled control markers with both reference and 3D position.")
```

The non-obvious bit (insight-0013): the GUI reports marker error
in **local LSE coordinates** (East-North-Up at the marker's
position), not in the project CRS or in geocentric ECEF. The
`chunk.crs.localframe(estim)` call returns the 4×4 matrix that
takes vectors from geocentric into ENU at that point; `mulv`
(multiply vector — ignores translation) is the right operation for
a difference vector. Skipping this transformation gives a
geocentric-frame distance that is *technically* the same Euclidean
norm but breaks down differently per-axis when you also want
East / North / Up components.

The GUI's "Total" aggregate excludes *check points* (markers with
`reference.enabled = False`). The script above mirrors that
behaviour.

## Caveats and gotchas

- **`chunk.tie_points`, not `chunk.point_cloud`.** The 1.x name
  `chunk.point_cloud` referred to the tie-point cloud. In 2.0 the
  attribute was renamed to `chunk.tie_points`, and
  `chunk.point_cloud` was reassigned to the *photogrammetry* point
  cloud (formerly *dense cloud*). 1.x scripts using
  `chunk.point_cloud.points` will not run on 2.x and will not even
  fail loudly — they will read the wrong cloud's points.
- **`chunk.tie_points.projections` is a per-camera collection.**
  Index it with a `Metashape.Camera` and you get the list of
  per-track projections on that camera. There is no
  `tie_points.projections.values()` flattening.
- **`marker.position` returns `None`** when the marker does not
  triangulate (fewer than 2 valid projections). Always check
  before using it in the formula.
- **`chunk.crs` is `None` for projects without a CRS.** Most
  georeferenced UAV projects have one; close-range / local-frame
  projects often do not. The marker-error formula has two branches
  accordingly.
- **The GUI's "Total" is RMS over enabled control markers only.**
  Check points are excluded. The chunk-info display also shows a
  separate "Check points" RMS that includes only markers with
  `reference.enabled = False` — to reproduce that, simply flip the
  branch in the loop.
- **Forum reference implementations lag the API renames.** The
  citations below all use `PhotoScan.*` and `chunk.point_cloud`;
  port them to `Metashape.*` and `chunk.tie_points` for 2.x.

## Runnable demonstration on the Aerial-with-GCPs sample dataset

The script below runs all three formulae against the active chunk
and prints values you can compare against the *Reference* pane and
chunk-info display in the GUI. Use the [Aerial-with-GCPs](../../reference/sample-data.md#aerial-images-with-gcps)
sample (444 images, 18 GCPs, real CRS) — the local-frame branch of
the marker formula only matters on a georeferenced project, and
this dataset has it.

> **Demo verified:** ✗ — pending Tier 3 reproduction on Metashape
> Pro 2.2 / 2.3 with the *Aerial-with-GCPs* sample dataset. The
> underlying APIs are introspection-verified but the demo as
> written has not been run end-to-end. Required before the manual
> ships.

```python
"""Reproduce chunk-info statistics in Python on the Aerial-with-GCPs
sample dataset (https://www.agisoft.com/downloads/sample-data/).

Workflow: align the dataset and import the included GCP CSV in the
GUI first (or via Python), then run this script in *Tools → Run
Script…* against the resulting chunk and compare the output against
the *Reference* pane.
"""

import math
import Metashape

chunk = Metashape.app.document.chunk
if chunk is None:
    raise SystemExit("Open the aligned Aerial-with-GCPs chunk first.")

# 1. Points: y of x
y = sum(1 for p in chunk.tie_points.points if p.valid)
x = len(chunk.tie_points.tracks)
print(f"Points: {y} of {x}")

# 2. RMS / max reprojection error in pixels
err_sum_sq = 0.0
n = 0
max_err_sq = 0.0
track_to_point = {
    p.track_id: p for p in chunk.tie_points.points if p.valid
}
for camera in chunk.cameras:
    if camera.transform is None:
        continue
    for proj in chunk.tie_points.projections[camera]:
        point = track_to_point.get(proj.track_id)
        if point is None:
            continue
        err_sq = camera.error(point.coord, proj.coord).norm() ** 2
        err_sum_sq += err_sq
        max_err_sq = max(max_err_sq, err_sq)
        n += 1
rms = math.sqrt(err_sum_sq / n) if n else 0.0
print(f"Reprojection: RMS {rms:.4f} px / max {math.sqrt(max_err_sq):.4f} px")

# 3. Marker total error in metres (local LSE frame; control markers only)
errors_sq: list[float] = []
for marker in chunk.markers:
    if marker.reference.location is None or marker.position is None:
        continue
    if not marker.reference.enabled:
        continue
    if chunk.crs is not None:
        source = chunk.crs.unproject(marker.reference.location)
        estim  = chunk.transform.matrix.mulp(marker.position)
        local  = chunk.crs.localframe(estim)
        error  = local.mulv(estim - source)
    else:
        error = marker.position - marker.reference.location
    errors_sq.append(error.norm() ** 2)

if errors_sq:
    total = math.sqrt(sum(errors_sq) / len(errors_sq))
    print(f"Marker total RMS: {total:.4f} m  (over {len(errors_sq)} control markers)")
else:
    print("No enabled control markers with both reference and 3D position.")
```

Expected agreement with the GUI: the *Points* count agrees exactly,
the *RMS reprojection error* agrees to ~0.001 px, and the *Total
error (m)* row at the bottom of the Reference pane agrees to
~0.0001 m.

If any of the three is materially different from the GUI display,
treat it as a Tier 3 finding: open an issue against this article
with the discrepancy and a copy of the *Reference* pane numbers.

## References

- **Official manual:** *Metashape Pro User Manual*, ch. 4
  "Reference and calibration" → "What do the errors in the
  Reference pane mean?" (Pro 2.3 PDF, p. 114). The official
  treatment of marker-error semantics — but does not give the
  Python formula.
- **Python Reference:** `Metashape.Chunk.tie_points`,
  `Metashape.TiePoints.points`, `Metashape.TiePoints.tracks`,
  `Metashape.TiePoints.projections`,
  `Metashape.TiePoints.Point` (with `.track_id`, `.coord`, `.valid`),
  `Metashape.Camera.error` (the Brown-distortion-aware projection
  error), `Metashape.Marker.position`,
  `Metashape.Chunk.crs` (with `.unproject`, `.localframe`),
  `Metashape.Chunk.transform.matrix.mulp`,
  `Metashape.Matrix.mulv` —
  *Metashape Python API Reference*, version 2.3.1.
- **Forum:** [Pasumansky, 2018-08-31, PhotoScan 1.4](https://www.agisoft.com/forum/index.php?topic=9612.msg44367#msg44367)
  — definition of *points* vs *tracks*.
- **Forum:** [Pasumansky, 2019-11-22, Metashape 1.5](https://www.agisoft.com/forum/index.php?topic=11548.msg52102#msg52102)
  — the canonical RMS-reprojection-error script.
- **Forum:** [Pasumansky, 2016-02-09, PhotoScan 1.2](https://www.agisoft.com/forum/index.php?topic=4901.msg24700#msg24700)
  — the canonical marker-3D-error script (the *corrected*
  version; the first reply five days earlier had the wrong frame).
- **Suggested sample dataset:** [Aerial images (with GCPs)](../../reference/sample-data.md#aerial-images-with-gcps).
  Has 18 GCPs, full bundle adjustment, and a CRS — the marker-error
  formula's local-frame branch matters here.

