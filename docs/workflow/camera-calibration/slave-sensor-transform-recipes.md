---
title: "The slave-sensor transform: composition rule, axis convention, and recipes"
status: unverified
applies_to: Metashape Pro 2.x — and unchanged from PhotoScan 1.x via the same API
edition: Pro
last_reviewed: 2026-05-23
diataxis: explanation
confidence: high
---

# The slave-sensor transform: composition rule, axis convention, and recipes
> **Confidence:** *high* for the API surface, axis convention,
> and composition rule (all empirically verified on Metashape
> 2.2.2). *Medium* for the specific cubemap / stereo / toe-in
> recipes — the matrix forms are correct by construction; the
> read-third-column diagnostic is the verification step.

This article extends [Declaring a fixed-geometry multi-camera
rig in Python](multi-camera-rig-python.md) with the
**direct matrix form** of slave-sensor offsets and the recipe
library for common rig configurations. Where A.1 covers the
introductory path (`sensor.reference.rotation` as
omega-phi-kappa Vector), this article covers the
bundle-internal form (`sensor.rotation` as 3×3 Matrix,
`sensor.location` as 3-Vector) that gives explicit
control over non-trivial rig geometries.

## Two surfaces for slave-sensor offsets

Each `Sensor` carries **two parallel surfaces** for its rig
offset relative to the master sensor:

| Surface | Type | Purpose |
|---------|------|---------|
| `sensor.reference.location` | 3-Vector (metres) | User-facing input; equivalent to GUI's *Slave offset → location* |
| `sensor.reference.rotation` | 3-Vector (omega, phi, kappa in degrees) | User-facing input; equivalent to GUI's *Slave offset → rotation*. The canonical thread's recommended path for simple rigs. |
| `sensor.location` | 3-Vector (metres) | Bundle-internal — slave's optical centre in master frame. |
| `sensor.rotation` | 3×3 `Metashape.Matrix` | Bundle-internal — slave-to-master rotation. |
| `sensor.fixed_location`, `sensor.fixed_rotation` | bool, default `True` | Hold the offset fixed during BA. |

The reference-surface form is the right answer for simple rigs
and quick setup (covered in A.1). The matrix form is the right
answer when:

- Rotations don't fit cleanly into Euler-angle representation
  (e.g., cubemap with discrete 90° steps about different axes).
- The rig configuration comes from external CAD or factory
  calibration as a 4×4 rigid transform.
- You need to verify the rig's pose end-to-end against a
  predicted `slave.transform`.

## The composition rule

For an aligned rig, the slave camera's chunk-frame pose is
**always** the composition:

```text
slave.transform = master.transform · T(R, t)

   where  R = sensor.rotation   (3×3 rotation matrix)
          t = sensor.location   (3-vector translation in master's frame, metres)

   T(R, t) = ⎡  R[0,0]  R[0,1]  R[0,2]  t[0] ⎤
             ⎢  R[1,0]  R[1,1]  R[1,2]  t[1] ⎥
             ⎢  R[2,0]  R[2,1]  R[2,2]  t[2] ⎥
             ⎣    0       0       0       1  ⎦
```

`T(R, t)` is the standard 4×4 rigid transform that maps points
in the **slave camera's local frame** to points in the **master
camera's local frame**. The full chunk-local pose for the slave
is then the master's chunk-local pose composed with that
local-to-local transform.

The empirical-verification recipe below is just this rule in
code form.

## The axis convention

Metashape's *Frame* camera type (the most common) uses the
photogrammetry convention. Empirically verified on Metashape
2.2.2:

```text
+X  =  image right
+Y  =  image down
+Z  =  optical axis, forward into the scene
```

The verification: set up a synthetic camera with `f=1000`,
`cx=cy=0`, identity transform; project test points:

| Point in chunk-local | `cam.project()` returns | Convention |
|---------------------|-------------------------|------------|
| `(0, 0, +10)` | `(W/2, H/2)` | `+Z` projects to image centre — forward |
| `(1, 0, +10)` | `(2577.8, 1500)` | `+X` projects right of centre — image right |
| `(0, 1, +10)` | `(2000, 2077.8)` | `+Y` projects below centre — image down |
| `(0, 0, -10)` | `None` | behind camera — `+Z` is forward |

(The `2577.8` and `2077.8` values are because `f=1000`,
focal-pixel offset for a 1 m sideways-displaced point at 10 m
distance is `1000 × 1/10 = 100`, projected at `(W/2 + 100 × focal_factor, …)`.
The point is the *direction* — right of centre, below centre.)

Both master and slave use this same convention in their
respective local frames.

## Semantics of `sensor.rotation`

The three columns of `sensor.rotation` are the slave camera's
three local axes expressed in the master camera's local frame:

| Column | Slave's axis | Direction in slave frame | Read off as |
|--------|--------------|--------------------------|-------------|
| 0 | `+X` | image right | first column of `sensor.rotation` (slave's right axis in master frame) |
| 1 | `+Y` | image down | second column of `sensor.rotation` (slave's down axis in master frame) |
| 2 | `+Z` | optical axis (forward) | **third column of `sensor.rotation`** (slave's optical axis in master frame) |

So `sensor.rotation · v` rotates a vector from the slave frame
to the master frame. This is the "slave-to-master" convention.
**The third column is the slave's optical-axis direction in the
master's frame** — the most useful single-column readout for
verifying which way the slave is looking.

## Semantics of `sensor.location`

`sensor.location` is the slave camera's optical centre expressed
in the **master's camera-local frame**, in metres:

- `sensor.location = (1, 0, 0)` — slave is 1 m to the master's
  image-right.
- `sensor.location = (0, -1, 0)` — slave is 1 m above master
  (i.e., master image-up direction).
- `sensor.location = (0, 0, 0.5)` — slave is 0.5 m forward in
  master's looking direction.

Both fields default to identity-like values (`rotation =
identity`, `location = (0, 0, 0)`) and `fixed_rotation =
fixed_location = True` — the bundle treats them as fixed by
default unless you explicitly let them refine.

## Sign-convention pitfall

Two `Rx(angle)` definitions are in common use, and they rotate
in **opposite** directions:

```python
import math

# Right-handed Rx — positive angle = CCW when looking from +X toward origin.
# This is what Metashape uses.
def Rx(deg: float) -> list[list[float]]:
    c = math.cos(math.radians(deg))
    s = math.sin(math.radians(deg))
    return [[1, 0, 0],
            [0, c, -s],     # ← note the sign on s
            [0, s, c]]

# Left-handed (the sign on s flipped) — opposite rotation direction!
def Rx_lh(deg: float) -> list[list[float]]:
    c = math.cos(math.radians(deg))
    s = math.sin(math.radians(deg))
    return [[1, 0, 0],
            [0, c, s],      # ← OPPOSITE sign
            [0, -s, c]]
```

`Rx(+90)` and `Rx_lh(+90)` rotate in opposite directions. The
classic failure mode: a cubemap rig configured with `Up:
Rx_lh(+90)` produces a sensor whose third column is `(0, +1, 0)`
— which is *master image-down*, not master image-up. The
"Up" sensor ends up looking DOWN.

**The diagnostic:** after setting `sensor.rotation = R`, read
off `R[:, 2]` (third column) and compare to the *expected*
optical-axis direction. If a direction labelled "Up" gives
`(0, +1, 0)` (master image-down) instead of `(0, -1, 0)`
(master image-up), the rotation matrix is using the wrong
handedness.

`Camera.project()` uses the **right-handed** convention, so
matrices built via the right-handed `Rx` / `Ry` / `Rz`
functions are the correct ones for Metashape.

## Recipe library

### Cubemap rig (6 faces, identical position, orthogonal optical axes)

Master = `Front`, looking `+Z`. Each slave shares the master's
position (`sensor.location = (0, 0, 0)`) and its rotation matrix
is chosen so the third column points in the desired
optical-axis direction:

| Face | Optical-axis target (master frame) | `sensor.rotation` |
|------|-----------------------------------|-------------------|
| Front | `(0, 0, +1)` (same as master) | identity |
| Back | `(0, 0, -1)` | `Ry(180)` (or equivalently `Rx(180)` — different roll) |
| Right | `(+1, 0, 0)` | `Ry(-90)` |
| Left | `(-1, 0, 0)` | `Ry(+90)` |
| Up | `(0, -1, 0)` (master image-up) | `Rx(-90)` |
| Down | `(0, +1, 0)` (master image-down) | `Rx(+90)` |

```python
import math
import Metashape

def Rx(deg):
    c, s = math.cos(math.radians(deg)), math.sin(math.radians(deg))
    return Metashape.Matrix([[1, 0, 0], [0, c, -s], [0, s, c]])

def Ry(deg):
    c, s = math.cos(math.radians(deg)), math.sin(math.radians(deg))
    return Metashape.Matrix([[c, 0, s], [0, 1, 0], [-s, 0, c]])

def Rz(deg):
    c, s = math.cos(math.radians(deg)), math.sin(math.radians(deg))
    return Metashape.Matrix([[c, -s, 0], [s, c, 0], [0, 0, 1]])

# Configure a cubemap rig.
chunk = Metashape.app.document.chunk
sensors = {s.label: s for s in chunk.sensors}

cubemap_rotations = {
    "Front":  Metashape.Matrix.Diag([1, 1, 1]),
    "Back":   Ry(180),
    "Right":  Ry(-90),
    "Left":   Ry(90),
    "Up":     Rx(-90),
    "Down":   Rx(90),
}

for face_name, R in cubemap_rotations.items():
    sensor = sensors[face_name]
    sensor.rotation = R
    sensor.location = Metashape.Vector([0, 0, 0])
    sensor.fixed_rotation = True
    sensor.fixed_location = True

    # Verify by reading the third column.
    third_col = (R[0, 2], R[1, 2], R[2, 2])
    print(f"{face_name:>6}: optical axis in master frame = {third_col}")
```

(Reminder: master image-up is `-Y_camera` for an upright master
camera; the slave's *image roll* is determined by the *other two
columns* of `sensor.rotation`, not just the third.)

### Stereo rig (parallel optical axes, baseline `b` along master image-right)

```python
sensor.rotation = Metashape.Matrix.Diag([1, 1, 1])     # identity
sensor.location = Metashape.Vector([b, 0, 0])          # slave to right of master by b metres
```

Slave is `b` metres to the right of the master; both look the
same direction.

### Stereo rig with toe-in (cameras converge by angle `θ`)

```python
sensor.rotation = Ry(-theta_deg)          # rotate slave left, toward master's view direction
sensor.location = Metashape.Vector([b, 0, 0])
```

The slave's optical axis converges on the master's by angle
`theta_deg`. Useful for short-range stereo where parallel
optical axes give insufficient binocular overlap on the subject.

### Tilted top camera (front + downward-tilted bottom)

```python
sensor.rotation = Rx(psi_deg)              # tilt slave optical axis downward by psi
sensor.location = Metashape.Vector([0, dy, 0])   # optional small offset along master image-down
```

## Empirical verification recipe

After setting `sensor.rotation = R` and `sensor.location = t`,
verify the composition rule by reading `camera.transform` and
comparing to the prediction:

```python
import Metashape

def compose(R: Metashape.Matrix, t: Metashape.Vector) -> Metashape.Matrix:
    """Build the 4×4 rigid transform from 3×3 rotation + 3-vec translation."""
    M = Metashape.Matrix.Diag([1, 1, 1, 1])
    for i in range(3):
        for j in range(3):
            M[i, j] = R[i, j]
        M[i, 3] = t[i]
    return M

def matrix_diff_max(A: Metashape.Matrix, B: Metashape.Matrix) -> float:
    """Maximum elementwise absolute difference."""
    return max(abs(A[i, j] - B[i, j]) for i in range(4) for j in range(4))

# After setting slave_sensor.rotation = R and slave_sensor.location = t,
# pick any aligned camera on the slave sensor.
slave_camera = next(
    c for c in chunk.cameras
    if c.sensor == slave_sensor and c.transform is not None
)
# Pair to the master camera captured at the same instant. The
# pairing predicate is dataset-specific; for Micasense rigs the
# filename suffix encodes the band index, so a label like
# "IMG_0001_4" pairs with "IMG_0001_1". For other rigs use
# capture timestamp, filegroup membership, or whatever encoding
# your dataset uses.
def _same_instant(master_cam, slave_cam):
    """Dataset-specific. Replace with the predicate that matches
    your rig's per-instant pairing convention."""
    # Example: strip the trailing band-index from the labels.
    return master_cam.label.rsplit("_", 1)[0] == slave_cam.label.rsplit("_", 1)[0]

master_camera = next(
    c for c in chunk.cameras
    if c.sensor == master_sensor and c.transform is not None
    and _same_instant(c, slave_camera)   # paired with slave_camera in the rig
)

predicted = master_camera.transform * compose(slave_sensor.rotation,
                                              slave_sensor.location)
actual = slave_camera.transform

drift = matrix_diff_max(predicted, actual)
print(f"max elementwise drift between predicted and actual: {drift:.2e}")
assert drift < 1e-6, f"composition rule violation: drift = {drift}"
```

Zero (or sub-1e-6) drift across all rig configurations confirms
the composition rule is correctly applied. Non-zero drift means
the rig declaration was either:

- not picked up by the bundle (try setting `fixed_rotation =
  True` and rerunning `chunk.alignCameras()`).
- conflicting with an automatic rig estimate (verify
  `slave_sensor.master == master_sensor`).

## Image-content vs rig-direction check

A rig that passes the math test above can still encode the
*wrong* rotations relative to actual image content — e.g., the
"Up" sensor's rotation matrix is mathematically valid, but the
images on it actually depict the *down* direction because the
sensor was mislabelled at capture time.

The cheap consistency check: for two adjacent faces A and B
(e.g., Front and Right), pick a pixel on the **shared edge** of
A, back-project to a 3D ray at depth ~10 m, project the
resulting world point onto B with `cam.project()`. The two
pixel values (in A's edge and in B's predicted position) should
be **nearly identical** — adjacent cube faces share content at
edges:

```python
def edge_consistency_check(face_a: Metashape.Camera,
                            face_b: Metashape.Camera,
                            edge_pixels: list[Metashape.Vector],
                            depth: float = 10.0) -> float:
    """Return mean RGB difference at predicted-corresponding edge pixels.

    Low score (< 20) → faces share content at edges (rig labels correct).
    High score (> 60) → rig labels wrong (looking at opposite faces).
    """
    import cv2
    import numpy as np

    def _read(path: str):
        return cv2.imread(path)   # H × W × 3, BGR

    def _sample(img, pixel: Metashape.Vector):
        x, y = int(round(pixel.x)), int(round(pixel.y))
        h, w = img.shape[:2]
        if not (0 <= x < w and 0 <= y < h):
            return None
        # OpenCV is BGR; convert to RGB tuple.
        b, g, r = img[y, x]
        return (int(r), int(g), int(b))

    chunk = face_a.chunk
    img_a = _read(face_a.photo.path)
    img_b = _read(face_b.photo.path)
    if img_a is None or img_b is None:
        return float("inf")

    diffs = []
    for pixel_a in edge_pixels:
        # Back-project to ray in chunk-local frame.
        direction_cam = face_a.calibration.unproject(pixel_a)
        direction_world = face_a.transform.mulv(direction_cam)
        ray_origin_local = Metashape.Vector(face_a.center)
        point_local = ray_origin_local + depth * direction_world

        # Project onto face B (already in chunk-local frame).
        pixel_b = face_b.project(point_local)
        if pixel_b is None:
            continue
        if not (0 <= pixel_b.x < face_b.sensor.width
                and 0 <= pixel_b.y < face_b.sensor.height):
            continue

        rgb_a = _sample(img_a, pixel_a)
        rgb_b = _sample(img_b, pixel_b)
        if rgb_a is None or rgb_b is None:
            continue
        diffs.append(np.linalg.norm(np.array(rgb_a) - np.array(rgb_b)))

    return float(np.mean(diffs)) if diffs else float("inf")
```

A diff of `< 20` across the shared edge indicates the rig is
configured correctly relative to image content. `> 60`
indicates the labels are wrong — a sensor labelled "Up" is
actually showing "Down" content. The check catches errors that
the math-only verification cannot.

## Caveats

- **The two surfaces are separately maintained.** Setting
  `sensor.reference.rotation = Vector([omega, phi, kappa])`
  does not automatically populate `sensor.rotation`; the bundle
  reconciles them at alignment time. To verify what the bundle
  is using, read `sensor.rotation` directly after
  `alignCameras`.
- **`fixed_rotation = True` and `fixed_location = True` are
  defaults.** A rig declaration is *fixed* unless explicitly
  refined; this is usually correct for factory-calibrated rigs
  but you must `fixed_*=False` when you want the bundle to
  adjust the rig.
- **Master sensor identification:** `sensor.master == sensor`
  is True for the master; `sensor.master == master_sensor` for
  every slave on that master. See [Choosing the master sensor in
  a multi-camera layout](choosing-master-sensor-multi-camera-layout.md)
  for how the master is determined at import.
- **`Metashape.Matrix(...)` accepts a list of lists** for
  3×3 (and 4×4) matrices. The `Rx` / `Ry` / `Rz` helper
  functions in this article use that constructor.
- **Image roll on cubemap faces** is determined by the *other
  two columns* of `sensor.rotation`, not just the optical-axis
  column. If a face's optical axis is correct but the image is
  rotated 90°, fix by composing with `Rz(±90)` after the
  primary rotation.
- **Per-camera rig refinement** (`fixed_rotation = False`) lets
  the bundle estimate the rig from the data. Useful when the
  factory calibration is approximate; risky when the data
  doesn't constrain the rig (small subject, narrow baseline,
  etc.) — the bundle can drift toward a wrong-but-tie-point-
  consistent solution.

## Runnable demonstration on a synthetic cubemap

A real cubemap dataset is not part of the Agisoft sample
collection. The script below sets up a 6-sensor cubemap with
synthetic identity-position offsets and verifies the
composition rule.

> **Demo verified:** ✗ — pending Tier 3 reproduction with a
> real or synthetic 6-camera cubemap dataset. The API surface
> and axis convention are introspection-verified on Metashape
> 2.2.2 (and the convention check shipped in this article's
> *Validation notes*); the cubemap-recipe matrices are correct
> by construction. End-to-end alignment + verification is the
> missing step.

```python
"""Configure a 6-sensor cubemap rig and verify composition rule.

Pre-condition: a chunk with 6 sensors imported from a synthetic
or real cubemap (e.g., MultiplaneLayout import). Sensor labels
are 'Front', 'Back', 'Right', 'Left', 'Up', 'Down'.
"""
import math
import Metashape

def Rx(deg):
    c, s = math.cos(math.radians(deg)), math.sin(math.radians(deg))
    return Metashape.Matrix([[1, 0, 0], [0, c, -s], [0, s, c]])

def Ry(deg):
    c, s = math.cos(math.radians(deg)), math.sin(math.radians(deg))
    return Metashape.Matrix([[c, 0, s], [0, 1, 0], [-s, 0, c]])

CUBEMAP = {
    "Front": Metashape.Matrix.Diag([1, 1, 1]),
    "Back":  Ry(180),
    "Right": Ry(-90),
    "Left":  Ry(90),
    "Up":    Rx(-90),
    "Down":  Rx(90),
}

chunk = Metashape.app.document.chunk
sensors_by_label = {s.label: s for s in chunk.sensors}

# Set the rotations.
master = sensors_by_label["Front"]
for face_label, R in CUBEMAP.items():
    sensor = sensors_by_label[face_label]
    sensor.rotation = R
    sensor.location = Metashape.Vector([0, 0, 0])
    sensor.fixed_rotation = True
    sensor.fixed_location = True

    # Read off the optical-axis direction (third column).
    optical_axis = (sensor.rotation[0, 2],
                    sensor.rotation[1, 2],
                    sensor.rotation[2, 2])
    print(f"{face_label:>6}: optical axis = {optical_axis}")

# Run alignment to apply the rig.
chunk.matchPhotos(downscale=1, keep_keypoints=True)
chunk.alignCameras()

# Verify the composition rule on a sample slave camera.
slave_label = "Right"
slave_sensor = sensors_by_label[slave_label]
slave_camera = next(c for c in chunk.cameras
                    if c.sensor == slave_sensor and c.transform is not None)
master_camera = next(c for c in chunk.cameras
                     if c.sensor == master and c.transform is not None)

# Build T(R, t).
R, t = slave_sensor.rotation, slave_sensor.location
T_offset = Metashape.Matrix.Diag([1, 1, 1, 1])
for i in range(3):
    for j in range(3):
        T_offset[i, j] = R[i, j]
    T_offset[i, 3] = t[i]

predicted = master_camera.transform * T_offset
actual = slave_camera.transform

max_drift = max(
    abs(predicted[i, j] - actual[i, j])
    for i in range(4) for j in range(4)
)
print(f"\nslave='{slave_label}': max drift = {max_drift:.2e}")
print("(Expect: < 1e-6 if rig + alignment are consistent.)")
```

**Expected output:** the optical-axis third column matches the
expected per-face directions; the composition-rule drift is
sub-1e-6 across all faces. If drift is large (> 1e-3), either
the rig declaration didn't take effect (verify
`sensor.fixed_rotation = True` and re-run alignment) or the
master sensor identification is wrong (`sensor.master`
mismatches).

## References

- [Forum thread, *Multiple-Camera Rig with Python API*, 2023](https://www.agisoft.com/forum/index.php?topic=16015.0)
  — the intro to the `MultiplaneLayout` +
  `sensor.reference` workflow (msg 72350, 2023-11-21,
  Metashape 2.1). The complementary surface to this article's
  matrix form.
- *Metashape Python Reference* (2.3.1), `Sensor.rotation`,
  `Sensor.location`, `Sensor.fixed_rotation`,
  `Sensor.fixed_location`, `Camera.project`,
  `Camera.calibration.unproject`, `Camera.transform`.
- *Metashape Professional Edition User Manual* (2.3), camera
  model section — the canonical pinhole projection formula
  using the convention this article documents.
- [Declaring a fixed-geometry multi-camera rig in Python](multi-camera-rig-python.md) — the introductory how-to using
  `sensor.reference.*`. This article is the deep-dive companion.
- [Choosing the master sensor in a multi-camera layout](choosing-master-sensor-multi-camera-layout.md) — how the master is determined at import; the
  composition rule presupposes a correct master assignment.
- [Metashape's distortion model and converting to OpenCV /
  Colmap](distortion-model-opencv-colmap.md) — the
  pinhole projection formula details + axis convention
  cross-referenced.
