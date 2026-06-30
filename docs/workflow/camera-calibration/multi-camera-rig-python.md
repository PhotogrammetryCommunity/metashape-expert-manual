---
title: Declaring a fixed-geometry multi-camera rig in Python
status: unverified
applies_to: Metashape Pro 2.x — and unchanged from Metashape 1.x via the same API
edition: Pro
last_reviewed: 2026-06-30
diataxis: how-to
confidence: high
---

# Declaring a fixed-geometry multi-camera rig in Python

> **Confidence:** *high.* The two-stage workflow
> (`MultiplaneLayout` + slave-sensor offsets) is forum-attested
> with explicit Python recipes from Agisoft support, and the
> entire `Sensor` / `Sensor.Reference` API surface is
> introspection-confirmed on Metashape 2.2.

A fixed-geometry multi-camera rig — a stereo pair, a multispectral
camera bank, an underwater rig with multiple ports — has cameras
whose mechanical relative orientation is constant during capture.
Telling Metashape about that constraint replaces N independent
exterior orientations with one master + (N − 1) fixed offsets,
greatly improving alignment robustness on rigs with limited
overlap.

The GUI does this through *Workflow → Add Folder* with the
"Multi-camera system" detection, followed by manually editing
slave offsets in *Tools → Camera Calibration*. The Python path
exposes the same surface but is more explicit.

## The two-stage Python workflow

### Stage 1 — Add the images with `MultiplaneLayout`

Each instant of capture across the rig contributes a *filegroup* —
one image per sensor for that instant. Metashape detects the rig
structure from the `filegroups` argument to `addPhotos` and
creates one `Sensor` per group member.

```python
import os
import Metashape

DATASET = "/path/to/stereo_rig"   # adjust
LEFT  = sorted(os.listdir(f"{DATASET}/SL"))
RIGHT = sorted(os.listdir(f"{DATASET}/SR"))
assert LEFT == RIGHT, "filename mismatch — pairs must align"

# Build (filename, filegroups) for a stereo pair.
# Each filegroup contains one image per sensor for the same instant.
filenames  = []
filegroups = []
for name in LEFT:
    filenames.extend([f"{DATASET}/SL/{name}", f"{DATASET}/SR/{name}"])
    filegroups.append(2)             # 2 images per group (L + R)

doc = Metashape.app.document
chunk = doc.addChunk()
chunk.addPhotos(
    filenames=filenames,
    filegroups=filegroups,
    layout=Metashape.MultiplaneLayout,
)

# After this, chunk.sensors has 2 sensors (left, right).
print(f"sensors: {len(chunk.sensors)}")
for s in chunk.sensors:
    print(f"  {s.label}  master={s.master.label!r}")
```

The `filegroups` argument is the per-instant count: `[N, N, N, …]`
where `N` is the rig's sensor count. The corresponding slice of
`filenames` is consumed in groups of `N`. The order matters —
within each filegroup, position `i` becomes a camera on sensor
`i`.

