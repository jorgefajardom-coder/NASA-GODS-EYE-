# Required AI-use declaration

Competition-required disclosure; not optional credit or AI authorship. Human
owners remain responsible for reviewing the work.

## Initial scaffold, 14 November 2026

OpenAI Codex assisted with ROS package skeletons, proposed interfaces, Python
contracts/stubs, gateway availability responses, frontend skeleton, configuration
templates, documentation and checks. It also assisted with the competition-policy
update in AGENTS.md. The idea and science specifications came from team guides.
Affected paths and generation metadata are recorded in [ai_usage.json](ai_usage.json).

No NASA scientific dataset, measured result or benchmark was generated or
claimed. No generated image/video/audio asset is included. The empty Three.js
grid is a code-rendered placeholder, not a terrain product or mission run.

## Web mission viewer, 14 November 2026

Claude (Anthropic), used through Claude Code as a coding assistant, helped write
the web viewer that replaced the empty scaffold grid in `web/`. This declares the
tool; it does not attribute authorship.

| Area | Paths |
|---|---|
| Viewer source | `web/src/**` |
| Data scripts | `web/scripts/extract-ctx-ortho.mjs`, `web/scripts/extract-ctx-crop.mjs`, `web/scripts/extract-hirise-crop.mjs`, `web/scripts/inspect-geotiff.mjs`, `web/scripts/make-demo-fixture.mjs` |
| Tests | `web/tests/**` |
| Build and configuration | `web/package.json`, `web/tsconfig.json`, `web/vite.config.ts`, `web/index.html` |
| Documentation | `web/README.md`, `THIRD_PARTY_NOTICES.md`, this section |

Generated data: `web/public/replay/demo/*` is a simulated replay from
`make-demo-fixture.mjs` (agent poses, routes, events, budgets, sigma and a
synthetic scarp in the hidden evaluator reference). It is labelled simulated or
fictitious in its manifest and is not a NASA observation.
`web/scripts/data/ctx_crop.json` holds real NASA/USGS CTX DTM heights; only the
resampling script was AI-assisted.
`web/public/replay/demo/ctx_ortho.png` holds real CTX orthomosaic pixels from JPL Mars
Trek (NASA/JPL-Caltech/MSSS/USGS); only `extract-ctx-ortho.mjs`, which resamples and
contrast-stretches it, was AI-assisted. Likewise `web/public/replay/demo/geology.json`
holds USGS SIM 3464 unit text and polygons unchanged apart from reprojection and clipping;
only `extract-geology.mjs` and the viewer code were AI-assisted.

Not AI-generated: terrain heights (USGS Astrogeology / NASA), the astronaut model
by LasquetiSpice (CC BY 4.0, materials converted only), and the fonts (SIL OFL 1.1).
No AI-generated image, video or audio is included. Machine-readable metadata:
[ai_usage.json](ai_usage.json), the `aiDisclosure` field in `web/package.json` and
the `ai_disclosure` object in `web/public/replay/demo/manifest.json`.

## Before delivery

- Record actual tool uses and affected code/data/assets in text and metadata.
- Keep a visible `AI-generated` watermark on generated images/videos and submitted
  captures/exports containing that material.
- Disclose generated audio/code/data in descriptive text and metadata; an AI
  author/coauthor signature does not replace disclosure.
- Generated content must not contain/use/modify NASA branding/design elements.
- Keep NASA source citations/licenses distinct from these declarations.
- Reflect actual uses in the competition submission form too.

[Official GO Team policy](https://github.com/nasa/spaceapps/discussions/1849).

## Existing integration contribution

The canonical ROS definitions, mock_agents publisher, smoke launch and ROS-only
contract checks were retained from dev/jesus at 00c8e44 with their history and
license metadata. Codex assisted with merging and adapting the shared scaffold.
The scope above does not assert that all retained contributor code was generated
by this tool; the contributor must confirm its own tool-use history for delivery.

## Contract reconciliation, 14 November 2026

OpenAI Codex assisted with the cross-branch audit, canonical replay adapter,
strict ROS/JSON and dataset checks, launch profile gates, provenance display
helper, contract/integration tests, target-platform validation script and the
baseline/matrix/five handoffs. Exact paths are recorded in ai_usage.json.
These are contract examples and tests, not replacement owner modules, an
approved science model, NASA observations or a completed mission.

The three unchanged MOCK replay files under tests/fixtures/replay were retained
from Jesus's integration commit d28f3e23f268d50c6c55f2b1f85a1cadbe9281ed.
The original contribution declares Claude Code (Anthropic) assistance; its source
and byte hashes are retained in tests/fixtures/replay/provenance.json. Synthetic
test arrays/metadata are explicitly MOCK and never NASA observational products.
No generated image, video or audio was created in this reconciliation. Existing
licences/attributions and mandatory declarations are preserved; human owner
review and competition submission disclosure remain required.

## Planner P0 implementation

Codex assisted the new bounded FAST/SAFE solver, input adapters, ROS service,
acceptance tests, benchmark generator and handoff documentation. Synthetic maps,
obstacles and resource assumptions in tests are newly generated illustrative
inputs; benchmark timings are measured from new executions.
Motion/resource profiles require human scientific review. NASA source data remain
observations from cited upstream products; new processing does not make those
observations newly acquired by the team. See [data provenance](planner_provenance.md)
for the crop workflow and source references.

Fresh computational benchmark measurements are now recorded under
evidence/planner-p0-20261114. Their scenarios were AI-assisted illustrative test
data; reported timings and costs are actual new executions of the recorded code
commit. They are computational test measurements, not physical or NASA mission
measurements. No generated image, video or audio asset was added.

The reconciliation verification logs/JUnit and hashes under
evidence/contract-baseline-20261114 are actual tool execution records on the
reported source. Codex assisted their collection/documentation; they are not
invented measurements or mission observations.
