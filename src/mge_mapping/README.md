# mge_mapping

Owner: Daniel. Status: **scaffold; operational implementation pending**.

| Layer | Responsibility |
| --- | --- |
| R | R05, R06 |
| F | F02: maintain prior, belief and versioned observations |
| L | BeliefMap, ObservationFusion |
| P | Python core in `mge_mapping/core.py`; ROS startup in `mge_mapping/node.py` |
| V&V | Guide acceptance cases remain pending; record actual runs under `evidence/` |

Run after a ROS 2 Jazzy workspace build: `ros2 run mge_mapping mapping_node`.
This only starts a warning-only node; it does not claim to provide the planned ROS services or topics.
`core.py` imports without ROS so future unit tests can run independently.
The package maintainer email is a placeholder and the distribution license is not yet assigned; the team must decide both before redistribution.

## Input/output contract and next work

Input: immutable public prior, belief/sigma state, and explicitly simulated
observations with run/agent/observation IDs, source version and simulation time.
Output (pending): belief/sigma and per-profile traversability plus a monotonic map
version. Preserve distinct NoData and not-yet-observed masks. The constructor only
checks observation structure; it does not establish bounds, sensor accuracy,
footprint truth or provenance. `fuse_observation` is intentionally unimplemented.

Daniel's first tasks: reject invalid or duplicate observations, update only cells
inside the footprint and increase version exactly once per valid event. Publish
`-1` unknown, `0` admissible and `100` prohibited masks after agreeing profiles
with Diego and David. Reference arrays are not mapping inputs. Acceptance cases:
individual guide T-03 through T-06 and a planner consumer test.
