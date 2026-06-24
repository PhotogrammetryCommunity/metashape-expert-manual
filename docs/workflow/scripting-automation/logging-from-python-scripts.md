---
title: Logging from Metashape Python scripts (and why `app.settings.log_*` does not work for headless scripts)
status: unverified
applies_to: Metashape Pro 2.0+. The behaviour described here was reported on PhotoScan 1.5 (insight-0014) and is unchanged on the local Metashape 2.2.2.
edition: Pro
last_reviewed: 2026-05-22
diataxis: how-to
confidence: medium
---

# Logging from Metashape Python scripts (and why `app.settings.log_*` does not work for headless scripts)
> **Confidence:** *medium.* The headless-script logging gotcha (`app.settings.log_*` not honoured outside the GUI) is forum-attested. The `logging`-module workaround is a synthesis from multiple Python-API forum threads.
## Problem

You have a Python script that drives Metashape headless (run as
`metashape -r script.py`) and want a log file capturing both your
own `print()` output and Metashape's per-operation messages
(timing, alignment results, depth-map generation status, error
traces). Setting `Metashape.app.settings.log_enable = True` and
`Metashape.app.settings.log_path = "..."` in the script appears to
work — the *Preferences → Write to log* checkbox is set, the path
field shows the right value — but no file is written.

## Context

The forum reports two distinct usage patterns for
`Metashape.app.settings.log_enable` / `.log_path`:

- **Interactive Metashape, with a GUI session running** — the
  attributes write to the path you specify. They behave as
  documented.
- **Headless Python, started via `metashape -r script.py`** — the
  attributes appear to take effect (the Preferences pane shows the
  checkbox set and the path correct) but no file is written.

The headless-Python case is the one most batch-pipeline scripts
need. The canonical thread's response to this distinction is to use
**OS-level output redirection** instead.

## Solution

### The OS-redirect approach

Run the script with shell redirection so the log captures both
stdout and stderr:

```bash
# macOS (Pro install at the default path)
/Applications/MetashapePro.app/Contents/MacOS/MetashapePro \
    -r /path/to/script.py \
    > /path/to/log.txt 2>&1

# Linux
metashape.sh -r /path/to/script.py > /path/to/log.txt 2>&1

# Windows
"C:\Program Files\Agisoft\Metashape Pro\metashape.exe" ^
    -r "D:\script.py" ^
    > "D:\log.txt" 2>&1
```

The `2>&1` is essential: it merges stderr into the same file, so
Python tracebacks and Metashape's own error-stream messages land
alongside the operator's `print()` output. Without it, errors
disappear into the void.

### Splitting the log inside the script

If you want both *Metashape's own messages* and *your own logger
output* in the same file, point Python's `logging` module at
stdout and rely on the OS redirect to capture the merged stream:

```python
import logging
import sys

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(
    logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
)
logger.addHandler(handler)

logger.info("Starting alignment …")
# … your Metashape calls …
logger.info("Finished.")
```

When the script is run via `metashape -r script.py > log.txt 2>&1`,
the file `log.txt` contains:

- Metashape's own per-operation lines (alignment progress, depth
  map generation, timing).
- Every `print()` call in the script.
- Every `logger.info(...)` (or other level) call.
- Any unhandled exception traceback.

This is the most useful single file for triaging a failed batch.

### A `tee` variant for live progress + log

If you want to *also* see progress on the terminal (e.g. for
interactive batch monitoring) while still capturing to a log file,
use `tee` from the shell:

```bash
metashape -r script.py 2>&1 | tee /path/to/log.txt
```

The same redirection caveats apply.

## Caveats and gotchas

- **Don't bother setting `Metashape.app.settings.log_enable` /
  `log_path` in headless scripts.** Neither does what you want.
  The `Preferences` pane reflects them, but no file appears.
- **GUI-mode logging works**, so if you ever switch a script
  between interactive and headless use, the headless mode will
  silently lose its log unless you've set up the redirect.
- **Without `2>&1`** the error stream is not captured. A script
  that fails an assertion will write the traceback to stderr and
  leave the log file ending mid-sentence on its last successful
  message. Always include `2>&1`.
- **The script's own `logging` module configuration is independent
  of Metashape's internal logging.** Each can be configured
  separately; both end up in the redirected file regardless.

## References

- **Official manual:** *Metashape Pro User Manual*, no dedicated
  section — the *Preferences* pane is documented but the
  headless-script behaviour is not.
- **Python Reference:** `Metashape.Application.Settings.log_enable`,
  `Metashape.Application.Settings.log_path` — *Metashape Python API
  Reference*, version 2.3.1. Documented, not deprecated; just do
  not behave as expected in headless mode.
- **Forum:** [Pasumansky, 2019-07-23, PhotoScan 1.5](https://www.agisoft.com/forum/index.php?topic=11129.msg50273#msg50273)
  — "For headless scripts I suggest to use the OS re-directing
  feature."
- **Forum:** [Pasumansky, 2019-07-25, PhotoScan 1.5](https://www.agisoft.com/forum/index.php?topic=11129.msg50316#msg50316)
  — the Windows redirection example with `2>&1`.
- **Related articles:** [Automating gradual selection in Python](automating-gradual-selection-python.md)
  is one example of a headless-friendly script; the redirect
  pattern here applies directly to it.
