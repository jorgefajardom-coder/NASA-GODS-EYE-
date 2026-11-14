"""Synthetic exported-evidence fixtures; these are not mission run results."""

from copy import deepcopy
import hashlib
import json
from pathlib import Path

import pytest

from mge_mission.audit import EvidenceAudit
from mge_mission.benchmark import (CONTEXT_FIELDS, METRICS, PREDICATES,
                                   FrozenBenchmarkPlan, RunOutcome, ScientificBenchmark)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def codes(findings, severity=None):
    return {item["code"] for item in findings if severity is None or item["severity"] == severity}


@pytest.fixture
def plan_data():
    context = {name: "a" * 64 if name.endswith("_sha256") else "synthetic-fixture"
               for name in CONTEXT_FIELDS}
    context.update(profile_status="proposed", model_id="synthetic-model-v1",
                   reference_id="opaque-evaluator-identity-only")
    return {"schema_version": "1.0.0", "status": "frozen", "benchmark_id": "audit-unit-fixture",
            "frozen_at_utc": "2026-11-14T06:00:00Z", "hypotheses": ["Synthetic fixture only"],
            "planned_seeds": [7], "policies": ["A", "B", "C"], "experiment_kind": "nominal",
            "context": context, "metric_definitions": {name: "Synthetic test definition" for name in METRICS},
            "source_revision": "b" * 40, "source_manifest_sha256": "c" * 64}


@pytest.fixture
def plan(plan_data):
    return FrozenBenchmarkPlan.from_dict(plan_data)


def write_artifact(data, root, role, payload, *, name=None):
    filename = name or ("timeline.jsonl" if role == "timeline" else f"{role}.json")
    path = root / filename
    if role == "timeline":
        path.write_text("".join(json.dumps(event, allow_nan=False) + "\n" for event in payload), encoding="utf-8")
    else:
        path.write_text(json.dumps(payload, allow_nan=False), encoding="utf-8")
    data["artifacts"] = [item for item in data["artifacts"] if item["path"] != filename]
    data["artifacts"].append({"role": role, "path": filename, "sha256": digest(path)})
    return path


def fixture_execution(root, plan, *, status="SUCCESS", policy="A"):
    root.mkdir(parents=True, exist_ok=True)
    source, run_id = plan.to_dict(), f"synthetic-audit-{policy}-{status.lower()}"
    predicates = {name: True if status == "SUCCESS" else None for name in PREDICATES}
    if status == "FAILED":
        predicates["primary_goal_completed"] = False
    metrics = {name: None for name in METRICS}
    metrics.update(verified_ground_fraction=1.0, unsafe_step_count=0,
                   optional_tasks_accepted=0, optional_tasks_rejected=0,
                   time_to_verified_route_s=1.0, mission_duration_s=60.0,
                   energy_est_wh={"human_1": 10.0}, oxygen_est_l=2.0,
                   replan_count=0, max_map_age_s=0.0)
    data = {"run_id": run_id, "policy": policy, "seed": 7, "attempt": 1,
            "freeze_sha256": plan.freeze_sha256, "execution_kind": "SIMULATED_MISSION",
            "started_at_utc": "2026-11-14T07:00:00Z", "finished_at_utc": "2026-11-14T07:01:00Z",
            "outcome_status": status, "termination_state": "COMPLETE" if status == "SUCCESS" else "BLOCKED",
            "reason_code": "" if status == "SUCCESS" else "SYNTHETIC_OUTCOME",
            "predicates": predicates, "metrics": metrics,
            "command": ["synthetic-fixture-command"], "environment": {"kind": "pytest-fixture"},
            "metrics_unavailable": {"replan_latency_ms": "No replan occurred in this synthetic fixture."},
            "artifacts": [], "event_refs": ["start", "finish"], "experiment_kind": "nominal",
            "source_revision": source["source_revision"],
            "source_manifest_sha256": source["source_manifest_sha256"]}
    events = [{"run_id": run_id, "event_id": "start", "seq": 1,
               "event_type": "MISSION_STATE_CHANGED", "new_state": "ACTIVE"},
              {"run_id": run_id, "event_id": "task", "seq": 2,
               "event_type": "TASK_STATE_CHANGED", "new_state": "DONE"},
              {"run_id": run_id, "event_id": "finish", "seq": 3,
               "event_type": "MISSION_STATE_CHANGED", "new_state": data["termination_state"]}]
    execution = {"run_id": run_id, "execution_kind": "SIMULATED_MISSION",
                 "event_refs": ["start", "finish"], "predicates": deepcopy(predicates),
                 "command": ["synthetic-fixture-command"], "environment": {"kind": "pytest-fixture"}}
    traversal = {"run_id": run_id, "event_refs": ["finish"],
                 "executed_ground_distance_m": 20.0, "verified_ground_distance_m": 20.0,
                 "unsafe_step_count": 0, "all_executed_steps_checked": True,
                 "model_id": source["context"]["model_id"]}
    for role, payload in (("timeline", events), ("execution", execution), ("traversal", traversal)):
        write_artifact(data, root, role, payload)
    return data, events, execution, traversal


