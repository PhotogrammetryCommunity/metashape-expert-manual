---
title: What's new
---

# What's new

A reader-facing history of changes to the manual, newest first.
The list of entries is generated from the manual's revision
history (`scripts/gen_changelog.py`); the one-line description
after each entry is written by hand and preserved when the list
is regenerated.

## September 2026

**Updated**

- [`chunk.transform.matrix` is local→world; `camera.transform` is local](../topics/crs/chunk-frame-vs-camera-frame.md) — Cross-linked the KB's Python coordinate-system recipes (EPSG / WKT / .prj / geoid / convert).
- [`mask_tiepoints` cross-view propagation and the foreground-occluder case](../workflow/alignment/mask-tiepoints-cross-view.md) — Noted the 2.3.1 regression where `chunk.mask_sets`/`masks` read empty after assigning `camera.mask` (fixed in 2.3.2).
- [Calibration groups: programmatic management in Python](../workflow/camera-calibration/calibration-groups-management.md) — Cross-linked the KB's GUI method for creating and splitting calibration groups.
- [Choosing camera axes: aerial vs terrestrial (and YPR vs OPK)](../topics/scripting/choosing-rotation-representation.md) — Hardened the `sensor.axes` `.psz` caveats — the serialization bug is confirmed still present in 2.3.2 (build 22956).
- [Coded circular targets: printing, sizing, and choosing a variant](../workflow/markers-gcps/coded-circular-targets.md) — Linked the KB's non-coded-target detection workflow from the non-coded section.
- [Declaring a fixed-geometry multi-camera rig in Python](../workflow/camera-calibration/multi-camera-rig-python.md) — Documented the 2.3 slave-offset rotation-direction flip (use `mat2opk(R.transpose())` on >= 2.3.0), verified still present in 2.3.2.
- [DEM build options: point cloud vs mesh as source, and the interpolation knob](../workflow/dem/build-options.md) — Added a Python `chunk.buildContours` section (the KB documents only the GUI).
- [Reference preselection](../reference/features/reference-preselection.md) — Trimmed the mode descriptions now covered by the KB and linked it; kept the Sequential-window and two-stage material.
- [Scripting context pitfalls: GUI vs command-line, document handles, and stage validation](../topics/scripting/scripting-context-pitfalls.md) — Added the 2.3.1 `==`/`None` interpreter-abort pitfall (fixed in 2.3.2; use `is` / `.key`).
- [The slave-sensor transform: composition rule, axis convention, and recipes](../workflow/camera-calibration/slave-sensor-transform-recipes.md) — Cross-linked the 2.3 slave-offset rotation-direction flip caveat.
- [Version timeline](../reference/version-timeline.md) — Added 2.3.2 (build 22956) point-release detail and per-bug status.

## August 2026

**New articles**

- [Choosing camera axes: aerial vs terrestrial (and YPR vs OPK)](../topics/scripting/choosing-rotation-representation.md) — Why terrestrial capture should use OPK reference angles today: the YPR gimbal-lock problem, the Sensor.axes fix, and the 2.3.1 .psz bug that keeps OPK the safe choice.

**Updated**

- [`chunk.transform.matrix` is local→world; `camera.transform` is local](../topics/crs/chunk-frame-vs-camera-frame.md) — Added a link to *Choosing camera axes*.
- [AprilTag detection — choosing a variant](../workflow/markers-gcps/apriltag-detection.md) — Trimmed the Context, moved the variant definitions beside the table, wrapped the confidence callout, and signposted the occlusion-robustness explanation.
- [Bundle-adjustment quality: variance factor, overfit testing, and reference detectability](../topics/repeatability-qa/bundle-adjustment-quality.md) — Added the per-observation a-priori σ column and a measured variance-factor benchmark, and clarified that the tie-point σ is per-projection (`tiepoint_accuracy × keypoint size`).
- [Camera reference error: computing per-camera location and orientation residuals in Python](../topics/repeatability-qa/camera-reference-error-python.md) — Added a link to *Choosing camera axes*.
- [Coded circular targets: printing, sizing, and choosing a variant](../workflow/markers-gcps/coded-circular-targets.md) — Merged the family-selection tables into one decision section, moved the marker-pool and binary-code tables into a reference appendix, shortened the title, and signposted the explanatory sections.
- [Drone metadata: DJI altitude semantics and RTK XMP accuracy tags](../workflow/project-setup/dji-drone-metadata.md) — Added a link to *Choosing camera axes*.
- [Fixing exterior orientation: skipping Align Photos with known EO](../workflow/project-setup/external-orientation-import.md) — Added a link to *Choosing camera axes*.
- [Gray flags in marker detection: what they mean and how to remove them](../workflow/markers-gcps/gray-flags-marker-detection.md) — Updated the coded circular targets cross-link label.
- [Helping alignment when photos don't align: markers, references, and what to use when](../workflow/alignment/helping-alignment.md) — Updated the coded circular targets cross-link label.
- [Importing camera orientation: EXIF, omega-phi-kappa, and yaw/pitch/roll](../workflow/project-setup/importing-camera-orientation.md) — Added a link to *Choosing camera axes*.
- [Keypoint-size-normalised reprojection error: the `kps` metric](../topics/repeatability-qa/keypoint-size-error-metric.md) — Verified the per-projection tie-point weighting (σ = `tiepoint_accuracy × proj.size`) empirically, promoted the article to verified, and repaired its front matter.
- [Programmatic marker placement and pinning](../workflow/markers-gcps/programmatic-marker-placement.md) — Updated the coded circular targets cross-link label.
- [Saving estimated reference values to file: location, rotation, error, and sigma](../topics/repeatability-qa/save-estimated-reference.md) — Added a link to *Choosing camera axes*.
- [Tightening reference accuracies after `alignCameras`: when the similarity-transform residual isn't enough](../workflow/optimization/tightening-reference-accuracies.md) — Added a link to *Choosing camera axes*.
- [YPR rotation conventions: `ypr2mat` vs `camera.reference.rotation`](../topics/scripting/ypr-rotation-conventions.md) — Added an inline link to *Choosing camera axes* at the OPK caveat.

## July 2026

**Updated**

- [Orthomosaic export — the 4GB / BigTIFF limit and shift-during-export](../workflow/orthomosaic/orthomosaic-export-pitfalls.md) — Added a hedged caveat on disabled cameras and seamline regeneration during export.
- [Reference preselection](../reference/features/reference-preselection.md) — Documented the measured sequential-preselection window and added a verification script.
