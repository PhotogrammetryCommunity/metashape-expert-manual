---
title: "Ground classification: the erosion radius parameter"
status: unverified
applies_to: Metashape Pro 1.7.5 — unchanged through 2.3
edition: Pro
last_reviewed: 2026-06-05
diataxis: explanation
confidence: high
---

# Ground classification: the erosion radius parameter

> **Confidence:** *high.* The parameter is documented in the
> official manual (§ *Editing → Classify Ground Points*, p. 146)
> and confirmed via forum post from Agisoft support with a
> permalink.

## What it does

The **Erosion radius** parameter in *Classify Ground Points* (added in
Metashape 1.7.5) creates a buffer zone around non-ground points. Any
ground-classified point within this radius of a non-ground point is
reclassified as unclassified.

> "Erosion radius determines the indentation (in meters) from
> unclassified points, ground points within that area will be
> unclassified. This new option may be useful when classifying areas
> with houses and trees to avoid 'stumps' on DTM when building
> elevation model from the ground points class."
> — Alexey Pasumansky, 2021-10-13, Metashape 1.7.5
> ([permalink](https://www.agisoft.com/forum/index.php?topic=13821.msg61023#msg61023))

## The "stump" problem

When a building or tree is classified as non-ground, the ground points
immediately adjacent to its base often remain classified as ground.
These edge points typically have slightly elevated Z values — they sit
on the building's foundation, root flare, or the transition zone where
the classifier is uncertain.

When a DTM is interpolated from ground-class points only, these edge
points create small raised "stumps" at the base of every removed
structure. The DTM surface rises slightly where each building or tree
was, then drops back to true ground level — producing visible artefacts
in the elevation model.

## How erosion radius fixes it

Setting `erosion_radius` to a positive value (in metres) removes all
ground points within that distance of any non-ground point. This
creates a clean buffer zone that the DTM interpolator bridges smoothly,
eliminating the stumps.

Typical values:

| Scenario | Erosion radius | Rationale |
|----------|---------------|-----------|
| Urban buildings | 0.5–1.0 m | Foundation footprint extends ~0.5 m beyond walls |
| Trees / vegetation | 0.3–0.5 m | Root flare and trunk base |
| Power lines / poles | 0.1–0.2 m | Narrow structures, small buffer needed |
| No erosion (default) | 0.0 m | Preserves all ground points |

## Python API

Ground classification is a method on the `PointCloud` object:

> **Demo verified:** ✗ — requires point cloud from aligned dataset.

```python
import Metashape

chunk = Metashape.app.document.chunk

chunk.point_cloud.classifyGroundPoints(
    max_angle=15.0,       # max angle (deg): ground-slope assumption
                          # (distinct from the separate 'Max terrain slope')
    max_distance=0.5,     # max distance to classified surface (m)
    cell_size=50.0,       # initial cell size for TIN (m)
    erosion_radius=0.5,   # buffer zone around non-ground (m)
)
```

The default `erosion_radius` is **0.0** (disabled). The parameter is
only meaningful after classification has already assigned non-ground
labels — it operates as a post-processing step on the classification
result.

## When to use it

- **DTM generation from classified point clouds.** If your DTM shows
  raised artefacts at building/tree bases, add erosion radius.
- **Urban scenes with many structures.** Buildings with wide
  foundations benefit from 0.5–1.0 m erosion.
- **Forested terrain.** Tree trunks and root systems create transition
  zones that the standard classifier often misclassifies.

## When NOT to use it

- **Flat terrain with no structures.** Erosion removes valid ground
  points near any non-ground classification. On flat terrain with
  sparse vegetation, this may create unnecessary gaps.
- **When ground point density is already low.** Erosion further reduces
  ground points. If your point cloud is sparse, the DTM interpolator
  may not have enough points to bridge the gaps cleanly.
- **Before verifying classification quality.** Fix misclassification
  first — erosion is a refinement step, not a substitute for correct
  classification parameters.

## Key points

- Added in Metashape 1.7.5. Default: 0.0 (disabled).
- Removes ground points within N metres of non-ground points.
- Prevents DTM "stumps" at building/tree bases.
- Accessed via `chunk.point_cloud.classifyGroundPoints()`.
- Typical values: 0.3–1.0 m depending on structure type.

## References

- *Metashape Pro User Manual* (2.3), § *Editing → Classify Ground
  Points*, p. 146 — documents all parameters including Erosion radius.
- [*Point Cloud Classification* (Agisoft KB)](https://agisoft.freshdesk.com/support/solutions/articles/31000148866)
  — the full ground / multi-class / manual classification workflow
  and DTM generation; and [*Parameters for ground point classification* (Agisoft KB)](https://agisoft.freshdesk.com/support/solutions/articles/31000160729)
  — a deep dive on Max angle, Max distance, Max terrain slope, Cell
  size, Return and Erosion radius with worked examples (rural,
  low-vegetation, satellite).

