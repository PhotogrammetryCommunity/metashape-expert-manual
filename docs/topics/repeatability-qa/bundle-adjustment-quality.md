---
title: "Bundle-adjustment quality: variance factor, overfit testing, and reference detectability"
status: unverified
applies_to: Metashape Pro 2.x. Uses the bundle-adjustment covariance API (`Calibration.covariance_matrix`, `Camera.location_covariance`) introspection-confirmed on 2.3.1; the statistical methods are standard geodesy/photogrammetry, not Agisoft-specific
edition: Pro
last_reviewed: 2026-06-16
diataxis: explanation
confidence: medium
---

# Bundle-adjustment quality: variance factor, overfit testing, and reference detectability

> **Confidence:** *medium.* The methods are standard
> least-squares / geodetic-adjustment theory (reduced chi-square;
> AIC/BIC; the Wald test; Baarda's data snooping and reliability
> numbers — see References); the Metashape API they read is
> introspection-confirmed on 2.3.1, and the bundle cost is per the
> Agisoft KB. The synthesis is original and **Demo ✗** — not yet
> reproduced end-to-end on a real install.

## Why the reported RMS isn't enough

The chunk-info dialog and the PDF report give you a *RMS
reprojection error* (in pixels and in the
[keypoint-size-normalised `kps` form](keypoint-size-error-metric.md))
and per-marker / per-camera reference errors. Those are
indispensable, but they share one blind spot: they are
**in-sample fit** metrics. The reprojection RMS can only go
**down** as you free more parameters (more adjustable
intrinsics, more tie points), so a lower RMS does **not** tell
you whether

- your **stochastic model** is sane (are the accuracy settings
  consistent with the residuals?),
- your **camera model** is *justified* rather than overfit
  (are those extra distortion coefficients earning their keep,
  or fitting noise?), or
- a **reference is wrong** (a mistyped GCP or a bad camera GPS
  fix) — and crucially, whether you could even *detect* it.

Three classical least-squares tools answer those three
questions: the **variance factor**, **calibration-parameter
significance** (is the model overfit?), and **reference
detectability** (Baarda data snooping with reliability numbers). None is reported by
Metashape directly, but all are computable from quantities the
bundle adjustment already produces.

## What *Optimize Cameras* actually solves

Photo alignment followed by *Optimize Cameras* solves a
weighted non-linear least-squares problem (a bundle
adjustment). Per Agisoft, the adjustment uses all available
measurements and their accuracies — tie- and marker-point image
projections, camera GPS positions, GCP coordinates, and scale-bar
distances ([*Control and Check points for aerial surveys* (Agisoft KB)](https://agisoft.freshdesk.com/support/solutions/articles/31000154132)).

To read any quality statistic you first have to count what is
being estimated and from what. Two ledgers:

**Free parameters `k`:**

| Source | Parameters each | Count |
|--------|-----------------|-------|
| Aligned camera (extrinsics) | 6 (3 translation + 3 rotation) | `6 · N_aligned_cameras` |
| Sensor intrinsics | adjusted calibration params (those **not** in `sensor.fixed_params`) | `Σ_sensors free_intrinsics` |
| Tie point (structure) | 3 (X, Y, Z) | `3 · N_tie_points` |
| Marker (with a 3D position) | 3 (X, Y, Z) | `3 · N_markers` |

The adjustable intrinsics are the Metashape Brown-model terms
`f, cx, cy, b1, b2, k1–k4, p1, p2` (and optional `p3, p4`); see
[Metashape's distortion model](../../workflow/camera-calibration/distortion-model-opencv-colmap.md).
The number actually adjusted for a sensor is
`len(sensor.calibration.covariance_params)` — the params left
free after `sensor.fixed_params`.

**Scalar residuals `N`:**

| Observation | Residuals each | Count | a-priori `σᵢ` |
|-------------|----------------|-------|---------------|
| Tie-point image projection | 2 (Δx, Δy, px) | `2 · N_tie_point_projections` | `tiepoint_accuracy × proj.size` — **per projection** |
| Marker image projection | 2 (Δx, Δy, px) | `2 · N_marker_projections` | `marker_projection_accuracy` |
| Camera **position** reference (enabled) | 3 (X, Y, Z, m) | `3 · N_cam_pos_ref` | `camera.reference.location_accuracy`, else `chunk.camera_location_accuracy` |
| Camera **rotation** reference (enabled) | 3 (yaw/pitch/roll or ω/φ/κ, °) | `3 · N_cam_rot_ref` | `camera.reference.rotation_accuracy`, else `chunk.camera_rotation_accuracy` |
| Marker **position** reference (enabled) | 3 (X, Y, Z, m) | `3 · N_marker_pos_ref` | `marker.reference.accuracy`, else `chunk.marker_location_accuracy` |
| Scale bar (enabled) | 1 (distance, m) | `N_scalebars` | `scalebar.reference.accuracy`, else `chunk.scalebar_accuracy` |

The `σᵢ` column is the whole stochastic model, and two rows of it are easy to get wrong:

- **The tie-point sigma is per-projection, not global.** Every projection carries a keypoint size
  (`TiePoints.Projection.size`), and its effective standard deviation is `tiepoint_accuracy`
  *multiplied by* that size — so `tiepoint_accuracy` is the accuracy of a projection **at scale 1**,
  not of every projection, and a coarse-scale feature is trusted proportionally less. Measured, not
  inferred: see [the kps metric](keypoint-size-error-metric.md) for the three experiments. The
  practical consequence is that the tie-point term must be built from the **kps** residual; using the
  pixel residual overstates it by the squared mean keypoint size (~7.6x at a 2.75 px mean).
- **A per-object accuracy supersedes the chunk default.** Where `camera.reference.location_accuracy`,
  `camera.reference.rotation_accuracy`, `marker.reference.accuracy` or
  `scalebar.reference.accuracy` is set, it wins over the corresponding `chunk.*` setting — per axis,
  for the vector-valued ones. A project that supplies per-camera accuracies in its reference table is
  therefore weighted by those, and reading the chunk-level setting alone will reproduce the wrong
  `σ̂₀²`.

Enablement is **per vector**: a camera contributes location
residuals iff `camera.reference.location_enabled`, rotation
residuals iff `rotation_enabled`; a marker contributes its 3
position residuals iff `marker.reference.enabled`. A
*referenced* marker therefore adds 3 variables (its X, Y, Z),
3 reference residuals, and 2 residuals per image projection; a
*non-referenced* marker (or any tie point) adds 3 variables and
2 residuals per projection but no reference residual.

The **redundancy** of the whole system is

```
DOF = N − k
```

(There is also a 7-parameter similarity *gauge* freedom when no
references constrain the datum; enabled references remove it.
Against millions of structure parameters this is a negligible
correction.)

## The variance factor (reduced chi-square)

With residuals `rᵢ` and their a-priori standard deviations `σᵢ`
(the per-observation `σᵢ` column of the residual table above —
note the tie-point sigma is `tiepoint_accuracy × proj.size`, and a
per-object accuracy supersedes the chunk default), the weighted
sum of squares and the
**variance factor** (a.k.a. reference variance, reduced
chi-square σ̂₀²) are

```
χ²   = Σᵢ (rᵢ / σᵢ)²          # the weighted cost at the optimum
σ̂₀²  = χ² / DOF
```

If the functional and stochastic models are both correct,
`E[σ̂₀²] = 1`. Reading it:

- **σ̂₀² ≈ 1** — residuals match the declared accuracies.
- **σ̂₀² ≪ 1** — the a-priori `σ` are *pessimistic* (residuals
  smaller than assumed). This is common because the default
  `tiepoint_accuracy = 1 px` is conservative; it does **not**
  mean the solution is bad.
- **σ̂₀² ≫ 1** — model error, under-weighting, or **outliers**.

> **What "good" actually looks like, measured.** Across 14 real projects (two 1000-camera arena scans
> and twelve 60-camera venue calibrations), with the tie-point sigma weighted correctly by
> `tiepoint_accuracy × proj.size` and Metashape's default `tiepoint_accuracy = 1 px`:
>
> | | min | median | max |
> |---|---|---|---|
> | `σ̂₀²` | 0.049 | **0.173** | 0.334 |
> | tie-point `rms_kps` | 0.221 | **0.250** | 0.362 |
>
> So a healthy solve reports **σ̂₀² ≈ 0.05–0.35, not ≈ 1**, and the genuinely stable quantity is
> `rms_kps ≈ 0.25` — it varies by less than a factor of 2 across projects spanning 60 to 1000 cameras.
> The low σ̂₀² is not a fault: it says the default 1 px is about **four times pessimistic** for these
> captures. Set `tiepoint_accuracy` to the observed `rms_kps` if you want σ̂₀² ≈ 1, since
> `√σ̂₀²` *is* the factor your declared σ were wrong by.
>
> Beware a specific trap: computing the tie-point term from the **pixel** RMS instead of the kps RMS
> inflates σ̂₀² by the squared mean keypoint size (a median factor of **12** in that sample), which
> lands it right inside a plausible-looking 0.5–2 band. That is two errors of opposite sign cancelling,
> not a calibrated model.
  This is the single most useful "is my stochastic model
  sane?" number, and the global gate for outlier detection
  below.

## Are your calibration parameters justified, or overfit?

Freeing more intrinsics (`f` → `f, cx, cy` → full Brown) always
lowers the in-sample reprojection RMS, so RMS alone cannot tell
"helpful" from "fitting noise". Three principled tests can —
and they are strongest when they **agree**.

### 1. Per-parameter significance (Wald test, from the BA covariance)

Metashape produces the parameter covariance for the adjusted
intrinsics (the *Correlation* tab; see
[*What does camera calibration results mean in Metashape?* (Agisoft KB)](https://agisoft.freshdesk.com/support/solutions/articles/31000158119)),
exposed as `sensor.calibration.covariance_matrix` (an N×N
`Matrix`) with `covariance_params` naming its rows/columns. For
an adjusted parameter θ̂ with standard error `σ_θ = sqrt(diag)`,
the Wald score `z = |θ̂| / σ_θ` tests whether the parameter
differs from a null value of **zero** (`|z| ≳ 2–3` ⇒
significant). That is meaningful for the distortion (`k1–k4`,
`p1, p2`), affinity (`b1, b2`), and principal-point (`cx, cy`)
terms — whose null is 0 — but **not** for the focal length `f`,
which is always estimated and never zero; for `f` read its
standard error and correlations, not `z`. The largest
off-diagonal **correlation** flags over-parameterisation: as
`|ρ| → 1`, two parameters are trading off against each other and
one is redundant.

```python
import math
import Metashape

def intrinsic_significance(sensor):
    """Standard errors, Wald-z, and the worst pairwise correlation
    of a sensor's adjusted intrinsics, from the BA covariance."""
    cov = sensor.calibration.covariance_matrix          # Metashape.Matrix, n x n
    names = sensor.calibration.covariance_params         # list[str], length n
    n = len(names)
    se = [math.sqrt(cov[i, i]) for i in range(n)]
    # Worst absolute correlation among the adjusted params.
    max_abs_corr = 0.0
    for i in range(n):
        for j in range(i + 1, n):
            denom = se[i] * se[j]
            if denom > 0:
                max_abs_corr = max(max_abs_corr, abs(cov[i, j] / denom))
    # Pair each standard error with the parameter value to form z = |value| / se.
    for i, name in enumerate(names):
        value = getattr(sensor.calibration, name.lower(), None)  # F->f, Cx->cx, K1->k1, ...
        # z tests H0: param == 0 — meaningful for the distortion / affinity /
        # principal-point terms, NOT focal length (always non-zero).
        if name.lower() == "f" or value is None or se[i] == 0:
            z_str = "z=  n/a"
        else:
            z_str = f"z={abs(value) / se[i]:6.1f}"
        print(f"  {name:>3}: value={value}  SE={se[i]:.4g}  {z_str}")
    print(f"  max |correlation| among adjusted params: {max_abs_corr:.3f}")

for s in Metashape.app.document.chunk.sensors:
    print(f"sensor {s.label!r}  adjusted: {s.calibration.covariance_params}")
    intrinsic_significance(s)
```

### 2. Held-out check points (cross-validation)

Disable a subset of markers' references (`reference.enabled =
False`) so they are *excluded* from the adjustment but still
triangulated. Their reprojection / 3D error is then a genuine
**held-out** estimate of accuracy (Metashape's *check* points;
see [Marker projection statistics](marker-projection-statistics.md)
and [Camera reference error](camera-reference-error-python.md)).
The decisive overfit signature: the *control* (in-sample) RMS
keeps falling while the *check* (held-out) RMS **rises** — the
extra parameters are fitting noise the held-out points don't
share.

### 3. AIC / BIC — useful, but read the caveat

For Gaussian residuals with the variance estimated from the
data, the information criteria are
`AIC = N·ln(χ²/N) + 2k` and `BIC = N·ln(χ²/N) + k·ln(N)` (up to
an additive constant common to models compared on the same
data). They penalise free parameters, so unlike RMS they *can*
prefer a simpler model. **But in a bundle adjustment they are
confounded:** the tie points are millions of *nuisance*
parameters whose count `N_tie_points` changes between runs
(alignment re-filters), so the difference in AIC across two
calibrations is dominated by `3 · Δ(N_tie_points)`, not by the
handful of intrinsics you actually care about. Use AIC/BIC only
to compare models on an **identical** observation set; for the
"which intrinsics?" question, prefer the Wald test (1) and
cross-validation (2), which are insensitive to the structure
count.

### Putting it together: the intrinsics ladder

Walk the calibration from few free parameters to many (control
`sensor.fixed_params`), **re-aligning from the same tie points**,
and read all three signals together: a richer model is justified
only when the added terms are strongly significant (`|z| ≳ 3`),
their correlation stays well below 1, **and** the held-out check
RMS improves. When the added terms are marginal, correlation
climbs toward 1, and the held-out RMS worsens while the in-sample
χ² keeps dropping, you are overfitting — fix them. The verdict is
dataset- and resolution-dependent.

For the full treatment of *which intrinsics to fix or optimize* —
the identifiability ladder, the radial-collinearity that makes
`k2, k3` unrecoverable, single- vs multi-sensor and focal-length
effects, the marginal-vs-conditional Wald test, and a controlled
synthetic study — see
[Choosing which camera parameters to fix or optimize](../../workflow/camera-calibration/choosing-camera-parameters.md).

## Detecting a bad reference — and whether you even can

A wrong GCP coordinate or a bad camera GPS fix is treated by
the bundle as a trusted observation and can warp the solution
for many cameras. Two questions: *which* reference is wrong,
and *could a wrong one even be detected?*

### Global gate, then localisation

An inflated **variance factor** says *something* is wrong but
not *what*. To localise, standardise each reference's residual
by its accuracy. A practical, conservative per-reference score
is the **Mahalanobis norm** over its enabled axes:

```
‖z‖ = sqrt( Σ_axis ( (estimated − measured)_axis / σ_axis )² )
```

For a 3-axis reference (`‖z‖` is distributed as χ with 3 DOF)
flag `‖z‖ > sqrt(χ²₃,₀.₉₉₉) ≈ 4.03`. This works uniformly for
**camera location**, **camera rotation**, and **marker
position** references — i.e. it extends the marker-only,
MAD-based screen in
[Helping alignment → *Markers have no automatic outlier detection*](../../workflow/alignment/helping-alignment.md)
to camera references, and replaces the robust-median scale with
the formally correct per-axis accuracy. The per-axis residuals
come from comparing the estimated position/rotation to the
reference (the machinery in
[Camera reference error](camera-reference-error-python.md)),
and the BA also exposes `Camera.location_covariance`,
`Camera.rotation_covariance`, and `Marker.position_covariance`
for a covariance-weighted version.

### Redundancy: some references are *uncheckable*

The catch — and the reason "no outliers flagged" can be
misleading — is **reliability**. Whether a wrong reference can
be caught at all depends on its **redundancy**: how much of its
error is geometrically *checkable* by the other observations.
With few or weakly-distributed references, a reference can have
so little redundancy that a blunder in it is **absorbed silently
into the fit** — the screen flags nothing not because the data
is clean but because it is *unverifiable*. So on a project with
only a handful of control points, "nothing flagged" is **not** a
clean bill of health. The fix is geometric, not statistical: add
more, well-spread, redundant references (extra overlapping GCPs,
more cameras seeing each one) so every reference is checked by
several others.

The formal (Baarda) version makes this quantitative: each
observation has a *redundancy number* `r̄ᵢ ∈ [0, 1]`; the w-test
standardises the residual by it
(`wᵢ = rᵢ / (σᵢ·sqrt(r̄ᵢ))`, flag `|wᵢ| > 3.29` at α = 0.1 %), and
the **Minimal Detectable Bias** `MDBᵢ = σᵢ·δ₀/sqrt(r̄ᵢ)`
(δ₀ ≈ 4.13) — the smallest catchable blunder — grows without
bound as `r̄ᵢ → 0`. Computing `r̄ᵢ` exactly needs the inverse of
the normal matrix (`R = I − A(AᵀPA)⁻¹AᵀP`), heavy for a
million-point bundle, so in practice treat a **low control-point
count as itself the warning sign** that redundancy — and
therefore detectability — is poor; the per-reference Mahalanobis
`‖z‖` above is a conservative proxy that ignores
cross-correlation.

## Caveats

- **σ̂₀² is only as honest as your accuracy settings.** The
  default `tiepoint_accuracy = 1 px` routinely makes σ̂₀² < 1;
  set realistic accuracies before reading the variance factor
  as model error.
- **Metashape filters gross errors during optimisation.** Its
  robust handling of large residuals removes the worst outliers
  from the cost, so σ̂₀² reflects the *post-filter* residuals and
  can read lower than the raw data would imply.
- **AIC/BIC are confounded by the tie-point count** — compare
  models only on an identical observation set; otherwise lean
  on the Wald test and held-out check points.
- **`covariance_matrix` requires a completed optimisation.**
  Run *Optimize Cameras* first; pass `tiepoint_covariance=True`
  if you also need tie-point covariances.
- **The Mahalanobis `‖z‖` screen ignores redundancy and
  cross-correlation.** It is a conservative flag, not the full
  Baarda w-test; with few references, low redundancy means real
  blunders can stay below threshold (see *uncheckable
  references*).
- These are **global, per-reconstruction** diagnostics; they do
  not replace per-tie-point or per-marker inspection.
- `status: unverified`, **Demo ✗** — the API is Tier-1 verified
  but the end-to-end procedure has not been reproduced on a
  real install.

## See also

- [Helping alignment when photos don't align](../../workflow/alignment/helping-alignment.md)
  — the pragmatic MAD/IRLS recipe for localising bad marker
  projections and references (this article is its rigorous,
  detectability-aware companion).
- [Keypoint-size-normalised reprojection error: the `kps` metric](keypoint-size-error-metric.md)
  and [Reprojection error analysis](reprojection-error-analysis.md)
  — the in-sample residuals these diagnostics sit on top of.
- [Marker projection statistics](marker-projection-statistics.md),
  [Scalebar distance error](scalebar-error-statistics.md),
  [Camera reference error](camera-reference-error-python.md)
  — per-observation error extraction.
- [Metashape's distortion model and converting to OpenCV / Colmap](../../workflow/camera-calibration/distortion-model-opencv-colmap.md)
  — the Brown model whose parameters the overfit test screens.

## References

- *Metashape Python Reference* (2.3.1): `Calibration.covariance_matrix`,
  `Calibration.covariance_params`, `Sensor.fixed_params`,
  `Camera.error`, `Camera.location_covariance`,
  `Camera.rotation_covariance`, `Marker.position_covariance`,
  `Chunk.optimizeCameras` (`tiepoint_covariance`). Symbols
  introspection-confirmed on 2.3.1.
- Agisoft KB [*Control and Check points for aerial surveys* (Agisoft KB)](https://agisoft.freshdesk.com/support/solutions/articles/31000154132)
  — the bundle cost (which measurements and accuracies enter the
  adjustment) and the control-vs-check distinction.
- Agisoft KB [*What does camera calibration results mean in Metashape?* (Agisoft KB)](https://agisoft.freshdesk.com/support/solutions/articles/31000158119)
  — the calibration covariance / *Correlation* tab and the
  bad-camera-model cues.
- Baarda, W. (1968). *A testing procedure for use in geodetic
  networks.* Netherlands Geodetic Commission — data snooping
  (w-test), reliability, and the Minimal Detectable Bias.
- Förstner, W. (1987). *Reliability analysis of parameter
  estimation in computer vision.* — redundancy numbers and
  internal/external reliability in photogrammetry.
- Akaike, H. (1974). *A new look at the statistical model
  identification.* IEEE TAC — AIC.
- Schwarz, G. (1978). *Estimating the dimension of a model.*
  Annals of Statistics — BIC.
