# P0 planning model and proof boundaries

Inputs are one copied, read-only **public belief** snapshot, explicit profile,
request and resource budget. There is no evaluator-reference argument. Local ENU
uses metres, southwest origin, rows north, columns east. P0 endpoints must be
cell-centre XY positions within 1e-6 m. A continuous pose is rejected rather than
silently snapped without costing/checking its connector. Output z is belief
surface elevation; this is a grid surface model, not a vehicle dynamics model.

## Admissibility and geometry

The graph has eight neighbours. Traversability -1 and invalid height/sigma are
unknown, 100 is forbidden and only valid 0 cells can support an executable
candidate. Diagonal moves cannot cut a forbidden or unknown orthogonal corner.
Transitions obey profile step and directed slope limits. A missing sigma raster
cannot satisfy a profile that explicitly requires a sigma threshold.

Clearance includes occupied/unknown cell squares, the map exterior, agent radius
and localization allowance. Distance to obstacle cell centres minus half the
cell diagonal is a conservative lower bound on distance to the whole occupied
square. Five samples per edge minus half their spacing preserve that bound
between samples using the 1-Lipschitz distance property. The map-boundary segment
distance is handled exactly. Consequently this model can reject a physically
possible narrow corridor; it never claims an exact collision geometry or an EVA
certificate. Reported clearance is a conservative footprint margin.

## Costs and joint search

For horizontal length h, 3-D length d and rise dz, set u=max(dz,0)/h and
v=max(-dz,0)/h. Supplied nonnegative profile coefficients define:

- time = d / speed * (1 + uphill_time_factor*u + downhill_time_factor*v)
- energy = d * energy_wh_per_m * (1 + uphill_energy_factor*u + downhill_energy_factor*v)
- human oxygen = time * oxygen_l_per_s
- service energy = service_time_s * service_power_w / 3600; service oxygen uses
  the same supplied illustrative/approved oxygen rate.

These parameterized rates are assumptions, never universal physiological or
vehicle constants. Non-human oxygen is None internally; the ROS adapter alone
maps that to its existing NaN sentinel.

FAST uses A* states (cell, goal-serviced phase), retaining nondominated labels
for time/energy/oxygen. Goal service is charged once on phase transition. Return
is searched jointly, so an over-budget fastest outbound path cannot hide a
slower feasible complete route. The heuristic uses remaining planar distances
divided by supplied speed plus pending service time; nonnegative slope factors
make this an optimistic lower bound. Reserves are constraints on all labels.

SAFE first finds a feasible FAST candidate, then repeatedly searches with a
clearance threshold strictly above that candidate's bottleneck. The finite graph
has finitely many bottlenecks. When no improvement is feasible, the candidate
maximizes conservative bottleneck clearance and minimizes time at that level.
Bounds apply to the entire sequence; a capped proof returns UNKNOWN rather than
an unproven SAFE optimum. EFFICIENT is explicitly unsupported in P0.

## Status semantics

- FEASIBLE: candidate fits the known-grid model, service, return and reserves.
- STALE_MAP: request map version differs from the snapshot.
- UNKNOWN: missing profile, mismatched run, unresolved corridor or search bound.
- INSUFFICIENT_BUDGET: exhaustive search on a fully known grid found no complete
  resource-feasible route, although an admissible geometric route exists.
- NO_PATH: even optimistic geometry through unknown cells cannot connect the
  requested complete mission under the declared grid/footprint model.
- ERROR: malformed positions, profile-kind mismatch or unsupported mode.

If known paths exceed the budget but unresolved cells remain, UNKNOWN is
deliberately conservative: an unknown shortcut could alter feasibility. Neither
unresolved terrain nor reached search limits prove global impossibility.
Only MissionManager may authorize/publish an active route. A route ID is
deterministic from run/request/version, actual output paths and costs; elapsed
search time is diagnostic and excluded from the identifier.
