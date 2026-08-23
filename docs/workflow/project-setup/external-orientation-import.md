---
title: "Fixing exterior orientation: skipping Align Photos with known EO"
status: unverified
applies_to: Metashape Pro 2.x — and PhotoScan 1.x via the same Import Cameras / triangulate workflow
edition: Pro
last_reviewed: 2026-05-28
diataxis: how-to
confidence: high
---

# Fixing exterior orientation: skipping Align Photos with known EO

> **Confidence:** *high.* The workflow (Import Cameras + Build
> Points / `triangulateTiePoints` with fixed orientation) is
> directly attested by Agisoft support across multiple forum
> threads with permalinks. The Python pattern for setting
> `camera.transform` from reference data is forum-attested with
> a complete recipe.

## Problem

Your imagery's exterior orientation (camera position + rotation,
EO) and interior orientation (intrinsics, IO) are already known
to high precision — from a separate aerial-triangulation pass,
from an inertial-navigation system (INS), from a custom external
package, or from a previous Metashape project. You want to use
this data **as-is** and skip *Align Photos* entirely. The bundle
should not refine the camera parameters; it should generate
products (point cloud, mesh, orthomosaic) using the known EO/IO.

## Context

Metashape's *Align Photos* operation does two things:

1. **Match Photos** — feature detection + pair matching to build
   the tie-point cloud.
2. **Align Cameras** — bundle adjustment to solve for camera
   poses + intrinsics + tie-point 3D positions.

Skipping step 2 means you get the matched tie-point cloud
without any pose refinement. That requires:

- Camera poses (`camera.transform`) set to the known EO before
  starting.
- Camera intrinsics (`sensor.calibration` and / or
  `sensor.user_calib`) set to the known IO.
- The "fix" flags on each sensor enabled so the bundle does not
  modify them.

## Solution

