<!--
Thanks for contributing! Please read CONTRIBUTING.md before opening
this PR.
-->

## Summary

<!-- One sentence describing what this PR adds or changes. -->

## Type

- [ ] New article
- [ ] Article update / correction
- [ ] Insight card(s) only
- [ ] Tooling / repo change
- [ ] Documentation of process (CONTRIBUTING, STYLE, etc.)

## Per-article self-review checklist

<!-- Required for new articles or article updates. Skip if not applicable. -->

- [ ] Article uses the `templates/article.md.tmpl` template (or the
      explanation/reference simpler templates).
- [ ] Article belongs to exactly one Diátaxis mode (how-to / explanation /
      reference).
- [ ] `edition:` field is set (`Standard` or `Pro`). See STYLE.md edition
      rule.
- [ ] At least one official-manual reference is present.
- [ ] At least one forum reference is present (or `original synthesis`
      flag is set with justification).
- [ ] Every forum citation includes **date AND version-at-time** per
      STYLE.md. Use `docs/reference/version-timeline.md` to look
      up the version.
- [ ] Any feature heavily relied on links to
      `docs/reference/features/<slug>.md`; the feature page is
      updated to mention this article.
- [ ] `applies_to:` field names a specific Metashape version range.
- [ ] `confidence:` field is set with one sentence of justification.
- [ ] `status:` field is set (`verified` / `unverified` / `deprecated`).
- [ ] No claim is made that isn't supported by an in-text reference,
      reproducible procedure, or stated reasoning.
- [ ] No license-circumventing or unsupported-export trick is documented
      (per STYLE.md "Things not to do").
- [ ] GUI steps name menu paths exactly as they appear in the current
      Metashape version.
- [ ] Python snippet imports `Metashape` and would run as shown.
- [ ] All images have alt-text and a captioned source dataset.
- [ ] Heading hierarchy is unbroken (no jump from `##` to `####`).

## Validation

<!-- Required if status: verified. -->

- Metashape version validated against:
- Dataset:
- Notes (any deviations from documented procedure):

## Automated verification log (Tier 1)

<!--
Required for any PR introducing or substantially editing an article.
See CONTRIBUTING.md.
-->

- Python API introspection ran against:
  `~/.pyenv/versions/Metashape-X.Y/bin/python` (Metashape <version>).
  - kwargs / methods confirmed: …
  - corrections applied: …
- PDF menu-label check ran against:
  `corpus/official/metashape-pro-<version>.pdf`.
  - menu paths confirmed: …
  - corrections applied: …
- Terminology-shift sweep: <findings, e.g. "Gradual Selection → Clean
  Tie Points in 2.x; article updated">.
- Items deferred to Tier 3 (real install): …

## Reviewer guidance

<!--
Reminder: only a human maintainer who has reproduced the procedure on a
real Metashape install may approve PRs or set article status to
`verified`.
-->

- Reviewers:
