"""Cross-check scientific acceptance contracts and analytical duration pilots."""

import importlib.util
import json
from pathlib import Path

import pytest
import yaml

from mge_mission.benchmark import PREDICATES

ROOT = Path(__file__).resolve().parents[2]


def module(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / f"scripts/{name}.py")
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def test_success_definition_preserves_approved_values_and_four_strict_predicates():
    criteria = json.loads((ROOT / "config/mission_success.experimental.json").read_text(encoding="utf-8"))
    mission = yaml.safe_load((ROOT / criteria["scenario_path"]).read_text(encoding="utf-8"))
    assert set(criteria["predicates"]) == set(PREDICATES)
    assert criteria["combination"] == "ALL_FOUR_TRUE"
    assert criteria["predicates"]["primary_goal_completed"]["required_service_s"] == mission["primary_service_time_s"]
    assert criteria["predicates"]["returned_to_base_within_tolerance"]["tolerance_m_3d"] == mission["return_tolerance_m"]
    assert criteria["predicates"]["verified_ground_traversal_under_model"]["estimated_route_is_verification"] is False
    assert criteria["operational_authorization"] is False
    assert criteria["status"] == "defined_pending_execution_binding"


def test_duration_pilot_budget_rejection_and_service_replacement(tmp_path):
    exporter = module("export_cost_agreement_vectors")
    vectors = exporter.build_vectors(ROOT / "config/cost_agreement.experimental.json", run_id="pilot-software-check",
                                     activity_pilot_path=ROOT / "config/activity_duration.pilot.json")
    path = tmp_path / "vectors.json"
    path.write_text(json.dumps(vectors), encoding="utf-8")
    report = module("evaluate_activity_duration_pilot").evaluate(path, run_id="pilot-software-check")
    cases = {item["case_id"]: item for item in report["cases"]}
    replacement = cases["inspection_300s_sensitivity"]
    assert replacement["combined_mission_cost"]["time_s"] == pytest.approx(
        report["baseline_primary_probe"]["total"]["time_s"] - 120 + 300)
    sample = cases["documented_sample_600s_mixed"]
    assert sample["activity_cost"]["time_s"] == 600
    assert sample["combined_mission_cost"]["energy_wh"] == pytest.approx(110.1036915066)
    assert not sample["resource_envelope_fits"]
    assert all(sample["reserve_margins"][key] < 0 for key in ("time_s", "energy_wh", "oxygen_l"))
    assert cases["trenching_180s"]["resource_envelope_fits"]
    assert report["approved_values_changed"] is False
    assert not report["mission_execution_authorized"]
    assert all(not item["task_assigned"] for item in report["cases"])
    assert report["scenario_readiness"]["scenario_approval"]["status"] == "APPROVED_EXPERIMENTAL_VALUES"
    assert report["baseline_readiness_inputs_sha256"]["manifest"]
    assert set(report["implementation_sha256"]) == {
        "scripts/size_jezero_proposal.py", "scripts/export_cost_agreement_vectors.py",
        "src/mge_mission/mge_mission/scenario.py", "src/mge_data/mge_data/core.py"}


def test_duration_pilot_rejects_stale_vectors_and_changed_approved_values(tmp_path, monkeypatch):
    exporter = module("export_cost_agreement_vectors")
    pilot = module("evaluate_activity_duration_pilot")
    vectors = exporter.build_vectors(ROOT / "config/cost_agreement.experimental.json", run_id="pilot-binding-check",
                                     activity_pilot_path=ROOT / "config/activity_duration.pilot.json")
    path = tmp_path / "vectors.json"
    vectors["inputs_sha256"]["scenario"] = "0" * 64
    path.write_text(json.dumps(vectors), encoding="utf-8")
    with pytest.raises(ValueError, match="identical model, profiles and scenario"):
        pilot.evaluate(path, run_id="stale-vectors")
    changed = yaml.safe_load((ROOT / "config/mission_jezero.experimental.yaml").read_text(encoding="utf-8"))
    changed["budgets"]["human_1"]["energy_wh"] += 1
    changed_path = tmp_path / "changed-scenario.yaml"
    changed_path.write_text(yaml.safe_dump(changed), encoding="utf-8")
    validate = pilot.validate_experimental_inputs
    monkeypatch.setattr(pilot, "validate_experimental_inputs", lambda _path, profiles, *, run_id:
                        validate(changed_path, profiles, run_id=run_id))
    with pytest.raises(ValueError, match="scenario approval/public inputs"):
        pilot.evaluate(path, run_id="changed-approved-budget")


def test_pilot_does_not_call_distinct_tasks_a_statistical_duration_range():
    pilot = json.loads((ROOT / "config/activity_duration.pilot.json").read_text(encoding="utf-8"))
    cases = {item["case_id"]: item for item in pilot["cases"]}
    assert pilot["status"] == "pending_review"
    assert cases["inspection_300s_sensitivity"]["evidence_kind"] == "engineering_assumption_pending_review"
    assert cases["documented_sample_600s_mixed"]["evidence_kind"] == "reported_analog_total_with_engineering_phase_allocation"
    assert sum(x["duration_s"] for x in cases["documented_sample_600s_mixed"]["schedule"]) == 600
