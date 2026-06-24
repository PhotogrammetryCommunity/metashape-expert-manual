---
title: "Programmatic calibration import / export"
status: unverified
applies_to: Metashape Pro 2.x — and unchanged from PhotoScan 1.x
edition: Pro
last_reviewed: 2026-05-23
diataxis: how-to
confidence: medium
---

# Programmatic calibration import / export
> **Confidence:** *medium.* The API surface is
> introspection-confirmed; specific load-format compatibility
> across third-party tools varies and is best verified per
> tool. The XML round-trip (Metashape → file → Metashape) is
> straightforward; cross-tool transfer requires the convention
> mapping documented in [N.1](distortion-model-opencv-colmap.md).

Three reproducible patterns for moving calibration between
projects, between Metashape and external tools, and between
runs of the same project.

## Pattern 1 — Externally-calibrated camera, fixed during BA

When a camera has been factory-calibrated or lab-calibrated,
the calibration should be loaded as the bundle's starting point
**and held fixed** during `alignCameras` / `optimizeCameras`.
The bundle uses the values verbatim:

```python
import Metashape

chunk = Metashape.app.document.chunk
sensor = chunk.sensors[0]

# Load XML (Metashape native format).
calib = Metashape.Calibration()
calib.load("/path/to/factory-calibration.xml")

# Match the loaded calibration to the sensor's image dimensions.
calib.width  = sensor.width
calib.height = sensor.height

# Assign to the sensor's INITIAL values.
sensor.user_calib = calib

# Fix all parameters during BA — bundle won't refine.
sensor.fixed_calibration = True

# Run alignment.
chunk.matchPhotos(downscale=1)
chunk.alignCameras()

# After alignment, sensor.calibration == sensor.user_calib.
```

The `sensor.fixed_calibration = True` is the load-bearing flag.
Without it, the bundle still uses `user_calib` as the starting
point but refines the values, which defeats the purpose of
loading the factory calibration.

## Pattern 2 — Seed values, allow refinement

When you have a good approximation but want the bundle to
refine it (e.g., a previous project's calibration of the same
rig used in a new scene):

```python
calib = Metashape.Calibration()
calib.load("/path/to/previous-project-calibration.xml")
calib.width  = sensor.width
calib.height = sensor.height

sensor.user_calib = calib
sensor.fixed_calibration = False  # default; let BA refine

chunk.matchPhotos(downscale=1)
chunk.alignCameras()

# sensor.calibration now holds the refined values, seeded by
# user_calib. Save them for the next project:
sensor.calibration.save("/path/to/refined-calibration.xml")
```

This is the canonical "calibration-handoff" pattern across
projects of the same physical rig. Each project's bundle
benefits from the previous project's converged calibration.

## Pattern 3 — Save bundle output for reuse

After a successful alignment, save the bundle-refined
calibration so future projects can use it:

```python
sensor.calibration.save(
    "/path/to/output.xml",
    format=Metashape.CalibrationFormatXML,
    label=sensor.label,            # optional, for traceability
)
```

Optional kwargs allow embedding additional metadata (label,
pixel_size for physical conversion, etc.) — useful when sharing
the file outside Metashape.

## XML format compatibility

The default `CalibrationFormatXML` is Metashape's native format
and is the most reliable for round-trips. Other formats — the
exact set varies by version — may include OpenCV, Photomodeler,
and similar; introspect on your installed version:

```python
print([n for n in dir(Metashape.CalibrationFormat) if not n.startswith("_")])
# ['CalibrationFormatXML', 'CalibrationFormatOpenCV', ...]
```

Cross-format conversion is **not lossless** when the source
format uses different conventions (P1/P2 swap, transformation
direction). See [N.1 — Metashape's distortion model and
converting to OpenCV / Colmap](distortion-model-opencv-colmap.md)
for the convention details.

## Caveats

- **`Calibration.width` and `.height` must match the sensor's
  image dimensions.** Loading a calibration with mismatched
  dimensions does not raise; the bundle silently uses incorrect
  pixel-normalised values. Always set
  `calib.width = sensor.width; calib.height = sensor.height`
  after `load`.
