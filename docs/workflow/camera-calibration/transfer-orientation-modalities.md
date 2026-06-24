---
title: "Transferring camera orientation between modalities (RGB → thermal)"
status: unverified
applies_to: Metashape Pro 2.x — pattern from `transfer_orientation.py` in the official metashape-scripts repo
edition: Pro
last_reviewed: 2026-05-30
diataxis: how-to
confidence: high
---

# Transferring camera orientation between modalities (RGB → thermal)

> **Confidence:** *high.* The script lives in Agisoft's
> official [`metashape-scripts`](https://github.com/agisoft-llc/metashape-scripts)
> repo, is tested against Metashape 2.3, and uses
> introspection-confirmed APIs (`Camera.transform`,
> `Camera.photo.meta`, `Camera.master`).

## Problem

Multi-modal capture: a drone with both an RGB sensor and a
thermal (or NIR, or multispectral) sensor takes synchronized
photos. The RGB photos have rich texture and align reliably;
the thermal photos have sparse features and frequently fail
*Align Photos*. You want to:

1. Align only the RGB cameras (which works reliably).
2. **Copy the alignment** to the corresponding thermal cameras
   (which were captured at the same time, in the same direction).
3. Build dense products from the now-aligned thermal cameras
   too.

Pure photogrammetry can't accomplish step 2 — the thermal
cameras need camera poses but `alignCameras` won't produce
them from sparse thermal features. The
[`transfer_orientation.py`](https://github.com/agisoft-llc/metashape-scripts/blob/master/src/transfer_orientation.py)
script handles this by **timestamp-matching** captures across
the two camera groups.

## Why timestamp matching

The trick: for a multi-camera rig firing simultaneously, each
camera's EXIF `DateTime` matches its sibling's to within a
fraction of a second. The script:

1. Reads `EXIF/DateTime` from every camera's metadata.
2. Sorts each modality's cameras by timestamp.
3. Pairs an RGB camera with a thermal camera if their
   timestamps match (within a 1-second tolerance) AND their
   sequence-position shift is consistent.
4. Copies `camera.transform` from the RGB to the thermal of
   each pair.

Subtleties:

- **Frame-counter shift detection.** If RGB and thermal
  cameras started numbering at different points (e.g., RGB
  starts at IMG_001, thermal starts at THM_023), the script
  detects the offset by which the most-frequent frame-shift
  produces matching timestamps.
- **Multi-shift handling.** Mid-flight reset of one camera
  produces a discontinuity. The script handles multiple
  shifts by trying each candidate shift and keeping the one
  that produces the most matches.

## Workflow

The script's own usage instructions:

> "Usage:
> 1. Chunk (right click) → Add → Add Folder... to add RGB photos
> 2. Chunk (right click) → Add → Add Photos... to add thermal
>    photos (using 'Multi-camera system' option)
> 3. Disable all thermal cameras (for example, in the Photos pane)
> 4. Workflow → Align Photos... (only RGB photos will be aligned)
> 5. Enable all cameras and click Scripts → Transfer orientations"

Programmatically:

> **Demo verified:** ✗ — pending Tier 3 reproduction on a real Metashape install.

```python
import datetime as dt
from datetime import datetime, timedelta
import Metashape

chunk = Metashape.app.document.chunk

def parse_datetime(s):
    try:
        return datetime.strptime(s, "%Y:%m:%d %H:%M:%S")
    except (ValueError, KeyError):
        return datetime(dt.MINYEAR, 1, 1)

def get_camera_meta(cam):
    """Return (camera, frame_number, timestamp)."""
    meta = cam.photo.meta
    # Extract trailing digits from filename as frame number
    digits = "".join(c for c in cam.label if c.isdigit())
    frame_n = int(digits) if digits else 0
    timestamp = parse_datetime(meta.get("Exif/DateTime", ""))
    return (cam, frame_n, timestamp)

# Step 1: separate cameras by sensor (master vs slave)
master_cams = []
slave_cams = []
for cam in chunk.cameras:
    if cam.master == cam:    # this camera IS its own master (the RGB modality, presumably)
        master_cams.append(get_camera_meta(cam))
    else:
        slave_cams.append(get_camera_meta(cam))

# Step 2: sort by timestamp
master_cams.sort(key=lambda x: x[2])
slave_cams.sort(key=lambda x: x[2])

# Step 3: pair (simplified — see the script for shift-detection)
TOLERANCE = timedelta(seconds=1)
pairs = []
for slave_meta in slave_cams:
    slave_cam, slave_frame, slave_ts = slave_meta
    closest = min(
        master_cams,
        key=lambda m: abs((m[2] - slave_ts).total_seconds())
    )
    if abs((closest[2] - slave_ts).total_seconds()) <= TOLERANCE.total_seconds():
        pairs.append((closest[0], slave_cam))

print(f"Paired {len(pairs)} cameras across modalities")

# Step 4: copy transform from RGB to thermal
for rgb_cam, thermal_cam in pairs:
    if rgb_cam.transform and not thermal_cam.transform:
        thermal_cam.transform = rgb_cam.transform.copy()

print(f"Transferred orientation to {sum(1 for _, t in pairs if t.transform)} thermal cameras")
```

The above is simplified; the [full script](https://github.com/agisoft-llc/metashape-scripts/blob/master/src/transfer_orientation.py)
adds the multi-shift detection and a proper Hungarian-style
matching for ambiguous cases.

## What's NOT transferred

The script copies **`camera.transform`** (the 4×4 pose matrix)
only. It does not transfer:

- **Calibration.** Thermal cameras have different intrinsics
  (focal length, distortion); these need separate calibration.
  The script's docstring is explicit:

  > "Important: Calibration for thermal cameras will not be
  > adjusted automatically."

- **Reference data.** `camera.reference.location` etc. on the
  thermal cameras retain whatever was loaded from EXIF (or
  None).
- **Bundle uncertainty / covariance.** Thermal cameras get
  the RGB transform but no `location_covariance` —
  downstream uncertainty analyses will treat thermal positions
  as exact.

## When this approach fails

| Failure mode | Cause | Mitigation |
|--------------|-------|-----------|
| **No timestamps match** | Cameras have different clock zones / no clock sync | Manually configure a frame-shift offset; or set both clocks before flight |
| **Multiple cameras at the same timestamp** | Burst-mode RGB but single thermal | Filter master_cams to keep only the closest-frame-number to each thermal |
| **Some thermal cams unmatched** | Thermal capture rate ≠ RGB capture rate | Accept partial transfer; unmatched thermal cams stay unaligned |
| **Frame-shift detection picks wrong shift** | Multi-shift reset produced ambiguity | Edit the script to fix the shift manually |
| **Thermal calibration is way off** | The transferred extrinsics are correct but intrinsics are wrong | Run *Optimize Cameras* with a fixed-extrinsics constraint to refine intrinsics only |

## After the transfer

Once thermal cameras have transforms, they participate in
downstream operations:

> **Demo verified:** ✗ — pending Tier 3 reproduction on a real Metashape install.

```python
# Build depth maps using both modalities (e.g., for sensor fusion)
chunk.buildDepthMaps(
    downscale=2,
    filter_mode=Metashape.FilterMode.MildFiltering,
)

# Build texture using only the RGB cameras
rgb_cams = [c for c in chunk.cameras if c.master == c]
chunk.buildTexture(
    cameras=rgb_cams,
    blending_mode=Metashape.BlendingMode.MosaicBlending,
)

# Build a thermal-data orthomosaic using only thermal cameras
thermal_cams = [c for c in chunk.cameras if c.master != c]
# (further depending on how the chunk's data sources are organized)
```

For multi-camera rig declarations that maintain the
relationship persistently in the project (rather than the
one-shot transfer this script does), see
[Declaring a fixed-geometry multi-camera rig in Python](multi-camera-rig-python.md).

## Caveats

- **Camera labels are best matched by trailing digits.** The
  script's `get_number` extracts the longest run of digits
  from the filename. For unusual naming schemes (e.g.,
  `IMG_2023-08-15_001.JPG`), the heuristic may pick the
  date digits instead of the frame number; verify before
  trusting the matching.
- **Master / slave designation matters.** The script uses
  `cam.master == cam` to identify the leading modality.
  Set this via the *Camera Calibration* dialog or via
  `chunk.sensors[i].makeMaster()` before running.
- **Time zones must match.** Both cameras must record in the
  same time zone (usually local time, but verify).
  Discrepancies of an hour produce zero matches.
- **The transferred transform is in chunk-local frame.** If
  your downstream tools expect world coordinates, multiply
  by `chunk.transform.matrix`.
- **`camera.transform.copy()` is required.** Sharing the
  same Matrix instance between two cameras is dangerous;
  modifications via one camera affect the other. The `.copy()`
  call ensures independent matrices.
- **Re-running *Align Photos*** after this discards the
  transferred transforms (replaces with bundle-derived
  values, which fail for thermal). Use the
  `keep_keypoints=True` workflow if you want to add cameras
  to the chunk later without losing the transfer.

## See also

- [Declaring a fixed-geometry multi-camera rig in Python](multi-camera-rig-python.md)
  — the persistent multi-camera-rig declaration approach
  (vs. the one-shot transfer here).
- [Multispectral imaging: per-file band declaration and
  master-band change](multispectral-band-handling.md)
  — for the `MultiplaneLayout` alternative when modalities
  are tied at addPhotos time.
- [Choosing the master sensor in a multi-camera layout](choosing-master-sensor-multi-camera-layout.md)
  — when to elect each modality as master.
- [The slave-sensor transform: composition rule, axis
  convention, and recipes](slave-sensor-transform-recipes.md)
  — for the offset-between-modalities pattern.

## References

- [`transfer_orientation.py`](https://github.com/agisoft-llc/metashape-scripts/blob/master/src/transfer_orientation.py)
  — the canonical implementation in Agisoft's official
  scripts repo.
- *Metashape Python API Reference* (2.3.1):
  `Camera.transform`, `Camera.master`, `Camera.photo`,
  `Photo.meta`, `Sensor.makeMaster`, `Matrix.copy`.

