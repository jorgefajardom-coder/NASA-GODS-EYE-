"""HTTP contract of the gateway, without ROS: a fake bridge feeds the store.

Covers the unavailable boundary (no run loaded: nothing is invented, nothing
is LIVE) and the envelope and error semantics once a run is active. The
ROS-to-HTTP flow itself is covered in tests/integration.
"""
import json

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from mge_gateway.app import create_app
from mge_gateway.store import RunStore

RUN = 'run-a'
GOAL = {
    'request_id': 'request-1', 'primary_agent_id': 'human_1',
    'base': {'x': 0, 'y': 0}, 'goal': {'x': 10, 'y': 0},
    'time_budget_s': 100, 'energy_budget_wh': 100,
}


class FakeBridge:
    cors_origins = ['http://localhost:5173']

    def __init__(self):
        self.store = RunStore(RUN)
        self.on_update = None
        self.answer = None
        self.goals = []

    def now_s(self):
        return 42.0

    def set_goal(self, fields):
        self.goals.append(fields)
        return self.answer


@pytest.fixture
def bridge():
    return FakeBridge()


@pytest.fixture
def client(bridge):
    with TestClient(create_app(bridge)) as session:
        yield session


def activate(bridge):
    bridge.store.apply_state({
        'run_id': RUN, 'last_event_seq': 1, 'map_version': 3, 'route_id': '',
        'agents': [{'agent_id': 'rover_1', 'agent_kind': 'ROVER', 'oxygen_remaining_l': None}],
    })
    bridge.store.apply_event({'run_id': RUN, 'event_id': f'{RUN}-e1', 'seq': 1})


def assert_unavailable(payload, run_id=None, reason='NO_ACTIVE_RUN', status='NOT_READY'):
    assert payload['schema_version'] == '1.0.0'
    assert payload['run_id'] == run_id
    assert payload['mode'] is None
    assert payload['map_version'] is None
    assert payload['timestamp_sim_s'] is None
    assert payload['status'] == status
    assert payload['reason_code'] == reason
    assert 'route_id' not in payload
    assert 'mission_state' not in payload


# ---- no run loaded --------------------------------------------------------

def test_health_distinguishes_process_availability_from_readiness(client):
    response = client.get('/api/health')
    assert response.status_code == 200
    payload = response.json()
    assert_unavailable(payload)
    assert payload['ros_connected'] is False


@pytest.mark.parametrize(('path', 'run_id'), [
    ('/api/manifest', None),
    ('/api/run/requested-run/snapshot', 'requested-run'),
    ('/api/run/requested-run/events', 'requested-run'),
])
def test_reads_return_503_without_inventing_state(client, path, run_id):
    response = client.get(path)
    assert response.status_code == 503
    assert_unavailable(response.json(), run_id)


def test_goal_is_not_forwarded_without_an_active_run(client, bridge):
    response = client.post('/api/mission/goal', json=GOAL)
    assert response.status_code == 503
    assert_unavailable(response.json())
    assert bridge.goals == []


def test_event_stream_reports_unavailable_then_closes_with_retry_code(client):
    with client.websocket_connect('/api/events') as socket:
        assert_unavailable(socket.receive_json())
        with pytest.raises(WebSocketDisconnect) as closed:
            socket.receive_json()
        assert closed.value.code == 1013


# ---- run active -----------------------------------------------------------

def test_active_run_is_live_with_full_envelope(client, bridge):
    activate(bridge)
    health = client.get('/api/health').json()
    assert health['status'] == 'READY' and health['ros_connected'] is True
    snap = client.get(f'/api/run/{RUN}/snapshot').json()
    assert {k: snap[k] for k in ('schema_version', 'run_id', 'mode', 'map_version',
                                 'timestamp_sim_s')} == {
        'schema_version': '1.0.0', 'run_id': RUN, 'mode': 'LIVE', 'map_version': 3,
        'timestamp_sim_s': 42.0}
    assert snap['mission_state']['agents'][0]['oxygen_remaining_l'] is None
    assert [e['seq'] for e in snap['events']] == [1]
    manifest = client.get('/api/manifest').json()
    assert manifest['agents'] == [{'agent_id': 'rover_1', 'agent_kind': 'ROVER'}]


def test_unknown_run_is_404(client, bridge):
    activate(bridge)
    assert client.get('/api/run/other/snapshot').status_code == 404
    assert client.get('/api/run/other/events').status_code == 404


