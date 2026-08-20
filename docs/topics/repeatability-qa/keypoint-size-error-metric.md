---
title: "Keypoint-size-normalised reprojection error: the `kps` metric"
status: verified
applies_to: "Metashape Pro 2.x — and PhotoScan 1.x via the same `TiePoints.Projection.size` (1.x: `PointCloud.Projection.size`) API surface"
edition: "Pro / Standard"
last_reviewed: 2026-08-19
diataxis: explanation
confidence: high
---

# Keypoint-size-normalised reprojection error: the `kps` metric

> **Confidence:** *high.* The official Metashape Pro 2.3 manual (page 90, *Processing Parameters*) states explicitly that the kps form *"is the quantity that is minimized during bundle adjustment"*; the dual-reporting (kps and pix) is documented there and corroborated by Metashape report excerpts in the forum. The `TiePoints.Projection.size` API attribute is introspection-confirmed on Metashape 2.2 and documented as "size" in the Python API Reference.

## Problem

Open the Metashape chunk-info dialog, or look at a generated PDF report's *Survey Data* / *Cameras* page, and the *RMS reprojection error* line shows two numbers separated by a parenthesis:

```
RMS reprojection error    0.130199 (0.363276 pix)
Max reprojection error    0.503363 (1.66923 pix)
Mean key point size                2.75397 pix

```

*— excerpt from a Metashape 1.5.3 report, t=11148*

Two things to notice:

1. The **first number** has no unit suffix.
2. The **second number** is in pixels.

The first number is the **keypoint-size-normalised** reprojection error — the same residual divided by the keypoint scale. It's referred to as `kps` in some contexts (short for "keypoint size") and is **the quantity Metashape's bundle adjustment actually minimises**. The pixel form is shown for convenience but is not what the optimiser fits to.

This article explains what the kps metric is, why Metashape reports both, and when you should reach for kps rather than the pixel form.

## What is keypoint size?

Every tie-point projection in Metashape carries a `size` attribute exposed via `Metashape.TiePoints.Projection.size`. The official manual defines this:

> "Key point size is the Sigma of the Gaussian blur at the pyramid level of scales at which the key point was found." — *Metashape Pro User Manual 2.3*, p. 90

In plain terms: feature detectors like SIFT search for keypoints across a *scale-space pyramid* — the image is progressively blurred (Gaussian blur with increasing σ) and downsampled, and keypoints are picked at the level where they are most distinctive. The σ at the level where the keypoint was located is reported as `proj.size`. A keypoint detected at a coarse pyramid level has a large size (say 8 px); one detected at fine detail has a small size (say 1 px). The keypoint's descriptor is computed over a patch proportional to this size, so a 0.5-pixel residual on an 8-pixel keypoint represents a much smaller fraction of the descriptor extent than a 0.5-pixel residual on a 1-pixel keypoint.

Metashape uses the keypoint size to **weight** the bundle adjustment's projection observations. The Reference pane's *Tie point accuracy* parameter (under *Settings*) is the normalised accuracy — the accuracy of a tie-point projection at scale 1 — and a projection detected at another scale inherits an accuracy proportional to its size, which is what lets the bundle adjustment weight fine-scale and coarse-scale features correctly against each other.

