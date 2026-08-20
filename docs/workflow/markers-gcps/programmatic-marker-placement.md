---
title: Programmatic marker placement and pinning
status: unverified
applies_to: Metashape Pro 2.0+. The `Metashape.Marker.Projection(coord, pinned)` two-positional-argument constructor is unchanged from PhotoScan 1.4 (insight-0010) through Metashape 2.2.2 (Tier 1 introspection confirms the `coord`, `pinned`, `valid` attribute set on the class).
edition: Pro
last_reviewed: 2026-05-22
diataxis: how-to
confidence: medium
---

# Programmatic marker placement and pinning

> **Confidence:** *medium.* The four `Marker.Projection`
> construction forms (Vector / list / tuple / `pinned=` kwarg)
> were introspection-verified on Metashape 2.2; the green-vs-blue
> flag distinction is documented in the official manual. The
> automatic-projection behaviour for new markers is a heuristic
> claim derived from forum reports.

## Problem

You have a list of GCPs (or fiducial points) with image-pixel
coordinates per camera, and you want to place markers programmatically
rather than clicking through every photo in the GUI. What is the
correct Python API in Metashape 2.x?

## Context

The Marker API has three relevant surfaces:

- `chunk.addMarker()` — creates a new marker on the chunk. Returns a
  `Metashape.Marker` instance with no projections yet.
- `marker.projections` — a `Metashape.Marker.Projections` collection
  indexed by `Metashape.Camera`. Each entry is a
  `Metashape.Marker.Projection`.
- `Metashape.Marker.Projection(coord, pinned)` — constructor for one
  projection. Two positional arguments: the image-pixel coordinate
  (a `Metashape.Vector`) and the pinned flag (a boolean).

The `pinned` flag is what determines whether the projection is
treated as a *green* flag (manually placed, fully trusted) or a
*blue* flag (automatically projected, treated identically by
optimisation but rendered differently in the GUI). Both colours
participate in *Optimize Cameras* — see [Removing "blue flag"
marker projections cleanly](removing-blue-flag-marker-projections.md).

## Solution

### Place a single marker on a known camera

```python
import Metashape

chunk = Metashape.app.document.chunk

# Find the camera by its label.
target_label = "DJI_0001.jpg"
camera = next((c for c in chunk.cameras if c.label == target_label), None)
if camera is None:
    raise ValueError(f"No camera labelled {target_label!r} in chunk")

# Create the marker and pin one projection.
marker = chunk.addMarker()
marker.label = "GCP_42"
marker.projections[camera] = Metashape.Marker.Projection(
    Metashape.Vector([1999, 2004]),       # X, Y in image pixels
    True,                                 # pinned: green flag
)
```

The `Metashape.Vector` wrapper is shown for consistency with the
rest of the Metashape API surface, but bare lists or tuples also
work — see Caveats / UV-009.

### Batch import GCPs from a CSV

For an external GCP file with one row per `(marker_label,
camera_label, x_pixel, y_pixel, pinned)`:

```python
import csv
import Metashape

chunk = Metashape.app.document.chunk
cameras_by_label = {c.label: c for c in chunk.cameras}
markers_by_label: dict[str, Metashape.Marker] = {}

with open("gcps.csv") as f:
    reader = csv.DictReader(f)
    for row in reader:
        marker_label = row["marker"]
        camera_label = row["camera"]
        x = float(row["x"])
        y = float(row["y"])
        pinned = row.get("pinned", "true").lower() in ("true", "1", "yes")

        camera = cameras_by_label.get(camera_label)
        if camera is None:
            print(f"  skipping {marker_label}: camera {camera_label} not in chunk")
            continue

        marker = markers_by_label.get(marker_label)
        if marker is None:
            marker = chunk.addMarker()
            marker.label = marker_label
            markers_by_label[marker_label] = marker

        marker.projections[camera] = Metashape.Marker.Projection(
            Metashape.Vector([x, y]),
            pinned,
        )
```

After the import, run *Optimize Cameras* to incorporate the GCPs
into the bundle. If the markers also carry world coordinates (from
a separate import via `marker.reference.location`), the bundle
becomes a true georeferenced solution.

### Avoid creating unwanted blue flags