> "Knowing the complete exterior orientation parameters
> (location and orientation angles) you can skip Align Cameras
> stage. It would work similar to Import Cameras feature that is
> Building Point cloud according to the imported EO/IO data —
> the images are matched, but EO and IO parameters are not
> refined."
> — Agisoft support, 2019-04-29, Metashape 1.5
> ([permalink](https://www.agisoft.com/forum/index.php?topic=10828.msg48916#msg48916))

### Path 1 — *Import Cameras* command (built-in)

For data formats Metashape natively supports (BINGO, PATB,
ORIMA Inpho, EnsoMOSAIC, Bundler, BlocksExchange, Pix4D):

1. *File → Import → Import Cameras…* and select the file.
2. Verify the imported cameras' positions and orientations in
   the *Reference* pane and the 3D view.
3. Load the camera calibration via *Tools → Camera Calibration
   → Load* (XML format) and check *Initial → Fix calibration*.
4. *Workflow → Build Point Cloud* (was: *Build Dense Cloud* in
   1.x), or first run *Workflow → Triangulate Tie Points* if
   the tie-point cloud is needed independently.

The tie-point cloud is produced by re-running matching against
the fixed camera poses; the cameras themselves are not adjusted.

### Path 2 — Python (when the format is unsupported)

For external formats not in the *Import Cameras* dropdown, set
`camera.transform` programmatically.

> **Demo verified:** ✗ — pending Tier 3 reproduction on a real Metashape install.

```python
import Metashape

chunk = Metashape.app.document.chunk
crs = chunk.crs
T = chunk.transform.matrix

# Set each camera's transform from its reference values
for camera in chunk.cameras:
    if camera.type != Metashape.Camera.Type.Regular:
        continue
    if not camera.reference.location or not camera.reference.rotation:
        continue
    # 1. Project geographic coordinates into the chunk's local frame
    pos_world = crs.unproject(camera.reference.location)
    pos_local = T.inv().mulp(pos_world)

    # 2. Build the rotation matrix from omega/phi/kappa or yaw/pitch/roll
    #    — pick the one matching your reference convention
    rot = Metashape.Utils.opk2mat(camera.reference.rotation)
    # rot = Metashape.Utils.ypr2mat(camera.reference.rotation)  # if YPR

    # 3. The camera-to-world transform in chunk-local frame
    #    must also be expressed via crs.localframe at the position
    local_frame = crs.localframe(pos_world)
    rot_local = T.rotation() * local_frame.inv().rotation() * rot

    # 4. Compose the 4x4 transform: rotation + translation
    M = Metashape.Matrix.Translation(pos_local) * \
        Metashape.Matrix.Rotation(rot_local)
    camera.transform = M
```

(The construction of the rotation in chunk-local coordinates
depends on whether the reference rotation is omega-phi-kappa
photogrammetric convention or yaw-pitch-roll drone convention —
see [YPR rotation conventions](../../topics/scripting/ypr-rotation-conventions.md)
for the choice and sign-convention details.)

After setting all camera transforms:

> **Demo verified:** ✗ — pending Tier 3 reproduction on a real Metashape install.

```python
# Lock each sensor's calibration before triangulating
for sensor in chunk.sensors:
    sensor.fixed_calibration = True
    sensor.fixed = True   # fix all parameters: extrinsics + intrinsics
                          # (not just calibration)

# Generate the tie-point cloud using the fixed camera poses
chunk.matchPhotos(downscale=1, generic_preselection=False, reference_preselection=False)
chunk.triangulateTiePoints()  # was Chunk.buildPoints in 1.x
```

The `chunk.triangulateTiePoints()` call performs the
re-triangulation step that *Build Points* in older versions
does — it computes 3D positions for each matched feature given
the fixed camera poses, but does not refine the poses themselves.

## Verifying the EO is fixed

After running matching + triangulation:

> **Demo verified:** ✗ — pending Tier 3 reproduction on a real Metashape install.

```python
for camera in chunk.cameras[:3]:
    print(f"{camera.label}")
    print(f"  reference.location: {camera.reference.location}")
    print(f"  reference.rotation: {camera.reference.rotation}")
    print(f"  transform translation: {camera.transform.translation()}")
```

If the bundle did not modify the cameras, the `camera.transform`
translations should match the reference values (after CRS
projection). If they differ, the `fixed` flag was not set
correctly.

## Caveats

- **Calibration must also be fixed.** If `sensor.fixed_calibration`
  is `False`, the bundle's optional intrinsics refinement still
  runs and can perturb the focal length / distortion coefficients
  even when extrinsics are locked. Set both:

  ```python
  sensor.fixed_calibration = True   # don't refine intrinsics
  sensor.fixed = True               # don't refine extrinsics
  ```

- **`reference.rotation` convention matters.** Metashape reads
  rotation references as omega-phi-kappa or yaw-pitch-roll
  depending on the *Reference Settings → Rotation angles* setting
  in the Reference pane. The Python `opk2mat` / `ypr2mat`
  helpers must match your convention; the wrong choice flips a
  pitch sign and produces cameras pointing in the opposite
  direction. See [YPR rotation conventions](../../topics/scripting/ypr-rotation-conventions.md).

- **Without an existing chunk transform**, `chunk.transform.matrix`
  is identity. The first camera you set the transform for
  effectively defines the chunk's local frame origin. To
  preserve a specific origin, set `chunk.transform.matrix` first
  via [Repositioning a chunk](repositioning-chunk-origin.md).

- **Re-running *Align Photos*** after this workflow will
  discard the imported EO unless *Reset current alignment* is
  unchecked AND the cameras are marked as already aligned in the
  Workspace pane.

## See also

- [Choosing camera axes: aerial vs terrestrial (and YPR vs OPK)](../../topics/scripting/choosing-rotation-representation.md)
- [Repositioning a chunk: moving the origin to a known point](repositioning-chunk-origin.md)
- [Drone metadata: DJI altitude semantics and RTK XMP accuracy tags](dji-drone-metadata.md)
- [YPR rotation conventions: `ypr2mat` vs `camera.reference.rotation`](../../topics/scripting/ypr-rotation-conventions.md)
- [Importing camera orientation: EXIF, OPK, yaw/pitch/roll](importing-camera-orientation.md)
- [`sensor.calibration` vs `sensor.user_calib` — initial vs adjusted values](../camera-calibration/sensor-calibration-vs-user-calib.md)

## References

- *Metashape Pro User Manual* (2.3), ch. 3 *General workflow*,
  § *Align Photos → Importing camera positions* — describes the
  *Import Cameras* command and supported formats.
- *Metashape Python API Reference* (2.3.1):
  `Camera.transform`, `Sensor.fixed_calibration`, `Sensor.fixed`,
  `Chunk.triangulateTiePoints`, `Utils.opk2mat`, `Utils.ypr2mat`,
  `CoordinateSystem.localframe`, `CoordinateSystem.unproject`.
- Forum thread, [*Metashape External Orientation instead of
  Aerial Triangulation*, 2019-2020](https://www.agisoft.com/forum/index.php?topic=10828.msg49989#msg49989)
  — the canonical Q&A; includes the Python recipe (msg 51996).
- Forum thread, [*Importing LIDAR Data*, 2018](https://www.agisoft.com/forum/index.php?topic=8315.msg40852#msg40852)
  — earlier Q&A on the same workflow with photogrammetric
  data from external packages.

