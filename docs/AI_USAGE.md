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
| Data scripts | `web/scripts/extract-ctx-crop.mjs`, `web/scripts/extract-hirise-crop.mjs`, `web/scripts/inspect-geotiff.mjs`, `web/scripts/make-demo-fixture.mjs` |
| Tests | `web/tests/**` |
| Build and configuration | `web/package.json`, `web/tsconfig.json`, `web/vite.config.ts`, `web/index.html` |
| Documentation | `web/README.md`, `THIRD_PARTY_NOTICES.md`, this section |

Generated data: `web/public/replay/demo/*` is a simulated replay from
`make-demo-fixture.mjs` (agent poses, routes, events, budgets, sigma and a
synthetic scarp in the hidden evaluator reference). It is labelled simulated or
fictitious in its manifest and is not a NASA observation.
`web/scripts/data/ctx_crop.json` holds real NASA/USGS CTX DTM heights; only the
resampling script was AI-assisted.

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