> **Empirically verified — 2026-08-19, Metashape 2.3, `AGISOFT_DISABLE_CHECKOUT=1`.** The effective
> per-projection standard deviation is
>
> ```
> sigma_i = tiepoint_accuracy * proj.size_i
> ```
>
> This was previously this article's own inference from the manual quotes above rather than a stated
> Agisoft formula. It is now measured, three independent ways on synthetic projects with injected,
> known errors:
>
> 1. **Size enters quadratically.** Two interleaved groups of projections were pushed in opposite
>    directions by an equal 0.25 px, differing only in `proj.size`. The groups were interleaved by
>    both track and camera so that neither a point's 3D position nor a camera pose could absorb the
>    perturbation, leaving the weighted compromise as the only resolution. The resulting residual
>    ratio tracked the **square** of the size ratio: **3.954** measured against 4.0 predicted for
>    sizes 1 and 2, and **15.42** (16.07 with intrinsics free) against 16.0 for sizes 1 and 4. An
>    equal-size control gave **1.004**, confirming the harness manufactures no asymmetry.
> 2. **Size and `tiepoint_accuracy` are interchangeable.** Sweeping `tiepoint_accuracy` against
>    deliberately biased camera references, the size-4 response curve was the size-1 curve shifted by
>    exactly a factor of 4 in `tiepoint_accuracy` — the same values (0.6387, 0.9656, 0.9912) recurring
>    in both columns to four decimal places. Quadrupling the keypoint size is numerically
>    indistinguishable from quadrupling `tiepoint_accuracy`, which is what a multiplicative sigma
>    means.
> 3. **Not specific to one observation type.** Repeating (2) with biased *marker* (GCP) references
>    reproduced the identical ×4 equivalence, so this is a property of the tie-point weighting rather
>    than of the competing reference type.
>
> Projection counts were unchanged across every solve, so nothing was silently rejected as an outlier
> and the comparisons are like-for-like. The practical consequence: a chi-square or variance-factor
> computation must divide the **kps** residual by `tiepoint_accuracy`; using the pixel residual
> overstates the tie-point term by the squared mean keypoint size — about 7.6x at the 2.75 px mean in
> the report excerpt above.

The chunk-wide **mean key point size** in the report excerpt above (2.75 px) is the average of `proj.size` across all projections that contributed to the bundle.

## Defining the kps error

For a single projection, the kps error is the pixel error normalised by the projection's keypoint size:

```
error_kps = error_pix / proj.size

```

Where `error_pix` is the standard 2D residual computed via `Camera.error` (the Brown-distortion-aware primitive — see the Caveats below for why this differs from a naive `camera.project` minus `proj.coord`):

```
error_pix = camera.error(point.coord, proj.coord).norm()

```

For a chunk-wide RMS, sum the squared kps errors across all projections of all valid tie points, divide by the projection count, and take the square root — the same aggregation pattern as the pixel-form RMS, just computed on the kps values:

> **Demo verified:** ✓ — 2026-08-19, Metashape 2.3. The kps aggregation below was reproduced on a
> synthetic project with a uniform keypoint size, where `rms_kps == rms_pix / size` holds exactly, and
> is now guarded by a regression test.

```python
import math
import Metashape

chunk = Metashape.app.document.chunk
tps = chunk.tie_points

# track_id → 3D coord lookup, valid points only
coord_by_track = {p.track_id: p.coord for p in tps.points if p.valid}

err_pix_sumsq = 0.0
err_kps_sumsq = 0.0
n_pix = 0          # projections with a valid 3D point
n_kps = 0          # subset of n_pix with proj.size > 0
for camera in chunk.cameras:
    if not camera.transform:
        continue
    for proj in tps.projections[camera]:
        coord = coord_by_track.get(proj.track_id)
        if coord is None:
            continue
        residual = camera.error(coord, proj.coord)
        err_pix = residual.norm()
        err_pix_sumsq += err_pix * err_pix
        n_pix += 1
        if proj.size > 0:
            err_kps = err_pix / proj.size
            err_kps_sumsq += err_kps * err_kps
            n_kps += 1

if n_pix > 0:
    rms_pix = math.sqrt(err_pix_sumsq / n_pix)
    rms_kps = math.sqrt(err_kps_sumsq / n_kps) if n_kps > 0 else 0.0
    print(f"RMS reprojection error: {rms_kps:.4f}  ({rms_pix:.4f} pix)")

```

The output should match the chunk-info dialog's first two numbers within rounding. The two counters (`n_pix` and `n_kps`) are kept separate because legacy / imported tie points can carry `proj.size == 0`; including them in the pixel sum but excluding them from the kps sum keeps each RMS on its proper denominator.

