---
title: Reducing camera overlap in over-acquired datasets
status: unverified
applies_to: Metashape Pro 2.x. Tier 1 introspection on Metashape 2.2.3 confirms the `Chunk.reduceOverlap(overlap, use_selection)` signature. The feature was introduced in Metashape 1.5 (2018) under the name *Optimize Coverage*; it was renamed *Reduce Overlap* in 2.x.
edition: Pro
last_reviewed: 2026-05-26
diataxis: how-to
confidence: medium
---

# Reducing camera overlap in over-acquired datasets
> **Confidence:** *medium.* The `Chunk.reduceOverlap(overlap, use_selection)` signature is introspection-confirmed; algorithm description (set-cover with angular deduplication) is forum-attested.
## Problem

You have a dataset with **excessive image overlap** — typically
a drone survey at conservatively low altitude with high front
and side overlap, or a mass-acquisition workflow where many
images observe the same surface region. The redundant cameras
slow processing without improving reconstruction quality.

You want to **disable the redundant cameras** while keeping a
camera subset that still observes every part of the surface
from the desired number of angles.

## Context

Metashape provides this as
`Chunk.reduceOverlap(overlap, use_selection)` (renamed from
*Optimize Coverage* in 1.5; current 2.x name is *Reduce
Overlap*). The feature was introduced as experimental:

