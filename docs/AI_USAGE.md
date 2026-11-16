# Required AI-use declaration

## Reviewed ImageGen Wiki illustrations

The repository owner supplied a 20-image ImageGen package for a scientific-Wiki visual refresh. OpenAI Codex assisted the semantic review, captions, provenance and documentation-only validation. Nine selected images were edited with image_gen to remove unsupported numerical, geographic, capability or evidence claims and to improve readability. Eleven originals remain excluded with reasons in `docs/wiki/Editorial-Review.md`. The supplied theses and private research working files were not uploaded as part of this edition.

New PNGs and encoding-only WebP reading copies are stored in `docs/wiki/assets/imagegen-20261115`. Each carries a large visible `AI-generated | Conceptual illustration` footer; prompts and source/output hashes are recorded under `docs/wiki/audit/editorial-20261115`. Original measured/model figures, all 21 existing assets, the three GIFs and historical manifests are preserved. Numerical interpretation remains tied to the original primary sources and run records. The edition introduces no technical or scientific-parameter change. The source package requires owner review before a separate Wiki synchronization; that review remains pending.
## Submission videos: AI-generated voice-over, 15 November 2026

The English voice-over of the team's 30-second submission videos is
**AI-generated speech**. It was made with Higgsfield (model Seed Audio 1.0 by
ByteDance) from text the team wrote, using built-in preset voices, not a cloned
or recorded human voice:

| Video file | Preset voice | Lines spoken |
| --- | --- | --- |
| `mars-gods-eye-demo.mp4` (Mars Gods Eye - Demo) | Andre | "Houston, we have a bug. It's not in our code. It's in the map." / "Explore six Mars zones, built on real NASA terrain." / "It plans the route, checks time, energy and oxygen, and replans when the ground disagrees." / "Follow the rover through its real stops, and see the photos NASA took there." / "Water and radiation for every zone, and a live link to the ROS gateway." / "Mars Gods Eye. Open it in your browser." |
| `mars-gods-eye-d.mp4` (Houston, we have a bug) | Andre | "Houston, we have a bug. It's not in our code. It's in the map." / "From orbit, Mars gets one height every twenty metres. A crew on foot needs more." / "So we built Mars Gods Eye. It plans the route, checks time, energy and oxygen. When the ground disagrees, it stops and replans." / "Five people. One hackathon. One crater." / "Mars Gods Eye. Open it in your browser." |
| `mars-gods-eye-a.mp4` (The map was wrong) | Gideon | "Jezero crater. The map says this ground is clear." / "The map was made from orbit. One height, every twenty metres." / "So when the ground disagrees, Mars Gods Eye stops, cancels the route, and plans a new one, with the oxygen that's left." / "Every decision, recorded. Replay it in your browser." / "Mars Gods Eye." |

The voice is also declared in each file's metadata (MP4 `comment` tag, which
starts "AI use: the voice-over is AI-generated speech (Higgsfield, Seed Audio
1.0, preset voice ...)"). The spoken words were checked against the script with
a local speech-to-text model.

Other AI use in the same videos:

- **Music and sound effects**: synthesised by a Python script written with
  Claude (Anthropic) through Claude Code; no generative audio model and no
  samples. Declared in the same metadata tag.
- **Editing**: the shot timing, on-screen type and frame-by-frame capture and
  render scripts were written with Claude through Claude Code.
- **Picture**: screen recordings of the project's own web viewer, not
  AI-generated video. The AI-generated images that appear in them (team logo,
  astronaut portrait) keep their burned-in `AI-generated` marks.
- **Not AI-generated**: the three Perseverance photos in the demo video are
  real NASA/JPL-Caltech raw images (sol 13: Navcam, front and rear Hazcam) from
  NASA's public raw-image feed, credited on screen.

The videos, voice files and scripts are kept outside the repository (Git-ignored
`.local/video/`). The videos contain no NASA logos, flags or mission marks, and
they label the replan as a recorded run with MOCK execution and the gateway
panel as a MOCK source: no live mission is claimed.

## English scientific Wiki and pedagogical media

OpenAI Codex assisted the complete English scientific Wiki in `docs/wiki`: nine chapters, the landing page and supporting glossary, parameter, bibliography and reproduction pages. Private doctoral and master's theses supplied style references only; they were read locally and were not uploaded or copied into the Wiki. Scientific statements cite original articles, NASA/JPL technical reports and public product metadata with locators; project outcomes retain their configuration and run identifiers.

The cover was generated with image_gen as an unbranded conceptual illustration. Documentation-only code constructs the scientific diagrams, model examples and three GIFs from declared inputs. Every image and every decoded GIF frame has a visible `AI-generated` mark; captions and metadata distinguish conceptual media, model calculations and the recorded SIMULATED case. Assets, input hashes, library versions and audit results are stored within the Wiki. No NASA insignia or mission-brand graphic is included in the generated artwork.

The work changes explanatory documentation and its tools only. Existing model coefficients, runtime configuration, contracts and technical implementations remain unchanged. The complete first draft is prepared for owner scientific audit; publication and approval retain their separate records. Previous sealed AI declarations are preserved under `docs/wiki/audit/previous-document-versions`.

## Root README summary for judges

Claude Code (Anthropic) assisted the integration owner in writing the
one-screen English summary for judges at the top of the root README: problem,
approach, public viewer link, the NASA resources with their actual role
(planner input, display context or held-back reference) and the stated
limitations. Every statement is drawn from the existing data-source register,
the viewer source table and the recorded-recovery evidence. The team status
moved below it, with the 20:00 submission target from D-DEL-03. No code, data,
observation, mission result, approval, image, video or audio was generated.
The affected paths are listed in ai_usage.json.
## Science extension tree and reproducible diagram

OpenAI Codex assisted the proposed 22-node guide (four common gates and eighteen
extensions), structured source, Markdown/SVG/PNG renderer, owner-navigation
updates and the latest local-idea clarification of D-DEL-03. The guide records
future questions, responsible leads/reviewers, AND dependencies, acceptance and
stop conditions; no capability or completed milestone is asserted.

`docs/assets/science-tree/science-tree.png` and `.svg` are code-rendered planning
diagrams, not image-model output or NASA observational imagery. They retain a
visible `AI-generated` label and embedded tool/source metadata. The renderer's
Pillow output was visually inspected for legibility; the source and image parity
check is reproducible. No image-generation model, NASA branding, terrain,
observation, mission measurement or new experiment result was generated. This
documentation preserves the delivery freeze and permits only the owner's bounded
local assessment of unlisted ideas for the 15-Nov-2026 discussion.

## Local per-agent campaign and EVA proposal

OpenAI Codex assisted primary-source research, per-patch analytical workloads,
phase-by-phase duration/resource calculations, sensitivity diagnostics and a
standalone reproducer for separate rover, human EVA and drone episodes. The
proposal, source register, derived data and validation artifacts are listed in
ai_usage.json. No runtime configuration, profile, owner implementation or
approved receipt is changed; all new work remains local without publication.

NASA/JPL publications provide cited hardware facts and terrestrial/lunar analog
context. Distances, ascents, station counts, phase allocations, waits and new
budgets are explicitly generated engineering proposals, not mapped routes,
NASA prescriptions, physical capacities, observations or executed science.
Adverse rejections and unestimated drone sleep/thermal/charging demand remain
visible. No recharge, new mock, terrain, media, scientific approval or execution
evidence is generated. Prior declarations and media metadata are preserved.

## Local scientific patch survey

