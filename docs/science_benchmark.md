# A/B/C benchmark protocol

Status: protocol and executable evidence audit; no integrated mission results are claimed.

Use the [evidence audit](benchmark_evidence.md) and its draft templates to record
the freeze and externally supplied execution outcomes. No mission is generated
by the auditor.
Owner: David. Integration and evidence support: Jesus and module owners.

## Experimental question

Compare whether reconnaissance changes the ability to complete the primary
human objective and return under the declared mission model. A reasoned abort
is a successful rejection test, but is not a completed mission.

Policies differ only in reconnaissance strategy:

- A: public orbital prior, no prior drone reconnaissance.
- B: reconnaissance concentrated on the candidate route corridor.
- C: reconnaissance selected to distinguish alternative corridors.

Do not call one policy superior until the integrated executions exist. A single
scenario or seed supports an exploratory example, not generalization.

## Freeze before running

Record the dataset/source and processing hashes, map/grid conventions, initial
public prior, hidden evaluator reference identifier, goal/base, task generator,
agent profiles, resource model/configuration hash, budgets, reserve requirements,
return tolerance, time step, observation model and seeds. These inputs remain
identical between A/B/C; only policy changes. Human optional sampling is allowed
only after the primary objective, following completed inspection.

P0 starts with one fixed seed (7). The planned follow-up seeds are 19 and 42;
record all three if the integration permits them. Do not replace difficult seeds
or alter assumptions after seeing outcomes. Parameter sensitivity uses the
nominal profile and one parameter's low/high values at a time with the same
scenario and seeds; keep sensitivity runs separate from the nominal comparison.

## Per-run evidence

Store immutable evidence under `evidence/<run_id>/`: code revisions, command,
configuration and model identifiers, dataset hashes, seed, policy, event stream,
execution/traversal evidence and an outcome record. Distinguish unavailable
evidence from a measured zero or a failed run.

Minimum outcome fields are run_id, policy, seed, mission_success,
primary_goal_completed, returned_to_base_within_tolerance,
verified_ground_traversal_under_model, no_budget_violation, termination_state,
reason_code, verified_ground_fraction, unsafe_step_count,
optional_tasks_accepted, optional_tasks_rejected, time_to_verified_route_s,
mission_duration_s, energy_est_wh, oxygen_est_l, replan_count,
replan_latency_ms and max_map_age_s. Define each measurement interval and retain
the event IDs from which it is computed; use null for unavailable metrics.

Preserve failures, aborts, timeouts and UNKNOWN outcomes in the final table.
Report planned N and observed N. Keep agent energy estimates separate: human
metabolic Wh and robot electrical Wh do not describe interchangeable resources.

## Isolation and acceptance

- Mission and planner consume public belief/observations only. Changing the
  hidden evaluator reference while holding public inputs fixed must not change
  their decisions.
- A proposed or illustrative profile does not become scientifically approved
  because a test passes. Record explicit review separately.
- A feasible plan cannot establish actual traversal, task completion or return.
- Current missing ROS discovery/completion/traversal inputs prevent claiming a
  complete benchmark through those inputs. Track that integration dependency.
- An offline replay must reproduce recorded events without a running backend
  and must remain labelled REPLAY; replay acceptance belongs to integration/UI.

## Review record

For each S-01 through S-08 acceptance case, record pending/pass/fail, reviewer,
run_id/evidence path, reason and correction owner. Implementation unit tests are
not a substitute for those reviews. No acceptance case is marked passed here.
