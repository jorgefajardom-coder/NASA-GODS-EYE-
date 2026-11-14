# Mission/main merge reconciliation

Requested by the repository owner after the two mission pushes. The approval
commit `09d7d6a` is already in main through PR14; the remaining delivery is
`ec819e52befb0fce0189dd46e02869c781c3e0c7`. This reconciliation incorporates
published main `5898e7d74c3eb00a018a2061a9b2264d947f12a8` into `feat/mission`
before its integration. Both histories and original evidence remain intact.

## Conflicts and preservation

Only `docs/AI_USAGE.md` and `docs/ai_usage.json` conflict. The resolution keeps
all 60 existing main usage records, both generated-media declarations, the
mission activity/cost packet and the new reconciliation disclosure. No owner
implementation, ROS field, enum, data array, approved scientific value or
operational approval is changed to resolve a conflict. Main's current viewer,
connector/recovery and recorder changes remain intact.

Compared with main, the runtime additions remain mission's analytic tools,
contracts, tests and the estimated-prior limitation wording already in ec819e5.
JZ-P01..07 approval is preserved. Profile approval, cost agreement and execution
acceptance remain open. No new mock, observation or completed task is supplied.

## Fresh diagnostics

- [Exact-main planner comparison](conformance-main/conformance.json): one
  agreement / six disagreements, all seven candidates feasible, authorization
  BLOCKED. Planner source manifest SHA-256 is
  `5ae78c00fe2358dec32cbbdc94efc3b95b4855777ecbf4eee1d2325a171211a4`.
- [Readiness](readiness/scenario_diagnostic.json): public package validated,
  zero findings, six missing operational requirements, NOT_READY; experimental
  values approved separately. [Candidate](readiness/mission_candidate.json)
  remains diagnostic.

Both commands retain run IDs, command lines, exact source/configuration hashes
and the pre-merge revision plus dirty state. These are fresh model/software
diagnostics; previous `69101e9` cost reports and pilot outputs remain immutable.

## Combined verification

| Check | Actual outcome | Evidence |
|---|---|---|
| Full Windows Python | 979 passed / 19 skipped; one existing deprecation warning | [Log](validation/python.log), [JUnit](validation/python.junit.xml) |
| Initial Windows run | 978 passed / 1 failed / 19 skipped: WinError5 during atomic replay manifest rename | [Original log](validation/python-initial.log), [JUnit](validation/python-initial.junit.xml) |
| Replay recheck, unchanged code | All 38 passed in a fresh temporary directory; the complete run above also passed | [Log](validation/replay-recheck.log), [JUnit](validation/replay-recheck.junit.xml) |
| Repository checker | Passed | [Log](validation/repository.log) |
| Frontend tests | 161 passed / one skipped | [Log](validation/web-tests.log) |
| Frontend production build | Passed | [Log](validation/web-build.log) |
| Ubuntu 24.04.4 / Jazzy | Eight packages built; six messages/two services inspected; 588 passed / one skipped | [Log](validation/jazzy.log), [JUnit](validation/jazzy.junit.xml), [source hashes](validation/jazzy.source.json), [platform](validation/jazzy-platform.log) |

Windows skips cover ROS imports and absent symlink privileges. The initial
atomic-rename denial was not reproduced; its cause remains undetermined and
no gateway workaround is introduced. Jazzy's skipped case needs an optional
materialized planner snapshot; the separate exact-main comparison above ran.
The web skip requires `MGE_REPLAY_PACKAGE`, which was not supplied. Existing
controlled ROS service/fixture providers are software harnesses; passing them
does not prove a scientific mission or cost agreement. Text logs and JUnit are
normalized to UTF-8/LF with line-end whitespace and trailing blank lines removed;
original console captures remain
in the local temporary directory. Exact commands and hashes are recorded in
`validation/validation.json`.

The local-organizer endorsement before final submission remains a separate
coordination gate. No submission or external team message is performed here.
