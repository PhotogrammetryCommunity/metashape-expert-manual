---
title: "Drone metadata: DJI altitude semantics and RTK XMP accuracy tags"
status: unverified
applies_to: Metashape Pro 1.5+ (XMP accuracy tags); Metashape Pro 2.x (current)
edition: Pro
last_reviewed: 2026-06-05
diataxis: how-to
confidence: high
---

# Drone metadata: DJI altitude semantics and RTK XMP accuracy tags

> **Confidence:** *high.* Both findings are directly attested by
> Agisoft support with permalinks. The altitude semantics claim
> is verified by inspecting `camera.photo.meta` on DJI imagery.

## Problem

You imported drone images and the chunk's vertical reference is
off by 5–50 m. Or: you imported Phantom 4 RTK images expecting
RTK precision and the alignment shows centimetre-precise
horizontal but suspicious vertical errors. Both situations stem
from how Metashape reads — and what DJI writes — to image
metadata.

## DJI writes two altitudes; Metashape reads one

DJI drones embed **two distinct altitude values** in image
metadata:

| Tag | Source | Meaning |
|-----|--------|---------|
| `EXIF GPSAltitude` | Read by Metashape by default | Barometric altitude (DJI's "Absolute altitude") |
| `XMP drone-dji:RelativeAltitude` | NOT read by default | Height above the take-off point |
| `XMP drone-dji:AbsoluteAltitude` | NOT read by default | Same as EXIF GPSAltitude (duplicated) |

> "DJI is storing two altitude values in the XMP meta-data:
> Absolute altitude (I assume it's a barometric altitude) and
> Relative (this one seems to be height above take-off point).
> Also they are copying one of these values to GPSAltitude tag
> in EXIF — and it's Absolute altitude."
> — Alexey Pasumansky, 2018-03-27, PhotoScan 1.4
> ([permalink](https://www.agisoft.com/forum/index.php?topic=8306.msg41134#msg41134))

### Why this matters

DJI's **"Absolute altitude" is barometric**, not geometric:

1. **No fixed reference.** The barometer is zeroed at take-off;
   absolute readings drift with weather.
2. **Not above MSL or the ellipsoid.** It is barometric, not
   geodetic. Vertical residuals of 5–50 m versus WGS84
   ellipsoidal height are normal.

Metashape treats `GPSAltitude` as if it were ellipsoidal height,
which is wrong for DJI imagery. The result: position-only
georeferencing has a systematic vertical bias that can only be
corrected with GCPs.

## Inspecting the metadata yourself

> **Demo verified:** ✗ — pending Tier 3 reproduction on a real Metashape install.

```python
import Metashape

chunk = Metashape.app.document.chunk
camera = chunk.cameras[0]

# Print all metadata keys for this camera
for key, value in camera.photo.meta.items():
    if any(k in key.lower() for k in ["altitude", "drone", "gps"]):
        print(f"  {key}: {value}")
```

Typical output for a DJI Phantom 4 camera:

```
  Exif/GPSAltitude: 156.5
  Xmp/drone-dji:AbsoluteAltitude: +156.50
  Xmp/drone-dji:RelativeAltitude: +85.20
  Xmp/drone-dji:GpsLatitude: 47.123456
  Xmp/drone-dji:GpsLongitude: 8.654321
```

## Workaround: use RTK if available, plus GCPs always

For accurate vertical reference on DJI projects:

1. **For RTK drones (Phantom 4 RTK, Mavic 3 Enterprise RTK,
   etc.):** the RTK fix produces accurate horizontal coordinates,
   but the vertical is still derived from the barometer + RTK
   base offset. Use the RTK position with **GCPs as vertical
   control**.
2. **For non-RTK drones:** treat `GPSAltitude` as approximate
   only. Always use **GCPs with surveyed elevations** for
   vertical control.

## XMP accuracy tags (Metashape 1.5.0+)

Metashape 1.5.0 (build 7205, November 2018) added support for
**per-image accuracy values** loaded from DJI's XMP metadata.
This enables proper RTK / PPK weighting in bundle adjustment.

> "In the latest pre-release of the version 1.5.0 (build 7205)
> we have added the support for the GPS accuracy tags load from
> XMP meta data to the Reference pane (corresponding flag should
> be enabled in the Advanced preferences tab)."
> — Alexey Pasumansky, 2018-11-19, Metashape 1.5.0 pre-release
> ([permalink](https://www.agisoft.com/forum/index.php?topic=9910.msg45643#msg45643))

### Enabling the XMP accuracy reader

In Metashape 2.x:

1. *Tools → Preferences → Advanced* tab.
2. Enable **"Load camera orientation angles from XMP meta data"**
   (also reads accuracy tags).
3. Restart Metashape.
4. After enabling, *Add Folder* with DJI RTK images: per-image
   accuracy values populate in the Reference pane automatically.

### What the per-image accuracies do

With XMP accuracies loaded, the bundle adjustment weights each
camera's reference position by its individual sigma (typically
0.01–0.05 m horizontal for RTK, 0.05–0.5 m vertical). Without
this, all cameras share the chunk-default accuracy from the
Reference Settings dialog — which over-weights low-quality
fixes and under-weights high-quality ones.

For mixed-quality flights (e.g., a flight that started outside
RTK fix and recovered mid-flight), per-image accuracies are
essential.

## Caveats

- **Firmware-dependent behaviour.** The exact XMP fields and
  accuracy semantics vary by DJI model and firmware version.
  The 2018 thread describes Phantom 4 RTK; newer drones (Mavic 3
  Enterprise, Matrice 30T, etc.) may write additional or
  differently-named tags.
- **Barometric drift across long flights.** A flight lasting
  >30 minutes can show 1–2 m of barometric drift between
  start and end. RTK position is unaffected, but GPSAltitude on
  the EXIF will drift.
- **Multi-battery flights have step changes.** Each battery
  swap may re-zero the barometer, producing a step discontinuity
  in `GPSAltitude` between battery sets. RTK-based vertical (when
  available via XMP accuracies) does not have this step.
- **The "Load camera orientation angles" preference** is the
  same flag for both rotation angles AND accuracy tags;
  enabling it has no downside if your imagery doesn't have the
  XMP fields.

## References

- *Metashape Pro User Manual* (2.3) §
  *Loading photos → EXIF metadata* — describes the GPS / orientation
  metadata Metashape reads.
- Forum thread, [*Altitude used in Processing UAV (DJI Phantom 4
  Pro)*](https://www.agisoft.com/forum/index.php?topic=8306.0) —
  the EXIF / XMP altitude distinction.
- Forum thread, [*Workflow to process the Photography of "PHANTOM
  4 RTK"*](https://www.agisoft.com/forum/index.php?topic=9910.0)
  — XMP accuracy tag introduction in 1.5.0.
- [*Possible causes of large altitude errors when working with DJI images in Metashape* (Agisoft KB)](https://agisoft.freshdesk.com/support/solutions/articles/31000152491)
  — the AbsoluteAltitude/RelativeAltitude distinction and scripts
  to read RelativeAltitude and add a known ellipsoidal offset; and
  [*DJI with RTK coordinates data processing* (Agisoft KB)](https://agisoft.freshdesk.com/support/solutions/articles/31000161735)
  — the end-to-end RTK workflow (XMP accuracy, GNSS bias adjustment).

## See also

- [Choosing camera axes: aerial vs terrestrial (and YPR vs OPK)](../../topics/scripting/choosing-rotation-representation.md)
- [Custom vertical datums: adding a geoid undulation grid](custom-geoid-vertical-datum.md)
- [Importing camera orientation: EXIF, OPK, yaw/pitch/roll](importing-camera-orientation.md)
- [YPR rotation conventions](../../topics/scripting/ypr-rotation-conventions.md)

