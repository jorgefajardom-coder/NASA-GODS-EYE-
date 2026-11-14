from copy import deepcopy
from array import array
import json
from math import nan
from pathlib import Path

import pytest

from mge_bringup.contract_guard import (
    AGENT_KINDS, ROUTE_MODES, ROUTE_STATUSES, GridGeometry,
    IdempotencyLedger, SnapshotLedger, assert_public_payload,
    candidate_rejection, enu_to_three, logical_stop_on_map_change, ros_json,
)
from mge_planning.core import RouteMode, RouteStatus
from mge_mission.core import MissionStatus, TaskStatus

ROOT = Path(__file__).resolve().parents[2]


def definitions(name):
    lines = (ROOT / "src/mge_interfaces/msg" / f"{name}.msg").read_text().splitlines()
    constants, fields = {}, {}
    for line in lines:
        line = line.split("#", 1)[0].strip()
        if not line:
            continue
        kind, name = line.split(maxsplit=1)
        if "=" in name:
            key, value = name.split("=", 1)
            constants[key] = (kind, value)
        else:
            fields[name] = kind
    return constants, fields


def test_wire_types_enums_and_consumer_enums_agree():
    constants, fields = definitions("RouteDecision")
    assert {v for k, (t, v) in constants.items() if k.startswith("STATUS_") and t == "string"} == ROUTE_STATUSES
    assert {v for k, (t, v) in constants.items() if k.startswith("MODE_") and t == "string"} == ROUTE_MODES
    assert {status.value for status in RouteStatus} == ROUTE_STATUSES
    assert {mode.value for mode in RouteMode} == ROUTE_MODES
    assert fields["map_version_used"] == "uint32"
    assert fields["outbound_path"] == fields["return_path"] == "geometry_msgs/Point[]"
    assert fields["oxygen_est_l"] == "float32"
    constants, _ = definitions("AgentState")
    assert {v for k, (t, v) in constants.items() if k.startswith("KIND_") and t == "string"} == AGENT_KINDS
    constants, _ = definitions("MissionState")
    assert {v for k, (t, v) in constants.items() if k.startswith("STATE_") and t == "string"} == {s.value for s in MissionStatus}
    assert {v for k, (t, v) in constants.items() if k.startswith("TASK_") and t == "string"} == {s.value for s in TaskStatus}
    _, fields = definitions("MissionEvent")
    assert fields["seq"] == "uint64"
    constants, fields = definitions("TerrainObservation")
    assert constants["OBSTACLE_UNKNOWN"] == ("int8", "-1")
    assert constants["OBSTACLE_FREE"] == ("int8", "0")
    assert constants["OBSTACLE_BLOCKED"] == ("int8", "100")
    assert constants["SOURCE_SIMULATED"] == ("string", "SIMULATED")
    assert fields["base_map_version"] == "uint32"


def test_asymmetric_grid_order_and_three_control_points():
    grid = GridGeometry(2, 3, 4, -6, 10)
    # Unequal dimensions/origin/elevation catch row/column and sign mistakes.
    cases = [(0, 0, 0, (-4, 12, 9), (-4, 9, -12)),
             (0, 2, 2, (4, 12, 5), (4, 5, -12)),
             (1, 1, 4, (0, 16, -2), (0, -2, -16))]
    for row, col, index, enu, three in cases:
        assert grid.index(row, col) == index
        assert grid.centre(row, col) == enu[:2]
        assert grid.require_centre(enu) == (row, col)
        assert enu_to_three(enu) == three


@pytest.mark.parametrize("point, reason", [((1.1, 1, 0), "NON_CELL_CENTER"),
    ((2, 1, 0), "NON_CELL_CENTER"), ((-1, 1, 0), "OUTSIDE_GRID"),
    ((1, nan, 0), "INVALID_POSITION")])
def test_continuous_pose_rejected_without_rounding(point, reason):
    with pytest.raises(ValueError, match=reason):
        GridGeometry(3, 3, 2).require_centre(point)