> "Optimize coverage is a new experimental feature that allows
> to disable the images that result in excessive overlap.
> Currently it requires to have the alignment and at least
> rough mesh model."
> — Alexey Pasumansky, 2018-11-18, Metashape 1.5.0 pre-release
> ([permalink](https://www.agisoft.com/forum/index.php?topic=9793.msg45620#msg45620))

The two prerequisites — alignment + rough mesh — are unchanged
in 2.x. A texture was briefly required in early 1.5.0 builds
but the requirement was relaxed:

> "No texture is required, only mesh model."
> — Alexey Pasumansky, 2018-11-19, Metashape 1.5.0 pre-release
> ([permalink](https://www.agisoft.com/forum/index.php?topic=9793.msg45633#msg45633))

### How the algorithm works (1.7+)

The algorithm was rewritten in Metashape 1.7. The current (2.x)
version solves a **minimum set-cover** problem:

> "Now algorithm tries to select minimal set of cameras such
> that each point of rough model is observed from at least N
> significantly different angles (multiple cameras from single
> direction count as one) where N is specified by user."
> — simiyutin, 2020-10-27, Metashape 1.7
> ([permalink](https://www.agisoft.com/forum/index.php?topic=12426.msg56344#msg56344))

In concrete terms:

1. **Visibility computation.** For each point (vertex or
   sampled location) on the rough mesh, the algorithm
   determines which cameras observe it by projecting cameras
   onto the polygonal surface.
2. **Angular deduplication.** Multiple cameras that observe the
   same surface point from approximately the same direction are
   counted as one. Only "significantly different angles"
   contribute to the coverage count.
3. **Minimal camera selection.** The algorithm selects the
   smallest subset of cameras such that every surface point is
   still observed from ≥ N different angles (where N is the
   `overlap` parameter). Cameras not in this minimal set are
   disabled.

The pre-1.7 algorithm "used similar logic but with more complex
formulation and weighting and was not as interpretable." The 1.7
rewrite also made the algorithm approximately 100× faster.

## Solution

### Pre-requisites

1. **Aligned cameras.** Run *Workflow → Align Photos* on the
   full dataset before invoking *Reduce Overlap*.
2. **Rough mesh model.** Run *Workflow → Build Mesh* with any
   reasonable parameters. The algorithm uses the mesh's surface
   geometry to compute per-camera coverage; a low-quality
   "rough" mesh is sufficient.

### GUI procedure

1. *Tools → Reduce Overlap* (in the menu bar).
2. The *Reduce Overlap* dialog appears with two parameters:
   - **Surface coverage** (integer): the target number of
     cameras observing each point. Lower = more aggressive
     elimination.
   - **Focus on selection** (checkbox): when on, only selected
     triangles of the polygonal model are considered as targets.
3. Click *OK*. Cameras determined to be redundant are
   **disabled** (not deleted) — the *enabled* checkbox is
   cleared in the *Photos* pane.

### Python API

```python
import Metashape

doc = Metashape.app.document
chunk = doc.chunk

# Default 'overlap=3' targets roughly 3 cameras per surface
# point. For high-overlap drone surveys, this often disables a
# substantial fraction of the original cameras (the exact
# fraction depends on the dataset's overlap characteristics —
# count after the call to verify).
chunk.reduceOverlap(overlap=3, use_selection=False)
doc.save()

# Inspect the result.
n_total = len(chunk.cameras)
n_enabled = sum(1 for c in chunk.cameras if c.enabled)
print(f"  enabled: {n_enabled}/{n_total} cameras")
```

The API surface (Tier 1 introspection on 2.2.3):

| Kwarg | Default | Effect |
|-------|--------|--------|
| `overlap` | `3` | Target number of cameras observing each point of the surface. Higher = more cameras kept; lower = more aggressive elimination. |
| `use_selection` | `False` | When `True`, only selected mesh triangles are considered. Cameras that don't observe any selected triangle are disabled. |
| `progress` | (none) | Optional progress callback. |

### Choosing `overlap`

Heuristics from typical drone-survey workflows:

- **`overlap=3`** (the default): keeps ≈3 cameras per surface
  point. Good general-purpose value. Reconstruction quality
  is preserved but redundant cameras are removed.
- **`overlap=2`**: more aggressive. Use when overlap is
  extreme (e.g., 90% front and 80% side overlap on a flat
  agricultural field).
- **`overlap=5+`**: conservative. Use when the surface has
  many fine details (vegetation, complex geometry) and you
  want extra cameras for redundancy.

The right value depends on how much over-acquisition the
dataset has. Always check the result by counting enabled
cameras and visually inspecting the camera coverage in the
*Model* view (selected/disabled cameras are visually
distinguishable).

### Re-enabling cameras

Disabled cameras are not deleted — they remain in the chunk
and can be re-enabled at any time via the GUI checkbox or
programmatically:

```python
# Re-enable all cameras (undo Reduce Overlap).
for cam in chunk.cameras:
    cam.enabled = True
```

This means *Reduce Overlap* is a non-destructive experiment;
you can always revert.

### Re-building after Reduce Overlap

After reducing overlap, the alignment is unchanged but the
*Build Point Cloud*, *Build Mesh*, *Build Texture*, etc.
results will be computed from the disabled-camera-set. The
typical workflow is:

1. *Align Photos* on full dataset.
2. *Build Mesh* (rough; for *Reduce Overlap* input).
3. *Tools → Reduce Overlap* (this typically disables a
   substantial fraction of cameras on high-overlap datasets;
   count after to verify).
4. Re-run *Build Point Cloud* and *Build Mesh* with the
   reduced camera set (faster + similar quality).
5. *Build Texture* / *Build DEM* / *Build Orthomosaic*.

## Caveats and gotchas

- **Prerequisite violations error or no-op.** If no cameras
  are aligned, or no mesh exists, *Reduce Overlap* either
  errors with a clear message or runs as a no-op (depending
  on which prerequisite is missing). Verify both prerequisites
  are met before scripting the call into a batch pipeline.
- **`use_selection=True` with empty selection.** If you pass
  `use_selection=True` but no triangles are selected, the
  command typically does nothing (no cameras get disabled).
  Make the selection explicit before the call.
- **The mesh quality used for *Reduce Overlap* matters less
  than expected.** A low-quality rough mesh (Quality: Lowest;
  Face count: Low) is sufficient. The algorithm needs surface
  geometry, not visual fidelity.

- **Reduce Overlap considers visual coverage only, not feature
  density.** Two cameras observing the same surface region
  from similar angles count as redundant even if one has
  significantly better focus or exposure. If a small subset of
  your cameras has known-superior quality (better lighting,
  GCP coverage, anchor frames), pin them to be kept by
  selecting the corresponding mesh triangles and using
  `use_selection=True`.

- **Markers are unaffected.** Disabled cameras retain their
  marker projections. Markers for which only disabled cameras
  have projections will not contribute to bundle adjustment;
  consider re-enabling those cameras specifically.

- **The default `overlap=3` is calibrated for typical aerial
  workflows.** Close-range / object photogrammetry projects
  often want `overlap=5` or higher because surface detail is
  finer.

- **Re-enabling does not re-introduce processing time penalty
  unless you re-build.** A camera that's disabled but was
  previously aligned remains aligned in `chunk.transform`
  state; re-enabling it is essentially free.

## See also

- [The Clean Tie Points → Optimize Cameras loop](clean-tie-points-optimize-cameras-loop.md)
  — companion technique for tie-point hygiene before
  `Reduce Overlap` is applied.
- *Metashape Change Log* (GUI), Version 1.5.2 (build 7838,
  March 2019) entry — "Renamed Optimize Coverage command to
  Reduce Overlap and revised command parameters." The Python
  API name (`chunk.reduceOverlap`) predates the rename and is
  unchanged.
- *Metashape Pro User Manual* (2.3), ch. 2 *Excessive image
  elimination* / *Reduce overlap parameters*.
- *Metashape Python Reference* (2.3.1):
  `Chunk.reduceOverlap`.
- [Forum topic 9793](https://www.agisoft.com/forum/index.php?topic=9793.0)
  — Metashape 1.5.0 pre-release thread (feature
  introduction).

