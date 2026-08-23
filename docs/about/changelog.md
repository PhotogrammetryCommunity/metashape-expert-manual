---
title: What's new
---

# What's new

A reader-facing history of changes to the manual, newest first.
The list of entries is generated from the manual's revision
history (`scripts/gen_changelog.py`); the one-line description
after each entry is written by hand and preserved when the list
is regenerated.

## August 2026

**New articles**

- [Choosing camera axes: aerial vs terrestrial (and YPR vs OPK)](../topics/scripting/choosing-rotation-representation.md) — Why terrestrial capture should use OPK reference angles today: the YPR gimbal-lock problem, the Sensor.axes fix, and the 2.3.1 .psz bug that keeps OPK the safe choice.

??? note "Updated — 15 articles"

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

## June 2026

??? note "New articles — 125 articles"

    - [`alignChunks(method=point)` cannot break geometric symmetry](../workflow/alignment/alignchunks-symmetric-scene-failure.md)
    - [`camera.project` and `camera.unproject`: 2D ↔ 3D in Python](../topics/scripting/camera-project-unproject.md)
    - [`chunk.transform.matrix` is local→world; `camera.transform` is local](../topics/crs/chunk-frame-vs-camera-frame.md)
    - [`exportPointCloud` defaults: GUI vs Python CRS difference](../workflow/export-reporting/exportpoints-crs-default.md)
    - [`filter_mask=True` starves `matchPhotos` when masks cover most of the image](../workflow/alignment/filter-mask-starvation.md)
    - [`mask_tiepoints` cross-view propagation and the foreground-occluder case](../workflow/alignment/mask-tiepoints-cross-view.md)
    - [`mergeChunks` does not deduplicate cameras](../workflow/chunks/no-camera-deduplication.md)
    - [`Model.renderDepth`: synthetic depth rendering from arbitrary viewpoints](../topics/scripting/model-render-depth.md)
    - [`sensor.calibration` vs `sensor.user_calib` — initial vs adjusted values](../workflow/camera-calibration/sensor-calibration-vs-user-calib.md)
    - [Adaptive camera model fitting](../reference/features/adaptive-camera-model-fitting.md)
    - [Adding cameras to an aligned chunk: the `keep_keypoints` workflow](../workflow/alignment/incremental-matching-keep-keypoints.md)
    - [Agisoft knowledge base](../reference/agisoft-knowledge-base.md)
    - [AI-assisted mask generation](../workflow/alignment/ai-mask-generation.md)
    - [Aligning two meshes / point clouds: model-to-model registration in Python](../topics/scripting/aligning-models-and-clouds.md)
    - [Applying *Patch* on multiple shapes (orthomosaic patching by script)](../workflow/orthomosaic/applying-patch-multiple-shapes.md)
    - [AprilTag detection — choosing a variant](../workflow/markers-gcps/apriltag-detection.md)
    - [Area and volume measurement: Model view vs DEM, Shapes vs cropping](../workflow/orthomosaic/area-volume-measurement.md)
    - [Auto-export per-shape: orthomosaic, DEM, point cloud, mesh, KMZ](../workflow/export-reporting/auto-export-per-shape.md)
    - [Automatic sky masking with ONNX: pre-clean for sky-prone aerial captures](../workflow/alignment/automatic-sky-masking.md)
    - [Automating gradual selection in Python](../workflow/scripting-automation/automating-gradual-selection-python.md)
    - [Bundle-adjustment quality: variance factor, overfit testing, and reference detectability](../topics/repeatability-qa/bundle-adjustment-quality.md)
    - [Calibration groups: programmatic management in Python](../workflow/camera-calibration/calibration-groups-management.md)
    - [Camera reference error: computing per-camera location and orientation residuals in Python](../topics/repeatability-qa/camera-reference-error-python.md)
    - [Camera stations: when to use them and the nodal-head requirement](../workflow/project-setup/camera-stations-nodal-head.md)
    - [Change Path: swapping image format / resolution after alignment](../workflow/project-setup/change-path-and-export-coords.md)
    - [Choosing the master sensor in a multi-camera layout](../workflow/camera-calibration/choosing-master-sensor-multi-camera-layout.md)
    - [Choosing which camera parameters to fix or optimize](../workflow/camera-calibration/choosing-camera-parameters.md)
    - [Coded circular targets: printing, sizing, and choosing a variant](../workflow/markers-gcps/coded-circular-targets.md)
    - [Color calibration: when to use it, what it does, and the white-balance / vignetting knobs](../workflow/texture/color-calibration.md)
    - [Comparing chunks for change detection: DEM, mesh, and point-cloud diff workflows](../topics/scripting/chunk-diff-volume-workflows.md)
    - [Components view](../reference/features/components-view.md)
    - [Computing camera direction vectors and look-at points in Python](../topics/scripting/camera-direction-vectors.md)
    - [Computing per-camera coverage area (image footprint on the model)](../topics/scripting/computing-camera-coverage-area.md)
    - [Contributing](../about/contributing.md)
    - [Converting `camera.transform` to ENU (or any local Cartesian)](../topics/scripting/camera-poses-to-enu.md)
    - [Creating point shapes programmatically: grid placement with DEM-based elevation](../topics/scripting/creating-point-shapes-from-dem.md)
    - [Custom vertical datums: adding a geoid undulation grid](../workflow/project-setup/custom-geoid-vertical-datum.md)
    - [Declaring a fixed-geometry multi-camera rig in Python](../workflow/camera-calibration/multi-camera-rig-python.md)
    - [DEM build options: point cloud vs mesh as source, and the interpolation knob](../workflow/dem/build-options.md)
    - [Depth-map quality and filter modes: choosing parameters for Build Point Cloud](../workflow/depth-maps/depth-map-quality-and-filter-modes.md)
    - [Diagnosing CUDA / OpenCL errors: timeouts, OOM, kernel failures](../topics/performance/diagnosing-cuda-opencl-errors.md)
    - [Diagnosing under-aligned chunks](../workflow/alignment/diagnosing-under-aligned-chunks.md)
    - [Diagnostic mesh visualisation: colorize by overlap or altitude](../topics/scripting/colorize-mesh-diagnostics.md)
    - [Drone metadata: DJI altitude semantics and RTK XMP accuracy tags](../workflow/project-setup/dji-drone-metadata.md)
    - [DSM ridge-line artefacts: alignment-quality diagnosis, not DEM-pipeline bugs](../topics/repeatability-qa/dsm-ridge-lines-diagnosis.md)
    - [Estimate image quality](../reference/features/estimate-image-quality.md)
    - [Exclude stationary tie points: when and why](../workflow/alignment/stationary-point-filter.md)
    - [EXIF focal length: which tags Metashape reads, and the no-crop-factor rule](../workflow/camera-calibration/exif-focal-length-estimation.md)
    - [Exporting cameras for Gaussian Splatting / Colmap downstream pipelines](../workflow/export-reporting/colmap-export-for-3dgs.md)
    - [Exporting depth maps from Python (32-bit, scaled)](../workflow/depth-maps/exporting-depth-maps-python.md)
    - [Exporting to Cesium 3D Tiles: point cloud vs tiled model](../workflow/orthomosaic/exporting-cesium-tiled-models.md)
    - [Filtering cameras by tie-point selection: which photos see this 3D point?](../topics/scripting/filter-cameras-by-tie-points.md)
    - [Fisheye and spherical sensors: the seven projection types and when each applies](../workflow/camera-calibration/fisheye-spherical-camera-types.md)
    - [Fixing exterior orientation: skipping Align Photos with known EO](../workflow/project-setup/external-orientation-import.md)
    - [Generic preselection](../reference/features/generic-preselection.md)
    - [Glossary](../reference/glossary.md)
    - [Gradual selection](../reference/features/gradual-selection.md)
    - [Gray flags in marker detection: what they mean and how to remove them](../workflow/markers-gcps/gray-flags-marker-detection.md)
    - [Ground classification: the erosion radius parameter](../workflow/point-cloud/ground-classification-erosion-radius.md)
    - [Guided matching](../reference/features/guided-matching.md)
    - [Helping alignment when photos don't align: markers, references, and what to use when](../workflow/alignment/helping-alignment.md)
    - [How Metashape computes vertex normals on model export](../workflow/mesh/vertex-normal-computation.md)
    - [Importing camera orientation: EXIF, omega-phi-kappa, and yaw/pitch/roll](../workflow/project-setup/importing-camera-orientation.md)
    - [Intel i9-13900K / 14900K instability: BIOS workarounds for Metashape crashes](../topics/hardware-io/intel-13900k-14900k-instability.md)
    - [Keypoint-size-normalised reprojection error: the `kps` metric](../topics/repeatability-qa/keypoint-size-error-metric.md)
    - [Linux vs Windows: 10–40% faster processing](../topics/performance/linux-vs-windows-performance.md)
    - [Logging from Metashape Python scripts (and why `app.settings.log_*` does not work for headless scripts)](../workflow/scripting-automation/logging-from-python-scripts.md)
    - [Mapping orthomosaic pixels back to source images](../topics/scripting/orthomosaic-pixel-to-source-image.md)
    - [Marker projection statistics: counts, per-marker errors, and metre-vs-pixel framing](../topics/repeatability-qa/marker-projection-statistics.md)
    - [Mesh and point-cloud editing recipes (Python)](../topics/scripting/mesh-pointcloud-editing-recipes.md)
    - [Mesh surface types: Arbitrary vs Height field, and the source-data choice](../workflow/mesh/mesh-surface-types.md)
    - [Metashape's distortion model and converting to OpenCV / Colmap](../workflow/camera-calibration/distortion-model-opencv-colmap.md)
    - [Multi-GPU setups: SLI, TCC mode, and utilization](../topics/performance/multi-gpu-utilization.md)
    - [Multispectral imaging: per-file band declaration and master-band change](../workflow/camera-calibration/multispectral-band-handling.md)
    - [Network processing: setup, monitoring, and common failure modes](../workflow/network-processing/network-processing-setup.md)
    - [Orthomosaic export — the 4GB / BigTIFF limit and shift-during-export](../workflow/orthomosaic/orthomosaic-export-pitfalls.md)
    - [Orthomosaic in a marker-defined planar projection](../workflow/orthomosaic/marker-defined-projection.md)
    - [Pair preselection: choosing between Disabled, Generic, and Reference](../workflow/alignment/pair-preselection-modes.md)
    - [Performance tuning: CPU, RAM, GPU, and OS](../topics/performance/cpu-ram-gpu-os-tuning.md)
    - [Point cloud confidence values: what they mean and how to filter](../workflow/point-cloud/point-cloud-confidence-values.md)
    - [Programmatic calibration import / export](../workflow/camera-calibration/calibration-import-export.md)
    - [Programmatic chunk.region control: move, scale, rotate the bounding box](../workflow/project-setup/region-control-python.md)
    - [Programmatic marker placement and pinning](../workflow/markers-gcps/programmatic-marker-placement.md)
    - [RAM and quality settings: what determines peak memory](../topics/performance/ram-and-quality-settings.md)
    - [Recovery paths for unaligned cameras](../workflow/alignment/recovery-paths-unaligned-cameras.md)
    - [Reducing camera overlap in over-acquired datasets](../workflow/optimization/reducing-camera-overlap.md)
    - [Reference preselection](../reference/features/reference-preselection.md)
    - [Release gate demos](../about/release-gate-demos.md)
    - [Removing "blue flag" marker projections cleanly](../workflow/markers-gcps/removing-blue-flag-marker-projections.md)
    - [Rendering models from synthetic cameras: spherical panoramas and regular views](../topics/scripting/rendering-from-synthetic-cameras.md)
    - [Repositioning a chunk: moving the origin to a known point](../workflow/project-setup/repositioning-chunk-origin.md)
    - [Reproducing chunk-info statistics in Python](../topics/repeatability-qa/reproducing-chunk-info-statistics-python.md)
    - [Reprojection error analysis: per-camera and per-tie-point](../topics/repeatability-qa/reprojection-error-analysis.md)
    - [Rolling-shutter compensation: Regularized vs Full, when to use which](../workflow/camera-calibration/rolling-shutter-compensation.md)
    - [Sample data](../reference/sample-data.md)
    - [Saving estimated reference values to file: location, rotation, error, and sigma](../topics/repeatability-qa/save-estimated-reference.md)
    - [Scalebar distance error: per-scalebar values and RMS aggregation](../topics/repeatability-qa/scalebar-error-statistics.md)
    - [Scripting context pitfalls: GUI vs command-line, document handles, and stage validation](../topics/scripting/scripting-context-pitfalls.md)
    - [Sensor and camera shared-tie-point graphs: detecting isolated groups](../topics/repeatability-qa/shared-tie-point-graphs.md)
    - [Setting `chunk.region` to bound the tie-point cloud](../workflow/project-setup/setting-the-chunk-region.md)
    - [Style](../about/style.md)
    - [Symlink filename — not target — controls the camera label](../workflow/project-setup/symlink-filename-camera-label.md)
    - [Synthetic position priors via `ReferencePreselectionSource`](../workflow/alignment/synthetic-priors-reference-preselection.md)
    - [Texture blending modes — what each one actually does](../workflow/texture/blending-modes.md)
    - [Texture in Metashape 2.3 — what changed and why your scripts may need updating](../workflow/texture/texture-in-2-3-changes.md)
    - [The `merge_tiepoints` option (and the `keep_keypoints` prerequisite)](../workflow/chunks/merge-tiepoints-and-keep-keypoints.md)
    - [The chunk's internal coordinate system: arbitrary scale and the `chunk.transform.scale` factor](../topics/scripting/chunk-internal-scale-and-units.md)
    - [The Clean Tie Points → Optimize Cameras loop](../workflow/optimization/clean-tie-points-optimize-cameras-loop.md)
    - [The slave-sensor transform: composition rule, axis convention, and recipes](../workflow/camera-calibration/slave-sensor-transform-recipes.md)
    - [The three `alignChunks` methods (point / marker / camera)](../workflow/chunks/alignchunks-three-methods.md)
    - [Tie-point multiplicity: track length, distribution, and what it tells you](../topics/repeatability-qa/tie-point-multiplicity.md)
    - [Tightening reference accuracies after `alignCameras`: when the similarity-transform residual isn't enough](../workflow/optimization/tightening-reference-accuracies.md)
    - [Tiled models: when to use, what they replace, and how to export](../workflow/tiled-model/tiled-model-when-to-use.md)
    - [Transferring camera orientation between modalities (RGB → thermal)](../workflow/camera-calibration/transfer-orientation-modalities.md)
    - [Troubleshooting Metashape: diagnostic ladder and where the logs live](../topics/troubleshooting/troubleshooting-diagnostic-ladder.md)
    - [Undocumented tweaks: a partial reference](../topics/scripting/undocumented-tweaks-reference.md)
    - [Unverified](../about/unverified.md)
    - [Version differences](../reference/version-differences.md)
    - [Version timeline](../reference/version-timeline.md)
    - [What `mergeChunks` actually does (and what it does not)](../workflow/chunks/what-mergechunks-does.md)
    - [When does `optimizeCameras` actually do something?](../workflow/optimization/when-optimize-cameras-helps.md)
    - [When does Metashape use the GPU? (and how to verify)](../topics/performance/gpu-usage-by-stage.md)
    - [When to use chunks: dataset partitioning strategies](../topics/multi-chunk/when-to-use-chunks.md)
    - [Working with shape geometries (1.7+ API)](../topics/scripting/shape-geometry-api.md)
    - [YPR rotation conventions: `ypr2mat` vs `camera.reference.rotation`](../topics/scripting/ypr-rotation-conventions.md)
