---
title: "Depth-map quality and filter modes: choosing parameters for Build Point Cloud"
status: unverified
applies_to: Metashape Pro 2.x and Metashape Standard 2.x — same `Quality` and `FilterMode` enums as PhotoScan 1.x
edition: "Pro / Standard"
last_reviewed: 2026-05-29
diataxis: explanation
confidence: high
---

# Depth-map quality and filter modes: choosing parameters for Build Point Cloud

> **Confidence:** *high.* The four filter modes are documented
> in the official manual at the dialog level. Operational
> nuances (excessive overlap → slow filtering; overview-photo
> pitfall) come from forum threads with permalinks. The
> `Chunk.buildDepthMaps` / `Chunk.buildPointCloud` API surface
> is introspection-confirmed on Metashape 2.2.

## Problem

The *Build Depth Maps* and *Build Point Cloud* dialogs each ask
for a **Quality** setting and a **Depth filtering** mode. The
defaults work for typical aerial projects but become wrong
choices for close-range, texture-poor surfaces, mixed-altitude
captures, or scenes with fine geometric detail. Wrong choices
either burn hours of compute on no-quality-improvement, or
silently delete legitimate small-scale geometry.

This article documents the parameter semantics so you can
choose deliberately.

## Quality: 5 levels

The *Quality* parameter controls **how much images are
downscaled** before depth-map computation. Each step downscales
by factor 2 per side (factor 4 in pixel count):

| Quality | Image scale | Depth map resolution | Time cost (relative) | RAM cost (relative) |
|---------|:-----------:|:--------------------:|:--------------------:|:-------------------:|
| **Ultra-High** | 1× (full) | Full | 16× | 16× |
| **High** (default) | 1/2 | 1/2 | 4× | 4× |
| **Medium** | 1/4 | 1/4 | 1× | 1× |
| **Low** | 1/8 | 1/8 | 1/4 | 1/4 |
| **Lowest** | 1/16 | 1/16 | 1/16 | 1/16 |

Each lower step trades depth-map detail for speed: Lowest is
~256× faster than Ultra-High but produces depth maps with
roughly 1/16 the linear resolution.

### When to use each

- **Ultra-High**: rarely justifiable. The default High at
  1/2 is sufficient for almost all production work; Ultra
  doubles depth-map detail at 4× the cost. Reserve for very
  fine close-range objects (small artefacts, jewellery,
  archaeological finds) where sub-millimetre detail matters.
- **High**: the production default. Aerial surveys, drone
  scans, larger close-range work all use High.
- **Medium**: previewing a project, or working on
  resource-constrained hardware. Quality drop is perceptible
  but not catastrophic.
- **Low / Lowest**: rough preview only. Useful for
  visualizing which areas the alignment covers; not for
  delivery.

The Quality value is recorded in the project; downstream
operations (mesh, orthomosaic) inherit the depth map's
resolution.

## Depth filter mode: 4 options

Quoting the official manual (*Build Point Cloud → Depth
filtering modes*):

> "If there are important small details which are spatially
> distinguished in the scene to be reconstructed, then it is
> recommended to set Mild depth filtering mode, for important
> features not to be sorted out as outliers. This value of the
> parameter may also be useful for aerial projects in case the
> area contains poorly textured roofs, for example. Mild depth
> filtering mode is also required for the depth maps based
> mesh reconstruction.
>
> If the area to be reconstructed does not contain meaningful
> small details, then it is reasonable to choose Aggressive
> depth filtering mode to sort out most of the outliers. This
> value of the parameter normally recommended for aerial data
> processing.
>
> Moderate depth filtering mode brings results that are in
> between the Mild and Aggressive approaches. You can
> experiment with the setting in case you have doubts which
> mode to choose.
>
> Additionally depth filtering can be Disabled. But this
> option is not recommended as the resulting point cloud could
> be extremely noisy."
> — *Metashape Pro Manual* 2.3

Operationally:

| Filter mode | Aggressiveness | When to use |
|-------------|:--------------:|-------------|
| **Disabled** | 0% | Diagnostic only — never for production. Shows what the matcher actually saw before any cleanup. |
| **Mild** (default for *Build Mesh* from depth maps) | low | Fine geometric detail (foliage, telecom equipment, intricate close-range objects); poorly-textured surfaces (glass, water, smooth concrete roofs) |
| **Moderate** | medium | When neither Mild nor Aggressive is clearly right; experimental tuning |
| **Aggressive** (default for *Build Point Cloud*) | high | Standard aerial surveys with well-textured surfaces; cleanup of isolated noise points |

### What the filter actually does

The manual elaborates:

> "The filtering modes control noise filtering in the raw
> depth maps. This is done using a connected component filter
> which operates on segmented depth maps based on the pixel
> depth values. The filtering preset control a maximum size of
> connected components that are discarded by the filter."
> — *Metashape Pro Manual* 2.3

Translation: each filter mode has a maximum-size threshold for
"isolated depth-blob" segments. Smaller-than-threshold blobs
are discarded as noise. Aggressive uses the largest threshold
(removes the most blobs), Mild uses the smallest.

## Recipe — Build Depth Maps then Build Point Cloud

> **Demo verified:** ✗ — pending Tier 3 reproduction on a real Metashape install.

```python
import Metashape

chunk = Metashape.app.document.chunk

# Stage 1: depth maps
chunk.buildDepthMaps(
    downscale=2,                              # 2 = High; 4 = Medium; 1 = Ultra-High
    filter_mode=Metashape.FilterMode.AggressiveFiltering,
)

# Stage 2: point cloud (uses the depth maps from stage 1)
chunk.buildPointCloud(
    point_colors=True,
    point_confidence=True,
    keep_depth=True,                           # required if the mesh step will use depth maps
)

print(f"Built point cloud with "
      f"{chunk.point_cloud.point_count if chunk.point_cloud else 0} points")
```

The `downscale` parameter maps to Quality:

| Quality | `downscale=` |
|---------|:------------:|
| Ultra-High | 1 |
| High | 2 |
| Medium | 4 |
| Low | 8 |
| Lowest | 16 |

`filter_mode` values:

- `Metashape.FilterMode.NoFiltering` (Disabled)
- `Metashape.FilterMode.MildFiltering` (Mild)
- `Metashape.FilterMode.ModerateFiltering` (Moderate)
- `Metashape.FilterMode.AggressiveFiltering` (Aggressive)

## Reusing existing depth maps

If you've already built depth maps and want to reuse them for
*Build Point Cloud* (skipping recomputation), pass
`reuse_depth=True`. The Quality and Filter mode are read from
the existing depth maps — they cannot be overridden:

> **Demo verified:** ✗ — pending Tier 3 reproduction on a real Metashape install.

```python
chunk.buildPointCloud(reuse_depth=True)
```

The manual confirms:

> "Depth maps available in the chunk can be reused for the
> point cloud generation operation. Select respective Quality
> and Depth filtering parameters values (see info next to Depth
> maps label on the Workspace pane) in Build Point Cloud
> dialog and then check Reuse depth maps option."
> — *Metashape Pro Manual* 2.3

To change Quality or Filter mode, you must rebuild the depth
maps (which discards the existing set):

```python
chunk.buildDepthMaps(downscale=2, filter_mode=Metashape.FilterMode.MildFiltering)
chunk.buildPointCloud(reuse_depth=True)   # uses the new depth maps
```

## The excessive-overlap pitfall

Long depth-filter runtimes are usually NOT due to the filter
mode but to **excessive image overlap**:

> "Depth filtering may take a long time due to excessive
> overlap. Usually the process is slowed significantly when
> there are overview photos — images that overlap with tens
> and even hundreds of other images. For example, for close
> range objects it means that there are mostly close-up images
> but some photos include the complete object in the frame.
> Or if speaking of aerial survey, the images are taken from
> several heights and the ones taken from the higher altitude
> have lower GSD, resulting in the overlap with considerable
> amount of lower altitude photos."
> — Agisoft support, 2016-01-19, PhotoScan 1.2
> ([permalink](https://www.agisoft.com/forum/index.php?topic=4841.msg24329#msg24329))

The fix: exclude the overview / high-altitude photos from
*Build Point Cloud* (set `camera.enabled = False` on those
cameras). The high-altitude photos contributed positions to
*Align Photos* but rarely add detail to the dense cloud:

> "I can suggest to exclude those general overview images from
> the dense cloud generation process. Usually they are shot in
> lower effective resolution, so actually do not provide any
> quality improvement."
> — Agisoft support, same thread

For the broader high-overlap-cleanup tweak see also
[`main/dense_cloud_max_neighbors` in *Undocumented tweaks*](../../topics/scripting/undocumented-tweaks-reference.md).

## When *Mild* is mandatory

The manual notes one case where Mild is not optional:

> "Mild depth filtering mode is also required for the depth
> maps based mesh reconstruction."
> — *Metashape Pro Manual* 2.3

If you plan to *Build Mesh* from depth maps (the default
mesh-generation path in 1.5+), the depth maps must have been
built with Mild filtering. Aggressive-filtered depth maps will
produce mesh holes where Aggressive removed legitimate small
geometry.

For a workflow that produces both a clean point cloud
(Aggressive) and a usable mesh (Mild), build the depth maps
twice — once with each filter — into separate sets via
`keep_depth=True`. Or build the mesh first from Mild, then
rebuild depth maps with Aggressive for the point cloud.

## Caveats

- **Quality and Filter mode are stored on the depth maps,
  not on the chunk.** Once built, you cannot retroactively
  change the filter mode without rebuilding.
- **`reuse_depth=True` silently inherits the depth maps'
  Quality and Filter mode.** This is a common source of
  confusion when scripts switch between Mild (for mesh) and
  Aggressive (for point cloud) — the second `buildPointCloud`
  with `reuse_depth=True` reuses whatever the depth maps were
  built with, NOT the requested filter.
- **Disabled filter is for diagnostic use only.** The
  resulting point cloud is dominated by sky / texture-mismatch
  noise. Useful for confirming what the matcher saw, not for
  delivery.
- **The 1.x → 2.x renames.** `chunk.dense_cloud` →
  `chunk.point_cloud`; `chunk.buildDenseCloud` →
  `chunk.buildPointCloud`. The depth-maps API
  (`chunk.buildDepthMaps`) is unchanged.
- **GPU memory matters at higher Quality.** Ultra-High depth
  maps on 8K imagery exceed 16GB VRAM on consumer GPUs.
  Metashape will fall back to CPU automatically but with a
  10-20× slowdown. For large projects, plan VRAM and Quality
  together — see [Performance tuning: CPU, RAM, GPU, and OS](../../topics/performance/cpu-ram-gpu-os-tuning.md).

## See also

- [`main/dense_cloud_max_neighbors` (in *Undocumented tweaks*)](../../topics/scripting/undocumented-tweaks-reference.md)
  — the tweak for accelerating excessive-overlap projects.
- [Point cloud confidence values: what they mean and how to filter](../point-cloud/point-cloud-confidence-values.md)
  — post-build cleanup of the point cloud.
- [DEM build options: point cloud vs mesh as source](../dem/build-options.md)
  — the next step after Build Point Cloud.
- [Performance tuning: CPU, RAM, GPU, and OS](../../topics/performance/cpu-ram-gpu-os-tuning.md)
  — hardware planning for high-Quality runs.
- [`Model.renderDepth`: synthetic depth from arbitrary viewpoints](../../topics/scripting/model-render-depth.md)
  — generating depth maps from arbitrary poses (different
  use case from build-depth-maps).

## References

- *Metashape Pro User Manual* (2.3), ch. 4 *Build Point Cloud*
  + ch. 4 *Build Mesh* — both define Quality and Filter mode
  parameters.
- *Metashape Python API Reference* (2.3.1):
  `Chunk.buildDepthMaps`, `Chunk.buildPointCloud`,
  `Chunk.depth_maps`, `FilterMode`, `Chunk.point_cloud`.
- Forum thread, [*depth filtering processing time*, 2016](https://www.agisoft.com/forum/index.php?topic=4841.msg24329#msg24329)
  — excessive-overlap pitfall and the exclude-overview-images
  workaround.
- Forum thread, [*When does depth filtering happen?*, 2013](https://www.agisoft.com/forum/index.php?topic=1108.msg5226#msg5226)
  — clarifies that filter mode is applied at depth-maps stage,
  not at point-cloud stage.

