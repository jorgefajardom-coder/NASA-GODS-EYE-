"""Software fixtures only; no fixture is a submitted mission result."""

from dataclasses import replace
import hashlib
import json

import pytest

from mge_mission.audit import EvidenceAudit
from mge_mission.benchmark import CONTEXT_FIELDS, METRICS, FrozenBenchmarkPlan
from mge_mission.models import CostEstimate
from mge_mission.recorder import EvidenceRecorder, ExecutedCost, TraversalClosure, TraversalRecord
from mge_mission.types import MissionEvent, MissionEvidence, ObservedTask, Point, TaskEvidence


def event(seq=1, time=0, state="ACTIVE"):
    return MissionEvent("fixture", f"e{seq}", seq, "public-observation", "MISSION_STATE_CHANGED",
                        "", "human_1", 1, "route", "", state, "", "", time)


def recorder():
    value = EvidenceRecorder("fixture", "fixture-model", execution_kind="SIMULATED_MISSION")
    value.record_event(event())
    value.record_event(event(2, 10, "COMPLETE"))
    return value


def metadata(status="UNKNOWN"):
    return dict(policy="A", seed=7, attempt=1, freeze_sha256="a" * 64,
                started_at_utc="2026-11-14T08:00:00Z", finished_at_utc="2026-11-14T08:01:00Z",
                outcome_status=status, termination_state="COMPLETE", reason_code="FIXTURE",
                experiment_kind="nominal", source_revision="b" * 40,
                source_manifest_sha256="c" * 64, command=["pytest-fixture"],
                environment={"kind": "software-test-fixture"})


def step(safe=True):
    return TraversalRecord("s1", "fixture", "human_1", 1, "route", "e2", 5, safe)


def cost():
    return ExecutedCost("c1", "fixture", "human_1", "human", "e2", "movement", 0, 10,
                        CostEstimate(10, 2, 1))


def test_export_round_trip_audit_and_no_overwrite(tmp_path):
    context = {key: "a" * 64 if key.endswith("_sha256") else "fixture" for key in CONTEXT_FIELDS}
    context.update(model_id="fixture-model", profile_status="proposed")
    plan = FrozenBenchmarkPlan.from_dict(dict(
        schema_version="1.0.0", status="frozen", benchmark_id="fixture",
        frozen_at_utc="2026-11-14T07:00:00Z", hypotheses=["software fixture"],
        planned_seeds=[7], policies=["A", "B", "C"], experiment_kind="nominal", context=context,
        source_revision="b" * 40, source_manifest_sha256="c" * 64,
        metric_definitions={key: "fixture" for key in METRICS}))
    value = recorder()
    value.record_traversal(step())
    value.close_traversal(TraversalClosure("close", "fixture", "e2", 1, 5))
    value.record_cost(cost())
    value.record_predicates(MissionEvidence("p1", "fixture", 1, "route", 10,
                                           True, True, True, True), "e2")
    data = metadata("SUCCESS")
    data["freeze_sha256"] = plan.freeze_sha256
    result = value.export(tmp_path / "run", data)
    assert EvidenceAudit().audit(plan, result, tmp_path / "run") == ()
    assert result.to_dict()["metrics"]["energy_est_wh"] == {"human_1": 2}
    for artifact in result.to_dict()["artifacts"]:
        assert hashlib.sha256((tmp_path / "run" / artifact["path"]).read_bytes()).hexdigest() == artifact["sha256"]
    assert json.loads((tmp_path / "run/outcome.json").read_text())["predicates"]["primary_goal_completed"]
    with pytest.raises(ValueError, match="sealed"):
        value.record_event(event(3, 11))
    with pytest.raises(FileExistsError):
        recorder().export(tmp_path / "run", metadata())


def test_delivery_deduplication_and_conflicts():
    value = recorder()
    value.record_event(event(2, 10, "COMPLETE"))
    value.record_traversal(step())
    value.record_traversal(step())
    with pytest.raises(ValueError, match="Conflicting"):
        value.record_traversal(replace(step(), distance_m=6))
    with pytest.raises(ValueError):
        value.record_event(event(4, 20))
    with pytest.raises(ValueError):
        value.record_event(event(3, 9))
    with pytest.raises(ValueError):
        value.record_traversal(replace(step(), evidence_id="other", map_version=2))
    with pytest.raises(ValueError):
        value.record_event(replace(event(3, 11), run_id="other"))


