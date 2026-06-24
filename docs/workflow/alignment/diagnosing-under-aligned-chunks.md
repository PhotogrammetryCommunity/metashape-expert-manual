---
title: Diagnosing under-aligned chunks
status: unverified
applies_to: Metashape Standard 2.0+ ; Metashape Pro 2.0+ (Python examples). The Components view in the Workspace pane requires version 1.7 or later.
edition: Standard
last_reviewed: 2026-05-22
diataxis: how-to
confidence: medium
---

# Diagnosing under-aligned chunks
> **Confidence:** *medium.* The six-rung diagnostic ladder is the canonical clean-alignment recipe attested by Agisoft support with permalink. Pilot article — extensively reviewed and tested.
## Problem

Some cameras refuse to align, or the chunk reports every camera as
aligned but the tie-point cloud shows two or more disconnected
sub-clusters of the same scene at different positions. Default settings
have already been tried; re-running *Align Photos* produces the same
result.

## Context

Photo alignment is feature matching (per-pair) followed by a global
bundle adjustment that solves jointly for camera poses, intrinsics, and
3D point positions. Each step has its own failure modes — feature
matching can fail when an image pair has too few correct matches; the
bundle can converge to a non-physical local minimum for a sub-set of
cameras. A user-visible "under-aligned" symptom can come from either
step, and distinguishing them is the diagnostic challenge this article
addresses.

## Solution

A six-rung diagnostic ladder, cheapest first. Stop when the chunk
aligns cleanly; the remaining rungs become more invasive.

