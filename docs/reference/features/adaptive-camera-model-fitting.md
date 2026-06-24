# Adaptive camera model fitting

> **Status:** documented (2026-05-24).

## What it is

*Adaptive camera model fitting* is a kwarg of
`alignCameras` and `optimizeCameras` that decides — per
camera, during the bundle — which lens-distortion parameters
to fit and which to hold fixed. Without it (the default), the
bundle uses a fixed parameter set: typically `f`, `cx`, `cy`,
`k1`, `k2`, `k3`, `p1`, `p2`. With adaptive fitting, the
bundle promotes additional parameters (`k4`, `b1`, `b2`) only
for cameras where the data supports them, and demotes
parameters that don't have enough constraint.

The intuition: a bundle with too many free parameters per
camera over-fits, especially for cameras with few tie points;
a bundle with too few free parameters under-fits cameras
whose actual lens distortion is more complex than the model
allows.

## Where it lives

| | Standard | Pro |
|---|---|---|
| **GUI** | *Workflow → Align Photos* → *Advanced* → **Adaptive camera model fitting**; same option in *Reference → Optimize Cameras* | (same) |
| **Python** | `Metashape.Chunk.alignCameras(adaptive_fitting=True/False, …)`<br>`Metashape.Chunk.optimizeCameras(adaptive_fitting=True/False, …)` | (Pro only) |
| **Default** | `False` | `False` |

## When to enable

The recommended setting in the canonical "clean" recipe (per
[Diagnosing under-aligned chunks](../../workflow/alignment/diagnosing-under-aligned-chunks.md))
is **disabled**:

> "Adaptive fitting - disabled" — Alexey Pasumansky,
> 2021-02-11, Metashape 1.7
> ([permalink](https://www.agisoft.com/forum/index.php?topic=13079.msg58789#msg58789))

That is, the alignment-debugging baseline keeps the parameter
set fixed rather than letting the bundle decide what to fit.
Adaptive fitting introduces enough variability that it can
mask the underlying alignment problem you're trying to
diagnose.

For *production* alignment (after the chunk is healthy), the
trade-off is dataset-specific:

- **Many cameras with high-quality matches across diverse
  views:** adaptive fitting can find better intrinsics for
  some cameras (the ones with enough constraint) without
  destabilising the others. Often a small accuracy
  improvement.
- **Few cameras, or cameras with poor matches:** adaptive
  fitting can overshoot — promoting parameters the data
  doesn't actually constrain. Often makes the bundle worse,
  not better.
- **Multi-sensor projects (rig with master + slaves):**
  adaptive fitting can produce non-uniform intrinsics across
  sensors that should be treated identically. Usually
  disabled for rigs.

## When to disable

- Always for the canonical "clean" debugging recipe.
- For alignment-failure diagnosis (lets you see the underlying
  problem rather than a parameter-fitted artefact of it).
- For multi-sensor rigs.
- When the dataset has many cameras with marginal tie-point
  support.

## Caveats

- **Adaptive fitting interacts with the explicit `fit_*` flags
  on `optimizeCameras`.** Passing
  `optimizeCameras(adaptive_fitting=True, fit_k4=False, ...)`
  may or may not override the adaptive selection — the
  documented behaviour is unclear. Best practice: set
  `adaptive_fitting=False` and explicitly set the `fit_*`
  flags you want.
- **The criterion for promoting / demoting parameters is not
  exposed.** Adaptive fitting is a black-box decision per
  camera; you cannot inspect *which* parameters were
  promoted/demoted for which cameras (or only via post-hoc
  analysis of `sensor.calibration`).
- **Adaptive fitting is per-camera, not per-sensor.** Cameras
  in the same sensor group can end up with different
  parameter sets. This is usually undesirable; reset and use
  `adaptive_fitting=False` if you observe per-camera
  intrinsic divergence within a sensor.

## Related concepts

- *Optimize Cameras* — the bundle-refinement step that uses
  this flag.
- [Tightening reference accuracies after `alignCameras`](../../workflow/optimization/tightening-reference-accuracies.md)
  — the multi-phase recipe that uses `adaptive_fitting=False`
  for stability.
- [The Clean Tie Points → Optimize Cameras loop](../../workflow/optimization/clean-tie-points-optimize-cameras-loop.md)
  — also uses `adaptive_fitting=False`.

## Articles in this manual

- [Diagnosing under-aligned chunks](../../workflow/alignment/diagnosing-under-aligned-chunks.md)
  — keeps adaptive fitting **disabled** in the canonical
  alignment-debugging recipe.

## Forum threads worth reading

| Date | Version | Author | Thread | One-line takeaway |
|------|---------|--------|--------|-------------------|
| 2021-02-11 | Metashape 1.7 | Alexey Pasumansky | [Tie points ghosting](https://www.agisoft.com/forum/index.php?topic=13079.msg58789#msg58789) | The canonical "clean" baseline keeps adaptive fitting disabled. |
