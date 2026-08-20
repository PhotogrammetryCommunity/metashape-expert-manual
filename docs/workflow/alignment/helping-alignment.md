---
title: "Helping alignment when photos don't align: markers, references, and what to use when"
status: unverified
applies_to: Metashape Pro 2.x — and PhotoScan / Metashape 1.x with the same Reference pane and marker workflow. Marker-based recovery is Pro-only; reference-based hints work on Standard and Pro.
edition: "Pro / Standard"
last_reviewed: 2026-06-16
diataxis: how-to
confidence: medium
---

# Helping alignment when photos don't align: markers, references, and what to use when

> **Confidence:** *medium.* Most operational claims in this
> article are forum-attested with an Agisoft-support permalink
> or sourced from the official Metashape Pro 2.3 manual, and the
> `Camera.transform`, `Camera.reference`, `Marker.projections`,
> `Chunk.alignCameras`, and `Chunk.updateTransform` API surface
> is introspection-confirmed (Metashape 2.2, with the marker /
> projection API used in the outlier-rejection recipe re-checked
> on 2.3.1). That recipe — in *Markers have no automatic outlier
> detection* — is **original synthesis** (the IRLS / MAD framing,
> thresholds, and projection-first ordering): its API calls are
> Tier-1 verified but the procedure itself is **Demo ✗**, not yet
> reproduced on a real install. The Ground Altitude caveat below
> is single-source and is flagged explicitly.

> **Scope statement.** This article unifies guidance from
> several existing pages:
> [Diagnosing under-aligned chunks](diagnosing-under-aligned-chunks.md),
> [Recovery paths for unaligned cameras](recovery-paths-unaligned-cameras.md),
> [Synthetic position priors via `ReferencePreselectionSource`](synthetic-priors-reference-preselection.md),
> and [Programmatic marker placement and pinning](../markers-gcps/programmatic-marker-placement.md).
> Read this for the **decision framework** ("when do I use what"); follow
> the cross-links for the deep-dive recipes.

## Problem

A set of photos doesn't align — or aligns only partially —
and the [canonical clean-settings re-run](diagnosing-under-aligned-chunks.md)
hasn't fixed it. Common root causes:

- **Lack of features**: featureless walls, blank sky, water,
  fog, snow.
- **Symmetries and repetitive patterns**: building façades,
  tiled floors, agricultural row crops, brick walls.
- **Specular or transparent objects**: glass, polished metal,
  water surfaces.
- **Motion blur or exposure issues**: blurry frames or wildly
  varying exposure.

The two interventions Metashape supports for these scenes are
**markers** and **camera references** (GPS positions, IMU
rotations, scalebar distances). They work via different
mechanisms and apply at different points in the pipeline.

This article answers the practical questions that come up when
deciding which to use: when to apply markers, how many you
need, whether approximate references help, what happens by
default with no reference data, and how to enter reference
information in the GUI.

## Alignment-aid mechanisms at a glance

The four mechanisms Metashape provides for helping a stuck
alignment, with what each is for:

| Mechanism | Where it acts | Required edition | Best for |
|-----------|---------------|------------------|----------|
| **Markers** (manual tie points) | After alignment runs — supplement automatic tie-point matches with hand-pinned 2D-2D correspondences | Pro only | Recovering specific unaligned cameras; bridging visually-distinct regions |
| **Camera reference priors** (`camera.reference.location` / `…rotation`) | Before / during alignment — restrict matcher pair candidates by spatial proximity; provide bundle constraints | Pro and Standard | Defeating repeated-geometry; large datasets where pair selection matters; bootstrapping a chunk-internal frame |
| **Markers with reference coordinates** (GCPs) | Both — manual tie points during alignment AND bundle constraints during *Optimize Cameras* | Pro only | Surveyed projects where world-frame accuracy matters |
| **Scalebars** (`Chunk.scalebars`) | After alignment — distance constraints during *Optimize Cameras* | Pro and Standard | Close-range projects without GPS; metric scale without full GCPs |

The first observation is the most important: **markers and
references are complementary**, not alternatives. A scene with
repeated geometry but accurate GPS is best handled by
[reference preselection with synthetic priors](synthetic-priors-reference-preselection.md);
a scene with no GPS but reachable surveyed targets is best
handled by markers.

## What happens with no reference data

