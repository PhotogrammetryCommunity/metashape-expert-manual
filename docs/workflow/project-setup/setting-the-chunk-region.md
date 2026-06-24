---
title: Setting `chunk.region` to bound the tie-point cloud
status: unverified
applies_to: Metashape Pro 2.0+. The 1.x `chunk.point_cloud.points` is `chunk.tie_points.points` on 2.x; the rest of the API surface (`chunk.region.center`, `.size`, `.rot`) is unchanged.
edition: Pro
last_reviewed: 2026-05-22
diataxis: how-to
confidence: medium
---

# Setting `chunk.region` to bound the tie-point cloud
> **Confidence:** *medium.* The `chunk.region` attribute and its effect on tie-point culling are introspection-confirmed; CRS-rotated region setup is forum-attested.
## Problem

After alignment you have a tie-point cloud and a default
`chunk.region` (the bounding box) that does not enclose all of it
— often because alignment produced more or fewer points than the
default region anticipated. You want to **resize the region to
contain the entire valid cloud** before running *Build Depth
Maps*, *Build Point Cloud*, *Build Mesh*, *Build DEM*, or *Build
Orthomosaic* (each respects the region).

## Context

`chunk.region` lives in the chunk's **internal coordinate system**,
not in the project's CRS. So do `chunk.tie_points.points` (each
`point.coord` is a 4-vector in homogeneous internal coordinates).
This means a region resize that fits the points can be computed
*without leaving the internal frame* — no CRS projection or
unprojection needed.

The most-cited forum answer (insight-0015) gives a longer script
that *does* take a CRS round-trip: project each point into the
CRS, take min/max in CRS, unproject the centre back, scale the
size by `1/T.scale()`, and rotate the region into the local
frame. That script works for georeferenced chunks but is
unnecessarily complex if the user only wants an axis-aligned
bounding box.

## Solution

### The simple, axis-aligned form

```python
import Metashape

chunk = Metashape.app.document.chunk
points = chunk.tie_points.points

xs = [p.coord[0] / p.coord[3] for p in points if p.valid]
ys = [p.coord[1] / p.coord[3] for p in points if p.valid]
zs = [p.coord[2] / p.coord[3] for p in points if p.valid]

m = Metashape.Vector([min(xs), min(ys), min(zs)])
M = Metashape.Vector([max(xs), max(ys), max(zs)])

chunk.region.center = (M + m) / 2
chunk.region.size = M - m
chunk.region.rot = Metashape.Matrix.Diag([1, 1, 1])         # axis-aligned
```

This works on georeferenced and unreferenced chunks alike: it
never references `chunk.crs` or `chunk.transform`, so it has no
behaviour difference between the two cases.

### When to use the rotated-frame form

If you specifically want the region's axes aligned to *East /
North / Up* at the cloud's centroid (e.g. for an aerial project
where you'll subsequently set up an orthomosaic in the local
geographic frame), the simple axis-aligned form is wrong — its
axes follow the chunk's internal frame, which is arbitrary
relative to the geographic frame after georeferencing.

The recipe walks the chunk's transform into the CRS local
frame and back:

```python
import math
import Metashape

chunk = Metashape.app.document.chunk
T = chunk.transform.matrix             # 4×4 chunk-to-world (2.x API)

# 1. Pick a reference point at the chunk origin.
v = Metashape.Vector([0, 0, 0, 1])
v_t = T * v
v_t.size = 3                            # drop homogeneous coordinate

# 2. The CRS local frame at v_t — its rows are East / North / Up.
m = chunk.crs.localframe(v_t)

# 3. Combine: m * T maps chunk-internal coords to ENU at v_t.
m = m * T

# 4. Extract the scale factor s implicit in the chunk transform.
s = math.sqrt(m[0, 0]**2 + m[0, 1]**2 + m[0, 2]**2)

# 5. The pure rotation R is m's 3×3 part, divided by s.
R = Metashape.Matrix([
    [m[0, 0] / s, m[0, 1] / s, m[0, 2] / s],
    [m[1, 0] / s, m[1, 1] / s, m[1, 2] / s],
    [m[2, 0] / s, m[2, 1] / s, m[2, 2] / s],
])

# 6. Apply to chunk.region.rot — region's axes now align to ENU.
#    The R.t() transpose convention follows the canonical
#    forum-attested script; whether the convention is
#    transpose-vs-direct is pending Tier 3 verification.
chunk.region.rot = R.t()

# 7. Set region center to the tie-point centroid (in internal
#    coordinates). Without this step the region keeps its
#    previous centre — typically wrong after the rotation.
points = [p.coord for p in chunk.tie_points.points if p.valid]
xs = [p[0] / p[3] for p in points]
ys = [p[1] / p[3] for p in points]
zs = [p[2] / p[3] for p in points]
centroid = Metashape.Vector([
    (min(xs) + max(xs)) / 2,
    (min(ys) + max(ys)) / 2,
    (min(zs) + max(zs)) / 2,
])
chunk.region.center = centroid

# 8. Optionally set region size in real-world units (metres).
#    Because the bundle's internal scale is s, a real-world size
#    must be divided by s to express it in internal units:
chunk.region.size = Metashape.Vector([100.0 / s, 100.0 / s, 50.0 / s])
```