OpenAI Codex assisted the primary-source literature search, interpretation of
the owner's supplied report, 17-sector candidate catalogues, proposed map
requests to Daniel, scale/resource calculations and their standalone reproducer,
source/validation records and mission-owned scientific documentation. Affected
paths are listed in ai_usage.json. The survey remains local during the owner's
separate reconciliation audit, without commits, pushes or merges.

Published NASA/USGS/instrument-team observations and historical waypoint values
are cited or copied with provenance. Candidate selection, geographic query
envelopes and model costs are generated research proposals/diagnostics, not new
NASA terrain, mineral detections, physical measurements or mission results.
No raster or evaluator array is generated, read into this research from the
private reference directory, or promoted to planning input. No media, new mock,
discovery/task producer, scientific approval or runtime change is supplied.

## Delivery conclusions and owner-confirmed freeze

OpenAI Codex assisted comparing the owner's five-page delivery PDF with the
Conciliación/Rama David chats and published main9198b3d, recording the explicit
scope/time replies, updating publication metadata and per-owner delivery tasks,
and adding a judge-facing summary. The local science/campaign reports were read
for conclusions only; their numeric drafts, data and the pending cost backend
were not imported. The original PDF is private reference material, not a new
source of official rules or scientific approval. These changes generate
documentation/metadata only, not code, terrain, observations, scientific results,
images, video or audio. Existing source credits and mandatory declarations remain.

## Audit contract reconciliation rc.2

OpenAI Codex assisted with the causal observation fix, explicit estimated-prior
candidate policy, producer/consumer tests, recorder reproduction script, exact-run
viewer entry, datum-aware camera, source/grid labels and scenario-bound overlays.
It also assisted the fresh cost comparison, interface-gap analysis, source locks,
handoffs and verification documentation. Exact affected paths are listed under
`audit_contract_reconciliation_rc2` in ai_usage.json.

The recorded single-cell contradiction is a deterministic SIMULATED test input,
not a NASA local measurement. The recording uses real public data/mapping/planner
with MOCK mission and kinematic primary-human execution; rover/drone remain idle.
READY and software-test results do not establish scientific COMPLETE, approved
costs, three-role execution or validated LIVE. Existing source terrain, target
approvals, scientific coefficients, licenses, contributor history and mandatory
media disclosures/watermarks are retained. No new image, video or audio is
generated by this reconciliation.

## Mission cost agreement and activity-duration research

OpenAI Codex assisted with the mission-owned cost-contract proposal, analytical
vector exporter, primary-source activity-duration review, duration-impact pilot,
contract-consistency tests and explicit success-evidence criteria. The work
also updates mission scenario references, the estimated-prior limitation text,
scientific decisions, handoff and retained diagnostic/validation records.
Affected files and evidence are enumerated in ai_usage.json.

NASA publications supply cited model assumptions and analog task observations;
the 300 s inspection alternative and mixed 600 s workflow phase allocation are
explicit engineering assumptions pending review. Pilot costs are generated
model diagnostics, not astronaut measurements, completed tasks or mission
results. Daniel's public terrain arrays and the original approved scenario
values/receipt remain unchanged. Published main/planner are inspected without
copying their implementations or changing shared messages. No mock, discovery,
execution observation, image, video, audio, scientific dataset, external message
or new scientific approval is produced. Existing profile/cost/execution gates
remain pending; criteria documentation does not close runtime acceptance.

## Mission branch reconciliation

OpenAI Codex assisted reconciling mission ec819e5 with main5898e7d, retaining
all contributor disclosures, generated-media records and both histories.
Fresh software validation and exact-source cost diagnostics are retained under
`evidence/mission-reconciliation-20261114/`. Existing owner implementations,
ROS fields, scenario-value approval and operational/scientific gates remain
unchanged. This merge is not a new mission result or scientific approval.

## Mission publication refresh

OpenAI Codex assisted retaining both sides' mandatory disclosures after README
PR22 advanced main to b0acc1c during PR25 validation. Mission entries precede
the main entries to avoid competing append conflicts. All main records and
media metadata remain intact; runtime sources match validated 5c66178 exactly.
No scientific value, operational approval or execution result is changed.

## Experimental continuous recovery

OpenAI Codex assisted the owner-requested NON_CELL_CENTER recovery. The opted-in
connector preserves supplied XYZ and charges profile-bounded 3-D movement. The
MOCK mission waits for fresh stop feedback, rejects stale results and retains
spent allocations and required reserves. Tests use synthetic inputs and a MOCK
software execution/recorder package. This does not approve a scientific model,
physical traversal or LIVE mission. Affected paths are in ai_usage.json.
The terrain batch test also waits for planner-side assembly within its existing
readiness deadline; substantive results and search limits are not retried.

## Strict recorded replay

OpenAI Codex assisted the owner-requested replay validation corrections. The web
loader validates counts, immutable routes, recorded raster versions and closing
snapshots. Regression tests use synthetic inputs and an actual MOCK software
recorder package; they do not approve a scientific model, physical traversal or
LIVE mission. Existing contributor work and disclosures remain intact. Affected
paths are in ai_usage.json.

## Estimated-terrain scope decision

OpenAI Codex assisted recording the owner's accepted D-EST-01 decision to permit
hypothetical planning over valid orbital estimates before local observation,
with contradiction-driven invalidation/replanning, ownership and acceptance
obligations. The documentation also preserves open integration steps 4/5 and
labels varied-scene/larger-map work and H-DAN-01 as optional extensions. No
planner/mapping behavior, generated terrain, experiment, media or mission result
was introduced by this documentation change.

Competition-required disclosure; not optional credit or AI authorship. Human
owners remain responsible for reviewing the work.

## PR12 final main reconciliation

OpenAI Codex assisted reconciling planner `a959d25` with main `3a9032b` before
the owner-authorized PR12 merge. Both sets of mandatory disclosures, planner
review corrections and main's callback scheduling/replay/executor changes are
preserved. No scientific model, physical execution or LIVE mission is approved.
The new kinematic execution test also uses the existing test-only ground-scene
initializer, with assertions for initial pose and observation datum consistency.

## CI workflow display name, 14 November 2026

OpenAI Codex assisted renaming the GitHub Actions workflow from `Scaffold checks`
to `CI checks` in `.github/workflows/ci.yml`. Triggers, jobs and commands are unchanged.

## Experimental scenario approval recording, 14 November 2026

OpenAI Codex assisted recording David's explicit approval of JZ-P01..JZ-P07,
the hash-bound receipt, separate pending-integration configuration, diagnostic
checks and tamper/runtime regression tests. The approval itself is the human
owner's instruction; generated metadata is a traceability record, not a digital
signature or model/mission approval. Existing proposal/evidence are preserved.
Profiles, cost agreement and execution evidence remain pending; no observations,
tasks, terrain, mock or mission execution were generated by this update.

## Concrete Jezero scientific proposal, 14 November 2026

OpenAI Codex assisted the proposed A/B/staging selection on Daniel's public
grid, mission service, resource allocations/reserves, rationale and sensitivity
records, the reproducible public-prior sizing tool and its consistency tests.
Generated numerical outputs are model diagnostics, not observations, planned
routes, executed tasks or scientific approval. Public terrain arrays and the
operational mission template remain unchanged. Exact affected paths are in
ai_usage.json; all new choices await David's review.

## Direct mission reconciliation, 14 November 2026

OpenAI Codex assisted resolving the mission/main documentation and validation
conflicts while preserving the latest journal/scenario implementation, existing
shared contracts and all contributor declarations. The repository owner
explicitly requested direct integration if permitted by branch rules. No branch
rule, hook or check is disabled; this is not authorization for future direct
merges. The planner PR and all other owners' implementations remain unchanged.
Retained checks are software evidence, not a validated mission or scientific
approval.

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

