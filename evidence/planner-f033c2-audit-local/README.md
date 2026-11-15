# Final local C2 audit evidence

Software audit over local afd6a281, with a minimal availability-admission fix.
No model/profile coefficient, node, ROS interface, MissionManager or core search
change. Source hashes identify the tested uncommitted fix and benchmark harness;
the subsequent local commit preserves both earlier C2 commits unchanged.

- admission_before.json: ten reproducible failures on afd6a281, including the
  original source/raw-local-JUnit hashes. Raw failing XML stays in ignored tmp.
- focused.junit.xml:267 passed,0 failed/errors,0 skipped; includes17 new audit cases.
- windows_full.junit.xml:1224 passed,0 failed/errors,22 skipped; one existing warning.
- jazzy.junit.xml:1105 passed,0 failed/errors,1 optional external snapshot skipped.
- benchmark.json:80 complete samples with fixed inputs, default limits, status/
  reason/labels, p50/p95, process high-water RSS, predicted costs and resources.
- validation.json: exact omissions, source/implementation identities and scope.

Selections overlap. Web201 passed/1 skipped; build passed. Eight native packages
built and eight interfaces inspected after an initial WSL resource startup error.
The native selection is planning/contracts/mission/unit, not complete ROS/Gazebo
integration. Legacy nodes stay legacy; the science backend remains Python opt-in.

Benchmark cases are the unchanged public Jezero primary scenario and the existing
synthetic D-07 search control. Data-owner loader verifies four public control
points. Source uncertainty2.5m and profile limit1m remain unchanged, so all public
samples are UNKNOWN/UNVERIFIED_CORRIDOR; no valid-route costs are asserted there.
Known synthetic control samples all fit the unchanged default search limits.

Reproduce with existing dependencies:

```powershell
.venv\Scripts\python.exe scripts/benchmark_scientific_planner.py --repeats 10 --output tmp/NEW-benchmark.json
.venv\Scripts\python.exe -m pytest tests/planning/test_scientific_admission.py tests/planning/test_scientific_benchmark_protocol.py -q
.venv\Scripts\python.exe -m pytest -q
.venv\Scripts\python.exe scripts/check_repository.py
git diff --check
```

Use a new output path: benchmark artifacts are never overwritten. Preparation
and interpreter startup are outside plan_route latency; process RSS includes
common preparation/imports and is not isolated heap use. No peak-heap or real-time
guarantee is inferred. Human energy/O2 remain model estimates; no execution ledger
or physical/approved-science evidence is generated. See the full audit report in
docs/planner_f033c2_final_audit.md for findings and recommendations.