> "If there's no information in the Reference pane and
> therefore no [R] or [T] mark next to the chunk's label in
> the Reference pane, then the chunk will remain unreferenced
> and all the coordinates and dimensions of the produced
> results would be in some arbitrary internal coordinate
> system."
> — Alexey Pasumansky, 2019-07-18, Metashape 1.5
> ([permalink](https://www.agisoft.com/forum/index.php?topic=11153.msg50187#msg50187))

So if you align without any reference (no GPS, no markers, no
scalebars), the result lives in a **chunk-internal arbitrary
frame**:

- `chunk.crs` is `None` (or an empty `CoordinateSystem()`).
- `chunk.transform.matrix` is the identity (or near-identity).
- `chunk.transform.scale` is 1.0; the unit is meaningless.
- The Reference pane's *Estimated* fields are blank.

**This is not first-camera-origin like COLMAP.** Unlike some
SfM tools that place the world origin at the first camera,
Metashape picks an internal frame chosen by the bundle solver
— typically near the centroid of the camera positions — with
arbitrary orientation. A common community observation is that
an exported mesh "lands at a seemingly random point in space"
relative to the world origin
([forum thread t=11120, daxils, 2019-07-09, Metashape 1.5](https://www.agisoft.com/forum/index.php?topic=11120.msg50096#msg50096));
that's expected behaviour, not a bug.

The chunk-internal scale being arbitrary has subtle
implications for distances and bundle conditioning; see
[The chunk's internal coordinate system: arbitrary scale and `chunk.transform.scale`](../../topics/scripting/chunk-internal-scale-and-units.md)
for the explanation.

You can still align, build dense products, and texture
without ever providing reference data. The chunk just has no
meaningful world-frame anchor — fine for many close-range and
artefact-scanning workflows.

## Markers as alignment aid

### Are markers and "manual tie points" the same thing?

**Yes.** Metashape has no separate "manual tie point" object
type; the mechanism for manual tie points IS the
`Metashape.Marker`. A marker without reference coordinates,
checked off in the Reference pane, with projections on two or
more images, behaves exactly as a manual tie point during
*Align Selected Cameras*.

> "You can use markers as manual tie points (they do not
> need to have any input coordinates in the Reference pane).
> Markers do not require to have their coordinates input in
> the Reference pane (and be checked on there). If marker
> has more than one projections, it will be used as a valid
> tie point during Align Photos or Align Selected Cameras
> operations."
> — Alexey Pasumansky, 2017-06-21, PhotoScan 1.3
> ([permalink](https://www.agisoft.com/forum/index.php?topic=7277.msg35040#msg35040);
> reaffirmed in [t=7977](https://www.agisoft.com/forum/index.php?topic=7977.msg37947#msg37947))

This matters for users coming from Pix4D or RealityCapture,
which have distinct *manual tie point* (MTP) concepts. In
Metashape, place a marker → don't tick its checkbox → you
have a manual tie point.

### Annotate before or after running Align Photos?

**After.** The standard workflow is:

1. Run *Align Photos* with [the canonical clean settings](diagnosing-under-aligned-chunks.md).
2. Identify cameras that didn't align (NA in the Workspace
   pane; `camera.transform is None` in Python).
3. Reset alignment for those specific cameras.
4. Place markers on each unaligned image, with each marker
   also visible on at least two **already-aligned** images.
5. Select the unaligned cameras → *Align Selected Cameras*.

> "Following this scenario you need to reset the alignment to
> incorrectly aligned cameras, place at least four markers on
> each of such photos (each marker should have at least two
> projections on correctly aligned images), then select these
> cameras and perform Align Selected operation."
> — Alexey Pasumansky, 2013-09-03, PhotoScan 1.0
> ([permalink](https://www.agisoft.com/forum/index.php?topic=1505.msg7674#msg7674))

This is documented step-by-step (with a worked GUI and Python
walkthrough) in
[Recovery paths for unaligned cameras → Path 2](recovery-paths-unaligned-cameras.md#path-2-marker-assisted-align-selected-pro-only).

The reason for "after, not before" is that markers serve as
**bridges between unaligned and aligned cameras** — they need
the aligned subset to anchor to. Placing markers before any
alignment runs means there's no anchor: every marker projection
is on a free-floating camera, and the bundle has nothing
fixed to solve against.

For the special case where the **whole project** fails to
align (no aligned subset to bridge to), the answer is rarely
markers. It's usually:

- **Repeated-geometry failure** → use synthetic position priors
  via reference preselection. See
  [Synthetic position priors via `ReferencePreselectionSource`](synthetic-priors-reference-preselection.md).
- **Symmetric-scene failure** → see
  [`alignChunks` cannot break geometric symmetry](alignchunks-symmetric-scene-failure.md);
  same priors-based remedy.
- **Insufficient overlap or motion blur** → the data needs
  to be recaptured. No marker recipe fixes a real overlap
  deficit.

### How do markers help?

A marker is a **manual tie point**: a 2D pixel position
clicked on one or more images that all observe the same 3D
scene point. The bundle adjustment treats marker projections
as **100% valid matches** — guaranteed-correct correspondences
that supplement (not replace) the automatic tie points found
by feature matching.

> "If there are no coordinates for markers they will not be
> used for camera alignment optimization. However, markers
> could be used for difficult datasets as 100% valid matches
> if 'Align selected' feature is used."
> — Alexey Pasumansky, 2012-10-18, PhotoScan 0.9
> ([permalink](https://www.agisoft.com/forum/index.php?topic=764.msg3576#msg3576))

> "Markers can be used as valid matching points between
> photos, but it works only for 'Align Selected Cameras'
> option. And you do not need to check them on in the Ground
> Control pane if the coordinate information is missing, just
> leave them unchecked."
> — Alexey Pasumansky, 2014-08-19, PhotoScan 1.0
> ([permalink](https://www.agisoft.com/forum/index.php?topic=2728.msg14454#msg14454))

Two scenarios worth distinguishing:

| Marker without reference coordinates | Marker with reference coordinates (GCP) |
|---|---|
| Acts only as a manual tie point during *Align Selected Cameras*. | Acts as a manual tie point AND as a 3D position constraint during *Optimize Cameras*. |
| Don't tick its checkbox in the Reference pane. | Tick its checkbox; the bundle will pull camera poses toward the surveyed coordinates. |
| Useful for: bridging unaligned cameras, repetitive-feature scenes. | Useful for: georeferencing, scale, accuracy validation, bridging unaligned cameras. |

A marker without coordinates is invisible to *Optimize
Cameras*. To get marker-driven bundle constraint, you need
either reference coordinates OR a scalebar that uses the
marker as an endpoint — see
[Scalebar distance error: per-scalebar values and RMS aggregation](../../topics/repeatability-qa/scalebar-error-statistics.md).

### How many markers do I need?

For recovering an unaligned camera: **at least 4 markers per
unaligned image**, each with at least 2 projections on
already-aligned images.

> "place at least four markers on each of such photos (each
> marker should have at least two projections on correctly
> aligned images)"
> — Alexey Pasumansky, 2013-09-03, PhotoScan 1.0
> ([permalink](https://www.agisoft.com/forum/index.php?topic=1505.msg7674#msg7674))

The "4" is the geometric minimum: a 6-DOF camera pose
(3 translation + 3 rotation) needs 4 non-coplanar 2D-3D
correspondences to solve via the Perspective-n-Point (PnP)
algorithm that backs *Align Selected Cameras*. Three markers
give an under-determined fit; four (non-coplanar) give a
unique solution; more than four over-determines and improves
robustness.

For chunk-wide recovery in repetitive-feature scenes, more is
better. One community user reports placing "dozens" of markers
without success in highly repetitive architecture
([t=1505 msg 7916](https://www.agisoft.com/forum/index.php?topic=1505.msg7916#msg7916));
in those cases the false matches outweigh the manual ones, and
either reference preselection or recapture is needed instead.

For **whole-project georeferencing** (rather than recovery),
fewer markers suffice — but their **spatial distribution**
matters more than the count:

> "You can use natural objects in scene instead of printed
> marks placed in advance. Two projections per marker (on
> aligned images) is minimal requirement, but I can suggest
> to put at least 4-5 projections, if you can distinguish
> the natural control point on the images. And you can have
> 10-15 different markers for the whole project, you do not
> have to place marker on every image in the dataset."
> — Alexey Pasumansky, 2020-12-07, Metashape 1.6
> ([permalink](https://www.agisoft.com/forum/index.php?topic=12852.msg56975#msg56975))

Three placement principles photogrammetric practice
generally agrees on (none specifically forum-attested but
inferable from the geometric requirements):

- **Spread across the project area.** Markers clustered in
  one corner constrain that corner well but leave the rest
  weakly anchored.
- **Vary elevation.** Markers all at the same Z don't
  constrain vertical scale; including some on raised
  surfaces (rooftops, hills, posts) breaks the
  focal-length / depth coupling that drives the
  [bowl effect](#bowl-dome-effect).
- **At least 4-5 projections per marker** improves bundle
  weighting beyond the 2-image triangulation minimum.

### Will automatic matches get more inliers from markers?

**No.** Markers don't improve the automatic feature matching;
they're additional constraints injected alongside the existing
tie points.

The automatic matcher's RANSAC inlier detection runs against
descriptor matches; it doesn't know about markers. Markers
become bundle observations that the *Align Selected* and
*Optimize Cameras* steps use, but the
[reprojection error analysis](../../topics/repeatability-qa/reprojection-error-analysis.md)
of automatic tie points is independent of marker placement.

This means: if the matcher couldn't find any matches for an
unaligned camera (because of motion blur, masking, exposure,
etc.), markers can recover the camera *without* the matcher
ever finding a match. The marker projections alone become the
valid correspondences for that camera.

### Markers have no automatic outlier detection — and what to do about it

A subtle but important asymmetry between markers and
automatic tie points:

- **Tie points** go through outlier rejection at two stages:
  RANSAC during pairwise feature matching, then *Gradual
  Selection* / reprojection-error filtering after the bundle
  runs. Bad matches are detected and dropped automatically.
- **Markers** are treated as **100% inliers** by the bundle.
  The bundle has no robust loss for marker observations and
  no automatic mechanism to recognise a misplaced
  projection or a mistyped reference coordinate.

A single misplaced marker projection or wrong GCP coordinate
can therefore propagate through the bundle and degrade the
solution for many cameras. This is forum-attested as a
real failure mode:

> "Reprojection error looks quite high in this project (maybe
> it is caused by optimization, basing on the incorrect
> markers) — usually mean value is about 1 pix, whereas here
> it is 5.5 pix."
> — Alexey Pasumansky, 2018-02-19, PhotoScan 1.4
> ([permalink](https://www.agisoft.com/forum/index.php?topic=8444.msg40226#msg40226))

Metashape's `Refine Markers` tool helps with auto-placed
projections but does not recognise reference-coordinate
errors. Manual visual inspection (sort the Reference pane by
Error, look for outliers) catches the obvious cases but
scales poorly past 20-30 markers.

**Prefer manual correction when it's tractable.** With a handful
of markers, the fastest and safest fix is to sort the Reference
pane by Error, inspect the worst offender, and decide *by eye*
whether it is a mis-clicked projection (re-place it, or *Remove
Projection*) or a wrong reference coordinate (fix the typed
value, or untick it). Automatic rejection is a convenience for
marker sets larger than the ~20–30 where visual triage stops
scaling — it is **not** a substitute for looking at a small
project, where a robust threshold estimated from only a few
markers is itself unreliable. Treat the script below as a
*reviewer that proposes* edits, not an autopilot.

When you do automate it, screen the residuals at the right
**granularity** — because a high marker error has two distinct
causes:

- A **mis-clicked image projection** on an otherwise-good marker.
  The tell-tale is one projection whose *reprojection error*
  (pixels) is far worse than that marker's other projections.
  Fix: drop that single projection; keep the marker.
- A **wrong reference coordinate** (mistyped GCP). The tell-tale
  is a marker whose projections are mutually consistent (low,
  uniform reprojection error) yet whose *3D error* (metres) stays
  high. Fix: disable that marker's reference; keep its
  projections contributing image geometry.

Rejecting the **whole marker** for either symptom is too blunt —
it throws away good image observations to remove one bad click,
or discards a usable image tie just because its typed coordinate
was wrong. So run two robust screens — iteratively reweighted
least squares (IRLS) on a median-absolute-deviation (MAD) scale
— at the two granularities, **projections first**:

1. **Per-projection screen** (pixel space). Compute every marker
   projection's reprojection error, threshold one-sided
   (`median + k × MAD`, `k = 3.5`), and drop the
   gross mis-clicks — never dropping a marker below two
   projections, which it needs to triangulate. Re-optimise; repeat.
2. **Per-reference screen** (object space). *After* the
   projections are clean — so a residual high error is no longer
   caused by a stray click — threshold the control markers' 3D
   errors and disable the wrong coordinates. Re-optimise; repeat.

This is the discrete-weight form of an *M-estimator* (a robust
estimator that bounds the influence of outliers): the Metashape
Python API doesn't expose per-residual bundle weights, so instead
of *down-weighting* a residual the loop *removes or disables* the
offending observation and re-fits — at the granularity where the
error originates (projection or reference).

> **Demo verified:** ✗ — pending Tier 3 reproduction on a real Metashape install.

```python
import statistics
from typing import Optional
import Metashape

def marker_3d_error_metres(marker, chunk):
    """Per-marker 3D error in metres: distance between the
    bundle-estimated and reference-supplied positions (in
    geocentric metres when georeferenced; chunk-local units
    otherwise). Returns None if the marker has no triangulated
    position, no reference coordinate, or the chunk has no
    transform yet."""
    if marker.position is None or marker.reference.location is None:
        return None
    T = chunk.transform.matrix
    if T is None:
        return None
    estimated_world = T.mulp(marker.position)
    if chunk.crs is not None:
        ref_world = chunk.crs.unproject(marker.reference.location)
    else:
        ref_world = marker.reference.location
    return (estimated_world - ref_world).norm()

def projection_reprojection_errors_px(chunk):
    """Yield (marker, camera, error_px) for every valid marker
    projection — the distance between the clicked pixel and the
    reprojection of the marker's estimated 3D position."""
    for m in chunk.markers:
        if m.position is None:
            continue
        for camera, proj in m.projections.items():
            if proj is None or not proj.valid:
                continue
            reprojected = camera.project(m.position)
            if reprojected is None:
                continue
            yield m, camera, (proj.coord - reprojected).norm()

def _mad_cutoff(values, k):
    """One-sided robust cutoff median + k * MAD (1.4826-scaled).
    Returns None when MAD ~ 0 (residuals already tight)."""
    median = statistics.median(values)
    mad = statistics.median(abs(v - median) for v in values) * 1.4826
    return None if mad < 1e-9 else median + k * mad

# Default bundle parameters; add fit_b1=True, fit_b2=True for
# stubborn bowl-like residual patterns.
_OPTIMIZE = dict(fit_f=True, fit_cx=True, fit_cy=True,
                 fit_k1=True, fit_k2=True, fit_k3=True,
                 fit_p1=True, fit_p2=True)

def detect_projection_outliers_irls(chunk, k_threshold=3.5,
                                    max_iterations=8, min_projections=2,
                                    optimize_kwargs=None, apply=False):
    """Per-PROJECTION screen. Dry run (default, apply=False) reports
    likely mis-clicks against the CURRENT bundle solution and changes
    nothing — run Optimize Cameras yourself first so the residuals are
    current. With apply=True it removes the single worst projection,
    re-runs Optimize Cameras, and repeats (so apply re-estimates
    intrinsics and discards any dense cloud / mesh / tiled model).
    Never drops a marker below min_projections. Returns
    [(marker_label, camera_label, error_px), ...]."""
    optimize_kwargs = optimize_kwargs or _OPTIMIZE
    flagged = []
    for it in range(max_iterations):
        if apply:
            chunk.optimizeCameras(**optimize_kwargs)   # refit after the previous removal
        errs = list(projection_reprojection_errors_px(chunk))
        if len(errs) < 4:
            print(f"iter {it}: too few projections ({len(errs)}) for a robust fit")
            break
        cutoff = _mad_cutoff([e for *_, e in errs], k_threshold)
        if cutoff is None:
            print(f"iter {it}: MAD ~ 0; projections are consistent")
            break
        remaining = {}
        for m, _c, _e in errs:
            remaining[m.key] = remaining.get(m.key, 0) + 1
        worst_first = sorted((t for t in errs if t[2] > cutoff), key=lambda t: -t[2])
        if not worst_first:
            print(f"iter {it}: no projection above {cutoff:.2f} px; converged")
            break
        if not apply:
            # Dry run: report every suspect against the current solution.
            for m, camera, e in worst_first:
                tag = ("" if remaining[m.key] > min_projections
                       else f"  [keep: only {remaining[m.key]} projections — inspect by hand]")
                print(f"flag {m.label}@{camera.label} (reproj {e:.1f} px > {cutoff:.1f}){tag}")
            break
        # Apply: remove only the single worst *removable* projection, then refit.
        removed = False
        for m, camera, e in worst_first:
            if remaining[m.key] <= min_projections:
                print(f"  KEEP {m.label}@{camera.label} ({e:.1f} px): removing it would "
                      f"drop below {min_projections} projections — inspect by hand "
                      f"(the reference coordinate may be the real fault)")
                continue
            print(f"iter {it}: REMOVE {m.label}@{camera.label} (reproj {e:.1f} px > {cutoff:.1f})")
            m.projections[camera] = None   # API equivalent of GUI 'Remove Projection'
            flagged.append((m.label, camera.label, e))
            removed = True
            break
        if not removed:
            print(f"iter {it}: nothing removable above cutoff; converged")
            break
    return flagged

def detect_reference_outliers_irls(chunk, k_threshold=3.5,
                                   max_iterations=8, min_markers=6,
                                   optimize_kwargs=None, apply=False):
    """Per-REFERENCE screen. Dry run (default) reports control markers
    whose 3D error is a robust outlier (likely a wrong/mistyped
    coordinate) against the CURRENT solution, changing nothing. With
    apply=True it disables the single worst marker's reference, re-runs
    Optimize Cameras, and repeats. Disabling keeps the marker's
    projections in the bundle and is reversible (reference.enabled =
    True). Run AFTER detect_projection_outliers_irls. Returns
    [(marker_label, error_m), ...]."""
    optimize_kwargs = optimize_kwargs or _OPTIMIZE
    flagged = []
    for it in range(max_iterations):
        if apply:
            chunk.optimizeCameras(**optimize_kwargs)
        errs = [(m, marker_3d_error_metres(m, chunk))
                for m in chunk.markers if m.reference.enabled]
        errs = [(m, e) for m, e in errs if e is not None]
        if len(errs) < min_markers:
            print(f"iter {it}: only {len(errs)} enabled control markers — too few for a "
                  f"robust threshold; correct these by hand instead")
            break
        cutoff = _mad_cutoff([e for _m, e in errs], k_threshold)
        if cutoff is None:
            print(f"iter {it}: MAD ~ 0; references are consistent")
            break
        worst_first = sorted(((m, e) for m, e in errs if e > cutoff), key=lambda t: -t[1])
        if not worst_first:
            print(f"iter {it}: no reference above {cutoff:.4f} m; converged")
            break
        if not apply:
            for m, e in worst_first:
                print(f"flag reference {m.label} (3D error {e:.4f} m > {cutoff:.4f})")
            break
        m, e = worst_first[0]
        print(f"iter {it}: DISABLE reference {m.label} (3D error {e:.4f} m > {cutoff:.4f})")
        m.reference.enabled = False
        flagged.append((m.label, e))
    return flagged

# Usage — DRY RUN first (default): both functions report against the
# CURRENT bundle solution and change nothing, so run *Optimize Cameras*
# yourself first. Review the two reports and fix the few that matter by
# hand where the project is small enough.
chunk = Metashape.app.document.chunk
print("== suspect projections (likely mis-clicks) ==")
detect_projection_outliers_irls(chunk)            # dry run, no mutation
print("\n== suspect references (likely wrong coordinates) ==")
detect_reference_outliers_irls(chunk)             # dry run, no mutation

# To apply automatically (projections FIRST, then references). NOTE: each
# apply pass re-runs Optimize Cameras — it re-estimates intrinsics and
# discards any dense cloud / mesh / tiled model — so run it before
# building those products, ideally on a duplicated chunk:
#   detect_projection_outliers_irls(chunk, apply=True)
#   detect_reference_outliers_irls(chunk,  apply=True)
```

Design rationale:

- **Dry run by default, and side-effect-free.** With `apply=False`
  both functions only *read* the current bundle solution and
  *print* candidates — nothing changes, so run *Optimize Cameras*
  yourself first to refresh the residuals. `apply=True` re-runs
  *Optimize Cameras* after each removal, which re-estimates
  intrinsics and discards any dense cloud / mesh / tiled model —
  run it before building those products, ideally on a duplicated
  chunk. Where the project is small, just fix the few offenders by
  hand; a person tells a genuine mis-click from a tight cluster
  faster than a threshold from a handful of markers can.
- **Projection removal is destructive.** Dropping a projection
  (`marker.projections[camera] = None`) deletes the manual click —
  there is no programmatic undo. Disabling a *reference* is
  reversible (set `reference.enabled = True` again), so the
  reference screen is the safer of the two to automate.
- **`k = 3.5`** sets a one-sided ~3.5σ-equivalent cutoff (in the
  spirit of Hampel-style rejection) — deliberately conservative,
  because here a false positive (rejecting a good observation) is
  worse than a false negative.
- **Minimum-count guards** (`< 4` projections; `< min_markers`
  control markers) stop each screen on small sets where MAD is
  poorly estimated — exactly the case where you should correct
  things by hand.
- **`min_projections = 2`** keeps every marker triangulable; a
  projection that can't be removed without breaching the floor is
  reported for manual inspection, because the real fault may be the
  reference coordinate rather than the click.
- **A grossly wrong GCP can bias the per-projection pass.** In
  `apply` mode the projection screen re-optimises with all
  references still enabled, so one badly mistyped coordinate warps
  the fit and can inflate other markers' reprojection errors. If
  the Reference pane shows a single enormous 3D outlier, fix or
  untick it by hand *before* running the projection screen.
- **Few references → low detectability.** A MAD screen can only
  flag a reference that *stands out* from the others; it has no
  notion of whether a reference is geometrically *checkable*. With
  few or weakly-distributed control points, a wrong coordinate can
  have so little redundancy that no screen — MAD or otherwise —
  can see it; the blunder is simply absorbed into the fit. The
  rigorous treatment (Baarda's w-test, redundancy numbers, the
  Minimal Detectable Bias, and the same standardised screen
  extended to **camera** position/rotation references) is in
  [Bundle-adjustment quality: variance factor, overfit testing, and reference detectability](../../topics/repeatability-qa/bundle-adjustment-quality.md).

For the per-projection and per-marker error statistics this builds
on (and the metre-vs-pixel framing), see
[Marker projection statistics: counts, per-marker errors, and metre-vs-pixel framing](../../topics/repeatability-qa/marker-projection-statistics.md).
For the chunk-local-vs-CRS frame mathematics behind
`marker_3d_error_metres` (the same `T.mulp(...)` /
`crs.unproject(...)` machinery), see
[Camera reference error: per-camera location and orientation residuals in Python](../../topics/repeatability-qa/camera-reference-error-python.md).
The GUI's *Remove Projection* — the manual equivalent of the
per-projection step — is covered in
[Gray flags in marker detection](../markers-gcps/gray-flags-marker-detection.md).

### GUI workflow for marker annotation

The fastest workflow for placing markers manually:

**Step 1 — Enter Edit Markers mode.**

Toolbar has a marker-edit-mode button (a flag icon). Toggle
it on. Without this, right-click context menus show the
*model-editing* commands instead of the *marker-editing*
commands.

**Step 2 — Open the photo and right-click the feature.**

Double-click a photo in the Workspace or Photos pane to open
it in the Photo view. Right-click on the desired marker
location:

- **Create Marker** (or *Add Marker* in older versions): adds
  a new marker. If a mesh exists, Metashape ray-casts from the
  camera centre through the 2D point onto the mesh, then
  back-projects the intersection onto every other photo —
  populating those photos with **blue (auto-placed)
  projections**.
- **Place Marker** → **(existing marker name)**: adds a
  projection of an *existing* marker to the current photo.
  Use this when the marker has already been created on
  another image and you're now placing its projection on the
  current image.

> "By right-clicking on the desired marker's position you'll
> see context menu — Create Marker option will add new marker
> on all the photos containing point's projection. Also you
> can use Place Marker option if you want to add another
> projection of existing marker to photo."
> — Alexey Pasumansky, 2012-01-17, PhotoScan 0.9
> ([permalink](https://www.agisoft.com/forum/index.php?topic=335.msg1353#msg1353))

**Step 3 — Refine the projection if needed.**

Drag a projection to refine its position. The flag changes
colour:

| Flag | Meaning | Used by bundle? |
|------|---------|-----------------|
| **Green** (pinned) | User-placed or user-refined | Yes |
| **Blue** (unpinned) | Automatically placed (via ray-cast or guided placement) | Yes |
| **Gray** (estimated) | Where the bundle *expects* the marker — purely informational | **No** — does not exist as a real projection |

> "Green flags indicate marker projection defined or refined
> by user. Blue flags — automatically placed projections.
> Grey flags shows the expected marker projection position
> according to the estimated camera positions and projections
> of the marker on other images. This is made for user
> convenience only and projections marked by grey flags do not
> really exist."
> — Alexey Pasumansky, 2015-02-04, PhotoScan 1.1
> ([permalink](https://www.agisoft.com/forum/index.php?topic=3371.msg17724#msg17724))

> "Both blue and green flags are considered. Blue (unpinned)
> markers usually are related to the automatically placed
> projections, whereas green (pinned) are those that are
> adjusted or placed by user manually."
> — Alexey Pasumansky, 2016-02-10, PhotoScan 1.2
> ([permalink](https://www.agisoft.com/forum/index.php?topic=4947.msg24735#msg24735))

A common mistake: assuming gray flags mean "marker is
visible here." They don't — the real projections are only the
green and blue ones. Gray is a UI hint for where you might
want to place the projection, nothing more.

**Step 4 — Pin projections on unaligned cameras before
running Refine Markers.**

If you place markers on cameras whose alignment is uncertain
and then run *Refine Markers*, the unpinned (blue) projections
on those uncertain cameras can disappear. Pin them first
(drag to confirm position; the flag goes green) so *Refine
Markers* leaves them alone.

> "Refine Markers option has no effect on the pinned markers
> (green flags), so you can manually adjust the positions of
> markers on the unaligned images converting them into pinned
> status."
> — Alexey Pasumansky, 2017-09-26, PhotoScan 1.3
> ([permalink](https://www.agisoft.com/forum/index.php?topic=7772.msg37143#msg37143))

For Python equivalents (programmatic marker creation, pinning,
and projection placement) see
[Programmatic marker placement and pinning](../markers-gcps/programmatic-marker-placement.md).

### Coded targets vs hand-placed markers

When markers are needed at scale, **printed physical targets**
are usually better than hand-placement after the fact. Two
families:

| Type | Detection | Best for |
|------|-----------|----------|
| **Coded targets** (12-bit, 14-bit, 16-bit, 20-bit, AprilTag) | Each target encodes its own ID; *Detect Markers* assigns labels automatically | High-GCP-count projects, surveyed coordinates pre-mapped to target IDs |
| **Non-coded circular targets** | Bare circular dots; *Detect Markers* finds them but labels are arbitrary indices (`point 1`, `point 2`, …) | Cost-sensitive projects; legacy capture sets without coded targets |
| **Hand-placed markers** | User clicks features in Photo view post-capture | Scenes with no physical targets — natural features only |

Coded targets remove the renaming step entirely:

> "Automatic marker detection gives default labels to the
> markers, so you need either to rename the found markers, or
> modify the file with the coordinates to fit the proper
> markers."
> — Alexey Pasumansky, 2016-12-10, PhotoScan 1.2
> ([permalink](https://www.agisoft.com/forum/index.php?topic=6258.msg30236#msg30236))

For non-coded targets with surveyed coordinates, the
*ignore labels* option in *Import Reference* matches each
detected marker to a coordinate row by spatial position
rather than label:

> "If you have a list of the targets, you can import
> reference data from CSV file using 'ignore labels'
> parameter, that should automatically compare the detected
> non-coded targets (distribution of the marker instances in
> space) with the distribution of the points in the CSV file
> and automatically assign the labels to the corresponding
> points."
> — Alexey Pasumansky, 2019-01-18, Metashape 1.5
> ([permalink](https://www.agisoft.com/forum/index.php?topic=10250.msg46776#msg46776))

For physical-target sizing rules, the printing workflow, and
the comparison between the four CircularTarget bit-counts,
see
[Coded circular targets: printing, sizing, and choosing a variant](../markers-gcps/coded-circular-targets.md).
For the AprilTag family added in 2.2, see
[AprilTag detection — choosing a variant](../markers-gcps/apriltag-detection.md).
For removing auto-placed projections that landed on the wrong
position, see
[Removing blue-flag marker projections](../markers-gcps/removing-blue-flag-marker-projections.md).

## Camera references as alignment aid

### Do I always need scale?

**No.** The bundle adjustment works fine in arbitrary internal
coordinates without any scale reference. Scale is required
only when you want real-world units in your output:

- DEM / orthomosaic exported in real-world coordinates.
- Measurements via the GUI's ruler / area / volume tools that
  return metres rather than dimensionless units.
- Multi-session consistency (same scale across separate
  scans).

A close-range project of a single artefact, with no
georeferencing requirements, can run from start to finish
without any scale reference. The mesh and orthomosaic are
produced in arbitrary units; downstream tools that don't care
about scale (3D printing at relative sizes, web viewers, etc.)
work fine.

When scale matters, you have three sources:

| Source | How it sets scale |
|--------|-------------------|
| **Two markers with surveyed coordinates** | Distance between the two coordinate values defines scale |
| **One scalebar with reference distance** | Distance between the two endpoints (markers or cameras) is constrained to the reference value |
| **GPS-tagged cameras with geographic coordinates** | The bundle is anchored in geocentric coordinates, scale follows |

The minimum is one constraint: a single scalebar with two
endpoints, OR two markers with known coordinates, OR three
GPS-tagged cameras (three points to define the world frame).

For the per-scalebar error mathematics see
[Scalebar distance error: per-scalebar values and RMS aggregation](../../topics/repeatability-qa/scalebar-error-statistics.md).

### Do I always need position AND orientation references?

**No, neither is required.** Position-only is the most common
case (EXIF GPS provides position; rotation is rarely
available). Rotation-only is rare but valid. Both are
optional, independent weighted constraints.

> "Camera rotation angle values loaded to the Reference pane
> will be used during the camera alignment and optimization
> operations with the certain weight defined by the
> corresponding measurement accuracy, providing that
> corresponding values are checked on in the Reference pane
> (coordinate information works in a similar way)."
> — Alexey Pasumansky, 2023-07-27, Metashape 2.0
> ([permalink](https://www.agisoft.com/forum/index.php?topic=15721.msg68018#msg68018))

> "Camera orientation angles are only taken into account if
> they are loaded to the Reference pane and when the Ground
> Altitude value is specified in the pane's preferences
> dialog."
> — Alexey Pasumansky, 2016-12-20, PhotoScan 1.2
> ([permalink](https://www.agisoft.com/forum/index.php?topic=6306.msg30457#msg30457))

Position alone is enough to enable *Reference Preselection*
(restricts matcher pair candidates by spatial proximity) and
to provide bundle constraints. Rotation alone, without
position, is unusual but technically valid — the bundle uses
the orientation prior, and your only world-frame anchor for
position is whatever else you provide (markers, scalebars).

### Do approximate references help?

**Yes.** Even very approximate references — accuracy in
hundreds or thousands of metres — provide value, as long as
the accuracy parameter is set to match the actual uncertainty.

> "You can use approximate X and Y values on input and define
> separate accuracy for XY coordinates (like hundreds or
> thousands of meters) and high accuracy on Z."
> — Alexey Pasumansky, 2021-02-03, Metashape 1.7
> ([permalink](https://www.agisoft.com/forum/index.php?topic=13047.msg57887#msg57887))

> "Probably you need to adjust the Camera Accuracy (m) value,
> as it is 10 meters by default. Maybe for the close range
> object you need to set it as 1 cm, or even lower."
> — Alexey Pasumansky, 2016-11-11, PhotoScan 1.2
> ([permalink](https://www.agisoft.com/forum/index.php?topic=6111.msg30095#msg30095))

The accuracy parameter does the work: a 1000-metre accuracy
tells the bundle "trust this position only loosely" and
weights the constraint accordingly. Two operational benefits
remain even when references are this rough:

1. **Reference preselection** filters matcher pair candidates
   to spatial neighbours. Even kilometre-scale priors usefully
   eliminate cross-region false matches in repetitive
   geometry. See
   [Synthetic position priors via `ReferencePreselectionSource`](synthetic-priors-reference-preselection.md)
   for the strict-mode workflow.

2. **Coarse world-frame anchor**. The bundle has *some* anchor
   to converge to, even if it's coarse. Without any references
   the bundle picks an arbitrary internal frame; with rough
   references it picks one consistent with the priors.

For the synthetic-priors workflow (where the priors don't
even come from real GPS — they're hand-clicked from a floor
plan), see
[Synthetic position priors via `ReferencePreselectionSource`](synthetic-priors-reference-preselection.md).

### Which reference preselection mode?

The *Align Photos* dialog and `Chunk.matchPhotos` API both
expose three reference-preselection modes. Each addresses a
different capture geometry:

| Mode | Pair candidates determined by | Best for |
|------|------------------------------|----------|
| **Source** | Loaded `camera.reference.location` values | GPS-tagged aerial / drone; synthetic priors |
| **Estimated** | Camera positions from a previous alignment | Second-pass refinement after a coarse alignment |
| **Sequential** | Camera label order (filename order) | Video frames or single continuous tracks |

> "Reference preselection in the actual version (1.2) uses
> the coordinate information trying to match the photos
> (using only certain number of neighbors according to the
> camera centers coordinates)."
> — Alexey Pasumansky, 2016-12-20, PhotoScan 1.2
> ([permalink](https://www.agisoft.com/forum/index.php?topic=6306.msg30457#msg30457))

For complex capture geometries (lawn-mower aerial patterns,
underwater scans, video sequences with cross-strip overlap),
a **two-pass approach** often outperforms a single mode:

> "If you are using 'space invader' scenario and have
> hundreds or thousands of images, it may be reasonable to
> align the data in two iterations: with sequential
> preselection and then with estimated preselection,
> providing that most of the cameras are properly aligned."
> — Alexey Pasumansky, 2020-09-12, Metashape 1.6
> ([permalink](https://www.agisoft.com/forum/index.php?topic=12553.msg55746#msg55746))

(*"Space invader"* is Agisoft community shorthand for a
lawn-mower flight pattern: parallel strips with cross-strip
overlap.)

The first pass (Sequential) anchors a per-track skeleton; the
second pass (Estimated, with `keep_keypoints=True`) finds
cross-track matches that the sequential pass missed. See
[Adding cameras to an aligned chunk: the `keep_keypoints` workflow](incremental-matching-keep-keypoints.md)
for the incremental-pass mechanics.

For the deep-dive on each mode see
[Pair preselection: choosing between Disabled, Generic, and Reference](pair-preselection-modes.md).

### Typical accuracy values

The Reference Settings dialog (Reference pane → Settings
button) takes accuracies for cameras, markers, scalebars, and
tie points. Forum-attested typical values:

| Source | Camera location accuracy (m) | Camera rotation accuracy (deg) | Notes |
|--------|------------------------------|-------------------------------|-------|
| Consumer drone GPS (DJI Phantom etc) | 10 (Metashape default) | n/a (no rotation usually) | Range typically 2.5 m — ∞; 10 is conservative |
| RTK drone (DJI Phantom 4 RTK etc) | 0.02 — 0.10 | 0.5 — 2 | DJI recommends 0.1 m per [*DJI with RTK coordinates data processing* (Agisoft KB)](https://agisoft.freshdesk.com/support/solutions/articles/31000161735) |
| PPK post-processed | 0.025 — 0.05 | 0.5 — 2 | Depends on baseline / fix |
| Smartphone GPS (no RTK) | 3 — 10 | n/a | EXIF varies wildly |
| No GPS at all | n/a (don't load reference) | n/a | Use markers / scalebars instead |

| Source | Marker location accuracy (m) | Marker projection accuracy (pix) |
|--------|------------------------------|----------------------------------|
| Total-station survey | 0.005 — 0.01 | 0.1 (Metashape default) |
| RTK rover | 0.01 — 0.05 | 0.1 |
| Hand-tape / approximate | 0.05 — 0.2 | 0.2 — 0.5 |
| Coded targets, well-lit | n/a (set per coordinate source) | 0.1 |

Per-axis accuracy is also possible (XY tighter than Z, for
example). In the GUI, type `0.01/0.05` to mean 0.01 m
horizontal and 0.05 m vertical. In Python:

> **Demo verified:** ✗ — pending Tier 3 reproduction on a real Metashape install.

```python
import Metashape

camera = Metashape.app.document.chunk.cameras[0]
# XY accuracy 1 cm, Z accuracy 5 cm — typical for surveyed projects
# where vertical precision lags horizontal.
camera.reference.location_accuracy = Metashape.Vector([0.01, 0.01, 0.05])
```

> "Camera accuracy (m) has to do with camera lat, lon, geotags
> embedded in headers or imported later. If they come from a
> regular on-board GPS, they are likely to be uncertain in the
> range from 2.5 to 'infinite' so 10 meters (default) is a
> flexible approach as a priori coordinates."
> — JMR, 2016-02-19, PhotoScan 1.2
> ([permalink](https://www.agisoft.com/forum/index.php?topic=4766.msg21024#msg21024))

For the per-scalebar accuracy field, ruler-measured distances
typically warrant `accuracy = 0.002 m` (2 mm); calliper-grade
goes lower; rough tape goes up to 0.01 m or more.

### GUI workflow for entering camera references

You don't need a CSV file to provide reference data. The
Reference pane (View → Reference) is the central UI:

**Step 1 — Open the Reference pane** and switch to the
**Source values** tab. The columns shown depend on what's
loaded; typically Label, X / Y / Z, and Accuracy.

**Step 2 — Type values directly into cells.**

> "According to the screenshot the Reference pane is
> displaying Source values that were loaded or input
> manually. Since you haven't input the coordinates of the
> camera positions to the Reference pane — the corresponding
> lines are empty."
> — Alexey Pasumansky, 2016-09-08, PhotoScan 1.2
> ([permalink](https://www.agisoft.com/forum/index.php?topic=5837.msg28390#msg28390))

Double-click a cell, type the value, press Enter. Repeat for
each camera or marker. For per-camera accuracy (different
from the chunk default), right-click the row → *Set
Accuracy…*.

**Step 3 — Or import from a CSV/TXT file.**

> "You can load the coordinate information for the camera
> locations to the Reference pane from the CSV/TXT file using
> Import button on the Reference pane toolbar. The input file
> should contain the image filename, x, y and z coordinate."
> — Alexey Pasumansky, 2020-09-19, Metashape 1.6
> ([permalink](https://www.agisoft.com/forum/index.php?topic=12581.msg55852#msg55852))

The Reference pane toolbar has an Import button (left side).
Pick the file, configure column mapping, OK. The values land
in the *Source values* tab, ready to be checked or edited.

**Step 4 — Tick the checkboxes.**

A loaded reference value is *not* used as a constraint until
its row is **checked** in the Reference pane. Untick to make
it a check point (post-hoc validation only).

> "For the reference preselection it does not matter, whether
> you have cameras checked on or unchecked in the pane — the
> coordinates from the source values tab of the Reference
> pane will be considered in any case."
> — Alexey Pasumansky, 2022-12-09, Metashape 2.0
> ([permalink](https://www.agisoft.com/forum/index.php?topic=15053.msg65810#msg65810))

So *Reference Preselection* uses the values whether ticked or
not (as long as they're in *Source values*); the bundle
adjustment uses them as constraints only when ticked. To
disable a value entirely (don't use as a check point either),
delete the row.

**Step 5 — *Reference → Update Transform*** to refresh the
estimated values once the bundle has run with the new
references.

### When do I need to run Update Transform?

*Update Transform* (the toolbar button on the Reference pane,
or `chunk.updateTransform()` in Python) computes the chunk's
seven-parameter transform (translation, rotation, scale) from
the currently checked reference data. The result is the
`chunk.transform.matrix` that maps chunk-internal coordinates
to world coordinates.

**Run *Update Transform* after any of these changes:**

- Adding or modifying marker / camera reference coordinates
  and ticking their checkboxes for the first time.
- Adding scalebars with reference distances.
- Editing the Reference Settings (Marker accuracy, Camera
  accuracy, etc.) — opening and closing the Settings dialog
  with OK also triggers an update.
- Unticking cameras to use only marker / scalebar
  references when the bundle was originally aligned with
  GPS-tagged cameras.

> "You can do it only once after all the marker projections
> are adjusted and the coordinates are input to the
> Reference pane. Under the same conditions (if nothing is
> changed in the project) there's no difference how many
> times you press Update Transform button."
> — Alexey Pasumansky, 2020-03-29, Metashape 1.6
> ([permalink](https://www.agisoft.com/forum/index.php?topic=12036.msg53833#msg53833))

> "Input coordinates for at least three markers that do not
> lay on the same line, check them on in the Reference pane
> and click Update Transform button on the pane's toolbar."
> — Alexey Pasumansky, 2023-11-21, Metashape 2.0
> ([permalink](https://www.agisoft.com/forum/index.php?topic=16013.msg68965#msg68965))

The "at least three non-collinear markers" rule is the
geometric minimum for a 2D-determinable rotation; for a full
7-parameter fit (X-Y-Z translation + 3 rotation + 1 uniform
scale), three non-collinear markers anchor the chunk
unambiguously. Two markers fix scale and the line between
them but leave a rotational degree of freedom; one marker
fixes only translation. (This is distinct from the 4-marker
minimum for marker-assisted *Align Selected Cameras*
covered above — that rule applies to bringing unaligned
cameras into the bundle, not to anchoring a chunk's world
frame.)

If the alignment ran with GPS-tagged cameras checked on,
*Update Transform* runs implicitly during *Align Photos* —
the chunk is already referenced when the alignment finishes.
Subsequent edits to references (adding GCPs, unticking
cameras, etc.) require a manual run.

### Update Transform vs Optimize Cameras

These are **two distinct operations** and confusing them is
the most common cause of "I changed reference data but the
results don't look right" support requests. The
distinguishing facts:

| Operation | What it does | Side effects on dense products |
|-----------|--------------|-------------------------------|
| **Update Transform** | Applies a 7-parameter similarity transform (translation, rotation, scale) to the chunk as a whole, to fit the checked reference data | Dense cloud / mesh / tiled model preserved; DEM and orthomosaic not deleted but should be **re-built** to reflect the new transform |
| **Optimize Cameras** | Full bundle adjustment refining intrinsic + extrinsic camera parameters per camera, with the checked reference data as constraints | **Discards** dense cloud, mesh, tiled model; DEM and orthomosaic must be re-built; intrinsics change |

> "You can georeference already reconstructed model, by
> loading reference coordinates for the cameras or markers.
> Then you just need to press Update button on the Reference
> pane toolbar after applying the coordinate information. In
> this case Affine transformations (Rotation, Translation
> and Scale) would be applied to the chunk as a whole to
> minimize the referencing errors. 'Update' would not have
> any effect on the already generated DEM and Orthomosaic,
> so they should be re-built anyway. Note that running the
> Optimize Cameras procedure would discard the generated
> dense cloud, mesh and tiled model."
> — Alexey Pasumansky, 2019-04-30, Metashape 1.5
> ([permalink](https://www.agisoft.com/forum/index.php?topic=10834.msg48943#msg48943))

> "During optimization PhotoScan performs full
> photogrammetric adjustment taking into account additional
> constraints introduced by ground control data. Extrinsic
> and intrinsic parameters for all cameras are optimized at
> this step, in contrast to the simple 7-parameter transform
> used for georeferencing by default. Thus optimization
> helps to significantly improve accuracy of the final
> solution."
> — Alexey Pasumansky, 2012-07-27, PhotoScan 0.9
> ([permalink](https://www.agisoft.com/forum/index.php?topic=600.msg2677#msg2677))

**The two are sequential, not mutually exclusive.** A typical
production workflow:

1. *Align Photos* (with GPS-tagged cameras ticked → implicit
   Update Transform happens at the end).
2. Add GCP markers, tick them in the Reference pane.
3. *Update Transform* — applies the similarity transform that
   includes the new GCP constraints; dense cloud (if any)
   is preserved (DEM / orthomosaic should be re-built).
4. *Optimize Cameras* — refines per-camera intrinsics; this
   step is **non-linear** and corrects bowl/dome effects
   that the similarity transform can't address.
5. Re-build dense cloud / DEM / orthomosaic.

If you only need to change which CRS your output is reported
in, *Update Transform* alone is enough. If the alignment is
geometrically wrong (bowl effect, ghosting, large
reprojection errors), *Optimize Cameras* is required and
downstream products will need rebuilding.

### Mixing reference sources

You can — and often should — combine GPS-tagged cameras with
GCP markers and scalebars in the same chunk:

- **GPS-tagged cameras**: provide approximate world-frame
  anchor + reference preselection benefit.
- **GCP markers**: refine the world-frame to GCP-survey
  precision; act as check points if unticked.
- **Scalebars**: enforce a measured distance constraint;
  useful for close-range projects where GPS isn't available
  but ruler-measured distances are.

All three appear in the Reference pane and can be
independently ticked or unticked. The bundle weighting is
controlled by the per-source accuracy values in
*Reference Settings*: lower accuracy values give the
constraint more weight.

> "Instances in the Reference pane that are used for scaling
> purposes should be checked on. And those that are assumed
> to be used for measurements should be unchecked."
> — Alexey Pasumansky, 2016-05-05, PhotoScan 1.2
> ([permalink](https://www.agisoft.com/forum/index.php?topic=5061.msg25163#msg25163))

**A common production pattern (GPS + GCPs + scalebars):**

1. **Initial alignment**: tick GPS-tagged cameras (uses GPS
   for reference preselection + coarse world-frame anchor).
2. **Add GCPs and scalebars**: place markers on coded targets,
   import surveyed coordinates, set scalebar reference
   distances. Tick the GCPs and scalebars in the Reference
   pane.
3. **Optimize Cameras**: untick the GPS cameras (or loosen
   `camera_accuracy` to match actual GPS uncertainty) so the
   bundle weights the surveyed GCPs more heavily. Keep
   scalebars ticked throughout.
4. **Validate**: untick a couple of GCPs to use them as check
   points; the residual on those check points is your
   external accuracy estimate.

There's no conflict between the three sources — they are
complementary, and the relative weighting follows from the
accuracy parameters set in *Reference Settings*.

## What if zero cameras align?

The recovery / decision flow above assumes *some* cameras
aligned. The harder case is **all cameras NA** — *Align
Photos* finishes but every camera shows NA in the Workspace
pane.

**Operational checklist for total alignment failure:**

1. **Check calibration / EXIF first.** Open *Tools → Camera
   Calibration*; verify focal length and pixel size are
   plausible. If EXIF was missing, input correct values
   manually before any re-align.
2. **Lower preselection strictness.** Disable pair
   preselection entirely on small datasets (< ~200 images);
   on larger datasets, switch from *Reference* to *Generic*
   preselection.
3. **Loosen tie-point limits.** Try `tie point limit = 10000`
   (default 4000) and `key point limit = 40000`.
4. **Re-run with the canonical clean settings**
   ([Diagnosing under-aligned chunks](diagnosing-under-aligned-chunks.md)
   rung 1).
5. **If still zero aligned**, the cause is almost certainly
   capture-side — insufficient overlap, motion blur,
   featureless content. No further parameter tuning will
   fix a real overlap deficit; recapture is the next step.

Each step is forum-attested:

> "The main problem is in lack of EXIF data for the
> images — there's no information about sensor pixel
> size, so PhotoScan initial calibration data may be
> incorrect."
> — Alexey Pasumansky, 2013-09-08, PhotoScan 1.0
> ([permalink](https://www.agisoft.com/forum/index.php?topic=1526.msg7833#msg7833))

> "I can suggest to increase tie point limit rather than
> key point limit, for example, up to 10 000. Also if you
> see that there are no tie points between the
> neighboring images you can try to Disable the pair
> preselection in the Align Photos dialog, if the
> dataset is not very big."
> — Alexey Pasumansky, 2016-07-11, PhotoScan 1.2
> ([permalink](https://www.agisoft.com/forum/index.php?topic=5585.msg27299#msg27299))

> "Without seeing the images themselves I can only say
> that the most common reasons of the alignment issues
> are lack of the image overlap and image quality (when
> too few tie points are detected on the images)."
> — Alexey Pasumansky, 2022-04-06, Metashape 1.8
> ([permalink](https://www.agisoft.com/forum/index.php?topic=14382.msg63242#msg63242))

## Bowl / dome effect

A characteristic alignment-quality artifact where the
reconstructed terrain curves upward (or downward) at the
edges of the project area, producing a bowl-shaped or
dome-shaped DEM that doesn't match reality. This is
distinct from the [DSM ridge-line artifact](../../topics/repeatability-qa/dsm-ridge-lines-diagnosis.md)
(which is local) — the bowl is a global, smooth curvature
that affects the entire reconstruction.

> "The bowl effect can be introduced during photo
> alignment, in case camera calibration estimates are
> inaccurate. If camera calibration is known in advance, it
> can be loaded in PhotoScan and fixed during photo
> alignment. But the recommended approach is to correct
> possible bowl effect during optimization procedure based
> on camera or GCP coordinates, performed after photo
> alignment."
> — Alexey Pasumansky, 2012-07-27, PhotoScan 0.9
> ([permalink](https://www.agisoft.com/forum/index.php?topic=600.msg2677#msg2677))

The cause is **focal-length under-determination** in nadir-only
aerial datasets: with all cameras pointing roughly downward,
the bundle has limited information to disambiguate "all
points are slightly closer + lens is slightly wider" from
"all points are at correct depth + lens is at the estimated
focal length." A small focal-length bias bends the
reconstruction into a bowl.

**Operational checklist for fixing the bowl:**

1. **Optimize Cameras with GCPs.** GCPs at varying ground
   elevations break the focal-length / depth coupling and
   straighten the reconstruction.
2. **If GPS-tagged cameras are the only reference** (no
   GCPs), tighten `camera_accuracy` to match the actual GPS
   uncertainty (default 10 m is too loose for RTK; set
   0.1 m for RTK drones, ~1-2 m for surveyed cameras).
3. **Enable additional corrections** in the Optimize
   Cameras dialog (the *Apply additional corrections*
   checkbox) for stubborn cases.
4. **Untick cameras during optimisation** if both GPS
   cameras and GCPs are present and the bowl persists with
   default weights:

   > "Please try to optimize the camera alignment after
   > unchecking all cameras in the Reference pane (while
   > having GCPs checked on). Use all parameters for
   > optimization except K4, P3 and P4, unless some of them
   > are suggested by default (and don't enable the
   > adaptive camera model fitting option)."
   > — Alexey Pasumansky, 2018-07-16, Metashape 1.4
   > ([permalink](https://www.agisoft.com/forum/index.php?topic=9244.msg43493#msg43493))

5. **Manual focal-length adjustment.** For severely bowed
   reconstructions, set the focal length manually in
   *Tools → Camera Calibration*, then re-run Optimize
   without F:

   > "The bowl-effect could be fixed with some manual
   > input, if you modify the adjusted parameters (mainly
   > the focal length) and optimize the alignment (without
   > F optimization), but it could require a few
   > iterations."
   > — Alexey Pasumansky, 2019-07-03, Metashape 1.5
   > ([permalink](https://www.agisoft.com/forum/index.php?topic=11068.msg52237#msg52237))

6. **Capture-side prevention**: include oblique imagery
   (camera-tilted shots) in addition to nadir. Convergent
   geometry is the structural cure for the
   focal-length-under-determination problem.

> "Yes, we assume that optimization will fix the
> 'bowl-effect' even GPS coordinates are not so accurate
> (about several meters)."
> — Alexey Pasumansky, 2012-07-27, PhotoScan 0.9
> ([permalink](https://www.agisoft.com/forum/index.php?topic=600.msg2893#msg2893))

So even if the only reference data is rough drone GPS
(several-metre accuracy), Optimize Cameras can correct the
bowl. The rough GPS isn't accurate enough to *georeference*
to survey precision, but it's enough to break the
focal-length / depth coupling.

## What if your reference data is wrong?

Sometimes the issue isn't that you lack reference data —
it's that your camera GPS is wrong (placeholder values like
`(0, 0, 0)`, drone EXIF written before satellite lock, RTK
fix lost mid-flight, etc.). Symptoms:

- All cameras stack at one location in the Reference pane.
- Estimated coordinates are wildly different from source.
- Reference Preselection produces no matches between
  spatially-distinct cameras.

> "To exclude the use of the image geotags for the model
> referencing I can suggest to perform the following:
> uncheck all cameras in the Reference pane (or just clear
> them), switch to local coordinates (or proper coordinate
> system that you will be using for the marker coordinates)
> option in the Reference pane setting dialog, right-click
> on the chunk's label in the Workspace pane and choose
> 'reset transform' option from the context menu."
> — Alexey Pasumansky, 2016-05-18, PhotoScan 1.2
> ([permalink](https://www.agisoft.com/forum/index.php?topic=5359.msg26355#msg26355))

The full operational sequence for bad GPS:

1. **Uncheck all cameras** in the Reference pane (don't
   tick), or **clear** their `camera.reference.location`
   values entirely if they're complete junk.
   - **GUI**: select all cameras in the Reference pane,
     right-click → *Reset Source* (or *Clear* in older
     versions). The cells empty out.
   - **Python**:
     `for c in chunk.cameras: c.reference.location = None`
   Note that *Reference Preselection* will still use the
   unchecked coordinates if they remain in *Source values* —
   so for placeholder values, **clear** them rather than
   just unticking.
2. **Switch to Local Coordinates** (or whatever CRS you'll
   use for markers later) in *Reference Settings*.
3. **Reset Transform** via right-click on the chunk's label
   in the Workspace pane.
4. Re-run alignment without reference preselection (or
   with *Generic* preselection only).
5. Add GCPs / scalebars later if metric scale is needed.

For the in-between case where GPS is **imprecise but not
junk**, set the accuracy value to match the actual
uncertainty — even per-axis, e.g.
`location_accuracy = Vector([5, 5, 30])` for "5 m horizontal,
30 m vertical" if you don't trust the drone's barometric
altitude.

## Decision tree

The tree below maps the user's situation to the recommended
response. Links point at the deep-dive recipe for each path.

- **Did the canonical clean-settings run already happen?**
  - No → Run [Diagnosing under-aligned chunks](diagnosing-under-aligned-chunks.md) rung 1 first.
  - Yes → continue.

- **Are SOME cameras aligned and you want to recover specific stragglers?**
  - Stragglers have feature matches to the aligned set →
    [Recovery paths Path 1: *Align Selected Cameras*](recovery-paths-unaligned-cameras.md#path-1-align-selected-cameras-cheapest-most-common).
  - Stragglers lack feature matches AND you have Metashape
    Pro →
    [Recovery paths Path 2: marker-assisted *Align Selected Cameras*](recovery-paths-unaligned-cameras.md#path-2-marker-assisted-align-selected-pro-only).
  - On Metashape Standard, OR markers failed
    (repetitive-feature scenes) →
    Recapture, OR use approximate position priors via
    [Synthetic position priors via `ReferencePreselectionSource`](synthetic-priors-reference-preselection.md).

- **Whole-project alignment failure (NO aligned subset)?**
  - Do you have approximate camera positions (GPS, floor
    plan, CAD)? → load them as Reference values, set accuracy
    generously, run a reference-preselection alignment via
    [Synthetic position priors via `ReferencePreselectionSource`](synthetic-priors-reference-preselection.md).
  - Repeated geometry / symmetry? → synthesise positions
    even if you don't have real ones (hand-click on a
    top-down reference image), then run as above. See
    [`alignChunks(method=point)` cannot break geometric symmetry](alignchunks-symmetric-scene-failure.md)
    for the diagnostic side.
  - Insufficient overlap or motion blur? → Recapture. No
    software fix replaces bad data.
  - Truly featureless content (blank walls, water)? →
    On Metashape Pro: add physical markers to the scene
    during capture, then place them in Metashape after
    running *Align Photos*. See *How many markers do I
    need?* above. On Metashape Standard: recapture with
    visual aids (textured panels, projected patterns) is the
    only option.

## Caveats

- **Markers without coordinates are invisible to *Optimize
  Cameras*.** They only act during *Align Selected Cameras*.
  If you want markers to also constrain the optimisation step
  (typical for surveyed projects), give them
  `marker.reference.location` values and tick them.
- **Markers are 100% inliers in the bundle — by default.**
  Unlike automatic tie points, markers have no robust loss
  and no automatic outlier rejection. A single misplaced
  projection or wrong reference coordinate can degrade the
  bundle for many cameras. For small projects, prefer fixing
  the obvious cases by hand — sort the Reference pane by Error,
  then re-place a mis-clicked projection or untick a wrong
  coordinate. For larger marker sets, the dry-run-first
  per-projection / per-reference recipe in *Markers have no
  automatic outlier detection* above proposes the same edits
  programmatically.
- **The 4-marker minimum is geometric, not arbitrary.** Three
  markers give an under-determined PnP fit; the bundle may
  converge to a wrong pose. Four non-coplanar is the minimum
  for a unique solution, and "non-coplanar" matters — four
  markers all on the same wall plane don't satisfy the
  requirement.
- **Reference Preselection in *Source* mode assumes cameras
  point roughly downward.** For typical aerial / nadir
  surveys with GPS-tagged cameras, *Source* mode is the
  default choice. For oblique / close-range projects with
  arbitrary camera orientations, *Estimated* mode (after a
  coarse alignment) or *Sequential* mode (consecutive video
  frames) is more appropriate — *unless* you're using
  synthetic priors specifically to defeat repeated geometry,
  in which case *Source* mode is correct because the priors
  exist precisely to gate matcher pair candidates by spatial
  proximity. See
  [Synthetic position priors via `ReferencePreselectionSource`](synthetic-priors-reference-preselection.md)
  for the strict-mode workflow.
- **`camera.reference.location_accuracy` is fixed input, not
  output.** Setting it to 0.01 m doesn't make the bundle
  produce 0.01 m results; it tells the bundle how tightly to
  trust the GPS value. Output quality is the
  [camera reference error](../../topics/repeatability-qa/camera-reference-error-python.md)
  you compute post-alignment.
- **Pinned (green) projections survive *Refine Markers*;
  unpinned (blue) projections do not necessarily survive.**
  Always pin manually-placed projections on uncertain cameras
  before running the refine pass.
- **`Align Photos` discards the existing alignment.** Even
  with markers placed, running *Align Photos* (rather than
  *Align Selected Cameras*) starts over. The marker recovery
  flow requires *Align Selected Cameras*.
- **Repetitive-feature scenes can defeat dozens of markers.**
  When the false matches in the existing tie-point graph
  reinforce the wrong pose, even many manual markers may not
  override. The remedy is reference preselection or
  recapture, not more markers.
- **Metashape Standard cannot use markers.** Markers are a
  Pro-only feature. Metashape Standard users with alignment
  problems have only the canonical-clean-settings re-run +
  reference preselection (if reference data exists) +
  recapture as options.
- **Camera orientation references need a Ground Altitude
  value.** Loaded `camera.reference.rotation` values are
  ignored by reference preselection unless the *Ground
  Altitude* parameter is set in the Reference Settings
  dialog. Without Ground Altitude, the orientation prior
  has no ground plane to project onto and the
  computed-footprint pair-selection logic falls back to
  position-only behaviour. The forum mention in
  [t=6306](https://www.agisoft.com/forum/index.php?topic=6306.msg30719#msg30719)
  is the only attested reference; the official manual
  doesn't expand on this. Set the value to the project's
  approximate ground elevation in the same units as the
  camera positions.

## See also

- [Diagnosing under-aligned chunks](diagnosing-under-aligned-chunks.md)
  — the diagnostic ladder you should run before reaching for
  markers or references.
- [Recovery paths for unaligned cameras](recovery-paths-unaligned-cameras.md)
  — the four operational paths (Align Selected; marker-
  assisted; transform import; cross-project transform import)
  for fixing stragglers in an otherwise-aligned project.
- [Synthetic position priors via `ReferencePreselectionSource`](synthetic-priors-reference-preselection.md)
  — the workflow for using approximate / synthetic position
  priors to defeat repeated-geometry failure modes.
- [`alignChunks` cannot break geometric symmetry](alignchunks-symmetric-scene-failure.md)
  — the broader symmetry-failure analysis; reference
  preselection is the recommended remedy.
- [Programmatic marker placement and pinning](../markers-gcps/programmatic-marker-placement.md)
  — the Python API for the marker workflow this article
  describes through the GUI.
- [Coded circular targets: printing, sizing, and choosing a variant](../markers-gcps/coded-circular-targets.md)
  — physical-target design and printing workflow for the
  CircularTarget family this article references.
- [AprilTag detection — choosing a variant](../markers-gcps/apriltag-detection.md)
  — the alternative target family added in Metashape 2.2.
- [The chunk's internal coordinate system: arbitrary scale and `chunk.transform.scale`](../../topics/scripting/chunk-internal-scale-and-units.md)
  — what "no reference data" actually produces under the hood.
- [Camera reference error: per-camera location and orientation residuals in Python](../../topics/repeatability-qa/camera-reference-error-python.md)
  — output-side error checking once your reference data is in.
- [Scalebar distance error: per-scalebar values and RMS aggregation](../../topics/repeatability-qa/scalebar-error-statistics.md)
  — for projects using scalebars instead of (or alongside) GCPs.

## References

- *Metashape Pro User Manual* (2.3), ch. 4 *Improving camera
  alignment*, *Reference pane and accuracy parameters* — the
  authoritative description of the Reference pane fields.
- *Metashape Python API Reference* (2.3.1):
  `Chunk.alignCameras`, `Chunk.cameras`, `Camera.transform`,
  `Camera.reference`, `Reference.location`,
  `Reference.location_accuracy`, `Reference.rotation`,
  `Reference.rotation_accuracy`, `Reference.enabled`,
  `Marker.position`, `Marker.projections`,
  `Marker.Projection.pinned`, `Chunk.markers`,
  `Chunk.scalebars`, `Chunk.transform`, `Chunk.crs`.
- Forum thread, [*Manual camera position?*](https://www.agisoft.com/forum/index.php?topic=1505.0)
  — Alexey Pasumansky, 2013-09-03, PhotoScan 1.0. The
  canonical 4-markers-per-photo recipe + repetitive-features
  caveat from community follow-up.
- Forum thread, [*tie points and optimization*](https://www.agisoft.com/forum/index.php?topic=764.0)
  — Alexey Pasumansky, 2012-10-18, PhotoScan 0.9. Markers as
  "100% valid matches" for *Align Selected Cameras* and the
  no-coordinates-don't-help-Optimize-Cameras distinction.
- Forum thread, [*Markers without coordinates*](https://www.agisoft.com/forum/index.php?topic=2728.0)
  — Alexey Pasumansky, 2014-08-19, PhotoScan 1.0. The
  Reference-pane-checkbox-not-required clarification for
  marker-as-tie-point usage.
- Forum thread, [*Marker projections*](https://www.agisoft.com/forum/index.php?topic=3008.0)
  — Alexey Pasumansky, 2014-10-22, PhotoScan 1.0. The
  ray-cast-onto-mesh mechanism for automatic marker
  projection placement (when *Create Marker* with a mesh
  present).
- Forum thread, [*Scaled model exporting*](https://www.agisoft.com/forum/index.php?topic=3371.0)
  — Alexey Pasumansky, 2015-02-04, PhotoScan 1.1. The
  green/blue/gray flag canonical definitions.
- Forum thread, [*guided marker placement — blue markers used in optimisation?*](https://www.agisoft.com/forum/index.php?topic=4947.0)
  — Alexey Pasumansky, 2016-02-10, PhotoScan 1.2. Both blue
  and green flags used in optimisation; how to deal with
  incorrect blue projections.
- Forum thread, [*Placed markers disappear from unaligned photos*](https://www.agisoft.com/forum/index.php?topic=7772.0)
  — Alexey Pasumansky, 2017-09-26, PhotoScan 1.3. Pinning
  projections before running *Refine Markers*.
- Forum thread, [*Extract and change the coordinate system*](https://www.agisoft.com/forum/index.php?topic=11153.0)
  — Alexey Pasumansky, 2019-07-18, Metashape 1.5. The
  "arbitrary internal coordinate system" definitive
  statement for unreferenced chunks.
- Forum thread, [*Constrained camera altitude but not horizontal position*](https://www.agisoft.com/forum/index.php?topic=13047.0)
  — Alexey Pasumansky, 2021-02-03, Metashape 1.7. Hundreds-
  or-thousands-of-metres-accuracy is fine for approximate
  references.
- Forum thread, [*Align with GPS coordinates: should images be checked or not?*](https://www.agisoft.com/forum/index.php?topic=15053.0)
  — Alexey Pasumansky, 2022-12-09, Metashape 2.0. Reference
  Preselection uses Source values regardless of ticked /
  unticked.
- Forum thread, [*Processing Smartphone Photos with Metashape*](https://www.agisoft.com/forum/index.php?topic=15721.0)
  — Alexey Pasumansky, 2023-07-27, Metashape 2.0. Position
  and rotation are independent optional weighted
  constraints; preselection in Source mode is for nadir
  surveys.
- Forum thread, [*Align images — Reference preselection*](https://www.agisoft.com/forum/index.php?topic=6306.0)
  — Alexey Pasumansky, 2016-12-20, PhotoScan 1.2. Camera
  orientation requires Ground Altitude in the pane's
  preferences; reference-preselection mechanism.
- Forum thread, [*Camera Pose Positions in UI and Exported Camera Poses*](https://www.agisoft.com/forum/index.php?topic=5837.0)
  — Alexey Pasumansky, 2016-09-08, PhotoScan 1.2. Reference
  values can be loaded OR input manually in the GUI.
- Forum thread, [*Use PPP corrected positions to overwrite image positions*](https://www.agisoft.com/forum/index.php?topic=12581.0)
  — Alexey Pasumansky, 2020-09-19, Metashape 1.6. The
  Import-button-on-Reference-pane-toolbar workflow for CSV /
  TXT bulk loading.
- Forum thread, [*Accuracy parameters in Reference Settings*](https://www.agisoft.com/forum/index.php?topic=4766.0)
  — JMR, 2016-02-19, PhotoScan 1.2.
  Field-by-field explanation of all Reference Settings
  values; typical ranges per source type.
- Forum thread, [*Adding (Manual) Tie Points in Photoscan*](https://www.agisoft.com/forum/index.php?topic=7277.0)
  — Agisoft support, 2017-06-21,
  PhotoScan 1.3. Markers without coordinates ARE manual
  tie points; no separate object type exists.
- Forum thread, [*Detect Markers (non coded) with survey coordinate*](https://www.agisoft.com/forum/index.php?topic=6258.0)
  — Agisoft support, 2016-12-10,
  PhotoScan 1.2. Coded targets get automatic labels;
  non-coded require renaming or *ignore labels* CSV import.
- Forum thread, [*Refine marker location with python scripts*](https://www.agisoft.com/forum/index.php?topic=10250.0)
  — Agisoft support, 2019-01-18,
  Metashape 1.5. The *ignore labels* CSV import strategy
  for non-coded targets matched by spatial distribution.
- Forum thread, [*Update Transform question*](https://www.agisoft.com/forum/index.php?topic=12036.0)
  — Agisoft support, 2020-03-29,
  Metashape 1.6. *Update Transform* runs once after
  reference data changes; idempotent thereafter.
- Forum thread, [*Detect markers*](https://www.agisoft.com/forum/index.php?topic=16013.0)
  — Agisoft support, 2023-11-21,
  Metashape 2.0. Three non-collinear markers minimum for
  *Update Transform*.
- Forum thread, [*Difficulties measuring using scale bars*](https://www.agisoft.com/forum/index.php?topic=5061.0)
  — Agisoft support, 2016-05-05,
  PhotoScan 1.2. Scaling vs measurement-only references
  (ticked vs unticked); mixing reference sources.
- Forum thread, [*Underwater orthomosaic with no GPS data*](https://www.agisoft.com/forum/index.php?topic=12553.0)
  — Agisoft support, 2020-09-12,
  Metashape 1.6. Two-pass alignment for video / underwater:
  Sequential first, then Estimated.
- Forum thread, [*Can't align photos*](https://www.agisoft.com/forum/index.php?topic=1526.0)
  — Agisoft support, 2013-09-08,
  PhotoScan 1.0. Missing EXIF / pixel-size as the most
  common total-failure cause.
- Forum thread, [*about the photo alignment*](https://www.agisoft.com/forum/index.php?topic=5585.0)
  — Agisoft support, 2016-07-11,
  PhotoScan 1.2. Tie-point-limit-up-to-10000 and
  disable-preselection-on-small-datasets recovery for
  total-failure cases.
- Forum thread, [*Photos failed to align*](https://www.agisoft.com/forum/index.php?topic=14382.0)
  — Agisoft support, 2022-04-06,
  Metashape 1.8. The "image overlap and image quality" as
  most-common-fundamental-cause framing.
- Forum thread, [*Strange artifacts on DEM (ridges and steps)*](https://www.agisoft.com/forum/index.php?topic=8444.0)
  — Agisoft support, 2018-02-19,
  PhotoScan 1.4. Confirms that "incorrect markers" can
  drive optimisation RMS up to 5.5 px (vs typical ~1 px);
  motivates the iterative-outlier-detection recipe in
  this article's "Markers have no automatic outlier
  detection" section.
- Forum thread, [*Projection error of a marker*](https://www.agisoft.com/forum/index.php?topic=5322.0)
  — Agisoft support, 2016-05-11,
  PhotoScan 1.2. The per-marker per-projection pixel-error
  formula
  (`(camera.project(marker.position) - projection.coord).norm()`)
  used in the per-projection IRLS screen of the
  outlier-detection recipe.
- Forum thread, [*The mysterious 'bowl effect'*](https://www.agisoft.com/forum/index.php?topic=600.0)
  — Agisoft support, 2012-07-27,
  PhotoScan 0.9. The canonical bowl-effect explanation:
  cause is inaccurate camera self-calibration during
  alignment; remedy is *Optimize Cameras* with reference
  data.
- Forum thread, [*add coordinates after build dense cloud*](https://www.agisoft.com/forum/index.php?topic=10834.0)
  — Agisoft support, 2019-04-30,
  Metashape 1.5. Update Transform vs Optimize Cameras: the
  former preserves dense products, the latter discards them.
- Forum thread, [*Bowl-shaped distortion in DEM*](https://www.agisoft.com/forum/index.php?topic=9244.0)
  — Agisoft support, 2018-07-16,
  Metashape 1.4. The "untick cameras / tick GCPs / Optimize
  with K1-K3, P1-P2, no adaptive" recipe for stubborn
  bowls.
- Forum thread, [*Underwater mapping model curved... help?*](https://www.agisoft.com/forum/index.php?topic=11068.0)
  — Agisoft support, 2019-07-03,
  Metashape 1.5. Manual focal-length adjustment + Optimize
  without F as a recovery for severely bowled
  reconstructions.
- Forum thread, [*ignore coordinate system*](https://www.agisoft.com/forum/index.php?topic=5359.0)
  — Agisoft support, 2016-05-18,
  PhotoScan 1.2. The "uncheck cameras / clear coordinates /
  switch to Local / Reset Transform" sequence for handling
  bogus GPS values.
- Forum thread, [*Placing markers without targets*](https://www.agisoft.com/forum/index.php?topic=12852.0)
  — Agisoft support, 2020-12-07,
  Metashape 1.6. Marker placement strategy: 10-15 markers
  for whole-project georeferencing, 4-5 projections per
  marker recommended.
- [*DJI with RTK coordinates data processing* (Agisoft KB)](https://agisoft.freshdesk.com/support/solutions/articles/31000161735)
  — official Agisoft guidance on RTK accuracy values and
  XMP loading; recommends 0.1 m camera accuracy for DJI
  P4 RTK.

