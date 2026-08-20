---
title: "Coded circular targets: printing, sizing, and choosing a variant"
status: unverified
applies_to: Metashape Pro 2.x — and PhotoScan / Metashape 1.x via the same `CircularTarget*` enum on the legacy `Metashape.TargetType` (and `PhotoScan.TargetType`). AprilTag detection is Metashape Pro 2.2+; see the AprilTag article.
edition: Pro
last_reviewed: 2026-06-05
diataxis: how-to
confidence: medium
---

# Coded circular targets: printing, sizing, and choosing a variant

> **Confidence:** *medium.* The four-family CircularTarget
> bit-count enumeration, the printing workflow, and the
> "12-bit decoded more precisely" claim are sourced from the
> official *Metashape Pro 2.3 User Manual* (p. 106–107). The
> sizing rules are forum-attested via a community user's
> empirical study; the 30-px upper limit is sourced from
> Agisoft's own *Coded Targets & Scale Bars in PhotoScan
> Pro 1.0.0* tutorial. The detection-angle behavior is
> partially attested but warrants further empirical work.
>
> The marker-separation, masquerade, and best-subset figures added
> below come from analyzing the decoded CircularTarget families with
> a rotation-invariant Hamming distance; worst-pair values are exact
> for the 12/14/16-bit families and greedy lower bounds for 20-bit.

## Problem

You need to place printed targets in a scene for one of:

- **Coordinate-system anchors** — coded targets give the
  bundle automatic, label-stable correspondences for
  georeferencing.
- **Scale anchors** — two coded targets at known distance
  define a scalebar.