def audit(plan, data, root):
    outcome = RunOutcome.from_dict(data)
    assert not outcome.validation_findings, outcome.validation_findings
    return EvidenceAudit().audit(plan, outcome, root)


def test_complete_hashed_export_is_consistent_without_granting_approval(tmp_path, plan):
    data, _, _, _ = fixture_execution(tmp_path, plan)
    findings = audit(plan, data, tmp_path)
    assert findings == ()
    benchmark = ScientificBenchmark(plan)
    benchmark.add(RunOutcome.from_dict(data), findings)
    report = benchmark.summary()
    assert report["scientific_approval"] is False
    assert report["retained_rows"][0]["outcome"]["metrics"]["energy_est_wh"] == {"human_1": 10.0}
    assert plan.to_dict()["context"]["profile_status"] == "proposed"
    assert report["retained_rows"][0]["eligible"] is True


def test_unavailable_metric_requires_a_reason_but_is_never_replaced_by_zero(tmp_path, plan):
    data, _, _, _ = fixture_execution(tmp_path, plan)
    data["metrics_unavailable"] = {}
    findings = audit(plan, data, tmp_path)
    assert not codes(findings, "error")
    assert codes(findings, "warning") == {"METRIC_UNAVAILABLE_REASON_MISSING"}
    assert data["metrics"]["replan_latency_ms"] is None


@pytest.mark.parametrize("kind", ["tamper", "missing"])
def test_artifact_hash_and_presence_are_checked(tmp_path, plan, kind):
    data, _, _, _ = fixture_execution(tmp_path, plan)
    path = tmp_path / "execution.json"
    if kind == "tamper":
        path.write_text("{}", encoding="utf-8")
    else:
        path.unlink()
    findings = audit(plan, data, tmp_path)
    expected = "ARTIFACT_HASH_MISMATCH" if kind == "tamper" else "ARTIFACT_UNAVAILABLE_OR_UNSAFE"
    assert {expected, "EXECUTION_EVIDENCE_MISSING"} <= codes(findings, "error")


@pytest.mark.parametrize("path", ["../outside.json", "/tmp/outside.json", "C:/outside.json",
                                   "./execution.json", "nested/../execution.json", "a\\b.json",
                                   "reference/hidden.json", ".git/config", ".env"])
def test_noncanonical_private_and_escaping_artifact_paths_are_rejected(tmp_path, plan, path):
    data, _, _, _ = fixture_execution(tmp_path, plan)
    data["artifacts"].append({"role": "diagnostic", "path": path, "sha256": "d" * 64})
    assert "ARTIFACT_UNAVAILABLE_OR_UNSAFE" in codes(audit(plan, data, tmp_path), "error")


