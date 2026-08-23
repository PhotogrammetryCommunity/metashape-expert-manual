---
title: "Importing camera orientation: EXIF, omega-phi-kappa, and yaw/pitch/roll"
status: unverified
applies_to: Metashape Pro 2.x and Standard 2.x — and PhotoScan 1.x via the same workflow
edition: Standard
last_reviewed: 2026-05-23
diataxis: how-to
confidence: medium
---

# Importing camera orientation: EXIF, omega-phi-kappa, and yaw/pitch/roll
> **Confidence:** *medium.* The CSV-import paths are
> introspection-verified and well-attested. The EXIF side
> depends on each camera manufacturer's compliance with EXIF
> 2.3 GPS-tag conventions — actual tag presence varies widely
> and is the empirical question per dataset.

Three reproducible paths for getting per-camera orientation
into a Metashape project, each suited to a different data
source. All three populate `camera.reference.rotation` as a
3-component `Metashape.Vector` of degrees; the bundle then uses
the rotation as a soft constraint with the per-axis accuracy
from `camera.reference.rotation_accuracy`.

This article covers what conventions each path expects, how to
diagnose missing or wrong orientations, and the most common
"why are my poses upside-down?" gotchas.

## Path A — EXIF tags (when the camera populates them)

Some cameras (notably most consumer drones with magnetometers
and IMUs) bake orientation into image-file EXIF metadata.
Metashape reads these on `addPhotos` if the relevant tags are
present.

The tags Metashape recognises follow the EXIF 2.3 standard
(CIPA DC-008-2012):

| EXIF tag | Meaning | Convention | Common cameras populating it |
|----------|---------|------------|------------------------------|
| `GPS:GPSImgDirection` | Yaw / azimuth from north | Degrees, 0–360 | Most prosumer drones |
| `GPS:GPSImgDirectionRef` | "T" (true north) or "M" (magnetic) | Single character | Drones |
| `GPS:GPSPitch` | Pitch | Degrees | Less common; some Sentera, Pix4D-tagged data |
| `GPS:GPSRoll` | Roll | Degrees | Less common |

