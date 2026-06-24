---
title: "Mesh and point-cloud editing recipes (Python)"
status: unverified
applies_to: Metashape Pro 2.x — and PhotoScan 1.x via the same Model / DepthMaps API
edition: Pro
last_reviewed: 2026-06-05
diataxis: how-to
confidence: high
---

# Mesh and point-cloud editing recipes (Python)

> **Confidence:** *high.* All API references
> (`chunk.model.renderDepth`, `chunk.depth_maps[].image`,
> `model.removeFaces`, `chunk.exportModel`) are
> introspection-confirmed on Metashape 2.2; recipes are forum-
> attested with permalinks.

A grab-bag of mesh and point-cloud editing recipes that
recur in forum support threads. Each is short, self-contained,
and exercises a concrete API. They are collected here so they
do not have to be re-derived for each new use case.

## Recipe 1 — Render depth from any camera pose

`chunk.model.renderDepth(transform, calibration)` produces a
depth map for an arbitrary pose / intrinsics, not limited to the
chunk's existing cameras. Useful for visibility analysis,
synthetic-stereo experiments, and orthorectification onto novel
view planes.

> **Demo verified:** ✗ — pending Tier 3 reproduction on a real Metashape install.

```python
import Metashape

chunk = Metashape.app.document.chunk
camera = chunk.cameras[0]

# Render from the camera's actual pose (mimics chunk.depth_maps[camera])
depth = chunk.model.renderDepth(
    camera.transform,
    camera.sensor.calibration,
)

# Or from a synthetic pose: identity transform = world origin
synth_T = Metashape.Matrix.Diag([1, 1, 1, 1])
synth_depth = chunk.model.renderDepth(synth_T, camera.sensor.calibration)
```

The returned `Image` holds **float32** values, not 8-bit grayscale.
To export as 8-bit PNG, normalise per-image:

> **Demo verified:** ✗ — pending Tier 3 reproduction on a real Metashape install.

```python
import numpy as np

arr = np.frombuffer(depth.tostring(), dtype=np.float32)
arr = arr.reshape(depth.height, depth.width)
valid = np.isfinite(arr)  # background pixels are NaN / inf
scaled = np.zeros_like(arr, dtype=np.uint8)
if valid.any():
    lo, hi = arr[valid].min(), arr[valid].max()
    scaled[valid] = ((arr[valid] - lo) / (hi - lo) * 255).astype(np.uint8)
# scaled is now ready to save with Pillow / OpenCV
```