def test_costs_cannot_overlap_or_assign_oxygen_to_robots(tmp_path):
    value = recorder()
    value.record_cost(cost())
    value.record_cost(cost())
    with pytest.raises(ValueError, match="overlap"):
        value.record_cost(replace(cost(), evidence_id="service", phase="service"))
    with pytest.raises(ValueError, match="oxygen"):
        value.record_cost(replace(cost(), kind="rover"))
    with pytest.raises(ValueError, match="Completion event"):
        value.record_cost(replace(cost(), finished_sim_s=11, cost=CostEstimate(11, 2, 1)))
    result = value.export(tmp_path / "run", metadata()).to_dict()
    assert result["metrics"]["energy_est_wh"] == {"human_1": 2}
    assert result["metrics"]["oxygen_est_l"] == 1
    assert result["metrics"]["unsafe_step_count"] is None
    assert all(x is None for x in result["predicates"].values())


@pytest.mark.parametrize("safe,closure", [(True, False), (None, True)])
def test_missing_checks_or_closure_cannot_become_verified_success(tmp_path, safe, closure):
    value = recorder()
    value.record_traversal(step(safe))
    if closure:
        value.close_traversal(TraversalClosure("close", "fixture", "e2", 1, 5))
    value.record_predicates(MissionEvidence("p", "fixture", 1, "route", 10,
                                           True, True, True, True), "e2")
    with pytest.raises(ValueError, match="verified executed"):
        value.export(tmp_path / "run", metadata("SUCCESS"))
    assert not (tmp_path / "run").exists()


def test_partial_intervals_are_not_full_mission_totals(tmp_path):
    value = recorder()
    value.record_cost(replace(cost(), started_sim_s=5, cost=CostEstimate(5, 2, 1)))
    metrics = value.export(tmp_path / "run", metadata()).to_dict()["metrics"]
    assert metrics["energy_est_wh"] == {"human_1": None}
    assert metrics["oxygen_est_l"] is None


def test_missing_predicate_is_not_retained_as_true(tmp_path):
    value = recorder()
    value.record_predicates(MissionEvidence("p", "fixture", 1, "route", 10,
                                           primary_goal_completed=True), "e2")
    value.record_event(event(3, 11, "COMPLETE"))
    value.record_predicates(MissionEvidence("p2", "fixture", 1, "route", 11), "e3")
    assert value.export(tmp_path / "run", metadata()).to_dict()["predicates"]["primary_goal_completed"] is None


def test_new_events_invalidate_old_success_snapshot(tmp_path):
    value = recorder()
    value.record_predicates(MissionEvidence("p", "fixture", 1, "route", 10,
                                           True, True, True, True), "e2")
    value.record_event(event(3, 11, "COMPLETE"))
    assert all(x is None for x in value.export(tmp_path / "run", metadata()).to_dict()["predicates"].values())


def test_public_discovery_and_completion_are_retained_with_causality(tmp_path):
    value = EvidenceRecorder("fixture", "fixture-model", execution_kind="SOFTWARE_TEST")
    discovery = replace(event(), event_type="TASK_DISCOVERED", task_id="poi", causality_id="obs")
    value.record_event(discovery)
    task = ObservedTask("poi", "fixture", 1, "obs", "human_1", "inspect", Point(0, 0), 10)
    value.record_discovery(task, "e1")
    value.record_discovery(task, "e1")
    with pytest.raises(ValueError, match="DONE"):
        value.record_task_completion(TaskEvidence("work", "fixture", 1, "route", "poi", 0), "e1")
    value.record_event(replace(event(2, 10, "DONE"), event_type="TASK_STATE_CHANGED",
                               task_id="poi", causality_id="work"))
    value.record_task_completion(TaskEvidence("work", "fixture", 1, "route", "poi", 10), "e2")
    data = metadata()
    data["termination_state"] = "ACTIVE"
    value.record_event(event(3, 11))
    value.export(tmp_path / "run", data)
    raw = json.loads((tmp_path / "run/records.json").read_text())["records"]
    assert [x["record_type"] for x in raw] == ["ObservedTask", "TaskEvidence"]
