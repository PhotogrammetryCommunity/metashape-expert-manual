# Scripting and automation

Cross-cutting articles on driving Metashape from the Python API:
math-focused recipes, coordinate-system utilities, and
visibility / projection patterns. Companion to
[Workflow → Scripting & automation](../../workflow/scripting-automation/index.md),
which covers procedural workflow scripts.

The Metashape Python API is **Professional-edition only**.
Scripts here will not run in Standard.

## Articles

- [Scripting context pitfalls: GUI vs command-line, document handles, and stage validation](scripting-context-pitfalls.md)
- [YPR rotation conventions: ypr2mat vs camera.reference.rotation](ypr-rotation-conventions.md)
- [Choosing camera axes: aerial vs terrestrial (and YPR vs OPK)](choosing-rotation-representation.md)
- [The chunk's internal coordinate system: arbitrary scale and chunk.transform.scale](chunk-internal-scale-and-units.md)
- [Working with shape geometries (1.7+ API)](shape-geometry-api.md)
- [Creating point shapes programmatically: grid placement with DEM-based elevation](creating-point-shapes-from-dem.md)
- [`camera.project` and `camera.unproject`: 2D ↔ 3D in Python](camera-project-unproject.md)
- [Converting `camera.transform` to ENU](camera-poses-to-enu.md)
- [Computing camera direction vectors and look-at points](camera-direction-vectors.md)
- [Computing per-camera coverage area](computing-camera-coverage-area.md)
- [Mapping orthomosaic pixels back to source images](orthomosaic-pixel-to-source-image.md)
- [Filtering cameras by tie-point selection: which photos see this 3D point?](filter-cameras-by-tie-points.md)
- [Mesh and point-cloud editing recipes (Python)](mesh-pointcloud-editing-recipes.md)
- [`Model.renderDepth`: synthetic depth from arbitrary viewpoints](model-render-depth.md)
- [Rendering models from synthetic cameras: spherical panoramas and regular views](rendering-from-synthetic-cameras.md)
- [Comparing chunks for change detection: DEM, mesh, point-cloud diff](chunk-diff-volume-workflows.md)
- [Aligning two meshes / point clouds: model-to-model registration in Python](aligning-models-and-clouds.md)
- [Diagnostic mesh visualisation: colorize by overlap or altitude](colorize-mesh-diagnostics.md)
- [Undocumented tweaks: a partial reference](undocumented-tweaks-reference.md)

## Related sections

- [Workflow → Scripting & automation](../../workflow/scripting-automation/index.md)
  — procedural automation scripts (gradual-selection loops,
  logging from headless runs).
- [Topics → CRS & georeferencing](../crs/index.md) — the
  coordinate-system distinctions these recipes depend on.
- [Topics → Performance & GPU](../performance/index.md) — for
  when scripts hit GPU-pipeline issues during dense-cloud /
  depth-maps stages.
