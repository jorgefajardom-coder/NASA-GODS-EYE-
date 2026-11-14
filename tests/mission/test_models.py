"""Simulation-model checks: units, direction, activities, provenance and approval."""

from dataclasses import FrozenInstanceError, replace
import json
import math
from pathlib import Path

import pytest

from mge_mission.models import (
    AgentProfile, AssumptionRecord, CostEstimate, OXYGEN_L_PER_WH,
    estimate_activity, estimate_segment, export_planner_profiles, load_profiles,
)

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def profiles():
    return load_profiles(ROOT / "config/science_profiles.proposed.json")


def changed(profile, **parameters):
    return replace(profile, parameters=dict(profile.parameters) | parameters)


def test_loaded_profiles_are_proposals_and_cannot_gain_approval_from_loading(profiles):
    assert set(profiles) == {"human_1", "rover_1", "drone_1"}
    assert {p.approval_status for p in profiles.values()} == {"proposed"}
    assert all(p.model_id == "mge-science-1.0.0" for p in profiles.values())


def test_profile_defensively_copies_and_freezes_input(profiles):
    original = profiles["human_1"]
    parameters = dict(original.parameters)
    powers = dict(original.activity_power_w)
    profile = replace(original, parameters=parameters, activity_power_w=powers)
    parameters["speed_m_s"] = 900
    powers["sample"] = 0
    assert profile.parameters["speed_m_s"] == .8333
    assert profile.activity_power_w["sample"] == 461.17
    with pytest.raises(TypeError):
        profile.parameters["speed_m_s"] = 10
    with pytest.raises(FrozenInstanceError):
        profile.approval_status = "approved"


def test_human_flat_edge_units_and_metabolic_oxygen(profiles):
    human = profiles["human_1"]
    cost = estimate_segment(human, (0, 0, 0), (10, 0, 0))
    assert cost.time_s == pytest.approx(10 / .8333)
    assert cost.energy_wh == pytest.approx(417.7 * cost.time_s / 3600)
    expected_l_per_wh = (.086 / .0319988 * 22.41396954) / 295
    assert cost.oxygen_l == pytest.approx(cost.energy_wh * expected_l_per_wh)


def test_human_directed_slope_consumes_climb_without_downhill_credit(profiles):
    human = profiles["human_1"]
    flat = estimate_segment(human, (0, 0, 0), (10, 0, 0))
    up = estimate_segment(human, (0, 0, 0), (10, 0, 1))
    down = estimate_segment(human, (10, 0, 1), (0, 0, 0))
    climb_wh = (80.7 + 120) * 3.71 / (.25 * 3600)
    assert up.time_s == down.time_s == pytest.approx(12 / .8333)
    assert up.time_s > flat.time_s
    assert up.energy_wh == pytest.approx(down.energy_wh + climb_wh)
    assert down.energy_wh == pytest.approx(417.7 * down.time_s / 3600)
    assert up.oxygen_l > down.oxygen_l > flat.oxygen_l


def test_subdividing_one_grade_has_no_rounding_or_discretization_credit(profiles):
    human = profiles["human_1"]
    whole = estimate_segment(human, (0, 0, 0), (10, 0, 1))
    parts = [estimate_segment(human, (x, 0, x / 10), (x + 1, 0, (x + 1) / 10)) for x in range(10)]
    assert sum(p.time_s for p in parts) == pytest.approx(whole.time_s)
    assert sum(p.energy_wh for p in parts) == pytest.approx(whole.energy_wh)
    assert sum(p.oxygen_l for p in parts) == pytest.approx(whole.oxygen_l)


@pytest.mark.parametrize("agent_id", ["human_1", "rover_1", "drone_1"])
def test_zero_segment_has_no_implicit_service_or_idle_cost(profiles, agent_id):
    cost = estimate_segment(profiles[agent_id], (1, 2, 3), (1, 2, 3))
    assert cost.time_s == cost.energy_wh == 0
    assert cost.oxygen_l == (0 if agent_id == "human_1" else None)


@pytest.mark.parametrize("agent_id", ["human_1", "rover_1"])
def test_ground_vertical_motion_and_excess_grade_fail_explicitly(profiles, agent_id):
    with pytest.raises(ValueError, match="vertical-only"):
        estimate_segment(profiles[agent_id], (0, 0, 0), (0, 0, 1))
    with pytest.raises(ValueError, match="slope limit"):
        estimate_segment(profiles[agent_id], (0, 0, 0), (1, 0, 1))


def test_rover_flat_formula_includes_auxiliary_and_slip(profiles):
    rover = profiles["rover_1"]
    cost = estimate_segment(rover, (0, 0, 0), (10, 0, 0))
    time = 10 / (.04 * .9)
    force = 1025 * 3.71 * .05
    expected = (100 * time + force * 10 / (.35 * .9)) / 3600
    assert cost.time_s == pytest.approx(time)
    assert cost.energy_wh == pytest.approx(expected)
    assert cost.oxygen_l is None


