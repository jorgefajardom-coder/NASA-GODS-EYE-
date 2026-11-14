# Integration log

| Date | Version | Owner | Evidence | Blockers | Next dependency |
|---|---|---|---|---|---|
| 2026-11-14 | ICD-ROS2-V1 draft, `mge_interfaces` 1.0.0 | Jesús | `colcon build` of 3 packages; `ros2 interface show` for the 8 definitions; `pytest tests/contract` 10 passed; `smoke.launch.py` publishes 3 agent states. Run locally in a ROS 2 Jazzy container. | ICD not yet confirmed by the team. Agent states are MOCK (static, placeholder budgets). CI workflow not yet run on GitHub. | Team freeze of ICD-V1; Daniel publishes `TerrainMeta` + prior; Diego serves `PlanRoute`. |
