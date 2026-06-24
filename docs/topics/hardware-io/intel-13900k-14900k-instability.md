---
title: "Intel i9-13900K / 14900K instability: BIOS workarounds for Metashape crashes"
status: unverified
applies_to: Metashape Pro 2.x and Metashape Standard 2.x — same hardware-level issue, independent of Metashape version
edition: "Pro / Standard"
last_reviewed: 2026-05-29
diataxis: how-to
confidence: high
---

# Intel i9-13900K / 14900K instability: BIOS workarounds for Metashape crashes

> **Confidence:** *high.* The CPU instability is widely attested
> in the Agisoft forum and across other CPU-heavy workloads
> (Unreal Engine shader compilation, scientific Python, BMW
> renders); BIOS workarounds are forum-attested with three
> independent users reporting success. This is a hardware-platform
> issue, not a Metashape bug.

## Problem

Your workstation runs an Intel i9-13900K, i9-14900K, or similar
13th/14th-gen "K"-series desktop CPU. Metashape crashes
inconsistently during *Align Photos* (specifically the
"estimating camera locations" sub-stage) or *Optimize Cameras*.
The crashes appear random — the same project may align cleanly
one run and crash another with identical parameters. Other
CPU-heavy applications may show similar instability.

This is **not a Metashape bug.** Intel acknowledged in 2024 that
13th and 14th-gen K-series CPUs have a microcode-level instability
related to elevated voltage / clock requests under sustained
load, particularly affecting heavily-binned high-end SKUs. The
issue manifests across many applications; Metashape's *Estimate
Camera Locations* stage is among the most affected because it
sustains 100% CPU on all cores for minutes-to-hours.

## Diagnostic ladder

Before applying BIOS workarounds, rule out conventional hardware
faults. Agisoft support's published diagnostic order:

1. **Memtest86** — multithreaded RAM check (run from bootable
   USB). Test each module individually to isolate failures.
   Tip: Metashape's own access pattern can stress RAM more than
   Memtest, so a clean Memtest run does NOT rule out RAM
   instability.
2. **Intel Processor Diagnostic Tool** — official Intel CPU
   stress test, free download.
3. **Prime95 with AVX2** — community-standard CPU stress test
   that exercises the AVX2 instructions Metashape uses heavily.
4. **Intel Extreme Tuning Utility (XTU) → Stress Test → AVX2**
   — Intel's tuning + diagnostic suite.

