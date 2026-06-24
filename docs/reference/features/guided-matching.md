# Guided matching

> **Status:** stub. This page is the structural example for the feature
> encyclopedia. It will be populated as the alignment
> articles are written.

## What it is

Guided matching is an option of the *Match Photos* / *Align Photos* step
that asks Metashape to use the rough camera-pair geometry from initial
matching to find additional tie points the regular match step missed.
It typically increases tie-point count and connectedness at the cost of
alignment time.

## Where it lives

| | Standard | Pro |
|---|---|---|
| **GUI** | Workflow → Align Photos → *Advanced* → **Guided image matching** | (same) |
| **Python** | `Metashape.Chunk.matchPhotos(guided_matching=True, ...)` | (Pro only) |
| **Available since** | _to be confirmed_ | _to be confirmed_ |

## Documented in the official manual

- _To be filled in once an article references this feature; capture
  the manual section / page._

## Related concepts

- [Reference preselection](reference-preselection.md)
- [Generic preselection](generic-preselection.md)
- [Tie points](../glossary.md#tie-point-cloud)

## Articles in this manual

- [Diagnosing under-aligned chunks](../../workflow/alignment/diagnosing-under-aligned-chunks.md)
  — the canonical "clean" alignment settings explicitly recommend
  guided matching disabled.

## Forum threads worth reading

A curated list of forum threads that contain substantive discussion of
guided matching. Each entry shows the date and the product version
current at that date.

| Date | Version | Author | Thread | One-line takeaway |
|------|---------|--------|--------|-------------------|
| _stub_ | _stub_ | _stub_ | _stub_ | _Populated as insight cards on this feature accumulate._ |

## Caveats

_Reserved for version-specific behaviour notes (e.g. "Metashape 2.x
behaves differently from 1.x: …") and known interactions with other
features._
