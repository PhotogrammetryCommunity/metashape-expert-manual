---
title: How Metashape computes vertex normals on model export
status: unverified
applies_to: Metashape Pro 2.x and Metashape Standard 2.x (tested on 2.2.x; cross-version not separately verified).
edition: "Pro / Standard"
last_reviewed: 2026-05-26
diataxis: explanation
confidence: medium
---

# How Metashape computes vertex normals on model export

> **Confidence:** *medium overall.* The algorithm finding
> (area-weighted averaging, no crease threshold) is
> high-confidence — Test F's 5° gap between schemes is far
> above measurement noise. The medium rating reflects
> *cross-version* applicability: only Metashape 2.2.x was
> tested. Cross-format applicability (only OBJ tested; PLY /
> FBX / GLTF not separately verified) is also medium.

## Problem

Your downstream pipeline (a renderer, a NeRF / Gaussian-splat
trainer, a CAD package, a 3D-printing slicer) needs **vertex
normals** in the OBJ / PLY / FBX / GLTF that Metashape exports.
You have set *Save vertex normals = ON* in *File → Export →
Export Model*, and the output file does contain `vn` lines.
But:

- Are the normals **smooth-shaded** (averaged across faces) or
  **flat-shaded** (one per face, with split vertices at every
  edge)?
- If averaged, **how** are they averaged — uniform, area-
  weighted, or angle-weighted?
- Is there a **crease-angle threshold** beyond which Metashape
  splits vertices to preserve a hard edge?

