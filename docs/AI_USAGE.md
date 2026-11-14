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

## Mission profiles and authority, 14 November 2026

OpenAI Codex assisted with the activity/grade cost models, proposed profile
registry and provenance records, illustrative test configuration, pure mission
authority and task/evidence types, ROS boundary, regression/contract tests,
reproducible formula-check script, scientific model documentation, benchmark
protocol and integration handoff. David selected the modeling approach and task
policy; numerical coefficients remain proposed unless separately approved.

NASA/JPL and NIST references are cited as technical sources, not authors of the
adapted engineering model. Synthetic formula outputs are marked MODEL_CHECK;
they are not NASA observations, live missions, physical tests or an A/B/C result.
No generated image, video or audio is part of this change.

## Planner response interoperability, 14 November 2026

OpenAI Codex assisted with mission-owned handling of unavailable planner metrics,
nullable internal decision values, map-batch response timestamps and related
Python/ROS regression tests. The published planner source was inspected at
34c515b6b86f73336844e8b3614c70b144574ec3; its code was not modified or merged.
These changes preserve failure reasons and do not approve scientific profiles.

## Delivery verification

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
