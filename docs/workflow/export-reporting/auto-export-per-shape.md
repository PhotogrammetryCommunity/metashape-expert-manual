---
title: "Auto-export per-shape: orthomosaic, DEM, point cloud, mesh, KMZ"
status: unverified
applies_to: Metashape Pro 2.x — and PhotoScan 1.x via the same `chunk.shapes` and `exportRaster` API
edition: Pro
last_reviewed: 2026-05-28
diataxis: how-to
confidence: high
---

# Auto-export per-shape: orthomosaic, DEM, point cloud, mesh, KMZ

> **Confidence:** *high.* The boundary-toggle pattern is forum-
> attested with a complete recipe (Agisoft support, 2020). The
> `Shape.boundary_type` toggle, `chunk.exportRaster`,
> `chunk.exportPointCloud`, and `chunk.exportModel` APIs are
> introspection-confirmed on Metashape 2.2.

> **Scope statement.** The official manual documents the GUI's
> per-shape *Setup boundaries* option in the *Export Orthomosaic*
> / *Export DEM* dialogs (one shape at a time, per dialog
> invocation). This article picks up where the manual stops:
> the **Python iteration pattern** that batches one export per
> shape across multiple product types (orthomosaic, DEM, point
> cloud, mesh, KMZ), with the `shape.boundary_type` toggle as
> the driver — plus the DXF POLYLINE compatibility note for
> CAD-sourced shape inputs.

## Problem

Your project covers a large area (a city, a multi-tile aerial
survey, a multi-room indoor scan) divided into named regions:
sheets / tiles / parcels / map indices. Each region is a
polygon shape in the chunk. You need to **export one file per
region** for orthomosaic, DEM, dense point cloud, and mesh —
ideally with the region's label baked into the filename, and
all in a single batch run.

The GUI's *File → Export → Export Orthomosaic* dialog has a
*Setup boundaries* option for the active boundary shape, but it
exports one file at a time. For many shapes, the per-shape
toggle becomes tedious.

## Solution: toggle each shape's `OuterBoundary` flag

The Python pattern: iterate over the chunk's polygons, set each
one in turn as the **OuterBoundary**, export, then reset.
Metashape's export commands honour the active outer-boundary
shape implicitly, so the per-shape export is just a
boundary-toggle loop.

### Recipe: orthomosaic per polygon

> **Demo verified:** ✗ — pending Tier 3 reproduction on a real Metashape install.

```python
import Metashape

chunk = Metashape.app.document.chunk
output_dir = Metashape.app.getExistingDirectory("Output folder:")

# Optional: explicit output CRS (else uses chunk.crs)
output_crs = Metashape.app.getCoordinateSystem(
    "Output CRS:", chunk.crs
) or chunk.crs
proj = Metashape.OrthoProjection()
proj.crs = output_crs

# Reset all boundaries first (only one OuterBoundary at a time)
for shape in chunk.shapes:
    if shape.geometry and shape.geometry.type == Metashape.Geometry.Type.PolygonType:
        shape.boundary_type = Metashape.Shape.BoundaryType.NoBoundary

# Per-polygon: set as boundary, export, reset
for shape in chunk.shapes:
    if not shape.geometry or shape.geometry.type != Metashape.Geometry.Type.PolygonType:
        continue
    shape.boundary_type = Metashape.Shape.BoundaryType.OuterBoundary

    if chunk.orthomosaic:
        out = f"{output_dir}/ortho_{shape.key}_{shape.label}.tif"
        chunk.exportRaster(
            out,
            source_data=Metashape.DataSource.OrthomosaicData,
            projection=proj,
            save_alpha=True,
        )

    shape.boundary_type = Metashape.Shape.BoundaryType.NoBoundary
```

The `shape.key` is included in the filename to avoid collisions
when two shapes share the same label.

### Recipe: all four product types per polygon

For a complete per-shape export covering orthomosaic + DEM +
point cloud + mesh:

> **Demo verified:** ✗ — pending Tier 3 reproduction on a real Metashape install.

```python
import Metashape

chunk = Metashape.app.document.chunk
output_dir = Metashape.app.getExistingDirectory("Output folder:")

output_crs = Metashape.app.getCoordinateSystem(
    "Output CRS:", chunk.crs
) or chunk.crs
proj = Metashape.OrthoProjection()
proj.crs = output_crs

# Reset all boundaries
for shape in chunk.shapes:
    if shape.geometry and shape.geometry.type == Metashape.Geometry.Type.PolygonType:
        shape.boundary_type = Metashape.Shape.BoundaryType.NoBoundary

for shape in chunk.shapes:
    if not shape.geometry or shape.geometry.type != Metashape.Geometry.Type.PolygonType:
        continue
    shape.boundary_type = Metashape.Shape.BoundaryType.OuterBoundary
    name = f"{shape.key}_{shape.label}"

    if chunk.orthomosaic:
        chunk.exportRaster(
            f"{output_dir}/ortho_{name}.tif",
            source_data=Metashape.DataSource.OrthomosaicData,
            projection=proj,
            save_alpha=True,
        )

    if chunk.elevation:
        chunk.exportRaster(
            f"{output_dir}/dem_{name}.tif",
            source_data=Metashape.DataSource.ElevationData,
            projection=proj,
        )

    if chunk.point_cloud:
        chunk.exportPointCloud(
            f"{output_dir}/cloud_{name}.las",
            source_data=Metashape.DataSource.PointCloudData,
            crs=output_crs,
        )

    if chunk.model:
        chunk.exportModel(
            f"{output_dir}/mesh_{name}.obj",
            format=Metashape.ModelFormat.ModelFormatOBJ,
            crs=output_crs,
        )

    shape.boundary_type = Metashape.Shape.BoundaryType.NoBoundary
```

