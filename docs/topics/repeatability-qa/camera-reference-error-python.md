---
title: "Camera reference error: computing per-camera location and orientation residuals in Python"
status: unverified
applies_to: Metashape Pro 2.x — and PhotoScan 1.x via the same `chunk.transform.matrix` and `chunk.crs` API surface
edition: Pro
last_reviewed: 2026-05-29
diataxis: how-to
confidence: high
---

# Camera reference error: computing per-camera location and orientation residuals in Python

> **Confidence:** *high.* Both recipes are forum-attested by
> Agisoft support with permalinks (2019). The
> `chunk.transform.matrix`, `chunk.crs.project`,
> `chunk.crs.unproject`, `camera.center`, and
> `camera.reference.location` API are introspection-confirmed on
> Metashape 2.2.

## Problem

You have a chunk with reference data (GNSS-derived camera
positions, surveyed marker coordinates, or both) and you've run
*Align Photos* + *Optimize Cameras*. The Reference pane shows
*Estimated* values next to the *Source* values, but you need to
**compute the per-camera errors programmatically** — for QA
reporting, batch-processing scripts that flag outliers, or
custom error metrics the GUI does not display.

A few related questions:

- "What's the difference between the *source* GPS and the
  *estimated* position for each camera?"
- "Why doesn't `camera.location_accuracy` change after
  alignment?"
- "How do I get the bundle's RMS error in metres, not pixels?"

## Context

Metashape exposes the building blocks but not the per-camera
error directly:

| Field | Meaning |
|-------|---------|
| `camera.reference.location` | Source location in the chunk's CRS (the *Source* column in the Reference pane) |
| `camera.reference.location_accuracy` | The user-supplied measurement precision (metres). **This is fixed input, not an output.** |
| `camera.transform` | The bundle-estimated 4×4 pose in chunk-local coordinates (None if unaligned) |
| `camera.center` | The camera centre in chunk-local coords (= `camera.transform.translation()`) |
| `chunk.transform.matrix` | The 4×4 chunk-local → world transform |
| `chunk.crs` | The world coordinate system (None for un-georeferenced chunks) |

The "per-camera error" is the difference between
`camera.reference.location` and the world-space projection of
`camera.center` after applying `chunk.transform.matrix`.

## Recipe — per-camera location error

