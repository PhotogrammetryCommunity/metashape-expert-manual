---
title: "Comparing chunks for change detection: DEM, mesh, and point-cloud diff workflows"
status: unverified
applies_to: Metashape Pro 2.x — and PhotoScan 1.x; DEM differences are native (Transform DEM), while mesh/point-cloud diffs route through external tools
edition: Pro
last_reviewed: 2026-06-05
diataxis: how-to
confidence: high
---

# Comparing chunks for change detection: DEM, mesh, and point-cloud diff workflows

> **Confidence:** *high.* DEM differencing is native (*Transform
> DEM → Calculate difference*, Workflow 0). The remaining point —
> that there is no one-click chunk-to-chunk *mesh / point-cloud*
> diff — is forum-attested (Agisoft support, 2017) and still holds
> in 2.x; the external-tool triage is reconstructed from
> multi-author thread replies.

## Problem

You have two chunks of the same site captured at different
times — before / after excavation, before / after construction,
seasonal change of a glacier or river. You need to quantify the
change: cubic metres of material removed, areas of subsidence,
average height difference. Metashape exposes per-chunk
*Measure Volume* and *Measure Area* tools, and — for **DEM**
surfaces — a native difference operator (*Tools → Transform DEM*
with *Calculate difference*, described next). For **mesh or
point-cloud** change, or for cross-package analysis, there is
still no one-click chunk-to-chunk operator, so the established
route is to export and diff in an external tool.

