---
title: "`alignChunks(method=point)` cannot break geometric symmetry"
status: unverified
applies_to: Metashape Pro 2.x — and unchanged from PhotoScan 1.x
edition: Pro
last_reviewed: 2026-05-22
diataxis: explanation
confidence: medium
---

# `alignChunks(method=point)` cannot break geometric symmetry
> **Confidence:** *medium.* The failure mode described here is
> inferred from the matcher's design (image-feature descriptors
> with no scene-level disambiguation) rather than observed in a
> controlled experiment. Treat as a strong working hypothesis
> pending Tier 3 reproduction on a known-symmetric dataset.

The point-based `alignChunks` matcher operates on **local image
features** (SIFT-like keypoints) and their cross-chunk
descriptor matches. On structures with bilateral or rotational
symmetry, those descriptors are also symmetric (within
detector noise), and the matcher has no way to distinguish one
symmetric copy of the structure from another. The result is a
**successful-looking alignment with the wrong answer**: the
`[R]` mark appears in the *Workspace* pane, the bundle scores
look acceptable, and yet mirror-image or rotational copies of
the structure overlap each other in the merged chunk.

This is distinct from the "no matches found" failure mode
covered in [The three `alignChunks` methods](../chunks/alignchunks-three-methods.md):
that case fails loudly (no `[R]` mark; no matches in the bundle).
The symmetry case fails *quietly* — there are plenty of matches,
just not the correct ones.

## When this happens

Three classes of structures that hit this failure mode:

- **Bilateral symmetry.** Church facades, neoclassical buildings,
  symmetric vehicle / object models, anatomical scans with
  left-right mirror symmetry.
- **Rotational symmetry.** Stadiums, cylindrical towers, regular
  polygonal buildings, turntable scenes treated as multiple
  chunks (each rotation viewed as its own chunk).
- **Translational repetition.** Apartment-block window grids,
  regular furniture rows, brick/tile patterns, agricultural
  fields.

In each case, the matcher finds many cross-chunk feature matches
(the descriptors are similar by construction), but a substantial
fraction of those matches are between the *wrong* symmetric
copies — points on the left tower of a symmetric building
matching the right tower's copy of the same feature, etc. The
fitted transformation is the one that reconciles those matches
geometrically; the answer is a smooth interpolation between
"correctly aligned" and "rotated by the symmetry's natural
rotation," and on inspection it visibly fails.

## Why no parameter tweak fixes it

The matcher is by design *scene-content-blind*: it knows only
keypoint descriptors and their cross-image similarity. The
correct alignment is no less plausible than the
symmetry-equivalent wrong alignment, given only that input.
Increasing `keypoint_limit=`, decreasing `downscale=`, or
toggling `generic_preselection=` changes the *number* of matches
but not their *symmetric-vs-correct* distribution.

The remedy is **external constraints the matcher cannot ignore**.

## The three workarounds

### Workaround 1 — Marker-based alignment (`method=1`)

Place ≥3 markers with non-symmetric labels on visually-distinct,
non-symmetric features in both source chunks. Then:

```python
doc.alignChunks(
    chunks=[chunk_a.key, chunk_b.key],
    reference=chunk_a.key,
    method=1,            # marker-based; uses shared markers as anchors
    fit_scale=True,
)
```

The marker-based fit operates on the markers' chunk-frame
positions, not on image features. As long as your markers are
*placed* on non-symmetric features (a window pattern that breaks
the symmetry, an asymmetrically-positioned object, etc.), the
fit has no symmetry ambiguity to resolve.

Three is the minimum for a non-degenerate similarity fit;
four or more is recommended for redundancy.

### Workaround 2 — Synthetic position priors

Populate `camera.reference.location` on the source chunks with
**synthetic priors** derived from a 2D site plan, CAD model, or
external positioning. Then run `matchPhotos` with
`reference_preselection=True,
reference_preselection_mode=Metashape.ReferencePreselectionSource`
*before* `alignChunks` — this restricts cross-chunk pair
candidates to spatially-neighbouring cameras only, preventing
the matcher from ever considering the symmetry-equivalent pairs.

See [Synthetic position priors via
`ReferencePreselectionSource`](synthetic-priors-reference-preselection.md)
for the full procedure. The priors don't have to be accurate —
they only need to be specific enough to disambiguate the symmetry.

### Workaround 3 — Camera-based alignment (`method=2`)

If the source chunks share cameras (e.g., one chunk is a subset
of the other, or they share an overview pass), camera-based
alignment uses the shared cameras' chunk-frame poses as
correspondences. This is *not* image-feature-based, so the
symmetry has no purchase:

```python
doc.alignChunks(
    chunks=[chunk_a.key, chunk_b.key],
    reference=chunk_a.key,
    method=2,            # camera-based
)
```

This works only when shared cameras are available. See
[Choosing the master sensor in a multi-camera layout](../camera-calibration/choosing-master-sensor-multi-camera-layout.md)
for related camera-based-alignment notes; the camera-deduplication
caveat in [`mergeChunks` does not deduplicate cameras](../chunks/no-camera-deduplication.md)
applies after merge.

