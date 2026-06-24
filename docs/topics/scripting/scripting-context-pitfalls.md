---
title: "Scripting context pitfalls: GUI vs command-line, document handles, and stage validation"
status: unverified
applies_to: Metashape Pro 2.x — and PhotoScan 1.x via the same `Metashape.app` GUI-only restrictions
edition: Pro
last_reviewed: 2026-06-01
diataxis: how-to
confidence: high
---

# Scripting context pitfalls: GUI vs command-line, document handles, and stage validation

> **Confidence:** *high.* Both findings are forum-attested by
> Agisoft support with permalinks (2020, 2023). The
> `Metashape.app.document` and `Metashape.Document()` API are
> introspection-confirmed on Metashape 2.2.

## Problem

You wrote a script that runs fine when *Run Script* is invoked
from the Metashape GUI, but fails when run via `metashape -r
script.py` or `metashape.exe --run script.py` on the command
line. The error is one of:

- `AttributeError: 'NoneType' object has no attribute 'chunk'`
- `RuntimeError: No active document`
- `RuntimeError: chunk is None`

Or: a script runs without errors but produces incomplete /
invalid output — *Build Point Cloud* "succeeded" silently but
the chunk has no point cloud, *Optimize Cameras* "completed"
but the bundle didn't converge.

These are two different scripting-context issues that frequently
trip up new users.

## Pitfall 1 — `Metashape.app.document` is None on command-line runs

