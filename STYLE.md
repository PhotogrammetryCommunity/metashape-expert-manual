<!--
This file is rendered both at the repo root (`STYLE.md`) and as a
published page at `docs/about/style.md` via `pymdownx.snippets`. Do
not use relative Markdown links to other `docs/` files — they resolve
differently in the two contexts and break the strict build. Reference
docs paths as plain `code` text instead.
-->

# Style Guide

The Metashape Expert Manual follows the
[Google Developer Documentation Style Guide](https://developers.google.com/style)
as its primary reference, with the
[Microsoft Writing Style Guide](https://learn.microsoft.com/en-us/style-guide/welcome/)
as a secondary reference for terms Google does not cover.

This document records project-specific overrides. Anything not covered here
defers to Google's guide.

## Voice and audience

- **Audience:** intermediate-to-advanced Metashape users.
- **Voice:** active voice, second person ("you"), present tense.
- **Variety of English:** US English. Spelling, terminology, and dates follow
  US conventions.

## Headings

- Sentence case for all headings (`Optimizing camera parameters`, not
  `Optimizing Camera Parameters`).
- Heading hierarchy must be unbroken — no jumps from `##` to `####`.
- Avoid more than three levels in a single article. If you need four, the
  article is too long.

## Diátaxis: keep how-tos focused

Most articles in this manual are how-tos. For
a how-to article:

- The **Context** section is at most one short paragraph (≤ 5 sentences).
  If you find yourself writing a second paragraph, you have drifted into
  *explanation* mode. Move that material to a separate explanation
  article (or a feature page) and link to it from the how-to.
- The **Solution** section carries the weight of the article. Steps are
  numbered, imperative ("Do X"), and verifiable ("you should now see Y").
- Resist the urge to teach foundations inline. Link to a glossary entry,
  a feature page, or an explanation article.

This rule was added after the alignment-quality pilot, where the first
draft's Context section had drifted into a two-paragraph taxonomy of
alignment failure modes.

## Metashape terminology

Metashape's terminology has shifted across versions; consistent naming
prevents reader confusion.

| Use | Do not use | Why |
|-----|-----------|-----|
| **Point cloud** | Dense cloud | Current 2.x term. Mention "1.x: dense cloud" parenthetically when the article applies to both. |
| **Build Point Cloud** | Build Dense Cloud | Current 2.x menu label. |
| **Tie point cloud** | Sparse cloud | Current 2.x term. |
| **Clean Tie Points** | Gradual Selection (alone) | Current 2.x menu label is *Tools → Tie Points → Clean Tie Points…*. The criteria-and-threshold dialog itself is unchanged. The historical term *Gradual Selection* survives in forum content and is OK to mention parenthetically; do not lead with it. |
| **Depth maps** | (no alternative) | Stable across versions. |
| **Chunk** | Block / project | Metashape's term of art for an internal grouping. |
| **Marker** | GCP / control point (alone) | "Marker" is the Metashape object; *type* (GCP, check point) is a property. |
| **Reference pane** | Ground control window | Current 2.x term. |
| **Optimization** (of cameras) | Bundle adjust | The user-facing term in Metashape; mention "bundle adjustment" parenthetically only when explaining what it does. |

When an article applies to multiple Metashape major versions, use the current
term in prose and note the older term once in the article preamble.

When the forum source post predates the rename (e.g. a 2018 post about
"Gradual Selection"), the article's prose uses the *current* term while
the citation may quote the historical term verbatim — quotations are
preserved as written. Add a parenthetical bridge if it helps clarity:
*"…using Gradual Selection (the 1.x name for what is now Clean Tie
Points)…"*.

### Detecting and recording terminology shifts

Before publishing an article whose source material is older than 12
months, run a terminology-shift sweep against the local manual PDF. If a rename is found:

1. Update the article to use the current term as primary.
2. Add (or update) the corresponding feature page in
   `docs/reference/features/` with a prominent rename note.
3. Add or update a row in this table.

## References to Metashape products

- Metashape **Professional** edition is what we target. Write *Metashape Pro*
  on second mention, never *MetashapePro* or *MS Pro*.
- Metashape **Standard** edition: write *Metashape Standard*.
- *Agisoft* is the company; *Metashape* is the product. Do not write *Agisoft
  Metashape* unless disambiguating from another Agisoft product.

## Citing forum posts

- Format: `[Author, YYYY-MM-DD, Cite-as](permalink)`, where `Cite-as`
  is the value from the corresponding row of
  `docs/reference/version-timeline.md`. Example:
  `[Pasumansky, 2018-05-12, PhotoScan 1.4](https://www.agisoft.com/forum/index.php?topic=...#msg...)`.
- For multi-sentence quotes that don't fit cleanly into the inline
  form above, the **blockquote-with-attribution** form is permitted
  (and used by most articles):

  ```markdown
  > "Multi-sentence quote text. Continued across lines, preserving
  > the source's exact wording, line breaks via `>` continuation
  > prefix on each line." — Author Name, YYYY-MM-DD, Cite-as
  > ([permalink](url))
  ```

  This form is more readable for long technical answers (sample
  scripts, enumerations, embedded manual quotes, etc.) and
  preserves the same attribution + permalink discipline.
- Always link the **exact message** permalink — the `#msgNNNNN` of the
  *specific post* the quotation or claim comes from, taken from that
  post's subject/title link in the topic view. Do **not** link the bare
  thread URL, and do **not** link the thread's first-post `#msg` (a
  common mistake: every citation in a thread ends up pointing at the
  opening post). A citation whose permalink resolves to the top of the
  thread instead of the cited message is a defect to fix before merging.