> "Have you checked already the examples of adding images using
> `MultiplaneLayout` (similar to Multi-camera system) option? It
> should work for steps 2-3 in your workflow, then camera
> calibration should be loaded for each sensor in `chunk.sensors`
> (you may need to understand which is left and right based on
> filename of any camera related to each sensor)." — Alexey
> Pasumansky, 2023-11-21, Metashape 2.1
> ([permalink](https://www.agisoft.com/forum/index.php?topic=16015.msg68969#msg68969))

### Stage 2 — Configure slave offsets

After `addPhotos` returns, `chunk.sensors` is a list of `Sensor`
objects. The first one (typically) is the master; the rest are
slaves. Their `.master` attribute confirms which is which (a
sensor is its own master iff it is the master).

For each *slave* sensor, declare its rigid offset relative to the
master:

```python
for sensor in chunk.sensors:
    if sensor.master == sensor:
        continue   # this is the master itself — no offset needed

    sensor.reference.location_enabled = True
    sensor.reference.rotation_enabled = True
    # x, y, z in metres (master frame)
    sensor.reference.location = Metashape.Vector([0.120, 0.000, 0.000])
    # omega, phi, kappa in degrees (master frame; always OPK,
    # independent of chunk.euler_angles — see Caveats)
    sensor.reference.rotation = Metashape.Vector([0.0, 0.0, 0.0])
```

The `*_enabled` flags **must** be `True` for the bundle to use the
declared values. Without them, the offsets are stored as metadata
but are not applied as constraints. With them set, the bundle
treats the slave-to-master transform as a fixed parameter — the
slave's pose follows the master's pose plus the offset.

> "To enable and define slave sensor offsets:
> ```python
> sensor.reference.location_enabled = True
> sensor.reference.rotation_enabled = True
> sensor.reference.location = Metashape.Vector([x, y, z])
> sensor.reference.rotation = Metashape.Vector([omega, phi, kappa])
> ```
> "
> — Alexey Pasumansky, 2023-11-21, Metashape 2.1
> ([permalink](https://www.agisoft.com/forum/index.php?topic=16015.msg72350#msg72350))

## Constraining the slave offsets during alignment

The slave-offset declaration above tells Metashape what the
offsets *are*. Whether the bundle should *trust* them as exact —
preventing further refinement during *Optimize Cameras* — is a
separate flag:

```python
sensor.fixed_location = True   # do not refine slave-to-master translation
sensor.fixed_rotation = True   # do not refine slave-to-master rotation
sensor.fixed_calibration = True   # do not refine intrinsics (focal length, etc.)
```

Set these when the offsets come from a high-precision factory
calibration (lab-measured rig geometry, with intrinsics from a
calibration pattern). Leave them `False` when the declared offsets
are approximate (CAD nominal, hand-measured) and you want the
bundle to refine them — typical when rig deformation between
captures is non-zero.

## Caveats

- **`addPhotos` creates a new `Sensor` per unique image
  dimension.** This is the default behaviour: a mixed batch of
  images with different pixel dimensions ends up split across
  multiple sensors after a single `addPhotos` call (e.g.,
  2048×2048 cubemap faces and 1024×768 aerial views land on two
  separate sensors). For a multi-camera rig where this isn't the
  intent, force a shared sensor explicitly:
  ```python
  shared_sensor = chunk.sensors[0]
  for cam in cameras_to_share:
      cam.sensor = shared_sensor
  ```
  Inversely, when calling `addPhotos` multiple times with images
  of different dimensions, the order of calls determines which
  sensor is `chunk.sensors[0]`. Don't rely on `chunk.sensors[0]`
  being a particular sensor — find sensors by `label` or by
  inspecting which cameras use them.
- **Rotation Vector convention — omega-phi-kappa.**
  `sensor.reference.rotation = Metashape.Vector([omega, phi,
  kappa])` is omega-phi-kappa in degrees (rotation about the X, Y,
  Z axes in that order), and this holds **independent of
  `chunk.euler_angles`**. This is the key difference from a *camera*
  reference rotation (`camera.reference.rotation`), which *does*
  follow `chunk.euler_angles` (yaw-pitch-roll when the chunk is
  YPR). Evidence: Agisoft support reads the adjusted slave offset
  as `Metashape.utils.mat2opk(sensor.rotation)`
  ([forum topic 11173](https://www.agisoft.com/forum/index.php?topic=11173.0)),
  and Agisoft's own *Apply Vertical Camera Alignment* script
  converts a *camera* reference via
  `euler2mat(rotation, chunk.euler_angles)` while converting the
  sensor-level `antenna.rotation` via a fixed `ypr2mat` — i.e.,
  sensor-level references are not routed through
  `chunk.euler_angles`
  ([agisoft-llc/metashape-scripts](https://github.com/agisoft-llc/metashape-scripts),
  quoted at [forum topic 17079](https://www.agisoft.com/forum/index.php?topic=17079.0)).
  Community recipes set the offset the same way, via
  `rotmat2opk` / explicit `omega, phi, kappa`
  ([topic 15021](https://www.agisoft.com/forum/index.php?topic=15021.0),
  [topic 10450](https://www.agisoft.com/forum/index.php?topic=10450.0)).
  Corroborated locally with `optimizeCameras` on a synthetic rig
  under a **YPR** chunk: a slave `reference.rotation` set from
  `mat2opk(solved_rotation)` (tight accuracy) stays put on
  re-optimize, while `mat2ypr(solved_rotation)` drags it away
  (single-chunk check — shows OPK is read under a YPR chunk, not a
  full two-convention proof). In the XML, the master sensor's
  `<sensor>` block has no `<rotation>` tag (implicit identity);
  slave sensors carry the declared offset — the same structure used
  for the RedEdge-M diagnosis in
  `choosing-master-sensor-multi-camera-layout.md`.
- **Master sensor selection is not made here.** It is determined
  earlier — by the filename/subfolder ordering of the images
  passed to `addPhotos`. The first sensor in alphabetical
  filename order becomes the master. If the desired master is not
  the alphabetically-first sensor, see
  [Choosing the master sensor](choosing-master-sensor-multi-camera-layout.md).
- **The four-element `ImageLayout` enum.** `Metashape.MultiplaneLayout`
  is one of `UndefinedLayout, FlatLayout, MultiframeLayout,
  MultiplaneLayout`. Use `MultiplaneLayout` for spatial-multiplexed
  rigs (multiple sensors capturing the same instant);
  `MultiframeLayout` is for time-multiplexed sequences (a single
  sensor capturing multiple frames per "instant"); `FlatLayout`
  is the default single-camera case.
- **Offsets are per-Sensor, not per-Camera.** All cameras
  belonging to the slave sensor inherit the same fixed offset.
  This is the whole point of the rig declaration — it factors out
  the offset from per-camera bundle parameters.

## Runnable demonstration on a stereo subset of the Building dataset

A genuine multi-camera dataset is not part of the Agisoft sample
collection. The script below treats two views of the
[Building](../../reference/sample-data.md#building) sample as a
synthetic stereo pair — adjacent frames, paired by index — to
demonstrate the API. Real rigs require real factory-calibrated
offsets; this demo exercises the API surface only.

> **Demo verified:** ✗ — pending Tier 3 reproduction on Metashape
> Pro 2.2 / 2.3 with a *MultiplaneLayout* dataset (synthetic from
> Building or a real rig). The underlying APIs are introspection-
> verified but the demo as written has not been run end-to-end.
> Required before the manual ships.

```python
"""Declare a synthetic stereo rig from the Building dataset.

Pre-condition: Building sample available; this script pairs frame
i with frame i+1 as a synthetic 'L'/'R' rig (offsets nominal).
"""
import os
import Metashape

DATASET = "/path/to/building"
images = sorted(os.listdir(DATASET))
n_pairs = len(images) // 2

filenames  = []
filegroups = []
for i in range(n_pairs):
    filenames.extend([f"{DATASET}/{images[2*i]}",
                      f"{DATASET}/{images[2*i + 1]}"])
    filegroups.append(2)

doc = Metashape.app.document
chunk = doc.addChunk()
chunk.addPhotos(filenames=filenames, filegroups=filegroups,
                layout=Metashape.MultiplaneLayout)

print(f"sensors: {len(chunk.sensors)}")
master = next(s for s in chunk.sensors if s.master == s)
slaves = [s for s in chunk.sensors if s.master != s]
print(f"master : {master.label}")
print(f"slaves : {[s.label for s in slaves]}")

# Declare a nominal 0.12 m baseline offset on each slave.
for sensor in slaves:
    sensor.reference.location_enabled = True
    sensor.reference.rotation_enabled = True
    sensor.reference.location = Metashape.Vector([0.120, 0.0, 0.0])
    sensor.reference.rotation = Metashape.Vector([0.0, 0.0, 0.0])

# Confirm the offsets are now stored.
for sensor in slaves:
    print(f"{sensor.label}: "
          f"loc={sensor.reference.location} "
          f"rot={sensor.reference.rotation} "
          f"loc_enabled={sensor.reference.location_enabled} "
          f"rot_enabled={sensor.reference.rotation_enabled}")
```

**Expected output:** `sensors: 2`, one master + one slave; the
declared offset shows up on the slave's `reference.location` and
`reference.rotation`. Subsequent `chunk.matchPhotos()` /
`chunk.alignCameras()` will run against a rig-constrained bundle.

## References

- [Forum thread, *Multiple-Camera Rig with Python API*, 2023](https://www.agisoft.com/forum/index.php?topic=16015.0)
  — primary source; the question + the
  Agisoft-support workflow (msg 72350).
- [Forum thread, *Multi-camera system Python add_photos*, 2022](https://www.agisoft.com/forum/index.php?topic=14453.0)
  — the earlier reference of the canonical
  `MultiplaneLayout` add-photos pattern (msg 63627).
- *Metashape Python Reference* (2.3.1), `Chunk.addPhotos` —
  documents `filegroups=` and `layout=`. `Sensor` and
  `Sensor.reference` document the offset surface.
- [Forum thread, *print adjusted slave-sensor offsets*](https://www.agisoft.com/forum/index.php?topic=11173.0)
  — Alexey Pasumansky (Agisoft) reads the adjusted offset as
  `mat2opk(sensor.rotation)`; confirms the slave offset is
  omega-phi-kappa.
- [agisoft-llc/metashape-scripts](https://github.com/agisoft-llc/metashape-scripts),
  *Apply Vertical Camera Alignment* (quoted at
  [forum topic 17079](https://www.agisoft.com/forum/index.php?topic=17079.0))
  — `camera.reference.rotation` is converted via
  `euler2mat(…, chunk.euler_angles)` while the sensor-level
  `antenna.rotation` uses a fixed `ypr2mat`; evidence that
  sensor-level references are not `euler_angles`-driven.
- [Forum thread, *How to enter slave offset values*, 2022](https://www.agisoft.com/forum/index.php?topic=15021.0)
  and [*input slave offset reference*, 2019](https://www.agisoft.com/forum/index.php?topic=10450.0)
  — community recipes setting `sensor.reference.rotation` as
  omega-phi-kappa (`rotmat2opk`). Corroboration; forum users, not
  Agisoft staff.