class RosAgentDouble:
    agent_kind = "ROVER"
    oxygen_remaining_l = nan
    pose = {"position": {"x": 1.0, "y": 2.0, "z": 3.0}}

    @staticmethod
    def get_fields_and_field_types():
        return {"agent_kind": "string", "oxygen_remaining_l": "float32", "pose": "geometry_msgs/Pose"}


def test_generated_ros_shape_nan_oxygen_to_strict_json_null():
    payload = ros_json({"agents": [RosAgentDouble()], "route": {"oxygen_est_l": nan}}, agent_kind="ROVER")
    assert payload["agents"][0]["oxygen_remaining_l"] is None
    assert payload["route"]["oxygen_est_l"] is None
    assert "NaN" not in json.dumps(payload, allow_nan=False)


@pytest.mark.parametrize("payload,kind,reason", [
    ({"oxygen_est_l": nan}, "HUMAN", "HUMAN_OXYGEN_REQUIRED"),
    ({"oxygen_est_l": nan}, None, "OXYGEN_KIND_REQUIRED"),
    ({"oxygen_est_l": 0}, "ROVER", "NONHUMAN_OXYGEN_MUST_BE_NAN"),
    ({"energy_est_wh": nan}, "ROVER", "NONFINITE_JSON_VALUE"),
    ({"energy_est_wh": float("inf")}, "ROVER", "NONFINITE_JSON_VALUE"),
    ({"agent_kind": "human"}, None, "UNKNOWN_AGENT_KIND"),
])
def test_nan_conversion_is_contextual_not_blanket_sanitizing(payload, kind, reason):
    with pytest.raises(ValueError, match=reason):
        ros_json(payload, agent_kind=kind)


@pytest.mark.parametrize("namespace", ["request", "event", "observation"])
def test_idempotent_duplicate_and_conflicting_identifier(namespace):
    ledger = IdempotencyLedger("run-1")
    options = {"seq": 8} if namespace == "event" else {}
    payload = {"run_id": "run-1", "value": [3, 1, 4]}
    assert ledger.accept(namespace, "id-1", payload, **options)
    assert not ledger.accept(namespace, "id-1", deepcopy(payload), **options)
    with pytest.raises(ValueError, match="IDEMPOTENCY_CONFLICT"):
        ledger.accept(namespace, "id-1", {**payload, "value": [1]}, **options)
    with pytest.raises(ValueError, match="RUN_MISMATCH"):
        ledger.accept(namespace, "id-2", {**payload, "run_id": "foreign"}, **options)


def test_event_order_requires_unique_increasing_sequence():
    ledger = IdempotencyLedger("run-1")
    payload = {"run_id": "run-1"}
    ledger.accept("event", "event-1", payload, seq=10)
    for seq in (10, 9, True, 2**64):
        with pytest.raises(ValueError, match="EVENT_SEQUENCE_REGRESSION"):
            ledger.accept("event", "event-2", payload, seq=seq)


def batch(version=1, stamp=(1, 0), run="run-1"):
    identity = {"run_id": run, "map_version": version, "stamp": list(stamp), "frame_id": "map"}
    layers = {"belief": [10, None, 12, 13], "sigma": [.1, None, .2, .3],
              "traversability/human": [0, -1, 100, 0],
              "traversability/rover": [0, -1, 100, 0],
              "traversability/drone": [0, -1, 0, 0]}
    return {**identity, "dataset_id": "synthetic-contract-grid",
            "geometry": {"rows": 2, "cols": 2, "resolution_m": 2},
            "layers": {name: {**identity, "values": values} for name, values in layers.items()}}


def test_complete_immutable_snapshot_identity_not_arrival_time():
    ledger = SnapshotLedger()
    original = batch()
    assert ledger.accept(original)
    assert not ledger.accept(deepcopy(original))
    changed = deepcopy(original)
    changed["layers"]["belief"]["values"][0] = 999
    with pytest.raises(ValueError, match="IMMUTABLE_BATCH_CHANGED"):
        ledger.accept(changed)
    assert ledger.accept(batch(2, (2, 0)))
    with pytest.raises(ValueError, match="STALE_MAP"):
        ledger.accept(original)
    with pytest.raises(ValueError, match="STAMP_REUSED"):
        ledger.accept(batch(3, (2, 0)))


