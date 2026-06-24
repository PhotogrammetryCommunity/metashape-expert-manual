---
title: "DEM build options: point cloud vs mesh as source, and the interpolation knob"
status: unverified
applies_to: Metashape Pro 2.x — and PhotoScan 1.x via the same `Chunk.buildDem` API; tiled-model-as-source available since Metashape 1.5
edition: Pro
last_reviewed: 2026-05-29
diataxis: how-to
confidence: high
---

# DEM build options: point cloud vs mesh as source, and the interpolation knob

> **Confidence:** *high.* The source-selection guidance is
> directly attested by Agisoft support with permalinks (2015,
> 2019). The `Chunk.buildDem` parameters and the
> `DataSource` enum values are introspection-confirmed on
> Metashape 2.2.

## Problem

You have a project with both a dense point cloud and a built
mesh — or sometimes just one of them — and you need to build
a DEM. The *Build DEM* dialog asks for a source data type
(point cloud, mesh, or tiled model). Which to pick depends on
the dataset's scale, the surface geometry, and the downstream
use of the DEM. The defaults are usually OK for typical aerial
projects but become wrong choices for façades, large areas,
and indoor scans.

This article documents the source-selection rule, the
interpolation parameter, and the common pitfalls.

## Source data: point cloud vs mesh vs tiled model

Three options:

| Source | Best for | Why |
|--------|----------|-----|
| **Point cloud** (default) | Typical aerial surveys; large project areas | Direct from depth maps; no meshing step; handles arbitrary terrain shape |
| **Mesh** | Small areas; building façades; custom planar projections | Mesh provides smoother local interpolation; mesh-based DEM has fewer pin-point artefacts at building edges |
| **Tiled model** (1.5+) | Very large areas where a single-block mesh isn't possible | Tiled model preserves mesh quality at scale; DEM rasterises one tile at a time |

