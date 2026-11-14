"""Scientific cost-contract vectors, not mock producers or mission outcomes."""

import importlib.util
import json
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("cost_agreement_vectors", ROOT / "scripts/export_cost_agreement_vectors.py")
vectors_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(vectors_module)
CONTRACT = ROOT / "config/cost_agreement.experimental.json"


@pytest.fixture(scope="module")
def report():
    return vectors_module.build_vectors(CONTRACT, run_id="cost-vector-software-check")


def vector(report, suffix):
    return next(x for x in report["vectors"] if x["vector_id"] == suffix)


def test_no_approval_or_execution_is_inferred(report):
    assert report["status"] == "AWAITING_CONSUMER_AGREEMENT"
    assert report["tolerances"] == {"relative": 1e-5, "absolute": 1e-3}
    assert set(report["profile_approval_states"].values()) == {"proposed"}
    assert not report["scientific_approval"]
    assert not report["cost_agreement_approved"]
    assert not report["mission_execution_authorized"]
    assert not report["integrated_mission_executed"]
    assert all(len(value) == 64 for value in report["inputs_sha256"].values())
    readiness = report["scenario_readiness"]
    assert readiness["dataset_status"] == "PUBLIC_PACKAGE_VALIDATED"
    assert readiness["scenario_approval"]["status"] == "APPROVED_EXPERIMENTAL_VALUES"
    assert readiness["status"] == "NOT_READY"
    assert len(readiness["missing_inputs"]) == 6


def test_primary_service_wait_and_return_are_charged_once(report):
    row = vector(report, "human_1-directed_itinerary")
    components = row["expected"]["components"]
    assert len(components) == 4
    assert components[1]["input"] == {"kind": "activity", "activity": "inspect", "duration_s": 120.0}
    assert components[1]["cost"]["energy_wh"] == pytest.approx(11.936)
    assert components[2]["input"]["activity"] == "idle"
    for metric, total in row["expected"]["cost"].items():
        assert total == pytest.approx(sum(x["cost"][metric] for x in components))
    ascent = vector(report, "human_1-ascent")["expected"]["cost"]
    descent = vector(report, "human_1-descent")["expected"]["cost"]
    assert ascent["energy_wh"] > descent["energy_wh"] > 0


def test_invalid_ground_and_valid_drone_vertical_cases_remain_explicit(report):
    for agent in ("human_1", "rover_1"):
        assert vector(report, f"{agent}-ground_vertical_or_drone_climb")["expected"]["status"] == "MODEL_INPUT_REJECTED"
        assert vector(report, f"{agent}-invalid_duration")["expected"]["exception"] == "ValueError"
    assert vector(report, "drone_1-ground_vertical_or_drone_climb")["expected"]["status"] == "ESTIMATED"
    hover = vector(report, "drone_1-hover")["expected"]["cost"]
    ground = vector(report, "drone_1-ground_wait")["expected"]["cost"]
    assert hover["energy_wh"] > ground["energy_wh"]
    assert hover["oxygen_l"] is None and ground["oxygen_l"] is None


@pytest.mark.parametrize("agent", ["human_1", "rover_1", "drone_1"])
def test_strict_budget_boundaries_and_remaining_prefix_accounting(report, agent):
    cases = vector(report, f"{agent}-resource_boundaries")["expected"]["budget_cases"]
    assert next(x for x in cases if x["case"] == "representable_feasible_boundary")["resource_feasible"]
    assert all(not x["resource_feasible"] for x in cases if x["case"].startswith("below_boundary"))
    assert not next(x for x in cases if x["case"] == "reserve_exceeds_capacity")["resource_feasible"]
    partial = vector(report, f"{agent}-partial_service_remaining")
    assert partial["input_kind"] == "analytic_accounting_example_not_execution"
    assert partial["current_remaining_budget"]["energy_wh"] < partial["initial_budget"]["energy_wh"]
    for key, value in partial["expected"]["original_complete_cost"].items():
        if value is None:
            assert partial["expected"]["cost"][key] is None
        else:
            assert partial["expected"]["completed_plus_remaining_cost"][key] == pytest.approx(value)
    if agent != "human_1":
        assert "oxygen_l" not in partial["current_remaining_budget"]


def test_changed_tolerances_do_not_silently_create_a_new_agreement(tmp_path):
    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    contract["comparison_tolerances"]["absolute"] = 1
    path = tmp_path / "contract.json"
    path.write_text(json.dumps(contract), encoding="utf-8")
    with pytest.raises(ValueError, match="existing tolerances"):
        vectors_module.build_vectors(path, run_id="bad-tolerance")


