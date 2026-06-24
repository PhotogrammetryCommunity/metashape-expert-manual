---
title: "EXIF focal length: which tags Metashape reads, and the no-crop-factor rule"
status: unverified
applies_to: Metashape Pro 2.x and Metashape Standard 2.x — same EXIF-tag handling as PhotoScan 1.x
edition: "Pro / Standard"
last_reviewed: 2026-06-04
diataxis: explanation
confidence: high
---

# EXIF focal length: which tags Metashape reads, and the no-crop-factor rule

> **Confidence:** *high.* Both the EXIF-tag set and the
> no-crop-factor rule are forum-attested with permalinks
> (Agisoft support, 2015). The fallback behaviour for missing
> `FocalPlaneXResolution` is described by Agisoft support in the
> same thread.

## Problem

A common confusion among photographers new to photogrammetry:

- "I have a 25mm lens on a Micro Four Thirds body — should I
  enter 50mm (the 35mm-equivalent) into Metashape?"
- "My drone records 8.8mm in EXIF, but the manufacturer says
  it's a 24mm-equivalent — which value should I use?"
- "My RAW converter reports a different focal length than the
  JPEG's EXIF — which one is right?"

The short answer: **never apply a crop factor.** Use the actual
optical focal length (the value engraved on the lens or written
in the sensor manufacturer's spec sheet). Metashape combines
this with sensor pixel pitch to derive the pixel-equivalent
focal length internally — and that's what the bundle uses.

## Which EXIF tags Metashape reads

> "PhotoScan reads the following tags from EXIF to estimate
> focal length in pixels: `FocalLength`, `FocalPlaneXResolution`,
> `FocalPlaneYResolution`"
> — Agisoft support, 2015-10-26, PhotoScan 1.1
> ([permalink](https://www.agisoft.com/forum/index.php?topic=4443.msg22617#msg22617))

| EXIF tag | Unit | Role |
|----------|------|------|
| `FocalLength` | millimetres | The optical focal length of the lens |
| `FocalPlaneXResolution` | pixels per unit | Horizontal sensor pixel density |
| `FocalPlaneYResolution` | pixels per unit | Vertical sensor pixel density |
| `FocalPlaneResolutionUnit` | enum (1/2/3/4/5) | Unit for the above (typically 2 = inches) |

The conversion is straightforward:

```
focal_length_x_pixels = FocalLength_mm × FocalPlaneXResolution × unit_factor
```

where `unit_factor = 25.4` if `FocalPlaneResolutionUnit = 2`
(inches, the most common case), or `1.0` if it's already in
millimetres.

A worked example: a Sony A7R III with a 35mm lens reports
`FocalLength=35`, `FocalPlaneXResolution=798.246`,
`FocalPlaneResolutionUnit=2` (inches). The pixel-equivalent
focal length is:

```
35 × 798.246 / 25.4 ≈ 1100 pixels
```

(Note: some cameras report `FocalPlaneXResolution` in mm-per-pixel
or pixels-per-millimetre directly; Metashape parses
`FocalPlaneResolutionUnit` to determine which.)

## The no-crop-factor rule

> "PhotoScan uses both focal length in mm and sensor pixel size
> to convert focal length into pixel units. So you do not need
> to recalculate focal length according to the camera crop
> factor."
> — Agisoft support, 2015-10-25, PhotoScan 1.1
> ([permalink](https://www.agisoft.com/forum/index.php?topic=4443.msg22594#msg22594))

Why this matters: photographers used to thinking in "35mm
equivalent" focal lengths sometimes manually input 35mm-eq
values when filling in the *Camera Calibration* dialog. The
result is a 1.5–2× overestimated focal length, which causes
*Align Photos* to start far from the optimum and slows
convergence (or in extreme cases, fails alignment entirely).

The correct value is always the **physical optical focal
length**, as printed on the lens or in the sensor manufacturer's
specification — never the crop-adjusted equivalent.

## Examples by camera class

| Camera / sensor | Lens focal length | Use this value |
|-----------------|-------------------|----------------|
| Full-frame (35mm) DSLR with 50mm lens | 50mm | 50 |
| APS-C DSLR with 50mm lens | 50mm | 50 |
| Micro Four Thirds with 25mm lens | 25mm | 25 |
| Smartphone with "24mm-equivalent" main camera | physical (~5mm) | 5 |
| DJI drone with "24mm-equivalent" 1-inch sensor | physical (~8.8mm) | 8.8 |

The drone example is a frequent source of error: DJI and similar
manufacturers prominently advertise the 35mm-equivalent focal
length in marketing material, but the actual optical focal length
in EXIF is the physical value (~8-13mm depending on model).

## When EXIF data is missing or wrong

Three failure modes and their fixes:

### 1. `FocalPlaneXResolution` missing entirely

Some cameras (older smartphones, some industrial cameras) don't
write `FocalPlaneXResolution`. Metashape falls back to a default
sensor size estimate that may be wrong by 20-50%.

**Fix:** Set the calibration manually. *Tools → Camera
Calibration*; input the actual sensor pixel size (from the
manufacturer's data sheet) and the image dimensions. Metashape
then derives the pixel-equivalent focal length from the
`FocalLength` EXIF tag and your pixel size.

### 2. EXIF reports a "computational" focal length

Modern smartphones with multi-camera systems sometimes report
a synthetic focal length that doesn't match any physical lens
(e.g., a 0.5× ultrawide module reporting 13mm-equivalent). The
RAW frame may have been digitally cropped or fused from multiple
sensors.

**Fix:** Use a calibration target to determine the real focal
length empirically — [*Lens calibration (using chessboard pattern) in Metashape* (Agisoft KB)](https://agisoft.freshdesk.com/support/solutions/articles/31000160059)
walks through the on-screen-chessboard *Tools → Camera →
Calibrate Lens* procedure (or use an AprilTag grid). Load the
result via `sensor.user_calib` (see
[`sensor.calibration` vs `sensor.user_calib`](sensor-calibration-vs-user-calib.md)).

### 3. Pre-undistorted images

DJI Phantom 4 RTK, Mavic 3 Cine, and some cinema cameras
internally undistort fisheye / wide imagery before writing JPEG
output. The EXIF still reflects the original optical focal
length, but the image content has been digitally rectified to a
narrower equivalent.

**Fix:** Treat the camera as a *Frame* sensor type with a
calibration solved from the rectified output. Don't try to
recover the original fisheye parameters — they don't apply
to the rectified pixels.

## EXIF focal length is only a starting estimate

> **Demo verified:** ✗ — pending Tier 3 reproduction on a real Metashape install.

```python
import Metashape

chunk = Metashape.app.document.chunk

# After Align Photos / Optimize Cameras, the bundle has refined
# the focal length away from the EXIF starting value.
for sensor in chunk.sensors:
    init = sensor.user_calib  # may be None if not user-set
    refined = sensor.calibration  # the bundle-adjusted value

    print(f"{sensor.label}")
    if init:
        print(f"  initial f (mm): {init.f}")
    print(f"  refined f (px):  {refined.f}")
    print(f"  refined cx, cy:  ({refined.cx}, {refined.cy})")
```

The bundle adjustment refines focal length to fit the tie-point
cloud. The EXIF value's accuracy mostly affects:

- **Alignment convergence speed.** A wildly wrong starting
  focal length (e.g., 100mm when the truth is 35mm) can take
  many bundle iterations to converge or fail entirely.
- **Failure modes for low-overlap sets.** With ≥80% image
  overlap and good distribution, the bundle converges to the
  correct focal regardless of EXIF accuracy. With <60%
  overlap, a wrong starting focal can produce a locally-optimal
  but globally-wrong solution.

For high-overlap aerial datasets with well-distributed cameras,
EXIF accuracy is usually not critical. For close-range,
single-orbit, or fisheye captures, EXIF accuracy matters more.

## Caveats

- **`FocalLength35efl` (the 35mm-equivalent EXIF tag)** is
  written by some cameras as a convenience field; Metashape
  does NOT use this tag. It reads the physical `FocalLength`
  only.
- **`LensInfo` and `Lens` model strings** in EXIF can hint at
  the lens but Metashape does not parse them. Identical lens
  serial numbers across multiple datasets do not automatically
  share calibrations — each chunk's calibration is solved
  independently unless you explicitly link sensors.
- **Variable-focal-length lenses** (zoom lenses, pancake
  retractable lenses): each photo's `FocalLength` is stored in
  EXIF. Metashape treats each unique focal length as a separate
  sensor by default; to merge them, group cameras manually
  in the *Camera Calibration* dialog. See [Declaring a
  fixed-geometry multi-camera rig in Python](multi-camera-rig-python.md)
  for the programmatic equivalent.
- **Fisheye / spherical sensors** read `FocalLength` but the
  pixel-equivalent calculation differs because the projection
  is not pinhole. Set the sensor type to *Fisheye* or
  *Spherical* before alignment for those cameras; see
  [Fisheye and spherical sensors: the five projection types](fisheye-spherical-camera-types.md).

## See also

- [`sensor.calibration` vs `sensor.user_calib`](sensor-calibration-vs-user-calib.md)
  — programmatic calibration import / override.
- [Fisheye and spherical sensors: the five projection types](fisheye-spherical-camera-types.md)
  — for non-pinhole projections.
- [Declaring a fixed-geometry multi-camera rig in Python](multi-camera-rig-python.md)
  — when one physical lens covers multiple `Sensor` objects.

## References

- *Metashape Pro User Manual* (2.3), ch. 4 *Camera calibration
  parameters → Initial calibration*.
- *EXIF specification 2.32*, §4.6.5 — `FocalLength`,
  `FocalPlaneXResolution`, `FocalPlaneYResolution`,
  `FocalPlaneResolutionUnit` definitions.
- *Metashape Python API Reference* (2.3.1):
  `Sensor.calibration`, `Sensor.user_calib`,
  `Calibration.f`.
- Forum thread, [*Focal length entry — should I apply crop
  factor?*, 2015](https://www.agisoft.com/forum/index.php?topic=4443.msg22687#msg22687)
  — the canonical clarification of the crop-factor confusion.
- [*Lens calibration (using chessboard pattern) in Metashape* (Agisoft KB)](https://agisoft.freshdesk.com/support/solutions/articles/31000160059)
  — the on-screen-chessboard empirical lens-calibration
  procedure (*Tools → Camera → Calibrate Lens*) for when EXIF
  focal length is missing or synthetic.