> "Usually we recommend to generate DEM from the dense cloud
> and use this surface as input for the orthomosaic generation,
> thus the meshing step can be skipped. For very large areas
> most likely it wouldn't be possible to generate a single-block
> mesh, therefore the DEM is recommended for large areas
> covered. Using Mesh surface may be reasonable for custom
> plane projections (like building facades, for example) or
> for small areas, when mesh surface produce more accurate
> results, for example, by the edges of the roofs."
> — Agisoft support, 2019-03-22, Metashape 1.5
> ([permalink](https://www.agisoft.com/forum/index.php?topic=10615.msg48212#msg48212))

The recommended workflow on aerial projects: build dense
point cloud → build DEM from point cloud → build orthomosaic
on top of the DEM. The mesh step can be skipped entirely
unless you specifically need it for non-DEM purposes.

For very large areas (kilometres of coverage at high
resolution), single-block mesh generation runs out of RAM.
The tiled-model path becomes the only mesh-based option:

> "In the version 1.5 it is possible, however, to generate the
> tiled model and then build DEM from it. In case you'll be
> experimenting with the tiled model generation, you can try
> to compare the orthomosaic outputs based on DEM from dense
> cloud and from the tiled model."
> — Agisoft support, same thread

## The interpolation parameter

The *Interpolation* dropdown in *Build DEM* controls how the
DEM fills cells where the source data is sparse:

| Mode | What it does | When to use |
|------|--------------|-------------|
| **Disabled** | Cells with no source data are NaN / no-data | Small, dense projects where every cell should have direct evidence |
| **Enabled (default)** | Empty cells filled by interpolating from neighbouring cells, but only within the bounding box | Most production workflows; balances coverage and fidelity |
| **Extrapolated** | Empty cells filled using extrapolation that may extend beyond the convex hull of source data | Final-product DEMs that must be rectangular without no-data holes; risk of edge artefacts |

> "If you are using enabled interpolation, then DEM will be
> interpolated in the areas that are visible from at least one
> camera inside bounding box."
> — Agisoft support, 2015-12-29, PhotoScan 1.2
> ([permalink](https://www.agisoft.com/forum/index.php?topic=4745.msg23951#msg23951))

The *Enabled* mode's "visible from at least one camera"
criterion is important: cells outside any camera's view get
no value even with interpolation enabled. This is correct for
aerial surveys (the DEM should not invent terrain in unseen
areas) but can produce unexpected holes near project
boundaries.

For mesh-based DEM generation specifically, the *Disabled*
interpolation option became available only after PhotoScan 1.2:

> "Disabled interpolation option for DEM based on Mesh
> generation will be available in the next version update."
> — Agisoft support, 2016-01-08, PhotoScan 1.2
> ([permalink](https://www.agisoft.com/forum/index.php?topic=4745.msg24131#msg24131))

If you're on a pre-1.3 version, mesh-source DEMs always
interpolate; only point-cloud-source DEMs allow Disabled.

## Recipe — DEM from point cloud (default)

> **Demo verified:** ✗ — pending Tier 3 reproduction on a real Metashape install.

```python
import Metashape

chunk = Metashape.app.document.chunk

if not chunk.point_cloud:
    raise RuntimeError("Build the point cloud first via Workflow → Build Point Cloud")

chunk.buildDem(
    source_data=Metashape.DataSource.PointCloudData,
    interpolation=Metashape.Interpolation.EnabledInterpolation,
    # Optional: limit to a region or shape
    # region=chunk.region,
)

print(f"DEM built: {chunk.elevation}")
```

## Recipe — DEM from mesh (for façades or small areas)

> **Demo verified:** ✗ — pending Tier 3 reproduction on a real Metashape install.

```python
import Metashape

chunk = Metashape.app.document.chunk

if not chunk.model:
    raise RuntimeError("Build the mesh first via Workflow → Build Mesh")

chunk.buildDem(
    source_data=Metashape.DataSource.ModelData,
    interpolation=Metashape.Interpolation.EnabledInterpolation,
)
```

For a façade-orthomosaic workflow, set the chunk's projection
to a vertical plane first via `chunk.crs` or
`OrthoProjection.type = Metashape.OrthoProjection.Type.Planar`
— see [Orthomosaic in a marker-defined planar projection](../orthomosaic/marker-defined-projection.md).

## Recipe — DEM from tiled model (very large areas)

> **Demo verified:** ✗ — pending Tier 3 reproduction on a real Metashape install.

```python
import Metashape

chunk = Metashape.app.document.chunk

if not chunk.tiled_model:
    raise RuntimeError("Build the tiled model first via Workflow → Build Tiled Model")

chunk.buildDem(
    source_data=Metashape.DataSource.TiledModelData,
    interpolation=Metashape.Interpolation.EnabledInterpolation,
)
```

The tiled-model-source DEM scales to project sizes where a
single-block mesh would exceed RAM (typically >10km² at
sub-decimetre resolution).

## Caveats

- **Bounding box matters.** *Build DEM* respects
  `chunk.region`. If the region is smaller than your
  point-cloud extent, only the portion inside the region
  gets a DEM cell. Verify the region covers what you want
  before running.
- **DEM resolution defaults to "auto".** Metashape picks a
  resolution based on point-cloud density. For consistent
  multi-epoch comparison, set
  `chunk.buildDem(resolution=<value>)` explicitly.
- **The 1.x → 2.x naming.** `chunk.dense_cloud` →
  `chunk.point_cloud`; `chunk.elevation` (the DEM result)
  unchanged. Old scripts that branch on `if chunk.dense_cloud`
  need the rename.
- **Interpolation Disabled produces non-rectangular outputs.**
  The DEM raster's bounding box is still rectangular, but
  cells without direct evidence are flagged no-data. This can
  surprise downstream tools that expect a fully-populated
  raster.
- **Mesh-source DEM at building edges.** The mesh's smooth
  surface at roof edges produces cleaner DEM cells than the
  point cloud, which has "step" noise at every vertical
  surface. This is the strongest argument for mesh-source DEM
  on small dense projects.
- **Tiled-model DEM may show seams** between tiles for
  certain visualisation contrasts. The seams aren't visible
  in the underlying data; they're a rendering artefact at
  steep colour ramps. Smooth out by adjusting the colour-ramp
  range in the GIS tool.

## See also

- [Comparing chunks for change detection: DEM, mesh, and
  point-cloud diff workflows](../../topics/scripting/chunk-diff-volume-workflows.md)
  — uses DEMs as input for between-epoch comparison.
- [Custom vertical datums: adding a geoid undulation grid](../project-setup/custom-geoid-vertical-datum.md)
  — for non-default vertical references in the exported DEM.
- [Area and volume measurement: Model view vs DEM, Shapes vs cropping](../orthomosaic/area-volume-measurement.md)
  — uses DEM-based measurement vs Model-based measurement.
- [Point cloud confidence values: what they mean and how to filter](../point-cloud/point-cloud-confidence-values.md)
  — clean up the point cloud before building the DEM.

## References

- *Metashape Pro User Manual* (2.3), ch. 5 *Build DEM* — covers
  the GUI dialog and parameter ranges.
- *Metashape Python API Reference* (2.3.1):
  `Chunk.buildDem`, `Chunk.elevation`, `Chunk.point_cloud`,
  `Chunk.model`, `Chunk.tiled_model`, `DataSource` enum,
  `Interpolation` enum.
- Forum thread, [*Orthophoto generation: source from DEM or
  Mesh?*, 2019](https://www.agisoft.com/forum/index.php?topic=10615.msg49635#msg49635)
  — canonical Q&A on source selection; tiled-model option
  introduction.
- Forum thread, [*DEM from Mesh not working*, 2015-2016](https://www.agisoft.com/forum/index.php?topic=4745.msg23951#msg23951)
  — interpolation semantics; the Disabled-on-mesh-source
  release timing.

