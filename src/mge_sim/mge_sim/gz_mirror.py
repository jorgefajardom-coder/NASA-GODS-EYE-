"""Mirror the agents' ROS poses into a Gazebo world built by `mge_sim.gz_world`.

Follows /mge/agents/<id>/state and moves the matching visual-only model with the world's
`set_pose` service (gz-transport). It never feeds anything back to ROS: Gazebo shows the
run; it does not drive it. The models have no collision, so this is a view of the
kinematic MOCK execution, not a physics simulation of the agents.

Cosmetic animation like the web viewer's: a drone's rotors (world.json `rotors`) spin up
while its mode is not IDLE or it is drawn more than 0.3 m above the ground (world.json
`ground_z_m`), and spin down otherwise, at the web's rates, through the rotor joints'
velocity commands (gz.msgs.Double on /model/<id>/joint/<rotor>_joint/cmd_vel). A rotor that
is still and stays still gets no command. The animation logic is mge_sim.rotors (pure
Python): this node does not import the world generator, numpy or scipy.
"""
import json
import time

import rclpy
from rclpy.node import Node

from mge_interfaces.msg import AgentState
from mge_sim.common import RELIABLE, agent_state_topic
from mge_sim.gz_control import gz_pose
from mge_sim.rotors import is_airborne, rotor_command, should_publish

ROTOR_PERIOD_S = 0.1


class GzMirror(Node):

    def __init__(self):
        super().__init__('gz_mirror')
        self.run_id = self.declare_parameter('run_id', 'mock-run').value
        world_json = self.declare_parameter('world_json', '').value
        self.min_period_s = float(self.declare_parameter('min_period_s', 0.1).value)
        with open(world_json, encoding='utf-8') as f:
            self.meta = json.load(f)
        from gz.msgs10.boolean_pb2 import Boolean
        from gz.msgs10.double_pb2 import Double
        from gz.msgs10.pose_pb2 import Pose
        from gz.transport13 import Node as GzNode
        self.Pose, self.Boolean, self.Double = Pose, Boolean, Double
        self.gz = GzNode()
        self.service = f'/world/{self.meta["world_name"]}/set_pose'
        self.last = {}
        self.modes = {}
        self.airborne = {}      # agent id -> drawn above the ground (like the web viewer)
        self.rotors = {}        # agent id -> (speed share 0..1, [(publisher, direction, max rad/s)])
        for agent_id, info in self.meta['agents'].items():
            if info.get('physical'):
                continue        # driven by physics (gz_rover_driver), never teleported
            self.create_subscription(AgentState, agent_state_topic(agent_id), self.on_state, RELIABLE)
            if info.get('rotors'):
                self.rotors[agent_id] = [0.0, [(self.gz.advertise(r['topic'], Double), r['direction'], r['max_rad_s'])
                                               for r in info['rotors']]]
        if self.rotors:
            self.last_tick = time.monotonic()
            self.create_timer(ROTOR_PERIOD_S, self.spin_rotors)
        self.get_logger().info(f'mirroring {sorted(self.meta["agents"])} into {self.service}'
                               + (f'; rotors of {sorted(self.rotors)}' if self.rotors else ''))

    def on_state(self, msg):
        if (msg.run_id != self.run_id or msg.agent_id not in self.meta['agents']
                or self.meta['agents'][msg.agent_id].get('physical')):
            return
        self.modes[msg.agent_id] = msg.mode
        now = time.monotonic()
        pose = gz_pose(msg, self.meta)
        self.airborne[msg.agent_id] = is_airborne(self.meta, pose[:3])
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

    def spin_rotors(self):
        now = time.monotonic()
        dt, self.last_tick = now - self.last_tick, now
        for agent_id, entry in self.rotors.items():
            # Unknown mode (no state yet) counts as IDLE on the ground: the rotors stay still.
            previous = entry[0]
            entry[0] = rotor_command(previous, self.modes.get(agent_id, 'IDLE'), dt,
                                     airborne=self.airborne.get(agent_id, False))
            if not should_publish(previous, entry[0]):
                continue
            for pub, direction, max_rad_s in entry[1]:
                cmd = self.Double()
                cmd.data = direction * max_rad_s * entry[0]
                pub.publish(cmd)


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
