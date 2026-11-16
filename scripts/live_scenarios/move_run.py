"""Launch a SIMULATED/MOCK kinematic run the viewer can watch, then drive it.

Mirrors tests/integration/test_vertical_execution.py: real public data/mapping/planner,
MOCK mission, kinematic executor. Observations are SIMULATED copies of the orbital
prior (test inputs, not NASA measurements). Leaves the stack running at the end.
Run from a built workspace root with ROS sourced.
"""
import json, os, struct, subprocess, sys, time
from pathlib import Path

import httpx, rclpy, yaml
from rclpy.qos import DurabilityPolicy, QoSProfile, ReliabilityPolicy
from sensor_msgs.msg import Image
from mge_interfaces.msg import AgentState, TerrainObservation

sys.path.insert(0, os.getcwd())
from tests.integration.ground_fixture import initialize_ground_agents, observed_public_scene

RUN_ID, PORT, RECORD_DIR = sys.argv[1], int(sys.argv[2]), sys.argv[3]
BASE = f'http://127.0.0.1:{PORT}'
ROOT = Path.cwd()
PROFILES = ROOT / 'config' / 'planner_profiles.illustrative.json'
ROWS = COLS = 32
BLOCK = [r * COLS + c for r in range(8, 24) for c in range(8, 24)]
LATCHED = QoSProfile(depth=1, reliability=ReliabilityPolicy.RELIABLE,
                     durability=DurabilityPolicy.TRANSIENT_LOCAL)


def centre(row, col):
    return -64.0 + (col + 0.5) * 4.0, -64.0 + (row + 0.5) * 4.0


HOME = centre(12, 12)
REQUEST = {'primary_agent_id': 'human_1', 'base': {'x': HOME[0], 'y': HOME[1]}, 'mode': 'FAST',
           'time_budget_s': 14400.0, 'energy_budget_wh': 1000.0, 'oxygen_budget_l': 1000.0,
           'reserve_time_s': 600.0, 'reserve_wh': 100.0, 'reserve_oxygen_l': 100.0}


def log(*a):
    print(time.strftime('%H:%M:%S'), *a, flush=True)


def get(path):
    return httpx.get(BASE + path, timeout=5).json()


def mission():
    return get(f'/api/run/{RUN_ID}/snapshot')['mission_state']


def wait(check, what, timeout=60.0):
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        try:
            r = check()
            if r:
                return r
        except Exception:
            pass
        time.sleep(0.25)
    raise SystemExit(f'timed out waiting for {what}')


surface, _ = observed_public_scene(RUN_ID, BLOCK)
template = yaml.safe_load((ROOT / 'src/mge_bringup/config/agents_jezero.yaml').read_text())
os.makedirs(RECORD_DIR, exist_ok=True)
agents_file = Path(RECORD_DIR) / f'{RUN_ID}-simulated-ground-agents.yaml'
agents_file.write_text(yaml.safe_dump(initialize_ground_agents(template, surface)))
launch_log = open(Path(RECORD_DIR) / f'{RUN_ID}-launch.log', 'w')
proc = subprocess.Popen(
    ['ros2', 'launch', 'mge_bringup', 'vertical_mock.launch.py', f'run_id:={RUN_ID}', f'port:={PORT}',
     'terrain:=real', 'planner:=real', 'allow_legacy_cost_model:=true', f'profiles_file:={PROFILES}', f'agents_file:={agents_file}',
     'agents:=kinematic', 'allow_continuous_starts:=true', 'record:=true', f'record_dir:={RECORD_DIR}'],
    stdout=launch_log, stderr=subprocess.STDOUT, start_new_session=True)
(Path(RECORD_DIR) / f'{RUN_ID}-launch.pid').write_text(str(proc.pid))
log('launch pid', proc.pid)

rclpy.init()
node = rclpy.create_node('viewer_demo_driver')
state = {'belief': None, 'human': []}
node.create_subscription(Image, '/mge/terrain/belief', lambda m: state.__setitem__('belief', m), LATCHED)
node.create_subscription(AgentState, '/mge/agents/human_1/state', state['human'].append,
                         QoSProfile(depth=50, reliability=ReliabilityPolicy.RELIABLE))
pub = node.create_publisher(TerrainObservation, '/mge/observations',
                            QoSProfile(depth=10, reliability=ReliabilityPolicy.RELIABLE))


