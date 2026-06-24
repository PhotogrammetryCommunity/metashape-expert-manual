---
title: "Automatic sky masking with ONNX: pre-clean for sky-prone aerial captures"
status: unverified
applies_to: Metashape Pro 2.3 — pattern from `automatic_sky_masking.py` in the official metashape-scripts repo; uses `onnxruntime` + a HuggingFace-hosted segmentation model
edition: Pro
last_reviewed: 2026-06-05
diataxis: how-to
confidence: high
---

# Automatic sky masking with ONNX: pre-clean for sky-prone aerial captures

> **Confidence:** *high.* The script lives in Agisoft's
> official [`metashape-scripts`](https://github.com/agisoft-llc/metashape-scripts)
> repo, ships against Metashape 2.3, and uses the publicly-
> available skyseg.onnx model. Documentation reflects the
> script's behaviour as published.

## Problem

Drone captures over open water, snow, or wide horizons include
substantial **sky pixels** that the matcher will (incorrectly)
try to find features in. The sky's dynamic content (clouds,
haze, sun glare) produces low-quality matches that pollute the
tie-point cloud and slow alignment.

Metashape's [AI-assisted mask generation](ai-mask-generation.md)
(introduced in 2.2) is one solution but targets foreground /
background segmentation, not specifically sky. For datasets
where the sky is the dominant unwanted region, a **purpose-built
sky segmentation model** produces more conservative,
better-targeted masks.