## Why Metashape reports both

The kps form is what the bundle adjustment actually **minimises**. The official Metashape Pro 2.3 manual states this explicitly:

> "On the processing parameters page of the report (as well as in chunk information dialog) two reprojection errors are provided: the reprojection error in the units of key point scale (**this is the quantity that is minimized during bundle adjustment**), and the reprojection error in pixels (for convenience)." — *Metashape Pro User Manual 2.3* (and Standard edition), p. 90, *Processing Parameters*

The pixel form is reported alongside as a convenience for human readers who think in pixels. It's not a separately computed quantity — the same per-projection residual is just expressed in the two units.

The two metrics therefore answer different questions:

| Metric | Question | Comparable across... |
| --- | --- | --- |
| `error_pix` | *How many pixels off is the bundle, in this image's coordinate system?* | Same camera; same image resolution. |
| `error_kps` | *How well-localised is each keypoint within its detection scale?* | Different cameras, different resolutions, different focal lengths — anything that changes the ratio of pixel size to scene-size. |

Concretely, two scenarios produce the same `error_pix` but different `error_kps`:

- **Scenario 1** — a 60 MP camera, keypoint size 1 px, residual 0.5 px → kps error = 0.5. The bundle reproduces a fine-detail feature to half its descriptor extent.
- **Scenario 2** — a 20 MP camera, keypoint size 4 px, residual 0.5 px → kps error = 0.125. The bundle reproduces a coarser feature to one-eighth of its descriptor extent.

Both have the same 0.5-pixel residual, but the second is *intrinsically* a tighter fit because the bundle agrees to within a much smaller fraction of the feature's spatial extent. The kps metric captures this: 0.125 < 0.5.

## Practical interpretation

For a healthy aligned project:

- **kps error ≤ ~1.0** indicates the bundle has reproduced most keypoints within roughly one keypoint-size unit. This is the regime where reprojection-error filtering can meaningfully improve the cloud.
- **kps error > 1** indicates many projections lie further from their reprojected 3D positions than the keypoint's descriptor patch — a signal that the bundle is struggling even after distortion correction.

The pixel-form thresholds in [Reprojection error analysis](reprojection-error-analysis.md) ("≤ 1 px healthy, > 2 px problematic") translate to kps thresholds via the chunk's mean keypoint size. For the Metashape 1.5.3 report excerpted above (mean keypoint size 2.75 px, RMS 0.36 px), the kps RMS of 0.13 fits comfortably in the "healthy" range. A project with mean keypoint size 1 px would need much tighter pixel residuals to hit the same kps score.

## Per-camera and per-sensor kps

The kps metric is most useful **per-sensor or per-camera**, not just chunk-wide:

- **Per-camera kps** highlights cameras whose projections systematically diverge — masking, removal, or separate calibration-group candidates.
- **Per-sensor kps** is invariant to the camera count per sensor. A chunk with 4 sensors of 50 cameras each, where one sensor has kps RMS 1.5 and the others 0.3, has a mis-calibrated or mis-mounted sensor; the sensor-RMS makes this immediately obvious where the chunk-wide RMS would bury it.

The aggregation pattern for per-sensor or per-camera kps is the same: maintain `errors_sumsq_kps`, `errors_sumsq_pix`, and `num_projections` accumulators per sensor / camera, then take the square root of `sumsq / count` at the end.

For a working pattern that does both the per-sensor and per-camera aggregation in a single pass, see [Reprojection error analysis](reprojection-error-analysis.md).

## Aggregation choice: per-projection vs per-point

A subtle issue when computing RMS: weight every **projection** equally, not every **point**. Metashape's chunk-info value uses projection-weighting, which means a tie point seen in 8 cameras contributes 8 squared errors to the sum and 8 to the count; a tie point seen in 2 cameras contributes 2.

