---
title: "Performance tuning: CPU, RAM, GPU, and OS"
status: unverified
applies_to: Metashape Standard 2.x ; Metashape Pro 2.x
edition: "Pro / Standard"
last_reviewed: 2026-06-05
diataxis: explanation
confidence: medium
---

# Performance tuning: CPU, RAM, GPU, and OS

> **Confidence:** *medium.* The CPU / GPU / OS findings are
> consistent across multiple forum threads (2013–2025) but
> the specific BIOS workarounds and CPU-stability claims are
> hardware- and firmware-dependent. Linux-vs-Windows speedups
> are community-benchmarked, not officially confirmed.

The official manual's *System Requirements* page lists hardware
recommendations but does not cover **what actually matters for
sustained Metashape throughput**, **why the differences arise**,
or **the BIOS / OS-level interactions** that most users
underestimate. This article consolidates the operational findings
from the forum.

The starting point: the existing
[GPU usage by stage](gpu-usage-by-stage.md) article enumerates
which processing steps use the GPU, the CPU, or both. Read that
first if you have not. This article addresses everything else:
CPU selection, RAM sizing, multi-GPU setups, the OS gap, and
known hardware instability.

## CPU: frequency matters more than core count

For most Metashape stages, **6–8 high-frequency cores beat 40+
low-frequency cores**. The classic finding from a 2013 PhotoScan
benchmark thread:

> "For dual-Xeon systems I can suggest to use 6-8 core Xeons
> with highest possible frequency. Using 40 cores with 2.2 GHz
> could be even slower than desktop six-core i7."
> — Alexey Pasumansky, 2015-02-09, PhotoScan 1.1
> ([permalink](https://www.agisoft.com/forum/index.php?topic=1868.msg17853#msg17853))

Reasons:

- **Thread synchronisation overhead** scales super-linearly past
  some saturation threshold. Beyond ~32 cores on most workloads,
  threading overhead consumes more cycles than the additional
  cores contribute. The exact threshold varies by stage and OS.
- **Turbo Boost only sustains briefly.** Sustained AVX2 /
  AVX-512 loads thermally throttle to base clock within seconds.
  Marketing labels (e.g., "5.8 GHz Turbo") are misleading;
  benchmark against the **base clock**.
- **Per-stage scaling differs.** On Agisoft's 2015 dual-Xeon
  tests:

  | Stage | Dual-Xeon vs Single speedup |
  |-------|-----------------------------|
  | Align Photos | 20–40% |
  | Build Point Cloud (CPU phase) | ~30% |
  | Build Mesh | 10–15% |

Modern CPUs scale further than 2015's, but the diminishing-returns
pattern remains.

## RAM: peak is during mesh / depth-map storage

See the existing [RAM and quality settings](ram-and-quality-settings.md)
article. Briefly: peak RAM is usually during *Build Mesh* (Ultra
quality) or during depth-map fusion if the project has many high-
resolution depth maps in memory simultaneously.

A practical guideline (Agisoft's): **4 GB → 30–50 photos at 10 MPx;
16 GB → 300–500 photos.** Modern builders typically target
64–128 GB for medium-large projects.

## GPU: depth maps + texture only

Per [GPU usage by stage](gpu-usage-by-stage.md), the GPU is
heavily used during:

- *Build Depth Maps* (the most GPU-intensive stage)
- *Build Point Cloud* (depth-maps phase only — phase 2 is CPU)
- *Build Texture* (since 2.x)

Other stages (alignment, mesh, orthomosaic, DEM) are CPU-only.
This means **GPU upgrades only help if depth maps or texture
generation dominates your wall-clock time**. For projects
dominated by alignment or orthomosaic export, GPU spending is
wasted.

### Multi-GPU: SLI is irrelevant; TCC mode helps Quadro/Tesla

See [Multi-GPU setups](multi-gpu-utilization.md). Three
operational facts:

- **SLI / NVLink does not accelerate compute.** Bridges are for
  visualisation only; remove them without consequence.
- **TCC mode** improves utilisation on Quadro / Tesla / Titan
  by removing WDDM overhead. **Not supported on GeForce
  GTX/RTX consumer cards.**
- **Linux has lower multi-GPU overhead** than Windows
  (no WDDM in the path).

## OS: Linux 10–40% faster than Windows on the same hardware

See [Linux vs Windows performance](linux-vs-windows-performance.md).
Three ways the gap manifests:

1. **Stock Windows vs stock Linux:** 30–40% faster on Linux
   (community benchmarks, December 2024, multiple users).
2. **Debloated Windows 10 LTSC vs Linux:** narrows to ~5–10%.
3. **Multi-GPU Windows:** further compounded by WDDM driver
   overhead per GPU.

Root causes:

- Windows background services (telemetry, Defender, Superfetch)
  consume cycles.
- Linux's GPU driver model has lower per-command overhead than
  WDDM.
- File-system differences (NTFS vs ext4/XFS) may contribute for
  I/O-heavy stages but are not conclusively isolated.

For sustained Metashape work, **Linux pays off** — either as a
dedicated processing machine or via dual-boot.

## Hardware instability: Intel i9-13900K / i9-14900K

A documented stability issue affects Intel Core i9-13900K and
i9-14900K CPUs under sustained AVX2 load (which Metashape exercises
during alignment and point-cloud computation). The crashes are
**not Metashape bugs** — they affect other CPU-heavy applications
too. Multiple forum users have confirmed BIOS-level workarounds:

- **Lower the *Turbo Power Limits*** in BIOS (Gigabyte and
  others).
- **Cap the Performance Active-Core Tuning Ratio** in Intel
  Extreme Tuning Utility (e.g., to 53× on a 14900K).
- **Apply the Intel microcode update** released in 2024 (newer
  BIOS revisions include this automatically).

Diagnostic tools the Agisoft team recommends:

- *Memtest86* — multithreaded RAM check (run from bootable USB)
- *Intel Processor Diagnostic Tool* — official CPU stress test
- *Prime95 with AVX2* — exercises the same instructions Metashape uses
- *Intel Extreme Tuning Utility* — AVX2 stress test + tuning

If your workstation crashes on alignment but other apps run
cleanly, run the AVX2 stress test first; the 13/14900K
instability often passes Prime95 SSE but fails AVX2.

> "Quite a lot of cases with i9-13900K and i9-14900K (and similar)
> CPU system crashes were related to the mentioned hardware
> issues, as confirmed by users."
> — Alexey Pasumansky, 2023-10-31, Metashape 2.1
> ([permalink](https://www.agisoft.com/forum/index.php?topic=15903.msg68784#msg68784))

For the full step-by-step BIOS-workaround procedure with vendor-
specific menu paths (ASUS, Gigabyte, MSI, ASRock), the diagnostic
ladder, and the crash-report locations Agisoft support needs, see
[Intel i9-13900K / 14900K instability: BIOS workarounds](../hardware-io/intel-13900k-14900k-instability.md).

## Practical recommendations

For a new workstation primarily running Metashape:

| Component | Choose | Avoid |
|-----------|--------|-------|
| CPU | 8–16 cores at 4.0+ GHz base, AMD Ryzen 7/9 or Intel i7/i9 (post-microcode-fix) | 32+ slow cores; pre-2024-microcode i9-13900K/14900K |
| RAM | 64–128 GB ECC (more for >1000-image projects) | 32 GB for serious work |
| GPU | Quadro / RTX 4090 with 24 GB VRAM (or multi-GPU on Linux for depth maps) | SLI bridges; GTX cards under 8 GB VRAM |
| OS | Linux for primary work; Windows for GUI-heavy editing | Stock Windows 11 with full bloat |
| Storage | NVMe for project working directory; large HDD/SAN for archive | Spinning HDD as primary |

For an existing workstation:

- **Run Memtest86** before blaming Metashape for crashes.
- **Disable Windows Defender real-time scanning** during
  long-running batches.
- **Consider a Linux dual-boot** if alignment / depth maps
  dominate your throughput.
- **Upgrade BIOS** if on i9-13/14900K to get the 2024 microcode
  fix.

## References

- *Metashape Pro User Manual* (2.3) §
  *System Requirements* — hardware compatibility list (no
  performance commentary).
- [*Hardware recommendations* (Agisoft KB)](https://agisoft.freshdesk.com/support/solutions/articles/31000172512)
  (the official sizing baseline), [*General information related to GPU processing* (Agisoft KB)](https://agisoft.freshdesk.com/support/solutions/articles/31000150614)
  (supported GPUs, configuring the GPU tab, Vulkan texture
  blending), and [*Does Metashape work on Apple M1 architecture?* (Agisoft KB)](https://agisoft.freshdesk.com/support/solutions/articles/31000158928).
- [GPU usage by stage](gpu-usage-by-stage.md) — companion
  article enumerating GPU usage per processing step.
- [Multi-GPU setups](multi-gpu-utilization.md) — SLI, TCC, WDDM
  details.
- [Linux vs Windows performance](linux-vs-windows-performance.md)
  — benchmark data and root-cause analysis.
- [RAM and quality settings](ram-and-quality-settings.md) —
  memory peak per stage.

## See also

- [Undocumented tweaks: a partial reference](../scripting/undocumented-tweaks-reference.md)
- [Diagnosing CUDA / OpenCL errors](diagnosing-cuda-opencl-errors.md)

