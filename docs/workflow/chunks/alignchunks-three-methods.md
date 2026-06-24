---
title: The three `alignChunks` methods (point / marker / camera)
status: unverified
applies_to: Metashape Pro 2.x — and unchanged from PhotoScan 1.x
edition: Pro
last_reviewed: 2026-05-22
diataxis: explanation
confidence: high
---

# The three `alignChunks` methods (point / marker / camera)

> **Confidence:** *high.* All three methods documented in the
> official manual; failure modes attested by Agisoft support
> with permalink. The `Document.alignChunks` Python signature
> (kwargs `method`, `fit_scale`, `downscale`,
> `generic_preselection`, `keypoint_limit`, `markers`) is
> introspection-confirmed on Metashape 2.2.

`Workflow → Align Chunks` has three radio-button modes. Each fits a
fundamentally different problem; substituting one for another
silently produces a poor alignment instead of a clean failure.

The Python entry point exposes the same three methods via an
integer argument:

```python
Metashape.Document.alignChunks(
    chunks=[…], reference=…,
    method=0,            # 0=point, 1=marker, 2=camera
    fit_scale=True,
    downscale=1,
    generic_preselection=False,
    keypoint_limit=40000,
    …
)
```

(introspected from Metashape 2.2.2)

## Method comparison

| Method | What it matches | Hard prerequisite | Failure mode |
|--------|----------------|------------------|---------------|
| `0` — point | Re-runs feature matching across cross-chunk image pairs; fits a transformation that maximises matched-point agreement. | Sub-chunks must photograph **visually overlapping content** (shared visual features). | Silent: succeeds with very few matches, fits a poor transformation, residual error large. |
| `1` — marker | Markers with shared `marker.label` in both chunks; fits a 7-parameter similarity (3R + 3T + scale when `fit_scale=True`). | Two or more shared markers, in non-degenerate configuration. | Silent no-op when the marker set is degenerate. |
| `2` — camera | Cameras with shared `camera.label` in both chunks; uses the cameras' chunk-frame poses as the alignment anchors. | Camera labels match exactly **and** the underlying physical positions match. | Silent no-op when no labels match. Useless result if labels match but cameras represent different positions. |

