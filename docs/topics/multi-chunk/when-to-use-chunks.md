---
title: "When to use chunks: dataset partitioning strategies"
status: unverified
applies_to: Metashape Pro 2.x and Standard 2.x — same `Document.addChunk` / `mergeChunks` API as PhotoScan 1.x
edition: "Pro / Standard"
last_reviewed: 2026-05-29
diataxis: explanation
confidence: high
---

# When to use chunks: dataset partitioning strategies

> **Confidence:** *high.* The strategic guidance is consistent
> across the official manual + multi-thread forum discussion;
> the chunk-API surface (`Document.addChunk`, `mergeChunks`,
> `alignChunks`) is introspection-confirmed on Metashape 2.2.

## What is a chunk

A **chunk** in Metashape is an independent processing unit:
its own camera set, tie-point cloud, point cloud, mesh,
texture, orthomosaic, and DEM. Multiple chunks live in one
project file (`Document`), can be processed in any order, and
can be merged or aligned with each other.

The default workflow uses a single chunk for the entire
project. Splitting into multiple chunks adds operational
complexity but unlocks scenarios that single-chunk processing
can't handle.

## Decision matrix

| Project | Recommendation |
|---------|---------------|
| Single drone flight, ~500-2000 images | Single chunk |
| Multi-day survey, 5,000+ images per session | One chunk per session, merge at end |
| Aerial > 5km² at high resolution | Split-in-chunks for mesh; single chunk for DEM |
| Mixed terrain + dense urban | Per-region chunks with appropriate surface types |
| Before / after monitoring | One chunk per epoch |
| Hybrid LiDAR + photogrammetry | One chunk per modality, merge after independent alignment |

The rest of the article unpacks each row's reasoning, the
operational strategies for splitting, and the merge step.

## Reasons to split into chunks

### 1. Memory limits

A single chunk's *Build Mesh* operation loads the entire mesh
into RAM. For large aerial projects (kilometres of coverage at
high resolution), this exceeds even high-end workstation RAM.
Splitting the area into chunks bounded by their own bounding
boxes keeps each Build Mesh tractable.

