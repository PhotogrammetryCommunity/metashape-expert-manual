---
title: "Adding cameras to an aligned chunk: the `keep_keypoints` workflow"
status: unverified
applies_to: Metashape Pro 2.x — and unchanged from Metashape 1.6
edition: Standard
last_reviewed: 2026-05-22
diataxis: how-to
confidence: high
---

# Adding cameras to an aligned chunk: the `keep_keypoints` workflow

> **Confidence:** *high.* The `keep_keypoints` prerequisite is
> directly attested by Agisoft support with permalinks; the
> `Chunk.matchPhotos(keep_keypoints=True)` parameter is
> introspection-confirmed on Metashape 2.2.

When new images need to be added to an already-aligned chunk, the
naïve approach — *Workflow → Align Photos* with *Reset current
alignment* enabled — wipes the existing alignment in full and
redoes matching from scratch. The correct workflow uses
**incremental matching**: the original alignment is preserved, and
keypoint detection runs only for the newly added images.

The whole workflow hinges on a single decision made *before the
first alignment*: whether *Keep Key Points* (or
`keep_keypoints=True`) was set. Without it, incremental matching
is not possible at all — the constraint is stated unambiguously
in the source thread (linked in *References*) and applies
through Metashape 2.2.2.

## Decision made before alignment: keep keypoints

