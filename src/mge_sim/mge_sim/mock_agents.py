"""MOCK agent state publisher.

Publishes a static AgentState for every agent listed in a YAML file so that
the ROS graph and its consumers can be exercised before the real simulation
adapter exists. Poses do not move and resources do not deplete: nothing
published here is evidence of locomotion, consumption or perception.
"""
import math

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy
import yaml

from mge_interfaces.msg import AgentState

KINDS = {AgentState.KIND_HUMAN, AgentState.KIND_DRONE, AgentState.KIND_ROVER}


def load_agents(path):
    with open(path, encoding='utf-8') as f:
        agents = yaml.safe_load(f)['agents']
    ids = [a['id'] for a in agents]
    if len(ids) != len(set(ids)):
        raise ValueError(f'duplicate agent ids in {path}: {ids}')
    for a in agents:
        if a['kind'] not in KINDS:
            raise ValueError(f"agent {a['id']}: unknown kind {a['kind']}")
    return agents


class MockAgents(Node):

    def __init__(self):
        super().__init__('mock_agents')
        self.run_id = self.declare_parameter('run_id', 'mock-run').value
        agents_file = self.declare_parameter('agents_file', '').value
        rate_hz = self.declare_parameter('rate_hz', 1.0).value
        self.agents = load_agents(agents_file)

        qos = QoSProfile(depth=10, reliability=ReliabilityPolicy.RELIABLE)
        self.pubs = {
            a['id']: self.create_publisher(AgentState, f"/mge/agents/{a['id']}/state", qos)
            for a in self.agents
        }
        self.create_timer(1.0 / rate_hz, self.publish)
        self.get_logger().warn(
            f'MOCK data: publishing static state for {len(self.agents)} agents '
            f'(run_id={self.run_id})')

    def publish(self):
        stamp = self.get_clock().now().to_msg()
        for a in self.agents:
            msg = AgentState()
            msg.header.stamp = stamp
            msg.header.frame_id = 'map'
            msg.run_id = self.run_id
            msg.agent_id = a['id']
            msg.agent_kind = a['kind']
            msg.pose.position.x = float(a['x_m'])
            msg.pose.position.y = float(a['y_m'])
            msg.pose.position.z = float(a.get('z_m', 0.0))
            msg.pose.orientation.w = 1.0
            msg.mode = AgentState.MODE_IDLE
            msg.time_remaining_s = float(a['time_budget_s'])
            msg.energy_remaining_wh = float(a['energy_budget_wh'])
            msg.oxygen_remaining_l = float(a.get('oxygen_budget_l', math.nan))
            msg.confidence = 1.0
            self.pubs[a['id']].publish(msg)


def main():
    rclpy.init()
    try:
        rclpy.spin(MockAgents())
    except KeyboardInterrupt:
        pass


if __name__ == '__main__':
    main()
