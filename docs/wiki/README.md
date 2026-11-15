# Scientific Wiki authoring tree

Begin with [Home](Home.md). This directory contains the complete English scientific draft, figures, animations and documentation audit prepared for owner review.

The nine chapters follow the agreed progression from research question and geological context to models, decisions, experimental method, cases and discussion. Supporting pages provide notation, parameters, references and reproduction instructions. `_Sidebar.md` and `_Footer.md` provide shared navigation.

The source files live alongside the repository so scientific statements can link to their exact implementation, configuration and evidence. This publication package retains the source/evidence links, all marked media and bounded supporting records. A native GitHub Wiki mirror uses publication-specific links to the source commit; its content remains scientifically auditable alongside this repository copy.

Rebuild documentation graphics with `python docs/wiki/tools/build_figures.py`, then inspect the [reproduction guide](Reproducibility.md) and run `python docs/wiki/tools/audit_publication.py`. These tools concern documentation only.

Scientific owner review follows this complete first draft. Existing approvals and acceptance criteria retain their recorded scope.

The [publication manifest](audit/publication-manifest.json) seals this bounded package. The renamed [local draft manifest](audit/local-draft-manifest.json) and original audit reports are historical records. Their references to the full local archive do not imply that raw capture frames, private worlds or every research working file are published.
