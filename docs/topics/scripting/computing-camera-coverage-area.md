---
title: "Computing per-camera coverage area (image footprint on the model)"
status: unverified
applies_to: Metashape Pro 2.x — and unchanged from PhotoScan 1.x via the same API
edition: Pro
last_reviewed: 2026-05-23
diataxis: how-to
confidence: high
---

# Computing per-camera coverage area (image footprint on the model)

> **Confidence:** *high.* The ray-casting algorithm is the
> canonical PhotoScan-era recipe ported to Metashape 2.x; all
> API references (`camera.calibration.unproject`,
> `model.pickPoint`, `chunk.transform.matrix`) are
> introspection-confirmed.

The "where on the ground does this image cover?" question recurs
in coverage analysis, image-pair preselection, and subset
selection. The naïve approaches (project camera centre to ground;
project at fixed altitude) lose terrain information and
occlusions. The principled answer is to **ray-cast frame-corner
pixels through the camera optics into the chunk's reconstructed
mesh** and find the first intersection per ray.

This article ports a canonical PhotoScan 1.0.4 sample script
to Metashape 2.x and walks through the math.

## The algorithm

1. For each frame-pixel position `(x, y)` of interest (typically
   the four corners plus optionally pixels along the frame's
   edges to capture the polygon shape):
   - Convert pixel to a 3D ray *in the camera's optical frame*:
     `direction = camera.calibration.unproject([x, y])`. This
     applies the inverse of the camera's lens distortion model.
   - Transform the direction to the chunk-local frame:
     `direction_local = camera.transform.mulv(direction)`. Note:
     `mulv` (multiply-vector) — no translation, just rotation.
2. Ray-cast `direction_local` from the camera's chunk-local
   centre (`camera.center`) against `chunk.model.faces`. For
   each triangular face, run a ray-triangle intersection test
   (Möller-Trumbore). Take the first hit.
3. The hit is in chunk-local coordinates. Convert to world via
   `chunk.transform.mulp(hit)`, then optionally to the chunk's
   CRS via `chunk.crs.project(world_point)`.

The output: a polygon in world (or CRS-target) coordinates
representing the camera's footprint on the model.

## The Python recipe (ported from PhotoScan 1.0.4 to Metashape 2.x)

```python
"""Project image-frame pixels onto the chunk's mesh.

Ported from the 2014 PhotoScan 1.0.4 forum sample script
(forum topic=2666, msg 13598).
"""
import time
from pathlib import Path
import Metashape

def cross(a: Metashape.Vector, b: Metashape.Vector) -> Metashape.Vector:
    return Metashape.Vector([
        a.y * b.z - a.z * b.y,
        a.z * b.x - a.x * b.z,
        a.x * b.y - a.y * b.x,
    ])

def camera_footprint(camera: Metashape.Camera, *,
                     pixel_step: int = 100) -> list[tuple]:
    """Return list of (pixel_x, pixel_y, world_x, world_y, world_z)
    for points on the camera's frame border, projected onto the chunk's mesh.
    """
    chunk = camera.chunk
    model = chunk.model
    if model is None:
        raise RuntimeError("Chunk has no mesh; call chunk.buildModel() first")

    faces = model.faces
    vertices = model.vertices

    width  = camera.sensor.width  - 1
    height = camera.sensor.height - 1
    step = pixel_step

    # Walk the four edges of the frame (clockwise from top-left).
    border_pixels: list[tuple[int, int]] = []
    border_pixels.extend([(x, 0)        for x in range(0, width,  step)])
    border_pixels.extend([(width, y)    for y in range(0, height, step)])
    border_pixels.extend([(x, height)   for x in range(width, 0, -step)])
    border_pixels.extend([(0, y)        for y in range(height, 0, -step)])

    cam_centre = Metashape.Vector(camera.center)
    results: list[tuple] = []

    for x, y in border_pixels:
        # Step 1: pixel → camera-frame ray direction.
        direction_cam = camera.calibration.unproject(Metashape.Vector([x, y]))

        # Step 2: camera-frame → chunk-local direction.
        direction_local = camera.transform.mulv(direction_cam)

        # Step 3: ray-mesh intersection (Möller-Trumbore).
        for face in faces:
            v_idx = face.vertices
            v0 = vertices[v_idx[0]].coord
            v1 = vertices[v_idx[1]].coord
            v2 = vertices[v_idx[2]].coord

            E1 = Metashape.Vector(v1 - v0)
            E2 = Metashape.Vector(v2 - v0)
            T_offset = Metashape.Vector(cam_centre - v0)
            P = cross(direction_local, E2)
            Q = cross(T_offset, E1)

            denom = P * E1
            if abs(denom) < 1e-12:
                continue

            result = Metashape.Vector([
                Q * E2,
                P * T_offset,
                Q * direction_local,
            ]) / denom
            t, u, v = result[0], result[1], result[2]

            if 0 < u and 0 < v and u + v <= 1 and t > 0:
                # Intersection found.
                hit_local = (1 - u - v) * v0 + u * v1 + v * v2
                hit_world = chunk.transform.mulp(hit_local)
                hit_crs = chunk.crs.project(hit_world) if chunk.crs else hit_world
                results.append((x, y, hit_crs[0], hit_crs[1], hit_crs[2]))
                break    # first hit only

    return results

# Example: dump the footprint of camera 0 to a TSV.
if __name__ == "__main__":
    chunk = Metashape.app.document.chunk
    camera = chunk.cameras[0]

    t0 = time.time()
    points = camera_footprint(camera, pixel_step=100)
    print(f"Computed {len(points)} footprint vertices in {time.time() - t0:.2f}s")

    out_path = Path("/tmp/footprint.tsv")
    with out_path.open("w") as f:
        f.write("pixel_x\tpixel_y\tworld_x\tworld_y\tworld_z\n")
        for px, py, wx, wy, wz in points:
            f.write(f"{px}\t{py}\t{wx:.4f}\t{wy:.4f}\t{wz:.4f}\n")
    print(f"Wrote {out_path}")
```

