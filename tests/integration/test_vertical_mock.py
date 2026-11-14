"""End-to-end test of the MOCK vertical through the web contract.

Starts `vertical_mock.launch.py` and talks to the gateway over HTTP and
WebSocket. It verifies the integration plumbing (ids, versions, ordering,
error states); the routes themselves come from a mock planner and prove
nothing about terrain.
"""
import asyncio
import json
import os
import signal
import subprocess
import time

import httpx
import pytest

pytest.importorskip('rclpy', reason='Requires built ROS 2 workspace')
websockets = pytest.importorskip('websockets')

RUN_ID = 'it-vertical'
PORT = 8765
BASE = f'http://127.0.0.1:{PORT}'
GOAL = {
    'primary_agent_id': 'human_1',
    'base': {'x': 2.5, 'y': 2.5},          # cell centres of the 5 m mock grid
    'goal': {'x': 302.5, 'y': 402.5},     # 500 m away -> 1000 m round trip
    'mode': 'FAST',
    'time_budget_s': 14400.0,
    'energy_budget_wh': 1000.0,
    'oxygen_budget_l': 1000.0,
    'reserve_time_s': 600.0,
    'reserve_wh': 100.0,
    'reserve_oxygen_l': 100.0,
}


def wait_for(predicate, timeout_s=20.0, what='condition'):
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        try:
            value = predicate()
            if value:
                return value
        except httpx.HTTPError:
            pass
        time.sleep(0.2)
    raise AssertionError(f'timed out waiting for {what}')


def snapshot():
    r = httpx.get(f'{BASE}/api/run/{RUN_ID}/snapshot')
    r.raise_for_status()
    return r.json()


def mission_in(*states):
    def check():
        snap = snapshot()
        ms = snap['mission_state']
        return snap if ms and ms['mission_state'] in states else None
    return check


@pytest.fixture(scope='module')
def stack(planner_ready):
    proc = subprocess.Popen(
        ['ros2', 'launch', 'mge_bringup', 'vertical_mock.launch.py',
         f'run_id:={RUN_ID}', f'port:={PORT}'],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, start_new_session=True)
    try:
        wait_for(lambda: (h := httpx.get(f'{BASE}/api/health').json())
                 and h['status'] == 'READY' and h['terrain_meta_received']
                 and len(httpx.get(f'{BASE}/api/manifest').json().get('agents', [])) == 3,
                 what='gateway, mission state and 3 agents')
        planner_ready()
        yield
    finally:
        os.killpg(proc.pid, signal.SIGINT)
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            os.killpg(proc.pid, signal.SIGKILL)


def test_envelope_and_manifest(stack):
    m = httpx.get(f'{BASE}/api/manifest').json()
    assert m['schema_version'] == '1.0.0'
    assert m['run_id'] == RUN_ID
    assert m['mode'] == 'LIVE'
    assert m['map_version'] == 1
    assert isinstance(m['timestamp_sim_s'], float)
    assert {a['agent_kind'] for a in m['agents']} == {'HUMAN', 'DRONE', 'ROVER'}
    assert m['terrain_meta']['dataset_id'].startswith('MOCK')
    assert httpx.get(f'{BASE}/api/run/other/snapshot').status_code == 404


def test_goal_to_route(stack):
    r = httpx.post(f'{BASE}/api/mission/goal', json={**GOAL, 'request_id': 'req-1'})
    assert r.status_code == 200, r.text
    assert r.json()['accepted'] is True
    snap = wait_for(mission_in('READY'), what='READY')
    ms = snap['mission_state']
    route = ms['active_route']
    assert route['status'] == 'FEASIBLE'
    assert route['map_version_used'] == 1
    assert ms['route_id'] == route['route_id'] != ''
    assert route['outbound_path'][0] == {'x': 2.5, 'y': 2.5, 'z': 0.0}
    assert route['outbound_path'][-1] == {'x': 302.5, 'y': 402.5, 'z': 0.0}
    assert route['return_path'][-1] == {'x': 2.5, 'y': 2.5, 'z': 0.0}
    assert route['travel_time_s'] == pytest.approx(1000.0)      # 1000 m at 1 m/s (mock)
    assert route['reserve_oxygen_l'] is not None                # human has oxygen
    types = [e['event_type'] for e in snap['events']]
    assert types == ['GOAL_ACCEPTED', 'MISSION_STATE_CHANGED', 'ROUTE_PUBLISHED',
                     'MISSION_STATE_CHANGED']
    seqs = [e['seq'] for e in snap['events']]
    assert seqs == sorted(set(seqs))