def test_goal_is_forwarded_and_answer_wrapped(client, bridge):
    activate(bridge)
    bridge.answer = {'accepted': True, 'request_id': 'request-1', 'run_id': RUN,
                     'mission_state': 'PLANNING', 'reason_code': 'ACCEPTED', 'detail': ''}
    response = client.post('/api/mission/goal', json=GOAL)
    assert response.status_code == 200
    body = response.json()
    assert body['accepted'] is True and body['mode'] == 'LIVE'
    assert bridge.goals[0]['request_id'] == 'request-1'
    assert bridge.goals[0]['mode'] == 'FAST'


def test_silent_mission_service_is_an_explicit_error(client, bridge):
    activate(bridge)
    response = client.post('/api/mission/goal', json=GOAL)   # fake answers None
    assert response.status_code == 503
    assert_unavailable(response.json(), RUN, 'MISSION_SERVICE_UNAVAILABLE', 'ERROR')


def test_malformed_goal_is_422(client, bridge):
    activate(bridge)
    bad = {k: v for k, v in GOAL.items() if k != 'goal'}
    assert client.post('/api/mission/goal', json=bad).status_code == 422
    assert client.post('/api/mission/goal', json={**GOAL, 'mode': 'TURBO'}).status_code == 422
    assert bridge.goals == []


@pytest.mark.parametrize('point', ['base', 'goal'])
@pytest.mark.parametrize('axis', ['x', 'y', 'z'])
@pytest.mark.parametrize('value', ['NaN', 'Infinity', '-Infinity'])
def test_nonfinite_coordinates_never_reach_ros(client, bridge, point, axis, value):
    activate(bridge)
    bridge.answer = {'accepted': True}
    payload = {**GOAL, point: {**GOAL[point], axis: value}}
    response = client.post('/api/mission/goal', json=payload)
    assert response.status_code == 422
    assert bridge.goals == []


@pytest.mark.parametrize('field', [
    'time_budget_s', 'energy_budget_wh', 'oxygen_budget_l',
    'reserve_time_s', 'reserve_wh', 'reserve_oxygen_l',
])
@pytest.mark.parametrize('value', ['NaN', 'Infinity', '-Infinity', -1, 1e100])
def test_invalid_resource_values_never_reach_ros(client, bridge, field, value):
    activate(bridge)
    bridge.answer = {'accepted': True}
    response = client.post('/api/mission/goal', json={**GOAL, field: value})
    assert response.status_code == 422
    assert bridge.goals == []


def test_finite_coordinates_and_zero_reserves_are_forwarded(client, bridge):
    activate(bridge)
    bridge.answer = {'accepted': True}
    response = client.post('/api/mission/goal', json={
        **GOAL, 'goal': {'x': -10.5, 'y': 2.25, 'z': 0.5},
        'oxygen_budget_l': 100, 'reserve_time_s': 0, 'reserve_wh': 0,
        'reserve_oxygen_l': 0,
    })
    assert response.status_code == 200
    assert bridge.goals[0]['goal'] == {'x': -10.5, 'y': 2.25, 'z': 0.5}
    assert bridge.goals[0]['reserve_wh'] == 0


@pytest.mark.parametrize('token', ['NaN', 'Infinity', '-Infinity', '1e309'])
def test_raw_nonfinite_json_gets_a_json_safe_422(client, bridge, token):
    activate(bridge)
    bridge.answer = {'accepted': True}
    raw = json.dumps({**GOAL, 'goal': {'x': '__invalid_number__', 'y': 0}})
    raw = raw.replace('"__invalid_number__"', token)
    response = client.post('/api/mission/goal', content=raw,
                           headers={'Content-Type': 'application/json'})
    assert response.status_code == 422
    assert response.json()['detail']
    json.dumps(response.json(), allow_nan=False)
    assert bridge.goals == []


def test_control_token_is_enforced(bridge, monkeypatch):
    monkeypatch.setenv('MGE_CONTROL_TOKEN', 'secret')
    activate(bridge)
    bridge.answer = {'accepted': True}
    with TestClient(create_app(bridge)) as client:
        assert client.post('/api/mission/goal', json=GOAL).status_code == 401
        ok = client.post('/api/mission/goal', json=GOAL,
                         headers={'Authorization': 'Bearer secret'})
        assert ok.status_code == 200


def test_event_stream_sends_backlog_then_state(client, bridge):
    activate(bridge)
    with client.websocket_connect('/api/events') as socket:
        first = socket.receive_json()
        assert first['type'] == 'event' and first['event']['seq'] == 1
        second = socket.receive_json()
        assert second['type'] == 'state' and second['mode'] == 'LIVE'