- **`load` populates `Calibration` in place but doesn't attach
  it to a sensor.** You must assign with `sensor.user_calib =
  calib` (or `sensor.calibration = calib` if you really know
  what you're doing — usually not what you want, see
  [N.2 — `sensor.calibration` vs `sensor.user_calib`](sensor-calibration-vs-user-calib.md)).
- **`save` from `sensor.user_calib` writes the *initial* values,
  not the bundle-refined ones.** To save the refined values,
  `sensor.calibration.save(...)`.
- **Multi-sensor projects need per-sensor calibrations.** A
  factory calibration for sensor A is wrong for sensor B even if
  they're "the same camera model" — sensor variation is real.
  Iterate: `for sensor in chunk.sensors: ...`.
- **Slave sensors of a multi-camera rig inherit from master.**
  The slave's `user_calib` may be silently overridden by the
  rig declaration. Skip slaves with the documented idiom:

  ```python
  for sensor in chunk.sensors:
      if sensor.master and sensor.master != sensor:
          continue   # slave; skip
      sensor.user_calib = factory_calib
  ```

## Runnable demonstration on the Aerial-with-GCPs sample dataset

The script below performs a save → load round-trip on a
sensor's calibration and verifies the result is byte-equal.

> **Demo verified:** ✗ — pending Tier 3 reproduction on Metashape
> Pro 2.2 / 2.3 with the *Aerial-with-GCPs* sample dataset. The
> XML round-trip is mechanically straightforward but warrants
> end-to-end confirmation.

```python
"""Save → load round-trip of a sensor's calibration."""
import tempfile
from pathlib import Path
import Metashape

chunk = Metashape.app.document.chunk
sensor = chunk.sensors[0]

# Snapshot the current calibration values.
src = sensor.calibration
src_values = {
    n: getattr(src, n)
    for n in ("f", "cx", "cy", "k1", "k2", "k3", "k4", "p1", "p2",
              "b1", "b2", "width", "height")
}

# Save and load.
with tempfile.NamedTemporaryFile(suffix=".xml", delete=False) as f:
    tmp_path = f.name

src.save(tmp_path)

reloaded = Metashape.Calibration()
reloaded.load(tmp_path)

# Compare.
print(f"{'param':>10}  {'original':>15}  {'reloaded':>15}  {'match':>6}")
all_match = True
for name, src_val in src_values.items():
    reload_val = getattr(reloaded, name)
    match = "✓" if abs(reload_val - src_val) < 1e-6 else "✗"
    if match == "✗":
        all_match = False
    print(f"{name:>10}  {src_val:>15.6f}  {reload_val:>15.6f}  {match:>6}")

print(f"\nRound-trip {'OK' if all_match else 'FAILED'}")
Path(tmp_path).unlink()
```

**Expected output:** every parameter matches with `✓`. If any
parameter differs by more than 1e-6, the XML format version may
have changed between Metashape versions, or
`Calibration.load`/`.save` may not be using the same precision
on both ends.

## References

- [Forum thread, *import calibration from other sw*, 2012](https://www.agisoft.com/forum/index.php?topic=563.0)
  — the framing of the format-compatibility question.
- [Forum thread, *Python script on precalibrated camera
  calibration parameters*, 2014](https://www.agisoft.com/forum/index.php?topic=1748.0)
  — community examples of programmatic loading.
- [Forum thread, *How to load calibration Camera parameter in
  batch file*, 2017](https://www.agisoft.com/forum/index.php?topic=6084.0)
  — batch-processing context.
- *Metashape Python Reference* (2.3.1), `Calibration.load`,
  `Calibration.save`, `Calibration` attribute set.
- [Metashape's distortion model and converting to OpenCV /
  Colmap](distortion-model-opencv-colmap.md) —
  prerequisite for cross-tool calibration transfer.
- [`sensor.calibration` vs `sensor.user_calib`](sensor-calibration-vs-user-calib.md) — the load target / save source distinction.
