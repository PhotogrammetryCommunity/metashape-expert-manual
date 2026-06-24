---
title: "Multispectral imaging: per-file band declaration and master-band change"
status: unverified
applies_to: Metashape Pro 2.x — and PhotoScan 1.4+ via the same `MultiplaneLayout` and `Sensor.master` API
edition: Pro
last_reviewed: 2026-06-05
diataxis: how-to
confidence: high
---

# Multispectral imaging: per-file band declaration and master-band change

> **Confidence:** *high.* Both recipes are forum-attested with
> permalinks (Agisoft support, 2018). The
> `MultiplaneLayout` enum, `Sensor.master`, and
> `Sensor.fixed_rotation` API are introspection-confirmed on
> Metashape 2.2.

> **Scope statement.** The official manual covers MicaSense
> (RedEdge, Altum) and Parrot Sequoia auto-detection at *Add
> Photos* time — these multispectral cameras are recognised by
> their EXIF metadata and Metashape constructs the multiplane
> layout automatically. This article picks up where the manual
> stops: the **two operations** for cameras Metashape doesn't
> auto-detect — declaring band groupings explicitly via a
> nested list (Problem 1), and changing the master band after
> the layout is set (Problem 2 — including the
> `fixed_rotation` fix for the `Empty camera list` error).

## Problem 1 — Loading non-MicaSense / non-Parrot multispectral images

Metashape automatically constructs the multispectral camera
layout for **MicaSense (RedEdge, Altum) and Parrot Sequoia**
imagery when you pass all band files in a single
`addPhotos(filenames, layout=MultiplaneLayout)` call — the
software recognises the metadata and groups bands by capture
instant.

For **other multispectral cameras** (custom RGB+NIR rigs,
hyperspectral, dual-camera setups), Metashape cannot
auto-detect the band groupings. You must declare the per-instant
band groupings explicitly via a **nested list**.

