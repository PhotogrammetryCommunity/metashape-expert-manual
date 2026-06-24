---
title: Texture in Metashape 2.3 — what changed and why your scripts may need updating
status: unverified
applies_to: Metashape Pro 2.3+ and Metashape Standard 2.3+. Tier 1 introspection on Metashape 2.3.1 confirms the full `Chunk.buildTexture` kwarg surface and the 6-value `BlendingMode` enum. Behaviour on Metashape 2.2.3 (the prior major) is included as the comparison baseline.
edition: "Pro / Standard"
last_reviewed: 2026-06-05
diataxis: how-to
confidence: medium
---

# Texture in Metashape 2.3 — what changed and why your scripts may need updating
> **Confidence:** *medium.* The 2.3 texture-pipeline changes (Vulkan, NaturalBlending) are documented in pre-release threads with permalinks. The version-specific API surface is introspection-confirmed against 2.3.
## Problem

Metashape 2.3 changed the default behaviour of
`Chunk.buildTexture` in a way that affects every existing script
that calls it without an explicit `blending_mode=` kwarg. The
release also introduced **five new kwargs** for the new *Natural*
blending pipeline. If you maintain a 2.x-era texture-build script,
it will produce **different output** on 2.3 — sometimes better,
sometimes worse, but always different. This article documents
the changes and how to handle each one.

## Context

`buildTexture` has had the same API surface across 2.0 / 2.1 /
2.2 — same kwargs, same defaults. 2.3 is the first major to
extend it. Tier 1 introspection on **Metashape 2.2.3** vs
**Metashape 2.3.1** shows the diff.

### `BlendingMode` enum (Metashape 2.3.1)

Six values (introspection-confirmed):

- `AverageBlending` — average all camera contributions per face.
- `DisabledBlending` — pick the first contributing camera.
- `MaxBlending` — maximum-intensity contribution per face.
- `MinBlending` — minimum-intensity contribution per face.
- `MosaicBlending` — pick the best camera per face (the 2.2 default).
- `NaturalBlending` — neural-network-inspired blending that
  preserves local contrast and reduces seam artifacts (the 2.3
  default; new in this release).

The 2.0–2.2 default `MosaicBlending` is still available. Pre-2.3
scripts that pass `blending_mode=Metashape.BlendingMode.MosaicBlending`
explicitly will behave identically on 2.3.

### `Chunk.buildTexture` signature diff

| Kwarg | 2.2.3 default | 2.3.1 default | Status |
|-------|---------------|---------------|--------|
| `blending_mode` | `MosaicBlending` | **`NaturalBlending`** | **Default changed** |
| `texture_size` | `8192` | `8192` | unchanged |
| `downscale` | (absent) | `2` | **new** (natural only) |
| `sharpening` | (absent) | `1` | **new** (natural only) |
| `use_assigned_images` | (absent) | `False` | **new** |
| `fill_holes` | `True` | `True` | unchanged |
| `ghosting_filter` | `True` | `True` | unchanged |
| `out_of_focus_filter` | (absent) | `False` | **new** (natural only) |
| `color_enhancement` | (absent) | `False` | **new** |
| `cameras` | (all) | (all) | unchanged |
| `texture_type` | `DiffuseMap` | `DiffuseMap` | unchanged |
| `source_data` | `ImagesData` | `ImagesData` | unchanged |
| `source_asset` | (none) | (none) | unchanged |
| `transfer_texture` | `True` | `True` | unchanged |
| `workitem_size_cameras` | `20` | `20` | unchanged |
| `max_workgroup_size` | `100` | `100` | unchanged |
| `anti_aliasing` | `1` | `1` | unchanged |

## Solution

### Migration step 1 — pin your blending mode explicitly

If you have an existing 2.x-era script that calls
`buildTexture()` without `blending_mode=`, **pin the mode** before
running on 2.3 to avoid silent behaviour changes:

```python
import Metashape

# Match 2.2 behaviour (mosaic blending).
chunk.buildTexture(
    blending_mode=Metashape.BlendingMode.MosaicBlending,
    texture_size=8192,
)

# Or opt in to the new 2.3 default explicitly (more readable
# than relying on the implicit default).
chunk.buildTexture(
    blending_mode=Metashape.BlendingMode.NaturalBlending,
    texture_size=8192,
)
```

Pinning is the no-regression migration. The script will produce
2.2-identical output on 2.3 and onward.

### Migration step 2 — opt in to natural blending where it helps

Natural blending shines on:

- **Captures with significant lighting variation** between
  adjacent images. Mosaic picks one camera per face; natural
  blends multiple, so seams from changing illumination are less
  visible.
- **Captures with motion blur or focus variation** — combine with
  `out_of_focus_filter=True` to discard blurry contributions.
- **Datasets where you previously used `AverageBlending`** to
  hide mosaic seams. Natural is a strict improvement: it uses
  more cameras like average blending but preserves local contrast
  better.

Mosaic is still preferable when:

- **Texture sharpness matters more than seam consistency** (e.g.
  archaeological scans where preserving the sharpest possible
  view per face is critical).
- **You are building a Tiled Model** where the
  `transfer_texture=True` baking step pulls from per-face source
  data and seam consistency matters less.
- **VRAM is tight** — natural blending was VRAM-heavy in early
  2.3 builds; pre-build-21576 versions can run out of memory at
  `texture_size=8192`. Attested verbatim:

  > "In the latest 2.3.0 pre-release update (build 21576) the
  > utilization of VRAM has been optimized for building texture
  > in Natural mode. So we expect no problems for 8K pages
  > generation now, as it could happen in earlier pre-release
  > versions." — Alexey Pasumansky, 2025-11-11, Metashape 2.3.0
  > pre-release ([permalink](https://www.agisoft.com/forum/index.php?topic=17361.msg74472#msg74472))

### Migration step 3 — discover the new natural-only controls

Three of the five new kwargs only take effect with
`blending_mode=NaturalBlending`:

- `downscale=2` — image-pyramid downscale factor. Higher = faster
  texture build but lower per-pixel sharpness. The default `2`
  matches what depth-map estimation uses.
- `sharpening=1` — output sharpening strength (0 = no
  sharpening, larger = stronger).
- `out_of_focus_filter=False` — when `True`, discards
  out-of-focus contributions on a per-face basis. Agisoft staff
  have publicly suggested this as a debugging step for
  natural-mode texture issues:

  > "Can you please check if adding `out_of_focus_filter=True`
  > parameter resolves the problem?" — Alexey Pasumansky,
  > 2025-12-03, Metashape 2.3.0 pre-release
  > ([permalink](https://www.agisoft.com/forum/index.php?topic=17361.msg74561#msg74561))

The parameter is a no-op in any non-natural blending mode.

### Migration step 4 — Keep UV + Natural-mode is forbidden, use Texture Transfer

If your pipeline preserves a custom UV layout (the *Keep UV*
option) and now wants natural blending, you cannot use both
together. The documented workaround:

> "Currently Keep UV option is not compatible to Natural
> texturing. But as a workaround in 2.3.0 pre-release version
> you can generate the texture in Natural mode over the
> duplicated copy of the source model and then switch back to
> the original model with custom UV layout and use Texture
> Transfer option in order to re-pack the texture generated in
> Natural mode to the desired UV layout." — Alexey Pasumansky,
> 2025-10-28, Metashape 2.3.0 pre-release
> ([permalink](https://www.agisoft.com/forum/index.php?topic=17361.msg74418#msg74418))

The procedure:

1. **Duplicate** the source model in the GUI (or `chunk.copy()`
   in Python). Keep the duplicate's auto-generated UV layout
   (don't apply *Keep UV*).
2. **Build texture** on the duplicate with Natural blending.
3. **Switch back** to the original model (with the custom UV
   layout intact).
4. **Texture Transfer** from the duplicate to the original. The
   transfer re-packs the natural texture into the custom UV
   layout.

There is no current Python API for *Texture Transfer*; this step
is GUI-only. The introspection-confirmed `transfer_texture` kwarg
on `buildTexture` is a different feature (controls whether to
bake source-image data into the texture during build).

### Migration step 5 — `use_assigned_images=True` for hand-curated camera selections

The new `use_assigned_images=False` kwarg respects the GUI's
*Assign Image* tool selections — you can manually mark which
camera(s) should provide texture for which face groups, then
rebuild with the flag set. The two-pass workflow, attested
verbatim:

> "Do you build the texture first, then use Assign Image tool
> and then rebuild the texture with 'use assigned images'
> option enabled?" — Alexey Pasumansky, 2025-12-03,
> Metashape 2.3.0 pre-release
> ([permalink](https://www.agisoft.com/forum/index.php?topic=17361.msg74558#msg74558))

The two-pass procedure:

1. Build texture once with default settings.
2. In the *Model* view, select faces; *Texture → Assign Image*
   to bind those faces to a specific camera. **Use the
   *Visible Selection* option** when selecting faces — without
   it, far-away or inverted faces (which the chosen camera
   cannot actually see) get included accidentally and produce
   visual artefacts. Attested:

   > "Is it possible that during the face selection for the
   > texture assignment you are not using Visible Selection
   > option and accidentally far away or inverted faces are
   > selected?" — Alexey Pasumansky, 2025-12-05,
   > Metashape 2.3.0 pre-release
   > ([permalink](https://www.agisoft.com/forum/index.php?topic=17361.msg74566#msg74566))

3. Rebuild with `use_assigned_images=True`. The new pass honours
   the manual assignments.

## Combined example

A complete 2.3-style texture build with the new controls:

```python
import Metashape

doc = Metashape.app.document
chunk = doc.chunk

# Recommended 2.3 default for most cases.
chunk.buildTexture(
    blending_mode=Metashape.BlendingMode.NaturalBlending,
    texture_size=8192,
    downscale=2,                 # default; raise to 4 for speed
    sharpening=1,                # default
    out_of_focus_filter=True,    # discard blurry contributions
    color_enhancement=False,     # opt-in if you want auto colour adjust
    fill_holes=True,
    ghosting_filter=True,
)
doc.save()
```

## Caveats and gotchas

- **The default flip is silent.** A 2.x script with no
  `blending_mode=` kwarg will produce different output on 2.3.
  Pin the mode explicitly before running on 2.3.
- **Natural-only kwargs are no-ops in mosaic mode.** Setting
  `out_of_focus_filter=True` while keeping
  `blending_mode=MosaicBlending` will not error; the kwarg is
  simply ignored. This is a footgun.
- **`color_enhancement=True` is automatic.** It runs an internal
  exposure / white-balance correction. If you have already
  pre-processed your images for consistent colour, leaving it
  off avoids double-correction.
- **Build 21576 is the minimum stable build for 8K natural
  textures.** Earlier 2.3.0 pre-release builds can run out of
  VRAM at `texture_size=8192`.
- **Texture Transfer is GUI-only as of 2.3.1.** No Python API
  for the re-pack step yet.

## See also

- [Forum topic 17361](https://www.agisoft.com/forum/index.php?topic=17361.0)
  — Metashape 2.3.0 pre-release thread (6 substantive
  Agisoft-staff posts on texture).
- [*New features in Agisoft Metashape 2.3.x* (Agisoft KB)](https://agisoft.freshdesk.com/support/solutions/articles/31000177202)
  — official 2.3 feature announcement.
- [*Texture map types* (Agisoft KB)](https://agisoft.freshdesk.com/support/solutions/articles/31000154587)
  — what the Diffuse, Occlusion, Normal and Displacement maps are
  (the options behind the `texture_type` kwarg).
- [Metashape / PhotoScan version timeline](../../reference/version-timeline.md)
  — version-at-time mapping.
- *Metashape Python API Reference* (2.3.1), Change Log §3.2
  "Metashape version 2.3.0" — explicitly documents the
  default-blending-mode flip ("Changed default value of
  `blending_mode` argument to `NaturalBlending` in
  `Chunk.buildTexture()` method") and lists all 5 new kwargs.
- *Metashape Python Reference* (2.3.1):
  `Chunk.buildTexture`, `BlendingMode`.

