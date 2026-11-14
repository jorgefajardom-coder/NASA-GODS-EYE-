# Scaffold verification

Date: 14 November 2026. Scope: repository structure and implemented contract
guards only. These results are not evidence of a Mars mission or EVA safety.

## Local checks

- Python 3.12: `python -m pytest` (93 local test cases across contracts, mapping,
  mission and planning). The HTTP TestClient requires an unrestricted local
  execution environment on this Windows host; the sandbox attempt stalled.
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