@pytest.mark.parametrize("target_kind", ["outside", "reference"])
def test_symlinks_cannot_open_external_or_hidden_reference_files(tmp_path, plan, monkeypatch, target_kind):
    root = tmp_path / "run"
    data, _, _, _ = fixture_execution(root, plan)
    secret = tmp_path / "outside.json" if target_kind == "outside" else root / "reference" / "hidden.json"
    secret.parent.mkdir(parents=True, exist_ok=True)
    secret.write_text('{"hidden_evaluator":true}', encoding="utf-8")
    alias = root / "public.json"
    try:
        alias.symlink_to(secret)
    except OSError as exc:
        pytest.skip(f"This host does not permit creating test symlinks: {exc}")
    data["artifacts"].append({"role": "diagnostic", "path": "public.json", "sha256": digest(secret)})
    original_open = Path.open

    def guarded_open(path, *args, **kwargs):
        if path.resolve() == secret.resolve():
            pytest.fail("The auditor attempted to read hidden or external evidence")
        return original_open(path, *args, **kwargs)

    monkeypatch.setattr(Path, "open", guarded_open)
    assert "ARTIFACT_UNAVAILABLE_OR_UNSAFE" in codes(audit(plan, data, root), "error")


def test_opaque_evaluator_identity_is_never_opened(tmp_path, plan_data, monkeypatch):
    secret = tmp_path / "evaluator.json"
    secret.write_text('{"never_load":true}', encoding="utf-8")
    plan_data["context"]["reference_id"] = str(secret)
    frozen = FrozenBenchmarkPlan.from_dict(plan_data)
    root = tmp_path / "run"
    data, _, _, _ = fixture_execution(root, frozen)
    original_open = Path.open

    def guarded_open(path, *args, **kwargs):
        if path.resolve() == secret.resolve():
            pytest.fail("Opaque evaluator identity was treated as a readable artifact")
        return original_open(path, *args, **kwargs)

    monkeypatch.setattr(Path, "open", guarded_open)
    assert audit(frozen, data, root) == ()


@pytest.mark.parametrize("change,expected", [("cross_run", "EVENT_RUN_MISMATCH"),
                                            ("conflict", "EVENT_ID_CONFLICT"),
                                            ("gap", "EVENT_SEQUENCE_INCOMPLETE")])
def test_timeline_rejects_foreign_conflicting_and_incomplete_events(tmp_path, plan, change, expected):
    data, events, _, _ = fixture_execution(tmp_path, plan)
    if change == "cross_run":
        events[0]["run_id"] = "foreign-run"
    elif change == "conflict":
        conflict = dict(events[1], new_state="CONFLICTING_STATE")
        events.insert(2, conflict)
    else:
        events[1]["seq"], events[2]["seq"] = 3, 4
    write_artifact(data, tmp_path, "timeline", events)
    assert expected in codes(audit(plan, data, tmp_path), "error")


def test_identical_event_redelivery_is_idempotent(tmp_path, plan):
    data, events, _, _ = fixture_execution(tmp_path, plan)
    events.insert(1, deepcopy(events[0]))
    write_artifact(data, tmp_path, "timeline", events)
    assert audit(plan, data, tmp_path) == ()


@pytest.mark.parametrize("target,expected", [("outcome", "EVENT_REFERENCE_UNRESOLVED"),
                                            ("execution", "EVIDENCE_EVENT_UNRESOLVED"),
                                            ("traversal", "EVIDENCE_EVENT_UNRESOLVED")])
def test_outcome_and_artifact_references_must_resolve(tmp_path, plan, target, expected):
    data, _, execution, traversal = fixture_execution(tmp_path, plan)
    if target == "outcome":
        data["event_refs"] = ["missing-event"]
    else:
        payload = execution if target == "execution" else traversal
        payload["event_refs"] = ["missing-event"]
        write_artifact(data, tmp_path, target, payload)
    assert expected in codes(audit(plan, data, tmp_path), "error")


@pytest.mark.parametrize("missing,expected", [("completion", "SUCCESS_EVENT_MISSING"),
                                             ("traversal", "TRAVERSAL_EVIDENCE_MISSING")])
def test_success_requires_recorded_completion_and_ground_traversal(tmp_path, plan, missing, expected):
    data, events, _, _ = fixture_execution(tmp_path, plan)
    if missing == "completion":
        events[-1]["new_state"] = "RETURNING"
        write_artifact(data, tmp_path, "timeline", events)
    else:
        data["artifacts"] = [item for item in data["artifacts"] if item["role"] != "traversal"]
    assert expected in codes(audit(plan, data, tmp_path), "error")


