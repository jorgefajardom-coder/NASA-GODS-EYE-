"""Obstacles + resources + system-chosen fallback, on a fresh MOCK/SIMULATED stack.

No operator decisions after the single sortie goal: the MOCK mission's opt-in
budget fallback picks nearer targets / the base by itself.
"""
import json, math, os, struct, subprocess, sys, time
from copy import deepcopy
from pathlib import Path

import httpx, rclpy, yaml
from rclpy.qos import DurabilityPolicy, QoSProfile, ReliabilityPolicy
from sensor_msgs.msg import Image
from mge_interfaces.msg import AgentState, RouteDecision, TerrainObservation
from mge_interfaces.srv import PlanRoute
from mge_sim.obstacle_field import generate_field, passage_exists

sys.path.insert(0, os.getcwd())
from tests.integration.ground_fixture import initialize_ground_agents, observed_public_scene

RUN_ID, PORT, RECORD_DIR = sys.argv[1], int(sys.argv[2]), sys.argv[3]
SEED = int(sys.argv[4]) if len(sys.argv) > 4 else 7
BASE = f'http://127.0.0.1:{PORT}'
ROOT = Path.cwd()
PROFILES = ROOT / 'config' / 'planner_profiles.illustrative.json'
ROWS = COLS = 32
WINDOW = (8, 23, 8, 23)
AREA = {(r, c) for r in range(8, 24) for c in range(8, 24)}
OBSERVED = sorted(r * COLS + c for r, c in AREA)
HOME_RC, TARGET_RC = (12, 12), (21, 21)
AGENT_CELLS = [(12, 12), (12, 13), (13, 12)]   # human, drone, rover in agents_jezero.yaml
MARGIN = 0.12
RESERVE = {'time': 120.0, 'wh': 5.0, 'o2': 0.3}
LATCHED = QoSProfile(depth=1, reliability=ReliabilityPolicy.RELIABLE,
                     durability=DurabilityPolicy.TRANSIENT_LOCAL)
journal = []


def centre(rc):
    return -64.0 + (rc[1] + 0.5) * 4.0, -64.0 + (rc[0] + 0.5) * 4.0


def cell_of(x, y):
    return math.floor((y + 64.0) / 4.0), math.floor((x + 64.0) / 4.0)


HOME = centre(HOME_RC)


def log(*a):
    line = ' '.join(str(x) for x in a)
    print(time.strftime('%H:%M:%S'), line, flush=True)
    journal.append({'t': time.time(), 'msg': line})


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


field = generate_field(ROWS, COLS, WINDOW, HOME_RC, TARGET_RC, protected=AGENT_CELLS, seed=SEED)
blocked = set(field.blocked)
surface, _ = observed_public_scene(RUN_ID, OBSERVED)
template = yaml.safe_load((ROOT / 'src/mge_bringup/config/agents_jezero.yaml').read_text())
os.makedirs(RECORD_DIR, exist_ok=True)
agents_file = Path(RECORD_DIR) / f'{RUN_ID}-simulated-ground-agents.yaml'
agents_file.write_text(yaml.safe_dump(initialize_ground_agents(template, surface)))
launch_log = open(Path(RECORD_DIR) / f'{RUN_ID}-launch.log', 'w')
proc = subprocess.Popen(
    ['ros2', 'launch', 'mge_bringup', 'vertical_mock.launch.py', f'run_id:={RUN_ID}', f'port:={PORT}',
     'terrain:=real', 'planner:=real', 'allow_legacy_cost_model:=true', f'profiles_file:={PROFILES}', f'agents_file:={agents_file}',
     'agents:=kinematic', 'allow_continuous_starts:=true', 'budget_fallback:=true',
     'record:=true', f'record_dir:={RECORD_DIR}'],
    stdout=launch_log, stderr=subprocess.STDOUT, start_new_session=True)
(Path(RECORD_DIR) / f'{RUN_ID}-launch.pid').write_text(str(proc.pid))
log(f'launch pid {proc.pid}; obstacle field seed {SEED}: ridge {len(field.ridge)} cells, '
    f'gap {field.gap}, {len(field.rocks)} rock clusters ({field.dropped} dropped to keep a passage)')

rclpy.init()
node = rclpy.create_node('obstacle_scenario_driver')
st = {'belief': None, 'human': []}
node.create_subscription(Image, '/mge/terrain/belief', lambda m: st.__setitem__('belief', m), LATCHED)
node.create_subscription(AgentState, '/mge/agents/human_1/state', st['human'].append,
                         QoSProfile(depth=50, reliability=ReliabilityPolicy.RELIABLE))
