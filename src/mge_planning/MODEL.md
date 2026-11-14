# P0 planning model and proof boundaries

Inputs are one copied, read-only **public belief** snapshot, explicit profile,
request and resource budget. There is no evaluator-reference argument. Local ENU
uses metres, southwest origin, rows north, columns east. Goals and return targets
must be cell-centre XY positions within 1e-6 m. Human/rover starts outside that
tolerance use the validated connector below. Centred requests retain the prior
graph-only behavior (including that tolerance). Graph waypoint z is belief surface
elevation; this is a grid surface model, not a vehicle dynamics model.

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

## Continuous ground start: one conservative connector

The only candidate is the centre of the cell containing the requested XY pose.
There is no nearest-free-cell fallback. Both endpoints lie in that convex cell,
so the entire straight segment remains there. A known admissible containing cell
is mandatory; unknown/NoData/sigma failures never produce a candidate. A pose on
a cell boundary still undergoes the footprint check against neighbouring cells.

The swept footprint uses the same obstacle-square distance lower bound as graph
edges, with a stricter rejection at zero obstacle clearance even for point agents.
For segment horizontal length h, let d_min be the smallest distance to any blocked
cell centre at five equally spaced samples. Every point lies within h/8 of a
sample. Thus d_min - h/8 - resolution/sqrt(2) - radius - localization_error bounds
the margin to every blocked/unknown square for the ENTIRE segment. A nonpositive
bound rejects the connector; it is never clamped to zero and accepted. Boundary
clearance is exact: each signed distance to an axis-aligned map boundary is affine
on the segment, with its minimum at an endpoint. The smaller of these margins and
the destination's graph clearance is included in SAFE's bottleneck objective.

A 3-D start retains its supplied z; a 2-D start uses the containing cell's belief
height. Within this single-cell model z varies linearly along the connector, so
its directed slope is constant and its total height change is checked against the
step limit. The same profile cost/limit function as graph edges is used. No
subcell relief is inferred from a single DEM height: input pose height/localization
must be consistent with the public map. This is not a reconstruction of physical
ground beneath the segment. Profiles and that modeling assumption need science
review; arbitrary drone altitude/flight remains unsupported.

Connector time/energy/human oxygen initialize the first A* label, before budget
pruning. They are charged exactly once along with outbound, service and return;
the heuristic, label dominance and graph search remain unchanged. SAFE filters
the connector by each trial threshold too. Optimality is within this ONE-connector
augmented graph, not among all possible continuous-space attachments or paths.

Successful Python results expose immutable `start_connector` metadata (start/end,
3-D distance, costs and minimum margin). `outbound_path` starts with its exact
3-D start and then retains every graph waypoint, including the attachment centre.
The ROS wire schema is unchanged: its first two outbound points delimit this
connector and existing resource fields include its costs; separate metadata is
Python-only. Centred results have `start_connector=None` and no extra waypoint.
If return is required, supply an explicit centred base: the default return-to-start
is rejected when that start is continuous. Continuous goals/bases are not added.

`UNKNOWN/UNVERIFIED_START_CONNECTOR` means unknown cells/sigma prevent verification
but an optimistic connector could exist (diagnosis only). Otherwise
`NO_PATH/NO_ADMISSIBLE_START_CONNECTOR` means this particular attachment is
inadmissible under the model; it does not prove every continuous route impossible.
Ordinary graph/budget/status handling applies after a connector is verified.

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

## Event policy

The independent `replan.py` layer reuses this geometry, costs and `plan_route()`.
It does not implement another search or change this service's wire definitions.
See [policy inputs, phase mapping and proof boundaries](../../docs/replan_policy.md).
