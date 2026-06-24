---
title: Exporting depth maps from Python (32-bit, scaled)
status: unverified
applies_to: Metashape Pro 2.0+. The API surface used here (`chunk.depth_maps[camera]`, `.image()`, `chunk.transform.scale`, `Image.save()`) is unchanged across the 1.6 → 2.x window.
edition: Pro
last_reviewed: 2026-05-22
diataxis: how-to
confidence: medium
---

# Exporting depth maps from Python (32-bit, scaled)
> **Confidence:** *medium.* The `chunk.depth_maps` API surface and the 32-bit-float depth format are introspection-confirmed; the scaling-to-real-units recipe is forum-attested with permalink.
## Problem

You have run *Build Depth Maps* in Metashape and want the *raw,
float32* depth-map images on disk — not the 8-bit grayscale that
the GUI's *File → Export → Export Depth* command produces from the
mesh. You want one file per camera, scaled to real-world units,
and you want this from Python so it can run in a batch.

## Context

Two distinct depth-map outputs exist in Metashape:

- **GUI's *Export Depth*.** Renders a depth image *from the mesh
  model*, in grayscale 8-bit. Suitable for inspection, lossy for
  any quantitative use. Requires a mesh to exist.
- **Per-camera depth maps from the alignment / depth-map step.**
  Stored in the project's `.files/<chunk>/<frame>/depth_maps/`
  directory as float32 EXR images, but **unscaled** — they are in
  the chunk's internal frame, not metres. Accessible via
  `chunk.depth_maps[camera].image()` from Python.

This article exports the second kind, applying
`chunk.transform.scale` to convert internal-frame depths to
real-world units.

## Solution

### The minimal export script

```python
import Metashape

chunk = Metashape.app.document.chunk

if chunk is None:
    raise SystemExit("No active chunk.")

scale = chunk.transform.scale or 1.0     # 1.0 for unreferenced chunks

output_dir = "/path/to/depth_export"
import os
os.makedirs(output_dir, exist_ok=True)

count = 0
for camera in chunk.cameras:
    if camera.transform is None:
        continue                         # not aligned
    if camera.type != Metashape.Camera.Type.Regular:
        continue                         # skip auxiliary frames
    if camera not in chunk.depth_maps:
        continue                         # no depth map computed

    depth = chunk.depth_maps[camera].image() * scale     # float32, scaled
    depth.save(os.path.join(output_dir, f"{camera.label}.tif"))
    count += 1

print(f"Exported {count} depth map(s) to {output_dir}")
```

The result: one `<camera_label>.tif` per camera, float32 1-band,
where each pixel is the distance from the camera to the surface
in the chunk's real-world units (metres, typically).

### Optional: 8-bit / 16-bit grayscale variants

For visualisation rather than computation, normalise to a 0–1
range first and convert to U8 / U16:

```python
img = chunk.depth_maps[camera].image() * scale     # raw float32, scaled

# grayscale 8-bit (255 = farthest, 0 = nearest, similar to GUI export)
import numpy as np
arr = np.frombuffer(img.tostring(), dtype=np.float32)
lo, hi = arr.min(), arr.max()
norm = (arr - lo) / (hi - lo) if hi > lo else arr * 0
u8 = (norm * 255).astype(np.uint8).reshape(img.height, img.width)
# … save u8 with PIL or imageio …
```

The forum reference (insight-0016) provides a full PySide2 dialog
that wraps three format options (1-band F32, Grayscale 8-bit,
Grayscale 16-bit) — useful as a starting point if you want a
reusable GUI tool.

## Caveats and gotchas

- **`chunk.depth_maps[camera]`** raises `KeyError` when the camera
  has no depth map. Always test with `camera in chunk.depth_maps`
  first. *Build Depth Maps* skips cameras with insufficient
  overlap; in a typical UAV project, a handful of cameras at the
  edges of the flight plan will have no depth map.
- **`chunk.transform.scale` is `None` for unreferenced chunks.**
  Use `or 1.0` to fall back to a unit scale.
