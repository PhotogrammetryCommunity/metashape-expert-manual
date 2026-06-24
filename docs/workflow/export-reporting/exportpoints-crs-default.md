---
title: "`exportPointCloud` defaults: GUI vs Python CRS difference"
status: unverified
applies_to: Metashape Pro 2.x — and PhotoScan 1.x via the same default-coordinate-system behaviour (under the older `exportPoints` name)
edition: Pro
last_reviewed: 2026-05-29
diataxis: explanation
confidence: high
---

# `exportPointCloud` defaults: GUI vs Python CRS difference

> **Confidence:** *high.* The default-coordinate-system
> difference is forum-attested with permalink (Agisoft support,
> 2016) and the Python API signature is introspection-confirmed
> on Metashape 2.2 — the `crs=` parameter is optional but
> defaults to chunk-internal when omitted.

## Problem

You export a tie-point cloud or dense point cloud via the GUI
(*File → Export → Export Points*), and the resulting `.las` /
`.ply` opens in QGIS or CloudCompare with the points placed at
their georeferenced coordinates. You then re-run the same export
via Python (`chunk.exportPointCloud("/path/output.las")`), and
the resulting file places the points near the origin
`(0, 0, 0)` — a different coordinate system entirely.

Same chunk, same project, two completely different output
coordinate systems. This is **not a bug** — it's a default
mismatch between the GUI and the Python API.

## The default mismatch

| Export route | Default CRS for points |
|--------------|------------------------|
| GUI (`File → Export → Export Points`) | The chunk's CRS (`chunk.crs`) — i.e., georeferenced coordinates |
| Python (`chunk.exportPointCloud(path)` with no `crs=`) | **Chunk-internal** coordinates — i.e., a local right-handed metric frame near `(0, 0, 0)` |