Neither the Metashape user manual, the Python API reference,
nor the Metashape changelog (GUI or Python API) documents
which scheme is used. The Python API exposes a
`save_normals: bool` kwarg on `Chunk.exportModel()` whose
docstring is a single sentence ("Enables/disables export of
vertex normals.") and no other knobs.

This article documents the answer empirically.

## Context

A vertex shared by multiple triangles has, in general, a
distinct face normal per triangle. The exported "vertex
normal" must combine them into a single direction. Common
schemes:

- **Uniform average:** sum the unit face normals and
  re-normalise. All faces contribute equally regardless of
  size or shape.
- **Area-weighted average:** weight each face's normal by its
  area before summing. Larger faces dominate.
- **Angle-weighted average:** weight by the corner angle the
  vertex makes inside each face. Sharp corners dominate.
- **Crease-angle threshold:** if the **dihedral angle**
  between two adjacent faces (the angle between their face
  normals) exceeds some threshold (often 30°–45°), split the
  vertex and emit one normal per face, preserving the visual
  crease in renderers that smooth-shade by default.

For a sphere mesh, all three smooth-shading schemes give
nearly the same answer: every face shares a similar normal
direction. They diverge on irregular meshes — boxes, jagged
surfaces, meshes with mixed triangle sizes.

## What Metashape does

Tier 3 testing on Metashape 2.2.x with six synthetic test
meshes establishes:

1. **Metashape does not split vertices at sharp edges**
   (verified up to 150° dihedrals).
2. **Metashape uses area-weighted averaging.** Uniform,
   angle-weighted, and crease-threshold schemes are all
   ruled out.

### Test results

The six test meshes were imported as OBJs into clean
Metashape projects, then exported via *File → Export →
Export Model* with *Save vertex normals = ON*. Each output
was compared to three predicted-normal sets computed offline.

The "deviation" is the mean angular difference (in degrees)
between Metashape's exported vertex normals and the
predicted normals under each weighting scheme. Lower is a
better match.

| Test | Geometry | Uniform | Area-weighted | Angle-weighted |
|------|----------|--------:|--------------:|---------------:|
| A | Two coplanar triangles | 0.000° | 0.000° | 0.000° |
| B | Cube (90° dihedrals) | 0.014° | 0.014° | **14.617°** |
| C | Icosahedron | 0.000° | 0.000° | 0.000° |
| D | Dihedral progression (0°–150°) | 0.024° | 0.024° | 0.024° |
| E | Tetrahedron | 0.000° | 0.000° | 0.000° |
| F | Two triangles, 11× area difference | **5.581°** | **0.026°** | 4.505° |

Tests A, C, D, E all have equal-area faces or symmetric
configurations where uniform and area-weighted give identical
results. Test B (cube) eliminates angle-weighted: cube faces
have equal areas (so uniform = area), but the corner angles
vary across the 12 triangulated faces, producing a 14.6°
deviation that's ~1000× the noise floor.

Test F is the decisive case. Two triangles share an edge,
with 11× area imbalance. Uniform-weighted prediction differs
from the area-weighted prediction by ~5°, and Metashape's
exported normals match area-weighted to 0.026° — well within
the 4-decimal-place precision Metashape uses in the OBJ
file.

### No crease-angle threshold

Test D was a fan of six triangles sharing a common edge,
with apex vertices at progressively-increasing angles from
horizontal: 0°, 30°, 60°, 90°, 120°, 150°. The maximum
**dihedral angle** between any two faces sharing the common
edge is therefore 150°. Even at this dihedral, Metashape
kept the shared vertices intact (8 input vertices → 8 output
vertices). The exported normals at the shared-edge vertices
were the area-weighted average of all six incident face
normals.

The cube test (B) corroborates: 8 corner vertices, each
shared by three perpendicular faces. Metashape produced 8
output vertices (not 24); each corner gets a single averaged
normal pointing diagonally outward.

## Implications

### For renderers and viewers

Cubes, machined parts, architectural models, and other
geometry with intentional hard edges will appear
**smooth-shaded** when imported into a viewer that respects
the file's vertex normals. The visible artifact: edges
appear rounded, with shading gradients across faces that
should look flat.

Mitigations, in order of effort:

1. **Re-compute normals downstream.** Most DCC tools
   (Blender, Maya, MeshLab) and game engines (Unity, Unreal)
   can recompute normals on import with their own crease
   threshold. This is usually the right fix.
2. **Strip the `vn` lines AND face-line normal indices from
   the export.** The file then contains no normals;
   downstream tools fall back to computing them. For OBJ:

    ```bash
    # Two-step: drop vn lines, then strip //<vn-idx> from f lines
    awk '!/^vn /' input.obj | sed -E 's#/[0-9]*/[0-9]+##g' > output.obj
    ```

    The first step removes the `vn` lines; the second
    rewrites face references like `f 1//3 2//5 3//7` to
    `f 1 2 3` so downstream parsers don't follow dangling
    indices. Always do both — running only the first step
    leaves face lines that reference deleted normals, which
    crashes some parsers and silently corrupts others.
3. **Build texture or shade-via-displacement-map** in
   Metashape itself if the rendering target supports it; the
   visual model is the texture, and lighting comes from the
   displacement map rather than from interpolated normals.

### For NeRF / Gaussian-splat / mesh-augmentation pipelines

Pipelines that consume the `vn` directly (e.g., to seed a
neural texture model with surface curvature, or to
initialise normal maps for relighting) will see a smooth
surface even where the underlying geometry has hard edges.

If your pipeline depends on accurate per-face normals, treat
Metashape's exported `vn` as a **smoothed approximation** and
recompute from face geometry where precision matters.

### For tools that do their own crease detection

Blender's *Auto Smooth* with a 30° threshold, MeshLab's
*Compute Vertex Normals* with a custom angle, Unity's import
*Smoothing Angle*, and similar features will all override
Metashape's `vn` based on geometry alone. In these
pipelines, the Metashape normals are effectively unused —
strip them from the export to save file size and reduce
confusion.

### When Metashape's smoothing is right

Photogrammetric meshes of natural surfaces (terrain,
sculptures, archaeological surfaces, organic objects) rarely
have hard edges in the mathematical sense. The triangulated
mesh is an approximation of a smooth surface, and
area-weighted averaging across all incident faces produces a
visually-correct shading direction. For these typical
photogrammetry use cases, the default behaviour is
appropriate; no mitigation needed.

## Test methodology and reproducibility

The full experiment lives in a single script:
`scripts/verify_vertex_normals.py`. To reproduce on your own
Metashape build (Pro license required for the export step):

```bash
~/.pyenv/versions/Metashape-2.3/bin/python \
    scripts/verify_vertex_normals.py
```

The script:

1. Generates 6 synthetic test meshes (each designed to
   differentiate one hypothesis about the normal-computation
   algorithm).
2. For each: writes the input OBJ, imports it into a fresh
   Metashape Document, and exports it via
   `chunk.exportModel(save_normals=True)`.
3. Parses both the input and exported OBJs and compares the
   exported vertex normals to three predicted weighting
   schemes (uniform, area-weighted, angle-weighted) computed
   offline.
4. Prints a per-test report and a summary table; the smallest
   deviation column identifies the scheme Metashape uses.

Optional `--keep-psz` writes a `.psz` project per test mesh
(useful for follow-up GUI inspection). Optional
`--output-dir PATH` overrides the default
`corpus/normals_experiment/`.

The test meshes are deliberately small (2–20 triangles each)
and use exact rational coordinates where possible. The
analyser reports angular deviations to 4 decimal places;
the noise floor on the 6-decimal-place OBJ output is
~0.001°.

## Caveats

- **Single Metashape version tested.** This article reflects
  empirical behaviour on Metashape 2.2.x. Whether the
  algorithm is the same in 2.0, 2.1, or 2.3 is not
  separately verified, though there is no reason to expect
  a change.
- **Area-weighted is industry-standard.** Most DCC tools
  default to area-weighted averaging when no crease threshold
  is specified, so Metashape's choice is unsurprising.
  Documenting it serves to confirm rather than discover.
- **The exported file's coordinate frame may be translated**
  relative to the input. Metashape applies the chunk's
  transform on export. The normals are unaffected
  (rotations preserve unit vectors, translations don't
  affect direction); but be careful when comparing exported
  vertex *positions* to input positions.
- **OBJ precision.** The default OBJ export uses 6 decimal
  places for vertex coordinates. The vertex-normal
  components are printed with 6 decimal places as well; this
  is the precision floor for the deviation analysis.
- **Other formats** (PLY, FBX, GLTF, U3D) were not separately
  tested. The vertex-normal computation is presumably
  format-independent; the precision of the saved values may
  differ.

## See also

- [Metashape user manual](https://www.agisoft.com/pdf/metashape-pro_2_3_en.pdf),
  *Building model* and *Exporting results* — documents
  `save_normals` but not the algorithm.
- *Metashape Python API Reference* (2.3.1), `Chunk.exportModel`,
  parameter `save_normals`.
- Reproducer script in this repository:
  `scripts/verify_vertex_normals.py` — a single-script
  end-to-end test that builds the meshes, runs the Metashape
  export (Pro license required), parses the output, and prints
  the deviation analysis.