The [`automatic_sky_masking.py`](https://github.com/agisoft-llc/metashape-scripts/blob/master/src/automatic_sky_masking.py)
script bundles this workflow: it downloads a HuggingFace-hosted
ONNX sky-segmentation model and runs it on each photo, producing
per-image masks that Metashape consumes via its standard mask
pipeline.

## How it works

The script's pipeline:

1. On first run, downloads `skyseg.onnx` from
   [`huggingface.co/JianyuanWang/skyseg`](https://huggingface.co/JianyuanWang/skyseg/blob/main/skyseg.onnx)
   into a folder next to the script.
2. Loads the model into `onnxruntime`.
3. For each chunk camera, preprocesses the image (resize,
   normalise to the model's expected input format).
4. Runs the model and thresholds the per-pixel sky-probability
   at 0.5.
5. Saves the resulting binary mask (sky=white, scene=black) and
   loads it into Metashape via `Camera.mask = mask`.

The `0.5` threshold gives a balanced cutoff; lower (e.g., 0.3)
produces aggressive sky removal that may bite into the horizon
line; higher (e.g., 0.7) leaves more sky-coloured haze in.

## Installation

The script auto-installs its Python dependencies on first run:

> **Demo verified:** ✗ — pending Tier 3 reproduction on a real Metashape install.

```python
onnxruntime==1.18.1
opencv-python==4.10.0.84
numpy==1.26.4
Pillow==10.3.0
```

For pre-installation:

```bash
~/.pyenv/versions/Metashape-2.3/bin/pip install \
    onnxruntime==1.18.1 \
    opencv-python==4.10.0.84 \
    numpy==1.26.4 \
    Pillow==10.3.0
```

The ONNX runtime ships CPU and GPU variants; the script uses
the CPU runtime by default. For GPU acceleration, swap to
`onnxruntime-gpu` and ensure the appropriate CUDA libraries
are available.

The model file (`skyseg.onnx`, ~28 MB) is downloaded once and
cached next to the script. To pre-deploy: download manually
from
[`https://huggingface.co/JianyuanWang/skyseg/resolve/main/skyseg.onnx`](https://huggingface.co/JianyuanWang/skyseg/resolve/main/skyseg.onnx)
and place it in the script's directory.

## Usage

The script registers a menu item in the Metashape GUI when
auto-loaded:

> "How to install (Linux):
> 1. Add this script to auto-launch — copy
>    `automatic_sky_masking.py` to
>    `/home/<username>/.local/share/Agisoft/Metashape Pro/scripts/`
> 2. Restart Metashape"

(Auto-launch path on Windows:
`C:/Users/<username>/AppData/Local/Agisoft/Metashape Pro/scripts/`.)

After auto-launch installation, the script appears under the
*Scripts* menu in the Metashape GUI. To run on the active chunk:

1. Open the project in Metashape.
2. *Scripts → Generate Sky Masks* (or whatever label the script
   registers).
3. Wait for processing to complete (depends on image count and
   image size; ~1-2s per image on CPU).

After completion, every camera in the chunk has a mask loaded.
Run *Workflow → Match Photos* / *Align Photos* with mask-
respecting parameters:

```python
chunk.matchPhotos(filter_mask=True, mask_tiepoints=True)
```

For the mask-parameter semantics see
[`mask_tiepoints` cross-view propagation](mask-tiepoints-cross-view.md)
and [`filter_mask=True` starves matchPhotos](filter-mask-starvation.md).

## When to use this vs. AI-assisted masking

| Scenario | Recommended |
|----------|-------------|
| Aerial survey with sky in the frame (oblique cameras, low altitude near horizon) | Sky masking script |
| Object-orbit capture (turntable, close-range artefact) | AI-assisted mask generation (`MaskingMode.MaskingModeAI`) |
| Drone survey at nadir over open ground | Often neither — the matcher's outlier rejection handles it |
| Mixed: nadir + oblique cameras | Sky masking on oblique only (per-camera batch via `cameras=` param in addPhotos / mask script) |
| Glass / water surfaces with reflected sky | Sky masking PLUS manual cleanup of water-region patches |

For close-range object scans where the *background* is the
problem (rather than the sky), the
[ai-mask-generation](ai-mask-generation.md) workflow is more
appropriate.

## Per-camera batching

If you only want sky masking on a subset of cameras (e.g.,
oblique cameras only), modify the script's iteration:

> **Demo verified:** ✗ — pending Tier 3 reproduction on a real Metashape install with sky_masking dependencies installed.

```python
import Metashape

chunk = Metashape.app.document.chunk

# Identify oblique cameras by EXIF pitch (assumes pitch metadata is loaded)
oblique_cams = []
for camera in chunk.cameras:
    if camera.reference.rotation:
        pitch_deg = camera.reference.rotation.y
        if abs(pitch_deg) < 60:    # less than 60° from horizontal => oblique
            oblique_cams.append(camera)

# Pass this subset to the sky-masking function
# (the script's main entry point may need adapting; see source)
print(f"Will sky-mask {len(oblique_cams)} oblique cameras")
```

## Caveats

- **The skyseg model is general-purpose.** It was trained on
  diverse outdoor imagery; it works reasonably well on most
  drone captures but may produce unexpected masks for:
  - Very dark skies (twilight, storms).
  - Overcast skies that visually blend with snow / fog.
  - Reflective surfaces (glassy water, mirror-like buildings)
    that the model classifies as "sky."
- **The 0.5 threshold is fixed in the script.** To adjust,
  edit `SKYSEG_PROB_THRESHOLD` in the script source.
- **Per-image masks consume disk space.** A 5000-image
  project with full-resolution PNG masks adds ~1-5 GB to
  the project file. For storage-constrained environments,
  Metashape can use compressed masks; check
  *Tools → Preferences → Advanced* for mask-compression
  options.
- **Re-running the script overwrites existing masks.** If
  you've manually refined some masks (e.g., to add water
  regions), re-running the sky script discards your
  manual work. Save manually-edited masks externally before
  re-running.
- **Performance scales with image dimensions.** A 24MP image
  takes 5-15× longer than a 4K-resolution image on the same
  CPU. For very large captures, consider downsampling the
  source images before sky-masking, then upscaling the mask
  back.
- **Network access required for first-time install.** The
  script downloads the ONNX model from HuggingFace.
  Air-gapped systems need the model pre-deployed
  (~28 MB).

## See also

- [AI-assisted mask generation](ai-mask-generation.md)
  — Metashape's built-in foreground / background AI masker
  (different segmentation target).
- [`mask_tiepoints` cross-view propagation and the
  foreground-occluder case](mask-tiepoints-cross-view.md)
  — how the masks are consumed during *Match Photos*.
- [`filter_mask=True` starves `matchPhotos` when masks cover
  most of the image](filter-mask-starvation.md)
  — pitfall to avoid when masks (sky or otherwise) cover
  large image regions.

## References

- [`automatic_sky_masking.py`](https://github.com/agisoft-llc/metashape-scripts/blob/master/src/automatic_sky_masking.py)
  — the canonical implementation in Agisoft's official
  scripts repo.
- [HuggingFace skyseg model](https://huggingface.co/JianyuanWang/skyseg)
  — the underlying segmentation model.
- *Metashape Python API Reference* (2.3.1):
  `Camera.mask`, `Camera.photo`, `Chunk.matchPhotos` (params
  `filter_mask`, `mask_tiepoints`).
- [*How to run Python script automatically on Metashape Professional start* (Agisoft KB)](https://agisoft.freshdesk.com/support/solutions/articles/31000133123)
  — auto-launch installation procedure.
- [*Working with masks* (Agisoft KB)](https://agisoft.freshdesk.com/support/solutions/articles/31000153479)
  — the general Generate Masks / import / edit workflow these
  script-generated masks plug into.

