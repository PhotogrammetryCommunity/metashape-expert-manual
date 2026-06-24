# Metashape Expert Manual

A community-built expert-level companion to the Agisoft Metashape user
manual, distilling insights from the [Agisoft community forum](https://www.agisoft.com/forum/),
the [`metashape-scripts`](https://github.com/agisoft-llc/metashape-scripts)
repository, and field experience that go beyond what the official
manuals cover.

This is a community project. It is not affiliated with or endorsed by
Agisoft LLC.

## Status

The manual is **published** at
<https://photogrammetrycommunity.github.io/metashape-expert-manual/>
and is rebuilt automatically by CI on every push to `main`.

It currently spans 150+ articles across the photogrammetry pipeline
(workflow), cross-cutting topics, and reference material. Articles
carry a `status:` field and stay `unverified` until a maintainer
reproduces the procedure on a real Metashape install — see the
Tier 1/2/3 verification model below.

For the full project state, read [`STATUS.md`](STATUS.md).

## Read-first sequence

If you are picking this project up for the first time, read these in
order. Each is short.

1. [`STATUS.md`](STATUS.md) — the current project state (60 seconds).
2. This README — `Quickstart`, `Conventions and gotchas`, `Repo layout`
   below.
3. [`CONTRIBUTING.md`](CONTRIBUTING.md) — workflow and the per-article
   self-review checklist.
4. [`STYLE.md`](STYLE.md) — Metashape terminology, citation format,
   Diátaxis discipline.

After that, sample the pilot article at
`docs/workflow/alignment/diagnosing-under-aligned-chunks.md` to see the
shape of the work.

## Quickstart

### Build and preview the docs site locally

```bash
# Create the docs build venv (Python 3.12 recommended).
~/.pyenv/versions/3.12.9/bin/python -m venv .venv
./.venv/bin/python -m pip install --upgrade pip
./.venv/bin/python -m pip install -r requirements.txt

# Build (strict — fails on broken links / missing nav entries).
./.venv/bin/mkdocs build --clean --strict

# Live preview.
./.venv/bin/mkdocs serve
# → open http://127.0.0.1:8000
```

### Local source corpus

The `corpus/` directory holds Agisoft's official PDFs and (later) forum
scrape output. It is **gitignored** because we do not redistribute
Agisoft's documentation. Each contributor downloads their own copy.
Refresh procedure: see [`corpus/README.md`](corpus/README.md) and
[`corpus/official/VERSIONS.md`](corpus/official/VERSIONS.md).

### Tier 1 verification commands

Run these before opening an article PR.

```bash
# Python API introspection — verify every Metashape.* symbol the article uses.
~/.pyenv/versions/Metashape-2.2/bin/python - <<'PY'
import inspect, Metashape
print(inspect.getdoc(Metashape.Chunk.matchPhotos))
print(sorted(dir(Metashape.MetaData)))   # find missing methods like .get()
PY

# Official-manual menu-label check.
PDF=corpus/official/metashape-pro-2_3_en.pdf
pdftotext -layout "$PDF" - | grep -niE "<command>"

# Terminology-shift sweep (forum corpus → current manual).
pdftotext -layout "$PDF" - | grep -niE "renamed|previously called|formerly"
```

Capture the commands and findings in the PR description's *Automated
verification log* section (template in
`.github/PULL_REQUEST_TEMPLATE.md`).

## Repo layout

```
.
├── README.md                  # this file (project entry point)
├── HISTORY.md                 # founding document, preserved verbatim
├── STATUS.md                  # 60-second project status snapshot
├── CONTRIBUTING.md            # workflow + per-article self-review checklist
├── STYLE.md                   # primary editorial reference
├── mkdocs.yml                 # MkDocs Material config (strict build)
├── requirements.txt
├── docs/                      # the published manual content
│   ├── index.md
│   ├── workflow/              # articles arranged along the photogrammetry pipeline
│   ├── topics/                # cross-cutting topic pages (tag-style)
│   └── reference/             # glossary, version timeline, feature encyclopedia
├── templates/                 # article / insight-card / feature-page templates
├── scripts/                   # ingestion + helper scripts
├── corpus/                    # gitignored: Agisoft PDFs, forum scrape, cloned scripts
└── .github/workflows/         # build + deploy to GitHub Pages on push to main
```

The published site mirrors `docs/` only. Everything else is internal
authoring or operational support.

## Conventions and gotchas

The most important environment-specific things a fresh contributor
needs to know up front:

- **Metashape Python API is locally installed at
  `~/.pyenv/versions/Metashape-2.2/`** (and adjacent versions: 1.8,
  2.0, 2.1, 2.3). Activation status is `False` — meaning we can run
  and inspect operations but cannot export project files / data. This
  is sufficient for almost all article validation; license-circumventing
  workarounds are explicitly out of scope.
- **Build under `strict: true`.** `mkdocs build --strict` fails on
  broken links, missing nav entries, and similar structural problems.
  Run it after every doc edit.
- **Human signoff required.** Automated tooling may draft, lint,
  and check, but only a human maintainer who has reproduced the
  procedure on a real Metashape install may approve a PR or set an
  article's `status:` to `verified` (see `CONTRIBUTING.md`).
- **Enable the commit guardrail.** Run `git config core.hooksPath
  .githooks` once per clone. The hooks block accidental commits of
  email addresses, absolute home paths, and key-like strings.
- **Pushing to `main` publishes the site.** The
  `.github/workflows/deploy.yml` workflow builds under `--strict` and
  deploys to GitHub Pages on every push to `main`. Prefer pull
  requests for review; reserve direct pushes to `main` for trivial
  fixes.

## Three-tier verification at a glance

Every article goes through three verification tiers:

| Tier | Done by | Confirms |
|------|---------|----------|
| 1 | scripts (Python introspection, PDF text extraction) | API kwargs, GUI menu paths, terminology |
| 2 | automated editorial + technical review | template, voice, citations, Diátaxis discipline, original-synthesis claims |
| 3 | a human at the real GUI on a sample dataset | runtime correctness, dialog behaviour |

Tier 1 is **prerequisite** to Tier 2. Only Tier 3 can promote
`status: unverified → verified`.

## License

Content is licensed under [CC-BY-4.0](https://creativecommons.org/licenses/by/4.0/).
Code samples are licensed under the MIT License. Forum quotations
belong to their respective authors and are reproduced with attribution
under fair-use technical commentary.

## Where this project came from

The original founding document — the project maintainer's question about
whether and how to build this manual — is preserved in
[`HISTORY.md`](HISTORY.md).
