# DAV-02 / CONT-DAV-01 cost agreement handoff

Status: **awaiting consumer agreement**, not scientific profile approval or
runtime authorization. This mission-owned packet leaves Diego's planner,
Jesús's executor and all ROS definitions unchanged. The baseline scenario
values remain approved under JZ-APP-20261114-01; source profile coefficients,
cost agreement and execution evidence remain pending.

The [experimental contract](../config/cost_agreement.experimental.json) fixes
units, accounting, current-resource/reserve semantics and the required schedule
context. It retains existing finite comparison tolerances `rel=1e-5`,
`abs=1e-3`. Those are not clearance/localization limits, scientific model
equivalence or permission to spend beyond a budget. A negative reserve margin
fails even if its magnitude is below a cost-comparison tolerance.

## Published gap

Audited planner: `69101e983c9a9668ba852460c484b5db8f12a1a5`; published main:
`2f50ae697b34fe82e575b386936d0d5e4d74db64`. Planning package code is identical
between these references. `MotionProfile`, `_motion_costs` and goal service
still use:

| Quantity | Current search model | Scientific audit model |
|---|---|---|
| Human movement time | 3D length/speed times directed grade factors | Horizontal length/speed times absolute-grade slowdown |
| Movement energy | 3D distance times per-metre grade multiplier | Human metabolic time + positive climb; rover auxiliary + traction/slip; drone activity power + positive climb |
| Human O2 | elapsed time times constant rate | estimated metabolic energy times BVAD-derived proportional factor |
| Service / wait | one `service_power_w`, one human O2 rate | explicit activity and duration; ground wait versus hover differ |

The current projection sets service power to the maximum activity power.
For primary B, `inspect` means 120 s of stationary light-work costing:
`358.08*120/3600 = 11.936 Wh`. The human projection instead uses 461.17 W,
giving `15.372333... Wh`, a **+3.436333... Wh** difference from service alone.
This is a demonstrable mismatch, not an approved conservative error bound.
Optional sampling requires another rate; merging wait into service cannot
reproduce different activity powers. Replacing only this coefficient cannot
resolve the other directed movement/O2 equations.

The ROS `PlanRoute` request carries `service_time_s`, but no activity name or
waiting schedule. Its consumer needs an agreed configuration/request-context
binding keyed by run/request/agent/map, with exact model/profile/config hashes.
This packet describes that need; it does not invent a metadata channel or ROS
field. An approval flag or profile filename is not proof of that binding.

## Deterministic scientific vectors

```sh
python scripts/export_cost_agreement_vectors.py --run-id cost-contract-review \
  --output-dir tmp/cost-contract-review
```

The exporter calls only the existing scientific API on analytic geometries and
durations. It reads the approved experimental file for primary service and
resource limits, and the unchanged proposed profiles for coefficients. It
does not start a planner/executor, infer a terrain route, publish an observation
or manufacture task/execution evidence. These are **test vectors**, not a
replacement module or an integrated mission result.

Each vector carries complete inputs and exact unrounded expected time, Wh and
applicable O2. Invalid vertical ground moves and negative durations retain
expected rejection instead of being silently omitted. Robot O2 remains null.
The full schedule contains outward movement, explicit service, explicit wait
and separately directed return exactly once. Boundary cases cover sufficient
remaining resources, a representable cost-plus-reserve boundary, insufficient
time/energy/human O2 and reserve greater than capacity. Constructed boundary
capacities explicitly record upward floating-point representation adjustment;
they do not alter the approved scenario allocations or permit numerical slack.

Partial-service vectors specify an already-completed analytical prefix, its
cost, current remaining resources, unfinished activity and return. Expected
remaining cost excludes that prefix. These are accounting examples, never
claims that the described movement or work happened. A replan consumer must
bind the values to received execution evidence before applying them at runtime.

Outputs retain contract/scenario/profile/model/exporter SHA-256, Git revision,
dirty state and `run_id`. An existing output directory is refused. Authorization
and scientific approval remain false even if all finite vector values match.

An optional `--activity-pilot <JSON>` adds source-traced activity-duration cases
without changing the approved 120 s primary service or 180 s sampling example.
The input has `schema_version: "1.0.0"`, `status: "proposed"` or `pending_review`,
and a `cases` list containing `case_id`, `agent_id`, `activity`, `duration_s`,
`source_url`, `source_locator` and optional explanatory fields. Preserve source
windows/derivation and caveats in those fields. The exporter copies them and
hashes the pilot file; it does not interpret an archival duration as approval
for a modern mission. David's scientific review supplies any such source values;
none is hardcoded in this toolkit.

A mixed workflow may instead supply `schedule: [{activity, duration_s}, ...]`
with source metadata at case level, omitting the single `activity`/`duration_s`
pair. Per-phase costs and their sum are exported. Supplying both forms is
rejected: a workflow's total must not be charged again in addition to its phases.
Any engineering allocation of light/heavy phases must remain labelled as an
assumption even if its total duration is anchored in an archival workflow.

## Closure matrix and owner actions

| Closure item | David / mission packet | Diego / planner | Jesús / integration | Acceptance still needed |
|---|---|---|---|---|
| One directed cost definition | Scientific API + analytic expected vectors | Implement/consume an equivalent backend, or submit a separately justified alternative for review | Use the agreed model when debiting execution intervals | Same exact inputs and schedule match; no projection-only approval |
| Explicit activity binding | Primary inspect120; wait/service separated; per-request context requirements | Confirm how requests select the correct activity and remaining duration | Bind authorized phase/task/command to that context | Same run/request/agent/map/model/profile identity through producer and consumer |
| Current resources / partial service | Prefix/current/unfinished-service examples and separate reserves | Avoid recharging completed connector/travel/service | Report actual debit/progress; no initial-resource reset | Same stopped pose/current budgets produce correct return/remaining cost |
| Geometry and uncertainty | Costs alone do not verify geometry | Preserve directed limits, connector and clearance checks | Observe only executed sensor footprints; acknowledge stop | Estimated path versus verified execution remain distinct |
| Numerical checks | Existing comparison bounds retained | Run identical vectors with own source/config hashes | Run the real mission/service consumer | Flat/up/down, activities, invalids, return, boundary and partial-service results retained |
| Approval | Scenario values approved; coefficients and agreement pending | Supply exact implementation evidence and remaining discrepancies | Supply binding/consumer evidence | David reviews profiles/error bounds; Jesús reviews wiring; only then consider agreement flags |

The seven-case published-source probe is complementary: run it against the
new exact source revision and retain disagreements/statuses. Do not relabel
the previous 1-agreement/6-disagreement report as a new test. Expand consumer
coverage to connectors, sensitivity and actual remaining-service requests;
matching this finite vector set alone cannot certify all inputs or close C3.

The [fresh retained comparison](../evidence/mission-cost-closure-20261114/conformance/conformance.json)
ran against the full planner SHA above: one agreement and six disagreements,
seven feasible candidates and authorization BLOCKED. It retains its own run ID,
command and source hashes; this is software/model diagnosis, not an executed
mission. The [duration research](activity_duration_research.md) supplies the
additional seven source-traced activity cases for the next consumer comparison.

D-EST-01 permits hypothetical planning over a valid orbital estimate without
marking it locally observed. That owner decision changes neither the resource
equations nor traversal verification. Daniel/Diego must implement the estimated
cell boundary together; mission must preserve stop/inspection/return authority.
`MODEL_NOT_AGREED` and `MODEL_MISMATCH` remain active until the joint closure.
