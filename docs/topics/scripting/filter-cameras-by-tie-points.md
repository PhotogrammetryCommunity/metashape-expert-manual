---
title: "Filtering cameras by tie-point selection: which photos see this 3D point?"
status: unverified
applies_to: Metashape Pro 2.x — and PhotoScan 1.x via the same `chunk.tie_points.projections` API (was `chunk.point_cloud` in 1.x)
edition: Pro
last_reviewed: 2026-05-29
diataxis: how-to
confidence: high
---

# Filtering cameras by tie-point selection: which photos see this 3D point?

> **Confidence:** *high.* The pattern is forum-attested with
> permalinks (Agisoft support, 2022). The
> `chunk.tie_points.points`, `chunk.tie_points.projections[camera]`,
> and `Projection.track_id` API are introspection-confirmed on
> Metashape 2.2.

## Problem

You need to find **which cameras observe a specific subset of
the tie-point cloud** — for any of these use cases:

- "Identify all photos that see the selected (via *Clean Tie
  Points*, historically *Gradual Selection*)
  tie points so I can mask them, retake them, or analyze them."
- "Which photos cover the area I just clicked on the dense
  cloud / mesh?"
- "For each suspicious tie point, list the cameras and per-camera
  pixel coordinates."

Metashape's GUI has *Reset Filter / Filter Photos by Cameras*
for the selection-driven case, but the tie-point-to-camera
mapping is what you need for programmatic filtering, custom
diagnostic visualisations, or non-GUI workflows.

## Context

The relevant data structures in Metashape 2.x:

| Object | What it is |
|--------|-----------|
| `chunk.tie_points` | The chunk's tie-point cloud (was `chunk.point_cloud` in 1.x) |
| `chunk.tie_points.points` | List of `Point` objects — each is a 3D tie point |
| `chunk.tie_points.tracks` | List of `Track` objects — each represents one tie point's identity across cameras |
| `chunk.tie_points.projections[camera]` | List of `Projection` objects — each is a 2D pixel where this camera observes some track |
| `Projection.track_id` | Index into the `tracks` list — links the 2D projection to its 3D track |
| `Point.track_id` | Same — links a 3D point to its track identity |
| `Point.selected` | True if the point is currently selected (e.g., from Gradual Selection) |
| `Point.valid` | True if the point passes the bundle's validity criteria |

The "which photos see this point?" question becomes:
*"Which projections have a track_id matching this point's
track_id?"*

## Recipe — cameras observing the selected tie points

