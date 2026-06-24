# Gradual selection

> **Status:** stub — to be populated.
> **Last reviewed:** 2026-05-22 (terminology verified against the local Metashape Pro 2.3 user manual PDF).
>
> **2.x rename:** Metashape 2.x has renamed the menu entry to **Clean Tie Points** (under *Tools → Tie Points → Clean Tie Points…*). The criteria-and-threshold dialog itself is unchanged. We keep "Gradual selection" as the page title because that is the term used overwhelmingly in the historical forum content this manual draws on; readers searching for "gradual selection metashape" should land here.

## What it is

*Gradual Selection* (since Metashape 2.x: *Clean Tie Points*) is the
tool used to mark tie points in the tie-point cloud for deletion based on
a numerical criterion. It is the primary mechanism for cleaning up an
alignment before running *Optimize Cameras*. The four built-in criteria
are *Reconstruction Uncertainty*, *Reprojection Error*, *Image Count*,
and *Projection Accuracy*; this page focuses on the first two, which
are the ones most relevant to alignment quality.

## Where it lives

| | Standard | Pro |
|---|---|---|
| **GUI (2.x)** | *Tools* → *Tie Points* → *Clean Tie Points…* | (same) |
| **GUI (1.x)** | *Edit* → *Gradual Selection…* (older) or *Model* → *Gradual Selection…* | (same) |
| **Python** | n/a | `Metashape.Chunk.cleanTiePoints(...)` (high-level), or `Metashape.TiePoints.Filter().init(chunk, criterion=...).selectPoints(threshold)` followed by `chunk.tie_points.removeSelectedPoints()` for the criterion-driven low-level workflow. Pro only — Python is Pro-exclusive. The 1.x class name `Metashape.PointCloud.Filter` was renamed to `Metashape.TiePoints.Filter` in the 2.x API rework. |
| **Available since** | early PhotoScan (the criteria definitions have been stable since at least 0.9) | Python equivalents shifted with the PointCloud / TiePoints API rework in Metashape 2.x — old scripts referencing `PhotoScan.PointCloud.Filter` will not run on 2.x without rewriting. |

## Documented in the official manual

The Metashape user manuals describe Gradual Selection in the *General
workflow → Optimization* section, with a list of criteria and short
definitions. The forum offers substantially more depth on what the
criteria *mean* geometrically and how to use them in practice — see the
threads below.

## Related concepts

- *Optimize Cameras* — the bundle adjustment step run after gradual
  selection.
- *Reconstruction Uncertainty* and *Reprojection Error* — the metrics
  most articles in this manual use.
- See also: [Tie point cloud](../glossary.md#tie-point-cloud).

## Articles in this manual

- [Diagnosing under-aligned chunks](../../workflow/alignment/diagnosing-under-aligned-chunks.md)
  — uses gradual selection as part of the cleanup ladder.
- [The Clean Tie Points → Optimize Cameras loop](../../workflow/optimization/clean-tie-points-optimize-cameras-loop.md)
  — the canonical post-alignment cleanup workflow built on top of
  this feature.
- [Automating gradual selection in Python](../../workflow/scripting-automation/automating-gradual-selection-python.md)
  — Pro-edition Python API equivalent of the cleanup loop, including
  the 1.x → 2.x migration notes (`PointCloud.Filter` →
  `TiePoints.Filter`; `buildPoints` removed).

## Forum threads worth reading

| Date | Version | Author | Thread | One-line takeaway |
|------|---------|--------|--------|-------------------|
| 2012-10-18 | PhotoScan 0.9 | Alexey Pasumansky | [clarification on gradual selection parameters please](https://www.agisoft.com/forum/index.php?topic=738.msg2769#msg2769) | Reconstruction Uncertainty is a max/min variance ratio in 2-camera triangulation; Reprojection Error is in pixels. |
| 2012-11-15 | PhotoScan 0.9 | gEEvEE (Geert) | [clarification on gradual selection parameters please](https://www.agisoft.com/forum/index.php?topic=738.msg3115#msg3115) | The widely-cited 4-step workflow: align → crop → gradual selection on reprojection (~1 px) → optimize, iterate at most 1–3 times. |
| 2012-11-15 | PhotoScan 0.9 | Alexey Pasumansky | [clarification on gradual selection parameters please](https://www.agisoft.com/forum/index.php?topic=738.msg3105#msg3105) | Never delete so many points that alignment can break. |

## Caveats

- The *Reprojection Error* histogram is in pixels and is therefore
  comparable across projects. The *Reconstruction Uncertainty* value
  is a dimensionless ratio and is mostly useful within a single
  project, not across projects.
- The community "1.0 pixel" target is a heuristic, not a universal threshold.
  Some datasets will not converge below 1.5 px without losing too many
  points; some converge to 0.4 px easily. Use the iteration count and
  the chunk's reported average error as the actual feedback.