@pytest.mark.parametrize("identity_key,new_value", [("run_id", "other"), ("map_version", 2),
    ("stamp", [2, 0]), ("frame_id", "odom")])
def test_rasters_cannot_mix_run_version_stamp_frame(identity_key, new_value):
    broken = batch()
    broken["layers"]["sigma"][identity_key] = new_value
    with pytest.raises(ValueError, match="LAYER_IDENTITY_MISMATCH"):
        SnapshotLedger().accept(broken)


def test_incomplete_negative_sigma_bad_mask_and_retired_run_fail():
    value = batch()
    del value["layers"]["sigma"]
    with pytest.raises(ValueError, match="SNAPSHOT_INCOMPLETE"):
        SnapshotLedger().accept(value)
    for name, bad_value in [("sigma", -.1), ("traversability/human", 7)]:
        value = batch()
        value["layers"][name]["values"][0] = bad_value
        with pytest.raises(ValueError, match="INVALID_"):
            SnapshotLedger().accept(value)
    ledger = SnapshotLedger()
    ledger.accept(batch())
    ledger.accept(batch(0, (3, 0), "run-2"))
    with pytest.raises(ValueError, match="RETIRED_RUN"):
        ledger.accept(batch(2, (4, 0)))


def route_case():
    a, b = {"x": 1, "y": 1, "z": 0}, {"x": 3, "y": 1, "z": 0}
    request = {"run_id": "run-1", "request_id": "request-1", "agent_id": "human-1", "agent_kind": "HUMAN",
        "mode": "FAST", "map_version": 1, "start": a, "goal": b, "return_to": a, "require_return": True,
        "service_time_s": 10, "time_budget_s": 100, "energy_budget_wh": 30, "oxygen_budget_l": 20,
        "reserve_time_s": 20, "reserve_wh": 5, "reserve_oxygen_l": 3}
    costs = {"travel_time_s": 50, "energy_est_wh": 10, "oxygen_est_l": 8}
    decision = {"run_id": "run-1", "request_id": "request-1", "agent_id": "human-1", "mode": "FAST",
        "map_version_used": 1, "status": "FEASIBLE", "route_id": "route-1", "min_clearance_m": .5,
        "outbound_path": [a, b], "return_path": [b, a], **costs,
        "reserve_time_s": 50, "reserve_wh": 20, "reserve_oxygen_l": 12}
    return request, decision, costs


def audit(request, decision, costs=None, agreed=True, version=1):
    return candidate_rejection(request, decision, current_run="run-1", current_map_version=version,
                               model_agreed=agreed, recomputed_costs=costs)


def test_candidate_needs_model_agreement_and_independent_numeric_audit():
    request, decision, costs = route_case()
    assert audit(request, decision, costs, agreed=False) == "MODEL_NOT_AGREED"
    assert audit(request, decision) == "MODEL_AUDIT_REQUIRED"
    assert audit(request, decision, costs) == ""
    assert audit(request, decision, {**costs, "energy_est_wh": 10.2}) == "MODEL_MISMATCH"
    assert audit(request, decision, costs, version=2) == "STALE_MAP"


@pytest.mark.parametrize("key,value,reason", [("return_path", [], "RETURN_PATH_REQUIRED"),
    ("reserve_time_s", 25, "RESERVE_MISMATCH"), ("energy_est_wh", -1, "INVALID_RESOURCES"),
    ("request_id", "other", "RESPONSE_MISMATCH")])
def test_route_return_and_identity_guard(key, value, reason):
    request, decision, costs = route_case()
    decision[key] = value
    assert audit(request, decision, costs) == reason


def test_roundtrip_reserve_is_constraint_not_merely_reported_number():
    request, decision, costs = route_case()
    request["reserve_time_s"] = 51
    assert audit(request, decision, costs) == "INSUFFICIENT_BUDGET"


@pytest.mark.parametrize("status", sorted(ROUTE_STATUSES - {"FEASIBLE"}))
def test_all_nonfeasible_statuses_remain_non_authorizable(status):
    request, decision, costs = route_case()
    decision["status"] = status
    assert audit(request, decision, costs) == status