The Agisoft-published [`split_in_chunks.py`](https://github.com/agisoft-llc/metashape-scripts)
script automates this: subdivide the project's bounding box
into N×N regions, copy cameras and point cloud to per-region
chunks, build mesh per chunk, then merge.

### 2. Independent capture sessions

Multi-day surveys, multiple teams, or multi-flight datasets
often warrant per-session chunks during initial alignment, then
merged once each session has its own clean alignment. Errors
in one session don't contaminate the others.

### 3. Different processing parameters per region

A project that mixes terrain (Height field) with detailed
buildings (Arbitrary surface) benefits from per-region chunks
each built with the appropriate surface type. See
[Mesh surface types](../../workflow/mesh/mesh-surface-types.md).

### 4. Comparison / change detection

Before / after epoch surveys are naturally per-epoch chunks.
Aligning them via *Align Chunks* puts them in a common
coordinate frame; computing differences (volumes, height
changes) operates on the matched chunks. See
[Comparing chunks for change detection](../scripting/chunk-diff-volume-workflows.md).

### 5. Multi-camera-rig consolidation

A project with 4 different cameras (e.g., RGB drone + thermal
drone + ground LiDAR + handheld) may align each modality
separately into its own chunk, then merge. The merged chunk
inherits camera positions from the first-aligned but each
chunk's calibrations stay distinct.

## Reasons NOT to split into chunks

### 1. The single-chunk version fits in memory

Splitting adds work (configure split, manage merge step,
handle the `mergeChunks` deduplication gotcha — see
[`mergeChunks` does not deduplicate cameras](../../workflow/chunks/no-camera-deduplication.md)).
If the single-chunk Build Mesh runs in available RAM, splitting
adds no value.

### 2. The chunks would each be tiny

Below ~50 cameras per chunk, the bundle adjustment becomes
under-determined and alignment quality drops. The classic
guidance: minimum 50-100 well-distributed cameras per chunk
for reliable alignment.

### 3. The result needs continuous processing

A single orthomosaic export across a multi-chunk project
requires merging the chunks first. If you'll merge anyway,
ask whether the split provided value compared to a single-
chunk approach.

## Strategies for splitting

### Spatial partition (the most common case)

Use `split_in_chunks.py` with an N×N or M×K grid; each chunk
covers an axis-aligned bounding-box region. Empty / sparse
regions get skipped via the empty-chunk handling pattern (see
[Mesh and point-cloud editing recipes](../scripting/mesh-pointcloud-editing-recipes.md),
Recipe 5).

The recommended N depends on dataset density:

| Total images | Suggested N (for N×N split) |
|-------------:|:---------------------------:|
| ~5,000 | 2 |
| ~20,000 | 3-4 |
| ~50,000 | 5-6 |
| 100,000+ | 8+ |

### Temporal partition

For multi-epoch / multi-flight datasets, partition by
acquisition session. Each chunk's `chunk.label` records the
session date; the merge step happens after all per-session
alignments are clean.

### Modality partition

For mixed-sensor projects (drone RGB + drone thermal + ground
camera), partition by sensor type. Each chunk's calibration
is computed independently. The merge step uses *Align Chunks*
with `method=Marker` if shared markers are visible across
modalities, or `method=PointCloud` for ICP-style alignment of
the point clouds.

## Merging chunks

Three different operations the GUI labels similarly:

| Operation | What it does |
|-----------|--------------|
| `Document.mergeChunks` | Combines selected chunks into one new chunk; cameras from each become independent (per-source) groups; tie points stay per-source unless `merge_tiepoints=True`. See [the mergeChunks Series](../../workflow/chunks/what-mergechunks-does.md). |
| *Align Chunks* | Computes a transform between source chunks so they share a frame; doesn't merge them. Use before mergeChunks when chunks are not yet co-registered. See [The three `alignChunks` methods](../../workflow/chunks/alignchunks-three-methods.md). |
| Manual rebuild | Discard chunks, rebuild from a single union chunk. Sometimes faster than the merge for problematic datasets. |

The mergeChunks Series in `workflow/chunks/` covers the
operational details (camera deduplication, tie-point merging,
the `keep_keypoints=True` prerequisite for cross-chunk tie
points).

## Recipe — split, process, merge

A skeleton showing the full workflow:

> **Demo verified:** ✗ — pending Tier 3 reproduction on a real Metashape install.

```python
import Metashape

doc = Metashape.app.document

# Assumes one already-aligned chunk with cameras; split into 3x3 grid
# (Use the agisoft-llc/metashape-scripts split_in_chunks.py for production)
src = doc.chunks[0]

# Per-chunk processing (skipping the actual split mechanics here)
for chunk in doc.chunks:
    if not chunk.cameras:
        continue
    try:
        chunk.buildDepthMaps(downscale=2)
        chunk.buildPointCloud(point_confidence=True)
        chunk.buildModel(
            surface_type=Metashape.SurfaceType.HeightField,
            source_data=Metashape.DataSource.DepthMapsData,
        )
    except Exception as e:
        print(f"Skipped {chunk.label}: {e}")
        continue

# Merge into a final chunk
doc.mergeChunks(
    chunks=[c.key for c in doc.chunks if c.label.startswith("region_")],
    merge_models=True,
    merge_dense_clouds=True,
    merge_tiepoints=False,         # see merge-tiepoints article
)
```

For the empty-chunk handling and the production recipe, see
[Mesh and point-cloud editing recipes Recipe 5](../scripting/mesh-pointcloud-editing-recipes.md).

## Caveats

- **Cameras don't deduplicate across chunks at merge.** Two
  source chunks each containing camera `IMG_0042.JPG` produce
  two separate camera entries in the merged chunk. See
  [`mergeChunks` does not deduplicate cameras](../../workflow/chunks/no-camera-deduplication.md).
- **`merge_tiepoints=True` requires `keep_keypoints=True` at
  match time.** If you forgot the keep_keypoints flag, the
  merged tie-point set will be small and the bundle adjustment
  on the merged chunk will be poor. See
  [The `merge_tiepoints` option (and the `keep_keypoints`
  prerequisite)](../../workflow/chunks/merge-tiepoints-and-keep-keypoints.md).
- **Per-chunk reference data should be consistent.** If chunk
  A has GCPs in WGS84 and chunk B has GCPs in UTM, *Align
  Chunks* via Marker method gets confused. Set the project
  CRS consistently before importing reference data.
- **Splitting after dense-cloud generation works** but
  requires copying the point cloud's per-camera depth maps
  into each child chunk. The split_in_chunks script handles
  this; manual splitting is error-prone.
- **Texture across merged chunks.** Each source chunk's
  texture image is preserved in the merge; the merged chunk
  doesn't get a single unified texture unless you re-run
  Build Texture on the merged result.
- **`mergeChunks` is non-destructive.** The source chunks
  remain in the document; you can delete them after
  verifying the merge.

## See also

- [What `mergeChunks` actually does](../../workflow/chunks/what-mergechunks-does.md)
  — Part 1 of the mergeChunks Series.
- [`mergeChunks` does not deduplicate cameras](../../workflow/chunks/no-camera-deduplication.md)
  — Part 2.
- [The `merge_tiepoints` option (and the `keep_keypoints`
  prerequisite)](../../workflow/chunks/merge-tiepoints-and-keep-keypoints.md)
  — Part 3.
- [The three `alignChunks` methods](../../workflow/chunks/alignchunks-three-methods.md)
  — pre-requisite for merging chunks not already in a common
  frame.
- [Comparing chunks for change detection](../scripting/chunk-diff-volume-workflows.md)
  — uses chunks-as-epochs for monitoring workflows.
- [Mesh and point-cloud editing recipes](../scripting/mesh-pointcloud-editing-recipes.md)
  — Recipe 5 (empty-chunk handling) and Recipe 6 (mesh
  splitting into N×N tiles).

## References

- *Metashape Pro User Manual* (2.3), ch. 4 *Working with chunks*
  — covers chunk creation, the Workspace pane, and merging.
- *Metashape Python API Reference* (2.3.1):
  `Document.chunks`, `Document.addChunk`, `Document.mergeChunks`,
  `Chunk.label`, `Chunk.cameras`, `Chunk.copy`.
- [`split_in_chunks.py`](https://github.com/agisoft-llc/metashape-scripts/blob/master/src/split_in_chunks_dialog.py)
  — Agisoft's reference implementation of spatial chunk
  partitioning.