- Quote **verbatim**. Preserve the source's wording, capitalisation,
  punctuation, and even typos. Mark editorial corrections with
  `[sic]` (preserving the original typo) or `[corrected]` (signalling
  an editorial replacement). Mark elision with `[...]`. **Do not**
  silently rewrite a quote to match the article's prose voice — the
  project's "verbatim quotes" claim is a load-bearing trust signal.
- **Composite quotes are forbidden.** Two posts from the same author
  on different dates must be quoted as **two separate blockquotes**
  with their own attributions and permalinks, even when their
  content is closely related. Do not concatenate into a single
  blockquote with `[...]` between them.
- Never reproduce a forum post in full, even if it is short — link to it.
- **Never publish a citation without the version-at-time.** If you cannot
  determine the version (very old, no clear date in the post), say so
  explicitly: `[Author, YYYY-MM-DD, version unknown](permalink)`.

## Citing the official manual and Python Reference

The Agisoft user manuals are distributed as PDFs only — no live HTML
version exists. Cite by **hierarchical address** so the citation
survives version bumps and re-pagination:

```
*Metashape <Edition> User Manual*, ch. <N> "<Chapter Title>" §
"<Section>" → "<Subsection>" → "<Paragraph>"
```

You may add the page number in the most recent PDF as a bonus, *but
flag it as version-specific* — page numbers shift with every release.

Examples:

- *Metashape Pro User Manual*, ch. 3 "General workflow" §
  "Aligning photos and laser scans" → "Components" (Pro 2.3, p. 40).
- *Metashape Standard User Manual*, ch. 4 "Reference and calibration"
  § "Optimization" (Standard 2.3, p. 110).

If the article cites the same section repeatedly, the first occurrence
gives the full address; subsequent ones may shorten to
`*…Manual*, § "Optimization"`.

The **Python API Reference** has no chapter structure — it is an
alphabetical reference. Cite by fully-qualified symbol name and
mention the version:

```
`Metashape.<Class>.<method>` — *Metashape Python API Reference*,
version <X.Y.Z>.
```

Example: `Metashape.Chunk.matchPhotos` — *Metashape Python API
Reference*, version 2.3.1.

Link to the Python Reference entry only when the method is the central
topic of a paragraph; the qualified name alone is enough in passing
references.

## Code blocks

- Always specify a language: `python`, `bash`, `text`, `xml`, `yaml`, `json`.
- Python snippets must be runnable as shown. No pseudocode interleaved with
  real code; if pseudocode is unavoidable, use a separate block flagged
  `text` and an explicit "this is not runnable" note.
