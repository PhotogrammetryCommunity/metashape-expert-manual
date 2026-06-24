---
title: "Diagnostic mesh visualisation: colorize by overlap or altitude"
status: unverified
applies_to: Metashape Pro 2.x — patterns from `colorize_model_by_overlap.py` and `colorize_model_by_altitude.py` in the official metashape-scripts repo
edition: Pro
last_reviewed: 2026-05-30
diataxis: how-to
confidence: high
---

# Diagnostic mesh visualisation: colorize by overlap or altitude

> **Confidence:** *high.* Both patterns are from Agisoft's
> official [`metashape-scripts`](https://github.com/agisoft-llc/metashape-scripts)
> repo. The vertex-colour APIs (`Vertex.color`,
> `Model.setVertexColors`) and the camera-vertex-projection
> arithmetic are introspection-confirmed on Metashape 2.2.

## Problem

A built mesh tells you what was reconstructed but not **why**
some areas look poor. Two common diagnostic questions:

- "Which areas had insufficient camera coverage?" → colorize
  by per-vertex overlap count.
- "What's the elevation distribution across the mesh?" →
  colorize by Z value.

Metashape's GUI shows mesh-quality diagnostics in
*Model → Show Vertex Confidence*, but the results are
qualitative. Programmatic colour-mapping gives you full
control over the colour ramp, breakpoints, and what gets
visualised.

## Recipe — colorize by overlap (camera-coverage diagnostic)

This is the pattern from `colorize_model_by_overlap.py`. For
each vertex, count how many cameras can see it (without
respecting occlusions — a fast approximation), then colour-map
the count onto a discrete palette.

> **Demo verified:** ✗ — pending Tier 3 reproduction on a real Metashape install.

```python
import Metashape

chunk = Metashape.app.document.chunk

if not chunk.model:
    raise RuntimeError("Build the mesh first")

# Discrete palette: white / red / orange / yellow / green / blue
COLORS = [
    (255, 255, 255),   # 0 cameras
    (220,  50,  50),   # 1
    (220, 125,  50),   # 2
    (220, 200,  50),   # 3
    (165, 220,  50),   # 4
    ( 90, 220,  50),   # 5
    ( 50, 220,  85),   # 6
    ( 50, 220, 160),   # 7
    ( 50, 205, 220),   # 8
    ( 50, 125, 220),   # 9
    ( 50,  50, 220),   # 10+
]

# Ensure vertex colours are initialised
if chunk.model.vertices and chunk.model.vertices[0].color is None:
    if hasattr(chunk.model, "setVertexColors"):
        chunk.model.setVertexColors()
    else:
        raise RuntimeError("Run Tools/Model/Colorize Vertices... first")

aligned_cams = [c for c in chunk.cameras if c.transform]
print(f"Counting overlap for {len(chunk.model.vertices)} vertices "
      f"across {len(aligned_cams)} aligned cameras...")

for vert in chunk.model.vertices:
    coord = vert.coord
    overlap = 0
    for camera in aligned_cams:
        # Project the vertex into camera-local coords
        camera_local = camera.transform.inv().mulp(coord)
        # Skip if behind camera (Z is forward in Metashape's convention)
        if camera_local.z < 0:
            continue
        # Cheap visibility check: project to image plane and verify in-bounds
        pixel = camera.sensor.calibration.project(camera_local)
        if pixel is None:
            continue
        if not (0 <= pixel.x < camera.sensor.width and
                0 <= pixel.y < camera.sensor.height):
            continue
        overlap += 1

    # Map count to colour (cap at len(COLORS) - 1)
    color_idx = min(overlap, len(COLORS) - 1)
    vert.color = COLORS[color_idx]
```

After running, *Tools → Model → View Vertex Colors* (or the
default Model view) shows the overlap heatmap.

The script's docstring notes the simplification:

> "Note that it doesn't respect occlusions and just calculates
> number of projections from each vertex to all cameras
> (without any checks for occlusions and distance between the
> vertex and the camera)."

For occlusion-aware overlap (a rendered camera that can't see
the vertex because something is in the way doesn't count), use
[`Model.renderDepth`](../scripting/model-render-depth.md) for
each candidate camera and check whether the vertex's expected
depth matches the rendered depth at the projected pixel.

## Recipe — colorize by altitude (elevation diagnostic)

This is the pattern from `colorize_model_by_altitude.py`. For
each vertex, map its Z value to a colour ramp:

> **Demo verified:** ✗ — pending Tier 3 reproduction on a real Metashape install.

```python
import Metashape

chunk = Metashape.app.document.chunk

if not chunk.model:
    raise RuntimeError("Build the mesh first")

if chunk.model.vertices and chunk.model.vertices[0].color is None:
    if hasattr(chunk.model, "setVertexColors"):
        chunk.model.setVertexColors()

# Find Z range
z_values = [v.coord.z for v in chunk.model.vertices]
z_min, z_max = min(z_values), max(z_values)
z_range = z_max - z_min if z_max > z_min else 1.0

# Rainbow ramp: blue (low) → green → yellow → red (high)
def rainbow(t):
    """t in [0, 1] → (R, G, B)."""
    t = max(0.0, min(1.0, t))
    if t < 0.25:
        return (0, int(255 * (t / 0.25)), 255)
    elif t < 0.5:
        return (0, 255, int(255 * (1 - (t - 0.25) / 0.25)))
    elif t < 0.75:
        return (int(255 * ((t - 0.5) / 0.25)), 255, 0)
    else:
        return (255, int(255 * (1 - (t - 0.75) / 0.25)), 0)

for vert in chunk.model.vertices:
    t = (vert.coord.z - z_min) / z_range
    vert.color = rainbow(t)
```

Adjust the colour ramp's breakpoints (the `0.25 / 0.5 / 0.75`
divisions above) to highlight specific elevation ranges. For
geological / hydrological work, you might want a brown-to-blue
ramp keyed to a known reference elevation (e.g., sea level).

## When to use each

| Diagnostic question | Recipe |
|---------------------|--------|
| "Which areas had poor camera coverage?" | Colorize by overlap |
| "Where is the mesh's geometry visually distributed by elevation?" | Colorize by altitude |
| "Where is the mesh confidence low?" (data-quality, not coverage) | Use the existing `Vertex.confidence` (see [Point cloud confidence values](../../workflow/point-cloud/point-cloud-confidence-values.md)) — same float-confidence concept applies to mesh vertices |
| "Where do tie points cluster?" | Different visualisation; use the tie-point cloud's per-point colour mapping |

## Performance considerations

The overlap recipe is O(V × C) — vertices times cameras.
For typical aerial projects:

- 1M vertices × 1000 cameras = 10⁹ operations.
- Per operation: ~5 floating-point multiplies + 1
  matrix-vector product + a bounds check.
- On a modern CPU: 5-30 minutes (CPython interpreter
  overhead dominates).

For faster execution:

- Pre-extract camera transforms into numpy arrays (speeds
  the inner loop ~10×).
- Use `numpy` matrix operations for batch projection of all
  vertices through one camera at a time.
- Implement the inner loop in C via Cython or pyo3.

The official `colorize_model_by_overlap.py` script runs in
pure Python and is acceptable for interactive QA but not for
automated batch pipelines on large datasets.

## Caveats

- **`vert.color` setting requires the vertex colour buffer
  to exist.** If the mesh was built without colour (rare in
  recent versions), call
  `chunk.model.setVertexColors()` first to allocate it.
- **Vertex colours are NOT preserved across mesh
  rebuilds.** If you re-run *Build Mesh*, the colourised
  output is lost. Save the modified mesh externally
  (e.g., as PLY) before rebuilding.
- **Vertex colours are exported with the mesh.** OBJ / PLY /
  GLTF exports include them by default. Set
  `chunk.exportModel(save_colors=False)` to omit.
- **The overlap recipe ignores occlusions.** A vertex behind
  a building is counted as visible from cameras on the other
  side. For occlusion-aware overlap (slower, more accurate),
  layer in `Model.renderDepth` checks per camera.
- **Build Texture overrides vertex colours** in the displayed
  view if a texture is applied. To see the per-vertex colour
  diagnostic, ensure no texture is currently applied (or
  toggle texture off in the *Model* view).

## See also

- [`Model.renderDepth`: synthetic depth from arbitrary
  viewpoints](../scripting/model-render-depth.md)
  — for occlusion-aware visibility tests.
- [Point cloud confidence values: what they mean and how to
  filter](../../workflow/point-cloud/point-cloud-confidence-values.md)
  — `Vertex.confidence` is a related per-vertex float
  metric.
- [How Metashape computes vertex normals on model export](../../workflow/mesh/vertex-normal-computation.md)
  — companion mesh-attribute behaviour.
- [Performance tuning: CPU, RAM, GPU, and OS](../performance/cpu-ram-gpu-os-tuning.md)
  — for the O(V × C) loop's CPU sizing on large meshes.

## References

- [`colorize_model_by_overlap.py`](https://github.com/agisoft-llc/metashape-scripts/blob/master/src/colorize_model_by_overlap.py)
  — the canonical overlap-colorization implementation.
- [`colorize_model_by_altitude.py`](https://github.com/agisoft-llc/metashape-scripts/blob/master/src/colorize_model_by_altitude.py)
  — the canonical altitude-colorization implementation.
- *Metashape Python API Reference* (2.3.1):
  `Model.vertices`, `Vertex.color`, `Vertex.coord`,
  `Model.setVertexColors`, `Camera.sensor`,
  `Sensor.calibration`, `Calibration.project`.

