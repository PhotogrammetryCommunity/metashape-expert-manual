---
title: "Sensor and camera shared-tie-point graphs: detecting isolated groups"
status: unverified
applies_to: Metashape Pro 2.x — and PhotoScan 1.x via the same projection iteration over `chunk.point_cloud.projections` (1.x) / `chunk.tie_points.projections` (2.x)
edition: "Pro / Standard"
last_reviewed: 2026-06-01
diataxis: how-to
confidence: high
---

# Sensor and camera shared-tie-point graphs: detecting isolated groups

> **Confidence:** *high.* The core API surface
> (`chunk.tie_points.projections`,
> `chunk.tie_points.points[i].valid`, `Camera.transform`) is
> introspection-confirmed on Metashape 2.2. The graph-building
> pattern is a direct application of the
> tracks-as-multi-camera-observations data model documented in
> the Python API Reference; the *under-connected isolated
> group* detection heuristic is a derived QA pattern, presented
> here with a worked example.

## Problem

After running *Align Photos*, you've got an aligned chunk with
multiple sensors (a multi-spectral rig, a top-down + 45° aerial
combo, RGB + thermal pairing) or a large camera count. The
chunk-info dialog reports:

- All cameras aligned ✓
- Reprojection error ≤ 1 px ✓
- One bundle component ✓

But a downstream product (an orthomosaic, a model, a tiled
output) shows a seam, a misalignment, or a quality
discontinuity that *looks* like the bundle is fine but the
chunks aren't actually well-stitched.

The likely cause: a **weakly-connected group** — a sensor or
a cluster of cameras that's nominally aligned (every camera
has a `transform`) but only via a thin bridge of shared tie
points with the rest of the project. The bundle finds a
mathematical solution but the geometry is under-constrained
in the bridge area, leading to subtle misalignments that
manifest only in dense products.

This article shows how to build the **shared-tie-point graph**
from the bundle's projections and use it to detect:

- Sensors that share too few tie points with other sensors.
- Cameras that share too few tie points with the rest of the
  chunk.
- Effective bundle "components" beneath the
  `chunk.components` view.

## The construction in one paragraph

Every track has projections in some subset of cameras. Two
sensors (or two cameras) "share" a track when both have a
projection of the same `track_id` AND the track triangulated
to a valid 3D point. Counting these shared tracks across all
sensor pairs (or camera pairs) yields a **co-observation
matrix**: a symmetric integer matrix where entry (i, j) is the
number of valid tracks observed by both sensor i and sensor j.

The recipes below build this matrix from
`chunk.tie_points.projections` and use it to detect under-
connected groups. The interpretation of diagonals (per-sensor
track count) and off-diagonals (cross-sensor shared tracks)
is covered alongside each recipe.

## Recipe — sensor↔sensor shared-tie-point counts

> **Demo verified:** ✗ — pending Tier 3 reproduction on a real Metashape install.

```python
from collections import defaultdict
from itertools import combinations
import Metashape

chunk = Metashape.app.document.chunk
tps = chunk.tie_points

# Build the set of validated track IDs (only valid 3D points count)
valid_track_ids = {p.track_id for p in tps.points if p.valid}

# For each track, collect the set of sensors that observed it on an aligned camera
track_to_sensors: dict[int, set[Metashape.Sensor]] = defaultdict(set)
for camera in chunk.cameras:
    if not camera.transform or camera.sensor is None:
        continue
    for proj in tps.projections[camera]:
        if proj.track_id in valid_track_ids:
            track_to_sensors[proj.track_id].add(camera.sensor)

# Pair-up sensors and tally shared tracks
shared = defaultdict(int)
for sensors in track_to_sensors.values():
    for s_a, s_b in combinations(sorted(sensors, key=lambda s: s.key), 2):
        shared[(s_a, s_b)] += 1

# Print as a matrix, plus the diagonals (per-sensor track count)
sensors = sorted(set(chunk.sensors), key=lambda s: s.key)
diag = {s: 0 for s in sensors}
for sensor_set in track_to_sensors.values():
    for s in sensor_set:
        diag[s] += 1

# Header
print(f"{'sensor':<25}", *[f"{s.label[:8]:>10}" for s in sensors])
for s_row in sensors:
    print(f"{s_row.label[:24]:<25}", end="")
    for s_col in sensors:
        if s_row is s_col:
            print(f"{diag[s_row]:>10}", end="")
        else:
            pair = (s_row, s_col) if s_row.key < s_col.key else (s_col, s_row)
            print(f"{shared.get(pair, 0):>10}", end="")
    print()
```