pub = node.create_publisher(TerrainObservation, '/mge/observations',
                            QoSProfile(depth=10, reliability=ReliabilityPolicy.RELIABLE))
planner = node.create_client(PlanRoute, '/mge/planner/plan_route')


def spin_until(check, what, timeout=60.0):
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        rclpy.spin_once(node, timeout_sec=0.05)
        r = check()
        if r:
            return r
    raise SystemExit(f'timed out waiting for {what}')


def observe(obs_id, cells_blocked):
    spin_until(lambda: st['belief'] is not None, 'belief')
    spin_until(lambda: pub.get_subscription_count() >= 1, 'mapping subscriber')
    heights = struct.unpack(f'<{ROWS * COLS}f', bytes(st['belief'].data))
    version = mission()['map_version']
    flat = {r * COLS + c for r, c in cells_blocked}
    msg = TerrainObservation()
    msg.header.frame_id = 'map'
    msg.header.stamp = node.get_clock().now().to_msg()
    msg.observation_id, msg.run_id, msg.agent_id = obs_id, RUN_ID, 'drone_1'
    msg.base_map_version = version
    msg.source_kind = TerrainObservation.SOURCE_SIMULATED
    msg.cell_indices = OBSERVED
    msg.elevation_m = [float(surface.elevation_m.flat[i]) for i in OBSERVED]
    msg.sigma_m = [0.25] * len(OBSERVED)
    msg.obstacle = [TerrainObservation.OBSTACLE_BLOCKED if i in flat else TerrainObservation.OBSTACLE_FREE
                    for i in OBSERVED]
    pub.publish(msg)
    log(f'drone_1 SIMULATED observation {obs_id} on map v{version}: {len(flat)} blocked cells')
    wait(lambda: mission()['map_version'] > version, f'map after {obs_id}')
    return version


def plan_cost(goal_rc, budget):
    spin_until(lambda: planner.service_is_ready(), 'planner service')
    h = spin_until(lambda: st['human'][-1] if st['human'] else None, 'human state')
    req = PlanRoute.Request()
    req.run_id, req.request_id, req.agent_id = RUN_ID, f'calib-{time.time():.0f}', 'human_1'
    req.agent_kind = h.agent_kind
    req.start = deepcopy(h.pose.position)
    req.goal.x, req.goal.y = centre(goal_rc)
    req.return_to.x, req.return_to.y = HOME
    req.require_return, req.mode = True, 'FAST'
    req.map_version = mission()['map_version']
    req.time_budget_s, req.energy_budget_wh, req.oxygen_budget_l = budget
    req.reserve_time_s, req.reserve_wh, req.reserve_oxygen_l = RESERVE['time'], RESERVE['wh'], RESERVE['o2']
    fut = planner.call_async(req)
    spin_until(lambda: fut.done(), 'planner answer', 120)
    return fut.result().decision


def res(s):
    return s.time_remaining_s, s.energy_remaining_wh, s.oxygen_remaining_l


