"""Resource-pressure scenario on the running MOCK/SIMULATED stack (no code changes).

1. Calibrate: ask the real planner (read-only PlanRoute call) for the cost of a far
   sortie for human_1, then allocate an oxygen/time/energy budget that fits it with a
   small margin above the reserve.
2. The MOCK mission publishes the route; the kinematic human spends resources along it.
3. Mid-outbound, the drone publishes a SIMULATED observation that blocks a band of
   cells across the route (obstacles). The map version changes, the human halts, and
   the mission replans from the halted pose with the allocation that is left
   (budget - consumed). The detour no longer fits -> INSUFFICIENT_BUDGET.
4. Operator fallback (this script): try nearer targets with the remaining allocation,
   then return to base, until one fits. Every step is a mission goal through the gateway.

All observations are SIMULATED test inputs; budgets are illustrative, not EVA limits.
"""
import json, math, os, struct, sys, time
from copy import deepcopy

import httpx, rclpy
from rclpy.qos import DurabilityPolicy, QoSProfile, ReliabilityPolicy
from sensor_msgs.msg import Image
from mge_interfaces.msg import AgentState, RouteDecision, TerrainObservation
from mge_interfaces.srv import PlanRoute

RUN_ID, PORT = sys.argv[1], int(sys.argv[2])
OUT = sys.argv[3]
BASE = f'http://127.0.0.1:{PORT}'
ROWS = COLS = 32
OBSERVED = [r * COLS + c for r in range(8, 24) for c in range(8, 24)]
LATCHED = QoSProfile(depth=1, reliability=ReliabilityPolicy.RELIABLE,
                     durability=DurabilityPolicy.TRANSIENT_LOCAL)
MARGIN = 0.12            # sortie allocation = cost * (1 + MARGIN) + reserve
RESERVE = {'time': 120.0, 'wh': 5.0, 'o2': 0.3}
TARGET = (21, 21)        # (row, col) far sortie target
WALL = [(18, c) for c in range(8, 22)]   # band across the route; gap at cols 22-23
FALLBACKS = [(17, 20), (16, 18), (15, 16), (14, 14)]
journal = []


def centre(row, col):
    return -64.0 + (col + 0.5) * 4.0, -64.0 + (row + 0.5) * 4.0


HOME = centre(12, 12)


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


rclpy.init()
node = rclpy.create_node('resource_scenario_driver')
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


def human():
    return spin_until(lambda: st['human'][-1] if st['human'] else None, 'human state')


def plan_cost(goal_rc, budget):
    """Read-only planner query from the human's current pose; nothing is published."""
    spin_until(lambda: planner.service_is_ready(), 'planner service')
    h = human()
    m = mission()
    req = PlanRoute.Request()
    req.run_id, req.request_id, req.agent_id = RUN_ID, f'calib-{time.time():.0f}', 'human_1'
    req.agent_kind = h.agent_kind
    req.start = deepcopy(h.pose.position)
    gx, gy = centre(*goal_rc)
    req.goal.x, req.goal.y = gx, gy
    req.return_to.x, req.return_to.y = HOME
    req.require_return = True
    req.mode = 'FAST'
    req.map_version = m['map_version']
    req.time_budget_s, req.energy_budget_wh, req.oxygen_budget_l = budget
    req.reserve_time_s, req.reserve_wh, req.reserve_oxygen_l = RESERVE['time'], RESERVE['wh'], RESERVE['o2']
    fut = planner.call_async(req)
    spin_until(lambda: fut.done(), 'planner answer', 90)
    return fut.result().decision


def observe(obs_id, blocked_cells):
    spin_until(lambda: st['belief'] is not None, 'belief')
    heights = struct.unpack(f'<{ROWS * COLS}f', bytes(st['belief'].data))
    version = mission()['map_version']
    blocked = {r * COLS + c for r, c in blocked_cells}
    msg = TerrainObservation()
    msg.header.frame_id = 'map'
    msg.header.stamp = node.get_clock().now().to_msg()
    msg.observation_id, msg.run_id, msg.agent_id = obs_id, RUN_ID, 'drone_1'
    msg.base_map_version = version
    msg.source_kind = TerrainObservation.SOURCE_SIMULATED
    msg.cell_indices = OBSERVED
    msg.elevation_m = [heights[i] for i in OBSERVED]
    msg.sigma_m = [0.25] * len(OBSERVED)
    msg.obstacle = [TerrainObservation.OBSTACLE_BLOCKED if i in blocked else TerrainObservation.OBSTACLE_FREE
                    for i in OBSERVED]
    pub.publish(msg)
    log(f'drone_1 SIMULATED observation {obs_id} on map v{version}: {len(blocked)} cells blocked')
    return version


def submit(request_id, goal_rc, budget):
    gx, gy = centre(*goal_rc) if goal_rc else HOME
    body = {'request_id': request_id, 'primary_agent_id': 'human_1',
            'base': {'x': HOME[0], 'y': HOME[1]}, 'goal': {'x': gx, 'y': gy}, 'mode': 'FAST',
            'time_budget_s': budget[0], 'energy_budget_wh': budget[1], 'oxygen_budget_l': budget[2],
            'reserve_time_s': RESERVE['time'], 'reserve_wh': RESERVE['wh'], 'reserve_oxygen_l': RESERVE['o2']}
    r = httpx.post(BASE + '/api/mission/goal', json=body, timeout=5).json()
    log(f'goal {request_id} -> {goal_rc or "BASE"} budget O2 {budget[2]:.2f} L, '
        f'energy {budget[1]:.1f} Wh, time {budget[0]:.0f} s: {r.get("reason_code")}')
    m = wait(lambda: (x := mission())['mission_state'] in ('READY', 'BLOCKED') and x, request_id)
    route = m.get('active_route') or {}
    log(f'  mission {m["mission_state"]} {m.get("reason_code", "")} route {m.get("route_id") or "-"} '
        f'est O2 {route.get("oxygen_est_l")} L, time {route.get("travel_time_s")} s')
    return m


