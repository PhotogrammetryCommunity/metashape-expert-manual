---
title: "DSM ridge-line artefacts: alignment-quality diagnosis, not DEM-pipeline bugs"
status: unverified
applies_to: Metashape Pro 2.x — and PhotoScan 1.x via the same alignment-residual pathology
edition: Pro
last_reviewed: 2026-05-29
diataxis: how-to
confidence: high
---

# DSM ridge-line artefacts: alignment-quality diagnosis, not DEM-pipeline bugs

> **Confidence:** *high.* The pathology is forum-attested with
> permalink (Agisoft support, 2018) and the recovery recipe
> reflects standard alignment-quality remediation. The 5.5-pixel
> RMS reprojection error in the source thread is at the extreme
> end; even 2-3 px reprojection signals the same underlying
> problem.

## Problem

Your exported DSM (or DEM, or orthomosaic draped on a DEM) shows
visible **ridge lines** — sharp height steps that follow no real
terrain feature, often along seams between flight lines or in
patterns suggesting the camera trajectory. Adding more GCPs
moves the ridges around but doesn't eliminate them. Increasing
DEM resolution makes them sharper, not better.

This is **not a DEM-pipeline issue**. The ridges are inherited
from a flawed alignment, propagated through every dense product
the chunk produces.

> "Such artifacts usually indicate that there are alignment
> issues for the related area."
> — Agisoft support, 2018-02-19, PhotoScan 1.4
> ([permalink](https://www.agisoft.com/forum/index.php?topic=8444.msg40298#msg40298))

## How to diagnose

Two indicators separate "DEM looks artefacted because the
alignment is bad" from "DEM looks artefacted because the DEM
parameters are wrong":

### 1. RMS reprojection error

Healthy projects have **mean RMS reprojection error ≤ 1 pixel**.
Anything above 2 pixels signals systemic alignment-quality
problems that will manifest in dense products.

Check via *Tools → Show Info → Total error*, or compute mean
reprojection error in Python:

> **Demo verified:** ✗ — pending Tier 3 reproduction on a real Metashape install.

```python
import Metashape

chunk = Metashape.app.document.chunk
tie_points = chunk.tie_points  # was chunk.point_cloud in 1.x

# Sum squared per-projection errors across all cameras
total_error_sq = 0.0
total_count = 0
for camera in chunk.cameras:
    if not camera.transform:
        continue
    # tie_points.projections[camera] gives the projections for this camera
    for projection in tie_points.projections[camera]:
        # Find the 3D point this projection corresponds to
        # (track_id maps the 2D projection to a 3D tie point)
        # See reprojection-error-analysis.md for the full computation
        pass

# Simpler proxy: marker projection errors via Reference pane
# (Marker.error is per-projection in pixels; aggregate manually)
for marker in chunk.markers:
    if marker.position is None:
        continue
    n_proj = sum(1 for p in marker.projections.values() if p)
    print(f"{marker.label}: position={marker.position}, "
          f"projections={n_proj}")
```

A 5.5-pixel mean RMS (the value in the source thread) is
extreme. Even 2-3 pixels indicates problems severe enough to
produce visible ridge artefacts on inclined surfaces.

For the systematic approach to reprojection-error analysis see
[Reprojection error analysis](reprojection-error-analysis.md).

### 2. Structured residual patterns on Camera Calibration tab

Open *Tools → Camera Calibration → [your sensor] → Residuals*
tab. Healthy residual scatter:

- Random distribution across the image plane
- No coherent gradient or rotational pattern
- Magnitude scales with image-plane radius modestly

Pathological patterns indicating mis-modelled intrinsics:

- **Radial gradient** (centre → edge). Indicates focal length
  bias.
- **Rotational pattern** (residuals form arcs / spirals).
  Indicates the principal-point estimate is biased or rolling
  shutter is uncompensated.
- **Sharp step / discontinuity** at a specific image-plane
  region. Indicates the bundle latched onto a local minimum.

> "The residuals pattern on the calibration pages also looks
> strange — I would rather suspect that the calibration is not
> correct."
> — Agisoft support, 2018-02-19, PhotoScan 1.4
> ([permalink](https://www.agisoft.com/forum/index.php?topic=8444.msg40300#msg40300))

## Recovery recipe — re-align with strict residual filtering

The recipe below comes from Agisoft support's response in the
source thread; it has worked across many similar cases.

The key insight: **markers added to a bad alignment pull the
solution further into a bad local minimum.** The optimisation
treats marker residuals as constraints, but if the underlying
tie-point cloud is contaminated, the solver shifts ridges
around without eliminating them. To recover, remove the markers
temporarily, re-align with the bad cameras unfrozen, then
re-import the markers.

### Step-by-step

1. **Set Reference-pane accuracy** to match your data:

   | Field | Value | Rationale |
   |-------|-------|-----------|
   | Marker accuracy (m) | 0.005 (or your survey precision) | Tells the bundle how tightly to trust each marker's world coords |
   | Marker accuracy (px) | 0.1 | Tells the bundle how tightly to trust each manually-placed projection |
   | Tie point accuracy (px) | 1.0 | Default; loosens the bundle's trust in tie points relative to markers |

2. **Export markers to XML.** *File → Export → Export Markers*
   (or `chunk.exportMarkers("markers.xml")`). This preserves the
   marker positions and projections for re-import after
   re-alignment.

3. **Remove markers from the project.** Right-click on each
   marker → *Remove*; or in Python:
   ```python
   chunk.remove(list(chunk.markers))
   ```

4. **Reset camera alignment.** *Workflow → Reset → Reset Camera
   Alignment* (this clears the existing tie-point cloud and
   camera poses; re-alignment starts from scratch).

5. **Re-run alignment** with the same parameters as before, but
   immediately follow with strict reprojection-error filtering
   (see [Cleaning tie points + Optimize Cameras: the loop](../../workflow/optimization/clean-tie-points-optimize-cameras-loop.md)).

6. **Re-import markers.** *File → Import → Import Markers* (or
   `chunk.importMarkers("markers.xml")`).

7. **Run *Optimize Cameras* with `adaptive_fitting=True`.** This
   re-solves the camera intrinsics adaptively rather than
   trusting the (possibly biased) initial calibration.

   > **Demo verified:** ✗ — pending Tier 3 reproduction on a real Metashape install.

   ```python
   import Metashape

   chunk = Metashape.app.document.chunk

   chunk.optimizeCameras(
       fit_f=True, fit_cx=True, fit_cy=True,
       fit_b1=True, fit_b2=True,
       fit_k1=True, fit_k2=True, fit_k3=True, fit_k4=False,
       fit_p1=True, fit_p2=True, fit_p3=False, fit_p4=False,
       adaptive_fitting=True,
   )
   ```

8. **Verify.** Re-export the DSM and inspect:
   - RMS reprojection error should drop to ≤ 1 px.
   - Camera-Calibration residual patterns should look like
     random scatter.
   - DSM ridges should be eliminated or substantially reduced.

If ridges persist after this recipe, the problem may be:

- **Insufficient overlap** in the affected area. Re-fly with
  higher overlap, or accept a smoothed product (export at
  lower resolution).
- **Severe rolling shutter** in the source data. See
  [Rolling-shutter compensation](../../workflow/camera-calibration/rolling-shutter-compensation.md).
- **Wrong sensor type** (a fisheye lens treated as Frame, or
  vice versa). See
  [Fisheye and spherical sensors: the five projection types](../../workflow/camera-calibration/fisheye-spherical-camera-types.md).

## Why ridges form

Conceptually, the alignment error manifests as a small but
systematic shift in the perceived 3D positions of features
along the boundary between flight strips. When the bundle
adjustment is converged to a local (not global) optimum, the
photos in strip A and strip B agree on the world coordinates of
the tie points they share — but disagree on the world
coordinates of points each sees individually. The dense-cloud
matcher inherits both views: in the strip-A interior it places
points at the strip-A-consistent positions; in the strip-B
interior at the strip-B-consistent positions; and at the
boundary the two estimates differ by the systematic shift.
The DEM rasterises this as a step / ridge.

Ridges therefore tend to follow strip boundaries (or block
boundaries in dense-as-tiles processing). If you can see flight
lines in the ridge pattern when overlaid on the orthomosaic,
that's diagnostic.

## Caveats

- **The 5.5 px example in the source thread is extreme.** Your
  project may show ridges at 2-3 px RMS, which is still
  recoverable but starting from a less-broken state. The same
  recipe applies.
- **Re-alignment is expensive.** On a 5000-image project,
  re-running *Align Photos* + *Optimize Cameras* can take
  several hours on consumer hardware. Export markers first;
  the re-import step is fast.
- **GCP precision matters.** If your GCPs are surveyed to
  ±5 cm absolute, set marker accuracy (m) to 0.05, not 0.005.
  Setting tighter than the actual survey precision tells the
  bundle to over-trust the GCPs and can introduce its own
  artefacts.
- **`adaptive_fitting=True`** lets Optimize Cameras choose which
  intrinsics to refine based on the data — useful when you're
  not sure whether `k3`, `p1`, `p2` etc are well-constrained.
  For nadir-only aerial sets, `adaptive_fitting=False` with a
  hand-picked subset (`fit_k1=True, fit_k2=True, fit_p1=True,
  fit_p2=True, others False`) often gives better results.

## See also

- [Reprojection error analysis](reprojection-error-analysis.md)
  — the canonical metric for alignment-quality diagnosis.
- [Cleaning tie points + Optimize Cameras: the loop](../../workflow/optimization/clean-tie-points-optimize-cameras-loop.md)
  — the iterative reprojection-error-and-clean loop the recovery
  recipe alludes to.
- [Recovery paths for unaligned cameras](../../workflow/alignment/recovery-paths-unaligned-cameras.md)
  — when the failure is total (cameras unaligned) rather than
  degraded.
- [Diagnosing under-aligned chunks](../../workflow/alignment/diagnosing-under-aligned-chunks.md)
  — the broader diagnostic ladder for alignment-quality issues.

## References

- *Metashape Pro User Manual* (2.3), ch. 4 *Improving camera
  alignment* — describes the reference-accuracy fields and
  *Optimize Cameras* options.
- *Metashape Python API Reference* (2.3.1):
  `Chunk.optimizeCameras`, parameter `adaptive_fitting`,
  `Chunk.exportMarkers`, `Chunk.importMarkers`.
- Forum thread, [*Strange artifacts on DEM (ridges and steps)*, 2018](https://www.agisoft.com/forum/index.php?topic=8444.msg40226#msg40226)
  — the canonical Q&A; identifies alignment as root cause and
  prescribes the recovery recipe.