- **The `.files/<chunk>/<frame>/depth_maps/` EXR files are
  *unscaled*.** If you bypass Python and read them directly,
  remember to multiply by `chunk.transform.scale`. The
  `chunk.depth_maps[camera].image() * scale` form does the
  multiplication for you.
- **`Camera.Type.Regular`** filters out keyframes / auxiliary
  frames. For specialised pipelines (laser scan trajectories etc.)
  you may want to handle `Camera.Type.Keyframe` differently.
- **The output `.tif` files require a viewer that handles 32-bit
  float.** ImageJ, GDAL, OpenCV's `IMREAD_UNCHANGED`,
  and the `tifffile` Python module all work; the macOS Preview
  application and most casual viewers will display a black or
  garbled image because they expect 8-bit.

## Runnable demonstration on the Aerial-with-GCPs sample dataset

The script below exports float32 depth maps from an aligned chunk
that has had *Build Depth Maps* run on it. Use the
[Aerial-with-GCPs](../../reference/sample-data.md#aerial-images-with-gcps)
sample.

> **Demo verified:** ✗ — pending Tier 3 reproduction on Metashape
> Pro 2.2 / 2.3 with the *Aerial-with-GCPs* sample dataset. The
> underlying APIs are introspection-verified but the demo as
> written has not been run end-to-end. Required before the manual
> ships.

```python
"""Export float32 depth maps from the Aerial-with-GCPs sample dataset.

Workflow: align the dataset in the GUI, run *Workflow → Build
Depth Maps* (any quality), then run this script in *Tools → Run
Script…*. The script prints how many depth maps were exported and
where; open one of the resulting .tif files in ImageJ or
`tifffile.imread` to confirm float32 content.
"""

import os
import Metashape

OUTPUT_DIR = "/path/to/depth_export/"   # ← adjust

chunk = Metashape.app.document.chunk
if chunk is None:
    raise SystemExit("Open the Aerial-with-GCPs chunk first.")
if not chunk.depth_maps:
    raise SystemExit("No depth maps in this chunk — run *Build Depth Maps* first.")

os.makedirs(OUTPUT_DIR, exist_ok=True)
scale = chunk.transform.scale or 1.0

count = 0
for camera in chunk.cameras:
    if camera.transform is None:
        continue
    if camera.type != Metashape.Camera.Type.Regular:
        continue
    if camera not in chunk.depth_maps:
        continue
    depth = chunk.depth_maps[camera].image() * scale
    depth.save(os.path.join(OUTPUT_DIR, f"{camera.label}.tif"))
    count += 1

print(f"exported {count} depth map(s) to {OUTPUT_DIR}")
print(f"chunk.transform.scale: {scale}  (1.0 = unreferenced; otherwise metres-per-unit)")
```

Expected: one `<camera_label>.tif` per camera that has a depth map.
Inspect any of them with `tifffile.imread()` (or ImageJ) and
confirm the values are float32 in metres — for the Aerial-with-GCPs
project that is georeferenced in EPSG:4978 / a UTM zone, the depth
range typically falls between 30 m and 200 m above ground level.

If the file viewer reports 8-bit content, you ran the wrong tool —
double-check that the script (not *File → Export → Export Depth*)
produced the file.

## References

- **Official manual:** *Metashape Pro User Manual*, ch. 3
  "General workflow" → "Building point cloud" → *Build Depth
  Maps* — describes the depth-map step but not the Python export
  pattern.
- **Python Reference:** `Metashape.Chunk.depth_maps` (the
  `DepthMaps` collection indexed by camera),
  `Metashape.DepthMap.image()` (returns `Metashape.Image`),
  `Metashape.Image.save(path)`, `Metashape.Chunk.transform.scale`,
  `Metashape.Camera.Type.Regular` —
  *Metashape Python API Reference*, version 2.3.1.
- **Forum:** [Pasumansky, 2020-09-11, Metashape 1.6](https://www.agisoft.com/forum/index.php?topic=12549.msg55731#msg55731)
  — full PySide2 dialog with the three-format export.
- **Suggested sample dataset:** [Aerial images (with GCPs)](../../reference/sample-data.md#aerial-images-with-gcps).
  Has 444 cameras and a real CRS so `chunk.transform.scale`
  produces metres.