def test_zero_ground_distance_has_null_fraction_and_cannot_claim_unsafe_zero(tmp_path, plan):
    data, _, _, traversal = fixture_execution(tmp_path, plan, status="UNKNOWN")
    traversal.update(executed_ground_distance_m=0.0, verified_ground_distance_m=0.0,
                     unsafe_step_count=None, all_executed_steps_checked=False)
    data["metrics"].update(verified_ground_fraction=None, unsafe_step_count=None)
    data["metrics_unavailable"].update(verified_ground_fraction="No ground traversal occurred.",
                                       unsafe_step_count="No ground steps were observed.")
    write_artifact(data, tmp_path, "traversal", traversal)
    assert not codes(audit(plan, data, tmp_path), "error")
    data["metrics"].update(verified_ground_fraction=0.0, unsafe_step_count=0)
    findings = audit(plan, data, tmp_path)
    assert {"UNDEFINED_VERIFIED_FRACTION", "UNOBSERVED_UNSAFE_ZERO"} <= codes(findings, "error")


def test_verified_fraction_is_executed_distance_weighted_not_an_average_of_segments(tmp_path, plan):
    data, _, _, traversal = fixture_execution(tmp_path, plan, status="FAILED")
    # One verified metre and nine unverified metres: segment-count mean .5 is wrong.
    traversal.update(executed_ground_distance_m=10.0, verified_ground_distance_m=1.0,
                     unsafe_step_count=None, all_executed_steps_checked=False)
    data["metrics"].update(verified_ground_fraction=0.1, unsafe_step_count=None)
    data["metrics_unavailable"]["unsafe_step_count"] = "The unverified segment was not fully checked."
    write_artifact(data, tmp_path, "traversal", traversal)
    assert not codes(audit(plan, data, tmp_path), "error")
    data["metrics"]["verified_ground_fraction"] = 0.5
    assert "VERIFIED_FRACTION_MISMATCH" in codes(audit(plan, data, tmp_path), "error")


def test_multiple_traversal_aggregates_are_rejected_instead_of_silently_combined(tmp_path, plan):
    data, _, _, traversal = fixture_execution(tmp_path, plan)
    write_artifact(data, tmp_path, "traversal", traversal, name="second-traversal.json")
    assert "AMBIGUOUS_TRAVERSAL_EVIDENCE" in codes(audit(plan, data, tmp_path), "error")


def test_multiple_execution_declarations_are_ambiguous(tmp_path, plan):
    data, _, execution, _ = fixture_execution(tmp_path, plan)
    write_artifact(data, tmp_path, "execution", execution, name="second-execution.json")
    assert "AMBIGUOUS_EXECUTION_EVIDENCE" in codes(audit(plan, data, tmp_path), "error")


@pytest.mark.parametrize("key,value,expected", [("verified_ground_distance_m", 21.0, "TRAVERSAL_DISTANCES_INVALID"),
                                               ("unsafe_step_count", True, "UNSAFE_COUNT_INVALID"),
                                               ("all_executed_steps_checked", False, "UNOBSERVED_UNSAFE_ZERO"),
                                               ("model_id", "different-model", "TRAVERSAL_MODEL_MISMATCH")])
def test_traversal_claims_require_consistent_model_and_checked_observations(tmp_path, plan, key, value, expected):
    data, _, _, traversal = fixture_execution(tmp_path, plan)
    traversal[key] = value
    write_artifact(data, tmp_path, "traversal", traversal)
    assert expected in codes(audit(plan, data, tmp_path), "error")


def test_failed_and_unknown_executions_remain_in_the_benchmark(tmp_path, plan):
    benchmark = ScientificBenchmark(plan)
    for policy, status in (("A", "SUCCESS"), ("B", "FAILED"), ("C", "UNKNOWN")):
        root = tmp_path / policy
        data, _, _, _ = fixture_execution(root, plan, status=status, policy=policy)
        findings = audit(plan, data, root)
        assert not codes(findings, "error")
        benchmark.add(RunOutcome.from_dict(data), findings)
    report = benchmark.summary()
    assert len(report["retained_rows"]) == 3
    assert report["policies"]["A"]["successes"] == 1
    assert report["policies"]["B"]["failures"] == 1
    assert report["policies"]["C"]["unknowns"] == 1
    assert report["scientific_approval"] is False and not report["comparison_ready"]


