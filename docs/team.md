# Team branches and ownership

The five branches start at the shared scaffold on main. They are work areas,
not completed features or approved PRs. Names follow the integration guide.

| Person | Branch | Scope | First handoff |
| --- | --- | --- | --- |
| Jorge | `feat/ux` | web | Three ENU control points rendered; route state and reason visible |
| Jesus | `feat/integration` | interfaces, gateway, bringup, sim, CI, ICD | Compile six messages/two services; confirm ICD; connect first vertical |
| Diego | `feat/planner` | planning package and tests | A* vs Dijkstra; return budget and blocked-corner cases |
| Daniel | `feat/data` | data, mapping, terrain config | Licensed Jezero crop, manifest, control points, isolated reference |
| David | `feat/mission` | mission, agent config, science docs | Approve success criteria, resources, task precedence and benchmark |

The pre-existing `dev/jesus` and `docs/agents-policy` branches are preserved.
The canonical integration front for this scaffold is `feat/integration`.
No GitHub usernames or reviewer permissions are guessed.

## Begin work

```sh
git fetch origin
git switch --track origin/feat/ux
```

Replace `feat/ux` with your branch. If already local, use `git switch feat/ux`
and `git pull --ff-only`. For later integration, fetch and merge `origin/main`
into your work branch. Never force-push another person's work.

## Merge gate

1. State requirement IDs, R-F-L-P mapping and input/output contracts.
2. Make a small logical change and review status/diff.
3. Run module checks plus a consumer test; record checks not run.
4. Update provenance, required AI declarations and ICD/version as relevant.
5. Open a PR to main with an English Conventional Commit title and evidence.
6. Jesus reviews integration; David approves scientific assumptions.

The ICD is proposed, pending team confirmation. No acceptance case is passed
until evidence exists. Prior code/assets need eligibility and license review.

## Integration cuts (America/Bogota)

Deadline: Sunday **2026-11-15 23:59**. First connect map -> route -> view; then
observation/replan; Sunday morning budgets and A/B/C; scope freeze Sunday 16:00;
presentation/compliance 16:00-20:00; submission buffer 20:00-23:59. Confirm any
earlier local cutoff. Guide milestones are targets, not proof of completion.
