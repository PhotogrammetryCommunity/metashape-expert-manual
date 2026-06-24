---
title: "`Model.renderDepth`: synthetic depth rendering from arbitrary viewpoints"
status: unverified
applies_to: Metashape Pro 2.x — and PhotoScan 1.x via the same `Model.renderDepth` API
edition: Pro
last_reviewed: 2026-05-29
diataxis: how-to
confidence: high
---

# `Model.renderDepth`: synthetic depth rendering from arbitrary viewpoints

> **Confidence:** *high.* The API is forum-attested with
> permalink (Agisoft support, 2016) and introspection-confirmed
> on Metashape 2.2: `Model.renderDepth(transform, calibration,
> cull_faces=True, add_alpha=True)` returns a `Metashape.Image`
> with float32 depth values.

## Problem

You have a built mesh in your chunk and you want a depth map for
a viewpoint that is **not one of the chunk's cameras** — perhaps
a synthetic camera position for orthorectification, a novel-view
synthesis for ML training data, or an occlusion-visibility check
from an arbitrary location. The GUI's *File → Export → Export
Depth* command operates on the existing chunk cameras only.

The Python API exposes a more flexible primitive:
`chunk.model.renderDepth(transform, calibration)`. It takes any
4×4 transform matrix and any `Calibration` object and returns a
synthetic depth map of the mesh as seen from that pose.

## API

```
Model.renderDepth(transform, calibration,
                  cull_faces=True, add_alpha=True) → Metashape.Image
```

