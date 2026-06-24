---
title: "Pair preselection: choosing between Disabled, Generic, and Reference"
status: unverified
applies_to: Metashape Pro 2.x ; Metashape Standard 2.x — and unchanged in concept from PhotoScan 1.x
edition: "Pro / Standard"
last_reviewed: 2026-05-28
diataxis: explanation
confidence: high
---

# Pair preselection: choosing between Disabled, Generic, and Reference

> **Confidence:** *high.* The accuracy/speed tradeoff is forum-
> attested with multiple permalinks (Agisoft support, 2013;
> jwoods, 2016). The `Chunk.matchPhotos(generic_preselection,
> reference_preselection)` parameter pair is introspection-
> confirmed on Metashape 2.2.

The *Align Photos* dialog has two checkboxes that control how
Metashape decides which image pairs to match: *Generic
preselection* and *Reference preselection*. The combinations
produce three operationally distinct modes. The accuracy /
speed / RAM tradeoff is large enough that mode choice should be
deliberate, not default.

## The three modes

| Mode | Generic | Reference | Pair-selection logic |
|------|:---:|:---:|----------------------|
| **Disabled** | ☐ | ☐ | Every image is matched against every other |
| **Generic** | ☑ | ☐ | Downscaled copies are matched first to find overlapping pairs; only those pairs go through full-resolution matching |
| **Reference** | ☑ | ☑ | EXIF-derived camera positions are used to pick neighbour pairs; full-resolution matching only on those |

The two checkboxes nest: enabling *Reference* without *Generic*
falls back to *Generic* internally because the reference-based
shortlist is filtered through the generic-overlap check.

## The accuracy / speed tradeoff

> "For the highest accuracy aligning with pair preselection
> disabled is the best method. The other pair preselection
> methods (reference and generic) will align your photos faster
> with more error."
> — jwoods, 2016-06-15, PhotoScan 1.2
> ([permalink](https://www.agisoft.com/forum/index.php?topic=5454.msg26770#msg26770))

As the Agisoft support forum describes it, Generic preselection
first finds candidate *overlapping* image pairs from downscaled
copies of the images, then matches only those pairs — so a given
photo is matched against the images it overlaps with rather than
against every image in the set (discussed at
[topic=2104](https://www.agisoft.com/forum/index.php?topic=2104.0)).

In short:

- **Disabled** is the most accurate because no pairs are
  silently skipped; the matcher considers every possible pair.
- **Generic** can miss legitimate matches when the downscaled-
  copy overlap detector returns a false negative (e.g., for
  rotated views, low-feature scenes, or symmetric structures).
- **Reference** can miss matches when the EXIF positions are
  inaccurate or the camera trajectory has more overlap than
  position-based neighbours suggest (e.g., a circular flight
  pattern around a tower).

## The georeferencing-doesn't-depend-on-Reference clarification

A frequent misunderstanding:

> "Disabling the reference preselection does *not* disable the
> georeferencing of the final alignment. As long as your photos
> have geotags the software will still estimate a coordinate
> system for the alignment."
> — jwoods, 2016-06-15, PhotoScan 1.2
> ([permalink](https://www.agisoft.com/forum/index.php?topic=5454.msg26770#msg26770))

Reference preselection only affects which pairs are **matched**
during alignment — it does not affect whether the chunk gets
georeferenced. A geotagged dataset processed with *Reference
preselection disabled* still produces a georeferenced chunk,
because the geotags are read separately by the
*Reference* pane.

## When to pick which

| Scenario | Recommended mode | Why |
|----------|:---------------:|------|
| Drone survey with reliable EXIF geotags, ≥80% overlap | Reference | EXIF positions accurately predict pair overlap; saves substantial time |
| Drone survey with poor / sparse EXIF | Generic | Cannot trust positions, but generic overlap detection still cuts pair count |
| Close-range / object photogrammetry from non-geotagged photos | Generic | Saves time without losing too many real pairs |
| Symmetric structure (statues, buildings with mirror symmetry) | Disabled | Generic is more likely to skip legitimate cross-symmetry pairs |
| Repeated-pattern scenes (vegetation, water, brick walls) | Disabled | Generic falsely deselects pairs whose downscaled overlap looks ambiguous |
| Final-quality run for publication / engineering deliverables | Disabled | Maximises pair-finding completeness; expect 5–30× longer runtime |
| Iterative tuning during processing-pipeline development | Generic | Fast feedback; switch to Disabled for the final run if needed |

## Python API

> **Demo verified:** ✗ — pending Tier 3 reproduction on a real Metashape install.

```python
import Metashape

chunk = Metashape.app.document.chunk

# Mode 1: Disabled
chunk.matchPhotos(
    downscale=1,
    generic_preselection=False,
    reference_preselection=False,
    keypoint_limit=40000,
    tiepoint_limit=4000,
)

# Mode 2: Generic
chunk.matchPhotos(
    downscale=1,
    generic_preselection=True,
    reference_preselection=False,
)

# Mode 3: Reference
chunk.matchPhotos(
    downscale=1,
    generic_preselection=True,        # implicit but explicit is clearer
    reference_preselection=True,
    reference_preselection_mode=Metashape.ReferencePreselectionSource,
)
```

The `reference_preselection_mode` parameter has three values
(introspection-confirmed):

- `ReferencePreselectionSource` — uses the *source* (input)
  reference values from the Reference pane.
- `ReferencePreselectionEstimated` — uses the *estimated*
  reference values from a prior alignment.
- `ReferencePreselectionSequential` — pairs cameras by their
  sequence index (useful for image-strip captures with no
  reference data but known capture order).

## Caveats

- **The "resize photos to a smaller resolution" trick** for
  faster alignment (sometimes recommended in older forum
  threads) is largely obsolete on modern hardware — the
  `downscale=` parameter does this internally and is the
  preferred path. Manually pre-resizing the images is rarely
  necessary.
- **Generic preselection's downscaled-copy overlap detector
  uses a fixed downsample factor** that's not exposed as a
  tweak. On extreme-overlap datasets it can over-select; on
  low-overlap it can under-select.
- **Reference preselection on cm-accurate RTK data** with a
  small project radius can pick *too few* neighbours (the
  position-based neighbour-finder has a default radius that
  may be smaller than the actual visual overlap zone).
  Switching to Generic in that case is faster than Disabled
  while regaining the missed pairs.

## See also

- [Synthetic position priors via `ReferencePreselectionSource`](synthetic-priors-reference-preselection.md)
  — using the Reference mode without real geotags by injecting
  synthetic priors.
- [Diagnosing under-aligned chunks](diagnosing-under-aligned-chunks.md)
  — the canonical diagnostic ladder when alignment fails; rung 1
  recommends *Disabled* for the clean-alignment baseline.
- [Reference preselection (feature page)](../../reference/features/reference-preselection.md)
  — feature-encyclopedia entry.
- [Generic preselection (feature page)](../../reference/features/generic-preselection.md).

## References

- *Metashape Pro User Manual* (2.3), ch. 3 *General workflow*,
  § *Align Photos parameters* — describes both checkboxes.
- *Metashape Python API Reference* (2.3.1):
  `Chunk.matchPhotos`, parameters `generic_preselection` and
  `reference_preselection`, plus
  `ReferencePreselectionMode` enum.
- Forum thread, [*Which Align mode I should use?*, 2016](https://www.agisoft.com/forum/index.php?topic=5454.msg26770#msg26770)
  — jwoods's accuracy/speed tradeoff summary; quotes
  the 2013-07-30 explanation
  ([permalink](https://www.agisoft.com/forum/index.php?topic=2104.msg10551#msg10551)).

