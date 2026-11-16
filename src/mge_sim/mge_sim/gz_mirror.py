"""Mirror the agents' ROS poses into a Gazebo world built by `mge_sim.gz_world`.

Follows /mge/agents/<id>/state and moves the matching visual-only model with the world's
`set_pose` service (gz-transport). It never feeds anything back to ROS: Gazebo shows the
run; it does not drive it. The models have no collision, so this is a view of the
kinematic MOCK execution, not a physics simulation of the agents.
"""
import json
import time

import rclpy
from rclpy.node import Node

from mge_interfaces.msg import AgentState
from mge_sim.common import RELIABLE, agent_state_topic
from mge_sim.gz_control import gz_pose


class GzMirror(Node):

    def __init__(self):
        super().__init__('gz_mirror')
        self.run_id = self.declare_parameter('run_id', 'mock-run').value
        world_json = self.declare_parameter('world_json', '').value
        self.min_period_s = float(self.declare_parameter('min_period_s', 0.1).value)
        with open(world_json, encoding='utf-8') as f:
            self.meta = json.load(f)
        from gz.msgs10.boolean_pb2 import Boolean
        from gz.msgs10.pose_pb2 import Pose
        from gz.transport13 import Node as GzNode
        self.Pose, self.Boolean = Pose, Boolean
        self.gz = GzNode()
        self.service = f'/world/{self.meta["world_name"]}/set_pose'
        self.last = {}
        for agent_id, info in self.meta['agents'].items():
            if info.get('physical'):
                continue        # driven by physics (gz_rover_driver), never teleported
            self.create_subscription(AgentState, agent_state_topic(agent_id), self.on_state, RELIABLE)
        self.get_logger().info(f'mirroring {sorted(self.meta["agents"])} into {self.service}')

    def on_state(self, msg):
        if (msg.run_id != self.run_id or msg.agent_id not in self.meta['agents']
                or self.meta['agents'][msg.agent_id].get('physical')):
            return
        now = time.monotonic()
        pose = gz_pose(msg, self.meta)
        previous = self.last.get(msg.agent_id)
        if previous and (now - previous[0] < self.min_period_s or previous[1] == pose):
            return
        req = self.Pose()
        req.name = msg.agent_id
        req.position.x, req.position.y, req.position.z = pose[:3]
        req.orientation.x, req.orientation.y, req.orientation.z, req.orientation.w = pose[3:]
        ok, _ = self.gz.request(self.service, req, self.Pose, self.Boolean, 500)
        if ok:
            self.last[msg.agent_id] = (now, pose)


def main():
    rclpy.init()
    node = None
    try:
        node = GzMirror()
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        if node is not None:
            node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