| Parameter | Type | Description |
|-----------|------|-------------|
| `transform` | `Metashape.Matrix` | 4×4 camera-to-chunk transform (a camera's `transform` property is suitable, or any synthetic 4×4) |
| `calibration` | `Metashape.Calibration` | Sensor intrinsics defining the projection (focal length, principal point, distortion, image dimensions) |
| `cull_faces` | bool | If True (default), back-facing triangles are skipped — same convention as the GUI depth export |
| `add_alpha` | bool | If True, the returned image has an alpha channel marking valid (mesh-hit) vs invalid (background) pixels |

Returns a `Metashape.Image` with `float32` pixel values
representing depth in the chunk-local coordinate frame.

## Recipe — depth from an existing camera's pose

The simplest case: render depth as Metashape's GUI would, but
programmatically:

> **Demo verified:** ✗ — pending Tier 3 reproduction on a real Metashape install.

```python
import Metashape

chunk = Metashape.app.document.chunk
camera = chunk.cameras[0]

if not chunk.model:
    raise RuntimeError("Build the mesh first via Workflow → Build Mesh")

# Render depth from this camera's pose and intrinsics
depth_image = chunk.model.renderDepth(
    camera.transform,
    camera.sensor.calibration,
)

print(f"Depth image: {depth_image.width} × {depth_image.height} "
      f"px, channels={depth_image.cn}, dtype={depth_image.data_type}")
```

The output `depth_image` has:

- `width × height` matching the camera's image dimensions
- One depth channel + (optionally) one alpha channel
- `data_type == "F32"` (32-bit float)

## Recipe — synthetic camera pose

For novel-view synthesis or visibility analysis, construct the
transform from scratch:

> **Demo verified:** ✗ — pending Tier 3 reproduction on a real Metashape install.

```python
import math
import Metashape

chunk = Metashape.app.document.chunk

# Synthetic pose: position above the chunk centre, looking down
centre = chunk.region.center  # in chunk-local coords
height_above = 50.0  # metres along chunk-local Z

# Translation: camera position
position = centre + Metashape.Vector([0, 0, height_above])

# Rotation: look down (camera Z-axis points DOWN in chunk frame)
# Metashape camera convention: Z forward (out of the lens), Y down.
# To look at chunk-Z-down, rotate 180° around X:
rotation = Metashape.Matrix.Rotation(
    Metashape.Matrix([
        [1,  0,  0],
        [0, -1,  0],
        [0,  0, -1],
    ])
)
synthetic_transform = (
    Metashape.Matrix.Translation(position) * rotation
)

# Borrow intrinsics from an existing camera (or construct manually)
calib = chunk.cameras[0].sensor.calibration

depth = chunk.model.renderDepth(
    synthetic_transform,
    calib,
)
```

The resulting `depth` is the depth map as seen from a nadir
camera 50 m above the chunk centre, with the same intrinsics as
camera 0.

## Recipe — convert float depth to 8-bit grayscale PNG

`renderDepth` returns float32 depth values in chunk-local units
(metres for georeferenced chunks). To save as an 8-bit grayscale
PNG, normalise:

> "renderDepth() is generating the depth in floating point
> format, so to get grayscale values in 0 - 255 range it would
> be necessary to transform the data 'manually' finding minimal
> and maximal floating point values and then scaling the pixel
> values accordingly."
> — Agisoft support, 2016-11-04, PhotoScan 1.2
> ([permalink](https://www.agisoft.com/forum/index.php?topic=6074.msg29487#msg29487))

> **Demo verified:** ✗ — pending Tier 3 reproduction on a real Metashape install.

```python
import numpy as np
import Metashape

chunk = Metashape.app.document.chunk
camera = chunk.cameras[0]
depth = chunk.model.renderDepth(camera.transform, camera.sensor.calibration)

# Pull the pixel buffer as numpy
arr = np.frombuffer(depth.tostring(), dtype=np.float32)
arr = arr.reshape(depth.height, depth.width, depth.cn)
# If add_alpha=True, the second channel is the alpha mask
if depth.cn == 2:
    depth_arr = arr[..., 0]
    alpha    = arr[..., 1]
    valid    = alpha > 0
else:
    depth_arr = arr[..., 0]
    valid    = np.isfinite(depth_arr) & (depth_arr > 0)

# Normalise valid range to 0..255
scaled = np.zeros(depth_arr.shape, dtype=np.uint8)
if valid.any():
    lo = depth_arr[valid].min()
    hi = depth_arr[valid].max()
    if hi > lo:
        scaled[valid] = ((depth_arr[valid] - lo) / (hi - lo) * 255).astype(np.uint8)

# Save with PIL
from PIL import Image as PILImage
PILImage.fromarray(scaled, mode="L").save("/tmp/depth.png")
```

For lossless float storage, save as TIFF instead:

> **Demo verified:** ✗ — pending Tier 3 reproduction on a real Metashape install.

```python
PILImage.fromarray(depth_arr, mode="F").save("/tmp/depth.tif")
```

## Use cases

- **Pre-built depth-map export from arbitrary poses** without
  re-running *Build Depth Maps* — the `renderDepth` path is much
  faster because it only renders the existing mesh.
- **Visibility computation.** Render depth at a candidate
  viewpoint, then for each chunk point of interest, compare its
  expected depth (computed from the geometry) against the
  rendered depth at the same pixel — points whose expected
  depth exceeds the rendered depth are occluded.
- **Synthetic stereo-pair generation** for computer-vision
  experiments. Construct two transforms separated by a fixed
  baseline; render depth from both; the depth maps + camera
  matrices form a perfect ground-truth stereo pair.
- **Rapid orthorectification.** Render depth from a synthetic
  nadir camera at fixed altitude; the depth map is the
  orthorectification height field for that AOI.

## Caveats

- **Requires a built mesh.** `chunk.model` must be non-`None`
  — call *Workflow → Build Mesh* (or
  `chunk.buildModel(...)`) first. If you only have a dense
  point cloud, `renderDepth` is not available; for point-cloud
  depth rendering, see the existing
  *Build Depth Maps* operation.
- **Returns float32 in chunk-local units.** For georeferenced
  chunks, the unit is the chunk CRS unit (typically metres).
  For un-georeferenced chunks, the unit is whatever
  `chunk.transform.scale` was set to — verify before assuming
  metric values.
- **`cull_faces=True` skips back-facing triangles.** For meshes
  with closed surfaces, this is correct (you don't want to see
  the back of a sphere). For open surfaces (a single
  ground-only mesh from aerial), back-face culling can cause
  near-edge pixels to be incorrectly invalid; pass
  `cull_faces=False` if needed.
- **`add_alpha=True` adds a second channel.** When True, the
  returned image has 2 channels (depth + alpha); when False,
  only the depth channel is returned. Background pixels (no
  mesh hit) have NaN or 0 depth and are flagged invalid by
  the alpha channel. Always check `depth.cn` to know which case
  you have.
- **The transform matrix is camera-to-chunk-local**, NOT
  camera-to-world. If you want a world-frame pose, multiply by
  `chunk.transform.matrix.inv()` first:

  ```python
  world_pose = ...  # 4x4 in world coords
  local_pose = chunk.transform.matrix.inv() * world_pose
  depth = chunk.model.renderDepth(local_pose, calib)
  ```

## See also

- [Photoset projection rendering: `Camera.image_keypoints` and
  `chunk.model.pickPoint`](../../topics/scripting/undocumented-tweaks-reference.md)
  — companion API surfaces for mesh-aware computation in Python.
- [Mesh and point-cloud editing recipes](mesh-pointcloud-editing-recipes.md)
  — broader collection of mesh-Python recipes (cropping, splitting,
  diff, etc).
- [Diagnosing CUDA / OpenCL errors during processing](../performance/diagnosing-cuda-opencl-errors.md)
  — `renderDepth` is a CPU operation and is unaffected by GPU
  errors that block *Build Depth Maps*.

## References

- *Metashape Python API Reference* (2.3.1):
  `Model.renderDepth`, `Image.tostring`, `Image.cn`,
  `Image.data_type`, `Calibration`, `Matrix.Rotation`,
  `Matrix.Translation`.
- Forum thread, [*model.renderDepth(transform, calibration)*, 2016](https://www.agisoft.com/forum/index.php?topic=6074.msg30401#msg30401)
  — the canonical Q&A; introduces the float32 output behaviour
  (msg 30459).

