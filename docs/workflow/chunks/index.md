# Chunks and merging

Working with multiple chunks is one of the most architecturally
nuanced parts of a Metashape project. The mechanics of *Align
Chunks* and *Merge Chunks* are well-documented at the GUI level
in the official manual, but the *implications* — what gets
preserved, what gets lost, and what optimisation can and cannot do
across chunk boundaries — are scattered across forum threads
spanning a decade.

The articles in this section consolidate the architectural rules:

- **[What `mergeChunks` actually does](what-mergechunks-does.md)** —
  Why merging produces orientation, not connection. The
  `merge_markers` and `merge_tiepoints` flags are the only
  mechanisms that actually link sub-chunks for downstream
  optimisation.
- **[The three `alignChunks` methods](alignchunks-three-methods.md)** —
  Point-based, marker-based, and camera-based: when each fits the
  problem, what their failure modes look like (mostly silent), and
  how to spot a failed alignment before merging.
- **[The `merge_tiepoints` option](merge-tiepoints-and-keep-keypoints.md)** —
  Why the GUI checkbox is greyed out by default, what
  `keep_keypoints=True` does, and when retaining cross-chunk
  tie points is worth the processing cost.
- **[`mergeChunks` does not deduplicate cameras](no-camera-deduplication.md)** —
  The architectural reason post-merge deduplication is
  destructive, a deduplication script (with caveats), and three
  cleaner architectural strategies.

## Articles

- [The three `alignChunks` methods](alignchunks-three-methods.md)
- [What `mergeChunks` actually does](what-mergechunks-does.md)
- [`mergeChunks` does not deduplicate cameras](no-camera-deduplication.md)
- [The `merge_tiepoints` option](merge-tiepoints-and-keep-keypoints.md)

## Quick decision table

| Goal                                              | Method                                                |
|---------------------------------------------------|--------------------------------------------------------|
| Place sub-chunks in their relative positions only | `mergeChunks` defaults — no link options              |
| Have *Optimize Cameras* refine cross-chunk geometry | `merge_markers=True` (when GCPs/markers shared) **or** `merge_tiepoints=True` (when keypoints stored) |
| Re-introduce tie points across chunks at merge    | `merge_tiepoints=True` + `keep_keypoints=True` at align time |
| Avoid duplicate cameras                           | Don't share images across source chunks; or use marker-based linkage |
| Dedupe cameras after a camera-based merge         | Use the 1.0-era deduplication script — but only after building all dependent dense products |

## Related sections

- [Workflow → Photo alignment](../alignment/index.md) — single-chunk
  alignment fundamentals.
- [Workflow → Markers, GCPs, scale bars](../markers-gcps/index.md) —
  marker mechanics, prerequisite to `merge_markers`.
- [Workflow → Optimization & accuracy](../optimization/index.md) —
  how `Optimize Cameras` interacts with merged chunks.
