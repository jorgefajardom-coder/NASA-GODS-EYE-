"""Synthetic reducer fixtures only; no integrated mission outcomes are generated."""

from copy import deepcopy

import pytest

from mge_mission.benchmark import (CONTEXT_FIELDS, METRICS, PREDICATES,
                                   FrozenBenchmarkPlan, RunOutcome, ScientificBenchmark)


@pytest.fixture
def plan_data():
    context = {key: "a" * 64 if key.endswith("_sha256") else "fixture"
               for key in CONTEXT_FIELDS}
    context["profile_status"] = "illustrative"
    return {"schema_version": "1.0.0", "status": "frozen", "benchmark_id": "synthetic-protocol-test",
            "frozen_at_utc": "2026-11-14T06:00:00Z", "hypotheses": ["Fixture hypothesis only"],
            "planned_seeds": [7], "policies": ["A", "B", "C"], "experiment_kind": "nominal",
            "context": context, "metric_definitions": {key: "Synthetic test measurement definition" for key in METRICS},
            "source_revision": "b" * 40, "source_manifest_sha256": "c" * 64}


@pytest.fixture
def plan(plan_data):
    return FrozenBenchmarkPlan.from_dict(plan_data)


def outcome_data(plan, policy="A", seed=7, attempt=1, status="SUCCESS"):
    predicates = {key: True if status == "SUCCESS" else None for key in PREDICATES}
    if status in {"FAILED", "TIMEOUT"}:
        predicates = {key: key != "primary_goal_completed" for key in PREDICATES}
    source = plan.to_dict()
    return {"run_id": f"fixture-{policy}-{seed}-{attempt}", "policy": policy, "seed": seed,
            "attempt": attempt, "freeze_sha256": plan.freeze_sha256, "execution_kind": "SIMULATED_MISSION",
            "started_at_utc": "2026-11-14T07:00:00Z", "finished_at_utc": "2026-11-14T07:01:00Z",
            "outcome_status": status, "termination_state": "COMPLETE" if status == "SUCCESS" else "BLOCKED",
            "reason_code": "" if status == "SUCCESS" else "FIXTURE_OUTCOME", "predicates": predicates,
            "metrics": {key: None for key in METRICS},
            "artifacts": [{"role": role, "path": f"{role}.json", "sha256": "d" * 64}
                          for role in ("execution", "timeline", "traversal")],
            "event_refs": ["fixture-event-1"], "experiment_kind": "nominal",
            "source_revision": source["source_revision"], "source_manifest_sha256": source["source_manifest_sha256"]}


def add(benchmark, data, findings=()):
    return benchmark.add(RunOutcome.from_dict(data), findings)


def test_empty_report_preserves_planned_denominator_and_missing_uncertainty(plan):
    report = ScientificBenchmark(plan).summary()
    assert report["comparison_ready"] is False
    assert report["scientific_approval"] is False
    for counts in report["policies"].values():
        assert counts["planned_n"] == counts["success_denominator"] == 1
        assert counts["observed_n"] == counts["successes"] == 0
        assert counts["missing"] == 1
        assert (counts["success_lower_bound"], counts["success_upper_bound"]) == (0, 1)


def test_complete_paired_actual_execution_records_are_comparable_without_approving_science(plan):
    benchmark = ScientificBenchmark(plan)
    for policy in "ABC":
        add(benchmark, outcome_data(plan, policy))
    report = benchmark.summary()
    assert report["comparison_ready"] is True
    assert report["paired_complete_seeds"] == [7]
    assert report["scientific_approval"] is False
    assert report["policies"]["A"]["successes"] == 1
    assert report["policies"]["A"]["success_lower_bound"] == 1


def test_omitting_filesystem_audit_cannot_make_metadata_only_comparison_ready(plan):
    benchmark = ScientificBenchmark(plan)
    for policy in "ABC":
        benchmark.add(RunOutcome.from_dict(outcome_data(plan, policy)))
    report = benchmark.summary()
    assert report["comparison_ready"] is False
    assert report["paired_complete_seeds"] == []
    assert all(row["mission_success"] is None for row in report["retained_rows"])
    assert all(any(f["code"] == "EVIDENCE_AUDIT_NOT_PERFORMED" for f in row["findings"])
               for row in report["retained_rows"])