### KMZ variant

For Google-Earth-compatible orthomosaic tiles, swap the format:

> **Demo verified:** ✗ — pending Tier 3 reproduction on a real Metashape install.

```python
chunk.exportRaster(
    f"{output_dir}/ortho_{name}.kmz",
    format=Metashape.RasterFormat.RasterFormatKMZ,
    source_data=Metashape.DataSource.OrthomosaicData,
    projection=proj,
)
```

### Mesh in a local coordinate system

To export the mesh in metric local coordinates (useful when
downstream tools dislike geographic CRSes), construct a generic
local CRS:

> **Demo verified:** ✗ — pending Tier 3 reproduction on a real Metashape install.

```python
local_crs = Metashape.CoordinateSystem(
    'LOCAL_CS["Local Coordinates (m)",LOCAL_DATUM["Local Datum",0],'
    'UNIT["metre",1,AUTHORITY["EPSG","9001"]]]'
)
chunk.exportModel(
    f"{output_dir}/mesh_{name}.obj",
    format=Metashape.ModelFormat.ModelFormatOBJ,
    crs=local_crs,
)
```

> "Please check, if the following approach solves the task of
> mesh export in local coordinates"
> — Agisoft support, 2020-12-23, Metashape 1.7
> ([permalink](https://www.agisoft.com/forum/index.php?topic=12813.msg57218#msg57218))

## DXF source compatibility

If the polygons come from a CAD-format file (DXF), Metashape's
*Import Shapes* requires the DXF to use **POLYLINE** entities
specifically — pure line segments, points, or other entity types
are silently ignored.

If your DXF was exported from a CAD tool that produces
non-POLYLINE polygons:

> "The provided DXF doesn't contain Metashape supported elements
> (POLYLINE type) therefore you should re-save the DXF in the
> external application, for example, Global Mapper."
> — Agisoft support, 2020-11-30, Metashape 1.7
> ([permalink](https://www.agisoft.com/forum/index.php?topic=12813.msg56813#msg56813))

Workarounds:

1. **Re-save the DXF** in Global Mapper, QGIS, or AutoCAD's
   "Save As" dialog with explicit polyline output.
2. **Convert to Shapefile** (.shp) — Metashape's *Import Shapes*
   handles SHP cleanly.
3. **Convert to GeoPackage** (.gpkg) — also well-supported.

## Caveats

- **Reset boundaries before the loop.** If any shape was already
  set to `OuterBoundary` (e.g., from a prior run), Metashape
  treats multiple boundaries as ambiguous and may export the
  wrong region. The "reset all → loop with toggle → reset each"
  pattern above ensures clean per-shape exports.
- **`shape.key` vs `shape.label`.** The `key` is a stable
  numeric ID; the `label` is user-set and may collide. Including
  both in the filename (`ortho_<key>_<label>.tif`) prevents
  filename collisions when two shapes share a label.
- **`chunk.point_cloud` requires Build Point Cloud first.** The
  recipe checks `if chunk.point_cloud:` to skip silently if not.
  Same for `chunk.elevation`, `chunk.orthomosaic`, `chunk.model`.
- **Output CRS handling.** If you don't pass `crs=`/`projection=`
  explicitly, Python defaults to chunk-internal coordinates (see
  [Change Path: swapping image format](../project-setup/change-path-and-export-coords.md)
  Problem 2). Always pass an explicit CRS for production
  workflows.
- **DEM export inherits the chunk's vertical datum.** If the
  chunk uses a custom geoid (see
  [Custom vertical datums](../project-setup/custom-geoid-vertical-datum.md)),
  exported DEM heights are in that datum. Verify with a known
  reference point.

## See also

- [Applying *Patch* on multiple shapes (orthomosaic patching by script)](../orthomosaic/applying-patch-multiple-shapes.md)
  — same iterate-over-shapes pattern for orthomosaic seam editing.
- [Change Path: swapping image format / resolution after alignment](../project-setup/change-path-and-export-coords.md)
  — the GUI/Python CRS-default difference for `exportPointCloud`.
- [Custom vertical datums: adding a geoid undulation grid](../project-setup/custom-geoid-vertical-datum.md)
- [Mesh and point-cloud editing recipes (Python)](../../topics/scripting/mesh-pointcloud-editing-recipes.md)

## References

- *Metashape Pro User Manual* (2.3), ch. 5 *Orthomosaic /
  DEM export* — describes the per-export GUI dialog options.
- *Metashape Python API Reference* (2.3.1):
  `Chunk.exportRaster`, `Chunk.exportPointCloud`,
  `Chunk.exportModel`, `Shape.boundary_type`,
  `Shape.BoundaryType`, `OrthoProjection`, `RasterFormat`,
  `ModelFormat`.
- Forum thread, [*Auto Export Orthophoto by index (sheet) name?*, 2020](https://www.agisoft.com/forum/index.php?topic=12813.msg56813#msg56813)
  — the canonical Q&A; per-shape export script (msg 57965);
  multi-product extension (msg 58060); KMZ variant (msg 58116);
  local-CRS mesh export (msg 58162).

