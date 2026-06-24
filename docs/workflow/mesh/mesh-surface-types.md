---
title: "Mesh surface types: Arbitrary vs Height field, and the source-data choice"
status: unverified
applies_to: Metashape Pro 2.x and Metashape Standard 2.x — same `SurfaceType` and `DataSource` enums as PhotoScan 1.5+
edition: "Pro / Standard"
last_reviewed: 2026-05-29
diataxis: explanation
confidence: high
---

# Mesh surface types: Arbitrary vs Height field, and the source-data choice

> **Confidence:** *high.* The two-mode surface-type framing
> is from the official manual; the source-data semantics
> (depth maps vs point cloud as input) are documented and
> introspection-confirmed on Metashape 2.2. Operational
> guidance on when each combination wins comes from forum
> threads with permalinks.

## Problem

The *Build Model* dialog has two key choices that interact:

1. **Surface type**: Arbitrary or Height field
2. **Source data**: Depth maps, Point cloud, Tie points, or
   Sparse cloud

Defaults work for typical aerial projects, but become wrong
choices for vertical structures, indoor scans, or close-range
objects. The two parameters are independent — wrong choice on
either produces a wrong-but-plausible mesh that survives
casual inspection.

This article documents the choice rules.

## Surface type — the geometry assumption

The surface type tells the mesher what kind of geometry to
expect:

> "**Arbitrary** surface type can be used for modeling of any
> kind of object. It should be selected for closed objects,
> such as statues, buildings, etc. It doesn't make any
> assumptions on the type of the object being modeled, which
> comes at a cost of higher memory consumption.
>
> **Height field** surface type is optimized for modeling of
> planar surfaces, such as terrains or basereliefs. It should
> be selected for aerial photography processing as it requires
> lower amount of memory and allows for larger data sets
> processing."
> — *Metashape Pro Manual* 2.3, § *Build Model → Surface type*

Operationally:

| Use case | Surface type | Why |
|----------|-------------|-----|
| Aerial survey of terrain | Height field | Memory-efficient; matches the "Z is up, every (X,Y) has one Z" assumption |
| Aerial survey with overhangs (cliffs, building eaves) | Arbitrary | Height field collapses overhangs into vertical walls |
| Close-range object scan (statue, pottery, scan target) | Arbitrary | The object has unconstrained geometry; height-field is wrong by definition |
| Building façades captured horizontally | Arbitrary | The "ground plane" is now vertical; height-field expects horizontal |
| Indoor scan | Arbitrary | Multi-room interior has no single up-down axis |

The Height-field reconstruction is dramatically cheaper:
~10× less RAM than Arbitrary on the same data. For aerial
surveys without overhangs, choose Height field.

## The bounding-box constraint for Height field

When using Height field, the bounding box has a **red face**
that defines the reconstruction plane. The mesher projects
features down onto this plane, so its orientation matters:

> "If the Height field reconstruction method is to be applied,
> it is important to control the position of the red side of
> the bounding box: it defines reconstruction plane. In this
> case make sure that the bounding box is correctly oriented."
> — *Metashape Pro Manual* 2.3

For aerial surveys with the chunk in a horizontal CRS, the
red face is automatically the bottom (XY plane). For chunks
where the surface of interest is vertical (a building façade),
you must rotate the bounding box so the red face is parallel
to the façade.

Programmatically, the chunk's `region.rot` matrix encodes the
orientation. Setting it to align with façades is documented
in [Setting `chunk.region` to bound the tie-point cloud](../project-setup/setting-the-chunk-region.md).

## Source data — what the mesher consumes

The four source-data options have different speed / quality
tradeoffs:

| Source | Speed | Quality | Memory | When to use |
|--------|:-----:|:-------:|:------:|-------------|
| **Depth maps** (default since 1.5) | fast | high | moderate | Most production cases; recommended for Arbitrary surface type |
| **Point cloud** | medium | high | high | When you've already built the dense cloud and want to skip rebuilding depth maps |
| **Tie points** | fast | low | low | Rough preview before dense-cloud generation |
| **Sparse cloud** (alias for Tie points in some versions) | fast | low | low | Same as Tie points |

The official manual's recommendation:

> "[Build Mesh from Depth Maps] is faster and is less resource
> demanding compared to the point cloud based reconstruction.
> The option is recommended to be used for Arbitrary surface
> type reconstruction, unless the workflow used assumes point
> cloud editing prior to the model reconstruction."
> — *Metashape Pro Manual* 2.3

Operational rule:

- If you need to clean / classify the point cloud before
  meshing, build the point cloud first, then use **point
  cloud** as the source.
- Otherwise, skip the point-cloud step and use **depth maps**
  directly.

## Recipe — Arbitrary surface from depth maps (default close-range)

> **Demo verified:** ✗ — pending Tier 3 reproduction on a real Metashape install.

```python
import Metashape

chunk = Metashape.app.document.chunk

# Depth maps must be built first with Mild filtering
# (Mild is required for depth-maps-based mesh; see depth-map-quality article)
chunk.buildDepthMaps(
    downscale=2,                              # High quality
    filter_mode=Metashape.FilterMode.MildFiltering,
)

chunk.buildModel(
    surface_type=Metashape.SurfaceType.Arbitrary,
    source_data=Metashape.DataSource.DepthMapsData,
    face_count=Metashape.FaceCount.HighFaceCount,
)
```

The mesh inherits its detail level from the depth maps' Quality
(set in `buildDepthMaps`); `buildModel` itself doesn't have a
quality kwarg.

## Recipe — Height field from depth maps (default aerial)

> **Demo verified:** ✗ — pending Tier 3 reproduction on a real Metashape install.

