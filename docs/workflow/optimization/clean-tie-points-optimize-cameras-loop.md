---
title: The Clean Tie Points → Optimize Cameras loop
status: unverified
applies_to: Metashape Pro 2.0+ and Metashape Standard 2.0+. The 2.x menu label is *Clean Tie Points*; the same dialog was called *Gradual Selection* in 1.x and earlier.
edition: Standard
last_reviewed: 2026-05-22
diataxis: how-to
confidence: medium
---

# The Clean Tie Points → Optimize Cameras loop

> **Confidence:** *medium.* The iterative loop pattern is
> well-attested in forum threads dating back to PhotoScan 0.9;
> specific threshold recommendations vary by dataset and are
> heuristic. The `chunk.cleanTiePoints` and
> `chunk.optimizeCameras` API surfaces are introspection-confirmed.

## Problem

You have just run *Align Photos* and the project looks reasonable —
all cameras report aligned, the tie-point cloud has the right shape,
average reprojection error is around 1 pixel. You want to *improve*
the alignment before moving on to depth maps and meshing. What is the
canonical post-alignment cleanup workflow, and when do you stop?

## Context

After alignment, the tie-point cloud contains every point the matcher
found, including marginal points whose contribution to the bundle is
mostly noise. *Clean Tie Points* (formerly *Gradual Selection*)
selects the marginal points by a numerical criterion so you can
delete them. *Optimize Cameras* re-runs the bundle adjustment on the
remaining points. Iterating the two — clean, optimize, clean,
optimize — concentrates the bundle on the most reliable observations.

## Solution

A four-step loop, run once per criterion that needs cleaning. The
ordering and the threshold guidance below are the canonical values
from the widely-cited 2012 community workflow (insight-0001), updated for
2.x menu labels and refined with the split-threshold pattern from
insight-0008.

### The loop

1. **Crop to the area of interest.** Set the bounding box to enclose
   only the object/region you care about. Tie points outside the box
   are noise for the bundle.