> "Camera based approach wouldn't work unless you have the images
> with the same labels in both chunks that represent exactly the
> same camera positions in the real world. Point based approach
> means that PhotoScan will be trying to find the matching points
> for the images from the different chunks, so if the image
> matching operation fails completely for the complete image set
> and no tie points are found for the images from light and dark
> sub-sets, the point based chunk alignment would likely fail."
> — Alexey Pasumansky, 2017-05-04, PhotoScan 1.3
> ([permalink](https://www.agisoft.com/forum/index.php?topic=6995.msg33747#msg33747))

## Diagnostic: did the alignment establish a transformation?

After *Align Chunks* succeeds, the source chunks carry an `[R]`
(*registered*) marker next to their labels in the *Workspace*
pane. **Absence of `[R]` means the alignment did not register the
chunks**, and any subsequent *Merge Chunks* will produce a useless
result (the chunks land in their default identity-transform
positions in the merged chunk).

```text
Workspace pane:
  Chunk 1 [R]    ← registered
  Chunk 2 [R]
  Chunk 3        ← NOT registered — alignment failed silently
```

In the Python API the equivalent check is on the chunk's
`transform.matrix` against the chunk-coordinate identity, but the
GUI cue is more direct.

## When each method actually fits

### `method=0` — Point based

Use when sub-chunks photograph genuinely overlapping content (e.g.
two flight passes covering an overlap zone). The alignment runs
matching across every cross-chunk image pair, so the cost grows
quadratically with the number of cameras involved — limit the
scope by passing only the relevant `chunks` argument.

The matches computed for the alignment fit are not persisted as
tie points in the source chunks. To obtain persistent cross-chunk
tie points, use the merge-time `merge_tiepoints=True` option (see
[The `merge_tiepoints` option](merge-tiepoints-and-keep-keypoints.md))
— this is the actual mechanism for retaining cross-chunk tie
points, not `alignChunks(method=0)`.

### `method=1` — Marker based

Use when GCPs or manually-placed markers exist with shared labels
in both chunks. The fit is a similarity transformation: 6 DOF when
`fit_scale=False`, 7 DOF when `fit_scale=True`. Two non-collinear
markers fix orientation but not scale; three non-collinear markers
fix all 7 DOF.

The marker-based fit is **purely geometric** — it uses only the
markers' chunk-frame coordinates, not the bundle. It cannot
correct for chunk-internal scale errors or rolling-shutter
distortions because it has no per-camera information.

### `method=2` — Camera based

Use when one chunk is a literal subset, regrouping, or near-clone
of another (same images, possibly different exclusion masks). The
matching is by `camera.label` only, with no awareness of whether
the images actually depict the same scene — match the labels and
the alignment will accept whatever poses they carry.

A common consequence: **duplicates after merge.** The merge
preserves both copies of any shared camera, with each copy's tie
points still anchored to its source chunk; see
[`mergeChunks` does not deduplicate cameras](no-camera-deduplication.md).

## Caveats

- **Failure modes are silent for all three methods.** Always check
  the `[R]` mark in the Workspace pane (or the chunk's
  `transform.matrix` in Python) before proceeding to *Merge
  Chunks*.
- **`method=0` is vulnerable to geometric symmetry.** When the
  source chunks photograph a structure with bilateral or
  rotational symmetry, the matcher can settle on a
  successful-looking-but-wrong alignment (mirror-equivalent or
  rotation-equivalent placement). The `[R]` mark appears, the
  bundle scores look fine, and yet the merged 3D viewport shows
  visible duplicate or mirrored geometry. See
  [`alignChunks(method=point)` cannot break geometric symmetry](../alignment/alignchunks-symmetric-scene-failure.md)
  for the diagnosis and three workarounds.
- **`method=0` cost is quadratic.** A 444-image chunk aligned
  point-based against another 444-image chunk runs ≈197 000
  candidate pairs. Use `keypoint_limit=` and `downscale=` to keep
  the cost manageable.
- **`method=1` does not perform bundle adjustment.** A successful
  marker-based alignment *can* leave large per-camera residuals —
  the markers fit, but the cameras' bundle relationship to the
  markers is whatever the source chunks left it as. Run
  *Optimize Cameras* afterwards if marker-residual quality is
  required.

## Runnable demonstration on the Building sample dataset

The script below tests the three methods on the
[Building](../../reference/sample-data.md#building) sample (50
images) split into two chunks, and prints the resulting
`chunk.transform.matrix` so you can compare what each method
produces.

> **Demo verified:** ✗ — pending Tier 3 reproduction on Metashape
> Pro 2.2 / 2.3 with the *Building* sample dataset. The underlying
> APIs are introspection-verified but the demo as written has not
> been run end-to-end. Required before the manual ships.

```python
"""Compare the three alignChunks methods on a split Building dataset.

Pre-condition: open the Building sample, split into two chunks
(cameras 0–24 in chunk_a, 25–49 in chunk_b), align both, place 3+
markers in both chunks with shared labels, and add overlap to the
camera labelling so method=2 has anchors.
"""
import Metashape

doc = Metashape.app.document
chunk_a = doc.chunks[0]
chunk_b = doc.chunks[1]
keys = [chunk_a.key, chunk_b.key]

for method, name in [(0, "point"), (1, "marker"), (2, "camera")]:
    # Reset chunk_b's transform to identity before each attempt.
    chunk_b.transform.matrix = Metashape.Matrix.Diag([1, 1, 1, 1])

    try:
        doc.alignChunks(chunks=keys, reference=chunk_a.key,
                        method=method)
        # Inspect the resulting transform.
        m = chunk_b.transform.matrix
        # Treat near-identity as "not registered" for diagnostic.
        registered = any(abs(m[i, j] - (1.0 if i == j else 0.0)) > 1e-6
                         for i in range(4) for j in range(4))
        status = "[R]" if registered else "(no transform)"
        print(f"method={method:>1} ({name:<6}): {status}")
        if registered:
            print(f"  translation = ({m[0,3]:.3f}, {m[1,3]:.3f}, {m[2,3]:.3f})")
    except RuntimeError as e:
        print(f"method={method:>1} ({name:<6}): RuntimeError: {e}")
```

**Expected output:** `method=0` registers if the two halves share
visual content. `method=1` registers if shared markers were placed.
`method=2` registers if camera labels were duplicated across the
chunks. The translation magnitudes should be similar across
successful methods (within the chunks' geometric agreement).

## References

- [Forum thread, *Merging Chunks*, 2017](https://www.agisoft.com/forum/index.php?topic=6995.0)
  — primary source; the failure-mode summary (msg 33625).
- [Forum thread, *Optimisation of Merged Chunks*, 2017](https://www.agisoft.com/forum/index.php?topic=6691.0)
  — extends the comparison to optimisation context (covered in
  [What `mergeChunks` actually does](what-mergechunks-does.md)).
- *Metashape Professional Edition User Manual* (2.3), §"Aligning
  chunks" — the official method descriptions.
