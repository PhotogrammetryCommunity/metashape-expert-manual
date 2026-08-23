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