## Planner model conformance, 14 November 2026

OpenAI Codex assisted with the isolated published-source loader, synthetic
seven-case cost comparison, reproducible CLI, tests and technical report.
The generated numerical diagnostics are classified MODEL_CONFORMANCE; they
are not NASA observations, integrated missions or an A/B/C benchmark. All
profile approval states remain unchanged and authorization remains blocked.
Exact source/model/profile hashes are retained with the comparison.

## Frozen benchmark evidence tools, 14 November 2026

OpenAI Codex assisted with immutable protocol/outcome types, first-attempt
comparison reporting, filesystem/event/traversal evidence checks, draft
templates, audit CLI, regression tests and documentation. Synthetic test
fixtures exercise the auditor; they are not submitted mission outcomes.
The recorded draft-readiness diagnostic reports NOT_READY and zero observed
mission runs. Software validation logs/JUnit reports record actual command
outcomes and preserve source hashes; they grant no scientific approval.

## Public evidence recorder and sensitivity tools, 14 November 2026

OpenAI Codex assisted with the typed public execution recorder/exporter,
interval accounting and traversal closure checks, offline coefficient sweep,
illustrative sensitivity cases, regression tests and handoff documentation.
The disclosure metadata lists the affected files and retained software/model
checks. No ROS evidence input, planner change, physical observation, mission
execution or A/B/C outcome was generated. Model coefficients remain proposed.

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

The surface base model starts from the Blender file
`web/scripts/blender/source/base-marciana-v2.blend`, an AI-generated 3D model created by the
owner with OpenAI Codex outside this repository (owner-confirmed, 14 November 2026). `web/scripts/blender/prepare_base.py`, written with Claude through Claude
Code, removes its ground and rocks and adds a deterministic realism pass (dust vertex
colours, sandbag berms, radiators, comms mast, cables) to produce
`web/public/assets/models/base.glb`: flat colours, no textures, no AI image generator, no
agency marks. `web/public/replay/demo/atmosphere.json` holds values copied or
grouped (medians per 15° of solar longitude) from the public NASA Mars weather feed
(Perseverance MEDA at Jezero, Curiosity REMS at Gale; CAB outreach summaries) and the MSL
RAD surface dose rates published by Hassler et al. (2014); only
`web/scripts/extract-atmosphere.mjs` and the Atmos tab code were AI-assisted, and no value
is generated. The slope layer (`web/src/lib/slope.ts`), the solid-block display and the optional surroundings (`web/scripts/extract-ctx-context.mjs`, `web/src/components/ContextTerrain.tsx`) were written with Claude through Claude Code; their values are computed from or copied out of the CTX DTM and orthomosaic, none generated.
The viewer's `source_mode` handling (status chip, gateway package adapter)
was also written with Claude through Claude Code. So were the viewer's walk-cycle timing and foot planting
(`web/src/lib/astronautPose.ts`), the per-agent and base cameras with grab-to-drag and the
terrain clamp (`web/src/components/CameraBar.tsx`, `FollowCamera.tsx`, `MissionScene.tsx`),
the distance pins (`AgentLayer.tsx`) and the running crew dose estimate in the telemetry block
(`web/src/lib/atmos.ts`, `HudGauge.tsx`, `RadialHud.tsx`), which multiplies the published RAD rate by the replay
time and generates no value.