2. **Clean by Reconstruction Uncertainty** *([Unverified — UV-006](../../about/unverified.md#uv-006))*. Open *Tools → Tie Points →
   Clean Tie Points…*, select *Reconstruction Uncertainty*. Drag the
   slider to a value that selects only obvious outliers — typically
   somewhere between 10 and 50. The Reconstruction Uncertainty value
   is dimensionless (a max/min variance ratio); the right cutoff
   depends on the dataset.
3. **Optimize cameras.** *Tools → Optimize Cameras*. Use the
   parameters in the box below.
4. **Clean by Reprojection Error.** Open *Clean Tie Points* again,
   select *Reprojection Error*. Drag the slider until 1 000–10 000
   points are selected (the count is shown live in the dialog).
   Aim for a slider value around **1.0** in pixel units.
5. **Optimize cameras** again with the same parameters.

If the chunk's reported *RMS reprojection error* (right-click chunk
→ *Show Info*) is still > 1.0 px after this pass, run one more
iteration. Stop after **at most 1–3 iterations of the (clean →
optimize) pair**: over-iterating produces "ripples" in subsequent
mesh reconstruction (insight-0001).

### Optimize Cameras parameter recommendations

For a typical *Frame*-camera dataset:

| Parameter | Recommendation | Why |
|-----------|----------------|-----|
| Fit f, cx, cy | **on** | Always refine principal point and focal length. |
| Fit k1, k2, k3, k4 | **on** | Standard radial distortion (Brown's model). |
| Fit p1, p2 | **on** | Tangential distortion. |
| Fit b1, b2 | **off** for most lenses | Affinity / non-orthogonality; relevant only for sensors that are non-square or non-orthogonal. |
| Fit additional corrections | **dataset-dependent** | New in 1.6. Compensates distortions the ideal Brown's model cannot represent — useful for wide-angle / fisheye, often unhelpful otherwise. Test both. |
| Adaptive camera model fitting | **off** unless you have a specific reason | Lets the bundle decide per-image which intrinsics to refine. Useful when the lens model is reliable; counter-productive while still cleaning the tie cloud. |

If your sensor is a normal square frame, *Fit Aspect* and *Fit Skew*
(legacy 1.x options) should stay off — those parameters are 0 for
such cameras and trying to fit them adds noise (insight-0001).

### Stopping rule

Stop iterating when **one of these is true**:

- The RMS reprojection error stops decreasing meaningfully between
  iterations (a delta below 0.05 px on a typical dataset).
- The tie-point count drops below ~25 % of the post-alignment count.
  Beyond that, you are deleting useful matches.
- You have done three full (clean → optimize) iteration pairs.

## Caveats and gotchas

- **The 2.x menu name is "Clean Tie Points".** Forum content
  overwhelmingly says "Gradual Selection". The dialog and slider
  behaviour are unchanged from 1.x.
- **Don't optimise away the camera model on small projects.**
  *Fit additional corrections* needs a lot of well-distributed tie
  points to estimate stably. On a 6-image *Coded targets* dataset,
  it is harmful; on a 444-image *Aerial-with-GCPs* set, it is
  usually beneficial.
- **The "Clean Tie Points" operation is destructive within the
  chunk.** Once deleted, those tie points are gone unless you
  revert. The Python API exposes a *Build Points* operation that
  rebuilds from stored matches and can reinstate previously deleted
  points; that is a different operation, covered in the Python
  article. (insight-0007.)
- **Iteration count is empirical, not theoretical.** A still-open
  question on the forum is whether running *Clean Tie Points* before
  *Optimize Cameras* actually does anything that the bundle's own
  internal thresholding does not (insight-0008). The answer in
  practice is "yes — it converges faster and produces cleaner
  numbers" but no Agisoft staff post in our corpus rigorously
  defends *why*. Treat the recipe as a useful heuristic, not a
  proof.
- **"Image Count" and "Projection Accuracy" criteria are out of
  scope here.** They have legitimate uses (filtering points seen by
  too few cameras, or with poor matched-feature accuracy), but the
  Reconstruction-Uncertainty / Reprojection-Error pair is the
  high-impact 90 % case. Cover them in a follow-up.

## Runnable demonstration on the Aerial-with-GCPs sample dataset

The Python equivalent of the GUI loop, scripted end-to-end on the
[Aerial-with-GCPs](../../reference/sample-data.md#aerial-images-with-gcps)
dataset. Loading and aligning 444 images takes a few minutes on
typical hardware; for a quicker smoke-test the
[Building](../../reference/sample-data.md#building) sample (50
images) follows the same script with no other changes.

> **Demo verified:** ✗ — pending Tier 3 reproduction on Metashape
> Pro 2.2 / 2.3 with the *Aerial-with-GCPs* (or faster *Building*)
> sample dataset. The underlying APIs are introspection-verified
> but the demo as written has not been run end-to-end. Required
> before the manual ships — particularly important for this
> article because the demo runs the full alignment + cleanup loop,
> which is the article's central claim.

```python
"""Run the Clean Tie Points → Optimize Cameras loop in Python on
the Aerial-with-GCPs sample dataset.

Workflow: download the sample, point DATASET_DIR at it, run this
script in *Tools → Run Script…*. The script prints tie-point counts
and reprojection-error before and after each iteration so you can
see the cleanup converge.
"""

import math
import os
import Metashape

DATASET_DIR = "/path/to/aerial_images_with_gcps/"   # ← adjust

OPTIMIZE_KWARGS = dict(
    fit_f=True, fit_cx=True, fit_cy=True,
    fit_k1=True, fit_k2=True, fit_k3=True, fit_k4=True,
    fit_p1=True, fit_p2=True,
    fit_b1=False, fit_b2=False,
    fit_corrections=False,
    adaptive_fitting=False,
)

def stats(chunk):
    """Tie-point count and RMS reprojection error in pixels."""
    n = 0
    err_sum_sq = 0.0
    track_to_point = {p.track_id: p for p in chunk.tie_points.points if p.valid}
    for camera in chunk.cameras:
        if camera.transform is None:
            continue
        for proj in chunk.tie_points.projections[camera]:
            point = track_to_point.get(proj.track_id)
            if point is None:
                continue
            err_sum_sq += camera.error(point.coord, proj.coord).norm() ** 2
            n += 1
    rms = math.sqrt(err_sum_sq / n) if n else 0.0
    return len(chunk.tie_points.points), rms

# 1. Load and align.
doc = Metashape.app.document
chunk = doc.chunk if doc.chunk else doc.addChunk()
photos = sorted(
    os.path.join(DATASET_DIR, f)
    for f in os.listdir(DATASET_DIR)
    if f.lower().endswith((".jpg", ".jpeg", ".tif", ".tiff", ".png"))
)
chunk.addPhotos(photos)
chunk.matchPhotos(downscale=1, generic_preselection=True,
                  reference_preselection=False, keypoint_limit=40_000,
                  tiepoint_limit=10_000, guided_matching=False,
                  filter_stationary_points=False)
chunk.alignCameras(adaptive_fitting=False)

points0, rms0 = stats(chunk)
print(f"after align:  points={points0}  rms={rms0:.4f} px")

# 2. Reconstruction Uncertainty descent (2 × t then t).
for threshold in (20.0, 10.0):
    chunk.cleanTiePoints(
        criterion=Metashape.TiePoints.Filter.ReconstructionUncertainty,
        threshold=threshold,
    )
    chunk.optimizeCameras(**OPTIMIZE_KWARGS)
    points, rms = stats(chunk)
    print(f"  RU≤{threshold:>4}:  points={points}  rms={rms:.4f} px")

# 3. Reprojection Error descent (2 × t then t).
for threshold in (2.0, 1.0):
    chunk.cleanTiePoints(
        criterion=Metashape.TiePoints.Filter.ReprojectionError,
        threshold=threshold,
    )
    chunk.optimizeCameras(**OPTIMIZE_KWARGS)
    points, rms = stats(chunk)
    print(f"  RE≤{threshold:>4}:  points={points}  rms={rms:.4f} px")
```

Expected: tie-point count drops monotonically across the four
iterations; RMS reprojection error drops too, ideally below 1.0 px
on the final pass; the GUI's *Reference* pane shows the same RMS
to ~0.001 px (insight-0012, the same formula).

If RMS stops dropping meaningfully between iterations, you are at
the natural floor for this dataset — stop early; further iterations
just carve away useful tie points (insight-0001's "ripples"
warning).

## References

- **Official manual:** *Metashape Pro User Manual*, ch. 4 "Reference
  and calibration" § "Optimization" (Pro 2.3 PDF, p. 110); the
  *Clean Tie Points* command lives in ch. 3 § "Aligning photos and
  laser scans" → "Tie Points" workflow.
- **Python Reference:** `Metashape.Chunk.optimizeCameras`,
  `Metashape.Chunk.cleanTiePoints` (GUI-equivalent helper —
  available since Metashape Pro **2.2.1**),
  `Metashape.TiePoints.Filter` (lower-level criterion-driven
  selection — `.ReprojectionError`, `.ReconstructionUncertainty`,
  `.ImageCount`, `.ProjectionAccuracy`; the `Criterion` enum was
  added in 2.2.1) — *Metashape Python API Reference*, version 2.3.1.
  On Pro 2.0–2.2.0 the lower-level pattern still works against the
  earlier `Metashape.PointCloud.Filter` class (which was renamed to
  `TiePoints.Filter` only in the 2.x rework). The article's *GUI*
  workflow itself works on Standard / Pro **2.0+**.
- **Forum:** [Pasumansky, 2012-10-18, PhotoScan 0.9](https://www.agisoft.com/forum/index.php?topic=738.msg2769#msg2769)
  — definitions of Reconstruction Uncertainty and Reprojection Error.
- **Forum:** [gEEvEE (Geert), 2012-11-15, PhotoScan 0.9](https://www.agisoft.com/forum/index.php?topic=738.msg3115#msg3115)
  — the 4-step workflow this article rests on.
- **Forum:** [Pasumansky, 2020-04-08, Metashape 1.6](https://www.agisoft.com/forum/index.php?topic=12069.msg53767#msg53767)
  — *Fit additional corrections* is a separate model, not p3/p4.
- **Forum:** [Dud3r, 2017-12-14, PhotoScan 1.4](https://www.agisoft.com/forum/index.php?topic=8140.msg38926#msg38926)
  — split-threshold descent pattern (`2 × t` then `t`).
- **Related articles:** [Diagnosing under-aligned chunks](../../workflow/alignment/diagnosing-under-aligned-chunks.md)
  — run that article's diagnostic ladder *before* running this loop;
  this loop assumes a basically-correct alignment.
- **Related feature pages:** [Gradual selection / Clean Tie Points](../../reference/features/gradual-selection.md).
- **Suggested sample datasets:** [Aerial images (with GCPs)](../../reference/sample-data.md#aerial-images-with-gcps)
  for an end-to-end walk; [Building](../../reference/sample-data.md#building)
  for a fast iteration.

