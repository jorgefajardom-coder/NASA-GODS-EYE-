"""Public prior proposal consistency; no synthetic observations or mission runs."""

import importlib.util
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("jezero_sizing", ROOT / "scripts/size_jezero_proposal.py")
sizing = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sizing)
PROPOSAL = ROOT / "config/mission_jezero.proposed.yaml"


@pytest.fixture(scope="module")
def report():
    return sizing.build_report(PROPOSAL, run_id="proposal-software-check")


def test_proposal_preserves_unknowns_and_never_approves(report):
    assert report["readiness"]["dataset_status"] == "PUBLIC_PACKAGE_VALIDATED"
    assert report["readiness"]["terrain"]["observed_cells"] == 0
    assert report["readiness"]["status"] == "NOT_READY"
    assert len(report["readiness"]["missing_inputs"]) == 6
    assert not report["mission_execution_authorized"]
    assert not report["scientific_approval"]
    assert all(not x["route_verified"] for x in report["probes"])


def test_costs_separate_service_wait_return_and_reserves(report):
    human = report["probes"][0]["nominal"]
    for metric in ("time_s", "energy_wh", "oxygen_l"):
        assert human["total"][metric] == pytest.approx(sum(human[k][metric] for k in ("outbound", "return", "service", "wait")))
    assert human["return"]["energy_wh"] > human["outbound"]["energy_wh"]
    assert human["reserve_margins"]["energy_wh"] == pytest.approx(100 - 20 - human["total"]["energy_wh"])
    assert human["total"]["time_s"] == pytest.approx(401.12290725129004)
    assert human["resource_envelope_fits"]
    assert human["step_proxy_exceeded"] is False
    assert report["direct_diagonal_counterexample"]["step_proxy_exceeded"]


def test_robot_oxygen_absent_and_slow_rover_may_exceed_horizon(report):
    for row in report["probes"][1:]:
        assert row["nominal"]["total"]["oxygen_l"] is None
        assert "oxygen_l" not in row["nominal"]["reserve_margins"]
    rover = report["probes"][1]
    slow = next(x for x in rover["coefficient_sensitivity_oat"]
                if x["parameter"].endswith("speed_m_s") and x["level"] == "sensitivity_min")
    assert not slow["resource_envelope_fits"]
    samples = report["optional_sample_duration_sensitivity"]
    assert samples[1]["additional_cost_fits"]
    assert not samples[2]["additional_cost_fits"]
    assert all(x["task_assigned"] is False for x in samples)


def test_changed_public_height_is_not_silently_accepted(tmp_path):
    data = yaml.safe_load(PROPOSAL.read_text(encoding="utf-8"))
    data["base_enu_m"][2] = 0
    path = tmp_path / "proposal.yaml"
    path.write_text(yaml.safe_dump(data), encoding="utf-8")
    with pytest.raises(ValueError, match="exact public cell"):
        sizing.build_report(path, run_id="proposal-software-check")


def test_nominal_config_is_pending_and_reserves_are_twenty_percent():
    data = yaml.safe_load(PROPOSAL.read_text(encoding="utf-8"))
    assert data["status"] == "proposed"
    assert data["approval_evidence"] == {}
    assert data["optional_tasks"] == []
    assert data["primary_activity"] == "inspect"
    assert "no optional inspection" in data["primary_service_meaning"]
    for budget in data["budgets"].values():
        for capacity, reserve in (("time_s", "reserve_time_s"), ("energy_wh", "reserve_wh"),
                                  ("oxygen_l", "reserve_oxygen_l")):
            if capacity in budget:
                assert budget[reserve] == pytest.approx(0.2 * budget[capacity])