Not AI-generated: terrain heights (USGS Astrogeology / NASA), the astronaut model
by LasquetiSpice (CC BY 4.0, materials converted only), and the fonts (SIL OFL 1.1).
The viewer's details panel includes an AI-generated image: `web/public/assets/portraits/human_1.webp`, the
portrait shown beside astronaut human_1 in the viewer's details panel. It was generated
with ChatGPT (OpenAI) and supplied by the owner; it was cropped and resized with Pillow and
carries a visible `AI-generated` band burned into the image, legible at its 80 px display
size and in any capture. It is an illustration, not a photograph of a crew member or NASA
data, and contains no NASA logos, flags or mission marks. One AI-generated video is included: `web/public/assets/intro/mars-gods-eye-intro.webm`,
the skippable intro screen (5 s, project emblem, no NASA marks). It was generated with Kling
and supplied by the owner (the file's AIGC metadata names Kling as content producer) and is
used as supplied except for one discreet `AI-GENERATED · KLING` mark burned into the
bottom-right corner of every frame (ffmpeg overlay of a Pillow-rendered label, VP9
re-encode), so the mark stays in downloads and captures; it is the only mark, and the
viewer adds no second label over the clip.
Its audio track is treated as AI-generated and declared here and in the file metadata; the
viewer plays the clip muted. Machine-readable metadata:
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

## Real mission provider handoff, 14 November 2026

OpenAI Codex assisted with reconciling the published mission implementation and
current main, selecting one MOCK or real mission provider in the launch file,
configuration/clock preflight, consumer regressions, test discovery/import fixes,
and this handoff's documentation and validation records. Existing mission
models, task authority, planner and wire definitions are preserved. No profile
or model was promoted to scientific approval and no mission outcome was invented.
No generated image, video, audio or NASA observation is introduced.

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

## Planner branch synchronization proposal

OpenAI Codex assisted the local origin/main merge review, combined planner and
integration capability summaries and preserved the union of mandatory AI-use
declarations. At the owner's instruction, the ICD conflict is resolved as an explicitly
unapproved ground-start extension alongside the retained main consumer baseline.
Jesus and David review gates remain pending; no shared ROS type, scientific model
approval or operational authorization was changed by this review.

## Gateway typed serialization and source provenance

Claude Code (Anthropic) assisted the integration owner with the typed JSON
converters in the gateway store, their adoption by the ROS bridge and replay
recorder, the `source_mode` field in the gateway manifest, recorded manifests,
launch files and offline validators, the mock planner clearance correction,
the new unit/contract/integration test cases and the related documentation.
Test inputs are illustrative values and relabelled copies of the MOCK fixture;
no scientific dataset, mission result, image, video or audio was generated.
The affected paths are listed in ai_usage.json.

## Vertical on the public Jezero terrain

Claude Code (Anthropic) assisted the integration owner with the `terrain:=real`
selection in `vertical_mock.launch.py`, the placeholder Jezero agents file, the
end-to-end integration test and the related documentation. The test sends an
illustrative SIMULATED observation that repeats public prior heights; no
terrain array, scientific dataset, mission result, image, video or audio was
generated. The affected paths are listed in ai_usage.json.

## Main synchronization after viewer merge

OpenAI Codex assisted with the README and mandatory metadata conflict resolution
when main7ec1a06 was incorporated into the mission handoff. Mission and viewer
implementations, existing licence notices and both contributors' required
AI-use declarations were retained. The provenance test declaration follows its
move to web/tests. No new generated code, media or scientific data is introduced
by this synchronization.

## ROS CI fixture readiness after main synchronization

OpenAI Codex assisted with two test-harness corrections after ROS CI exhausted
its search limit and the mission fixture timed out. The terrain functional test
now has an explicit finite 10-second search budget; production defaults and all
feasibility assertions remain unchanged. The mission fixture probes the actual
canonical planner for a complete loaded map before submitting its one mission
goal, and retains diagnostic state on failure. No runtime policy, scientific
approval, observation or resource model is changed.

The authority smoke now scopes its synthetic grid to16x16 cells at the same
five-metre resolution through a test-only LaunchService wrapper around the
unchanged production LaunchDescription. Actual service providers, positions,
readiness/model checks and the default production200x200 grid are preserved.
This fixture is not a large-map throughput benchmark or a scientific dataset.

## PR11 reconciliation review

OpenAI Codex assisted preserving the real mission selector while merging the
terrain/provenance integration cut with main. Both launch preflights and all
existing disclosures remain; no scientific approval or media was generated.

## PR12 synchronization with mission and integration main

OpenAI Codex assisted the local main4b72d309 merge review, README and mandatory
AI metadata conflict reconciliation, and actual planner/mission consumer checks.
Both contributions and all source/licence disclosures remain. No operational
authorization, model agreement, new science data or ROS wire change is introduced.

The PR12 synchronization also adjusts the planner test helper import to the
package-qualified tests.planning path required by main's pytest importlib mode.
All assertions and the production planner remain unchanged. Linux HTTP test
dependencies were isolated under ignored tmp; no system Python or source
requirements were changed.

## PR12 planner technical-review corrections

OpenAI Codex assisted reproducing the ten observations in PR12 comment
6882884265 against the prior planner source, implementing the planner-only
corrections and synthetic regression tests, and updating the English model,
handoff and proposed ICD extension. Affected code: core.py, replan.py and node.py
under src/mge_planning/mge_planning; tests/planning continuous-start, D-07, kernel,
policy and test_pr12_review cases; tests/contract/test_planner_service.py opt-in
checks. The extension remains disabled by default in the ROS service. Shared
wire definitions and MissionManager were not modified or scientifically approved.

The descriptive audit is docs/pr12_review_corrections.md; the machine-readable
declaration is docs/ai_usage.json. evidence/planner-pr12-review-20261114 contains
actual test outputs, source hashes and synthetic reproduction outcomes; it does
not contain generated NASA observations, physical validation, images or audio.
Existing licence notices and mandatory disclosures remain intact. Human owner
review of these corrections, modelling choices and integration remains pending.

## PR12 simulated ground-Z fixture follow-up

OpenAI Codex assisted tracing ROS-default/omitted z values in two integration
fixtures and preparing test-only simulated initial conditions and regressions.
Affected paths: tests/integration/ground_fixture.py, test_terrain_batch.py and
test_vertical_terrain.py; tests/planning/test_simulated_ground_initialization.py;
docs/pr12_review_corrections.md and planner_handoff.md. Evidence is recorded under
evidence/planner-pr12-ground-z-20261114 with actual test outcomes and hashes.

The temporary MOCK agents configuration uses public prior values repeated in
explicit SIMULATED scene observations, retaining the declared public vertical
datum. It is not new scientific data, physical telemetry, evaluator reference or
a measured Mars surface. No elevation values were invented; copied values are
explicit SIMULATED inputs, not new NASA observations. No media was generated.
The actual ROS belief stays unknown until observation.
Planner safety guards, shared ROS definitions, runtime simulation/mission code and
recorder remain unchanged from the preceding audited corrections. Integration
fixture review by Jesus and scientific review by David are pending.

OpenAI Codex also assisted the owner-authorized local merge commit audit and its
included-file/validation metadata under the same evidence directory. Raw prior
test reports remain historical; this does not generate scientific observations,
approve models or add optional authorship/co-authorship credits.

## PR12 review corrections

OpenAI Codex assisted reconciling the planner branch with reviewed main, preserving
both sets of mandatory declarations, and adding reserve/goal/route-context guards
with regression tests. No scientific coefficients, ROS definitions, approval gates
or execution authorization were changed. Test results describe software checks only.

## Mission reconciliation with published main

OpenAI Codex assisted reconciling main `6ec9b84` into `feat/mission`, retaining
both sides' scientific and contributor declarations, namespacing mission tests
alongside planner tests, and adapting the mission validation snapshot to copy
explicit public inputs only. Other owners' implementations remain unchanged;
this merge grants no scientific approval or verified mission result.

## Persistent mission journal and scenario readiness

OpenAI Codex assisted the optional durable recorder/recovery, fault and audit
tests, the public scenario diagnostic/candidate exporter, CLI and tests, and
the related mission documentation and retained validation reports. Scenario
checks consume Daniel's existing observational public arrays unchanged; no
terrain, observation or scientific dataset was generated. Journal tests use
software fixtures, not submitted execution outcomes. Model conformance and
readiness outputs are diagnostics; proposed assumptions remain unapproved.

## Public raster recording

Claude Code (Anthropic) assisted the integration owner with the public raster
assembler and its use by the replay recorder, writer, offline validator and
contract oracle, the observed-mask layer in `mapping_node` and `mock_terrain`,
the unit and integration tests and the related contract documentation. Test
layers are illustrative values; recorded rasters are copies of the public
prior and of SIMULATED test observations, not new terrain. No scientific
dataset, mission result, image, video or audio was generated. The affected
paths are listed in ai_usage.json.

## PR12 remote publication reconciliation

OpenAI Codex assisted merging remote planner38ad692 and main7c16cd8 while preserving both histories, reserve/goal guards, prior corrections and mandatory disclosures. Documentation and software-test evidence are in planner_pr12_publication.md and evidence/planner-pr12-publish-20261114. Production mission, simulation, mapping, gateway and ROS definitions are retained from main unchanged; fixture/scientific integration review remains pending. No scientific observations or media generated.

## Team continuation planning

OpenAI Codex assisted drafting the owner-requested next-work plan and navigation
updates in AGENTS.md, team.md, mission_checklist.md and all five handoff guides.
The plan records human assignments, the Conciliación integration cuts, larger-map
feasibility, Fajardo's future NASA-criteria research and shared deployment work.
Publication usability is an explicit planning assumption, not new verification.
No runtime code, scientific criteria/results, terrain, observations or media were
generated. No scientific or operational approval is granted by these documents.

## MOCK kinematic execution

OpenAI Codex subsequently assisted the owner-requested PR17 timeout diagnosis,
callback scheduling fix in `mge_planning/node.py`, ROS concurrency and terrain
batch regressions, and integration handoff. Delayed callbacks and flat grids
are synthetic software fixtures, not scientific observations or mission results.
No imagery, scientific dataset or media was generated by this correction.

Claude Code (Anthropic) assisted the integration owner with the kinematic
execution core and executor node in `mge_sim`, its launch selection, the
unit, contract and integration tests and the related documentation. Paths,
estimates and observations in the tests are illustrative inputs; motion and
consumption derive from planner estimates and are not a model. No scientific
dataset, mission result, image, video or audio was generated. The affected
paths are listed in ai_usage.json.

## Integration test isolation

Claude Code (Anthropic) assisted the integration owner with per-module ROS
domain isolation and readiness waits in the integration test fixtures and the
related log entry. No data, mission result, image, video or audio was
generated. The affected paths are listed in ai_usage.json.

## Root README overview

Claude Code (Anthropic) assisted the integration owner in rewriting the root
README from a review of the repository, its branches and pull requests and the
merged web viewer: system overview, branch and PR state, viewer features,
launch arguments, gateway API, CI jobs and open milestones. The data
provenance table and the AI declarations already on main are kept unchanged.
No code, data, mission result, image, video or audio was generated. The
affected paths are listed in ai_usage.json.

## Replay recorder shutdown fix

Claude Code (Anthropic) assisted the integration owner in fixing a shutdown
race in the replay recorder: a signal now only asks the node to stop between
callbacks, the writer closes idempotently and a closed package is never
extended, with unit tests in `tests/unit/test_replay.py`. It also keeps planner
searches valid while other agent kinds complete the same map batch
(`mge_planning`, tests in `tests/planning/test_adapter.py`) and gives the MOCK
mission more time for the planner to assemble a new map version. No data,
mission result, image, video or audio was generated. The affected paths are listed in
ai_usage.json.

## Terrain script review corrections

Claude Code (Anthropic) assisted the repository owner in reviewing the
configurable region options of `scripts/prepare_jezero_terrain.py`: slope
screening limits now come from `config/planner_profiles.proposed.json` (still
pending model agreement) and the summary is labelled as an estimate, not
certified passage; `--sync-terrain-yml` is refused for a package outside
`data/sample`; an undocumented duplicate scale tier was removed; and offline
tests were added in `tests/mapping/test_prepare_jezero_terrain.py`. No terrain
data, observation, mission result, image, video or audio was generated.

## Viewer first-person view, drone scan and Pages publishing

Claude Code (Anthropic) assisted the viewer owner with the opening terrain
formation (the layer rises from flat zone by zone), the height morph between
layers and map versions, the first-person camera and its HUD (route guide,
minimap, optional sway), the interface entrance animation, the plain-text
descriptions of the viewer for language models (llms.txt, about page, page
metadata, window.mge.state()), the drone
camera scan, the rendering fallback for browsers without a usable GPU (a lite
3D tier and a 2D map without WebGL), the drone camera window, the first-person
power-on, dock and resource alert, the astronaut helmet lights, the sky (Sun
from Mars24, stars from the Yale Bright Star Catalogue with the IAU rotation
model of Mars, key light following the Sun) and the star-extraction script,
the first-person terrain scan (state machine, wave/indicator/footprint shaders,
scan key and synthesised sounds; inspired by Death Stranding's Odradek scanner,
no game assets), the drone window's Hazards tab (`web/src/lib/droneHazards.ts`,
`DroneMap.tsx`: steep cells and contradictions of the orbital prior read from the
replay's simulated observations, not LiDAR; it replaces the earlier survey map tab), the astronaut facing its walking direction, the photo directions of the rover tour (`photoAim.ts`) and the rover's real-camera rig and arm close-up (`roverCameras.ts`, `roverRig.ts`, `RoverCameraBar.tsx`; the field of view, focal length, focus range and stereo baseline numbers are NASA's or from the instrument papers, the mast slew and zoom speeds and the stowed arm pose are display assumptions, the deployed arm pose is solved from a NASA feed camera position), the Gale (Curiosity) world, the Gusev (Spirit), Elysium (InSight), Meridiani (Opportunity) and Valles Marineris (Melas) worlds and the zone selector, a Mars globe built from the Viking MDIM 2.1 mosaic tiles with real zone positions, a radially fitted card and a horizon from the Melas DEM (`extract-globe-tiles.mjs`, `extract-zone-horizon.mjs`, `zoneGlobe.ts`; the globe imagery and horizon heights are NASA data, not generated; the zone synopses are AI-assisted text summarising public mission facts; the travel transition fills the screen with the zone's orbital image and warps it onto the projected terrain footprint before fading into the scene, `arrivalQuad.ts`, display code only, the image is NASA data) (`extract-gale-crop.mjs`, `extract-dem-crop.mjs`, `extract-mer-traverse.mjs`, `make-demo-fixture.mjs`, `data/worlds.ts`, `ZoneSelector.tsx`, `scripts/data/<zone>/`, `public/replay/<zone>-demo/`; the terrain, imagery and Spirit/Opportunity stops, the real science sites used as POIs C and D (`extract-science-sites.mjs`, `scripts/data/<zone>/science_sites.json`) and every zone card image are NASA data from JPL Mars Trek, NASA/JPL and the PDS Geosciences Node, not generated; the astronaut sites (Three Forks depot from the PDS, `extract-three-forks.mjs`; science stop; habitat area by the NASA Exploration Zone slope criterion) are NASA data or a published criterion applied by an AI-assisted script; the water, ice and radiation context, documented only (`extract-zone-environment.mjs`, `scripts/data/zone_environment.json`; Mars Odyssey GRS water, the RAD Gale dose and, elsewhere, RAD's published dose-pressure relation applied to each scene's pressure, flagged outside its measured range; no ice value) is NASA data with an AI-assisted derivation; the science-POI dossier `docs/science_poi_dossier.md` was drafted with AI assistance from the cited sources and awaits David's audit; the mission story in each scene's timeline, routes and rasters is generated and simulated, as in the other demos), the minimap surroundings (`tacticalMap.ts`, `Minimap.tsx`), the rover photo tour (`make-demo-fixture.mjs` tour phase, `MarsNow.tsx` controls; generated simulated motion, labelled illustrative), the real Perseverance stop markers and the stop-image window (`roverStops.ts`, `RoverStopMarkers.tsx`, `extract-rover-waypoints.mjs`; the stop positions are NASA data, not generated), the expanded demo crop (landing area plus the earlier demo area, 8 m display grid) (`extract-ctx-crop.mjs`, `make-demo-fixture.mjs`; the terrain heights stay NASA/USGS data), the opt-in Perseverance raw-images panel
(`perseveranceRaw.ts`, `rawImagesStore.ts`, `RawImagesPanel.tsx`, and the first-person `MarsNow.tsx` window; the images are real NASA/JPL-Caltech files read
from the public feed on request, not AI-generated and not stored) and the site icons
(`siteKinds.ts`, `SiteIcon.tsx`, `SitesList.tsx`),
their tests, and the workflow that publishes the public viewer to
GitHub Pages. The scan only redraws the slope already computed from the orbital
CTX DTM prior around the drone in display bands; it is not an observation, it
does not change the map version, and its bands are display thresholds pending
science approval. No data, measurement, image, video or audio was generated.
The affected paths are listed in ai_usage.json.

## Team logo and link preview

The team logo (`web/public/assets/brand/mars-gods-eye-logo.webp`) was generated
with ChatGPT (OpenAI) and edited by the team. A band with a visible
`AI-generated logo (ChatGPT, edited)` label is burned into the image, and it
stays visible in the README and the about page. The link preview
(`og-image.jpg`) is the NASA/JPL/USGS Viking global color mosaic of Mars (PIA00407),
centred on black with Pillow (no text); it is not AI-generated (credits in
THIRD_PARTY_NOTICES.md). The browser tab icon
(`web/public/favicon.ico` and its PNG sizes) is an illustration of Mars made by
the team, not with AI; only its black background was removed and it was resized.
An earlier SVG icon drawn with Claude Code was replaced and is not shipped. None of these
images uses NASA logos, flags or mission marks or is presented as NASA data.

## Optional auxiliary NASA/USGS terrain layers and HTTP range optimization

Google Antigravity assisted the data and mapping owner with bounded HTTP 206
keep-alive/block-cache optimizations in `scripts/prepare_jezero_terrain.py` and
with a standalone auxiliary layer pipeline (`scripts/prepare_jezero_aux_layers.py`,
`src/mge_data/mge_data/core.py`, `src/mge_data/mge_data/node.py`, and
`tests/contracts/test_data_manifest.py`). The pipeline keeps `data/sample/terrain.npz`
and `data/sample/manifest.json` unchanged by default while producing separate,
cell-aligned auxiliary files (`jezero_aux_layers.npz`, `ctx_ortho.png`,
`geology.json`, `aux_layers_manifest.json`) derived via GDAL/rasterio and ArcGIS
REST from the official USGS Mars 2020 TRN MRO/CTX 6 m/px controlled orthomosaic
and USGS SIM 3464 geologic map. `data/sample/ctx_ortho.png` is a deterministic
north-up grayscale crop of the observational MRO/CTX orthomosaic, not an
AI-generated image.

## Proposal publication after reconciliation

OpenAI Codex assisted publication of the local scientific patch/campaign proposal,
reconciliation of both AI registers with main9198b3d and fresh software checks.
All prior disclosures/media metadata are retained; approvals remain unchanged.
Evidence: evidence/mission-proposal-publication-20261115.

## F03.3 main-only resource audit

OpenAI Codex assisted reading only published main c58e7f6, comparing existing search/science cost APIs, constructing explicit synthetic characterization tests and documenting the audit. Paths: docs/planner_f033_resource_audit.md and evidence/planner-f033-audit-20261114. Production code, coefficients, MissionManager and ROS contracts were not modified. Existing public main profile values were consumed unchanged; no scientific measurements or media generated. Test passes confirm existing discrepancies and do not approve model equivalence or physical execution.

## F03.3 remaining-availability guard

OpenAI Codex assisted the planner-only availability admission guard and human/rover regressions based on published main0339bbd, plus MODEL/handoff/audit updates and actual test evidence. Paths: src/mge_planning/mge_planning/replan.py; tests/planning/test_f033_resource_guard.py; src/mge_planning/MODEL.md; docs/planner_handoff.md; docs/replan_policy.md; docs/planner_f033_resource_audit.md; evidence/planner-f033-guard-20261114. No search/science formula, ROS field or MissionManager change, scientific observations or media generated. The previous numerical audit and disclosures were backed up and preserved. New mission/authorization, restart and replenishment decisions remain integration responsibilities.

## F03.3 delivery review

OpenAI Codex assisted the mainb5dc681 delivery comparison, local commit/PR drafts, fresh software validation evidence and a separate local-only future cost-backend proposal. Evidence is under evidence/planner-f033-delivery-20261114. The proposal is not implemented or included in the guard payload. ROS startup failures and previous hash-matched ROS results are explicitly distinguished. No publication, model change or scientific observation is produced by this preparation.

## F03.3-B experimental cost adapter

OpenAI Codex assisted planner resource_costs.py, test_resource_costs.py, the F03.3-B technical report and evidence/planner-f033b-20261114. The adapter reuses published mission functions; tests compare stored David vectors. Outputs are software estimates, not observations or model approval. Search, MissionManager and ROS remain unchanged.

## F03.3-C independent oracle

OpenAI Codex assisted tests/planning/scientific_oracle.py, test_scientific_oracle.py, docs/planner_f033c_oracle.md and evidence/planner-f033c-oracle-20261115. Tiny synthetic graphs and clearances are test inputs, not physical data. Costs delegate to published mission functions. Production search, ROS and authorization remain unchanged; PR28 coordination metadata was read without copying its implementation.

## F03.3 main synchronization and review preparation

OpenAI Codex assisted reconciliation of mandatory disclosures and preparation of the review PR. Current software validation outputs are retained in evidence/planner-f033-pr-sync-20261115. Both branches disclosures are preserved; no scientific measurements, production backend activation or operational approval are inferred. Native ROS is blocked before execution by WSL resources.

## Private-browser replay check

Claude Code (Anthropic) assisted the browser check script
`evidence/web-private-replay-20261115/reproduce_private_replay.mjs`, its
evidence record and the matching README wording. The script reads the built
viewer and the existing recorded package; it generated no mission data,
observation, measurement, image, video or audio. Its outputs are software
check results, not an AC-08 acceptance.

## PR36 raw-image acquisition provenance correction

OpenAI Codex assisted the owner-requested correction of shared image-query
identity in `web/src/lib/rawImagesStore.ts`, its consumers in `App.tsx`,
`RawImagesPanel.tsx` and `MarsNow.tsx`, and the raw-image regression tests.
The tests use synthetic feed fixtures and jsdom, pinned as a development-only
dependency. No NASA image, observation, mission result or media was generated.
This software correction does not approve scientific models or close mission,
replay or submission acceptance.

## PR36 zone-selector fallback correction

OpenAI Codex assisted the owner-requested WebGL allocation fallback in
`web/src/components/ZoneSelector.tsx`, its App tier binding and fallback styles,
the jsdom navigation regressions, and the validation record under
`evidence/pr36-viewer-regressions-20261115/`. The tests and browser checks are
software evidence; no image, video, NASA observation or mission result was
generated. Existing asset declarations and watermarks remain intact. This cut
does not close AC-08, steps 4/5, scientific approvals or organizer endorsement.

## Zone water and radiation display and project page text

Claude Code (Anthropic) assisted the display of the existing per-zone water and
radiation context (`web/src/lib/zoneEnvironment.ts`, the Atmos panel and zone
cards, with tests) and the English project-page draft `docs/project_page.md`.
The values come unchanged from `web/scripts/data/zone_environment.json` (Mars
Odyssey GRS, MSL RAD, Guo et al. 2018); the 4 h Marswalk dose is a linear
display estimate without shielding or solar particle events. No image, video,
audio or NASA observation was generated; scientific review of the wording and
organizer endorsement remain open.

The same assistance added the HUD's exhaled-CO₂ gauge (`web/src/lib/co2.ts`, the second
press of the oxygen button, with tests): a display estimate from the replay's oxygen line
and an assumed respiratory quotient of 0.85, pending scientific review; no CO₂ data or
suit capacity is generated. It also switched the HUD dose gauge to each zone's surface
rate from the existing zone environment data, with NASA's 600 mSv career limit as scale
context; no dose value was generated.