def spin_until(check, what, timeout=60.0):
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        rclpy.spin_once(node, timeout_sec=0.05)
        r = check()
        if r:
            return r
    raise SystemExit(f'timed out waiting for {what}')


def observe(obs_id, base_version):
    spin_until(lambda: state['belief'] is not None, 'belief layer')
    spin_until(lambda: pub.get_subscription_count() >= 1, 'mapping subscriber')
    heights = struct.unpack(f'<{ROWS * COLS}f', bytes(state['belief'].data))
    msg = TerrainObservation()
    msg.header.frame_id = 'map'
    msg.header.stamp = node.get_clock().now().to_msg()
    msg.observation_id, msg.run_id, msg.agent_id = obs_id, RUN_ID, 'drone_1'
    msg.base_map_version = base_version
    msg.source_kind = TerrainObservation.SOURCE_SIMULATED
    msg.cell_indices = BLOCK
    msg.elevation_m = [heights[i] for i in BLOCK]
    msg.sigma_m = [0.25] * len(BLOCK)
    msg.obstacle = [TerrainObservation.OBSTACLE_FREE] * len(BLOCK)
    pub.publish(msg)
    log('published SIMULATED observation', obs_id, 'on map v', base_version)


def submit(request_id, goal):
    r = httpx.post(BASE + '/api/mission/goal', timeout=5, json={
        **REQUEST, 'request_id': request_id, 'goal': {'x': goal[0], 'y': goal[1]}}).json()
    log('goal', request_id, '->', r.get('reason_code'), r.get('detail'))
    m = wait(lambda: (m := mission())['mission_state'] in ('READY', 'BLOCKED', 'EXECUTING') and m,
             f'{request_id} to settle')
    log('mission', m['mission_state'], m.get('reason_code'), 'route', m.get('route_id'))
    return m


try:
    wait(lambda: len(get('/api/manifest').get('agents', [])) == 3, 'gateway with 3 agents', 90)
    wait(lambda: mission()['map_version'] >= 1, 'map v1')
    log('gateway ready; holding 20 s on map v1 so the viewer can attach')
    time.sleep(20)
    observe('obs-block', 1)
    wait(lambda: mission()['map_version'] == 2, 'map v2')
    log('map v2 (SIMULATED observation fused)')

    m = submit('trip-short', centre(14, 12))
    if m['mission_state'] != 'BLOCKED':
        start = len(state['human'])
        spin_until(lambda: any(s.mode == AgentState.MODE_MOVING for s in state['human'][start:]), 'human moving')
        log('human_1 moving')
        spin_until(lambda: state['human'][-1].mode == AgentState.MODE_IDLE
                   and state['human'][-1].velocity.linear.x == 0.0, 'human back', 180)
        log('human_1 back at base')
    time.sleep(5)

    m = submit('trip-long', centre(19, 19))
    if m['mission_state'] != 'BLOCKED':
        start = len(state['human'])
        spin_until(lambda: any(s.mode == AgentState.MODE_MOVING for s in state['human'][start:]), 'human moving')
        time.sleep(0)
        spin_until(lambda: False if not state['human'] else
                   ((p := state['human'][-1].pose.position) and ((p.x - HOME[0]) ** 2 + (p.y - HOME[1]) ** 2) ** .5 > 6.0),
                   'human under way', 120)
        observe('obs-again', 2)
        h = spin_until(lambda: next((s for s in state['human'][start:] if s.mode == AgentState.MODE_HALTED), None),
                       'halt acknowledgement')
        log('human_1 HALTED at', round(h.pose.position.x, 2), round(h.pose.position.y, 2))
        m = wait(lambda: (x := mission())['map_version'] == 3 and x['mission_state'] in ('READY', 'BLOCKED', 'EXECUTING') and x,
                 'replan on map v3')
        log('replanned on map v3:', m['mission_state'], m.get('route_id'))
        spin_until(lambda: state['human'][-1].mode == AgentState.MODE_IDLE
                   and state['human'][-1].velocity.linear.x == 0.0 and len(state['human']) > start + 5,
                   'human idle after resumed trip', 300)
        log('human_1 finished resumed trip')
    events = get(f'/api/run/{RUN_ID}/events')['events']
    log('events:', len(events), sorted({e['event_type'] for e in events}))
    log('DONE; stack left running. Stop with: kill -INT -', proc.pid)
finally:
    node.destroy_node()
    rclpy.shutdown()