> "If you are adding images from Parrot Sequoia or MicaSense
> RedEdge cameras using a single list for all bands, PhotoScan
> would create multiplane (multispectral) layout automatically.
> But if you are using some other sources, you can follow this
> approach"
> — Agisoft support, 2018-05-08, PhotoScan 1.4
> ([permalink](https://www.agisoft.com/forum/index.php?topic=8978.msg42061#msg42061))

### Pattern: nested list with per-instant band groups

> **Demo verified:** ✗ — pending Tier 3 reproduction on a real Metashape install.

```python
import os
import Metashape

# Two-band rig (RGB + NIR) with images already separated by folder
rgb = sorted([f"/images/rgb/{p}" for p in os.listdir("/images/rgb")])
nir = sorted([f"/images/nir/{p}" for p in os.listdir("/images/nir")])
assert len(rgb) == len(nir), "RGB and NIR must have the same number of frames"

# Build nested list: outer = per-instant; inner = band order within that instant
photo_groups = [[rgb[i], nir[i]] for i in range(len(rgb))]

doc = Metashape.app.document
chunk = doc.addChunk()
chunk.addPhotos(photo_groups, layout=Metashape.MultiplaneLayout)

# After this, chunk.sensors has one sensor per band (RGB and NIR sensors)
print(f"sensors created: {len(chunk.sensors)}")
for s in chunk.sensors:
    master_label = s.master.label if s.master and s.master is not s else "(self)"
    print(f"  {s.label}  master={master_label!r}")
```

The first sensor (alphabetically by filename, typically) becomes
the master; the rest are slaves with offsets relative to it. To
override this default, see Problem 2 below.

The format `addPhotos([[band0, band1, band2], ...], layout=MultiplaneLayout)`
is documented but easy to miss in the API reference because the
`filenames` parameter is shown as a flat list everywhere else.

## Problem 2 — Changing the master band after `addPhotos`

The default master band is determined by Metashape's
auto-detection (lowest `CentralWavelength` for native MicaSense /
Parrot, alphabetically-first sensor for nested-list sets). To
change it programmatically:

> "Master Band in the multispectral camera approach has
> different meaning from Primary channel, so changing the
> primary channel wouldn't have any effect on the Master Band.
> To switch the Master Band I can suggest the following
> solution"
> — Agisoft support, 2018-05-08, PhotoScan 1.4
> ([permalink](https://www.agisoft.com/forum/index.php?topic=8967.msg42062#msg42062))

### Pattern: clear-then-reassign

> **Demo verified:** ✗ — pending Tier 3 reproduction on a real Metashape install.

```python
import Metashape

chunk = Metashape.app.document.chunk

# Pick the new master sensor (e.g., the 4th band in a 5-band rig)
new_master = chunk.sensors[3]

# Step 1: clear all master assignments + reset 'fixed rotation' flag
for s in chunk.sensors:
    s.master = None
    s.fixed_rotation = False

# Step 2: assign the new master and lock its rotation
for s in chunk.sensors:
    s.master = new_master
new_master.fixed_rotation = True
```

The two-step assignment matters. Setting `s.master = new_master`
directly without first clearing the existing master can leave
the old master's `fixed_rotation` flag in place — which causes
later alignment to fail with `Empty camera list` errors when
the old master's images are no longer reference-frames.

### Common pitfall: `Empty camera list` error

If alignment (or orthomosaic generation) fails with `Empty camera
list` after a master-band change, the old master's
`fixed_rotation = True` flag persisted. Apply the two-step
pattern above (clear all flags first; then assign the new master
and lock only its rotation). This was the operational fix in
the source thread.

### Primary channel ≠ master band

The *Primary channel* (set via `chunk.primary_channel = N`)
controls **which band's pixels** are used for tie-point matching.
The master band is **which sensor's pose** is the bundle's
reference frame. Setting one does NOT change the other:

| Property | What it controls |
|----------|------------------|
| `chunk.primary_channel = N` | Which band index (0-based) provides the pixels for matching / texture |
| `sensor.master = X` for all sensors | Which sensor X is the rig's reference frame |

A typical workflow change might require setting both: switching
to a NIR-as-master rig might want NIR pixels (`primary_channel = 1`)
AND NIR pose as reference (`new_master = nir_sensor`).

A documented real-world case is the **Sentera 6X**: Agisoft
recommends changing the master band from NIR to **Green** (the
NIR band tends to oversaturate without a sun sensor) — see KB
[*How to process data from Sentera 6X in Metashape?* (Agisoft KB)](https://agisoft.freshdesk.com/support/solutions/articles/31000161146).

## Caveats

- **`MultiplaneLayout` requires consistent band counts.** Every
  per-instant entry in the nested list must have the same length
  (same number of bands). Variable-band layouts are not
  supported by `addPhotos`.
- **Re-running `chunk.matchPhotos` after a master-band change**
  uses the new master pose as the reference. If the new master's
  images differ significantly in feature density from the old
  master (e.g., changing from RGB to thermal), alignment may
  fail where it previously succeeded.
- **`chunk.resetRegion()` may be needed** after the master-band
  change. The bounding box was computed against the old master's
  poses; switching invalidates it. Add `chunk.resetRegion()`
  before *Build Depth Maps* to avoid `Empty region` / `Zero
  resolution` errors.
- **Reflectance calibration** (for MicaSense / Parrot
  multispectral) is independent of master-band selection. See
  the multispectral processing tutorial linked below.

## See also

- [Declaring a fixed-geometry multi-camera rig in Python](../camera-calibration/multi-camera-rig-python.md)
  — the broader rig-declaration pattern (general, not multispectral-
  specific).
- [Choosing the master sensor in a multi-camera layout](../camera-calibration/choosing-master-sensor-multi-camera-layout.md)
  — overview of master-sensor selection for any multi-camera rig.
- [The slave-sensor transform: composition rule, axis convention, and recipes](../camera-calibration/slave-sensor-transform-recipes.md)
  — the geometry behind master / slave offsets.

## References

- *Metashape Pro User Manual* (2.3), §
  *MicaSense, Parrot and DJI multispectral cameras* — describes
  the auto-detection workflow and Reflectance Calibration.
- *Per-sensor processing workflows* (end-to-end,
  including reflectance calibration):
    - [*MicaSense Altum processing workflow (including Reflectance Calibration) in Agisoft Metashape Professional* (Agisoft KB)](https://agisoft.freshdesk.com/support/solutions/articles/31000148381)
    - [*MicaSense RedEdge MX processing workflow (including Reflectance Calibration) in Agisoft Metashape Professional* (Agisoft KB)](https://agisoft.freshdesk.com/support/solutions/articles/31000148780)
    - [*How to add MicaSense RedEdge MX Dual data properly* (Agisoft KB)](https://agisoft.freshdesk.com/support/solutions/articles/31000161029)
    - [*DJI Phantom 4 Multispectral data processing* (Agisoft KB)](https://agisoft.freshdesk.com/support/solutions/articles/31000159853)
    - [*How to process data from Sentera 6X in Metashape?* (Agisoft KB)](https://agisoft.freshdesk.com/support/solutions/articles/31000161146)
- *Downstream / thermal:*
    - [*Prescription maps generation in Agisoft Metashape* (Agisoft KB)](https://agisoft.freshdesk.com/support/solutions/articles/31000161545) (NDVI-zone output)
    - [*Thermal imagery processing* (Agisoft KB)](https://agisoft.freshdesk.com/support/solutions/articles/31000158942)
    - [*Processing R-JPEG data in Metashape* (Agisoft KB)](https://agisoft.freshdesk.com/support/solutions/articles/31000166933)
- *Metashape Python API Reference* (2.3.1):
  `Chunk.addPhotos`, `Metashape.MultiplaneLayout`,
  `Sensor.master`, `Sensor.fixed_rotation`, `Chunk.primary_channel`.
- Forum thread, [*Multispectral Cameras from Files as Bands*, 2018](https://www.agisoft.com/forum/index.php?topic=8978.msg42061#msg42061)
  — nested-list `addPhotos` pattern.
- Forum thread, [*Python function on how to change master band in
  multispectral image mosaic*, 2018](https://www.agisoft.com/forum/index.php?topic=8967.msg42514#msg42514)
  — master-band change recipe with the `fixed_rotation` fix.