It also assisted the read-only live gateway panel (`web/src/lib/gatewayLive.ts`,
`web/src/components/LiveGatewayPanel.tsx`, `web/tests/gatewayLive.test.ts`) and its check
against a running MOCK ROS stack in WSL. The tests use synthetic gateway envelopes; no ROS
output, NASA observation or mission result was generated, and the panel labels a MOCK stack
MOCK.
The fixed *Offline* link headline in the top-right status (`web/src/components/Frame.tsx`) was
removed, since the panel already shows the connection; that status now describes only the replay.
An *Exit photo tour* button (also Esc) in the rover HUD (`web/src/components/FirstPersonHud.tsx`,
`web/src/App.tsx`, `web/tests/photoTourExit.test.ts`) leaves the photo tour from anywhere; it
changes no data.
The gateway panel was then reduced to one thin line at the top of the status column (where
*Offline* used to be) with a dropdown for the details (`web/tests/liveGatewayPanel.test.ts`, synthetic
MOCK state), so it no longer covers the map.

## PR37 scientific presentation corrections — 15 November 2026

OpenAI Codex assisted the HUD/context code, source-year corrections, project-page draft and regression tests listed in `ai_usage.json` under `pr37_scientific_presentation_corrections`. RAD dose equivalent is not converted into NASA effective dose or a career-limit percentage. An unavailable CO2 rate remains unavailable. No new measured data, numerical radiation inputs, scientific profile or approval was generated. Owner scientific review remains pending.