> "If you need to get the difference between the estimated
> camera locations and the source values, input to the Reference
> pane, then you can use the following code"
> — Agisoft support, 2019-02-13, Metashape 1.5
> ([permalink](https://www.agisoft.com/forum/index.php?topic=10415.msg47414#msg47414))

> **Demo verified:** ✗ — pending Tier 3 reproduction on a real Metashape install.

```python
import Metashape

chunk = Metashape.app.document.chunk
T = chunk.transform.matrix
crs = chunk.crs

if crs is None:
    raise RuntimeError("chunk has no CRS — error must be computed in chunk-local coords")

print(f"{'Label':<20} {'Error (m)':>12}")
print("-" * 35)
for camera in chunk.cameras:
    if not camera.transform or not camera.reference.location:
        continue
    # Estimated: chunk-local center → world geocentric → CRS coords
    estimated_world = T.mulp(camera.center)
    estimated_geo = crs.project(estimated_world)

    # Source: from Reference pane (already in CRS coords)
    source_geo = camera.reference.location

    # Difference in metres (Vector subtraction in 3D, then norm)
    err = (
        crs.unproject(estimated_geo) - crs.unproject(source_geo)
    ).norm()
    print(f"{camera.label:<20} {err:>12.3f}")
```

Notes on the projection / unprojection round-trip:

- `crs.project(world_xyz)` converts geocentric (X, Y, Z) →
  CRS coordinates (e.g., longitude, latitude, height for a
  geographic CRS, or easting/northing/elevation for a projected
  one).
- `crs.unproject(crs_coords)` is the inverse, returning
  geocentric (X, Y, Z).
- Computing the norm in **geocentric** coordinates (the
  `unproject(estimated) - unproject(source)` form above) gives
  metres directly. Computing norms on raw CRS values would
  mix degrees and metres for geographic CRSes.

## Recipe — RMS error across all aligned cameras

> "To get the total error value for the aligned cameras I can
> suggest the following code"
> — Agisoft support, 2019-07-04, Metashape 1.5
> ([permalink](https://www.agisoft.com/forum/index.php?topic=11077.msg49903#msg49903))

> **Demo verified:** ✗ — pending Tier 3 reproduction on a real Metashape install.

```python
import math
import Metashape

chunk = Metashape.app.document.chunk
T = chunk.transform.matrix
crs = chunk.crs

sum_sq = 0.0
n = 0
for camera in chunk.cameras:
    if not camera.transform or not camera.reference.location:
        continue
    estimated_geoc = T.mulp(camera.center)
    err_vec = crs.unproject(camera.reference.location) - estimated_geoc
    sum_sq += err_vec.norm() ** 2
    n += 1

if n > 0:
    rms_error_m = math.sqrt(sum_sq / n)
    print(f"Camera location RMS error: {rms_error_m:.3f} m  ({n} cameras)")
```

The result is the **3D Euclidean RMS** between source and
estimated locations across all aligned reference cameras.

## Why `camera.reference.location_accuracy` doesn't change

> "`camera_location_accuracy` parameter defines the precision of
> the measurement device, so this value is fixed and wouldn't
> change due to the processing workflow."
> — Agisoft support, 2019-02-13, Metashape 1.5
> ([permalink](https://www.agisoft.com/forum/index.php?topic=10415.msg47414#msg47414))

Common confusion: users expect `camera.reference.location_accuracy`
to drop after Optimize Cameras as the bundle "improves" the
estimate. It does not. That field stores **input data**: the
measurement precision the user (or EXIF parser) declared when
the source position was loaded. The bundle uses it as a weight
on the residual, but never modifies it.

To get an **output** quality metric, compute the per-camera
location error using the recipes above. The "estimated minus
source" residual is the bundle's actual achievement against the
input data.

## Recipe — per-camera orientation error (yaw/pitch/roll)

For projects with reference rotations (e.g., drone IMU
orientations), compute orientation residuals separately:

> **Demo verified:** ✗ — pending Tier 3 reproduction on a real Metashape install.

```python
import math
import Metashape

chunk = Metashape.app.document.chunk
T = chunk.transform.matrix

print(f"{'Label':<20} {'Δyaw':>8} {'Δpitch':>8} {'Δroll':>8}  (degrees)")
print("-" * 50)
for camera in chunk.cameras:
    if not camera.transform or not camera.reference.rotation:
        continue
    # Estimated rotation in world frame
    R_local = camera.transform.rotation()
    R_world = T.rotation() * R_local
    # Convert to yaw-pitch-roll using Metashape's helper
    estimated_ypr = Metashape.Utils.mat2ypr(R_world)
    source_ypr = camera.reference.rotation

    diffs = [estimated_ypr[i] - source_ypr[i] for i in range(3)]
    print(f"{camera.label:<20}"
          f" {diffs[0]:>+8.3f} {diffs[1]:>+8.3f} {diffs[2]:>+8.3f}")
```

The signs show direction of error; the magnitudes are absolute
residuals in degrees. For a project with cm-precise position
priors but loose rotation priors, you'll typically see <0.1°
location-derived rotation residuals and several degrees of
direct-orientation residuals.

For the conventions and the omega-phi-kappa equivalent see
[YPR rotation conventions: `ypr2mat` vs `camera.reference.rotation`](../scripting/ypr-rotation-conventions.md).

## Caveats

- **`camera.transform` is None for unaligned cameras.** Always
  check before using; the recipes above skip unaligned ones.
- **`camera.reference.location` is None for cameras without
  reference data.** Check before using; the recipes skip them.
- **The error is in chunk CRS units.** For geographic CRSes
  (lat/lon/height), convert through `crs.unproject` first to
  get metres. For projected CRSes (UTM, State Plane), the
  difference of projected XYZ values is already in metres but
  ignores Earth-curvature effects over large areas.
- **GPS reference accuracy ≠ alignment accuracy.** A 2 m GPS
  RMS does not mean the bundle's geometric accuracy is 2 m. The
  bundle can be far better internally but constrained to drift
  by ~2 m to fit the GPS data. For the *internal* geometric
  accuracy, look at reprojection error (in pixels) — see
  [Reprojection error analysis: per-camera and per-tie-point](reprojection-error-analysis.md).
- **`chunk.crs` is None for un-georeferenced chunks.** The
  recipes above raise / skip in that case. Comparison without
  a CRS is meaningless because there are no source coordinates
  to compare against.
- **The orientation-error recipe assumes YPR convention.**
  If your project uses omega-phi-kappa (set in *Reference*
  pane → *Settings* → *Rotation angles*), use
  `Metashape.Utils.mat2opk` instead.

## See also

- [Reprojection error analysis: per-camera and per-tie-point](reprojection-error-analysis.md)
  — pixel-space residuals (the bundle's internal geometric
  quality measure).
- [DSM ridge-line artefacts: alignment-quality diagnosis](dsm-ridge-lines-diagnosis.md)
  — when reference errors signal a deeper alignment problem.
- [YPR rotation conventions](../scripting/ypr-rotation-conventions.md)
  — for the orientation-error recipe.
- [Cleaning tie points + Optimize Cameras: the loop](../../workflow/optimization/clean-tie-points-optimize-cameras-loop.md)
  — the iterative procedure that reduces residuals across passes.

## References

- *Metashape Pro User Manual* (2.3), ch. 4 *Improving camera
  alignment* — Reference pane and accuracy parameters.
- *Metashape Python API Reference* (2.3.1):
  `Camera.transform`, `Camera.center`, `Camera.reference`,
  `Reference.location`, `Reference.location_accuracy`,
  `Reference.rotation`, `Chunk.transform`, `Matrix.mulp`,
  `Matrix.rotation`, `CoordinateSystem.project`,
  `CoordinateSystem.unproject`, `Utils.mat2ypr`,
  `Utils.mat2opk`.
- Forum thread, [*Getting the final accuracy for the reference
  coordinates*, 2019](https://www.agisoft.com/forum/index.php?topic=10415.msg47137#msg47137)
  — per-camera location error recipe; the
  `location_accuracy` is fixed-input clarification.
- Forum thread, [*How to return total camera error*, 2019](https://www.agisoft.com/forum/index.php?topic=11077.msg49903#msg49903)
  — RMS aggregation recipe.
- [*How to calculate estimated Exterior Orientation parameters for the cameras using Python* (Agisoft KB)](https://agisoft.freshdesk.com/support/solutions/articles/31000145016)
  — supplementary tutorial.