- **Manual-tie-point fall-back** — coded targets are 100%
  valid matches that supplement automatic feature matching
  (see [Helping alignment when photos don't align](../alignment/helping-alignment.md)).

Coded *circular* targets — the family Metashape has supported
since PhotoScan 1.0 — are still the default choice for
close-range photogrammetry: cheap to print, sub-pixel
detection accuracy, automatic ID assignment.

This article covers the 12-bit / 14-bit / 16-bit / 20-bit
circular family specifically. For the AprilTag family added
in 2.2.0, see
[AprilTag detection — choosing a variant](apriltag-detection.md).

## What 12-bit circular coded targets are

The manual:

> "The following types of coded targets are detected in
> Metashape: Circular and AprilTag. […] Metashape supports
> four types of circle CTs: 12 bit, 14 bit, 16 bit and
> 20 bit. While 12 bit pattern is considered to be decoded
> more precisely, 14 bit, 16 bit and 20 bit patterns allow
> for a greater number of CTs to be used within the same
> project."
> — *Metashape Pro User Manual* 2.3, p. 107

A 12-bit circular target is a small printed pattern with:

- A solid black **central circle** (the centroid is the
  detected 2D point).
- A surrounding **ring** divided into black/white segments
  encoding 12 bits of identifier — yielding 161 unique
  codes after parity-check filtering in the current *Print
  Markers* output (561 for 14-bit, 2,001 for 16-bit, and
  26,013 for 20-bit).

The detection algorithm finds the central circle by ellipse
fitting (so the same target works at varying viewing
angles), then decodes the ring to recover the integer ID.

### Origin and patent

The 12-bit circular coded-target design is based on a method
described in:

> Schneider, C. T. (1991). "3-D Vermessung von Oberflächen
> und Bauteilen durch Photogrammetrie und Bildverarbeitung."
> *Proc. IDENT/VISION 91*, 14–17.

The corresponding German patent has expired, so the design
is freely usable. Independent open-source implementations of
related coded targets (including 14-bit) exist:

- [mpetroff.net analysis of photogrammetry targets](https://mpetroff.net/2018/05/photogrammetry-targets/)
  — historical and design comparisons of coded-target
  systems.
- [`14-Bit-Circular-Coded-Target` (natowi)](https://github.com/natowi/14-Bit-Circular-Coded-Target)
  — Python script to generate compatible 14-bit targets
  outside of Metashape.
- [`CCTDecode` (poxiao2)](https://github.com/poxiao2/CCTDecode)
  — open-source decoder for the same target family.

## Choosing a target family

| Variant | API enum (`Metashape.TargetType`) | Library size | When to use |
|---------|---|---|---|
| **12-bit circular** | `CircularTarget12bit` | 161 codes | Default close-range; single-chunk projects with a few dozen markers; "most precise" per manual |
| **14-bit circular** | `CircularTarget14bit` | 561 codes | Multi-chunk projects with up to a few hundred markers |
| **16-bit circular** | `CircularTarget16bit` | 2,001 codes | Industrial / many-target metrology (thousands of targets) |
| **20-bit circular** | `CircularTarget20bit` | 26,013 codes | Massive code-library needs (rare in practice) |
| **AprilTag** (Metashape 2.2+) | `AprilTag*` (7 variants) | varies by variant | Robotics-derived workflows; robust detection in cluttered scenes — see [AprilTag detection](apriltag-detection.md) |
| **Non-coded** (white circle / 4-segment) | — | n/a | Aerial / large-area projects where coded targets would be impractically large |

The exact code counts vary by Metashape version and the
parity-check scheme in effect; the manual's own description
("12 bit pattern is considered to be decoded more precisely,
14 bit, 16 bit and 20 bit patterns allow for a greater number
of CTs") implies the families differ by *order of magnitude*
in library size, which the table reflects.

To check the exact count for any variant on your installed
Metashape version, open *Tools → Markers → Print Markers…*,
select the variant, and count the targets in the generated
PDF. (For close-range projects with fewer than ~25 unique
markers, 12-bit is the default choice; for anything larger,
verify before printing.)

The manual's claim that 12-bit is decoded "more precisely"
relates to the lower bit-count's better signal-to-noise ratio
in the ring-decoding step — the parity-checked ring is
shorter and survives more degradation.

For non-coded targets, identity is assigned by spatial position
rather than an encoded ID — match them via *ignore labels* on
import, or by renaming detected markers after detection. For
automation-friendly defaults, 12-bit circular targets plus
AprilTag (when 2.2+ is available) cover the vast majority of
close-range and field-survey use cases. To refine the choice by
how many mutually-robust markers you need, see
[Which family for a given k?](#which-family-for-a-given-k)
below.

## Printing the targets in Metashape

The targets are generated by Metashape itself:

> **Demo verified:** ✗ — pending Tier 3 reproduction on a real Metashape install.

1. Open Metashape Pro (target generation is Pro-only).
2. *Tools → Markers → Print Markers…* opens the Print
   Markers dialog.
3. Pick the target type (12-bit, 14-bit, 16-bit, 20-bit, or
   AprilTag if on 2.2+) and choose a target size in
   millimeters.
4. *OK* writes a multi-page PDF; the first page contains all
   the unique codes.
5. Print the PDF on a paper / vinyl that won't reflect or
   warp; mount on rigid backing for field deployment.

The printed PDF is the canonical source — there's no need to
generate targets externally unless you need a non-default
layout (turntables, custom plates, embedded references). For
turntables specifically, the
[community JSFiddle target generator](https://www.reddit.com/r/photogrammetry/comments/8p5bim/jsfiddle_photoscan_coded_target_tool_updated_with/)
produces a printable circular layout; one open issue: the
default `count = Math.trunc(circ / (codeSize * 3))`
formula in the `turntable()` function over-spaces targets;
replace with `count = Math.trunc(circ / (codeSize + padding))`
for evenly-spaced rings.

## Optimal target size (forum-attested empirical guidance)

How big should the printed target be? The detection
algorithm has a minimum size below which the central circle
isn't reliably detected, and an upper limit above which it
becomes wasteful (or reduces the count of usable targets in
the field of view).

**Lower bound — minimum 9–10 pixel central circle.** A
community user's empirical study with 12-bit targets on
multiple cameras (DJI Phantom 4, GoPro Hero 4):

> "In order to be detected, the **center point of a
> PhotoScan 12-bit target** has to cover a minimum of
> **9–10 pixels on the image**. […] As the global diameter
> of the target is 3.5 times the diameter of the center
> point, the whole target should have a minimum size of
> 35 cm [for a 1 cm GSD]."
> — Yoann Courtois (community forum user), 2017-04-03,
> PhotoScan 1.3
> ([permalink](https://www.agisoft.com/forum/index.php?topic=2768.msg32898#msg32898))

**Upper bound — the central circle should not exceed 30
pixels.** From Agisoft's own *Coded Targets & Scale Bars in
PhotoScan Pro 1.0.0* tutorial, as quoted in the same forum
thread:

> "The central black circle-point on the taken photo is not
> greater than 30 pix."
> — Agisoft, *Coded Targets & Scale Bars* tutorial
> (PhotoScan Pro 1.0.0), via
> [forum thread t=2768](https://www.agisoft.com/forum/index.php?topic=2768.msg14648#msg14648)

So aim for **10–30 pixels** of central circle on the image,
with the **global target diameter ≈ 3.5× the central-circle
diameter**.

### Worked example — sizing for a known GSD

If your project's expected GSD is 1 cm:

| Quantity | Formula | Value |
|----------|---------|-------|
| Minimum central-circle diameter on image | `10 px` (forum-attested floor) | 10 px |
| Minimum central-circle diameter at GSD | `10 px × GSD` | `10 × 1 cm = 10 cm` |
| Minimum global target diameter | `3.5 × central diameter` | `3.5 × 10 cm = 35 cm` |
| Recommended print size of central circle | `~5 px × GSD` margin above floor | `~5 × 1 cm = 5 cm` (use as a working *radius* to leave headroom; resulting central *diameter* on print is ≥ 10 cm) |

If GSD is 2 mm (close-range artifact scanning), the central
circle becomes 2 cm and the global target ~7 cm — easy to
print on letter paper. If GSD is 5 cm (high-altitude aerial),
the global target balloons to 175 cm, which is impractical
to lay out — at which point the manual's recommendation
becomes relevant:

> "while [coded targets] generally prove to be useful in
> close-range imagery projects, aerial photography projects
> will demand too huge CTs to be placed on the ground, for
> the CTs to be detected correctly. Hence, for aerial
> photography projects it makes sense to consider non-coded
> targets implementation."
> — *Metashape Pro User Manual* 2.3, p. 107

## Detection-angle behavior

Detection from oblique angles is partially understood:

> "I didn't handle precise measurements but I can say the
> angle of view is not the main limitation in automatic
> detection. For UAV survey with nadiral images for example,
> the limit of detection will be the effective GSD on the
> target when the camera will fly away from the target
> position, and not the angle of view."
> — Yoann Courtois (community forum user), 2017-04-03,
> PhotoScan 1.3
> ([permalink](https://www.agisoft.com/forum/index.php?topic=2768.msg32898#msg32898))

In other words: the detector copes with oblique angles
reasonably well (the central-circle ellipse fit is
designed for it), but the **effective GSD on the target's
plane** is what drives detection success. A target viewed at
60° projects onto the image as an ellipse with the minor
axis foreshortened by `cos(60°) ≈ 0.5` while the major axis
is preserved. The ellipse's *minor-axis* length on image
falls below the 10-px minimum sooner than a nadir target
would; the ellipse-fit detector is robust to the
foreshortening up to the point where the minor axis is too
short to anchor the fit reliably.

This is an experimental area worth testing on your specific
camera + flight plan. Print targets at multiple sizes, capture
from multiple angles, measure the major and minor axes of
the central-circle ellipse on each image, and note the
detection threshold. The "10 px minor-axis floor" gives a
starting point, but no upper-bound for θ has been
forum-attested in the corpus.

## Marker ambiguity and the minimum Hamming distance

> **Explanation / reference (background).** The sections from here to
> *Binary code tables* explain *why* some markers get confused and
> provide the code data behind the recommendations. They go beyond the
> print-and-size how-to and the *Choosing a target family* table above;
> you need none of it to simply pick and print a family.

*The separation, masquerade, and best-subset figures in the sections
below come from analyzing the decoded CircularTarget families — the
patterns in the* Print Markers *PDFs — with a rotation-invariant Hamming
distance. Worst-pair (max-min) values are exact for the 12-, 14-, and
16-bit families and greedy lower bounds for 20-bit.*

Coded circular targets are not all equally distinguishable from one
another. Whether two markers can be confused is governed by a
**rotation-invariant Hamming distance**: the number of ring segments
that must be misread to turn one valid code into the other, *minimized
over every rotation* of the ring. A printed target can be photographed
at any orientation, so the relevant distance is the smallest one across
all `N` cyclic rotations:

```text
d(a, b) = min over r in 0..N-1 of  hamming( code_a, rotate(code_b, r) )
```

The **family floor** is the smallest `d(a, b)` over all pairs in the
library — the worst case for the whole family: how many segment errors
are needed before *some* pair collides.

**For the CircularTarget families the floor is 2.** Agisoft's families
apply no inter-marker distance optimization: the codes are simply the
valid parity-checked patterns, and the closest pairs sit only two
segments apart at their nearest relative rotation. Two consequences
follow:

- **A single-segment (1-bit) error is always safe.** No two distinct
  markers differ by only one segment, so one misread segment can never
  turn a valid marker into another valid marker — it produces an invalid
  pattern that the parity check rejects (the marker is dropped, not
  mis-identified).
- **A two-segment (2-bit) error can cause a silent mis-identification.**
  For the closest pairs (those at the floor distance of 2), two
  coincident segment errors — from blur, low resolution, a printing
  defect, or partial occlusion — can flip one valid marker into another
  valid marker. The detector then reports a confident, wrong ID.

This is the core robustness limitation of CircularTargets, and it is why
*which* markers you choose matters.

### Measuring the family floor

You can reproduce the floor from the printed family alone:

1. Decode each target in the *Print Markers* PDF to its `N`-bit integer
   (or read the published code tables — see *Binary code tables* below).
2. For every pair, compute `d(a, b)` as the minimum Hamming distance over
   the `N` cyclic rotations of one code.
3. The global minimum is the family floor; the per-pair values identify
   the closest (most confusable) pairs.

The pairwise distance is cheap to vectorize: for a 0/1 bit matrix `B`
with per-row popcounts `w`, `hamming(a, R*b) = w_a + w_b - 2*(B . (R*B)^T)`
for each rotation `R`, taking the elementwise minimum over the `N`
rotations.

## The masquerade (occlusion) effect

A subtler failure mode is **masquerade**: a *partially occluded* marker
decoding as a **different** valid marker.

A CircularTarget is read by fitting the central dot, then sampling the
surrounding ring segment by segment. When a marker sits in cluttered
surroundings — a dark object overlapping one side, a bright highlight,
debris — a contiguous arc of the ring can be forced to a single color
(all black or all white) while the central dot stays visible and the
target is still detected. If that occluded pattern happens to match
another valid code (under the same rotation-invariant identification),
the marker is silently read as a legitimate, *different* marker. When
both markers belong to your project, the result is a confident wrong
correspondence that is very hard to diagnose.

A pair `{i, j}` is **forbidden** when occluding some arc of `i` (any
start, any end, either color) makes it identify as `j`, or vice versa.
Because the CircularTarget floor is only 2, forbidden pairs are common:

| Family | Markers | Forbidden pairs | Share of all pairs |
|--------|--------:|----------------:|-------------------:|
| 12-bit | 161 | 1,652 | 12.8% |
| 14-bit | 561 | 9,414 | 6.0% |
| 16-bit | 2,001 | 49,523 | 2.5% |
| 20-bit | 26,013 | 1,174,354 | 0.35% |

Smaller families are denser in code space, so relatively more occlusions
land on another member. An *unconstrained* "most separated" set almost
always still contains forbidden pairs — the separation objective and the
occlusion objective are different — so masquerade avoidance has to be
requested explicitly.

### Detecting masquerade pairs

Identification reuses the decoder's own rotation-invariance, so no large
rotation tables are needed:

1. Reduce every marker's code to its **canonical form** — the minimum
   value over its `N` cyclic rotations — and build a lookup from
   canonical form to marker ID.
2. For each color (black, white) and each contiguous arc `(start, end)`
   with wraparound, occlude every marker at once (`code | arc_mask` for
   white, `code & ~arc_mask` for black), canonicalize the result, and
   look it up.
3. Wherever an occluded marker's canonical form matches a *different*
   marker, record the unordered forbidden pair.

## Choosing a well-separated, occlusion-robust subset

Most projects do not need the whole library — they need `k` markers.
"The first `k`" (targets 1...k) or a random subset is a poor choice:
those subsets sit at or near the family floor, so they include the most
confusable pairs. A deliberately chosen subset does markedly better at no
practical cost.

### The selection objective

The governing quantity is the **worst (smallest) pairwise distance in the
chosen set** — the closest pair is what drives a mis-read. So the "best"
`k`-subset is the one that **maximizes the minimum pairwise distance** (a
*max-min*, or maximum-minimum-distance, objective). When the family is
saturated and many subsets tie on the worst pair, a secondary objective —
maximize the *sum* of pairwise distances — breaks the tie by spreading
the picks out, minimizing *how many* pairs sit at the floor.

### The algorithm, in brief

- **Greedy farthest-point (a 2-approximation).** Seed with the two
  markers farthest apart, then repeatedly add the marker whose *minimum*
  distance to the already-chosen set is largest. This is the classic
  farthest-point heuristic (Gonzalez, 1985), within a factor of two of
  the optimal worst-pair distance; restarting from every seed and keeping
  the best result tightens it further.
- **Masquerade-free as a constraint.** Treat the forbidden (masquerade)
  pairs as edges of a graph and require the chosen set to be an
  **independent set** in it (no forbidden pair). In the greedy, drop a
  candidate's forbidden neighbors as the set grows. This is nearly free:
  it holds the same worst-pair score and costs only a few hundredths of a
  bit of mean separation.
- **Exact optimum (small / medium families).** The exact max-min for `k`
  markers equals the largest threshold `t` for which the graph of pairs
  at distance >= `t` contains a clique of size `k`. Solving maximum-clique
  on these threshold graphs (climbing up from the greedy lower bound, with
  a `(k-1)`-core prune) gives a proven optimum for the 12-, 14-, and
  16-bit families. The 20-bit family is too large to solve exactly, so its
  figures are greedy lower bounds.
- **Largest masquerade-free pool.** The largest subset with *no* forbidden
  pair is a maximum independent set in the forbidden graph, found exactly
  by integer linear programming (maximize the count subject to
  `x_i + x_j <= 1` for every forbidden pair).

### Which family for a given k?

More bits buy more separation. At `k = 20`, the best achievable worst-pair
distance is:

| Family | Sector | Library | Best worst-pair (max-min) | Normalized (/ N) |
|--------|-------:|--------:|--------------------------:|-----------------:|
| 12-bit | 30.0 deg | 161 | 2 (saturated, exact) | 0.17 |
| 14-bit | 25.7 deg | 561 | 4 (exact) | 0.29 |
| 16-bit | 22.5 deg | 2,001 | 4 (exact) | 0.25 |
| 20-bit | 18.0 deg | 26,013 | >= 6 (greedy bound) | 0.30 |

The **12-bit family is saturated at `k = 20`**: even the optimal subset
cannot exceed a worst pair of 2, so it cannot supply 20 mutually-robust
markers. 14-bit lifts the worst pair to 4 and is the **efficient
default** — near-best normalized separation with the largest sectors (so
the smallest printable marker for a given pixels-per-sector budget). 16-
and 20-bit give more absolute margin when your imaging can resolve the
finer ring. Rule of thumb: **pick the smallest `N` whose ring your imaging
can resolve; among those, more bits means more separation.** Detection and
centroid *precision* depend on the marker's pixel size (the central-dot
ellipse fit), not on bit count — more bits costs only ring-decoding
resolution, not measurement accuracy.

### Ready-to-use best 10-marker sets

The most-separated, **masquerade-free** 10-marker set per family.
Worst-pair = the smallest pairwise rotation-invariant Hamming distance
within the set (higher is more robust). Numbers are Metashape **target
numbers** (the 1-based *Print Markers* label order):

| Family | Target numbers | Worst-pair | Mean |
|--------|----------------|-----------:|-----:|
| 12-bit | 13, 30, 49, 52, 81, 94, 123, 146, 153, 157 | 4 | 4.89 |
| 14-bit | 31, 60, 63, 121, 206, 219, 378, 508, 549, 560 | 4 | 5.69 |
| 16-bit | 81, 402, 430, 561, 853, 1177, 1691, 1929, 1996, 2000 | 4 | 7.02 |
| 20-bit | 575, 2258, 9370, 13238, 20197, 21153, 24077, 25628, 25800, 26006 | 8* | 8.84 |

`*` The 20-bit worst-pair is a greedy lower bound (the family is too large
to verify exactly): treat "8" as ">= 6, probably 8" rather than a proven
optimum. For comparison, a *random* 10-marker subset of the 12-bit family
sits at worst-pair 2 (a confusable pair) versus 4 for the chosen set, and
contains masquerade pairs that the chosen set does not.

## Caveats

- **Library size limits.** The 12-bit family has 161 unique
  codes; if your project needs more markers than that, you'll
  run out of unique IDs (causing identity collisions) and must
  switch to 14-bit (561 codes), 16-bit (2,001), or 20-bit
  (26,013). More important than raw count is *separation*: see
  "Choosing a well-separated, occlusion-robust subset" above —
  the 12-bit family cannot supply 20 mutually-robust markers
  even though it has 161 codes. Plan target counts and
  separation before printing.
- **Mounting flatness matters.** A bent or curled target
  introduces ellipse-fitting bias in the central-circle
  detection. Mount targets on rigid panels (foamcore,
  aluminum, MDF) before deployment.
- **Lighting and contrast.** Uniform lighting across the
  target's surface is critical. Targets in deep shadow have
  reduced contrast at the ring boundaries; the parity-check
  may then fail and the target is silently dropped from
  detection.
- **Surface reflectance.** Glossy or reflective surfaces
  (laminated targets in direct sunlight) create specular
  highlights that confuse the detector. Matte vinyl or
  photo-quality matte paper outperforms glossy print.
- **Print accuracy.** The central circle's diameter and the
  ring widths must be reproduced accurately by the printer.
  Inkjet printers can drift by a few percent; for metrology
  use, verify printed target dimensions with a caliper
  against the dimensions specified in the *Print Markers*
  dialog.
- **Aerial impracticality at high GSD.** Per the manual, a
  35-cm-diameter target for 1-cm-GSD aerial work scales to
  175 cm at 5-cm GSD — impractical. Switch to non-coded
  targets (or pre-surveyed natural features) for high-GSD
  aerial work.
- **The 30-px upper bound is from a 2014-era tutorial.** The
  detection algorithm has improved since; the upper bound is
  almost certainly looser today, but no updated guidance has
  been forum-published. Treat 30 px as a soft ceiling for
  conservative target sizing.
- **Patent status varies by jurisdiction.** The German
  patent (Schneider 1991) has expired; equivalent patents in
  other jurisdictions may not have, depending on national
  filing dates. For commercial use, verify your local IP
  position before mass-producing 12-bit targets.

## Reference: marker pools and binary code tables

The following are reference data supporting the recommendations
above — the largest occlusion-safe marker pools per family, and the
raw binary codes.

### Safer marker pools: the maximum masquerade-free sets

If you would rather pick your own markers than copy a fixed list, draw
them from a **maximum masquerade-free pool** — the largest subset of a
family that contains *no* forbidden (masquerade) pair at all. Any subset
you then choose from such a pool is automatically free of occlusion
masquerade between its members. You still want to spread your choices out
for separation: these pools are saturated at worst-pair 2, so they remove
masquerade, not the need to choose a well-separated subset. It is safer to
pick your markers from these sets.

Each pool is the unique maximum independent set in its family's forbidden
graph:

- **12-bit: 79 of 161 markers** are masquerade-free together.
- **14-bit: 217 of 561 markers.**
- **16-bit: 809 of 2,001 markers.**

??? note "12-bit — 79 masquerade-free target numbers"

    ```text
    7, 11, 13, 14, 15, 22, 26, 28, 29, 30, 34, 36, 37, 38, 39, 40, 41, 42, 43,
    44, 49, 53, 54, 55, 56, 59, 60, 61, 62, 63, 64, 65, 66, 67, 68, 70, 71,
    72, 73, 74, 75, 76, 77, 78, 79, 81, 82, 83, 84, 85, 86, 88, 89, 95, 96,
    97, 98, 99, 100, 101, 102, 103, 105, 106, 107, 108, 109, 110, 111, 112,
    114, 115, 116, 117, 123, 124, 126, 127, 146
    ```

??? note "14-bit — 217 masquerade-free target numbers"

    ```text
    31, 62, 78, 85, 89, 91, 92, 93, 120, 134, 141, 145, 147, 148, 149, 161,
    168, 172, 174, 175, 176, 183, 187, 189, 190, 191, 194, 196, 197, 198, 199,
    200, 201, 202, 203, 204, 218, 230, 237, 241, 242, 243, 244, 254, 261, 265,
    266, 267, 268, 274, 278, 279, 280, 281, 283, 284, 285, 286, 287, 288, 289,
    290, 291, 292, 297, 304, 307, 308, 309, 310, 315, 318, 319, 320, 321, 323,
    324, 325, 326, 327, 328, 329, 330, 331, 332, 334, 337, 338, 339, 340, 342,
    343, 344, 345, 346, 347, 348, 349, 350, 351, 353, 354, 355, 356, 357, 358,
    359, 360, 361, 362, 364, 365, 366, 367, 368, 370, 371, 381, 386, 388, 389,
    390, 391, 394, 396, 397, 398, 399, 400, 401, 402, 403, 404, 405, 406, 407,
    408, 412, 413, 414, 415, 416, 418, 419, 420, 421, 422, 423, 424, 425, 426,
    427, 428, 429, 430, 431, 433, 434, 435, 436, 437, 438, 439, 440, 441, 442,
    443, 444, 445, 447, 448, 449, 450, 451, 452, 453, 454, 456, 457, 458, 464,
    465, 466, 467, 468, 469, 470, 471, 473, 474, 475, 476, 477, 478, 479, 480,
    481, 482, 483, 485, 486, 487, 488, 489, 490, 492, 498, 500, 501, 502, 503,
    505, 512, 530, 531, 532, 534
    ```

??? note "16-bit — 809 masquerade-free target numbers"

    ```text
    31, 47, 55, 59, 61, 62, 63, 94, 110, 118, 122, 124, 125, 126, 142, 150,
    154, 156, 157, 158, 165, 169, 171, 172, 173, 177, 179, 180, 181, 183, 184,
    185, 186, 187, 188, 217, 233, 240, 244, 246, 247, 248, 263, 270, 274, 276,
    277, 278, 285, 289, 291, 292, 293, 297, 299, 300, 301, 303, 304, 305, 306,
    307, 308, 322, 329, 333, 335, 336, 337, 344, 348, 350, 351, 352, 356, 358,
    359, 360, 362, 363, 364, 365, 366, 367, 375, 379, 381, 382, 383, 387, 389,
    390, 391, 393, 394, 395, 396, 397, 398, 402, 404, 405, 406, 408, 409, 410,
    411, 412, 413, 415, 416, 417, 418, 419, 420, 422, 423, 424, 426, 444, 458,
    465, 469, 471, 472, 473, 486, 493, 497, 499, 500, 501, 508, 512, 514, 515,
    516, 520, 522, 523, 524, 525, 526, 527, 528, 529, 530, 541, 548, 552, 554,
    555, 556, 563, 567, 569, 570, 571, 575, 577, 578, 579, 580, 581, 582, 583,
    584, 585, 592, 596, 598, 599, 600, 604, 606, 607, 608, 609, 610, 611, 612,
    613, 614, 617, 619, 620, 621, 622, 623, 624, 625, 626, 627, 629, 630, 631,
    632, 633, 634, 636, 637, 638, 640, 647, 654, 658, 660, 661, 662, 669, 673,
    675, 676, 677, 680, 682, 683, 684, 685, 686, 687, 688, 689, 690, 696, 700,
    702, 703, 704, 707, 709, 710, 711, 712, 713, 714, 715, 716, 717, 720, 722,
    723, 724, 725, 726, 727, 728, 729, 730, 732, 733, 734, 735, 736, 737, 739,
    740, 741, 743, 747, 751, 753, 754, 755, 758, 760, 761, 762, 763, 764, 765,
    766, 767, 768, 771, 773, 774, 775, 776, 777, 778, 779, 780, 781, 783, 784,
    785, 786, 787, 788, 790, 791, 792, 794, 798, 800, 801, 802, 803, 804, 805,
    806, 807, 808, 810, 811, 812, 813, 814, 815, 817, 818, 819, 821, 825, 826,
    827, 828, 829, 831, 832, 833, 835, 839, 840, 842, 863, 870, 874, 875, 876,
    877, 883, 887, 888, 889, 890, 893, 894, 895, 896, 897, 898, 899, 900, 901,
    902, 910, 917, 921, 922, 923, 924, 930, 934, 935, 936, 937, 940, 941, 942,
    943, 944, 945, 946, 947, 948, 949, 954, 958, 959, 960, 961, 964, 965, 966,
    967, 968, 969, 970, 971, 972, 973, 975, 976, 977, 978, 979, 980, 981, 982,
    983, 984, 986, 987, 988, 989, 990, 991, 993, 994, 995, 1003, 1007, 1008,
    1009, 1010, 1016, 1020, 1021, 1022, 1023, 1025, 1026, 1027, 1028, 1029,
    1030, 1031, 1032, 1033, 1034, 1038, 1042, 1043, 1044, 1045, 1047, 1048,
    1049, 1050, 1051, 1052, 1053, 1054, 1055, 1056, 1058, 1059, 1060, 1061,
    1062, 1063, 1064, 1065, 1066, 1067, 1069, 1070, 1071, 1072, 1073, 1074,
    1076, 1077, 1078, 1083, 1084, 1085, 1086, 1088, 1089, 1090, 1091, 1092,
    1093, 1094, 1095, 1096, 1097, 1099, 1100, 1101, 1102, 1103, 1104, 1105,
    1106, 1107, 1108, 1110, 1111, 1112, 1113, 1114, 1115, 1117, 1118, 1119,
    1124, 1125, 1126, 1127, 1128, 1129, 1130, 1131, 1132, 1134, 1135, 1136,
    1137, 1138, 1139, 1141, 1142, 1143, 1148, 1149, 1150, 1151, 1153, 1154,
    1155, 1160, 1173, 1174, 1175, 1176, 1177, 1178, 1179, 1180, 1181, 1182,
    1185, 1188, 1189, 1190, 1191, 1193, 1194, 1195, 1196, 1197, 1198, 1199,
    1200, 1201, 1202, 1204, 1205, 1206, 1207, 1208, 1209, 1210, 1211, 1212,
    1213, 1215, 1216, 1217, 1218, 1219, 1220, 1222, 1223, 1228, 1229, 1230,
    1232, 1233, 1234, 1235, 1236, 1237, 1238, 1239, 1240, 1241, 1243, 1244,
    1245, 1246, 1247, 1248, 1249, 1250, 1251, 1252, 1254, 1255, 1256, 1257,
    1258, 1259, 1261, 1262, 1267, 1268, 1269, 1270, 1271, 1272, 1273, 1274,
    1276, 1277, 1278, 1279, 1280, 1281, 1283, 1284, 1289, 1290, 1291, 1293,
    1294, 1299, 1311, 1312, 1313, 1315, 1316, 1317, 1318, 1319, 1320, 1321,
    1322, 1323, 1324, 1326, 1327, 1328, 1329, 1330, 1332, 1333, 1338, 1339,
    1340, 1341, 1342, 1343, 1344, 1346, 1347, 1348, 1349, 1350, 1352, 1353,
    1358, 1359, 1360, 1362, 1363, 1368, 1381, 1382, 1383, 1384, 1385, 1387,
    1388, 1393, 1394, 1395, 1397, 1398, 1403, 1416, 1417, 1422, 1458, 1460,
    1461, 1462, 1463, 1464, 1465, 1466, 1467, 1468, 1469, 1470, 1471, 1472,
    1475, 1476, 1477, 1478, 1479, 1480, 1481, 1482, 1483, 1484, 1485, 1486,
    1487, 1489, 1490, 1491, 1492, 1493, 1494, 1495, 1496, 1498, 1499, 1500,
    1501, 1503, 1508, 1509, 1510, 1511, 1512, 1513, 1514, 1515, 1516, 1518,
    1519, 1520, 1521, 1522, 1523, 1524, 1525, 1527, 1528, 1529, 1530, 1532,
    1537, 1538, 1539, 1540, 1541, 1543, 1544, 1545, 1546, 1548, 1553, 1555,
    1570, 1571, 1572, 1573, 1574, 1575, 1576, 1577, 1578, 1580, 1581, 1582,
    1583, 1584, 1585, 1586, 1587, 1589, 1590, 1591, 1592, 1598, 1599, 1600,
    1601, 1602, 1603, 1604, 1605, 1607, 1608, 1609, 1610, 1611, 1612, 1613,
    1614, 1616, 1617, 1618, 1619, 1625, 1626, 1627, 1628, 1630, 1631, 1632,
    1633, 1654, 1655, 1657, 1658, 1659, 1665, 1666, 1667, 1669, 1670, 1671,
    1742, 1743, 1745, 1746, 1766, 1772, 1774, 1929
    ```

### Binary code tables (12-bit and 14-bit)

Each marker's identity is an `N`-bit integer. Bit `s` (value `2**s`)
corresponds to ring **sector `s`**, at angle `s * 360/N` degrees
counter-clockwise from the 3-o'clock direction; a set bit is a black
segment. By convention sector 0 is always black, so every code is odd.
Because a printed target can be photographed at any orientation, the
marker's *identity* is rotation-invariant: rotating the physical target
cyclically shifts the bits, and the canonical identifier is the minimum
value over the `N` cyclic rotations of the code.

**Worked example (12-bit).** Target #1 has code `71` = `0000 0100 0111`
in 12 bits — sectors 0, 1, 2, and 6 are black. To recognize a rotated
capture, compare canonical forms (the minimum over the 12 cyclic shifts)
rather than the raw integer.

The integers below are listed in target-number order: the first value is
target #1, the second is target #2, and so on.

??? note "12-bit — 161 codes (target order)"

    ```text
    71, 75, 77, 83, 85, 89, 95, 99, 101, 105, 111, 113, 119, 123, 125, 135,
    139, 141, 147, 149, 153, 159, 163, 165, 169, 175, 177, 183, 187, 189, 195,
    197, 201, 207, 209, 215, 219, 221, 231, 235, 237, 243, 245, 249, 255, 275,
    277, 281, 287, 291, 293, 297, 303, 311, 315, 317, 325, 329, 335, 343, 347,
    349, 359, 363, 365, 371, 373, 377, 383, 399, 407, 411, 413, 423, 427, 429,
    435, 437, 441, 447, 455, 459, 461, 467, 469, 473, 479, 485, 489, 495, 503,
    507, 509, 585, 591, 599, 603, 605, 615, 619, 621, 627, 629, 639, 663, 667,
    669, 679, 683, 685, 691, 693, 703, 715, 717, 723, 725, 735, 751, 759, 763,
    765, 819, 821, 831, 845, 853, 863, 879, 887, 891, 893, 927, 943, 951, 955,
    957, 975, 983, 987, 989, 1003, 1005, 1013, 1023, 1365, 1375, 1391, 1399,
    1403, 1455, 1463, 1467, 1495, 1499, 1535, 1755, 1791, 1919, 1983, 2015
    ```

??? note "14-bit — 561 codes (target order)"

    ```text
    135, 139, 141, 147, 149, 153, 159, 163, 165, 169, 175, 177, 183, 187, 189,
    195, 197, 201, 207, 209, 215, 219, 221, 225, 231, 235, 237, 243, 245, 249,
    255, 263, 267, 269, 275, 277, 281, 287, 291, 293, 297, 303, 305, 311, 315,
    317, 323, 325, 329, 335, 337, 343, 347, 349, 353, 359, 363, 365, 371, 373,
    377, 383, 387, 389, 393, 399, 401, 407, 411, 413, 417, 423, 427, 429, 435,
    437, 441, 447, 455, 459, 461, 467, 469, 473, 479, 483, 485, 489, 495, 497,
    503, 507, 509, 531, 533, 537, 543, 547, 549, 553, 559, 561, 567, 571, 573,
    579, 581, 585, 591, 593, 599, 603, 605, 615, 619, 621, 627, 629, 633, 639,
    645, 649, 655, 657, 663, 667, 669, 679, 683, 685, 691, 693, 697, 703, 711,
    715, 717, 723, 725, 729, 735, 739, 741, 745, 751, 753, 759, 763, 765, 783,
    785, 791, 795, 797, 807, 811, 813, 819, 821, 825, 831, 839, 843, 845, 851,
    853, 857, 863, 867, 869, 873, 879, 881, 887, 891, 893, 903, 907, 909, 915,
    917, 921, 927, 931, 933, 937, 943, 945, 951, 955, 957, 965, 969, 975, 977,
    983, 987, 989, 999, 1003, 1005, 1011, 1013, 1017, 1023, 1093, 1097, 1103,
    1111, 1115, 1117, 1127, 1131, 1133, 1139, 1141, 1145, 1151, 1161, 1167,
    1175, 1179, 1181, 1191, 1195, 1197, 1203, 1205, 1209, 1215, 1223, 1227,
    1229, 1235, 1237, 1241, 1247, 1251, 1253, 1257, 1263, 1271, 1275, 1277,
    1303, 1307, 1309, 1319, 1323, 1325, 1331, 1333, 1337, 1343, 1351, 1355,
    1357, 1363, 1365, 1369, 1375, 1379, 1381, 1385, 1391, 1399, 1403, 1405,
    1419, 1421, 1427, 1429, 1433, 1439, 1443, 1445, 1449, 1455, 1463, 1467,
    1469, 1481, 1487, 1495, 1499, 1501, 1511, 1515, 1517, 1523, 1525, 1529,
    1535, 1587, 1589, 1593, 1599, 1607, 1611, 1613, 1619, 1621, 1625, 1631,
    1637, 1641, 1647, 1655, 1659, 1661, 1677, 1683, 1685, 1689, 1695, 1701,
    1705, 1711, 1719, 1723, 1725, 1737, 1743, 1751, 1755, 1757, 1767, 1771,
    1773, 1779, 1781, 1785, 1791, 1823, 1829, 1833, 1839, 1847, 1851, 1853,
    1865, 1871, 1879, 1883, 1885, 1895, 1899, 1901, 1907, 1909, 1913, 1919,
    1935, 1943, 1947, 1949, 1959, 1963, 1965, 1971, 1973, 1977, 1983, 1995,
    1997, 2003, 2005, 2009, 2015, 2021, 2025, 2031, 2039, 2043, 2045, 2343,
    2347, 2349, 2355, 2357, 2367, 2379, 2381, 2387, 2389, 2399, 2405, 2415,
    2423, 2427, 2429, 2451, 2453, 2463, 2469, 2479, 2487, 2491, 2493, 2511,
    2519, 2523, 2525, 2535, 2539, 2541, 2547, 2549, 2559, 2643, 2645, 2655,
    2671, 2679, 2683, 2685, 2709, 2719, 2735, 2743, 2747, 2749, 2767, 2775,
    2779, 2781, 2791, 2795, 2797, 2803, 2805, 2815, 2863, 2871, 2875, 2877,
    2895, 2903, 2907, 2909, 2919, 2923, 2925, 2931, 2933, 2943, 2967, 2971,
    2973, 2983, 2987, 2989, 2995, 2997, 3007, 3021, 3027, 3029, 3039, 3055,
    3063, 3067, 3069, 3279, 3287, 3291, 3293, 3303, 3307, 3309, 3317, 3327,
    3383, 3387, 3389, 3407, 3415, 3419, 3421, 3431, 3435, 3437, 3445, 3455,
    3483, 3485, 3495, 3499, 3501, 3509, 3519, 3541, 3551, 3567, 3575, 3579,
    3581, 3701, 3711, 3741, 3755, 3757, 3765, 3775, 3797, 3807, 3823, 3831,
    3835, 3837, 3903, 3925, 3935, 3951, 3959, 3963, 3965, 3999, 4015, 4023,
    4027, 4029, 4055, 4059, 4061, 4075, 4077, 4085, 4095, 5463, 5467, 5483,
    5503, 5547, 5567, 5599, 5615, 5623, 5627, 5823, 5855, 5871, 5879, 5883,
    5983, 5999, 6007, 6011, 6063, 6071, 6075, 6107, 6143, 7023, 7031, 7095,
    7167, 7679, 7935, 8063, 8127
    ```

## See also

- [AprilTag detection — choosing a variant](apriltag-detection.md)
  — the alternative target family added in Metashape 2.2.
- [Helping alignment when photos don't align: markers, references, and what to use when](../alignment/helping-alignment.md)
  — the broader decision framework for when to use coded
  targets, hand-placed markers, or reference priors.
- [Programmatic marker placement and pinning](programmatic-marker-placement.md)
  — Python API for `chunk.detectMarkers()` and per-marker
  manipulation.
- [Gray flags in marker detection: what they mean and how to remove them](gray-flags-marker-detection.md)
  — flag-color semantics during automated detection.
- [Removing "blue flag" marker projections cleanly](removing-blue-flag-marker-projections.md)
  — managing auto-placed projections after a detection
  pass.
- [Marker projection statistics: counts, per-marker errors, and metre-vs-pixel framing](../../topics/repeatability-qa/marker-projection-statistics.md)
  — post-detection accuracy reporting.

## References

- *Metashape Pro User Manual* 2.3 (and Standard edition),
  p. 106–107, *Working with coded and non-coded targets*. The
  authoritative description of the four CircularTarget
  variants, the AprilTag family, the *Print Markers* workflow,
  and the precision / library-size tradeoff.
- *Metashape Python API Reference* (2.3.1):
  `Metashape.TargetType.CircularTarget12bit`,
  `CircularTarget14bit`, `CircularTarget16bit`,
  `CircularTarget20bit`, plus the AprilTag variants;
  `Chunk.detectMarkers(target_type=…)`.
- Forum thread, [*The size of coded markers for UAV
  acquisition*](https://www.agisoft.com/forum/index.php?topic=2768.0)
  — the canonical sizing thread; a community-user reply
  (2017-04-03, PhotoScan 1.3) provides the empirical
  9-10 px minimum central circle, 3.5× ratio for global
  diameter, and angle-of-view-secondary-to-effective-GSD
  finding.
- Schneider, C. T. (1991). "3-D Vermessung von Oberflächen
  und Bauteilen durch Photogrammetrie und Bildverarbeitung."
  *Proc. IDENT/VISION 91*, 14–17. The original
  coded-target design publication; corresponding German
  patent has expired.
- [Photogrammetry targets: an overview (Petroff, 2018)](https://mpetroff.net/2018/05/photogrammetry-targets/)
  — independent analysis of coded-target families in
  Metashape and other photogrammetry tools.
- [`14-Bit-Circular-Coded-Target` (natowi, GitHub)](https://github.com/natowi/14-Bit-Circular-Coded-Target)
  — Python script that generates Metashape-compatible
  14-bit circular coded targets outside of the *Print
  Markers* dialog.
- [`CCTDecode` (poxiao2, GitHub)](https://github.com/poxiao2/CCTDecode)
  — open-source decoder for circular coded targets in the
  same family as Metashape's CircularTarget.
- [Photoscan coded-target turntable JSFiddle (community)](https://www.reddit.com/r/photogrammetry/comments/8p5bim/jsfiddle_photoscan_coded_target_tool_updated_with/)
  — generator for round-table target plates; replace the
  default `count = Math.trunc(circ / (codeSize * 3))` line
  with `count = Math.trunc(circ / (codeSize + padding))`
  for even target spacing on each ring.

- Garrido-Jurado, S., et al. (2014). "Automatic generation and detection
  of highly reliable fiducial markers under occlusion." *Pattern
  Recognition* 47(6), 2280-2292. Background on occlusion-robust fiducial
  design and marker confusability.
- Garrido-Jurado, S., et al. (2016). "Generation of fiducial marker
  dictionaries using mixed integer linear programming." *Pattern
  Recognition* 51, 481-491. Optimizing a marker dictionary for
  inter-marker distance.
- Gonzalez, T. F. (1985). "Clustering to minimize the maximum intercluster
  distance." *Theoretical Computer Science* 38, 293-306. The farthest-point
  heuristic underlying max-min subset selection.
- [*Coded targets and Scale bars* (Agisoft KB)](https://agisoft.freshdesk.com/support/solutions/articles/31000148855)
  — Agisoft's basic workflow for printing, placing and
  auto-detecting circular coded targets and building scale bars
  from the detected markers.

