# Jezero primary mission: approved experimental scenario

Proposal `jezero-primary-review-01` was recorded on **14 November 2026** and
subsequently approved explicitly by David for **JZ-P01 through JZ-P07 as
experimental scenario values only**. The approval is recorded as
[JZ-APP-20261114-01](science_approvals/jezero_scenario_20261114.json), binding the
reviewed proposal and approved nominal values. Profile coefficients, cost-model
agreement, snapshot/execution inputs and operational authorization remain pending.

Use the separate [experimental configuration](../config/mission_jezero.experimental.yaml)
for the approved values. Its runtime status remains `pending_integration`, with
`scenario_approval` recorded separately and operational `approval_evidence`
empty. The current node must reject it. The
[original proposed configuration](../config/mission_jezero.proposed.yaml) and
original sizing evidence remain unchanged as the historical review artifacts.
Neither preparing this document nor recording approval changes a runtime flag.

## Scenario and objective

Use Daniel's `jezero_mvp` public package from main PR #8, whose exact manifest
SHA-256 is fixed in the proposal. It has 32 by 32 cells at 4 m, native CTX
resolution 20 m, southwest origin (-64,-64), rows north, frame `map`, and
MOLA/DeltaGeoid vertical datum. Keep public elevations unchanged; no local z
offset or viewer exaggeration is applied. Data provenance and original NASA/
USGS source identities remain in [data sources](data_sources.md).

| Item | Approved nominal experimental value | Reason / qualification |
|---|---|---|
| Base A | cell (12,12): (-14,-14,-2571.199462890625) m | Matches the current integration human placeholder's XY, limiting handoff changes; this does not establish a safe landing/base site |
| Objective B | cell (23,23): (30,30,-2573.264892578125) m | 62.23 m horizontal separation; compact experiment inside the crop, 34 m from the nearest crop edge; no geological-interest claim |
| Rover staging | cell (13,12): (-14,-10,-2571.32958984375) m | Adjacent main placeholder XY; costs start from this distinct point |
| Drone staging | cell (12,13): (-10,-14,-2571.231201171875) m | Adjacent main placeholder XY; terrain elevation is a ground reference, **not flight altitude** |
| Primary service | 120 s stationary visual observation/check-in | Existing `inspect` light-work power is a costing alias; it creates no completed inspection TaskSpec |
| Waiting allowance for sizing | human/rover 60 s each; drone 10 s on ground | Chosen allowance, counted once; actual runtime consumption must use observed intervals |
| Return tolerance | 1 m, **3D distance** used by MissionManager | Model-pose threshold below half the 4 m cell spacing; native 20 m DEM and initial sigma 2.5 m do not substantiate physical 1 m accuracy |
| Planning mode / connectivity | FAST / ideal_global_p0 | Keep the existing experimental baseline fixed across comparisons; no communications guarantee |

The original `agents_jezero.yaml` remains unchanged. The approved experimental
z values and resource allocations still need explicit owner integration; never
replace the latest observed pose by an approved staging position. Neither B nor
the local rover sizing endpoint is a discovered POI. No future task catalogue,
reference DEM, observation or new mock is used.

## Resources and reserves

| Agent | Initial experimental allocation | Separate reserve (20%) | Usable after reserve |
|---|---|---|---|
| Human | 1200 s; 100 Wh metabolic; 25 L O2 | 240 s; 20 Wh; 5 L | 960 s; 80 Wh; 20 L |
| Rover | 1200 s; 60 Wh electrical | 240 s; 12 Wh | 960 s; 48 Wh |
| Drone | 180 s; 15 Wh electrical | 36 s; 3 Wh | 144 s; 12 Wh |

The 20-minute shared human/rover horizon makes slow, distant rover tasks
rejectable and keeps a first comparison bounded. Human energy/O2 caps leave
headroom for short optional work without automatically admitting every task.
The rover cap targets local inspection; accompanying the human all the way to
B is not assumed feasible. The drone cap is a short analytical envelope only.
These approved experimental allocations do **not** describe suit/battery capacity,
certified endurance or physical safety. The 20% holdback is our policy, **not a NASA
standard**; return is costed first and the reserve must remain afterward.

O2 means equivalent dry ideal gas at 273.15 K / 101.325 kPa. It covers the
existing model's metabolic estimate only, not suit leakage/purge or all life
support consumables. Human Wh and robot Wh have different meanings and must
not be pooled. Coefficients remain proposed in the source registry.

## Reproducible dimensioning, not route authorization

```sh
python scripts/size_jezero_proposal.py --run-id jezero-review \
  --output-dir tmp/jezero-review
```

The tool consumes Daniel's unchanged public loader, validates the original proposal,
and evaluates explicit geometry and activity costs through the scientific API.
It performs no search or traversability update and generates no observations.
Its proposed-only input guard remains intact for reproducing the historical
review. Approval does not relabel its original output as an execution result.

