---
title: Automating gradual selection in Python
status: unverified
applies_to: Metashape Pro 2.2.1+ — and PhotoScan 1.x via the renamed APIs (see Caveats)
edition: Pro
last_reviewed: 2026-06-04
diataxis: how-to
confidence: medium
---

# Automating gradual selection in Python

> **Confidence:** *medium.* The `TiePoints.Filter` API surface
> is introspection-confirmed on Metashape 2.2. The 1.x → 2.x
> rename history (`buildPoints` → `triangulateTiePoints`,
> `point_cloud` → `tie_points`) is forum-attested; the precise
> intermediate names in 1.6 are inferred from changelogs.

## Problem

You have read [The Clean Tie Points → Optimize Cameras loop](../optimization/clean-tie-points-optimize-cameras-loop.md)
and want the same behaviour in a script — applied across many
projects, run in batch, or driven by a threshold rather than a
slider. What does the 2.x Python API actually look like, and what
older scripts will *not* work?

## Context

Two things changed in the 2.x API rework that 1.x-era scripts on the
forum still reference:

- **`PhotoScan.PointCloud.Filter` is gone.** The 2.x equivalent is
  **`Metashape.TiePoints.Filter`**, with the four criteria exposed
  as enum-like attributes on `TiePoints.Filter` itself
  (`ReprojectionError`, `ReconstructionUncertainty`, `ImageCount`,
  `ProjectionAccuracy`).
- **`chunk.buildPoints(error=...)` was renamed twice.** It became
  `chunk.triangulatePoints(max_error=..., min_image=...)` in
  Metashape 1.6 and was renamed again to
  `chunk.triangulateTiePoints(max_error=..., min_image=...)` in 2.0.
  The function is alive and its behaviour — *rebuild the tie-point
  cloud from stored matches at a reprojection-error threshold* —
  is unchanged. 1.x-era forum scripts (`insight-0007`,
  `insight-0008`) referencing `buildPoints` will not run on 2.x
  without renaming the method call and the `error` keyword to
  `max_error`.

A higher-level helper has also appeared:
**`Metashape.Chunk.cleanTiePoints(criterion, threshold)`** does the
"select by criterion → delete" sequence in one call, mirroring the
GUI's *Tools → Tie Points → Clean Tie Points…* command.

The authoritative source for these renames is the *Python API
Change Log* — chapter 3 of `corpus/official/metashape-python-api-2_3_1.pdf`,
which lists every per-version rename explicitly. There is also a
GUI changelog at `corpus/official/metashape-changelog.pdf` that
records GUI-level renames such as *Gradual Selection* →
*Clean Tie Points*.

## Solution

Three patterns, ordered cheapest first.

### Pattern 1 — single criterion, one-line cleanup

Use the high-level `chunk.cleanTiePoints` helper. This is the
direct Python equivalent of opening *Clean Tie Points* in the GUI,
choosing one criterion, dragging the slider to a value, and
clicking *OK*.

```python
import Metashape

doc = Metashape.app.document
chunk = doc.chunk

# Delete tie points with reprojection error > 1.0 px.
chunk.cleanTiePoints(
    criterion=Metashape.TiePoints.Filter.ReprojectionError,
    threshold=1.0,
)
chunk.optimizeCameras(
    fit_f=True, fit_cx=True, fit_cy=True,
    fit_k1=True, fit_k2=True, fit_k3=True,
    fit_p1=True, fit_p2=True,
    fit_b1=False, fit_b2=False,
    fit_corrections=False,
    adaptive_fitting=False,
)
```

This matches the canonical *Optimize Cameras* parameter set from
[The Clean Tie Points → Optimize Cameras loop](../optimization/clean-tie-points-optimize-cameras-loop.md)
article, made explicit because Python kwarg defaults differ from the
GUI defaults.

### Pattern 2 — explicit Filter for finer control

When you need to *inspect* the selection before deleting (count,
distribution, value range), use `Metashape.TiePoints.Filter`
directly:

```python
import Metashape

chunk = Metashape.app.document.chunk

f = Metashape.TiePoints.Filter()
f.init(
    chunk,                                                # accepts a Chunk
    criterion=Metashape.TiePoints.Filter.ReprojectionError,
)

# At this point f.values, f.min_value, f.max_value are populated —
# inspect the distribution before deciding the threshold.
print(f"  reprojection error range: {f.min_value:.3f} .. {f.max_value:.3f}")
print(f"  median:                   {sorted(f.values)[len(f.values) // 2]:.3f}")

# Select then remove (two-step):
threshold = 1.0
f.selectPoints(threshold)
chunk.tie_points.removeSelectedPoints()

# Alternative one-step that selects-and-removes in one call:
# f.removePoints(threshold)
```

`f.values` is the list of per-point criterion values — useful for
data-driven thresholds (e.g. "delete the worst 10 % regardless of
absolute value", which `cleanTiePoints` cannot express because it
takes a fixed threshold).

### Pattern 3 — the iteration loop

The split-threshold descent from `insight-0008`, written for 2.x:

```python
import Metashape

chunk = Metashape.app.document.chunk

OPTIMIZE_KWARGS = dict(
    fit_f=True, fit_cx=True, fit_cy=True,
    fit_k1=True, fit_k2=True, fit_k3=True, fit_k4=True,
    fit_p1=True, fit_p2=True,
    fit_b1=False, fit_b2=False,
    fit_corrections=False,
    adaptive_fitting=False,
)

def descend(criterion, target_threshold):
    """Two-pass descent on a single criterion: 2*t then t.

    Removes points with criterion-value > 2*target_threshold first
    (the worst outliers), runs Optimize Cameras, then narrows down to
    the target threshold and optimizes again.
    """
    for t in (2 * target_threshold, target_threshold):
        chunk.cleanTiePoints(criterion=criterion, threshold=t)
        chunk.optimizeCameras(**OPTIMIZE_KWARGS)

# Standard alignment-quality cleanup, in order:
descend(Metashape.TiePoints.Filter.ReconstructionUncertainty,
        target_threshold=10.0)
descend(Metashape.TiePoints.Filter.ReprojectionError,
        target_threshold=1.0)
```

