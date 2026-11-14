"""Provider injection contracts, explicitly not real planner acceptance."""
from copy import deepcopy
import importlib.util
from pathlib import Path

import pytest

from mge_bringup.contract_guard import request_candidate


def request():
    point = {"x": 1.0, "y": 1.0, "z": 0.0}
    return {"run_id": "contract-mock-run", "request_id": "contract-request-1", "agent_id": "rover-1",
        "agent_kind": "ROVER", "mode": "FAST", "map_version": 3,
        "start": point, "goal": {**point, "x": 3.0}, "return_to": point,
        "require_return": True, "service_time_s": 0.0, "time_budget_s": 100.0,
        "energy_budget_wh": 100.0, "oxygen_budget_l": None,
        "reserve_time_s": 10.0, "reserve_wh": 10.0, "reserve_oxygen_l": None}


class CallableMockProvider:
    """Deterministic canonical service double, with no physical model."""
    def __call__(self, payload):
        return {"decision": {
            "header": {"frame_id": "map", "stamp": {"sec": 0, "nanosec": 0}},
            **{key: payload[key] for key in ("run_id", "request_id", "agent_id", "mode")},
            "map_version_used": payload["map_version"], "route_id": "",
            "status": "UNKNOWN", "reason_code": "MOCK_NO_PHYSICS",
            "detail": "Contractual mock; no physical feasibility is calculated.",
            "outbound_path": [], "return_path": [], "travel_time_s": 0.0,
            "energy_est_wh": 0.0, "oxygen_est_l": None, "min_clearance_m": 0.0,
            "reserve_time_s": 0.0, "reserve_wh": 0.0, "reserve_oxygen_l": None}}


def transport_mock_provider(payload):
    # A distinct transport seam returns the same service response shape. Both
    # providers in this test are mocks; neither may be labelled REAL or LIVE.
    return deepcopy(CallableMockProvider()(payload))


@pytest.mark.parametrize("provider", [CallableMockProvider(), transport_mock_provider])
def test_mock_provider_replacement_preserves_same_consumer(provider):
    payload = request()
    before = deepcopy(payload)
    result = request_candidate(provider, payload)
    assert result["status"] == "UNKNOWN"
    assert result["reason_code"] == "MOCK_NO_PHYSICS"
    assert payload == before


@pytest.mark.parametrize("provider", [lambda p: {"route": {}},
    lambda p: {"decision": {**p, "status": "LIVE"}},
    lambda p: {"decision": {**p, "run_id": "other", "status": "UNKNOWN"}}])
def test_consumer_rejects_provider_that_changes_contract(provider):
    with pytest.raises(ValueError, match="RESPONSE_REQUIRED|INVALID_PLAN_ROUTE_RESPONSE"):
        request_candidate(provider, request())


def test_real_planner_provider_uses_same_consumer_when_owner_module_available():
    if importlib.util.find_spec("mge_planning.adapter") is None:
        pytest.skip("REAL producer module is unavailable in this checkout; canonical mock seam only is tested")
    core = pytest.importorskip("mge_planning.core")
    if not hasattr(core, "TerrainGrid"):
        pytest.skip("Advanced planner has not been integrated")
    np = pytest.importorskip("numpy")
    payload = request()
    terrain = core.TerrainGrid(run_id=payload["run_id"], map_version=3,
        elevation_m=np.zeros((3, 3)), traversability=np.zeros((3, 3), dtype=int), resolution_m=2)
    # Deliberately omit a profile: a real planner must honestly return UNKNOWN,
    # without letting a mock's availability enable physical feasibility.
    def real_provider(message):
        plan = core.PlanRequest(run_id=message["run_id"], request_id=message["request_id"],
            agent_id=message["agent_id"], agent_kind="rover", map_version=3,
            start=(1, 1, 0), goal=(3, 1, 0), return_to=(1, 1, 0),
            budget=core.ResourceBudget("rover", 100, 100, 10))
        candidate = core.plan_route(terrain=terrain, request=plan)
        response = CallableMockProvider()(message)
        response["decision"].update(status=candidate.status.value, reason_code=candidate.reason_code)
        return response
    result = request_candidate(real_provider, payload)
    assert result["status"] == "UNKNOWN"
    assert result["reason_code"] == "PROFILE_NOT_READY"


def test_contractual_mock_fields_exactly_match_canonical_ros_service():
    root = Path(__file__).resolve().parents[2] / "src/mge_interfaces"
    def fields(text):
        result = set()
        for line in text.splitlines():
            line = line.split("#", 1)[0].strip()
            if line and line != "---" and "=" not in line:
                result.add(line.split()[1])
        return result
    service = (root / "srv/PlanRoute.srv").read_text().split("---", 1)
    payload = request()
    response = CallableMockProvider()(payload)
    assert set(payload) == fields(service[0])
    assert set(response) == fields(service[1])
    assert set(response["decision"]) == fields((root / "msg/RouteDecision.msg").read_text())
