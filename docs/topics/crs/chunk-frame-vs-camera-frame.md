---
title: "`chunk.transform.matrix` is local→world; `camera.transform` is local"
status: unverified
applies_to: Metashape Pro 2.x — and unchanged from PhotoScan 1.x
edition: Pro
last_reviewed: 2026-05-22
diataxis: explanation
confidence: high
---

# `chunk.transform.matrix` is local→world; `camera.transform` is local

> **Confidence:** *high.* The local-vs-world distinction is
> documented in the official manual and reinforced in multiple
> forum threads; `chunk.transform.matrix`,
> `camera.transform`, and the `Reference.location`/
> `Reference.location_accuracy` Vector forms are
> introspection-confirmed on Metashape 2.2.

The single most common Python-script confusion in Metashape:
camera poses returned from the API are in **chunk-local** space,
but reference data (camera/marker `reference.location`, GCPs
imported via `chunk.importReference`, all external coordinates
you set) is in **world** space. To compare them you must apply
`chunk.transform.matrix` first.

This article is the cross-reference for the two coordinate
systems, the per-axis-accuracy `Vector` machinery on
`Camera.Reference`, and the (subtly different)
`Marker.Reference` surface.

## The two coordinate systems

```text
                        camera.transform           chunk.transform.matrix
   ┌──────────────┐    ┌──────────────────┐      ┌────────────────────────┐
   │ Camera pose  │    │ pose in chunk-   │      │ chunk-local → world    │
   │ in chunk-    │ →  │ local frame      │ × →  │ similarity transform   │
   │ local frame  │    │ (4×4 matrix)     │      │ (4×4 matrix)           │
   └──────────────┘    └──────────────────┘      └────────────────────────┘
                                                            │
                                                            ▼
                                                  ┌──────────────────┐
                                                  │ pose in WORLD    │
                                                  │ frame, comparable│
                                                  │ to reference data│
                                                  └──────────────────┘
```

In code:

```python
import Metashape

chunk = Metashape.app.document.chunk
T = chunk.transform.matrix          # 4×4 Matrix, chunk-local → world

for camera in chunk.cameras:
    if camera.transform is None:
        continue                     # unaligned

    # Camera position in CHUNK-LOCAL frame:
    local_position = camera.transform.translation()

    # Camera position in WORLD frame (comparable to references):
    world_position = T.mulp(camera.transform.translation())

    # Compare to the camera's reference location (also world frame):
    if camera.reference.location is not None:
        delta = world_position - camera.reference.location
        print(f"{camera.label:>20}  Δ = {delta}")
```

**Default identity matrix.** A fresh chunk's
`chunk.transform.matrix` is the 4×4 identity, meaning chunk-local
*is* world. After alignment with georeferencing, the matrix
becomes the similarity transformation that takes the chunk-local
frame to the world frame; chunk-local positions then differ from
world positions.

## "But the alignment looks tilted!" — and why it isn't a bug

After a successful georeferenced alignment, the chunk-local frame
is *some* world-aligned frame. It does **not** automatically have
world axes parallel to local axes. Camera positions printed
without applying `chunk.transform.matrix` look "tilted" relative
to GCPs (which are in world frame), even though the alignment is
geometrically correct.

This is a **presentation property of the chunk frame**, not a
calibration bug. The user's instinct is to debug the alignment;
the actual fix is to apply `chunk.transform.matrix` before
comparison.

If you want to **force** the chunk-local frame to be world-aligned
(useful when downstream tools assume an identity chunk
transform), set a Cartesian local CRS *before* alignment:

```python
chunk.crs = Metashape.CoordinateSystem("LOCAL")
# Now run alignment — chunk-local axes will match world axes.
```

This sets up the chunk to operate in a local Cartesian frame
matching the world, eliminating the chunk-frame-vs-world-frame
distinction at the cost of giving up CRS-aware downstream
features.

## Per-axis accuracy is a `Vector`, not a scalar

`Camera.reference` carries two accuracy fields:

```python
# Both are 3-component Metashape.Vector instances.
# Each component is honoured independently during BA.
camera.reference.location_accuracy = Metashape.Vector([30.0, 30.0, 400.0])
camera.reference.rotation_accuracy = Metashape.Vector([10.0, 30.0, 5.0])
```

