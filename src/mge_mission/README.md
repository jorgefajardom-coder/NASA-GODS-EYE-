# mge_mission

Owner: David; integration by Jesus. Status: **scaffold; operational implementation pending**.

| Layer | Responsibility |
| --- | --- |
| R | R01, R05, R10, R11, R12, R16, R18 |
| F | F04: mission authority, task precedence and acceptance |
| L | MissionSpec, TaskGraph, TaskAllocator, ScientificBenchmark |
| P | Python core in `mge_mission/core.py`; ROS startup in `mge_mission/node.py` |
| V&V | Guide acceptance cases remain pending; record actual runs under `evidence/` |

Run after a ROS 2 Jazzy workspace build: `ros2 run mge_mission mission_node`.
This only starts a warning-only node; it does not claim to provide the planned ROS services or topics.
`core.py` imports without ROS so future unit tests can run independently.
The package maintainer email is a placeholder and the distribution license is not yet assigned; the team must decide both before redistribution.

## Input/output contract and next work

Input: mission/profile configuration, public agent/map state, observed discovery
events, goal requests and planner feasibility/costs. Output (pending): authoritative
mission state, idempotent ordered events and active paths. The planner returns
candidates; this module alone will select the published route. No evaluator
reference or hidden POI list belongs in mission input.

`mission_success` implements only the guide's four-boolean criterion: primary goal,
return within a declared tolerance, verified traversal under the model, and no
budget violation. It does not measure or prove those facts. Allocation, ROS state
authority and execution are not implemented; `assign_optional_task` raises
`NotImplementedError` rather than accepting a task without evidence.

David and Jesus's first tasks: freeze mission assumptions and profile ranges;
enforce survey -> discover -> inspect -> sample precedence; evaluate incremental
task cost while preserving the primary goal, return and reserves; and log both an
accepted and rejected optional POI. Return has priority over optional tasks.
Benchmark A/B/C uses identical terrain, goals, budgets and seeds and preserves
failed runs. Guide S-01 through S-08 remain acceptance work, not claimed results.
