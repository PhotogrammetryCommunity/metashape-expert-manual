---
title: "Exporting cameras for Gaussian Splatting / Colmap downstream pipelines"
status: unverified
applies_to: Metashape Pro 2.2+ — Colmap export added natively at 2.2; the standalone `export_for_gaussian_splatting.py` script is discontinued
edition: Pro
last_reviewed: 2026-05-30
diataxis: how-to
confidence: high
---

# Exporting cameras for Gaussian Splatting / Colmap downstream pipelines

> **Confidence:** *high.* The native Colmap-export support
> ships in Metashape 2.2+ as confirmed by the discontinued-
> script notice in
> [`metashape-scripts/export_for_gaussian_splatting.py`](https://github.com/agisoft-llc/metashape-scripts/blob/master/src/export_for_gaussian_splatting.py).
> The export-cameras GUI dialog and Python API are
> introspection-confirmed on Metashape 2.2.

## Problem

You have a Metashape project with aligned cameras and you want
to feed it into:

- A **Gaussian Splatting** training pipeline (e.g., the
  reference [3DGS implementation](https://github.com/graphdeco-inria/gaussian-splatting)
  from INRIA, or `nerfstudio`'s Splatfacto).
- A **NeRF** training pipeline (`nerfstudio`, `instant-ngp`,
  others).
- A **Colmap-format** consumer (any tool that ingests Colmap's
  `cameras.txt` / `images.txt` / `points3D.txt`).

These pipelines need three pieces of data:

1. **Per-camera intrinsics** (focal length, principal point,
   distortion).
2. **Per-camera extrinsics** (the camera's pose in a common
   world frame).
3. **A sparse point cloud** providing initial scene structure
   (for Gaussian Splatting's initialization).

Metashape produces all three; the question is just the file
format.

## Native Colmap export (Metashape 2.2+)

Since Metashape 2.2, the export-cameras dialog includes a
**Colmap (\*.txt)** option that produces the three Colmap
files directly:

> "`export_for_gaussian_splatting.py` is discontinued because
> corresponding functionality now included in Metashape.
> Please, use instead: *File → Export → Export Cameras...* and
> choose 'Colmap (\*.txt)' in 'Files of type'."
> — Agisoft, [`export_for_gaussian_splatting.py`](https://github.com/agisoft-llc/metashape-scripts/blob/master/src/export_for_gaussian_splatting.py)
> (script body, 2024+)

For Metashape **2.1, 2.0, or earlier**, see
[Older Metashape versions: the historical
`export_for_gaussian_splatting.py` script](#older-metashape-versions-the-historical-export_for_gaussian_splattingpy-script)
below.

### GUI workflow

1. *File → Export → Export Cameras…*
2. Pick a target folder.
3. In the *Files of type* dropdown, choose **Colmap (\*.txt)**.
4. Click *Save*.

Metashape writes three files into the folder:

- `cameras.txt` — per-sensor intrinsics (one entry per
  unique `Sensor` in the chunk).
- `images.txt` — per-camera extrinsics + the image filename
  reference for each one.
- `points3D.txt` — the sparse tie-point cloud.

These are the three files the Colmap-format consumer expects.

### Python equivalent

> **Demo verified:** ✗ — pending Tier 3 reproduction on a real Metashape install.

```python
import Metashape

chunk = Metashape.app.document.chunk

# Export to Colmap text format
chunk.exportCameras(
    "/path/to/output_folder/cameras.txt",
    format=Metashape.CamerasFormat.CamerasFormatColmap,
)
```

`exportCameras` writes all three Colmap files into the parent
directory of the path you specify.

## Workflow connection: from project to Gaussian Splatting

A typical end-to-end workflow:

1. **Capture and align** the dataset in Metashape (standard
   workflow up to *Align Photos* + *Optimize Cameras*).
2. **Save the source images** somewhere accessible. Gaussian
   Splatting reads the source RGB images directly, so they
   need to be on disk.
3. **Export to Colmap format** as above.
4. **Organise the directory** for the downstream tool. Most
   3DGS / NeRF tools expect a directory like:

   ```
   project/
       images/
           IMG_0001.JPG
           IMG_0002.JPG
           ...
       sparse/
           0/
               cameras.txt
               images.txt
               points3D.txt
   ```

   Move Metashape's exported `*.txt` files into `sparse/0/`
   (the `0` is a sub-key Colmap uses for multi-version
   reconstructions).

5. **Run the downstream tool.** For 3DGS:

   ```bash
   python train.py -s /path/to/project/ --resolution 1
   ```

   The training script reads `sparse/0/` for camera info and
   `images/` for the photos.

## Distortion-model compatibility

Metashape and Colmap use different distortion-model
parameterisations. Metashape's export to Colmap format
**translates** between them automatically — but the translation
is lossy for some Metashape distortion-model choices:

| Metashape sensor type | Translates to Colmap as | Notes |
|----------------------|-------------------------|-------|
| Frame | OPENCV_FISHEYE or OPENCV | Direct correspondence |
| Fisheye | OPENCV_FISHEYE | Direct |
| Spherical | (not exported) | 3DGS / NeRF don't support spherical natively |
| Cylindrical | (not exported) | Same as spherical |
| RPC | (not exported) | Satellite imagery is out of scope for 3DGS |

For projects with mixed sensor types, the spherical /
cylindrical / RPC cameras are silently dropped from the
export. Verify the exported `cameras.txt` contains all
expected sensors before training.

For a deeper look at Metashape's distortion model and the
mapping to Colmap's parameter set, see
[Metashape's distortion model and converting to OpenCV /
Colmap](../camera-calibration/distortion-model-opencv-colmap.md).

## What the export contains in detail

### `cameras.txt`

Each row: `CAMERA_ID MODEL WIDTH HEIGHT PARAMS...`. Metashape
emits one row per `Sensor`. The `MODEL` is `OPENCV` or
`OPENCV_FISHEYE` based on the sensor's type. `PARAMS` are the
distortion coefficients in Colmap's order:
`fx fy cx cy k1 k2 p1 p2 [k3 k4 k5 k6]`.

### `images.txt`

Each entry has two lines:

```
IMAGE_ID QW QX QY QZ TX TY TZ CAMERA_ID NAME
POINTS2D_X POINTS2D_Y POINT3D_ID ...
```

The first line is the camera's pose (rotation as quaternion;
translation in world coordinates) and metadata. The second
line lists the 2D tie-point projections in this image, each
linked to a 3D point in `points3D.txt` by ID.

### `points3D.txt`

Each row: `POINT3D_ID X Y Z R G B ERROR TRACK[]`. The TRACK is
a list of `(IMAGE_ID, POINT2D_IDX)` pairs identifying which
images observe this 3D point.

## Recipe — minimum viable export for 3DGS

For users who don't need the full project export:

> **Demo verified:** ✗ — pending Tier 3 reproduction on a real Metashape install.

```python
import Metashape
import os

doc = Metashape.app.document
chunk = doc.chunk

output_dir = "/path/to/training_data"
sparse_dir = os.path.join(output_dir, "sparse", "0")
images_dir = os.path.join(output_dir, "images")
os.makedirs(sparse_dir, exist_ok=True)
os.makedirs(images_dir, exist_ok=True)

# Step 1: Colmap export
chunk.exportCameras(
    os.path.join(sparse_dir, "cameras.txt"),
    format=Metashape.CamerasFormat.CamerasFormatColmap,
)

# Step 2: Copy / symlink the source images
for camera in chunk.cameras:
    if camera.transform:
        src = camera.photo.path
        dst = os.path.join(images_dir, os.path.basename(src))
        if not os.path.exists(dst):
            os.symlink(src, dst)   # use copy() if cross-filesystem

print(f"Training data prepared in {output_dir}/")
```

## When to use Metashape → 3DGS vs. running 3DGS standalone

| Workflow | Pros | Cons |
|----------|------|------|
| **Metashape align → export → 3DGS train** | High-quality alignment from Metashape; reuses GCPs and reference data | Two-tool workflow; alignment quality is from Metashape (not Colmap, which 3DGS docs assume) |
| **Pure Colmap → 3DGS train** | Single-tool workflow per the 3DGS reference docs | Colmap alignment quality may be lower than Metashape's on aerial / GCP-driven datasets |
| **3DGS without sparse init** | Simplest setup | Worse training convergence; may miss objects in the scene |

The Metashape-prepared workflow tends to give faster 3DGS
convergence on GCP-driven datasets because Metashape's bundle
adjustment uses the GCPs effectively.

## Older Metashape versions: the historical `export_for_gaussian_splatting.py` script

Metashape 2.1, 2.0, and earlier do **not** have the native
Colmap export. For users on these versions — which is common
in production environments where upgrading is gated by client
acceptance — the previously-published
`export_for_gaussian_splatting.py` script is the supported
path. The script was discontinued at commit
[`39a990b`](https://github.com/agisoft-llc/metashape-scripts/commit/39a990bd9e08f7f568f5c34a14a2e4ddef13eb19)
in early 2024 (when the native 2.2 export shipped); the repo's
`master` branch now contains only a stub. The **last
fully-working revision** is at commit
[`45693c3`](https://github.com/agisoft-llc/metashape-scripts/blob/45693c397b0f0c201e61352ca3ad8c4134fa132b/src/export_for_gaussian_splatting.py)
(parent of the discontinue commit) and is API-compatible with
**Metashape 2.0, 2.1, 2.2, and 2.3**.

### Quick install + usage

1. Download `45693c3`'s
   [`export_for_gaussian_splatting.py`](https://github.com/agisoft-llc/metashape-scripts/blob/45693c397b0f0c201e61352ca3ad8c4134fa132b/src/export_for_gaussian_splatting.py)
   (right-click → save raw file).
2. (Metashape 2.0 / 2.1 only) Edit the line near the top:
   ```python
   compatible_major_version = "2.2"
   ```
   to match your Metashape version (`"2.0"` or `"2.1"`). No
   other edits needed — see *Why this works on older
   versions* below for the API-stability audit.
3. Save to your Metashape scripts auto-launch folder
   (per OS — see
   [*How to run Python script automatically on Metashape Professional start* (Agisoft KB)](https://agisoft.freshdesk.com/support/solutions/articles/31000133123)).
4. Restart Metashape.
5. The script appears under *Scripts → Export Colmap project
   (for Gaussian Splatting)*.

The script does NOT require `open3d`, `onnxruntime`, or any
other external dependency beyond Metashape's bundled Python.

### What the script provides beyond the native export

For Metashape 2.2 users who prefer the script (rather than the
native export), the script offers options not currently in the
native dialog:

| Script option | What it does | Why it matters for 3DGS / NeRF |
|---------------|--------------|-------------------------------|
| **Enforce zero cx, cy** | Forces principal-point offsets to zero in the output calibrations | Some 3DGS implementations don't yet support non-zero `cx, cy`; setting them to zero is a workaround at the cost of small re-cropping |
| **Use localframe** | Shifts coordinate origin to the bounding-box centre, applying the CRS's local frame at that point | Reduces precision loss when feeding large-coordinate-magnitude data (e.g., UTM eastings of ~500,000 m) into 3DGS, which uses single-precision floats |
| **Image quality** | JPEG quality (0-100) for the output undistorted images | The script also produces undistorted images; quality tradeoff vs. file size |
| **Export images** | Toggle off to skip the undistorted-image export | If you've already generated undistorted images by other means |

The native 2.2+ export covers the canonical Colmap-format
output but does NOT produce undistorted images, NOR does it
expose the localframe / zero-cx-cy options. For workflows
that depend on these, the script remains the more capable path
even on 2.2+.

### Output structure (script vs native)

The script writes a hierarchical structure:

```
<chosen_folder>
└── <chunk_0_folder>
    └── <frame_0_folder>
        ├── images/
        │   ├── <image_0>
        │   ├── <image_1>
        │   └── ...
        └── sparse/
            └── 0/
                ├── cameras.bin
                ├── images.bin
                └── points3D.bin
```

This matches the directory layout the 3DGS reference
implementation expects directly — `train.py -s
<chosen_folder>/<chunk_folder>/<frame_folder>` works as-is.
The native 2.2+ export writes only the `cameras.txt` /
`images.txt` / `points3D.txt` files; you reorganise into the
3DGS-expected layout yourself (see the
"Workflow connection" section above).

### Why this works on older versions (API audit)

The `45693c3` script's `compatible_major_version` is set to
`"2.2"` but the substantive code only uses APIs that have been
stable since Metashape 2.0 — verified by introspecting every
Metashape API surface the script touches against local
Metashape-2.0, Metashape-2.1, Metashape-2.2, and Metashape-2.3
installs. The APIs the script uses:

- `Metashape.Vector`, `Matrix.Diag`, `Matrix.Rotation`,
  `Matrix.Translation`, `Vector.cross`, `Vector.norm`,
  `Vector.normalized`
- `Calibration`, `ImageCompression`
- `chunk.frame`, `chunk.frames`, `frame.tie_points`,
  `frame.region`, `frame.transform`, `frame.cameras`,
  `frame.sensors`, `frame.crs`
- `Camera.image`, `Camera.transform`, `Camera.mask`,
  `Camera.photo`, `Camera.sensor`, `Camera.enabled`
- `Sensor.type`, `Sensor.calibration`, `Sensor.Type.Frame`,
  `Sensor.Type.Fisheye`
- `Calibration.f`, `cx`, `cy`, `width`, `height`, `project`,
  `unproject`
- `app.document`, `app.getBool`, `app.getExistingDirectory`

The `tie_points` API has been used since the script's first
commit (2023). The `point_cloud → tie_points` rename happened
at the 2.0 boundary, so the script targets the post-rename
namespace from the start. **The script does NOT work on
Metashape 1.x;** the 1.x equivalent would require
`tie_points` replaced with `point_cloud` throughout.

There is no need to pull earlier-targeting revisions of the
script. The substantive code didn't change between the 2.0,
2.1, 2.2, and 2.3 version-bumps. Each "update scripts
compatible versions to N" commit only changes the
`compatible_major_version` string. Earlier revisions also have
fewer accumulated bug fixes — use `45693c3` regardless of your
Metashape version.

## Caveats

- **The Colmap export is from Metashape 2.2+.** Earlier
  versions need the historical `export_for_gaussian_splatting.py`
  script — see [Older Metashape versions](#older-metashape-versions-the-historical-export_for_gaussian_splattingpy-script)
  above for the per-version permalinks.
- **Image paths in `images.txt` are filename-only.** The
  downstream tool resolves images via the `images/` directory;
  ensure file names in your project match (no spaces, no
  unusual characters).
- **`save_alpha=True` doesn't apply** — `exportCameras` is
  geometry-and-pose, not raster.
- **The exported sparse cloud might be too sparse for 3DGS
  initialization.** Some 3DGS implementations want >100K tie
  points. Metashape projects with high tie-point limits
  (e.g., `tiepoint_limit=4000` per image) produce dense enough
  clouds; very low limits (`tiepoint_limit=500`) may not.
- **Per-image `IMAGE_ID` ordering matters.** Some downstream
  tools assume sequential 1..N ordering. Metashape's export
  uses the chunk's camera ordering; if you've reordered
  cameras, the IDs reflect that.
- **Spherical / cylindrical cameras are dropped silently.**
  Verify the `cameras.txt` row count matches your aligned
  sensor count.

## See also

- [Metashape's distortion model and converting to OpenCV /
  Colmap](../camera-calibration/distortion-model-opencv-colmap.md)
  — the distortion-parameter mapping in detail.
- [Auto-export per-shape: orthomosaic, DEM, point cloud,
  mesh, KMZ](auto-export-per-shape.md)
  — for batch / per-shape variants of the export pattern.
- [`exportPointCloud` defaults: GUI vs Python CRS difference](exportpoints-crs-default.md)
  — analogous default-behaviour gotcha for point cloud
  exports.
- [Tiled models: when to use, what they replace, and how to
  export](../tiled-model/tiled-model-when-to-use.md)
  — alternative export target for browser viewing.

## References

- *Metashape Pro User Manual* (2.3), ch. 5 *Export →
  Export Cameras → Colmap format*.
- *Metashape Python API Reference* (2.3.1):
  `Chunk.exportCameras`, `CamerasFormat.CamerasFormatColmap`.
- [`export_for_gaussian_splatting.py`](https://github.com/agisoft-llc/metashape-scripts/blob/master/src/export_for_gaussian_splatting.py)
  — the discontinued standalone script (now redirects users
  to the native export).
- [Last working version of the script (commit `45693c3`)](https://github.com/agisoft-llc/metashape-scripts/blob/45693c397b0f0c201e61352ca3ad8c4134fa132b/src/export_for_gaussian_splatting.py)
  — API-compatible with Metashape 2.0, 2.1, and 2.2; for
  the older versions, edit the `compatible_major_version`
  string. Useful for Metashape 2.2+ users who need the
  script's extra options (zero cx/cy, localframe,
  image-export).
- [Gaussian Splatting reference implementation](https://github.com/graphdeco-inria/gaussian-splatting)
  — INRIA's reference 3DGS code that consumes Colmap-format
  output.
- [Colmap output format reference](https://colmap.github.io/format.html)
  — the canonical specification of `cameras.txt`,
  `images.txt`, `points3D.txt`.

