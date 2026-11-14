# Current contract reconciliation verification

Source `f2af4b23b57e0ef28c245cca0ad64a886ded039e`, based on updated main
`004b3b2`; baseline `1.0.0-rc.1`, 2026-11-14 (America/Bogota).

| Command / platform | Actual result |
| --- | --- |
| python -m pytest (Python 3.12.14, Windows) | 263 passed; four ROS-only modules skipped |
| python scripts/check_repository.py | Passed including nested handoff links |
| web: npm ci; npm test; npm run build (Node24.18.0) | Passed; 4 tests; build passed |
| Ubuntu24.04/Jazzy colcon build --symlink-install | All 8 packages built |
| ros2 interface show | All six messages/two services inspected |
| Jazzy: python3 -m pytest tests/contract tests/integration | 129 passed, no skips |
| git diff --check | Passed |

[Immutable source hashes, JUnit and full target log](../evidence/contract-baseline-20261114/README.md).
The real planner/provider seam now passes after PR #2 was merged externally.
The generated tests cover actual ROS arrays/NaN plus the real planner failure
serializer; generated PlanRoute service tests are included on target. These
checks do not imply real MissionManager/data/gateway/viewer execution together.

The initial native-path ROS attempt failed in rosidl/CMake on spaces/non-ASCII;
the successful script uses an exact source copy under a fresh ASCII temporary
path. Native Python required an isolated basetemp due local Temp permissions.
Earlier setup errors were corrected before the final recorded passes. Existing
Starlette TestClient deprecation and >500kB web bundle warnings remain.

Not executed: Gazebo Harmonic E2E, complete mission/executor stop feedback,
scientific model agreement, canonical georeferenced data acceptance and a fresh
combined run of unmerged PR #3/#5 stacks. All R01-R18 system acceptance remains
pending/blocked as detailed in the matrix. Branch-owner reports retain their
original source/revision and are not substituted for these fresh results.

## Historical records retained below

The following scaffold/planner records describe earlier snapshots; the current
result above supersedes their environment/availability statements.

# Scaffold verification

Date: 14 November 2026. Scope: repository structure and implemented contract
guards only. These results are not evidence of a Mars mission or EVA safety.

## Local checks

- Python 3.12: `python -m pytest` (93 local test cases across contracts, mapping,
  mission and planning). The HTTP TestClient requires an unrestricted local
  execution environment on this Windows host; the restricted attempt stalled.
- `python scripts/check_repository.py`: package XML, Python syntax, JSON,
  declared AI paths and local documentation links.
- Frontend: `npm test` (2 tests); `npm run build` (TypeScript + Vite).
- `git diff --check`: whitespace validation.

Known nonblocking warnings: Starlette deprecates its httpx TestClient integration;
Three.js produces a minified bundle above 500 kB. Resolve as dependencies and
viewer scope evolve; neither is a scientific result.

## Not validated locally

ROS 2 Jazzy, colcon and Gazebo are unavailable in this native Windows session.
The ROS CI job must build packages and inspect all eight custom interfaces on
Ubuntu 24.04 / Jazzy. No simulator world, ROS graph flow, real NASA crop,
observation fusion, planner, optional-task allocation, saved replay, browser E2E,
public site, mission benchmark or competition submission has been validated.
All R01-R18 acceptance criteria remain pending.

## Team target checks

After dependencies are installed, use README commands. For ROS: colcon build,
source install/setup.bash, inspect all six messages and two services, and run
`python3 -m pytest tests/contract`. Other tests run from the repository root
with requirements-dev.txt installed. Package-local colcon test suites do not
exist yet. An HTTP 200 health response only means the process is available;
it explicitly says ROS is disconnected. An API command receives 503, not an
acceptance. Record actual consumer/run evidence separately under evidence/.

## Included ROS-only tests

The ten interface checks from dev/jesus require rosidl_runtime_py and a sourced
built workspace. They skip as one module locally and run explicitly in ROS CI.
Contributor-reported checks are retained in integration_log.md; the combined
workspace must pass a fresh ROS CI build before it is called compiled.

## Combined workspace build evidence