> "If such random crashes occur during CPU/RAM-intensive steps,
> it is recommended to:
> - perform multithreaded Memtest86 checks,
> - confirm if crashes happen regardless the number of RAM
>   modules used,
> - try reducing RAM frequency in BIOS,
> - try CPU stress test using Prime95 (with AVX2),
> - try Intel Processor Diagnostic Tool,
> - try Intel XTU CPU stress test."
> — Agisoft support, 2023-10-31, Metashape 2.1
> ([permalink](https://www.agisoft.com/forum/index.php?topic=15903.msg72205#msg72205))

If all four diagnostic tools pass cleanly **and** Metashape still
crashes, the BIOS workarounds below are the most reliable
remediation reported in the forum.

## BIOS workarounds (forum-attested)

Each workaround restricts the CPU's maximum sustained clock or
voltage slightly, which prevents the instability that triggers
crashes. The cost is a 5-15% performance reduction on heavily-
threaded workloads.

### Workaround 1 — Cap Turbo Power Limits (PL1 / PL2)

In BIOS, set *Turbo Power Limits* (PL1 and PL2 / "long-duration"
and "short-duration" power caps) to fixed values rather than the
motherboard's default AUTO setting. Recommended caps:

- **PL1 (long-duration):** 253 W (Intel's official 13900K/14900K
  base TDP) — this is what the chip is rated for sustained.
- **PL2 (short-duration):** 253 W — same as PL1, eliminating the
  brief Turbo overshoot.

This is reported to fix many crashes:

> "I think it could be a setting in the Gigabyte BIOS that is
> causing the issues. In the BIOS, under CPU settings: 'Turbo
> Power Limits' is default on 'AUTO' [...] Changing from 'AUTO'
> to 'Intel POR' currently seems to be rectifying the issue.
> This has worked for me on a couple of small (700-800 image)
> datasets, now trying on a 63k image dataset."
> — 3dMB Ltd, 2024-01-19, Metashape 2.1
> ([permalink](https://www.agisoft.com/forum/index.php?topic=15903.msg69649#msg69649))

The setting name varies by motherboard:

| Vendor | Setting path |
|--------|--------------|
| ASUS | *Ai Tweaker → Internal CPU Power Management → Long Duration Power Limit / Short Duration Power Limit* |
| Gigabyte | *Tweaker → Advanced CPU Settings → Turbo Power Limits* |
| MSI | *OC → CPU Specifications → Long Duration Power Limit / Short Duration Power Limit* |
| ASRock | *OC Tweaker → CPU Configuration → Long Duration Power Limit* |

### Workaround 2 — Cap the Performance Active-Core Tuning Ratio

In Intel XTU (or BIOS, where exposed), set the *Performance
Active-Core Tuning Ratio* (per-core multiplier) to a value below
the chip's stock turbo. For 13900K stock turbo is 58×; capping
to 53× has been reported as stable:

> "I just wanted to provide an update that I was able to fix the
> crashing issue by going into the Intel(R) extreme tuning utility
> and setting the Performance Active-Core Tuning Ratio of all of
> the cores to 53x."
> — colbyrand, 2024-04-02, Metashape 2.1
> ([permalink](https://www.agisoft.com/forum/index.php?topic=15903.msg70291#msg70291))

This caps each core's turbo to 5.3 GHz (53 × 100 MHz BCLK)
instead of the stock 5.8 GHz. The 8.6% clock reduction
substantially improves stability under sustained load.

### Workaround 3 — Disable Thermal Velocity Boost

If both workarounds above don't suffice, disable *Thermal
Velocity Boost* (TVB) entirely in BIOS. TVB is the most
aggressive opportunistic-clock feature on K-series CPUs and is
the first to trigger the instability under thermal/power stress.

### Workaround 4 — Replace the motherboard

In one user's case, replacing the Gigabyte Z790 motherboard with
an ASUS Prime Z790-P fully resolved crashes that no BIOS
adjustment fixed:

> "I tried to replace every part of the system, frames, graphics
> card, disk, but with no results. Only replacing the motherboard
> with an ASUS Prime Z790-P allowed it to work without errors."
> — geodamkru, 2023-11-23, Metashape 2.1
> ([permalink](https://www.agisoft.com/forum/index.php?topic=15903.msg69015#msg69015))

This points to motherboard-level VRM (voltage regulator module)
quality / firmware as a contributing factor on certain Gigabyte
Z790 boards. Before attempting motherboard replacement, ensure
the board's BIOS is up-to-date — Intel released microcode patches
in mid-2024 (Intel Reference Code 0x125+) that address some of
the instability on the BIOS side.

## Verifying the fix

After applying a BIOS workaround:

1. **Reboot.** BIOS power-limit changes don't take effect until
   reboot.
2. **Re-run the failing project.** Use the same dataset that
   reproduced the crash; expected behaviour is a complete
   alignment with no crash.
3. **Monitor with HWInfo64** (Windows) or `s-tui` (Linux)
   during alignment. Watch CPU package power draw — confirm
   it stays below the new PL1 limit. Watch CPU package
   temperature — it should stay below 90°C under sustained
   load.

## Crash-report locations for Agisoft support

If you submit a crash report to Agisoft support, the dump files
are at:

| OS | Path |
|----|------|
| Windows | `C:\Users\<username>\AppData\Roaming\Agisoft\Metashape Pro\Crash Reports\pending\` |
| Linux | `~/.agisoft/metashape pro/Crash Reports/pending/` |
| macOS | `~/Library/Application Support/Agisoft/Metashape Pro/Crash Reports/pending/` |

Attach both the `.dmp` and `.extra` files for each crash —
support uses both to determine the failure mode (CPU exception,
GPU driver crash, RAM corruption, etc.).

## Caveats

- **The workarounds reduce maximum performance ~5-10%** in
  exchange for stability. On batch-processing workstations this
  is usually an acceptable trade. For interactive work with
  smaller projects, the stock clocks may still work fine.
- **Intel microcode updates (mid-2024)** addressed some causes
  of the instability at the firmware level. Users on the latest
  BIOS may not need manual workarounds. Check your motherboard
  vendor's BIOS release notes for "Intel microcode 0x125" or
  newer.
- **The thread is still active.** Behaviour on newer Intel
  generations (Core Ultra Series 1 / Series 2 desktop) is
  uncharacterised in this thread. If you have a Core Ultra
  workstation that exhibits similar symptoms, search the forum
  for "Core Ultra crash" before assuming the same fix applies.
- **DDR5 RAM stability** is a separate concern. Some users in the
  source thread reported that RAM frequency / module count
  affected stability:

  > "The more RAM sticks you use - the bigger chance of RAM
  > instability and the lower maximum frequency at which memory
  > is stable."
  > — PolarNick, 2023-10-16, Metashape 2.1
  > ([permalink](https://www.agisoft.com/forum/index.php?topic=15903.msg68616#msg68616))

  4×32GB DDR5 sticks at the kit's rated XMP speed often run
  unstable; reducing to 2×32GB or dropping the XMP profile to
  default JEDEC speeds can help. This is a general DDR5
  motherboard / CPU memory-controller limitation, not a
  Metashape issue.
- **AMD Ryzen 7000 / 9000 series** does NOT exhibit this
  particular instability. If you are buying a new workstation
  primarily for Metashape stability, the AMD platform may be a
  lower-risk choice in 2024-2025.

## See also

- [Diagnosing CUDA / OpenCL errors during processing](../performance/diagnosing-cuda-opencl-errors.md)
  — companion article on GPU-side crash diagnosis.
- [CPU / RAM / GPU / OS performance tuning](../performance/cpu-ram-gpu-os-tuning.md)
  — broader hardware tuning context.
- [Multi-GPU utilization](../performance/multi-gpu-utilization.md)
  — when multiple GPUs help vs hurt.

## References

- *Metashape Pro User Manual* (2.3) — does not currently document
  hardware crash-diagnosis paths beyond `Help → Save Session
  Logs`.
- Forum thread, [*Metashape Pro Crashing During Image Alignment*, 2023-2024](https://www.agisoft.com/forum/index.php?topic=15903.0)
  — primary source; ~30 substantive replies; multi-vendor
  reproduction; multi-workaround validation.
- *Intel*, [Intel® Core™ Processors Intel® Microcode Patch Update Notes, 2024](https://www.intel.com/content/www/us/en/support/articles/000089190.html)
  — official Intel response (external; verify currency).

