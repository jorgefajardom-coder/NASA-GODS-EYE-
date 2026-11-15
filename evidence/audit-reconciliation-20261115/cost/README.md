# Published-main cost conformance diagnostic

Classification: **new synthetic model-comparison execution**. Run ID:
`audit-reconciliation-cost-20261115`. The planner source is the exact published
revision `6bcf208868e37b7e15e9189fac11de96e7414eff`.

The existing comparison CLI materialized that Git snapshot under the ignored
`tmp/` directory, generated and verified its source manifest and imported the
verified planner package. The temporary snapshot was then removed by the CLI.
No new planner implementation was introduced in a mission module. Source
revision/content hashes in the report make the snapshot reproducible from Git.

```sh
python scripts/check_planner_conformance.py --planner-ref 6bcf208868e37b7e15e9189fac11de96e7414eff --profiles config/science_profiles.proposed.json --run-id audit-reconciliation-cost-20261115 --output-dir evidence/audit-reconciliation-20261115/cost
```

The recorded output directory is immutable. Reproduction must select a new
output directory and run ID. The exact Python executable/command, versions,
input hashes and output hashes are retained in [provenance.json](provenance.json).

| Case | Fresh outcome |
|---|---|
| human_flat | DISAGREE |
| human_slope | DISAGREE |
| human_service_wait | DISAGREE |
| rover_flat | AGREE |
| rover_slope | DISAGREE |
| rover_service_wait | DISAGREE |
| drone_observe | DISAGREE |

Result: **COMPLETED**, exit code 0; **one agreement, six disagreements, zero
non-feasible cases and zero errors**. All seven planner candidates were feasible
under their declared search model. Authorization remains **BLOCKED** with
`MODEL_DISAGREEMENT`; no scientific/profile approval changed. A successful CLI
execution records the disagreements; it does not authorize a route.

Artifacts:

- [conformance.json](conformance.json): newly generated comparisons, exact inputs,
  per-cost/reserve comparisons and planner/science provenance.
- [command.log](command.log): actual command output.
- [provenance.json](provenance.json): environment, input/output hashes, result and
  limits.

The planner source-manifest SHA-256 is
`b813d4f051a87b3b2379d73297fb29e875272102ff0725630f2a2af29915dd43`.
The scientific model-source SHA-256 is
`178785d57ed3fa478061c451e774bc0686a7a7c486a9c57820a517104fe2be52`.
Full file/profile hashes are in the linked JSON artifacts.

The concurrent working tree contained reconciliation work. This comparison
uses the **published Git planner snapshot**, not uncommitted experimental
implementation changes. The supplied scientific profile registry retains its
proposed status and recorded hash. This run covers seven controlled analytic
cases; the complete activity/connector/partial-service vector set, real context
binding, executor debits and integrated mission acceptance remain pending.

This report is newly executed evidence even though its aggregate counts match
an earlier comparison. Existing reports are preserved. It is no mission run,
NASA observation, completed task, three-agent execution or A/B/C result. See the
[proposed context and execution closure](../../../docs/audit_cost_execution_gaps.md).