@pytest.mark.parametrize("field", ["budget", "base", "sizing"])
def test_changed_experimental_values_are_not_exported_as_approved(tmp_path, field):
    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    scenario = yaml.safe_load((ROOT / contract["scenario_path"]).read_text(encoding="utf-8"))
    if field == "budget":
        scenario["budgets"]["human_1"]["energy_wh"] += 1
    elif field == "base":
        scenario["base_enu_m"][0] += 4
    else:
        scenario["sizing"]["human_probe_cells"][1][0] -= 1
    scenario_path = tmp_path / "scenario.yaml"
    scenario_path.write_text(yaml.safe_dump(scenario), encoding="utf-8")
    contract["scenario_path"] = str(scenario_path)
    contract_path = tmp_path / "contract.json"
    contract_path.write_text(json.dumps(contract), encoding="utf-8")
    with pytest.raises(ValueError, match="scenario approval/public inputs"):
        vectors_module.build_vectors(contract_path, run_id="changed-experiment")


def test_metadata_references_preserve_approval_but_profile_and_manifest_bindings_must_match(tmp_path):
    original = yaml.safe_load((ROOT / "config/mission_jezero.experimental.yaml").read_text(encoding="utf-8"))
    scenario = {**original, "activity_duration_pilot_status": "pending_review_metadata_only"}
    path = tmp_path / "scenario.yaml"
    path.write_text(yaml.safe_dump(scenario), encoding="utf-8")
    _, readiness = vectors_module.validate_experimental_inputs(
        path, ROOT / original["profiles_path"], run_id="metadata-reference")
    assert readiness["scenario_approval"]["status"] == "APPROVED_EXPERIMENTAL_VALUES"
    profiles_copy = tmp_path / "profiles.json"
    profiles_copy.write_bytes((ROOT / original["profiles_path"]).read_bytes())
    with pytest.raises(ValueError, match="model/profile/manifest bindings"):
        vectors_module.validate_experimental_inputs(path, profiles_copy, run_id="profile-binding")
    scenario["manifest_sha256"] = "0" * 64
    path.write_text(yaml.safe_dump(scenario), encoding="utf-8")
    with pytest.raises(ValueError, match="model/profile/manifest bindings"):
        vectors_module.validate_experimental_inputs(path, ROOT / original["profiles_path"], run_id="manifest-binding")


def test_optional_activity_pilot_preserves_sources_and_does_not_change_baseline(tmp_path):
    # Fixture duration is an explicit software example, not a claim about its linked source.
    pilot = {"schema_version": "1.0.0", "status": "proposed", "cases": [
        {"case_id": "fixture-duration", "agent_id": "human_1", "activity": "inspect", "duration_s": 60,
         "source_url": "https://ntrs.nasa.gov/", "source_locator": "Software fixture only, no NASA-duration claim"}]}
    path = tmp_path / "pilot.json"
    path.write_text(json.dumps(pilot), encoding="utf-8")
    result = vectors_module.build_vectors(CONTRACT, run_id="pilot-test", activity_pilot_path=path)
    assert result["activity_pilot"] == pilot
    assert vector(result, "activity-pilot-fixture-duration")["expected"]["cost"]["energy_wh"] == pytest.approx(5.968)
    assert vector(result, "human_1-service")["schedule"][0]["duration_s"] == 120
    assert not result["cost_agreement_approved"]
    pilot["status"] = "approved"
    path.write_text(json.dumps(pilot), encoding="utf-8")
    with pytest.raises(ValueError, match="must remain"):
        vectors_module.build_vectors(CONTRACT, run_id="pilot-test", activity_pilot_path=path)


def test_mixed_pilot_workflow_charges_each_phase_once_and_rejects_total_as_extra_phase(tmp_path):
    pilot = {"schema_version": "1.0.0", "status": "proposed", "cases": [
        {"case_id": "mixed-workflow-fixture", "agent_id": "human_1",
         "schedule": [{"activity": "inspect", "duration_s": 420}, {"activity": "sample", "duration_s": 180}],
         "source_url": "https://ntrs.nasa.gov/", "source_locator": "Software allocation fixture, not measured phase breakdown"}]}
    path = tmp_path / "mixed-pilot.json"
    path.write_text(json.dumps(pilot), encoding="utf-8")
    report = vectors_module.build_vectors(CONTRACT, run_id="mixed-pilot-test", activity_pilot_path=path)
    expected = vector(report, "activity-pilot-mixed-workflow-fixture")["expected"]
    assert len(expected["components"]) == 2
    assert expected["cost"]["time_s"] == 600
    assert expected["cost"]["energy_wh"] == pytest.approx((358.08 * 420 + 461.17 * 180) / 3600)
    for metric, total in expected["cost"].items():
        assert total == pytest.approx(sum(phase["cost"][metric] for phase in expected["components"]))
    assert report["activity_pilot"] == pilot
    pilot["cases"][0]["duration_s"] = 600
    path.write_text(json.dumps(pilot), encoding="utf-8")
    with pytest.raises(ValueError, match="not both"):
        vectors_module.build_vectors(CONTRACT, run_id="mixed-pilot-test", activity_pilot_path=path)
