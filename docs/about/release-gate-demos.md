# Release gate — demos to run before the manual ships

This page is the audit list of every runnable demonstration in
the manual and its current verification state. **Every entry must
read ✓ before the manual is published or shared widely.** This is
in addition to the per-claim Tier 3 verification tracked in
`docs/about/unverified.md`; the two are independent (an article
can hold UV markers and verified demos, or vice versa).

The verification rules are in [`STYLE.md`](https://github.com/PhotogrammetryCommunity/metashape-expert-manual/blob/main/STYLE.md) § "Demo verification
status".

## Current state

| Article | Sample dataset | Status | Notes |
|---------|---------------|--------|-------|
| [Removing "blue flag" marker projections cleanly](../workflow/markers-gcps/removing-blue-flag-marker-projections.md) | Coded targets | ✓ | API surface verified on synthetic cameras (UV-008 falsified). End-to-end run completed on the *Coded targets* sample (Metashape 2.2.3, 2026-06-04); the demo as written runs and matches its expected output. **Why not auto-validated in CI:** Object-model API auto-checked here (UV-008 falsified on synthetic cameras); end-to-end needs the *Coded targets* sample (`detectMarkers`). |
| [Programmatic marker placement and pinning](../workflow/markers-gcps/programmatic-marker-placement.md) | Coded targets | ✓ | Construction forms verified on Metashape 2.2.2 (UV-009 falsified). End-to-end run completed on the *Coded targets* sample (Metashape 2.2.3, 2026-06-04); the demo as written runs and matches its expected output. **Why not auto-validated in CI:** Construction forms auto-checked here (UV-009 falsified); end-to-end needs the *Coded targets* sample. |
| [The Clean Tie Points → Optimize Cameras loop](../workflow/optimization/clean-tie-points-optimize-cameras-loop.md) | Aerial-with-GCPs (or Building) | ✗ | Full alignment + cleanup loop end-to-end. Highest priority — the demo *is* the article's central claim. **Why not auto-validated in CI:** Needs the *Aerial-with-GCPs* sample. Processing runs without a license, so this becomes automatable once the dataset is downloaded. |
| [Reproducing chunk-info statistics in Python](../topics/repeatability-qa/reproducing-chunk-info-statistics-python.md) | Aerial-with-GCPs | ✗ | Three-formula run; expected agreement with the GUI's *Reference* pane to ~0.001 px (RMS) and ~0.0001 m (marker total). **Why not auto-validated in CI:** Needs the *Aerial-with-GCPs* sample (full alignment) to compare against the Reference pane. |
| [Setting `chunk.region` to bound the tie-point cloud](../workflow/project-setup/setting-the-chunk-region.md) | Aerial-with-GCPs | ✗ | Region resize end-to-end; observable via *Region → Show Bounding Box* in the GUI. **Why not auto-validated in CI:** The region API is auto-checkable (object-model); the *Show Bounding Box* confirmation is GUI-only. |
| [Exporting depth maps from Python (32-bit, scaled)](../workflow/depth-maps/exporting-depth-maps-python.md) | Aerial-with-GCPs | ✗ | Float32 export; verify resulting `.tif` files in ImageJ or `tifffile.imread`. **Why not auto-validated in CI:** Needs the *Aerial-with-GCPs* sample **and** export is license-gated (this API build is unactivated). |
| [What `mergeChunks` actually does](../workflow/chunks/what-mergechunks-does.md) | Building (split into 2 chunks) | ✗ | Counts cross-chunk tracks after merge with `merge_tiepoints=False`. Expected: 0. **Why not auto-validated in CI:** Needs the *Building* sample split into 2 chunks; automatable once downloaded (processing runs unactivated). |
| [The three `alignChunks` methods](../workflow/chunks/alignchunks-three-methods.md) | Building (split into 2 chunks) | ✗ | Compares `method=0/1/2` outcomes; reads `chunk.transform.matrix` to detect registration. Pre-condition: shared markers and shared camera labels. **Why not auto-validated in CI:** Needs the *Building* sample split into 2 chunks with shared markers/cameras; automatable once downloaded. |
| [The `merge_tiepoints` option](../workflow/chunks/merge-tiepoints-and-keep-keypoints.md) | Building (split into 2 chunks) | ✗ | Compares track count with and without `merge_tiepoints=True` after running `matchPhotos(keep_keypoints=True)`. **Why not auto-validated in CI:** Needs the *Building* sample split into 2 chunks; automatable once downloaded. |
| [`mergeChunks` does not deduplicate cameras](../workflow/chunks/no-camera-deduplication.md) | Building (split into 2 chunks, camera-based align + merge) | ✗ | Counts duplicates by `camera.photo.path`. Pre-condition: shared cameras across source chunks. **Why not auto-validated in CI:** Needs the *Building* sample with shared cameras across source chunks; automatable once downloaded. |
| [Recovery paths for unaligned cameras](../workflow/alignment/recovery-paths-unaligned-cameras.md) | Building | ✗ | Force-resets 5 random cameras, runs Path 1 (`chunk.alignCameras(cameras=…)`), reports recovery rate. Pre-condition: Building chunk fully aligned. **Why not auto-validated in CI:** Needs the *Building* sample (a fully aligned chunk); automatable once downloaded. |
| [Adding cameras to an aligned chunk: the `keep_keypoints` workflow](../workflow/alignment/incremental-matching-keep-keypoints.md) | Building (split into 25 + 25) | ✗ | Aligns first 25 images with `keep_keypoints=True`, then incrementally adds and aligns the second 25. Verifies existing tracks are preserved (`reset_matches=False`). **Why not auto-validated in CI:** Needs the *Building* sample (split 25+25); automatable once downloaded. |
| [Declaring a fixed-geometry multi-camera rig in Python](../workflow/camera-calibration/multi-camera-rig-python.md) | Building (synthetic stereo) or real multi-camera | ✗ | Demonstrates `MultiplaneLayout` add + per-sensor offset declaration. Synthetic on Building (frame-pair as fake stereo); real verification needs a multi-camera dataset. **Why not auto-validated in CI:** Layout construction is auto-checkable (object-model); real verification needs a multi-camera dataset, which is **not in the Agisoft sample collection**. |
| [Choosing the master sensor in a multi-camera layout](../workflow/camera-calibration/choosing-master-sensor-multi-camera-layout.md) | multi-folder synthetic or real multispectral | ✗ | Verifies that `filegroups` ordering controls master selection (`Sensor.master == sensor` test). Requires a multi-folder dataset; not in the Agisoft sample collection. **Why not auto-validated in CI:** Needs a multi-folder dataset, which is **not in the Agisoft sample collection**. |
| [When does `optimizeCameras` actually do something?](../workflow/optimization/when-optimize-cameras-helps.md) | Aerial-with-GCPs | ✗ | Runs Optimize twice and compares RMS / track-count delta. Expected: first run non-trivial, second near-zero. Demonstrates the canonical thread's "very little effect" claim in numbers. **Why not auto-validated in CI:** Needs the *Aerial-with-GCPs* sample; automatable once downloaded. |
| [`mask_tiepoints` cross-view propagation](../workflow/alignment/mask-tiepoints-cross-view.md) | Building (with synthetic occluder masks) or true foreground-occluder dataset | ✗ | Compares alignments with `mask_tiepoints=True` vs `False`. Inconclusive on Building (no real occluder); requires a true foreground-occluder dataset to confirm the inferred behaviour. **Why not auto-validated in CI:** Needs a true foreground-occluder dataset, which is **not in the Agisoft sample collection**. |
| [`alignChunks(method=point)` cannot break geometric symmetry](../workflow/alignment/alignchunks-symmetric-scene-failure.md) | controlled symmetric-structure dataset | ✗ | Hypothesis-confirmation demo: tests whether `method=0` produces visibly-wrong alignment on a bilaterally-symmetric input where `method=1` (markers) does not. Not testable on Agisoft sample collection. **Why not auto-validated in CI:** Needs a controlled symmetric-structure dataset, which is **not in the Agisoft sample collection**. |
| [Synthetic position priors via `ReferencePreselectionSource`](../workflow/alignment/synthetic-priors-reference-preselection.md) | controlled repeated-geometry dataset | ✗ | Bootstrap alignment on a scene unconstrained matching can't handle. Requires a deliberately-symmetric or repeated-feature dataset; not in Agisoft sample collection. **Why not auto-validated in CI:** Needs a repeated-geometry dataset, which is **not in the Agisoft sample collection**. |
| [`filter_mask=True` starves matchPhotos when masks cover most of the image](../workflow/alignment/filter-mask-starvation.md) | dataset with controlled mask-coverage fractions | ✗ | Tests starvation threshold with 20%/40%/60%/80% mask coverage. Not in Agisoft sample collection. **Why not auto-validated in CI:** Needs a dataset with controlled mask-coverage fractions, which is **not in the Agisoft sample collection**. |
| [Symlink filename — not target — controls the camera label](../workflow/project-setup/symlink-filename-camera-label.md) | any single image | ✗ | One-line API check; verify `Camera.label` derives from symlink basename, `Camera.photo.path` from resolved target. Tier 3 multi-platform check (macOS, Linux, Windows). **Why not auto-validated in CI:** The `Camera.label` API check is auto-checkable; the claim is multi-platform (macOS/Linux/Windows), so the cross-platform part needs human Tier 3. |
| [`chunk.transform.matrix` is local→world; `camera.transform` is local](../topics/crs/chunk-frame-vs-camera-frame.md) | Aerial-with-GCPs | ✗ | Confirms chunk-local vs world-frame distinction by comparing `T.mulp(camera.transform.translation())` to `camera.reference.location` (world-frame ref). Expected agreement to RMS. **Why not auto-validated in CI:** Needs the *Aerial-with-GCPs* sample (an aligned chunk with world-frame refs); automatable once downloaded. |
| [Tightening reference accuracies after `alignCameras`](../workflow/optimization/tightening-reference-accuracies.md) | Aerial-with-GCPs | ✗ | Two-phase recipe demonstration: report camera/marker Δ at baseline, after Phase 1 (tight camera refs), after Phase 2 (loose camera refs + tight markers). Expected: marker-Δ drops from baseline to cm to mm range. The article's central claim — high priority for Tier 3. **Why not auto-validated in CI:** Needs the *Aerial-with-GCPs* sample; automatable once downloaded. |
| [Metashape's distortion model and converting to OpenCV / Colmap](../workflow/camera-calibration/distortion-model-opencv-colmap.md) | Aerial-with-GCPs | ✗ | Read calibration with units annotated; export Colmap cameras.txt with build-aware P1/P2 swap. Fix is automatic on Metashape 2.3.0 build 21778+; manual swap on earlier builds. **Why not auto-validated in CI:** Calibration read is auto-checkable; the full Colmap export round-trip uses the *Aerial-with-GCPs* sample. |
| [`sensor.calibration` vs `sensor.user_calib`](../workflow/camera-calibration/sensor-calibration-vs-user-calib.md) | Aerial-with-GCPs | ✗ | Demonstrates user_calib (input) vs calibration (output): write known-wrong f to user_calib, run alignment, observe user_calib unchanged and calibration refined. **Why not auto-validated in CI:** Needs the *Aerial-with-GCPs* sample (alignment to observe `calibration` refine while `user_calib` stays fixed). |
| [Programmatic calibration import / export](../workflow/camera-calibration/calibration-import-export.md) | any project with a sensor | ✓ | Save → load round-trip with byte-equality check on all Calibration attributes. Aerial-with-GCPs sufficient. **Why not auto-validated in CI:** **Auto-validated in this environment** (Metashape 2.2.3, unactivated): `Calibration` save -> load round-trip preserves `f, cx, cy, b1, b2, k1-k4, p1, p2, width, height` exactly. No dataset or license needed. |
| [Computing per-camera coverage area](../topics/scripting/computing-camera-coverage-area.md) | Aerial-with-GCPs | ✗ | the 2014 forum sample script ported to 2.x. Outputs camera footprint TSV (pixel_x, pixel_y, world_x, world_y, world_z). Pre-condition: chunk has built mesh. **Why not auto-validated in CI:** Needs the *Aerial-with-GCPs* sample with a built mesh; automatable once downloaded. |
| [Converting `camera.transform` to ENU](../topics/scripting/camera-poses-to-enu.md) | Aerial-with-GCPs | ✗ | Try Approach 1 (`+proj=topocentric` CRS); fall back to Approach 2 (pyproj). Output: ENU camera positions. The PROJ-syntax acceptance is the empirically-testable claim. **Why not auto-validated in CI:** Needs the *Aerial-with-GCPs* sample; automatable once downloaded. |
| [Mapping orthomosaic pixels back to source images](../topics/scripting/orthomosaic-pixel-to-source-image.md) | Aerial-with-GCPs (with manual Point shape) | ✗ | the 2018 forum script ported to 2.x. Pre-condition: a Point shape on the orthomosaic with all three coordinates populated (run `chunk.updateAltitude([shape])` first). **Why not auto-validated in CI:** Needs the *Aerial-with-GCPs* sample (ortho + a populated Point shape); automatable once downloaded. |
| [Orthomosaic export — 4GB / BigTIFF / shift](../workflow/orthomosaic/orthomosaic-export-pitfalls.md) | Aerial-with-GCPs | ✗ | Export with `split_in_blocks=True`; verify block files. Aerial-with-GCPs is small enough to fit in 1–4 blocks; production datasets produce more. **Why not auto-validated in CI:** Needs the *Aerial-with-GCPs* sample **and** export is license-gated (this API build is unactivated). |
| [Importing camera orientation — EXIF, OPK, yaw/pitch/roll](../workflow/project-setup/importing-camera-orientation.md) | Aerial-with-GCPs | ✗ | Synthesise a CSV from existing camera positions with placeholder YPR; import via `chunk.importReference`; verify `camera.reference.rotation` populated. **Why not auto-validated in CI:** Needs the *Aerial-with-GCPs* sample; automatable once downloaded. |

## How to verify a demo (procedure)

1. Download the named sample dataset from
   <https://www.agisoft.com/downloads/sample-data/>.
2. In the article, copy the demo's code block; adjust the dataset
   path constant; run it through *Tools → Run Script…* or
   `metashape -r demo.py`.
3. Compare the printed output against the *Expected* paragraph
   that follows the code block.
4. **If the output matches:**
    - Update the demo's `**Demo verified:**` header to ✓ with the
      run date, the Metashape version, and a one-line note.
    - Update this page's *Status* column to ✓.
5. **If the output does not match, or the script raises:**
    - Do *not* update the header to ✓.
    - Either correct the article (preferred — the article was
      wrong about the API or the expected output) or open a
      UV-NNN entry in `docs/about/unverified.md` (when the
      discrepancy looks like a runtime / dataset-specific
      behaviour rather than a code error).

## Why this exists

A runnable demo that has not been run is no better than prose. The
manual's expert-overlay value depends on its claims being
trustworthy; a script the reader copies should produce the output
the article promises. This page is the explicit audit list so that
gap is visible and closable before publication.

The same principle is documented less formally in [`STYLE.md`](https://github.com/PhotogrammetryCommunity/metashape-expert-manual/blob/main/STYLE.md)'s
*Caveat phrasing — observed vs inferred claims* section: a UV
marker is metadata, not a license to assert inferences as observed
facts. A demo's `**Demo verified:**` header is the runtime analogue.
