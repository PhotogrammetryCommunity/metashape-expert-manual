---
title: "Choosing camera axes: aerial vs terrestrial (and YPR vs OPK)"
status: unverified
applies_to: "Metashape Pro 2.x and Standard 2.x (GUI Camera axes). The Python Sensor.axes attribute and Sensor.Axes enum were added in 2.3."
edition: "Pro / Standard"
last_reviewed: 2026-08-20
diataxis: explanation
confidence: medium
---

# Choosing camera axes: aerial vs terrestrial (and YPR vs OPK)

> **Confidence:** *medium.* The `Sensor.axes` attribute, the
> `Sensor.Axes` enum (`Aerial`, `Terrestrial`, default `Aerial`), and
> the version in which they were added are Tier 1 introspection-confirmed
> on Metashape 2.3.1 and stated in the Python API Reference change log.
> The axis-direction and platform framing are quoted from the Pro 2.3
> user manual. Gimbal lock at a middle angle of ±90° is general
> Tait–Bryan math. What is *synthesised* here — and so hedged — is the
> link from the terrestrial axes setting to gimbal-lock avoidance, and
> whether the choice perturbs Metashape's internal bundle adjustment
> (which may use rotation matrices) versus only reference entry,
> display, and per-axis priors.

When you set camera-orientation references, two separate things control
how a rotation is interpreted:

1. **Camera axes — Aerial or Terrestrial** (`Sensor.axes`). This selects
   the camera's local axis directions, and it is the **primary
   aerial-vs-terrestrial control**.
2. **Angle elements — YPR / OPK / POK / ANK** (`Chunk.euler_angles`).
   This only selects which angle triple *expresses* the rotation.

For a terrestrial, horizontal-looking capture there are two ways to
avoid the ill-conditioning explained below:

- **Theoretically correct:** set the sensor's **camera axes to
  Terrestrial** (`Sensor.axes`) and keep YPR. This re-centers the
  parameterization so a horizontal camera is well-conditioned.
- **Recommended in practice today:** use **OPK reference angles**
  instead. The camera-axes setting is new in 2.3 and, as of 2.3.1, has
  a serialization bug that silently drops it when a project is saved to
  `.psz` (see *Caveats*), so OPK remains the safe workaround for now.

## The two controls

- **Camera Calibration dialog → *Camera axes* (Aerial / Terrestrial);
  Python `Sensor.axes`.** Selects the camera's axis directions:

  > "Metashape allows to specify camera axes in the Camera Calibration
  > dialog window for aerial and terrestrial data. For aerial data the
  > Z-axis is directed backward, and the Y-axis is directed upward. For
  > terrestrial data, the Y-axis is directed backward and the Z-axis is
  > directed upward."
  > — *Metashape Pro User Manual* 2.3, ch. "General workflow" §
  > "Camera orientation and angles conventions" (Pro 2.3, p. 35)

  The Python API Reference documents `Sensor.axes` as the "Local camera
  coordinate system orientation," of type `Metashape.Sensor.Axes`
  (`Aerial` or `Terrestrial`). It is **per-sensor** and defaults to
  `Aerial`.

- **Reference Settings dialog → angle elements; Python
  `Chunk.euler_angles`.** Selects which triple expresses the rotation:

  > "For images system of angular elements of exterior orientation
  > ([yaw,pitch,roll], [omega, phi, kappa] or [alpha, nu, kappa]) can be
  > switched in the Reference Settings dialog."
  > — *Metashape Pro User Manual* 2.3, § "Camera axes for aerial and
  > terrestrial data" (Pro 2.3, p. 36)

## What the YPR angles describe

YPR angles describe the **platform (aircraft) that carries the camera**,
not the optical axis directly. Under the default (aerial) axes, a zero
triple is a level platform whose camera looks straight *down*:

> "Rotation angles for the camera coordinates in Metashape are defined
> around the following axes: yaw axis runs from top to bottom, pitch
> axis runs from left to right wing of the drone, roll axis runs from
> tail to nose of the drone. Zero values of the rotation angle triple
> define the following camera position aboard: camera looks down to the
> ground, frames are taken in landscape orientation, and horizontal axis
> of the frame is perpendicular to the central (tail-nose) axis of the
> drone."
> — *Metashape Pro User Manual* 2.3, § "Camera axes for aerial and
> terrestrial data" (Pro 2.3, p. 36)

That aerial framing is the default because it is what an airborne IMU
reports:

> "The more common scenario is to load [yaw, pitch, roll] measurements
> directly from the airborne IMU system and, hence, default setting in
> Metashape is to tackle the input values as [yaw, pitch, roll] data."
> — *Metashape Pro User Manual* 2.3, § "INS offset for terrestrial data"

## Why a horizontal camera is awkward under aerial axes: gimbal lock

Every three-angle (Tait–Bryan) parameterization has one orientation
where the first and third axes align and the triple loses a degree of
freedom — **gimbal lock**. For yaw-pitch-roll this is at the **middle
angle, pitch = ±90°**.

Under the **aerial** axes the zero pose is a down-looking camera, so to
make that camera look at the **horizon** the platform must pitch by
±90° — right on the singularity. There, yaw and roll rotate about the
same axis, the `(yaw, pitch, roll)` triple is non-unique, small pose
changes swing yaw and roll wildly, and the per-axis yaw/roll accuracies
you set as priors lose independent meaning. A nadir aerial camera, by
contrast, sits at pitch ≈ 0° — nowhere near the singularity.

Switching the sensor to **Terrestrial** axes changes the local axis
directions (Y backward, Z up rather than Z backward, Y up), which
re-centers the parameterization so the *horizontal-looking* pose — the
normal terrestrial case — is the well-conditioned zero region rather
than the ±90° singularity. That is why terrestrial camera axes is the
*principled* fix for ground-based capture — although, as of 2.3.1, a
serialization bug (see *Caveats*) means OPK references remain the safer
choice in practice.

> **Note (unverified).** The clear, math-level effect is on
> *representing* the orientation near pitch ±90° — entering, importing,
> displaying, and setting per-axis priors. Whether the axes choice also
> changes Metashape's internal bundle adjustment (which may parameterize
> rotations as matrices/quaternions) is not established here; treat that
> as pending Tier 3 verification.

## Setting it in Python

```python
import Metashape

chunk = Metashape.app.document.chunk

# PRIMARY control: aerial vs terrestrial camera axes (Metashape 2.3+).
# Per-sensor; the default is Sensor.Axes.Aerial.
for sensor in chunk.sensors:
    sensor.axes = Metashape.Sensor.Axes.Terrestrial   # ground-based capture

# SEPARATE, largely independent: which angle triple expresses the
# rotation when you import / display / export references.
chunk.euler_angles = Metashape.EulerAnglesYPR         # or EulerAnglesOPK / POK / ANK
```

`Sensor.axes` (and the `Sensor.Axes` enum) were **added in Metashape
2.3**; on 2.2.x and earlier the attribute does not exist, and the
aerial/terrestrial choice is only reachable in the GUI (or not at all,
depending on version). `Chunk.euler_angles` has been available across
2.x.

> **Warning — `.psz` serialization bug (Metashape 2.3.1).** Saving a
> project to `.psz` silently drops a non-default `sensor.axes`: set
> Terrestrial, `doc.save()` to `.psz`, reopen, and the sensor is back to
> `Aerial` with nothing logged. The `.psx` format and
> `exportCameras(..., CamerasFormatXML)` write it correctly, and the
> `.psz` reader honours it — only the `.psz` *writer* omits it. Until
> this is fixed, do not rely on `sensor.axes` in any workflow that
> round-trips through `.psz`; use OPK reference angles instead. The bug
> is logged against 2.3.1 and **may be resolved in 2.3.2 or later** —
> check the current status in the linked report before relying on either
> path.

## Choosing

- **Nadir / near-nadir aerial (drone) survey → Aerial axes (default),
  YPR.** It matches the IMU data and sits far from the pitch-±90°
  singularity.
