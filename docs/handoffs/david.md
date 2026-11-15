# David - retain scientific mission authority and approve the model

## Audit reconciliation rc.2 — current candidate over main6bcf208

Read the [current gap/evidence matrix](../audit_reconciliation.md) and
[cost/context/interval proposal](../audit_cost_execution_gaps.md). PR25's cost,
duration and success packet is already integrated; do not duplicate it. New
main6bcf208 comparison again gives 1 agreement / 6 disagreements and BLOCKED
authorization. Next deliverable with Diego/Jesus: select the cost backend and
immutable request context, then bind evidence-backed service progress and the
existing scientific recorder. Review experimental exploration limits separately
from model/profile approval. Actual accepted/rejected optional work and three
executed roles remain pending; the featured READY/MOCK replay does not close them.
Scientific target/purpose work is excluded from this reconciliation and remains
in the owner's other chat. Historical inventories below retain their dated scope.

## Current continuation — 14 November 2026, main 5ab1387

Follow [CONT-DAV-01..04](../team_continuation_plan.md#david--mission-authority-and-scientific-acceptance):
agree executable scenario/costs and drone scope with Diego/Jesús; bind evidence
and outcome criteria; review Fajardo's NASA-criteria dossier and Daniel's
larger-map feasibility; freeze experiment metrics before comparisons. The plan
includes dependencies, acceptance and organizer reminders. Historical inventories
below retain their original cut; they do not supersede this next-work allocation.

Active branch: **`feat/mission`**. Audited head: `cf292107277e1aaf130d6c0ecd33904a22638f4f` (scientific mission authority). This head is unchanged at the final refresh. Main `004b3b2` now includes
Diego's real planner externally via PR #2; Jesus's latest integration branch
already tests it behind MOCK mission/terrain. Existing handoff is `docs/mission_handoff.md`; also read `docs/science_models.md`, `docs/science_benchmark.md`, `docs/science_decisions.md` and the retained mission validation/model-check evidence on that branch. Continue its actual manager, models, adapters and tests rather than the main scaffold.

Read [AGENTS.md](../../AGENTS.md), [ICD](../ICD.md), [contract baseline](../CONTRACT_BASELINE.md) and [integration matrix](../INTEGRATION_MATRIX.md) before editing. Canonical ROS fields/types live in `src/mge_interfaces/msg` and `srv`; preserve them and adapt representations explicitly.

## Owned implementation and scientific policy

Own `src/mge_mission/`, `config/agents.yaml`, `config/mission.yaml`, proposed science/planner profile registries, mission tests, science decisions and A/B/C protocol. Preserve immutable profiles, activity/grade estimates, idempotent goals, ordered events, remaining allocations, return priority and task evidence. Your primary role is scientific direction/validation, not implementing all five fronts. Do not replace Diego's advanced planner with another A*.

MissionManager is the sole authority for primary goal, survey -> inspect -> sample precedence, capability assignment, optional eligibility, risk/uncertainty/ resource rejection, return priority and the single authorized active route.

Consume canonical SetMissionGoal/AgentState/TerrainMeta/RouteDecision; publish MissionState/MissionEvent and active Path. Candidate FEASIBLE is necessary but insufficient: verify current run/map/pose, full return, reserves and agreed model/profile. A changed map clears old route ID and active path before new planning; Jesus must verify the execution consumer's separate stop acknowledgement. Preserve NON_CELL_CENTER from unchanged continuous input; never snap poses.

## Model agreement, evidence and remaining bindings

Keep `mge-science-1.0.0` as the scientific itinerary audit authority pending your explicit coefficient/profile approval. Proposed source profiles and a projected planner configuration are separate approvals. Projection status `pending_model_agreement` must block route authorization. Distance/slope rates and activity/grade/climb models are not equivalent by parameter conversion. With Diego, identify shared speed/geometry/budget fields and every persistent mathematical difference. Compare flat, uphill, downhill, service, waiting, zero-length, outbound/return and boundary-budget itineraries across all kinds. Retain the current audit tolerances (relative 1e-5, absolute 1e-3) unless a reviewed change establishes stronger justified values; agreement needs numeric checks plus exact model/configuration identity, not numbers alone. Record model ID/config SHA-256 and profile approval in run metadata because ROS wire fields do not carry that identity. No message change is justified solely for convenience.

Human oxygen means equivalent ideal dry O2 litres at 273.15 K and 101.325 kPa in the proposed model; capacities/reserves must use the same definition. Nonhuman oxygen is absent internally, NaN on ROS and null in JSON. Experimental budgets are not certified EVA limits. Preserve uncertainty/missing-input gates.

Discovery, work completion and traversal evidence have Python boundaries but no agreed operational ROS input. Bind them with Jesus explicitly; do not infer completion from a route or animation. The initial active-path publisher controls the primary human; optional robot assignments do not prove robot execution. Daniel owns public observations and isolated evaluator reference. Controlled planner mocks are allowed only for deterministic interface tests, never science acceptance or demonstrated mission completion.

## Synchronize without losing existing work

After saving/reviewing local edits, use the existing worktree for this branch:

```sh
git status --short
git fetch origin --prune
git switch feat/mission
git pull --ff-only origin feat/mission
git log -1 --format=fuller origin/main
git diff --stat origin/main...HEAD
git diff origin/main...HEAD -- src/mge_mission tests/mission config docs/science_decisions.md
git merge origin/main
```

If the branch is not local, use `git switch --track -c feat/mission origin/feat/mission` instead of switch/pull. Do not switch it if another worktree already has it checked out. Merge main only while on your owned branch. Stop to reconcile any shared-contract conflict with Jesus and the producer/consumer owners; preserve both implementations and never force-push. This reconciliation becomes the main contract only after its PR is merged. Before that, review it as a proposal and do not claim it is published in main.

## Tests and actual planner consumer

First run `python -m pytest tests/mission`. Keep model formula/input checks, mission idempotency, route/state invalidation, task precedence, capabilities, return priority and reserve rejection tests. Run `python scripts/check_mission_models.py --run-id NEW_RUN --output-dir evidence/NEW_RUN` in a fresh evidence directory; its synthetic MODEL_CHECK is not an A/B/C run. After baseline merge run `python -m pytest tests/contract/test_baseline_guards.py tests/integration/test_provider_substitution.py`.

On Jazzy use the branch's `scripts/validate_mission_ros.sh`/documented ASCII-path workspace when the Windows path prevents ROSIDL generation, then run `python3 -m pytest tests/contract/test_mission_service.py`. Existing reports verify a controlled planner, not Diego's actual numerical model.

With Jesus/Diego, replace that controlled provider by the real PlanRoute server without changing the MissionManager consumer. Demonstrate accepted agreed full itinerary, MODEL_MISMATCH, NON_CELL_CENTER, stale result, return-reserve rejection, map-change invalidation and separate execution acknowledgement. Retain exact sources/configs/data hashes and rejected runs.

The final integration log's callback/search-limit findings belong to Diego and
Jesus; numerical model approval does not resolve them. Existing feat/ux now
plays the recorded MOCK gateway package, but neither that replay nor the MOCK
mission proves that your real manager and planner model agree.

## Acceptance and next delivery

First deliver reviewed profiles, documented model equivalence/conservative limits, explicit tolerances and model/configuration run identity. Then freeze success criteria and A/B/C inputs/metrics/seeds before collecting comparison runs. Maintain primary completed AND return in tolerance AND verified ground traversal under model AND no budget violation; a correct BLOCKED rejection is not mission success. Bind execution/discovery inputs with Jesus and approve scenario/grid assumptions with Daniel. Deliver an incremental mission PR; full mission acceptance needs real cross-module execution evidence.

## PR and handoff evidence

Include the tested source SHA, baseline/schema versions, dataset/run/map IDs, model/configuration hashes where relevant, exact commands/outcomes and links to immutable evidence. Name any MOCK provider and all skipped checks, with reasons. Run `python -m pytest`, `python scripts/check_repository.py`, and the frontend `npm ci`, `npm test`, `npm run build` where available, using `web/.nvmrc`. On Ubuntu 24.04/Jazzy, build with `colcon build --symlink-install`, source `install/setup.bash`, inspect the six messages/two services and run the ROS contract/integration tests. A Windows skip is not a passing ROS test.

Review `git status`, `git diff` and `git diff --check`. Keep commits atomic and English Conventional Commits; preserve Git identity, third-party rights and mandatory AI usage text/metadata/watermarks. Update `docs/AI_USAGE.md`, `docs/ai_usage.json` and your handoff. Do not upload secrets or evaluator data.
Jesus reviews integration; David approves scientific assumptions/success.
Software tests, replay and synthetic fixtures do not establish a validated
LIVE mission. No push, merge or release is implied by this handoff alone.

## Continuation packet: costs, durations and success evidence

Current isolated mission baseline: `09d7d6a`. Read-only comparison used main
`2f50ae697b34fe82e575b386936d0d5e4d74db64` and planner
`69101e983c9a9668ba852460c484b5db8f12a1a5`. This continuation does not merge
their producer/executor changes or modify planner, data, mapping, simulation,
gateway, viewer or wire contracts. The older audited heads above remain
historical context, not a claim that those branches have stopped advancing.

The publication recheck fetched main `9614816081acc7779e6a565f5f4ebad8b0bd5287`
(viewer PR #19). Its delta from the reviewed main affects viewer/assets and
related documentation, not planner/data/simulation/interfaces or D-EST-01.
Planner remains `69101e9`; integration remains `c42ca24`. No merge is performed.

- Review the [cost packet](../cost_agreement_handoff.md) and
  [machine-readable contract](../../config/cost_agreement.experimental.json).
  The export contains 38 base vectors and seven activity-duration cases,
  preserving directed return, service/wait separation, current remaining
  resources, reserves and exact model/profile/configuration hashes. No planner
  substitute or new mock is introduced.
- The published planner comparison is one agreement / six disagreements,
  authorization BLOCKED. In particular the approved 120 s human light-work
  service differs from the projected fixed heavy-work service power. Preserve
  MODEL_NOT_AGREED/MODEL_MISMATCH; finite examples alone do not prove global
  model identity. Diego must consume the scientific API or establish reviewed
  equivalence and agree activity/wait identity bound to run/request context.
- David requested the [duration source review and pilot](../activity_duration_research.md)
  before asking Diego and Jesús to incorporate timings. The 30/60/180 s lunar
  model primitives are not complete sample cycles. Approximately 600 s for a
  documented D-RATS sample informs a proposed mixed workflow; its 420/180 s
  phase split is an engineering assumption. A 300 s inspection is likewise
  pending, not a measured NASA average. No new duration is approved.
- The additional 600 s mixed workflow plus the unchanged primary probe exceeds
  all three human usable budgets: 1001.12 s / 110.10 Wh / 22.48 L against
  960 s / 80 Wh / 20 L after reserves. Extra optional travel is excluded.
  Preserve the approved JZ-P01..07 configuration, including the 120 s check-in
  and 180 s sampling example, until an explicit scenario revision is approved.
- The [success contract](../mission_success_contract.md) and
  [criteria JSON](../../config/mission_success.experimental.json) are prepared,
  not runtime acceptance. The present manager's Boolean completion input does
  not prove 120 s of service or unfinished-work progress; the reviewed executor
  averages route costs into movement rather than implementing stationary
  service/wait. Jesús owns the producer contract. Await public task/traversal
  inputs and implement only the agreed mission consumer. Arrival, animation,
  stop acknowledgement and a calculated route are insufficient evidence.
- Honor main's D-EST-01 distinction between valid estimated prior, NoData and
  verified execution. Do not fabricate observations or lower uncertainty to
  obtain a path. Daniel/Diego own coordinated estimated-planning implementation;
  the proposed next-segment execution hold/inspection policy needs Jesús review.

Retained commands, results, source versions and configuration hashes belong
under `evidence/mission-cost-closure-20261114/`: `conformance`, `vectors-final`,
`pilot-final`, `readiness` and `validation`. Initial vectors/pilot are analytical
diagnostics from an earlier worktree snapshot. Consult the validation record
for actual completed checks; this handoff does not assert pending checks passed.
CONT-DAV-01/02 remain prepared for joint review. Profiles, cost agreement,
execution evidence and operational authorization are separate open gates.

Validation of this isolated snapshot: Windows Python 740 passed / 16 skipped;
Ubuntu 24.04.4/Jazzy 550 passed / one skipped after eight packages built and
six messages/two services inspected; frontend 84 passed and build passed;
repository check passed after the generated linked artifacts were present.
The Windows skips cover ROS and unavailable symlink privileges. Jazzy skips
the optional materialized planner snapshot; the separate published-source
conformance report remains BLOCKED. Existing controlled ROS test providers
are software harnesses, not a new mock or verified integrated execution.

At scope freeze/readiness/pre-submission, remind Jesús to obtain and record the
local organizer's explicit endorsement with review margin; David is backup.
No organizer contact, endorsement, external team message or A/B/C execution is
performed by this packet.

## Requested merge reconciliation

The owner requested conflict resolution and integration after the two pushes.
The scenario approval commit `09d7d6a` is already in main through PR14. The
remaining packet `ec819e5` is reconciled with published main
`5898e7d74c3eb00a018a2061a9b2264d947f12a8`. Two content conflicts in the
mandatory AI registers retain both sides, including all main media declarations.
Owner implementations and shared contracts are retained from main unchanged.
Earlier source/validation records remain historical snapshots, not replaced.

The [fresh comparison](../../evidence/mission-reconciliation-20261114/conformance-main/conformance.json)
against that main planner still reports one agreement and six disagreements,
authorization BLOCKED. The [new readiness](../../evidence/mission-reconciliation-20261114/readiness/scenario_diagnostic.json)
preserves approved experimental values, zero findings and six pending inputs.
This Git merge does not close scientific or execution gates. Fresh combined
checks and exact tested source hashes are retained with the
[reconciliation evidence](../../evidence/mission-reconciliation-20261114/README.md).

## Local science-patch research during the reconciliation audit

At the owner's request, the [17-sector survey](../science_patch_survey.md),
[prioritized map requests](../science_patch_map_requests.md) and
[local source/scale records](../../evidence/science-patch-survey-20261114/)
propose Bright Angel/Neretva, Hawksbill/Hogwallow and Bunsen Peak first, with
Mawrth as the first alternative outside Jezero. The 128 m control is retained;
512/1,024 m context and nested 128/256 m windows are proposals, not new missions.
NASA historical positions provide query anchors with explicit association/CRS
limitations; they are not current A/B poses or verified crop boundaries.

The owner confirms Daniel can generate crops but has not delivered these new
packages. Ask him to prepare the specified data, report coverage/registration
and preserve public/evaluator roles. No silent coordinate adjustment or invented
observations. Diego/Jesus/Jorge own subsequent performance, capture and display
checks; this research changes none of their implementations. CONT-DAV-03 stays
prepared for review, not completed acceptance. See proposed PATCH-P01..05 in
the scientific register. All new work stays local with no commits, push or merge
until the owner changes that instruction; model/cost/execution gates remain open.

## Local rover-campaign / human-EVA resource proposal

Source `c3ec4c1f1515dbc981ba82eed2ab1f54e9586264`, ICD candidate
`1.0.0-rc.1`, science model `mge-science-1.0.0`; no fetch or publication during
the owner's parallel audit. The [proposal](../agent_campaign_proposal.md) and
[source/analysis/validation packet](../../evidence/agent-campaign-proposal-20261114/README.md)
separate Bunsen/Bright Angel/Hawksbill rover episodes, human EVA and drone
sorties. Source/input/config hashes and analytical run identity are retained.

The proposed nominal allocations are EVA 35/60/85 min, 225/400/550 metabolic Wh
and 45/80/115 dry O2 L; rover 6.5/10/14.5 h and 800/1,200/1,800 gross electrical
Wh. They include separate 20% reserves and costed directed return. Workloads
are analytical design assumptions, not trajectories from unavailable crops.
All nine nominal envelopes fit by construction; all nine joint adverse cases
fail. Full drone-campaign energy remains NOT_ESTIMATED; sortie counters never
reset accumulated use. No physical energy availability or new operational
authorization is asserted. CAM-P01..07 await David's review.

Next: Daniel supplies registered public crops/uncertainty for real itineraries;
Diego reconciles exact scientific movement/activity/return costs without changing
tolerances; Jesús reviews agent release/progress/wait/thermal/SOC/evidence
bindings against main before any schedule integration. This packet changes
none of their implementations or contracts and creates no new MOCK. Strict
success criteria and the original scenario/profile/approval records remain
unchanged. Software checks and analytical reproduction are not LIVE evidence.

Local organizer notification/explicit endorsement remains a delivery gate:
remind Jesús at scope freeze/readiness/pre-submission with at least four hours
of review margin (or longer if requested); David is backup. This proposal is
not submission readiness and performs no external contact.

Fresh local checks for this proposal: Python 979 passed / 19 environment skips
(ROS modules and Windows symlink privileges), one existing Starlette warning;
frontend 161 passed / one optional-package skip; repository check and build
passed with Python 3.12.14 / Node 24.18.0 / npm 12.0.1. Reproduction, input
hashes, overwrite refusal, phase sums, causal waiting, cumulative flights and
original approval/readiness preservation pass. Ubuntu/Jazzy/colcon/ROS exchange
was not run for this analytical cut; earlier results are not relabelled fresh.

## Publication after reconciliation

The owner authorized integration after reconciliation. Published main9198b3d
(PR28) is incorporated unchanged. The earlier local-only status describes
the preparation cut; this publication preserves all proposed/approval states.
D-COST-02 accepts reuse of the scientific API as implementation direction;
profile approval, cost-context agreement and execution evidence remain open.
The rc.2 contract record is not a scientific approval or a semantic freeze.
Original analysis/report hashes and pinned c3ec4c1 reproduction remain historical.

Publication CI for 6e497a1: Python, web and ROS passed (run43670914573). ROS built/inspected all interfaces and passed the MOCK vertical integration suite. This remains software evidence, not scientific mission acceptance. See evidence/mission-proposal-publication-20261115/ci.json.
