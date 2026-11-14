# Team branches and ownership

The active branch inventory was inspected against remote main
`f75c54e929576c6780d559c9daa24d06ccf0a0b8` on 2026-11-14. See [contract baseline](CONTRACT_BASELINE.md) and [integration matrix](INTEGRATION_MATRIX.md) for publication state, exact revisions, contracts and unresolved acceptance.

| Person | Actual active branch | Owned scope | Individual handoff |
| --- | --- | --- | --- |
| Jorge | `feature/web-replay-viewer` | Existing 3D viewer, scene, assets, layers, agents, timeline, display adapters | [Jorge](handoffs/jorge.md) |
| Jesus | `feat/integration` | ROS interfaces, ICD, gateway, recorder, bringup, sim/CI and integration adapters | [Jesus](handoffs/jesus.md) |
| Diego | `feat/planner` | Advanced planning engine, snapshot adapter, PlanRoute service and planner tests | [Diego](handoffs/diego.md) |
| Daniel | `feat/data` | Canonical public data, mapping, terrain configuration, provenance and control points | [Daniel](handoffs/daniel.md) |
| David | `feat/mission` | Scientific authority, mission/task manager, resource profiles, acceptance and benchmark protocol | [David](handoffs/david.md) |

`feat/ux` has no changes beyond audited main and is not Jorge's implementation front. Preserve it; do not replace the real viewer with its scaffold. `dev/jesus` was pruned remotely; its prior work survives on `feat/integration`. `codex/docs-probable-mission-plan` remains the separate PR #4 documentation proposal. No GitHub usernames or reviewer permissions are guessed.

## Begin or resume work

Read AGENTS.md, ICD.md, CONTRACT_BASELINE.md and your handoff first. Keep local changes safe before switching. For an existing local branch, replacing BRANCH with the exact active branch above:

```sh
git status --short
git fetch origin --prune
git switch BRANCH
git pull --ff-only origin BRANCH
git log -1 --format=fuller origin/main
git diff --stat origin/main...HEAD
git merge origin/main
```

If the branch is not local, use `git switch --track -c BRANCH origin/BRANCH`
in place of switch/pull. Merge origin/main only while on your owned branch.
Do not switch a branch that is already active in another worktree; use that
worktree. Resolve conflicts by contract ownership and rerun producer/consumer
checks; never force-push, reset away work, or resolve by copying another
module.

The proposed reconciliation is consumable as the main baseline only
after its review/merge. Do not pull an unmerged contract as if it were main.

## Merge gate and ownership

1. State requirement IDs and R-F-L-P allocation, input/output contracts,
   baseline/schema versions, source/configuration hashes and pending decisions.
2. Make a small logical change; review status/diff and preserve concurrent edits.
3. Run module unit checks, contract checks and at least one actual consumer case;
   identify every mock and every check not run.
4. Update provenance, required AI declarations/metadata, licenses and watermarks.
   Never publish the evaluator reference in web assets, replay or planner input.
5. Open/update a PR to main with an English Conventional Commit title and actual
   evidence. Do not redefine shared .msg/.srv fields to suit one consumer.
6. Jesus reviews integration; David approves scientific assumptions, success
   criteria and model agreement. Data/grid changes also require Daniel; display
   compatibility requires Jorge; planner math requires Diego.

MissionManager alone owns mission state, task eligibility and active-route
policy. Planner returns candidates. Gateway serializes authoritative state.
Web displays it. Missing producers use conforming deterministic MOCK providers;
exactly one provider may own each canonical ROS service in a launch profile.

The ICD is versioned for reconciliation, with outstanding owner decisions; it
is not a claim that scientific approval or all system acceptance is frozen.
Do not report MOCK, replay, synthetic observations, a build or a unit test as
validated LIVE mission execution.

## Integration cuts (America/Bogota)

The existing team target remains Sunday **2026-11-15 23:59**; this is a team
planning target, not a newly verified official competition cutoff. The prior
guide targets map -> route -> view, then observation/replan, Sunday morning
budgets/A-B-C, scope freeze Sunday 16:00, presentation/compliance 16:00-20:00,
and submission buffer 20:00-23:59. Readiness is determined by evidence and
owner approval, not elapsed time. Preserve the final buffer and confirm any
applicable earlier local deadline with the organizer.