- **Terrestrial / façade / any horizontal-looking capture → OPK
  reference angles (recommended today).** Terrestrial camera axes with
  YPR is the cleaner solution in principle, but it is new in 2.3 and the
  2.3.1 `.psz` writer silently drops it (see *Caveats*), so prefer OPK
  references until that is fixed (possibly 2.3.2+).
- **YPR vs OPK is a secondary, representation-level choice.** Pick
  whichever your reference data already uses (drone IMU/EXIF → YPR;
  classical aerotriangulation / survey exports → OPK) so you do not
  convert through the singular region.

## Caveats

- **`Sensor.axes` is per-sensor.** Set it on every sensor whose cameras
  need the terrestrial convention, not once on the chunk.
- **Version floor.** `Sensor.axes` / `Sensor.Axes` are 2.3+. Scripts
  targeting 2.2.x cannot set the axes convention through Python.
- **`.psz` silently drops `sensor.axes` (2.3.1).** A non-default
  `sensor.axes` is not written by the `.psz` writer, so saving to `.psz`
  and reopening reverts the sensor to `Aerial` with no warning
  (`.psx` and `exportCameras` XML are unaffected). This is why OPK
  references are recommended over terrestrial axes today. The bug is
  logged against 2.3.1 and **may be fixed in 2.3.2 or later** — verify
  the current status in the linked report before relying on
  `sensor.axes` with `.psz`.
- **Axes and angle elements are independent.** `Sensor.axes` chooses the
  axis directions; `Chunk.euler_angles` chooses the angle triple.
  Changing either re-interprets your `camera.reference.rotation` values.
- **YPR sign conventions are separately subtle.** For the math-vs-drone
  pitch-sign flip when round-tripping YPR through the API, see
  [YPR rotation conventions](ypr-rotation-conventions.md).

## See also

- [YPR rotation conventions: `ypr2mat` vs `camera.reference.rotation`](ypr-rotation-conventions.md)
  — the pitch-sign convention and round-trip recipe within YPR.
- [Importing camera orientation: EXIF, omega-phi-kappa, and yaw/pitch/roll](../../workflow/project-setup/importing-camera-orientation.md)
  — how to populate `camera.reference.rotation` from each source.
- [Chunk frame vs camera frame: per-axis priors](../crs/chunk-frame-vs-camera-frame.md)
  — the per-axis `rotation_accuracy` surface that the singularity
  makes ambiguous.
- [Bundle-adjustment quality: variance factor, overfit testing, and reference detectability](../repeatability-qa/bundle-adjustment-quality.md)
  — where camera rotation references enter as weighted observations.

## References

- *Metashape Pro User Manual* 2.3 (and Standard edition), ch. "General
  workflow" § "Camera orientation and angles conventions" (Pro 2.3,
  p. 35) — the *Camera axes* (aerial / terrestrial) setting and the
  axis directions it selects.
- *Metashape Pro User Manual* 2.3 (and Standard edition), ch. "General
  workflow" § "Camera axes for aerial and terrestrial data" (Pro 2.3,
  p. 36) — the YPR / OPK / POK / ANK axis assignments and the "camera
  looks down at zero" platform convention.
- *Metashape Pro User Manual* 2.3, § "INS offset for terrestrial data"
  — YPR is the default because it is what the airborne IMU provides.
- *Metashape Python API Reference* (2.3.1): `Sensor.axes` ("Local camera
  coordinate system orientation"), the `Sensor.Axes` enum
  (`Aerial`, `Terrestrial`) — both **added in 2.3** per the reference's
  change log — and `Chunk.euler_angles`, `Metashape.EulerAngles`.
- [Forum thread, *Z axis convention for aerial datasets*, 2016](https://www.agisoft.com/forum/index.php?topic=6126.0)
  — the drone-Z-axis-pointing-to-ground canonical pose.
- [Forum bug report, *[2.3.1] doc.save() to .psz silently drops sensor.axes*, 2026](https://www.agisoft.com/forum/index.php?topic=17595.0)
  — Metashape 2.3.1: the `.psz` writer omits `sensor.axes` while `.psx`,
  `exportCameras` XML, and the `.psz` reader all handle it; may be
  addressed in 2.3.2 or later.