When you place projections on a marker that already has a 3D
position (from prior projections allowing triangulation, or from
`marker.reference.location`), Metashape may automatically project
that 3D position into other cameras that see it — those become
blue flags. If your workflow does not want them (e.g. because
automatic placement is known to be wrong on this dataset), follow
the placement with the bulk-removal script in
[Removing "blue flag" marker projections cleanly](removing-blue-flag-marker-projections.md).
Or place the marker on multiple cameras explicitly before letting
the GUI / script display, so the automatic projection lands closer
to truth.

## Caveats and gotchas

- **`Marker.Reference` is a strict subset of `Camera.Reference`.**
  The two `reference` attributes share the type name `Reference`
  but `Marker.Reference` exposes only `accuracy`, `enabled`,
  `location` — none of `Camera.Reference`'s `location_accuracy`,
  `location_enabled`, `rotation`, `rotation_accuracy`,
  `rotation_enabled`. Code that works for cameras raises
  `AttributeError` on markers for any of those five missing
  attributes. The asymmetry is sensible (markers are 3D points;
  orientation is meaningless for them) but is not foregrounded
  by the API documentation. See [`chunk.transform.matrix` is
  local→world; `camera.transform` is local](../../topics/crs/chunk-frame-vs-camera-frame.md)
  for the full surface comparison and a defensive idiom for code
  that handles both.
- **The second positional argument is `pinned`, not a `quality`
  or `weight`.** The Python Reference lists `coord`, `pinned`,
  `valid` as the `Projection` attributes, which can be misread as
  separate kwargs at construction time. Only `coord` and `pinned`
  are passed in.
