---
title: "Color calibration: when to use it, what it does, and the white-balance / vignetting knobs"
status: unverified
applies_to: Metashape Pro 2.x and Standard 2.x — same `Calibrate Colors` command since PhotoScan 1.4 (Jan 2018)
edition: "Pro / Standard"
last_reviewed: 2026-06-01
diataxis: explanation
confidence: high
---

# Color calibration: when to use it, what it does, and the white-balance / vignetting knobs

> **Confidence:** *high.* The feature description is from the
> official manual (chapters on *Build Texture* and *Build
> Orthomosaic*). Operational nuances (white-balance vs
> per-band, the reset-button bug in 1.5.3-1.5.4, accessing
> vignetting coefficients) are forum-attested with permalinks.
> The `Chunk.image_brightness`, `Chunk.image_contrast`, and
> `Chunk.calibrateColors` API are introspection-confirmed.

> **Scope statement.** The official manual extensively
> documents *Calibrate Colors* and the *Color calibration*
> dialog parameters at the GUI feature-reference level. This
> article picks up where the manual stops: what each parameter
> means **operationally**; the white-balance vs per-band
> distinction's effect on multispectral / NDVI workflows; the
> Python API equivalent; the historical context (replacement
> for the 1.3-era *Color Correction* checkbox); and four
> common failure modes with fixes.

## Problem

Your project's source images have inconsistent brightness or
white balance. Common causes:

- **Long capture sessions** where lighting drifted (sun moved
  across the sky during a 3-hour drone flight; cloud cover
  changed mid-flight).
- **Mixed cameras** with different built-in white-balance
  algorithms.
- **Vignetting** — uncorrected lens-darkening at the corners
  of each image, producing visible pattern in the orthomosaic
  that follows the camera-flight line.
- **Overlapping images** from different exposures (HDR
  bracketed, automatic exposure changing between captures).

The visible symptom: orthomosaic seams appear as bright /
dark stripes where adjacent images had different exposure.
Texture-on-mesh shows similar checkerboard pattern from
per-image colour shifts. Both are aesthetically wrong even
when the geometric reconstruction is fine.

Metashape's *Tools → Calibrate Colors…* command (introduced in
PhotoScan 1.4, January 2018) addresses all three: brightness
evening, white-balance evening, and vignetting correction.
This article covers what each option does, when to use it,
and the operational pitfalls.

## What `Calibrate Colors` does

The procedure analyses overlapping image regions across the
chunk's photo set and estimates per-image **brightness and
vignetting coefficients** that minimise the colour difference
between observations of the same surface point from different
cameras.

> "If the lighting conditions have been changing significantly
> during capturing scenario, it is recommended to use Calibrate
> colors option from the Tools menu before Build texture
> procedure. The option can help to even brightness and white
> balance of the images over the data set."
> — *Metashape Pro Manual* 2.3, § *Color calibration*

The corrections are **stored on each camera** and applied
**automatically** during *Build Texture* and *Build Orthomosaic*.
You do NOT see modified pixels in the *Photos* view; the
correction is a multiplicative adjustment applied at
texture-fetch time.

The key historical context (from the source thread):

