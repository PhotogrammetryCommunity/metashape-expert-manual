---
title: "Troubleshooting Metashape: diagnostic ladder and where the logs live"
status: unverified
applies_to: Metashape Pro 2.x and Metashape Standard 2.x — applies to all versions
edition: "Pro / Standard"
last_reviewed: 2026-06-05
diataxis: how-to
confidence: high
---

# Troubleshooting Metashape: diagnostic ladder and where the logs live

> **Confidence:** *high.* The crash-report locations are
> attested in the official user manual; the diagnostic ladder
> consolidates patterns from across the Metashape forum,
> with the recommendation to check stable-issue articles
> (e.g., the Intel-13/14900K instability article) for
> known-platform-specific causes.

## Problem

Metashape crashed, hung, or produced unexpectedly bad output.
Before opening a forum thread or contacting support, you can
narrow the diagnosis with a structured first-pass.

This article covers:

- The diagnostic ladder (what to check, in order).
- Where logs and crash reports live per OS.
- How to gather useful information for a forum/support post.
- When the problem isn't Metashape.

## The diagnostic ladder

Work through these in order. Most issues are resolved within
the first three steps.

### 1. Is this a known issue?

Before deep diagnosis, check the most common categories of
"not actually a Metashape bug":

- **Intel i9-13900K / 14900K instability** — random crashes
  during alignment / optimization on these CPUs are usually
  hardware/BIOS, not Metashape. See
  [the Intel-instability article](../hardware-io/intel-13900k-14900k-instability.md).
- **CUDA / OpenCL driver issues** — see
  [Diagnosing CUDA / OpenCL errors](../performance/diagnosing-cuda-opencl-errors.md).
- **DDR5 instability** at XMP profiles — common with 4×32GB
  modules. Drop to JEDEC speeds and re-test.
- **Disk full** during depth-maps generation — depth maps
  can require 10× the photo set's size in temp storage.
- **Mixed Metashape versions** (network processing) — all
  workers must run the same version as the server.

If your symptom matches a known issue, follow that article's
remediation rather than the generic ladder below.

### 2. Reproduce in isolation

The reliability of a bug report scales with reproducibility:

| Reproducibility | Useful for support? |
|-----------------|:-------------------:|
| "Happens every time on the same project" | Excellent |
| "Happens 1 in 10 runs on the same project" | Useful (probably hardware) |
| "Happened once, can't reproduce" | Limited |

To probe reproducibility:

1. Re-run the failing operation immediately. Same crash?
2. Restart Metashape, re-open the project, retry. Same crash?
3. Reboot, retry. Same crash?
4. Try on the smallest subset of cameras that reproduces. Does
   it survive the cull?

A repeatable crash on a minimal subset is a high-quality bug
report. A flaky crash on the full project usually indicates
hardware (RAM, CPU, GPU instability) rather than Metashape.

### 3. Check the log file

Metashape writes a session log every run. *Tools →
Preferences → General → Write log to file* enables capture
to a known path. The log captures:

- Each operation's start / end / duration.
- Per-stage progress messages.
- Error messages that appear in the GUI's *Console* pane.
- Stack traces for fatal exceptions (at moderate-or-greater
  log level).

If *Write log to file* was off when the crash occurred,
enable it and reproduce. The log + the crash dump together
are what Agisoft support needs.

### 4. Check resource utilization at the crash time

Open *Task Manager* (Windows), `htop` (Linux), or *Activity
Monitor* (macOS) while reproducing the crash. Watch for:

- **RAM exhaustion** — physical RAM hits 100%, swap spikes,
  Metashape disappears from the process list.
