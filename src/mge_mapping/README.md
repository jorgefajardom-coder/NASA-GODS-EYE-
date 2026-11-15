# mge_mapping

Owner: Daniel. **Implemented footprint fusion and coherent ROS map publisher.**
The earlier scaffold description is historical. Scientific approval and
physical traversal acceptance remain separate.

| Layer | Responsibility |
| --- | --- |
| R | R05, R06 |
| F | F02: maintain prior, belief and versioned observations |
| L | BeliefMap, ObservationFusion |
| P | Python core in `mge_mapping/core.py`; ROS startup in `mge_mapping/node.py` |
| V&V | Guide acceptance cases remain pending; record actual runs under `evidence/` |

Run after a ROS 2 Jazzy workspace build: `ros2 run mge_mapping mapping_node`.
The node publishes TerrainMeta, belief, sigma, observed coverage and kind masks
under a unique shared stamp, repeating complete batches for DDS ordering.
`core.py` imports without ROS for Python tests.
The package maintainer email is a placeholder and the distribution license is not yet assigned; the team must decide both before redistribution.

## Input/output contract and next work

Input: immutable public prior, belief/sigma state, and explicitly simulated
observations with run/agent/observation IDs, source version and simulation time.
Output: belief/sigma and per-profile traversability plus a monotonic map
version. Preserve distinct NoData and not-yet-observed masks. The constructor only
checks observation structure; it does not establish bounds, sensor accuracy,
footprint truth or provenance. Fusion validates causal context and footprint
before updating an immutable snapshot. Reference arrays are never inputs.

Freshness is deliberately conservative: a new observation requires the current
base and cannot predate the last applied observation anywhere in the run.
Rejections are atomic, including delayed disjoint footprints. Applied IDs are
idempotent. Invalid frame/clock inputs are rejected, never corrected. Missing
or UNKNOWN obstacle evidence cannot clear a confirmed obstacle; explicit FREE
evidence must be current and nonolder. This is not probabilistic sensor fusion.

The legacy default requires local coverage and sigma ≤1 m. D-EST-01's candidate
extension is explicitly selected with `exploration_policy_file`, e.g.
`config/exploration_policy.illustrative.json`. The illustrative, versioned policy
admits finite estimates under its sigma/slope limits, preserving sigma and
observed=false. Its ID/schema/hash travel in TerrainMeta.sources and the replay.
`0` means admissible for a proposal, never verified or authorized passage;
`-1` remains unknown and `100` forbidden. NoData cannot become free. Planner
profiles independently enforce uncertainty; a 1 m profile still rejects the
2.5 m prior. Limits need owner review and do not approve scientific costs.

Tests: `python -m pytest tests/mapping
tests/contract/test_mapping_observation_adapter.py`; use the Jazzy consumer for
estimated route → local contradiction → acknowledged stop → replan → return.
See [current reconciliation](../../docs/audit_reconciliation.md) and
[D-EST-01](../../docs/decisions/2026-11-14-estimated-terrain-planning.md).
