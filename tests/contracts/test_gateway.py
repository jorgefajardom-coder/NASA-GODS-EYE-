"""Verify the unavailable HTTP boundary never fabricates an operational mission."""

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from mge_gateway.api import app


@pytest.fixture
def client():
    with TestClient(app) as session:
        yield session


def assert_unavailable(payload, run_id=None):
    assert payload["schema_version"] == "1.0.0"
    assert payload["run_id"] == run_id
    assert payload["mode"] is None
    assert payload["map_version"] is None
    assert payload["timestamp_sim_s"] is None
    assert payload["status"] == "NOT_READY"
    assert payload["reason_code"] == "ROS_NOT_CONNECTED"
    assert "route_id" not in payload
    assert "mission_success" not in payload


def test_health_distinguishes_process_availability_from_ros_readiness(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    payload = response.json()
    assert_unavailable(payload)
    assert payload["ros_connected"] is False
    assert payload["implementation_status"] == "scaffold"


@pytest.mark.parametrize(
    ("path", "run_id"),
    [("/api/manifest", None), ("/api/run/requested-run/snapshot", "requested-run")],
)
def test_unavailable_reads_return_503_without_inventing_state(client, path, run_id):
    response = client.get(path)
    assert response.status_code == 503
    assert_unavailable(response.json(), run_id)


def test_goal_is_not_accepted_when_ros_is_disconnected(client):
    response = client.post(
        "/api/mission/goal",
        json={"run_id": "requested-run", "request_id": "request-1"},
    )
    assert response.status_code == 503
    assert_unavailable(response.json(), "requested-run")
    assert response.json().get("accepted") is not True


def test_event_stream_reports_unavailable_then_closes_with_retry_code(client):
    with client.websocket_connect("/api/events") as socket:
        assert_unavailable(socket.receive_json())
        with pytest.raises(WebSocketDisconnect) as closed:
            socket.receive_json()
        assert closed.value.code == 1013
