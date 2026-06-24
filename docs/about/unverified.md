# Unverified claims

Specific factual claims in this manual that have not yet been confirmed
on a real Metashape install. They are listed here so readers can
calibrate their trust at the claim level — finer than the per-article
`status:` field allows.

## How this works

When an article asserts something a `status: unverified` author could
not personally validate, the article carries an inline marker:

```
*([Unverified — UV-NNN](../../about/unverified.md#uv-nnn))*
```

That marker links to a section on this page. Each entry records:

- **In:** the article and section the claim appears in
- **Claim:** what the article says
- **Source attestation:** what the source material (insight cards,
  forum threads, PDF) actually supports
- **To verify:** the concrete check needed
- **Status:** `pending` | `verified` | `falsified` | `deferred`

When a maintainer verifies a pending claim on a real install, the
entry's status flips to `verified` (or, if the claim turns out to be
wrong, `falsified` — and the article is corrected). The inline
marker on the article is removed once the claim is verified; the
tracker entry stays as audit trail.

This page is part of the manual's Tier 1 / 2 / 3 verification
model: a claim stays listed here until a maintainer reproduces it
on a real Metashape install.

## Maintenance

This page is maintained by hand for now. As the count of UV entries
grows, expect a small `scripts/build_unverified.py` helper that grep's
the manual for `UV-NNN` references and produces a checklist for the
project owner.

To add a new UV entry:

1. Decide the next free `UV-NNN` integer.
2. Add an inline marker at the claim site:
   `*([Unverified — UV-NNN](../../about/unverified.md#uv-nnn))*`.
3. Add a section here under *Pending* using the template at the top.
4. Open a PR; reviewer confirms the marker resolves and the entry is
   complete.

To resolve a pending entry:

1. Walk the verification on a real Metashape install.
2. If confirmed: update the entry's status, dataset, version, date,
   and remove the inline marker from the article. Move the entry to
   *Recently verified*.
3. If contradicted: update the article to match reality, set the
   entry's status to `falsified`, and explain the correction.

---

## Pending

### UV-001 — Components folder in the Workspace pane {#uv-001}

- **In:** [Diagnosing under-aligned chunks](../workflow/alignment/diagnosing-under-aligned-chunks.md)
  — Rung 2 of the diagnostic ladder, and *GUI* step 2.
- **Claim:** Aligned subsets appear under a *Components* folder in the
  *Workspace* pane. Right-clicking a component → *Show Cameras*
  filters the photo pane.
