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
The rover and drone models (`web/public/assets/models/rover.glb`, `drone.glb`) are official
NASA/JPL-Caltech models, not AI-generated; the Blender scripts that removed their branding,
decimated and exported them (`web/scripts/blender/`) were AI-assisted.
During integration review, Claude through Claude Code also wrote
`web/scripts/strip-glb-branding.mjs` (with `web/scripts/glb.mjs` and `glb.d.mts`) and
`web/tests/modelBranding.test.ts`. They remove the marks the Blender pass missed: the
rover's blade sheet is replaced with the drone's already cleaned sheet, and two logos on the
drone blade roughness map are filled with its plain background. This is a deterministic flat
fill or copy, not generative inpainting, so the models still contain no AI-generated imagery.

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

## Probable mission planning and traceability

OpenAI Codex assisted the owner-selected probable-roadmap checklist, dependency
and acceptance definitions, NASA resource-to-result register, navigation updates
and correction of the provisional data-register status. Internal desired/expected
milestone estimates and compact observations from parallel planner/mission work are
maintained locally under Git-ignored .local/planning, with their own metadata.
Estimates are planning assumptions, not measured human effort, scientific results
or newly completed mission acceptance. No media or NASA observation was generated
by this documentation work. Human owners approve science and integration closure.

## Optional terrain-randomization hypothesis

OpenAI Codex assisted documenting the owner's H-DAN-01 proposal, Daniel's P1
checklist entry and source/assumption/seed traceability requirements. The proposed
experiment remains unimplemented and untested. No rover image was imported and
no terrain generator, synthetic map, image/video/audio or experiment result was
created by this documentation change. Future generated artifacts require their
own actual tool-use records and applicable visible watermarks.

## PR #3 input-validation correction

OpenAI Codex assisted finite coordinate and explicit resource-input validation in
the gateway and its new HTTP regression cases. Tests use illustrative malformed
and valid requests; no scientific dataset, mission run or media was generated.
The existing ROS fields, optional oxygen sentinel and mission authority remain
unchanged. The affected code/tests and contract clarification are listed in
ai_usage.json.

The HTTP correction also covers raw non-finite JSON numbers and numeric overflow:
rejected values are sanitized in validation-error details so HTTP 422 itself
cannot fail JSON serialization. Four additional adversarial regression requests
exercise that case without forwarding a ROS command.

## PR #3 late-event replay correction

OpenAI Codex assisted consistent validation of arrival-ordered replay records
against sequence-ordered snapshot history, rejection of conflicting/invalid event
sequences, regression tests and the corresponding ICD clarification. The tests
generate illustrative event/state fixtures in temporary directories; no NASA
observations, mission benchmark or media are generated. Original event stamps,
late deliveries and existing source/tool disclosures are preserved.


The late-event regression also exercises the real ReplayWriter through the
strict offline contract reader and viewer oracle added by the approved main
baseline. That consumer now compares snapshot history by sequence while
preserving arrival timestamps and all existing identity/provenance guards.

## Local organizer delivery coordination

OpenAI Codex assisted documenting the owner's pre-submission organizer notice
and endorsement requirement, the proposed coordination margin, responsibility,
acceptance evidence and contextual agent reminders in AGENTS.md and the team
checklist. No organizer was contacted, endorsement obtained, scheduled alert
created, scientific observation or media generated by this documentation change.

## Terrain provider integration corrections

Claude Code (Anthropic) assisted the integration owner in reviewing PR #8 and
correcting the `mge_data` and `mge_mapping` ROS nodes to follow the planner's
map batch protocol, declaring their package dependencies, writing the ROS
integration test for them and updating the related documentation. The test
sends illustrative SIMULATED observations that repeat public prior heights; no
terrain array, scientific dataset, mission result, image, video or audio was
generated. The affected paths are listed in ai_usage.json.

## Gateway typed serialization and source provenance

Claude Code (Anthropic) assisted the integration owner with the typed JSON
converters in the gateway store, their adoption by the ROS bridge and replay
recorder, the `source_mode` field in the gateway manifest, recorded manifests,
launch files and offline validators, the mock planner clearance correction,
the new unit/contract/integration test cases and the related documentation.
Test inputs are illustrative values and relabelled copies of the MOCK fixture;
no scientific dataset, mission result, image, video or audio was generated.
The affected paths are listed in ai_usage.json.