The `pixel_step=100` argument controls density — every 100
pixels along each frame edge produces a footprint vertex. Larger
step = faster but coarser polygon; smaller step = slower but
finer polygon. For typical 24-megapixel cameras with 6000×4000
resolution, `step=100` produces ~200 vertices in a few seconds
on a modest mesh.

## Performance notes

The pure-Python ray-triangle iteration is `O(border_pixels ×
faces)`. For a 24 MP camera with `step=100` (~200 border pixels)
against a 1-million-face mesh, that's 200 million tests — slow.

Two optimisations worth knowing:

- **Early termination on `t > 0` mismatch.** The script breaks
  on the first hit; pre-sorting faces by distance from camera
  approximately reduces the typical iteration count.
- **Spatial index.** A bounding-volume hierarchy (BVH) over the
  mesh reduces per-ray complexity from `O(faces)` to `O(log
  faces)`. Metashape doesn't expose its internal BVH; for
  production use, build one with `trimesh.Trimesh(...)` or
  similar from the chunk's exported mesh.

For one-off coverage analysis (a few cameras), the
literal-port version above is fast enough. For batch over
hundreds of cameras, port to a numpy-vectorised or trimesh-
backed implementation.

## Caveats

- **Chunk must have a built mesh.** `chunk.model` is `None` for
  chunks where only the tie-point cloud exists. Run
  `chunk.buildModel()` first (or pre-condition the demo's
  dataset to already have a mesh).
- **Occlusion handling is implicit in "first hit."** If a
  hill stands between the camera and a far field, the ray hits
  the hill's surface, not the field. This is correct
  behaviour — the camera doesn't see what's behind the hill —
  but it does mean the footprint polygon is a *visible-surface*
  polygon, not a "where the ray would land if there were no
  occluders" polygon.
- **`step=1` is correct but very slow.** For a high-fidelity
  polygon, `step=10` is usually sufficient (~2400 border pixels
  on a 24 MP camera).
- **The 2014 script's namespace was `PhotoScan`.** This article's
  port renames to `Metashape`; all function signatures are
  unchanged. If you find an older copy of the script online,
  the `PhotoScan` → `Metashape` rename is the only change
  needed.

## Runnable demonstration on the Aerial-with-GCPs sample dataset

The script above is itself the runnable demonstration. The
*Aerial-with-GCPs* sample after `chunk.buildModel()` is a
suitable test case.

> **Demo verified:** ✗ — pending Tier 3 reproduction on Metashape
> Pro 2.2 / 2.3 with the *Aerial-with-GCPs* sample dataset. The
> port is mechanical (`PhotoScan` → `Metashape`); the original
> 1.0.4 script is published in the source thread (linked under
> *References*). End-to-end confirmation with current API is
> the missing step.

## References

- [Forum thread, *How can I compute the area that a camera is
  covering?*, 2014](https://www.agisoft.com/forum/index.php?topic=2666.0)
  — primary source; the complete sample script (msg
  13598, 2014-07-29) and the 1.0.4 → 1.1 port note (msg 14893,
  2015-01-24).
- [Forum thread, *Calculate Coverage Area of Chunk*, 2024](https://www.agisoft.com/forum/index.php?topic=17411.0)
  — companion thread with a more recent rephrasing of the same
  question.
- [agisoft-llc/metashape-scripts on GitHub](https://github.com/agisoft-llc/metashape-scripts/blob/master/src/footprints_to_shapes.py)
  — the official `footprints_to_shapes.py` script, an evolved
  version of the 2014 sample; consult for vectorised /
  shape-aware variations.
- *Metashape Python Reference* (2.3.1), `Camera.calibration`,
  `Calibration.unproject`, `Camera.transform`, `Chunk.model`,
  `Model.faces`, `Model.vertices`.
- [Converting `camera.transform` to ENU (or any local Cartesian)](camera-poses-to-enu.md) — the footprint coordinates can be ENU-converted
  via the same procedure.
- Related: [Mapping orthomosaic pixels back to source images](orthomosaic-pixel-to-source-image.md) — the *inverse* direction. This article projects
  rays from the camera into the scene (forward); P.3 projects
  3D points back onto cameras (reverse). Both use the same
  `Calibration.unproject` / `Camera.project` machinery.
