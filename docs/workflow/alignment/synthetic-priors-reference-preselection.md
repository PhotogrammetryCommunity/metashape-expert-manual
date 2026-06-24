---
title: Synthetic position priors via `ReferencePreselectionSource`
status: unverified
applies_to: Metashape Pro 2.x — and unchanged from PhotoScan 1.3+
edition: Pro
last_reviewed: 2026-05-22
diataxis: how-to
confidence: medium
---

# Synthetic position priors via `ReferencePreselectionSource`
> **Confidence:** *medium.* The source thread documents what
> `reference_preselection` *does*; the *application* — using
> synthetic priors specifically to defeat repeated geometry — is
> a synthesis of the documented behaviour with the matcher's
> known weaknesses. The technique is testable; reproductibility
> is high.

## Problem

Some scenes the matcher cannot disambiguate from image content
alone:

- **Symmetric structures** (see
  [`alignChunks` cannot break geometric symmetry](alignchunks-symmetric-scene-failure.md)).
- **Repeated textures** — apartment-block window grids,
  agricultural row crops, tiled or brick-patterned surfaces.
- **Sparse or featureless regions** mixed with feature-rich
  ones, where the matcher pairs sparse-region cameras across
  the scene's gap to feature-rich-region cameras.

In each case, unconstrained `matchPhotos` discovers many false
cross-region matches; `alignCameras` then turns those into a
globally-consistent but geometrically-wrong reconstruction.

## Solution: synthetic priors restrict the matcher's pair candidates

`Chunk.matchPhotos(reference_preselection=True,
reference_preselection_mode=ReferencePreselectionSource, …)`
restricts cross-image pair candidates to cameras whose
`reference.location` priors are spatially close. The canonical thread's
2016 description:

> "Reference preselection in the actual version (1.2) uses the
> coordinate information trying to match the photos (using only
> certain number of neighbors according to the camera centers
> coordinates) also the Generic preselection method is applied
> to those neighbors. [...] In the next version we've made the
> Generic and Reference option are separated adding new
> preselection mode (reference without generic)." — Alexey
> Pasumansky, 2016-12-20, PhotoScan 1.2
> ([permalink](https://www.agisoft.com/forum/index.php?topic=6306.msg30457#msg30457))

The application that defeats repeated-geometry: **populate
`camera.reference.location` with synthetic priors** — hand-clicked
positions on a 2D site plan, CAD-derived coordinates, or output
from coarse external tracking — and use them to gate the
matcher's pair selection. Cross-region false matches never enter
the tie-point graph, because candidate pairs are filtered by
spatial proximity in the prior frame *before* matching runs.

The priors **do not have to be accurate.** They are used for
pair selection, then act as soft constraints during
`alignCameras` with the per-axis accuracies you set. Two-axis
priors with very loose Z accuracy (`Metashape.Vector([…, …, 1e6])`)
work fine; Metashape recovers Z from tie points alone.

## The workflow

### Step 1 — Populate `camera.reference.location`

Source the priors from whatever 2D-or-better information you have.
Three common sources:

#### Source A: hand-click positions on a top-down reference image

For an indoor capture or fixed-angle outdoor capture where you
know the camera positions roughly from a floor plan:

```python
import Metashape

# Mapping from camera label → (x, y) in metres on the floor plan.
# Z left at 0 because the priors are 2D; Metashape will recover Z.
priors = {
    "DSC_1234.JPG": (12.5, 4.0),
    "DSC_1235.JPG": (15.0, 4.5),
    # …
}

chunk = Metashape.app.document.chunk
for camera in chunk.cameras:
    if camera.label not in priors:
        continue
    x, y = priors[camera.label]
    camera.reference.location = Metashape.Vector([x, y, 0.0])
    # Tight on X/Y, very loose on Z (we don't know Z).
    camera.reference.location_accuracy = Metashape.Vector([2.0, 2.0, 1e6])
    camera.reference.location_enabled = True
    camera.reference.enabled = True
```

#### Source B: extract from CAD / floor plan / pre-existing survey

Convert the CAD coordinates to metres in the same world frame as
the priors above; structure of the loop is identical.

#### Source C: coarse external tracking (e.g., GNSS, SLAM)

For aerial or long-baseline outdoor captures with low-precision
GNSS or visual-odometry output:

```python
# location_accuracy reflects the tracking system's
# confidence — typically metres for consumer GNSS, decimetres
# for differential GNSS, etc.
camera.reference.location          = Metashape.Vector(gnss_xyz)
camera.reference.location_accuracy = Metashape.Vector([5.0, 5.0, 8.0])
camera.reference.location_enabled  = True
```

### Step 2 — Run `matchPhotos` with `ReferencePreselectionSource`

```python
chunk.matchPhotos(
    downscale=1,
    generic_preselection=False,    # disable feature-based pair selection
    reference_preselection=True,
    reference_preselection_mode=Metashape.ReferencePreselectionSource,
    keep_keypoints=True,
    reset_matches=True,            # fresh start, the priors filter out
                                   #   the bad matches the prior run made
)
```

Two non-default kwargs matter:

- **`reference_preselection_mode=ReferencePreselectionSource`**
  is the *strict* mode: pair candidates are determined only by
  proximity in the prior frame, with no fallback to image
  content. This is what defeats repeated geometry.
- **`generic_preselection=False`** disables the additional
  feature-based pair filtering. With both flags set, the matcher
  is constrained to spatial neighbourhoods only.

The other two preselection modes
(`ReferencePreselectionEstimated`, `ReferencePreselectionSequential`)
do *not* solve the repeated-geometry problem in the same way —
they use estimated camera positions or sequential-frame ordering
respectively, neither of which addresses the bootstrap case where
the matcher needs prior priors to avoid false matches.

### Step 3 — Align cameras

```python
chunk.alignCameras()
```

The bundle adjustment uses the priors as soft constraints with
the per-axis accuracies set in Step 1. Tight prior axes (e.g.,
X, Y at 2 m accuracy) constrain the bundle; loose axes (Z at
1 × 10⁶) effectively let the bundle find the value freely.

## Caveats

- **The priors must distinguish the regions you want to keep
  apart.** If your priors are too coarse (every camera within
  the same neighbourhood), the matcher still makes false
  matches inside that neighbourhood. The priors must be
  *separating* — adjacent priors should be closer to each other
  than they are to any falsely-matched neighbour.
- **`generic_preselection=False` plus
  `reference_preselection=True` is the strict mode.** Setting
  `generic_preselection=True` re-introduces feature-based pair
  filtering on top of reference preselection — useful when
  priors are coarse and you trust feature matching not to
  cross neighbourhoods, but typically not what you want for
  the bootstrap case.
- **The priors disappear after `alignCameras` if you forget to
  enable them.** Setting `camera.reference.location_enabled=True`
  is required for the priors to act as bundle constraints.
  Without it, the priors are stored but not used.
- **Per-axis accuracy is a `Vector`, not a scalar.** See
  [`chunk.transform.matrix` is local→world; `camera.transform`
  is local](../../topics/crs/chunk-frame-vs-camera-frame.md)
  for the full surface; tutorials commonly show scalar accuracy,
  but the API uses 3-component vectors and uses each component
  independently.

## Runnable demonstration on a synthetic dataset

The Building sample is not the right demonstration target — it
has no repeated-geometry problem to defeat. The technique is
testable on any controlled scene with deliberately introduced
symmetry or repeating textures.

> **Demo verified:** ✗ — pending Tier 3 reproduction on a
> repeated-geometry dataset. The behaviour described is testable
> on a controlled scene; the demo is reproducible-by-design but
> requires a dataset with the failure mode the technique
> addresses.

```python
"""Bootstrap alignment via synthetic priors on a
repeated-geometry scene.

Pre-condition: a chunk with cameras photographing a scene with
strong repeated structure (regular building, agricultural rows,
etc.) where unconstrained alignment confuses regions. Hand-clicked
or CAD-derived priors provide approximate positions in metres.
"""
import Metashape

# Step 1: synthetic priors (label → (x_m, y_m)).
# In a real workflow these would come from a top-down reference
# image, a CAD plan, or external tracking.
priors = {
    "IMG_0001.JPG": (0.0, 0.0),
    "IMG_0002.JPG": (5.0, 0.0),
    "IMG_0003.JPG": (10.0, 0.0),
    # … 2D positions for each camera
}

chunk = Metashape.app.document.chunk
for c in chunk.cameras:
    if c.label not in priors:
        continue
    x, y = priors[c.label]
    c.reference.location          = Metashape.Vector([x, y, 0.0])
    c.reference.location_accuracy = Metashape.Vector([2.0, 2.0, 1e6])
    c.reference.location_enabled  = True
    c.reference.enabled           = True

# Step 2: matchPhotos with strict reference preselection.
chunk.matchPhotos(
    downscale=1,
    generic_preselection=False,
    reference_preselection=True,
    reference_preselection_mode=Metashape.ReferencePreselectionSource,
    keep_keypoints=True,
    reset_matches=True,
)

# Step 3: align.
chunk.alignCameras()

aligned = sum(1 for c in chunk.cameras if c.transform is not None)
print(f"aligned: {aligned}/{len(chunk.cameras)}")
```

**Expected output:** alignment succeeds where the unconstrained
attempt previously failed (or produced a geometrically-wrong
result). Diagnostic test: re-run with `reference_preselection=False`
and compare — the unconstrained run should show one of the
repeated-geometry failure modes (false matches across
neighbourhoods, mirror-equivalent placement, etc.).

## See also

- [Helping alignment when photos don't align: markers, references, and what to use when](helping-alignment.md)
  — the unified decision framework that places this technique
  in the broader "approximate references help" context, with
  guidance on accuracy values and when to choose synthetic
  priors over markers.
- [`alignChunks(method=point)` cannot break geometric symmetry](alignchunks-symmetric-scene-failure.md)
  — the symmetry failure mode this technique works around.

## References

- [Forum thread, *Align images - Reference preselection*, 2016](https://www.agisoft.com/forum/index.php?topic=6306.0)
  — primary source; the clarification of what
  `reference_preselection` does (msg 30716).
- *Metashape Python Reference* (2.3.1), `Chunk.matchPhotos` —
  documents `reference_preselection`,
  `reference_preselection_mode`, and the three modes
  (`ReferencePreselectionEstimated`, `…Sequential`, `…Source`).
- [`alignChunks(method=point)` cannot break geometric symmetry](alignchunks-symmetric-scene-failure.md) — the failure mode this technique works around.
- [Adding cameras to an aligned chunk: the `keep_keypoints`
  workflow](incremental-matching-keep-keypoints.md) — combines
  with the synthetic-priors workflow when the project also needs
  incremental matching.