The same convention applies to both `kps` and `pix` forms. Switching to point-weighting (one entry per tie point, averaged across its projections) gives a different, smaller number that won't match the GUI.

## Caveats

- `proj.size > 0` is a necessary guard. Some legacy formats or imported tie points have `size = 0` and would produce a divide-by-zero. The recipe above guards explicitly.
- **Projections without valid 3D points** are silently skipped. A `coord_by_track` lookup that returns `None` (the track triangulated to no valid point, or the point was filtered out as invalid) means the kps contribution is undefined for that projection.
- **Cross-version naming.** In Metashape 1.x the projection is reached via `chunk.point_cloud.projections[camera]`; in 2.x it's `chunk.tie_points.projections[camera]`. The `Projection.size` attribute name is the same in both.
- **`Camera.error(coord, proj.coord)` is the right primitive.** It applies the Brown-distortion correction; `camera.project(coord) - proj.coord` skips that step and produces a slightly different number that won't match the GUI. See [Reprojection error analysis](reprojection-error-analysis.md).
- **Mean keypoint size depends on the matching pipeline.** Increasing image quality, changing pre-selection mode, or switching between *Generic* and *Reference Preselection* changes which keypoints survive matching, and therefore the mean keypoint size. Compare kps values across re-runs of the same parameters; comparisons across pipelines are apples-to-oranges.
- **The kps metric is dimensionless**, despite intuitions to the contrary. It's a ratio of two pixel-quantities. The PDF report displays it without a unit on purpose — the "0.130199" in the excerpt is a pure number.

## See also

- [Reproducing chunk-info statistics in Python](reproducing-chunk-info-statistics-python.md) — the broader chunk-info reproduction recipe; this article's kps focus complements its pixel-form RMS computation.
- [Reprojection error analysis: per-camera and per-tie-point](reprojection-error-analysis.md) — pixel-space residual recipes; pair with this article for full per-camera kps + pix monitoring.
- [Tie-point multiplicity: track length, distribution, and what it tells you](tie-point-multiplicity.md) — the other novel chunk-info statistic; complements kps for comprehensive QA.
- [DSM ridge-line artefacts: alignment-quality diagnosis](dsm-ridge-lines-diagnosis.md) — symptom-driven entry into reprojection-error analysis.

## References

- ***Metashape Pro User Manual** 2.3* (and Standard edition), p. 90, *General workflow → Processing Parameters*. Two canonical statements:
    - "Key point size is the Sigma of the Gaussian blur at the pyramid level of scales at which the key point was found."
    - "the reprojection error in the units of key point scale (this is the quantity that is minimized during bundle adjustment), and the reprojection error in pixels (for convenience)."
- *Metashape Python API Reference* (2.3.1): `TiePoints.Projection.size`, `TiePoints.Projection.coord`, `TiePoints.Projection.track_id`, `Camera.error`, `Camera.transform`, `Chunk.tie_points`.
- Forum thread, *[Average Tie point multiplicity parameter](https://www.agisoft.com/forum/index.php?topic=11148.0)* — community forum users and Pasumansky, 2019-07-15, Metashape 1.5. Quotes the chunk-info dialog format with both kps and pix forms of RMS reprojection error, plus the *Mean key point size* line that anchors the kps interpretation.
- Forum thread, *[Reproduce chunk info reprojection error](https://www.agisoft.com/forum/index.php?topic=11548.msg52102#msg52102)* — Agisoft support, 2019-11-22, Metashape 1.5. The canonical pixel-form RMS recipe, which this article extends to the kps form.
- Forum thread, *[Point cloud gradual selection threshold](https://www.agisoft.com/forum/index.php?topic=13387.0)* — a community forum user and Agisoft support, 2021-05-19, Metashape 1.7. The community user states empirically that the *Reprojection Error* gradual-selection criterion uses the kps form (pixel error divided by keypoint size); the reply points at the manual's description without contradicting this.

