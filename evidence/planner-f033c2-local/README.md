# Local-only F03.3-C2 validation

Synthetic model estimates and actual software test/benchmark results. No physical,
NASA observational, approved-profile or LIVE mission evidence. Exact source hashes,
protected interfaces and selection omissions are in validation.json.

Working source is based on ffea8c2 plus local immutable-context commit 9c69980 and
the scientific Python search/policy changes fingerprinted in validation.json.
The latter hashes identify tested sources without a self-referential commit ID.
Reference main5a7db3d was inspected, not merged. No push or PR update performed.

| Selection | Passed | Failed/errors | Skipped |
|---|---:|---:|---:|
| Baseline planning, before changes | 369 | 0 | 0 |
| Final Windows full Python | 1207 | 0 | 22 |
| Final F03.3/D-07/F03.4 focused | 250 | 0 | 0 |
| Final native Jazzy planning/contracts/mission/unit | 1088 | 0 | 1 |
| Web | 201 | 0 | 1 |

Selections overlap. Windows has one existing Starlette/httpx deprecation warning.
Web build passes (678 modules). Node24.18.1 differs from the pinned24.18.0 by a
patch; no dependency was installed. Native colcon built all eight packages and
six messages/two services were inspected. Nodes/consumers use existing legacy
configuration; new scientific calls are isolated Python tests, never ROS activation.
Full native integration/Gazebo/three-role science execution was NOT performed.
The native skip is the explicitly absent external planner snapshot.

Initial native run: 1074 passed / 1 skipped / 14 SETUP ERRORS, caused by pytest8
interpreting helper name setup as an xunit module hook. Renaming it scientific_case
preserved all assertions; final complete native selection above passed. The
superseded errors and raw local XML hash are retained in jazzy_initial_fixture_errors.json.
The first search fixture also conservatively rejected an undersized rover map;
only the synthetic raster scale was corrected, not the published safety limits.

comparisons.json retains actual _search-versus-exhaustive results on the 1.36 Wh
directed graph, real public plan_route-versus-oracle FAST/SAFE output on a 1.6 Wh
raster, and one-run 12x12 computational timings/label counts. Example human label
counts are 22 legacy versus 358 science; rover22 versus326. h=0 is admissible but
can cost substantially more work. Coarse host timing and these small grids do not
establish real-time limits or large-map performance. Cache memory is bounded by
8192 directed entries per call; peak process memory was not measured.

Reproduce from the repo with the existing Python environment:

```powershell
.venv\Scripts\python.exe -m pytest tests/planning/test_scientific_context.py tests/planning/test_scientific_search.py tests/planning/test_scientific_replan.py -q
.venv\Scripts\python.exe -m pytest -q
.venv\Scripts\python.exe scripts/check_repository.py
git diff --check
```

From web: npm test; npm run build. Native target: source Jazzy and the locally
built workspace, then python3 -m pytest tests/planning tests/contract tests/mission
tests/unit. Use fresh ignored tmp paths for JUnit/base-temp output. No assertion
was weakened and no formula or approval was changed to obtain these passes.