> **Demo verified:** ✗ — pending Tier 3 reproduction on a
> georeferenced sample dataset. The math (localframe + matrix
> composition + scale extraction) is canonical; the `R.t()`
> transpose convention is taken from the source thread's
> 2014-era script and has not been independently verified on
> 2.x.

Two key behavioural facts underpin the recipe:

> "Chunk.region.size and center are in the internal units
> referred to the internal chunk coordinate system. So, for
> example, to convert chunk.region.center vector from this
> system you need to use chunk.transform matrix" — Alexey
> Pasumansky, 2014-01-09, PhotoScan 1.0
> ([permalink](https://www.agisoft.com/forum/index.php?topic=1886.msg10041#msg10041))

> "When using real-world scales for the bounding box size you
> need to divide them by the scale factor s, calculated during
> rotation estimation. As for the region center coordinates, you
> need to use all three point coordinates X, Y and Z, otherwise
> centerGEO vector in geocentric coordinates will be calculated
> incorrectly due to zero altitude above ellipsoid using in the
> script provided." — Alexey Pasumansky, 2014-12-09, PhotoScan 1.0
> ([permalink](https://www.agisoft.com/forum/index.php?topic=1886.msg16605#msg16605))

The two-coordinate gotcha (omitting altitude) is a recurring
source of bugs in older scripts. Always pass three real-world
coordinates when computing a geocentric region centre, even if
the project is "essentially 2D."

**API note for older scripts.** Pre-1.1 scripts use
`chunk.transform` directly. From PhotoScan 1.1 (2015) onward,
`chunk.transform` is a wrapper object — the matrix is at
`chunk.transform.matrix`:

> "There were some major changes in Python API for version 1.1.
> Transformation matrix for chunk is now accessible via
> chunk.transform.matrix." — Alexey Pasumansky, 2014-09-29,
> PhotoScan 1.0 → 1.1 transition
> ([permalink](https://www.agisoft.com/forum/index.php?topic=1886.msg15464#msg15464))

### Excluding outliers before the resize

The simple form has a known weakness: **a few outlier tie
points far from the main cloud will inflate the region**.
Mitigations:

1. Run *Clean Tie Points* by *Reconstruction Uncertainty* and
   *Reprojection Error* first (see [The Clean Tie Points → Optimize
   Cameras loop](../optimization/clean-tie-points-optimize-cameras-loop.md)).
2. Drop the bottom and top *p*-th percentile of each axis before
   taking min/max:
   ```python
   def clamp(coords, lo=0.01, hi=0.99):
       coords = sorted(coords)
       n = len(coords)
       return coords[int(n * lo) : int(n * hi)]
   ```

## Caveats and gotchas

- **`point.coord` is a 4-vector in homogeneous coordinates.**
  Always dehomogenise with `coord[i] / coord[3]` before taking
  min/max. Skipping the divisor produces wildly wrong values.
- **`point.valid` filters out tracks that did not triangulate.**
  `chunk.tie_points.points` includes invalid placeholders; the
  list comprehension's `if p.valid` is required.
- **`chunk.region` is in internal coordinates.** Setting it from
  CRS coordinates (e.g. via `chunk.crs.unproject(...)` without
  also applying `chunk.transform.matrix.inv()`) produces a region
  that does not match the cloud at all — a common bug in
  hand-written variants.
- **The forum's CRS-roundtrip script is mathematically correct
  for the rotated-frame case** but does substantially more work
  than the simple form. Use it only when you specifically want
  the local-frame rotation.

## Runnable demonstration on the Aerial-with-GCPs sample dataset

The script below resets the region to bound the tie-point cloud
on an aligned chunk. Use the [Aerial-with-GCPs](../../reference/sample-data.md#aerial-images-with-gcps)
sample after alignment.

> **Demo verified:** ✗ — pending Tier 3 reproduction on Metashape
> Pro 2.2 / 2.3 with the *Aerial-with-GCPs* sample dataset. The
> underlying APIs are introspection-verified but the demo as
> written has not been run end-to-end. Required before the manual
> ships.

```python
"""Resize chunk.region to bound the tie-point cloud on the
Aerial-with-GCPs sample dataset.

Workflow: align Aerial-with-GCPs in the GUI first, then run this
script in *Tools → Run Script…* against the aligned chunk. The
script prints the before/after region size so you can confirm it
shrank to fit the cloud.
"""

import Metashape

chunk = Metashape.app.document.chunk
if chunk is None:
    raise SystemExit("Open the aligned Aerial-with-GCPs chunk first.")

before = chunk.region
print(
    f"before: center={tuple(round(v, 2) for v in before.center)}  "
    f"size={tuple(round(v, 2) for v in before.size)}"
)

points = chunk.tie_points.points
xs = [p.coord[0] / p.coord[3] for p in points if p.valid]
ys = [p.coord[1] / p.coord[3] for p in points if p.valid]
zs = [p.coord[2] / p.coord[3] for p in points if p.valid]

m = Metashape.Vector([min(xs), min(ys), min(zs)])
M = Metashape.Vector([max(xs), max(ys), max(zs)])

chunk.region.center = (M + m) / 2
chunk.region.size = M - m
chunk.region.rot = Metashape.Matrix.Diag([1, 1, 1])

after = chunk.region
print(
    f"after:  center={tuple(round(v, 2) for v in after.center)}  "
    f"size={tuple(round(v, 2) for v in after.size)}"
)
print(
    f"valid points used: {len(xs)} of {len(points)} "
    f"({100 * len(xs) / len(points):.1f}%)"
)
```

Expected: the *after* region is smaller than the *before* on each
axis (typical for an aligned chunk where the default region was
oversized). The *valid points used* count matches the *Points: y*
half of the chunk-info display (insight-0011); invalid points are
correctly excluded by the `p.valid` filter.

After running, switch to *Region → Show Bounding Box* in the GUI
and confirm the region tightly encloses the cloud. To see the
opposite — the longer CRS-roundtrip form — implement the snippet
from the linked forum thread under *References* below and run on
the same chunk; the bounding boxes should be the same axis-aligned
cuboid (modulo small numerical differences).

## See also

- [Programmatic chunk.region control: move, scale, rotate the
  bounding box](region-control-python.md)
  — once the region is set, this article covers the operational
  patterns for translating, scaling, and rotating it
  programmatically.
- [Repositioning a chunk: moving the origin to a known point](repositioning-chunk-origin.md)
  — for moving the chunk origin (different operation from
  region positioning).
- [Mesh surface types: Arbitrary vs Height field](../mesh/mesh-surface-types.md)
  — Height-field mesh generation requires the region's red face
  to be oriented along the desired reconstruction-plane normal.

## References

- **Official manual:** *Metashape Pro User Manual*, ch. 3
  "General workflow" → "Aligning photos and laser scans" → the
  *Region* description (Pro 2.3 PDF — region selection is
  documented as a GUI operation).
- **Python Reference:** `Metashape.Chunk.region`,
  `Metashape.Region` (with `.center`, `.size`, `.rot`),
  `Metashape.Chunk.tie_points`, `Metashape.TiePoints.Point`
  (with `.coord` and `.valid`) — *Metashape Python API
  Reference*, version 2.3.1.
- **Forum:** [Pasumansky, 2017-08-14, PhotoScan 1.3](https://www.agisoft.com/forum/index.php?topic=7543.msg36125#msg36125)
  — the CRS-roundtrip reference snippet. *This article
  intentionally documents a simpler alternative that does not use
  the round-trip; both produce a region that bounds the cloud.*
- **Related articles:** [Reproducing chunk-info statistics in Python](../../topics/repeatability-qa/reproducing-chunk-info-statistics-python.md)
  — uses the same `chunk.tie_points.points` collection but for
  error metrics rather than region bounds.
- **Suggested sample dataset:** [Aerial images (with GCPs)](../../reference/sample-data.md#aerial-images-with-gcps).
  444 images, 18 GCPs, georeferenced — the dataset where the
  rotated-frame form might be relevant. Run both forms on it and
  compare; for a typical UAV project, the difference is small.