## Diagnosis: how to tell you've hit this failure

Symptoms:

- `Align Chunks` runs to completion with `[R]` in the Workspace
  pane.
- The merged chunk's reprojection RMS *looks fine* on
  its own; per-chunk it was fine; the cross-chunk subset would
  also be fine in isolation.
- But the merged 3D viewport shows visible duplicate or
  mirrored geometry — features on opposite-symmetric sides of
  the structure overlap each other.

Diagnostic Python:

```python
# After alignChunks, inspect the chunk-to-chunk transformation.
T_b = chunk_b.transform.matrix
print(f"chunk_b transform translation : {T_b.translation()}")
print(f"chunk_b transform determinant : {T_b.det()}")

# A determinant of -1 (or a large angular separation that has no
# physical justification) suggests the matcher returned a
# mirror-equivalent or symmetry-equivalent answer.
```

A negative determinant on a similarity transform is the most
damning evidence: the fit is a *reflection* in addition to a
rotation/translation, which is geometrically impossible for a
correctly-photographed scene. Metashape's `alignChunks` may not
emit a reflection in the strict sense, but a fitted
transformation with `fit_scale=False` that is *very far* from
the user's expected pose for chunk B is a strong indicator.

## Caveats

- **The article's claim is inferred from the matcher's design,
  not from a forum post.** No specific Agisoft thread documents
  the symmetric-structure failure as a separate item — it is a
  natural consequence of how the point-based matcher works,
  observable on any synthetic symmetric dataset. Tier 3
  reproduction on a controlled symmetric dataset would promote
  the claim from inferred to observed.
- **`method=2` (camera based) does not have this failure mode**
  but has its own constraints — it requires shared cameras with
  identical labels, and produces duplicate cameras after merge
  unless mitigated (see the no-camera-deduplication article).
- **`method=1` (marker based) requires GCPs / markers placed on
  non-symmetric features.** Markers placed *on the symmetry*
  (e.g., the centre of a bilaterally-symmetric building) do not
  help.
- **Very-low symmetry cases can still align correctly with
  `method=0`.** Architectural symmetry is rarely perfect (small
  decorative differences, weathering, etc.); detector noise
  sometimes finds enough non-symmetric matches to disambiguate.
  The failure is most reliable on synthetic-symmetric or
  highly-regular targets.

## Runnable demonstration on a synthetic symmetric scene

A genuinely symmetric dataset is not part of the Agisoft sample
collection. The article's hypothesis is testable on any
controlled synthetic dataset (e.g., a rendering of a
bilaterally-symmetric building from two opposite angles, treated
as two chunks).

> **Demo verified:** ✗ — pending Tier 3 reproduction on a
> controlled symmetric-structure dataset. The failure mode
> described is inferred from the matcher's design; empirical
> confirmation is required before this article's claims can be
> promoted to observed.

```python
"""Test the symmetric-structure failure mode hypothesis.

Pre-condition: two chunks photographing a bilaterally-symmetric
structure from opposite (mirror-image) sides. The structure
should have visually-distinct asymmetric features in some images
to act as an oracle for whether the alignment is correct.
"""
import Metashape

doc = Metashape.app.document
chunk_a = doc.chunks[0]      # left-side capture
chunk_b = doc.chunks[1]      # right-side capture (opposite-symmetric)

# Sanity: each chunk aligns fine on its own.
assert sum(1 for c in chunk_a.cameras if c.transform is not None) > 0
assert sum(1 for c in chunk_b.cameras if c.transform is not None) > 0

# Attempt point-based align.
doc.alignChunks(chunks=[chunk_a.key, chunk_b.key],
                reference=chunk_a.key, method=0)

T_b = chunk_b.transform.matrix
print(f"chunk_b transform after method=0:")
print(f"  translation : {T_b.translation()}")
print(f"  determinant : {T_b.det()}")

# Manual visual inspection: merge with no link options and check
# the 3D viewport for overlap of mirror-equivalent geometry.
doc.mergeChunks(chunks=[chunk_a.key, chunk_b.key],
                merge_markers=False, merge_tiepoints=False)
```

**Expected output:** *for a sufficiently-symmetric input*, the
merged 3D viewport shows visible mirror-equivalent overlap of
geometry. Re-running with `method=1` (marker-based, with
non-symmetric markers placed) should produce a correct
alignment, confirming that the failure was symmetry-driven.

## References

- *Metashape Python Reference* (2.3.1), `Document.alignChunks` —
  documents the three `method` values (0/1/2) without warnings
  about content-symmetry-driven failures.
- [The three `alignChunks` methods](../chunks/alignchunks-three-methods.md) — companion article on the matcher's
  silent-failure modes when matches are not found.
- [Synthetic position priors via `ReferencePreselectionSource`](synthetic-priors-reference-preselection.md) — Workaround 2.
- [`mergeChunks` does not deduplicate cameras](../chunks/no-camera-deduplication.md) — caveat that applies after the merge step that
  follows `alignChunks`.
