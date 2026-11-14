# Public execution recorder and sensitivity handoff

`mge_mission.recorder.EvidenceRecorder` is a pure Python, single-writer API.
It does not subscribe to ROS, execute agents, read evaluator references or
derive completed work from a planned route. Integration must supply public
observations through the existing core before recording the resulting events.
The proposed ROS interfaces remain unchanged.

## Recording and export

Create one recorder per `run_id`, with the actual `model_id` and explicit
`execution_kind`: `SIMULATED_MISSION`, `REPLAY`, `SOFTWARE_TEST` or `MODEL_CHECK`.
Only the first kind is eligible for the existing mission benchmark auditor.
The caller must describe the actual origin; changing a label cannot establish
execution. Synthetic pytest fixtures remain software tests, not mission results.

1. Feed every `MissionEvent` from sequence one through `record_event`. Identical
   deliveries are idempotent; conflicting IDs, gaps and backwards times fail.
2. Feed public `ObservedTask` and completed `TaskEvidence` through
   `record_discovery` and `record_task_completion`, referencing the matching core
   discovery/DONE event. Their causal IDs, task, run, map and route are retained.
3. For each actually executed ground step, supply `TraversalRecord` to
   `record_traversal`. The record binds agent, route and map to its event and
   includes executed distance and a true/false/unknown public-model safety check.
   `TraversalClosure` explicitly states the executor's total step count and
   distance at the final event. Missing closure, omitted steps or unknown checks
   cannot establish complete traversal or a zero unsafe-step count.
4. Supply `ExecutedCost` for each completed movement/service/wait interval using
   estimates from the science API. Intervals for an agent cannot overlap;
   duplicate deliveries are not added again. Oxygen is human-only. Energy totals
   remain separated by agent. A gap or partial timeline coverage makes that
   agent's total unknown; raw interval estimates remain in the export. Agents
   absent from cost records have no claimed consumption. There is no reserve
   expenditure or allocation cost automatically added to executed consumption.
5. Supply the latest explicit `MissionEvidence` snapshot via `record_predicates`,
   bound to the final observed event's map, route and simulation time. Each new
   event invalidates earlier predicate snapshots. Missing predicates stay null.
6. Call `export(new_directory, metadata)`. Metadata must carry the frozen
   protocol identity, policy/seed/attempt, actual UTC execution times,
   termination state, outcome status, reason, command and environment. The
   format is the existing `RunOutcome` contract; it cannot override evidence,
   metrics or artifact hashes. SUCCESS additionally requires COMPLETE, four
   explicit true predicates and fully checked executed ground steps.

The exporter creates `timeline.jsonl`, `records.json`, `execution.json`, optional
`traversal.json`, and `outcome.json` with artifact SHA-256 hashes. It refuses an
existing directory and seals the recorder after export. Inputs are retained in
memory until export: this version is **not a durable crash-recovery journal**.
Failed filesystem writes may leave a partial directory; use a fresh directory
for retry, and never submit a directory without its completed outcome.

Mission duration is the last minus first recorded simulation timestamp, only
when all event times exist. Consumption requires complete interval coverage
over that same recorded timeline. Traversal fraction is distance-weighted and
requires explicit closure. Optional-task counts, replan latency, map age and
time to verified route remain null with reasons: their measurement boundaries
need an execution producer. No unavailable metric is replaced with zero.

Run `scripts/audit_benchmark.py` with the frozen plan and exported outcome before
comparison. Hash consistency and explicit declarations do not independently
prove physical execution, scientific validity or approved coefficients.

## Offline coefficient sensitivity

```sh
python scripts/sweep_mission_sensitivity.py --run-id sensitivity-example \
  --output-dir tmp/sensitivity-example
```

The CLI reads `config/science_profiles.proposed.json` and the explicit
`sensitivity_cases` in `config/scenario_demo.yaml`. Coordinates, durations,
budgets and reserves in this file are illustrative. They do not replace
Daniel's operational scenario. No new terrain assumptions are inferred.

For each case and traced profile coefficient, the pure `sweep` API evaluates
minimum, nominal and maximum values, changing one coefficient at a time without
mutating profiles. Each row retains the source/justification, unit, approval
status, directed outbound/return costs, service/wait costs, totals, delta from
nominal and remaining margin after reserves. It reports budget feasibility and
whether it changes from nominal; this is not optional-task execution authority.
Unspecified budgets yield unknown feasibility. Invalid nominal inputs fail;
invalid variants remain explicit `MODEL_REJECTED` rows.

Shared oxygen conversion/reference constants stay fixed in this model version
and appear in `fixed_assumptions`; `oxygen_scale` explores proportional oxygen
uncertainty. Clearance/footprint/step/uncertainty parameters are traced but are
not evaluated by these segment formulas: zero change is not proof of safety.
The report includes exact profile/scenario/model/script hashes, source revision,
dirty-tree flag and `run_id`. It is `MODEL_CHECK`, with
`integrated_mission_executed=false` and `scientific_approval=false`. It cannot
enter the A/B/C comparison as a mission result. This is an OAT exploration,
not joint uncertainty propagation or a statistical confidence interval.

Remaining integration work belongs at the agreed execution boundary: supply
observed steps and closures, core task evidence, interval coverage and runtime
measurements. No planner, ROS message, simulator or frontend field was changed
for this handoff. Coefficient approval and the existing planner cost agreement
gate remain pending their owners.