> "If you would like to iterate through all the tie points, you
> need to replace the line `if points[point_id].selected:` with
> `if points[point_id].valid:`"
> — Agisoft support, 2022-11-30, Metashape 2.0
> ([permalink](https://www.agisoft.com/forum/index.php?topic=15017.msg66716#msg66716))

> **Demo verified:** ✗ — pending Tier 3 reproduction on a real Metashape install.

```python
import Metashape

chunk = Metashape.app.document.chunk
tie_points = chunk.tie_points
points = tie_points.points

# Build the set of track_ids belonging to currently-selected points
selected_track_ids = {
    points[i].track_id
    for i in range(len(points))
    if points[i].selected
}
print(f"Selected points: {len(selected_track_ids)} unique tracks")

# For each camera, find which projections match
cameras_observing_selected = {}   # camera -> list of (proj.x, proj.y) pixel coords
for camera in chunk.cameras:
    if not camera.transform:
        continue
    projections = tie_points.projections[camera]
    if projections is None:
        continue
    for proj in projections:
        if proj.track_id in selected_track_ids:
            cameras_observing_selected.setdefault(camera, []).append(
                (proj.coord.x, proj.coord.y)
            )

# Print summary
print(f"\n{'Camera':<25} {'Selected pts':>12}")
print("-" * 40)
for camera, coords in cameras_observing_selected.items():
    print(f"{camera.label:<25} {len(coords):>12}")
```

After this, `cameras_observing_selected` maps each affected
camera to the list of pixel coordinates where the selected
tie points project. Use this for:

- **Masking**: paint over those pixels in a mask image to
  prevent re-detection.
- **Filtering by Cameras**: select these cameras in
  `chunk.cameras` for retake / re-import.
- **Diagnostic visualisation**: overlay the pixel coordinates
  on each camera's preview.

## Recipe — iterate ALL tie points (not just selected)

Replace the `selected` filter with `valid` to iterate every
valid tie point. Useful for full-coverage analyses:

> **Demo verified:** ✗ — pending Tier 3 reproduction on a real Metashape install.

```python
import Metashape

chunk = Metashape.app.document.chunk
tie_points = chunk.tie_points
points = tie_points.points

# Track-id -> list of (camera, x, y)
observers = {}
for camera in chunk.cameras:
    if not camera.transform:
        continue
    projections = tie_points.projections[camera]
    if projections is None:
        continue
    for proj in projections:
        observers.setdefault(proj.track_id, []).append(
            (camera, proj.coord.x, proj.coord.y)
        )

# Iterate all valid 3D points; report observer count
under_observed = []
for i in range(len(points)):
    p = points[i]
    if not p.valid:
        continue
    observer_list = observers.get(p.track_id, [])
    if len(observer_list) < 3:
        under_observed.append((p.track_id, p.coord, observer_list))

print(f"Tie points with < 3 observers: {len(under_observed)}")
```

`< 3` observers is a common quality threshold — points seen on
fewer than 3 cameras have no triangulation redundancy and are
more vulnerable to noise.

## Recipe — find cameras around a 3D point of interest

Inverse use case: you have a specific 3D position (e.g., a
suspicious mesh region, a clicked dense-cloud point) and want
to find which cameras observe nearby tie points.

> **Demo verified:** ✗ — pending Tier 3 reproduction on a real Metashape install.

```python
import Metashape

chunk = Metashape.app.document.chunk
tie_points = chunk.tie_points
points = tie_points.points

# 3D query point in chunk-local coords
query = Metashape.Vector([10.0, 5.0, 2.0])
radius_sq = 0.5 ** 2   # 0.5m radius

# Find tracks whose 3D points are within radius
nearby_tracks = set()
for i in range(len(points)):
    p = points[i]
    if not p.valid:
        continue
    if (p.coord - query).norm2() < radius_sq:
        nearby_tracks.add(p.track_id)

print(f"Nearby tracks: {len(nearby_tracks)}")

# Cameras observing those tracks
cameras_seen = set()
for camera in chunk.cameras:
    if not camera.transform:
        continue
    projections = tie_points.projections[camera]
    if projections is None:
        continue
    for proj in projections:
        if proj.track_id in nearby_tracks:
            cameras_seen.add(camera)
            break   # one match per camera is enough

print(f"Cameras with view of region: {len(cameras_seen)}")
for cam in cameras_seen:
    print(f"  - {cam.label}")
```

`norm2()` (squared norm) avoids a per-point square root and is
~2× faster than `norm()` for proximity tests.

## 1.x → 2.x naming change

The tie-point cloud's API was renamed at the 2.0 transition:

| 1.x | 2.x |
|-----|-----|
| `chunk.point_cloud.points` | `chunk.tie_points.points` |
| `chunk.point_cloud.tracks` | `chunk.tie_points.tracks` |
| `chunk.point_cloud.projections[camera]` | `chunk.tie_points.projections[camera]` |

If you're maintaining 1.x scripts:

```python
# Cross-version compatible:
tie_points = getattr(chunk, "tie_points", None) or getattr(chunk, "point_cloud")
```

## Caveats

- **`chunk.tie_points.projections[camera]` may be None** for
  cameras that never ran through *Match Photos* (e.g., manually
  added cameras with no matching pass). Always check before
  iterating.
- **`Projection.track_id`** is an integer index; the
  corresponding `Track` object is `chunk.tie_points.tracks[track_id]`
  if you need it. For the inverse mapping (Track → Point), iterate
  `chunk.tie_points.points` and check `point.track_id`.
- **Selected vs. valid vs. enabled.**
  - `point.selected` — currently selected in the GUI / Gradual
    Selection.
  - `point.valid` — passed the bundle's validity criteria; safe
    for ordinary use.
  - `point.enabled` doesn't exist on points (it does on Markers).
- **Iteration cost.** On a 5M-point chunk with 5000 cameras,
  the recipes above are O(P + C × P̂) where P is total points
  and P̂ is per-camera projections (typically 50-500). For
  multi-million-point chunks, batch the work in chunks of
  10000 tracks at a time and consider numpy-based filtering.

## See also

- [Mesh and point-cloud editing recipes](mesh-pointcloud-editing-recipes.md)
  — companion patterns for mesh-side data manipulation.
- [Cleaning tie points + Optimize Cameras: the loop](../../workflow/optimization/clean-tie-points-optimize-cameras-loop.md)
  — the iterative procedure that uses Gradual Selection (the
  source of the `point.selected` flag).
- [Marker projection statistics](../repeatability-qa/marker-projection-statistics.md)
  — the same `projections` API surface for markers.

## References

- *Metashape Python API Reference* (2.3.1):
  `Chunk.tie_points`, `TiePoints.points`, `TiePoints.tracks`,
  `TiePoints.projections`, `Track`, `Point.coord`,
  `Point.track_id`, `Point.selected`, `Point.valid`,
  `Projection.coord`, `Projection.track_id`, `Vector.norm2`.
- Forum thread, [*Filter photos by point using Python API*, 2022](https://www.agisoft.com/forum/index.php?topic=15017.msg66716#msg66716)
  — `selected` vs `valid` filter; the (camera, x, y) tuple
  collection pattern.