def test_rover_downhill_never_regenerates_and_slip_costs_more(profiles):
    rover = profiles["rover_1"]
    down = estimate_segment(rover, (10, 0, 1), (0, 0, 0))
    assert down.energy_wh == pytest.approx(100 * down.time_s / 3600)
    baseline = estimate_segment(rover, (0, 0, 0), (10, 0, 0))
    slippery = estimate_segment(changed(rover, slip=.3), (0, 0, 0), (10, 0, 0))
    assert slippery.time_s > baseline.time_s
    assert slippery.energy_wh > baseline.energy_wh


def test_rolling_resistance_sensitivity_increases_drive_energy(profiles):
    rover = profiles["rover_1"]
    baseline = estimate_segment(rover, (0, 0, 0), (10, 0, 0))
    resistive = estimate_segment(changed(rover, rolling_resistance=.1), (0, 0, 0), (10, 0, 0))
    assert resistive.time_s == baseline.time_s
    assert resistive.energy_wh > baseline.energy_wh


def test_drive_efficiency_sensitivity_changes_tractive_energy_only(profiles):
    rover = profiles["rover_1"]
    baseline = estimate_segment(rover, (0, 0, 0), (10, 0, 1))
    inefficient = estimate_segment(changed(rover, drive_efficiency=.25), (0, 0, 0), (10, 0, 1))
    assert inefficient.time_s == baseline.time_s
    assert inefficient.energy_wh > baseline.energy_wh


def test_rover_directed_uphill_cost_exceeds_downhill_for_equal_distance(profiles):
    rover = profiles["rover_1"]
    uphill = estimate_segment(rover, (0, 0, 0), (10, 0, 1))
    downhill = estimate_segment(rover, (10, 0, 1), (0, 0, 0))
    assert uphill.time_s == downhill.time_s
    assert uphill.energy_wh > downhill.energy_wh > 0


def test_human_climb_efficiency_and_grade_slowdown_sensitivities(profiles):
    human = profiles["human_1"]
    baseline = estimate_segment(human, (0, 0, 0), (10, 0, 1))
    inefficient = estimate_segment(changed(human, climb_efficiency=.2), (0, 0, 0), (10, 0, 1))
    slower = estimate_segment(changed(human, slope_slowdown=3), (0, 0, 0), (10, 0, 1))
    assert inefficient.time_s == baseline.time_s
    assert inefficient.energy_wh > baseline.energy_wh
    assert slower.time_s > baseline.time_s
    assert slower.energy_wh > baseline.energy_wh
    assert slower.oxygen_l > baseline.oxygen_l


def test_drone_simultaneous_motion_uses_max_time_and_explicit_climb(profiles):
    drone = profiles["drone_1"]
    cost = estimate_segment(drone, (0, 0, 0), (10, 0, 2))
    assert cost.time_s == 5
    assert cost.energy_wh == pytest.approx((350 * 5 + 1.8 * 3.71 * 2 / .5) / 3600)
    assert cost.oxygen_l is None


def test_drone_descent_and_airborne_wait_are_not_ground_idle(profiles):
    drone = profiles["drone_1"]
    descent = estimate_segment(drone, (0, 0, 10), (0, 0, 0))
    assert descent.time_s == 10
    assert descent.energy_wh == pytest.approx(230 * 10 / 3600)
    ground = estimate_activity(drone, "ground_wait", 30)
    hover = estimate_activity(drone, "hover", 30)
    observe = estimate_activity(drone, "observe", 30)
    assert ground.energy_wh == pytest.approx(5 * 30 / 3600)
    assert hover == observe
    assert hover.energy_wh > ground.energy_wh


def test_service_is_integrated_once_at_activity_rate(profiles):
    human = profiles["human_1"]
    sample = estimate_activity(human, "sample", 60)
    inspect = estimate_activity(human, "inspect", 60)
    assert sample.time_s == inspect.time_s == 60
    assert sample.energy_wh == pytest.approx(461.17 / 60)
    assert inspect.energy_wh == pytest.approx(358.08 / 60)
    assert sample.oxygen_l == pytest.approx(sample.energy_wh * OXYGEN_L_PER_WH)
    assert estimate_activity(human, "wait", 60) == inspect


@pytest.mark.parametrize("point", [(0, 0), (0, 0, float("nan")), (True, 0, 0), ("1", 0, 0)])
def test_bad_coordinates_do_not_create_a_cost(profiles, point):
    with pytest.raises(ValueError, match="three finite coordinates"):
        estimate_segment(profiles["human_1"], (0, 0, 0), point)


