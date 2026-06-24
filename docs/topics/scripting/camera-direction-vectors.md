---
title: "Computing camera direction vectors and look-at points in Python"
status: unverified
applies_to: Metashape Pro 2.x — same approach in PhotoScan 1.x via `Calibration.unproject` + `camera.transform`
edition: Pro
last_reviewed: 2026-05-29
diataxis: how-to
confidence: high
---

# Computing camera direction vectors and look-at points in Python

> **Confidence:** *high.* The pattern is forum-attested by
> Agisoft support with permalink (2019). The
> `Calibration.unproject`, `camera.transform.mulp`, and
> `camera.center` API are introspection-confirmed on Metashape
> 2.2.

## Problem

You need the **3D direction the camera is looking** — a unit
vector in world coordinates pointing away from the lens, along
the optical axis. Common use cases:

- Visualising camera frusta in an external 3D tool.
- Computing the angle between a camera and a surface normal
  (for reprojection-quality assessment).
- Calculating where each camera's optical axis intersects the
  ground plane (a "look-at" point).
- Filtering cameras by viewing direction (e.g., "show me only
  the cameras facing approximately north").

Metashape doesn't expose `camera.direction` directly — it gives
you the full pose (`camera.transform`) and the calibration
(`camera.sensor.calibration`), and you derive the direction
yourself.

## Recipe — direction vector in chunk-local coordinates

The trick is to **unproject the principal point** (the image
centre) into a 3D ray, then use the camera's pose to express
that ray in chunk-local coordinates:

> "I suggest to use the following vector"
> — Agisoft support, 2019-11-07, Metashape 1.5
> ([permalink](https://www.agisoft.com/forum/index.php?topic=11506.msg51385#msg51385))

> **Demo verified:** ✗ — pending Tier 3 reproduction on a real Metashape install.

```python
import Metashape

chunk = Metashape.app.document.chunk
camera = chunk.cameras[0]

# Pixel coordinates of the image centre (the principal point's
# image-space proxy)
image_centre_px = Metashape.Vector([
    camera.sensor.width / 2,
    camera.sensor.height / 2,
])

# Unproject the image-centre pixel to a 3D ray in camera-local
# coordinates (z = 1 for a frame sensor, ray is normalized output
# of unproject)
ray_camera = camera.sensor.calibration.unproject(image_centre_px)

# Transform the ray endpoint into chunk-local coordinates,
# then subtract the camera centre to get the direction vector.
ray_world_endpoint = camera.transform.mulp(ray_camera)
direction = (ray_world_endpoint - camera.center).normalized()

print(f"{camera.label}: direction = {direction}")
```

Why subtract `camera.center`? Because `camera.transform.mulp(ray_camera)`
gives a *point* in chunk-local coordinates — specifically, the
location 1 unit along the optical axis from the camera. Subtracting
the camera's position gives the direction *vector* from the camera.

Equivalently, you can construct the direction directly from the
pose's rotation matrix:

> **Demo verified:** ✗ — pending Tier 3 reproduction on a real Metashape install.

```python
# The camera-local +Z axis IS the optical-axis direction
# in camera-local coords. Rotate to world frame:
R = camera.transform.rotation()
direction = R * Metashape.Vector([0, 0, 1])
direction.normalize()
```

Both expressions produce the same result. The first is more
explicit about what's being computed (an unprojection of the
image centre); the second is faster.

## Recipe — direction vector in world / CRS coordinates

For georeferenced chunks, transform the chunk-local direction
into world (geocentric) coordinates by applying
`chunk.transform.matrix.rotation()`:

> **Demo verified:** ✗ — pending Tier 3 reproduction on a real Metashape install.

```python
import Metashape

chunk = Metashape.app.document.chunk
T_chunk_to_world = chunk.transform.matrix.rotation()

for camera in chunk.cameras[:5]:
    if not camera.transform:
        continue

    # Direction in chunk-local
    R = camera.transform.rotation()
    dir_local = R * Metashape.Vector([0, 0, 1])

    # Direction in world (geocentric)
    dir_world = T_chunk_to_world * dir_local
    dir_world.normalize()

    print(f"{camera.label}: world direction = {dir_world}")
```

For a north-east-up (NEU) local frame around a specific
geographic point, project the chunk's centre to the CRS, then
build the local frame transform via `crs.localframe()`:

> **Demo verified:** ✗ — pending Tier 3 reproduction on a real Metashape install.

```python
crs = chunk.crs
chunk_centre_geocentric = chunk.transform.matrix.translation()
local_frame = crs.localframe(chunk_centre_geocentric)
# Apply local_frame.rotation() to dir_world to get NEU direction
```

See [Converting `camera.transform` to ENU](camera-poses-to-enu.md)
for the full recipe.

## Recipe — look-at point on the ground plane

Find where each camera's optical axis hits the chunk's ground
plane (the XY plane in chunk-local coords, or any reference
plane you define):

> **Demo verified:** ✗ — pending Tier 3 reproduction on a real Metashape install.

```python
import Metashape

chunk = Metashape.app.document.chunk
ground_z = 0.0   # chunk-local Z value of the ground plane

for camera in chunk.cameras[:5]:
    if not camera.transform:
        continue

    R = camera.transform.rotation()
    direction = (R * Metashape.Vector([0, 0, 1])).normalized()

    if abs(direction.z) < 1e-6:
        # Ray parallel to ground; no intersection
        continue

    # Parametric ray: P(t) = camera.center + t * direction
    # Find t where P.z = ground_z
    t = (ground_z - camera.center.z) / direction.z
    if t < 0:
        # Ground is "behind" the camera in its viewing direction
        continue

    look_at = camera.center + direction * t
    print(f"{camera.label}: look-at = {look_at}")
```

The look-at point is in chunk-local coords. Multiply by
`chunk.transform.matrix` to get geocentric, then `chunk.crs.project`
to get CRS coords (lat/lon/elev or easting/northing/elevation).

## Recipe — angle between two cameras' viewing directions

For camera-overlap analysis or pair-selection diagnostics:

> **Demo verified:** ✗ — pending Tier 3 reproduction on a real Metashape install.

```python
import math
import Metashape

def viewing_direction(camera):
    R = camera.transform.rotation()
    return (R * Metashape.Vector([0, 0, 1])).normalized()

cam_a = chunk.cameras[0]
cam_b = chunk.cameras[1]

if cam_a.transform and cam_b.transform:
    dir_a = viewing_direction(cam_a)
    dir_b = viewing_direction(cam_b)
    cos_angle = max(-1.0, min(1.0, dir_a * dir_b))   # dot product, clipped
    angle_deg = math.degrees(math.acos(cos_angle))
    print(f"angle between {cam_a.label} and {cam_b.label}: {angle_deg:.1f}°")
```

The dot product `dir_a * dir_b` works because Metashape's
`Vector` overloads `*` to return the scalar dot product when
both operands are vectors of the same dimension.

## Caveats

- **`camera.sensor.calibration.unproject`** for fisheye / spherical
  sensors does NOT produce a Z=1 ray. The unprojected point lies
  on the unit sphere (for spherical) or unit hemisphere (for
  fisheye). The direction-vector computation still works because
  the difference from `camera.center` is the actual ray direction,
  but the sign of `direction.z` may need flipping depending on
  the projection.
- **Camera convention.** Metashape uses Z **forward** (out of
  the lens, toward the scene), Y **down**, X **right**. This
  matches OpenCV's convention. Some downstream tools (Blender,
  three.js) use Y up + Z toward the camera, requiring an axis
  swap.
- **`camera.transform` is None for unaligned cameras.** Always
  check before computing direction.
- **The `chunk.transform.matrix` rotation** must be a pure
  rotation (no scale) for the world-space direction to be a
  unit vector. Metashape's chunk transforms typically include
  scale; use `T.rotation()` (which extracts the rotation
  component) rather than the full matrix to avoid scaling
  the direction.

## Edge case: chunk with no transform applied

If `chunk.transform.matrix` is the identity (un-georeferenced
chunk that has not been transformed to a real-world CRS), then
chunk-local and world coordinates coincide. The direction
recipes above all still work — `T.rotation()` returns the
identity rotation, so `dir_world == dir_local`.

To check:

> **Demo verified:** ✗ — pending Tier 3 reproduction on a real Metashape install.

```python
if chunk.transform.matrix.isidentity():
    # chunk-local coords are world coords
    pass
```

(Where `isidentity()` is a `Matrix` method that returns True
if the matrix is the 4×4 identity. If your project's chunk
transform is the identity but you expected it to be
non-identity, run *Update Transform* in the Reference pane to
refresh it from the loaded reference data.)

## See also

- [`camera.project` and `camera.unproject`: 2D ↔ 3D in Python](camera-project-unproject.md)
  — the projective half of camera-coordinate scripting; uses
  the same `Calibration.unproject` primitive on different
  pixel inputs.
- [Converting `camera.transform` to ENU](camera-poses-to-enu.md)
  — the full recipe for east-north-up local frame conversions.
- [YPR rotation conventions: `ypr2mat` vs `camera.reference.rotation`](ypr-rotation-conventions.md)
  — for converting between rotation-matrix and yaw-pitch-roll.
- [`chunk.transform.matrix` is local→world; `camera.transform` is local](../crs/chunk-frame-vs-camera-frame.md)
  — the conceptual model for the transforms used here.
- [Camera reference error: per-camera location and orientation in Python](../repeatability-qa/camera-reference-error-python.md)
  — the orientation-error recipe uses the same `T.rotation()` pattern.

## References

- *Metashape Python API Reference* (2.3.1):
  `Camera.transform`, `Camera.center`, `Camera.sensor`,
  `Sensor.calibration`, `Sensor.width`, `Sensor.height`,
  `Calibration.unproject`, `Matrix.rotation`, `Matrix.mulp`,
  `Vector.normalized`, `Vector.normalize`,
  `CoordinateSystem.localframe`.
- Forum thread, [*Camera orientation*, 2019](https://www.agisoft.com/forum/index.php?topic=11506.msg51385#msg51385)
  — the canonical Q&A; introduces the `unproject(image_centre)
  → mulp → minus camera.center` pattern.