- **GPU OOM** — VRAM at 100%, possibly followed by a
  driver-level reset (Windows shows a "display driver
  recovered" balloon).
- **CPU thermal throttling** — sustained 100% CPU, then
  rapid CPU-frequency drop, then crash. Common on laptops or
  poorly-cooled workstations.
- **Disk full** — temp partition at 100% during depth-maps
  generation.

These manifest as different Metashape symptoms (silent exit
vs explicit "out of memory" error) but the root cause is the
same: insufficient resources for the chosen settings.

### 5. Reduce per-operation resource demand

If the failing operation is RAM-bound:

- Lower the *Quality* setting on depth-maps from Ultra-High
  → High → Medium.
- Switch *Surface type* from Arbitrary to Height field (10×
  RAM saving).
- Split the chunk via [split_in_chunks](../../topics/multi-chunk/when-to-use-chunks.md).

If GPU-bound:

- Disable GPU and run on CPU only (slower but uses system
  RAM, not VRAM).
- Update GPU driver.
- Check VRAM usage and consider a higher-VRAM card.

### 6. File a bug report or forum thread

If steps 1-5 haven't resolved it, the problem may be a real
bug. Useful information for the report:

- **Metashape version + build number**
  (*Help → About* — note the parenthesised number after
  "Build", e.g., "Metashape Pro 2.2.2 (build 18654)").
- **Operating system + version** (Windows 11 24H2; Ubuntu
  22.04 LTS; macOS 14.6.1).
- **Hardware**: CPU model, RAM amount + type, GPU model + VRAM,
  storage type.
- **Project size**: number of cameras, image dimensions, total
  source-data size.
- **Reproduction steps**: minimum sequence of operations that
  triggers the issue.
- **The log file** (with *Write log to file* enabled before
  reproduction).
- **The crash dump** (location below).

Forum thread submission goes via the *General* board. Support
ticket submission via *Help → Submit Crash Report* (which
collects all of the above automatically) or *Help → Email
Agisoft Support* for non-crash issues.

## Where logs and crash reports live

| OS | Crash reports | Session logs |
|----|--------------|--------------|
| Windows | `%APPDATA%\Agisoft\Metashape Pro\Crash Reports\pending\` | `%APPDATA%\Agisoft\Metashape Pro\Logs\` (when enabled) |
| Linux | `~/.agisoft/metashape pro/Crash Reports/pending/` | `~/.agisoft/metashape pro/Logs/` |
| macOS | `~/Library/Application Support/Agisoft/Metashape Pro/Crash Reports/pending/` | `~/Library/Application Support/Agisoft/Metashape Pro/Logs/` |

Each crash produces two files:

- **`*.dmp`** — the binary crash dump (debugger-ingestible).
- **`*.extra`** — text file with version / OS / GPU / project
  details at the crash moment.

When submitting to Agisoft support, attach both. The .dmp
alone is rarely enough; the .extra contextualizes which build,
OS, and GPU are involved.

## Diagnostic Python recipe

For collecting environment info programmatically (useful in
multi-machine bug reports):

> **Demo verified:** ✗ — pending Tier 3 reproduction on a real Metashape install.

```python
import platform
import Metashape

print(f"Metashape version: {Metashape.app.version}")
print(f"OS: {platform.system()} {platform.release()}")
print(f"CPU: {platform.processor()}")

settings = Metashape.app.settings
gpu_devices = []
for i in range(10):
    name = settings.value(f"main/gpu_name/{i}")
    if name:
        gpu_devices.append(name)
print(f"GPUs known to Metashape: {gpu_devices}")

doc = Metashape.app.document
if doc:
    chunk = doc.chunk
    if chunk:
        print(f"Project: {len(chunk.cameras)} cameras, "
              f"{len(chunk.markers)} markers")
        print(f"Aligned: {sum(1 for c in chunk.cameras if c.transform)}")
```

## When the problem isn't Metashape

Common cases where the user blames Metashape but the cause is
elsewhere:

- **Hardware instability** (RAM, CPU, GPU). Run Memtest86 + Prime95
  before assuming a software bug.
- **Driver issues**. Roll back / update GPU driver and re-test.
- **OS bugs**. Sometimes an OS-level patch fixes
  Metashape-stability symptoms (the Windows scheduler updates
  for hybrid CPUs, the macOS Sonoma graphics regression of
  early 2024).
- **Antivirus or backup software** locking the project's
  temp files. Exclude Metashape's temp directory.
- **Filesystem issues** (corrupt project file). Reproduce on
  a freshly-saved copy of the project.
- **License-server connectivity** (network license editions).
  License-checks can hang Metashape on startup if the server
  is unreachable. Firewalls blocking Metashape's optional online
  services (Agisoft Cloud, base maps, online publishing) cause
  similar hangs — see [*Firewall configuration* (Agisoft KB)](https://agisoft.freshdesk.com/support/solutions/articles/31000163280)
  for the endpoints to allow.

If you've worked through the ladder and the problem is on the
"isn't Metashape" list, address that root cause first. Otherwise
file the report from step 6.

## Caveats

- **The "default" Metashape log level is moderate.** For
  particularly elusive bugs, increase the verbosity via
  *Tools → Preferences → General → Log level*. The next-higher
  level can balloon the log file size by 10×; budget disk
  accordingly.
- **Crash dumps may contain project data** (camera positions,
  paths, project structure). For projects with confidential
  imagery, review the .extra file content before sharing
  publicly.
- **The `pending/` folder accumulates indefinitely.** After
  resolving an issue, periodically clear old crashes (move
  the .dmp/.extra files to an archive or delete) to keep the
  folder manageable.
- **Reproduce-on-fresh-project tests narrow the cause.** A
  bug that disappears on a fresh project but reproduces on
  the original suggests project-file corruption — open the
  original via *File → Open* (not double-click) and check
  the *Console* pane for warnings during load.

## See also

- [Intel i9-13900K / 14900K instability: BIOS workarounds](../hardware-io/intel-13900k-14900k-instability.md)
  — the most-common known platform-level issue.
- [Diagnosing CUDA / OpenCL errors during processing](../performance/diagnosing-cuda-opencl-errors.md)
  — GPU-specific diagnostic ladder.
- [Performance tuning: CPU, RAM, GPU, and OS](../performance/cpu-ram-gpu-os-tuning.md)
  — broader hardware tuning context.
- [Scripting context pitfalls: GUI vs command-line](../scripting/scripting-context-pitfalls.md)
  — for headless / batch-script issues that are scripting-
  context bugs, not Metashape bugs.

## References

- *Metashape Pro User Manual* (2.3), ch. *Help → Submit Crash
  Report* — describes the in-app submission flow.
- [*What to do, if Metashape crashes?* (Agisoft KB)](https://agisoft.freshdesk.com/support/solutions/articles/31000159037)
  (crash-report submission, Memtest86, GPU drivers, Windows Event
  Viewer), [*What do some error messages in Metashape interface mean?* (Agisoft KB)](https://agisoft.freshdesk.com/support/solutions/articles/31000148432)
  (the cryptic-message glossary: Empty extent, Null model, Zero
  resolution, etc.), and [*Troubleshooting about usage on Linux* (Agisoft KB)](https://agisoft.freshdesk.com/support/solutions/articles/31000163267)
  (glibc / OpenGL / codec / missing-library fixes).