Output (for a hypothetical 3-sensor rig with 60 cameras each):

```
sensor                      RGB-front  RGB-back  Thermal
RGB-front                   28,431       12,440    1,847
RGB-back                    12,440       27,116      980
Thermal                      1,847          980    8,612
```

Reading: each diagonal entry is the **per-sensor track
count** — validated tracks with at least one projection on
that sensor's cameras. Each off-diagonal is the
**cross-sensor shared count** — validated tracks observed by
at least one camera of each sensor; the bundle uses these
as the geometric bridge between sensor solutions.

In the example above, thermal is weakly connected to both RGB
sensors — 1,847 and 980 shared tracks respectively, vs the
RGB-front × RGB-back's 12,440. Thermal's diagonal (8,612) is
also smaller, reflecting fewer features detected on the
thermal modality.

A reasonable QA threshold: the smallest off-diagonal divided
by the smaller of the two diagonals (the "bridge ratio")
should be ≥ ~5-10%. Below that, the inter-sensor connection
is fragile. A multi-sensor project where every off-diagonal is
≥ ~50% of the smaller sensor's diagonal is well-connected; a
project where any off-diagonal approaches zero has a sensor
that's effectively floating — only the global-camera-residual
constraint and its own per-sensor tie points keep its position
pinned.

## Recipe — sensor connectivity threshold per camera count

A more operationally useful metric than the absolute share
count is **shared tie points per camera**, normalising for
sensor size:

> **Demo verified:** ✗ — pending Tier 3 reproduction on a real Metashape install.

```python
# Number of cameras per sensor
cameras_per_sensor = defaultdict(int)
for camera in chunk.cameras:
    if camera.transform and camera.sensor:
        cameras_per_sensor[camera.sensor] += 1

# Threshold: each sensor should have at least one peer with this many shared tracks per camera
THRESHOLD_PER_CAM = 0.5

print(f"\n{'sensor':<25} {'cameras':>8} {'best_peer_shared':>18} {'per_cam':>10} {'verdict':<10}")
for s in sensors:
    n_cams = cameras_per_sensor[s]
    if n_cams == 0:
        continue
    # Find the highest off-diagonal involving this sensor
    best = 0
    best_peer = None
    for other in sensors:
        if other is s:
            continue
        pair = (s, other) if s.key < other.key else (other, s)
        if shared.get(pair, 0) > best:
            best = shared[pair]
            best_peer = other
    per_cam = best / n_cams if n_cams else 0
    verdict = "OK" if per_cam >= THRESHOLD_PER_CAM else "ISOLATED"
    peer_label = best_peer.label[:15] if best_peer else "(none)"
    print(f"{s.label[:24]:<25} {n_cams:>8} {best:>18} {per_cam:>10.2f} {verdict:<10}  (best peer: {peer_label})")
```

A sensor with 60 cameras and a best-peer of 8 shared tracks
per camera scores 8.0 — well-connected. A 60-camera sensor
with only 0.3 shared tracks per camera (so 18 total shared)
is at risk and warrants investigation.

The `THRESHOLD_PER_CAM` is operational, not absolute. Start at
0.5 and tune based on the tightness of your QA bar.

## Recipe — camera↔camera shared tracks (isolated-camera detection)