> "In current version of PhotoScan you cannot subtract DEM models
> produced in different chunks, so you need to do that with the
> exported results in the external GIS applications (like
> GlobalMapper or Q-GIS, for example)."
> — Agisoft support, 2017-05-15, PhotoScan 1.3
> ([permalink](https://www.agisoft.com/forum/index.php?topic=7056.msg34042#msg34042))

**That 2017 answer is now outdated for DEMs.** Current Metashape
Professional can subtract one DEM from another natively via
*Tools → Transform DEM* with the *Calculate difference* option:
import the other chunk's DEM into the project first (or keep both
as DEM instances in one chunk), then difference them to produce a
result DEM — [*DEM difference calculation* (Agisoft KB)](https://agisoft.freshdesk.com/support/solutions/articles/31000156301).
The external-tool route below is still worthwhile for finer
control over resampling, for **mesh / point-cloud** diffs that a
2.5-D DEM cannot represent, and for cross-package analysis.

## Pre-requisite: chunk co-registration

Before any diff operation produces meaningful numbers, both
chunks must be in the **same world coordinate frame**. A 1 cm
horizontal misalignment can produce 100+ m³ of spurious volume
difference on a 100 m × 100 m area.

Three co-registration strategies:

1. **Shared GCPs.** Most robust. Place the same surveyed marker
   set in both chunks; the markers' identical world coordinates
   force the chunks into a common frame.
2. **`Align Chunks → Method: Marker`.** Use markers visible in
   both chunks (e.g., painted ground targets that survived from
   epoch 1 to epoch 2).
3. **`Align Chunks → Method: Point cloud`.** ICP-style alignment
   on the dense clouds; works when no markers exist but
   stability is poor near the actively-changing area (the
   alignment is biased by the change region).

Verify alignment quality after `Align Chunks` using
*Tools → Reference → Inspect Markers* — marker errors should be
sub-cm for high-quality diff work.

For the broader chunk-alignment topic see
[Align Chunks: three methods](../../workflow/chunks/alignchunks-three-methods.md).

## Four diff workflows

| Workflow | Tool | Best for | Output |
|----------|------|----------|--------|
| 0. **Native DEM difference** | Metashape *Transform DEM* | quick in-app DEM change, same project | Result DEM layer |
| 1. **DEM raster subtraction** | QGIS / GlobalMapper / ArcGIS | rasterised surfaces (terrain) | Difference GeoTIFF |
| 2. **Point-cloud cloud-to-cloud** | CloudCompare | overhanging or non-rasterisable geometry | Per-point distance values |
| 3. **Per-chunk volume measurement** | Metashape native | quick excavation / earthwork volumes | Two scalar volumes; subtract manually |

## Workflow 0 — native DEM difference (Transform DEM)

For DEM surfaces this is the quickest path and needs no external
tool. Bring both epochs' DEMs into one project, then:

1. *File → Import → Import DEM* to add the second epoch's DEM
   alongside the first (a chunk can hold several DEM instances).
2. Select the DEM to subtract *from*, open *Tools → Transform
   DEM…*, enable *Calculate difference*, and pick the other DEM
   from the dropdown.
3. *OK* produces a new difference-DEM layer (positive =
   accumulation, negative = loss) that you can measure or export.

It is exact and georeferenced but shares the DEM's 2.5-D
limitation (no overhangs), and gives less control over resampling
than a GIS. For mesh / point-cloud change use the export-and-diff
workflows below. See [*DEM difference calculation* (Agisoft KB)](https://agisoft.freshdesk.com/support/solutions/articles/31000156301).

## Workflow 1 — DEM raster subtraction (GIS)

Standard workflow for terrain change detection (excavations,
landslides, glacier retreat):

1. Build DEM in each chunk: *Workflow → Build DEM* with
   identical projection, identical pixel size, identical
   bounding box.
2. Export each as GeoTIFF: *File → Export → Export DEM*. Set
   *Region* identically in both exports (use the same shape
   boundary in both chunks).
3. Open both rasters in QGIS:
   *Raster → Raster Calculator*
   ```
   "after@1" - "before@1"
   ```
4. The output is a difference raster in metres (positive =
   accumulation, negative = excavation).
5. Compute volume:
   *Raster → Zonal Statistics* on the difference raster, or
   *r.volume* in GRASS, or:
   ```
   total_volume = SUM(diff_pixel_value × pixel_area_m²)
   ```

**Pros:**
- Preserves georeferencing; output is directly drape-able on
  basemaps.
- Resolution-controllable (downscale before subtraction for
  smoothing).
- Handles arbitrary horizontal extents.

**Cons:**
- 2.5D — fails on overhanging geometry (cliffs, caves,
  buildings).
- Requires both DEMs to be in the same horizontal CRS.
- Pixel-size mismatch between exports forces a resampling
  step (use bilinear interpolation; nearest-neighbour
  exaggerates noise).

### Quick QGIS Python recipe

> **Demo verified:** ✗ — This is QGIS Python, not Metashape Python; verify the QGIS API on your install.

```python
# QGIS Python console
from qgis.analysis import QgsRasterCalculator, QgsRasterCalculatorEntry

before = iface.mapCanvas().layers()[0]  # your "before" DEM layer
after  = iface.mapCanvas().layers()[1]  # your "after" DEM layer

entries = [
    QgsRasterCalculatorEntry().__init__(name="b@1", layer=before, ref=1),
    QgsRasterCalculatorEntry().__init__(name="a@1", layer=after,  ref=1),
]
calc = QgsRasterCalculator(
    "a@1 - b@1",
    "/path/diff.tif",
    "GTiff",
    after.extent(),
    after.width(),
    after.height(),
    entries,
)
calc.processCalculation()
```

## Workflow 2 — CloudCompare cloud-to-cloud

For high-precision diffs or non-rasterisable geometry (cliffs,
indoor scans, vegetation canopy):

1. Build dense point cloud in each chunk:
   *Workflow → Build Point Cloud*. Use Mild filtering for
   change-detection accuracy (Aggressive removes legitimate
   small-scale features alongside noise).
2. Export both: *File → Export → Export Points* with
   `crs = chunk.crs` (see
   [`exportPointCloud` defaults: GUI vs Python CRS difference](../../workflow/export-reporting/exportpoints-crs-default.md)).
3. Open both in CloudCompare.
4. Verify alignment in 3D view — should overlap visually except
   in the change region.
5. *Tools → Distances → Cloud-to-Cloud Distance*:
   - Reference cloud: "before"
   - Compared cloud: "after"
   - Output: per-point signed distance.
6. Apply a colour ramp on the distance scalar field for
   visualisation; export the coloured cloud as PLY.

**Pros:**
- Higher spatial resolution than rasterised DEMs.
- Handles overhanging / non-2.5D geometry.
- Free, well-documented (CloudCompare wiki).

**Cons:**
- The output is a per-point distance; converting to volume
  requires extra steps (e.g., 2.5D rasterisation followed by
  workflow 1).
- Asymmetric: cloud-to-cloud distance is not symmetric
  (B→A ≠ A→B in general); use M3C2 (a CloudCompare plugin) for
  signed-distance with normal-aware comparisons.

## Workflow 3 — Per-chunk volume measurement

For quick excavation / earthwork volume estimates without
external tools:

1. In each chunk, draw the **same** polygon shape covering the
   area of interest. Critical: the polygons must have identical
   vertices in world coordinates. The simplest way: draw the
   shape in chunk 1, copy it to chunk 2 via:
   ```
   chunk_1.shapes → right-click → Copy →
   chunk_2.shapes → right-click → Paste
   ```
2. In each chunk: right-click the shape → *Measure Volume*. The
   dialog asks for a reference plane; use *Best Fit Plane* in
   both chunks for consistency.
3. Subtract:
   ```
   excavated_volume = volume_before - volume_after
   ```

**Pros:**
- No external tools required.
- Polygons-from-Metashape preserve exact vertex coordinates,
  guaranteeing identical reference geometries.

**Cons:**
- The "reference plane" choice (best-fit vs three-point) must
  match between epochs. Using *Best Fit* in one chunk and
  *Three Points* in the other yields incomparable volumes.
- One scalar per epoch: no spatial distribution of change.
- Multi-region projects need one polygon per region —
  cumbersome for many regions.

You can also draw a polygon shape and use the **Measure Volume**
tool, which reports the volume between the polygon and the
DEM or mesh surface (*Tools → Measure → Volume*, on a closed
shape).

## Caveats

- **Chunk alignment quality dominates.** If your alignment
  marker error is 5cm RMS, your volume diff is unreliable
  below that scale. Use post-processed kinematic (PPK) GNSS
  or surveyed monuments for high-precision diff work.
- **Vegetation, wind, lighting changes** between epochs add
  noise that the diff cannot distinguish from real change.
  Where possible: capture both epochs at similar time of day,
  similar leaf-on/leaf-off state, similar wind. For glacier /
  earthwork monitoring, late-summer captures with low vegetation
  give the cleanest diffs.
- **Edge effects.** Both DEMs and point clouds have lower
  density and higher noise at the project's edges. Crop the
  diff result to the well-overlapped interior using a smaller
  inner shape boundary.
- **Differential scale errors.** If chunk 1 has scale-bar
  control but chunk 2 does not, a small scale difference can
  manifest as systematic Z-error proportional to height above
  ground. Use shared scale bars or shared GCPs.
- **Filter consistency.** Both chunks must use the same
  point-cloud filter setting (all Mild, all Moderate, all
  Aggressive) — otherwise you're diffing different
  representations of the surface, not different surfaces.

## See also

- [Align Chunks: three methods](../../workflow/chunks/alignchunks-three-methods.md)
  — pre-requisite for any chunk-diff workflow.
- [Mesh and point-cloud editing recipes](mesh-pointcloud-editing-recipes.md)
  — Recipe 4 is a companion overview of the same chunk-comparison
  options (native DEM diff, GIS, CloudCompare, per-chunk volume).
- [Area and volume measurement: Model view vs DEM, Shapes vs cropping](../../workflow/orthomosaic/area-volume-measurement.md)
  — the per-chunk *Measure Volume* mechanics in detail.
- [`exportPointCloud` defaults: GUI vs Python CRS difference](../../workflow/export-reporting/exportpoints-crs-default.md)
  — for clean point-cloud exports into CloudCompare.

## References

- *Metashape Pro User Manual* (2.3), ch. 6 *Measurements →
  Volume measurement* — describes the per-chunk *Measure Volume*
  dialog.
- [*DEM difference calculation* (Agisoft KB)](https://agisoft.freshdesk.com/support/solutions/articles/31000156301)
  — the native *Tools → Transform DEM → Calculate difference*
  operator (Workflow 0).
- *CloudCompare Wiki*, [Cloud-to-Cloud Distance](https://www.cloudcompare.org/doc/wiki/index.php/Cloud-to-Cloud_Distance)
  — workflow 2 reference (external).
- *QGIS Documentation*, [Raster Calculator](https://docs.qgis.org/latest/en/docs/user_manual/processing_algs/qgis/rasteranalysis.html#raster-calculator)
  — workflow 1 reference (external).
- Forum thread, [*Comparing chunks: volume calculations*, 2017](https://www.agisoft.com/forum/index.php?topic=7056.msg34042#msg34042)
  — the canonical Q&A; multiple users contribute the three-
  workflow triage.

