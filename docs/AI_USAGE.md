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

## Integration work (Jesus), 14 November 2026

Claude Code (Anthropic) assisted the integration owner with the canonical ROS
message and service definitions, the mock nodes in `src/mge_sim`, the launch
files in `src/mge_bringup`, the ROS-backed gateway, replay recorder and replay
validator in `src/mge_gateway`, their tests, the development image and script,
and the related sections of the README, ICD and integration log. The work was
directed and reviewed by the integration owner; the requirements and
architecture came from the team guides. This confirms the tool-use history of
the contribution retained from `dev/jesus`.

The mock nodes produce synthetic placeholder values at run time (a flat grid,
static agent states, straight-line routes). They are labelled `MOCK` and are not
NASA observational data. `data/sample/replay` is a recording of those mock
nodes, produced by `scripts/record_sample_replay.py`; it is not a mission
result. OpenAI Codex assisted with the earlier merge of that contribution into
the shared scaffold.

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