The same construction at the camera level identifies cameras
that are weakly tied to the rest of the chunk:

> **Demo verified:** ✗ — pending Tier 3 reproduction on a real Metashape install.

```python
from collections import defaultdict
import Metashape

chunk = Metashape.app.document.chunk
tps = chunk.tie_points
valid_track_ids = {p.track_id for p in tps.points if p.valid}

# Build per-camera set of valid tracks
cam_tracks = defaultdict(set)
for camera in chunk.cameras:
    if not camera.transform:
        continue
    for proj in tps.projections[camera]:
        if proj.track_id in valid_track_ids:
            cam_tracks[camera].add(proj.track_id)

# For each camera, count shared tracks with each other camera
def shared_count(c_a, c_b):
    return len(cam_tracks[c_a] & cam_tracks[c_b])

# For each camera, compute its peer-rank: the count of shared tracks
# with the K-th best peer (K = 3 by default — looking past the camera's
# closest two neighbours, which may be near-duplicates in a video sequence).
K = 3
peer_kth_counts = {}
for camera in chunk.cameras:
    if not camera.transform:
        continue
    peers = sorted(
        (shared_count(camera, other) for other in chunk.cameras if other is not camera),
        reverse=True,
    )
    peer_kth_counts[camera] = peers[K] if len(peers) > K else 0

# Average across all cameras' kth-peer counts
avg_kth = sum(peer_kth_counts.values()) / len(peer_kth_counts) if peer_kth_counts else 0
threshold = max(1, int(0.01 * avg_kth))   # 1% of average = isolation cutoff

print(f"\nAverage K-th-best-peer ({K=}) shared count: {avg_kth:.1f}")
print(f"Isolation threshold (1% of avg): {threshold}\n")

isolated = sorted(
    [(c, k) for c, k in peer_kth_counts.items() if k < threshold],
    key=lambda x: x[1],
)
if isolated:
    print(f"{'Camera':<25} {'Kth peer count':>15}")
    for camera, k in isolated:
        print(f"{camera.label[:24]:<25} {k:>15}")
else:
    print("No isolated cameras detected.")
```

The K-th-peer trick is the practical heart of the recipe:
looking only at the *best* peer can be misleading because a
single near-duplicate frame (consecutive video frame, or a
deliberately overlapping pair) drives the count up. Looking at
the K-th best (typically 2-3) gives a more robust signal —
isolated cameras have low K-th peer counts even if they share
features with one or two near-duplicates.

The 1%-of-average threshold reflects the empirical
observation that a healthy camera shares many features with
its 2-3 nearest neighbours. A camera at < 1% of the global
average has lost the matching graph entirely.

## What to do with isolated cameras / sensors

Three options when an isolated group is identified:

### Option 1 — Add masks and re-run

If the isolated group has consistent visual features that
prevent matching (motion blur, overexposure, fog, glass), add
masks and re-run *Align Photos* and *Match Photos*.

### Option 2 — Force the isolated cameras un-aligned and refit

If the cameras are aligned but unreliable, set their
`transform = None` and re-run *Optimize Cameras*. The bundle
will reproject them based on a residuals-only fit:

```python
isolated_set = set(c for c, _ in isolated)
for camera in isolated_set:
    camera.transform = None
chunk.optimizeCameras(adaptive_fitting=True)
chunk.alignCameras(cameras=list(isolated_set))
```

If the isolated cameras fail to re-align, that's diagnostic —
they truly have no overlap with the rest.

### Option 3 — Split into separate chunks

For systematically unrelated camera groups (different missions,
different sensors that should never share features), accept
the result and process each as a separate chunk. The
[multi-chunk workflow](../multi-chunk/when-to-use-chunks.md)
covers this case.

## Why `chunk.components` isn't enough

Metashape exposes `chunk.components` (since 2.1) — a list of
sub-graphs of the bundle's connectivity. A chunk with only
one component is *globally connected*, but the connection may
be a thin thread of one or two tracks. The shared-tie-point
graph reveals these threads where `chunk.components` alone
declares everything fine.

