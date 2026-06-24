---
title: "Programmatic chunk.region control: move, scale, rotate the bounding box"
status: unverified
applies_to: Metashape Pro 2.x — pattern from `region_control.py` in the official metashape-scripts repo
edition: Pro
last_reviewed: 2026-05-30
diataxis: how-to
confidence: high
---

# Programmatic chunk.region control: move, scale, rotate the bounding box

> **Confidence:** *high.* The pattern is from Agisoft's
> official [`metashape-scripts`](https://github.com/agisoft-llc/metashape-scripts)
> repo (`region_control.py`). The `Chunk.region`,
> `Region.center`, `Region.size`, `Region.rot` API is
> introspection-confirmed on Metashape 2.2.

## Problem

The chunk's bounding box (`chunk.region`) controls which part
of the project gets reconstructed during *Build Point Cloud*,
*Build Mesh*, *Build DEM*, etc. Adjusting it precisely from
the GUI's *Region* toolbar buttons works for small tweaks but
becomes tedious for:

- **Mid-flight repositioning** during scripted batch
  workflows.
- **Per-pass cropping** (e.g., shrinking the region for
  high-resolution mesh of a sub-region after a low-resolution
  full-area pass).
- **Programmatic alignment of the region to a feature
  axis** (e.g., setting the region's red face parallel to a
  building façade for Height-field reconstruction).
- **Multi-chunk consistency** (giving every chunk in a
  split-in-chunks workflow the same region size).

The [`region_control.py`](https://github.com/agisoft-llc/metashape-scripts/blob/master/src/region_control.py)
script provides a GUI dialog for these operations. This article
documents the underlying API patterns.

## The `Chunk.region` API

`chunk.region` is a `Region` object with three attributes:

| Attribute | Type | Meaning |
|-----------|------|---------|
| `center` | `Vector` (3D) | The bounding-box centre in chunk-local coordinates |
| `size` | `Vector` (3D) | The bounding-box dimensions (full extent, not half-extent) |
| `rot` | `Matrix` (3×3) | The rotation that aligns the bounding-box axes with chunk-local axes |

Setting any of these takes effect immediately. To "rebuild"
the region from the current tie-point cloud's bounding box,
call `chunk.resetRegion()`.

> **Important — assignment back is required.** Modifying
> `region.center`, `region.size`, or `region.rot` in place
> does **not** persist the change. After modification, you
> must reassign the Region back to the chunk with
> `chunk.region = region`. This is the most common gotcha
> in the chunk-region API; every recipe below ends with this
> reassignment.

## Recipe — translate the region

> **Demo verified:** ✗ — pending Tier 3 reproduction on a real Metashape install.

```python
import Metashape

chunk = Metashape.app.document.chunk
region = chunk.region

# Move the region centre by an offset (chunk-local coordinates)
offset = Metashape.Vector([10.0, 0.0, 0.0])   # 10m in +X
region.center = region.center + offset
chunk.region = region   # assignment is required; modifying region in-place doesn't persist
```

**Important:** assignment to `chunk.region = region` is what
persists the change. Modifying `region.center` directly without
the assignment does not save the modification.

## Recipe — scale the region

> **Demo verified:** ✗ — pending Tier 3 reproduction on a real Metashape install.

```python
import Metashape

chunk = Metashape.app.document.chunk
region = chunk.region

# Multiply each dimension by a factor (Vector componentwise)
factor = Metashape.Vector([1.5, 1.5, 1.0])   # +50% on X and Y, unchanged on Z
region.size = Metashape.Vector([
    region.size.x * factor.x,
    region.size.y * factor.y,
    region.size.z * factor.z,
])
chunk.region = region
```

For uniform scaling: multiply by a single scalar via
`region.size * factor`.

## Recipe — rotate the region around its centre

To align the region with a feature axis (e.g., a building
façade), rotate `region.rot`:

> **Demo verified:** ✗ — pending Tier 3 reproduction on a real Metashape install.

```python
import math
import Metashape

chunk = Metashape.app.document.chunk
region = chunk.region

# Rotate 30° around the chunk-local Z axis
angle = math.radians(30)
cos_a, sin_a = math.cos(angle), math.sin(angle)
rotation_z = Metashape.Matrix([
    [cos_a, -sin_a, 0],
    [sin_a,  cos_a, 0],
    [0,         0,  1],
])

region.rot = rotation_z * region.rot
chunk.region = region
```

For an off-axis rotation around an arbitrary axis, build the
rotation matrix from the axis-angle representation:

> **Demo verified:** ✗ — pending Tier 3 reproduction on a real Metashape install.

```python
def axis_angle_to_matrix(axis, angle_rad):
    """Rodrigues formula."""
    a = axis.normalized()
    c, s = math.cos(angle_rad), math.sin(angle_rad)
    K = Metashape.Matrix([
        [0, -a.z, a.y],
        [a.z, 0, -a.x],
        [-a.y, a.x, 0],
    ])
    I = Metashape.Matrix.Diag([1, 1, 1])
    return I + K * s + K * K * (1 - c)
```

## Recipe — align region with a CRS local frame

For georeferenced chunks, align the region's axes with
geographic conventions (X = east, Y = north, Z = up) via
`crs.localframe`:

> **Demo verified:** ✗ — pending Tier 3 reproduction on a real Metashape install.

```python
import Metashape

chunk = Metashape.app.document.chunk
crs = chunk.crs
T = chunk.transform.matrix
region = chunk.region

if crs is None:
    raise RuntimeError("Chunk has no CRS; alignment is meaningless")

# Get the chunk centre in geocentric coords
centre_world = T.mulp(region.center)

# Compute the local-frame rotation at that point
local_frame = crs.localframe(centre_world)

# The local frame's rotation, expressed in chunk-local coords
# (we're rotating from chunk-local axes to ECEF, then to local NEU)
region.rot = T.rotation().inv() * local_frame.rotation().inv()
chunk.region = region
chunk.resetRegion()   # re-fit the region size to the data after rotation
```

After this, the region's red face (the one that defines the
*Height field* reconstruction plane) points up in geographic
coordinates — appropriate for terrain-style Height-field
reconstruction.

For region rotation specifically tuned to building façades,
use the marker-defined-projection pattern from
[Orthomosaic in a marker-defined planar projection](../orthomosaic/marker-defined-projection.md).

## Recipe — copy region between chunks

A common multi-chunk-workflow need: ensure two chunks have
identical region sizes and orientations, even though they're
positioned differently:

> **Demo verified:** ✗ — pending Tier 3 reproduction on a real Metashape install.

```python
import Metashape

doc = Metashape.app.document
source_chunk = doc.chunks[0]
target_chunk = doc.chunks[1]

# Copy size and rotation only (preserve target's centre)
region = target_chunk.region
region.size = source_chunk.region.size.copy() if hasattr(source_chunk.region.size, 'copy') else Metashape.Vector(source_chunk.region.size)
region.rot = source_chunk.region.rot.copy()
target_chunk.region = region
```

For the related operation "copy bounding box from one chunk to
another, including position", the script
[`copy_bounding_box_dialog.py`](https://github.com/agisoft-llc/metashape-scripts/blob/master/src/copy_bounding_box_dialog.py)
handles the cross-chunk-coordinate transformation.

## Caveats

- **Modifying `region.center`, `region.size`, or `region.rot`
  in-place does NOT persist.** You must assign the modified
  Region back to `chunk.region`. This is one of the more
  common Python-API gotchas in Metashape.
- **`chunk.resetRegion()` discards manual changes.** It
  re-fits the region to the current tie-point cloud. Don't
  call it after carefully positioning the region unless you
  want it overridden.
- **`region.size` represents the FULL extent**, not half-
  extent. A region with `size = (10, 10, 10)` extends ±5m
  from the centre on each axis, not ±10m.
- **`region.rot` is a 3×3 rotation matrix**, not a quaternion
  or Euler angles. For Euler conversion, use
  `Metashape.Utils.mat2ypr` or `mat2opk`.
- **Region changes don't trigger automatic re-build.**
  *Build Point Cloud*, *Build Mesh*, etc. respect the current
  region at run time, but existing built data (point cloud,
  mesh, DEM) was produced with the region active at THAT
  build's time. If you change the region after building, the
  built data extends to the old region; only re-running the
  build operation respects the new region.
- **The Height-field "red face" is the +Z direction in
  region-local coordinates.** To position the red face
  manually, set `region.rot` such that the local +Z axis
  points along the desired reconstruction-plane normal.

## See also

- [Setting `chunk.region` to bound the tie-point cloud](setting-the-chunk-region.md)
  — the foundational article on region setup.
- [Repositioning a chunk: moving the origin to a known
  point](repositioning-chunk-origin.md)
  — for moving the chunk frame, not just the region.
- [Mesh surface types: Arbitrary vs Height field](../mesh/mesh-surface-types.md)
  — Height-field's dependency on region orientation.
- [Orthomosaic in a marker-defined planar projection](../orthomosaic/marker-defined-projection.md)
  — for region alignment to a marker-defined plane.
- [When to use chunks: dataset partitioning strategies](../../topics/multi-chunk/when-to-use-chunks.md)
  — multi-chunk workflows where region copying is common.

## References

- [`region_control.py`](https://github.com/agisoft-llc/metashape-scripts/blob/master/src/region_control.py)
  — interactive region-control dialog.
- [`copy_bounding_box_dialog.py`](https://github.com/agisoft-llc/metashape-scripts/blob/master/src/copy_bounding_box_dialog.py)
  — for cross-chunk region copying with coordinate
  transformation.
- *Metashape Python API Reference* (2.3.1):
  `Chunk.region`, `Chunk.resetRegion`, `Region.center`,
  `Region.size`, `Region.rot`, `Matrix.Diag`,
  `Vector.normalized`, `CoordinateSystem.localframe`.