- **`Metashape.Vector([X, Y])`, a bare list `[X, Y]`, or a tuple
  `(X, Y)` all work as the first argument** *([Resolved — UV-009](../../about/unverified.md#uv-009))*.
  The article uses `Vector` for consistency with the rest of the
  Metashape API surface, but you can pass a bare 2-element
  sequence and the binding will convert it. **The second argument
  `pinned` must be passed positionally, however:** the keyword form
  `Marker.Projection(coord, pinned=True)` silently returns an
  *unpinned* projection (`pinned=False`) on Metashape 2.2.3 —
  verified end-to-end on the *Coded targets* sample (2026-06-04).
- **Marker labels are not unique by default.** If you want to
  prevent duplicates when re-importing, key your dictionary on the
  external label (the recommended
  pattern in the example above) and reuse the existing marker
  rather than calling `chunk.addMarker()` again.
- **`marker.reference.location` is unset by default.** If your CSV
  also has world coordinates for each marker, set
  `marker.reference.location = Metashape.Vector([X, Y, Z])` and
  `marker.reference.enabled = True` *after* placing the
  projections.
- **There is no `pin()` method to flip an existing projection's
  flag.** To change a projection from blue to green, replace it
  entirely:
  `marker.projections[camera] = Metashape.Marker.Projection(p.coord, True)`.

## Runnable demonstration on the Coded targets sample dataset

The snippet below loads the [Coded targets](../../reference/sample-data.md#coded-targets)
sample (6 images, 3 markers), demonstrates that all three input
forms — `Metashape.Vector`, bare list, and tuple — produce
equivalent `Marker.Projection` instances, and confirms the article's
*Caveats* claim that none of them is required over the others.

> **Demo verified:** ✓ — run end-to-end on the *Coded targets*
> sample (Metashape 2.2.3, 2026-06-04). `chunk.addPhotos` +
> `chunk.detectMarkers` succeed; the three **positional**
> construction forms (Vector / list / tuple) return
> `pinned=True, valid=True`, and the demo marker is placed. **One
> correction from the run:** the `pinned=` *keyword* form does
> **not** work — it silently returns `pinned=False` — so step 3 and
> the Caveats now document that quirk.

```python
"""Demonstrate Marker.Projection construction forms on the Coded
targets sample dataset (https://www.agisoft.com/downloads/sample-data/).

Adjust DATASET_DIR to your local download path, then run inside
Metashape's *Tools → Run Script…* console (or save and run with
`metashape -r demo_marker_projection.py`).
"""

import os
import Metashape

DATASET_DIR = "/path/to/coded_targets/"   # ← adjust to your download

# 1. Load the 6 images and detect the 3 coded targets.
doc = Metashape.app.document
chunk = doc.chunk if doc.chunk else doc.addChunk()
photos = sorted(
    os.path.join(DATASET_DIR, f)
    for f in os.listdir(DATASET_DIR)
    if f.lower().endswith((".jpg", ".jpeg", ".tif", ".tiff", ".png"))
)
chunk.addPhotos(photos)
chunk.detectMarkers(target_type=Metashape.CircularTarget12bit, tolerance=50)
camera = chunk.cameras[0]
print(f"loaded {len(chunk.cameras)} cameras, "
      f"detected {len(chunk.markers)} markers")

# 2. All three coordinate forms produce equivalent projections.
forms = {
    "Vector": Metashape.Vector([100.0, 200.0]),
    "list":   [100.0, 200.0],
    "tuple":  (100.0, 200.0),
}
for label, coord in forms.items():
    p = Metashape.Marker.Projection(coord, True)
    print(f"  {label:7} → coord={p.coord}, pinned={p.pinned}, valid={p.valid}")

# 3. WARNING: the keyword form does NOT work as expected — `pinned=True`
#    is silently ignored and the projection comes back UNPINNED.
#    Pass `pinned` positionally (as in step 2). Verified on 2.2.3.
p = Metashape.Marker.Projection(Metashape.Vector([100.0, 200.0]),
                                pinned=True)
print(f"  kwarg   → pinned={p.pinned}  (BUG: expected True — pass positionally)")

# 4. Optional: place a fresh marker on the chunk using the
#    Vector form (the article's recommended style) and confirm
#    the projection lands on the chosen camera.
new_marker = chunk.addMarker()
new_marker.label = "demo_marker"
new_marker.projections[camera] = Metashape.Marker.Projection(
    Metashape.Vector([1000.0, 1500.0]), True
)
print(f"  placed marker {new_marker.label!r} with "
      f"{len(list(new_marker.projections.keys()))} projection(s)")
```

Expected output: the three **positional** forms each print
`pinned=True, valid=True`; the **keyword** form prints
`pinned=False` (the silent-ignore quirk noted in step 3); and a
final line confirms the demo marker was placed. This matches the
end-to-end run on Metashape 2.2.3 (2026-06-04).

## See also

- [Helping alignment when photos don't align: markers, references, and what to use when](../alignment/helping-alignment.md)
  — the GUI workflow analogue of this Python-API article,
  with the broader decision framework for when to use markers
  vs camera references.
- [Coded circular targets: printing, sizing, and choosing a variant](coded-circular-targets.md)
  — what the physical targets look like, sizing rules, and
  the *Print Markers* workflow that produces them.
- [Recovery paths for unaligned cameras](../alignment/recovery-paths-unaligned-cameras.md)
  — Path 2 (marker-assisted *Align Selected Cameras*) is the
  primary use-case for the API documented here.

## References

- **Official manual:** *Metashape Pro User Manual*, ch. 4
  "Reference and calibration" → "Georeferencing" → markers and the
  Reference pane (Pro 2.3 PDF, p. 98).
- **Python Reference:** `Metashape.Chunk.addMarker`,
  `Metashape.Marker.Projection` (with `coord`, `pinned`, `valid`
  attributes — confirmed against Metashape 2.2.2),
  `Metashape.Marker.projections` (the `Marker.Projections`
  collection), `Metashape.Marker.reference.location` —
  *Metashape Python API Reference*, version 2.3.1.
- **Forum:** [Pasumansky, 2018-12-21, PhotoScan 1.4](https://www.agisoft.com/forum/index.php?topic=10129.msg46256#msg46256)
  — the canonical two-positional-argument example. The `PhotoScan`
  module name in the snippet is the only thing that needs renaming
  for 2.x.
- **Related articles:** [Removing "blue flag" marker projections cleanly](removing-blue-flag-marker-projections.md)
  is the inverse operation — when you want to *delete* an existing
  projection rather than create one.
- **Suggested sample dataset:** [Coded targets](../../reference/sample-data.md#coded-targets)
  is the natural fit (6 images, 3 markers, automatic detection
  workflow). For a CSV-import test, generate a synthetic
  `gcps.csv` from the auto-detected projections, clear them, and
  re-import.
