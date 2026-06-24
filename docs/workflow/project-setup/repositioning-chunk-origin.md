---
title: "Repositioning a chunk: moving the origin to a known point"
status: unverified
applies_to: Metashape Pro 2.x — and unchanged from PhotoScan 1.x via the same `chunk.transform.matrix` API
edition: Pro
last_reviewed: 2026-06-05
diataxis: how-to
confidence: high
---

# Repositioning a chunk: moving the origin to a known point

> **Confidence:** *high.* Three distinct approaches are forum-
> attested with permalinks (Agisoft support, 2018 + 2023); all
> referenced API surfaces (`chunk.transform.matrix`,
> `chunk.region`, `Move Object` tool) are introspection-confirmed.

> **Scope statement.** The official manual covers the
> *Reference* pane workflow for georeferencing (load coordinates
> for cameras / markers, click *Update Transform*) — this is
> approach 1 in the table below. The manual also briefly
> mentions the *Move Object* / *Rotate Object* tools (approach
> 3). This article picks up where the manual stops: the **three
> approaches compared side-by-side**, two concrete Python
> recipes for direct `chunk.transform.matrix` manipulation
> (approach 2), and explicit "when to pick which" guidance
> based on whether you have surveyed reference points, want
> programmatic control, or just need a quick visual nudge.

## Problem

After alignment, the chunk's coordinate origin is in an arbitrary
location: the centroid of the tie-point cloud, or the first
camera's position, or some EXIF-derived geographic coordinate.
You need the origin to land on a specific feature: the corner of
a building, the centre of a turntable, a known marker, or
exactly `(0, 0, 0)` for downstream tools that expect a clean
origin.

## Three approaches

