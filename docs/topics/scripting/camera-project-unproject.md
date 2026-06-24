---
title: "`camera.project` and `camera.unproject`: 2D ↔ 3D in Python"
status: unverified
applies_to: Metashape Pro 2.x — and PhotoScan 1.x via the same `Camera.project` / `Calibration.unproject` API
edition: Pro
last_reviewed: 2026-05-29
diataxis: how-to
confidence: high
---

# `camera.project` and `camera.unproject`: 2D ↔ 3D in Python

> **Confidence:** *high.* The API is forum-attested with
> permalink (Agisoft support, 2024). The
> `Camera.project`, `Camera.unproject`, `Sensor.calibration`,
> and `Calibration.project` / `Calibration.unproject` are
> introspection-confirmed on Metashape 2.2.

## Problem

Photogrammetry workflows constantly translate between
**2D image pixels** and **3D world points**. Common needs:

- "Where on this image does my 3D point project?"
- "Given a pixel I clicked, what 3D ray does it correspond to?"
- "Convert drone image pixels to global lat/lon coordinates."
- "For a given (camera, 3D point) pair, what's the reprojection
  residual in pixels?"

Metashape exposes these via `Camera.project`,
`Camera.unproject`, and the lower-level
`Calibration.project` / `Calibration.unproject`. The four
methods cover the four directions:

| Method | Input | Output |
|--------|-------|--------|
| `camera.project(point_3d)` | 3D point in chunk-local coords | 2D pixel coordinates on this image |
| `camera.unproject(point_2d)` | 2D pixel + (optional) depth | 3D point in chunk-local coords |
| `sensor.calibration.project(point_3d)` | 3D point in **camera-local** coords | 2D pixel |
| `sensor.calibration.unproject(point_2d)` | 2D pixel | 3D ray endpoint in **camera-local** coords |

The Camera-level methods include the camera's pose
(`camera.transform`); the Calibration-level methods operate in
the camera's own frame (origin = optical centre, Z = forward).