> "You can check EXIF 2.3 standard specification:
> [http://www.cipa.jp/std/documents/e/DC-008-2012_E.pdf](http://www.cipa.jp/std/documents/e/DC-008-2012_E.pdf)" —
> Alexey Pasumansky, 2014-07-03, PhotoScan 1.0
> ([permalink](https://www.agisoft.com/forum/index.php?topic=2572.msg13156#msg13156))

### Diagnose what your camera emits

```bash
exiftool -s your_image.jpg | grep -E '(GPS|Yaw|Pitch|Roll)'
```

Look for `GPSImgDirection`, `GPSPitch`, `GPSRoll`. If your
camera emits proprietary tags instead (e.g., DJI's
`DJI:FlightYawDegree`, Sentera's `SenteraPitch`), Metashape
won't pick them up — you need to convert to a CSV (Path B).

### How to inject orientations into EXIF (rarely the right answer)

If you must inject orientations into EXIF (e.g., your downstream
toolchain expects them there), `exiftool` can write the standard
tags:

```bash
exiftool -GPSImgDirection=123.4 -GPSImgDirectionRef=T \
         -GPSPitch=2.1 -GPSRoll=-0.3 \
         your_image.jpg
```

But this is **not** the recommended path for Metashape — CSV
import (Path B) is more reliable, doesn't modify image files,
and supports per-axis accuracy specification.

## Path B — Reference CSV with yaw/pitch/roll

The most flexible and recommended path. Build a CSV with one
row per image:

```csv
label,longitude,latitude,altitude,yaw,pitch,roll,sigma_xyz,sigma_ypr
IMG_0001.jpg,-79.152,37.401,208.0,123.4,2.1,-0.3,0.5,1.0
IMG_0002.jpg,-79.151,37.401,208.5,124.5,1.8,-0.5,0.5,1.0
```

Import via `chunk.importReference`:

```python
import Metashape

chunk = Metashape.app.document.chunk
chunk.importReference(
    path="/path/to/orientations.csv",
    format=Metashape.ReferenceFormatCSV,
    delimiter=",",
    columns="nxyzabc",          # n=label, xyz=position, abc=yaw/pitch/roll
    items=Metashape.ReferenceItemsCameras,
)
```

The `columns` argument maps each character to a column role:

| Char | Role |
|------|------|
| `n` | Label (file name) |
| `x` | Longitude / Easting |
| `y` | Latitude / Northing |
| `z` | Altitude |
| `a` | Yaw (or Omega — see Path C) |
| `b` | Pitch (or Phi) |
| `c` | Roll (or Kappa) |
| `X` / `Y` / `Z` | Position accuracy (per-axis sigma) |
| `A` / `B` / `C` | Rotation accuracy (per-axis sigma) |
| `_` | Skip column |

After import:

- `camera.reference.location` is populated with the X / Y / Z.
- `camera.reference.rotation` is populated with the (yaw, pitch, roll)
  Vector.
- `camera.reference.location_accuracy` and `rotation_accuracy`
  are populated if X/Y/Z and A/B/C accuracy columns were
  supplied.
- `camera.reference.location_enabled` and `rotation_enabled`
  are set to `True`.

## Path C — Reference CSV with omega/phi/kappa

OPK is photogrammetry-classical: rotations about X (omega), Y
(phi), Z (kappa), in the order specified by the convention.
Metashape supports this when the chunk's *Reference settings* —
*Camera reference rotation* — is set to *Omega-Phi-Kappa* before
the import:

```python
chunk.importReference(
    path="/path/to/opk.csv",
    format=Metashape.ReferenceFormatCSV,
    delimiter=",",
    columns="nxyzabc",          # a/b/c interpreted via rotation_angles below
    items=Metashape.ReferenceItemsCameras,
    rotation_angles=Metashape.EulerAnglesOPK,
)
```

The rotation-angle convention is set per-call via the
`rotation_angles` kwarg. Available enum values (Tier 1
introspection on Metashape 2.2.3):
`EulerAnglesOPK` (omega/phi/kappa),
`EulerAnglesYPR` (yaw/pitch/roll),
`EulerAnglesPOK` (phi/omega/kappa, alternate ordering),
`EulerAnglesANK` (alpha/nu/kappa, photogrammetry alternative),
`EulerAnglesUndefined` (defer to chunk default).

The `columns` syntax is the same as Path B; the *interpretation*
of `a/b/c` is set by `rotation_angles`. The GUI equivalent is
*Reference Settings → Camera reference rotation*; the dropdown
maps to the same enum values. There is no chunk-level attribute
that holds the rotation-angle format — it is set per
`importReference` call.

## Choosing between paths

| Scenario | Best path |
|----------|-----------|
| Images already have EXIF orientations (drone autopilot baked them in) | **A** — `addPhotos` picks them up automatically |
| External CSV from drone log with yaw/pitch/roll | **B** — most common production path |
| Photogrammetric OPK file from INS / IMU system (Riegl, Yellowscan, etc.) | **C** — set chunk rotation format to OPK first |
| Position-only (no orientation known) | None — set `rotation_enabled = False` and rely on the bundle |

When in doubt, Path B (CSV with yaw/pitch/roll) is the most
debuggable and convention-explicit path. EXIF (Path A) hides
its conventions; OPK (Path C) requires a global chunk-setting
toggle.

## Common gotchas

### Yaw conventions: degrees vs radians, 0–360 vs ±180

Metashape's `camera.reference.rotation` expects degrees in the
range that the chosen rotation format dictates. Yaw in the
yaw-pitch-roll convention is typically 0–360 (azimuth from
north); some external tools use ±180 (signed deviation from
north). A 720° azimuth is no different from a 0° azimuth in
practice, but a -90° vs +270° distinction matters for some
external comparison tools.

### Magnetic vs true-north yaw

`GPSImgDirectionRef` distinguishes magnetic vs true-north yaw.
Most magnetometer-based cameras emit magnetic (`M`); true-north
yaw requires the local magnetic declination as a correction.
Metashape doesn't apply this correction automatically — if your
GCPs are in true-north and your camera emits magnetic-north, the
bundle will produce a uniform yaw offset.

### "My poses are upside-down"

A common symptom of axis-convention mismatch between the source
data and Metashape's interpretation. Three things to check:

- **Sign of pitch / roll.** Some external tools use
  positive-down for pitch; Metashape uses positive-up. A 180°
  rotation about the Y axis flips this. **The
  `Metashape.Utils.mat2ypr` helper itself uses a different
  pitch sign than `camera.reference.rotation` for the same
  physical pose** — for the deep-dive, see
  [YPR rotation conventions: `ypr2mat` vs `camera.reference.rotation`](../../topics/scripting/ypr-rotation-conventions.md).
- **Yaw direction.** Clockwise from north (standard navigation)
  vs counter-clockwise from north (some mathematical
  conventions).
- **Right-handed vs left-handed coordinate system.** Metashape
  uses right-handed; some game engines use left-handed.
  Round-tripping between them flips one axis.

The diagnostic: `print(camera.transform.rotation())` after the
bundle settles. The 3×3 sub-matrix should make sense for the
camera's actual orientation; if it's clearly wrong (e.g.,
Z column points to nadir for an oblique camera), the input
convention was misread.

### Per-axis accuracy is a `Vector`, not a scalar

```python
camera.reference.rotation_accuracy = Metashape.Vector([2.0, 5.0, 10.0])
# 2° on yaw (high-confidence from compass), 5° on pitch,
# 10° on roll (low-confidence from a noisy magnetometer)
```

See [`chunk.transform.matrix` is local→world; `camera.transform`
is local](../../topics/crs/chunk-frame-vs-camera-frame.md) for
the per-axis accuracy machinery.

## Caveats

- **EXIF tag support varies wildly between cameras.** A
  manufacturer that emits GPSImgDirection but not GPSPitch /
  GPSRoll requires a CSV side-channel for full orientations.
  `exiftool -s` is the diagnostic tool.
- **CSV-import column-string syntax is per-character.** Don't
  separate the characters with anything; `columns="nxyzabc"`
  not `columns="n,x,y,z,a,b,c"`.
- **OPK vs YPR is a chunk-level setting.** Switching it after
  import re-interprets existing rotations — likely producing
  geometrically wrong poses. Set the format *before*
  `importReference`.
- **Negative yaw values are accepted** but interact with the
  bundle's parameterisation. Prefer 0–360 for yaw in YPR mode
  to match standard EXIF / drone-log conventions.
- **Roll-pitch-yaw vs heading-pitch-bank.** Some external
  conventions use H-P-B which is structurally the same as Y-P-R
  but with different per-axis labels. Confirm the convention's
  axis mapping before using `columns=` to interpret a CSV.

## Runnable demonstration on the Aerial-with-GCPs sample dataset

The script below imports a CSV of yaw/pitch/roll for the chunk's
cameras (synthesised from the existing camera positions for
demo purposes), and verifies that `camera.reference.rotation`
gets populated.

> **Demo verified:** ✗ — pending Tier 3 reproduction on Metashape
> Pro 2.2 / 2.3 with the *Aerial-with-GCPs* sample dataset. The
> CSV-import API surface is introspection-verified; full
> end-to-end run with realistic orientation data is the missing
> step.

```python
"""Demonstrate Path B (CSV with yaw/pitch/roll) on Aerial-with-GCPs.

Pre-condition: chunk loaded with images.
"""
import csv
from pathlib import Path
import Metashape

chunk = Metashape.app.document.chunk

# Synthesize a CSV from existing camera positions, with placeholder
# orientations (yaw aligned with flight direction, level pitch/roll).
csv_path = Path("/tmp/orientations.csv")
with csv_path.open("w") as f:
    w = csv.writer(f)
    w.writerow(["label", "lon", "lat", "alt", "yaw", "pitch", "roll"])
    for cam in chunk.cameras:
        if cam.reference.location is None:
            continue
        loc = cam.reference.location
        w.writerow([cam.label, loc.x, loc.y, loc.z, 0.0, 0.0, 0.0])

# Import.
chunk.importReference(
    path=str(csv_path),
    format=Metashape.ReferenceFormatCSV,
    delimiter=",",
    columns="nxyzabc",
    items=Metashape.ReferenceItemsCameras,
)

# Verify.
populated = sum(
    1 for c in chunk.cameras
    if c.reference.rotation is not None
)
print(f"Cameras with reference.rotation populated: {populated}")
print()
sample = chunk.cameras[0]
print(f"First camera: {sample.label}")
print(f"  reference.rotation = {sample.reference.rotation}")
print(f"  reference.location = {sample.reference.location}")
```

**Expected output:** every camera's `reference.rotation` is
populated with `Vector([0, 0, 0])` (the placeholder values).
On a real flight log the values would carry the actual
yaw/pitch/roll per image.

## See also

- [Choosing camera axes: aerial vs terrestrial (and YPR vs OPK)](../../topics/scripting/choosing-rotation-representation.md)

## References

- [Forum thread, *Where to store Roll Pitch Yaw data in EXIF for
  import into PS*, 2014](https://www.agisoft.com/forum/index.php?topic=2572.0)
  — primary source; the pointer to EXIF 2.3 spec
  (msg 13156, 2014-07-03), 26-reply discussion of the EXIF
  side.
- [Forum thread, *How to convert Euler angles to Yaw, Pitch, &
  Roll (what are PS's conventions?)*, 2015](https://www.agisoft.com/forum/index.php?topic=3901.0)
  — convention details for the YPR mode.
- [Forum thread, *omega phi kappa import*, 2015](https://www.agisoft.com/forum/index.php?topic=4569.0)
  — OPK-mode specifics.
- [Forum thread, *Orientation issues*, 2015](https://www.agisoft.com/forum/index.php?topic=4425.0)
  — general orientation-issue diagnostic patterns.
- [Forum thread, *Write Camera Locations to EXIF*, 2013](https://www.agisoft.com/forum/index.php?topic=512.0)
  — EXIFTool recipes for the rare "inject into EXIF" case.
- *EXIF 2.3 specification*, CIPA DC-008-2012 ([cipa.jp link](http://www.cipa.jp/std/documents/e/DC-008-2012_E.pdf))
  — the canonical tag schema.
- *Metashape Python Reference* (2.3.1), `Chunk.importReference`,
  `Camera.reference.rotation`, `Camera.reference.rotation_accuracy`,
  `Camera.reference.rotation_enabled`.
- [`chunk.transform.matrix` is local→world; `camera.transform`
  is local](../../topics/crs/chunk-frame-vs-camera-frame.md) — per-axis accuracy `Vector` machinery.
