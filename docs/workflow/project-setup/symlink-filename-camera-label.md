---
title: Symlink filename — not target — controls the camera label
status: unverified
applies_to: Metashape Pro 2.x and Standard 2.x — and unchanged from PhotoScan 1.x
edition: Standard
last_reviewed: 2026-05-22
diataxis: how-to
confidence: medium
---

# Symlink filename — not target — controls the camera label
> **Confidence:** *medium.* The behaviour is API-introspectable in
> principle but requires file-system testing to confirm fully.
> Tier 3 reproduction recommended on multiple platforms (macOS,
> Linux, Windows) before promoting to *observed* — Windows
> symlink semantics differ enough that the behaviour may not be
> identical there.

A non-obvious but useful behaviour of `Chunk.addPhotos`:

- **`Camera.photo.path`** is the *resolved* canonical path —
  symlinks have been followed.
- **`Camera.label`** is the *basename of the path you passed in*
  — derived from the symlink's filename, not from the target's
  filename.

In other words, the symlink's basename determines the camera's
label and its sort position in `chunk.cameras` (which is
alphabetically ordered by label), independent of where the
actual image file lives on disk.

## The use case

Force a specific camera to sort first in the GUI, or group
cameras under a coherent naming scheme, **without renaming source
data**. Three operational scenarios:

### Scenario 1 — Anchor camera in a multi-camera layout

[Choosing the master sensor in a multi-camera layout](../camera-calibration/choosing-master-sensor-multi-camera-layout.md)
documents that the master sensor is determined by alphabetical
filename ordering at import. If the desired master is not
alphabetically-first, you can rename the folder containing it
to `1` — but only if you can rename source data. If the source
images are read-only, on a network share, or in a structure you
shouldn't modify, **build symlinks under your project's working
directory with whatever filename prefix you need**:

```python
import os
from pathlib import Path

source = Path("/data/shared/aerial_2025/IMG_0042.jpg")
sym = Path("/path/to/working_dir/0_anchor.jpg")
sym.symlink_to(source.resolve())   # use absolute target

chunk.addPhotos([str(sym)])

camera = chunk.cameras[-1]
assert camera.label      == "0_anchor"
assert camera.photo.path == str(source.resolve())
```

The symlink basename `0_anchor` becomes the label; the source
image stays where it is on disk; the camera sorts first because
`0_anchor` precedes anything starting with a higher digit or
letter.

### Scenario 2 — Unify naming across disparate source locations

A project assembling images from multiple capture sessions, drives,
or shared mounts can build a single working-directory tree of
symlinks with a unified naming scheme. The labels in
`chunk.cameras` then follow the working-directory scheme, not the
source-disk paths.

```python
session_a = Path("/data/2024_q4/session_a")
session_b = Path("/data/2025_q1/session_b")
working   = Path("/path/to/project_workdir/images")
working.mkdir(parents=True, exist_ok=True)

for i, src in enumerate(sorted(session_a.glob("*.jpg"))):
    (working / f"a_{i:04d}.jpg").symlink_to(src.resolve())
for i, src in enumerate(sorted(session_b.glob("*.jpg"))):
    (working / f"b_{i:04d}.jpg").symlink_to(src.resolve())

chunk.addPhotos([str(p) for p in sorted(working.glob("*.jpg"))])
# Cameras sort: a_0000, a_0001, …, b_0000, b_0001, …
# Their photo.path values still reference the original data
```

Re-running the project doesn't require copying source data; the
working-directory symlinks are all that needs to be rebuilt.

### Scenario 3 — Test ordering hypotheses without disturbing source

When debugging multi-camera-layout behaviour or other
ordering-dependent issues, build a throwaway working directory of
symlinks with controlled filenames; iterate quickly without
touching source data.

## What is verifiable, what isn't

The basic API surface is documented:

- `Camera.label` (`str`, "Camera label.") — confirmed by
  introspection on Metashape 2.2.2.
- `Camera.photo` (`Photo`) — has `path` attribute (canonical
  string path).
- `Chunk.addPhotos(filenames=…, …)` — accepts a list of paths.

What's *not* documented is the **derivation rule** for
`Camera.label` (where it comes from when the path is a symlink).
The article documents the observed behaviour: symlink basename →
label; symlink target → `photo.path`.

## Caveats

- **Tested on macOS and Linux.** Windows symlink semantics differ
  (symlinks require admin permission on most installations,
  shortcut `.lnk` files are entirely different from POSIX
  symlinks). Behaviour on Windows is unverified by this article.
- **Use absolute paths in `symlink_to`.** Relative-target
  symlinks become brittle if the working directory moves; use
  `source.resolve()` when constructing the symlink to capture an
  absolute target.
- **`strip_extensions=True` (the default for `addPhotos`)** trims
  the file extension from the label. So
  `addPhotos(["/path/0_anchor.jpg"])` produces a camera with
  `label="0_anchor"`, not `"0_anchor.jpg"`. The article's
  examples reflect this.
- **The `Camera.label` is editable.** If post-import renaming is
  appropriate, set `camera.label = "new_name"` directly. The
  symlink trick is for projects where the label needs to be
  controlled at *import* time (e.g., for the multi-camera master
  selection that happens at import).
- **Source data must remain accessible at the symlink target's
  resolved path.** Moving or renaming the source breaks all
  symlinks; the working-directory symlinks then point to
  non-existent files and `addPhotos` fails. Use this technique
  only when source data has stable absolute paths.

## Runnable demonstration

The demo below is a one-line API check that any installation can
run; no sample dataset required as long as you have any image
file.

> **Demo verified:** ✗ — pending Tier 3 reproduction on multiple
> platforms (macOS, Linux, Windows) to confirm the symlink
> basename → label rule. The demo's API surface is verified; the
> file-system behaviour requires platform-specific testing.

```python
"""Confirm: Camera.label derives from symlink basename;
Camera.photo.path is the resolved target."""
import os
from pathlib import Path

import Metashape

# Pick any image file you have access to.
SOURCE = Path("/path/to/any_image.jpg")
WORKDIR = Path("/tmp/symlink_test")
WORKDIR.mkdir(exist_ok=True)

sym = WORKDIR / "0_force_first.jpg"
if sym.exists() or sym.is_symlink():
    sym.unlink()
sym.symlink_to(SOURCE.resolve())

doc = Metashape.Document()
chunk = doc.addChunk()
chunk.addPhotos([str(sym)])

cam = chunk.cameras[0]
print(f"Camera.label      = {cam.label!r}")
print(f"Camera.photo.path = {cam.photo.path!r}")
print(f"Source was        = {SOURCE.resolve()!r}")

# Cleanup.
sym.unlink()
WORKDIR.rmdir()
```

**Expected output:** `Camera.label = '0_force_first'` (symlink
basename, extension stripped) and `Camera.photo.path =
'<absolute path of original image>'` (resolved). If the label
matches the source basename instead, the version of Metashape on
this machine is doing path-resolution differently than tested,
and the article needs revision.

## References

- *Metashape Python Reference* (2.3.1), `Camera.label`,
  `Camera.photo`, `Chunk.addPhotos` — documents the API surface
  but not the symlink-basename-vs-target derivation rule.
- [Choosing the master sensor in a multi-camera layout](../camera-calibration/choosing-master-sensor-multi-camera-layout.md) — the operational scenario this technique
  supports.