## PR38 auxiliary-context reconciliation — 15 November 2026

OpenAI Codex assisted strict DEM/metadata/hash/path and public-array validation, bounded HTTP Range handling, synthetic regression fixtures, a ROS consumer test, and the auxiliary visual-context contract. The complete file scope is registered in `ai_usage.json` under `pr38_auxiliary_context_reconciliation`. Acquired imagery/geology/NPZ bytes were preserved; interpreted DN/slope categories are estimated visual proxies without navigation authorization. No new scientific parameter, measured observation or approval was generated.

## Height contract reconciliation — 15 November 2026

OpenAI Codex assisted the initial-condition resolver, executor XYZ guards, immutable planner metadata binding, shared rendered-triangle sampler and regression tests listed in `ai_usage.json` under `height_contract_reconciliation`. New scene heights are explicitly SIMULATED initial conditions derived from the declared public prior, not measured observations. Historical packages are retained unchanged. New recordings and browser captures preserve MOCK/REPLAY and required marks; no scientific approval, physical validation or complete three-agent mission is asserted.

## Height-corrected software recovery recording — 15 November 2026

OpenAI Codex assisted recording workflow, new URL-entry integration, tests and audit receipts for `height-recovery-20261115-01` / `recorded-recovery-002`. The exact MOCK recording includes AI-assisted code and a deterministic SIMULATED observation, not new observational NASA data. Its scene initialization parks the drone; the human alone executes stop/replan/return. File scope and evidence are registered as `height_recovery_recording_and_presentation`; source/pose identities and historical package bytes are preserved. Capture/edited media retains visible labels and metadata.

