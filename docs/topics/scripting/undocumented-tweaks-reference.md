---
title: "Undocumented tweaks: a partial reference"
status: unverified
applies_to: Metashape Pro 2.x — exact tweak names may change between versions
edition: Pro
last_reviewed: 2026-05-28
diataxis: reference
confidence: medium
---

# Undocumented tweaks: a partial reference

> **Confidence:** *medium.* Each tweak is forum-attested with a
> permalink, but the names and semantics are **not part of the
> stable Python API**. Agisoft may rename, repurpose, or remove
> any of these without notice. Test on a copy of the project
> before relying on a tweak in production.

Metashape exposes "tweaks" — internal settings adjustable via
`Metashape.app.settings.setValue(name, value)`. These are not
documented in the official Python API Reference; they surface in
forum threads when Agisoft support recommends them as
performance-tuning or workaround knobs.

This article catalogues the tweaks confirmed in forum posts. The
list is not exhaustive — Agisoft uses many internal settings; only
those that have been disclosed in forum support threads are
included here.

## How to set a tweak

> **Demo verified:** ✗ — pending Tier 3 reproduction on a real Metashape install.

```python
import Metashape

# All values are set as STRINGS, even for integers / floats
Metashape.app.settings.setValue("main/dense_cloud_max_neighbors", "16")

# Read back to confirm
print(Metashape.app.settings.value("main/dense_cloud_max_neighbors"))
# → "16"
```

Tweaks persist in the Metashape application settings (not in the
project file). Set them once before running the affected stage;
they apply to all subsequent calls until reset or changed.

GUI access is via *Tools → Preferences → Advanced → Tweaks…*
(in 2.x). Tweaks set via the GUI are equivalent to the Python form.

## Catalogue

### `main/dense_cloud_max_neighbors`

**Purpose:** Limit the number of camera pairs evaluated per
camera during point-cloud (depth-map) filtering. Higher = more
quality, slower; lower = faster, noisier.

**Type:** integer (string-encoded)

**Default:** `-1` (unlimited) since Metashape 1.4. Earlier
versions (1.3) used `50` as a hard-coded threshold.

**Recommended values:**

| Value | Speed | Quality | Use when |
|-------|-------|---------|----------|
| `-1` | slow | best | Default — typical projects |
| `80` | medium | slightly worse | High-overlap aerial (>80% side and forward) |
| `50` | fast | noisier | Extreme overlap (>90%, dense survey grids) |
| `30` or below | fastest | poor | Not recommended |

> *Sources: Agisoft support, 2018-05-11, Metashape 1.4 ([permalink](https://www.agisoft.com/forum/index.php?topic=8984.msg42655#msg42655)); 2019-01-29, Metashape 1.5 ([permalink](https://www.agisoft.com/forum/index.php?topic=10304.msg47977#msg47977)).*

### `main/mesh_trimming_radius`

**Purpose:** Maximum distance (in chunk-local units) for mesh
trimming during depth-maps-based mesh generation. Trimming removes
isolated mesh fragments far from the main reconstructed surface.

**Type:** float (string-encoded), interpreted in metres for
georeferenced chunks.

**Default:** internally computed from the bounding box and point
density.

**Recommended values:**

- `30` — for typical aerial / building scans where stray geometry
  appears > 30 m from the main surface.
- Lower values trim more aggressively; too low risks losing
  legitimate distant features.

Source: Agisoft support, 2019-08-16, Metashape 1.5.4 ([permalink](https://www.agisoft.com/forum/index.php?topic=10848.msg53212#msg53212)).

### `main/mesh_visibility_trimming_radius`

**Purpose:** Companion to `mesh_trimming_radius` — controls
visibility-based trimming (faces not seen from any camera position
within this radius are removed).

**Default:** internally computed.

**Use:** typically set together with `mesh_trimming_radius` to the
same value.

### `BuildDepthMaps/pm_point_threshold`

**Purpose:** Minimum number of valid tie points a camera must
have for Metashape to generate a depth map for it. Cameras with
fewer tie points are silently skipped.

**Type:** integer.

**Default:** `50`. This default has been stable since at least
Metashape 1.6.

**When to lower:** if heavy masking or low-overlap regions cause
some cameras to fall just below 50 tie points and you want a
depth map anyway. Quality suffers but coverage is preserved.

**When NOT to lower:** if cameras have legitimately too few tie
points, the resulting depth map will be unreliable. Better to
fix the alignment than work around the threshold.

Source: Agisoft support, 2021-02-09, Metashape 1.7.1 ([permalink](https://www.agisoft.com/forum/index.php?topic=13066.msg58847#msg58847)).

## Caveats

- **Tweaks are unstable across versions.** Agisoft has renamed or
  removed tweaks in past releases. Always re-verify the tweak
  works on your installed Metashape version before relying on it.
- **No GUI feedback for invalid tweaks.** Setting a non-existent
  tweak name silently does nothing. Verify with
  `Metashape.app.settings.value(name)` after setting.
- **Tweaks affect Metashape globally**, not per-project. If you
  set `dense_cloud_max_neighbors=16` for one project, it remains
  set for the next project unless explicitly cleared. Reset to
  defaults via *Tools → Preferences → Advanced → Reset all
  preferences*.
- **The list above is non-exhaustive.** Agisoft uses many internal
  settings; this article catalogues only those confirmed in forum
  posts. Don't probe undocumented names speculatively — invalid
  names silently no-op.

## When to use tweaks at all

Tweaks are appropriate when:

- **A specific performance bottleneck** has been profiled to a
  single stage (e.g., depth-map filtering on a high-overlap
  project) and a documented tweak addresses it.
- **A specific quality artefact** has been identified (e.g.,
  isolated mesh fragments) and a tweak addresses the trimming
  radius.
- **Agisoft support has recommended a specific tweak** for your
  project's situation.

Tweaks are NOT appropriate for general "make Metashape faster"
attempts. The default values are tuned by Agisoft's team and work
well across most projects. Reaching for a tweak should be the
last optimisation step, not the first.

## References

- *Metashape Pro User Manual* (2.3), § *Preferences → Advanced
  → Tweaks…* — describes the GUI dialog where tweaks are set
  (the manual does not enumerate the tweak names, which is why
  this reference exists).
- *Metashape Python API Reference* (2.3.1):
  `Metashape.app.settings`. The tweaks themselves are NOT in the
  API reference.
- [`scripts/forum_mining_status.py`](https://github.com/PhotogrammetryCommunity/metashape-expert-manual/blob/main/scripts/forum_mining_status.py)
  — internal: future tweak discoveries can be added by re-mining
  the forum corpus for `setValue("main/...")` patterns.

## See also

- [Performance tuning: CPU, RAM, GPU, and OS](../performance/cpu-ram-gpu-os-tuning.md)
- [When does Metashape use the GPU?](../performance/gpu-usage-by-stage.md)

