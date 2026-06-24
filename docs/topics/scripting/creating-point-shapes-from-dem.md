---
title: "Creating point shapes programmatically: grid placement with DEM-based elevation"
status: unverified
applies_to: Metashape Pro 2.x — and Metashape Pro 1.7+ via the same `chunk.shapes` API and `Elevation.altitude` method (the `Geometry.Point` constructor was introduced in 1.7)
edition: Pro
last_reviewed: 2026-06-01
diataxis: how-to
confidence: high
---

# Creating point shapes programmatically: grid placement with DEM-based elevation

> **Confidence:** *high.* The recipe is forum-attested with
> permalink (Agisoft support, 2024). The
> `Chunk.shapes`, `Shapes.addShape`, `Geometry.Point`,
> `Elevation.altitude`, `Elevation.left/right/top/bottom`,
> and degree-conversion API are introspection-confirmed on
> Metashape 2.2.

## Problem

You need to create a **regular grid of point shapes** across
your project area, each at the correct elevation per a built
DEM. Common use cases:

- **Volumetric monitoring**: a fixed grid of measurement
  points to track elevation changes between epochs.
- **Cross-section sampling**: extracting per-grid-cell DEM
  values for downstream analysis (water flow, cut/fill).
- **Pre-positioned check points**: marker locations that
  follow the terrain for later GCP verification.
- **Sparse point exports for GIS**: creating a regular grid
  of attributed points (Z = DEM altitude) for QGIS / ArcGIS
  consumption.

Manually clicking each shape in the GUI is impractical for
grids of more than ~20 points. The Python API supports
programmatic shape creation, including elevation lookup via
`chunk.elevation.altitude(point_2d)`.

## Recipe — N×N grid with DEM-derived Z

This recipe is the canonical pattern from Agisoft support's
2024 forum reply:

> "Please see the example below that creates a grid of point
> shapes with elevation calculated based on DEM altitude in
> corresponding XY location"
> — Agisoft support, 2024-06-24, Metashape 2.1
> ([permalink](https://www.agisoft.com/forum/index.php?topic=16516.msg70934#msg70934))

> **Demo verified:** ✗ — pending Tier 3 reproduction on a real Metashape install.

```python
import Metashape

def convert_meters_to_deg(value_m, chunk):
    """For geographic CRSes (lat/lon), convert metres to a
    longitude/latitude step pair. For projected CRSes (UTM,
    State Plane), the value is already in metres."""
    crs = chunk.crs
    if crs is None or crs.authority != "EPSG::4326":
        return Metashape.Vector([value_m, value_m])

    T = chunk.transform.matrix
    origin = chunk.region.center
    origin_geoc = T.mulp(origin)
    origin_geog = crs.project(origin_geoc)

    # Longitude scale at this latitude (metres per 1e-5 degree)
    pt_lon = origin_geog + Metashape.Vector([1e-5, 0, 0])
    v_x = (crs.unproject(pt_lon) - origin_geoc).norm() * 1e5
    # Latitude scale (metres per 1e-5 degree)
    pt_lat = origin_geog + Metashape.Vector([0, 1e-5, 0])
    v_y = (crs.unproject(pt_lat) - origin_geoc).norm() * 1e5

    return Metashape.Vector([value_m / v_x, value_m / v_y])

def create_grid_of_point_shapes(step_m=10.0):
    """Create a grid of point shapes spaced step_m metres apart,
    each with elevation read from the chunk's DEM."""
    chunk = Metashape.app.document.chunk
    if not chunk or not chunk.elevation:
        raise RuntimeError("Active chunk must have a built DEM")

    dem = chunk.elevation
    # DEM bounds (in DEM CRS coords — typically same as chunk CRS)
    x_min, x_max = dem.left, dem.right
    y_min, y_max = dem.bottom, dem.top

    # Ensure shapes container exists
    if not chunk.shapes:
        chunk.shapes = Metashape.Shapes()
        chunk.shapes.crs = dem.crs

    group = chunk.shapes.addGroup()
    group.label = f"Grid points (step {step_m:.1f} m)"

    # Convert step to CRS units (degrees for EPSG:4326, metres otherwise)
    step = convert_meters_to_deg(step_m, chunk)

    n_created = 0
    y = y_min
    while y < y_max:
        x = x_min
        while x < x_max:
            # Look up DEM altitude at this XY
            altitude = dem.altitude(Metashape.Vector([x, y]))
            # NaN != NaN in IEEE 754; this detects DEM holes returned as NaN.
            if altitude is None or not (altitude == altitude):
                x += step.x
                continue

            # Create the point shape
            shape = chunk.shapes.addShape()
            shape.geometry = Metashape.Geometry.Point(
                Metashape.Vector([x, y, altitude])
            )
            shape.group = group
            shape.label = f"({x:.6f}, {y:.6f})"
            n_created += 1

            x += step.x
        y += step.y

    print(f"Created {n_created} point shapes in group {group.label!r}")

# Usage
create_grid_of_point_shapes(step_m=10.0)
```

The full script (with GUI dialog for the step-size prompt) is
at the source forum thread (msg 72856).

## How `dem.altitude(point_2d)` works

`Elevation.altitude(point)` accepts a 2D `Vector` with the
DEM's CRS coordinates and returns the interpolated elevation
at that location:

| Input | Output |
|-------|--------|
| `(x, y)` inside the DEM extent, valid cell | Z value (float, metres in the DEM's vertical datum) |
| `(x, y)` outside the DEM extent | `None` |
| `(x, y)` over a hole (no DEM cell) | `None` or `NaN` (version-dependent; the recipe checks both) |

For CRSes other than the DEM's, transform first:

```python
target_crs = chunk.crs
dem_crs = chunk.elevation.crs
if target_crs != dem_crs:
    point_in_dem_crs = Metashape.CoordinateSystem.transform(
        point_in_target_crs, target_crs, dem_crs
    )
else:
    point_in_dem_crs = point_in_target_crs

altitude = chunk.elevation.altitude(point_in_dem_crs)
```

## Geographic CRS step-size pitfall

The recipe handles a subtle issue: in **geographic CRSes**
(EPSG:4326 / WGS84 lat-lon), the units are degrees, not
metres. A "10-metre step" doesn't map to a constant degree
value — the longitude-degree size shrinks as you move toward
the poles.

The `convert_meters_to_deg` function handles this by:

1. Taking the chunk's region centre as a reference point.
2. Converting it to ECEF (geocentric metres).
3. Computing the **local** distance per 1e-5 degree of
   longitude (varies with latitude) and per 1e-5 degree of
   latitude (≈ 111,320 m everywhere).
4. Returning the appropriate degree-step for the requested
   metre-step.

For projected CRSes (UTM zone N, State Plane, local-grid),
the step is already in metres and the function returns the
input verbatim.

## Removing or modifying shape groups

To clean up after a grid creation pass — or to remove an
incorrect grid before re-running:

> **Demo verified:** ✗ — pending Tier 3 reproduction on a real Metashape install.

```python
import Metashape

chunk = Metashape.app.document.chunk

# Remove all shapes in the most-recently-created group
target_label = "Grid points (step 10.0 m)"
target_group = next(
    (g for g in chunk.shapes.groups if g.label == target_label),
    None,
)
if target_group:
    # Remove the shapes belonging to the group, then the group itself
    shapes_to_remove = [s for s in chunk.shapes if s.group == target_group]
    for shape in shapes_to_remove:
        chunk.shapes.remove(shape)
    chunk.shapes.remove(target_group)
    print(f"Removed group {target_label!r} ({len(shapes_to_remove)} shapes)")
```

The shapes-then-group order matters: if you remove the group
first, its child shapes become orphaned but the API may not
allow that operation in 2.x.

> "You need to remove the shapes from the layer first, then
> remove the layers."
> — Agisoft support, 2018-08-24, PhotoScan 1.4
> ([permalink](https://www.agisoft.com/forum/index.php?topic=9587.msg44910#msg44910))

## Caveats

- **DEM must exist before grid creation.** The recipe checks
  `chunk.elevation`; without a built DEM, it raises. To build
  the DEM first, see [DEM build options: point cloud vs
  mesh as source](../../workflow/dem/build-options.md).
- **DEM CRS may differ from chunk CRS.** The recipe assumes
  they match (the script's `chunk.shapes.crs = DEM.crs` line
  ensures shape coords are stored in the DEM's CRS). For
  cross-CRS workflows, transform via
  `Metashape.CoordinateSystem.transform(...)`.
- **Holes in the DEM produce skipped points.** The recipe's
  `if altitude is None` check skips them silently. For a
  filled grid (every cell has a point, even over holes), use
  the *Extrapolated* interpolation mode when building the
  DEM — see the DEM-build-options article.
- **Performance** — for grids exceeding ~10,000 points, the
  per-point shape creation becomes slow (each `addShape` call
  has overhead). For very large grids, batch-create shapes via
  Python, then save the project once at the end (not after
  each shape).
- **Z-axis convention**. The recipe creates 3D point shapes;
  `Geometry.Point(Vector([x, y, z]))` produces a point with
  the explicit Z value. For 2D point shapes (no Z), pass
  `Vector([x, y])` instead — but Metashape will then assign
  a default Z (typically 0 or the chunk's bounding-box top).
- **`convert_meters_to_deg` only detects EPSG:4326 as a
  geographic CRS.** Other geographic (degrees-based) CRSes
  exist — EPSG:4269 (NAD83), EPSG:4674 (SIRGAS 2000),
  EPSG:4258 (ETRS89), and so on. The recipe will silently
  treat them as projected CRSes and use the requested step
  value as if it were already in the CRS units, producing a
  wildly wrong grid. If your project is in a non-WGS84
  geographic CRS, either modify the authority check
  (`crs.authority not in ("EPSG::4326", "EPSG::4269", ...)`)
  or convert your project to EPSG:4326 first.

## See also

- [Working with shape geometries (1.7+ API)](shape-geometry-api.md)
  — the broader `chunk.shapes` API surface.
- [DEM build options: point cloud vs mesh as source](../../workflow/dem/build-options.md)
  — pre-requisite for using `dem.altitude()`.
- [Auto-export per-shape: orthomosaic, DEM, point cloud, mesh, KMZ](../../workflow/export-reporting/auto-export-per-shape.md)
  — once the grid is created, this article exports per-shape
  products.
- [Mesh and point-cloud editing recipes](mesh-pointcloud-editing-recipes.md)
  — broader collection of Python recipes for mesh / cloud /
  shape manipulation.

## References

- *Metashape Python API Reference* (2.3.1):
  `Chunk.shapes`, `Shapes.addShape`, `Shapes.addGroup`,
  `Shapes.remove`, `Shapes.groups`, `Shape.geometry`,
  `Shape.group`, `Shape.label`, `Geometry.Point`,
  `Elevation.altitude`, `Elevation.left`, `Elevation.right`,
  `Elevation.top`, `Elevation.bottom`, `Elevation.crs`,
  `CoordinateSystem.transform`, `CoordinateSystem.project`,
  `CoordinateSystem.unproject`.
- Forum thread, [*script inserting points with Z label*, 2024](https://www.agisoft.com/forum/index.php?topic=16516.msg70934#msg70934)
  — the canonical recipe for grid creation with DEM-derived
  elevation.
- Forum thread, [*remove shape layers*, 2018](https://www.agisoft.com/forum/index.php?topic=9587.msg44910#msg44910)
  — the shapes-then-group cleanup pattern.

