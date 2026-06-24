---
title: "Network processing: setup, monitoring, and common failure modes"
status: unverified
applies_to: Metashape Pro 2.x — `metashape --worker` and `metashape-server` are unchanged in concept since PhotoScan 1.x
edition: Pro
last_reviewed: 2026-06-04
diataxis: how-to
confidence: medium
---

# Network processing: setup, monitoring, and common failure modes

> **Confidence:** *medium.* The architectural overview is from
> the official manual at the dialog level. Operational
> guidance and common failure modes come from forum threads,
> with attribution. The CLI flags are confirmed against the
> manual's *Distributed processing* chapter.

## Problem

You have a CPU-bound aerial-survey workload that doesn't fit
in one workstation's processing budget — *Build Depth Maps*
takes hours, *Build Point Cloud* takes more, and the project
needs to deliver this week. Metashape's **network processing**
mode distributes the work across multiple workstations on a
local network. This article covers when network processing
helps, how to set it up, and the common failure modes that
trip up first-time deployments.

## When network processing makes sense

Per the official manual:

> "Processing tasks are divided between the workers on a chunk
> by chunk or frame by frame basis (when possible). In addition
> a more fine grained distribution can be optionally enabled
> for image matching and alignment, generation of point clouds,
> tiled models, DEMs and orthomosaics, as well as model
> generation from depth maps, in which case processing of
> individual chunks/frames will be further subdivided between
> several processing workers."
> — *Metashape Pro Manual* 2.3, § *Distributed processing*

Concrete decision rule:

| Scenario | Use network processing? |
|----------|:----------------------:|
| Single project, multi-day processing budget on one workstation | ✓ yes |
| Multiple projects in parallel, each fits on one workstation | ❌ no — run separately |
| Multi-chunk projects | ✓ yes (chunk-level parallelism scales well) |
| Single-chunk project with low total processing time (<2h) | ❌ no — coordination overhead exceeds gains |
| Mixed Windows / Linux workstations | ✓ but with extra setup (path-prefix configuration) |

For projects where total processing fits in <4 hours on one
machine, the setup-and-coordination overhead of network
processing usually exceeds the wall-clock savings.

## Architecture

Three roles, each running its own Metashape binary:

| Role | What it runs | Hardware tier |
|------|--------------|---------------|
| **Server** | `metashape-server` (binary), single instance | Slow hardware OK; just coordinates |
| **Worker** (1 or more) | `metashape --worker` | Fast hardware required; this is where the actual computation happens |
| **Client** | `metashape` (regular) configured as network client | Fast hardware; the user's workstation |

Plus shared infrastructure:

- **Shared storage** accessible from all workers and clients
  at the same absolute path.

## Setup checklist

### 1. Shared storage with consistent paths

Every worker and client must reach the project files at the
same path. Two paths to this:

- **Same mount point on Linux** — e.g., `/mnt/metashape-shared/`
  on every worker.
- **Same UNC path on Windows** — e.g.,
  `\\fileserver\metashape\` on every worker.
- **Path prefix per worker** (mixed environments) — workers
  use their own local path, with a prefix translated against
  the server's path.

The manual cautions:

> "Before proceeding to the following steps please make sure
> that shared network storage is accessible from all processing
> and client workers using the same absolute path. It should be
> either mounted to the same folder on all workers (Linux), or
> should have the same UNC network path (Windows)."
> — *Metashape Pro Manual* 2.3

### 2. Static IP for the server

> "It is recommended to configure server with a static IP
> address, not dynamically assigned one. This IP address will
> be needed for each processing worker and client."
> — *Metashape Pro Manual* 2.3

DHCP-assigned addresses break the cluster on the next reboot.

### 3. Server start command

```bash
metashape-server --host 10.0.1.1
```

Options:

- `--host <ip>[:port]` — interface and port (default port:
  5840). Specify multiple times for multi-interface.
- `--resume-workers` — auto-resume paused workers on connect
  (default behaviour pauses each worker on connection).
- `--scheduling sequential` (default) or `--scheduling parallel`
  — sequential serializes equal-priority projects;
  parallel distributes workers across them.

### 4. Worker start command

```bash
metashape --worker --host 10.0.1.1
```

Optional:

- `--root <prefix>` — override the worker's path prefix for
  the shared storage (use when the worker's mount point
  differs from the server's reference path).

### 5. Client configuration

In the GUI: *Tools → Preferences → Network* tab. Enable
*Network processing*, enter the server IP, save preferences.
Subsequent processing operations now offer a *Network
processing* checkbox in the dialog.

For Python-driven workflows, set
`Metashape.app.settings.setValue("network/host", "10.0.1.1")`
before submitting tasks; then start operations with
`network=True`.

## Recipe — submit a build job from the client

> **Demo verified:** ✗ — pending Tier 3 reproduction on a real Metashape install.

```python
import Metashape

doc = Metashape.app.document
chunk = doc.chunk

