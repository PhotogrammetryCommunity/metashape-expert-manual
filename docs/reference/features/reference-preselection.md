# Reference preselection

> **Status:** documented (2026-05-24). Synthesises
> forum-attested mechanism + introspection-confirmed API
> surface. The Sequential-mode ±24-frame window is
> empirically verified on Metashape 2.2.3 (2026-07-10).

## What it is

*Reference preselection* is an option of *Match Photos* / *Align
Photos* that uses the cameras' reference-pane coordinates (or
estimated coordinates from a prior alignment, or sequential
image order) to pick which image pairs the matcher should
consider. Without preselection — or with `generic_preselection`
alone — the matcher considers every camera against every other,
which scales O(N²) and quickly becomes the dominant cost on
large surveys.

The mechanism, attested verbatim (PhotoScan 1.2 era):

> "Reference preselection in the actual version (1.2) uses the
> coordinate information trying to match the photos (using only
> certain number of neighbors according to the camera centers
> coordinates) also the Generic preselection method is applied
> to those neighbors. [...] In the next version we've made the
> Generic and Reference option separated adding new
> preselection mode (reference without generic)." —
> Alexey Pasumansky, 2016-12-20, PhotoScan 1.2
> ([permalink](https://www.agisoft.com/forum/index.php?topic=6306.msg30457#msg30457))

In other words, reference preselection is a **two-stage**
process in modern Metashape:

1. **Coordinate-based shortlist.** Pick the N nearest
   neighbours of each camera by reference-pane coordinates.
2. **Optional generic preselection on the shortlist.** If
   `generic_preselection=True`, run the additional
   feature-based pair selection within the shortlist.

The 1.3-era separation introduced
`ReferencePreselectionMode` as an enum so that callers could
opt into reference-only preselection (no generic) when the
references are trustworthy enough that feature-based pair
filtering becomes redundant overhead.

## Where it lives

| | Standard | Pro |
|---|---|---|
| **GUI** | *Workflow → Align Photos* → check *Reference preselection* | (same) |
| **Python** | `Metashape.Chunk.matchPhotos(reference_preselection=True, reference_preselection_mode=…)` | (Pro only) |
| **Available since** | PhotoScan 1.2 | PhotoScan 1.2 |
| **Mode-enum separation** | PhotoScan 1.3+ | PhotoScan 1.3+ |

## The three preselection modes

`Metashape.ReferencePreselectionMode` enumerates three sources
for the coordinate-based shortlist (introspection-confirmed on
Metashape 2.2.2):

| Mode | What it uses | Typical scenario |
|------|-------------|------------------|
| `ReferencePreselectionSource` (default) | The values in `camera.reference.location` (and `.rotation`, if loaded). These are the user-supplied / EXIF-derived reference coordinates. | Drone surveys with GPS-tagged images; aerial flights where every image has a position. |
| `ReferencePreselectionEstimated` | The values in `camera.transform` from a *previous* alignment. Not the reference-pane values. | Re-running matching after an initial alignment, where the bundle-adjusted positions are more accurate than the GPS reference. |
| `ReferencePreselectionSequential` | Image-order pairs: each camera *i* with the **24 preceding and 24 following** frames (a fixed ±24 window — see below). No coordinates required. | Video frames, drone fast-flights where the ordered sequence approximates spatial proximity, time-lapse from a moving rig. |

The default is `ReferencePreselectionSource` — the user manual's
expected behaviour for a typical aerial workflow.

## Python API

```python
import Metashape

chunk = Metashape.app.document.chunk

# Default: reference preselection ON, mode = Source.
chunk.matchPhotos(
    downscale=1,
    generic_preselection=True,        # run generic on the shortlist
    reference_preselection=True,
    reference_preselection_mode=Metashape.ReferencePreselectionSource,
    keypoint_limit=40000,
    tiepoint_limit=4000,
)

# Reference-only mode (no generic on the shortlist).
chunk.matchPhotos(
    reference_preselection=True,
    reference_preselection_mode=Metashape.ReferencePreselectionSource,
    generic_preselection=False,        # disable generic; trust the references
    ...
)

# Estimated mode — for a second matching pass after initial alignment.
chunk.matchPhotos(
    reference_preselection=True,
    reference_preselection_mode=Metashape.ReferencePreselectionEstimated,
    keep_keypoints=True,
    reset_matches=False,
    ...
)

# Sequential mode — for video / time-ordered captures.
chunk.matchPhotos(
    reference_preselection=True,
    reference_preselection_mode=Metashape.ReferencePreselectionSequential,
    ...
)
```

## When to enable / disable

### Enable reference preselection when
- Camera positions are reliable (drone GPS, surveyed positions,
  laboratory-known geometry).
- The dataset is large enough that O(N²) all-pairs matching
  would be slow (typically > ~200–500 images).
- You want to constrain the bundle to spatially-plausible
  matches, reducing the chance of false-match catastrophes
  (e.g., two images of the same texture in different parts of
  the scene becoming spuriously matched).

### Disable reference preselection when
- Camera positions are missing, wildly inaccurate, or
  unavailable. Reference preselection with bad references
  prunes correct pairs → forces alignment to fail.
- You're debugging an alignment failure (per the canonical
  "clean" recipe; see [Diagnosing under-aligned chunks](../../workflow/alignment/diagnosing-under-aligned-chunks.md))
  — disabling preselection lets the matcher find pairs
  generic-preselection identifies as similar even when the
  references would have excluded them.
- The dataset has a deliberately-symmetric layout where
  reference preselection would mistakenly identify
  geometrically-symmetric viewpoints as candidate matches
  (see [Synthetic priors and `ReferencePreselectionSource`](../../workflow/alignment/synthetic-priors-reference-preselection.md)).

## How wide is the "neighbour" search

The default neighbour-count for the coordinate-based shortlist
is not exposed as a Python kwarg. The PhotoScan 1.2-era
description above is "a certain number of neighbors" without
specifying the number; subsequent forum discussion (and the
GUI's `Reference accuracy` setting indirectly) suggests the
search radius scales with the user-supplied
`location_accuracy`. A camera with `location_accuracy = 50 m`
will be matched against more candidates than one with
`location_accuracy = 1 m`.

A follow-up reply raised the open question of how robust the
algorithm is to mis-localised priors:

> "I had a hunch it might do that after it aligned some images
> in a previous project where the coordinates were completely
> wrong in some parts." — James, 2016-12-20, PhotoScan 1.2
> ([permalink](https://www.agisoft.com/forum/index.php?topic=6306.msg30456#msg30456))

The thread doesn't resolve the question. Empirically, reference
preselection with bad coordinates can either fail outright (no
candidate pairs include the correct match) or succeed
serendipitously (correct match happens to be in the shortlist
anyway). The diagnostic is to disable reference preselection
and re-run; if alignment improves, the references are bad.

### Sequential mode: a fixed ±24-frame window

The coordinate-based shortlist above applies to `Source` and
`Estimated` modes. **Sequential** mode is different: it ignores
coordinates entirely and pairs each image with a *fixed* window
of its neighbours in label (filename) order.

A synthetic-pattern experiment on **Metashape 2.2.3** pins that
window at **±24**: each image is matched with the **24 preceding
and 24 following** frames — up to 48 neighbours per image. The
window **wraps around the ends of the sequence**: the user manual
states that *"the first with the last images in the sequence will
also be compared"*, so the sequence is treated as a loop and even
the first and last frames get the full ±24 window (pairing with
frames at the opposite end) rather than a truncated one.

*Method.* Build image sequences that repeat the first *p* unique
frames, so two identical frames sit exactly *p* apart, then run
`matchPhotos(generic_preselection=False, reference_preselection=True,
reference_preselection_mode=ReferencePreselectionSequential)`.
A frame only matches an identical copy when that copy falls
inside the window, i.e. when *p* ≤ window. Average tie-point
projections per image stayed high (~73) for every period *p* from
5 through 24 and collapsed to **exactly zero** at *p* = 25 and
above — locating the one-directional reach at 24.

> **Verified:** ✓ empirically (synthetic
> repeating-pattern sequences, generic preselection disabled,
> `filter_stationary_points=False`). The window is not exposed as
> a `matchPhotos` kwarg and may differ in other versions —
> re-measure if the exact value matters for your pipeline.

The verification script is a self-contained binary search: it
generates random-noise patterns, repeats the first *p* of them, and
detects the match cliff — [**download `measure_sequential_window.py`**](measure_sequential_window.py):

??? example "Show the verification script (`measure_sequential_window.py`)"

    ```python
    --8<-- "reference/features/measure_sequential_window.py"
    ```

## Generic preselection on top of reference preselection

When both `reference_preselection=True` and
`generic_preselection=True` are set, the documented behaviour
is two-stage:

1. Reference preselection picks N candidates by coordinate
   proximity.
2. Generic preselection runs feature-based pair selection
   *within those N candidates*.

The combined cost is `O(N · k)` where N is the dataset size
and k is the per-camera shortlist size — much less than the
all-pairs `O(N²)` cost of generic alone.

When references are reliable, the combined mode is the right
default. When references are unreliable, **disable reference
preselection**, not just generic — generic-on-a-bad-shortlist
will still miss the correct matches that the bad reference
shortlist excluded.

## Caveats

- **Reference preselection does NOT use rotation by default.**
  Attested verbatim: "Camera orientation angles
  are only taken into account if they are loaded to the
  Reference pane and when the Ground Altitude value is
  specified in the pane's preferences dialog." Most aerial
  workflows leave rotation out of the preselection because
  the GPS-only references don't carry orientation; a strapdown
  IMU dataset with full pose references can opt in.
- **Sequential mode is for ordered captures.** It assumes
  consecutive images are spatially close. A randomly-shuffled
  image set with `ReferencePreselectionSequential` produces
  garbage pair selections. It matches a **fixed ±24-frame
  window** (24 preceding + 24 following frames, cyclic),
  independent of any coordinates or `location_accuracy` — see
  above.
- **Estimated mode requires a prior alignment.** Calling
  `matchPhotos(reference_preselection_mode=…Estimated)` on a
  fresh chunk with no prior `alignCameras` raises an error:
  there are no estimated transforms to use.
- **The coordinate-shortlist neighbour count (`Source` /
  `Estimated` modes) is not user-tunable via Python.** The
  internal logic depends on
  `camera.reference.location_accuracy` and the dataset's
  density. To force a wider search radius, increase the
  `location_accuracy` value (or set it to a Vector with the
  desired uncertainty); to force a narrower search, decrease
  it. (Sequential mode does not use this logic; its window is
  fixed — see above.)
- **Reference preselection is the default; disabling it is the
  unusual choice.** Most production aerial workflows will not
  touch this setting. Disable it only when diagnosing
  alignment problems (per the "clean" recipe) or when
  references are demonstrably unreliable.

## Related concepts

- [Generic preselection](generic-preselection.md) — the
  feature-based pair-selection method that runs on the
  reference-preselection shortlist, or on its own.
- *Guided matching* — a separate option that adds matches at a
  later stage of alignment, not at pair-selection time.
- [Tie points](../glossary.md#tie-point-cloud)

## Articles in this manual

- [Diagnosing under-aligned chunks](../../workflow/alignment/diagnosing-under-aligned-chunks.md)
  — the canonical "clean" alignment recipe explicitly
  recommends *Reference preselection: disabled* as the
  alignment-debugging baseline.
- [Synthetic priors via `ReferencePreselectionSource`](../../workflow/alignment/synthetic-priors-reference-preselection.md)
  — uses `Source` mode with synthetic (centroid-pointing)
  priors to bootstrap alignment on repeated-feature scenes.
- [`alignChunks(method=PointBased)` cannot break geometric
  symmetry](../../workflow/alignment/alignchunks-symmetric-scene-failure.md)
  — recommends `reference_preselection=True,
  reference_preselection_mode=ReferencePreselectionSource`
  *before* `alignChunks` to prune the cross-chunk pair pool.

## Forum threads worth reading

| Date | Version | Author | Thread | One-line takeaway |
|------|---------|--------|--------|-------------------|
| 2016-12-20 | PhotoScan 1.2 | Alexey Pasumansky | [Align images - Reference preselection](https://www.agisoft.com/forum/index.php?topic=6306.msg30226#msg30226) | The canonical mechanism: coordinate-based shortlist + generic on the shortlist. The 1.3 separation introduces "reference without generic" mode. |
| 2016-12-20 | PhotoScan 1.2 | James | [Align images - Reference preselection](https://www.agisoft.com/forum/index.php?topic=6306.msg30227#msg30227) | Open question on robustness with bad coordinates; the thread doesn't resolve it. |

