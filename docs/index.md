# Metashape Expert Manual

An expert-level companion to the [official Agisoft Metashape user manuals](https://www.agisoft.com/downloads/user-manuals/),
distilling insights from the [Agisoft community forum](https://www.agisoft.com/forum/),
the [`metashape-scripts`](https://github.com/agisoft-llc/metashape-scripts)
repository, and field experience that go beyond what the official docs cover.

## Who this is for

Intermediate-to-advanced Metashape users. We assume you have read the official
manual once and completed at least one end-to-end project. If you are new to
Metashape, the [official Getting Started guide](https://www.agisoft.com/support/tutorials/)
is the right starting point — this manual deliberately does not duplicate it.

## What this is *not*

- Not a replacement for the official [user manual](https://www.agisoft.com/pdf/metashape-pro_2_3_en.pdf) or [Python Reference](https://www.agisoft.com/pdf/metashape_python_api_2_3_1.pdf) (latest: Metashape Pro 2.3 / Python API 2.3.1).
- Not a substitute for the official [Agisoft Knowledge Base](https://agisoft.freshdesk.com/support/solutions) (support articles, tutorials, licensing and troubleshooting guides). Where it already covers a topic well, our articles link to it rather than duplicate it — see the [Agisoft Knowledge Base index](reference/agisoft-knowledge-base.md).
- Not a beginner tutorial.
- Not an unofficial source of vendor advice. We cite the official docs and
  the forum as primary sources, with attribution.

## How content is organised

Two navigation axes:

- **Workflow** — articles arranged along the photogrammetry pipeline (alignment
  → point cloud → mesh → texture → DEM/orthomosaic → export). This mirrors the
  official user manual.
- **Topics** — cross-cutting tags (Performance, CRS, Markers/GCPs, Scripting,
  Troubleshooting, …). The same articles, organised by concern.

Every article follows a fixed template: problem → context → solution → GUI
walkthrough → Python equivalent → caveats → references. GUI and Python are
treated as two views of the same operation because forum advice routinely
mixes both.

## Contributing

This project is built by a mix of human authors and AI agents under human
review. Read [Contributing](about/contributing.md) before opening a PR — there
are firm rules around validation, citation, and the **no-agent-merge** policy
that exist to keep this manual trustworthy.

## License and attribution

Content is licensed under [CC-BY-4.0](https://creativecommons.org/licenses/by/4.0/).
Code samples are licensed under the MIT License. Forum quotations belong to
their respective authors and are reproduced with attribution under fair-use
technical commentary.

This is a community project. It is not affiliated with or endorsed by
Agisoft LLC.