# Workflow operations accept network=True to dispatch to the cluster
chunk.matchPhotos(downscale=1, generic_preselection=True, network=True)
chunk.alignCameras(network=True)
chunk.buildDepthMaps(downscale=2, filter_mode=Metashape.FilterMode.AggressiveFiltering, network=True)
chunk.buildPointCloud(network=True)
```

The client returns immediately after each call; the actual
work runs on the workers. Use *Tools → Network Monitor* (or
the standalone `metashape-monitor` binary) to track progress.

## Common failure modes

### "Server stopped" / connection refused

- The server's static IP changed (DHCP-assigned); workers
  can no longer find the server.
- Firewall blocking port 5840 on the server's host.
- The server process crashed; restart it.

Verification:

```bash
# From a worker host:
nc -zv 10.0.1.1 5840   # should report "succeeded"
```

### "Path not found" / "image not found" mid-job

A worker can't reach a path that the server / client could.
Causes:

- Inconsistent mount point or UNC path (see Setup checklist
  step 1).
- Permissions: the worker's user account doesn't have read
  access to the project files.
- The shared storage was unmounted on a worker that's still
  registered.

Verification:

```bash
# On each worker, run:
ls /mnt/metashape-shared/your_project.psx
```

If any worker can't list the file, the cluster will fail
mid-job.

### Worker disconnects randomly

Usually a network issue (cable, switch, intermittent NIC),
not Metashape. Check OS-level network logs.

### Worker shows "ERROR: BAD ALLOCATION"

Out of RAM on the worker for the assigned task. Reduce per-task
RAM by lowering `quality` (depth maps) or splitting the chunk
into smaller chunks. See [the bad-alloc thread for context](https://www.agisoft.com/forum/index.php?topic=5553.0)
(forum t=5553).

### License complaints

Network processing needs **Metashape Professional** on every
worker and on the client — but the license may be **node-locked
or floating** (or a mix). Each worker consumes one license; the
**server needs none**; the client needs one (and a machine that
is both worker and client needs only one). A 1-server /
10-worker cluster therefore needs 10 worker licenses (node-locked,
a floating count of 10, or a mix), plus one for the client —
unless that client is also one of the 10 workers, in which case it
shares a license.
Standard Edition cannot act as server, worker, or client. Check
*Tools → License → Information* on each machine. (Per
[*How many licenses are required for network processing* (Agisoft KB)](https://agisoft.freshdesk.com/support/solutions/articles/31000145920)
and [*Is network processing supported in Standard and/or Professional edition* (Agisoft KB)](https://agisoft.freshdesk.com/support/solutions/articles/31000145919).)

## Performance tuning

> "For projects calculated over network processing time will
> be displayed as a sum of the time spent for processing by
> each node."
> — *Metashape Pro Manual* 2.3

The displayed total time is the *sum* of per-worker times, NOT
the wall-clock time. To assess actual speedup, look at job
start / end timestamps, not the displayed elapsed.

Stage-by-stage scaling:

| Stage | Network parallelism quality |
|-------|------------------------------|
| Match Photos | Excellent (per-pair parallelism) |
| Align Cameras | Poor (single-threaded by design) — runs on one worker |
| Build Depth Maps | Excellent (per-camera) |
| Build Point Cloud | Good (per-region) |
| Build Mesh (depth-maps) | Good if `split_in_blocks=True` |
| Build Texture | Limited |
| Build DEM | Excellent (per-tile) |
| Build Orthomosaic | Excellent (per-tile) |
| Build Tiled Model | Excellent (per-tile) |

Don't expect linear scaling on Align Cameras; expect near-
linear scaling on Match Photos, Build Depth Maps, Build DEM,
Build Tiled Model.

## Caveats

- **Network processing is Pro-edition only.** Standard Edition
  has no `--worker` mode.
- **Shared storage is the bottleneck for many clusters.** A
  10GbE shared NAS is much better than 1GbE. If the workers
  are CPU-bound but storage is saturated, upgrading the NAS
  helps more than adding workers.
- **Server is a single point of failure.** Plan for the server's
  uptime (UPS, monitoring, watchdog). Lost server = lost
  in-progress jobs.
- **Worker version mismatch.** All workers must run the same
  Metashape version as the server. Mixed versions produce
  silent failures or incorrect results.
- **Server CPU usage is light.** A small VM (2 vCPU, 4GB RAM)
  is sufficient as the server. Don't waste a fast workstation
  in the server role.
- **The `network=True` flag does not validate cluster health
  before submitting.** If no workers are connected, the job
  silently waits in the queue. Check Network Monitor before
  starting long jobs.

## See also

- [Performance tuning: CPU, RAM, GPU, and OS](../../topics/performance/cpu-ram-gpu-os-tuning.md)
  — for sizing per-worker hardware.
- [Multi-GPU setups: SLI, TCC mode, and utilization](../../topics/performance/multi-gpu-utilization.md)
  — per-worker GPU configuration.
- [When to use chunks: dataset partitioning strategies](../../topics/multi-chunk/when-to-use-chunks.md)
  — chunk-level parallelism is the cleanest fit for network
  processing.

## References

- *Metashape Pro User Manual* (2.3), ch. 8 *Distributed
  processing → Local network processing* — comprehensive
  setup reference (~10 pages).
- *Metashape Python API Reference* (2.3.1):
  `Chunk.matchPhotos(network=True)`, `Chunk.alignCameras`,
  `Chunk.buildDepthMaps`, `Chunk.buildPointCloud`,
  `Chunk.buildModel`, `Chunk.buildDem`,
  `Chunk.buildOrthomosaic`, `Chunk.buildTiledModel` — all
  accept `network=True`.
- [*How to configure the network processing* (Agisoft KB)](https://agisoft.freshdesk.com/support/solutions/articles/31000145918)
  — the official server/worker/client setup walkthrough (the
  2.2.0+ `metashape-server` utility, `--resume-workers`,
  `--root`, Network Monitor); plus [*Is network processing supported in Standard and/or Professional edition* (Agisoft KB)](https://agisoft.freshdesk.com/support/solutions/articles/31000145919),
  [*How many licenses are required for network processing* (Agisoft KB)](https://agisoft.freshdesk.com/support/solutions/articles/31000145920),
  and [*Licensing for the network processing* (Agisoft KB)](https://agisoft.freshdesk.com/support/solutions/articles/31000133121)
  for the licensing rules.

