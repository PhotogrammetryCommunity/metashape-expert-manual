---
title: "Scalebar distance error: per-scalebar values and RMS aggregation"
status: unverified
applies_to: Metashape Pro 2.x — and PhotoScan 1.x via the same `chunk.scalebars` API; per-scalebar dictionary indexing requires Metashape ≥ 2.0.4 (Scalebar became hashable)
edition: "Pro / Standard"
last_reviewed: 2026-06-05
diataxis: how-to
confidence: high
---

# Scalebar distance error: per-scalebar values and RMS aggregation

> **Confidence:** *high.* The scalebar error formula
> (estimated minus reference, with `chunk.transform.scale`
> applied) is forum-attested with permalink (Agisoft support,
> 2016, t=6147). The
> `Chunk.scalebars`, `Scalebar.point0`, `Scalebar.point1`,
> `Scalebar.reference.distance`, `Scalebar.reference.enabled`
> API surface is introspection-confirmed on Metashape 2.2.

## Problem

You've added scalebars to a chunk — between two markers, or
between two camera centres for a known-baseline rig — and
need programmatic access to:

- **Per-scalebar distance error** in metres for QA reports.
- **Chunk-wide RMS** distance error across all scalebars.
- **Control vs check** scalebar separation (check scalebars
  not bound into the bundle, used post-hoc for validation).

The Metashape *Reference* pane shows aggregate scalebar info
but extracting per-scalebar error in Python takes a few API
steps that aren't obvious from the docs.

## How scalebar error is computed

For each scalebar, the **reference distance** is the
user-supplied real-world value (in metres) accessible via
`scalebar.reference.distance`. The **estimated distance** is
the actual distance between the two endpoints in chunk-local
units, multiplied by `chunk.transform.scale` to convert to
real-world metres.

The endpoints (`scalebar.point0`, `scalebar.point1`) can be
either `Marker` or `Camera` objects. For markers, use
`marker.position`; for cameras, use `camera.center`. Both are
in chunk-internal coordinates.

The error is straightforward:

```
error_m = (estimated_distance - reference_distance)
```

with `estimated_distance` computed from chunk-local geometry
and scaled to metres via `chunk.transform.scale`.

