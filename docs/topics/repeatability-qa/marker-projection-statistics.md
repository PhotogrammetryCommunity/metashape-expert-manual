---
title: "Marker projection statistics: counts, per-marker errors, and metre-vs-pixel framing"
status: unverified
applies_to: Metashape Pro 2.x — and PhotoScan 1.x via the same `Marker.projections` API
edition: Pro
last_reviewed: 2026-05-29
diataxis: how-to
confidence: high
---

# Marker projection statistics: counts, per-marker errors, and metre-vs-pixel framing

> **Confidence:** *high.* Both recipes are forum-attested with
> permalinks (Agisoft support, 2019). The
> `Marker.projections`, `Marker.position`, and
> `Marker.reference.location` API are introspection-confirmed on
> Metashape 2.2.

## Problem

You need quick programmatic access to marker statistics — for
QA reporting, marker-quality dashboards, or batch-processing
scripts that flag under-projected markers:

- "How many images is each marker visible in?"
- "What's the error in metres for each marker?"
- "Why does my per-image marker error in metres come out the
  same for every image?"

The Reference pane shows projection counts and per-image pixel
errors, but extracting them in bulk requires Python.

## Recipe — projection count per marker

> "You can use the following simple code to output the marker
> label and corresponding number of projections in the active
> chunk of the currently opened document"
> — Agisoft support, 2019-08-21, PhotoScan 1.5
> ([permalink](https://www.agisoft.com/forum/index.php?topic=11286.msg50690#msg50690))

> **Demo verified:** ✗ — pending Tier 3 reproduction on a real Metashape install.

```python
import Metashape

chunk = Metashape.app.document.chunk

print(f"{'Marker':<15} {'Projections':>12}")
print("-" * 30)
for marker in chunk.markers:
    n_projections = len(marker.projections.keys())
    print(f"{marker.label:<15} {n_projections:>12}")
```

`marker.projections` is a dict-like mapping from `Camera` to
`Marker.Projection`. Calling `.keys()` returns the cameras
the marker has been placed on; `len()` gives the count.

For Reference-pane-style filtering — only markers visible on
≥ 2 aligned cameras (the threshold for the marker to influence
the bundle adjustment):

> **Demo verified:** ✗ — pending Tier 3 reproduction on a real Metashape install.

```python
def aligned_projection_count(marker, chunk):
    n = 0
    for camera in marker.projections.keys():
        if camera.transform:  # aligned
            n += 1
    return n
```

## Recipe — per-marker error in metres (one value per marker)

The metre error is **per-marker, not per-image**. There is one
3D position (`marker.position`) per marker; the difference from
the surveyed `marker.reference.location` is one number, not one
per camera.

> **Demo verified:** ✗ — pending Tier 3 reproduction on a real Metashape install.

```python
import Metashape

chunk = Metashape.app.document.chunk
T = chunk.transform.matrix
crs = chunk.crs

print(f"{'Marker':<15} {'Error (m)':>12}")
print("-" * 30)
for marker in chunk.markers:
    if marker.position is None or marker.reference.location is None:
        continue

    # Estimated position in geocentric coordinates
    estimated_geocentric = T.mulp(marker.position)

    # Reference position from CRS (lat/lon/elev or E/N/Elev) → geocentric
    if crs is not None:
        reference_geocentric = crs.unproject(marker.reference.location)
    else:
        # No CRS: reference values are already in chunk-local coords
        reference_geocentric = marker.reference.location

    error_m = (estimated_geocentric - reference_geocentric).norm()
    print(f"{marker.label:<15} {error_m:>12.4f}")
```

The CRS unprojection step is critical for georeferenced chunks.
Without it, you'd be subtracting longitude-degrees from
geocentric-metres, producing meaningless numbers.

> "In case your project is georeferenced in geographic/projected
> coordinate system you need to define 'ref' variable as:
> `ref = chunk.crs.unproject(marker.reference.location)`. Thus
> both est and ref values would be in geocentric coordinate
> system and you can calculate the error as a norm of the
> connecting vector."
> — Agisoft support, 2019-08-22, PhotoScan 1.5
> ([permalink](https://www.agisoft.com/forum/index.php?topic=11286.msg50699#msg50699))

## The metre-vs-pixel distinction

A frequent confusion: users compute the per-marker metre error,
loop it inside an outer `for camera in marker.projections.keys()`
loop, and then wonder why every camera gets the same value.

The answer: the metre error **is** the same for every camera,
because it's a property of the marker's 3D position, not of any
projection. Per-image errors only exist in **pixels**:

| Quantity | Per-camera? | What it measures |
|----------|:-:|------------------|
| `marker.position` (3D estimated) | No (one per marker) | Bundle's solution for the marker's world position |
| `marker.reference.location` (3D source) | No (one per marker) | User-supplied surveyed position |
| Metre error: `(est - ref).norm()` | No (one per marker) | 3D Euclidean distance between estimated and reference |
| Pixel error: per-projection reprojection residual | Yes (one per (marker, camera) pair) | How far the projected 3D position lands from the manually-placed 2D pixel |

> "I just can get 1 value of error (m) by target for all chunk,
> but I can't get 1 value of error (m) by target by image, that's
> it?"
> — the source-thread user, 2019-08-22, PhotoScan 1.5
> ([permalink](https://www.agisoft.com/forum/index.php?topic=11286.msg49832#msg49832))

> "Yes indeed I was wrong in what I wanted to do: I can only have
> one residue in m per point for a whole chunk but several
> residues px of a point."
> — the source-thread user, 2019-08-22, PhotoScan 1.5
> ([permalink](https://www.agisoft.com/forum/index.php?topic=11286.msg50706#msg50706))

## Recipe — per-projection pixel error

For the per-(marker, camera) pixel residual, project the
marker's 3D position back to the camera's image plane and
compare with the manual 2D placement:

> **Demo verified:** ✗ — pending Tier 3 reproduction on a real Metashape install.

```python
import Metashape

chunk = Metashape.app.document.chunk

print(f"{'Marker':<15} {'Camera':<25} {'Error (px)':>12}")
print("-" * 55)
for marker in chunk.markers:
    if marker.position is None:
        continue
    for camera, projection in marker.projections.items():
        if not camera.transform:
            continue
        # Where the marker's 3D position projects to on this camera
        reprojected_2d = camera.project(marker.position)
        if reprojected_2d is None:
            continue   # marker behind camera or outside image
        # The user-placed projection coordinate
        manual_2d = projection.coord
        # Residual in pixels
        error_px = (reprojected_2d - manual_2d).norm()
        print(f"{marker.label:<15} {camera.label:<25} {error_px:>12.2f}")
```

The pixel residual differs per camera because each camera sees
the marker's 3D position from a different angle — small bundle
errors translate to different 2D residuals on different cameras.
Mean and max across projections are useful aggregate metrics
for marker-quality reporting.

## Aggregating into chunk-level RMS

For a chunk-wide RMS marker error in metres:

> **Demo verified:** ✗ — pending Tier 3 reproduction on a real Metashape install.

```python
import math
import Metashape

chunk = Metashape.app.document.chunk
T = chunk.transform.matrix
crs = chunk.crs

sum_sq = 0.0
n = 0
for marker in chunk.markers:
    if marker.position is None or marker.reference.location is None:
        continue
    est = T.mulp(marker.position)
    ref = crs.unproject(marker.reference.location) if crs else marker.reference.location
    sum_sq += (est - ref).norm() ** 2
    n += 1

if n > 0:
    print(f"Marker RMS error: {math.sqrt(sum_sq / n):.4f} m  ({n} markers)")
```

This is the value Metashape's *Reference* pane shows as the
"Marker error (m)" total. Computing it manually lets you filter
(e.g., excluding *check points* that should not influence the
RMS), weight by accuracy, or apply your own outlier rejection.

## Caveats

- **`marker.position` is None for unaligned markers.** A marker
  needs at least 2 projections on aligned cameras for the bundle
  to triangulate its 3D position. Markers without `position`
  are typically newly added and not yet bundle-included.
- **`marker.reference.location` is None for markers without
  surveyed coordinates.** Check before using; markers added
  manually for visualization may not have reference data.
- **`marker.projections.items()`** in 2.x returns a list of
  `(Camera, Projection)` pairs. In 1.x it was the same. The
  `Projection` object has `.coord` (2D pixel position),
  `.pinned` (bool), and `.visible` (bool) attributes.
- **`camera.project(point_3d)` returns None** when the
  projection falls outside the image or behind the camera.
  Always check before using the result.
- **For check-point analysis**, exclude markers from the bundle
  by setting `marker.reference.enabled = False`. The bundle
  then ignores their reference data; you can compute their
  error post-hoc as a check on the alignment quality the bundle
  was constrained by.

## See also

- [Camera reference error: per-camera location and orientation in Python](camera-reference-error-python.md)
  — the same metre-error pattern for camera GPS positions.
- [Reprojection error analysis: per-camera and per-tie-point](reprojection-error-analysis.md)
  — pixel-space residuals across the whole tie-point cloud.
- [DSM ridge-line artefacts: alignment-quality diagnosis](dsm-ridge-lines-diagnosis.md)
  — when marker errors signal a deeper alignment problem.

## References

- *Metashape Pro User Manual* (2.3), ch. 4 *Improving camera
  alignment* — Reference pane and marker-error display.
- *Metashape Python API Reference* (2.3.1):
  `Marker.projections`, `Marker.Projection`,
  `Marker.position`, `Marker.reference`, `Camera.project`,
  `Chunk.transform`, `CoordinateSystem.unproject`.
- Forum thread, [*Export number projection of markers*, 2019](https://www.agisoft.com/forum/index.php?topic=11286.msg50690#msg50690)
  — projection-count recipe + per-marker error walkthrough +
  metre-vs-pixel framing clarification.

