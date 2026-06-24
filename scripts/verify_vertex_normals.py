#!/usr/bin/env python3
"""Verify how Metashape computes vertex normals on model export.

End-to-end single-script test:

  1. Builds 6 synthetic test meshes (each designed to
     differentiate one hypothesis about the vertex-normal
     algorithm).
  2. For each mesh: writes input OBJ; imports into a fresh
     Metashape Document; exports via `chunk.exportModel(...,
     save_normals=True)`; optionally saves the project as
     .psz.
  3. Parses input + exported OBJs; for each shared vertex,
     compares Metashape's exported normal to three predicted
     weighting schemes (uniform, area-weighted, angle-
     weighted) computed offline.
  4. Prints a per-test report showing the mean angular
     deviation of each scheme. The smallest column is the
     scheme Metashape uses.

Requires a Metashape Pro license (the export step is
license-gated). The script falls back gracefully if no
license is found: it still builds the test inputs but skips
the Metashape steps and reports which manual exports are
needed.

Usage:
    ~/.pyenv/versions/Metashape-2.3/bin/python \\
        scripts/verify_vertex_normals.py
    # writes inputs/*.obj, exports/*.obj, and prints analysis

    ~/.pyenv/versions/Metashape-2.3/bin/python \\
        scripts/verify_vertex_normals.py --keep-psz
    # also keeps .psz projects (license required)

    ~/.pyenv/versions/Metashape-2.3/bin/python \\
        scripts/verify_vertex_normals.py --output-dir /tmp/normals
    # write artefacts under a custom directory

Test cases (each designed to differentiate one hypothesis):

  A — two_coplanar_triangles
        Baseline: shared-edge vertices should have the same
        normal regardless of weighting scheme.

  B — cube
        90° dihedrals; tests for crease-angle splitting.
        Cube faces have equal area, so uniform == area;
        corner angles vary, so angle-weighted differs.

  C — icosahedron
        Smooth surface; sanity-check the radial direction.

  D — dihedral_progression
        Strip of triangles at 0°/30°/60°/90°/120°/150°
        dihedrals; tests for crease-angle threshold.

  E — tetrahedron
        Sharp + symmetric small case.

  F — unequal_areas
        Two triangles sharing an edge with 11× area
        difference. Differentiates uniform from area-weighted.
"""

from __future__ import annotations
import argparse
import math
import sys
from pathlib import Path
from typing import Optional


# ──────────────────────────────────────────────────────────
# Test-mesh factories
# ──────────────────────────────────────────────────────────


def write_obj(path: Path, vertices: list[tuple[float, float, float]],
              faces: list[tuple[int, int, int]]) -> None:
    """Write a minimal OBJ — vertices and triangular faces only.

    No vertex normals on input. Metashape will compute them.
    Face indices are 1-based per OBJ convention.
    """
    with path.open("w") as f:
        f.write(f"# Vertex-normal experiment input\n")
        f.write(f"# {len(vertices)} vertices, {len(faces)} triangles\n")
        for v in vertices:
            f.write(f"v {v[0]} {v[1]} {v[2]}\n")
        for face in faces:
            f.write(f"f {face[0]} {face[1]} {face[2]}\n")


def build_test_A() -> tuple[list, list]:
    """Two coplanar triangles sharing an edge."""
    vertices = [
        (0.0, 0.0, 0.0),
        (1.0, 0.0, 0.0),
        (1.0, 1.0, 0.0),
        (0.0, 1.0, 0.0),
    ]
    faces = [(1, 2, 3), (1, 3, 4)]
    return vertices, faces


