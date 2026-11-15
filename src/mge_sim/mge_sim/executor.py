"""MOCK kinematic executor: agents follow the authorized active path.

Replaces `mock_agents` (one publisher per agent state topic). Every agent of
the YAML file is published at `rate_hz`; the mission's primary agent follows
`/mge/planner/active_path` once that path is associated with the authorized
route of the current MissionState (same route ID, path equal to the route's
outbound points, optionally followed by its return points) and begins exactly
at the agent's pose. Motion and consumption come from mge_sim.kinematics.

Stop acknowledgement uses the existing AgentState fields (docs/ICD.md, section
7): when the route ID changes or clears, or the path empties or changes, the
agent halts where it is and keeps publishing mode HALTED with zero velocity at
the current clock. Consumers confirm the stop from that state, not from the
empty path. A halted agent starts again only on a new authorized route.
"""
import math

import rclpy
from rclpy.node import Node

from mge_interfaces.msg import AgentState, MissionState
from nav_msgs.msg import Path
from mge_sim.common import (
    agent_state_topic, LATCHED, RELIABLE, TOPIC_ACTIVE_PATH, TOPIC_MISSION_STATE)
from mge_sim.kinematics import ExecutionRefused, HALTED, IDLE, MOVING, PathFollower, route_rates
from mge_sim.mock_agents import load_agents


def xyz(point):
    return (float(point.x), float(point.y), float(point.z))


class KinematicExecutor(Node):

    def __init__(self):
        super().__init__('kinematic_executor')
        self.run_id = self.declare_parameter('run_id', 'mock-run').value
        agents_file = self.declare_parameter('agents_file', '').value
        rate_hz = float(self.declare_parameter('rate_hz', 10.0).value)
        # Agents driven and published by another node (e.g. a physical rover in Gazebo):
        # comma-separated IDs. Keeps exactly one publisher per agent state topic.
        external = {i.strip() for i in str(self.declare_parameter('external_agents', '').value).split(',') if i.strip()}
        self.agents = {}
        for a in load_agents(agents_file):
            if a['id'] in external:
                continue
            self.agents[a['id']] = {
                'kind': a['kind'],
                'position': (float(a['x_m']), float(a['y_m']), float(a['z_m'])),
                'time_s': float(a['time_budget_s']),
                'energy_wh': float(a['energy_budget_wh']),
                'oxygen_l': float(a.get('oxygen_budget_l', math.nan)),
                'mode': IDLE,
            }
        self.pubs = {i: self.create_publisher(AgentState, agent_state_topic(i), RELIABLE)
                     for i in self.agents}
        self.mission = None
        self.path = []
        self.follow = None          # (agent_id, route_id, PathFollower)
        self.finished = set()       # route IDs already executed or refused
        self.last = None
        self.create_subscription(MissionState, TOPIC_MISSION_STATE, self.on_mission, LATCHED)
        self.create_subscription(Path, TOPIC_ACTIVE_PATH, self.on_path, LATCHED)
        self.create_timer(1.0 / rate_hz, self.tick)
        self.get_logger().warn(
            f'MOCK kinematic executor for {len(self.agents)} agents (run_id={self.run_id}): '
            'constant speed and linear consumption from the route estimates')

    # ---- inputs -----------------------------------------------------------
    def on_mission(self, msg):
        if msg.run_id == self.run_id:
            self.mission = msg
            self.reconcile()

    def on_path(self, msg):
        if msg.header.frame_id in ('', 'map'):
            self.path = [xyz(p.pose.position) for p in msg.poses]
            self.reconcile()

    def authorized(self):
        """(agent_id, route_id, points, route) when path and state agree."""
        m = self.mission
        if m is None or not m.route_id or not self.path or m.active_route.route_id != m.route_id:
            return None
        outbound = [xyz(p) for p in m.active_route.outbound_path]
        back = [xyz(p) for p in m.active_route.return_path]
        if self.path not in (outbound, outbound + back[1:], outbound + back):
            return None
        return m.primary_agent_id, m.route_id, self.path, m.active_route

    def reconcile(self):
        current = self.authorized()
        if self.follow is not None:
            agent_id, route_id, follower = self.follow
            if current is None or current[1] != route_id or current[2] != follower.points:
                self.halt(agent_id, follower)
        if self.follow is not None or current is None:
            return
        agent_id, route_id, points, route = current
        if route_id in self.finished or agent_id not in self.agents:
            return
        self.finished.add(route_id)
        agent = self.agents[agent_id]
        try:
            rates = route_rates([xyz(p) for p in route.outbound_path],
                                [xyz(p) for p in route.return_path],
                                route.travel_time_s, route.energy_est_wh, route.oxygen_est_l)
            follower = PathFollower(points, rates, agent['position'])
        except ExecutionRefused as e:
            # Rejection is a stop, never a vertical correction or a resource debit.
            agent['mode'] = HALTED
            self.get_logger().error(f'route {route_id} not executed: {e}')
            return
        self.follow = (agent_id, route_id, follower)
        agent['mode'] = MOVING
        self.get_logger().info(f'{agent_id} executing route {route_id}')

    def halt(self, agent_id, follower):
        follower.stop()
        self.agents[agent_id]['mode'] = HALTED if follower.state == HALTED else IDLE
        self.follow = None
        self.get_logger().info(f'{agent_id} halted at {self.agents[agent_id]["position"]}')

    # ---- motion and output ------------------------------------------------
    def tick(self):
        now = self.get_clock().now()
        dt = 0.0 if self.last is None else (now - self.last).nanoseconds * 1e-9
        self.last = now
        velocity = (0.0, 0.0, 0.0)
        if self.follow is not None and dt > 0:
            agent_id, _, follower = self.follow
            agent = self.agents[agent_id]
            moved_s = follower.advance(dt)
            agent['position'] = follower.position
            agent['time_s'] = max(0.0, agent['time_s'] - moved_s)
            agent['energy_wh'] = max(0.0, agent['energy_wh'] - moved_s * follower.rates.energy_wh_s)
            if not math.isnan(agent['oxygen_l']):
                agent['oxygen_l'] = max(0.0, agent['oxygen_l'] - moved_s * follower.rates.oxygen_l_s)
            velocity = tuple(c * follower.rates.speed_m_s for c in follower.direction())
            if follower.state != MOVING:            # arrived at the end of the path
                agent['mode'] = IDLE
                self.follow = None
        self.publish(now, velocity)

    def publish(self, now, velocity):
        stamp = now.to_msg()
        moving = self.follow[0] if self.follow is not None else None
        for agent_id, a in self.agents.items():
            msg = AgentState()
            msg.header.stamp = stamp
            msg.header.frame_id = 'map'
            msg.run_id = self.run_id
            msg.agent_id = agent_id
            msg.agent_kind = a['kind']
            msg.pose.position.x, msg.pose.position.y, msg.pose.position.z = a['position']
            msg.pose.orientation.w = 1.0
            if agent_id == moving:
                msg.velocity.linear.x, msg.velocity.linear.y, msg.velocity.linear.z = velocity
            msg.mode = a['mode']
            msg.time_remaining_s = a['time_s']
            msg.energy_remaining_wh = a['energy_wh']
            msg.oxygen_remaining_l = a['oxygen_l']
            msg.confidence = 1.0
            self.pubs[agent_id].publish(msg)


def main():
    rclpy.init()
    try:
        rclpy.spin(KinematicExecutor())
    except KeyboardInterrupt:
        pass


if __name__ == '__main__':
    main()
