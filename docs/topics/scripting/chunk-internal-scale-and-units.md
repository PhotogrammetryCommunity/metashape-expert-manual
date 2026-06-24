---
title: "The chunk's internal coordinate system: arbitrary scale and the `chunk.transform.scale` factor"
status: unverified
applies_to: Metashape Pro 2.x — and PhotoScan 1.x via the same `chunk.transform` API
edition: Pro
last_reviewed: 2026-06-01
diataxis: explanation
confidence: high
---

# The chunk's internal coordinate system: arbitrary scale and the `chunk.transform.scale` factor

> **Confidence:** *high.* The "chunk-internal coordinates have
> arbitrary orientation and scale" semantic is forum-attested
> with a permalink (Agisoft support, 2022). The
> `chunk.transform.matrix`, `chunk.transform.scale`, and
> `chunk.region.center` API are introspection-confirmed on
> Metashape 2.2.

## Problem

You're measuring distances in chunk-internal coordinates — for
example, computing the diagonal of `chunk.region.size`, or the
distance between two markers via `marker.position` — and the
numbers don't match real-world metres. A 50-metre baseline
between cameras measures as `9.43` units, or `265.07`, or
some other arbitrary value. Why?

The answer: **the chunk's internal coordinate system is not
metric.** It has an arbitrary scale (and arbitrary orientation)
chosen during alignment. To convert internal-coordinate
distances to real metres, you need the chunk's transform
matrix — specifically its scale component — to scale them.

This article explains what the chunk-internal frame is, how to
read its scale factor, and when you need to apply it.

## The two coordinate frames

| Frame | Origin | Scale | Orientation | Used by |
|-------|--------|-------|-------------|---------|
| **Chunk-internal** (chunk-local) | Arbitrary, near the centroid of features | Arbitrary; depends on alignment | Arbitrary; depends on alignment | `camera.transform`, `camera.center`, `marker.position`, `chunk.region.center`, `chunk.region.size`, `chunk.region.rot`, `chunk.model.vertices[N].coord`, `chunk.tie_points.points[N].coord`, `chunk.point_cloud.points[N].coord` |
| **World / ECEF** (geocentric) | Earth's centre | Metres (always) | ECEF (X-axis through equator/Greenwich, Z-axis through poles) | The output of `chunk.transform.matrix.mulp(local_point)` |

