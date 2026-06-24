---
title: "`sensor.calibration` vs `sensor.user_calib` — initial vs adjusted values"
status: unverified
applies_to: Metashape Pro 2.x — and unchanged from PhotoScan 1.x
edition: Pro
last_reviewed: 2026-05-23
diataxis: explanation
confidence: high
---

# `sensor.calibration` vs `sensor.user_calib` — initial vs adjusted values

> **Confidence:** *high.* The initial-vs-adjusted distinction is
> directly attested by Agisoft support in a 2025 forum reply with
> permalink, and the full `Sensor.Calibration` /
> `Sensor.user_calib` surface is introspection-confirmed on
> Metashape 2.2.

`Metashape.Sensor` carries **two `Calibration` objects** — same
Python type, different roles in the bundle. The Python API
documentation does not foreground the distinction; misusing
either is a common script bug. This article documents which is
which, when each is the right write target, and how the two
relate to the GUI's *Camera Calibration* dialog.

## The distinction

| Object | Role | GUI equivalent | Read after… | Write before… |
|--------|------|----------------|-------------|---------------|
| `sensor.user_calib` | **Initial** values (bundle's starting point) | *Initial* tab of *Camera Calibration* | initial assignment | running `alignCameras` (where it matters) |
| `sensor.calibration` | **Adjusted** values (bundle output) | *Adjusted* tab of *Camera Calibration* | `alignCameras` / `optimizeCameras` | (rarely written manually) |

The canonical-thread statement on the distinction:

> "`user_calib` is similar to the input to Initial values tab of
> Camera Calibration dialog, whereas `calibration` represent
> adjusted values. If you need to input pre-calibrated values,
> then use `user_calib` and optionally fix all the calibration
> parameters." — Alexey Pasumansky, 2025-09-27, Metashape 2.2
> ([permalink](https://www.agisoft.com/forum/index.php?topic=17357.msg74309#msg74309))

## Why it matters

Two common script bugs the distinction catches:

### Bug 1 — Writing to `sensor.calibration` before alignment

```python
# WRONG.
sensor.calibration.f = 4500.0
sensor.calibration.cx = 0.0
chunk.alignCameras()                # discards the values you wrote
print(sensor.calibration.f)         # bundle-refined value, not 4500
```

The bundle reads from `user_calib` (or from defaults if
`user_calib` is empty) when it computes its own calibration; the
values you wrote to `sensor.calibration` are silently discarded.

### Bug 2 — Reading `sensor.user_calib` after alignment

```python
# WRONG (assuming you wanted the bundle-refined values).
sensor.user_calib.f = 4500.0
chunk.alignCameras()
print(sensor.user_calib.f)          # still 4500 — input, not output
print(sensor.calibration.f)         # bundle-refined — what you wanted
```

`user_calib` is the *input* to the bundle and isn't modified by
`alignCameras` or `optimizeCameras`. To get the refined
calibration, read `sensor.calibration`.

## When to write to `user_calib`

The three operational scenarios:

### Pre-calibrated camera, fix during BA

When a camera has been factory-calibrated or lab-calibrated,
its intrinsics should not be refined by the bundle (the bundle
might over-fit to the noise in your tie points). Write
`user_calib` and lock it:

```python
sensor.user_calib.f  = 4500.0
sensor.user_calib.cx = 12.5
sensor.user_calib.cy = -8.3
sensor.user_calib.k1 = -0.0123
# ... other coefficients
sensor.fixed_calibration = True     # don't refine during BA
```

After alignment, `sensor.calibration` will equal `sensor.user_calib`
(the bundle was instructed to leave it alone).

### Seed values, allow refinement

When you have a good starting point (e.g., a previous project's
result, or a manufacturer-claimed approximation) but want the
bundle to refine it:

```python
sensor.user_calib = previous_calibration  # Calibration instance
sensor.fixed_calibration = False          # let BA refine (default)
```

The bundle starts from `user_calib` and converges to a refined
solution in `sensor.calibration`. Better starting points
typically converge faster and to better local minima.

### Fine-grained parameter fixing

`fixed_calibration` is all-or-nothing. For partial fixing —
e.g., trust the focal length but allow distortion-coefficient
refinement — use `fixed_params`:

```python
sensor.fixed_params = ['f', 'cx', 'cy']     # fix only intrinsic centre
# 'fixed_params' values are parameter-name strings;
# bundle refines anything not in the list.
```

The valid parameter names match the `Calibration` attributes
(`'f'`, `'cx'`, `'cy'`, `'k1'`, `'k2'`, `'k3'`, `'k4'`, `'p1'`,
`'p2'`, `'b1'`, `'b2'`).

## When to read `sensor.calibration`

Always after `alignCameras` or `optimizeCameras`. Examples:

```python
# Report bundle-refined intrinsics.
calib = sensor.calibration
print(f"f  = {calib.f:.3f} px")
print(f"cx = {calib.cx:.3f}, cy = {calib.cy:.3f}")
print(f"k1 = {calib.k1:.4e}, k2 = {calib.k2:.4e}")

# Save bundle-refined intrinsics for reuse in another project.
sensor.calibration.save("/path/to/refined-calibration.xml")
```

## Caveats

- **`user_calib.f` defaults to a nominal value (typically 50 px
  for an empty sensor, or derived from EXIF for a sensor created
  from images).** The default is rarely a useful starting point;
  populate explicitly when you have pre-calibration data.
- **`fixed_calibration = True` and `fixed_params = [...]` are
  not mutually exclusive but usually you want only one.** If
  both are set, the all-or-nothing `fixed_calibration = True`
  takes precedence; `fixed_params` becomes a no-op. Set one or
  the other, not both.
- **The two `Calibration` objects are independent instances.**
  Writing `sensor.calibration.f = 100` does *not* update
  `sensor.user_calib.f` and vice versa.
- **`copy()` makes a value-equal but identity-distinct copy.**
  `sensor.user_calib = sensor.calibration.copy()` snapshots the
  current adjusted values as the new initial values — useful
  for "freeze the bundle's result and reuse it" workflows.
- **Slave sensors of a multi-camera rig inherit calibration
  from the master.** Writing `slave_sensor.user_calib` directly
  may be silently overridden when the rig declaration is
  applied. Verify with `slave_sensor.master == sensor` first
  (see [Declaring a fixed-geometry multi-camera rig in Python](multi-camera-rig-python.md)).

## Runnable demonstration on the Aerial-with-GCPs sample dataset

The script below demonstrates the read/write cycle: write
known values to `user_calib`, run alignment, observe
`user_calib` unchanged and `calibration` refined.

> **Demo verified:** ✗ — pending Tier 3 reproduction on Metashape
> Pro 2.2 / 2.3 with the *Aerial-with-GCPs* sample dataset. The
> underlying API surface is introspection-confirmed; the
> initial-vs-adjusted distinction is forum-attested in the
> source thread.

```python
"""Demonstrate that user_calib is input, calibration is output.

Pre-condition: a chunk with images added but NOT yet aligned.
"""
import Metashape

chunk = Metashape.app.document.chunk
sensor = chunk.sensors[0]

# Known-wrong starting focal length to make the bundle's
# adjustment visible.
sensor.user_calib.f = 100.0
sensor.user_calib.cx = 0.0
sensor.user_calib.cy = 0.0
sensor.fixed_calibration = False  # let BA refine

print(f"Before alignment:")
print(f"  user_calib.f   = {sensor.user_calib.f}")
print(f"  calibration.f  = {sensor.calibration.f}")
print()

# Align.
chunk.matchPhotos(downscale=1)
chunk.alignCameras()

print(f"After alignment:")
print(f"  user_calib.f   = {sensor.user_calib.f}    (unchanged — input)")
print(f"  calibration.f  = {sensor.calibration.f:.3f}    (bundle-refined — output)")
print()

# A fresh-by-construction sensor would use defaults; reading
# user_calib of a sensor created by addPhotos returns whatever
# EXIF-derived initial estimate was used.
```

**Expected output:** `user_calib.f` is still `100.0` after
alignment; `calibration.f` is the bundle's refined value (which
should be close to the true focal length of the camera, in
pixels).

## References

- [Forum thread, *sensor.calibration vs sensor.user_calib*, 2025](https://www.agisoft.com/forum/index.php?topic=17357.0)
  — primary source; the clarification (msg 74305,
  2025-09-27).
- [Forum thread, *Fail to load calibration*, 2020](https://www.agisoft.com/forum/index.php?topic=11491.0)
  — operational case showing user_calib.load misuse.
- [Forum thread, *calibration in each photo?*, 2024](https://www.agisoft.com/forum/index.php?topic=16395.0)
  — companion thread on per-image vs per-sensor calibration.
- *Metashape Python Reference* (2.3.1), `Sensor.calibration`,
  `Sensor.user_calib`, `Sensor.fixed_calibration`,
  `Sensor.fixed_params`.
- [Metashape's distortion model and converting to OpenCV / Colmap](distortion-model-opencv-colmap.md) — companion article on the conventions used by
  both `user_calib` and `calibration`.
- [Programmatic calibration import / export](calibration-import-export.md) — uses `user_calib` as the load target.
