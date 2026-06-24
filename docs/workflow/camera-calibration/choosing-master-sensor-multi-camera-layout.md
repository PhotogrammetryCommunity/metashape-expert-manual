---
title: Choosing the master sensor in a multi-camera layout
status: unverified
applies_to: Metashape Pro 2.x — and unchanged from Metashape 1.x via the same API
edition: Pro
last_reviewed: 2026-05-26
diataxis: how-to
confidence: medium
---

# Choosing the master sensor in a multi-camera layout
> **Confidence:** *medium.* Master-sensor selection is documented in the manual and forum-attested with permalinks. Multi-folder ordering rule is empirically confirmed; per-sensor master-changing API (`Sensor.makeMaster`) is introspection-confirmed.
In a multi-camera layout, one sensor in each rig group is the
**master** — the sensor whose pose is the bundle parameter; all
other sensors' poses are computed from the master pose plus
their fixed offsets (see [Declaring a fixed-geometry
multi-camera rig in Python](multi-camera-rig-python.md)).
Choosing which sensor is the master is operationally
significant when:

- One band has better feature density than the others (e.g. NIR
  on a healthy-vegetation scene gives stronger matches than
  RGB).
- One band has better georeferencing (e.g. NIR has a synced
  GNSS receiver and the others do not).
- The rig's mechanical reference frame corresponds to a
  specific sensor's position (factory calibration data is most
  natural in that frame).

## How master assignment is decided

Two GUI/API surfaces look like they should control master
assignment but **do not** control it for camera alignment:

- **The *Set Master* toggle in *Tools → Camera Calibration*
  sets the master for calibration grouping only, not for
  alignment.** Exported XML shows the calibration master in
  `<sensors>` but the alignment master in `<cameras>` —
  they can disagree.
- **The order of items in the `Chunk.addPhotos(filenames=...)`
  list does not control master assignment** (falsified at
  Tier 3, 2026-05-25; see UV-010).

The actual rule: **master assignment follows alphabetical sort
of the full image path within each filegroup at import time**.
Once set, there is no API to change it post-import — only
delete-and-re-import works.

## How to make a specific sensor the master

The technique is to control which path sorts first within each
filegroup. Two equivalent approaches:

### Technique A — rename the source folders

Rename the folder containing the intended-master sensor's
images so it sorts first alphabetically. The conventional
choice is `1_<sensor>` (or just `1`).

```
multispectral_root/
├── 1_NIR/        ← intended master
├── 2_BLUE/
├── 3_GREEN/
├── 4_RED/
└── 5_REDEDGE/
```

Then *Workflow → Add Folder* on `multispectral_root/` with the
*Create sensor from each subfolder* option. The first-sorting
folder's sensor becomes the alignment master.

This works for the GUI and the Python API equally — both apply
the same path-sort rule.

### Technique B — symlink prefix in the working directory

When source data must remain untouched, build a symlink tree
under your project's working directory with prefixes that
produce the desired sort order. Pass the symlink paths to
`addPhotos`. Source data is not modified.

```python
import os
from pathlib import Path
import Metashape

DATASET = Path("/path/to/multispectral_root")    # BLUE/, GREEN/, RED/, REDEDGE/, NIR/
WORKDIR = Path("/path/to/working_directory")

# Map each source sensor to a sort-prefixed symlink subdir.
# The numeric prefix forces NIR's full path to sort first.
SORT_ORDER = {
    "NIR":     "1_NIR",
    "BLUE":    "2_BLUE",
    "GREEN":   "3_GREEN",
    "RED":     "4_RED",
    "REDEDGE": "5_REDEDGE",
}

# Build per-sensor symlink trees; no source data is moved.
for src_name, dst_name in SORT_ORDER.items():
    dst = WORKDIR / dst_name
    dst.mkdir(parents=True, exist_ok=True)
    for img in (DATASET / src_name).glob("*.tif"):
        link = dst / img.name
        if not link.exists():
            link.symlink_to(img.resolve())

# Build filenames + filegroups with one filegroup per instant.
instants = sorted(p.name for p in (WORKDIR / "1_NIR").glob("*.tif"))
filenames, filegroups = [], []
for inst in instants:
    for dst_name in SORT_ORDER.values():     # any order works here
        filenames.append(str(WORKDIR / dst_name / inst))
    filegroups.append(len(SORT_ORDER))

doc = Metashape.app.document
chunk = doc.addChunk()
chunk.addPhotos(
    filenames=filenames,
    filegroups=filegroups,
    layout=Metashape.MultiplaneLayout,
)

# Confirm.
master = next(s for s in chunk.sensors if s.master == s)
print(f"alignment master: {master.label}")
```

Both techniques set the alignment master via the same
mechanism. Choose Technique A when source folders can be
renamed; choose Technique B when source data is read-only.

