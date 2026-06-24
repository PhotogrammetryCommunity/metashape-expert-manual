---
title: "Camera stations: when to use them and the nodal-head requirement"
status: unverified
applies_to: Metashape Pro 2.x ; Metashape Standard 2.x — and unchanged from PhotoScan 1.x
edition: Standard
last_reviewed: 2026-05-28
diataxis: explanation
confidence: high
---

# Camera stations: when to use them and the nodal-head requirement

> **Confidence:** *high.* The nodal-head requirement is directly
> attested by Agisoft support with permalink. The Camera Station
> group type and its usage are documented in the official manual
> (*Camera station data* section).

A **camera station** in Metashape is a group of images that the
software treats as having been captured from the **same physical
optical centre**, with only orientation varying. Photogrammetric
processing handles them differently from independent cameras.

## What a camera station is

The official manual describes the feature: a `CameraGroup` with
type `Station` instructs Metashape that all images in the group
share one optical centre. Bundle adjustment then solves for one
position plus N orientations, instead of N independent
6-degree-of-freedom poses.

> **Demo verified:** ✗ — pending Tier 3 reproduction on a real Metashape install.

```python
import Metashape

chunk = Metashape.app.document.chunk

group = chunk.addCameraGroup()
group.label = "Station 1 (tripod, north view)"
group.type = Metashape.CameraGroup.Type.Station
for cam in chunk.cameras[:5]:   # the 5 images shot from this station
    cam.group = group
```

After this, *matchPhotos* and *alignCameras* respect the station
constraint: tie points within the group are skipped (no
parallax), and the group's images are placed in 3D space with a
single shared centre.

## The hidden requirement: nodal-head capture

What the manual does not emphasise: this only works correctly if
**the images really were captured from the same optical centre**.
Metashape does not detect or correct sub-millimetre translation
drift between station images. Hand-held capture introduces such
drift; a properly-set tripod head with the camera rotated about
its **lens nodal point** does not.

> "PhotoScan assumes that all images in the camera station group
> are taken from exactly the same camera position, so using nodal
> head is recommended. Offsets would not be compensated and may
> lead to the reconstruction problems."
> — Alexey Pasumansky, 2015-03-27, PhotoScan 1.1
> ([permalink](https://www.agisoft.com/forum/index.php?topic=3525.msg18949#msg18949))

Practical consequences:

1. **A regular tripod head is not a nodal head.** The camera
   rotates around the tripod ball-mount, not around the lens
   nodal point. This introduces translation as the camera swings.
2. **Hand-held "panorama-style" images are NOT camera stations.**
   Even careful spinning in place introduces decimetre-scale
   translation drift between images.
3. **Bracketed exposures from a fixed tripod ARE camera stations**
   (no orientation change either, which means the bundle has
   nothing to solve within the group; the group simply prevents
   redundant tie-point matching across the bracketed images).

## When to use camera stations

| Capture pattern | Use station? |
|-----------------|--------------|
| Spherical / 360° panorama from a nodal-head tripod | ✓ One station per pano |
| Bracketed exposures (HDR) from a tripod | ✓ One station per location |
| Multi-shot focus-stacking from a tripod | ✓ One station per stack |
| Hand-held "photogrammetry-style" coverage | ✗ Each image is its own |
| Drone flight (each image at a unique position) | ✗ Each image is its own |
| Tripod-mounted camera with deliberate translation | ✗ Each image is its own |

## Implications for 3D reconstruction

A single camera station, by itself, **cannot reconstruct 3D
geometry**. With one optical centre, there is no parallax — only
orientation. Reconstruction requires at least two stations with a
non-zero baseline between them.

The official manual states this explicitly: photogrammetric
processing requires at least two camera stations with overlapping
images (*Metashape Pro User Manual* 2.3, § *Camera station data*,
p. 39).

This is a feature, not a bug: the station type tells the bundle
"don't try to extract depth from within this group; treat it as
a single observer". The depth comes from the inter-station
baseline.

## The 360° panorama use case

The most common legitimate use of camera stations:

1. Mount the camera on a nodal-head tripod, rotate to the
   nodal point.
2. Capture multiple images per station, covering the full
   sphere or the relevant azimuth range.
3. Translate to a new station (typically 1–10 m baseline for
   close-range scenes), repeat.
4. In Metashape, group images per station via the Workspace pane
   or Python.
5. Run *matchPhotos* / *alignCameras*.

The reconstructed 3D model is built from the parallax between
stations, with each station contributing extensive scene coverage
from one viewpoint.

## Caveats

- **Not the same as `MultiplaneLayout`.** Camera stations group
  per-image-orientation under one optical centre; `MultiplaneLayout`
  groups per-instant captures across multiple sensors with fixed
  inter-sensor offsets. They solve different problems — see
  [Declaring a fixed-geometry multi-camera rig in Python](../camera-calibration/multi-camera-rig-python.md).
- **No automatic detection.** Camera stations must be declared
  manually (GUI grouping or Python API). EXIF metadata does not
  carry station information.
- **Nodal-point calibration.** The "nodal point" of a lens is
  the entrance pupil, not the front element or the sensor.
  Calibrating the tripod head's rotation axis to coincide with
  the entrance pupil takes practice; mis-calibrated nodal heads
  reintroduce parallax that the station model cannot handle.

## References

- *Metashape Pro User Manual* (2.3) §
  *Camera station data* (p. 39) — describes the feature and
  the "Set Group Type → Station" workflow.
- *Metashape Python API Reference* (2.3.1):
  `CameraGroup.Type.Station`, `Camera.group`,
  `Chunk.addCameraGroup`.
- Forum thread, [*Best practices for tank
  scanning*](https://www.agisoft.com/forum/index.php?topic=3525.0)
  — the nodal-head requirement (msg 17376).

## See also

- [Declaring a fixed-geometry multi-camera rig in Python](../camera-calibration/multi-camera-rig-python.md)
- [Drone metadata: DJI altitude semantics](dji-drone-metadata.md)