> "`camera.project` method can be used to get the 2D pixel
> coordinates in the image space of the 3D point (defined in
> the internal coordinate system of the chunk)."
> — Agisoft support, 2024-06-07, Metashape 2.1
> ([permalink](https://www.agisoft.com/forum/index.php?topic=16481.msg70795#msg70795))

## Recipe — 3D point → image pixel

> **Demo verified:** ✗ — pending Tier 3 reproduction on a real Metashape install.

```python
import Metashape

chunk = Metashape.app.document.chunk
camera = chunk.cameras[0]

# A 3D point in chunk-local coordinates
target_3d = Metashape.Vector([5.0, 3.0, 0.5])

# Project to this camera's image plane
pixel = camera.project(target_3d)

if pixel is None:
    print(f"{camera.label}: target is behind camera or off-image")
else:
    print(f"{camera.label}: target projects to pixel ({pixel.x:.1f}, {pixel.y:.1f})")
```

`camera.project` returns `None` when:

- The 3D point is behind the camera (negative Z in camera frame)
- The projected pixel falls outside the image bounds (after
  distortion warping)

For "is this point visible from this camera?" tests, check
`pixel is not None` and verify the pixel is within
`(0, 0)` to `(camera.sensor.width, camera.sensor.height)`.

## Recipe — image pixel → 3D ray

The inverse operation is fundamentally under-determined: a 2D
pixel corresponds to a *ray* through the camera centre, not a
single 3D point. `camera.unproject` returns the ray's direction
endpoint at unit depth.

> **Demo verified:** ✗ — pending Tier 3 reproduction on a real Metashape install.

```python
import Metashape

chunk = Metashape.app.document.chunk
camera = chunk.cameras[0]

# A pixel I want to convert
pixel = Metashape.Vector([1024.0, 768.0])

# Unproject to a 3D ray endpoint in chunk-local coords
# (at distance 1 unit from camera; multiply to scale)
ray_endpoint = camera.unproject(pixel)
ray_direction = (ray_endpoint - camera.center).normalized()

print(f"Ray from camera at {camera.center}")
print(f"  in direction {ray_direction}")
```

To find where the ray hits a known 3D plane (e.g., the chunk's
ground at Z=0), parameterise:

> **Demo verified:** ✗ — pending Tier 3 reproduction on a real Metashape install.

```python
# Ground plane: chunk-local Z = 0
if abs(ray_direction.z) > 1e-6:
    t = -camera.center.z / ray_direction.z
    if t > 0:
        hit_point = camera.center + ray_direction * t
        print(f"Pixel maps to ground point: {hit_point}")
```

To find where the ray hits the chunk's mesh surface, use
`chunk.model.pickPoint(ray_origin, ray_direction)` — see
the *Picking* section below.

## Recipe — 3D world point → pixel for georeferenced data

If your input is in geographic / projected coordinates (lat/lon,
UTM), convert via the chunk's CRS first:

> **Demo verified:** ✗ — pending Tier 3 reproduction on a real Metashape install.

```python
import Metashape

chunk = Metashape.app.document.chunk
T = chunk.transform.matrix

# Target in chunk's CRS coords (e.g., latitude, longitude, elevation)
target_crs = Metashape.Vector([10.5, 47.3, 1500.0])

# Step 1: CRS → geocentric (X, Y, Z in metres)
target_geocentric = chunk.crs.unproject(target_crs)

# Step 2: geocentric → chunk-local
target_chunk_local = T.inv().mulp(target_geocentric)

# Step 3: project on each camera
for camera in chunk.cameras:
    if not camera.transform:
        continue
    pixel = camera.project(target_chunk_local)
    if pixel is None:
        continue
    if 0 <= pixel.x < camera.sensor.width and 0 <= pixel.y < camera.sensor.height:
        print(f"{camera.label}: visible at pixel ({pixel.x:.1f}, {pixel.y:.1f})")
```

This is the canonical "drone pixels to global coordinates"
workflow inverse: given an external coordinate, find which
images cover that point and where.

## Recipe — pixel → world coords via mesh intersection

For "I clicked a pixel; what's its real-world 3D position?",
ray-cast the unprojected ray against the chunk's mesh:

> **Demo verified:** ✗ — pending Tier 3 reproduction on a real Metashape install.

```python
import Metashape

chunk = Metashape.app.document.chunk
camera = chunk.cameras[0]

if not chunk.model:
    raise RuntimeError("Build the mesh first (Workflow → Build Mesh)")

pixel = Metashape.Vector([1024.0, 768.0])

# Unproject to chunk-local ray
ray_endpoint = camera.unproject(pixel)
ray_origin = camera.center

# Pick the first mesh intersection along the ray
hit = chunk.model.pickPoint(ray_origin, ray_endpoint)

if hit is None:
    print(f"Pixel {pixel} doesn't hit the mesh (looking off into space)")
else:
    # Convert chunk-local → CRS coords if you want lat/lon
    T = chunk.transform.matrix
    geocentric = T.mulp(hit)
    crs_coords = chunk.crs.project(geocentric)
    print(f"Pixel {pixel} → world {crs_coords}")
```

`Model.pickPoint(ray_origin, ray_endpoint)` returns the first
intersection in chunk-local coords, or `None` if the ray misses.
The arguments are points (not vectors); `pickPoint` constructs
the ray from `(ray_endpoint - ray_origin)`.

## Recipe — verify a tie point's reprojection residual

For per-(point, camera) reprojection error in pixels:

> **Demo verified:** ✗ — pending Tier 3 reproduction on a real Metashape install.

```python
import Metashape

chunk = Metashape.app.document.chunk
tie_points = chunk.tie_points

for camera in chunk.cameras[:3]:
    if not camera.transform:
        continue

    projections = tie_points.projections[camera]
    if projections is None:
        continue

    sum_sq, n = 0.0, 0
    for proj in projections[:50]:   # sample first 50 for speed
        track = tie_points.tracks[proj.track_id]
        # Find the 3D point with this track_id
        # (For a fast lookup, build a dict track_id → point upfront)
        for p in tie_points.points:
            if p.track_id == proj.track_id and p.valid:
                # Reproject this point onto this camera
                reprojected = camera.project(p.coord)
                if reprojected is not None:
                    residual = (reprojected - proj.coord).norm()
                    sum_sq += residual ** 2
                    n += 1
                break

    if n > 0:
        rms_px = (sum_sq / n) ** 0.5
        print(f"{camera.label}: reprojection RMS = {rms_px:.2f} px ({n} samples)")
```

For a more efficient implementation across the full point
cloud, see [Reprojection error analysis: per-camera and
per-tie-point](../repeatability-qa/reprojection-error-analysis.md).

## The Camera-level vs Calibration-level distinction

| You want… | Use |
|----------|------|
| Project / unproject in **chunk-local** world frame | `Camera.project` / `Camera.unproject` |
| Project / unproject in **camera-local** frame (origin = optical centre, Z = forward) | `Sensor.calibration.project` / `Sensor.calibration.unproject` |

Camera-level methods compose the calibration with `camera.transform`:

```
camera.project(world_pt) ≡ calibration.project(camera.transform.inv().mulp(world_pt))
camera.unproject(pixel) ≡ camera.transform.mulp(calibration.unproject(pixel))
```

Use the Calibration-level methods when:

- You're working with a synthetic camera pose (no
  `camera.transform` set yet)
- You want camera-frame ray directions (for
  [direction-vector computation](camera-direction-vectors.md))
- You're constructing a virtual `renderImage` view

Use the Camera-level methods when working with real chunk
cameras and chunk-local 3D points.

## Caveats

- **The 3D point must be in chunk-local coordinates** for
  `camera.project`. For georeferenced input (CRS coords),
  convert via `chunk.transform.matrix.inv().mulp(crs.unproject(input))`.
- **Returns are `None`-or-Vector**, not exceptions. Always
  check `is not None` before using the result.
- **Pixel coordinates are continuous floats**, not integer
  indices. A pixel at `(1024.5, 768.5)` is the centre between
  pixels (1024, 768) and (1025, 769). For image-array indexing,
  cast via `int()` or `round()`.
- **Distortion is applied automatically** in both
  `Camera.project` and `Camera.unproject`. The result is in the
  raw image pixel coordinate system, not the undistorted one.
  For undistorted pixel coords, use the calibration's
  `undistort` workflow (see undistorted-image articles).
- **`Model.pickPoint` requires a built mesh**
  (`chunk.model is not None`). For point-cloud-based picking,
  use a manual nearest-neighbour search on
  `chunk.point_cloud.points`.
- **Spherical and fisheye sensors** project differently from
  Frame. The `unproject` for these returns a unit-sphere or
  unit-hemisphere endpoint, not a Z=1 ray endpoint. The
  `(endpoint - camera.center).normalized()` direction-vector
  pattern still works.

## See also

- [Computing camera direction vectors and look-at points](camera-direction-vectors.md)
  — uses `Calibration.unproject` to derive optical-axis
  direction.
- [Converting `camera.transform` to ENU (or any local Cartesian)](camera-poses-to-enu.md)
  — for converting projected 3D points and camera poses into
  east-north-up local frame.
- [Reprojection error analysis: per-camera and per-tie-point](../repeatability-qa/reprojection-error-analysis.md)
  — efficient implementation of the residual-computation pattern.
- [`chunk.transform.matrix` is local→world; `camera.transform` is local](../crs/chunk-frame-vs-camera-frame.md)
  — the conceptual model for the chunk-local ↔ world conversions.
- [`Model.renderDepth`: synthetic depth from arbitrary viewpoints](model-render-depth.md)
  — generates depth maps from synthetic poses constructed via
  these recipes.

## References

- *Metashape Python API Reference* (2.3.1):
  `Camera.project`, `Camera.unproject`, `Sensor.calibration`,
  `Calibration.project`, `Calibration.unproject`,
  `Model.pickPoint`, `Vector`, `CoordinateSystem.project`,
  `CoordinateSystem.unproject`.
- Forum thread, [*question about camera.project and
  camera.unproject*, 2024](https://www.agisoft.com/forum/index.php?topic=16481.msg72862#msg72862)
  — the canonical Q&A explaining the chunk-local-coords
  convention.

