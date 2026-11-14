# Integration log

| Cut | Owner | State | Next handoff | Evidence |
| --- | --- | --- | --- | --- |
| Initial scaffold, 2026-11-14 | Jesus + team | Structure only | Confirm ICD; crop; profiles; first vertical | verification.md; no mission run |

Add commit/schema version, owner, run_id, command, observed result and next
dependency per integration cut. Do not call a build a successful mission.

## Existing team contribution preserved

Merged source: `dev/jesus` at `00c8e44`. The branch's integration log reports
that Jesus built its three original ROS packages in a Jazzy container, inspected
eight interfaces, passed ten ROS contract tests and published three static MOCK
agent states. Those results are contributor-reported and were not rerun on this
native Windows host. The current combined workspace requires its own CI build.
The original commits and interface definitions are retained; no contract freeze
or physical mission validation is implied.

## Planner P0 takeover

| Commit / run | Owner / review | Observed result | Next dependency |
| --- | --- | --- | --- |
| a6204dd | Diego front; Jesus integration review | FAST/SAFE kernel, resource-constrained joint return and acceptance cases published | Guarded ROS adapter |
| 6e4984d | Diego front; David science review | PlanRoute server, immutable public batches, fresh CTX prior and isolated local HiRISE reference | Jazzy CI, producer batch protocol, approved profiles |
| planner-p0-20261114 | Team takeover | Nine new illustrative benchmark queries match independent Dijkstra; real unverified CTX yields UNKNOWN; 154 local tests pass, two ROS modules skip | Full mission/consumer acceptance on Daniel and David inputs |

## Web viewer (feat/ux, PR #5)

| Commit / run | Owner / review | Observed result | Next dependency |
| --- | --- | --- | --- |
| fc03df6 | Jorge; Jesus integration review | Mission viewer replaces the web scaffold; scaffold stale-route guard and envelope types kept in the viewer | Review of PR #5 |
| 89216fc | Jorge; Jesus | Viewer plays the gateway package `mock-vertical-001` (copied unchanged from feat/integration d28f3e2) and ends in READY, map v2, route r2 | Rasters inside replay packages; live gateway connection |
| 1e37fd3 | Jorge | `main` (planner PR #2) merged into feat/ux; only the AI disclosure register conflicted, both entries kept | Consume planner routes in the viewer |

Local evidence: 64 web tests, `npm run build` and `scripts/check_repository.py` pass;
`python -m pytest` was not run on this host (pytest not installed). The terrain is a
provisional CTX crop pending Daniel's processed package.

Continue on feat/planner; see planner_handoff.md. The generated benchmark is
computational acceptance evidence, not mission safety or scientific validation.
