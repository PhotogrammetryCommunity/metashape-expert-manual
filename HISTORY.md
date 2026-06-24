# Project history

This file preserves the project's founding document — the original
`README.md` the project maintainer wrote in May 2026 to ask whether and how
the Metashape Expert Manual should be built. It is kept verbatim for
the historical record. The current `README.md` at the repo root is now
the project entry point.

---

## Original README (2026-05-22, founding document)

When using the Metashape software (by Agisoft), I noticed that the user
manual and the python API manual only covered basic usage, but I very
often have to search the Agisoft forums or the agisoft sample scripts
<https://github.com/agisoft-llc/metashape-scripts> to get better answers
and insights from long-time metashape users and agisoft developers
(especially Alexey Pasumansky).

I wonder if we could write a "expert" manual that contains all insights
from the agisoft forums: solutions to issues, tricks, best practices,
etc.

Answers from Alexey Pasumansky or Agisoft Technical Support on the
forum usually contain very insightful information.

What strategy do you propose to make that manual? I think that we
shouldn't separate Python API usage from GUI usage, because very often
the same tricks apply to both.

Should we scrape the whole agisoft forums before we proceed?

Should we download and analyze existing Metashape documentation before
we proceed?

How should the expert manual be organized?

Of course, this "expert" manual should have proper references in each
article to:

- the existing metashape manuals (user manual and python API)
- links to relevant agisoft forum articles (even direct links to
  messages if applicable).

This manual should be made available as a searchable documentation,
either online or downloadable. What format do you recommend to write
the manual? I think markdown (with extensions such as mermaid diagrams
and figures) is a good option, whay's your opinion.

Can you write a document that describes the step-by-step strategy to
build this manual? I guess there will be analysis phases, writing
phases, and consolidation phases.
