# Estimate Image Quality (Analyze Images)

> **Status:** documented (2026-05-24).

## What it is

*Estimate Image Quality* (the GUI command) and `analyzeImages`
(the Python equivalent) compute a per-image quality score
designed to flag motion-blurred, out-of-focus, or otherwise
low-quality images that may degrade alignment. The score is
stored in `camera.meta["Image/Quality"]` as a float; cameras
with quality below 0.5 are conventionally considered blurred
and the documented recommendation is to disable them
(`camera.enabled = False`) before alignment.

## Where it lives

| | Standard | Pro |
|---|---|---|
| **GUI** | *Workflow → Estimate Image Quality* (older versions: *Photo → Analyze Photos*) | (same) |
| **Python** | `chunk.analyzeImages(cameras=[…], filter_mask=False)` | (Pro only) |
| **Per-camera result** | `camera.meta["Image/Quality"]` (float, typically 0–1) | (same) |
| **Available since** | early — feature has existed in PhotoScan since at least 1.0 | (same) |

The 2.x rename: the Python method is `analyzeImages` (not
`analyzePhotos` — verify on your installed version). The 1.x
GUI command was *Analyze Photos*; 2.x renamed to *Estimate
Image Quality*.

## API surface

```python
chunk.analyzeImages(
    cameras=None,           # default: all cameras
    filter_mask=False,      # restrict analysis to unmasked region
)
```

The introspection-confirmed docstring (Metashape 2.2.2):

> "Estimate image quality. Estimated value is stored in camera
> metadata with Image/Quality key. Cameras with quality less
> than 0.5 are considered blurred and we recommend to disable
> them."

## How to read the per-camera result

```python
import Metashape

chunk = Metashape.app.document.chunk
chunk.analyzeImages()    # populate Image/Quality on every camera

for cam in chunk.cameras:
    quality = float(cam.meta.get("Image/Quality", "nan"))
    flag = "BLURRED" if quality < 0.5 else "ok"
    print(f"{cam.label!r:>30}  quality={quality:.3f}  {flag}")

# Disable blurred cameras (the documented recommendation).
n_disabled = 0
for cam in chunk.cameras:
    quality = float(cam.meta.get("Image/Quality", "nan"))
    if quality < 0.5:
        cam.enabled = False
        n_disabled += 1
print(f"disabled {n_disabled} blurred cameras")
```

`camera.meta` is a `Metashape.MetaData` dict-like; missing
keys raise `KeyError` on `[]` lookup. Use `in` to check
presence first or wrap in `try`/`except`.

## When to use

- **Before alignment**, on any large dataset where image
  quality is suspect (handheld captures with motion blur,
  drone fast-flights, low-light surveys). Disabling blurred
  cameras before `matchPhotos` reduces matching time and the
  number of false matches the bundle has to work around.
- **As a triage step** when alignment fails: a high
  proportion of low-quality images may be the root cause.
- **For per-frame video extraction**: video frames captured
  during fast pans are systematically blurrier than steady
  frames; quality scoring helps select the keepers.

## Caveats

- **The 0.5 threshold is a *guideline*, not a strict rule.**
  Some genuinely-useful imagery scores below 0.5 (low-contrast
  scenes, deliberate soft focus, certain macro work). Inspect
  the distribution before applying a hard threshold.
- **`Image/Quality` is computed once.** Re-running
  `analyzeImages` overwrites the values. If you've changed
  the source images (re-developed RAWs, different JPEG
  quality), re-run.
- **Disabled cameras are excluded from `matchPhotos` and
  `alignCameras` but remain in the chunk.** Re-enable them
  later (`camera.enabled = True`) if you want to include them
  in a subsequent matching pass with relaxed quality
  thresholds.
- **`filter_mask=True` restricts the analysis region** when
  you have masks defined — useful when the unmasked region
  (a moving subject) is what matters for quality, not the
  background.
- **The Python API name is `analyzeImages`**, not
  `analyzePhotos` (1.x → 2.x rename). Old forum scripts may
  use the deprecated form.

## Related concepts

- *Camera enable / disable* — the typical follow-up action
  after running `analyzeImages`.
- [Tie points](../glossary.md#tie-point-cloud) — blurred
  images contribute fewer / lower-quality tie points,
  motivating the "disable before matching" recipe.

## Articles in this manual

- [Diagnosing under-aligned chunks](../../workflow/alignment/diagnosing-under-aligned-chunks.md)
  — the diagnostic ladder's rung 5 explicitly recommends running
  `chunk.analyzeImages()` and disabling cameras with quality < 0.5
  before alignment.

## Forum threads worth reading

| Date | Version | Author | Thread | One-line takeaway |
|------|---------|--------|--------|-------------------|
| _stub_ | _stub_ | _stub_ | _stub_ | _Populated as insight cards on this feature accumulate._ |