- Imports are required even if the example is short. Readers copy-paste.

## Images

- All images require alt text describing the image content
  (accessibility requirement).
- Every screenshot has a caption naming the source dataset and the Metashape
  version it was produced on.
- File-naming: `<article-slug>-<short-description>.png`, lowercase, hyphens.

## Source datasets — prefer Agisoft's free samples

Whenever an article asserts a procedure that needs a dataset to
illustrate or validate, **prefer one of the ten Agisoft sample
datasets** at <https://www.agisoft.com/downloads/sample-data/>. The
canonical list with naming conventions and "best illustrates" notes is
on the published page at `docs/reference/sample-data.md`.

Why prefer them:

- Reproducibility — any reader can download and follow along.
- Consistency — multiple articles citing the same dataset reinforce
  shared mental models.
- Attribution — the licence is clear; we do not need to host or
  redistribute imagery.

When you choose a dataset for an article:

1. Pick the dataset whose scenario is closest to the article's claim
   (the "best illustrates" notes on
   `docs/reference/sample-data.md` are the index).
2. Link the dataset by its anchor on first mention. Example:
   `…using the [Witcher dataset](../../reference/sample-data.md#witcher),
   a 239-image close-range turntable capture…`.
3. Add a one-line back-pointer under that dataset's *Articles in
   this manual* section on `docs/reference/sample-data.md`.
4. Caption screenshots with `(Witcher dataset, Metashape Pro 2.2)` or
   the equivalent. Per *Images* above.

When **no sample dataset fits**, a contributor-private dataset is
acceptable — but say so explicitly in the article preamble and in the
screenshot captions, and acknowledge the reader will not be able to
reproduce the exact result without their own data.

The pilot article `diagnosing-under-aligned-chunks.md` cites no
specific dataset because its claims (UV-001 … UV-005) are about
behaviour that any aligned project will exhibit — but the *Aerial
images (with GCPs)* and *Witcher* datasets are both reasonable choices
when reproducing the canonical clean-recipe rung on a real install.

### Runnable demonstrations on sample datasets

**Anything that can be demonstrated using a sample dataset should
have a runnable code snippet that does so.** This makes the article
self-verifying: a reader can copy the snippet, point it at their
local copy of the dataset, and observe the expected behaviour
firsthand. It also ties the article's claims back to a public,
reproducible reference.

Standards for the snippet:

- **Use direct method calls, not the Tasks interface.** Write
  `chunk.matchPhotos(...)` or `chunk.point_cloud.classifyGroundPoints(...)`,
  not `Metashape.Tasks.MatchPhotos()`. Readers who need the Tasks
  form (for Agisoft Cloud or network processing) can derive it from
  the direct call; the reverse is harder.
- Mark the dataset path as a clearly-named constant at the top
  (`DATASET_DIR = "/path/to/coded_targets/"`) so the reader knows
  what to change.
- Include the data-loading boilerplate: `chunk.addPhotos(...)`,
  alignment if the demo needs it, marker detection if needed.
- Proceed to the actual demonstration with concise, commented
  steps.
- Print observable output (point counts, status flags, exceptions
  caught) the reader can compare against their own run. The output
  should be sufficient to confirm the article's claim — if the
  expected line is "no exception raised" or "all three forms
  succeed", say so in a comment.
- Keep the snippet ≤ ~30 lines after boilerplate; very long
  snippets belong in `scripts/` with a one-line link from the
  article.
- **Carry an explicit verification status header** immediately
  before the code block. See *Demo verification status* below.

When the article's claim is *runtime behaviour that the local
Metashape Python API can already verify in isolation* (no dataset
needed — typical for kwarg-name and constructor-form questions),
prefer a synthetic-chunk demonstration over loading a sample. UV-008
and UV-009 are a hybrid case: they can be verified with synthetic
cameras, but a snippet that uses real data (the
`docs/reference/sample-data.md#coded-targets` *Coded targets*
dataset for those two specifically) is more illustrative because
it shows the API surface in the context where readers actually
use it.