> "Metashape.app.document can be only used for the GUI-based
> scripts, as this call is related to the currently opened
> project. For the command-line run scripts the correct way is
> creating a new Metashape.Document() instance."
> — Agisoft support, 2020-09-28, Metashape 1.6
> ([permalink](https://www.agisoft.com/forum/index.php?topic=12603.msg55985#msg55985))

`Metashape.app.document` is the **currently-loaded GUI
document**. In headless / command-line runs, no GUI is loaded,
so `Metashape.app.document` is None. Calling `.chunk`,
`.chunks`, or any attribute on it raises `AttributeError`.

### Fix: detect context and adapt

> **Demo verified:** ✗ — pending Tier 3 reproduction on a real Metashape install.

```python
import Metashape, sys

if Metashape.app.document is not None:
    # Running inside the GUI — use the active document
    doc = Metashape.app.document
else:
    # Headless / command-line — create a new Document
    doc = Metashape.Document()
    if len(sys.argv) > 1:
        doc.open(sys.argv[1])

chunk = doc.chunk
```

This pattern works for both contexts. The script can be invoked
as:

- *GUI:* `Tools → Run Script → script.py`
- *Command line:* `metashape -r script.py /path/to/project.psx`

### When to create a new vs. open existing

| Use case | Pattern |
|----------|---------|
| Process an existing project | `doc = Metashape.Document(); doc.open(path)` |
| Build a project from scratch | `doc = Metashape.Document(); doc.save(path)` (saves empty); then add chunk via `doc.addChunk()` |
| Inside the GUI | `doc = Metashape.app.document` (already loaded) |

For new projects, `doc.save(path)` BEFORE adding chunks is
important — it sets the project's working directory so
subsequent operations (depth maps, dense cloud) know where to
write intermediate data.

## Pitfall 2 — `*.app.*` calls in headless scripts

`Metashape.app.document` is one of many `Metashape.app.*` APIs
that only work in GUI context. The full list of GUI-only calls:

| GUI-only API | Headless equivalent |
|--------------|---------------------|
| `Metashape.app.document` | `Metashape.Document()` instance |
| `Metashape.app.getInt(...)` | `int` from `sys.argv` or environment variable |
| `Metashape.app.getString(...)` | `str` from `sys.argv` or environment variable |
| `Metashape.app.getExistingDirectory(...)` | Pre-set path in script or argv |
| `Metashape.app.getCoordinateSystem(...)` | `Metashape.CoordinateSystem("EPSG::NNNN")` literal |
| `Metashape.app.viewpoint` | Synthetic camera transform constructed manually |
| `Metashape.app.captureModelView(...)` | `chunk.model.renderImage(transform, calibration)` |
| `Metashape.app.messageBox(...)` | `print()` to stdout |

For batch / pipeline scripts that should run in both contexts,
guard each `Metashape.app.*` call:

> **Demo verified:** ✗ — pending Tier 3 reproduction on a real Metashape install.

```python
import os
import Metashape

def get_param(prompt, default, env_var=None):
    """Read a parameter from GUI dialog, env var, or default."""
    if Metashape.app.document is not None:
        # GUI context — prompt the user
        return Metashape.app.getString(prompt, default)
    elif env_var and env_var in os.environ:
        # Headless with env var
        return os.environ[env_var]
    else:
        # Headless without env var — use default
        return default

output_dir = get_param("Output folder:", "/tmp/output", "MS_OUTPUT")
```

## Pitfall 3 — Validating that a stage actually completed

Metashape's processing stages don't return a status code. They
either complete silently (success) or raise an exception
(failure). But "exception" is a narrow definition of failure —
zero-resolution chunks, empty depth maps, and other
"degenerate-but-not-error" cases produce no exception, just an
empty result.

> "You can use try-except concept, if you want to track
> unexpected assertions, such as 'Zero Resolution', 'Null tie
> points' and similar."
> — Agisoft support, 2023-02-10, Metashape 2.0
> ([permalink](https://www.agisoft.com/forum/index.php?topic=15240.msg66874#msg66874))

### Pattern: try-except + content check

> **Demo verified:** ✗ — pending Tier 3 reproduction on a real Metashape install.

```python
import Metashape

chunk = Metashape.app.document.chunk

# Build dense cloud, catching errors AND checking output
try:
    chunk.buildDepthMaps(downscale=4)
    chunk.buildPointCloud()
except Exception as e:
    print(f"Build Point Cloud raised: {type(e).__name__}: {e}")
    raise

# Verify the chunk actually has a point cloud
if not chunk.point_cloud:
    print("WARNING: buildPointCloud completed but chunk.point_cloud is None")
elif len(chunk.point_cloud.points) == 0:
    print("WARNING: chunk.point_cloud is empty (zero points)")
else:
    print(f"OK: {len(chunk.point_cloud.points)} points")
```

The `try/except` catches exceptions; the post-condition check
catches "completed but produced nothing" cases that don't raise.

### Stage-specific post-condition checks

| Stage | Post-condition |
|-------|---------------|
| `matchPhotos` | At least some pairs have keypoints / matches; check `len(chunk.tie_points.tracks)` |
| `alignCameras` | `camera.transform is not None` for some fraction of cameras |
| `triangulateTiePoints` | `len(chunk.tie_points.points) > 0` |
| `buildDepthMaps` | `chunk.depth_maps is not None` and has entries per camera |
| `buildPointCloud` | `chunk.point_cloud is not None` and non-empty |
| `buildModel` | `chunk.model is not None` |
| `buildTexture` | `chunk.model.texture is not None` |
| `buildOrthomosaic` | `chunk.orthomosaic is not None` |

For a robust pipeline:

> **Demo verified:** ✗ — pending Tier 3 reproduction on a real Metashape install.

```python
def assert_stage(condition, stage_name):
    if not condition:
        raise RuntimeError(f"{stage_name} produced no output")

chunk.matchPhotos(downscale=1, generic_preselection=True)
assert_stage(len(chunk.tie_points.tracks) > 100, "matchPhotos")

chunk.alignCameras()
n_aligned = sum(1 for c in chunk.cameras if c.transform)
assert_stage(n_aligned > len(chunk.cameras) * 0.5, "alignCameras (>50% aligned)")

chunk.buildDepthMaps(downscale=4)
assert_stage(chunk.depth_maps is not None, "buildDepthMaps")

chunk.buildPointCloud()
assert_stage(chunk.point_cloud and len(chunk.point_cloud.points) > 0,
             "buildPointCloud")
```

## Pitfall 4 — Document-save-as resets the chunk handle

A subtle one: calling `doc.save(new_path)` (with a path argument)
behaves like *Save As* — it saves the project under a new path
**and re-opens it**. The reopen invalidates any `chunk` variable
you held before:

> **Demo verified:** ✗ — pending Tier 3 reproduction on a real Metashape install.

```python
import Metashape

doc = Metashape.app.document
chunk = doc.chunk

doc.save("/path/to/new_project.psx")
# At this point, the OLD `chunk` reference may be stale.
# Re-fetch it:
chunk = doc.chunk
```

The safe pattern: call `doc.save()` (no argument) for the
"save in place" case. Use `doc.save(path)` only when you
actually mean "save as a new project," and re-fetch all object
handles afterwards.

## Pitfall 5 — PSX format required for orthomosaic / DEM / tiled model

A subtle gotcha for headless scripts that generate orthomosaics
or DEMs: these assets can ONLY be saved into the PSX project
format, not the older PSZ format.

> "Orthomosaic, DEM and tiled model can be only generated and
> saved in the PSX file format. I suggest to save the project
> in PSX format from the very beginning (right after creating
> Metashape.Document instance) and then just call doc.save()
> method without path argument."
> — Agisoft support, 2020-11-25, Metashape 1.6
> ([permalink](https://www.agisoft.com/forum/index.php?topic=4853.msg56725#msg56725))

This restriction persists in Metashape 2.x: PSX is the only
project format that supports orthomosaic, DEM, and tiled-model
storage. PSZ (single-archive format) remains for backward
compatibility but cannot hold these products.

The fix: save the project to a `.psx` path BEFORE building
any of those products:

> **Demo verified:** ✗ — pending Tier 3 reproduction on a real Metashape install.

```python
import Metashape

doc = Metashape.Document()
doc.save("/path/to/project.psx")   # creates the .psx file + .files folder

chunk = doc.addChunk()
# ... add photos, align, etc.

chunk.buildOrthomosaic(...)         # works — PSX project is in place
doc.save()                           # save updates without re-pathing
```

If you start with `Metashape.Document()` and never save before
calling `chunk.buildOrthomosaic(...)`, the build typically
fails with a "Null project file" or "Can't write" error
(behaviour varies by version: in some 2.x builds it raises
during the build call; in others it completes but
`chunk.orthomosaic` remains `None`). The fix is unchanged
across versions: save as PSX first.

The PSZ format (single-archive project) is also more limited:
no network/cloud processing support, no fine-level task
subdivision, slow load/save for large projects. PSX is the
recommended default for any new script. Old projects in PSZ
can be opened and re-saved as PSX via *File → Save As → PSX*.

## Caveats

- **`Metashape.app.document` is read-only.** You can't assign a
  new value to it from scripts; the GUI manages it.
- **A `Metashape.Document()` instance is not the same as the
  GUI document.** Operations on a script-created Document don't
  affect what the GUI shows; you must `doc.save()` and have the
  user open the file (or restart Metashape) to see changes.
- **`chunk.depth_maps`, `chunk.point_cloud`, `chunk.model`,
  `chunk.orthomosaic`** are all None until the corresponding
  build stage completes. Always check before iterating.
- **Stage failures sometimes leave half-built data.** A
  *buildPointCloud* that crashes mid-way may leave
  `chunk.point_cloud` non-None but with a fraction of expected
  points. The post-condition checks above guard against this.
- **The `--run` (or `-r`) command-line flag** runs the script
  but exits Metashape afterwards. For interactive command-line
  runs that keep Metashape open, use `--script` instead (where
  supported).

## See also

- [Mesh and point-cloud editing recipes](mesh-pointcloud-editing-recipes.md)
  — Recipe 5 demonstrates the same try/except pattern for
  empty-chunk handling in `split_in_chunks` workflows.
- [Auto-export per-shape: orthomosaic, DEM, point cloud, mesh, KMZ](../../workflow/export-reporting/auto-export-per-shape.md)
  — uses `Metashape.app.getExistingDirectory` (GUI-only); good
  example to refactor with the `get_param` pattern above for
  headless use.
- [`exportPointCloud` defaults: GUI vs Python CRS difference](../../workflow/export-reporting/exportpoints-crs-default.md)
  — another GUI-vs-Python behavioural difference (unrelated:
  CRS defaults, not document handles).

## References

- *Metashape Python API Reference* (2.3.1):
  `Metashape.app`, `Metashape.app.document`,
  `Metashape.app.getInt`, `Metashape.app.getString`,
  `Metashape.app.getExistingDirectory`,
  `Metashape.app.getCoordinateSystem`, `Metashape.Document`,
  `Document.open`, `Document.save`, `Document.chunk`.
- [*How to run the script in headless mode from the command-line* (Agisoft KB)](https://agisoft.freshdesk.com/support/solutions/articles/31000133141)
  — supplementary tutorial.
- Forum thread, [*Metashape.app.document is NoneType*, 2020](https://www.agisoft.com/forum/index.php?topic=12603.msg55985#msg55985)
  — the GUI-vs-headless context restriction.
- Forum thread, [*Validate if the stage was successfully
  completed*, 2023](https://www.agisoft.com/forum/index.php?topic=15240.msg66874#msg66874)
  — try/except pattern for stage assertion errors.

