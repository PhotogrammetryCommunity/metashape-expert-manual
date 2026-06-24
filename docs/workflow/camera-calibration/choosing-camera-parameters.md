---
title: "Choosing which camera parameters to fix or optimize"
status: unverified
applies_to: Metashape Pro 2.x. The decision criterion uses the bundle-adjustment covariance (`Calibration.covariance_matrix` / `covariance_params`) introspection-confirmed on 2.3.1; the controlled study and the methods are standard photogrammetry, not Agisoft-specific
edition: Pro
last_reviewed: 2026-06-23
diataxis: explanation
confidence: medium
---

# Choosing which camera parameters to fix or optimize

> **Confidence:** *medium.* The decision criterion (the Wald
> identifiability test and the parameter-correlation check) is
> standard estimation theory; the code reads
> `Calibration.covariance_matrix` / `covariance_params`,
> introspection-confirmed on 2.3.1. The quantitative results
> below come from a **controlled synthetic study** (this
> manual's) — original synthesis, **Demo ✗**, not yet reproduced
> on an independent install. The qualitative rules are
> corroborated by the official manual, the Agisoft KB, and the
> forum (see References).

## The problem

`Optimize Cameras` (and `Align Photos`) lets you choose which
intrinsics to estimate — focal length `f`, principal point
`cx, cy`, radial distortion `k1–k4`, tangential `p1, p2`,
affinity `b1, b2`. Free **too few** and you bake real lens
distortion into the reconstruction (bias); free **too many** and
the surplus parameters absorb measurement noise instead of lens
behaviour (variance / overfitting). The usual advice — "use the
default set", or "free everything and let the bundle sort it
out" — is lore. This article gives a quantitative way to decide,
for *your* camera, scene, and sensor layout.

The central idea: **what you can estimate is set by the geometry
and the observation strength, not by the lens alone.** A
parameter is *identifiable* only if the data actually constrain
it. Agisoft's own *Adaptive camera model fitting* is built on
exactly this — it automatically selects which parameters to adjust from their
*reliability estimates*: with strong camera geometry (a building
shot from all sides, at multiple levels) it can adjust more
parameters, while with weak geometry (a typical aerial set) it
holds the unconstrained ones fixed to prevent divergence —
radial distortion, for instance, is very unreliable when the
object covers only the image centre
(*Metashape Pro 2.3 manual*, *Aligning photos and laser scans*).
This article makes that principle measurable.

## The criterion: the Wald identifiability test

After a bundle adjustment, every free parameter has an estimate
`θ̂` and a standard error `σ_θ = sqrt(diag(covariance))`. Their
ratio is the **Wald statistic**:

```
|z(θ)| = |θ̂| / σ_θ
```

Read it as *how well the data determine the parameter*:

- `|z| ≳ 3` — solidly determined; **keep it**.
- `|z| < 2` — indistinguishable from its null value: either its
  standard error is too large to pin it down (unidentifiable) or
  the term is genuinely ≈ 0. Either way it isn't earning its
  place — **fix it**.
- `2 ≤ |z| < 3` — a gray zone; keep only with corroborating
  evidence (a held-out improvement; see the recipe).

Two properties make `|z|` convenient. First, it scales
**approximately** as `1/σ` — roughly, halving the feature-matching
noise doubles each *identifiable* `z`, though a slow per-parameter
drift can re-order parameters whose `|z|` are near-tied (see the
`k1`/`cx` crossover below). Second, an *unidentifiable* parameter
floors at `|z| ≈ 1` rather than decaying to zero — so `|z| ≈ 1` is
the positive signature of "the data can't see this". (For `f` the
test reads simply as "very well determined"; `f` is always kept.)

Metashape exposes the covariance but not `|z|`. Compute it from
any solved chunk (after `optimizeCameras`); this needs only the
Metashape API and the standard library, and runs without a
license:

```python
import math

def wald_z(calibration):
    """Per-parameter Wald |z| = |value| / standard_error for a solved
    Metashape calibration. |z| >~ 3 -> keep; |z| < 2 -> fix."""
    names = list(calibration.covariance_params)   # e.g. ['F','Cx','Cy','K1','K2','K3','P1','P2']
    cov = calibration.covariance_matrix           # p x p Metashape.Matrix
    out = {}
    for i, name in enumerate(names):
        value = getattr(calibration, name.lower())  # f, cx, cy, k1, ...
        var = cov[i, i]
        # nan flags a degenerate / non-positive variance (broken covariance), not "keep".
        out[name] = abs(value) / math.sqrt(var) if var > 0 else float("nan")
    return out
```

A companion check — the **parameter correlation matrix** —
exposes parameters that trade off against each other (the root
cause of unidentifiable distortion terms):

```python
import math

def parameter_correlations(calibration):
    """Pairwise correlations of the estimated intrinsics. |corr| -> 1
    means the two parameters are near-degenerate; keep the lower-order
    / dominant one and fix the other."""
    names = list(calibration.covariance_params)
    cov = calibration.covariance_matrix
    sd = [math.sqrt(cov[i, i]) if cov[i, i] > 0 else 0.0 for i in range(len(names))]
    out = {}
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            denom = sd[i] * sd[j]
            out[(names[i], names[j])] = cov[i, j] / denom if denom > 0 else float("nan")
    return out
```

These two functions are the entire decision tool. The rest of
the article builds intuition for reading them.

## What the data can actually determine — a controlled study

To check that the Wald test gives the *right* answer, a
controlled synthetic scene with a **known** lens was rendered,
calibrated with the same free-pose bundle adjustment SfM uses,
and swept across feature-matching noise. The scene is
representative of a real calibration capture: 1000 points in a
sphere, **12 cameras around it at diverse azimuths and
elevations**, the target **filling the frame**, a wide-angle
24 mm lens with visible distortion (`k1` ≈ 40 px at the corner,
`k2` ≈ 4 px, a deliberately *visible* `k3` ≈ 1 px). Independent
Gaussian pixel noise (feature matchers typically reach 0.3–1 px)
was added; every figure is averaged over 5 noise realizations.

Per-parameter `|z|` for the **single-sensor 24 mm** baseline
(**bold** = `|z| ≲ 2`, i.e. fitting noise):

| σ (px) | `f` | `cx` | `cy` | `k1` | `k2` | `k3` | `p1` | `p2` |
|-------:|----:|-----:|-----:|-----:|-----:|-----:|-----:|-----:|
| 0.20 | >10⁴ | 70 | 49 | 62 | **2.1** | **1.3** | 22 | 14 |
| 0.50 | 8249 | 28 | 20 | 25 | **1.4** | **1.2** | 8.8 | 5.6 |
| 1.00 | 4125 | 14 | 9.9 | 13 | **1.3** | **1.2** | 4.4 | 2.8 |

At realistic noise the identifiable model is exactly
**`f, k1, cx, cy, p1, p2`** — fix `k2, k3`. The **order** in
which parameters drop out as noise rises (the *identifiability
ladder*, most robust first) is:

```
f  >  k1  >  cx, cy  >  p1, p2  >  k2  >  k3
```

The principal point (`cx, cy`) and the tangential terms
(`p1, p2`) are each treated as a **pair**: they are physically
coupled and the small within-pair threshold differences are
measurement noise, not a real ordering — which is why the
recommended models are written `C` and `P`, never split.

The ladder ranks `k1` above the `cx, cy` pair even though the `|z|`
table shows `cx` slightly *higher* across the tabulated range: the two are
near-tied, but `k1` stays above the `|z| = 2` line to higher noise
(it doesn't drop out until ≈ 11 px) than `cx` (≈ 8 px), so it is
the more robust *as noise rises* — the `1/σ` scaling is only
approximate. Both readings are correct, and the distinction is
operationally moot: at ≤ 1 px all of `f, cx, cy, k1, p1, p2` sit
far above the keep line, so the identifiable model is `k1 + C + P`
either way.

`k2, k3` sit at the `|z| ≈ 1.2` floor — *even the visible 1 px
`k3`* — at every realistic noise level.

## Why `k2, k3` fail: collinearity, not weak signal

It is tempting to assume `k2, k3` fail because their effect is
tiny. It is not: at **zero** noise they *are* recovered. They
become unidentifiable the instant noise enters, because the
radial monomials `r², r⁴, r⁶` are nearly **collinear** over the
image-radius range a real capture spans. The measured
correlations are stark:

```
corr(k2, k3) = -0.99    corr(k1, k2) = -0.97    corr(k1, k3) = +0.93
```

`k1` absorbs essentially all the recoverable radial signal, and
the standard errors of `k2, k3` are hugely inflated. Raising `k3`
to a clearly visible 1 px only moved its threshold
proportionally — identifying `k3` at 0.5 px noise would need
~12 px of corner distortion (a strong fisheye). **The binding
constraint is the collinearity, not the magnitude.** Practical
reading: when `parameter_correlations` shows `|corr| > ~0.95` for
a pair, keep the lower-order/dominant term (here `k1`) and fix
the rest.

## Geometry, sensors, and focal length

Three levers move the whole ladder:

- **Capture geometry decides observability.** A *planar* ring of
  cameras gives horizontal parallax (constrains `cx`) but no
  vertical parallax, leaving `cy` unidentifiable; diverse
  elevations fix it. Radial terms need features at the image
  **periphery**, so the scene must fill the frame. This is the
  manual's "strong vs weak geometry" made concrete.
- **A shared sensor is far more robust than per-camera
  intrinsics.** When *one physical camera* takes all the images
  (model it as a **single sensor**), the principal-point and
  tangential terms become identifiable at realistic noise; with
  *different* cameras each carrying their own intrinsics
  (**multi-sensor**), only `f` and `k1` survive per camera —
  in the study, the usable-noise threshold for `cx, cy, p1, p2`
  was **~14–50× higher** for a shared sensor. Group cameras that
  share an identical lens into one sensor where that is valid.
- **Longer focal length weakens every term, the principal point
  first.** A narrow, near-orthographic field cannot separate the
  principal point from a small camera translation. On long
  lenses, free fewer parameters and fix the high-order distortion
  earlier.

## The recipe — choosing parameters for your configuration

Don't pick the set from lore or from a fixed-pose fit — **measure
it on the solve you will actually run.** The one subtlety that
governs *how many steps* this takes: each parameter's `|z|` is
**conditional** on which others are free (collinear terms share
signal), so you **cannot** read all the `|z|` once and fix every
low one in a single shot. Use **backward elimination**, re-fitting
between each removal:

1. **Solve realistically** with the full candidate set free: poses
   and points free, your real geometry, candidate intrinsics free,
   **one sensor per physical camera**.
2. **Compute** `wald_z` and `parameter_correlations` for the free
   parameters.
3. **Fix the single least-significant parameter.** A term with
   `|z| < 2` is unidentifiable — fix it; a term in the `2–3` gray
   zone is fixed only if doing so does not worsen a **held-out**
   error (check
   points, or a left-out image subset) — held-out, not the
   in-sample tie-point residual, which *always* falls as you add
   parameters (see [Bundle-adjustment quality](../../topics/repeatability-qa/bundle-adjustment-quality.md)).
   Treat `cx, cy` and `p1, p2` as **pairs** — drop or keep each
   pair together. For a strongly collinear pair (`|corr| > ~0.95`,
   e.g. the radial terms) fix the higher-order / redundant one.
4. **Re-solve** — realign and optimize (`alignCameras(reset_alignment=True)`
   then `optimizeCameras`, *not* an optimize-only pass over frozen
   tracks, which inherits the old model's geometry) — and **repeat
   from 2** on the smaller model, until every remaining parameter
   has `|z| ≳ 3` and removing any further term would worsen the
   held-out error.

**Drop one parameter (or pair) per iteration, not all the low ones
at once.** A term that looks marginal while a collinear partner is
free can become significant once that partner is fixed (and
vice-versa) — judge each by its **conditional** `|z|` (with the
others still free), never its **marginal** `|z|` against a bare
baseline. `k2` is the classic trap: significant against `f, k1`
alone, but becomes noise once `cx, cy, p1, p2` are free.

**Pragmatic shortcut (often just two solves).** When the `|z|` are
already well separated after the first solve — `k2, k3` deeply
insignificant (`|z| ≈ 1`) while `f, k1, cx, cy, p1, p2` are clearly
significant (`|z| ≫ 3`), the common low-distortion case — you may
fix all the clearly-insignificant terms at once, re-solve **once**,
and simply *verify* that every kept parameter is still `|z| ≳ 3`.
The full iteration only bites when terms sit in the gray zone
(`2 ≤ |z| < 3`) or are mutually collinear.

**Group sensors by focal length** and run this per group: a long
lens overfits `k3` far sooner than a wide one, so a single global
parameter set can be wrong for a mixed-lens rig.

Two further checks when the data allow them:

- **Per-camera spread** across physically identical lenses: if a
  term's value scatters wildly camera-to-camera, it is being set
  by per-image noise, not a shared lens property — fix it.
- **Cross-capture transfer (the strongest test):** calibrate the
  *same* lens twice (e.g. two resolutions of the same sensor).
  The dimensionless distortion coefficients (`k1–k4, p1, p2`)
  should be **identical**; `f, cx, cy` should differ only by the
  pixel-pitch ratio. Keep only the coefficients that reproduce —
  a single solve can call a term significant that a second
  capture exposes as non-reproducible.

### What to expect

- `f` and `k1` are almost always identifiable — keep them.
- `cx, cy` and `p1, p2` earn their place when the geometry is
  rich (many cameras, diverse directions, scene filling the
  frame, ideally a shared sensor) — the common **`k1 + C + P`**
  model `f, k1, cx, cy, p1, p2`. Freeing the **principal point is
  often the single biggest win**; tangential `p1, p2` (degree-2
  *decentering*, well-sampled across the frame, orthogonal to the
  radial series) routinely beat the high-order radial `k3`
  (degree-6, corner-only, collinear with `k1, k2`).
- `k2, k3` rarely earn their place (radial collinearity). Free
  them only with low noise, strong distortion, *and* a
  demonstrated held-out improvement.

This is consistent with the forum guidance to "select camera
parameters based on the camera type" — a frame camera being
"processed well with default parameter set" (`f, cx, cy, k1–k3, p1, p2`)
(nprokofyev, 2021-03-30, Metashape 1.7,
[topic 13221](https://www.agisoft.com/forum/index.php?topic=13221.msg58683#msg58683))
— and with the KB cue to fix `cx, cy, b1, b2` when their adjusted
values come out implausibly large
([*What does camera calibration results mean in Metashape?* (Agisoft KB)](https://agisoft.freshdesk.com/support/solutions/articles/31000158119)).

## Or let Metashape decide: Adaptive camera model fitting

Metashape's *Adaptive camera model fitting* automates the
promote/demote decision per camera from reliability estimates. It
helps for strong geometry and prevents divergence for weak
geometry, but it is a black box (you can't see which parameters
it kept), it is per-camera (can diverge across a rig's sensors),
and it is **disabled** in the canonical clean-alignment baseline.
For a rig, or when you need a reproducible, inspectable choice,
prefer the manual `fit_*` selection driven by the recipe above.
See [Adaptive camera model fitting](../../reference/features/adaptive-camera-model-fitting.md)
for when to enable vs disable it.

## Caveats

- **Identifiability is dataset-specific.** The model that is
  right for a rich, shared-sensor capture is wrong for a sparse,
  multi-sensor or long-lens one — re-run the recipe per
  configuration; don't transplant a parameter set.
- **`covariance_matrix` requires a completed optimization**, and
  reflects Metashape's post-filter residuals (gross-error
  filtering can deflate the standard errors).
- **The Wald test needs free poses.** A fixed-pose fit overstates
  identifiability because a principal-point shift is nearly
  degenerate with a small camera translation.
- **`b1, b2` (affinity/skew) are ~0 for square-pixel digital
  sensors** — leave them fixed unless you have a specific reason.
- `status: unverified`, **Demo ✗** — the snippets are Tier-1
  API-verified; the study's figures are original synthesis, not
  reproduced on an independent install.

## See also

- [Bundle-adjustment quality: variance factor, overfit testing, and reference detectability](../../topics/repeatability-qa/bundle-adjustment-quality.md)
  — the broader diagnostics (variance factor, held-out check
  points, reference outliers) this builds on.
- [Adaptive camera model fitting](../../reference/features/adaptive-camera-model-fitting.md)
  — Metashape's automatic alternative.
- [Metashape's distortion model and converting to OpenCV / Colmap](distortion-model-opencv-colmap.md)
  — the Brown model whose terms are being selected.
- [`sensor.calibration` vs `sensor.user_calib`](sensor-calibration-vs-user-calib.md),
  [Rolling-shutter compensation](rolling-shutter-compensation.md)
  — fixing intrinsics requires undistorted, rolling-shutter-clean input.

## References

- *Metashape Python Reference* (2.3.1): `Calibration.covariance_matrix`,
  `Calibration.covariance_params`, `Sensor.fixed_params`,
  `Chunk.optimizeCameras` (`fit_f`, `fit_cx`, …, `adaptive_fitting`),
  `Chunk.alignCameras` (`reset_alignment`). Introspection-confirmed on 2.3.1.
- *Metashape Professional User Manual* (2.3): *Aligning photos and
  laser scans* — *Adaptive camera model fitting* (≈ p. 46);
  *Optimize Camera Alignment parameters* (≈ p. 118); *Appendix C,
  Camera models*.
- [*What does camera calibration results mean in Metashape?* (Agisoft KB)](https://agisoft.freshdesk.com/support/solutions/articles/31000158119)
  — the "fix `cx, cy, b1, b2` when their adjusted values are large" cue.
- Forum, [*Selecting camera parameters to be optimized*](https://www.agisoft.com/forum/index.php?topic=13221.msg58683#msg58683)
  — nprokofyev, 2021-03-30, Metashape 1.7: choose by camera type;
  a frame camera is processed well by the default set.
- Brown, D. C. (1971). *Close-range camera calibration.*
  Photogrammetric Engineering — the radial/decentering model.
- Wald, A. (1943). *Tests of statistical hypotheses concerning
  several parameters when the number of observations is large.*
  Trans. Amer. Math. Soc. — the large-sample `|z|` significance test.