> "renderDepth() is generating the depth in floating point
> format, so to get grayscale values in 0 - 255 range it would
> be necessary to transform the data 'manually'."
> — Alexey Pasumansky, 2016-11-04, PhotoScan 1.2
> ([permalink](https://www.agisoft.com/forum/index.php?topic=6074.msg30459#msg30459))

## Recipe 2 — Read existing depth maps as numpy arrays

For depth maps already computed via *Build Depth Maps*, the
data is in `chunk.depth_maps[camera]`. Convert to numpy without
writing intermediate files:

> **Demo verified:** ✗ — pending Tier 3 reproduction on a real Metashape install.

```python
import Metashape
import numpy as np

chunk = Metashape.app.document.chunk
camera = chunk.cameras[0]

depth_image = chunk.depth_maps[camera].image()
h, w = depth_image.height, depth_image.width

# F32 buffer → 2D numpy array
arr = np.frombuffer(depth_image.tostring(), dtype=np.float32).reshape(h, w)

# arr holds chunk-local depth values; multiply by chunk scale for metres
if chunk.transform.scale:
    arr_metres = arr * chunk.transform.scale
```

> "tostring() method is similar to tobytes() method available
> in the older numpy versions. The result is represented as a
> linear array (in the given case all the depth image lines go
> one by one). If you would like to convert it into 2D array
> you should use reshape method:
> `numpy.frombuffer(depth.tostring(), dtype=numpy.float32).reshape(height, width)`"
> — Alexey Pasumansky, 2022-03-21, Metashape 1.8
> ([permalink](https://www.agisoft.com/forum/index.php?topic=14317.msg63021#msg63021))

For multi-channel images (RGB camera output), reshape with the
channel count:

> **Demo verified:** ✗ — pending Tier 3 reproduction on a real Metashape install.

```python
rgb = camera.image()
arr = np.frombuffer(rgb.tostring(), dtype=np.uint8).reshape(rgb.height, rgb.width, 3)
```

## Recipe 3 — Crop a mesh to a boundary shape

`chunk.exportModel()` exports the entire mesh, ignoring any
chunk shapes. To export only the portion inside a polygon, delete
the outside faces first.

> "Currently it is expected behavior for Export Model procedure.
> As a workaround it is possible to delete the polygons which do
> not have any vertex inside the boundary shape using Python and
> export the cropped model."
> — Alexey Pasumansky, 2020-08-08, Metashape 1.6
> ([permalink](https://www.agisoft.com/forum/index.php?topic=12421.msg55331#msg55331))

> **Demo verified:** ✗ — pending Tier 3 reproduction on a real Metashape install.

```python
import Metashape

def point_in_polygon(point, poly):
    """Standard ray-casting point-in-polygon test."""
    x, y = point.x, point.y
    inside = False
    p1x, p1y = poly[0]
    for i in range(len(poly) + 1):
        p2x, p2y = poly[i % len(poly)]
        if y >= min(p1y, p2y) and y <= max(p1y, p2y) and x <= max(p1x, p2x):
            if p1y != p2y:
                xinters = (y - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
            if p1x == p2x or x <= xinters:
                inside = not inside
        p1x, p1y = p2x, p2y
    return inside

chunk = Metashape.app.document.chunk
model = chunk.model

# Find boundary shapes (uses the first one found)
boundary = next(
    (s for s in chunk.shapes
     if s.boundary_type == Metashape.Shape.BoundaryType.OuterBoundary),
    None,
)
if boundary is None:
    raise ValueError("no outer-boundary shape found")

# Convert shape vertices to chunk-local (X, Y) tuples
T_inv = chunk.transform.matrix.inv()
poly = [
    (T_inv.mulp(v).x, T_inv.mulp(v).y)
    for v in boundary.geometry.coordinates[0]   # outer ring
]

# Mark faces with all 3 vertices outside the polygon as selected, then remove
for face in model.faces:
    face.selected = False
for face in model.faces:
    verts = [model.vertices[i].coord for i in face.vertices]
    if not any(point_in_polygon(v, poly) for v in verts):
        face.selected = True

model.removeSelection()      # removes selected faces + their orphan vertices
chunk.exportModel(path="/path/cropped.obj")
```

The vertex-in-polygon test produces a jagged boundary. For a
clean cut along the polygon edge, the script must subdivide
boundary faces — a more complex geometric operation not covered
here.

## Recipe 4 — Compare chunks for change detection / volume

Metashape Professional *can* subtract one **DEM** from another
natively — *Tools → Transform DEM → Calculate difference* (import
the other chunk's DEM into the project first). For **mesh /
point-cloud** change, or finer control, route through an external
tool. Options:

> "In current version of PhotoScan you cannot subtract DEM models
> produced in different chunks, so you need to do that with the
> exported results in the external GIS applications (like
> GlobalMapper or Q-GIS, for example)."
> — Alexey Pasumansky, 2017-05-15, PhotoScan 1.3
> ([permalink](https://www.agisoft.com/forum/index.php?topic=7056.msg34042#msg34042))

That 2017 answer predates the native **Transform DEM → Calculate
difference** operator ([*DEM difference calculation* (Agisoft KB)](https://agisoft.freshdesk.com/support/solutions/articles/31000156301));
for the full chunk-diff treatment see [Comparing chunks for change
detection](chunk-diff-volume-workflows.md).

| Approach | Pros | Cons |
|----------|------|------|
| **External GIS DEM raster diff** | Reusable; preserves georeferencing | Requires aligned CRS + same resolution |
| **CloudCompare cloud-to-cloud** | High resolution; works for non-rasterisable shapes | Less directly interpretable as volume |
| **Per-chunk volume + subtract** | Stays inside Metashape | Requires same polygon vertices in both chunks |

Native per-chunk volume measurement is exposed via the
*Measure → Volume* command (right-click on a polygon shape).
Subtract two volumes computed against the same reference plane
to get an excavation volume.

## Recipe 5 — Empty-chunk handling for `split_in_chunks` workflows

When using the `split_in_chunks` script (from
[`metashape-scripts`](https://github.com/agisoft-llc/metashape-scripts))
to divide a project into spatial sub-chunks, some sub-chunks may
contain no aligned cameras (corner / edge cells with no
coverage). Calling `chunk.buildPointCloud()` or
`chunk.buildModel()` on such chunks raises errors like
`Zero resolution`, `Null image`, or `Empty surface`.

Wrap each batch operation in a try / except:

> **Demo verified:** ✗ — pending Tier 3 reproduction on a real Metashape install.

```python
for chunk in doc.chunks:
    try:
        chunk.buildPointCloud()
    except Exception as exc:
        print(f"Skipped {chunk.label}: {exc}")
        continue
    try:
        chunk.buildModel()
    except Exception as exc:
        print(f"Mesh skipped for {chunk.label}: {exc}")
        continue
```

> "In order to skip 'zero resolution' chunks for the dense cloud
> generation, you can use try-except approach"
> — Alexey Pasumansky, 2019-01-17, Metashape 1.5
> ([permalink](https://www.agisoft.com/forum/index.php?topic=10245.msg47893#msg47893))

## Recipe 6 — Split a mesh into N×N tiles

For very large meshes that exceed memory budgets during *Build
Texture* or downstream-tool import, split the mesh into a grid
of smaller meshes. The script below creates an N×N grid in the
XY plane based on the chunk's bounding box; for each cell, it
duplicates the mesh and clips to the cell's polygon.

> **Demo verified:** ✗ — pending Tier 3 reproduction on a real Metashape install.

```python
import Metashape

def split_mesh(n_tiles_per_side: int = 5):
    """Split chunk.model into N×N XY-plane tiles."""
    chunk = Metashape.app.document.chunk
    if not chunk or not chunk.model:
        raise ValueError("No active chunk with a model")

    # Create a shape group for the tile boundaries
    if not chunk.shapes:
        chunk.shapes = Metashape.Shapes()
        chunk.shapes.crs = chunk.crs
    tiles = chunk.shapes.addGroup()
    tiles.label = f"Mesh split grid ({n_tiles_per_side}x{n_tiles_per_side})"

    # Compute the chunk's bounding box in world coordinates
    region = chunk.region
    T = chunk.transform.matrix
    R = region.rot
    C = region.center
    S = region.size

    # Build the 8 corners of the bounding box in world coords
    corners_world = []
    for dx, dy, dz in [(-1,-1,-1),(1,-1,-1),(1,1,-1),(-1,1,-1),
                        (-1,-1, 1),(1,-1, 1),(1,1, 1),(-1,1, 1)]:
        local = C + R * Metashape.Vector([dx*S.x, dy*S.y, dz*S.z]) / 2
        corners_world.append(T.mulp(local))

    # Find XY extent (lowest Z = ground)
    xs = [c.x for c in corners_world]
    ys = [c.y for c in corners_world]
    x_min, x_max = min(xs), max(xs)
    y_min, y_max = min(ys), max(ys)
    z_top = max(c.z for c in corners_world)
    z_bot = min(c.z for c in corners_world)

    # Create N×N rectangular tile shapes covering the XY extent
    dx = (x_max - x_min) / n_tiles_per_side
    dy = (y_max - y_min) / n_tiles_per_side
    for i in range(n_tiles_per_side):
        for j in range(n_tiles_per_side):
            x0 = x_min + i * dx
            y0 = y_min + j * dy
            poly = [
                Metashape.Vector([x0,      y0,      z_bot]),
                Metashape.Vector([x0 + dx, y0,      z_bot]),
                Metashape.Vector([x0 + dx, y0 + dy, z_bot]),
                Metashape.Vector([x0,      y0 + dy, z_bot]),
            ]
            shape = chunk.shapes.addShape()
            shape.geometry = Metashape.Geometry.Polygon(poly)
            shape.boundary_type = Metashape.Shape.BoundaryType.OuterBoundary
            shape.label = f"tile_{i}_{j}"
            shape.group = tiles

            # Duplicate the mesh clipped to this tile shape
            task = Metashape.Tasks.DuplicateAsset()
            task.asset = chunk.model.key
            task.clip_to_boundary_shapes = True
            task.apply(chunk)

            # Reset boundary so the next tile gets its own
            shape.boundary_type = Metashape.Shape.BoundaryType.NoBoundary

# Usage:
# split_mesh(n_tiles_per_side=5)
```

The resulting chunk has the original mesh plus `n_tiles_per_side²`
clipped duplicates, each named after its grid cell. Generate
texture per tile, then export each tile's mesh and texture
separately for downstream consumers.

The full version of the script (with command-line dialog and
error handling) is in the source thread.

> "Please check this script. It splits the active (default)
> mesh model in the active chunk by N×N grid (N will be asked
> on script start) in XY plane (as if you are looking from Top
> on the mesh)."
> — Alexey Pasumansky, 2022-02-25, Metashape 1.8
> ([permalink](https://www.agisoft.com/forum/index.php?topic=14150.msg63645#msg63645))

## Recipe 7 — Merging multiple point clouds in one chunk

When you've imported multiple LiDAR scans (or built point
clouds in different sessions and they ended up under one
chunk's `chunk.point_clouds`), you can merge them into a
single point cloud asset — equivalent to right-clicking on
multiple clouds in the Workspace pane and choosing *Merge*.

> "I suggest the following code to merge all the available
> dense clouds in the active chunk into new dense cloud
> instance"
> — Alexey Pasumansky, 2019-04-07, Metashape 1.5
> ([permalink](https://www.agisoft.com/forum/index.php?topic=10720.msg48535#msg48535))

> **Demo verified:** ✗ — pending Tier 3 reproduction on a real Metashape install.

```python
import Metashape

chunk = Metashape.app.document.chunk

# Clear the active point cloud reference
chunk.point_cloud = None  # 1.x: chunk.dense_cloud = None

# Merge all point cloud assets via the Tasks API
task = Metashape.Tasks.MergeAssets()
task.assets = [cloud.key for cloud in chunk.point_clouds]
task.apply(chunk)

# After merging, chunk.point_clouds contains the merged asset
# (plus the originals, which can be removed if desired)
print(f"After merge: {len(chunk.point_clouds)} point cloud(s) in chunk")
```

For 1.x compatibility, replace `chunk.point_clouds` with
`chunk.dense_clouds` and `point_cloud` with `dense_cloud`.

## Caveats

- **`renderDepth` requires a built mesh.** `chunk.model` must be
  non-None.
- **`tostring()` is the documented method on Metashape's `Image`
  class.** Pillow's image type uses `tobytes()` (Pillow 10+);
  do not confuse the two.
- **Recipe 3 (mesh crop) is destructive.** The face-removal
  modifies the chunk's mesh. Duplicate the chunk before running
  if you want to preserve the original.
- **Recipe 5 (empty chunks) hides legitimate errors too.**
  Inspect the printed messages — distinguish "zero resolution"
  (genuinely empty) from real errors (missing depth maps, etc.).

## References

- *Metashape Python API Reference* (2.3.1):
  `Model.renderDepth`, `DepthMaps.image`, `Image.tostring`,
  `Model.removeSelection`, `Chunk.exportModel`,
  `Chunk.buildPointCloud`, `Chunk.buildModel`,
  `Tasks.MergeAssets`, `Chunk.point_clouds`,
  `Chunk.point_cloud`.
- *Metashape Pro User Manual* (2.3) §
  *Editing → Editing model* — describes the GUI's mesh-editing
  tools (this article documents the Python equivalents).
- [*Advanced Selection tools for Point Cloud and Model* (Agisoft KB)](https://agisoft.freshdesk.com/support/solutions/articles/31000167986)
  — the GUI Visible Selection / Invert / Grow / Shrink / Filter-by-
  Selection tools whose Python equivalents these recipes use.

## See also

- [Reprojection error analysis: per-camera and per-tie-point](../repeatability-qa/reprojection-error-analysis.md)
- [Exporting depth maps from Python (32-bit, scaled)](../../workflow/depth-maps/exporting-depth-maps-python.md)
- [Computing per-camera coverage area](computing-camera-coverage-area.md)

