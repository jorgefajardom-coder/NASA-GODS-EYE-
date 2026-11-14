# Diego - preserve the advanced planner and reconcile resource costs

Active branch: **`feat/planner`**. Audited head: `34c515b6b86f73336844e8b3614c70b144574ec3`; PR #2 is open, not merged. Algorithm commit `a6204dd`, ROS/snapshot/provisional crop commit `6e4984d` and handoff `40c252d` contain the substantive increment. Read the existing `docs/planner_handoff.md`, `src/mge_planning/MODEL.md` and `docs/planner_provenance.md` on this branch; keep their evidence intact.

Read [AGENTS.md](../../AGENTS.md), [ICD](../ICD.md), [contract baseline](../CONTRACT_BASELINE.md) and [integration matrix](../INTEGRATION_MATRIX.md) before editing. Canonical ROS fields/types live in `src/mge_interfaces/msg` and `srv`; preserve them and adapt representations explicitly.

## Owned implementation and contracts

Own `src/mge_planning/`, planner profiles/provisional crop preparation, `tests/planning/`, `tests/contract/test_planner_service.py` and planner evidence. Retain resource-constrained joint outbound/service/return FAST and SAFE search, clearance/corner/unknown gates, bounded work, immutable snapshot assembler and ROS service. **Do not restart A* or replace it with a simplified search.** Consume complete public TerrainMeta/belief/sigma/kind-mask snapshots with unique matching stamps and explicit profile configuration. Serve canonical PlanRoute and return RouteDecision candidates, never publish/authorize active_path. Use canonical FEASIBLE/UNKNOWN/NO_PATH/INSUFFICIENT_BUDGET/STALE_MAP/ERROR, uppercase wire kinds and nonhuman oxygen NaN (JSON conversion is gateway work). EFFICIENT remains ERROR/MODE_NOT_SUPPORTED; do not advertise it as implemented. Missing profiles/layers or unverified prior remain UNKNOWN.

P0 start/goal/return XY must be exact cell centres within 1e-6 m. Preserve `NON_CELL_CENTER` rejection for continuous mission poses; never snap silently. A future connector requires collision/uncertainty validation and costs charged to outbound/return budgets, plus coordinated contract tests and owner approval.

## Scientific dependency and mocks

The mission activity/grade model `mge-science-1.0.0` and the planner's 3D-distance/slope rates are mathematically different. Human metabolic energy/ oxygen and directed climbing, rover tractive/slip costs, drone activities and service costs cannot be made equivalent by merely loading projected fields. `pending_model_agreement` is not approved, even if source profiles are approved.

David governs mission scientific audit/time/energy/oxygen approval. Agree a shared model or documented conservative treatment with numerical full-itinerary comparisons including flat/up/downhill, service, outbound and return, zero edges, nonhuman oxygen, reserves, unknowns and boundary budgets. Record model ID, configuration hash and tolerances.

Keep MODEL_NOT_AGREED/MODEL_MISMATCH rejection until this passes; never claim operational feasibility from the approximation. All budgets remain experimental, not certified EVA limits.

Daniel supplies one public dataset, masks/sigma and three control points. Current planner crop (~128 m / 4 m at 18.45N,77.45E) differs from web's crop; never align them by index alone. Contract mocks may supply deterministic complete public snapshots for tests, with illustrative profile opt-in and MOCK labels. Never access evaluator reference or future task knowledge.

## Synchronize without losing existing work

After saving/reviewing local edits, use the existing worktree for this branch:

```sh
git status --short
git fetch origin --prune
git switch feat/planner
git pull --ff-only origin feat/planner
git log -1 --format=fuller origin/main
git diff --stat origin/main...HEAD
git diff origin/main...HEAD -- src/mge_planning tests/planning config/planner_profiles.illustrative.json docs/ICD.md
git merge origin/main
```

If the branch is not local, use `git switch --track -c feat/planner origin/feat/planner` instead of switch/pull. Do not switch it if another worktree already has it checked out. Merge main only while on your owned branch. Stop to reconcile any shared-contract conflict with Jesus and the producer/consumer owners; preserve both implementations and never force-push. This reconciliation becomes the main contract only after its PR is merged. Before that, review it as a proposal and do not claim it is published in main.

## Tests and consumer proof

First run `python -m pytest tests/planning tests/contracts/test_planner_provenance.py`. Keep independent Dijkstra, resource-feasible alternative path, FAST/SAFE, blocked corner, footprint/slope, stale batch and bounded-search tests. After baseline merge run `python -m pytest tests/contract/test_baseline_guards.py tests/contract/test_dataset.py` as well.

On Jazzy, build/source the workspace and run `python3 -m pytest tests/contract/test_planner_service.py`. Test with the existing explicitly illustrative flags only in a labelled test scenario; production must require confirmed batch protocol and reviewed profiles.

With Jesus/David, run actual MissionManager -> PlanRoute -> MissionManager, including one accepted cost-agreed full return/reserve candidate, one MODEL_MISMATCH, one insufficient budget and NON_CELL_CENTER. Record exact source/configuration IDs; a controlled planner mock does not prove this real consumer integration. Re-run seeded search benchmarks in a new evidence directory without overwriting old runs; search results are not mission A/B/C.

## Acceptance and next delivery

First deliver the numerical model reconciliation with David and a versioned model/configuration record. Then demonstrate the unchanged real service against Daniel's coherent dataset and David's actual manager. Preserve return budgets, explicit unsupported modes and all rejection reasons. Route/task mission policy, active route authorization, observation fusion, web scene and alternate mission search engines are outside this front and must not be duplicated.

## PR and handoff evidence

Include the tested source SHA, baseline/schema versions, dataset/run/map IDs, model/configuration hashes where relevant, exact commands/outcomes and links to immutable evidence. Name any MOCK provider and all skipped checks, with reasons. Run `python -m pytest`, `python scripts/check_repository.py`, and the frontend `npm ci`, `npm test`, `npm run build` where available, using `web/.nvmrc`. On Ubuntu 24.04/Jazzy, build with `colcon build --symlink-install`, source `install/setup.bash`, inspect the six messages/two services and run the ROS contract/integration tests. A Windows skip is not a passing ROS test.

Review `git status`, `git diff` and `git diff --check`. Keep commits atomic and English Conventional Commits; preserve Git identity, third-party rights and mandatory AI usage text/metadata/watermarks. Update `docs/AI_USAGE.md`, `docs/ai_usage.json` and your handoff. Do not upload secrets or evaluator data.
Jesus reviews integration; David approves scientific assumptions/success.
Software tests, replay and synthetic fixtures do not establish a validated
LIVE mission. No push, merge or release is implied by this handoff alone.