def test_new_map_requires_invalidation_and_logical_stop():
    _, route, _ = route_case()
    assert logical_stop_on_map_change(route, current_run="run-1", current_map_version=1) == {
        "invalidate_route": False, "stop_required": False, "reason_code": ""}
    assert logical_stop_on_map_change(route, current_run="run-1", current_map_version=2) == {
        "invalidate_route": True, "stop_required": True, "reason_code": "STALE_MAP"}


@pytest.mark.parametrize("payload", [
    {"evaluator_reference": [1]}, {"layers": [{"ground_truth_dem": "secret.tif"}]},
    {"wrapper": {"role": "reference"}}, {"future_tasks": []}, {"metadata": {"hiddenSites": []}},
])
def test_reference_rejected_in_nested_and_unexpected_fields(payload):
    with pytest.raises(ValueError, match="EVALUATOR_REFERENCE|NONPUBLIC_ROLE"):
        assert_public_payload(payload)


def test_complete_snapshot_rejects_nonallowlisted_fields_even_if_renamed():
    value = batch()
    value["extra_layer"] = {"role": "belief", "values": [42]}
    with pytest.raises(ValueError, match="UNEXPECTED_BATCH_FIELDS"):
        SnapshotLedger().accept(value)


def test_nodata_is_never_silently_treated_as_free():
    value = batch()
    value["layers"]["traversability/rover"]["values"][1] = 0
    with pytest.raises(ValueError, match="NODATA_MARKED_FREE"):
        SnapshotLedger().accept(value)


def test_nonhuman_roundtrip_normalized_oxygen_and_invalid_boolean_version():
    request, decision, costs = route_case()
    request["agent_kind"] = "ROVER"
    request["oxygen_budget_l"] = request["reserve_oxygen_l"] = None
    decision["oxygen_est_l"] = decision["reserve_oxygen_l"] = None
    assert audit(request, decision, costs) == ""
    decision["oxygen_est_l"] = 0
    assert audit(request, decision, costs) == "OXYGEN_NOT_APPLICABLE"
    decision["map_version_used"] = True
    assert audit(request, decision, costs) == "INVALID_MAP_VERSION"


def test_agreement_requires_explicit_boolean_and_service_in_total_time():
    request, decision, costs = route_case()
    assert audit(request, decision, costs, agreed="true") == "MODEL_NOT_AGREED"
    request["service_time_s"] = 51
    assert audit(request, decision, costs) == "INVALID_TOTAL_TIME"


def test_ros_native_arrays_serialize_without_losing_values_or_order():
    payload = ros_json({"cell_indices": array("I", [3, 0, 7]),
        "elevation_m": array("f", [1.5, -2.0, 3.25]), "obstacle": array("b", [0, -1, 100])})
    assert payload == {"cell_indices": [3, 0, 7], "elevation_m": [1.5, -2.0, 3.25], "obstacle": [0, -1, 100]}
    json.dumps(payload, allow_nan=False)
    with pytest.raises(ValueError, match="NONFINITE_JSON_VALUE"):
        ros_json({"elevation_m": array("f", [float("nan")])})


def test_nodata_nan_requires_explicit_terrainmeta_context_and_never_allows_infinity():
    assert ros_json({"nodata_value": nan}, message_type="mge_interfaces/msg/TerrainMeta") == {"nodata_value": None}
    assert ros_json({"nodata_value": -9999.0}, message_type="mge_interfaces/msg/TerrainMeta") == {"nodata_value": -9999.0}
    for payload, context in [({"nodata_value": nan}, None),
            ({"nodata_value": float("inf")}, "mge_interfaces/msg/TerrainMeta"),
            ({"elevation_m": nan}, "mge_interfaces/msg/TerrainMeta"),
            ({"nested": {"nodata_value": nan}}, "mge_interfaces/msg/TerrainMeta")]:
        with pytest.raises(ValueError, match="NONFINITE_JSON_VALUE"):
            ros_json(payload, message_type=context)
