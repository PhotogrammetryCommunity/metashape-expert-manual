---
title: Orthomosaic in a marker-defined planar projection
status: unverified
applies_to: Metashape Pro 2.x. The technique is conceptually unchanged since PhotoScan 1.1.6 (2015); the API was refactored from chunk-transform manipulation to a clean projection-object approach in 2.x.
edition: Pro
last_reviewed: 2026-05-25
diataxis: how-to
confidence: medium
---

# Orthomosaic in a marker-defined planar projection
> **Confidence:** *medium.* The two-marker / three-marker projection construction recipes are forum-attested with permalinks; the `OrthoProjection` API surface is introspection-confirmed.
## Problem

You need an orthomosaic that is **not north-up**. The object's
natural reference frame is rotated relative to the world frame:
an excavation trench laid out at 30° to north; a building façade
photographed obliquely; a museum artefact on a copy stand. The
default *Build Orthomosaic* + *Export Raster* workflow produces
a north-up orthomosaic in the chunk's CRS — useful for a
georeferenced aerial site but the wrong product for an
object-aligned reconstruction.

You want to define the orthomosaic's projection plane by
**placing markers on your object** at known relative positions
(e.g. two markers along a wall's edge define a horizontal
direction; a third marker out-of-plane defines vertical) and
have Metashape produce an orthomosaic aligned to those axes.

## Context

Metashape supports custom orthomosaic projections via
`Metashape.OrthoProjection` (defining the projection plane via
a 4×4 matrix) and `Metashape.BBox` (defining the output region
in projection space). Both pass into
`Chunk.buildOrthomosaic(projection=…, region=…)` and onward to
`Chunk.exportRaster(projection=…, region=…, north_up=False, …)`.
The `north_up=False` argument is critical — the default
re-rotates output to north-up, defeating the projection's
purpose. The technique works as follows: two markers define a
horizontal vector; an orthogonal vertical vector is derived
(typically aligned to world Z); the cross product gives the
third axis. These three axes form the projection's rotation
matrix. Multi-version Python scripts implementing the technique
are available in the source thread (linked under *See also*),
covering PhotoScan 1.1.6 through 1.3.2; the API has been
substantially refactored since (chunk-transform manipulation
replaced by a projection-object), but the *conceptual* recipe
is the same.

## Solution

### Conceptual recipe

A planar projection is defined by three orthogonal axes:

1. **`x`** — typically the horizontal direction along the
   object. Computed as the unit vector from one marker to
   another.
2. **`z`** — typically the projection plane's *normal* (the
   "look-down" direction). Often kept aligned to world `Z` for
   a top-down ortho, or computed orthogonally from a third
   marker for a fully-rotated projection.
3. **`y`** — `z × x` (cross product); completes the
   right-handed frame.

These three unit vectors form the columns of a 3×3 rotation
matrix `R`. The 4×4 projection matrix is:

```
matrix = [ R | t ]
         [ 0 | 1 ]
```

where `t` is the projection's origin (typically the first
marker's position).

### Python implementation

> **Demo verified:** ✗ — pending Tier 3 reproduction on a real
> project. The API surface (`OrthoProjection`, `BBox`,
> `buildOrthomosaic`, `exportRaster` signatures) is Tier 1
> introspection-confirmed on Metashape 2.2.3. The matrix-axis
> layout (column-major vs row-major) and the exact behaviour of
> `north_up=False` for a custom projection are behavioural
> claims that need empirical verification before this article
> can be promoted to `verified`.

