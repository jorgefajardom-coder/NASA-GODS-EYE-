# Contract reconciliation verification

Source commit: `f2af4b23b57e0ef28c245cca0ad64a886ded039e`.
Reference main: `004b3b2c59a27794a1e49a61f48d0569bad020b2`.
Baseline `1.0.0-rc.1`; run_id `contract-baseline-20261114`.

Actual final results and limits are in validation.json; tested-source-sha256.json
binds exact runtime/configuration/test inputs. The JUnit files and stdout logs
are actual command outputs. These results verify software contracts, not a
complete mission, science-model equivalence or physical safety.

Commands executed on the combined source:

```sh
python -m pytest --basetemp .local/combined-pytest --junitxml=evidence/contract-baseline-20261114/windows-pytest.xml -q
python scripts/check_repository.py
cd web
npm ci
npm test
npm run build
```

In Ubuntu 24.04/Jazzy, `bash scripts/validate_contract_baseline.sh` copies the
same source to an ASCII temporary path, builds eight packages with colcon,
sources the install, inspects all eight interfaces and runs
`python3 -m pytest tests/contract tests/integration`. PYTEST_ADDOPTS points
JUnit output at the evidence path during that invocation. See the full target
build/interface/test log. The source is copied because rosidl/CMake failed on
the original Windows checkout's spaces/non-ASCII path; no ROS interface was
modified to address that environment issue.

263 Python cases pass on Windows; four ROS-only modules skip there. Target
Jazzy contract/integration run passes all 129 cases, including actual generated
serialization, real PlanRoute transport and the unchanged consumer with the
real planner. The four web tests and build pass. The independent read-only
planner seam also passed seven cases before main incorporated that planner.
Unmerged owner-branch suite reports are clearly distinguished in the matrix.

Remaining real data, mission/science approval, executor feedback, actual viewer
strict-contract integration and final public evaluator isolation are pending.
