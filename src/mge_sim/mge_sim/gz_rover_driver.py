"""Drive a physical rover in Gazebo along the authorized route and publish its AgentState.

Replaces the kinematic executor for one agent (launch it with `external_agents:=<id>`).
The route authorization is the executor's: the primary agent's active path must match the
MissionState route (`mge_sim.executor.KinematicExecutor.authorized`). The rover is steered
by pure pursuit through the gz DiffDrive plugin (`/model/<id>/cmd_vel`); its pose is the
model's ground-truth odometry (`/model/<id>/odometry_gt`), so it moves only as the physics
lets it: heightmap contact, Mars gravity, wheel friction and the rocks' collisions.

Stop acknowledgement keeps the ICD semantics: when the route changes or clears the rover
brakes, and once it is at rest it reports HALTED (route interrupted) or IDLE (end reached)
with exactly zero velocity and its rest pose frozen, so a re-plan starts from a stable pose.
Height: the Gazebo ground is built on the planner's cell centres (gz_world), but the rover's
reference point settles a few centimetres off it (wheel-ground contact penetration and the
heightfield's collision thickness). That constant vertical datum offset is measured ONCE, at
rest after spawning, against the public map height at the rover's XY, logged, and applied to
every reported z. After that the reported z is the physics z: it follows the Gazebo terrain
and is never replaced by the map. An offset above MAX_DATUM_OFFSET_M is refused (bad world).
Energy is debited per metre actually driven at the route's own estimate (energy/length);
time is debited as it passes while moving. Illustrative MOCK accounting, not a power model.
"""
import json
import math
import threading

import rclpy
from rclpy.node import Node

from mge_interfaces.msg import AgentState, MissionState
from nav_msgs.msg import Path
from mge_sim.common import LATCHED, RELIABLE, TOPIC_ACTIVE_PATH, TOPIC_MISSION_STATE, agent_state_topic
from mge_sim.mock_agents import load_agents

LOOKAHEAD_M = 1.2
ARRIVE_M = 0.6
TURN_IN_PLACE_RAD = 0.6
MAX_YAW_RATE = 0.5
REST_SPEED_M_S = 0.03
MAX_DATUM_OFFSET_M = 0.3


def map_height(prior, origin, res, x, y):
    """Bilinear height of a cell-centre grid (row 0 = south) at ENU (x, y), clamped at the edges."""
    rows, cols = len(prior), len(prior[0])
    fx = min(max((x - origin[0]) / res - 0.5, 0.0), cols - 1.0)
    fy = min(max((y - origin[1]) / res - 0.5, 0.0), rows - 1.0)
    c0, r0 = min(int(fx), cols - 2), min(int(fy), rows - 2)
    tx, ty = fx - c0, fy - r0
    return ((prior[r0][c0] * (1 - tx) + prior[r0][c0 + 1] * tx) * (1 - ty)
            + (prior[r0 + 1][c0] * (1 - tx) + prior[r0 + 1][c0 + 1] * tx) * ty)


def datum_offset(map_z, physics_z):
    """Constant vertical offset between the map and the settled physics height, or None."""
    offset = map_z - physics_z
    return offset if abs(offset) <= MAX_DATUM_OFFSET_M else None


def yaw_of(q):
    return math.atan2(2 * (q[3] * q[2] + q[0] * q[1]), 1 - 2 * (q[1] ** 2 + q[2] ** 2))


def pursuit(pose_xy, yaw, points, index, speed):
    """(v, w, new_index, done) for pure pursuit through `points` (x, y) from `index`."""
    x, y = pose_xy
    while index < len(points) - 1 and math.dist((x, y), points[index]) < LOOKAHEAD_M:
        index += 1
    tx, ty = points[index]
    if index == len(points) - 1 and math.dist((x, y), (tx, ty)) < ARRIVE_M:
        return 0.0, 0.0, index, True
    err = math.atan2(ty - y, tx - x) - yaw
    err = math.atan2(math.sin(err), math.cos(err))
    w = max(-MAX_YAW_RATE, min(MAX_YAW_RATE, 1.5 * err))
    v = 0.0 if abs(err) > TURN_IN_PLACE_RAD else speed * math.cos(err)
    return v, w, index, False