The order matters: Reconstruction Uncertainty first removes
ill-conditioned tie points, then Reprojection Error narrows on the
remaining well-conditioned ones.

For larger / messier projects the *whole* `descend` block can be
wrapped in a loop with a stopping rule (e.g. "stop when the chunk's
average reprojection error stops dropping by more than 0.05 px"),
mirroring the stopping rule in the GUI article.

## Caveats and gotchas

- **`buildPoints` migration is the trickiest part of porting 1.x
  scripts.** A script that calls `chunk.buildPoints(error=t)` needs
  to become `chunk.triangulateTiePoints(max_error=t)` on 2.x —
  *both* the method name and the keyword changed. The same script
  on 1.6–1.8 needs `chunk.triangulatePoints(max_error=t)` (the
  intermediate name). Behaviour is identical across the renames:
  rebuild from stored matches with a reprojection-error threshold,
  reinstating points whose error has improved since they were
  removed.
- **Pattern 4 — non-destructive rebuild loop.** When you want the
  reinstate-points behaviour described in `insight-0008` pattern B,
  use:

  ```python
  for _ in range(MAX_ITERS):
      chunk.triangulateTiePoints(max_error=1.0)   # rebuild + threshold
      chunk.optimizeCameras(**OPTIMIZE_KWARGS)
  ```

  Unlike `cleanTiePoints`, this can grow the cloud across
  iterations as the bundle improves. Stop when consecutive passes
  produce nearly the same point count and reprojection error.
- **`PointCloud` ≠ `TiePoints`.** Metashape 2.x distinguishes the
  *tie-point cloud* (`chunk.tie_points`, the cloud of tie points
  from alignment) from the *point cloud* (`chunk.point_clouds`,
  the photogrammetry point cloud from depth maps; the 1.x term for
  this was *dense cloud*). 1.x had a single *PointCloud* and the
  Filter operated on it; in 2.x, `Metashape.TiePoints.Filter` acts
  on tie points only. Cleaning the photogrammetry point cloud is a
  different API (out of scope here).
- **`Filter.init(chunk, criterion=...)` accepts a `Chunk` despite
  the formal signature naming the parameter `points`.** This works
  by convention; pass the `chunk` directly per the API
  documentation example.
- **Optimize Cameras kwargs do not match GUI defaults.** The Python
  defaults bias toward "fit only the basics" (`fit_corrections=False`,
  `fit_k4=False`, `adaptive_fitting=False`). The GUI's *Optimize
  Cameras* dialog can be configured differently. Always pass the
  kwargs you want explicitly.
- **No automatic stopping rule.** None of these patterns stop
  iterating on their own. You must implement your own convergence
  test against the chunk's reported reprojection error
  (`chunk.meta` or by reading `f.max_value` after each pass).
  Three iterations of `descend` is the practical ceiling — beyond
  that you start carving useful tie points away (insight-0001).

## References

- **Official manual:** *Metashape Pro User Manual*, ch. 4 "Reference
  and calibration" § "Optimization" (Pro 2.3 PDF, p. 110).
- **Python Reference:** `Metashape.Chunk.cleanTiePoints`,
  `Metashape.Chunk.optimizeCameras`, `Metashape.TiePoints.Filter`,
  `Metashape.TiePoints.Filter.Criterion` —
  *Metashape Python API Reference*, version 2.3.1.
- [*How to select fixed percent of the points (Gradual Selection) using Python* (Agisoft KB)](https://agisoft.freshdesk.com/support/solutions/articles/31000154629)
  — Agisoft's own example of filtering tie points by reprojection
  error to retain a target percentage (the data-driven-threshold
  idea in Pattern 2), with both the 1.x `PointCloud.Filter` and
  2.x `TiePoints.Filter` code.
- **Forum (1.x context, do not copy verbatim):** [Dud3r, 2017-12-14, PhotoScan 1.4](https://www.agisoft.com/forum/index.php?topic=8140.msg38926#msg38926)
  for the original split-threshold-descent script.
- **Forum (the rename / API gotcha):** [LFSantosgeo, 2018-05-16, PhotoScan 1.4](https://www.agisoft.com/forum/index.php?topic=9018.msg42291#msg42291)
  for the *Gradual Selection vs Build Points* distinction (now
  obsolete in 2.x where `buildPoints` is gone).
- **Related articles:** [The Clean Tie Points → Optimize Cameras loop](../optimization/clean-tie-points-optimize-cameras-loop.md)
  is the GUI equivalent of this article; read it first for the
  rationale behind the criterion ordering and the parameter table.
- **Related feature pages:** [Gradual selection / Clean Tie Points](../../reference/features/gradual-selection.md).
- **Companion scripting articles:** [Logging from Metashape Python
  scripts](logging-from-python-scripts.md) — for capturing
  console output during long batch runs (essential during the
  iterative descent in pattern 3); [Exporting depth maps from
  Python (32-bit, scaled)](../depth-maps/exporting-depth-maps-python.md)
  — adjacent Python-API export workflow.
- **Suggested sample dataset:** [Aerial images (with GCPs)](../../reference/sample-data.md#aerial-images-with-gcps)
  — large enough that pattern-3 descent has measurable effect.

