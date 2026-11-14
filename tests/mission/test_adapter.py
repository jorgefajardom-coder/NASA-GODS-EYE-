"""ROS representation checks run without importing rclpy or generated messages."""

from math import isnan
from types import SimpleNamespace as NS

import pytest

from mge_mission import adapter
from mge_mission.node import create_node_class
from mge_mission.types import PlanRequest, Point, RouteDecision


def wire_point(x=0.0, y=0.0, z=0.0):
    return NS(x=x, y=y, z=z)


def header(seconds=4, frame="map"):
    return NS(frame_id=frame, stamp=NS(sec=seconds, nanosec=0))


def agent(kind="HUMAN", oxygen=100.0):
    return NS(
        header=header(), run_id="run", agent_id="human_1", agent_kind=kind,
        pose=NS(position=wire_point(1.0, 2.0), orientation=NS(x=0.0, y=0.0, z=0.0, w=1.0)),
        velocity=NS(linear=wire_point(), angular=wire_point()), mode="IDLE",
        time_remaining_s=1000.0, energy_remaining_wh=1000.0,
        oxygen_remaining_l=oxygen, confidence=1.0,
    )


def route_message():
    return NS(
        header=header(), run_id="run", request_id="request", route_id="route",
        agent_id="human_1", mode="FAST", map_version_used=2, status="FEASIBLE",
        reason_code="", detail="", outbound_path=[wire_point(1.0, 2.0), wire_point(3.0, 2.0)],
        return_path=[wire_point(3.0, 2.0), wire_point(1.0, 2.0)],
        travel_time_s=40.0, energy_est_wh=5.0, oxygen_est_l=1.0,
        min_clearance_m=1.0, reserve_time_s=960.0, reserve_wh=995.0, reserve_oxygen_l=99.0,
    )


@pytest.mark.parametrize("value", [float("nan"), float("inf"), -float("inf"), True, "1", None])
def test_finite_conversion_rejects_non_numeric_or_nonfinite(value):
    with pytest.raises(ValueError):
        adapter.finite_number(value, "resource")


def test_float32_conversion_is_explicit_and_rejects_overflow():
    assert adapter.float32(1 / 3, "resource") != 1 / 3
    assert isnan(adapter.float32(None, "oxygen", oxygen_na=True))
    with pytest.raises(ValueError, match="float32"):
        adapter.float32(1e100, "resource")


@pytest.mark.parametrize("kind", ["ROVER", "DRONE"])
def test_nonhuman_nan_oxygen_maps_to_none_and_zero_is_rejected(kind):
    state = adapter.agent_from_wire(agent(kind, float("nan")), "run", 4.0)
    assert state.oxygen_remaining_l is None
    with pytest.raises(ValueError, match="NaN"):
        adapter.agent_from_wire(agent(kind, 0.0), "run", 4.0)


def test_wire_kind_casing_is_intentional():
    assert adapter.kind_from_wire("HUMAN") == "human"
    assert adapter.kind_to_wire("rover") == "ROVER"
    with pytest.raises(ValueError, match="uppercase"):
        adapter.kind_from_wire("human")


@pytest.mark.parametrize("change", ["run", "frame", "future", "bad_stamp"])
def test_header_rejects_cross_run_wrong_frame_and_invalid_simulation_time(change):
    message = agent()
    if change == "run":
        message.run_id = "another-run"
    elif change == "frame":
        message.header.frame_id = "odom"
    elif change == "future":
        message.header.stamp.sec = 5
    else:
        message.header.stamp.nanosec = 1_000_000_000
    with pytest.raises(ValueError):
        adapter.agent_from_wire(message, "run", 4.0)


def test_goal_empty_run_is_resolved_without_changing_wire_names():
    request = NS(request_id="goal", run_id="", primary_agent_id="human_1",
                 base=wire_point(), goal=wire_point(3.0, 2.0), mode="FAST",
                 time_budget_s=100.0, energy_budget_wh=100.0, oxygen_budget_l=20.0,
                 reserve_time_s=10.0, reserve_wh=10.0, reserve_oxygen_l=2.0)
    goal = adapter.goal_from_wire(request, "run")
    assert goal.run_id == "run"
    assert goal.goal == Point(3.0, 2.0, 0.0)
    with pytest.raises(ValueError, match="human"):
        adapter.goal_from_wire(request, "run", primary_kind="rover")


def test_goal_fingerprint_uses_normalized_semantics_not_serialized_storage():
    def request():
        return NS(request_id="goal", run_id="", primary_agent_id="human_1",
                  base=wire_point(), goal=wire_point(3.0, 2.0), mode="FAST",
                  time_budget_s=100.0, energy_budget_wh=100.0, oxygen_budget_l=20.0,
                  reserve_time_s=10.0, reserve_wh=10.0, reserve_oxygen_l=2.0)
    first, rebuilt = request(), request()
    rebuilt.run_id = "run"
    rebuilt.base.x = -0.0
    assert first is not rebuilt and first.base is not rebuilt.base
    assert adapter.goal_fingerprint(first, "run") == adapter.goal_fingerprint(rebuilt, "run")
    rebuilt.goal.x = 4.0
    assert adapter.goal_fingerprint(first, "run") != adapter.goal_fingerprint(rebuilt, "run")
    rebuilt = request()
    first.oxygen_budget_l = rebuilt.oxygen_budget_l = float("nan")
    assert adapter.goal_fingerprint(first, "run") == adapter.goal_fingerprint(rebuilt, "run")


