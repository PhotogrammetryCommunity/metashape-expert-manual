---
title: "Tiled models: when to use, what they replace, and how to export"
status: unverified
applies_to: Metashape Pro 2.x — `Chunk.buildTiledModel` API stable since PhotoScan 1.4
edition: Pro
last_reviewed: 2026-05-29
diataxis: explanation
confidence: medium
---

# Tiled models: when to use, what they replace, and how to export

> **Confidence:** *medium.* The when-to-use guidance and tile-
> count recommendations are forum-attested with permalinks
> (Agisoft support, 2019). The `Chunk.buildTiledModel` API is
> introspection-confirmed on Metashape 2.2. The export-format
> coverage is best confirmed empirically per format.

## Problem

You have an aerial dataset that is too large for a single-block
mesh — *Build Mesh* either runs out of RAM or produces a mesh
so dense that downstream tools choke. The *Build Tiled Model*
command produces a different output: a hierarchical multi-resolution
representation that scales to any project size at the cost of
being less directly editable.

Common questions:

- "When should I use tiled model instead of mesh?"
- "How many tiles should I use?"
- "Can I export it to Cesium / Unreal / Unity / a viewer?"
- "Why doesn't *Build Texture* work on tiled models?"

## What a tiled model is

A tiled model is a **hierarchical 3D representation** built
from depth maps, where the scene is divided into spatial tiles
each containing its own mesh + texture. At runtime, a viewer
loads only the tiles needed for the current view at the
appropriate level of detail. The output format follows the
3D-Tiles or i3s standard — both supported by Cesium, Esri's
ArcGIS, and several visualisation engines.

Compared to a single-block mesh + texture:

| Property | Single mesh + texture | Tiled model |
|----------|----------------------|-------------|
| Project-area scale | RAM-limited (~10-50 km² typical max) | Effectively unlimited |
| Editability in Metashape | Yes (vertex editing, hole filling) | No (read-only output) |
| Texture per region | One texture, often massive | Per-tile textures, smaller |
| Viewer-friendly | Loads entire mesh upfront | Streams on demand |
| Export targets | OBJ, PLY, FBX, GLTF, etc. | 3D Tiles, i3s, OSGB, SLPK, KMZ |
| Build cost | Single big computation | Per-tile parallel; total cost similar |

## When to use tiled model