| Public-prior cost probe | Nominal time | Nominal energy | Nominal O2 |
|---|---:|---:|---:|
| Human: north then east, 88 m each way; 120 s service + 60 s wait | 401.12 s | 45.27 Wh | 9.24 L |
| Rover: 8 m out and back from its own staging; 120 s inspection + 60 s wait | 624.47 s | 23.03 Wh | absent |
| Drone: scalar chord comparison from its own staging to B and back; 30 s suspended observation + 10 s ground wait | 99.46 s | 7.72 Wh | absent |

Human outward energy is 12.83 Wh and return 14.54 Wh: descending and ascending
are charged independently. The north/east probe's largest public cell-height
difference is 0.13013 m. A direct diagonal instead reaches 0.23047 m, exceeding
the proposed 0.20 m step proxy. Do not substitute that diagonal or label the L
probe safe: footprint clearance and local obstacles are unverified. All 1024
cells remain unobserved, with initial sigma 2.5 m versus the proposed 1 m limit.
Subsequent main decision D-EST-01 permits hypothetical planning over valid
estimated prior; unobserved is not synonymous with NoData. It does not verify
traversal, change the proposed uncertainty limit or authorize this itinerary.
The producer/consumer bindings remain pending; see the
[mission success contract](mission_success_contract.md). Original sizing
outputs retain their historical assumptions and hashes.
Drone chord calculations prescribe no altitude, takeoff/landing, swept volume
or executable flight path. Missing flight validation is not solved by budget fit.

Single-coefficient low/high sensitivity and reserve fractions 10/20/30% are
retained in the report. Human minimum walking speed raises the primary probe
to 487.10 s / 55.25 Wh; rover minimum speed raises its local probe to 1068.94 s,
exceeding 960 s usable and requiring rejection. A 180 s optional heavy sampling
cost adds 23.06 Wh / 4.71 L to the human nominal probe; the combined 68.33 Wh
fits 80 Wh usable. A 300 s sample reaches 83.70 Wh and fails. These are cost
checks, never accepted tasks. Sampling still requires public discovery,
completed compatible inspection, primary B completion, actual remaining
resources, verified return and reserve checks. Combined worst coefficients
can fail even when individual sensitivities fit.

The local rover probe lasts longer than the nominal human primary round trip.
It therefore does not promise a completed inspection before B or an available
sampling window. Any extra coordination/waiting beyond the 60 s sizing allowance
must be charged from current resources and may eliminate the sampling margin.
Drone observation duration likewise implies no footprint or corridor coverage;
the observation producer/model must establish that separately.

## Evidence, sources and approval boundaries

The [retained sizing](../evidence/jezero-proposal-review-20261114/proposal_sizing.json)
binds the public inputs, proposal, profile registry and implementation hashes.
That original report remains immutable and describes the pre-approval state.
The [approval readiness diagnostic](../evidence/jezero-scenario-approval-20261114/readiness/scenario_diagnostic.json)
reports the experimental approval separately while retaining `NOT_READY` and
pending operational/model/snapshot requirements. The approval receipt is a
traceability record, not an authenticated signature or execution evidence.

The existing human activity anchors come from the lunar analog in
[NASA/TM-2010-216138, Table 4](https://ntrs.nasa.gov/api/citations/20110001417/downloads/20110001417.pdf#page=21).
Using light stationary work for a visual check-in is our modeling choice.
The proportional O2 estimate derives from 0.086 kg/h and 1.062 MJ/h (295 W)
in [BVAD Rev2, Table 4-70](https://ntrs.nasa.gov/api/citations/20210024855/downloads/BVAD_2.15.22-final.pdf?attachment=true#page=149).
[Perseverance components](https://science.nasa.gov/mission/mars-2020-perseverance/rover-components/)
and [Ingenuity hover telemetry](https://science.nasa.gov/blog/what-were-learning-about-ingenuitys-flight-control-and-aerodynamic-performance/)
provide reference scales only; our vehicle coefficients, budgets and reserve
fraction are not inferred NASA operational limits. The full source/assumption
registry remains in [scientific models](science_models.md).

David has approved the nominal scenario, cells, service, tolerance, allocations
and reserves recorded under JZ-P01 through JZ-P07. Sensitivity alternatives
remain analytical cases; they are not additional approved execution settings.
FAST and ideal_global_p0 keep their existing experimental baseline meanings;
this decision freezes no shared contract. Profile coefficient approval, consumer
O2 semantics, planner-model agreement and execution/observation bindings remain
separate gates. The scenario approval does not approve those gates, freeze A/B/C,
populate operational `approval_evidence`, or change the global
`scientific_approval=false` / `mission_execution_authorized=false` readiness flags.
