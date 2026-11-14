# Frozen benchmark evidence and audit

Status: executable consistency tools; no integrated A/B/C results exist.

These tools consume externally recorded executions. They never run a mission,
approve profiles, infer traversal from a plan, or convert a replay/model check
into a new execution. Hashes establish consistency and traceability, rather than
independent proof of physical execution or scientific validity.

## Freeze before execution

Fill [the plan template](../config/benchmark_plan.template.json) with actual
common-input hashes, source revision/manifest, model, opaque evaluator-reference
ID and metric definitions. The mission configuration hash covers base/goal,
budgets, reserves, tolerance, time step and other common decisions. Separate
hashes identify public prior/initial belief, dataset manifest, profiles,
observation model, task generator and model source.

Keep common inputs identical for A/B/C. Choose seeds before outcomes; the draft
starts with seed 7 and mentions 19/42 only as possible preregistered follow-ups.
Use separate frozen plans for nominal and sensitivity experiments; record the
sensitivity parameter/value in context. A model ID alone does not identify
coefficients. Profile approval status is preserved.

After filling and reviewing the protocol, explicitly set status to frozen and
record its UTC freeze timestamp. The API computes canonical JSON SHA-256 over
the full plan, excluding an optional self-reported freeze hash. Changing common
inputs, definitions, seeds or hypotheses creates a different protocol. The
supplied draft intentionally fails this readiness gate.

## Export every attempt

Each actual attempt uses [the outcome template](../config/benchmark_outcome.template.json):
unique run ID, policy, seed, attempt, freeze hash, source identity, actual
command/environment, UTC interval, termination/reason, four boolean-or-null
predicates, nullable metrics and hashed evidence references.

SIMULATED_MISSION describes an actual simulated execution. MODEL_CHECK,
SOFTWARE_TEST and REPLAY are not eligible new attempts. Retain retries with new
run IDs and increasing attempt numbers; never replace an unfavorable first
attempt. Per-agent energy keeps human metabolic Wh and robot electrical Wh
separate. Null means unavailable and needs an explanation; zero requires an
instrumented observation. Ground verification is weighted by executed distance
using knowledge available at traversal time, and is undefined for zero distance.

## Evidence accepted by v1

Artifacts use relative POSIX paths, SHA-256 and a role. The auditor reads text
exports confined to the supplied run directory. Escaped/symlinked evaluator
reference/private paths are rejected. The opaque reference ID is never opened.

- timeline: ordered JSONL events or JSON event array with run_id, event_id and
  seq starting at one. Identical duplicate deliveries are idempotent; conflicts,
  gaps and unresolved references are findings.
- execution: one aggregate JSON object with run_id, execution_kind, matching
  predicates and event_refs resolving in the timeline.
- traversal: at most one aggregate JSON object with run_id, model_id,
  executed_ground_distance_m, verified_ground_distance_m, unsafe_step_count,
  all_executed_steps_checked and event_refs. Success requires this artifact,
  full verification, zero checked unsafe steps and a COMPLETE event.
- Optional metrics/environment/configuration/diagnostic text may support the
  record, but cannot replace execution/traversal evidence.

Export traversal chunks as one distance-weighted aggregate before using v1.
The auditor checks declarations and consistency; it does not recompute
perception or vehicle dynamics.

## API and command

Use FrozenBenchmarkPlan, RunOutcome and ScientificBenchmark from
mge_mission.benchmark, and EvidenceAudit from mge_mission.audit. Pass the
auditor's findings explicitly to add; omission blocks comparison eligibility.

```sh
python scripts/audit_benchmark.py --plan path/to/frozen-plan.json \
  --outcome evidence/run-A/outcome.json \
  --outcome evidence/run-B/outcome.json \
  --outcome evidence/run-C/outcome.json \
  --output-dir evidence/new-audit
```

Existing reports are not overwritten. Exit 2 means the plan is not ready; exit
1 means input/evidence errors are retained. With no supplied runs, a valid plan
reports NO_EXECUTIONS and zero observations.

Reports retain planned/observed/invalid/missing attempts, failures, unknowns,
timeouts and bounds using planned N. Valid retries stay visible but do not
improve the primary comparison. Pairing requires A/B/C first attempts for each
planned seed. comparison_ready means complete, consistent comparison inputs.
scientific_approval remains false: the tool does not grant human approval.
