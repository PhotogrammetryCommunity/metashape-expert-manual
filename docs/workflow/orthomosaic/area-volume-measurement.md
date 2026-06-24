---
title: "Area and volume measurement: Model view vs DEM, Shapes vs cropping"
status: unverified
applies_to: Metashape Pro 2.x — and unchanged from PhotoScan 1.x
edition: Pro
last_reviewed: 2026-06-05
diataxis: explanation
confidence: high
---

# Area and volume measurement: Model view vs DEM, Shapes vs cropping

> **Confidence:** *high.* The Model-view-Shapes limitation is
> directly attested by Agisoft support with permalink. The
> crop-then-measure workaround and the duplicate-with-boundary
> workflow are forum-attested across multiple replies.

## Problem

You drew a polygon shape on the model, right-clicked it, and
selected *Measure*. The dialog shows a perimeter but the area
field is blank or zero. Or: you measured area on the *DEM* view
for a sloped roof and got a value smaller than the actual
inclined surface area. Both are not bugs — they reflect how
Metashape's measurement tools work.

## The two measurement contexts

Metashape has two distinct area/volume measurement subsystems:

| Subsystem | Inputs | Output dimensions |
|-----------|--------|-------------------|
| *Tools → Measure Area & Volume* (Model view) | The active mesh, ALL polygons | 3D inclined surface area; volumetric volume |
| *Right-click shape → Measure* (DEM / Ortho view) | A polygon shape on a DEM | XY-plane (planimetric) area; volume below or above the polygon plane |

The Model-view version measures the **actual inclined mesh
area** but operates on the entire mesh (or whatever is left
after cropping). The DEM-view version respects shape boundaries
but measures **planimetric area only** — a sloped roof's
measured area equals its plan footprint.

## The Shapes-on-Model-view limitation

