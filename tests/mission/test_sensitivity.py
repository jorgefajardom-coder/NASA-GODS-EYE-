"""Sensitivity checks on synthetic geometry; no mission outcomes."""

from dataclasses import replace
import json
from pathlib import Path

import pytest

from mge_mission.models import estimate_activity, estimate_segment, load_profiles
from mge_mission.sensitivity import SensitivityCase, sweep
from mge_mission.types import Budgets

ROOT = Path(__file__).resolve().parents[2]
REGISTRY = ROOT / "config/science_profiles.proposed.json"


def inputs(agent="human_1"):
    profiles = load_profiles(REGISTRY)
    records = json.loads(REGISTRY.read_text())["assumptions"]
    case = SensitivityCase("fixture", agent, ((0, 0, 0), (10, 0, 1)),
                           ((10, 0, 1), (0, 0, 0)),
                           (("sample" if agent == "human_1" else "inspect", 10),), 5)
    return profiles, records, case


def test_directional_return_service_wait_counted_once_and_profiles_immutable():
    profiles, records, case = inputs()
    before = dict(profiles[case.agent_id].parameters)
    report = sweep(profiles, records, [case])
    row = next(x for x in report["results"] if x["level"] == "nominal")
    profile = profiles[case.agent_id]
    expected = sum(x.energy_wh for x in (
        estimate_segment(profile, (0, 0, 0), (10, 0, 1)),
        estimate_segment(profile, (10, 0, 1), (0, 0, 0)),
        estimate_activity(profile, "sample", 10), estimate_activity(profile, "idle", 5)))
    assert row["total"]["energy_wh"] == pytest.approx(expected)
    assert row["components"]["outbound"][0]["energy_wh"] > row["components"]["return"][0]["energy_wh"]
    assert profiles[case.agent_id].parameters == before
    assert row["budget_feasible_under_model"] is None
    assert report["scientific_approval"] is False


@pytest.mark.parametrize("agent,key,metric,increasing", [
    ("human_1", "speed_m_s", "time_s", False),
    ("human_1", "climb_efficiency", "energy_wh", False),
    ("rover_1", "rolling_resistance", "energy_wh", True),
    ("rover_1", "slip", "time_s", True),
    ("rover_1", "drive_efficiency", "energy_wh", False)])
def test_expected_sensitivity_direction(agent, key, metric, increasing):
    profiles, records, case = inputs(agent)
    rows = [x for x in sweep(profiles, records, [case])["results"]
            if x["parameter"].endswith("." + key)]
    low, nominal, high = [x["total"][metric] for x in rows]
    assert (low < nominal < high) if increasing else (low > nominal > high)


def test_reserves_can_flip_budget_decision():
    profiles, records, case = inputs()
    initial = sweep(profiles, records, [case])
    nominal = next(x for x in initial["results"] if x["level"] == "nominal")["total"]
    case = replace(case, budgets=Budgets(nominal["time_s"] + 2, 100, 100, 1, 1, 1))
    rows = [x for x in sweep(profiles, records, [case])["results"]
            if x["parameter"].endswith(".speed_m_s")]
    assert rows[0]["budget_feasible_under_model"] is False
    assert rows[0]["budget_decision_changed"] is True
    assert rows[1]["budget_feasible_under_model"] is True


def test_bad_registry_and_missing_return_are_input_errors():
    profiles, records, case = inputs()
    with pytest.raises(ValueError, match="nominal assumption"):
        sweep({**profiles, "human_1": replace(profiles["human_1"],
              parameters={**profiles["human_1"].parameters, "speed_m_s": 0.8})}, records, [case])
    with pytest.raises(ValueError, match="return paths"):
        sweep(profiles, records, [replace(case, return_enu_m=((10, 0, 1), (1, 0, 0)))])
    with pytest.raises(ValueError, match="Robots"):
        rover = replace(case, agent_id="rover_1", services=(),
                        budgets=Budgets(100, 100, 1, 0, 0, 0))
        sweep(profiles, records, [rover])


def test_rejected_variant_retains_reason_and_unknown_budget():
    profiles, records, case = inputs()
    records = [{**x, "sensitivity_min": 0.1} if x["parameter"].endswith("human_1.parameters.max_slope_deg")
               else x for x in records]
    report = sweep(profiles, records, [case])
    rejected = [x for x in report["results"] if x["status"] == "MODEL_REJECTED"]
    assert len(rejected) == 1
    assert rejected[0]["reason"]
    assert rejected[0]["budget_feasible_under_model"] is None
    assert len(report["fixed_assumptions"]) == 6