@pytest.mark.parametrize("duration", [-1, True, float("nan"), float("inf")])
def test_invalid_service_duration_fails(profiles, duration):
    with pytest.raises(ValueError):
        estimate_activity(profiles["human_1"], "sample", duration)


def test_unsupported_activity_fails_instead_of_using_generic_service(profiles):
    with pytest.raises(ValueError, match="unsupported"):
        estimate_activity(profiles["rover_1"], "sample", 10)


def test_oxygen_sensitivity_does_not_change_metabolic_energy(profiles):
    human = profiles["human_1"]
    baseline = estimate_activity(human, "sample", 60)
    varied = estimate_activity(changed(human, oxygen_scale=1.25), "sample", 60)
    assert varied.energy_wh == baseline.energy_wh
    assert varied.oxygen_l == pytest.approx(baseline.oxygen_l * 1.25)


@pytest.mark.parametrize("parameter,value", [("slip", 1), ("drive_efficiency", 0), ("speed_m_s", 0), ("rolling_resistance", float("nan"))])
def test_invalid_rover_parameters_rejected(profiles, parameter, value):
    with pytest.raises(ValueError):
        changed(profiles["rover_1"], **{parameter: value})


def test_robot_profile_rejects_oxygen_parameters(profiles):
    with pytest.raises(ValueError, match="oxygen"):
        changed(profiles["rover_1"], oxygen_l_per_s=.1)


def test_missing_parameter_and_unknown_kind_are_rejected(profiles):
    human = profiles["human_1"]
    with pytest.raises(ValueError, match="missing"):
        replace(human, parameters={})
    with pytest.raises(ValueError, match="lowercase"):
        replace(human, kind="HUMAN")


def test_cost_estimates_never_contain_negative_or_nonfinite_resources():
    for values in [(-1, 0, None), (0, float("inf"), None), (0, 0, -1), (True, 0, None)]:
        with pytest.raises(ValueError):
            CostEstimate(*values)


def test_each_profile_parameter_and_rate_has_a_provenance_record(profiles):
    registry = json.loads((ROOT / "config/science_profiles.proposed.json").read_text())
    records = {r["parameter"]: AssumptionRecord(**r) for r in registry["assumptions"]}
    for agent_id, profile in profiles.items():
        for group in ("parameters", "activity_power_w"):
            for name, value in getattr(profile, group).items():
                record = records[f"profiles.{agent_id}.{group}.{name}"]
                assert record.value == value
                assert record.approval_status == "proposed"
                assert record.sensitivity_min <= value <= record.sensitivity_max
    assert registry["oxygen_volume_basis"]["temperature_k"] == 273.15
    assert registry["oxygen_volume_basis"]["pressure_pa"] == 101325


def test_planner_projection_remains_pending_even_if_profiles_approved(profiles):
    approved = {key: replace(profile, approval_status="approved") for key, profile in profiles.items()}
    export = export_planner_profiles(approved)
    assert export["status"] == "pending_model_agreement"
    assert export["approximation"]["exact_science_model"] is False
    assert set(export["profiles"]) == set(profiles)
    assert export["profiles"]["rover_1"]["oxygen_l_per_s"] is None
    json.dumps(export, allow_nan=False)


def test_only_all_illustrative_inputs_enable_illustrative_projection(profiles):
    illustrative = {key: replace(profile, approval_status="illustrative") for key, profile in profiles.items()}
    assert export_planner_profiles(illustrative)["status"] == "illustrative"
    illustrative["human_1"] = profiles["human_1"]
    assert export_planner_profiles(illustrative)["status"] == "pending_model_agreement"


def test_human_projection_oxygen_does_not_claim_flat_only_rate(profiles):
    export = export_planner_profiles(profiles)["profiles"]["human_1"]
    profile = profiles["human_1"]
    slope = math.radians(profile.parameters["max_slope_deg"])
    worst = estimate_segment(profile, (0, 0, 0), (1, 0, math.tan(slope)))
    assert export["oxygen_l_per_s"] >= worst.oxygen_l / worst.time_s - 1e-12


def test_illustrative_scenario_is_loadable_but_remains_illustrative():
    illustrative = load_profiles(ROOT / "config/scenario_demo.yaml")
    assert {p.approval_status for p in illustrative.values()} == {"illustrative"}
    import yaml
    scenario = yaml.safe_load((ROOT / "config/scenario_demo.yaml").read_text())
    assert scenario["dataset_id"] == "synthetic-flat-grid"
    assert scenario["mission"]["discovery_inputs"] == []


def test_assumption_records_require_traceability_and_bounded_sensitivity():
    with pytest.raises(ValueError, match="HTTPS"):
        AssumptionRecord("speed", 1, "m/s", "source", "", .5, 2)
    with pytest.raises(ValueError, match="contain"):
        AssumptionRecord("speed", 1, "m/s", "engineering_assumption", "", 2, 3)