> "The internal coordinate system of the chunk (in which
> `origin_local` is defined) is not scaled to real world
> dimensions. It is `chunk.transform` that applies proper
> scale, when you are transforming to ECEF system."
> — Agisoft support, 2022-09-09, Metashape 1.8
> ([permalink](https://www.agisoft.com/forum/index.php?topic=14821.msg66108#msg66108))

The chunk-internal system serves three roles internally:

1. **Bundle adjustment**: tie-point matching and pose
   refinement happen in chunk-local coords; arbitrary scale
   is fine because the bundle solves for relative geometry.
2. **Storage**: per-camera `transform`, per-vertex `coord`,
   region geometry — all in chunk-local for compact storage.
3. **Real-world translation**: at export / measurement time,
   `chunk.transform.matrix` maps chunk-local into world
   metres.

## Reading the scale factor

`chunk.transform.scale` returns the scalar factor that the
matrix applies. For a chunk that has been aligned and scaled
to a CRS:

> **Demo verified:** ✗ — pending Tier 3 reproduction on a real Metashape install.

```python
import Metashape

chunk = Metashape.app.document.chunk

scale = chunk.transform.scale
if scale == 1.0 and chunk.transform.translation.norm() == 0.0:
    print("Identity-like transform — chunk likely has no real-world reference")
else:
    print(f"chunk.transform.scale = {scale}")
    print(f"  (1 unit in chunk-internal ≈ {scale} metres in world)")
```

For an un-georeferenced chunk (no `chunk.crs` set, no
reference data loaded), `chunk.transform.matrix` is an
identity-like transform and `chunk.transform.scale` is 1.0 —
internal distances are arbitrary in those fictional metres.

Note: there's no `Matrix.isidentity()` method in the 2.x API.
The closest reliable identity check is comparing
`chunk.transform.matrix` to `Metashape.Matrix.Diag([1, 1, 1, 1])`
or testing scale + translation directly as above.

## When you need to apply the scale

Three operational cases:

### Case 1 — Distance between two markers

```python
m_a = chunk.markers[0]
m_b = chunk.markers[1]

# Chunk-internal distance (NOT real metres)
distance_local = (m_b.position - m_a.position).norm()

# Real-world distance
T = chunk.transform.matrix
distance_metres = (T.mulp(m_b.position) - T.mulp(m_a.position)).norm()

# Equivalent: scale the local distance directly
distance_metres_v2 = distance_local * chunk.transform.scale

print(f"Local: {distance_local:.3f}, Real: {distance_metres:.3f} m")
```

The two methods agree because translation cancels in the
subtraction, leaving only the rotation-and-scale portion of
`T` to act on the difference vector. For Metashape's
uniform-scale chunk transform, that rotation-and-scale reduces
to a uniform multiplication by `chunk.transform.scale`. The
second method is faster when computing many distances against
the same chunk transform.

### Case 2 — `chunk.region.size` for memory estimates

```python
# Region's diagonal in real metres
size_local = chunk.region.size.norm()
size_metres = size_local * chunk.transform.scale
print(f"Region diagonal: {size_metres:.1f} metres")
```

This matters when sizing memory estimates: the raw
`chunk.region.size` value is meaningless without multiplying
by `chunk.transform.scale`. Forum thread t=14821 reports a
real measured `chunk.transform.scale` of `5.30154` for an
aerial project — meaning a `chunk.region.size` of (10, 8, 2)
in chunk-internal units corresponds to (53, 42, 11) real
metres after scaling.

### Case 3 — Tie-point cloud bounding-box volume

```python
# Bounding-box volume in real cubic metres
volume_local = chunk.region.size.x * chunk.region.size.y * chunk.region.size.z
scale_cubed = chunk.transform.scale ** 3   # volume scales as scale^3
volume_m3 = volume_local * scale_cubed
print(f"Bounding-box volume: {volume_m3:.1f} m³")
```

Volume scales as the cube of the linear scale factor; area
scales as the square.

## Why the internal scale is arbitrary

> "The internal system of the chunk has arbitrary orientation
> and scale, you cannot predict, how it will be related to the
> ECEF or geographic/projected coordinate system before the
> alignment is completed."
> — Agisoft support, 2022-09-12, Metashape 1.8
> ([permalink](https://www.agisoft.com/forum/index.php?topic=14821.msg64950#msg64950))

The bundle-adjustment optimisation has only image observations
to work with, plus user-supplied reference data (camera GPS,
GCP coordinates). It picks a chunk-local frame that:

- Centres the tie-point cloud near the origin.
- Orients the axes to match the data's principal extents.
- Sets the scale so that tie-point coordinates have reasonable
  magnitudes.

The result is well-conditioned for the bundle but has no
particular relationship to real metres or to a specific
geographic axis until the user supplies reference data and
runs `chunk.updateTransform()` (or *Reference → Update
Transform* in the GUI).

After `updateTransform`, the chunk has:

- `chunk.crs` set to the user's chosen CRS.
- `chunk.transform.matrix` containing the (rotation × scale ×
  translation) that maps chunk-local → world geocentric.
- `chunk.transform.scale` revealing the scale factor.

Before `updateTransform`, all distances are in arbitrary
chunk-units.

## Region rotation and the `region.rot` matrix

A related but separate concept: `chunk.region.rot` is the
rotation that aligns the bounding-box's local axes with
chunk-local axes. This rotation does NOT include scale;
multiplying through `region.rot` preserves chunk-internal
distances.

For full coordinate-frame manipulation (translating / scaling /
rotating the region itself), see [Programmatic chunk.region
control: move, scale, rotate the bounding box](../../workflow/project-setup/region-control-python.md).

## Caveats

- **Pre-alignment, `chunk.transform.matrix` is the identity.**
  Distances measured in chunk-local are arbitrary and
  meaningless. The scale factor is 1.0 but the "metres" are
  fictional.
- **`chunk.transform.scale` is a scalar, not a 3-vector.**
  The chunk's transform applies a uniform scale to all axes.
  This means there's no way to encode "X is in metres but Y
  is in feet" within a single chunk transform — those
  workflows need per-axis CRS handling.
- **For comparison across chunks**, the per-chunk scale
  factors will generally differ. Two chunks of the same
  dataset, aligned independently, will have different
  `chunk.transform.scale` values until both are referenced
  to the same CRS via reference data.
- **The scale factor changes when reference data is updated.**
  If you load camera GPS positions and re-run *Update
  Transform*, the scale shifts to fit the new reference. Save
  the value before re-running if you need to compare scaled
  distances across the operation.
- **Bundle adjustment in Metashape uses chunk-internal coords.**
  Reprojection-error metrics (in pixels) are not affected by
  the scale factor; metric error metrics (in metres for
  reference points) are computed via the full transform.
  See [Reprojection error analysis](../repeatability-qa/reprojection-error-analysis.md)
  vs [Camera reference error: per-camera location and
  orientation in Python](../repeatability-qa/camera-reference-error-python.md).

## See also

- [`chunk.transform.matrix` is local→world; `camera.transform` is local](../crs/chunk-frame-vs-camera-frame.md)
  — the broader chunk-local vs world frame article (this
  article's scale-factor focus complements it).
- [Programmatic chunk.region control: move, scale, rotate the bounding box](../../workflow/project-setup/region-control-python.md)
  — region API including `region.rot` (orientation, no scale).
- [Repositioning a chunk: moving the origin to a known point](../../workflow/project-setup/repositioning-chunk-origin.md)
  — for changing what `chunk.transform.matrix` does.
- [Converting `camera.transform` to ENU (or any local Cartesian)](camera-poses-to-enu.md)
  — for camera poses; uses the same chunk-local → world →
  CRS chain.

## References

- *Metashape Python API Reference* (2.3.1):
  `Chunk.transform`, `ChunkTransform.matrix`,
  `ChunkTransform.scale`, `ChunkTransform.translation`,
  `ChunkTransform.rotation`, `Chunk.region`, `Region.center`,
  `Region.size`, `Region.rot`, `Chunk.updateTransform`.
- Forum thread, [*Confused about local to geographic
  conversion*, 2022](https://www.agisoft.com/forum/index.php?topic=14821.msg66108#msg66108)
  — the canonical Q&A on the chunk-internal arbitrary-scale
  semantic.