### Demo verification status

Every runnable demo carries a one-line status header **immediately
before the code block** so a reader (and the project owner during
Tier 3) can see at a glance whether the demo has been executed
end-to-end against the cited sample dataset. The verification
state is independent of the article's overall `status:` field —
an article can be `unverified` overall while a sub-demo is
verified, or vice versa.

Format and the three states:

```
> **Demo verified:** ✓ on Metashape Pro 2.2.2 with the *Coded targets*
> sample dataset, 2026-05-22. Full end-to-end run; output matched the
> expected lines in the *Expected output* paragraph below.
```

```
> **Demo verified:** ✗ — pending Tier 3 reproduction on Metashape
> Pro 2.2 / 2.3 with the *Aerial-with-GCPs* sample dataset. The
> underlying API surfaces are introspection-verified but the demo
> as written has not been run end-to-end.
```

```
> **Demo verified:** partial — the API surfaces used (`X.Y`,
> `Z.W`) were introspection-verified on Metashape 2.2.2; the
> full demo (load + alignment + cleanup) has not been run end-
> to-end. Pending Tier 3 reproduction.
```

The same caveat-phrasing rule applies (above): the verified
state must be reported honestly. A demo whose API surface was
introspected but whose end-to-end run was skipped is *partial*,
not ✓. *Not yet run on the named sample dataset* is ✗, even when
the underlying APIs are verified.

When you verify a previously-✗ demo:

1. Run the demo end-to-end on the named sample dataset.
2. Confirm the printed output matches the article's *Expected
   output* paragraph.
3. Update the verification header to ✓ with the date, the
   Metashape version, and a note that the output matched.
4. If the output *did not* match, do not update the header to ✓;
   instead either correct the article or open a UV-NNN entry for
   the discrepancy.

A repository-wide audit of demo verification state is a release
gate. Before the manual is published or shared widely, every demo
header must read ✓ on the chosen reference version.

When no sample dataset fits, document the gap explicitly: "The
claim below cannot be reproduced from a sample dataset because no
sample contains *X*; a contributor-private dataset is required."
This is rare — most claims that aren't already covered by a sample
should be flagged as UV markers and verified by the project owner.

## Caveat phrasing — observed vs inferred claims

The UV-NNN system records that a claim hasn't been verified yet.
It is **not** a license to state inferences as if they were
observed facts.

When you write a caveat, distinguish what you have *seen* from
what you have *inferred*. Specifically: "the canonical forum
snippet uses pattern X" is an observation; "the alternatives fail"
is an inference until verified.

Bad (overclaiming):

> Iterating `marker.projections.keys()` directly raises a
> collection-mutated-during-iteration exception. Always wrap in
> `list(...)`.

Good (honest hedge):

> The canonical forum snippet wraps `marker.projections.keys()`
> in `list(...)`. Whether the bare form is also safe is unverified
> (UV-NNN); the wrap is preserved here for compatibility.

The bad form's problem is not the UV marker — both forms can
carry one — but that the *prose itself* over-claims. A reader who
sees only the prose, with no UV awareness, walks away believing
the bare form fails. When the claim is later falsified, the
correction is more disruptive than it would have been if the
caveat had been honestly hedged.