> "The position of the model in space can be performed using one
> of the following approaches:
>
> - setting the coordinate system (Professional edition only) by
>   using the coordinate information for cameras and/or markers,
> - using Python scripting (also available in Professional
>   edition only) to perform additional transformation to the
>   complete alignment results (including all the chunk contents:
>   cameras, point clouds, mesh, etc.) that would move the
>   model's origin to the user-defined location (for example, to
>   the coordinate system origin),
> - using Rotate Object and Move Object tools to modify the
>   model location and orientation in space."
> — Alexey Pasumansky, 2018-06-27, PhotoScan 1.4
> ([permalink](https://www.agisoft.com/forum/index.php?topic=9240.msg43080#msg43080))

| Approach | Effort | Persists across re-build | Notes |
|----------|--------|--------------------------|-------|
| 1. **Markers + Reference pane** | GUI, low effort | Yes | Set marker coordinates in the Reference pane; *Update Transform* aligns the chunk to those references |
| 2. **Python `chunk.transform.matrix`** | Python, moderate | Yes | Modify the 4×4 transform matrix directly; affects everything in the chunk |
| 3. **Move / Rotate Object tools** | GUI, low effort | No (visualization-only by default) | Drags the model in 3D view; useful for quick framing but not part of the persistent transform |

Approach 1 is the recommended workflow when you have known
coordinates for at least 3 points (markers or cameras).
Approach 2 gives full programmatic control. Approach 3 is for
quick visual repositioning, not for downstream-tool exports.

## Approach 1 — Markers + Reference pane

For georeferenced or local-coordinate workflows where the
target origin is known by surveyed points:

1. Place markers on visible features whose coordinates you know
   (corner of a building at `(0, 0, 0)`; second corner at
   `(10, 0, 0)`; third corner at `(0, 10, 0)`).
2. In the *Reference* pane, enter each marker's known
   coordinates in the **Source values** column.
3. Click *Update Transform* (the gear icon, top of the pane).
4. The chunk is rotated, translated, and scaled (similarity
   transform) to fit the markers to their reference values.
5. *Optimize Cameras* afterwards if marker residuals warrant
   it.

The persistent state lives in `chunk.transform.matrix` plus the
markers' projections — re-opening the project preserves the
repositioning.

## Approach 2 — Python `chunk.transform.matrix`

For programmatic / batch workflows or when no surveyed markers
are available:

> "Mesh model doesn't have its own coordinate system, so it is
> following chunk.crs and chunk.transform. Therefore to move
> the model's origin you need to modify chunk.transform.matrix,
> so that its translation component (last column of the matrix)
> points to the desired origin location."
> — Alexey Pasumansky, 2023-02-16, Metashape 2.0
> ([permalink](https://www.agisoft.com/forum/index.php?topic=9240.msg66440#msg66440))

### Recipe: move chunk origin to the model's geometric centre

> **Demo verified:** ✗ — pending Tier 3 reproduction on a real Metashape install.

```python
import Metashape

def move_origin_to_model_center(chunk):
    """Move the chunk origin so that the model's centroid is at world (0,0,0)."""
    model = chunk.model
    if not model:
        print("No model in chunk; nothing to do.")
        return

    # Sample up to ~10K vertices to estimate centroid (fast for large meshes)
    vertices = model.vertices
    step = max(1, len(vertices) // 10_000)

    sum_local = Metashape.Vector([0, 0, 0])
    n = 0
    for i in range(0, len(vertices), step):
        sum_local += vertices[i].coord
        n += 1
    if n == 0:
        return
    centroid_local = sum_local / n

    # Build a translation in world space that maps centroid → (0, 0, 0)
    T = chunk.transform.matrix
    centroid_world = T.mulp(centroid_local)
    new_T = Metashape.Matrix.Translation(-centroid_world) * T
    chunk.transform.matrix = new_T

move_origin_to_model_center(Metashape.app.document.chunk)
```

The `chunk.transform.matrix` change immediately propagates to:
the tie-point cloud, point cloud, mesh, depth maps, orthomosaic,
DEM, and all marker / camera world positions.

### Recipe: align chunk so a specific marker is at the origin

> **Demo verified:** ✗ — pending Tier 3 reproduction on a real Metashape install.

```python
import Metashape

chunk = Metashape.app.document.chunk
target_label = "M1"  # the marker that should land at (0,0,0)

target_marker = next((m for m in chunk.markers if m.label == target_label), None)
if target_marker is None:
    raise ValueError(f"marker {target_label!r} not found")

# Marker.position is in chunk-local coords; project to world via T
T = chunk.transform.matrix
marker_world = T.mulp(target_marker.position)

# Translate so the marker lands at world origin
chunk.transform.matrix = Metashape.Matrix.Translation(-marker_world) * T
```

This translates without rotating. To also rotate so a marker
pair defines an axis, see
[Orthomosaic in a marker-defined planar projection](../orthomosaic/marker-defined-projection.md)
for the matrix construction recipe (the same construction
applies to chunk re-orientation).

## Approach 3 — Move / Rotate Object tools

In the GUI's *Model* view: *Tools → Rotate Object* and
*Tools → Move Object* let you drag the displayed geometry. By
default this is **visualisation-only**: it changes how the model
is rendered without modifying `chunk.transform.matrix`. To
persist the change, use *Tools → Apply Transform* (which writes
the visualization transform into the chunk).

This approach is best when:

- You need a quick re-frame for a screenshot or video.
- You want to nudge the model 0.5 m before adding markers.
- You're exploring options before committing to one of the
  scripted approaches.

It is NOT recommended for production workflows because the
transformation is hard to reproduce (mouse-drag values are not
recorded).

## Caveats

- **`chunk.region` is independent of `chunk.transform.matrix`**.
  Repositioning the chunk does NOT automatically resize or
  reposition the region (bounding box). After
  approach 2, call `chunk.resetRegion()` to recompute the region
  to encompass the relocated geometry. See [Setting `chunk.region`
  to bound the tie-point cloud](setting-the-chunk-region.md).
- **Markers' `marker.position` is in chunk-local coordinates,
  not in CRS coordinates.** For approach 1 to work, the
  markers' source coordinates in the Reference pane must be in
  the chunk's CRS (or you must change the chunk CRS to match
  what your reference values are in).
- **Re-running alignment after the transform** preserves the
  manual transform — `chunk.matchPhotos` and `chunk.alignCameras`
  use the existing tie-point cloud, but they do NOT re-derive a
  fresh `chunk.transform.matrix` unless you also use *Reset
  Current Alignment*.
- **The scale component** of `chunk.transform.matrix` is set
  during alignment (1.0 for un-georeferenced chunks; some metres-
  per-chunk-unit value for georeferenced ones). Multiplying the
  whole matrix by a translation preserves the scale; multiplying
  by a scale matrix would also re-scale all geometry.

## See also

- [*Exported model becomes less detailed and ripples* (Agisoft KB)](https://agisoft.freshdesk.com/support/solutions/articles/31000162477)
  — if the reason you are repositioning is that large
  Easting/Northing values truncate on model export (the "blocky"
  mesh), the Export Model *Shift* fields or *Local Coordinates*
  option fix it per-export, without moving the chunk.
- [Setting `chunk.region` to bound the tie-point cloud](setting-the-chunk-region.md)
- [`chunk.transform.matrix` is local→world; `camera.transform` is local](../../topics/crs/chunk-frame-vs-camera-frame.md)
- [Orthomosaic in a marker-defined planar projection](../orthomosaic/marker-defined-projection.md)
- [Custom vertical datums: adding a geoid undulation grid](custom-geoid-vertical-datum.md)

## References

- *Metashape Pro User Manual* (2.3), ch. 4 *Improving camera
  alignment* — describes the *Reference* pane and *Update
  Transform* workflow.
- *Metashape Python API Reference* (2.3.1):
  `Chunk.transform`, `Matrix.Translation`, `Matrix.mulp`,
  `Chunk.resetRegion`.
- Forum thread, [*How to position object on zero point?*, 2018-2023](https://www.agisoft.com/forum/index.php?topic=9240.0)
  — three-approach overview (msg 44103) +
  `chunk.transform.matrix` recipe (msg 69113).

