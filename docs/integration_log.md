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

Continue on feat/planner; see planner_handoff.md. The generated benchmark is
computational acceptance evidence, not mission safety or scientific validation.

## Contract reconciliation cut, 2026-11-14

- Baseline candidate: 1.0.0-rc.1, ROS package/schema unchanged at1.0.0/ICD-ROS2-V1;
  canonical gateway replay1.0.0. Commit041a636 introduced adapters/contracts;
  source f2af4b23b57e0ef28c245cca0ad64a886ded039e reconciles concurrent main004b3b2.
- Main PR #2 was merged externally by Jesus during this task. Only that already
  reviewed main was incorporated; no other owner PR was merged here. Initial
  audit main f75c54e is retained in the source lock.
- Source commit uses the existing David Yanguas Git identity. Integration
  approval remains Jesus; scientific/model acceptance remains David with Diego;
  commit identity does not assert those approvals.
- Latest audited heads and owners are in contract_baseline.json/matrix.
  feat/ux now continues Jorge's original feature/web-replay-viewer via PR #5;
  source alignment awaits Jorge/Jesus, no branch was overwritten.
- run_id contract-baseline-20261114: native Python263 passed/four ROS module
  skips; Ubuntu24.04/Jazzy8 packages/all8interfaces and129 tests passed; web
  npm ci/test/build passed (4 tests); repository and whitespace checks passed.
- Exact commands/source hashes/JUnit/stdout: evidence/contract-baseline-20261114.
  Generated-interface and actual PlanRoute tests run on Jazzy; MOCK-only guards
  do not establish full mission acceptance.
- Blockers: real public canonical dataset, numerical resource-model agreement,
  public evaluator leakage in web demo, gateway MOCK/LIVE provenance, existing
  TS replay strict validation, stop acknowledgement and owner-reported
  callback/search-limit performance. No operational feasibility is approved.
- Target publication is a reviewed reconciliation PR to main. Main was
  re-fetched before publishing; its observed SHA is004b3b2. The candidate remains
  unmerged and must not be reported as a published main baseline.