> "For very large areas most likely it wouldn't be possible to
> generate a single-block mesh, therefore the DEM is recommended
> for large areas covered. Using Mesh surface may be reasonable
> for custom plane projections (like building facades, for
> example) or for small areas, when mesh surface produce more
> accurate results, for example, by the edges of the roofs."
> — Agisoft support, 2019-03-22, Metashape 1.5
> ([permalink](https://www.agisoft.com/forum/index.php?topic=10615.msg48212#msg48212))

> "For the upload to 4DMapper you might really need tiled
> model. Usually we suggest to use 256 tiles option for faster
> navigation. Default face count is 'low' for the Tiled model,
> but usually it is sufficient for aerial projects. But you
> can go with Medium, if you wish."
> — Agisoft support, 2019-12-15, Metashape 1.6
> ([permalink](https://www.agisoft.com/forum/index.php?topic=11630.msg52157#msg52157))

Concrete decision rules:

| Use case | Use Mesh? | Use Tiled Model? |
|----------|:---------:|:----------------:|
| Aerial survey for DSM / DEM only | ❌ skip mesh | ❌ skip tiled model |
| Aerial survey for orthomosaic (default) | ❌ skip mesh | ❌ build orthomosaic from DEM |
| Aerial survey for textured 3D viewing | ❌ too big | ✅ tiled model |
| Aerial survey delivered to Cesium / 4DMapper / ArcGIS | ❌ | ✅ tiled model |
| Close-range / object scan | ✅ mesh | ❌ tile model unnecessary |
| Building façade orthomosaic | ✅ mesh (Arbitrary) | ❌ |
| Multi-km² urban scan with detailed buildings | ✅ via [split-in-chunks](../chunks/index.md) | ✅ for direct upload |

The decision boils down to: are you delivering an editable
mesh, or a viewer-ready 3D scene?

## Recipe — Build Tiled Model from depth maps

> **Demo verified:** ✗ — pending Tier 3 reproduction on a real Metashape install.

```python
import Metashape

chunk = Metashape.app.document.chunk

# Depth maps must be built first
chunk.buildDepthMaps(
    downscale=2,                              # High quality
    filter_mode=Metashape.FilterMode.AggressiveFiltering,
)

chunk.buildTiledModel(
    pixel_size=0.0,                          # 0 = auto from depth maps
    tile_size=256,                            # tile dimension; 256 is standard
    face_count=Metashape.FaceCount.LowFaceCount,
    source_data=Metashape.DataSource.DepthMapsData,
    transfer_texture=False,
)
```

The `tile_size=256` reflects the support recommendation; values
smaller than 256 produce many small tiles (cheaper per tile,
more overhead); larger values produce fewer larger tiles
(harder to stream).

The `pixel_size=0.0` defaults the texel size to the depth-map
resolution. For a specific output GSD, set `pixel_size=<value>`
in chunk units (metres for georeferenced projects).

## Recipe — Build Tiled Model from mesh + texture

If you already have a textured mesh (e.g., for a small subset
of the project) and want to convert it to tiled form:

> **Demo verified:** ✗ — pending Tier 3 reproduction on a real Metashape install.

```python
import Metashape

chunk = Metashape.app.document.chunk

if not chunk.model or not chunk.model.texture:
    raise RuntimeError("Build mesh + texture first")

chunk.buildTiledModel(
    source_data=Metashape.DataSource.ModelData,
    tile_size=256,
    transfer_texture=True,                   # carry the existing texture into tiles
)
```

The mesh-source path is rarely useful for production aerial
work (the depth-map source is more accurate) but is helpful for
final export when an edited mesh has been corrected by hand.

## Export targets

`Chunk.exportTiledModel` supports several formats; the format
choice determines the consumer:

| Format constant | Consumer | Notes |
|-----------------|----------|-------|
| **`TiledModelFormatCesium`** | Cesium ion, viewers honoring the OGC 3D Tiles spec | The most portable format; URL-streamable |
| **`TiledModelFormatSLPK`** | Esri ArcGIS Earth, ArcGIS Online | Uses i3s-in-SLPK packaging |
| **`TiledModelFormatOSGB`** | OpenSceneGraph viewers; Bentley ContextCapture-compatible legacy GIS | OSG-binary format |
| **`TiledModelFormatOSGT`** | OpenSceneGraph text variant | Less common |
| **`TiledModelFormat3MX`** | Bentley Acute3D / ContextCapture | Vendor-specific |
| **`TiledModelFormatLOD`** | Generic LOD format | |
| **`TiledModelFormatTLS`** | Metashape-native | Round-trippable in Metashape |
| **`TiledModelFormatZIP`** | Zipped output | Container format |

> **Demo verified:** ✗ — pending Tier 3 reproduction on a real Metashape install.

```python
import Metashape

chunk = Metashape.app.document.chunk

# Cesium 3D Tiles export (most common target)
chunk.exportTiledModel(
    "/path/output_dir",
    format=Metashape.TiledModelFormat.TiledModelFormatCesium,
)
```

For Cesium ion specifically, the Cesium-format export integrates
with the existing [Exporting to Cesium 3D Tiles](../orthomosaic/exporting-cesium-tiled-models.md)
workflow — the same Cesium hosting pipeline accepts both
DEM-on-orthomosaic and tiled-model uploads.

## Caveats

- **Tiled models are read-only in Metashape.** You cannot edit
  vertices, fix holes, or adjust topology after build. To
  modify, rebuild from depth maps with corrected source data.
- **No `buildTexture` step.** The texture is computed during
  *Build Tiled Model* — separate texture generation isn't
  meaningful for the tiled-output format.
- **Tile-size is GUI-dropdown-only.** The `tile_size` Python
  parameter accepts arbitrary values, but the GUI exposes
  64 / 128 / 256 / 512. Stick to power-of-2 values for
  compatibility.
- **Face count "Low" is reasonable for aerial.** Per Agisoft
  support: "Default face count is 'low' for the Tiled model,
  but usually it is sufficient for aerial projects." Don't
  reflexively bump to Medium / High — the tile structure
  already provides multi-resolution detail.
- **`pixel_size` units.** For georeferenced chunks,
  `pixel_size` is in chunk units (typically metres). For
  un-georeferenced chunks, it's chunk-local units.
- **Storage size.** Tiled model output can be 2-5× larger than
  a single textured mesh on the same data due to the LOD
  pyramid. Plan disk accordingly.

## See also

- [Exporting to Cesium 3D Tiles](../orthomosaic/exporting-cesium-tiled-models.md)
  — the canonical Cesium pipeline; tiled models slot in as the
  geometry source.
- [Mesh surface types: Arbitrary vs Height field](../mesh/mesh-surface-types.md)
  — when to use mesh vs tiled model for non-massive projects.
- [DEM build options: point cloud vs mesh as source](../dem/build-options.md)
  — DEM can be built from tiled-model source as an alternative
  to point-cloud source on very large areas.
- [Performance tuning: CPU, RAM, GPU, and OS](../../topics/performance/cpu-ram-gpu-os-tuning.md)
  — RAM planning for the tiled-model build step.

## References

- *Metashape Pro User Manual* (2.3), ch. 4 *Build Tiled Model*
  — covers the GUI dialog and parameter ranges.
- *Metashape Python API Reference* (2.3.1):
  `Chunk.buildTiledModel`, `Chunk.exportTiledModel`,
  `Chunk.tiled_model`, `TiledModelFormat`, `DataSource`,
  `FaceCount`.
- Forum thread, [*Optimal tiled model settings?*, 2019](https://www.agisoft.com/forum/index.php?topic=11630.msg52157#msg52157)
  — tile-count and face-count recommendations.
- Forum thread, [*Orthophoto generation: source from DEM or
  Mesh?*, 2019](https://www.agisoft.com/forum/index.php?topic=10615.msg49635#msg49635)
  — when-to-use rule including tiled-model option.

