# Generic preselection

> **Status:** documented (2026-05-24).

## What it is

*Generic preselection* is a feature-based pair-selection
method used by *Match Photos* / *Align Photos* to identify
candidate image pairs for matching. Unlike
[reference preselection](reference-preselection.md), which uses
camera coordinates, generic preselection uses low-resolution
feature comparison: each image's features are matched against
every other image's features (or against a shortlist if
reference preselection is also enabled), and pairs above a
similarity threshold are kept for the full matching step.

## Where it lives

| | Standard | Pro |
|---|---|---|
| **GUI** | *Workflow → Align Photos* → check *Generic preselection* | (same) |
| **Python** | `Metashape.Chunk.matchPhotos(generic_preselection=True/False, …)` | (Pro only) |
| **Default** | `True` | `True` |

## How it interacts with reference preselection

The two preselection methods are **independent kwargs** that
can both be `True`, both be `False`, or either one alone.
Their interaction is documented in
[Reference preselection](reference-preselection.md):

- **Both `True`:** reference preselection picks N nearest
  neighbours by coordinate; generic preselection runs feature
  similarity on that shortlist. Recommended default for aerial
  surveys with reliable GPS.
- **Generic only (`reference_preselection=False`,
  `generic_preselection=True`):** O(N²) feature comparison
  across all images. Recommended when references are missing
  or unreliable.
- **Reference only (`reference_preselection=True`,
  `reference_preselection_mode=…`,
  `generic_preselection=False`):** introduced in PhotoScan 1.3.
  Trusts the references to identify pairs without further
  feature filtering. Useful when references are very accurate
  (surveyed positions) and feature-based selection is
  unnecessary overhead.
- **Both `False`:** matches every image against every other
  image without any pair filtering. Slowest; rarely the right
  choice.

## When to disable

The canonical "clean" alignment recipe (per
[Diagnosing under-aligned chunks](../../workflow/alignment/diagnosing-under-aligned-chunks.md))
keeps generic preselection **enabled**:

- Accuracy: High
- **Generic preselection: enabled**
- Reference preselection: disabled
- ...

Disable generic preselection only when you have very accurate
reference data and want to trust it exclusively
(`reference_preselection=True,
reference_preselection_mode=ReferencePreselectionSource,
generic_preselection=False`). This is the
"reference-without-generic" mode introduced in PhotoScan 1.3.

## Caveats

- **Generic preselection is the default.** Disabling it without
  enabling reference preselection produces the slowest possible
  alignment (full all-pairs matching).
- **The similarity threshold is not user-tunable** via Python.
  The internal threshold is calibrated for typical photographic
  content; performance on synthetic / rendered / non-photographic
  imagery may be unpredictable.
- **`filter_stationary_points`** (a separate kwarg) interacts
  with the matching, not with preselection. It removes tie
  points that are stationary across image pairs (typical of
  reflections, dust on the lens, static foreground); see the
  matchPhotos signature for details.

## Related concepts

- [Reference preselection](reference-preselection.md) — the
  coordinate-based pair-selection partner.
- [Guided matching](guided-matching.md) — a separate option
  applied at the *match* stage, not at *pair selection*.
- [Tie points](../glossary.md#tie-point-cloud)

## Articles in this manual

- [Diagnosing under-aligned chunks](../../workflow/alignment/diagnosing-under-aligned-chunks.md)
  — recommends `generic_preselection=True` as part of the
  canonical "clean" recipe.
- [Synthetic priors via `ReferencePreselectionSource`](../../workflow/alignment/synthetic-priors-reference-preselection.md)
  — a deliberate `generic_preselection=False` case for
  repeated-feature scenes where generic preselection would
  produce false matches.

## Forum threads worth reading

| Date | Version | Author | Thread | One-line takeaway |
|------|---------|--------|--------|-------------------|
| 2016-12-20 | PhotoScan 1.2 | Alexey Pasumansky | [Align images - Reference preselection](https://www.agisoft.com/forum/index.php?topic=6306.msg30226#msg30226) | Generic preselection runs on the reference-preselection shortlist when both are enabled (1.2 era; separable in 1.3+). |
| 2021-02-11 | Metashape 1.7 | Alexey Pasumansky | [Tie points ghosting](https://www.agisoft.com/forum/index.php?topic=13079.msg58789#msg58789) | The canonical "clean" baseline keeps generic preselection enabled. |