def resources(s):
    return s.time_remaining_s, s.energy_remaining_wh, s.oxygen_remaining_l


try:
    wait(lambda: mission()['mission_state'] in ('IDLE', 'READY', 'BLOCKED'), 'mission settled')
    h0 = human()
    spin_until(lambda: st['human'][-1].mode in (AgentState.MODE_IDLE,), 'human idle', 300)
    log(f'human_1 at ({h0.pose.position.x:.1f}, {h0.pose.position.y:.1f}) '
        f'O2 {h0.oxygen_remaining_l:.2f} L, energy {h0.energy_remaining_wh:.1f} Wh')

    d = plan_cost(TARGET, (14400.0, 1000.0, 1000.0))
    if d.status != RouteDecision.STATUS_FEASIBLE:
        raise SystemExit(f'calibration failed: {d.status} {d.reason_code} {d.detail}')
    cost = (d.travel_time_s, d.energy_est_wh, d.oxygen_est_l)
    budget = (cost[0] * (1 + MARGIN) + RESERVE['time'], cost[1] * (1 + MARGIN) + RESERVE['wh'],
              cost[2] * (1 + MARGIN) + RESERVE['o2'])
    log(f'calibration: sortie to {TARGET} costs {cost[0]:.0f} s, {cost[1]:.2f} Wh, {cost[2]:.3f} L O2; '
        f'allocating +{MARGIN:.0%} over cost plus reserve')

    start_res = resources(human())
    m = submit('sortie-far', TARGET, budget)
    if m['mission_state'] != 'READY':
        raise SystemExit('far sortie not authorized')
    out = m['active_route']['outbound_path']
    first = len(st['human'])
    # Let the human spend ~45% of the outbound leg before the drone reports the band.
    leg = sum(math.dist((a['x'], a['y']), (b['x'], b['y'])) for a, b in zip(out, out[1:]))
    spin_until(lambda: any(s.mode == AgentState.MODE_MOVING for s in st['human'][first:]), 'moving')
    walked = lambda: math.dist((st['human'][-1].pose.position.x, st['human'][-1].pose.position.y), HOME)
    spin_until(lambda: walked() > 0.45 * leg, 'human under way', 300)
    observe('obs-wall', WALL)
    halted = spin_until(lambda: next((s for s in st['human'][first:] if s.mode == AgentState.MODE_HALTED), None),
                        'halt acknowledgement')
    used = [a - b for a, b in zip(start_res, resources(halted))]
    log(f'human_1 HALTED at ({halted.pose.position.x:.1f}, {halted.pose.position.y:.1f}); '
        f'consumed {used[0]:.0f} s, {used[1]:.2f} Wh, {used[2]:.3f} L O2')
    m = wait(lambda: (x := mission())['mission_state'] in ('READY', 'BLOCKED')
             and x['map_version'] > halted.header.stamp.sec * 0 and x, 'automatic replan')
    m = wait(lambda: (x := mission())['mission_state'] in ('READY', 'BLOCKED') and x, 'replan settled')
    route = m.get('active_route') or {}
    log(f'automatic replan on map v{m["map_version"]}: {m["mission_state"]} {m.get("reason_code", "")} '
        f'{route.get("status", "")} {route.get("reason_code", "")}')

    if m['mission_state'] == 'BLOCKED':
        left = [max(0.0, b - u) for b, u in zip(budget, used)]
        log(f'remaining allocation: {left[0]:.0f} s, {left[1]:.2f} Wh, {left[2]:.3f} L O2 '
            f'(reserve {RESERVE["o2"]} L)')
        for i, rc in enumerate(FALLBACKS + [None]):
            m = submit(f'fallback-{i + 1}', rc, left)
            if m['mission_state'] == 'READY':
                break
    if m['mission_state'] == 'READY':
        n = len(st['human'])
        spin_until(lambda: any(s.mode == AgentState.MODE_MOVING for s in st['human'][n:]), 'moving', 30)
        spin_until(lambda: st['human'][-1].mode == AgentState.MODE_IDLE
                   and st['human'][-1].velocity.linear.x == 0.0, 'human home', 400)
        end = resources(st['human'][-1])
        log(f'human_1 back at ({st["human"][-1].pose.position.x:.1f}, {st["human"][-1].pose.position.y:.1f}); '
            f'total consumed {start_res[2] - end[2]:.3f} L O2 of {budget[2]:.3f} L allocated '
            f'(reserve {RESERVE["o2"]} L kept: {budget[2] - (start_res[2] - end[2]) >= RESERVE["o2"] - 1e-6})')
    events = get(f'/api/run/{RUN_ID}/events')['events']
    log('events so far:', len(events))
finally:
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, f'{RUN_ID}-resource-scenario.json'), 'w') as f:
        json.dump({'run_id': RUN_ID, 'source_mode': 'MOCK', 'observations': 'SIMULATED',
                   'note': 'Illustrative budgets; not EVA limits or a validated mission.',
                   'journal': journal}, f, indent=1)
    node.destroy_node()
    rclpy.shutdown()