def build_test_B_cube() -> tuple[list, list]:
    """Standard cube; 8 vertices, 12 triangles."""
    vertices = [
        (0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (1.0, 1.0, 0.0), (0.0, 1.0, 0.0),
        (0.0, 0.0, 1.0), (1.0, 0.0, 1.0), (1.0, 1.0, 1.0), (0.0, 1.0, 1.0),
    ]
    # Quads → triangles, outward-facing winding.
    faces = [
        # Bottom Z=0  (winding so normal points -Z)
        (1, 3, 2), (1, 4, 3),
        # Top Z=1
        (5, 6, 7), (5, 7, 8),
        # -Y face
        (1, 2, 6), (1, 6, 5),
        # +Y face
        (4, 7, 3), (4, 8, 7),
        # -X face
        (1, 5, 8), (1, 8, 4),
        # +X face
        (2, 3, 7), (2, 7, 6),
    ]
    return vertices, faces


def build_test_C_icosahedron() -> tuple[list, list]:
    """Regular icosahedron centred at origin, radius 1."""
    phi = (1 + math.sqrt(5)) / 2
    norm = math.sqrt(1 + phi * phi)
    vertices_raw = [
        (-1,  phi, 0), (1,  phi, 0), (-1, -phi, 0), (1, -phi, 0),
        (0, -1,  phi), (0, 1,  phi), (0, -1, -phi), (0, 1, -phi),
        ( phi, 0, -1), ( phi, 0, 1), (-phi, 0, -1), (-phi, 0, 1),
    ]
    vertices = [(x / norm, y / norm, z / norm) for x, y, z in vertices_raw]
    # 20 triangular faces (1-based)
    faces = [
        (1, 12, 6),  (1, 6, 2),   (1, 2, 8),   (1, 8, 11),  (1, 11, 12),
        (2, 6, 10),  (6, 12, 5),  (12, 11, 3), (11, 8, 7),  (8, 2, 9),
        (4, 10, 5),  (4, 5, 3),   (4, 3, 7),   (4, 7, 9),   (4, 9, 10),
        (5, 10, 6),  (3, 5, 12),  (7, 3, 11),  (9, 7, 8),   (10, 9, 2),
    ]
    return vertices, faces


def build_test_D_dihedral_progression() -> tuple[list, list]:
    """Strip of triangles with progressively-increasing dihedrals.

    Six triangles share a common edge along the X axis. The
    other vertex of each triangle sits above the X axis at
    increasing dihedral angle from the horizontal: 0°, 30°,
    60°, 90°, 120°, 150°.
    """
    vertices = [
        (0.0, 0.0, 0.0),    # V1 (shared)
        (1.0, 0.0, 0.0),    # V2 (shared)
    ]
    faces = []
    for i, deg in enumerate([0, 30, 60, 90, 120, 150]):
        rad = math.radians(deg)
        x = 0.5
        y = math.cos(rad)
        z = math.sin(rad)
        vertices.append((x, y, z))
        # 1-based; V1=1, V2=2; new vertex index = i + 3
        third = i + 3
        faces.append((1, 2, third))
    return vertices, faces


def build_test_E_tetrahedron() -> tuple[list, list]:
    """Regular tetrahedron centred at origin."""
    s = 1.0 / math.sqrt(3)
    vertices = [
        ( s,  s,  s),
        ( s, -s, -s),
        (-s,  s, -s),
        (-s, -s,  s),
    ]
    faces = [(1, 2, 3), (1, 3, 4), (1, 4, 2), (2, 4, 3)]
    return vertices, faces


def build_test_F_unequal_areas() -> tuple[list, list]:
    """Two triangles sharing an edge with very different areas
    AND different face normals. Distinguishes uniform from
    area-weighted averaging at the shared-edge vertices.
    """
    vertices = [
        (0.0, 0.0, 0.0),     # V1 (shared edge)
        (1.0, 0.0, 0.0),     # V2 (shared edge)
        (0.5, 1.0, 0.0),     # V3 (small-face apex)
        (0.5, -10.0, 5.0),   # V4 (large-face apex)
    ]
    faces = [
        (1, 2, 3),    # small triangle (area 0.5; normal +Z)
        (1, 4, 2),    # large triangle (area ~5.6; normal tilted)
    ]
    return vertices, faces


TEST_CASES = [
    ("A_two_coplanar_triangles", build_test_A),
    ("B_cube",                    build_test_B_cube),
    ("C_icosahedron",             build_test_C_icosahedron),
    ("D_dihedral_progression",    build_test_D_dihedral_progression),
    ("E_tetrahedron",             build_test_E_tetrahedron),
    ("F_unequal_areas",           build_test_F_unequal_areas),
]


# ──────────────────────────────────────────────────────────
# Vector helpers (used in analyser)
# ──────────────────────────────────────────────────────────


def vec_sub(a, b): return tuple(a[i] - b[i] for i in range(3))
def vec_add(a, b): return tuple(a[i] + b[i] for i in range(3))
def vec_dot(a, b): return sum(a[i] * b[i] for i in range(3))


def vec_cross(a, b):
    return (a[1] * b[2] - a[2] * b[1],
            a[2] * b[0] - a[0] * b[2],
            a[0] * b[1] - a[1] * b[0])


def vec_norm(a): return math.sqrt(sum(x * x for x in a))


def vec_normalize(a):
    n = vec_norm(a)
    return tuple(x / n for x in a) if n > 1e-12 else (0.0, 0.0, 0.0)


def face_normal(p0, p1, p2):
    """Right-handed face normal from 3 vertex positions."""
    return vec_normalize(vec_cross(vec_sub(p1, p0), vec_sub(p2, p0)))


def face_area(p0, p1, p2):
    return 0.5 * vec_norm(vec_cross(vec_sub(p1, p0), vec_sub(p2, p0)))


def face_corner_angle(p_corner, p_a, p_b):
    """Interior angle at p_corner of triangle (p_corner, p_a, p_b)."""
    a = vec_normalize(vec_sub(p_a, p_corner))
    b = vec_normalize(vec_sub(p_b, p_corner))
    return math.acos(max(-1.0, min(1.0, vec_dot(a, b))))


def compute_expected_normals(v: list, faces_v_idx: list[list[int]],
                              weighting: str) -> list:
    """Compute vertex normals from face mesh under the named
    weighting scheme. faces_v_idx is list of [v1, v2, v3]
    1-based triangles. weighting is 'uniform', 'area', or
    'angle'.
    """
    accum = [(0.0, 0.0, 0.0) for _ in v]
    for face in faces_v_idx:
        if len(face) != 3:
            continue
        p = [v[face[i] - 1] for i in range(3)]
        fn = face_normal(*p)
        if weighting == "uniform":
            weights = [1.0, 1.0, 1.0]
        elif weighting == "area":
            a = face_area(*p)
            weights = [a, a, a]
        elif weighting == "angle":
            weights = [
                face_corner_angle(p[0], p[1], p[2]),
                face_corner_angle(p[1], p[2], p[0]),
                face_corner_angle(p[2], p[0], p[1]),
            ]
        else:
            raise ValueError(weighting)
        for i in range(3):
            w = weights[i]
            accum[face[i] - 1] = vec_add(
                accum[face[i] - 1],
                tuple(fn[j] * w for j in range(3)),
            )
    return [vec_normalize(a) for a in accum]


# ──────────────────────────────────────────────────────────
# OBJ parser (output of our own write_obj() and Metashape's export)
# ──────────────────────────────────────────────────────────


def parse_obj(path: Path) -> dict:
    """Parse a Wavefront OBJ. Returns dict with keys:
        v: list[(x, y, z)] — vertex positions
        vn: list[(x, y, z)] — vertex normals (in vn-list order)
        f: list[list[(v_idx, vn_idx)]] — faces; both indices
            are 1-based; vn_idx is 0 if absent.
    """
    v, vn, f = [], [], []
    with path.open() as fh:
        for line in fh:
            parts = line.split()
            if not parts:
                continue
            if parts[0] == "v":
                v.append(tuple(float(x) for x in parts[1:4]))
            elif parts[0] == "vn":
                vn.append(tuple(float(x) for x in parts[1:4]))
            elif parts[0] == "f":
                face = []
                for tok in parts[1:]:
                    bits = tok.split("/")
                    v_idx = int(bits[0])
                    vn_idx = (int(bits[2]) if len(bits) >= 3 and bits[2]
                              else 0)
                    face.append((v_idx, vn_idx))
                f.append(face)
    return {"v": v, "vn": vn, "f": f}


# ──────────────────────────────────────────────────────────
# Metashape glue (uses the API; license required for export)
# ──────────────────────────────────────────────────────────


def has_license() -> bool:
    """True if a Metashape license is active. Tested by trying
    to save a doc to a temporary path and checking whether
    OSError('No license found') is raised.
    """
    import Metashape
    import tempfile, os
    with tempfile.TemporaryDirectory() as td:
        path = os.path.join(td, "license-probe.psz")
        try:
            doc = Metashape.Document()
            doc.addChunk()
            doc.save(path)
            return True
        except Exception:
            return False


def run_metashape_export(name: str, vertices: list, faces: list,
                          inputs_dir: Path, exports_dir: Path,
                          projects_dir: Optional[Path]) -> Optional[Path]:
    """Build an .obj, import into Metashape, export with
    save_normals=True. Returns the exported OBJ path on
    success, or None if the export step failed (no license,
    typically).
    """
    import Metashape

    obj_in = inputs_dir / f"{name}.obj"
    obj_out = exports_dir / f"{name}_metashape.obj"

    write_obj(obj_in, vertices, faces)

    doc = Metashape.Document()
    chunk = doc.addChunk()
    chunk.label = f"vertex-normal-test_{name}"
    chunk.importModel(
        path=str(obj_in),
        format=Metashape.ModelFormat.ModelFormatOBJ,
    )

    if projects_dir is not None:
        psz_path = projects_dir / f"{name}.psz"
        try:
            doc.save(str(psz_path))
        except Exception as e:
            print(f"  {name}: psz save skipped: {type(e).__name__}: {e}")

    try:
        chunk.exportModel(
            path=str(obj_out),
            format=Metashape.ModelFormat.ModelFormatOBJ,
            save_normals=True,
            binary=False,         # OBJ is text-only; explicit
        )
    except Exception as e:
        print(f"  {name}: ✗ exportModel failed: "
              f"{type(e).__name__}: {e}")
        return None

    if not obj_out.exists():
        print(f"  {name}: ✗ export produced no output at {obj_out}")
        return None
    return obj_out


# ──────────────────────────────────────────────────────────
# Per-test analysis
# ──────────────────────────────────────────────────────────


def analyse(name: str, in_path: Path, out_path: Path) -> dict:
    """Compare Metashape's exported normals to predicted
    normals under each weighting scheme. Returns a dict of
    deviations (in degrees).
    """
    inp = parse_obj(in_path)
    out = parse_obj(out_path)

    print(f"=== {name} ===")
    print(f"  input:   {len(inp['v'])} vertices, {len(inp['f'])} faces, "
          f"{len(inp['vn'])} normals")
    print(f"  output:  {len(out['v'])} vertices, {len(out['f'])} faces, "
          f"{len(out['vn'])} normals")

    vertex_split = len(out["v"]) > len(inp["v"])
    if vertex_split:
        print(f"  → Vertex count INCREASED ({len(inp['v'])} → {len(out['v'])})"
              "; Metashape SPLIT vertices at sharp edges")
    else:
        print(f"  → Vertex count preserved; Metashape kept shared vertices")

    result = {"name": name, "vertex_split": vertex_split,
              "deviations": {}}

    if not vertex_split and len(out["vn"]) > 0:
        faces_v_idx = [[c[0] for c in face] for face in inp["f"]]
        expected = {
            "uniform": compute_expected_normals(
                inp["v"], faces_v_idx, "uniform"),
            "area":    compute_expected_normals(
                inp["v"], faces_v_idx, "area"),
            "angle":   compute_expected_normals(
                inp["v"], faces_v_idx, "angle"),
        }

        per_vertex_normal = [None] * len(out["v"])
        for face in out["f"]:
            for v_idx, vn_idx in face:
                if vn_idx > 0 and per_vertex_normal[v_idx - 1] is None:
                    per_vertex_normal[v_idx - 1] = out["vn"][vn_idx - 1]

        # Match output vertex i to input vertex j by closest
        # position. Metashape's chunk transform on a fresh
        # imported mesh (no georeferencing) is identity, so
        # output positions equal input positions; nearest-
        # neighbour matching is exact. For georeferenced
        # projects the transform may include translation —
        # we centroid-correct first to handle that case.
        in_centroid = tuple(
            sum(p[i] for p in inp["v"]) / len(inp["v"])
            for i in range(3)
        )
        out_centroid = tuple(
            sum(p[i] for p in out["v"]) / len(out["v"])
            for i in range(3)
        )
        offset = vec_sub(out_centroid, in_centroid)

        def match_vertex(out_pos):
            shifted = vec_sub(out_pos, offset)
            best, best_d = None, 1e9
            for j, ipos in enumerate(inp["v"]):
                d = vec_norm(vec_sub(shifted, ipos))
                if d < best_d:
                    best, best_d = j, d
            # Sanity check: the match should be exact (sub-mm).
            if best_d > 0.01:
                raise RuntimeError(
                    f"vertex match failed: output vertex {out_pos} "
                    f"has no input within 0.01 (closest: {best_d:.4f})"
                )
            return best

        scores = {"uniform": 0.0, "area": 0.0, "angle": 0.0}
        n_compared = 0
        for i, n_meas in enumerate(per_vertex_normal):
            if n_meas is None:
                continue
            j = match_vertex(out["v"][i])
            for scheme, exp_list in expected.items():
                exp = exp_list[j]
                dot = max(-1.0, min(1.0, vec_dot(n_meas, exp)))
                deg = math.degrees(math.acos(dot))
                scores[scheme] += deg
            n_compared += 1

        if n_compared > 0:
            print(f"  Mean angular deviation from each expected weighting "
                  f"({n_compared} vertices):")
            for scheme, total in scores.items():
                avg = total / n_compared
                result["deviations"][scheme] = avg
                print(f"    {scheme:>8}:  {avg:.4f}°")
            best = min(scores, key=scores.get)
            result["best"] = best
            print(f"  → BEST FIT: {best}")

    print()
    return result


# ──────────────────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────────────────


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--output-dir", type=Path,
                    default=Path("corpus/normals_experiment"),
                    help="Root directory for inputs/, exports/, "
                         "and (optionally) projects/")
    ap.add_argument("--keep-psz", action="store_true",
                    help="Save the .psz project for each test mesh "
                         "(license required)")
    args = ap.parse_args()

    inputs_dir = (args.output_dir / "inputs").resolve()
    exports_dir = (args.output_dir / "exports").resolve()
    inputs_dir.mkdir(parents=True, exist_ok=True)
    exports_dir.mkdir(parents=True, exist_ok=True)

    projects_dir: Optional[Path] = None
    if args.keep_psz:
        projects_dir = (args.output_dir / "projects").resolve()
        projects_dir.mkdir(parents=True, exist_ok=True)

    try:
        import Metashape
    except ImportError:
        print("ERROR: 'Metashape' module not importable. Run from a "
              "Python interpreter where Metashape is installed.")
        return 2

    if not has_license():
        print("ERROR: no Metashape license. This script requires a Pro "
              "license to call Chunk.exportModel.")
        return 2

    print(f"Inputs  → {inputs_dir}")
    print(f"Exports → {exports_dir}")
    if projects_dir:
        print(f"PSZ     → {projects_dir}")
    print()

    results = []
    for name, factory in TEST_CASES:
        vertices, faces = factory()
        out_path = run_metashape_export(
            name, vertices, faces,
            inputs_dir, exports_dir, projects_dir,
        )
        if out_path is None:
            continue
        in_path = inputs_dir / f"{name}.obj"
        results.append(analyse(name, in_path, out_path))

    # Summary table
    if results:
        print("=" * 60)
        print("SUMMARY")
        print()
        header = (
            f"{'test':<28}{'vsplit':>8}"
            f"{'uniform':>10}{'area':>10}{'angle':>10}{'best':>10}"
        )
        print(header)
        print("-" * len(header))
        for r in results:
            d = r.get("deviations", {})
            print(
                f"{r['name']:<28}"
                f"{'YES' if r['vertex_split'] else 'no':>8}"
                f"{d.get('uniform', float('nan')):>9.4f}°"
                f"{d.get('area',    float('nan')):>9.4f}°"
                f"{d.get('angle',   float('nan')):>9.4f}°"
                f"{r.get('best','—'):>10}"
            )

    return 0


if __name__ == "__main__":
    sys.exit(main())
