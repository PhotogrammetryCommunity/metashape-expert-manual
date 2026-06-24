---
title: "Aligning two meshes / point clouds: model-to-model registration in Python"
status: unverified
applies_to: Metashape Pro 2.x — uses external `open3d` library; pattern from `align_model_to_model.py` in the official metashape-scripts repo
edition: Pro
last_reviewed: 2026-05-30
diataxis: how-to
confidence: high
---

# Aligning two meshes / point clouds: model-to-model registration in Python

> **Confidence:** *high.* The script lives in Agisoft's
> official [`metashape-scripts`](https://github.com/agisoft-llc/metashape-scripts)
> repo (not just forum content), is tested against Metashape
> 2.3, and uses standard `open3d` ICP / RANSAC primitives.
> Article framing extracts the operational pattern; specific
> parameter values come from the script verbatim.

## Problem

You have two independently-built 3D representations that
should align — for example:

- Two photogrammetry models built from non-overlapping captures
  of the same site (different flights, different chunks).
- A photogrammetry model and a LIDAR point cloud of the same
  area.
- Two LIDAR scans from different stations.
- A "before" and "after" mesh of an excavation site.

You need them in a common coordinate frame so that downstream
operations (chunk-diff, comparison, blending) can run on them
together. Metashape's *Align Chunks* is one option for camera-
based chunks; for chunks where you have only the geometry (no
shared cameras), or for aligning external imports, you need a
**model-to-model / point-cloud-to-point-cloud registration**
step.

## What's available

Metashape's GUI has *Align Chunks → method=Point cloud* which
runs an ICP-style registration. For more control or for
external data (LIDAR loaded as point cloud), Agisoft publishes
[`align_model_to_model.py`](https://github.com/agisoft-llc/metashape-scripts/blob/master/src/align_model_to_model.py)
in its official scripts repo. It uses
[`open3d`](https://www.open3d.org/) — a separate Python library
that ships standard global-and-local registration primitives —
to perform a two-stage registration:

1. **Global registration** (RANSAC on FPFH features) gets
   approximate alignment when the two clouds are far apart.
2. **Local refinement** (ICP) tightens the alignment using
   point-to-plane distance.

The script handles three sub-cases that pure ICP doesn't: (a)
unknown scale ratio between source and target, (b) unknown
appropriate ICP voxel size (target_resolution), and (c) the
"only common geometry overlaps" case (where you crop both
clouds to the shared region before registration).

## When to use this vs. *Align Chunks*

| Scenario | Recommended |
|----------|-------------|
| Two chunks with shared cameras | *Align Chunks → method=Camera* |
| Two chunks with shared markers | *Align Chunks → method=Marker* |
| Two chunks in same coordinate frame, geometry-only | *Align Chunks → method=Point cloud* |
| Two clouds in different scales (e.g., LIDAR + photogrammetry where one is in CRS metres and the other in chunk-internal units) | `align_model_to_model.py` |
| Imported LIDAR cloud + photogrammetry model | `align_model_to_model.py` |
| Want fine-grained control over voxel size, RANSAC parameters, ICP iterations | `align_model_to_model.py` |
| Want a fully GUI-driven workflow | *Align Chunks* |

## Recipe — adapt the script's pattern for your data

The complete script is in the metashape-scripts repo. The core
pattern, simplified for documentation:

> **Demo verified:** ✗ — pending Tier 3 reproduction on a real Metashape install with `open3d` installed.

```python
import numpy as np
import open3d as o3d
import Metashape

chunk = Metashape.app.document.chunk

# Step 1: extract source and target as numpy arrays
def chunk_model_to_numpy(chunk):
    """Extract chunk.model vertices as Nx3 numpy array."""
    if not chunk.model:
        raise RuntimeError("No model in chunk")
    coords = np.array([
        [v.coord.x, v.coord.y, v.coord.z]
        for v in chunk.model.vertices
    ])
    return coords

def chunk_pointcloud_to_numpy_via_export(chunk, las_path):
    """Extract chunk.point_cloud points as Nx3 numpy array.

    The 2.x point-cloud API does not expose per-point iteration
    in Python, so the canonical pattern is: export the point cloud
    to a temp LAS file, then read it back via laspy or similar.
    """
    pc = chunk.point_cloud
    if not pc:
        raise RuntimeError("No point cloud in chunk")
    chunk.exportPointCloud(
        las_path,
        source_data=Metashape.DataSource.PointCloudData,
        crs=chunk.crs,
    )
    # Read the LAS file (requires laspy)
    import laspy
    las = laspy.read(las_path)
    return np.column_stack([las.x, las.y, las.z])

# Step 2: build open3d point clouds from numpy
def to_o3d_cloud(arr_nx3):
    pcd = o3d.geometry.PointCloud()
    pcd.points = o3d.utility.Vector3dVector(arr_nx3)
    return pcd

source_pts = chunk_model_to_numpy(chunk)
target_pts = ...  # from the other chunk or via chunk_pointcloud_to_numpy_via_export(other_chunk, "/tmp/target.las")

source_pcd = to_o3d_cloud(source_pts)
target_pcd = to_o3d_cloud(target_pts)

# Step 3: estimate scale ratio (if not 1.0)
# (See align_model_to_model.py's `estimate_convex_hull_size` for the heuristic)
scale_ratio = 1.0   # for LIDAR-to-LIDAR; for photogrammetry-to-LIDAR use the script's hull-based estimate

# Step 4: voxel-downsample both clouds for global registration
voxel_size = 0.5   # in target-cloud units
source_down = source_pcd.voxel_down_sample(voxel_size)
target_down = target_pcd.voxel_down_sample(voxel_size)

# Step 5: estimate normals and FPFH features
o3d.geometry.PointCloud.estimate_normals(source_down)
o3d.geometry.PointCloud.estimate_normals(target_down)
source_fpfh = o3d.pipelines.registration.compute_fpfh_feature(
    source_down, o3d.geometry.KDTreeSearchParamHybrid(radius=voxel_size * 5, max_nn=100))
target_fpfh = o3d.pipelines.registration.compute_fpfh_feature(
    target_down, o3d.geometry.KDTreeSearchParamHybrid(radius=voxel_size * 5, max_nn=100))

# Step 6: global registration via RANSAC
result_global = o3d.pipelines.registration.registration_ransac_based_on_feature_matching(
    source_down, target_down, source_fpfh, target_fpfh,
    mutual_filter=True,
    max_correspondence_distance=voxel_size * 1.5,
    estimation_method=o3d.pipelines.registration.TransformationEstimationPointToPoint(False),
    ransac_n=3,
    checkers=[
        o3d.pipelines.registration.CorrespondenceCheckerBasedOnEdgeLength(0.9),
        o3d.pipelines.registration.CorrespondenceCheckerBasedOnDistance(voxel_size * 1.5),
    ],
    criteria=o3d.pipelines.registration.RANSACConvergenceCriteria(100000, 0.999),
)

# Step 7: local ICP refinement
result_icp = o3d.pipelines.registration.registration_icp(
    source_pcd, target_pcd,
    max_correspondence_distance=voxel_size * 0.4,
    init=result_global.transformation,
    estimation_method=o3d.pipelines.registration.TransformationEstimationPointToPlane(),
)

# Step 8: apply the final transform back to the source chunk
T_4x4 = result_icp.transformation   # 4x4 numpy array
T_metashape = Metashape.Matrix(T_4x4.tolist())
chunk.transform.matrix = T_metashape * chunk.transform.matrix
```

For the production-quality version with logging, scale-ratio
estimation, error reporting, and the GUI dialog, use the
[`align_model_to_model.py`](https://github.com/agisoft-llc/metashape-scripts/blob/master/src/align_model_to_model.py)
script directly.

## Two-stage registration: why both global + ICP

ICP alone fails when the source and target are far apart in
their starting positions. The local-search nature of ICP means
it converges to whichever local minimum is closest — which is
usually wrong unless the input is already roughly aligned.

The global RANSAC step uses **feature descriptors** (FPFH)
that match similar-shaped local geometry across the two clouds.
Even if the source and target are arbitrarily oriented, RANSAC
finds correspondences between similar features, then estimates
a rough transform. ICP then refines.

A trick the script uses: if you know the two clouds **are**
already roughly aligned (e.g., both in the same world CRS),
skip the global step via `no_global_alignment=True`. Saves
significant time on already-near-aligned data.

## Pre-requisite: install `open3d`

The script auto-installs `open3d` on first run via
`pip_install(requirements_txt)`. For manual install:

```bash
~/.pyenv/versions/Metashape-2.3/bin/pip install open3d==0.19.0 scipy==1.12.0 numpy==1.26.4
```

Pin to the exact versions the script specifies — `open3d` API
changes between versions, and the script depends on the
`o3d.pipelines.registration` namespace (renamed from
`o3d.registration` at some open3d version).

## Caveats

- **Scale ratio matters.** If you don't know the true scale
  ratio (e.g., one cloud is in millimetres, the other in
  metres), the script's heuristic estimate via convex-hull
  size is unreliable for partially-overlapping data. Measure
  a known-length feature in both clouds and divide for the
  reliable scale ratio.
- **Voxel size determines registration accuracy.** Too large:
  loses detail, fails on small features. Too small: slow,
  noise-sensitive. Start at ~0.01 of the cloud's diagonal
  bounding-box length and tune.
- **The script's GUI runs synchronously.** On large clouds
  (>10M points), the global registration alone can take
  10+ minutes. The Metashape GUI appears unresponsive during
  this; don't kill the process.
- **`open3d` and Metashape's Python share interpreters.** The
  script installs `open3d` into Metashape's Python env. This
  works but means subsequent unrelated Metashape Python
  scripts may inherit `open3d`'s import overhead.
- **The transform is applied to `chunk.transform.matrix`.**
  This affects all chunk geometry (cameras, points, mesh,
  orthomosaic). For per-asset transforms (move only the mesh,
  not the cameras), you'd need to use the asset-specific
  transform fields, which the script does not currently
  handle.
- **Output transformation is in source's chunk-local frame.**
  If you want the transform in geocentric or CRS coordinates
  for downstream tools, multiply by the chunk's transform.

## See also

- [The three `alignChunks` methods (point / marker / camera)](../../workflow/chunks/alignchunks-three-methods.md)
  — the GUI alternatives when chunks share cameras or markers.
- [Comparing chunks for change detection: DEM, mesh, and
  point-cloud diff workflows](chunk-diff-volume-workflows.md)
  — uses model-to-model alignment as a pre-requisite for
  diffing.
- [`Model.renderDepth`: synthetic depth from arbitrary
  viewpoints](model-render-depth.md) — uses similar Matrix
  manipulation.
- [Mesh and point-cloud editing recipes](mesh-pointcloud-editing-recipes.md)
  — broader Python recipes for mesh / point-cloud manipulation.

## References

- [`align_model_to_model.py`](https://github.com/agisoft-llc/metashape-scripts/blob/master/src/align_model_to_model.py)
  — the canonical implementation in Agisoft's official
  scripts repo.
- *Open3D documentation*, [Global registration](https://www.open3d.org/docs/release/tutorial/pipelines/global_registration.html)
  — the FPFH + RANSAC algorithm the script uses.
- *Open3D documentation*, [ICP registration](https://www.open3d.org/docs/release/tutorial/pipelines/icp_registration.html)
  — the point-to-plane ICP variant for the local refinement
  step.
- *Metashape Python API Reference* (2.3.1):
  `Chunk.transform`, `Chunk.model`, `Chunk.point_cloud`,
  `Matrix`.