[CI run for 0294f19](https://github.com/jorgefajardom-coder/NASA-GODS-EYE-/actions/runs/43608206824)
compiled all eight packages, inspected the eight definitions and passed all ten
ROS contract tests. Python/web jobs passed. Its final empty package-local test
discovery step exited with code 5; CI now explicitly uses the actual root
pytest suites and ROS contract tests rather than claiming package-local tests.

## Planner branch verification

The P0 planner at code commit `6e4984d` passes 154 local Python cases, including
new D-01..D-10 scenarios, batch/provenance guards and a fresh-prior check. Two
ROS-only test modules skip on native Windows; Jazzy CI runs them with generated
messages and a real request/publisher/service/client flow. The tests include
missing data, stale map and invalidation during search.

New measured artifacts are in evidence/planner-p0-20261114. Nine illustrative
FAST round-trip queries across three seeds matched independent Dijkstra. The
fresh CTX check correctly returned UNKNOWN rather than inventing local corridor
verification. These checks replace the initial planner placeholder only; the
full mission, final science products, approved rates and public live demo remain
unvalidated. This branch leaves the existing ROS message/service schema intact.

## Preserved mission-branch records (source8f69f62)

These module records predate the combined mission-service handoff; they are not
combined-main acceptance. Fresh results will accompany this PR.

## Mission module verification, 14 November 2026

The mission branch now has implementation and software-contract evidence, not
an accepted end-to-end mission. Operational scientific parameters remain
proposed and S-01 through S-08 reviews remain pending.

| Check | Observed outcome |
| --- | --- |
| Windows Python 3.12.14, `python -m pytest -q` | 226 passed; 2 ROS-dependent modules skipped |
| Ubuntu 24.04 / ROS 2 Jazzy, `colcon build --symlink-install` | All 8 packages compiled |
| `ros2 interface show` | All 6 messages and 2 services inspected |
| Jazzy mission and contract suites | 162 passed; no skips or failures |
| `python scripts/check_repository.py` | Passed, 8 package manifests |
| Pinned Node 24.18.0, `npm test` | 2 passed |
| `npm run build` | Passed, TypeScript and Vite |
| `git diff --check` | Passed |

The [machine-readable record](../evidence/mission-validation-20261114-v2/validation.json)
contains JUnit reports, the build/test log and SHA-256 hashes for 93 exact files
copied to the tested ROS workspace. Three idempotency failures from the prior ROS
attempt are preserved with their correction and passing regressions. Raw CDR
serialization is not a canonical equality key; the adapter now compares request
field values explicitly.

Native Windows Python requires the existing virtual environment on this host;
the Store launcher is inaccessible. The installed ROSIDL tooling failed with the
Windows source path containing spaces/accented characters. Run
`bash scripts/validate_mission_ros.sh` on Jazzy to build an ASCII-path Linux
snapshot instead. The script retains logs/source hashes/JUnit XML in ignored
`tmp/`, and uses ROS domain 83 unless `MGE_TEST_ROS_DOMAIN_ID` is supplied.

The ROS smoke uses a controlled planner and synthetic inputs. It verifies actual
services, state/events/path publications, run/time/version guards, idempotency
and invalidation. It establishes no Gazebo movement, NASA terrain processing,
physical stop acknowledgement or complete optional-task/mission execution.
Scientific-model agreement with `feat/planner` and ROS inputs for discovery,
work completion and traversal evidence remain integration work.

The standalone [final model check](../evidence/mission-models-20261114-v2/model_checks.json)
records 15 synthetic formula estimates, input profiles and code/configuration
hashes. It is labelled MODEL_CHECK and does not establish NASA observations,
scientific acceptance or an A/B/C benchmark. Existing Starlette/httpx deprecation
and frontend bundle-size warnings remain outside this module's changes.

## Evidence recorder and sensitivity follow-up, 14 November 2026

The isolated `feat/mission` follow-up passed 366 Python cases on Windows
(five platform/ROS skips) and 312 mission/contract cases on Ubuntu 24.04/Jazzy
(one optional published-planner-snapshot skip). The eight packages compiled
and six messages/two services were inspected. Repository checks, both frontend
tests and frontend production build passed. Existing Starlette deprecation
and frontend chunk-size warnings remain. A sandboxed Windows full-suite attempt
stalled and was interrupted; the successful complete suite used the permitted
launcher outside that restriction.

The [retained validation record](../evidence/mission-recorder-validation-20261114/validation.json)
includes exact tested source hashes and JUnit/log exports. The
[sensitivity report](../evidence/mission-sensitivity-20261114/sensitivity.json)
contains 138 low/nominal/high model evaluations across three illustrative
round trips. Nominal time/energy estimates are human 98.801 s / 12.850 Wh,
rover 628.326 s / 24.095 Wh, drone 80 s / 4.823 Wh. Low drone horizontal
speed changes model budget feasibility because the illustrative time reserve
leaves only one second nominal margin. These are synthetic calculations,
not observed endurance, mission success, scientific approval or A/B/C results.