## Final delivery candidate reconciliation — 15 November 2026

OpenAI Codex assisted local integration of PR37/PR38 and the height/replay cut, structured conflict resolution preserving both mandatory disclosure histories, a trailing-blank-line correction and delivery handoff documentation. Registered as `final_delivery_candidate_reconciliation`. Actual checks, deferred work and human gates are distinguished in `final_delivery_candidate.md`; no automatic main merge, physical validation or external submission was performed.

## Same-run browser video — 15 November 2026

OpenAI Codex assisted Chrome capture/edit scripts, English overlays/subtitles, metadata and technical review for `web/public/media/height-recovery-002.mp4`. The actual viewer replays the exact MOCK software run; the edit does not generate NASA observations or mission telemetry. Visible `AI-generated edit | SIMULATED | NOT LIVE` and existing portrait marks remain readable. Capture metadata locks viewerf7938f5, execution742eed5 and all four recorder files. No image-generation model or NASA branding was used to create the capture/edit. Third-party source terms remain; raw frames/browser profiles/caches are excluded. Final owner merge, organizer endorsement and submission approval remain pending.

## PR39 read-only gateway contract reconciliation — 15 November 2026

OpenAI Codex assisted client envelope/payload validation, session recovery, contiguous event cursors, separate mission/terrain versions, regression tests and public status documentation. The exact file scope is registered as `pr39_gateway_contract_reconciliation`. The bounded HTTP/WebSocket consumer evidence uses the actual unchanged gateway with public recorded-recovery-002 inputs, explicitly replay-fed MOCK. It sends no goals and performs no ROS mission execution or scientific acceptance. No recorded package, measured NASA observation, generated media or shared contract was changed. Existing contributor declarations and mandatory watermarks are preserved.

## Viewer terrain shape and zone menu — 15 November 2026

Claude (Anthropic) through Claude Code assisted a viewer fix registered in `ai_usage.json` as `viewer_terrain_shape_and_zone_menu_fix`: the updated-map layer keeps the ground shape of the run's last public map version from the start (no sudden rise of observed ground near the agents), while observed-cell tints and uncertainty still follow the current map version; the zone menu opens on the Jezero card. Code and tests only; no data or observations were generated.

## Crop-edge margins in the demo generator — 15 November 2026

