---
title: "Point cloud confidence values: what they mean and how to filter"
status: unverified
applies_to: Metashape Pro 2.x — and PhotoScan 1.4+ via the same `Point.confidence` API; also applies to mesh vertex confidence on built models
edition: Pro
last_reviewed: 2026-06-05
diataxis: how-to
confidence: high
---

# Point cloud confidence values: what they mean and how to filter

> **Confidence:** *high.* The confidence-value semantics are
> directly attested by Agisoft support with permalinks (2020,
> 2022). The `Point.confidence` API and the *Filter by
> Confidence* GUI workflow are introspection-confirmed on
> Metashape 2.2.

## Problem

You've built a dense point cloud. Some regions look noisy or
spurious — areas where Metashape's matcher had little
confidence in the depth values it produced. You want to:

- Understand what the per-point confidence value actually
  measures.
- Filter or remove low-confidence points programmatically.
- Export confidence as a per-point attribute for downstream
  tools (CloudCompare, QGIS, GIS pipelines).

> **Quick answer.** Each point's confidence is **the number
> of depth maps that contributed to it** — an integer count,
> not a probability. Mesh vertices use a similar concept but
> store a **float** (averaged depth-map count over a vertex
> neighbourhood). Higher = more cross-camera agreement = more
> trustworthy.

## Context: what `Point.confidence` measures

The confidence value on each point in `chunk.point_cloud.points`
is **the number of depth maps that contributed to that point's
generation**. It's an integer count, not a probability or
quality score:

> "For the dense cloud points the confidence value means the
> number of the depth maps involved to the point generation
> process. The value is integer."
> — Agisoft support, 2022-04-07, Metashape 1.8
> ([permalink](https://www.agisoft.com/forum/index.php?topic=14381.msg63268#msg63268))

A point with `confidence=5` was independently observed by 5
depth maps; the matcher fused those depth values into one 3D
point. A point with `confidence=1` came from a single depth
map — no cross-camera verification, more likely to be noise.

For the **mesh** built from the point cloud, the per-vertex
confidence is different:

> "The confidence value for the mesh vertices carries the
> statistical information about the averaged number of depth
> maps used for the model reconstruction in the neighborhood
> of the given vertex. The value is float."
> — Agisoft support, same thread

So:

| Object | Confidence type | What it measures |
|--------|----------------|------------------|
| `Point.confidence` (point cloud) | int | Depth-map count for this exact point |
| `Vertex.confidence` (mesh) | float | Local-neighbourhood average depth-map count |

## Filtering low-confidence points (GUI)

The standard cleanup workflow Agisoft support recommends:

> "You can use the confidence filter to show only those points
> that you would like to remove, then select and delete those
> points and after that reset filter."
> — Agisoft support, 2020-02-09, Metashape 1.6
> ([permalink](https://www.agisoft.com/forum/index.php?topic=11817.msg52924#msg52924))

Step-by-step:

1. *Tools → Point Cloud → Set Confidence Filter…*
2. Set the visible range to the *high*-confidence end first
   (e.g., 3 to max). Verify visually that the surviving points
   look correct.
3. Reset, then set the visible range to the *low*-confidence
   end (e.g., 0 to 2).
4. Select all visible (`Ctrl+A` / `Cmd+A`) → *Delete*.
5. *Reset Filter* (or set range back to full) — the surviving
   high-confidence points become the active cloud.

## Filtering low-confidence points (Python)

The 2.x point-cloud API does not expose per-point iteration or
a single "delete by confidence" call. The recommended Python
approach uses the same `setConfidenceFilter` primitive as the
GUI, paired with the chunk's region or a polygon as the
selection:

> **Demo verified:** ✗ — pending Tier 3 reproduction on a real Metashape install.

```python
import Metashape

chunk = Metashape.app.document.chunk
pc = chunk.point_cloud   # in 1.x this was chunk.dense_cloud

threshold = 3   # remove points with confidence < threshold

# Step 1: limit visibility to the to-be-removed confidence range
pc.setConfidenceFilter(0, threshold - 1)

# Step 2: select the visible points by selecting the chunk's full region
#         (selection respects the active confidence filter)
pc.selectPointsByRegion(chunk.region)

# Step 3: delete the selection
pc.removeSelectedPoints()

# Step 4: restore unfiltered visibility
pc.resetFilters()

print(f"Cleanup at confidence < {threshold} done.")
```

The pattern: the visibility filter narrows the cloud to the
deletion candidates; the region selection grabs them all; the
remove call deletes them. Subtleties:

- `selectPointsByRegion(chunk.region)` selects every point
  *currently visible* inside the chunk's bounding box.
  Combined with the confidence filter, this effectively
  selects the low-confidence points without needing per-point
  iteration.
- `removeSelectedPoints()` honours the selection; the
  confidence filter does NOT need to be in place during the
  removal call (only during the selection call).

For spatially-bounded cleanup (e.g., remove low-confidence
points only inside a polygon shape), use
`selectPointsByShapes` instead:

> **Demo verified:** ✗ — pending Tier 3 reproduction on a real Metashape install.

```python
boundary = next(s for s in chunk.shapes if s.label == "cleanup_zone")
pc.setConfidenceFilter(0, 2)
pc.selectPointsByShapes([boundary])
pc.removeSelectedPoints()
pc.resetFilters()
```

If you need confidence-range diagnostics without modifying the
cloud, use the filter as a visualisation tool only and skip the
selection / remove steps. Combined with `point_count` per
filter range you can build a histogram:

> **Demo verified:** ✗ — pending Tier 3 reproduction on a real Metashape install.

```python
pc.setConfidenceFilter(0, 1)
print(f"conf 0-1: {pc.point_count} points")
pc.setConfidenceFilter(2, 4)
print(f"conf 2-4: {pc.point_count} points")
pc.setConfidenceFilter(5, 255)
print(f"conf 5+: {pc.point_count} points")
pc.resetFilters()
```

(The exact behaviour of `point_count` against the active
filter is best verified empirically; treat the recipe above as
a template to confirm on your install.)

## Exporting confidence as a per-point attribute

For LAS / LAZ output, confidence is exported via the *extra
bytes* concept introduced in LAS 1.4:

> "Confidence is exported to LAS/LAZ formats via the extra
> bytes concept introduced in the LAS 1.4 specification."
> — Agisoft support, 2020-10-16, Metashape 1.6
> ([permalink](https://www.agisoft.com/forum/index.php?topic=12270.msg56225#msg56225))

The Python export:

> **Demo verified:** ✗ — pending Tier 3 reproduction on a real Metashape install.

```python
import Metashape

chunk = Metashape.app.document.chunk

chunk.exportPointCloud(
    "/path/output.las",
    source_data=Metashape.DataSource.PointCloudData,
    save_point_confidence=True,   # write confidence as extra-bytes field
    save_point_intensity=True,    # often paired with confidence in QA workflows
    crs=chunk.crs,
)
```

`save_point_confidence=True` is the default, but stating it
explicitly makes the script's intent clear. The exported field
is readable in CloudCompare (`Tools → Other → SF → Set SF as
intensity`) and in QGIS-with-LAS-plugin.

## Recommended threshold values

There is no universally-correct threshold; choice depends on
the dataset's overlap pattern. Empirical baselines:

| Project type | Suggested low-conf threshold | Rationale |
|--------------|:---------------------------:|-----------|
| High-overlap aerial (≥80% side, ≥60% forward) | 3 | Most legitimate points see ≥3 depth maps |
| Medium-overlap aerial (60-80% side) | 2 | Many edge points only have 2 observers |
| Low-overlap aerial / handheld terrestrial | 2 | Aggressive cleanup risks deleting valid points |
| Drone close-range / orbit | 4-5 | High redundancy expected; aggressive cleanup is safe |

To tune the threshold interactively before scripted use, run
the GUI's *Tools → Point Cloud → Set Confidence Filter…* and
move the slider while watching which areas disappear. Pick the
threshold value that hides the noise without removing visible
geometry.

## The classification connection

The *Point Cloud → Classify Points* workflow respects the
confidence filter. If you've filtered to high-confidence-only
before classifying ground points, the classifier ignores the
hidden low-confidence noise and produces cleaner classes.

> "`list(range(128))` — creates the list of ints, that defines
> the classes of the dense cloud (all classes, actually)."
> — Agisoft support, 2021-04-29, Metashape 1.7
> ([permalink](https://www.agisoft.com/forum/index.php?topic=12114.msg59880#msg59880))

For batch classification using the confidence filter as a
pre-clean step (the classify method lives on the PointCloud
in 2.x, not on the Chunk):

> **Demo verified:** ✗ — pending Tier 3 reproduction on a real Metashape install.

```python
chunk.point_cloud.setConfidenceFilter(3, 255)   # show only conf >= 3
chunk.point_cloud.classifyGroundPoints(
    max_angle=10.0,
    max_distance=1.0,
    cell_size=50.0,
    erosion_radius=0.5,
)
chunk.point_cloud.resetFilters()
```

For the parameters of `classifyGroundPoints` itself, see
[Ground classification: the erosion radius parameter](ground-classification-erosion-radius.md).

## Caveats

- **Confidence depends on processing settings.** A point cloud
  built with `quality=Low` (4× downscaled depth maps) has
  fewer per-pixel depth observations than a `quality=High`
  cloud, so confidence values are systematically lower.
  Compare confidences only across clouds built with the same
  parameters.
- **Confidence is computed at build time, not stored from
  matching.** If you re-run *Build Point Cloud* with new
  depth maps, the confidence values change. Save the LAS/LAZ
  export if you need historical confidence for QA records.
- **Mesh vertex confidence is float, not int.** Post-meshing
  scripts that assume `int` will misbehave. The mesh path is
  separate from the point-cloud path; treat them as different
  data types even though they share the name "confidence."
- **GUI confidence filter only affects display.** Unless you
  *delete* the hidden points, they remain in the cloud — just
  invisible. For permanent cleanup, follow the show-low →
  select-all → delete pattern.
- **The 1.x → 2.x rename.** `chunk.dense_cloud` became
  `chunk.point_cloud` at the 2.0 transition. Old scripts using
  `dense_cloud.points[i].confidence` need the rename to work
  on 2.x.

## See also

- [Ground classification: the erosion radius parameter](ground-classification-erosion-radius.md)
  — the `classifyGroundPoints` workflow that pairs naturally
  with confidence filtering.
- [`exportPointCloud` defaults: GUI vs Python CRS difference](../export-reporting/exportpoints-crs-default.md)
  — the broader export-CRS gotcha that applies to confidence
  export too.
- [Mesh and point-cloud editing recipes](../../topics/scripting/mesh-pointcloud-editing-recipes.md)
  — for further programmatic point-cloud manipulation.
- [`main/dense_cloud_max_neighbors` tweak (in *Undocumented tweaks*)](../../topics/scripting/undocumented-tweaks-reference.md)
  — affects how many depth maps contribute to each point,
  which directly affects confidence values.

## References

- *Metashape Pro User Manual* (2.3), ch. 5 *Point cloud → Filter
  Points by Confidence*.
- [*Point cloud editing with confidence filter tool* (Agisoft KB)](https://agisoft.freshdesk.com/support/solutions/articles/31000162209)
  — Agisoft's walkthrough of Calculate point confidence, Filter by
  Confidence (which hides, not deletes), and the select-then-delete
  cleanup.
- *Metashape Python API Reference* (2.3.1):
  `Chunk.point_cloud`, `PointCloud.setConfidenceFilter`,
  `PointCloud.setSelectionFilter`, `PointCloud.selectPointsByShapes`,
  `PointCloud.selectPointsByRegion`, `PointCloud.removeSelectedPoints`,
  `PointCloud.cropSelectedPoints`, `PointCloud.resetFilters`,
  `PointCloud.classifyGroundPoints`, `PointCloud.point_count`,
  `PointCloud.Point.confidence`, `Chunk.exportPointCloud`.
- Forum thread, [*Confidence math*, 2022](https://www.agisoft.com/forum/index.php?topic=14381.msg63972#msg63972)
  — point vs mesh-vertex confidence semantics; integer vs
  float distinction.
- Forum thread, [*Remove Points By Confidence*, 2020](https://www.agisoft.com/forum/index.php?topic=11817.msg52924#msg52924)
  — canonical filter-then-delete workflow.
- Forum thread, [*Export confidence as intensity*, 2020](https://www.agisoft.com/forum/index.php?topic=12270.msg58112#msg58112)
  — LAS 1.4 extra-bytes export mechanism.
- Forum thread, [*Removing low confidence dense cloud points*, 2021](https://www.agisoft.com/forum/index.php?topic=12114.msg59880#msg59880)
  — combined confidence filter + classification pattern.