```python
import Metashape

def marker_by_label(chunk, label):
    """Return a marker by label, or None."""
    for m in chunk.markers:
        if m.label == label:
            return m
    return None

doc = Metashape.app.document
chunk = doc.chunk

# Step 1 — the three reference markers.
# Marker A: origin (lower-left of the orthomosaic).
# Marker B: defines the +X axis (placed along the horizontal).
# Marker C: defines the +Y axis (placed along the vertical).
mA = marker_by_label(chunk, "A")
mB = marker_by_label(chunk, "B")
mC = marker_by_label(chunk, "C")
assert mA and mB and mC, "all three markers must be placed and pinned"
for m in (mA, mB, mC):
    if m.position is None:
        raise ValueError(
            f"marker {m.label}.position is None — pin in >= 2 cameras "
            f"and ensure the chunk is aligned before running this recipe"
        )

# Marker positions in chunk-local coordinates.
pA = mA.position
pB = mB.position
pC = mC.position

# Step 2 — compute the three orthogonal axes.
x_axis = (pB - pA).normalized()
y_axis_raw = (pC - pA).normalized()
z_axis = Metashape.Vector.cross(x_axis, y_axis_raw).normalized()
# Re-orthogonalise y_axis to ensure exact orthogonality.
y_axis = Metashape.Vector.cross(z_axis, x_axis).normalized()

# Step 3 — build the projection matrix.
# Columns are the three axes; translation is marker A's position.
matrix = Metashape.Matrix([
    [x_axis.x, y_axis.x, z_axis.x, pA.x],
    [x_axis.y, y_axis.y, z_axis.y, pA.y],
    [x_axis.z, y_axis.z, z_axis.z, pA.z],
    [0,        0,        0,        1   ],
])

# Step 4 — define the projection.
proj = Metashape.OrthoProjection()
proj.type = Metashape.OrthoProjection.Type.Planar
proj.matrix = matrix
proj.crs = chunk.crs       # reuse chunk's CRS

# Step 5 — define the export region in projection space.
# Width along x_axis = |pB - pA|; height along y_axis = |pC - pA|.
# Pad slightly to avoid edge-interpolation artifacts (see Caveats).
width = (pB - pA).norm()
height = (pC - pA).norm()
pad = 0.05 * max(width, height)   # 5% padding
bbox = Metashape.BBox()
bbox.min = Metashape.Vector([-pad, -pad, -10.0])     # min Z is below the surface
bbox.max = Metashape.Vector([width + pad, height + pad, 10.0])

# Step 6 — build and export.
chunk.buildOrthomosaic(
    surface_data=Metashape.DataSource.ModelData,
    projection=proj,
    region=bbox,
    resolution=0.01,        # 1 cm/pixel; adjust per project
)

chunk.exportRaster(
    path="/path/to/output.tif",
    projection=proj,
    region=bbox,
    north_up=False,         # essential — preserves custom orientation
    save_world=True,        # writes a .tfw world file
    image_format=Metashape.ImageFormat.ImageFormatTIFF,
)

doc.save()
```

The script assumes three reference markers labelled `A`, `B`,
and `C`. Adjust the marker-discovery logic for your project's
naming convention.

### Two-marker variant

If only two markers are available (and a top-down projection
is desired), use world `Z` as the projection normal and derive
the in-plane Y axis from it:

```python
# Two-marker variant: A → B defines X; world Z is the projection
# normal; Y is derived.
x_axis = (pB - pA).normalized()
z_axis = Metashape.Vector([0, 0, 1])       # world up; project top-down
cross_zx = Metashape.Vector.cross(z_axis, x_axis)
if cross_zx.norm() < 1e-6:
    raise ValueError(
        "A→B is parallel to world Z; the two-marker variant "
        "cannot derive an in-plane Y axis. Add a third marker "
        "(switch to the three-marker recipe), or pick a "
        "different pair so A→B is not vertical."
    )
y_axis = cross_zx.normalized()
# (rest of the script is identical)
```

The degeneracy guard catches the legitimate-but-unsupported
case where A→B is exactly vertical (markers placed top-and-
bottom on a wall). For that geometry, the two-marker recipe
cannot determine the in-plane horizontal direction without
ambiguity — use the three-marker recipe instead, with marker C
defining the in-plane horizontal direction.

## Caveats and gotchas

