---
title: Working with shape geometries (1.7+ API)
status: unverified
applies_to: Metashape Pro 2.x and Metashape Standard 2.x. The shape geometry API was introduced in Metashape 1.7 (2021); pre-1.7 scripts using `shape.vertices` need rewriting. Tier 1 introspection on Metashape 2.2.3 confirms the full API surface.
edition: "Pro / Standard"
last_reviewed: 2026-05-26
diataxis: how-to
confidence: medium
---

# Working with shape geometries (1.7+ API)
> **Confidence:** *medium.* The 1.7+ shape geometry API (`Geometry.Polygon`, `Shape.geometry`) is introspection-confirmed; the migration from 1.x `shape.vertices` is forum-attested with permalinks.
## Problem

You have a script that does any of:

- Reads vertex coordinates from a shape (`shape.vertices[0]`)
- Creates a new shape programmatically
- Iterates over a polygon's edges
- Checks whether a shape's vertices are attached to markers

…and the script either errors with `AttributeError: 'Shape'
object has no attribute 'vertices'` or silently produces
garbage on Metashape 1.7 or later. The `Shape` API changed
fundamentally between 1.6 and 1.7, and the new structure is
not obviously discoverable from forum-era code samples.

## Context

In Metashape 1.7, `Shape` gained a GeoJSON-aligned **geometry**
model. Vertex coordinates are no longer at `shape.vertices`;
they are at `shape.geometry.coordinates` — a **nested list
structure**. The pivot is canonical, attested verbatim:

> "For shape properties you should now access shape.geometry
> (actually, should be available in 1.7 API as well)."
> — Alexey Pasumansky, 2021-11-30, Metashape 1.8.0 pre-release
> ([permalink](https://www.agisoft.com/forum/index.php?topic=13736.msg61603#msg61603))

The API mirrors the [GeoJSON
specification](https://datatracker.ietf.org/doc/html/rfc7946):
each `Geometry` has a `type` (one of 7 values: `Point`,
`LineString`, `Polygon`, `MultiPoint`, `MultiLineString`,
`MultiPolygon`, `GeometryCollection`) and a corresponding
`coordinates` shape. For single-part shapes, the outermost
index is always `[0]`; the actual vertex array sits inside it.

## Solution

### The 7 geometry types and their `coordinates` shape

Tier 1 introspection on Metashape 2.2.3 confirms `Geometry.Type`
has 7 values. Each has a different `coordinates` structure
(GeoJSON-aligned):

| `geometry.type` | Visual | `coordinates` structure | Example access |
|-----------------|--------|------------------------|-----------------|
| `Point` | one vertex | `list[Vector]` of length 1 | `coords[0]` |
| `LineString` | a polyline | `list[Vector]` | `coords[N]` for vertex *N* |
| `Polygon` | one polygon (with optional inner holes) | `list[list[Vector]]` (outer ring first; inner rings after) | `coords[0][N]` for outer vertex *N* |
| `MultiPoint` | scattered vertices | `list[Vector]` | `coords[N]` |
| `MultiLineString` | several polylines | `list[list[Vector]]` | `coords[L][N]` for line *L* vertex *N* |
| `MultiPolygon` | several polygons | `list[list[list[Vector]]]` | `coords[P][0][N]` for polygon *P* outer vertex *N* |
| `GeometryCollection` | mixed types | `geometries` attribute (list of `Geometry`) | iterate `geom.geometries` |

**The constructor argument shape differs from the
`coordinates` shape** — see the next section. Polygon's
*constructor* takes a flat `list[Vector]` (the exterior ring),
but its `coordinates` attribute returns nested `[[Vector,
Vector, ...]]` (the wrapped exterior ring, plus optional inner
rings). This is the convenience overload: the constructor
accepts the simpler form, the data structure preserves the
GeoJSON nesting.

### Reading vertex coordinates

For a single-polygon shape (the common case for orthomosaic
patch boundaries):

```python
import Metashape

chunk = Metashape.app.document.chunk
shape = chunk.shapes[0]                 # first shape

# For a Polygon, coordinates[0] is the outer ring.
outer_ring = shape.geometry.coordinates[0]
for vertex in outer_ring:
    print(f"  vertex: {vertex.x}, {vertex.y}, {vertex.z}")
```

For a single-point shape:

```python
# Point.coordinates is a list of length 1 wrapping the vertex.
vertex = shape.geometry.coordinates[0]   # a Vector
```

The `coordinates` shape differs by geometry type — `Point`
gets `list[Vector]` of length 1; `Polygon` gets nested rings;
see the table above for the per-type access pattern.

The list-of-lists addressing convention, attested verbatim:

> "shapes in 1.8 version may be represented by the collection
> of multiple elements and will appear as list of lists via
> API. So if there's only single shape, then to access the
> coordinates of the Nth vertex you should use:
> `shape.geometry.coordinates[0][N]`"
> — Alexey Pasumansky, 2021-11-30, Metashape 1.8.0 pre-release
> ([permalink](https://www.agisoft.com/forum/index.php?topic=13736.msg61615#msg61615))

### Adding a shape programmatically

> **Demo verified:** ✓ partial — Tier 1 introspection on
> Metashape 2.2.3 confirmed the constructor signatures via
> live invocation: `Polygon(exterior_ring)` with a flat
> `list[Vector]` works and produces `coordinates =
> [[V1, V2, V3, V1]]`; the nested-list form raises
> `ValueError`. Point and LineString constructors confirmed
> by introspection. Tier 3 reproduction with end-to-end
> shape creation in a real chunk is still pending.

The 1.7+ pattern: create the `Shape` via `chunk.shapes.addShape()`,
then assign a `Geometry` object to its `geometry` attribute:

```python
import Metashape

chunk = Metashape.app.document.chunk

# Add a single-point shape.
point = chunk.shapes.addShape()
point.geometry = Metashape.Geometry.Point(Metashape.Vector([x, y, z]))

# Add a polygon shape (single outer ring; no inner holes).
# Constructor signature: Polygon(exterior_ring, [interior_rings])
# where exterior_ring is a flat list[Vector]. The constructor
# auto-wraps into the nested coordinates structure.
poly = chunk.shapes.addShape()
poly.geometry = Metashape.Geometry.Polygon([
    Metashape.Vector([x1, y1, z1]),
    Metashape.Vector([x2, y2, z2]),
    Metashape.Vector([x3, y3, z3]),
    Metashape.Vector([x1, y1, z1]),     # close the ring (first==last)
])
# After construction: poly.geometry.coordinates == [[V1, V2, V3, V1]]
# — note the outer wrap, even though the constructor took a flat list.

# Add a polyline (line string).
line = chunk.shapes.addShape()
line.geometry = Metashape.Geometry.LineString([
    Metashape.Vector([x1, y1, z1]),
    Metashape.Vector([x2, y2, z2]),
])
```

Note the closing-ring convention for polygons: the first and
last vertex must be the same `Vector` value. Metashape does not
auto-close the ring; an open polygon will error or produce a
degenerate shape.

### Coordinate system caveat

Shape coordinates are in the **chunk's CRS** (or in chunk
local frame if the chunk is ungeoreferenced) — *not* in
chunk-internal coordinates. This is opposite to
`chunk.region` (internal coords) and `chunk.tie_points`
(internal coords). When mixing shapes with tie-points or
regions, transform via `chunk.crs` and
`chunk.transform.matrix` as needed. See [Setting
`chunk.region`](../../workflow/project-setup/setting-the-chunk-region.md)
for the analogous transform pattern.

## Caveats and gotchas

- **`is_attached` shapes return marker keys, not coordinates.**
  When a shape's vertices are pinned to markers
  (`shape.is_attached == True`), `shape.geometry.coordinates`
  contains **integer marker keys** (`marker.key`), not
  `Vector` objects. Code that calls `vector.x` on the
  iterated values will raise `AttributeError`. Attested
  verbatim:

  > "If the shape has attached markers to its vertices
  > (`shape.is_attached == True`), then the list of
  > `shape.geometry.coordinates` will contain the keys of the
  > related markers (`marker.key`)."
  > — Alexey Pasumansky, 2021-11-30, Metashape 1.8.0 pre-release
  > ([permalink](https://www.agisoft.com/forum/index.php?topic=13736.msg61623#msg61623))

  The pattern for handling attached shapes:

  ```python
  if shape.is_attached:
      for marker_key in shape.geometry.coordinates[0]:
          marker = next(m for m in chunk.markers if m.key == marker_key)
          vertex = marker.position
          # use vertex
  else:
      for vertex in shape.geometry.coordinates[0]:
          # vertex is already a Vector
          pass
  ```

- **Pre-1.7 scripts using `shape.vertices` will not run on
  2.x.** The attribute does not exist; introspection raises
  `AttributeError`. Migrate to
  `shape.geometry.coordinates[0]` for the simple polygon case.

- **GUI-drawn shapes vs script-drawn shapes** — both produce
  the same `Geometry` structure. The GUI's *Shape* tools
  produce `Polygon` or `LineString` types; the *Marker*
  attached-shape tool produces `is_attached==True` shapes.

- **The closing-ring convention is unforgiving.** A polygon
  must have its first and last vertex as the same `Vector`.
  An open polygon will silently produce a degenerate result
  or error in `buildOrthomosaic` later.

- **`shape.geometry.is_3d` matters for some operations.**
  `is_3d=True` shapes have meaningful Z values; `is_3d=False`
  ones have Z=0 (or undefined). Operations like
  `shape.geometry.area` may behave differently depending on
  this flag.

## See also

- [Applying *Patch* on multiple shapes](../../workflow/orthomosaic/applying-patch-multiple-shapes.md)
  — uses `shape.geometry.coordinates` for the orthomosaic
  patching workflow.
- [Mapping orthomosaic pixels back to source images](orthomosaic-pixel-to-source-image.md)
  — uses `shape.geometry.coordinates[0][0]` for the
  point-shape lookup.
- *Metashape Python API Reference* (2.3.1), Change Log:
  - §3.29 "Metashape version 1.7.0" — addition: "Added
    `Geometry` and `AttachedGeometry` classes" + "Added
    `Shape.geometry` and `Shape.is_attached` attributes."
  - §3.22 "Metashape version 1.8.0" — removal: "Removed
    `has_z`, `type`, `vertex_ids` and `vertices` attributes
    from `Shape` class."
- *Metashape Python Reference* (2.3.1):
  `Shape`, `Geometry`, `AttachedGeometry`.
- [Forum topic 13736](https://www.agisoft.com/forum/index.php?topic=13736.0)
  — the 1.8.0 pre-release thread (4 substantive Agisoft-staff
  posts on the shape geometry API).
- [GeoJSON specification (RFC 7946)](https://datatracker.ietf.org/doc/html/rfc7946)
  — the structural standard the `Geometry` API mirrors.