This means: "tighter prior on X and Y position (30 m,
typical for consumer-GNSS uncertainty in aerial work) than
on Z (400 m, intentionally loose to let the bundle absorb
GNSS-altitude bias); tight on yaw (10°), loose on pitch
(30°), tight on roll (5°)." Tutorials commonly show a
single scalar. The API's actual surface uses `Vector` — and
the per-axis form lets you encode whatever asymmetric prior
knowledge you actually have.

A common operational case: a camera with known X/Y from a
photogrammetric prior survey but unknown Z (Z = 0 with very loose
accuracy):

```python
camera.reference.location          = Metashape.Vector([x, y, 0.0])
camera.reference.location_accuracy = Metashape.Vector([2.0, 2.0, 1e6])
camera.reference.location_enabled  = True
```

The bundle treats X and Y as tightly-constrained priors and Z as
effectively unconstrained — the bundle solves for Z from tie
points alone. This is exactly the synthetic-priors workflow
documented in [Synthetic position priors via
`ReferencePreselectionSource`](../../workflow/alignment/synthetic-priors-reference-preselection.md).

Default values:

| Field | Default | After assignment |
|-------|---------|------------------|
| `location_accuracy` | `None` | `Metashape.Vector([…])` |
| `rotation_accuracy` | `None` | `Metashape.Vector([…])` |
| `accuracy` | `None` | `Metashape.Vector([…])` (alias of `location_accuracy` on cameras; the per-axis location accuracy on markers) |

Assigning a Python `list` works thanks to the implicit
`Metashape.Vector` conversion, but the canonical form is to wrap
in `Metashape.Vector(…)` explicitly.

> **`accuracy` vs `location_accuracy` on `Camera.Reference`.**
> Both attributes exist on `Camera.Reference` and have identical
> docstrings ("Camera location accuracy", `Metashape.Vector`).
> They are aliases of the same underlying field. The
> article on tightening reference accuracies uses
> `c.reference.accuracy` (the legacy form, also in the GUI's
> Reference pane); this article uses `c.reference.location_accuracy`
> (the explicit per-axis form). Either works in code.

## `Marker.Reference` is a strict subset

The `Reference` class returned by `marker.reference` and
`camera.reference` shares the type name `Reference` but has
different attribute sets. The Marker variant is a **strict
subset** of the Camera variant:

| Attribute | `Camera.Reference` | `Marker.Reference` |
|-----------|:------------------:|:------------------:|
| `accuracy` | ✓ | ✓ |
| `enabled` | ✓ | ✓ |
| `location` | ✓ | ✓ |
| `location_accuracy` | ✓ | ✗ |
| `location_enabled` | ✓ | ✗ |
| `rotation` | ✓ | ✗ |
| `rotation_accuracy` | ✓ | ✗ |
| `rotation_enabled` | ✓ | ✗ |

(Confirmed by introspection on Metashape 2.2.2.)

The runtime consequence: code that works for `camera.reference`
raises `AttributeError` on `marker.reference` for any of the
five missing attributes. A defensive idiom for code that handles
both:

```python
def set_location_prior(ref, location, location_accuracy, *, enabled=True):
    """Works for both Camera.reference and Marker.reference."""
    ref.location = Metashape.Vector(location)

    if hasattr(ref, "location_accuracy"):     # Camera
        ref.location_accuracy = Metashape.Vector(location_accuracy)
    else:                                     # Marker — uses single accuracy
        ref.accuracy = Metashape.Vector(location_accuracy)

    if hasattr(ref, "location_enabled"):      # Camera
        ref.location_enabled = enabled
    else:                                     # Marker — atomic toggle only
        ref.enabled = enabled
```

The reasons for the asymmetry are sensible — markers are 3D
points, so orientation is meaningless; the all-or-nothing
`enabled` toggle reflects that markers either have a known
location or don't. But the API documentation does not
foreground the asymmetry, and code that assumes the Camera
shape on Markers fails with `AttributeError` rather than a clear
error message. See also the *Caveats* section of [Programmatic
marker placement and pinning](../../workflow/markers-gcps/programmatic-marker-placement.md).

## Caveats

- **`chunk.transform.matrix` is read/write.** Setting it to a
  custom transformation moves the chunk in world space without
  re-running `alignCameras`. Useful for forcing alignment to a
  known external reference frame; risky if the existing
  alignment depends on a specific chunk-frame convention.
- **`camera.transform` may be `None`** for unaligned cameras.
  Always check before applying `T.mulp(...)`.
