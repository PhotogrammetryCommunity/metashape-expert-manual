# Scripts

Helpers used during article authoring and ingestion. None of these are
run as part of the published site — they are authoring tooling.

## `verify_article.py`

Tier 1 automated verification helper. Runs
three checks on a single article and emits a markdown report ready to
paste into a PR description.

```bash
./.venv/bin/python scripts/verify_article.py \
    docs/workflow/<stage>/<article>.md > /tmp/tier1.md
```

What it checks:

- **Python API references.** Every `Metashape.X.Y` reference in the
  article is introspected against the local Metashape Python API
  (default: `~/.pyenv/versions/Metashape-2.2/bin/python`). Missing
  methods, mismatched kwarg names, and outdated defaults are
  surfaced.
- **Python API change-log cross-check.** Every reference is also
  looked up in the *Python API Change Log* (chapter 3 of
  `corpus/official/metashape-python-api-2_3_1.pdf`). Renames,
  additions, and removals across versions are surfaced even when
  the current name introspects fine — useful for spotting
  introduced-in-version constraints (e.g. `Chunk.cleanTiePoints`
  added in 2.2.1) and for recommending migration notes for 1.x
  readers. *This is the check that would have caught UV-007 in the
  first place.*
- **GUI menu paths.** Every italic `*Foo → Bar*` style menu path is
  searched in the local Pro user-manual PDF (default:
  `corpus/official/metashape-pro-2_3_en.pdf`). Zero-hit paths are
  flagged as likely-wrong labels.
- **GUI change-log cross-check.** The same menu leaves are looked
  up in the GUI changelog (default:
  `corpus/official/metashape-changelog.pdf`). Surfaces historical
  renames such as *Gradual Selection* → *Clean Tie Points* in 2.0.
- **Forum-era terminology.** Sweeps the article for terms that have
  shifted in Metashape 2.x (`dense cloud` → `point cloud`, `Gradual
  Selection` → `Clean Tie Points`, …). Each occurrence is reported so
  the author can confirm it is intentional (a verbatim quote) or
  update to the current term.
- **`applies_to` consistency check.** Parses the article's
  `applies_to:` floor and compares each `Metashape.X.Y` reference's
  *introduction version* against it. Warns when an API was added (or
  renamed to its current name) at a version *later* than the article
  claims to support. Catches a class of bug Tier 1 introspection
  alone misses: the API exists *now* on the validated machine, but
  the article claims to support older versions where the API didn't
  exist yet. Detection is deliberately strict (case-sensitive
  identifier matching, with `Added X to Y.leaf` rejected as a target
  pattern rather than counted as an introduction of `leaf`).
  Sometimes the warning is *informational* rather than a bug — for
  example, when an article's primary claim is about the GUI workflow
  and the Python references are bonus material on a later version.
  In those cases, address the constraint inline (a parenthetical in
  the References section) rather than bumping `applies_to`.

Flags:

- `--metashape-python <path>` — override the Metashape Python venv.
- `--manual <path>` — override the user-manual PDF.
- `--api-changelog <path>` — override the Python API PDF.
- `--gui-changelog <path>` — override the GUI changelog PDF.
- `--no-introspect` — skip the Python step (faster smoke test).
- `--no-pdf` — skip the PDF / terminology checks (when corpus is
  unavailable).
- `--no-changelog` — skip the change-log cross-checks.

Limitations the author should be aware of:

- The PDF check matches only the *leaf* of the menu path
  (the last segment). It cannot confirm the parent menu — for
  example, "*Tools → Camera Calibration*" matches whenever "Camera
  Calibration" appears anywhere in the manual, including dialog
  references. Use the hits as evidence the *label* exists; pair with
  Tier 3 to confirm the *menu placement*.
- Context-menu commands (right-click) are not detected by the menu
  regex (it requires the leading italic-wrapped menu chain).
- The change-log cross-check searches by *leaf identifier* only
  (e.g. it looks up `cleanTiePoints`, not `Metashape.Chunk.cleanTiePoints`).
  Common identifiers like `Filter` will surface unrelated entries;
  treat the output as a pointer rather than as authoritative.
- The script reads but does not modify the article.

## `parse_printpage.py`

Strips HTML and renders SMF `?action=printpage` thread captures
(`corpus/forum/printpage-NNNNN.html`) as readable text with one chunk
per post. Used during insight-card authoring to inspect threads
locally without re-fetching from the forum.

```bash
./.venv/bin/python scripts/parse_printpage.py corpus/forum/printpage-NNNNN.html
```
