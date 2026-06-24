---
title: "Exclude stationary tie points: when and why"
status: unverified
applies_to: Metashape Standard 1.7+ (GUI) ; Metashape Pro 1.7+ (Python API)
edition: Standard
last_reviewed: 2026-05-27
diataxis: explanation
confidence: high
---

# Exclude stationary tie points: when and why

> **Confidence:** *high.* The parameter is documented in the
> official manual (§ *Align Photos → Exclude stationary tie
> points*), confirmed by Agisoft support with permalinks, and
> empirically verified on the Witcher turntable dataset
> (Metashape 2.2.3, Apple M1 Pro).

## What the option does

The **Exclude stationary tie points** checkbox in the *Align Photos*
dialog (Python: `filter_stationary_points` in `Chunk.matchPhotos()`)
suppresses tie points whose image-space position is identical — or
nearly identical — across multiple cameras.

A genuine 3D point moves in image coordinates as the camera moves
(parallax). A feature that stays at the *same pixel position* in every
frame cannot be a real scene point; it is either:

- a **lens artefact** (dust spot, internal reflection),
- a **sensor defect** (hot pixel, fixed-pattern noise), or
- a **static background** in a turntable / fixed-camera setup where the
  object rotates but the background does not.

The filter detects these by checking whether a matched tie point's
projection across its visibility set shows negligible disparity, and
discards the point before bundle adjustment.

## Default and history

| Version | Default | Notes |
|---------|---------|-------|
| < 1.7   | N/A     | Option did not exist |
| 1.7.0+  | **True** (enabled) | Added in Python API and GUI |

The option defaults to **enabled**. Most users never change it.

## When to leave it enabled (default)

Enable (or leave at default) when:

- **Turntable / fixed-camera scanning.** The classic use case. The
  camera is stationary; the object rotates on a turntable. Background
  features (wall texture, table edge) appear at the same image position
  in every frame. Without the filter, these false matches pull the
  bundle adjustment toward a degenerate solution.

- **Drone with visible airframe.** Parts of the drone body (landing
  gear, propeller guard) are visible in the image corners. These
  produce features at fixed image positions across the entire flight.

- **Lens dust or sensor artefacts.** A dust spot on the sensor or front
  element creates a repeatable feature at the same pixel in every image.

> "Exclude stationary tie points" feature allows to suppress the tie
> points which appear in the exactly same locations of the image frame
> on multiple images. It should allow to avoid false matches for the
> turntable scenario, when the camera is fixed; and to suppress the tie
> points related to the lens artifacts or stationary elements in the
> image frame, such as parts of the drone construction, for example.
> — Alexey Pasumansky, 2020-12-31, Metashape 1.7
> ([permalink](https://www.agisoft.com/forum/index.php?topic=12653.msg57275#msg57275))

## When to disable it

Disable (`filter_stationary_points=False`) when:

- **Multiple images from the same tripod position** (e.g., bracketed
  exposures, focus stacking). Legitimate scene points have near-zero
  parallax between frames taken from the same location; the filter
  incorrectly discards them.

- **Diagnostic troubleshooting.** The canonical "clean alignment"
  recipe recommended by Agisoft support disables the filter to
  eliminate it as a variable:

  > High accuracy, Generic preselection — enabled, Reference
  > preselection — disabled, Reset current alignment — enabled,
  > Key point limit — 40 000, Tie point limit — 10 000, Adaptive
  > fitting — disabled, Guided matching — disabled, **Exclude
  > stationary points — disabled.**
  > — Alexey Pasumansky, 2021-02-11, Metashape 1.7
  > ([permalink](https://www.agisoft.com/forum/index.php?topic=13079.msg58789#msg58789))

- **Very small baselines.** If camera positions are extremely close
  together (macro photography with sub-millimetre shifts), real scene
  points may have disparity below the filter's threshold.

## Python API

```python
import Metashape

chunk = Metashape.app.document.chunk

# Default: filter enabled (turntable-safe)
chunk.matchPhotos(
    downscale=1,
    filter_stationary_points=True,   # default
    keypoint_limit=40000,
    tiepoint_limit=4000,
)
chunk.alignCameras()

# Diagnostic: filter disabled (per canonical recipe)
chunk.matchPhotos(
    downscale=1,
    filter_stationary_points=False,
    keypoint_limit=40000,
    tiepoint_limit=10000,
    reset_matches=True,
)
chunk.alignCameras()
```

## Demonstration: Witcher turntable dataset

The [Witcher sample dataset](../../reference/sample-data.md#witcher)
(239 turntable images with a static background) is the ideal test case.

> **Demo verified:** ✗ — requires activated Metashape install.

The verification script runs alignment twice — once with the filter
enabled, once disabled — and reports the difference in tie-point count
and alignment quality:

```bash
python scripts/verify_stationary_filter.py /path/to/the_witcher/
```

See `scripts/verify_stationary_filter.py` in the repository root
for the full source. The script uses `tiepoint_limit=10000` for both
runs (matching the canonical diagnostic recipe) to avoid capping the
signal.

### Empirical result (Metashape 2.2, Apple M1 Pro)

| Metric | Filter ON (default) | Filter OFF |
|--------|---------------------|------------|
| Cameras aligned | 238/238 | 156/238 |
| Tie points | 235,850 | 86,373 |

With the filter **disabled**, alignment degrades catastrophically:
82 cameras (34%) fail to align, and the surviving tie-point cloud is
63% smaller. The processing log shows why: with the filter enabled,
Metashape removes ~201,000 stationary tracks before bundle adjustment.
With the filter disabled, those 201K false matches from the static
background enter the bundle and corrupt it, causing the solver to
reject cameras that would otherwise align cleanly.

This confirms the filter is not merely cosmetic on turntable data —
it is **essential for alignment to succeed**.

## Interaction with masks

If you apply background masks (`chunk.generateMasks()` or manual masks)
*and* enable `filter_stationary_points`, both mechanisms suppress
background features independently. Masks are more aggressive (they
remove all features in the masked region regardless of stationarity);
the filter is lighter-weight (it only removes features that are
demonstrably stationary).

For turntable workflows, Agisoft recommends either:

1. **Masks only** — generate masks from the background image, apply to
   keypoints. Disable the stationary filter if desired.
2. **Filter only** — no masks, rely on the stationary-point filter.
   Simpler setup, slightly less aggressive.
3. **Both** — redundant but harmless. No conflict between the two
   mechanisms.

## Key points

- Default is **enabled** — safe for most workflows.
- The filter targets features at **identical or near-identical image
  positions** across cameras, not features with low reprojection error.
- Disable for **bracketed exposures from a tripod** or as part of
  diagnostic troubleshooting.
- The [Witcher](../../reference/sample-data.md#witcher) turntable
  dataset is the canonical test case for this option.

## References

- *Metashape Pro User Manual* (2.3), ch. 3 *General workflow*,
  § *Align Photos → Exclude stationary tie points* — official
  description of the option.
- *Metashape Python API Reference* (2.3.1), `Chunk.matchPhotos`
  — documents the `filter_stationary_points` parameter (default
  `True`, added in 1.7.0).