def test_repeated_request_is_idempotent(stack):
    before = len(snapshot()['events'])
    r = httpx.post(f'{BASE}/api/mission/goal', json={**GOAL, 'request_id': 'req-1'})
    assert r.json()['accepted'] is True
    time.sleep(1.0)
    snap = snapshot()
    assert len(snap['events']) == before
    assert snap['mission_state']['mission_state'] == 'READY'


def test_observation_bumps_map_and_replans(stack):
    old_route = snapshot()['mission_state']['route_id']
    obs = json.dumps({'observation_id': 'obs-1', 'run_id': RUN_ID, 'agent_id': 'drone_1',
                      'base_map_version': 1, 'source_kind': 'SIMULATED'})
    pub = ['ros2', 'topic', 'pub', '--once', '--qos-reliability', 'reliable',
           '-w', '1', '/mge/observations', 'mge_interfaces/msg/TerrainObservation', obs]
    subprocess.run(pub, check=True, capture_output=True, timeout=30)

    def replanned():
        snap = snapshot()
        ms = snap['mission_state']
        ok = ms['map_version'] == 2 and ms['mission_state'] == 'READY' and ms['route_id']
        return snap if ok else None

    snap = wait_for(replanned, what='replan on map version 2')
    ms = snap['mission_state']
    assert ms['route_id'] != old_route
    assert ms['active_route']['map_version_used'] == 2
    types = [e['event_type'] for e in snap['events']]
    i = types.index('MAP_UPDATED')
    assert types[i:i + 3] == ['MAP_UPDATED', 'ROUTE_INVALIDATED', 'MISSION_STATE_CHANGED']
    assert 'REPLAN' in [e['new_state'] for e in snap['events']]

    # I-04: the same observation again changes nothing.
    count = len(snap['events'])
    subprocess.run(pub, check=True, capture_output=True, timeout=30)
    time.sleep(1.0)
    snap = snapshot()
    assert snap['mission_state']['map_version'] == 2
    assert len(snap['events']) == count


def test_insufficient_budget_is_explicit(stack):
    r = httpx.post(f'{BASE}/api/mission/goal',
                   json={**GOAL, 'request_id': 'req-2', 'oxygen_budget_l': 50.0})
    assert r.json()['accepted'] is True
    ms = wait_for(mission_in('BLOCKED'), what='BLOCKED')['mission_state']
    assert ms['reason_code'] == 'INSUFFICIENT_BUDGET'
    assert ms['route_id'] == ''
    assert ms['active_route']['status'] == 'INSUFFICIENT_BUDGET'
    assert ms['active_route']['reason_code'] == 'RESERVE_NOT_MET_OXYGEN'
    assert ms['active_route']['outbound_path'] == []


def test_unknown_agent_is_rejected(stack):
    r = httpx.post(f'{BASE}/api/mission/goal',
                   json={**GOAL, 'request_id': 'req-3', 'primary_agent_id': 'ghost'})
    body = r.json()
    assert body['accepted'] is False
    assert body['reason_code'] == 'UNKNOWN_AGENT'
    assert snapshot()['events'][-1]['event_type'] == 'GOAL_REJECTED'


def test_invalid_body_is_rejected(stack):
    bad = {k: v for k, v in GOAL.items() if k != 'goal'}
    assert httpx.post(f'{BASE}/api/mission/goal', json=bad).status_code == 422


def test_websocket_and_polling_agree(stack):
    polled = httpx.get(f'{BASE}/api/run/{RUN_ID}/events', params={'after_seq': 2}).json()

    async def collect():
        got = []
        async with websockets.connect(f'ws://127.0.0.1:{PORT}/api/events?after_seq=2') as ws:
            while True:
                msg = json.loads(await asyncio.wait_for(ws.recv(), 5))
                assert msg['mode'] == 'LIVE' and msg['run_id'] == RUN_ID
                if msg['type'] == 'state':
                    return got, msg['state']
                got.append(msg['event'])

    events, state = asyncio.run(collect())
    assert [e['event_id'] for e in events] == [e['event_id'] for e in polled['events']]
    assert events[0]['seq'] == 3
    assert state['run_id'] == RUN_ID
