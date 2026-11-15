"""ROS node that records a run into a replay package (see mge_gateway.replay).

Besides mission state, events and terrain metadata, it records the public
raster layers: the immutable prior and, per map version, the belief, sigma and
observed mask of the batch published under that version's stamp
(mge_gateway.public_rasters). Only public topics are subscribed.
"""
import signal
import struct
import sys
import threading

import rclpy
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, QoSProfile, ReliabilityPolicy
from rclpy.signals import SignalHandlerOptions
from nav_msgs.msg import OccupancyGrid
from sensor_msgs.msg import Image

from mge_gateway.public_rasters import PublicRasterAssembler, RasterInputError
from mge_gateway.replay import ReplayWriter
from mge_gateway.ros_bridge import LATCHED, msg_json, RELIABLE
from mge_gateway.store import NonFiniteValue
from mge_interfaces.msg import MissionEvent, MissionState, TerrainMeta

# Latched like the publishers, but deep enough that two map versions published
# in quick succession are both delivered before the batch is repeated.
LAYER_QOS = QoSProfile(depth=10, reliability=ReliabilityPolicy.RELIABLE,
                       durability=DurabilityPolicy.TRANSIENT_LOCAL)
ENCODINGS = {'prior': '32FC1', 'belief': '32FC1', 'sigma': '32FC1', 'observed': 'mono8'}


def image_values(name, msg):
    """Row-major cell values of a public layer, checked against its encoding."""
    rows, cols, data = msg.height, msg.width, bytes(msg.data)
    if msg.encoding != ENCODINGS[name]:
        raise RasterInputError(f'{name}: encoding {msg.encoding!r}, expected {ENCODINGS[name]}')
    if ENCODINGS[name] == 'mono8':
        if msg.step != cols or len(data) != rows * cols:
            raise RasterInputError(f'{name}: {len(data)} bytes for {rows} x {cols} mono8')
        return rows, cols, list(data)
    if msg.is_bigendian or msg.step != cols * 4 or len(data) != rows * cols * 4:
        raise RasterInputError(f'{name}: not a little-endian {rows} x {cols} 32FC1 image')
    return rows, cols, list(struct.unpack(f'<{rows * cols}f', data))


def header_json(msg):
    return {'frame_id': msg.header.frame_id,
            'stamp': {'sec': msg.header.stamp.sec, 'nanosec': msg.header.stamp.nanosec}}


class ReplayRecorder(Node):

    def __init__(self):
        super().__init__('replay_recorder')
        run_id = self.declare_parameter('run_id', 'mock-run').value
        root = self.declare_parameter('record_dir', 'evidence').value
        sim_time = self.get_parameter('use_sim_time').value
        source_mode = self.declare_parameter('source_mode', 'UNKNOWN').value
        self.writer = ReplayWriter(
            root, run_id, 'sim' if sim_time else 'system', source_mode)
        self.rasters = PublicRasterAssembler(run_id)
        self.create_subscription(
            MissionState, '/mge/mission/state',
            lambda m: self.record('state', m), LATCHED)
        self.create_subscription(
            MissionEvent, '/mge/mission/events',
            lambda m: self.record('event', m), RELIABLE)
        self.create_subscription(
            TerrainMeta, '/mge/terrain/meta', self.on_meta, LAYER_QOS)
        for name in ENCODINGS:
            self.create_subscription(
                Image, f'/mge/terrain/{name}',
                lambda m, name=name: self.on_layer(name, m), LAYER_QOS)
        # Optional obstacle layer: the human traversability mask of each batch.
        self.create_subscription(
            OccupancyGrid, '/mge/terrain/traversability/human', self.on_traversability, LAYER_QOS)
        self.get_logger().info(f'recording run {run_id} to {self.writer.dir}')

    def record(self, kind, msg):
        """An invalid message is left out of the package and reported."""
        try:
            payload = msg_json(kind, msg)
        except NonFiniteValue as e:
            self.get_logger().error(f'not recorded, {kind} message: {e}')
            return None
        self.writer.record(kind, payload)
        return payload

    def on_meta(self, msg):
        payload = self.record('terrain_meta', msg)
        if payload is not None:
            self.update_rasters(self.rasters.on_meta, payload)

    def on_layer(self, name, msg):
        if msg.header.frame_id != 'map':
            self.get_logger().error(f'not recorded, {name} layer in frame {msg.header.frame_id!r}')
            return
        try:
            rows, cols, values = image_values(name, msg)
        except RasterInputError as e:
            self.get_logger().error(f'not recorded, {e}')
            return
        if name == 'prior':
            self.update_rasters(self.rasters.on_prior, rows, cols, values)
        else:
            self.update_rasters(self.rasters.on_layer, name, header_json(msg), rows, cols, values)

    def on_traversability(self, msg):
        if msg.header.frame_id != 'map':
            self.get_logger().error(f'not recorded, traversability in frame {msg.header.frame_id!r}')
            return
        rows, cols = msg.info.height, msg.info.width
        self.update_rasters(self.rasters.on_impassable, header_json(msg), rows, cols, list(msg.data))

    def update_rasters(self, method, *args):
        """A rejected layer is reported and left out; nothing is filled in."""
        try:
            changed = method(*args)
        except RasterInputError as e:
            self.get_logger().error(f'public raster not recorded: {e}')
            return
        if changed:
            self.writer.write_public_rasters(self.rasters.attachment())


def main():
    # A signal only asks the loop to stop. The default handling raised
    # KeyboardInterrupt inside a callback, so a record cut between its timeline
    # line and the manifest/snapshot rewrite left the package inconsistent
    # (timeline one record ahead of record_count and event_count).
    rclpy.init(signal_handler_options=SignalHandlerOptions.NO)
    stop = threading.Event()
    for signum in (signal.SIGINT, signal.SIGTERM):
        signal.signal(signum, lambda *_: stop.set())
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
        while rclpy.ok() and not stop.is_set():
            rclpy.spin_once(node, timeout_sec=0.1)
    finally:
        node.writer.close()
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == '__main__':
    main()