> "Providing that the chunk is referenced, scale bar has
> input (source) distance and both of it's ends are defined in
> space you can use the following code to get the estimated
> distance and errors"
> — Agisoft support, 2016-12-06, PhotoScan 1.2
> ([permalink](https://www.agisoft.com/forum/index.php?topic=6147.msg30121#msg30121))

## Recipe — per-scalebar distance error

> **Demo verified:** ✗ — pending Tier 3 reproduction on a real Metashape install.

```python
import Metashape

chunk = Metashape.app.document.chunk
scale = chunk.transform.scale or 1.0

def endpoint_position(point):
    """Return chunk-local 3D position of a Marker or Camera scalebar endpoint."""
    if isinstance(point, Metashape.Marker):
        return point.position
    return point.center  # Camera

print(f"{'Scalebar':<25} {'Type':<8} {'Reference (m)':>14} "
      f"{'Estimated (m)':>14} {'Error (m)':>12}")
print("-" * 80)
for sb in chunk.scalebars:
    ref_dist = sb.reference.distance
    if not ref_dist:
        continue   # no source distance set

    p0 = endpoint_position(sb.point0)
    p1 = endpoint_position(sb.point1)
    if p0 is None or p1 is None:
        continue   # endpoint not triangulated yet

    estimated_local = (p1 - p0).norm()
    estimated_m = estimated_local * scale
    error_m = estimated_m - ref_dist
    sb_type = "control" if sb.reference.enabled else "check"

    print(f"{sb.label:<25} {sb_type:<8} {ref_dist:>14.4f} "
          f"{estimated_m:>14.4f} {error_m:>+12.4f}")
```

The sign of `error_m` matters:

- **Positive**: the bundle's estimate is *longer* than the
  reference. Common cause: the bundle's scale is loose and
  the scalebar is "stretching" the chunk.
- **Negative**: estimate is *shorter*. Bundle is "compressing"
  the chunk — common when the scalebar reference is too tight
  (over-stating its precision) and pulling neighbouring tie
  points closer.

For sub-millimetre absolute errors you typically need
calibrated scalebars and the bundle's `optimizeCameras` step
to actively fit them.

## Control vs check scalebars

Just like markers, scalebars carry a `reference.enabled` flag
that determines whether the bundle adjustment uses the
scalebar as a constraint:

- **`enabled = True` (control).** The bundle uses this
  scalebar's reference distance during *Update Transform*
  and *Optimize Cameras*. The estimated distance will be
  pulled toward the reference, weighted by
  `reference.accuracy`.
- **`enabled = False` (check).** The bundle ignores the
  reference distance. The error is a **post-hoc validation**:
  does the chunk's geometry, derived from other constraints
  (markers, GPS, image content), agree with the scalebar's
  known length?

Splitting a chunk's scalebars into control and check sets is
the photogrammetric equivalent of splitting markers into
ground-control points (GCPs) and check points: control
constrains, check validates.

## Recipe — RMS aggregation by control / check

> **Demo verified:** ✗ — pending Tier 3 reproduction on a real Metashape install.

```python
import math
import Metashape
from collections import defaultdict

def endpoint_position(point):
    """Return chunk-local 3D position of a Marker or Camera scalebar endpoint."""
    if isinstance(point, Metashape.Marker):
        return point.position
    return point.center  # Camera

chunk = Metashape.app.document.chunk
scale = chunk.transform.scale or 1.0

sumsq = defaultdict(float)
count = defaultdict(int)

for sb in chunk.scalebars:
    ref = sb.reference.distance
    if not ref:
        continue
    p0 = endpoint_position(sb.point0)
    p1 = endpoint_position(sb.point1)
    if p0 is None or p1 is None:
        continue

    err = (p1 - p0).norm() * scale - ref
    err_sq = err * err

    bucket = "control" if sb.reference.enabled else "check"
    sumsq[bucket] += err_sq
    count[bucket] += 1
    sumsq["all"] += err_sq
    count["all"] += 1

for bucket in ("control", "check", "all"):
    if count[bucket] > 0:
        rms = math.sqrt(sumsq[bucket] / count[bucket])
        print(f"{bucket.capitalize():<10} scalebars: RMS error = {rms:.4f} m  "
              f"(over {count[bucket]} scalebars)")
```

The "all" bucket reports the chunk-wide RMS regardless of
which scalebars are enabled. The control / check split lets
you separately report:

- **Control RMS**: how well the bundle has fit the constraints
  it was given.
- **Check RMS**: how well the chunk's geometry generalises
  to scalebars the bundle has not seen.

A large gap between the two (e.g., control RMS 1 mm vs check
RMS 50 mm) indicates the bundle has overfit the control
scalebars at the cost of overall geometric accuracy — usually
because the control set is too small or unrepresentative.

## Marker-vs-camera endpoint cases

Both endpoints of a scalebar can be either a marker or a
camera centre. Common configurations:

- **Marker ↔ marker.** Two surveyed targets with a
  laser-range or measuring-tape reference distance. The
  classic photogrammetric scalebar.
- **Camera ↔ camera.** Two cameras on a known-baseline rig
  (stereo capture, multi-camera array). Uses the camera
  centres' known separation as the reference.
- **Marker ↔ camera.** Less common; sometimes used in
  precision metrology when one endpoint is a fixed reference
  marker and the other is a camera with a precisely-measured
  optical centre.

The `endpoint_position` helper in the recipes handles both
cases via `isinstance(point, Metashape.Marker)`.

## When `chunk.transform.scale` is wrong

The recipe multiplies the chunk-local distance by
`chunk.transform.scale` to convert to metres. This works for:

- **Georeferenced chunks**: scale is automatic from
  `updateTransform` against the reference data.
- **Local-frame chunks with at least one control scalebar**:
  the bundle uses the scalebar to estimate scale.
- **Manually-scaled chunks**: scale was set via
  `chunk.transform.scale = X` in a script or via *Update
  Transform* with a known scale.

For chunks where none of these apply, `chunk.transform.scale`
may be `None` (recipe falls back to 1.0) or a meaningless
arbitrary value left from initialisation. The estimated
distances will then be in chunk-local units, not metres —
and the errors will be in the same arbitrary units.

For more on this, see
[The chunk's internal coordinate system: arbitrary scale and
`chunk.transform.scale`](../scripting/chunk-internal-scale-and-units.md).

## Caveats

- **`scalebar.reference.distance` may be `None`**. Scalebars
  without a reference distance are unconstrained and should
  be skipped. The recipes guard with `if not ref_dist`.
- **Endpoints may not be triangulated yet.** A new marker
  scalebar where the markers haven't been pinned on enough
  cameras has `marker.position is None`; iterate after the
  bundle has run, or guard explicitly.
- **Per-scalebar dictionary key requires Metashape ≥ 2.0.4.**
  Earlier versions can't use `Scalebar` objects as dict keys
  (the type wasn't hashable). The recipes above use a `label`
  string for output and don't rely on Scalebar-as-key, so
  they work on older versions; if you need a per-scalebar
  result dict, key by `scalebar.label` or `id(scalebar)`.
- **`chunk.transform.scale` is a property, not a method.**
  Use it directly without `()`.
- **`reference.accuracy` weights the bundle, not the
  computed error.** The accuracy field tells the bundle how
  tightly to weight the scalebar's constraint; it doesn't
  change the post-hoc error computation. A scalebar with
  `accuracy = 0.001` (1mm precision claimed) and the bundle
  unable to fit it within 5cm produces the same 5cm error as
  if `accuracy` were 1.0. The accuracy only matters during
  *Update Transform* / *Optimize Cameras*.
- **CRS rotation doesn't affect distance.** Whether the chunk
  is in a local CRS, UTM, geographic lat-lon, or geocentric
  ECEF, the *distance* between two 3D points is the
  Euclidean norm of the vector difference. The recipes
  therefore work in chunk-local coordinates without needing
  CRS projection.
- **For very long baselines (km-scale) on geographic CRSes**,
  the chunk-local approximation breaks down because Earth
  curvature isn't included. For sub-km scalebars, the chunk's
  flat-frame approximation is well within typical accuracy
  expectations.

## See also

- [Marker projection statistics: counts, per-marker errors, and metre-vs-pixel framing](marker-projection-statistics.md)
  — the same control/check distinction applied to markers.
- [Camera reference error: per-camera location and orientation residuals in Python](camera-reference-error-python.md)
  — per-camera distance from GPS reference, the
  marker/scalebar analogue at the camera level.
- [Reproducing chunk-info statistics in Python](reproducing-chunk-info-statistics-python.md)
  — the chunk-wide reproducible-statistics recipe; a
  scalebar-error block plugs in nicely.
- [The chunk's internal coordinate system: arbitrary scale and `chunk.transform.scale`](../scripting/chunk-internal-scale-and-units.md)
  — explains the scale factor that the recipes here apply.

## References

- *Metashape Pro User Manual* (2.3), ch. 4 *Improving camera
  alignment* — Reference pane and scalebar workflow.
- *Metashape Python API Reference* (2.3.1):
  `Chunk.scalebars`, `Scalebar.point0`, `Scalebar.point1`,
  `Scalebar.label`, `Scalebar.reference`,
  `Scalebar.Reference.distance`, `Scalebar.Reference.enabled`,
  `Scalebar.Reference.accuracy`, `Marker.position`,
  `Camera.center`, `Chunk.transform`,
  `ChunkTransform.scale`.
- Forum thread, [*Total Error of References*](https://www.agisoft.com/forum/index.php?topic=6147.msg30121#msg30121)
  — Agisoft support, 2016-12-06,
  PhotoScan 1.2. The canonical scalebar-error recipe walks
  through both Marker and Camera endpoint cases and the
  `chunk.transform.scale` factor.
- Forum thread, [*Set distances of scalebars via Python API*](https://www.agisoft.com/forum/index.php?topic=14526.msg64060#msg64060)
  — Agisoft support, 2022-05-30,
  Metashape 2.0. The `scalebar.reference.distance =` and
  `scalebar.reference.enabled =` setter pattern, including
  the required `chunk.updateTransform()` call after batch
  updates.
- [*Creating scale bars in the project without coded targets* (Agisoft KB)](https://agisoft.freshdesk.com/support/solutions/articles/31000162602)
  and [*Coded targets and Scale bars* (Agisoft KB)](https://agisoft.freshdesk.com/support/solutions/articles/31000148855)
  — Agisoft's GUI workflows for building scale bars (manually
  between markers, or from detected coded targets) and setting
  their reference distance and accuracy.