Claude (Anthropic) through Claude Code assisted generator changes registered as `demo_generator_crop_edge_margins`: simulated agents no longer drive along the edge of the terrain crop (Meridiani's base and pads sat 4-12 m from it; Jezero and Gale photo tours ran 4 m from it). The regenerated Jezero, Gale and Meridiani packages remain SIMULATED stories on NASA terrain; rover stop markers keep their real NASA positions, and edge stops are visited from up to 20 m inside, as stated in the tour event. No observations were generated.

PR39 refresh against main798016e preserves the concurrent terrain/menu/crop fixes and combines its per-zone photo-tour title with the reviewed exit handler. OpenAI Codex assisted this narrow conflict resolution; no scene, recording or scientific value was generated by the refresh.

The same PR39 refresh restricts final-story terrain geometry to explicitly illustrative SIMULATION scenes, with a shared stable shape for belief/sigma. Recorded and unknown-source runs keep current-version geometry; no future observation is displayed early. The exact recorded002 cell regression and NoData/layer checks are software tests, not generated NASA measurements.

## PR42 delivery integration continuation — 15 November 2026

OpenAI Codex assisted the metadata/hash continuation and read-only native Wiki verification registered as `pr42_delivery_integration_reconciliation`. The owner explicitly approved PR39/42 merge and native synchronization; native82534db was already published with recorded authorization and is preserved. All39 media match the reviewed edition and18new endpoints return HTTP200. Preparation-time editorial flags remain historical; this continuation does not confer scientific-model, mission or final-delivery acceptance. No new media or observations were generated.

## PR44 late-event stream reconciliation — 15 November 2026

OpenAI Codex assisted a minimal gateway event-stream correction, four real WebSocket regressions, actual-client validation and review handoff registered as `pr44_late_event_stream_reconciliation`. The original high-water filter lost a unique event2 after event3; a fixed resume floor plus emitted-sequence set preserves late events and deduplicates backlog/queue overlap. Tests use synthetic envelopes or the existing public MOCK replay, not new NASA observations or a new mission. Original contributor history, declarations and schema1.0.0 are retained. Final owner merge approval and organizer endorsement remain separate gates.

## Live bar and run selector — 15 November 2026

Claude (Anthropic) through Claude Code assisted the viewer changes registered as `live_bar_and_direct_run_switch`: the read-only ROS gateway bar is always shown, disconnected (and never contacting a server) when the page has no `?gateway=`; a run chosen in the run selector opens directly instead of returning to the intro and zone menu. Code and tests only; no data, observation or live mission is claimed.

## Paired fixed and adaptive analytical study — 15 November 2026

OpenAI Codex assisted the experimental consumer, seeded synthetic mission records, statistical protocol and analysis, independent bookkeeping audit, English explanation and numerical plots in `evidence/rigid-adaptive-study-20261115` and `docs/wiki/10-Adaptive-Planning-Study.md`. The archive includes the exact experimental code and meaningful verification tests without activating it in production paths. The source and result manifests identify tool use, SIMULATED status, seeds, input/module hashes and publication provenance. Every new plot retains a visible `AI-generated | SIMULATED` label.

The records are analytical experiments on public CTX terrain with explicitly hypothetical perturbations and public simulated mission notices. They are not observational NASA data or verified LIVE execution. Published planning and science code is consumed at the declared SHA; this publication changes no shared contract, operational approval, production implementation or scientific coefficient approval. The experimental archive includes mandatory AI declarations as metadata and prose, with no optional authorship credit.

## README scientific synthesis — 15 November 2026

OpenAI Codex assisted the English scientific synthesis in `README.md`: the research question, terrain/model explanation and balanced summary of the already published fixed/adaptive study. The numerical claims retain the PR47 source catalogues, nominal empirical resampling intervals, separate batch denominators and existing approval states. This edit generates no new experimental results, media, profile values or production code. Existing AI declarations and marked assets are preserved.

Documentation-only preparation and verification helpers are retained locally under `.local/readme-science-update`; their use is recorded in the machine-readable entry.

## Operational scientific cost integration — 15 November 2026

OpenAI Codex assisted the native scientific-cost search integration, typed immutable planning context, real ROS producer/consumer, compatibility migration, regression tests and this documentation. `docs/ai_usage.json` lists every affected delivered path. The existing scientific formulas and profile coefficients are reused; their approval status is unchanged. Declared synthetic maps support software/model tests, not new NASA observations or physical mission completion. Original evidence and all previous AI declarations remain intact. Local preparation and verification helpers are recorded as internal provenance.

The executed reports, source fingerprints and real-service JUnit record are retained under `evidence/scientific-cost-integration-20261115`. Their values come from the actual scientific search, explicit legacy control and ROS service calls; AI assisted orchestration, metadata and explanation. Both reports retain blocked operational authorization because numerical consistency does not grant scientific coefficient or mission approval.

## PR49 Gazebo integration corrections — 15 November 2026

OpenAI Codex assisted the corrections registered as
`pr49_gazebo_integration_corrections` in `docs/ai_usage.json`: physical-rover
execution guards, measured odometry/stop feedback, coherent scene-sensor
confirmation, immutable recorded obstacle masks, the opt-in MOCK Gazebo launch,
regression tests and this handoff. The exact modules and tests are listed in the
machine-readable declaration. Test scenes and observations are explicitly
synthetic/SIMULATED; runtime checks are experimental software evidence, not NASA
measurements, scientific approval or validated LIVE execution. No image, video
or audio asset was generated in this correction cut. Existing third-party
attributions, disclosures and required media watermarks remain intact.

## MOCK budget fallback and obstacle fields — 15 November 2026

Claude (Anthropic) through Claude Code assisted the changes registered as `mock_mission_budget_fallback_and_obstacle_field`. The MOCK mission gains an opt-in `budget_fallback` (off by default): when the goal in force no longer fits the remaining allocation it tries nearer targets on the base-goal line and then the base, without lowering reserves or re-allocating consumed resources. Goals and bases outside the terrain grid are rejected (`OUT_OF_MAP`). `mge_sim.obstacle_field` generates deterministic SIMULATED obstacle fields (a ridge with one gap and seeded rock clusters) that keep a passage from base to goal. The recorder adds an optional `impassable` cell list per map version to the public raster attachment, taken from the mapping's human traversability mask, and the viewer draws those cells as cosmetic rocks with a rust tint; rock sizes and turns are display only. An opt-in `scene_sensor` node reports a declared SIMULATED scene around the agents (a drone on landing, ground agents as they walk), and an opt-in `complete_on_return` closes a MOCK goal once its agent is back at base. Viewer rocks follow the Golombek-Rapp size law with each blocked cell's main rock deliberately enlarged to 1.5 m for readability, styled by the cell's USGS SIM 3464 unit. A Gazebo Harmonic world generator (`gz_world`) and pose mirror (`gz_mirror`) show a run on the public terrain with the scene's rocks; the terrain tint, grain, normal map and rock shapes are cosmetic, and mirrored agents are only shown; a later addition drives one physical rover in Gazebo along the authorized route (heightmap aligned with the planner cell centres, one constant vertical datum offset measured at rest) and draws the web viewer GLB models at their true sizes. Code and tests only; the obstacle fields are synthetic test scenes, never NASA observations, and no run is a validated LIVE mission.

## Owner-supplied slower Wiki animation — 15 November 2026

OpenAI Codex assisted copying and verifying the owner-supplied slower `docs/wiki/assets/prior-observation.gif`, with no image edits. The three displayed stages total 7.5 seconds instead of 4.2 seconds. The existing visible `AI-generated | Conceptual simulation` watermark is preserved. The current asset manifest and `docs/wiki/audit/slower-prior-observation-20261115.json` record the new hash and timing; historical publication/editorial seals retain their original dated scope. No scientific results or technical implementation changed.

## Simulation time source (D-CLK-01) — 15 November 2026

Claude (Anthropic) through Claude Code assisted the change registered as `simulation_time_source_contract` in `docs/ai_usage.json`: the `vertical_mock.launch.py` preflight that now requires exactly one external, advancing `/clock` whenever `use_sim_time:=true` (MOCK or real mission), its contract tests, the ICD section 2 clarification and the D-CLK-01 decision record. No ROS message, service, unit, enum, replay or raster version changes. No data, image, video or audio was generated, and no run is claimed as LIVE or physically validated. Existing declarations, attributions and watermarks are unchanged.


## Historical planner disclosures retained during reconciliation

These records describe historical commits, not the current operational backend.

## F03.3-C2 immutable Python scientific context

OpenAI Codex assisted ScientificContext in resource_costs.py, tests/planning/test_scientific_context.py and docs/planner_scientific_context.md. Published science functions and profile coefficients are reused unchanged. The explicit immutable context is experimental, has no ROS transport or authorization and does not approve profiles. Test terrains are synthetic inputs.


## F03.3-C2 local opt-in scientific search and replanning

OpenAI Codex assisted core.py and replan.py experimental context integration, tests/planning/test_scientific_search.py and test_scientific_replan.py, MODEL/handoff/local technical documentation and evidence/planner-f033c2-local. Costs reuse the published science API; graph/raster fixtures are synthetic. Evidence records actual local software results and computational timings, including the corrected pytest helper-name error. No ROS activation, production node wiring, coefficients, mission authority or scientific approvals were changed. No GitHub publication is part of this cut.


## F03.3-C2 local final admission and performance audit

OpenAI Codex assisted the minimal replan.py admission-order correction, tests/planning/test_scientific_admission.py and test_scientific_benchmark_protocol.py, scripts/benchmark_scientific_planner.py, planner MODEL/handoff/audit documentation and evidence/planner-f033c2-audit-local. The before-fix failures and actual local software measurements are retained. Public Jezero data and source uncertainties were loaded unchanged; the secondary synthetic D-07 control reuses existing inputs. No observation, coefficient, MissionManager, ROS contract, production activation or scientific approval was generated. No GitHub publication is part of this cut.


## MVP-PL-01 local planner consumer validation

OpenAI Codex assisted tests/planning/test_mvp_mission_consumer.py, docs/planner_mvp_pl01.md, the planner handoff and evidence/planner-mvp-pl01-local. The tests join the actual Python planner and MissionManager using an explicit test-only translation and synthetic grid/telemetry; test-local illustrative flags exercise the independent numerical audit without granting approval. Evidence records actual software outcomes and limitations, including environment failures. Production implementations, scientific coefficients, ROS interfaces and the frozen delivery revision are unchanged. No scientific observations, executed physical mission, media, runtime science activation or publication are generated by this cut.


## F-TERRAIN-01 local diagnostics

OpenAI Codex assisted terrain_diagnostics.py, test_terrain_diagnostics.py, planner_terrain_mobility_review.md and evidence/planner-terrain-local. All new terrain and paired jump samples are explicitly synthetic analytical fixtures. Diagnostics do not authorize routes or alter production admission, profiles, science equations, mapping, public data or ROS. Computation timings are local software measurements, not physical mobility validation.


## F-TERRAIN-02 synthetic local-surface experiment

OpenAI Codex assisted local_surface.py, test_local_surface.py, planner_terrain_mobility_f02.md, planner handoff and evidence/planner-terrain-f02. Analytic synthetic grids and explicit trial parameters exercise the unchanged A* on a fine raster. All outputs are software estimates and diagnostics, not Mars observations or physical certification. No production default, shared core, scientific coefficients, MissionManager, ROS, public data or frozen delivery revision is altered.


## Local planner reconciliation
Codex assisted conflict reconciliation preserving the published scientific backend and historical disclosure records; no scientific coefficients or interfaces changed.


## Local terrain contribution 1
OpenAI Codex assisted add conservative terrain mobility diagnostics. Affected code/tests: src/mge_planning/mge_planning/terrain_diagnostics.py, tests/planning/terrain_fixtures.py, tests/planning/test_terrain_diagnostics.py. Synthetic fixtures only; no physical certification, coefficient approval or operational activation.