def test_failures_timeouts_and_unknowns_are_retained_with_explicit_bounds(plan):
    benchmark = ScientificBenchmark(plan)
    for policy, status in zip("ABC", ("FAILED", "TIMEOUT", "UNKNOWN")):
        add(benchmark, outcome_data(plan, policy, status=status))
    report = benchmark.summary()
    assert len(report["retained_rows"]) == 3
    assert report["policies"]["A"]["failures"] == 1
    assert report["policies"]["B"]["failures"] == report["policies"]["B"]["timeouts"] == 1
    assert report["policies"]["C"]["unknowns"] == 1
    assert report["policies"]["C"]["success_upper_bound"] == 1
    assert not report["comparison_ready"]


def test_one_false_predicate_demonstrates_failure_even_when_other_evidence_is_null(plan):
    data = outcome_data(plan, status="UNKNOWN")
    data["predicates"]["primary_goal_completed"] = False
    benchmark = ScientificBenchmark(plan)
    add(benchmark, data)
    report = benchmark.summary()
    assert report["retained_rows"][0]["mission_success"] is False
    assert report["policies"]["A"]["failures"] == 1
    assert not report["comparison_ready"]


@pytest.mark.parametrize("change", [
    {"status": "draft"}, {"planned_seeds": [True]}, {"planned_seeds": []},
    {"planned_seeds": [7, 7]}, {"policies": ["A", "B"]}, {"source_revision": "short"},
    {"hypotheses": []}, {"frozen_at_utc": "2026-11-14T06:00:00"},
])
def test_draft_or_incomplete_plans_cannot_become_frozen(plan_data, change):
    plan_data.update(change)
    with pytest.raises(ValueError):
        FrozenBenchmarkPlan.from_dict(plan_data)


def test_hash_is_stable_for_key_order_and_freezes_nested_context(plan_data):
    first = FrozenBenchmarkPlan.from_dict(plan_data)
    reordered = dict(reversed(list(plan_data.items())))
    assert FrozenBenchmarkPlan.from_dict(reordered).freeze_sha256 == first.freeze_sha256
    plan_data["context"]["scenario_id"] = "changed"
    assert first.to_dict()["context"]["scenario_id"] == "fixture"
    detached = first.to_dict()
    detached["metric_definitions"][METRICS[0]] = "changed"
    assert first.to_dict()["metric_definitions"][METRICS[0]] != "changed"
    assert FrozenBenchmarkPlan.from_dict(plan_data).freeze_sha256 != first.freeze_sha256


def test_freeze_hash_round_trip_validates_optional_claim(plan):
    data = plan.to_dict()
    data["freeze_sha256"] = plan.freeze_sha256
    assert FrozenBenchmarkPlan.from_dict(data).freeze_sha256 == plan.freeze_sha256
    data["freeze_sha256"] = "0" * 64
    with pytest.raises(ValueError):
        FrozenBenchmarkPlan.from_dict(data)


@pytest.mark.parametrize("field,value,code", [
    ("freeze_sha256", "0" * 64, "FROZEN_CONTEXT_MISMATCH"),
    ("seed", 19, "UNPLANNED_SEED"),
    ("experiment_kind", "sensitivity", "EXPERIMENT_KIND_MISMATCH"),
    ("source_revision", "e" * 40, "SOURCE_IDENTITY_MISMATCH"),
    ("started_at_utc", "2026-11-14T05:00:00Z", "EXECUTION_PRECEDES_FREEZE"),
])
def test_protocol_drift_is_retained_with_diagnostics(plan, field, value, code):
    benchmark = ScientificBenchmark(plan)
    data = outcome_data(plan)
    data[field] = value
    add(benchmark, data)
    row = benchmark.summary()["retained_rows"][0]
    assert any(f["code"] == code for f in row["findings"])
    assert not row["eligible"]
    assert not benchmark.summary()["comparison_ready"]


