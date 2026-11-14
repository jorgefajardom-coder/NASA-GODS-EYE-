"""ROS node that records a run into a replay package (see mge_gateway.replay)."""
import sys

import rclpy
from rclpy.node import Node

from mge_gateway.replay import ReplayWriter
from mge_gateway.ros_bridge import LATCHED, msg_json, RELIABLE
from mge_gateway.store import NonFiniteValue
from mge_interfaces.msg import MissionEvent, MissionState, TerrainMeta


class ReplayRecorder(Node):

    def __init__(self):
        super().__init__('replay_recorder')
        run_id = self.declare_parameter('run_id', 'mock-run').value
        root = self.declare_parameter('record_dir', 'evidence').value
        sim_time = self.get_parameter('use_sim_time').value
        source_mode = self.declare_parameter('source_mode', 'UNKNOWN').value
        self.writer = ReplayWriter(
            root, run_id, 'sim' if sim_time else 'system', source_mode)
        self.create_subscription(
            MissionState, '/mge/mission/state',
            lambda m: self.record('state', m), LATCHED)
        self.create_subscription(
            MissionEvent, '/mge/mission/events',
            lambda m: self.record('event', m), RELIABLE)
        self.create_subscription(
            TerrainMeta, '/mge/terrain/meta',
            lambda m: self.record('terrain_meta', m), LATCHED)
        self.get_logger().info(f'recording run {run_id} to {self.writer.dir}')

    def record(self, kind, msg):
        """An invalid message is left out of the package and reported."""
        try:
            self.writer.record(kind, msg_json(kind, msg))
        except NonFiniteValue as e:
            self.get_logger().error(f'not recorded, {kind} message: {e}')


def main():
    rclpy.init()
    try:
        node = ReplayRecorder()
    except FileExistsError as e:
        print(f'replay_recorder: {e.filename} already exists; a recorded run is never '
              'overwritten. Use another run_id or record_dir.', file=sys.stderr)
        sys.exit(1)
    except ValueError as e:
        print(f'replay_recorder: {e}', file=sys.stderr)
        sys.exit(1)
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.writer.close()


if __name__ == '__main__':
    main()
