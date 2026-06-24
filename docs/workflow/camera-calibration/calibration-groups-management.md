---
title: "Calibration groups: programmatic management in Python"
status: unverified
applies_to: Metashape Pro 2.x and Metashape Standard 2.x — same `Sensor` API as PhotoScan 1.x
edition: "Pro / Standard"
last_reviewed: 2026-05-29
diataxis: how-to
confidence: high
---

# Calibration groups: programmatic management in Python

> **Confidence:** *high.* Both recipes are forum-attested
> (Agisoft support, 2020). The `chunk.sensors`, `Sensor.type`,
> `Sensor.Type.Fisheye`, and sensor split / merge mechanics are
> introspection-confirmed on Metashape 2.2.

## Problem

You have a project with images from multiple cameras, or with
images that need different calibration treatment, and you need
to manage **calibration groups** programmatically:

- "Set every sensor in the project to fisheye type."
- "Split the calibration groups by camera serial number — all
  Camera A images in one group, all Camera B in another."
- "Apply different initial calibrations to different sensors
  loaded from external XML files."

The GUI's *Tools → Camera Calibration* dialog handles this for
small projects via right-click *Group* / *Ungroup*. For
batch-processing scripts, automated multi-camera-rig pipelines,
or programmatic IO/calibration management, you need the
`Sensor` API.

## Background: what is a calibration group?

A **calibration group** in Metashape is a `Sensor` object — one
per group. Each `chunk.cameras[i]` references its group via
`camera.sensor`. Cameras sharing the same `sensor` are in the
same group; cameras with different `sensor` values are in
different groups.

By default, Metashape creates one sensor per unique
`(camera_model, focal_length, image_dimensions)` triple at
*Add Photos* time. So 100 photos from one camera with a single
focal length end up in one group; mixed focal lengths from a
zoom lens end up in multiple groups.

## Recipe 1 — Switch all sensors to a specific type

