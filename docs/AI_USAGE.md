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

## Existing integration contribution

The canonical ROS definitions, mock_agents publisher, smoke launch and ROS-only
contract checks were retained from dev/jesus at 00c8e44 with their history and
license metadata. Codex assisted with merging and adapting the shared scaffold.
The scope above does not assert that all retained contributor code was generated
by this tool; the contributor must confirm its own tool-use history for delivery.

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

## Continuous ground-start extension

OpenAI Codex assisted with the within-cell start connector, shared directed cost
function, search/result integration, synthetic regression tests and associated
model/interface documentation on feat/planner. Affected paths are recorded in
ai_usage.json. Tests use illustrative grids and resource parameters, not new NASA
observations or certified mobility limits. No ROS message/service definition or
generated media was added. Human review remains pending.

## D-07 explicit replanning after 20 metres

OpenAI Codex assisted with tests/planning/test_d07_twenty_metres.py and its
documentation. These newly generated synthetic flat-grid scenarios interpolate
20 metres along the initial planned polyline, independently account for consumed
resources, then request a new round trip after a map update. JSON/JUnit files
are outputs of actual test executions; scenario geometry and rates are
illustrative, not NASA observations, physiology or physical validation. No
automatic replan policy, MissionManager change or ROS wire change is included.

## F03.4 ROS-independent event policy

OpenAI Codex assisted with replan.py, synthetic event-policy tests and policy/model
documentation. The policy reuses the existing planner and movement model; it does
not authorize routes, command physical stops or change ROS contracts/MissionManager.
Test data and thresholds are illustrative, not approved scientific limits or NASA
observations. Local JUnit outputs record actual computational executions, without
claiming ROS integration, vehicle dynamics or physical safety. Affected paths are
listed in ai_usage.json; human review remains pending.

The subsequent contingency extension and English planner/root README updates were
also assisted by OpenAI Codex. The policy now tests direct-base return after a
proven primary-mission no-path/budget failure during OUTBOUND, preserving both
attempts for audit. Human/rover test scenarios distinguish detour, base-only access,
no escape, uncertainty and budgets; these remain synthetic computational examples.

Codex also assisted the subsequent audit fixes: reject premature service debits
during OUTBOUND, explicitly invalidate event/map version mismatches, and add
human/rover regression tests plus English policy/README/handoff clarification.
No A*, MissionManager or ROS contract change was made for these fixes.
