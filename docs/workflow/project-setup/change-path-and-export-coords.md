---
title: "Change Path: swapping image format / resolution after alignment"
status: unverified
applies_to: Metashape Pro 2.x — and PhotoScan 1.x via the same `camera.photo.path` field
edition: Pro
last_reviewed: 2026-05-28
diataxis: how-to
confidence: high
---

# Change Path: swapping image format / resolution after alignment

> **Confidence:** *high.* Both findings (Change Path semantics
> and the GUI/Python CRS export difference) are directly attested
> by Agisoft support with permalinks. The format-swap script is
> introspection-confirmed against the `camera.photo.path` API.

## Problem 1 — The GUI's *Change Path* command does not change extensions

The GUI command *Tools → Cameras → Change Path* lets you redirect
a chunk's image references to a different folder when the source
images have moved. It does **not** rename the files or change
their extensions. Pointing it at a folder of `.tiff` files when
the chunk references `.jpg` images silently keeps the original
`.jpg` extension, so Metashape will fail to find the new files.

> "According to its' name, the feature only changes the path to
> the images (for example, if the image set has been moved to
> another folder) and is not able to change the extension of the
> images used for the project."
> — Alexey Pasumansky, 2014-03-17, PhotoScan 1.0
> ([permalink](https://www.agisoft.com/forum/index.php?topic=2150.msg11404#msg11404))

### Use case: low-res align, then high-res process

A common workflow pattern:

1. Resize a copy of your image set to half resolution (faster
   matching).
2. Run *Align Photos* on the half-res JPGs.
3. After alignment converges, swap the chunk's image references
   to the full-resolution TIFFs.
4. Re-build dense product (depth maps, mesh, texture) at full
   resolution.

Step 3 cannot be done via the GUI's *Change Path*; it requires a
Python script.

### Solution

> **Demo verified:** ✗ — pending Tier 3 reproduction on a real Metashape install.

```python
import Metashape

chunk = Metashape.app.document.chunk

# Replace .jpg with .tiff in every camera's image path
for camera in chunk.cameras:
    camera.photo.path = camera.photo.path.replace(".jpg", ".tiff")

# Verify
for camera in chunk.cameras[:5]:
    print(camera.photo.path)
```

For more complex renames (e.g., a different naming scheme between
the two image sets), use a regex:

> **Demo verified:** ✗ — pending Tier 3 reproduction on a real Metashape install.

```python
import re

# Map "image_thumb_001.jpg" → "/full/res/image_001.tiff"
for camera in chunk.cameras:
    old = camera.photo.path
    new = re.sub(
        r"^.*image_thumb_(\d+)\.jpg$",
        r"/full/res/image_\1.tiff",
        old,
    )
    if new != old:
        camera.photo.path = new
```

### Caveats

- **The image dimensions must match.** Half-resolution JPGs are
  used during alignment; the chunk's intrinsics (focal length in
  pixels) are calibrated for that resolution. Swapping to
  full-resolution TIFFs invalidates the intrinsics.

  Two options:
  - **Force the new images to the same dimensions** as the
    aligned set (resize back down before the swap — defeats the
    purpose).
  - **Re-run `Optimize Cameras`** after the swap, with
    `fit_f=True, fit_cx=True, fit_cy=True` to recalibrate
    intrinsics for the new resolution. This works because the
    extrinsic camera positions are already approximately correct
    from the half-res alignment.

- **Path display lag in the GUI.** After the swap, the *Photos*
  pane may still show the old extension until the project is
  saved and reopened. Cosmetic only — actual processing uses
  the new path.

- **Multi-frame chunks need a different access path.**
  `camera.photo.path` works for single-frame chunks (most cases).
  For multi-frame chunks (timelapse, video import), iterate
  `camera.frames[i].photo.path` instead.

## Problem 2 — `chunk.exportPoints()` defaults to chunk-internal coords

A different but related GUI / Python mismatch: when exporting
tie-point or point-cloud coordinates, the **GUI defaults to the
chunk's CRS**, while **Python defaults to chunk-internal
coordinates**. Scripts that mirror GUI exports must pass `crs=`
explicitly.

> "From GUI you are exporting points in the geographic
> coordinates, while script export saves the coordinates in the
> internal coordinates."
> — Alexey Pasumansky, 2016-03-01, PhotoScan 1.2
> ([permalink](https://www.agisoft.com/forum/index.php?topic=5037.msg25059#msg25059))

### Solution

> **Demo verified:** ✗ — pending Tier 3 reproduction on a real Metashape install.

```python
import Metashape

chunk = Metashape.app.document.chunk

# WRONG: produces chunk-internal coordinates
chunk.exportPointCloud("/path/output.las")

# RIGHT: explicit CRS
chunk.exportPointCloud(
    "/path/output.las",
    crs=chunk.crs,                                 # or any specific CRS:
    # crs=Metashape.CoordinateSystem("EPSG::4326"),
)
```

### Caveats

- **`chunk.crs` may be `None`** for non-georeferenced projects.
  Always check before passing.

- **Two-camera "not georeferenced" gotcha.** Even if the
  Reference pane shows camera coordinates from EXIF, the chunk
  is only "referenced" with **≥ 3 reference points** (cameras
  or markers). Two GPS-tagged cameras alone are insufficient to
  triangulate a chunk-to-CRS transform. The GUI then also falls
  back to chunk-internal coords, matching Python.

- **Z-axis sign** can differ between chunk-internal and CRS
  coordinates (chunk uses right-handed local; some CRSes are
  left-handed or have inverted Z). Verify orientation after
  export with a known reference point.

## References

- *Metashape Pro User Manual* (2.3) §
  *Loading photos → Adding photos / Cameras submenu* — describes
  the GUI's Change Path command (without the format-swap caveat).
- *Metashape Python API Reference* (2.3.1):
  `Camera.photo.path`, `Chunk.exportPointCloud`, `Chunk.crs`.
- Forum threads:
  [*Change path/replace photos*](https://www.agisoft.com/forum/index.php?topic=2150.0)
  (Change Path semantics);
  [*exportPoints()*](https://www.agisoft.com/forum/index.php?topic=5037.0)
  (CRS-default difference).

## See also

- [Custom vertical datums: adding a geoid undulation grid](custom-geoid-vertical-datum.md)
- [`chunk.transform.matrix` is local→world; `camera.transform` is local](../../topics/crs/chunk-frame-vs-camera-frame.md)
- [Adding cameras to an aligned chunk: the `keep_keypoints` workflow](../alignment/incremental-matching-keep-keypoints.md)