try:
    wait(lambda: len(get('/api/manifest').get('agents', [])) == 3, 'gateway with 3 agents', 90)
    wait(lambda: mission()['map_version'] >= 1, 'map v1')
    log('gateway ready; holding 15 s on map v1 so the viewer can attach')
    time.sleep(15)
    observe('obs-field', blocked)

    d = plan_cost(TARGET_RC, (14400.0, 1000.0, 1000.0))
    if d.status != RouteDecision.STATUS_FEASIBLE:
        raise SystemExit(f'calibration failed: {d.status} {d.reason_code} {d.detail}')
    direct = math.dist(centre(HOME_RC), centre(TARGET_RC)) * 2
    log(f'route around the obstacles costs {d.travel_time_s:.0f} s, {d.energy_est_wh:.2f} Wh, '
        f'{d.oxygen_est_l:.3f} L O2 (path {len(d.outbound_path) + len(d.return_path)} points; '
        f'straight round trip would be {direct:.0f} m)')
    budget = (d.travel_time_s * (1 + MARGIN) + RESERVE['time'], d.energy_est_wh * (1 + MARGIN) + RESERVE['wh'],
              d.oxygen_est_l * (1 + MARGIN) + RESERVE['o2'])
    start = res(st['human'][-1])
    body = {'request_id': 'sortie-far', 'primary_agent_id': 'human_1', 'base': {'x': HOME[0], 'y': HOME[1]},
            'goal': dict(zip('xy', centre(TARGET_RC))), 'mode': 'FAST',
            'time_budget_s': budget[0], 'energy_budget_wh': budget[1], 'oxygen_budget_l': budget[2],
            'reserve_time_s': RESERVE['time'], 'reserve_wh': RESERVE['wh'], 'reserve_oxygen_l': RESERVE['o2']}
    r = httpx.post(BASE + '/api/mission/goal', json=body, timeout=5).json()
    log(f'sortie to {TARGET_RC}: allocation O2 {budget[2]:.3f} L (+{MARGIN:.0%} over the route plus reserve): '
        f'{r.get("reason_code")}')
    m = wait(lambda: (x := mission())['mission_state'] in ('READY', 'BLOCKED') and x, 'sortie plan')
    if m['mission_state'] != 'READY':
        raise SystemExit(f'sortie not authorized: {m.get("reason_code")}')
    outbound = [(p['x'], p['y']) for p in m['active_route']['outbound_path']]
    log(f'route {m["route_id"]} published, {len(outbound)} outbound points')

    # Drone finds new rocks ahead on the outbound leg once the human has walked ~40% of it.
    first = len(st['human'])
    spin_until(lambda: any(s.mode == AgentState.MODE_MOVING for s in st['human'][first:]), 'moving')
    k = max(1, int(0.4 * (len(outbound) - 1)))
    spin_until(lambda: math.dist((st['human'][-1].pose.position.x, st['human'][-1].pose.position.y),
                                 outbound[0]) >= math.dist(outbound[0], outbound[k]), 'under way', 300)
    here = cell_of(st['human'][-1].pose.position.x, st['human'][-1].pose.position.y)
    ahead = cell_of(*outbound[min(len(outbound) - 1, int(0.75 * (len(outbound) - 1)))])
    keep = {(r + dr, c + dc) for r, c in (here, HOME_RC, TARGET_RC, *AGENT_CELLS)
            for dr in (-1, 0, 1) for dc in (-1, 0, 1)}
    new = set()
    for radius in (2, 1, 0):
        blob = {(ahead[0] + dr, ahead[1] + dc) for dr in range(-radius, radius + 1)
                for dc in range(-radius, radius + 1)} & AREA - keep
        if blob and passage_exists(here, TARGET_RC, AREA - blocked - blob):
            new = blob
            break
    blocked |= new
    observe('obs-rocks-ahead', blocked)
    halted = spin_until(lambda: next((s for s in st['human'][first:] if s.mode == AgentState.MODE_HALTED), None),
                        'halt acknowledgement')
    used = [a - b for a, b in zip(start, res(halted))]
    log(f'human_1 HALTED at cell {here} after {used[0]:.0f} s, {used[1]:.2f} Wh, {used[2]:.3f} L O2; '
        f'{len(new)} new rocks around cell {ahead}')

    # From here on only the mission decides. Follow its events until the human is home or it blocks.
    seen = 0
    end = time.monotonic() + 600
    while time.monotonic() < end:
        rclpy.spin_once(node, timeout_sec=0.1)
        events = get(f'/api/run/{RUN_ID}/events?after_seq={seen}')['events']
        for e in events:
            seen = max(seen, e['seq'])
            if e['event_type'] != 'MISSION_STATE_CHANGED' or e.get('reason_code'):
                log(f'  #{e["seq"]} {e["event_type"]} {e.get("reason_code", "")}: {e.get("detail", "")[:120]}')
        m = mission()
        h = st['human'][-1]
        at_home = math.dist((h.pose.position.x, h.pose.position.y), HOME) < 1e-3
        if m['mission_state'] == 'BLOCKED' and h.mode != AgentState.MODE_MOVING:
            log('mission BLOCKED with the human stopped')
            break
        if at_home and h.mode == AgentState.MODE_IDLE and len(st['human']) > first + 20 and m['mission_state'] == 'READY':
            spent = start[2] - h.oxygen_remaining_l
            log(f'human_1 home; consumed {spent:.3f} L O2 of {budget[2]:.3f} L allocated; '
                f'reserve kept: {budget[2] - spent >= RESERVE["o2"] - 1e-6}')
            break
    log('final goal in force:', m.get('primary_goal'), 'state', m['mission_state'])
    log(f'DONE; stack left running. Stop with: kill -INT -{proc.pid}')
finally:
    with open(Path(RECORD_DIR) / f'{RUN_ID}-scenario.json', 'w') as f:
        json.dump({'run_id': RUN_ID, 'source_mode': 'MOCK', 'observations': 'SIMULATED', 'seed': SEED,
                   'obstacles': {'ridge': field.ridge, 'gap': field.gap, 'rocks': field.rocks},
                   'note': 'Illustrative budgets and synthetic obstacles; not EVA limits or a validated mission.',
                   'journal': journal}, f, indent=1)
    node.destroy_node()
    rclpy.shutdown()