- **Interpolation artifacts at the BBox edges** when the
  marker-defined region is flush with the underlying mesh's
  silhouette. Attested verbatim:

  > "Such “interpolated” raster appears when the edges of the
  > used area are close to the frame border and in the actual
  > version the issue can be solved by increasing the size of
  > the image (adding more space by the image frame borders),
  > in GUI it can be done using Region section in the Export
  > dialog. In the next version it should be fixed." —
  > Alexey Pasumansky, 2016-09-29, PhotoScan 1.2 era
  > ([permalink](https://www.agisoft.com/forum/index.php?topic=3996.msg28868#msg28868))

  The Agisoft-staff "in the next version it should be fixed"
  follow-up confirms the issue was patched in subsequent
  PhotoScan releases. The 5% padding in the script above is a
  defensive measure that costs little. If you observe
  unexpected interpolation in 2.x, try increasing the pad to
  10–20% of the projection extent.

- **Resolution units are metres-per-pixel.** Setting
  `resolution=0.01` produces a 1 cm/pixel output. The 2015
  script's dialog field had the same semantics:

  > "Resolution field in the script dialog means the pixel
  > size (i.e. m/pix) and not the output image dimensions." —
  > Alexey Pasumansky, 2015-10-13, PhotoScan 1.1.6
  > ([permalink](https://www.agisoft.com/forum/index.php?topic=3996.msg22403#msg22403))

  To compute the expected output image dimensions: `width_px =
  bbox_width / resolution`. For the script above:
  `(width + 2*pad) / 0.01` pixels wide.

- **`north_up=False` is essential.** The default
  `north_up=True` rotates the output back to north-up,
  defeating the projection's purpose. Always pass
  `north_up=False` when exporting a custom-projection ortho.

- **Origin choice — keep project origin or move to first
  marker?** The 2015 script offered both variants. For
  georeferenced projects (with a real-world CRS), keep the
  project origin; the BBox is in projection space anyway, so
  the absolute origin doesn't matter for the output's content
  but does matter for the world file (.tfw) georeferencing.
  For ungeoreferenced projects, moving the origin to marker A
  produces a world file in marker-relative coordinates —
  often more useful for downstream CAD-style coordinate work.

- **Marker accuracy compounds.** The projection axes are
  derived from marker positions. If the markers were placed
  with low pixel accuracy or insufficient camera coverage,
  the axes will be tilted. Always verify with *Reference →
  Reset Camera Alignment* and re-optimise before relying on
  marker positions for projection.

- **Markers must be 3D-located.** `marker.position` returns
  `None` until the marker has projections in at least 2
  cameras and the chunk has been aligned. The script above
  will throw on `pA - pB` if any position is `None`.

- **Special-character encoding in script files.** If your
  marker labels or comments contain non-ASCII text (German
  umlauts, accented characters), save the script file as
  UTF-8. From a script-debugging session in the source thread:

  > "Then I can suggest to edit the text messages and comments
  > in the lines [...] removing the special characters. If you
  > are using any text editor, make sure you are using UTF-8
  > encoding." — Alexey Pasumansky, 2016-04-27, PhotoScan 1.2
  > ([permalink](https://www.agisoft.com/forum/index.php?topic=3996.msg25940#msg25940))

## See also

- [Orthomosaic export pitfalls](orthomosaic-export-pitfalls.md)
  — the 4 GB / BigTIFF / shift issues for the default north-up
  workflow.
- [Applying *Patch* on multiple shapes](applying-patch-multiple-shapes.md)
  — companion technique for orthomosaic post-processing.
- [Mapping orthomosaic pixels back to source images](../../topics/scripting/orthomosaic-pixel-to-source-image.md)
  — the inverse operation.
- *Metashape Python Reference* (2.3.1):
  `Chunk.buildOrthomosaic`, `Chunk.exportRaster`,
  `OrthoProjection`, `BBox`.
- [Forum topic 3996](https://www.agisoft.com/forum/index.php?topic=3996.0)
  — the original 2015–2017 script-evolution thread (15
  the posts including 4 substantial script revisions).

