"""Generated Jazzy messages -> strict JSON, distinct from ROS-shaped doubles."""
from array import array
import json
from math import nan

import pytest

rosidl = pytest.importorskip("rosidl_runtime_py.utilities", reason="Requires built ROS 2 Jazzy interfaces")
from mge_bringup.contract_guard import ros_json


def test_generated_agentstate_nonhuman_oxygen_converts_to_null():
    state = rosidl.get_message("mge_interfaces/msg/AgentState")()
    state.agent_kind = state.KIND_ROVER
    state.agent_id = "generated-contract-rover"
    state.run_id = "generated-contract-run"
    state.oxygen_remaining_l = nan
    state.pose.position.x = 1.25
    state.pose.position.y = -2.5
    state.pose.position.z = 3.75
    payload = ros_json(state)
    assert payload["oxygen_remaining_l"] is None
    assert payload["pose"]["position"] == {"x": 1.25, "y": -2.5, "z": 3.75}
    assert json.loads(json.dumps(payload, allow_nan=False)) == payload


def test_generated_routedecision_point_arrays_and_nan_oxygen():
    decision = rosidl.get_message("mge_interfaces/msg/RouteDecision")()
    Point = rosidl.get_message("geometry_msgs/msg/Point")
    start, goal = Point(), Point()
    start.x, start.y, start.z = 1.0, 1.0, 2.0
    goal.x, goal.y, goal.z = 3.0, 1.0, 2.5
    decision.outbound_path = [start, goal]
    decision.return_path = [goal, start]
    decision.status = decision.STATUS_FEASIBLE
    decision.oxygen_est_l = nan
    decision.reserve_oxygen_l = nan
    payload = ros_json(decision, agent_kind="ROVER")
    assert payload["oxygen_est_l"] is None
    assert payload["reserve_oxygen_l"] is None
    assert payload["outbound_path"] == [{"x": 1.0, "y": 1.0, "z": 2.0}, {"x": 3.0, "y": 1.0, "z": 2.5}]
    assert payload["return_path"] == list(reversed(payload["outbound_path"]))
    json.dumps(payload, allow_nan=False)
    with pytest.raises(ValueError, match="HUMAN_OXYGEN_REQUIRED"):
        ros_json(decision, agent_kind="HUMAN")


def test_generated_observation_native_arrays_preserve_cell_order_and_types():
    observation = rosidl.get_message("mge_interfaces/msg/TerrainObservation")()
    observation.run_id = "generated-contract-run"
    observation.observation_id = "generated-observation-1"
    observation.source_kind = observation.SOURCE_SIMULATED
    observation.cell_indices = array("I", [5, 0, 3])
    observation.elevation_m = array("f", [10.5, -2.0, 7.25])
    observation.sigma_m = array("f", [0.5, 0.25, 1.0])
    observation.obstacle = array("b", [0, -1, 100])
    payload = ros_json(observation)
    assert payload["cell_indices"] == [5, 0, 3]
    assert all(type(value) is int for value in payload["cell_indices"])
    assert payload["elevation_m"] == [10.5, -2.0, 7.25]
    assert payload["sigma_m"] == [0.5, 0.25, 1.0]
    assert payload["obstacle"] == [0, -1, 100]
    json.dumps(payload, allow_nan=False)


def test_generated_terrainmeta_nan_nodata_has_explicit_json_sentinel():
    meta = rosidl.get_message("mge_interfaces/msg/TerrainMeta")()
    meta.run_id = "generated-contract-run"
    meta.dataset_id = "generated-contract-dataset"
    meta.nodata_value = nan
    payload = ros_json(meta)
    assert payload["nodata_value"] is None
    json.dumps(payload, allow_nan=False)
    meta.nodata_value = float("inf")
    with pytest.raises(ValueError, match="NONFINITE_JSON_VALUE"):
        ros_json(meta)


def test_actual_planner_failure_serializes_unavailable_metrics_explicitly():
    # Use the integrated producer's failure builder rather than recreating its
    # NaN convention in a test double. This still tests serialization, not ROS
    # service transport or physical feasibility.
    from mge_planning.node import _failure
    from mge_planning.core import RouteStatus
    PlanRoute = rosidl.get_service("mge_interfaces/srv/PlanRoute")
    request, response = PlanRoute.Request(), PlanRoute.Response()
    request.run_id, request.request_id = "generated-run", "generated-request"
    request.agent_id, request.agent_kind, request.mode = "human-1", "HUMAN", "FAST"
    response = _failure(request, response, RouteStatus.UNKNOWN, "PROFILE_NOT_READY", "Profile missing.")
    payload = ros_json(response.decision, agent_kind=request.agent_kind)
    assert payload["status"] == "UNKNOWN"
    assert payload["reason_code"] == "PROFILE_NOT_READY"
    assert payload["route_id"] == ""
    for key in ("travel_time_s", "energy_est_wh", "oxygen_est_l", "min_clearance_m",
                "reserve_time_s", "reserve_wh", "reserve_oxygen_l"):
        assert payload[key] is None
    json.dumps(payload, allow_nan=False)
    response.decision.energy_est_wh = float("inf")
    with pytest.raises(ValueError, match="NONFINITE_JSON_VALUE"):
        ros_json(response.decision, agent_kind=request.agent_kind)
