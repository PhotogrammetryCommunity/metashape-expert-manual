# AGENTS.md

Repo-specific rules for AI agents working on the Metashape Expert Manual.
See `README.md`, `CONTRIBUTING.md`, and `STYLE.md` for the full workflow.

## Custom Instructions

### Reader-facing changelog

The "What's new" page (`docs/about/changelog.md`, in the nav under
*About*) is a hybrid: the **list** of entries is generated from git
history, but the **one-line description** after each entry is written by
hand.

- After committing a content change under `docs/`, run
  `./.venv/bin/python scripts/gen_changelog.py` to add the new
  create/update entries to the list (it reads committed history).
- Then **hand-write a short sentence** describing what changed, after the
  ` — ` on each new entry. The generator preserves these sentences when
  the list is regenerated — it never writes them.
- Do not restructure the page by hand (month grouping, links); change the
  generator instead. Only the per-entry sentences are edited by hand.
- Pre-push / CI gate: `./.venv/bin/python scripts/gen_changelog.py --check`
  must pass — it flags a stale entry *list*; your sentences are
  preserved.
- **Site-wide mechanical commits** (e.g. a bulk find-and-replace across
  many articles) are not per-article reader news and would flood the
  list. Add their commit SHA to
  `scripts/data/changelog-ignore-commits.txt` (one SHA per line, like
  git's `.git-blame-ignore-revs`) so the generator skips them.

### Archived companions on forum/KB citations

Every forum/KB link must carry a verified-Wayback archived companion
(see `STYLE.md` → *Archived companions for forum and KB links*).

- After adding or changing a forum/KB citation, archive the source on
  the Wayback Machine, add its `original-url → wayback-url` row to
  `scripts/data/archive-wayback.tsv` (status `LIVE`), then run
  `./.venv/bin/python scripts/add_archive_links.py --all` to attach the
  companion.
- Pre-push / CI gate:
  `./.venv/bin/python scripts/add_archive_links.py --all --check` must
  pass — it fails if any cited forum/KB link lacks a companion or if a
  cited URL has no verified snapshot (generic site roots are exempt).

Both gates run locally via `.githooks/pre-push` (enable once per clone
with `git config core.hooksPath .githooks`) and in CI
(`.github/workflows/deploy.yml`, the *Content checks* step).
