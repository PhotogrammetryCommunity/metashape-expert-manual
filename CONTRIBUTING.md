<!--
This file is rendered both at the repo root (`CONTRIBUTING.md`) and as
a published page at `docs/about/contributing.md` via
`pymdownx.snippets`. Do not use relative Markdown links to other
`docs/` files — they resolve differently in the two contexts and break
the strict build. Reference docs paths as plain `code` text instead.
-->

# Contributing to the Metashape Expert Manual

This manual is built incrementally under human review. Automated
tooling may draft, lint, and check, but a human maintainer who has
reproduced the procedure on a real Metashape install is always the one
who approves and publishes.

## Ground rules

1. **Human signoff required.** Automated tooling may draft, critique,
   lint, suggest, or refactor — it may **not** approve a PR or set an
   article's status to `verified`. A human maintainer who has
   reproduced the procedure on a real Metashape install must do that.
2. **Every published article is either author-validated or carries an
   `unverified` badge.** No exceptions.
3. **Every article cites at least one official-manual reference and at
   least one forum reference**, or carries an explicit "original
   synthesis" flag.
4. **Every article pins a Metashape version**, declares a confidence
   level, and lives in exactly one Diátaxis mode (how-to, explanation,
   or reference).

## Workflow

The canonical authoring order:

1. Pick (or be assigned) an article from the backlog.
2. **Insight cards first.** Curate the 3–7 forum threads that will
   ground the article. For each, write an insight card in `insights/`
   *before* drafting prose. The cards are the article's source-of-truth
   citations and prevent the drafting step from drifting into
   speculation.
3. Draft the article using the template in `templates/article.md.tmpl`.
4. **Run Tier 1 automated verification** *before* requesting review.
   Use the helpers:

   ```bash
   # Build first; some checks need the rendered HTML.
   ./.venv/bin/mkdocs build --clean --strict

   # Tier 1 sweep — all five must report 0 issues:
   ./.venv/bin/python scripts/verify_article.py \
       docs/workflow/<stage>/<your-article>.md
   ./.venv/bin/python scripts/verify_demo_code.py \
       docs/workflow/<stage>/<your-article>.md
   ./.venv/bin/python scripts/verify_quotes.py \
       docs/workflow/<stage>/<your-article>.md
   ./.venv/bin/python scripts/audit_personal_references.py \
       docs/workflow/<stage>/<your-article>.md
   node scripts/verify_mermaid_rendered.js site/
   ```

   The five checks cover:

    - `verify_article.py` — Python API introspection + PDF
      menu-label lookup + terminology-shift sweep.
    - `verify_demo_code.py` — every `Metashape.X.Y` reference in
      Python code blocks resolves on the local install.
    - `verify_quotes.py` — every blockquote near a forum
      permalink matches the cached source HTML verbatim.
    - `audit_personal_references.py` — personal names only in
      attribution lines / References / link labels (per the
      personal-name rule in [`STYLE.md`](https://github.com/PhotogrammetryCommunity/metashape-expert-manual/blob/main/STYLE.md)).
    - `verify_mermaid_rendered.js` — Mermaid diagrams parse
      cleanly in the *built* HTML (catches the
      mkdocs-mermaid2 HTML-stripping bug class that the
      markdown-source mermaid-parse cannot detect).

   The output is markdown formatted; paste the relevant findings
   (and any corrections you applied as a result) into the PR
   description's *Automated verification log* section.
5. Run the per-article self-review checklist below.
6. Open a PR. CI runs lint, link check, the template-compliance
   check, and posts an automated review.
7. Address review comments. A human maintainer validates the procedure
   on a real Metashape install before merge.

## Per-article self-review checklist

Run this before submitting any draft for review.

- [ ] Article uses the `templates/article.md.tmpl` template (or the
      explanation/reference simpler templates).
- [ ] Article belongs to exactly one Diátaxis mode.
- [ ] If a how-to: **Context section is one short paragraph** (≤ 5
      sentences) per [`STYLE.md`](https://github.com/PhotogrammetryCommunity/metashape-expert-manual/blob/main/STYLE.md). No drift into explanation mode.
- [ ] **Tier 1 automated verification** has been run (the five scripts
      above). The PR description carries the *Automated verification
      log*.
- [ ] `edition:` field is set (`Standard` or `Pro`); edition rule in
      [`STYLE.md`](https://github.com/PhotogrammetryCommunity/metashape-expert-manual/blob/main/STYLE.md) followed.
- [ ] At least one official-manual reference is present.
- [ ] At least one forum reference is present (or "original synthesis"
      flag is set with justification).
- [ ] Every forum citation includes **date AND version-at-time** per
      [`STYLE.md`](https://github.com/PhotogrammetryCommunity/metashape-expert-manual/blob/main/STYLE.md). Use `docs/reference/version-timeline.md` to look
      up the version.
- [ ] Any feature this article relies on heavily is linked to its
      `docs/reference/features/<slug>.md` page, and that feature
      page has been updated to mention this article.
- [ ] `Applies to:` field names a specific Metashape version range.
- [ ] `Confidence:` field is set (`high` / `medium` / `low`) with one
      sentence of justification.
- [ ] `Status:` field is set (`verified` / `unverified` / `deprecated`).
- [ ] No claim is made that isn't supported by an in-text reference,
      reproducible procedure, or stated reasoning.
- [ ] No license-circumventing or unsupported-export trick is
      documented (per [`STYLE.md`](https://github.com/PhotogrammetryCommunity/metashape-expert-manual/blob/main/STYLE.md)).
- [ ] GUI steps name menu paths exactly as they appear in the current
      Metashape version.
- [ ] Python snippet (if any) imports `Metashape` and would run as
      shown — no pseudocode silently mixed in.
- [ ] All images have alt-text and a captioned source dataset.
- [ ] If the article needs a dataset to illustrate or validate, an
      Agisoft sample dataset has been considered first (see
      `docs/reference/sample-data.md`); a contributor-private dataset
      is used only when no sample fits, and the article says so.
- [ ] Heading hierarchy is unbroken (no jump from `##` to `####`).
- [ ] **Any claim the author could not personally validate carries an
      inline UV-NNN marker** linking to `docs/about/unverified.md`,
      and the corresponding tracker entry is filled in (per [`STYLE.md`](https://github.com/PhotogrammetryCommunity/metashape-expert-manual/blob/main/STYLE.md)
      § "Marking unverified claims inline").

## Relevance check (after each batch of new articles)

After any batch of ≥ 3 new articles, run this review pass before
declaring the batch complete. It guards against publishing content
that substantively duplicates the official manual, the freshdesk
tutorials, or existing articles in the corpus.

For each new article, fill in a one-row entry:

```
| article | manual coverage of same topic | this article's value-add | tier |
```

Tiers:

- **A**: Manual / freshdesk does not cover the topic at all (forum-
  only API surface, undocumented tweak, forum-attested gotcha).
- **B**: Manual / freshdesk covers the topic at a different depth or
  scope; the article either goes operationally deeper, addresses a
  forum-attested gotcha, or surfaces a use-case not in the docs. The
  article must include an **explicit scope statement** (in the
  opening section or Confidence callout) naming what the manual
  covers and where the article picks up.
- **C**: Substantively duplicates manual or existing article. **C-tier
  articles must be rewritten or cut before the batch is declared
  complete.**

Heuristics for the reviewer:

- The novelty-signal score from `scripts/manual_cross_check.py` is a
  weak prior, not a verdict. Low novelty (< +10) warrants a closer
  read; it does NOT automatically mean the article is redundant.
- Articles that explicitly point to where the manual covers the
  basics tend to read more rigorously than articles that imply
  differentiation. Encourage Tier B articles to add an explicit
  scope statement.
- "Relevant to whom?" Each article should solve a concrete reader
  pain point — preferably one that surfaced in the source forum
  thread. Articles whose only value is "the API exists" without a
  use-case framing get pushed to Tier C.

### Nav ordering check

After every batch that adds articles, also verify the affected
sections in `mkdocs.yml` are still ordered **by importance**, not
chronologically. New articles slot in at their importance tier:

1. **Foundational concepts** (used by many other articles).
2. **Core operations** (daily-use APIs / workflows).
3. **Recipes** (focused how-tos).
4. **Specialised** (less-common scenarios).
5. **Reference** (undocumented tweaks, deep API surfaces) — last.

Articles in a deliberate **Series** stay in their series order even if
that conflicts with the importance principle (the sequence itself is
the signal).

The check at the section level: scan the section's TOC and ask "if a
reader scrolled this list looking for what to read first, would they
find the most-foundational article at the top?" If not, reorder.
Section ordering itself goes **most general → less general**.

Reordering is a `mkdocs.yml`-only change; article content does not
move. Verify with `mkdocs build --strict` to catch typos in the nav
entries.

## Style

- Primary: [Google Developer Documentation Style Guide](https://developers.google.com/style).
- Secondary: [Microsoft Writing Style Guide](https://learn.microsoft.com/en-us/style-guide/welcome/).
- Project-specific overrides: [`STYLE.md`](https://github.com/PhotogrammetryCommunity/metashape-expert-manual/blob/main/STYLE.md).
- US English. Active voice. Second person ("you"). Sentence-case
  headings.

## Reporting issues

- Factual errors in published articles → file an issue with the
  `accuracy` label. Treated as P1; triaged within 7 days.
- Broken links → file an issue with the `link-rot` label, or wait for
  the monthly CI sweep.
- Style or template issues → PR welcome.

## Insight cards

Insight cards in `insights/` are *internal authoring notes*, not
published content. They have lower bars for prose quality but the same
bars for citation and accuracy.