This was the failure mode that produced UV-008 ("`list(...)` is
required") and UV-009 ("`Vector` is required"). Both were inferred
from "the canonical pattern is X" and stated as observed facts. Tier 1
verification falsified both. Going forward:

- If you observe pattern X in a forum snippet, write "the
  canonical pattern is X." Do not extrapolate to "alternatives
  fail" without verification.
- If your draft contains a strong negative claim ("X raises", "X
  silently fails"), pause and ask whether you have actually
  reproduced the failure. If not, soften the prose and add an
  UV-NNN marker — the marker is supplementary, not a substitute
  for honest phrasing.

## Article preamble fields

Every article begins with a fixed front-matter block in **YAML
form** (the canonical format; older bold-list-blockquote forms
have been migrated). The block
goes between `---` delimiters at the very top of the file:

```yaml
---
title: Article title (sentence case)
status: unverified           # verified | unverified | deprecated
applies_to: Metashape Pro 2.x — and unchanged from PhotoScan 1.x
edition: Pro                 # Pro | Standard | "Pro / Standard"
last_reviewed: 2026-05-23    # ISO date
diataxis: how-to             # how-to | explanation | reference | tutorial
confidence: medium           # high | medium | low
---

# Article title
```

Field semantics:

- **`title`** — the same string as the H1 below the
  frontmatter; used for nav and search.
- **`status`** — `unverified` until the project owner
  reproduces the procedure on a real Metashape install (Tier 3);
  promoted to `verified` only after that.
- **`applies_to`** — precise version range. Prefer the prose
  form `Metashape Pro 2.x — and unchanged from PhotoScan 1.x`
  for clarity over the compact `Metashape Pro 2.0+` form.
- **`edition`** — which Metashape edition this article applies
  to. Use `Pro` for Python-only articles, `Standard` for
  GUI-only, or `"Pro / Standard"` for articles whose procedure
  works in both.
- **`last_reviewed`** — ISO date of the last review pass.
- **`diataxis`** — the Diátaxis category. See the *Diátaxis* section
  above for guidance. Hybrid articles (mostly explanation with a
  recipe section, or vice versa) declare their dominant mode.
- **`confidence`** — epistemic flag for the article's claims:
  `high` when every claim is forum-attested or
  introspection-confirmed; `medium` when the article synthesises
  multiple sources or contains inferred claims; `low` when
  significant claims await Tier 3 verification. Justify in the
  body's first paragraph or in a confidence callout below the
  H1.

The frontmatter block is **rendered as a visible "Article info"
admonition** at the top of the published page via the
`hooks/render_metadata.py` MkDocs hook — readers see a
two-column table summarising the metadata. The hook reads only
the fields above; project-specific extensions in frontmatter are
ignored by the hook (but available to `scripts/verify_article.py`
and `scripts/review_articles.py`).

The older bold-list-blockquote form:

```markdown
# Title

> - **edition:** `Standard`
> - **applies_to:** Metashape ...
> - ...
```

was migrated to YAML on 2026-05-23 (commit `396b57a`). All
articles now use the YAML form.

## Section index pages

Every Workflow and Topics section has an `index.md` landing page,
surfaced as the clickable section title in the nav (via the
`navigation.indexes` theme feature). Each such page carries an
`## Articles` list that links **every** article in the section, in
the same order as the section's `nav:` entry in `mkdocs.yml`.

- When you add, remove, or rename an article, update the section's
  `index.md` `## Articles` list in the **same** change. A list that
  shows only some of the section's articles (a stale list) — or is
  missing entirely — is a review-blocking defect.
- Keep the order identical to `nav:` so the landing page and the
  sidebar agree.
- The list is link-only (`- [Article title](article-slug.md)`); the
  descriptive prose lives in the articles themselves, not the index.
- The lists are mechanically regenerable from the nav, so the fastest
  way to fix drift across many sections at once is to re-derive them
  from `mkdocs.yml` rather than hand-editing each page.

## Inclusive language

Follow Google's
[inclusive documentation guidance](https://developers.google.com/style/inclusive-documentation).
- Prefer "allowlist / blocklist" over the older paired terms.
- Avoid gendered placeholders.
- Avoid ableist metaphors.

## Things not to do

- **Do not use personal names in body text.** Personal references
  (Agisoft staff, named forum contributors) appear *only* in
  citations: blockquote attribution lines, References sections, and
  URL link labels. Body prose, headings, captions, decision trees,
  and tables describe Metashape behaviour without naming the people
  who use or develop it.

  Forbidden patterns and rewrites (this is not exhaustive — apply
  the spirit, not just the letter):

  | Forbidden | Rewrite |
  |-----------|---------|
  | "Pasumansky's diagnostic" | "the documented diagnostic" |
  | "Pasumansky-attested facts" | "forum-attested facts" |
  | "Pasumansky's 2014 sample script" | "the 2014 forum sample script" |
  | "James's enumeration of when X" | "the canonical enumeration of when X" |
  | "Heinrich's caveat" | "the repetitive-features caveat" |
  | "As Pasumansky observed" / "Per Pasumansky" | "Per the canonical thread" / "As documented" |
  | "Cockey 2014; not contradicted by later Pasumansky" | "2014 forum statement; not contradicted by later forum activity" |
  | "BobvdMeij's user-manual quote" | "the user-manual quote (cited in the source thread)" |

  Permitted: the citation itself.

  ```
  > "Quote text." — Alexey Pasumansky, YYYY-MM-DD, Cite-as
  > ([permalink](url))
  ```

  Permitted: References / See also entries at the bottom of an
  article (a forum thread link's label may include the original
  poster's name, e.g.,
  `[Forum thread, *Mesh editing*, 2019](url)`).

  Rationale: the manual's value is *what Metashape does and how to
  use it*, not *who said so on the forum*. Naming a single forum
  contributor a hundred times in body text creates a misleading
  impression that the book "summarises one person's transcript"
  when it actually documents Metashape behaviour using forum and
  manual sources for attestation. A reader does not need to know
  names to apply the guidance; they need to know the claims are
  sourced (which the citation in the References section provides).

  This rule was added 2026-05-23 after a sweep that removed ~120
  personal-name occurrences from body text across 29 articles. The
  audit script is `scripts/audit_personal_references.py`; the
  bulk-rewriter is `scripts/rewrite_personal_references.py`.

- Do not editorialise about Agisoft, the forum community, or
  individual contributors. State facts, link sources.
- Do not paraphrase a forum post and present it as your own analysis.
- Do not include unverified claims without the `unverified` status badge.
- Do not write tutorials. This manual is a how-to / reference / explanation
  resource (per Diátaxis).
- **Do not document license-circumventing tricks**, custom export
  workarounds, or anything that depends on bypassing Metashape's
  licensing model. The expert manual is a complement to the official
  product, not a workshop for unsupported tooling. (Project decision,
  2026-05-22.)

## Marking unverified claims inline

The article-level `status:` field is coarse — `verified` /
`unverified` / `deprecated`. For specific claims that the author could
not personally validate (typically GUI behaviour or runtime
characteristics), use the inline **UV marker** convention. This lets
an article be *partly* verified while flagging the still-pending bits
to readers.

**Inline marker syntax** (immediately after the affected sentence or
list item):

```
*([Unverified — UV-NNN](../../about/unverified.md#uv-nnn))*
```

The relative path is from the article location to
`docs/about/unverified.md`. The anchor `uv-nnn` is the entry's stable
ID on the tracker page.

**For each marker**, add a corresponding entry in
`docs/about/unverified.md` with:

- Article and section the claim appears in
- The exact claim
- What the source material attests (insight cards, forum quotes, PDF)
- The concrete verification step a maintainer would take
- Status: `pending` initially

When a maintainer verifies a claim:

1. Update the tracker entry's status, dataset, version, date.
2. Remove the inline marker from the article.
3. Move the entry from *Pending* to *Recently verified* on the
   tracker.

When verification falsifies a claim, correct the article first, then
move the entry to *Falsified* with an explanation.

The tracker page is published; readers see it in the site nav under
*About → Unverified claims*.

## Edition badges (Standard vs Pro)

Every article carries an `edition:` field in its front matter. The values
are:

- **`Standard`** — the GUI procedure works in Metashape Standard Edition.
  The article may *also* show a Python equivalent (Python is Pro-only),
  but is still tagged Standard if the GUI path needs no Pro features.
- **`Pro`** — either:
    - the only path described is Python (which is Pro-only), or
    - the GUI procedure uses Pro-only features (network processing,
      multi-camera tools, scripting console, certain export formats,
      etc.).

When an article applies to both editions but with different procedures,
prefer splitting it into two articles rather than mixing edition-specific
notes into a single page.

The edition badge is shown prominently in the rendered article so readers
can filter at a glance. It is independent of the `applies_to:` version
field — an article can be `Standard, applies_to: 2.x` if its GUI path
works in Standard 2.x.