- **`T.mulp(v)` vs `T * v`.** The matrix-times-Vector form
  `T * v` requires `v` to be a 4-component homogeneous vector;
  `T.mulp(v)` (mul-point) accepts a 3-vector and applies the
  full affine transform including translation. For points in
  3D space (as opposed to direction vectors), use `mulp`.
- **The chunk's CRS controls how reference data is interpreted,
  not where camera poses live.** A chunk with
  `chunk.crs = Metashape.CoordinateSystem("EPSG::4326")` still
  has `camera.transform` in chunk-local space; the CRS controls
  how `chunk.reference` and `camera.reference.location` are
  parsed and displayed.

## Runnable demonstration on the Aerial-with-GCPs sample dataset

The script below runs through the full chunk-local-to-world
comparison cycle, on the
[Aerial-with-GCPs](../../reference/sample-data.md#aerial-images-with-gcps)
dataset which has a real CRS and real GCPs.

> **Demo verified:** ✗ — pending Tier 3 reproduction on
> Metashape Pro 2.2 / 2.3 with the *Aerial-with-GCPs* sample
> dataset. The underlying APIs are introspection-verified; the
> demo as written has not been run end-to-end.

```python
"""Confirm chunk-local vs world-frame distinction with comparison
to reference data.

Pre-condition: Aerial-with-GCPs project loaded, fully aligned,
GCPs imported and applied.
"""
import Metashape

chunk = Metashape.app.document.chunk
T = chunk.transform.matrix
print(f"chunk.transform.matrix (chunk-local → world):")
print(T)
print()

# Camera positions in chunk-local vs world frame.
print(f"{'label':>20}  {'local pos':>30}  {'world pos':>30}  {'reference':>30}")
for camera in chunk.cameras[:5]:
    if camera.transform is None:
        continue
    loc_local = camera.transform.translation()
    loc_world = T.mulp(loc_local)
    ref = camera.reference.location
    print(f"{camera.label:>20}  "
          f"{tuple(round(v, 2) for v in loc_local)}  "
          f"{tuple(round(v, 2) for v in loc_world)}  "
          f"{tuple(round(v, 2) for v in ref) if ref else '(no ref)'}")

# Marker world positions (markers are stored chunk-local; same rule).
print()
for marker in chunk.markers[:3]:
    if marker.position is None:
        continue
    pos_local = marker.position
    pos_world = T.mulp(pos_local)
    ref = marker.reference.location
    print(f"marker {marker.label}: "
          f"local={tuple(round(v, 2) for v in pos_local)}  "
          f"world={tuple(round(v, 2) for v in pos_world)}  "
          f"reference={tuple(round(v, 2) for v in ref) if ref else '(no ref)'}")
```

**Expected output:** `local pos` and `world pos` differ in
general; `world pos` matches `reference` to within the bundle's
RMS (typically a few centimetres on aerial-with-GCPs). If
`world pos` does not match `reference`, the bundle has not yet
absorbed the references — run `chunk.optimizeCameras(…)` first
(see [When does `optimizeCameras` actually do something?](../../workflow/optimization/when-optimize-cameras-helps.md)).

## See also

- [Choosing camera axes: aerial vs terrestrial (and YPR vs OPK)](../scripting/choosing-rotation-representation.md)

## References

- *Metashape Python Reference* (2.3.1), `Chunk.transform`,
  `Chunk.transform.matrix`, `Camera.transform`,
  `Camera.reference`, `Marker.reference`, `Reference.accuracy`
  family.
- *Metashape Python Reference* (2.3.1), `Metashape.Matrix.mulp`
  — mul-point form for 3D homogeneous-affine application.
- [Synthetic position priors via `ReferencePreselectionSource`](../../workflow/alignment/synthetic-priors-reference-preselection.md) — uses the per-axis accuracy machinery
  systematically.
- [Programmatic marker placement and pinning](../../workflow/markers-gcps/programmatic-marker-placement.md) — Marker.Reference workflow; affected by the
  asymmetry described here.
- [The chunk's internal coordinate system: arbitrary scale and `chunk.transform.scale`](../scripting/chunk-internal-scale-and-units.md) — deep dive on the arbitrary-scale factor and how to convert chunk-internal distances to real metres.
- Related: [Importing camera orientation: EXIF, omega-phi-kappa,
  and yaw/pitch/roll](../../workflow/project-setup/importing-camera-orientation.md) — uses the per-axis `Vector` accuracy machinery
  documented here for camera orientation imports.