## Confirming the master after import

The introspection cue is `Sensor.master`: a sensor is its own
master if and only if it is the master sensor.

```python
for sensor in chunk.sensors:
    is_master = (sensor.master == sensor)
    print(f"{sensor.label:>20}  master={is_master}  "
          f"layer_index={sensor.layer_index}")
```

In the exported `cameras.xml`, the alignment master is the
`master_id` referenced from the `<cameras>` block (each
camera's `master_id` should point to the intended master
sensor's `id`). If the calibration master and alignment
master disagree (the *Set Master* toggle was used after
import), the calibration master is in the `<sensors>` block's
`master_id` and the alignment master is in the `<cameras>`
block's `master_id`.

## Caveats and gotchas

- **The *Set Master* toggle in *Tools → Camera Calibration* is
  not redundant.** It controls calibration grouping (which
  sensor's intrinsics are the reference for non-fixed
  sensors). It does not control alignment. The exported XML
  preserves both choices.
- **No post-import API reassigns the master.** As of Metashape
  2.2.3, the master is fixed at import. To change it, delete
  and re-import with corrected path ordering.
- **Sort key is the full path, not just basename.** Metashape
  sorts each filegroup by the **complete path** before
  assigning master. So `…/B_band/IMG001.tif` and
  `…/A_band/IMG001.tif` produce different masters even though
  the basenames are identical. This is what makes the
  prefix-the-folder technique reliable.
- **`sensor.layer_index` is independent of master assignment.**
  It is a band index for multispectral export, not a master
  identifier.

## Runnable demonstration on a synthetic multi-band dataset

The Building sample is single-band, so a faithful
master-band-selection demo would need real multispectral data
(Micasense, Sentera) which is not part of the Agisoft sample
collection. The Python pattern above is testable on any
multi-folder layout.

> **Demo verified:** ✓ partial — Tier 3 testing on a real
> multi-camera dataset (2026-05-25) confirmed that master
> assignment follows alphabetical sort of full paths regardless
> of `filenames` list order. End-to-end demo on the
> symlink-prefix variant remains pending Tier 3 reproduction
> with a publicly-shareable multispectral sample.

```python
"""Verify master-sensor assignment via path-sort, not list order.

Pre-condition: a multi-folder dataset where each folder has
the same filenames (one image per sensor per instant). The
relevant behaviour: master assignment follows alphabetical
sort of full image path within each filegroup, NOT the order
of the filenames list.
"""
import os
import Metashape

DATASET = "/path/to/multi_band_root"   # adjust

# A and B sort A < B alphabetically. The master will be
# whichever sensor's full path sorts first — i.e., the
# A_-prefixed one.
INTENDED_MASTER_DIR = "A_make_this_master"
OTHER_DIRS = ["B_other", "C_other"]

instants = sorted(f for f in os.listdir(f"{DATASET}/{INTENDED_MASTER_DIR}"))

# Deliberately put the OTHER dirs first in the Python list to
# demonstrate that list order does NOT matter.
filenames, filegroups = [], []
for inst in instants:
    for d in OTHER_DIRS + [INTENDED_MASTER_DIR]:    # master is LAST in list
        filenames.append(f"{DATASET}/{d}/{inst}")
    filegroups.append(len(OTHER_DIRS) + 1)

doc = Metashape.app.document
chunk = doc.addChunk()
chunk.addPhotos(filenames=filenames, filegroups=filegroups,
                layout=Metashape.MultiplaneLayout)

# Confirm.
print("sensor   layer_index   is_master   sample_image")
for sensor in chunk.sensors:
    is_master = sensor.master == sensor
    sample_cam = next(c for c in chunk.cameras if c.sensor == sensor)
    print(f"{sensor.label:>15}  {sensor.layer_index:>4}        "
          f"{is_master!r:>5}     {os.path.basename(sample_cam.photo.path)}")
```

**Expected output:** `is_master=True` for the sensor whose
images came from `A_make_this_master` (alphabetically-first
full path), even though it was placed last in the `filenames`
list. Other sensors: `is_master=False`.

## References

- [Forum thread, *RedEdge-M: changing the master band for camera alignment*](https://www.agisoft.com/forum/index.php?topic=13684.0)
  — primary source thread documenting the calibration-vs-alignment master distinction and the folder-rename fix.
- [Forum thread, *Multiple-Camera Rig with Python API*](https://www.agisoft.com/forum/index.php?topic=16015.0)
  — companion thread for the Python-API surface once the master is chosen.
- *Metashape Python Reference* (2.3.1), `Sensor.master` — confirms the `master == self` test for master identification.
- Related: [Symlink filename — not target — controls the camera label](../project-setup/symlink-filename-camera-label.md) — the cleanest workaround when source image folders cannot be renamed.