@pytest.mark.parametrize("kind", ["MODEL_CHECK", "REPLAY", "SOFTWARE_TEST"])
def test_nonmission_artifacts_are_not_opened_or_counted_as_new_missions(tmp_path, plan, monkeypatch, kind):
    data, _, _, _ = fixture_execution(tmp_path, plan)
    data["execution_kind"] = kind
    outcome = RunOutcome.from_dict(data)
    monkeypatch.setattr(Path, "open", lambda *args, **kwargs: pytest.fail("Nonmission evidence was opened"))
    findings = EvidenceAudit().audit(plan, outcome, tmp_path)
    assert codes(findings, "error") == {"NOT_MISSION_EVIDENCE"}
    benchmark = ScientificBenchmark(plan)
    benchmark.add(outcome, findings)
    report = benchmark.summary()
    assert report["policies"]["A"]["observed_n"] == 0
    assert len(report["retained_rows"]) == 1 and not report["retained_rows"][0]["eligible"]


@pytest.mark.parametrize("key,value,expected", [("source_revision", "d" * 40, "SOURCE_IDENTITY_MISMATCH"),
                                               ("source_manifest_sha256", "e" * 64, "SOURCE_IDENTITY_MISMATCH"),
                                               ("started_at_utc", "2026-11-14T05:00:00Z", "EXECUTION_BEFORE_FREEZE"),
                                               ("freeze_sha256", "0" * 64, "FROZEN_CONTEXT_MISMATCH"),
                                               ("experiment_kind", "sensitivity", "EXPERIMENT_KIND_MISMATCH"),
                                               ("seed", 19, "UNPLANNED_POLICY_OR_SEED")])
def test_frozen_source_identity_and_execution_order_are_enforced(tmp_path, plan, key, value, expected):
    data, _, _, _ = fixture_execution(tmp_path, plan)
    data[key] = value
    assert expected in codes(audit(plan, data, tmp_path), "error")


def test_execution_declaration_cannot_contradict_outcome_predicates(tmp_path, plan):
    data, _, execution, _ = fixture_execution(tmp_path, plan)
    execution["predicates"]["primary_goal_completed"] = False
    write_artifact(data, tmp_path, "execution", execution)
    assert "PREDICATE_EVIDENCE_MISMATCH" in codes(audit(plan, data, tmp_path), "error")


@pytest.mark.parametrize("field,expected", [("command", "EXECUTION_COMMAND_MISSING"),
                                           ("environment", "EXECUTION_ENVIRONMENT_MISSING")])
def test_actual_execution_command_and_environment_are_required(tmp_path, plan, field, expected):
    data, _, _, _ = fixture_execution(tmp_path, plan)
    del data[field]
    assert expected in codes(audit(plan, data, tmp_path), "error")


def test_execution_record_from_another_run_cannot_support_this_outcome(tmp_path, plan):
    data, _, execution, _ = fixture_execution(tmp_path, plan)
    execution["run_id"] = "another-run"
    write_artifact(data, tmp_path, "execution", execution)
    assert {"EVIDENCE_RECORD_INVALID", "EXECUTION_EVIDENCE_MISSING"} <= codes(audit(plan, data, tmp_path), "error")


def test_nonfinite_json_in_hashed_timeline_is_not_accepted(tmp_path, plan):
    data, _, _, _ = fixture_execution(tmp_path, plan)
    path = tmp_path / "timeline.jsonl"
    path.write_text('{"run_id":"fixture","event_id":"bad","seq":NaN}\n', encoding="utf-8")
    next(item for item in data["artifacts"] if item["role"] == "timeline")["sha256"] = digest(path)
    assert "TIMELINE_INVALID" in codes(audit(plan, data, tmp_path), "error")
