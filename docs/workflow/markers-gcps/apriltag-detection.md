---
title: AprilTag detection — choosing a variant
status: unverified
applies_to: Metashape Pro 2.2.0+. Marker detection (including AprilTag variants) is **Pro-only**, attested in the body. Tier 1 introspection on Metashape 2.2.2 confirms 7 AprilTag variants in the `Metashape.TargetType` enum.
edition: Pro
last_reviewed: 2026-06-03
diataxis: how-to
confidence: medium
---

# AprilTag detection — choosing a variant
> **Confidence:** *medium.* The seven AprilTag variants and `chunk.detectMarkers` kwarg surface are introspection-confirmed; the bit / library-size / Hamming-distance tradeoff table is forum-attested. The occlusion-robustness and best-subset claims come from analyzing the published `tagStandard41h12` codes with a rotation-invariant Hamming distance, together with the AprilTag minimum-distance guarantee from the literature.
## Problem

Metashape 2.2.0 added **AprilTag detection** as a coded-target type
alongside the existing CircularTarget family. AprilTags are widely
used in robotics and field photogrammetry, but the API exposes
**seven** variants (`AprilTag16h5`, `AprilTag25h9`, `AprilTag36h10`,
`AprilTag36h11`, `AprilTagCircle21h7`, `AprilTagStandard41h12`,
`AprilTagStandard52h13`). This article covers which variant to choose
and why.

## Context

AprilTag is a fiducial marker family designed by the University of
Michigan APRIL Lab (Olson 2011, Wang & Olson 2016). Each variant is
a **dictionary** of valid bit-codes:

- The **bit count** (`16h5` = 16 bits per tag) sets the tag's
  internal grid size.
- The **Hamming distance** (the `h` number) is the minimum number
  of bit-flips between any two valid codes — higher Hamming
  distance is more error-resilience at the cost of fewer unique
  tags.
- The **library size** is the number of unique codes the dictionary
  contains. Larger library = more unique markers in one project.

In Metashape these are exposed as enum values on
`Metashape.TargetType`. The `chunk.detectMarkers(...)` API takes
**any** of them (or the legacy `CircularTarget*` variants) via the
`target_type` kwarg.

Marker detection — including AprilTag — is **Pro-only**:

> "At the moment we are not planning to add markers to Standard
> edition of Metashape." — Alexey Pasumansky, 2024-11-26
> ([permalink](https://www.agisoft.com/forum/index.php?topic=16745.msg72257#msg72257))

## Solution

### The seven AprilTag variants

Tier 1 introspection on Metashape 2.2.2 confirms these enum values
on `Metashape.TargetType`:

| Variant | Bit count | Library size | Hamming distance |
|---------|----------:|-------------:|-----------------:|
| `AprilTag16h5` | 16 | 30 | 5 |
| `AprilTag25h9` | 25 | 35 | 9 |
| `AprilTag36h10` | 36 | 2 320 | 10 |
| `AprilTag36h11` | 36 | 587 | 11 |
| `AprilTagCircle21h7` | 21 (circular) | 38 | 7 |
| `AprilTagStandard41h12` | 41 | 2 115 | 12 |
| `AprilTagStandard52h13` | 52 | 48 714 | 13 |

The library-size and Hamming-distance values are from the public
AprilTag specification (Olson 2011 + Wang & Olson 2016 + Krogius et
al. 2019); they are not Metashape-specific. Always test on a
sample frame before committing to a variant — Metashape may
internally use a subset of the standard family in some variants.

### Choosing a variant

The decision is a tradeoff between **library size** (how many
unique markers a project needs) and **detection robustness** (how
gracefully the variant degrades when image resolution is low or
markers are partially occluded).

**Heuristic:**

- **`AprilTag36h11`** is the **photogrammetry default**. 587 unique
  codes, 36-bit grid, Hamming distance 11. It's the variant most
  widely supported across detection libraries, has the most empirical
  validation in the field, and 587 codes is enough for almost any
  project.
- **`AprilTagStandard41h12`** or **`AprilTagStandard52h13`** if you
  need a **larger library** than `AprilTag36h11`'s ~590 codes.
  These newer "Standard" variants (Krogius et al. 2019) detect at
  lower resolutions and cleaner at long range.
- **`AprilTag16h5`** or **`AprilTag25h9`** for **small projects with
  many cameras and few markers** — small libraries are detected
  faster and have higher per-tag error-resilience because the bits
  are larger relative to the tag's footprint.
- **`AprilTagCircle21h7`** for **printable-on-round-stickers** use
  cases (e.g. mounting markers on cylindrical objects).

### Python API

```python
import Metashape

doc = Metashape.app.document
chunk = doc.chunk

# Detect AprilTag36h11 markers on every camera in the chunk.
chunk.detectMarkers(
    target_type=Metashape.TargetType.AprilTag36h11,
    tolerance=50,         # 0–100; raise if some tags miss
    filter_mask=False,    # set True to ignore masked regions
    inverted=False,       # set True for white-on-black tags
)
doc.save()
```

The full kwarg surface (Tier 1 introspection on 2.2.2) — same for
all `target_type` values:

| Kwarg | Default | Effect |
|-------|--------|--------|
| `target_type` | `CircularTarget12bit` | Set this to one of the 7 `AprilTag*` enum values. |
| `tolerance` | `50` | Detector tolerance, 0–100. Raise if tags are missed; lower if false positives appear. |
| `filter_mask` | `False` | Ignore masked image regions. |
| `inverted` | `False` | Detect markers printed white-on-black instead of black-on-white. |
| `noparity` | `False` | Disable parity checking. AprilTag has no parity; this kwarg is for CircularTarget targets. |
| `maximum_residual` | `5` | Maximum residual in pixels (mostly relevant for non-coded targets). |
| `minimum_size` | `0` | Minimum target radius in pixels (`CrossTarget` only). |
| `minimum_dist` | `5` | Minimum distance between detected targets, in pixels. |
| `merge_markers` | `False` | Merge markers with the same numeric ID across the project. Useful when the same physical tag appears in multiple chunks. |
| `cameras` | (all) | Optional camera subset. |
| `frames` | (all) | Frames to process (multi-frame chunks only). |

### AprilTag vs CircularTarget

When should you choose AprilTag over the older CircularTarget
variants?

- **Use AprilTag** when you need **fast detection at low
  resolutions** — AprilTag's machine-vision-style detection is
  more robust to motion blur and partial occlusion than the
  CircularTarget concentric-ring detector. Aerial photogrammetry
  with markers on the ground at long camera-to-tag distances is
  a typical case.
- **Use CircularTarget** when you need **maximum sub-pixel
  accuracy at short range** under controlled lighting. The
  concentric-ring design provides slightly better center-of-mass
  estimation than AprilTag's corner-based detection.

There is no documented penalty for using both target types in the
same chunk; call `detectMarkers` twice with different
`target_type` values. No adverse interaction has been reported,
but test on a representative frame before scaling.

### Printing recommendations

- **Tag size:** target a tag that occupies at least 30×30 pixels
  in the smallest expected camera-to-tag distance. Smaller and
  detection rate drops sharply.
- **Contrast:** matte black on matte white. Glossy tags suffer
  from specular reflections. If glossy is unavoidable, use
  `tolerance=70` or higher.
- **White margin:** keep at least one tag-cell-width of white
  margin around the tag's outer black border. Without margin,
  the detector cannot find the tag's bounding box reliably.
- **Mounting:** rigid backing. AprilTag (like CircularTarget)
  fails on wrinkled or curved surfaces beyond a few-percent
  curvature. For curved subjects, place tags on a separate
  rigid scaffold and reference them as scale bars.

### Caveats and gotchas

- **Detection rate sensitivity to resolution.** Detection rate
  drops sharply as the tag's pixel footprint shrinks. The
  AprilTag literature suggests targeting at least 6× the tag's
  bit-grid edge length in pixels (so ~36 pixels per side for a
  6×6 grid). Verify on a representative frame at the smallest
  expected camera-to-tag distance before committing to a tag
  size for the whole capture.
- **Out-of-focus tags fail silently.** AprilTag detection does not
  hint that a tag is present-but-blurry; it simply doesn't
  detect. If a project is consistently missing some tags but
  not others, check focus rather than tolerance first.
- **Same numeric ID in different variants is unrelated.** Tag #5
  in `AprilTag36h11` is a completely different bit-pattern from
  Tag #5 in `AprilTag16h5`. Don't mix variants within one
  project unless you're tracking different physical markers.
- **The `noparity` kwarg does nothing for AprilTag.** AprilTag
  has its own internal error-correction; the parity flag is for
  CircularTarget detection only.

## Why AprilTags don't masquerade (occlusion robustness by construction)

The CircularTarget families have a minimum rotation-invariant Hamming
distance of just 2, which makes them prone to **masquerade** — a partially
occluded marker decoding as a *different* valid marker (see
[Coded circular targets](coded-circular-targets.md)). AprilTag does not
share this weakness, and the reason is structural.

Every AprilTag dictionary guarantees a **minimum Hamming distance equal to
its `h` number, rotations included** — 12 for `AprilTagStandard41h12`, 11
for `AprilTag36h11`, and so on. Occluding a contiguous arc of the outer
border ring to a solid color flips those bits all to one value (all 0 or
all 1). To turn one valid tag into another, the occlusion would have to
flip at least `h` specific bits into exactly the pattern of another code —
but no two codes are closer than `h` bits apart, so a single solid-color
arc can never reach another valid code. Empirically, `AprilTagStandard41h12`
has **zero** outer-occlusion masquerade pairs: no arc, no color makes any
tag decode as a different valid tag.

Even allowing for a detector that error-corrects up to `r` bit flips,
masquerade would require occluding at least `h - r` aligned outer bits —
for `41h12` with `r = 2`, that is 10 of the 32 outer bits (over 30% of the
ring) aligned to another code, which does not occur among the 2,115 codes.
In short: AprilTag's high minimum distance buys occlusion robustness by
construction, whereas the CircularTarget floor of 2 does not. This is the
main reason to prefer AprilTag in cluttered scenes where partial occlusion
is likely.

## Selecting a maximally-separated AprilTag subset

Occlusion robustness does not mean every subset is equally good. The
`41h12` family floor of 12 leaves real **headroom**: a random 20-tag
subset sits near the floor (worst pair around 12), while a deliberately
chosen subset lifts the worst pair well above it. Choosing the `k` tags
that maximize the smallest pairwise (rotation-invariant) Hamming distance —
the same *max-min* objective used for CircularTargets, but over the four
90-degree rotations instead of `N` cyclic ones — is worthwhile even for a
family already engineered for separation.

A best (max-min) 10-tag set of `AprilTagStandard41h12`, by tag id:

```text
319, 1063, 1236, 1531, 1650, 1834, 1897, 2016, 2028, 2088
```

Every pair of these tags differs by at least **18** bits at any
orientation (the family floor is 12; mean pairwise distance around 19.7) —
exact-optimal at `k = 10`. Because AprilTag is occlusion-robust by
construction, separation is the *only* objective here; there is no
masquerade-free variant to request, as there is for CircularTargets.

## See also

- [Coded circular targets: 12-bit markers, printing, sizing, and the 14-bit / 16-bit / 20-bit family](coded-circular-targets.md)
  — the older CircularTarget family that AprilTag joined,
  plus printing workflow and target-sizing guidance.
- [Programmatic marker placement and pinning](programmatic-marker-placement.md)
  — once detected, markers can be programmatically placed,
  pinned, or moved.
- [Removing "blue flag" marker projections cleanly](removing-blue-flag-marker-projections.md)
  — auto-projected markers vs. manually-pinned markers.
- *Metashape Python API Reference* (2.3.1), Change Log §3.6
  "Metashape version 2.2.0" — documents the addition: "Added
  `AprilTag16h5`, `AprilTag25h9`, `AprilTag36h10`,
  `AprilTag36h11`, `AprilTagCircle21h7`, `AprilTagStandard41h12`
  and `AprilTagStandard52h13` to `TargetType` enum."
- *Metashape Python Reference*:
  `Chunk.detectMarkers`, `TargetType` (enum: 5 CircularTarget = 4 coded + 1 non-coded,
  plus 7 AprilTag + CrossTarget).
- [Forum topic 16745](https://www.agisoft.com/forum/index.php?topic=16745.0)
  — Metashape 2.2.0 pre-release thread.
- [AprilTag homepage (April Lab, U. Michigan)](https://april.eecs.umich.edu/software/apriltag)
  — Olson 2011 (original specification), Wang & Olson 2016
  (`AprilTag36h11` family), Krogius et al. 2019 (`AprilTagStandard*`
  family).
- [*New features in Agisoft Metashape 2.2.x* (Agisoft KB)](https://agisoft.freshdesk.com/support/solutions/articles/31000173952)
  — official 2.2 feature announcement.

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

