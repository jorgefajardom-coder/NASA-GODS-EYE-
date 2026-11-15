# MVP-PL-01 local software evidence

Read [the scope and coverage report](../../docs/planner_mvp_pl01.md).
Tested source is `feat/planner@d81407de` plus the new hashed test file.
`validation.json` contains full source revisions, per-file hashes, configuration,
versions, actual commands, omissions and attempt history. `traces.json` extracts
the FAST/SAFE paths, estimates, identities and remaining allocations from the
new tests' JUnit properties. They are synthetic software results, not physical
measurements or a NASA mission.

| Final selection | Passed | Failed/errors | Skipped |
| --- | ---: | ---: | ---: |
| New Python consumer cases | 12 | 0 | 0 |
| All planning, Windows | 465 | 0 | 0 |
| Full Python, Windows | 1236 | 0 | 22 |
| Native Jazzy planning/contracts/mission/unit | 1117 | 0 | 1 |
| Selected existing ROS integrations | 8 | 0 | 0 |
| Local web | 201 | 0 | 1 |

Selections overlap. `focused.junit.xml`, `planning.junit.xml`,
`windows_full.junit.xml`, `jazzy.junit.xml` and `integration.junit.xml` retain
the exact final cases. Eight ROS packages built; six messages/two services were
inspected. Repository/whitespace checks and web TypeScript/Vite build passed.

Preserved unsuccessful attempts are deliberately separate:

- `authoring_initial.json`: 12 new-test draft failures caused by the helper
  passing uppercase HUMAN into the planner; corrected explicit kind translation. All failure traces and the original XML hash
  are retained; raw XML stays unchanged at `tmp/mvp-pl01-first.xml` because its
  traceback contains trailing whitespace.
- `integration_initial_collection.junit.xml`: one missing-httpx collection error,
  zero executed integration cases. An existing Linux environment supplied that
  dependency for the successful final run; no installation was performed.

WSL resource failure preceded the successful retry. Native pytest is 7.4.4 versus
the declared >=8 range; local Node is 24.18.1 versus pinned 24.18.0. This evidence
does not claim a locked CI-equivalent environment. Windows omissions/native
snapshot omission and the native JUnit-format warnings are enumerated in JSON.
Web's one omitted test needs an external recorder package.

To reproduce the new boundary test with the repository's development environment:

```powershell
.venv\Scripts\python.exe -m pytest tests/planning/test_mvp_mission_consumer.py -q -o junit_family=xunit1 --junitxml=tmp/mvp-pl01-repeat.xml
.venv\Scripts\python.exe scripts/check_repository.py
git diff --check
```

Use a fresh temp/output path for repeats. On Ubuntu 24.04/Jazzy, build/source the
unchanged workspace, then run `tests/planning tests/contract tests/mission
tests/unit` and the three integration modules named in `validation.json`.
Exact build commands and the existing-environment invocation are retained there.
Dependency deviations must be reported or reconciled before claiming exact CI
equivalence. No science backend is passed to a ROS node by these commands.

ROS scope: real MissionNode/legacy planner with synthetic providers tests the
closed model gate; real public terrain/mapping/planner/recorder with MOCK mission
and kinematic execution tests recovery/recording. Closing packages are READY,
with three IDLE agent states; only the primary human moves. The exact generated
packages stay under ignored tmp; hashes, closing routes/resources and provenance
are retained in JSON. This is not three-role scientific COMPLETE or a physical
mission. Evaluator/reference arrays are not included.

No production source, MissionManager, scientific model, configuration, ROS field,
authorization setting or frozen delivery revision was changed. All C2 commits
and foreign files remain intact. Publication is not part of this local cut.