@pytest.mark.parametrize("execution_kind", ["MODEL_CHECK", "SOFTWARE_TEST", "REPLAY"])
def test_model_tests_and_replay_never_fill_observed_mission_slots(plan, execution_kind):
    data = outcome_data(plan)
    data["execution_kind"] = execution_kind
    benchmark = ScientificBenchmark(plan)
    add(benchmark, data)
    report = benchmark.summary()
    assert report["policies"]["A"]["observed_n"] == 0
    assert report["policies"]["A"]["missing"] == 1
    assert len(report["retained_rows"]) == 1
    assert not report["retained_rows"][0]["eligible"]
    assert report["retained_rows"][0]["mission_success"] is None


def test_success_requires_complete_boolean_predicates_and_traversal_artifact(plan):
    data = outcome_data(plan)
    data["predicates"]["verified_ground_traversal_under_model"] = None
    data["artifacts"] = [a for a in data["artifacts"] if a["role"] != "traversal"]
    benchmark = ScientificBenchmark(plan)
    add(benchmark, data)
    report = benchmark.summary()
    assert report["policies"]["A"]["successes"] == 0
    assert report["policies"]["A"]["invalid_n"] == 1
    assert {f["code"] for f in report["retained_rows"][0]["findings"]} >= {"UNSUPPORTED_SUCCESS", "EXECUTION_EVIDENCE_MISSING"}


def test_external_audit_failure_prevents_comparison_and_warning_is_retained(plan):
    benchmark = ScientificBenchmark(plan)
    add(benchmark, outcome_data(plan), [{"severity": "error", "code": "HASH_MISMATCH", "detail": "Fixture tamper finding."}])
    report = benchmark.summary()
    assert report["policies"]["A"]["invalid_n"] == 1
    assert report["policies"]["A"]["success_upper_bound"] == 1
    assert not report["comparison_ready"]
    other = ScientificBenchmark(plan)
    warning = {"severity": "warning", "code": "UNAVAILABLE_METRICS", "detail": "Null values remain unavailable."}
    add(other, outcome_data(plan), [warning])
    assert other.summary()["retained_rows"][0]["findings"] == [warning]


def test_retries_do_not_fill_missing_primary_or_replace_primary_failure(plan):
    benchmark = ScientificBenchmark(plan)
    add(benchmark, outcome_data(plan, attempt=2))
    assert benchmark.summary()["policies"]["A"]["missing"] == 1
    assert benchmark.summary()["policies"]["A"]["retry_rows"] == 1
    assert benchmark.summary()["retained_rows"][0]["valid"]
    assert not benchmark.summary()["retained_rows"][0]["eligible"]
    add(benchmark, outcome_data(plan, status="FAILED"))
    report = benchmark.summary()
    assert report["policies"]["A"]["failures"] == 1
    assert report["policies"]["A"]["successes"] == 0
    assert len(report["retained_rows"]) == 2


def test_identical_duplicate_is_idempotent_conflicting_id_is_retained_diagnostically(plan):
    benchmark = ScientificBenchmark(plan)
    original = outcome_data(plan)
    assert add(benchmark, original)
    assert not add(benchmark, deepcopy(original))
    conflict = deepcopy(original)
    conflict["reason_code"] = "DIFFERENT_PAYLOAD"
    assert not add(benchmark, conflict)
    report = benchmark.summary()
    assert len(report["retained_rows"]) == 1
    assert report["retained_rows"][0]["outcome"] == original
    assert report["diagnostics"][0]["rejected_outcome"] == conflict
    assert report["policies"]["A"]["invalid_n"] == 1


def test_distinct_run_ids_cannot_compete_for_best_result_in_same_attempt(plan):
    benchmark = ScientificBenchmark(plan)
    add(benchmark, outcome_data(plan, status="FAILED"))
    competing = outcome_data(plan)
    competing["run_id"] = "competing-success"
    assert add(benchmark, competing)
    report = benchmark.summary()
    assert len(report["retained_rows"]) == 2
    assert report["policies"]["A"]["invalid_n"] == 1
    assert report["policies"]["A"]["successes"] == 0
    assert all(not row["eligible"] for row in report["retained_rows"])
    assert [row["primary_attempt"] for row in report["retained_rows"]] == [True, False]