> "The following code sample will switch the camera type for all
> the calibration groups to Fisheye"
> — Agisoft support, 2020-03-08, Metashape 1.6
> ([permalink](https://www.agisoft.com/forum/index.php?topic=11931.msg53450#msg53450))

> **Demo verified:** ✗ — pending Tier 3 reproduction on a real Metashape install.

```python
import Metashape

chunk = Metashape.app.document.chunk

for sensor in chunk.sensors:
    sensor.type = Metashape.Sensor.Type.Fisheye
```

Available types:

| `Sensor.Type` | When to use |
|----------------|-------------|
| `Frame` (default) | Standard rectilinear lens (≤ ~80° FOV) |
| `Fisheye` | Fisheye lens (≥ ~120° FOV) |
| `Spherical` | 360° equirectangular projection |
| `Cylindrical` | Panoramic strip imagery |
| `RPC` | Satellite imagery with rational-polynomial coefficients |

For per-sensor selection (mixed Frame + Fisheye projects), use
metadata to decide:

> **Demo verified:** ✗ — pending Tier 3 reproduction on a real Metashape install.

```python
import math
import Metashape

chunk = Metashape.app.document.chunk

for sensor in chunk.sensors:
    # Approximate horizontal field-of-view from focal length and sensor width
    f = sensor.calibration.f
    if f > 0:
        fov_deg = 2 * math.degrees(math.atan(sensor.width / (2 * f)))
    else:
        fov_deg = 0.0
    # Or rely on the sensor's label / metadata:
    if "fisheye" in sensor.label.lower() or "ultra" in sensor.label.lower() or fov_deg > 100:
        sensor.type = Metashape.Sensor.Type.Fisheye
    else:
        sensor.type = Metashape.Sensor.Type.Frame
```

## Recipe 2 — Split sensors by image-path pattern

For multi-camera capture rigs where each camera's images live
in its own folder, split by path:

> **Demo verified:** ✗ — pending Tier 3 reproduction on a real Metashape install.

```python
import Metashape

chunk = Metashape.app.document.chunk

# Identify cameras by source folder
cam_a_cameras = [c for c in chunk.cameras if "/camera_a/" in c.photo.path]
cam_b_cameras = [c for c in chunk.cameras if "/camera_b/" in c.photo.path]

# Create new sensors for camera A and camera B
sensor_a = chunk.addSensor()
sensor_a.label = "Camera A"
sensor_a.type = Metashape.Sensor.Type.Frame
sensor_a.width = cam_a_cameras[0].sensor.width
sensor_a.height = cam_a_cameras[0].sensor.height

sensor_b = chunk.addSensor()
sensor_b.label = "Camera B"
sensor_b.type = Metashape.Sensor.Type.Fisheye
sensor_b.width = cam_b_cameras[0].sensor.width
sensor_b.height = cam_b_cameras[0].sensor.height

# Reassign each camera to the appropriate new sensor
for camera in cam_a_cameras:
    camera.sensor = sensor_a
for camera in cam_b_cameras:
    camera.sensor = sensor_b

# Optionally: remove the old (now empty) sensors
to_remove = [s for s in chunk.sensors if s not in (sensor_a, sensor_b)]
chunk.remove(to_remove)
```

## Recipe 3 — Split sensors by EXIF metadata

For multi-camera projects in a single folder, separate by
EXIF camera model:

> **Demo verified:** ✗ — pending Tier 3 reproduction on a real Metashape install.

```python
import Metashape

chunk = Metashape.app.document.chunk

# Group cameras by EXIF model name
groups = {}
for camera in chunk.cameras:
    model = camera.photo.meta.get("Exif/Image/Model", "Unknown")
    groups.setdefault(model, []).append(camera)

print(f"Found {len(groups)} unique camera models:")
for model, cams in groups.items():
    print(f"  {model}: {len(cams)} images")

# Create one sensor per unique model
new_sensors = {}
for model, cams in groups.items():
    sensor = chunk.addSensor()
    sensor.label = model
    sensor.type = Metashape.Sensor.Type.Frame
    sensor.width = cams[0].sensor.width
    sensor.height = cams[0].sensor.height
    new_sensors[model] = sensor

# Reassign cameras to the per-model sensors
for camera in chunk.cameras:
    model = camera.photo.meta.get("Exif/Image/Model", "Unknown")
    camera.sensor = new_sensors[model]

# Cleanup unused sensors
chunk.remove([s for s in chunk.sensors if s not in new_sensors.values()])
```

## Recipe 4 — Load external calibrations into specific groups

Once sensors are split, load per-group calibration from XML
files:

> **Demo verified:** ✗ — pending Tier 3 reproduction on a real Metashape install.

```python
import Metashape

chunk = Metashape.app.document.chunk

calibration_files = {
    "Camera A": "/path/to/camera_a_calib.xml",
    "Camera B": "/path/to/camera_b_calib.xml",
}

for sensor in chunk.sensors:
    path = calibration_files.get(sensor.label)
    if not path:
        continue
    user_calib = Metashape.Calibration()
    user_calib.load(path)
    sensor.user_calib = user_calib
    sensor.fixed_calibration = True   # don't refine during bundle
```

The `sensor.user_calib` field provides the **initial values**
for the bundle. With `sensor.fixed_calibration = True`, those
values are kept as-is; with `False`, the bundle refines them.
For the distinction see [`sensor.calibration` vs `sensor.user_calib`](sensor-calibration-vs-user-calib.md).

## Caveats

- **Cameras must remain assigned to a sensor.** Setting
  `camera.sensor = None` raises an error. Always reassign
  before removing the old sensor.
- **`chunk.addSensor()` produces a fresh sensor with a default
  calibration.** You typically must set `width`, `height`, and
  `type` before assigning cameras; otherwise the sensor's
  calibration won't match the images' dimensions and *Align
  Photos* fails.
- **Sensor reassignment after alignment invalidates the
  alignment.** If cameras have already been aligned and you
  reassign their sensor, run *Optimize Cameras* afterwards to
  re-converge the bundle on the new calibration grouping.
- **`camera.photo.meta.get(key, default)` is the safe access
  pattern** for EXIF/XMP metadata. The dict-like `meta` object
  returns the key-not-present case via the default; direct
  access via `[]` raises `KeyError`.
- **Some cameras don't write `Exif/Image/Model`** (older
  industrial cameras, some smartphones). The Recipe 3 grouping
  falls back to `"Unknown"` for these — review the result before
  trusting it.

## See also

- [Declaring a fixed-geometry multi-camera rig in Python](multi-camera-rig-python.md)
  — for rigid sensors that must move together (multispectral,
  stereo).
- [`sensor.calibration` vs `sensor.user_calib` — initial vs adjusted values](sensor-calibration-vs-user-calib.md)
  — for using `user_calib` correctly.
- [Multispectral imaging: per-file band declaration and master-band change](multispectral-band-handling.md)
  — for the multispectral-specific `MultiplaneLayout` use case.
- [EXIF focal length: which tags Metashape reads](exif-focal-length-estimation.md)
  — for understanding how EXIF maps to sensor parameters.

## References

- *Metashape Pro User Manual* (2.3), ch. 4 *Camera calibration*
  — covers the GUI calibration dialog.
- *Metashape Python API Reference* (2.3.1):
  `Chunk.sensors`, `Chunk.addSensor`, `Chunk.remove`,
  `Sensor.type`, `Sensor.Type` (Frame / Fisheye / Spherical /
  Cylindrical / RPC), `Sensor.user_calib`,
  `Sensor.fixed_calibration`, `Sensor.width`, `Sensor.height`,
  `Sensor.label`, `Camera.sensor`, `Camera.photo`,
  `Photo.meta`.
- Forum thread, [*Calibrating a specific Camera Model*, 2020](https://www.agisoft.com/forum/index.php?topic=11931.msg53450#msg53450)
  — set-all-to-fisheye recipe; multi-camera split by path
  prompts.