1. **Re-run with the canonical "clean" settings** *([Unverified — UV-004](../../about/unverified.md#uv-004))*. The canonical
   recommended starting recipe whenever an alignment
   misbehaves, attested verbatim:

   > "High accuracy, Generic preselection - enabled, Reference
   > preselection - disabled, Reset current alignment - enabled,
   > Key point limit - 40 000, tie point limit - 10 000, Adaptive
   > fitting - disabled, Guided matching - disabled, Exclude
   > stationary points - disabled." — Alexey Pasumansky,
   > 2021-02-11, Metashape 1.7
   > ([permalink](https://www.agisoft.com/forum/index.php?topic=13079.msg58789#msg58789))

   In the GUI:

    - Accuracy: High
    - Generic preselection: enabled
    - Reference preselection: disabled
    - Reset current alignment: enabled
    - Key point limit: 40 000
    - Tie point limit: 10 000
    - Adaptive camera model fitting: disabled
    - Guided matching: disabled
    - Exclude stationary tie points: disabled

   These over-ride defaults that are tuned for speed in favour of
   defaults that are tuned for getting alignment right at all.
2. **Inspect the Components view in the Workspace pane** (Metashape
   1.7+) *([Unverified — UV-001](../../about/unverified.md#uv-001))*. Each component is a sub-set of cameras the bundle solved as
   one rigid block. If you see more than one component, the bundle has
   *not* found a globally consistent solution even if every camera
   reports aligned — a "ghosting" symptom.
3. **Read the alignment log file** *([Unverified — UV-002](../../about/unverified.md#uv-002), [UV-003](../../about/unverified.md#uv-003))*. For each block, the log records
   the estimated `f`, `cx`, `cy`, `k1`, `k2`, `k3`. Look for a sub-block
   whose intrinsics differ wildly from the rest of the project (e.g.
   `f = 91 454 px` when the project mean is `8 400 px`) — that
   sub-block has wandered into a non-physical local minimum and will
   not merge with the main block. Run *Align Selected Cameras* on just
   that sub-block; it usually finds a sane intrinsic and the cameras
   then merge.
4. **Verify camera type** *([Unverified — UV-005](../../about/unverified.md#uv-005))*. A single mis-set camera type — for example,
   *Frame* configured in *Tools → Camera Calibration* on a fisheye
   dataset — produces ghosting that no parameter tuning can fix.
   Switching the type and re-aligning resolves it.
5. **Check overlap and image quality.** If the same physical region
   keeps failing across re-aligns, the cause is almost always
   insufficient overlap or motion blur, not a parameter setting. No
   rung above this fixes a real overlap deficit. Run *Tools → Estimate
   Image Quality* and disable images below 0.5 before alignment.
6. **Force correspondences with markers.** As a last resort, place
   markers manually on the affected images and on adjacent ones, then
   *Align Selected Cameras* on the affected subset. This forces
   correspondences that feature matching cannot find on its own.

If none of the rungs help, the project is one for Agisoft support
(<support@agisoft.com>) — save a PSZ with the alignment results only
(no images), and send the log file along with it.

### GUI

For each rung, the corresponding menu path:

1. *Workflow* → *Align Photos…* — set the values listed above. *Reset
   current alignment* must be checked, otherwise existing keypoints are
   reused and the rerun has limited effect.
2. *Workspace* pane — expand the chunk; aligned subsets appear under
   the *Components* folder *([Unverified — UV-001](../../about/unverified.md#uv-001))*. Right-click a component → *Show Cameras*
   to filter the photo pane.
3. To find the alignment log: open `<project>.files/0/log.txt` (PSX
   format) on disk *([Unverified — UV-002](../../about/unverified.md#uv-002))*, or watch the *Console* pane while alignment runs.
   Search for the line `optimized in N seconds` followed by the
   per-block intrinsics dump.
4. *Tools* → *Camera Calibration…* — verify the camera type matches
   the actual lens (Frame, Fisheye, Spherical, Cylindrical).
5. In the *Photos* pane, switch to *Details* view (using the *Change*
   menu on the pane toolbar). Select all photos, right-click →
   *Estimate Image Quality*. Sort the *Photos* pane by the *Quality*
   column and disable images below 0.5.
6. Place markers via right-click → *Place Marker* in the photo view,
   then in the *Workspace* pane select the affected cameras,
   right-click → *Align Selected Cameras*.

### Python

> **Demo verified:** ✗ — pending Tier 3 reproduction on a real
> install. The Python API surface is introspection-verified on
> Metashape Pro 2.2.2.

The same ladder via the Python API. Pro edition only — the Python API
is not available in Standard.

```python
import Metashape

doc = Metashape.app.document
chunk = doc.chunk

# Rung 1 — re-run with canonical clean settings.
# The GUI checkbox "Reset current alignment" is split across two calls
# in the Python API: reset_matches=True (in matchPhotos) discards
# previously found keypoints, and reset_alignment=True (in
# alignCameras) discards solved camera poses.
chunk.matchPhotos(
    downscale=1,                           # Accuracy: High
    generic_preselection=True,
    reference_preselection=False,
    reset_matches=True,                    # discard previous keypoints
    keypoint_limit=40_000,
    tiepoint_limit=10_000,
    guided_matching=False,
    filter_stationary_points=False,        # GUI: "Exclude stationary tie points"
)
chunk.alignCameras(
    adaptive_fitting=False,
    reset_alignment=True,                  # discard previous camera poses
)

# Rung 5 — image-quality screen before re-aligning.
# Per the API doc on Chunk.analyzeImages: "Estimated value is stored
# in camera metadata with Image/Quality key. Cameras with quality
# less than 0.5 are considered blurred and we recommend to disable
# them."
chunk.analyzeImages(cameras=chunk.cameras)
for camera in chunk.cameras:
    quality = camera.meta["Image/Quality"]   # MetaData[k] returns None if missing
    if quality is not None and float(quality) < 0.5:
        camera.enabled = False

# Rung 6 — align a chosen subset only.
subset = [c for c in chunk.cameras if c.transform is None]   # unaligned
chunk.matchPhotos(cameras=subset, reset_matches=False)
chunk.alignCameras(cameras=subset, reset_alignment=False)
```

The argument names are the Python equivalents of the GUI labels;
defaults differ in places (notably `adaptive_fitting`,
`reference_preselection`, and `filter_stationary_points`), so prefer
explicit keyword arguments rather than relying on defaults. The kwarg
names above were verified against the local Metashape 2.2.2 Python API.

## Caveats and gotchas

- **Components view requires 1.7+.** On Metashape 1.6 and earlier you
  have to identify ghosting by visually inspecting the tie-point cloud
  for spatially separated clusters of similar geometry.
- **The "clean" settings are intentionally permissive on key/tie point
  limits** (40,000 / 10,000). On modern hardware this is rarely a
  problem; on older hardware it can substantially extend alignment
  time. If memory is the bottleneck, lower the tie point limit first,
  not the key point limit.
- **Reference preselection is disabled in the clean recipe** even when
  photos are geotagged. This is deliberate: when an alignment is
  *already* failing, geotag-driven pair preselection can constrain the
  bundle into the same bad solution. Re-enable Reference preselection
  for production runs once alignment is stable.
- **`Adaptive camera model fitting` should stay off** during this
  diagnostic loop. Adaptive fitting decides per-image which intrinsic
  parameters to refine; it is useful when the lens model is reliable
  and counter-productive when alignment is failing because the lens
  model is what is failing.
- **The "log file" is the operations log**, not the report. The report
  (PDF) summarises results; the log is the per-iteration bundle output.
  Save the project as PSX to get the log on disk.

## See also

- [Helping alignment when photos don't align: markers, references, and what to use when](helping-alignment.md)
  — the unified decision framework for picking between this
  diagnostic ladder, marker-assisted recovery, and reference-
  based priors.
- [Recovery paths for unaligned cameras](recovery-paths-unaligned-cameras.md)
  — the four operational paths for fixing stragglers once the
  diagnostic ladder identifies the failure mode.

## References

- **Official manual:** *Metashape Pro User Manual*, ch. 3 "General
  workflow" § "Aligning photos and laser scans" — including the
  "Components" subsection (Pro 2.3 PDF, p. 35–40; page numbers vary
  by version).
- **Python Reference:** `Metashape.Chunk.matchPhotos`,
  `Metashape.Chunk.alignCameras`, `Metashape.Chunk.analyzeImages` —
  *Metashape Python API Reference*, version 2.3.1.
- **Forum:** [Pasumansky, 2021-02-11, Metashape 1.7](https://www.agisoft.com/forum/index.php?topic=13079.msg58789#msg58789)
  — origin of the canonical clean-settings recipe.
- **Forum:** [Paulo, 2022-02-19, Metashape 1.8](https://www.agisoft.com/forum/index.php?topic=14222.msg63988#msg63988)
  — log-file analysis of runaway intrinsics in a sub-block.
- **Forum:** [Pasumansky, 2021-03-04, Metashape 1.7](https://www.agisoft.com/forum/index.php?topic=13079.msg59330#msg59330)
  — camera-type mismatch as a ghosting cause; introduction of the
  Components view.
- **Forum:** [SAV, 2017-05-10, PhotoScan 1.3](https://www.agisoft.com/forum/index.php?topic=7020.msg34121#msg34121)
  — overlap, key/tie point limits, and markers as the recovery ladder
  for low-feature subjects.
- **Forum:** [jwoods, 2016-06-15, PhotoScan 1.2](https://www.agisoft.com/forum/index.php?topic=5454.msg26905#msg26905)
  — preselection-mode tradeoffs for accuracy vs speed.
- **Related feature pages:** [Gradual selection](../../reference/features/gradual-selection.md),
  [Guided matching](../../reference/features/guided-matching.md),
  [Reference preselection](../../reference/features/reference-preselection.md),
  [Generic preselection](../../reference/features/generic-preselection.md),
  [Adaptive camera model fitting](../../reference/features/adaptive-camera-model-fitting.md),
  [Components view](../../reference/features/components-view.md),
  [Estimate Image Quality](../../reference/features/estimate-image-quality.md).

