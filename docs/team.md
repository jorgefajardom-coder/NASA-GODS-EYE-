# Team branches and ownership

Current priority after PR28: [delivery closure](delivery_closure_plan.md) and
[D-DEL-03](decisions/2026-11-14-delivery-freeze.md). Basic reconciliation is
published at main9198b3d; source/parameter freeze and full mission acceptance
remain separate. Pause expansion, preserve existing studies and target the
20:00 submission with organizer endorsement. The continuation allocation and
inventories below retain earlier planning context, not the current freeze policy.

Current next assignments: [continuation plan, 14 November 2026](team_continuation_plan.md),
based on main `5ab1387` and the Conciliación cuts. Read its per-owner checklists
before the historical branch inventories below. Daniel continues larger-map
feasibility; Jorge Fajardo investigates NASA science-target/patch criteria and
co-owns shared site deployment with Jesús. His latest publication is assumed
usable for allocating these tasks; its verification remains in the other chat.
Execution, same-run replay and delivery acceptance remain separate gates.

Follow accepted owner decision [D-EST-01](decisions/2026-11-14-estimated-terrain-planning.md):
plan hypothetical routes over valid orbital estimates before local observation;
revise on contradictory evidence. The old blanket observation prerequisite is
superseded in scope. PR28 implements an explicit illustrative estimated-prior
path; no-policy callers retain observed-only behavior and independent profile
limits remain active. Scientific and owner semantic approval remain separate.
Keep step 4 (integrated execution/roles/stop/replan) and step 5 (same-run offline
replay and web video) open while independent module work continues. Varied scenes,
larger maps and H-DAN-01 remain optional and must protect these P0 milestones.

The owner-selected working baseline is the [probable minimum mission
checklist](mission_checklist.md), with priorities, dependencies, acceptance cases
and desired coordination cuts. Follow its [NASA traceability
register](nasa_traceability.md). Detailed expected/desired effort forecasts and
thread snapshots are internal local records under Git-ignored `.local/planning/`;
they are estimates, not evidence of completion or a public submission artifact.

The active branch inventory was inspected against remote main
`004b3b2c59a27794a1e49a61f48d0569bad020b2` at the final refresh on
2026-11-14; initial audit main was `f75c54e`. PR #2 merged externally during
this task, and that main is incorporated into the reconciliation. See [contract baseline](CONTRACT_BASELINE.md) and [integration matrix](INTEGRATION_MATRIX.md) for publication state, exact revisions, contracts and unresolved acceptance.

| Person | Actual active branch | Owned scope | Individual handoff |
| --- | --- | --- | --- |
| Jorge | `feat/ux` (verified latest continuation; PR source alignment pending) | Existing 3D viewer, scene, assets, layers, agents, timeline, display adapters | [Jorge](handoffs/jorge.md) |
| Jesus | `feat/integration` | ROS interfaces, ICD, gateway, recorder, bringup, sim/CI and integration adapters | [Jesus](handoffs/jesus.md) |
| Diego | `feat/planner` | Advanced planning engine, snapshot adapter, PlanRoute service and planner tests | [Diego](handoffs/diego.md) |
| Daniel | `feat/data` | Canonical public data, mapping, terrain configuration, provenance and control points | [Daniel](handoffs/daniel.md) |
| David | `feat/mission` | Scientific authority, mission/task manager, resource profiles, acceptance and benchmark protocol | [David](handoffs/david.md) |

The initial audit found `feat/ux` at the scaffold; concurrent work has since
advanced it to `d649e2e` with the complete viewer, gateway replay adapter and
main merge. `feature/web-replay-viewer` at `73f22db` is a verified ancestor and
remains preserved. The objective requested that historical branch as PR source;
Jorge/Jesus must confirm alignment with the latest `feat/ux`/PR #5. Do not force
branch changes or substitute an older scaffold for either implementation.

`dev/jesus` was pruned remotely; its prior work survives on `feat/integration`
(now `45a4590`). `codex/docs-probable-mission-plan` remains PR #4's separate
proposal, now at `5bb6566`. No GitHub usernames or reviewer permissions are
guessed. The matrix retains both initial and final inventories.

## Begin or resume work

Read AGENTS.md, ICD.md, CONTRACT_BASELINE.md and your handoff first. Keep local changes safe before switching. For an existing local branch, replacing BRANCH with your confirmed active branch above (Jorge confirms PR-source alignment first):

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

Local organizer endorsement is a P0 delivery gate: Jesus contacts the organizer
when the package is ready, David backs him up, and everyone checks JES-07/AC-10
in the mission checklist. Reserve at least four hours before intended submission
(or longer if requested); the current coordination target is Sunday 16:00 for
the desired 20:00 submission, subject to earlier local requirements. Every
member's agent must remind them at scope freeze, readiness and pre-submission
while notification/explicit endorsement is undocumented. Record the pending
action in handoffs; silence does not close the gate. See AGENTS.md section 15.
