---
title: "Saving estimated reference values to file: location, rotation, error, and sigma"
status: unverified
applies_to: Metashape Pro 2.x — pattern from `save_estimated_reference.py` in the official metashape-scripts repo
edition: Pro
last_reviewed: 2026-06-04
diataxis: how-to
confidence: high
---

# Saving estimated reference values to file: location, rotation, error, and sigma

> **Confidence:** *high.* The script lives in Agisoft's
> official [`metashape-scripts`](https://github.com/agisoft-llc/metashape-scripts)
> repo, is tested against Metashape 2.3, and uses
> introspection-confirmed APIs (`Camera.location_covariance`,
> `Sensor.antenna`, `crs.localframe`, `crs.geoccs`).

## Problem

After running *Align Photos* + *Optimize Cameras*, you want a
**file output** containing the estimated camera positions,
rotations, and their uncertainty estimates — typically for:

- **GPS / INS sensor calibration reports.** The estimated
  values + the per-axis sigma let downstream tools assess
  the inertial sensor's quality.
- **External GIS / surveying workflows.** The CSV is the
  hand-off format for clients who don't run Metashape.
- **QA archives.** The "snapshot of estimated values at
  alignment time" supports later audits ("did anything drift
  between the alignment in March and the reprocess in
  October?").

Metashape's GUI has *File → Export → Export Reference* but
exposes a limited subset of fields. The scripted version
includes:

- Estimated location (in CRS coords).
- Estimated rotation in the chunk's configured Euler-angle
  convention (yaw-pitch-roll or omega-phi-kappa).
- Per-axis location error (estimated minus reference, in metres).
- Per-axis rotation error (estimated minus reference, in degrees).
- Per-axis location sigma (standard deviation from the bundle's
  covariance).
- Per-axis rotation sigma.
- Antenna offset corrections (where the GPS antenna is mounted
  off-axis from the camera's optical centre).

The full implementation is in
[`save_estimated_reference.py`](https://github.com/agisoft-llc/metashape-scripts/blob/master/src/save_estimated_reference.py).
This article covers the operational pattern.

## Why this is harder than it looks

Three subtleties make a naive "subtract reference from estimated"
recipe wrong for high-precision applications:

### 1. The GPS antenna isn't at the camera centre

For drone surveys, the GPS antenna is typically several
centimetres above the camera's optical centre. The reference
*location* is where the antenna was when the photo was taken;
the estimated *location* (from the bundle) is the camera's
optical centre. Subtracting these directly produces a 5-50 cm
systematic bias.

The fix: encode the antenna's position relative to the camera
in `sensor.antenna.location` (a `Vector`) and rotation in
`sensor.antenna.rotation`. The script's
`getAntennaTransform(sensor)` reads these and applies the
transform when computing the estimated location:

```python
location_ecef = camera_transform.translation() + camera_transform.rotation() * antenna_transform.translation()
```

If your sensor doesn't have antenna offsets configured, the
defaults are zero and the recipe collapses to simple
location subtraction.

### 2. Earth curvature matters for large project areas

Subtracting two CRS values (e.g., longitude / latitude) gives
degrees, not metres. Naive recipes that compute
`(estimated.x - reference.x)**2 + ...` ship degrees-squared,
not metres-squared.

The fix: convert both to ECEF (Earth-Centered Earth-Fixed)
geocentric coordinates, subtract there, then transform the
difference vector back to a local frame for per-axis
interpretation:

> **Demo verified:** ✗ — pending Tier 3 reproduction on a real Metashape install.

```python
# Both in geocentric metres
estimated_ecef = camera_transform.translation()
reference_ecef = crs.unproject(camera.reference.location)

# Difference in geocentric metres
err_ecef = estimated_ecef - reference_ecef

# Project to local north-east-up frame for per-axis values
local_frame = crs.localframe(estimated_ecef)
err_local = local_frame.rotation() * err_ecef
# err_local.x = north error, err_local.y = east error, err_local.z = up error
```

The `crs.localframe(point)` method gives you the rotation
matrix from ECEF to north-east-up at that specific point —
this is what makes the per-axis error interpretation correct
across large project extents.

### 3. Sigma comes from the bundle's covariance, not from
   the residual

The "uncertainty" of an estimated camera position is what the
bundle-adjustment produced as the estimate's variance, NOT
the residual against the reference. These are different
quantities:

- **Residual error** = estimated minus reference (a value).
- **Sigma / standard deviation** = how confidently the bundle
  knows the estimate, derived from the inverse Hessian of the
  least-squares cost.

The script reads `camera.location_covariance` (a 3×3 matrix)
and projects it through the local-frame rotation to get
per-axis sigmas in metres:

> **Demo verified:** ✗ — pending Tier 3 reproduction on a real Metashape install.

```python
T = crs.localframe(location_ecef) * transform
R = T.rotation() * T.scale()
cov = R * camera.location_covariance * R.t()
sigma = [math.sqrt(cov[i, i]) for i in range(3)]
```

For rotation-uncertainty, the script uses
`camera.rotation_covariance` plus partial-derivative matrices
for the Euler-angle parameterisation.

## Recipe — minimal CSV export

For a basic implementation that covers the most common case
(no antenna offset, no covariance):

> **Demo verified:** ✗ — pending Tier 3 reproduction on a real Metashape install.

```python
import math
import Metashape

chunk = Metashape.app.document.chunk
T = chunk.transform.matrix
crs = chunk.crs

with open("/path/estimated_reference.csv", "w") as fh:
    fh.write("label,est_x,est_y,est_z,err_x,err_y,err_z,err_total_m\n")
    for camera in chunk.cameras:
        if not camera.transform:
            continue

        # Estimated location (in CRS)
        estimated_world = T.mulp(camera.center)
        estimated_crs = crs.project(estimated_world)

        # Reference location (already in CRS)
        if not camera.reference.location:
            err_x = err_y = err_z = err_total = ""
        else:
            ref_ecef = crs.unproject(camera.reference.location)
            err_ecef = estimated_world - ref_ecef
            local_frame = crs.localframe(estimated_world)
            err_local = local_frame.rotation() * err_ecef
            err_x = f"{err_local.x:.4f}"
            err_y = f"{err_local.y:.4f}"
            err_z = f"{err_local.z:.4f}"
            err_total = f"{err_ecef.norm():.4f}"

        fh.write(
            f"{camera.label},"
            f"{estimated_crs.x:.6f},{estimated_crs.y:.6f},{estimated_crs.z:.4f},"
            f"{err_x},{err_y},{err_z},{err_total}\n"
        )
```

For the production version with antenna offset, sigma, and the
full Euler-angle output, the [`save_estimated_reference.py`
script](https://github.com/agisoft-llc/metashape-scripts/blob/master/src/save_estimated_reference.py)
runs the above plus the covariance-projection mathematics and
writes a richer CSV.

## Recipe — including sigma values

For projects where covariance is meaningful (large-project
bundle adjustments where the per-camera uncertainty varies
across the chunk):

> **Demo verified:** ✗ — pending Tier 3 reproduction on a real Metashape install.

```python
import math
import Metashape

chunk = Metashape.app.document.chunk
T = chunk.transform.matrix
crs = chunk.crs

for camera in chunk.cameras:
    if not camera.transform or not camera.location_covariance:
        continue

    estimated_world = T.mulp(camera.center)
    local_frame = crs.localframe(estimated_world)

    # Project covariance to local frame
    R = local_frame.rotation() * T.rotation() * T.scale()
    cov_local = R * camera.location_covariance * R.t()

    sigma_x = math.sqrt(cov_local[0, 0])
    sigma_y = math.sqrt(cov_local[1, 1])
    sigma_z = math.sqrt(cov_local[2, 2])

    print(f"{camera.label}: sigma = ({sigma_x:.4f}, {sigma_y:.4f}, {sigma_z:.4f}) m")
```

`camera.location_covariance` is None for cameras the bundle
didn't include (unaligned cameras, cameras the user manually
disabled). Always check before using.

## When sigma values are NOT available

Two causes:

- **Camera unaligned.** No bundle estimate ⇒ no covariance.
- **Bundle didn't compute covariance.** This is the default
  in older Metashape versions and for some `optimizeCameras`
  parameter combinations. To force computation, ensure
  `chunk.optimizeCameras(adaptive_fitting=True)` ran with
  recent versions; covariance is computed automatically as
  part of the bundle adjustment.

## Caveats

- **Antenna offsets are per-sensor, not per-camera.** Set
  them once for each `Sensor` (typically once per drone /
  sensor model). Cameras inherit from their `camera.sensor`.
- **The script's `getCartesianCrs` falls back to LOCAL.**
  When `chunk.crs` has no defined geocentric system (e.g.,
  un-georeferenced project), the script uses
  `Metashape.CoordinateSystem('LOCAL')`. This means the
  output values are in chunk-local metres, not real-world
  coordinates.
- **`euler_angles` choice affects the rotation output.**
  `chunk.euler_angles` can be YPR (yaw-pitch-roll, drone
  convention) or OPK (omega-phi-kappa, photogrammetry
  convention). The script reads this value and configures
  output accordingly. For mixed-convention environments,
  set this explicitly before exporting.
- **Sigma values reflect the BA's confidence, not absolute
  truth.** A 1cm sigma means the bundle thinks it knows the
  position to ±1cm; this can be wrong if the bundle has
  systematic biases (poor GCP distribution, lens distortion
  miscalibration, etc.).
- **CSV format vs Reference-pane format.** Metashape's
  *Export Reference* exports a specific format with
  fixed column ordering. The script's CSV is more flexible
  but won't round-trip back through *Import Reference* without
  a format-conversion step.

## See also

- [Choosing camera axes: aerial vs terrestrial (and YPR vs OPK)](../scripting/choosing-rotation-representation.md)
- [Camera reference error: per-camera location and orientation
  in Python](camera-reference-error-python.md)
  — the simpler, no-antenna-offset, no-sigma version of this
  pattern.
- [Computing camera direction vectors and look-at points](../scripting/camera-direction-vectors.md)
  — uses similar `crs.localframe` mathematics.
- [DJI metadata: altitude semantics and RTK XMP accuracy tags](../../workflow/project-setup/dji-drone-metadata.md)
  — how `camera.reference.location_accuracy` gets populated
  from drone metadata.
- [Reprojection error analysis: per-camera and per-tie-point](reprojection-error-analysis.md)
  — pixel-space residuals (different metric, different
  question).

## References

- [`save_estimated_reference.py`](https://github.com/agisoft-llc/metashape-scripts/blob/master/src/save_estimated_reference.py)
  — the canonical script implementation.
- [*How to calculate estimated Exterior Orientation parameters for the cameras using Python* (Agisoft KB)](https://agisoft.freshdesk.com/support/solutions/articles/31000145016)
  — Agisoft's pointer to the script, noting it also accounts for
  GPS/INS antenna offsets and meridian convergence.
- *Metashape Python API Reference* (2.3.1):
  `Camera.transform`, `Camera.center`, `Camera.location_covariance`,
  `Camera.rotation_covariance`, `Camera.reference`,
  `Sensor.antenna`, `Antenna.location`, `Antenna.rotation`,
  `Antenna.location_ref`, `Antenna.rotation_ref`,
  `Chunk.transform`, `Chunk.crs`, `Chunk.euler_angles`,
  `CoordinateSystem.localframe`, `CoordinateSystem.unproject`,
  `CoordinateSystem.geoccs`, `CoordinateSystem.transform`,
  `CoordinateSystem.datumTransform`, `Utils.mat2euler`,
  `Utils.dmat2euler`.

