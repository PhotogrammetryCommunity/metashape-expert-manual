---
title: "Linux vs Windows: 10–40% faster processing"
status: unverified
applies_to: Metashape Pro 2.x ; Metashape Standard 2.x
edition: "Pro / Standard"
last_reviewed: 2026-05-27
diataxis: explanation
confidence: medium
---

# Linux vs Windows: 10–40% faster processing

> **Confidence:** *medium.* Based on community benchmarks (3
> users, 3 hardware configurations, December 2024). Agisoft has
> not confirmed or denied the findings. No official documentation
> addresses OS-level performance differences. This article cannot
> be demonstrated via a sample dataset — it requires comparative
> benchmarking on identical hardware under two operating systems.

## The finding

Multiple independent benchmarks (December 2024, Metashape 2.1.3+)
report that Metashape runs **10–40% faster on Linux** than on Windows
on identical hardware.

| Hardware | Linux (Rocky 9.5) | Windows 11 | Δ |
|----------|-------------------|------------|---|
| AMD Ryzen 9 9900X + RTX 4090 | 4380 s | 6016 s | +37% slower on Win |
| Intel i9-9900K + RTX 2080 Super | 8999 s | 11815 s | +31% slower on Win |

Source: Agisoft forum, 2024-12-07, Metashape 2.1
([permalink](https://www.agisoft.com/forum/index.php?topic=16909.0))

## Controlled isolation

A controlled test with locked CPU (4.4 GHz) and GPU (1700 MHz)
frequencies on debloated Windows 10 LTSC vs Arch Linux showed a
narrower gap: **~10% difference**.

The residual ~5% is attributed to OS overhead:

| Metric | Windows | Linux |
|--------|---------|-------|
| Processes | ~141 | ~62 |
| Threads | ~1720 | ~149 |
| OS handles / kernel threads | ~50,500 | ~259 |

## Root causes

The performance gap has multiple contributing factors:

1. **Windows background services.** Telemetry, Defender real-time
   scanning, Superfetch, Cortana, Windows Update. Each consumes CPU
   cycles and causes context switches. Disabling these narrows the gap
   significantly.

2. **Thread scheduling overhead.** The Windows kernel maintains far
   more threads and handles than a minimal Linux installation. Each
   context switch has a cost; with 1700 threads vs 149, the aggregate
   overhead is measurable on compute-heavy workloads.

3. **WDDM driver model.** On Windows, NVIDIA GPUs use the Windows
   Display Driver Model (WDDM), which adds overhead for GPU command
   submission compared to Linux's direct kernel-mode driver. This
   affects all GPU-accelerated stages (feature detection, depth maps).

4. **File system.** NTFS vs ext4/XFS may contribute for I/O-heavy
   stages (loading images, writing depth maps). Not conclusively
   isolated in these benchmarks.

## What Agisoft says

Agisoft support requested detailed per-step logs for investigation
but made no official statement on the performance difference as of
December 2024. In an older thread (2017), Agisoft support explicitly
recommended trying Linux for multi-GPU setups where Windows showed low
utilization:

> "I can suggest to try running PhotoScan on Linux [...] As there
> shouldn't be an issue related to WDDM driver, I believe the
> utilization of the cards would be considerably better."
> — Alexey Pasumansky, 2017-05-04, PhotoScan 1.3
> ([permalink](https://www.agisoft.com/forum/index.php?topic=6992.msg33765#msg33765))

## Practical recommendations

- **If you process large datasets regularly**, the 10-40% speedup on
  Linux compounds into significant time savings. A dual-boot or
  dedicated Linux processing machine pays for itself quickly.

- **If you must stay on Windows**, debloat aggressively: disable
  Defender real-time scanning during processing, disable telemetry,
  Superfetch, and unnecessary services. Windows 10 LTSC is closer to
  Linux performance than stock Windows 11.

- **The difference is per-step, not per-stage.** Every processing step
  (match photos, align, depth maps, mesh, texture) is affected, not
  just GPU-heavy stages. This suggests the overhead is systemic (OS
  scheduling + driver model), not specific to one algorithm.

- **SLI/NVLink does not help.** Multi-GPU setups benefit from Linux
  even more because WDDM overhead affects each GPU independently. See
  [Multi-GPU setups](multi-gpu-utilization.md) and
  [GPU usage by stage](gpu-usage-by-stage.md) for details.

## Caveats

- Sample size is small (3 users, 3 hardware configurations).
- The 30-40% figure is for "stock" Windows vs Linux. With debloating,
  the gap narrows to ~5-10%.
- Agisoft has not confirmed or explained the difference officially.
- Results are from December 2024 (Metashape 2.1.3); newer versions may
  differ.
- Linux requires manual NVIDIA driver installation and lacks the
  Metashape GUI's full feature parity (some dialogs differ slightly).

## References

- *Metashape Pro User Manual* (2.3), § *System Requirements* —
  lists Windows, macOS, and Linux as supported platforms without
  noting performance differences.
- *Metashape Python API Reference* (2.3.1): `Application.gpu_mask`,
  `Application.enumGPUDevices()`.

