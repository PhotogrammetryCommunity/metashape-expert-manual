# Components view (Workspace pane)

> **Status:** documented (2026-05-24).

## What it is

The *Components* view, available in the *Workspace* pane on
Metashape 1.7+, displays the connected components of the
chunk's tie-point graph after alignment. Each *component* is
a sub-set of cameras the bundle solved as one rigid block;
two cameras are in the same component if and only if there's
a path of shared tie points between them.

A healthy alignment produces **one component** containing all
cameras. Multiple components signal that the bundle has *not*
found a globally-consistent solution — even if every camera
reports as aligned, the chunk is internally split into
disconnected sub-blocks held together only by the shared
chunk transform (georeferencing, etc.). This is the
"ghosting" symptom: the model looks coherent but exhibits
seams or duplications between sub-blocks.

## Where it lives

| | Standard | Pro |
|---|---|---|
| **GUI** | *Workspace* pane → click on a chunk → expand the *Tie point cloud* node → expand the *Components* sub-node | (same) |
| **Python** | `chunk.components` (list) and `chunk.component` (active component) | (Pro only) |
| **Available since** | Metashape 1.7 | Metashape 1.7 |

## How to inspect components in Python

```python
import Metashape

chunk = Metashape.app.document.chunk

# Number of components — the headline diagnostic.
print(f"components: {len(chunk.components)}")

# Per-component camera count.
for i, comp in enumerate(chunk.components):
    aligned = sum(1 for c in chunk.cameras
                  if c.transform is not None
                  and c in comp.cameras)
    print(f"  component {i}: {aligned} aligned cameras")

# The "active" component (the one the GUI considers default).
print(f"active component: {chunk.component}")
```

A `len(chunk.components) > 1` outcome is an alignment-quality
red flag, regardless of how many cameras report as aligned.

## What components mean for downstream stages

- **Build Dense Cloud / Depth Maps:** typically processes the
  active component only by default (verify on the *Reference*
  pane's region setting). Cameras in non-active components
  may be silently excluded.
- **Build Mesh / Build Tiled Model:** depends on the source
  data (depth maps follow component-active; tie-point-driven
  mesh uses the whole tie point cloud). Mixing components in
  a single mesh produces visible seams.
- **Export:** orthomosaic / point-cloud exports respect
  whatever the active component plus chunk region defines.
  Multi-component chunks need `mergeComponents()` first to
  produce a single coherent output.

## Merging and splitting components

```python
# Merge all components into one. Used after a manual fix
# (markers, transform import) brings the components close
# enough that the bundle should solve them as one.
chunk.mergeComponents()

# Split a single component into multiple by some criterion.
# Rarely needed; the typical path is mergeComponents after
# a fix.
chunk.splitComponents()
```

`mergeComponents()` does NOT add new tie points across
component boundaries — it only marks the components as
merged in the bundle's bookkeeping. To genuinely connect
disconnected components, you need either marker-based
linkage (markers projecting on cameras from both components)
or cross-block matching (`matchPhotos(cameras=[…],
reset_matches=False)` with carefully-chosen camera lists);
see [`mergeChunks` does not deduplicate cameras](../../workflow/chunks/no-camera-deduplication.md)
and [Adding cameras to an aligned chunk: the `keep_keypoints`
workflow](../../workflow/alignment/incremental-matching-keep-keypoints.md)
for the architectural strategies.

## Caveats

- **Component count vs aligned-camera count.** A chunk with
  100 cameras all reporting `c.transform is not None` but
  4 components is *worse* than 100 cameras aligned in 1
  component, even though both report 100% aligned. The
  diagnostic value is in the component count, not the
  aligned-camera count.
- **`chunk.component` (singular) is the *active* component.**
  Switching the active component changes which sub-block
  Build Dense Cloud / orthomosaic operations target. The
  default is the largest component.
- **Components is a 1.7+ feature.** Older PhotoScan / Metashape
  versions do not expose this view; the bundle still has the
  same connected-components structure internally, but you
  can't see it from the GUI.

## Related concepts

- *Tie point cloud* — the structure that defines components
  via shared-track membership.
- [Chunks and merging](../../workflow/chunks/index.md) — the
  multi-chunk architecture that motivates component-aware
  workflows.

## Articles in this manual

- [Diagnosing under-aligned chunks](../../workflow/alignment/diagnosing-under-aligned-chunks.md)
  — Components view is the second rung of the diagnostic
  ladder: "If you see more than one component, the bundle
  has *not* found a globally consistent solution."
- [`alignChunks(method=PointBased)` cannot break geometric
  symmetry](../../workflow/alignment/alignchunks-symmetric-scene-failure.md)
  — symmetric-scene failure mode shows up as multiple
  components after `alignChunks`.

## Forum threads worth reading

| Date | Version | Author | Thread | One-line takeaway |
|------|---------|--------|--------|-------------------|
| _stub_ | _stub_ | _stub_ | _stub_ | _Populated as insight cards on this feature accumulate._ |
