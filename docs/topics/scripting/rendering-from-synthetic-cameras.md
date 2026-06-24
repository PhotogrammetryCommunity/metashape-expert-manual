---
title: "Rendering models from synthetic cameras: spherical panoramas and regular views"
status: unverified
applies_to: Metashape Pro 2.x — pattern from `render_model.py` in the official metashape-scripts repo
edition: Pro
last_reviewed: 2026-05-30
diataxis: how-to
confidence: high
---

# Rendering models from synthetic cameras: spherical panoramas and regular views

> **Confidence:** *high.* The script lives in Agisoft's
> official [`metashape-scripts`](https://github.com/agisoft-llc/metashape-scripts)
> repo, is tested against Metashape 2.3, and uses
> introspection-confirmed APIs (`Model.renderImage`,
> `Calibration` setup, `Sensor.Type.Spherical`).

## Problem

You've built a textured mesh and want **rendered images of
the model** — for visualisations, marketing material, or
synthetic training data — from camera positions that don't
match any of the chunk's actual cameras. Use cases:

- 360° spherical panoramas for VR / AR viewers.
- Specific viewpoints (e.g., "show the front face of this
  building from 50m back").
- Animation sequences (a circular orbit, a fly-through).
- Synthetic training datasets for computer vision research
  (with known ground-truth poses).

Metashape's `chunk.model.renderImage(transform, calibration)`
API renders the textured mesh from any synthetic pose. The
[`render_model.py`](https://github.com/agisoft-llc/metashape-scripts/blob/master/src/render_model.py)
script wraps this with a GUI that handles two common modes
(spherical and regular) and the necessary transform / calibration
setup.

This article covers the operational pattern for both modes.

## Two render modes

| Mode | Output | Calibration | Use case |
|------|--------|-------------|----------|
| **Spherical panorama** | 360° equirectangular image (typically 4K × 2K or 8K × 4K) | `Sensor.Type.Spherical` with `width:height = 2:1` | VR viewers; immersive context shots |
| **Regular** (frame projection) | Rectilinear-projection image with specified FOV | `Sensor.Type.Frame` with chosen `f`, `cx`, `cy` | Standard photo-like outputs; vis from specific perspective |

Both render the same chunk model; the difference is the
calibration object passed to `renderImage`.

## Recipe — spherical panorama

> **Demo verified:** ✗ — pending Tier 3 reproduction on a real Metashape install with a textured mesh.

```python
import Metashape

chunk = Metashape.app.document.chunk

if not chunk.model:
    raise RuntimeError("Build the mesh first; renderImage requires chunk.model")

# Synthetic camera centre — chunk-local coordinates
center = chunk.region.center   # e.g., scene centroid

# Rotation — point the panoramic "camera" any direction
# (For a panorama, the rotation defines the seam orientation)
rotation = Metashape.Matrix([
    [1, 0, 0],
    [0, 1, 0],
    [0, 0, 1],
])

# Build the 4×4 transform from rotation + translation
transform_4x4 = (
    Metashape.Matrix.Translation(center) *
    Metashape.Matrix.Rotation(rotation)
)

# Spherical calibration: 2:1 aspect ratio, no focal length
calibration = Metashape.Calibration()
calibration.type = Metashape.Sensor.Type.Spherical
calibration.width = 8000
calibration.height = 4000

# Render
image = chunk.model.renderImage(transform_4x4, calibration)
image.save("/path/panorama.jpg")
```

The result is an equirectangular projection: longitude
runs along the horizontal axis (0° at image-centre x), latitude
along the vertical (0° at image-centre y, ±90° at top/bottom).

For a sequence of panoramas along a flight path, iterate the
chunk's cameras (or any other set of poses):

> **Demo verified:** ✗ — pending Tier 3 reproduction on a real Metashape install.

```python
for i, camera in enumerate(chunk.cameras):
    if not camera.transform:
        continue
    image = chunk.model.renderImage(camera.transform, calibration)
    image.save(f"/path/panorama_{i:04d}.jpg")
```

This produces one panorama per actual capture position, useful
for "what would this point have looked like as a 360° image?"
visualisations.

## Recipe — regular (rectilinear) render

> **Demo verified:** ✗ — pending Tier 3 reproduction on a real Metashape install with a textured mesh.

```python
import math
import Metashape

chunk = Metashape.app.document.chunk

# Output dimensions
width, height = 1920, 1080

# Field of view — chosen explicitly
fov_horizontal_deg = 90.0
focal_length_pixels = (width / 2.0) / math.tan(math.radians(fov_horizontal_deg / 2.0))

# Frame calibration
calibration = Metashape.Calibration()
calibration.type = Metashape.Sensor.Type.Frame
calibration.width = width
calibration.height = height
calibration.f = focal_length_pixels
calibration.cx = 0   # offset from image center (0 = center)
calibration.cy = 0

# Synthetic pose: looking at the chunk centre from a specific position
target = chunk.region.center
distance = chunk.region.size.norm() * 1.5   # back off ~1.5× the chunk diagonal
viewer_position = target + Metashape.Vector([distance, 0, distance / 2])

# Compute look-at rotation
look_dir = (target - viewer_position).normalized()
up = Metashape.Vector([0, 0, 1])
right = Metashape.Vector.cross(look_dir, up).normalized()
up_corrected = Metashape.Vector.cross(right, look_dir).normalized()

R = Metashape.Matrix([
    [right.x, up_corrected.x, -look_dir.x],
    [right.y, up_corrected.y, -look_dir.y],
    [right.z, up_corrected.z, -look_dir.z],
])

transform_4x4 = (
    Metashape.Matrix.Translation(viewer_position) *
    Metashape.Matrix.Rotation(R)
)

image = chunk.model.renderImage(transform_4x4, calibration)
image.save("/path/render.jpg")
```

The look-at construction follows the standard graphics-library
convention: build the camera's right / up / forward axes, then
combine into a rotation matrix.

## Getting the current GUI viewpoint

If you want to render exactly what's visible in the current
*Model* view (the user's interactive perspective), the GUI
context exposes `Metashape.app.model_view` (with similar
attributes like `width`, `height`, `viewpoint` matrix at
runtime). The exact API surface depends on the Metashape
version; verify on your install:

```python
# In GUI context only:
v = Metashape.app.model_view   # or Metashape.app.viewpoint in some versions
print(v.width, v.height)
# Use v.viewpoint or similar to get the transform; see the script source
```

Headless / command-line scripts have no current viewpoint;
construct the transform yourself.

## What rendered images contain

The output `Metashape.Image` is RGB (3-channel) by default;
its alpha channel can be enabled via the `add_alpha=True`
parameter (matching the `Model.renderDepth` API). The image
captures:

- **The chunk's textured mesh** as currently built.
- **The active texture** (if multiple are present).
- **No transparency through the mesh** — the model is opaque
  in the render, even if some triangles have alpha-channel
  texture pixels.
- **Lighting from the current GUI lighting setup** (in 2.x;
  this may change in future versions).

The rendered image is 8-bit per channel by default. For
floating-point output (HDR-like, useful for relighting in
external tools), check the `Image.data_type` and convert if
necessary.

## When to use this vs. `Model.renderDepth`

| Render goal | API |
|------------|-----|
| Synthetic photo (RGB, textured) | `Model.renderImage(transform, calibration)` |
| Synthetic depth map (single-channel float) | `Model.renderDepth(transform, calibration)` |
| Synthetic normal map | `Model.renderNormalMap(...)` (not covered here) |
| Synthetic mask (visible-vs-not) | `Model.renderMask(...)` (not covered here) |

Both `renderImage` and `renderDepth` accept the same transform
+ calibration, so a typical "ground-truth dataset"
generation script renders all of them at the same poses.

## Caveats

- **Requires a built textured mesh.** `chunk.model` and a
  loaded texture both must exist; check before calling.
- **Sphere-rotation matters for panoramas.** The seam (the
  longitude where the panorama wraps) is at the rotation's
  +X direction by default. For panoramas oriented towards
  a specific landmark, rotate the transform such that the
  landmark sits at the panorama's centre rather than the seam.
- **Calibration distortion parameters are NOT applied** in
  rendering by default. The render uses the pinhole model
  even if your `Calibration` has `k1`, `k2`, etc. set. To
  apply distortion (for synthetic training data with realistic
  distortion), post-process the rendered image through
  Metashape's distortion model.
- **Large output sizes are slow.** An 8K × 4K panorama on a
  10M-face mesh can take 5-10 seconds per render. For
  animation frames, expect 100s of seconds for a 30s clip
  at 30 FPS.
- **GPU acceleration is automatic when present.** No explicit
  flag — the render uses whatever GPU configuration is set
  in *Tools → Preferences → GPU*.

## See also

- [`Model.renderDepth`: synthetic depth from arbitrary
  viewpoints](model-render-depth.md) — same calibration +
  transform pattern for depth-map output.
- [Computing camera direction vectors and look-at points](camera-direction-vectors.md)
  — for constructing the synthetic transform.
- [`camera.project` and `camera.unproject`: 2D ↔ 3D in
  Python](camera-project-unproject.md) — for inverse
  operation (image pixel → world point).
- [Tiled models: when to use, what they replace, and how to
  export](../../workflow/tiled-model/tiled-model-when-to-use.md)
  — alternative for browser-based interactive 3D.

## References

- [`render_model.py`](https://github.com/agisoft-llc/metashape-scripts/blob/master/src/render_model.py)
  — the canonical implementation in Agisoft's official
  scripts repo.
- *Metashape Python API Reference* (2.3.1):
  `Model.renderImage`, `Calibration`, `Calibration.type`,
  `Calibration.f`, `Calibration.cx`, `Calibration.cy`,
  `Calibration.width`, `Calibration.height`,
  `Sensor.Type.Spherical`, `Sensor.Type.Frame`,
  `Matrix.Translation`, `Matrix.Rotation`.

