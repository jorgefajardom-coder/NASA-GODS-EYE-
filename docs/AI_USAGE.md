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

## Terrain data and incremental mapping implementation (`feat/data`), 14 November 2026

Google Antigravity assisted Daniel with the bounded HTTP 206 ingestion script
(`scripts/prepare_jezero_terrain.py`), the public terrain validation and ENU
georeferencing module (`src/mge_data`), the incremental belief fusion and
traversability module (`src/mge_mapping`), the terrain configuration and
provenance documentation (`config/terrain.yml`, `docs/data_sources.md`,
`data/sample/README.md`), and the contract/mapping test suites
(`tests/contracts/test_data_manifest.py`, `tests/mapping/test_observation.py`).

All elevation arrays in `data/sample/terrain.npz`,
`data/sample/mola_regional_context.npz`, and `data/reference/` are real
observational planetary products retrieved from official NASA PDS / USGS
Astrogeology archives (MRO/CTX DOI `10.5066/P906QQT8`, MRO/HiRISE DOI
`10.5066/P9REJ9JN`, and Mars Global Surveyor/MOLA PDS bundle
`urn:nasa:pds:mgs_mola_topography_derived::1.0`), not AI-generated terrain.
`data/sample/preview_ctx_prior.png` is a deterministic grayscale raster plot of
the observational MRO/CTX elevation grid, not an AI-generated image.

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
