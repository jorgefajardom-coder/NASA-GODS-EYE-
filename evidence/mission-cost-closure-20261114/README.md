# Mission cost closure and activity-duration pilot

Classification: **software validation and analytical model diagnostics**.
No integrated mission, astronaut experiment, completed task, NASA measurement
or A/B/C result is claimed. No new mock or execution-input producer is supplied.
JZ-P01..07 remain approved scenario values only; profiles, cost agreement,
execution evidence and operational authorization remain pending.

## Sources and boundaries

The worktree is `feat/mission`, based on `09d7d6a29abd4501bb4d2491037985f073fb39e3`
plus the retained changed-source hashes. Main was reviewed at
`2f50ae697b34fe82e575b386936d0d5e4d74db64`, then rechecked at
`9614816081acc7779e6a565f5f4ebad8b0bd5287` before publication. The intervening
viewer PR does not change the reviewed planner, simulation, data, interfaces
or D-EST-01 decision. No producer changes were merged into this worktree.
Planner source is `69101e983c9a9668ba852460c484b5db8f12a1a5`; integration
head is `c42ca246018e677bfb68cf4ace29a6c5be2c223e`.

See the [duration sources and interpretation](../../docs/activity_duration_research.md),
[cost agreement packet](../../docs/cost_agreement_handoff.md), and
[success-evidence boundaries](../../docs/mission_success_contract.md).

## Retained artifacts

| Artifact | Meaning |
|---|---|
| [Published planner comparison](conformance/conformance.json) | Fresh exact-source comparison: 1 agreement / 6 disagreements, 7 feasible candidates, authorization BLOCKED |
| [Final scientific vectors](vectors-final/cost_vectors.json) | 38 baseline and seven duration cases with exact model/profile/config hashes; no backend replacement |
| [Final duration impact](pilot-final/activity_pilot_impact.json) | Seven analytical activity cases tied to validated scenario-value approval and original public-prior baseline |
| [Readiness](readiness/scenario_diagnostic.json) | Public package validated, zero findings, six pending requirements, NOT_READY; values approved separately |
| [Candidate](readiness/mission_candidate.json) | Diagnostic configuration export; no execution authorization |
| [Validation record](validation/validation.json) | Commands, versions, hashes, actual checks and limitations |
| [Jazzy source snapshot hashes](validation/jazzy.source.json) | Exact public sources copied for target-platform build/tests |

The initial `vectors/` and `pilot/` directories are earlier analytical
snapshots, retained without rewriting. Their input/scenario/source hashes
precede the metadata references and additional approval-validation checks.
Use `vectors-final/` and `pilot-final/` for the current handoff. None is an
execution journal or a newly approved duration.

## Results and practical limit

Adding a 600 s documented-sample workflow (420 s light + 180 s heavy work,
an explicit unapproved phase-allocation assumption) to the unchanged human
public-prior probe gives 1001.12 s / 110.10 Wh / 22.48 L. The usable allocation
after reserve is 960 s / 80 Wh / 20 L: all three margins fail. Additional
optional travel, extra coordination and suit losses are excluded. A 180 s
acquisition primitive is not a complete documented sample cycle.

| Check | Actual outcome | Retained details |
|---|---|---|
| Windows `python -m pytest` | 740 passed, 16 skipped, one existing deprecation warning | [Log](validation/python.log), [JUnit](validation/python.junit.xml); ROS imports/symlink privilege skips |
| Repository checker | Passed | [Final log](validation/repository.log); [initial sequencing failure](validation/repository-initial.log) ran before linked final export existed |
| `web`: `npm test` | 84 passed | [Log](validation/web-tests.log); existing checkout frontend, not newly merged viewer PR |
| `web`: `npm run build` | Passed | [Log](validation/web-build.log) |
| Ubuntu 24.04.4 / Jazzy | Eight packages built; six messages/two services inspected; 550 passed, one skipped | [Log](validation/jazzy.log), [JUnit](validation/jazzy.junit.xml), [platform versions](validation/jazzy-platform.log) |

Jazzy's skipped case requires an explicitly materialized optional planner
snapshot. The separate published-source comparison above does run against
the pinned planner source and retains disagreements. Existing controlled ROS
service and fixture providers validate software exchange; they do not prove
execution with agreed Diego costs. The science duration/progress gaps in the
success contract remain open despite passing software checks.

Windows Python is 3.12.14; Node is the pinned 24.18.0; Linux Python is 3.12.3.
The validation record lists runtime dependencies and complete report hashes.
All values and source interpretations still require the stated owner reviews.
