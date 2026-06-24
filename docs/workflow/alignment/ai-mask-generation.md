---
title: AI-assisted mask generation
status: unverified
applies_to: Metashape Standard 2.2.0+ and Metashape Pro 2.2.0+. The `Metashape.MaskingMode.MaskingModeAI` enum value was introduced in Metashape 2.2.0. Tier 1 introspection on Metashape 2.2.2 confirms the enum and the full `chunk.generateMasks` kwarg surface.
edition: "Pro / Standard"
last_reviewed: 2026-06-05
diataxis: how-to
confidence: medium
---

# AI-assisted mask generation
> **Confidence:** *medium.* The `MaskingMode.MaskingModeAI` enum and `chunk.generateMasks` kwargs are introspection-confirmed on Metashape 2.2.0+. The turntable / close-range scope is forum-attested with permalinks.
## Problem

You have a turntable, copy-stand, or close-range capture of a single
object against a non-uniform background — a museum artifact on a
neutral cloth, an industrial part on a workbench, a sculpture in a
gallery — and you need per-image masks so the background does not
contribute tie-points or texture. Drawing masks by hand or chroma-keying
out a non-uniform backdrop is too slow. Metashape 2.2.0 introduces an
AI masking mode for exactly this scenario, but its design point is
narrow and its limitations are not documented in the official manual.

## Context

Metashape 2.2.0 adds `MaskingMode.MaskingModeAI` — a neural-network
segmenter that isolates foreground from background using a
pre-trained model packaged with Metashape. The model is
downloaded on first use and cached locally; subsequent runs work
offline. It joins the four legacy modes (`MaskingModeAlpha`,
`MaskingModeBackground`, `MaskingModeFile`, `MaskingModeModel`)
as a fifth option.

The AI option is **not a general-purpose semantic-segmentation
tool**. It is calibrated for a specific shooting scenario,
attested verbatim:

> "Mostly this new feature is applicable to the close-range
> shooting scenarios of rather small objects. Mainly for
> turn-table sessions, but could be also used to isolate the
> lone-standing object from non-uniform background."
> — Alexey Pasumansky, 2024-10-08, Metashape 2.2.0 pre-release
> ([permalink](https://www.agisoft.com/forum/index.php?topic=16745.msg71715#msg71715))

The model targets **lone-standing objects** with **non-uniform
backgrounds**. Aerial flights, multi-object compositions, and
scenes with many co-equal subjects are explicitly *not* the
design point.

## Solution

### When to use AI masking

Choose the AI mode when **all** of these hold:

1. The scene contains **one obvious subject** that occupies the
   centre of every frame.
2. The background is **non-uniform** — varied colour, texture, or
   lighting — so chroma-key (`MaskingModeBackground`) doesn't work.
3. You don't yet have a reconstructed mesh — so `MaskingModeModel`
   isn't an option.
4. You want to **avoid drawing masks by hand** in every frame.

### When NOT to use AI masking

Don't use it when:

- The scene has **multiple co-equal subjects**. The AI is
  designed to segment a single foreground; behaviour with
  multiple co-equal objects is unattested and may produce
  incomplete masks.
- The capture is **aerial or landscape**. The model wasn't
  trained for these scenarios.
- The **subject and background share visual structure** (e.g. a
  ceramic vessel against a textured cloth in similar tones). The
  segmentation degrades.
- **Glass, transparent, or highly reflective subjects** —
  these tend to mis-segment in practice.

In any of these cases, prefer:

- `MaskingModeBackground` if you have control over the background
  (drop a fabric backdrop, light it uniformly) — see KB
  [*Masks from background photos* (Agisoft KB)](https://agisoft.freshdesk.com/support/solutions/articles/31000162414).
- `MaskingModeModel` after you have a rough first reconstruction
  — re-mask using the model silhouette and re-align for
  better tie-points; see [*Automatic masking from the model* (Agisoft KB)](https://agisoft.freshdesk.com/support/solutions/articles/31000163388).
- Hand-drawn masks for the first 5–10 frames + propagate via the
  *Apply Mask to Tie Points* technique discussed in
  [Cross-view mask propagation](mask-tiepoints-cross-view.md).

### GUI procedure

*Workflow → Generate Masks…*

In the dialog, choose AI masking via the *Method* control (the
exact label hierarchy and dialog flow may differ between 2.2.0
and 2.3.0; pin down at Tier 3 verification). The API constant
the GUI selects is `Metashape.MaskingMode.MaskingModeAI`.

Whether `tolerance` and the *defocus* sub-options affect AI mode
output is not directly attested in the source thread. Their
behaviour is documented under each kwarg in the Python API
section below; verify the AI-mode interaction at Tier 3.

### Python API

```python
import Metashape

doc = Metashape.app.document
chunk = doc.chunk

# Generate AI-based masks for all cameras.
chunk.generateMasks(
    masking_mode=Metashape.MaskingMode.MaskingModeAI,
    mask_operation=Metashape.MaskOperation.MaskOperationReplacement,
)
doc.save()
```

The full kwarg surface (Tier 1 introspection on 2.2.2):

| Kwarg | Default | Effect |
|-------|--------|--------|
| `path` | `'{filename}_mask.png'` | Used by file-based modes; ignored for AI mode. |
| `masking_mode` | `MaskingModeAlpha` | Set this to `MaskingModeAI`. |
| `mask_operation` | `MaskOperationReplacement` | How to combine the new mask with any existing mask: `Replacement` (overwrite), `Union` (logical OR), `Intersection` (logical AND), `Difference` (subtract new from existing). |
| `tolerance` | `10` | Segmentation tolerance for the older non-AI modes. Whether this affects AI-mode output is unattested in the source thread; verify at Tier 3 before relying on it. |
| `cameras` | (all) | Optional list of cameras to process. |
| `replace_asset` | `True` | Update the chunk's default mask set. |
| `frames` | (all) | Frames to process (multi-frame chunks only). |
| `mask_defocus` | `False` | **Orthogonal** to the AI mode. When `True`, mask out-of-focus regions inside the AI-segmented foreground. |
| `fix_coverage` | `True` | Extend the defocus mask to cover the full mesh (only used if `mask_defocus=True`). |
| `blur_threshold` | `3` | Allowed blur radius in pixels (only if `mask_defocus=True`). |
| `depth_threshold` | `≈ 3.4 × 10³⁸` | Maximum depth in metres for distance-based masking. The default (FLT_MAX) effectively disables depth filtering; set to a finite value to mask pixels beyond a given depth from the camera. (Only used if `mask_defocus=False`.) |

### Combining AI masks with defocus masks

`mask_defocus=True` lets you stack two filters: keep only the AI-
segmented foreground **and** drop blurry regions within it. Useful
for turntable captures where a deep object is partially out of
focus at the extremes.

```python
chunk.generateMasks(
    masking_mode=Metashape.MaskingMode.MaskingModeAI,
    mask_defocus=True,
    blur_threshold=3,        # pixels; tune per camera
    fix_coverage=True,
)
```

### Combining AI masks with existing masks

If you have hand-drawn masks for a few critical frames, use
`mask_operation=MaskOperationIntersection` to keep only pixels both
masked manually *and* by the AI — useful when the AI is too
aggressive on shadows or thin protrusions:

```python
chunk.generateMasks(
    masking_mode=Metashape.MaskingMode.MaskingModeAI,
    mask_operation=Metashape.MaskOperation.MaskOperationIntersection,
)
```

Or `MaskOperationUnion` to add to existing masks rather than replace
them.

### Offline-mode caveat

The pre-trained model is downloaded on first use. After that, AI
masking works offline. From the source thread:

> "Providing that the trained model is already downloaded, it
> should work even when no Internet connection is available."
> — Alexey Pasumansky, 2024-10-29, Metashape 2.2.0 pre-release
> ([permalink](https://www.agisoft.com/forum/index.php?topic=16745.msg71933#msg71933))

If you operate in air-gapped environments, run AI masking once on a
connected machine before isolating it. The model location is in
the user-config directory; it is not project-local.

A regression in early 2.2.0 pre-release builds broke offline mode;
it was resolved in build 19440 (later 2.2.0 pre-release update,
2024-11-12) before the official release.

## See also

- [Cross-view mask propagation](mask-tiepoints-cross-view.md)
  — older, manual approach to mask propagation; still useful when AI
  masking isn't applicable.
- [`filter_mask=True` starves `matchPhotos` when masks cover most
  of the image](filter-mask-starvation.md) — relevant when an AI
  mask is too aggressive and leaves matchPhotos with insufficient
  keypoints.
- *Metashape Python API Reference* (2.3.1), Change Log §3.6
  "Metashape version 2.2.0" — documents the addition: "Added
  `MaskingModeAI` to `MaskingMode` enum."
- *Metashape Python Reference*:
  `Chunk.generateMasks`, `MaskingMode`, `MaskOperation`.
- [Forum topic 16745](https://www.agisoft.com/forum/index.php?topic=16745.0)
  — Metashape 2.2.0 pre-release thread (4 substantive Agisoft-staff
  posts on AI masking).
- [*New features in Agisoft Metashape 2.2.x* (Agisoft KB)](https://agisoft.freshdesk.com/support/solutions/articles/31000173952)
  — official 2.2 feature announcement (cited in the
  pre-release thread).
- [*Working with masks* (Agisoft KB)](https://agisoft.freshdesk.com/support/solutions/articles/31000153479)
  — the canonical Generate Masks workflow (manual editing, From
  Model, From Background, and Automatic AI methods) plus mask
  import/export.
- [*Automatic background masking using custom script* (Agisoft KB)](https://agisoft.freshdesk.com/support/solutions/articles/31000161958)
  — the pre-2.2 rembg-based `automatic_masking.py` (Pro 1.7.4+),
  the script alternative for versions without the built-in AI mode.