> "Area and volume measurements in the Model view are not
> supported via Shapes. Currently the only way to measure the
> area on the mesh is to crop everything except the area of
> interest and run *Tools Menu → Measure Area & Volume*
> function, it will sum the area of every polygon left, then
> you can undo the polygons removal."
> — Agisoft support, 2018-04-27, PhotoScan 1.4
> ([permalink](https://www.agisoft.com/forum/index.php?topic=8879.msg41875#msg41875))

In Model view, the *Measure* command does not accept polygon
shapes as boundary input. To measure inclined surface area
within a region:

1. **Draw the polygon shape in Ortho view.** Switch to *Ortho*
   view (you can switch even without an orthomosaic generated;
   the view shows the chunk's geometry from above).
2. **Set its boundary type to Outer Boundary.** Right-click the
   shape and choose *Set Boundary Type → Outer Boundary*.
3. **Duplicate the mesh with clip-to-boundary enabled.**
   Right-click the model in the Workspace pane → *Duplicate
   Asset* → check *Clip to boundary shapes*.
4. **Measure on the duplicate.** Switch to Model view, ensure
   the duplicated mesh is active, and run *Tools → Measure Area
   & Volume*.
5. **Discard the duplicate** when done (it was only needed for
   the measurement).

> "Currently I can only suggest to switch the type of the
> polygonal shape to Outer Boundary, then duplicate the mesh
> model with 'clip to boundary shapes' option enabled. After
> that use Measure Area & Volume option in Tools menu."
> — Agisoft support, 2021-04-14, Metashape 1.7
> ([permalink](https://www.agisoft.com/forum/index.php?topic=8879.msg58893#msg58893))

## Python automation for many polygons

When you have many shapes (e.g., one per building roof on an
aerial survey), the GUI duplicate-and-measure loop is tedious.
A Python pattern using the Tasks API:

> **Demo verified:** ✗ — pending Tier 3 reproduction on a real Metashape install.

```python
import Metashape

chunk = Metashape.app.document.chunk

results = []
for shape in chunk.shapes:
    if not shape.geometry:
        continue
    # 1. Promote each shape to outer-boundary
    shape.boundary_type = Metashape.Shape.OuterBoundary

    # 2. Duplicate the mesh with clip-to-boundary
    task = Metashape.Tasks.DuplicateAsset()
    task.asset = chunk.model.key
    task.clip_to_boundary_shapes = True
    task.apply(chunk)
    duplicated = chunk.models[-1]

    # 3. Sum face areas on the duplicate (= inclined surface area)
    surface_area = sum(
        face_area_3d(duplicated, face) for face in duplicated.faces
    )
    results.append((shape.label, surface_area))

    # 4. Discard the duplicate
    chunk.remove([duplicated])

    # 5. Reset the shape's boundary type
    shape.boundary_type = Metashape.Shape.NoBoundary
```

`face_area_3d` is the standard triangle-area formula:
`0.5 * (v1 - v0).cross(v2 - v0).norm()` over each face's three
vertices. The sum gives the total inclined surface area in
chunk units (multiply by `chunk.transform.scale` for metres on
georeferenced chunks).

## DEM-based measurements

> "DEM based measurements for area wouldn't include the roof
> inclination and you'll get the area in XY plane based on the
> input shape."
> — Agisoft support, 2018-04-27, PhotoScan 1.4
> ([permalink](https://www.agisoft.com/forum/index.php?topic=8879.msg41875#msg41875))

DEM-based measurements are **planimetric** by construction: the
DEM is a 2.5D height-field, so area is computed in the XY plane
regardless of slope. For a flat-roofed building this matches
the inclined area; for any sloped roof it does not.

If you need:

- **Footprint area** (e.g., for property tax, planning permits) —
  use DEM measurement; the planimetric value is what those
  contexts expect.
- **Roof surface area** (e.g., for solar-panel coverage, roofing
  cost) — use the Model-view duplicate-and-crop workflow above.
- **Excavation or fill volume** between two epochs — see
  [Mesh and point-cloud editing recipes](../../topics/scripting/mesh-pointcloud-editing-recipes.md)
  Recipe 4 (chunk-diff workflows).

## The Outer Boundary type quirk

Until at least Metashape 2.1, the *Set Boundary Type → Outer
Boundary* option is only exposed in the *Ortho* and *DEM*
views, not in *Model* view. To set the type while working
mostly in Model view:

1. Switch to *Ortho* view (no orthomosaic needed; the view
   renders the geometry from above).
2. Right-click the shape → *Set Boundary Type → Outer Boundary*.
3. Switch back to *Model* view to do the measurement.

## Caveats

- **The crop-and-measure workaround is destructive** if you
  forget to duplicate the mesh first. *Always* duplicate before
  cropping so the original mesh survives the operation.
- **`Tools → Measure Area & Volume`** sums face areas of the
  *active* mesh. If multiple meshes are visible, the active one
  (highlighted in the Workspace pane) is the measurement target.
- **Volume measurements in Model view** require a closed mesh.
  Open meshes (e.g., a flat roof patch with no underside) report
  zero or undefined volume. To get a closed mesh, use *Tools →
  Mesh → Close Holes…* with appropriate parameters before
  measuring.
- **Ortho-view planimetric volumes** require an explicit
  reference plane (the "below the polygon plane" reference). The
  default reference is the lowest point in the polygon's
  footprint; for surveying applications you may need to set a
  custom reference plane via the *Measure Volume* dialog.

## See also

- [Mesh and point-cloud editing recipes](../../topics/scripting/mesh-pointcloud-editing-recipes.md)
  — Recipe 3 (mesh-to-shape clipping) and Recipe 4 (chunk-diff
  for volume change detection).
- [Applying *Patch* on multiple shapes](applying-patch-multiple-shapes.md)
  — companion pattern of iterating over chunk shapes for batch
  workflows.

## References

- *Metashape Pro User Manual* (2.3), ch. 6 *Measurements →
  Distances, areas and volumes* — describes both subsystems.
- [*Measurement tools in Model view* (Agisoft KB)](https://agisoft.freshdesk.com/support/solutions/articles/31000170365),
  [*DEM based measurements* (Agisoft KB)](https://agisoft.freshdesk.com/support/solutions/articles/31000148884),
  and [*Mesh model based volume measure* (Agisoft KB)](https://agisoft.freshdesk.com/support/solutions/articles/31000166942)
  — Agisoft's how-tos for the Model-view ruler/profile/shape
  tools, the planimetric DEM measurements, and closed-mesh volume
  (Close Holes + Measure Area & Volume) respectively.
- *Metashape Python API Reference* (2.3.1):
  `Shape.boundary_type`, `Shape.OuterBoundary`,
  `Tasks.DuplicateAsset`, `Model.faces`, `Model.vertices`.
- Forum thread, [*Area calculation — Only getting perimeter
  measure*, 2018-2021](https://www.agisoft.com/forum/index.php?topic=8879.msg42196#msg42196)
  — the workaround chain (the 2018-04-27 thread + 2021-04-14;
  the batch-script extension 2021-04-15).