- **Source attestation:** confirmed in the *Metashape Pro 2.3 User
  Manual*, ch. 3 § "Aligning photos and laser scans" → "Components"
  ("the chunk's contents of the Workspace pane inside the Components
  folder"). The right-click *Show Cameras* behaviour is asserted by
  the author and not directly attested in the manual or insight cards.
- **To verify:** open a project on Metashape 2.2; confirm the
  *Components folder* appears under the chunk in the Workspace pane,
  and that right-click → *Show Cameras* filters the photo pane.
- **Status:** pending

### UV-002 — Log file path for PSX projects {#uv-002}

- **In:** [Diagnosing under-aligned chunks](../workflow/alignment/diagnosing-under-aligned-chunks.md)
  — Rung 3, *GUI* step 3.
- **Claim:** The alignment log is captured in
  `<project>.files/0/log.txt` when the project is saved as PSX.
- **Source attestation:** insight-0005 references the log file
  generically; the exact path is the author's recollection.
- **To verify:** save a PSX project that has been aligned and check
  whether `<project>.files/0/log.txt` exists. If the path is
  different (for example for the multi-frame layout), document the
  correct path on this entry.
- **Status:** pending

### UV-003 — Per-block intrinsics in the alignment log {#uv-003}

- **In:** [Diagnosing under-aligned chunks](../workflow/alignment/diagnosing-under-aligned-chunks.md)
  — Rung 3.
- **Claim:** "For each block, the log records the estimated `f`,
  `cx`, `cy`, `k1`, `k2`, `k3`."
- **Source attestation:** insight-0005 (the source thread log analysis from
  forum topic 14222) directly attests only `f` ("estimated f of some
  91 000 pixels compared to average f of around 8 400 pixels"). The
  remaining five intrinsics are an extrapolation by the author.
- **To verify:** open a real alignment log on Metashape 2.2; confirm
  whether all six intrinsics are emitted per block, or only `f`. If
  the actual list differs, correct the article.
- **Status:** pending

### UV-004 — Canonical "clean" alignment recipe reproduces {#uv-004}

- **In:** [Diagnosing under-aligned chunks](../workflow/alignment/diagnosing-under-aligned-chunks.md)
  — Rung 1 (the canonical clean settings).
- **Claim:** Re-running *Align Photos* with the recipe (High accuracy,
  Generic preselection on, Reference preselection off, Reset current
  alignment on, key 40 000 / tie 10 000, Adaptive fitting off, Guided
  matching off, Exclude stationary tie points off) produces a usable
  alignment on a project where defaults had failed.
- **Source attestation:** the recipe is verbatim from the canonical
  thread on Metashape 1.7 (insight-0004). The Python kwargs are
  verified against the local 2.2.2 API. Whether the recipe still
  produces a usable alignment in 2.2 on a typical dataset is
  unconfirmed.
- **To verify:** take a project that ghosted or under-aligned with
  defaults; re-run with the recipe; confirm that the alignment
  improves (more cameras aligned, single component, plausible
  reprojection error). Note any regression cases (datasets where the
  recipe makes things worse) for the article's *Caveats* section.
  Suggested datasets: the [Aerial-with-GCPs](../reference/sample-data.md#aerial-images-with-gcps) set
  (444 images, full UAV pipeline) for an end-to-end test, or the
  [Witcher](../reference/sample-data.md#witcher) set (239 turntable images) if you
  want to exercise the recipe on close-range data.
- **Status:** pending

### UV-005 — Camera-type ghosting reproduces {#uv-005}

- **In:** [Diagnosing under-aligned chunks](../workflow/alignment/diagnosing-under-aligned-chunks.md)
  — Rung 4 (camera-type verification).
- **Claim:** Setting *Frame* in *Tools → Camera Calibration* on a
  fisheye dataset produces visible ghosting (multiple components in
  the Workspace pane); switching to *Fisheye* and re-aligning
  resolves to a single component.
- **Source attestation:** insight-0004 reports the canonical thread diagnosing this
  exact case on a real customer project (forum topic 13079, Metashape
  1.7). Reproducibility on Metashape 2.2 is unconfirmed.
- **To verify:** take a fisheye dataset, set the camera type to
  *Frame* in *Tools → Camera Calibration*, run *Align Photos* with
  defaults, observe the result. If multiple components appear, switch
  to *Fisheye*, *Reset Camera Alignment*, and re-align. Confirm the
  single-component result.
  *Note:* none of the Agisoft sample datasets is fisheye, so this UV
  needs a contributor-private fisheye dataset (or you can simulate a
  near-equivalent failure by deliberately mis-setting *Frame* on a
  rectilinear dataset and observing whether the bundle still
  recovers).
- **Status:** pending

### UV-008 — Iterating `marker.projections.keys()` requires `list(...)` {#uv-008}

- **Status:** **falsified, 2026-05-22.** Tier 1 reproduction in
  Metashape 2.2.2 with a synthetic 2-camera chunk: a bare
  `for camera in marker.projections.keys():` loop that assigns
  `marker.projections[camera] = None` inside the loop **runs to
  completion without raising**. The `list(...)` wrap is defensive
  practice (and is what the canonical thread uses in every snippet) but
  is not strictly required in 2.x. The article's caveat was
  rewritten to reflect this; the canonical pattern still uses
  `list(...)` for exact compatibility with the cited 2017 snippet.
- **Reproduction:** Python session against the local 2.2.2 venv:
  create a `Document`, add a chunk, attach two synthetic cameras
  via `chunk.addCamera()`, place two `Marker.Projection` instances
  on a marker, run the bare iteration, observe no exception.

### UV-009 — `Metashape.Vector([X, Y])` is required vs `[X, Y]` works {#uv-009}

- **Status:** **falsified, 2026-05-22.** Tier 1 reproduction in
  Metashape 2.2.2: `Marker.Projection` accepts **all three** forms
  for the coordinate argument:
    - `Marker.Projection(Metashape.Vector([1.5, 2.5]), True)` ✓
    - `Marker.Projection([1.5, 2.5], True)` ✓ (bare list)
    - `Marker.Projection((1.5, 2.5), True)` ✓ (tuple)
  All produce a projection with the expected `coord`, `pinned`,
  `valid` attributes when `pinned` is passed **positionally**.
  Correction (end-to-end run on the *Coded targets* sample,
  Metashape 2.2.3, 2026-06-04): the `pinned=` **keyword** form
  does **not** work — it silently returns `pinned=False`, so
  `pinned` must be passed positionally.
  The article's caveat was rewritten: the `Vector` recommendation
  is preserved as a style preference (matches the rest of the
  Metashape API), not as a correctness requirement.

### UV-006 — Reconstruction Uncertainty cutoff range {#uv-006}

- **In:** [The Clean Tie Points → Optimize Cameras loop](../workflow/optimization/clean-tie-points-optimize-cameras-loop.md)
  — step 2 of the loop.
- **Claim:** A typical Reconstruction Uncertainty cutoff is "between
  10 and 50".
- **Source attestation:** insight-0001 (the canonical thread, 2012, PhotoScan 0.9)
  defines the metric (max/min variance ratio in two-camera
  triangulation) but **does not** recommend a threshold value. The
  10–50 range is consensus-style heuristic from community workflow
  scripts; no Agisoft-staff post in the local corpus pins down a
  recommended range.
- **To verify:** run *Clean Tie Points* with criterion
  *Reconstruction Uncertainty* on the
  [Aerial-with-GCPs](../reference/sample-data.md#aerial-images-with-gcps)
  dataset post-alignment and observe what slider values select
  10 %, 25 %, and 50 % of the cloud. Pin the recommended cutoff to
  whatever range visibly captures *outliers without core points*.
  Note any dataset-specific caveats.
- **Status:** pending

### UV-007 — `chunk.buildPoints` removal in 2.x {#uv-007}

- **Status:** **falsified, 2026-05-22.** Method was *renamed*, not
  removed. The 1.6 release renamed `Chunk.buildPoints()` to
  `Chunk.triangulatePoints()` (with the `error` kwarg becoming
  `max_error`). The 2.0 release renamed it again to
  `Chunk.triangulateTiePoints()`. Confirmed by:
  - introspection: `Metashape.Chunk.triangulateTiePoints(max_error=10, min_image=2, [progress])`
    is present in 2.2.2; `triangulatePoints` and `buildPoints` both
    return False for `hasattr`,
  - the *Python API Change Log* in
    `corpus/official/metashape-python-api-2_3_1.pdf` chapter 3
    (1.6.0 section: *"Renamed Chunk.buildPoints() method to
    Chunk.triangulatePoints()"*; 2.0.0 section: *"Renamed
    Chunk.triangulatePoints() method to triangulateTiePoints()"*).
- **Article correction:** `automating-gradual-selection-python.md`
  *Context* and *Caveats and gotchas* sections rewritten to
  describe the rename rather than a removal, and a Pattern 4 added
  showing the non-destructive-rebuild loop with the correct 2.x
  method name.
- **Lesson learned:** the *Python API Change Log* (chapter 3 of the
  Python API PDF) and the GUI changelog
  (`corpus/official/metashape-changelog.pdf`) are now first-class
  Tier 1 sources. Either would have caught this.

---

## Recently verified

*(empty)* — entries move here when a maintainer confirms the claim
on a real install. Each carries the date, Metashape version, and
sample dataset used.

---

## Falsified

- **UV-007** — `chunk.buildPoints` removal in 2.x. *Falsified
  2026-05-22.* The method was renamed twice
  (`buildPoints` → `triangulatePoints` in 1.6 → `triangulateTiePoints`
  in 2.0), not removed. Article corrected. Full audit trail kept
  in the *Pending* section above.
- **UV-008** — Iterating `marker.projections.keys()` requires
  `list(...)`. *Falsified 2026-05-22.* Bare iteration with
  simultaneous mutation runs to completion in Metashape 2.2.2
  without raising. The `list(...)` wrap is defensive practice but
  not a correctness requirement. Article corrected.
- **UV-009** — `Metashape.Vector` is required vs bare list works.
  *Falsified 2026-05-22.* `Marker.Projection` accepts bare list,
  tuple, and `Vector` interchangeably for the coordinate argument.
  The `pinned=` keyword form does **not** work (silently returns
  `pinned=False`; found on the *Coded targets* run 2026-06-04) —
  pass `pinned` positionally. Article corrected.
- **UV-010** — Python `addPhotos(filenames=…)` list order
  controls master-sensor assignment. *Falsified 2026-05-25.*
  Tier 3 testing on a real multi-camera dataset (Metashape 2.2.3)
  showed master assignment follows alphabetical sort of full
  image paths within each filegroup; Python list order is
  irrelevant. Article
  (`docs/workflow/camera-calibration/choosing-master-sensor-multi-camera-layout.md`)
  rewritten on 2026-05-25 with corrected Python recipe (symlink
  prefix technique) and a *History* note explaining the change.
  Insight-0024 also corrected.