> "From GUI you are exporting points in the geographic
> coordinates, while script export saves the coordinates in the
> internal coordinates."
> — Agisoft support, 2016-03-01, PhotoScan 1.2
> ([permalink](https://www.agisoft.com/forum/index.php?topic=5037.msg25059#msg25059))

Same `chunk.exportPointCloud` API exists in 1.x as `exportPoints`
(renamed at the 2.0 transition). The default-coordinate behaviour
is unchanged across both names.

## When this matters

The default mismatch only causes problems when the chunk is
**referenced**. Three operational cases:

| Project state | GUI default → | Python default → | Mismatch? |
|---------------|---------------|------------------|-----------|
| Fully georeferenced (≥3 cameras or markers with reference data) | CRS coords | Chunk-internal | **YES** |
| Two cameras with reference (chunk NOT marked "referenced") | Chunk-internal | Chunk-internal | No |
| Markerless / un-georeferenced photo set | Chunk-internal | Chunk-internal | No |
| Markers with no reference data | Chunk-internal | Chunk-internal | No |

The "≥3 references for the chunk to be considered referenced"
threshold is important. If you have only 2 cameras with EXIF
GPS data, Metashape **does not** treat the chunk as
georeferenced even though the Reference pane shows coordinates.
Both GUI and Python then use chunk-internal — no mismatch.

## Solution: pass `crs=` explicitly

> **Demo verified:** ✗ — pending Tier 3 reproduction on a real Metashape install.

```python
import Metashape

chunk = Metashape.app.document.chunk

# Implicit (chunk-internal coords — usually NOT what you want)
chunk.exportPointCloud("/path/output_local.las")

# Explicit chunk CRS (matches GUI default)
chunk.exportPointCloud(
    "/path/output_geo.las",
    source_data=Metashape.DataSource.PointCloudData,
    crs=chunk.crs,
)

# Explicit different CRS (e.g., WGS84 lat/lon)
wgs84 = Metashape.CoordinateSystem("EPSG::4326")
chunk.exportPointCloud(
    "/path/output_wgs84.las",
    source_data=Metashape.DataSource.PointCloudData,
    crs=wgs84,
)
```

For tie-point export specifically (sparse / matched feature
cloud), use:

> **Demo verified:** ✗ — pending Tier 3 reproduction on a real Metashape install.

```python
chunk.exportPointCloud(
    "/path/tie_points.las",
    source_data=Metashape.DataSource.TiePointsData,
    crs=chunk.crs,
)
```

The `source_data=` distinguishes which point set to export —
omitting it defaults to the dense point cloud
(`PointCloudData`).

## Forcing chunk-internal export from the GUI

If you want chunk-internal coordinates from a referenced chunk,
the GUI does not directly expose this — it always uses the chunk
CRS for referenced chunks. To force chunk-internal:

> "Clear the coordinate information in the Reference pane and
> also use *Reset Transform* option in the chunk context menu
> after right-clicking on its label in the Workspace pane."
> — Agisoft support, 2016-03-01, PhotoScan 1.2
> ([permalink](https://www.agisoft.com/forum/index.php?topic=5037.msg25071#msg25071))

This drops the chunk's reference frame entirely, making the
chunk no longer "referenced" — at which point GUI and Python
both export in chunk-internal coords. The downside is that
re-georeferencing requires re-loading marker / camera reference
data.

## Caveats

- **`chunk.crs` is `None` for non-georeferenced projects.** If
  you call `chunk.exportPointCloud(path, crs=chunk.crs)` on an
  un-georeferenced chunk, you pass `None` — which Metashape
  treats as "chunk-internal" (the same as omitting `crs=`).
  Defensive check:

  ```python
  out_crs = chunk.crs or Metashape.CoordinateSystem("EPSG::4326")
  chunk.exportPointCloud(path, crs=out_crs)
  ```

- **Z-axis sign** may flip between chunk-internal and the chunk
  CRS depending on the CRS's axis order. Most projected CRSes
  (UTM, State Plane) are right-handed with Z up; chunk-internal
  is also right-handed but has its origin near the project's
  centroid. Geographic CRSes (lat/lon) preserve handedness but
  the X/Y axes swap from "easting/northing" to "longitude/latitude."
- **The `shift=` parameter** moves the export's origin by an
  arbitrary 3D offset — useful for downstream tools that don't
  handle large coordinate values (UTM coordinates can exceed the
  range of single-precision floats). Pass `shift=Metashape.Vector([
  E_origin, N_origin, 0])` to centre the output on a specific
  Easting/Northing.
- **`Metashape.exportPoints` (the 1.x name) was renamed to
  `chunk.exportPointCloud` at the 2.0 transition.** Old scripts
  using `exportPoints` need updating; the parameter set is
  similar but `point_class=` was removed (use `clip_to_boundary=`
  + `point_clouds=` instead).

## See also

- [Change Path: swapping image format / resolution after alignment](../project-setup/change-path-and-export-coords.md)
  — same kind of GUI-vs-Python default mismatch, for image-path
  changes.
- [`chunk.transform.matrix` is local→world; `camera.transform` is local](../../topics/crs/chunk-frame-vs-camera-frame.md)
  — the broader context: where chunk-internal coordinates come
  from.
- [Auto-export per-shape: orthomosaic, DEM, point cloud, mesh, KMZ](auto-export-per-shape.md)
  — uses the explicit `crs=` pattern in production-style code.

## References

- *Metashape Pro User Manual* (2.3), ch. 5 *Export Point Cloud /
  Tie Points* — describes the GUI dialog options.
- *Metashape Python API Reference* (2.3.1):
  `Chunk.exportPointCloud`, parameter `crs`,
  `Chunk.crs`, `CoordinateSystem`, `DataSource.PointCloudData`,
  `DataSource.TiePointsData`.
- Forum thread, [*Different point cloud from script export*, 2016](https://www.agisoft.com/forum/index.php?topic=5037.msg25241#msg25241)
  — the canonical Q&A; default-coordinate-system difference
  identified by Agisoft support.