For a true multi-component check (the bundle solver actually
gave up trying to fit them as one), use `chunk.components`.
For an early-warning signal of fragile connectivity, use the
shared-tie-point graph in this article.

## Performance considerations

For a chunk with N tracks and M cameras, the build cost is
O(M × projections-per-camera) for the per-camera tracks set
(typical: minutes for a 5,000-image project), plus
O(M²) for the camera↔camera pairwise shared-count
(typical: a few seconds, since the set-intersection is fast on
modern Python). For very large projects (M > 5,000), batch the
camera loop and prune (skip camera pairs whose individual
track sets overlap by less than a threshold) to avoid
producing the dense matrix.

The sensor↔sensor matrix has the same construction with much
smaller M (typically S ≤ 10), so it's always cheap.

## Caveats

- **Validity matters.** The recipes filter by
  `point.valid` so that filtered-out tie points don't
  contaminate the connectivity count. Skip this filter at your
  peril: a track with no validated 3D point may still have
  multiple projections in the data structure but contributes
  nothing to the bundle's geometry.
- **`camera.transform is not None`** is the alignment check.
  Cameras with `None` transform haven't been aligned and don't
  contribute projections to the bundle; skip them in the
  iteration.
- **The "isolation threshold" is empirical.** The 1%-of-average
  cutoff reflects observed behaviour on multi-sensor mission
  data; adjust upward (5%, 10%) if your projects have tighter
  inter-camera connectivity expectations.
- **Bird's-eye / orbital camera additions.** Some workflows
  add synthetic high-altitude cameras to bridge separate
  flight strips — these inflate the K-th-peer counts but for
  good reason (they're literally the bridge). Be mindful of
  this when interpreting the per-cam threshold.
- **API rename in 2.x.** In 1.x, `chunk.point_cloud` was the
  tie-point cloud (now: `chunk.tie_points`). The `points`,
  `tracks`, and `projections` sub-attributes keep their names.
- **Per-camera analysis is dominated by I/O on large
  projects.** The
  `tps.projections[camera]` access is fast, but iterating the
  full chunk for every recipe is N×M. Cache the per-camera
  sets in `cam_tracks` once and reuse for both the connectivity
  graph and any subsequent QA queries.

## See also

- [Tie-point multiplicity: track length, distribution, and what it tells you](tie-point-multiplicity.md)
  — the per-track measure that complements the per-pair
  shared-track measure introduced here.
- [Reproducing chunk-info statistics in Python](reproducing-chunk-info-statistics-python.md)
  — the chunk-wide *Tie points: y of x* recipe; uses the
  same `chunk.tie_points.projections` iteration as this
  article.
- [When does Metashape need multiple chunks?](../multi-chunk/when-to-use-chunks.md)
  — once you've identified isolated camera groups, this
  article covers the chunk-splitting decision.
- [Diagnosing under-aligned chunks](../../workflow/alignment/diagnosing-under-aligned-chunks.md)
  — the broader diagnostic ladder; the shared-tie-point
  graph is one of the more advanced rungs.
- [DSM ridge-line artefacts: alignment-quality diagnosis](dsm-ridge-lines-diagnosis.md)
  — symptom-driven entry; ridge artefacts at flight-strip
  boundaries are often a downstream signal of the
  weak-connectivity problem this article detects upstream.

## References

- *Metashape Python API Reference* (2.3.1):
  `Chunk.tie_points`, `Chunk.cameras`, `Chunk.sensors`,
  `Chunk.components`, `Camera.transform`, `Camera.sensor`,
  `Sensor.label`, `Sensor.key`, `TiePoints.projections`,
  `TiePoints.points`, `TiePoints.Point.track_id`,
  `TiePoints.Point.valid`, `TiePoints.Projection.track_id`.

