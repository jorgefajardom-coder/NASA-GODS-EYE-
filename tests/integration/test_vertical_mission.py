"""Real mission + real planner transport smoke with synthetic public inputs.

The test-only clock and static terrain/agents are MOCK. The expected outcome is
MODEL_NOT_AGREED and an empty route, never physical or scientific acceptance.
"""
from pathlib import Path
import os
import signal
import subprocess
from threading import Thread
from time import monotonic, sleep

import httpx
import pytest

rclpy = pytest.importorskip('rclpy', reason='Requires built ROS 2 Jazzy workspace')
from builtin_interfaces.msg import Time
from rclpy.context import Context
from rclpy.executors import SingleThreadedExecutor
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy
from rosgraph_msgs.msg import Clock

ROOT = Path(__file__).resolve().parents[2]
RUN_ID = 'synthetic-real-mission-handoff'
DOMAIN_ID = 173
PORT = 8773
BASE = f'http://127.0.0.1:{PORT}'
GOAL = {
    'request_id': 'real-mission-model-gate', 'primary_agent_id': 'human_1',
    'base': {'x': 2.5, 'y': 2.5, 'z': 0.0},
    'goal': {'x': 12.5, 'y': 2.5, 'z': 0.0}, 'mode': 'FAST',
    'time_budget_s': 3600.0, 'energy_budget_wh': 600.0, 'oxygen_budget_l': 150.0,
    'reserve_time_s': 360.0, 'reserve_wh': 60.0, 'reserve_oxygen_l': 15.0,
}


def wait_for(predicate, timeout=30.0):
    deadline = monotonic() + timeout
    while monotonic() < deadline:
        try:
            result = predicate()
            if result:
                return result
        except (httpx.HTTPError, KeyError):
            pass
        sleep(0.1)
    raise AssertionError('Real mission transport smoke did not reach its expected condition')


def snapshot():
    response = httpx.get(f'{BASE}/api/run/{RUN_ID}/snapshot', timeout=5)
    response.raise_for_status()
    return response.json()


@pytest.fixture(scope='module')
def stack(tmp_path_factory):
    # This clock exists only in the test process. It advances deterministically
    # by 50 ms per timer callback; it claims no Gazebo or Mars dynamics.
    clock_context = Context()
    rclpy.init(context=clock_context, domain_id=DOMAIN_ID)
    clock_node = Node('synthetic_mission_handoff_clock', context=clock_context)
    publisher = clock_node.create_publisher(Clock, '/clock',
        QoSProfile(depth=1, reliability=ReliabilityPolicy.BEST_EFFORT))
    ticks = [100_000_000_000]
    def tick():
        ticks[0] += 50_000_000
        publisher.publish(Clock(clock=Time(sec=ticks[0] // 10**9, nanosec=ticks[0] % 10**9)))
    timer = clock_node.create_timer(0.05, tick)
    executor = SingleThreadedExecutor(context=clock_context)
    executor.add_node(clock_node)
    thread = Thread(target=executor.spin, daemon=True)
    thread.start()
    directory = tmp_path_factory.mktemp('real-mission-transport')
    log_path = directory / 'launch.log'
    proc = None
    try:
        with log_path.open('w', encoding='utf-8') as output:
            proc = subprocess.Popen([
                'ros2', 'launch', 'mge_bringup', 'vertical_mock.launch.py',
                f'run_id:={RUN_ID}', f'port:={PORT}', 'mission:=real', 'planner:=real',
                'use_sim_time:=true', f'mission_profiles_path:={ROOT / "config/scenario_demo.yaml"}',
                f'mission_path:={ROOT / "config/scenario_demo.yaml"}',
                f'profiles_file:={ROOT / "config/planner_profiles.illustrative.json"}',
                'base_enu_m:=[2.5, 2.5, 0.0]', 'allow_illustrative:=true',
                'model_agreement_confirmed:=false',
            ], env={**os.environ, 'ROS_DOMAIN_ID': str(DOMAIN_ID)},
                stdout=output, stderr=subprocess.STDOUT, start_new_session=True)
            wait_for(lambda: len(httpx.get(f'{BASE}/api/manifest', timeout=5).json().get('agents', [])) == 3)
            answer = httpx.post(f'{BASE}/api/mission/goal', json=GOAL, timeout=10)
            assert answer.status_code == 200 and answer.json()['accepted'] is True, answer.text
            wait_for(lambda: snapshot()['mission_state']['reason_code'] == 'MODEL_NOT_AGREED')
            yield clock_node
    except Exception:
        if log_path.exists():
            print(log_path.read_text(encoding='utf-8'))
        raise
    finally:
        if proc is not None and proc.poll() is None:
            os.killpg(proc.pid, signal.SIGINT)
            try:
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                os.killpg(proc.pid, signal.SIGKILL)
                proc.wait(timeout=5)
        executor.shutdown(timeout_sec=5)
        thread.join(timeout=5)
        clock_node.destroy_timer(timer)
        clock_node.destroy_node()
        clock_context.shutdown()


def test_real_mission_is_the_only_goal_and_route_authority(stack):
    def sole_authority():
        names = [name for name, _ in stack.get_node_names_and_namespaces()]
        return names if 'mission_node' in names and 'planning_node' in names else None
    names = wait_for(sole_authority)
    assert names.count('mission_node') == names.count('planning_node') == 1
    assert 'mock_mission' not in names and 'mock_planner' not in names
    providers = []
    for name, namespace in stack.get_node_names_and_namespaces():
        if any(service == '/mge/mission/set_goal'
               for service, _ in stack.get_service_names_and_types_by_node(name, namespace)):
            providers.append(name)
    assert providers == ['mission_node']
    manifest = httpx.get(f'{BASE}/api/manifest', timeout=5).json()
    assert manifest['schema_version'] == '1.0.0'
    assert manifest['terrain_meta']['dataset_id'] == 'MOCK-flat-grid'


def test_actual_planner_candidate_is_blocked_without_model_agreement(stack):
    response = httpx.post(f'{BASE}/api/mission/goal', json=GOAL, timeout=10)
    assert response.status_code == 200, response.text
    assert response.json()['accepted'] is True
    def blocked():
        payload = snapshot()
        state = payload['mission_state']
        return payload if state['mission_state'] == 'BLOCKED' else None
    payload = wait_for(blocked)
    state = payload['mission_state']
    assert state['reason_code'] == 'MODEL_NOT_AGREED'
    assert state['route_id'] == ''
    assert state['active_route']['outbound_path'] == []
    assert not any(event['event_type'] == 'ROUTE_PUBLISHED' for event in payload['events'])


def test_changed_payload_cannot_reuse_real_mission_request_id(stack):
    # The old mock simply returned its cached response for a conflicting payload.
    # This observes the real authority's fail-closed idempotency via the gateway.
    response = httpx.post(f'{BASE}/api/mission/goal', json={**GOAL,
        'goal': {'x': 17.5, 'y': 2.5, 'z': 0.0}}, timeout=10)
    assert response.status_code == 200, response.text
    assert response.json()['accepted'] is False
    assert response.json()['reason_code'] == 'REQUEST_ID_CONFLICT'
    assert snapshot()['mission_state']['route_id'] == ''