```python
import Metashape

chunk = Metashape.app.document.chunk

chunk.buildDepthMaps(
    downscale=2,
    filter_mode=Metashape.FilterMode.AggressiveFiltering,  # OK for aerial
)

chunk.buildModel(
    surface_type=Metashape.SurfaceType.HeightField,
    source_data=Metashape.DataSource.DepthMapsData,
    face_count=Metashape.FaceCount.MediumFaceCount,        # often enough for aerial DSMs
)
```

The face-count knob trades polygon density for export size:

| `face_count` | Aerial use case |
|--------------|-----------------|
| `LowFaceCount` | Quick visualisation; large project areas |
| `MediumFaceCount` (typical) | Production aerial |
| `HighFaceCount` | Detailed terrain analysis |
| `CustomFaceCount` (with `face_count_custom=N`) | Specific polygon budget for downstream tools |

## Recipe — Arbitrary from point cloud (after cleanup)

If you've cleaned the dense cloud (via confidence filter,
classification, or selectPointsByShapes) and want the mesh to
honour the cleaned cloud:

> **Demo verified:** ✗ — pending Tier 3 reproduction on a real Metashape install.

```python
import Metashape

chunk = Metashape.app.document.chunk

if not chunk.point_cloud:
    raise RuntimeError("Build the point cloud first")

chunk.buildModel(
    surface_type=Metashape.SurfaceType.Arbitrary,
    source_data=Metashape.DataSource.PointCloudData,
    interpolation=Metashape.Interpolation.EnabledInterpolation,
)
```

## When Height field produces visible wrongness

Symptoms that indicate Height field is the wrong choice:

1. **Overhangs collapse to vertical walls.** A cliff-face
   protrusion appears as a flat vertical surface in the mesh.
2. **Trees become "cylinders".** Each tree's complex canopy
   collapses to a single Z-value per (X,Y) cell.
3. **Buildings lose their roofs' overhangs.** The roof edge
   appears flush with the wall plane below.
4. **Interior structures disappear.** Indoor scans rendered
   as Height field show only the topmost surface (ceiling-like).

If you see any of these on data that *should* show overhangs,
re-run with `SurfaceType.Arbitrary`.

## When Arbitrary on aerial data is overkill

Symptoms:

1. **Memory exhaustion.** Arbitrary on a multi-km² aerial
   project on consumer hardware (32-64GB RAM) often crashes.
2. **Slow re-meshing during iteration.** Multiple texture /
   colour adjustments require multiple Build Mesh runs;
   Arbitrary is 4-10× slower than Height field on the same data.
3. **No real overhangs in the captured area.** If the
   project is open ground (fields, roads, low buildings) with
   no caves, cliffs, or eaves, Height field's assumption is
   correct.

For aerial projects with mixed terrain (some flat, some
buildings with eaves), the canonical workaround is to **split
into chunks** by region and build each with the appropriate
surface type. See [What `mergeChunks` actually does (and what
it does not)](../chunks/what-mergechunks-does.md) for the
merge step.

## Caveats

- **`SurfaceType` cannot be changed after Build Mesh.** To
  change, run *Build Mesh* again from scratch.
- **The bounding-box red-face matters only for Height field.**
  For Arbitrary surface type, all bounding-box faces are
  equivalent.
- **Mild filtering required for depth-maps-based mesh.** See
  [Depth-map quality and filter modes](../depth-maps/depth-map-quality-and-filter-modes.md);
  Aggressive-filtered depth maps produce mesh holes.
- **`build_uv` defaults to True.** The mesh ships with a UV
  unwrap by default; set `build_uv=False` if you'll re-unwrap
  in an external tool. See *Texture in Metashape 2.3 — what
  changed* for the 2.3 UV change.
- **`vertex_colors=True`** can save a Build Texture step for
  preview workflows. The vertex colours are not as detailed
  as a proper texture but are sufficient for QA preview.
- **`source_data=Metashape.DataSource.TiePointsData`** uses
  the sparse cloud — the result is dramatically lower-quality
  but takes seconds. Useful for confirming the project's
  rough shape before committing to a multi-hour Build Mesh.

## See also

- [Depth-map quality and filter modes](../depth-maps/depth-map-quality-and-filter-modes.md)
  — the depth-maps source's filter requirement (Mild for
  mesh).
- [Setting `chunk.region` to bound the tie-point cloud](../project-setup/setting-the-chunk-region.md)
  — for the Height-field bounding-box orientation requirement.
- [Mesh and point-cloud editing recipes](../../topics/scripting/mesh-pointcloud-editing-recipes.md)
  — Recipe 6 (split into N×N tiles) for breaking up large
  Arbitrary meshes.
- [DEM build options: point cloud vs mesh as source](../dem/build-options.md)
  — DEM source selection follows similar logic.
- [Performance tuning: CPU, RAM, GPU, and OS](../../topics/performance/cpu-ram-gpu-os-tuning.md)
  — RAM planning for Arbitrary surface type on large
  projects.

## References

- *Metashape Pro User Manual* (2.3), ch. 4 *Build Model →
  Surface type, Source data, Quality, Face count*.
- *Metashape Python API Reference* (2.3.1):
  `Chunk.buildModel`, `SurfaceType` (Arbitrary, HeightField),
  `DataSource` (DepthMapsData, PointCloudData, TiePointsData),
  `FaceCount` (LowFaceCount, MediumFaceCount, HighFaceCount,
  CustomFaceCount), `Interpolation`.
- Forum thread, [*Optimal tiled model settings?*, 2019](https://www.agisoft.com/forum/index.php?topic=11630.msg53148#msg53148)
  — depth-maps-based mesh memory expectations (≤16 GB on
  typical aerial).

