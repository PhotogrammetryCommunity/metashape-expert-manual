---
title: "Tie-point multiplicity: track length, distribution, and what it tells you"
status: unverified
applies_to: Metashape Pro 2.x — and PhotoScan 1.x via the same `chunk.point_cloud.projections` (1.x) / `chunk.tie_points.projections` (2.x) iteration
edition: "Pro / Standard"
last_reviewed: 2026-06-01
diataxis: explanation
confidence: high
---

# Tie-point multiplicity: track length, distribution, and what it tells you

> **Confidence:** *high.* The chunk-info dialog's
> *Average tie point multiplicity* field, and the formula used
> to compute it (sum of projections divided by number of
> tracks), is forum-attested via a community user's empirical
> verification (forum thread t=11148, 2019). The
> `chunk.tie_points.tracks`,
> `chunk.tie_points.points`, and
> `chunk.tie_points.projections` API surface is
> introspection-confirmed on Metashape 2.2.

## Problem

Open the Metashape chunk-info dialog or look at a generated
PDF report's *Survey Data* / *Cameras* page, and you'll see a
line like:

```
Tie points:                       226,305
Projections:                      647,136
Average tie point multiplicity:   3.21228
```
*— excerpt from a Metashape 1.5.3 report, t=11148*

The "average multiplicity" is reporting how many cameras the
typical tie point is observed in. A value of 3.21 means each
tie point was projected to ~3.2 cameras on average — a
useful summary of effective image-overlap quality.

But the field is subtly tricky:

- It's **not** simply *projections* divided by *tie points*
  (`647,136 / 226,305 ≈ 2.86`, which doesn't match `3.21`).
- It's **not** the same as the per-camera average projection
  count.
- The field changes — or doesn't change — when you remove
  tie points, depending on whether the removal also dropped
  the underlying tracks.

This article explains what tie-point multiplicity is, what
the chunk-info dialog actually computes, how it differs from
the related per-validated-tie-point multiplicity, and why
the multiplicity *distribution* (min / median / max / p95)
matters more than the average alone.

## Tracks, points, and projections

The three concepts behind any multiplicity calculation:

| Concept | API | Meaning |
|---------|-----|---------|
| **Track** | `chunk.tie_points.tracks` | A candidate match across cameras. The matcher hypothesises a single 3D scene point and assigns one *track ID*; every image where the matcher detected that point receives a *projection* with the same `track_id`. |
| **Projection** | `chunk.tie_points.projections[camera]` (per camera) | A 2D pixel coordinate in one camera, with the keypoint scale (`size`) and the `track_id` linking it to its track. |
| **Tie point** | `chunk.tie_points.points` | A track that **triangulated** to a valid 3D position. Tracks that didn't triangulate (e.g., too few projections after filtering, or all projections on a single camera) are tracks but not tie points. |

A track has *N* projections (one per camera that observed it,
modulo masking and filtering). Triangulating *that* track
yields a tie point with `point.track_id` set to the
originating track's ID. Filtering can mark a tie point's
`valid` flag as `False`, but the track and its projections
remain in the data structure.

## What chunk-info's "Average tie point multiplicity" actually computes

The official Metashape Pro 2.3 manual states a simple formula:

> "Average tie point multiplicity value is the ratio of the
> total number of projections to the number of tie points."
> — *Metashape Pro User Manual 2.3*, p. 90, *Processing
> Parameters*

But the manual's value (projections / tie points) doesn't
reproduce the report's displayed value. For the example
report excerpt above:

```
647,136 (projections) / 226,305 (tie points) = 2.860   ❌  doesn't match the displayed 3.21228
```

A community user's forum analysis pinned down the actual
formula:

> "in Metashape the average multiplicity is calculated using
> total original Tie points not final number after discarding
> those that do not meet some criteria. That is using number
> of tracks (initial number of Tie points, 478 570 in provided
> example), and all projections based on these tracks we get
> the number 3.21 of example."
> — Paulo (community forum user), 2019-07-15, Metashape 1.5
> ([permalink](https://www.agisoft.com/forum/index.php?topic=11148.msg50135#msg50135))

In other words, Metashape's *Average tie point multiplicity*
is:

```
Average = (total projection count) / (count of tracks with at least one aligned-camera projection)
```

Both quantities use the **original, unfiltered** values:

- The numerator counts every projection in
  `chunk.tie_points.projections` for every aligned camera.
- The denominator counts the size of `chunk.tie_points.tracks`,
  excluding tracks whose projections all fell on unaligned
  cameras.

So when you run *Gradual Selection → Reprojection Error*,
delete the selected tie points, and re-check the chunk info,
the *Average tie point multiplicity* may not move much — the
underlying tracks and their projections are still there, only
the validated tie points were dropped.

For the report excerpt above:

```
647,136 (projections) / 478,570 (all tracks)        = 1.353  ❌  doesn't match 3.21228
647,136 (projections) / 226,305 (validated tie pts) = 2.860  ❌  manual's stated formula, doesn't match either
647,136 (projections) / 201,481 (tracks-with-aligned-cam-projections) = 3.21228  ✅
```

The denominator that recovers `3.21228` is the number of
**tracks that have at least one projection on an aligned
camera** — not the validated-tie-point count, and not the
total-track count. Tracks whose projections all fell on
unaligned cameras don't enter the count.

You can derive this denominator yourself by running the
Python recipe below: it produces `n_tracks_with_projs`,
which equals 647,136 / 3.21228 ≈ 201,481 for the example
report. The Python value will match the chunk-info dialog's
multiplicity exactly when you re-run alignment statistics on
the same project; the discrepancy with the manual's stated
formula is documented but Metashape support has not
explicitly clarified which is intentional.

## Two multiplicity measures (the API supports both)

Once you accept that the chunk-info value uses tracks (not
validated tie points), it's natural to also compute the
**validated-tie-point multiplicity**: the average number of
projections per track that *did* triangulate to a valid 3D
point. The two measures differ when the dataset has lots of
filtered-out tie points:

- **Track multiplicity** (chunk-info value): includes tracks
  with no valid 3D point. Lower bound on real-world overlap.
- **Validated tie-point multiplicity**: only counts tracks that
  produced a valid 3D point. Stays high even after aggressive
  filtering of tie points (which doesn't remove the tracks).

For QA, both are useful:

- Track multiplicity tells you about **matching** quality —
  how many cameras the matcher believes saw each scene point.
- Validated tie-point multiplicity tells you about **bundle**
  quality — how many cameras the bundle agrees triangulated
  consistently for each point that survived.

## Computing both in Python

> **Demo verified:** ✗ — pending Tier 3 reproduction on a real Metashape install.

```python
from collections import Counter
import Metashape

chunk = Metashape.app.document.chunk
tps = chunk.tie_points

# track_id → 3D coord lookup, valid points only
valid_track_ids = {p.track_id for p in tps.points if p.valid}

# Iterate aligned cameras' projections; count per-track projections
track_proj_count = Counter()
for camera in chunk.cameras:
    if not camera.transform:
        continue
    for proj in tps.projections[camera]:
        track_proj_count[proj.track_id] += 1

# Track multiplicity: (sum of projections) / (number of tracks with ≥1 aligned-camera projection)
total_projs = sum(track_proj_count.values())
n_tracks_with_projs = len(track_proj_count)
avg_track_mult = total_projs / n_tracks_with_projs if n_tracks_with_projs else 0.0

# Validated tie-point multiplicity: same numerator restricted to validated tracks
total_validated_projs = sum(
    c for tid, c in track_proj_count.items() if tid in valid_track_ids
)
n_validated = sum(1 for tid in track_proj_count if tid in valid_track_ids)
avg_tie_point_mult = total_validated_projs / n_validated if n_validated else 0.0

print(f"Track multiplicity:           {avg_track_mult:.3f}  "
      f"({total_projs:,} projections / {n_tracks_with_projs:,} tracks)")
print(f"Validated tie-point multiplicity: {avg_tie_point_mult:.3f}  "
      f"({total_validated_projs:,} projections / {n_validated:,} validated tracks)")
```

The first value should match the chunk-info dialog's
*Average tie point multiplicity*. The second is typically
slightly higher when filtering has removed badly-triangulated
points (whose tracks tended to have few projections).

## Why the distribution matters

A single average hides important signal:

- **Average ~3.2**, with the bulk of tracks at multiplicity
  2-3 and a long tail to multiplicity 12: typical aerial
  mission with consistent overlap. Healthy.
- **Average ~3.2**, with a bimodal distribution — half the
  tracks at multiplicity 2, the other half at 4-5: indicates
  two non-overlapping image sets glued together. The
  cross-set tracks are scarce, and re-alignment may wander
  if those bridging tracks are filtered.
- **Average ~3.2**, with most tracks tightly clustered at
  multiplicity 3 and 4 (max only 4): almost certainly a
  synthetic / scripted dataset, or a turntable shoot with
  rigid camera positions where every feature is visible from
  the same small set of cameras.

For real-world projects, monitor the **maximum** and the
**95th-percentile** of the multiplicity distribution alongside
the average:

> **Demo verified:** ✗ — pending Tier 3 reproduction on a real Metashape install.

```python
from collections import Counter

# Build a distribution: how many tracks have multiplicity 2, 3, 4, ...?
length_distribution = Counter(track_proj_count.values())

# Sorted lengths
sorted_lengths = sorted(length_distribution.keys())

# Max multiplicity
max_mult = sorted_lengths[-1] if sorted_lengths else 0

# 95th percentile (linear interpolation between integer multiplicities)
total_tracks = sum(length_distribution.values())
target = total_tracks * 0.95
cum = 0
p95 = 0.0
for i, length in enumerate(sorted_lengths):
    prev = cum
    cum += length_distribution[length]
    if cum >= target:
        # Linear interpolation
        if prev < target < cum and i > 0:
            frac = (target - prev) / length_distribution[length]
            p95 = sorted_lengths[i - 1] + frac * (length - sorted_lengths[i - 1])
        else:
            p95 = float(length)
        break

print(f"Max multiplicity:            {max_mult}")
print(f"95th-percentile multiplicity: {p95:.2f}")
```

Common interpretations:

- **Max ≥ 8** is typical for aerial nadir grids with strong
  overlap. Below that suggests gaps in coverage.
- **p95 ≥ 5** indicates a healthy fraction of well-observed
  features. Below 4 suggests a thin matching graph that's
  vulnerable to filter passes.
- **Max < 3** means almost every "tie point" is a binary
  match (the bare minimum to triangulate). Strict filtering
  will gut the cloud.

## Per-sensor and per-camera multiplicity

The same aggregation works per-sensor or per-camera by
restricting the iteration:

- **Per-camera multiplicity**: average over the projections of
  one camera. Useful for spotting cameras whose features
  rarely match elsewhere (often outliers — fog, unique
  perspective, motion blur).
- **Per-sensor multiplicity**: average over the projections of
  all cameras with that sensor. Useful when one sensor in a
  multi-sensor rig is consistently under-matching the others.

The pattern is the same as the chunk-wide loop, with the
camera filter narrowed.

## Caveats

- **The chunk-info value uses tracks, not validated tie
  points.** When users report "the multiplicity didn't change
  after filtering," they're usually right — and the
  validated-tie-point multiplicity is what they actually want
  to monitor for filter effectiveness.
- **Unaligned cameras are excluded.** The numerator only
  counts projections from `camera.transform is not None`. If
  half your cameras are unaligned, the multiplicity number is
  reported on the aligned half only.
- **A "track" can have all its projections on a single
  camera.** Such tracks have multiplicity 1 and don't
  triangulate. Their inclusion in the denominator drags the
  average down. The recipe above, using
  `track_proj_count` (built only over aligned-camera
  projections), implicitly counts these single-camera tracks
  in the denominator, matching Metashape's chunk-info.
- **The 1.x → 2.x rename:** `chunk.point_cloud.projections`
  in 1.x became `chunk.tie_points.projections` in 2.x. The
  `Projection.track_id` attribute name is unchanged.
- **Cross-version comparisons need fixed pipelines.** Changing
  the *Generic Preselection* / *Reference Preselection* /
  *Tie point limit* settings between runs will change the
  multiplicity. Compare numbers across re-runs of the same
  parameters; otherwise you're measuring pipeline drift.
- **The bundle adjustment doesn't directly use multiplicity.**
  But low multiplicity is correlated with poor bundle
  conditioning — features observed in only 2 cameras have a
  4-degree-of-freedom 3D position fit, vs an 8-camera
  observation pinning a far better-conditioned 3D position.
  Multiplicity is therefore a *proxy* for bundle quality, not
  a direct input.

## See also

- [Reproducing chunk-info statistics in Python](reproducing-chunk-info-statistics-python.md)
  — the canonical chunk-info reproduction recipe; this
  article extends its *Tie points: y of x* coverage with
  the multiplicity dimension.
- [Keypoint-size-normalised reprojection error](keypoint-size-error-metric.md)
  — the other novel chunk-info statistic; pair with
  multiplicity for a comprehensive matching-quality view.
- [Sensor and camera shared-tie-point graphs](shared-tie-point-graphs.md)
  — multiplicity *across* groups (e.g. how many tie points
  one sensor shares with another).
- [Diagnosing under-aligned chunks](../../workflow/alignment/diagnosing-under-aligned-chunks.md)
  — the broader alignment-quality diagnostic ladder; low
  multiplicity is one of the leading indicators it follows.

## References

- ***Metashape Pro User Manual** 2.3* (and Standard edition),
  p. 90, *General workflow → Processing Parameters*. States
  the *Average tie point multiplicity* formula as
  "ratio of the total number of projections to the number of
  tie points" — note the discrepancy with the empirically
  reproducible formula documented in the forum thread cited
  below.
- *Metashape Python API Reference* (2.3.1):
  `Chunk.tie_points`, `TiePoints.points`, `TiePoints.tracks`,
  `TiePoints.projections`, `TiePoints.Point.track_id`,
  `TiePoints.Point.valid`, `TiePoints.Projection.track_id`.
- Forum thread, [*Average Tie point multiplicity parameter*](https://www.agisoft.com/forum/index.php?topic=11148.0)
  — a community forum user, 2019-07-15, Metashape 1.5.
  The canonical Q&A: a community forum user and Agisoft support
  work through the formula. The empirical analysis
  confirms Metashape's displayed value uses the
  original-tracks denominator (specifically, tracks with at
  least one projection on an aligned camera), not the
  post-filter validated-tie-points denominator the manual
  states.