@pytest.mark.parametrize("field", ["time_budget_s", "energy_budget_wh", "oxygen_budget_l",
                                  "reserve_time_s", "reserve_wh", "reserve_oxygen_l"])
def test_goal_fingerprint_detects_each_changed_resource_field(field):
    request = NS(request_id="goal", run_id="run", primary_agent_id="human_1",
                 base=wire_point(), goal=wire_point(3.0, 2.0), mode="FAST",
                 time_budget_s=100.0, energy_budget_wh=100.0, oxygen_budget_l=20.0,
                 reserve_time_s=10.0, reserve_wh=10.0, reserve_oxygen_l=2.0)
    original = adapter.goal_fingerprint(request, "run")
    setattr(request, field, getattr(request, field) + 1.0)
    assert adapter.goal_fingerprint(request, "run") != original


def test_route_round_trip_preserves_canonical_fields():
    route = adapter.decision_from_wire(route_message(), "run", 4.0, kind="human")
    output = route_message()
    adapter.decision_to_wire(route, output, NS(sec=4, nanosec=0), wire_point)
    assert output.request_id == route.request_id
    assert output.outbound_path[1].x == 3.0
    assert output.oxygen_est_l == route.oxygen_est_l
    assert output.header.frame_id == "map"


@pytest.mark.parametrize("status", ["UNKNOWN", "NO_PATH", "INSUFFICIENT_BUDGET"])
def test_planner_failures_preserve_nan_metrics_as_unavailable(status):
    message = route_message()
    message.status, message.reason_code = status, f"{status}_DETAIL"
    message.route_id, message.outbound_path, message.return_path = "", [], []
    # Published planner 34c515b6 emits zero stamp before a map is loaded and
    # NaN in every unavailable metric, including human oxygen.
    message.header.stamp.sec = 0
    fields = ("travel_time_s", "energy_est_wh", "oxygen_est_l", "min_clearance_m",
              "reserve_time_s", "reserve_wh", "reserve_oxygen_l")
    for name in fields:
        setattr(message, name, float("nan"))
    result = adapter.decision_from_wire(message, "run", 4.0, kind="human")
    assert result.status == status and result.reason_code == f"{status}_DETAIL"
    assert all(getattr(result, name) is None for name in fields)
    output = adapter.decision_to_wire(result, route_message(), message.header.stamp, wire_point)
    assert all(isnan(getattr(output, name)) for name in fields)
    assert output.route_id == "" and output.outbound_path == [] and output.return_path == []


@pytest.mark.parametrize("field", ["travel_time_s", "energy_est_wh", "oxygen_est_l", "min_clearance_m",
                                  "reserve_time_s", "reserve_wh", "reserve_oxygen_l"])
def test_feasible_candidate_still_requires_every_applicable_finite_metric(field):
    message = route_message()
    setattr(message, field, float("nan"))
    with pytest.raises(ValueError, match="finite"):
        adapter.decision_from_wire(message, "run", 4.0, kind="human")


@pytest.mark.parametrize("invalid", ["frame", "run", "future"])
def test_failure_cannot_bypass_valid_run_frame_and_nonfuture_stamp(invalid):
    message = route_message()
    message.status, message.route_id, message.outbound_path, message.return_path = "UNKNOWN", "", [], []
    if invalid == "frame":
        message.header.frame_id = "odom"
    elif invalid == "run":
        message.run_id = "another-run"
    else:
        message.header.stamp.sec = 5
    with pytest.raises(ValueError):
        adapter.decision_from_wire(message, "run", 4.0, kind="human")


def test_failure_must_not_advertise_a_route():
    message = route_message()
    message.status = "NO_PATH"
    with pytest.raises(ValueError, match="failed planning decision"):
        adapter.decision_from_wire(message, "run", 4.0, kind="human")


def test_robot_plan_writes_nan_oxygen_and_uppercase_kind():
    plan = PlanRequest("run", "request", "rover_1", "ROVER", Point(0, 0), Point(1, 0),
                       Point(0, 0), True, "FAST", 2, 0.0, 100.0, 100.0, None,
                       10.0, 10.0, None)
    message = adapter.plan_to_wire(plan, NS(), wire_point)
    assert message.agent_kind == "ROVER"
    assert isnan(message.oxygen_budget_l) and isnan(message.reserve_oxygen_l)


def test_invalidation_writes_empty_map_path():
    pose_factory = lambda: NS(header=header(), pose=NS(position=wire_point(), orientation=NS(w=0.0)))
    route = RouteDecision("run", "request", "route", "human_1", "FAST", 2, "FEASIBLE",
                          outbound_path=(Point(0, 0), Point(1, 0)))
    message = adapter.active_path_to_wire(route, NS(header=header()), NS(sec=4, nanosec=0), pose_factory)
    assert len(message.poses) == 2 and message.poses[0].pose.orientation.w == 1.0
    adapter.active_path_to_wire(None, message, NS(sec=4, nanosec=0), pose_factory)
    assert message.poses == [] and message.header.frame_id == "map"


def test_node_factory_is_importable_without_initializing_ros():
    assert callable(create_node_class)