class GzRoverDriver(Node):

    def __init__(self):
        super().__init__('gz_rover_driver')
        self.run_id = self.declare_parameter('run_id', 'mock-run').value
        self.agent_id = self.declare_parameter('agent_id', 'rover_1').value
        world_json = self.declare_parameter('world_json', '').value
        agents_file = self.declare_parameter('agents_file', '').value
        self.speed = float(self.declare_parameter('speed_m_s', 0.65).value)
        with open(world_json, encoding='utf-8') as f:
            world = json.load(f)
        self.z_ref = world['z_ref_m']
        from mge_data.core import default_manifest_path, load_public_terrain
        tile = load_public_terrain(default_manifest_path())
        prior = tile.prior.astype(float)
        prior[tile.nodata_mask] = float(prior[~tile.nodata_mask].min())
        self.prior = prior.tolist()
        self.origin = (world['origin_x_m'], world['origin_y_m'])
        self.res = world['resolution_m']
        self.offset = None          # vertical datum offset, measured once at rest
        spec = next(a for a in load_agents(agents_file) if a['id'] == self.agent_id)
        self.kind = spec['kind']
        self.time_s, self.energy_wh = float(spec['time_budget_s']), float(spec['energy_budget_wh'])
        self.mode = 'IDLE'
        self.mission, self.path = None, []
        self.follow = None          # (route_id, points, energy per metre, index)
        self.finished = set()
        self.stopping_to = None     # mode to report once at rest
        self.rest = None            # frozen (x, y, z, yaw) reported while not moving
        self.odom = None            # latest (x, y, z, yaw, speed) from Gazebo
        self.lock = threading.Lock()
        self.last_xy = None
        self.last_t = None
        from gz.msgs10.odometry_pb2 import Odometry
        from gz.msgs10.twist_pb2 import Twist
        from gz.transport13 import Node as GzNode
        self.Twist = Twist
        self.gz = GzNode()
        self.cmd = self.gz.advertise(f'/model/{self.agent_id}/cmd_vel', Twist)
        self.gz.subscribe(Odometry, f'/model/{self.agent_id}/odometry_gt', self.on_odom)
        self.pub = self.create_publisher(AgentState, agent_state_topic(self.agent_id), RELIABLE)
        self.create_subscription(MissionState, TOPIC_MISSION_STATE, self.on_mission, LATCHED)
        self.create_subscription(Path, TOPIC_ACTIVE_PATH, self.on_path, LATCHED)
        self.create_timer(0.1, self.tick)
        self.get_logger().warn(f'Gazebo-driven {self.agent_id}: physics pose, pure pursuit, MOCK resource accounting')

    def on_odom(self, msg):
        p, q, t = msg.pose.position, msg.pose.orientation, msg.twist.linear
        with self.lock:
            self.odom = (p.x, p.y, p.z, yaw_of((q.x, q.y, q.z, q.w)), math.hypot(t.x, t.y))

    def on_mission(self, msg):
        if msg.run_id == self.run_id:
            self.mission = msg

    def on_path(self, msg):
        if msg.header.frame_id in ('', 'map'):
            self.path = [(p.pose.position.x, p.pose.position.y, p.pose.position.z) for p in msg.poses]

    def authorized(self):
        m = self.mission
        if m is None or not m.route_id or not self.path or m.active_route.route_id != m.route_id:
            return None
        if m.primary_agent_id != self.agent_id:
            return None
        xyz = lambda p: (p.x, p.y, p.z)  # noqa: E731
        outbound = [xyz(p) for p in m.active_route.outbound_path]
        back = [xyz(p) for p in m.active_route.return_path]
        if self.path not in (outbound, outbound + back[1:], outbound + back):
            return None
        length = sum(math.dist(a[:2], b[:2]) for a, b in zip(self.path, self.path[1:])) or 1.0
        energy = m.active_route.energy_est_wh
        return m.route_id, [p[:2] for p in self.path], (energy / length if math.isfinite(energy) else 0.0)

    def drive(self, v, w):
        msg = self.Twist()
        msg.linear.x, msg.angular.z = float(v), float(w)
        self.cmd.publish(msg)

    def tick(self):
        with self.lock:
            odom = self.odom
        if odom is None:
            return
        x, y, z, yaw, speed = odom
        now = self.get_clock().now()
        current = self.authorized()
        if self.follow is not None and (current is None or current[0] != self.follow[0]):
            self.stopping_to, self.follow = 'HALTED', None          # route interrupted: brake
        if self.follow is None and self.stopping_to is None and current is not None and current[0] not in self.finished:
            self.finished.add(current[0])
            self.follow = [current[0], current[1], current[2], 0]
            self.mode, self.rest = 'MOVING', None
            self.get_logger().info(f'{self.agent_id} driving route {current[0]}')
        if self.follow is not None:
            v, w, self.follow[3], done = pursuit((x, y), yaw, self.follow[1], self.follow[3], self.speed)
            if done:
                self.stopping_to, self.follow = 'IDLE', None
            else:
                self.drive(v, w)
        if self.stopping_to is not None:
            self.drive(0.0, 0.0)
            if speed < REST_SPEED_M_S:
                self.mode, self.rest, self.stopping_to = self.stopping_to, (x, y, z, yaw), None
                self.get_logger().info(f'{self.agent_id} {self.mode} at ({x:.2f}, {y:.2f})')
        # Resources: time while moving, energy per metre actually driven.
        if self.last_xy is not None and self.mode == 'MOVING':
            dt = (now - self.last_t).nanoseconds * 1e-9
            self.time_s = max(0.0, self.time_s - dt)
            rate = self.follow[2] if self.follow is not None else 0.0
            self.energy_wh = max(0.0, self.energy_wh - rate * math.dist(self.last_xy, (x, y)))
        if self.mode != 'MOVING' and self.rest is None and speed < REST_SPEED_M_S:
            if self.offset is None:
                self.offset = datum_offset(map_height(self.prior, self.origin, self.res, x, y), z + self.z_ref)
                if self.offset is None:
                    self.get_logger().error('rover rests too far from the map height; check the Gazebo world')
                    return
                self.get_logger().info(f'vertical datum offset measured at rest: {self.offset:+.4f} m')
            self.rest = (x, y, z, yaw)          # settled after spawning: report a stable pose
        self.last_xy, self.last_t = (x, y), now
        self.publish(now, (x, y, z, yaw, speed))

    def publish(self, now, odom):
        if self.mode == 'MOVING' or self.rest is None:
            x, y, z, yaw, speed = odom
        else:                                   # at rest: frozen pose, exactly zero velocity
            (x, y, z, yaw), speed = self.rest, 0.0
        msg = AgentState()
        msg.header.stamp = now.to_msg()
        msg.header.frame_id = 'map'
        msg.run_id, msg.agent_id, msg.agent_kind = self.run_id, self.agent_id, self.kind
        msg.pose.position.x, msg.pose.position.y = x, y
        msg.pose.position.z = z + self.z_ref + (self.offset or 0.0)
        msg.pose.orientation.z, msg.pose.orientation.w = math.sin(yaw / 2), math.cos(yaw / 2)
        if self.mode == 'MOVING':
            msg.velocity.linear.x, msg.velocity.linear.y = speed * math.cos(yaw), speed * math.sin(yaw)
        msg.mode = self.mode
        msg.time_remaining_s, msg.energy_remaining_wh, msg.oxygen_remaining_l = self.time_s, self.energy_wh, math.nan
        msg.confidence = 1.0
        self.pub.publish(msg)


def main():
    rclpy.init()
    try:
        rclpy.spin(GzRoverDriver())
    except KeyboardInterrupt:
        pass


if __name__ == '__main__':
    main()
