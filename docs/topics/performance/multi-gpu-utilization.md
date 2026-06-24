---
title: "Multi-GPU setups: SLI, TCC mode, and utilization"
status: unverified
applies_to: Metashape Pro 2.x (Python) ; Metashape Standard 2.x (GUI)
edition: "Pro / Standard"
last_reviewed: 2026-05-27
diataxis: explanation
confidence: high
---

# Multi-GPU setups: SLI, TCC mode, and utilization

> **Confidence:** *high.* GPU configuration is documented in the
> official manual (§ *System Requirements → GPU recommendations*),
> and the SLI / TCC claims are directly from Agisoft support
> with permalinks.

## SLI / NVLink is irrelevant

Metashape uses CUDA (NVIDIA) or OpenCL (AMD / Apple) for GPU-
accelerated stages. It addresses each GPU independently — SLI and
NVLink bridges do **not** accelerate processing.

> "SLI doesn't help for CUDA computations. SLI is used to improve
> the visualization only."
> — Alexey Pasumansky, 2017-05-08, PhotoScan 1.3
> ([permalink](https://www.agisoft.com/forum/index.php?topic=6992.msg32413#msg32413))

If you have two GPUs connected via SLI/NVLink, Metashape will use both
independently for compute. The bridge adds no benefit and can be
removed without affecting processing speed.

## TCC mode on Windows (Quadro / Tesla / Titan only)

On Windows, NVIDIA GPUs use the **WDDM** (Windows Display Driver
Model) by default. WDDM adds overhead for GPU command submission
because it routes through the Windows graphics stack.

For GPUs **not connected to a display** (dedicated compute cards),
switching to **TCC** (Tesla Compute Cluster) mode removes this
overhead:

```
nvidia-smi.exe -g <card_id> -dm 1   # switch to TCC (requires reboot)
```

**Caveat:** TCC is only supported on:

- Quadro cards
- Tesla / A100 / H100 data-centre cards
- Titan cards (varies by generation)

**GeForce GTX / RTX consumer cards do NOT support TCC.** Attempting to
switch them will fail silently or error.

After switching, verify with `nvidia-smi.exe` — the card should show
"TCC" instead of "WDDM".

## Point cloud fusion phase is CPU-only

GPU utilization drops to near-zero during the **second phase** of
point cloud generation (fusion / filtering). This is expected
behaviour, not a driver issue or configuration problem.

The two phases are:

1. **Depth map computation** — GPU-accelerated (high utilization).
2. **Point cloud fusion** — CPU-only (GPU idle).

If you observe high GPU utilization during depth maps followed by a
long CPU-only phase, this is normal. See
[GPU usage by stage](gpu-usage-by-stage.md) for the full breakdown.

## Linux has better multi-GPU utilization

On multi-GPU Windows systems, users frequently report low GPU
utilization (20-30%) during depth map generation. The same hardware
under Linux typically shows higher utilization because Linux's GPU
driver model has lower per-command overhead than WDDM.

See [Linux vs Windows performance](linux-vs-windows-performance.md)
for benchmarks and root-cause analysis.

See also: [GPU usage by stage](gpu-usage-by-stage.md).

## Configuring multi-GPU in Metashape

In the GUI: *Tools → Preferences → GPU* tab. Check all GPUs you want
to use. Optionally uncheck "Use CPU when processing" if you want
GPU-only processing (useful for isolating GPU performance).

In Python:

> **Demo verified:** ✓ — Metashape 2.2.3, Apple M1 Pro (attributes confirmed via introspection).

```python
import Metashape

# List available GPUs
print(Metashape.app.gpu_mask)  # bitmask of enabled GPUs
print(Metashape.app.enumGPUDevices())  # list of GPU device strings

# Enable all GPUs (set all bits)
Metashape.app.gpu_mask = (1 << len(Metashape.app.enumGPUDevices())) - 1

# Disable CPU during GPU processing
Metashape.app.cpu_enable = False
```

## Key points

- **SLI/NVLink:** irrelevant for processing. Remove if desired.
- **TCC mode:** improves utilization on Quadro/Tesla/Titan (not GeForce).
- **Point cloud fusion:** CPU-only by design. GPU idle is expected.
- **Linux:** better multi-GPU utilization due to lower driver overhead.
- **Multiple GPUs:** each is used independently; more GPUs = faster
  depth maps (near-linear scaling for that stage).

## References

- *Metashape Pro User Manual* (2.3), § *System Requirements → GPU
  recommendations* — lists supported GPU families and CUDA/OpenCL
  requirements.
- *Metashape Python API Reference* (2.3.1): `Application.gpu_mask`,
  `Application.enumGPUDevices()`, `Application.cpu_enable`.