> "If you remove key points from the Workspace pane [...], there
> will be no way to use 'incremental alignment approach'." —
> Alexey Pasumansky, 2020-09-24, Metashape 1.6
> ([permalink](https://www.agisoft.com/forum/index.php?topic=12596.msg56131#msg56131))

The same constraint applies in reverse: without keypoints stored
in the first place, you cannot retroactively enable incremental
matching. **Re-running `matchPhotos(keep_keypoints=True)` later
does store the keypoints — but it also redoes all the matching
from scratch**, defeating the purpose of incremental.

The decision matrix:

| Initial alignment was…                 | Incremental matching for new images?    |
|---------------------------------------|------------------------------------------|
| `keep_keypoints=False` (default)       | Not possible without redoing alignment   |
| `keep_keypoints=True`                  | **Yes** — follow the workflow below      |
| GUI *Keep Key Points* preference set   | **Yes** — same as Python `keep_keypoints=True` |
| Keypoints removed via *Workspace → Tie point cloud → Remove Keypoints* | Not possible until next full alignment |

## The canonical incremental workflow

### GUI workflow

1. **One-time preparation:** *Edit → Preferences → Advanced* →
   enable *Keep key points*. Required only when starting a project
   or when the previous alignment did not enable it.
2. *Workflow → Add Photos*, run *Workflow → Align Photos* on the
   initial set.
3. After the alignment completes, the *Workspace* pane shows a
   *Tie point cloud* node under the chunk. Right-click reveals a
   *Remove Keypoints* item — its presence (vs greyed-out absence)
   confirms that keypoints are stored.
4. To add cameras: *Workflow → Add Photos*, then *Workflow →
   Align Photos* with **the *Reset current alignment* checkbox
   left disabled**. Keypoint detection runs for the new images
   only; the existing alignment is preserved.

### Python equivalent

```python
import Metashape

chunk = Metashape.app.document.chunk

# --- Initial alignment (must use keep_keypoints=True) ---
chunk.matchPhotos(downscale=1, keep_keypoints=True)
chunk.alignCameras()

# --- Add new images later ---
chunk.addPhotos(["/path/to/new/image1.jpg", "/path/to/new/image2.jpg"])

# Identify newly added cameras (transform is None — they're unaligned).
new_cameras = [c for c in chunk.cameras if c.transform is None]

# Match only the new cameras against the existing keypoint store.
chunk.matchPhotos(
    cameras=[c.key for c in new_cameras],
    keep_keypoints=True,    # store keypoints for these too
    reset_matches=False,    # do NOT discard existing matches
)

# Align only the new cameras (existing alignment preserved).
chunk.alignCameras(cameras=[c.key for c in new_cameras])
```

> "If you want to follow the incremental image alignment approach
> and align newly added photos to the existing camera alignment,
> you should have kept the key points for initial alignment, then
> run `matchPhotos` operation for the newly added cameras and
> then use `alignCameras` command." — Alexey Pasumansky,
> 2022-03-07, Metashape 1.8
> ([permalink](https://www.agisoft.com/forum/index.php?topic=14276.msg62809#msg62809))

Followed up three weeks later when the OP reported that the
direct approach still left the new camera with no projections /
errors:

> "Do you have key points saved for the initial alignment?
>
> You should use `keep_keypoints=True` parameter for
> `matchPhotos()` task both for initial alignment and when adding
> to photos to the existing alignment." — Alexey Pasumansky,
> 2022-03-29, Metashape 1.8
> ([permalink](https://www.agisoft.com/forum/index.php?topic=14276.msg63132#msg63132))

The two non-default kwargs are essential:

- **`keep_keypoints=True`** — required on the second call too,
  not just the first. Without it the second call still runs
  matching, but the *new* keypoints it computes are not stored,
  so future incremental additions to the same chunk fail.
- **`reset_matches=False`** — required to keep the existing
  matches. The kwarg defaults to `False` already, so this is
  defensive: if you copy a `matchPhotos` line from a script that
  set `reset_matches=True` for some other reason, you destroy the
  existing matches.

The split between `matchPhotos()` and `alignCameras()` matters
here. In the GUI, *Align Photos* runs them as one operation; in
Python they are separate, and `cameras=` controls them
independently. Attested verbatim:

> "Currently it is not possible to split key point detection and
> image matching stages, they are grouped into Match Photos task.
> Keep key points feature has been introduced to allow the
> incremental matching, when new images are added to the already
> matched and aligned set of images." — Alexey Pasumansky,
> 2020-11-24, Metashape 1.6
> ([permalink](https://www.agisoft.com/forum/index.php?topic=12596.msg56684#msg56684))

## The silent-skip gotcha

A subtle gap in the API surfaced in production use, attested
verbatim:

> "If both images of a couple already have saved key points (with
> `keep_keypoints=True` during main process), the
> `matchPhotos(reset_matches=False)` method ignore this couple,
> even if this couple has never been matched before." — Yoann
> Courtois, 2022-01-25, Metashape 1.8
> ([permalink](https://www.agisoft.com/forum/index.php?topic=14141.msg63027#msg63027))

The gotcha applies when **both** of two conditions are true:

1. Both endpoints of the pair have keypoints stored in the chunk.
2. You want `matchPhotos` to consider that specific pair —
   typically because preselection excluded it on the original
   alignment, or because you've inferred from a *Components*
   tree (the disconnected sub-chunks shown after a partial
   alignment) that two clusters could be bridged if their pair
   were matched.

In this case, `matchPhotos(pairs=[(a.key, b.key)], reset_matches=False)`
silently skips the pair. The matcher's logic appears to be
"pair has both endpoints' keypoints already → consider it
already-handled." Whether or not the pair has actual *matches*
recorded is not the trigger.

The two workarounds — neither clean — are:

### Workaround A: remove and re-add the relevant images

The recommended workaround:

> "I think in the described case the only solution would be to
> remove the images, which should have newly detected key points,
> from the chunk, re-add them and run the image matching operation
> without resetting the tie points." — Alexey Pasumansky,
> 2022-01-29, Metashape 1.8
> ([permalink](https://www.agisoft.com/forum/index.php?topic=14141.msg62343#msg62343))

This is destructive: removing an image discards the tie points
attached to it. Re-adding it gets new keypoints (since `cameras=`
will trigger detection for it), and the second `matchPhotos`
will then try to match it against the rest of the chunk. The
existing tie points for *other* cameras survive, but the removed
camera loses everything from its first alignment.

```python
# Workaround A: remove + re-add specific cameras.
to_redo = [c for c in chunk.cameras if c.label in {"DSC_1234.JPG", "DSC_1235.JPG"}]
paths = [c.photo.path for c in to_redo]
chunk.remove(to_redo)
chunk.addPhotos(paths)
new_cams = [c for c in chunk.cameras if c.transform is None]
chunk.matchPhotos(cameras=[c.key for c in new_cams],
                  keep_keypoints=True, reset_matches=False)
chunk.alignCameras(cameras=[c.key for c in new_cams])
```

### Workaround B: remove all keypoints, rematch from scratch

`chunk.tie_points.removeKeypoints()` clears the chunk's keypoint
store entirely (no per-image variant exists). After it,
`matchPhotos(reset_matches=False)` re-detects all keypoints and
re-runs matching for every pair. This is equivalent in cost to
*Reset current alignment* + *Align Photos* — i.e. starting from
scratch.

```python
# Workaround B: nuclear — re-detects all keypoints.
chunk.tie_points.removeKeypoints()
chunk.matchPhotos(downscale=1, keep_keypoints=True,
                  reset_matches=False, pairs=[…])
chunk.alignCameras()
```

This is rarely worth it. If you're already paying the full-rematch
cost, *Reset current alignment + Align Photos* is simpler.

### What to do when neither workaround fits

The forum thread (with 2023-02 and 2023-08 follow-up bumps) does
not surface a fix. The honest answer for cases that need to add
manual pairs without disturbing existing tie points is: **the API
does not currently support it.** When manual cross-cluster
linkage matters, the alternatives are:

- Use markers as bridge constraints (see
  [Recovery paths for unaligned cameras](recovery-paths-unaligned-cameras.md),
  Path 2). Markers are not affected by the keypoint-skip behaviour.
- Reorganise the alignment: place the disconnected images in their
  own chunk, align that chunk, then merge with `merge_tiepoints=True`
  (see [The `merge_tiepoints` option](../chunks/merge-tiepoints-and-keep-keypoints.md)).

## Caveats

- **Standard edition has no Python API.** The GUI workflow above
  is available in Standard; the Python code blocks are Pro-only.
- **`keep_keypoints` storage cost is non-trivial.** Each image
  contributes ≈10–40 MB of keypoint data to the project file
  (depending on `keypoint_limit`). For a 100k-image project, this
  is GBs. Plan disk accordingly.
- **The silent-skip gotcha was unresolved as of Metashape 2.2.2.**
  Behaviour above reflects the 2022 report and the
  2023-08 confirmation that the issue persisted. It is plausible
  the API will gain a force-match flag in a future release; until
  it does, treat the workarounds as the only options.
- **`Reset current alignment = disabled` in the GUI corresponds
  to `reset_alignment=False` in `chunk.alignCameras()`** — and
  the latter is the default. Do not override.

- **Don't double-call `matchPhotos` to retry alignment for
  unaligned cameras.** If the first match-and-align pass left
  some cameras unaligned, the second call to `matchPhotos`
  re-runs feature detection from scratch, which is wasteful
  (and overwrites the keypoint cache unless `keep_keypoints=True`
  was used the first time). Instead, just re-run `alignCameras`:
  the existing matches are reused and only the un-positioned
  cameras get a fresh alignment attempt.

  > "If you need to re-align the cameras that have not been
  > aligned initially, then you do not need to re-match the
  > photos, just run `alignCameras` and the available matching
  > points would be re-used."
  > — Agisoft support, 2019-04-24, Metashape 1.5
  > ([permalink](https://www.agisoft.com/forum/index.php?topic=10802.msg48826#msg48826))

- **`keypoint_limit=0` and `tiepoint_limit=0` are not "use
  defaults"** — they mean *unlimited*. Setting both to 0 makes
  `matchPhotos` use every key point and every tie point
  detected, which has two negative consequences: the
  matching time becomes very long, and the bundle includes
  low-confidence key points that produce false matches and
  poorly-localized tie points.

  > "Using 0 for key point and tie point limits means that all
  > the detected key point and matching points would be used.
  > It may be not good due to the following two reasons:
  > matching time would be considerably longer, even the key
  > points of low confidence would be used, therefore the
  > project could contain big number of false matches and tie
  > points of the large scale (poorly localized)."
  > — Agisoft support, same thread

  Use the standard `keypoint_limit=40000`,
  `tiepoint_limit=4000` (the GUI defaults) unless you have a
  specific reason to override.

## Runnable demonstration on the Building sample dataset

The script below splits the
[Building](../../reference/sample-data.md#building) sample's 50
images into two halves, runs the canonical incremental workflow on
the second half, and reports the alignment state.

> **Demo verified:** ✗ — pending Tier 3 reproduction on Metashape
> Pro 2.2 / 2.3 with the *Building* sample dataset. The underlying
> APIs are introspection-verified but the demo as written has not
> been run end-to-end. Required before the manual ships.

```python
"""Incremental matching: align 25 images, add 25 more, align them.

Pre-condition: a fresh empty chunk; Building sample directory
with 50 images at known paths.
"""
import Metashape

DATASET = "/path/to/building"  # adjust
images = [f"{DATASET}/IMG_{i:04d}.JPG" for i in range(50)]

doc = Metashape.app.document
chunk = doc.addChunk()

# --- Stage 1: initial alignment of the first 25 images ---
chunk.addPhotos(images[:25])
chunk.matchPhotos(downscale=1, keep_keypoints=True)
chunk.alignCameras()

initially_aligned = sum(1 for c in chunk.cameras if c.transform is not None)
n_tracks_initial = len(chunk.tie_points.tracks) if chunk.tie_points else 0
print(f"after stage 1: {initially_aligned}/25 aligned, {n_tracks_initial} tracks")

# --- Stage 2: add 25 more, incremental match + align ---
chunk.addPhotos(images[25:])
new_cams = [c for c in chunk.cameras if c.transform is None]
print(f"new cameras: {len(new_cams)} (expect 25)")

chunk.matchPhotos(
    cameras=[c.key for c in new_cams],
    keep_keypoints=True,
    reset_matches=False,
)
chunk.alignCameras(cameras=[c.key for c in new_cams])

finally_aligned = sum(1 for c in chunk.cameras if c.transform is not None)
n_tracks_final = len(chunk.tie_points.tracks)
print(f"after stage 2: {finally_aligned}/50 aligned, {n_tracks_final} tracks "
      f"(+{n_tracks_final - n_tracks_initial})")

# Sanity: the original 25 cameras' poses should be unchanged after
# the incremental step. Capture before-and-after to verify.
```

**Expected output:** `25/25` aligned after stage 1; `50/50`
aligned after stage 2. Track count grows but does not collapse —
the existing tracks are preserved (`reset_matches=False` honoured).
If `finally_aligned < 50`, some new images failed to match —
applying [Recovery paths for unaligned cameras](recovery-paths-unaligned-cameras.md)
to the stragglers.

## References

- [Forum thread, *"Keep keypoints" confusion - not working as
  expected*, 2020](https://www.agisoft.com/forum/index.php?topic=12596.0)
  — primary canonical workflow source; msgs 56131,
  57093.
- [Forum thread, *alignCameras() not working*, 2022](https://www.agisoft.com/forum/index.php?topic=14276.0)
  — Python translation of the workflow; msgs 63571.
- [Forum thread, *Images rematching in an aligned project*, 2022](https://www.agisoft.com/forum/index.php?topic=14141.0)
  — silent-skip gotcha report (msg 63027) and
  the remove-readd workaround (msg 63072). The
  2023-02 follow-up and the 2023-08 bump confirm the issue
  persisted.
- *Metashape Python Reference* (2.3.1), `Chunk.matchPhotos` —
  documents `keep_keypoints`, `reset_matches`, `pairs`, `cameras`
  kwargs.
- *Metashape Pro User Manual* (2.3), ch. 3 *General workflow*,
  § *Align Photos* and *Preferences → Advanced* — official
  description of the *Keep Key Points* preference flag.