def test_idempotent_record_does_not_suppress_later_evidence_audit_errors(plan):
    benchmark = ScientificBenchmark(plan)
    data = outcome_data(plan)
    assert add(benchmark, data)
    assert not add(benchmark, data, [{"severity": "error", "code": "HASH_MISMATCH", "detail": "Re-audit found changed execution evidence."}])
    report = benchmark.summary()
    assert len(report["retained_rows"]) == 1
    assert report["policies"]["A"]["invalid_n"] == 1
    assert any(f["code"] == "HASH_MISMATCH" for f in report["retained_rows"][0]["findings"])


@pytest.mark.parametrize("metric,value", [
    ("unsafe_step_count", True), ("optional_tasks_accepted", -1),
    ("replan_count", 1.5), ("verified_ground_fraction", 1.1),
    ("mission_duration_s", -0.1), ("energy_est_wh", 12.5),
    ("energy_est_wh", {"human_1": True}), ("energy_est_wh", {"rover_1": -1}),
])
def test_invalid_finite_metrics_are_preserved_and_ineligible(plan, metric, value):
    data = outcome_data(plan)
    data["metrics"][metric] = value
    outcome = RunOutcome.from_dict(data)
    assert any(f["code"] == "INVALID_METRIC_VALUE" for f in outcome.validation_findings)
    benchmark = ScientificBenchmark(plan)
    benchmark.add(outcome)
    assert benchmark.summary()["retained_rows"][0]["outcome"]["metrics"][metric] == value
    assert benchmark.summary()["policies"]["A"]["invalid_n"] == 1


def test_null_metrics_remain_null_and_agent_energy_is_never_pooled(plan):
    data = outcome_data(plan)
    data["metrics"]["energy_est_wh"] = {"human_1": 12.5, "rover_1": 30, "drone_1": None}
    outcome = RunOutcome.from_dict(data)
    assert outcome.validation_findings == ()
    data["metrics"]["energy_est_wh"]["human_1"] = 999
    detached = outcome.to_dict()
    assert detached["metrics"]["energy_est_wh"]["human_1"] == 12.5
    assert detached["metrics"]["unsafe_step_count"] is None
    detached["artifacts"][0]["path"] = "changed"
    assert outcome.to_dict()["artifacts"][0]["path"] != "changed"


@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf")])
def test_nonfinite_input_is_rejected_before_json_serialization(plan, value):
    data = outcome_data(plan)
    data["metrics"]["energy_est_wh"] = {"human_1": value}
    with pytest.raises(ValueError):
        RunOutcome.from_dict(data)


def test_each_planned_seed_needs_all_three_first_attempts(plan_data):
    plan_data["planned_seeds"] = [7, 19]
    plan = FrozenBenchmarkPlan.from_dict(plan_data)
    benchmark = ScientificBenchmark(plan)
    for policy in "ABC":
        add(benchmark, outcome_data(plan, policy, 7))
    add(benchmark, outcome_data(plan, "A", 19))
    report = benchmark.summary()
    assert report["paired_complete_seeds"] == [7]
    assert not report["comparison_ready"]
    assert report["policies"]["A"]["success_denominator"] == 2
    assert report["policies"]["B"]["success_lower_bound"] == 0.5
    assert report["policies"]["B"]["success_upper_bound"] == 1


def test_incomplete_schema_is_retained_instead_of_fabricating_fields(plan):
    outcome = RunOutcome.from_dict({"run_id": "incomplete-external-record"})
    assert outcome.validation_findings
    benchmark = ScientificBenchmark(plan)
    benchmark.add(outcome)
    report = benchmark.summary()
    assert report["retained_rows"][0]["outcome"] == {"run_id": "incomplete-external-record"}
    assert report["policies"]["A"]["observed_n"] == 0


def test_arbitrary_finite_invalid_field_types_are_retained_without_parser_crashes(plan):
    invalid = {"run_id": "bad-types", "policy": [], "seed": {}, "attempt": True,
               "termination_state": [], "outcome_status": {}, "predicates": [],
               "metrics": [], "artifacts": {}, "event_refs": [False]}
    outcome = RunOutcome.from_dict(invalid)
    benchmark = ScientificBenchmark(plan)
    assert benchmark.add(outcome)
    assert benchmark.summary()["retained_rows"][0]["outcome"] == invalid
    assert not benchmark.summary()["comparison_ready"]
