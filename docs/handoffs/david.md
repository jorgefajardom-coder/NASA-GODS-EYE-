# David - retain scientific mission authority and approve the model

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