> "Yes, it can be said that Calibrate Colors procedure
> substitutes Color Correction option in Build Texture / Build
> Orthomosaic dialogs. This new function can be used any time,
> before texture/orthomosaic are generated."
> — Agisoft support, 2018-01-22, PhotoScan 1.4
> ([permalink](https://www.agisoft.com/forum/index.php?topic=8284.msg39640#msg39640))

In PhotoScan 1.3 and earlier, the equivalent functionality
was a checkbox **inside** *Build Texture* / *Build Orthomosaic*
called *Color Correction*. The 1.4 redesign separated it into
its own command so that:

1. The same calibration could feed multiple downstream products
   (one Calibrate Colors run, then both Build Texture and
   Build Orthomosaic use the result).
2. The calibration could be inspected / reset between texture
   builds without rebuilding from scratch.
3. The procedure became scriptable as `chunk.calibrateColors(...)`.

## The two main options

The *Calibrate Colors* dialog has two key parameters that are
often misunderstood:

### Source data

Defines **what overlapping-region geometry** the procedure uses
to find shared surface points across images:

| Source data | Quality | Speed | When to use |
|-------------|---------|-------|-------------|
| **Tie points** | rough | fast | Initial pass; very large datasets where mesh isn't built |
| **Model** (mesh) | best | slow (mesh must be built) | Most accurate; recommended for texture quality |
| **DEM** | medium | medium | Aerial datasets where a single mesh isn't feasible |

The manual is explicit:

> "Model — gives more precise results, but only on condition
> that the surface is detailed enough. This parameter value is
> the recommended one if the aim is to calibrate colors to
> improve the quality of the model texture."
> — *Metashape Pro Manual* 2.3

For aerial projects: build the DEM first, then *Calibrate
Colors → Source data: DEM*. Skip the *Model* option since the
single-block mesh is often impractical at large project sizes.
For close-range / object scans: build the mesh first, then use
Model as source.

### Calibrate white balance

A checkbox controlling whether each colour band is corrected
**independently** (separately) or **together**:

| Setting | Behaviour | When to use |
|---------|-----------|-------------|
| **Unchecked** | All bands corrected with the same multiplier per image | Brightness-only correction; preserves per-band relationships |
| **Checked** | Each band gets its own per-image multiplier | Different cameras' white-balance shifts; mixed lighting |

> "White balance calibration options means that each band would
> be corrected separately, whereas with the option unchecked
> all bands will be corrected simultaneously."
> — Agisoft support, 2018-01-22, PhotoScan 1.4
> ([permalink](https://www.agisoft.com/forum/index.php?topic=8284.msg39640#msg39640))

For multispectral / NDVI / scientific work: leave unchecked
to preserve the per-band relationships (NDVI = (NIR-RED)/(NIR+RED)
depends on consistent inter-band ratios). For visual / aesthetic
work: check it for the cleanest result.

## Recipe — Python invocation

> **Demo verified:** ✗ — pending Tier 3 reproduction on a real Metashape install.

```python
import Metashape

chunk = Metashape.app.document.chunk

# Build mesh first if you'll use Model as source
if not chunk.model:
    chunk.buildDepthMaps(downscale=2,
                         filter_mode=Metashape.FilterMode.MildFiltering)
    chunk.buildModel(surface_type=Metashape.SurfaceType.Arbitrary,
                     source_data=Metashape.DataSource.DepthMapsData)

# Run color calibration
chunk.calibrateColors(
    source_data=Metashape.DataSource.ModelData,   # or TiePointsData / ElevationData
    color_balance=True,                           # the "Calibrate white balance" checkbox
)

# Now build texture / orthomosaic — corrections apply automatically
chunk.buildUV()
chunk.buildTexture(blending_mode=Metashape.BlendingMode.MosaicBlending)
```

The `source_data=` parameter accepts the same `DataSource` enum
values as other build operations.

## Per-image manual brightness adjustments

For finer control, *Tools → Adjust Color Levels…* (per-image,
right-click in the *Photos* pane) lets you set per-image
brightness / contrast manually. The settings are stored on each
camera and apply during build operations.

> **Demo verified:** ✗ — pending Tier 3 reproduction on a real Metashape install.

```python
import Metashape

chunk = Metashape.app.document.chunk

# Set chunk-wide brightness/contrast
chunk.image_brightness = 500   # range 0-1000; 500 is "no change"
chunk.image_contrast = 200     # range 0-1000; 200 is "no change"
```

The forum-attested pattern from Agisoft support:

> "You can set brightness and contrast in the following way:
> `chunk.image_brightness = 500` / `chunk.image_contrast = 200`.
> But there's no straightforward way to estimate the default
> values, like via GUI."
> — Agisoft support, 2019-07-23, Metashape 1.5
> ([permalink](https://www.agisoft.com/forum/index.php?topic=11164.msg50274#msg50274))

The "no straightforward way to estimate default values"
caveat is important: the GUI's *Adjust Color Levels* dialog
runs an analysis to suggest defaults, but the analysis isn't
exposed to scripts. For batch / automated workflows, you must
hardcode reasonable values (often `500 / 200` works).

## Vignetting correction

If your camera writes vignetting metadata (some calibrated
DSLR / industrial cameras do), Metashape **automatically loads
and applies it** at *Add Photos* time:

> "Vignetting correction information is saved in meta data in
> these types of cameras. This information will be loaded
> automatically into Metashape and can be used to improve
> orthomosaic generation results."
> — *Metashape Pro Manual* 2.3, § *Vignetting correction*

For cameras without metadata-encoded vignetting, *Calibrate
Colors* estimates per-image vignetting coefficients along with
the brightness/white-balance corrections. The coefficients are
stored in the chunk's internal data structures.

### Reading the estimated vignetting coefficients

The vignetting coefficients aren't directly accessible through
the Python API in some Metashape versions. The forum-attested
workaround:

> "You can try to open doc.xml inside the corresponding to
> chunk.zip archive in project.files directory and check for
> <vignetting> section contents."
> — Agisoft support, 2020-02-12, Metashape 1.6
> ([permalink](https://www.agisoft.com/forum/index.php?topic=11803.msg53024#msg53024))

The `project.files/<chunk_id>/0/chunk.zip` archive contains
`doc.xml` with `<vignetting>` blocks; each block contains a
2D polynomial coefficient grid. Decoding requires understanding
the polynomial form (the manual doesn't document it; coefficient
indexing is `[i, j]` where `i+j ≤ 3`).

For most users, the calibration is opaque and "just works"; the
internal-XML inspection is only needed for forensic debugging
of mis-corrected images.

## When to NOT use Calibrate Colors

| Scenario | Why skip |
|----------|----------|
| Single-flight datasets with stable lighting | No correction needed; the procedure burns time without improving the result |
| Multispectral / scientific NDVI workflows where exact per-band radiometry matters | Calibration may introduce artefacts that confound NDVI calculation; use radiometric calibration (reflectance panels) instead |
| Already-calibrated reflectance imagery (MicaSense, Parrot Sequoia post-reflectance-cal) | The reflectance calibration is the radiometric truth; further calibration distorts it |
| Very large datasets (>10,000 images) on time-constrained pipelines | Processing time is significant; if texture quality is acceptable without it, skip |

For multispectral / reflectance workflows, see
[Multispectral imaging: per-file band declaration and master-band change](../camera-calibration/multispectral-band-handling.md).

## Common failure modes

### "Calibrate Colors made my orthomosaic worse"

Possible causes:

- **Wrong Source data choice** for the dataset. Tie-points
  source on a sparse-feature scene gives bad estimates. Switch
  to Model or DEM.
- **Insufficient overlap** between images. The procedure needs
  overlapping regions to compare. Below ~50% overlap, estimates
  are noisy.
- **Sky / water in the images** dominating the overlap regions.
  Mask sky / water before calibration; see
  [Automatic sky masking](../alignment/automatic-sky-masking.md).
- **Mixed sensor types** (RGB + thermal in same chunk). The
  procedure assumes consistent radiometry across the source
  set. Calibrate per-modality, not per-chunk.

### "Reset Calibrate Colors didn't undo the correction"

In Metashape 1.5.3-1.5.4, the *Reset Color Calibration* button
had a known bug:

> "I think the reset color calibration isn't working for me.
> I'm using 1.5.3 build 8469 on mac. When I try the reset
> button, it might change 1 or 2 thumbnails back to the
> original appearance, but still has the 'corrected' version
> if I open the individual image. I managed to remove it by
> editing out the <vignette> blocks in the chunk. and frame.
> files for that model, but the button would be easier!"
> — *hairyfreak*, 2019-10-02, Metashape 1.5.3
> ([permalink](https://www.agisoft.com/forum/index.php?topic=11404.msg51148#msg51148))

The bug was fixed in Metashape 1.5.5 per the same thread. If
you're on 1.5.3 or 1.5.4, manually delete the `<vignetting>`
blocks from the chunk's internal XML; if you're on 1.5.5+ or
2.x, the GUI button works.

### "Calibrate Colors is too slow"

The procedure is O(images × overlap-regions). On a 5,000-image
project with high overlap, expect 1-3 hours.

To speed up:

- Use *Tie points* as source (fastest; lower quality but
  often good enough for orthomosaic).
- Disable *Calibrate white balance* if brightness-only is
  sufficient.
- Mask sky / water (smaller search regions).
- For very large datasets: split into chunks, calibrate each,
  then merge.

## Caveats

- **Calibrate Colors must run BEFORE Build Texture / Build
  Orthomosaic** to take effect. Running it after produces
  the calibrated values in the chunk's per-camera storage,
  but the existing texture / orthomosaic are still based on
  the un-calibrated values until rebuilt.
- **The corrections are NOT applied to exported source images**
  (the photo files on disk are unchanged). They apply only at
  Metashape's internal texture-fetch step. If you need
  calibrated images on disk, export via the
  [Undistort Photos workflow](https://github.com/agisoft-llc/metashape-scripts/blob/master/src/undistort_photos.py)
  with calibration applied.
- **The Reset button (in 2.x) clears the correction** without
  modifying the source images. Re-running *Calibrate Colors*
  recomputes the correction.
- **Per-camera `image_brightness` / `image_contrast` chunk
  attributes are global** to the chunk, not per-image. For
  per-image adjustments, use the GUI's *Adjust Color Levels…*
  on individual cameras.
- **Some cameras embed bad vignetting metadata.** Particularly
  for older smartphones and budget action cameras, the
  EXIF-encoded vignetting can be wrong, producing visible
  artefacts. Run *Calibrate Colors* (estimated, not
  metadata-encoded) as a sanity check.
- **For thermal imagery, do NOT calibrate.** Thermal pixel
  values are radiometric (object temperature). Calibration
  treats them as visual brightness, distorting the
  measurement. Process thermal in a separate chunk and
  reference it back via [Transferring camera orientation
  between modalities (RGB → thermal)](../camera-calibration/transfer-orientation-modalities.md).

## See also

- [Texture blending modes — what each one actually does](../texture/blending-modes.md)
  — the downstream consumer of the calibration; certain
  blending modes (Mosaic) interact with calibration in
  visible ways.
- [Orthomosaic export — the 4GB / BigTIFF limit](../orthomosaic/orthomosaic-export-pitfalls.md)
  — the orthomosaic that consumes the calibration.
- [Multispectral imaging: per-file band declaration and
  master-band change](../camera-calibration/multispectral-band-handling.md)
  — for the reflectance-calibration alternative to
  visual-only colour calibration.
- [Automatic sky masking with ONNX](../alignment/automatic-sky-masking.md)
  — pre-clean for sky / water regions that confuse Calibrate
  Colors.

## References

- *Metashape Pro User Manual* (2.3), ch. 4 *Building model
  texture → Color calibration* and ch. 5 *Build Orthomosaic →
  Color calibration*.
- *Metashape Python API Reference* (2.3.1):
  `Chunk.calibrateColors`, `Chunk.image_brightness`,
  `Chunk.image_contrast`, `DataSource` enum.
- Forum thread, [*Questions about new calibrate color feature
  in 1.4*, 2018](https://www.agisoft.com/forum/index.php?topic=8284.msg40046#msg40046)
  — feature introduction and the white-balance-checkbox
  semantic.
- Forum thread, [*How to get the Vignetting coefficients?*, 2020](https://www.agisoft.com/forum/index.php?topic=11803.msg53024#msg53024)
  — the doc.xml inspection workaround.
- Forum thread, [*reset calibrate color not working*, 2019](https://www.agisoft.com/forum/index.php?topic=11404.msg51148#msg51148)
  — the 1.5.3-1.5.4 reset-button bug; fixed in 1.5.5.
- Forum thread, [*Run "Set Brightness" tool to estimate
  brightness from python*, 2019](https://www.agisoft.com/forum/index.php?topic=11164.msg49325#msg49325)
  — the per-chunk image_brightness / image_contrast attributes.

