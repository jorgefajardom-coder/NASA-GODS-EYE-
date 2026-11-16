"""SIMULATED on-board sensor node: agents report the declared test scene around them.

Reads a SIMULATED scene file (blocked cells; truth heights are the public prior
of the run's dataset), follows the configured agents' states and publishes
TerrainObservation messages on /mge/observations with source SIMULATED, using
the reporting policy of `mge_sim.scene_sensing`: hazards are reported as soon
as a moving agent sees them, plain coverage only while it is stopped. It never
uses evaluator reference data and never claims a measurement.
"""
import math
import struct
import uuid

import rclpy
from rclpy.node import Node
from nav_msgs.msg import OccupancyGrid
from sensor_msgs.msg import Image

from mge_data.core import default_manifest_path, load_public_terrain
from mge_interfaces.msg import AgentState, TerrainMeta, TerrainObservation
from mge_sim.common import LATCHED, RELIABLE, TOPIC_OBSERVATIONS, TOPIC_TERRAIN_META, agent_state_topic
from mge_sim.scene_sensing import (
    FeedbackBatches, FreshTelemetry, SensorLedger, footprint, observation_values,
    scene_from_file, stamp_ns,
)


class SceneSensor(Node):

    def __init__(self):
        super().__init__('scene_sensor')
        self.run_id = self.declare_parameter('run_id', 'mock-run').value
        self.scene_file = self.declare_parameter('scene_file', '').value
        manifest = self.declare_parameter('manifest_path', str(default_manifest_path())).value
        ids = list(self.declare_parameter('agent_ids', ['drone_1', 'human_1', 'rover_1']).value)
        radii = [float(r) for r in self.declare_parameter('radii_m', [24.0, 8.0, 12.0]).value]
        self.period_s = float(self.declare_parameter('period_s', 1.0).value)
        self.sigma_m = float(self.declare_parameter('sigma_m', 0.25).value)
        resend_s = float(self.declare_parameter('resend_s', 3.0).value)
        max_age_s = float(self.declare_parameter('telemetry_max_age_s', 1.0).value)
        defer = list(self.declare_parameter('defer_while_moving', ['drone_1']).value)
        if (len(ids) != len(set(ids)) or len(ids) != len(radii)
                or any(not math.isfinite(r) or r < 0 for r in radii)):
            raise ValueError('agent_ids and radii_m must pair up with finite nonnegative radii')
        if any(not math.isfinite(v) or v <= 0 for v in (self.period_s, self.sigma_m, resend_s)):
            raise ValueError('sensor period, sigma and resend timeout must be positive and finite')
        if not self.scene_file:
            raise ValueError('scene_file is required: a SIMULATED scene declares what there is to sense')
        self.radii = dict(zip(ids, radii))
        self.ledger = SensorLedger(resend_s=resend_s, defer=frozenset(defer))
        self.telemetry = FreshTelemetry(self.run_id, ids, max_age_s)
        tile = load_public_terrain(manifest)
        self.expected_meta = {name: getattr(tile.metadata, name) for name in (
            'dataset_id', 'rows', 'cols', 'origin_x_m', 'origin_y_m', 'resolution_m',
            'crs', 'origin_lat_deg', 'origin_lon_deg', 'vertical_datum', 'checksum_sha256')}
        grid = tuple(self.expected_meta[k] for k in ('rows', 'cols', 'origin_x_m', 'origin_y_m', 'resolution_m'))
        heights = [None if nodata else float(h)
                   for h, nodata in zip(tile.prior.ravel(), tile.nodata_mask.ravel())]
        self.scene = scene_from_file(self.scene_file, grid, heights)
        self.feedback = FeedbackBatches(self.scene.rows * self.scene.cols)
        self.failed = False
        self.map_version = 0
        self.count = 0
        self.session_id = uuid.uuid4().hex  # restart cannot reuse an already-applied observation ID
        self.pub = self.create_publisher(TerrainObservation, TOPIC_OBSERVATIONS, RELIABLE)
        self.create_subscription(TerrainMeta, TOPIC_TERRAIN_META, self.on_meta, LATCHED)
        for name in ('belief', 'sigma', 'observed'):
            self.create_subscription(Image, f'/mge/terrain/{name}',
                                     lambda msg, name=name: self.on_layer(name, msg), LATCHED)
        self.create_subscription(OccupancyGrid, '/mge/terrain/traversability/drone',
                                 self.on_traversability, LATCHED)
        for agent_id in ids:
            self.create_subscription(AgentState, agent_state_topic(agent_id), self.on_state, RELIABLE)
        self.create_timer(self.period_s, self.tick)
        self.get_logger().warn('SIMULATED scene sensor: reports a declared test scene, not measurements')

    def on_meta(self, meta):
        if meta.run_id != self.run_id:
            return
        try:
            if (meta.header.frame_id != 'map' or meta.map_version < 1
                    or any(getattr(meta, key) != value for key, value in self.expected_meta.items())):
                raise ValueError('scene dataset, checksum, geometry or datum differs from the public terrain')
            self.feedback.on_meta(meta.map_version, stamp_ns(meta.header.stamp))
            self.map_version = self.feedback.version
            self.ledger.confirm(self.feedback.current())
        except ValueError as exc:
            self.fail(str(exc))

    def on_layer(self, name, msg):
        try:
            if (msg.header.frame_id != 'map' or (msg.height, msg.width) != (self.scene.rows, self.scene.cols)
                    or msg.is_bigendian not in (0, 1)):
                raise ValueError('feedback image frame/shape/byte order differs from the scene')
            if name == 'observed':
                if msg.encoding != 'mono8' or msg.step != msg.width or len(msg.data) != msg.height * msg.step:
                    raise ValueError('feedback observed image must be a packed mono8 grid')
                values = tuple(bytes(msg.data))
            else:
                if msg.encoding != '32FC1' or msg.step != 4 * msg.width or len(msg.data) != msg.height * msg.step:
                    raise ValueError('feedback height/sigma image must be a packed 32FC1 grid')
                values = struct.unpack(f'{">" if msg.is_bigendian else "<"}{msg.height * msg.width}f', bytes(msg.data))
            self.feedback.on_layer(name, stamp_ns(msg.header.stamp), values)
            self.ledger.confirm(self.feedback.current())
        except (ValueError, struct.error) as exc:
            self.fail(str(exc))

    def on_traversability(self, msg):
        try:
            origin = msg.info.origin
            expected = self.expected_meta
            if (msg.header.frame_id != 'map'
                    or (msg.info.height, msg.info.width) != (self.scene.rows, self.scene.cols)
                    or not math.isclose(msg.info.resolution, self.scene.resolution_m, rel_tol=1e-6, abs_tol=0)
                    or (origin.position.x, origin.position.y, origin.position.z)
                    != (expected['origin_x_m'], expected['origin_y_m'], 0.0)
                    or (origin.orientation.x, origin.orientation.y, origin.orientation.z, origin.orientation.w)
                    != (0.0, 0.0, 0.0, 1.0)):
                raise ValueError('feedback traversability geometry differs from the scene')
            self.feedback.on_layer('traversability', stamp_ns(msg.header.stamp), tuple(msg.data))
            self.ledger.confirm(self.feedback.current())
        except ValueError as exc:
            self.fail(str(exc))

    def fail(self, reason):
        if not self.failed:
            self.get_logger().error(f'Sensing disabled until a new run/node: {reason}')
        self.failed = True

    def on_state(self, msg):
        self.telemetry.accept(msg, self.get_clock().now().nanoseconds)
        if self.telemetry.clock_failed:
            self.fail('clock moved backwards')

    def now_s(self):
        return self.get_clock().now().nanoseconds * 1e-9

    def tick(self):
        now_ns = self.get_clock().now().nanoseconds
        if not self.telemetry.clock(now_ns):
            self.fail('clock moved backwards')
        feedback = self.feedback.current()
        if self.failed or feedback is None:
            return
        self.ledger.confirm(feedback)
        self.ledger.expire(now_ns * 1e-9)
        for agent_id in sorted(self.radii):
            state = self.telemetry.acquire(agent_id, now_ns, feedback.stamp_ns)
            if state is None:
                continue
            p = state.pose.position
            acquired_ns = stamp_ns(state.header.stamp)
            linear, angular = state.velocity.linear, state.velocity.angular
            moving = (state.mode in (AgentState.MODE_MOVING, AgentState.MODE_RETURNING)
                      or any(abs(v) > 1e-9 for v in
                             (linear.x, linear.y, linear.z, angular.x, angular.y, angular.z)))
            in_view, moving = self.ledger.view(
                agent_id, footprint(self.scene, p.x, p.y, self.radii[agent_id]),
                moving, acquired_ns=acquired_ns,
                base_version=self.map_version)
            cells = self.ledger.select(self.scene, in_view, moving=moving)
            if cells:
                self.report(agent_id, cells, acquired_ns)
                return      # ledger blocks every further report until evidence or timeout

    def report(self, agent_id, cells, acquired_ns):
        self.count += 1
        msg = TerrainObservation()
        msg.header.frame_id = 'map'
        msg.header.stamp.sec, msg.header.stamp.nanosec = divmod(acquired_ns, 1_000_000_000)
        msg.observation_id = f'{self.run_id}-sense-{self.session_id}-{self.count}'
        msg.run_id, msg.agent_id = self.run_id, agent_id
        msg.base_map_version = self.map_version
        msg.source_kind = TerrainObservation.SOURCE_SIMULATED
        msg.cell_indices = cells
        msg.elevation_m, msg.sigma_m, msg.obstacle = observation_values(self.scene, cells, self.sigma_m)
        self.pub.publish(msg)
        self.ledger.sent(msg.observation_id, cells, self.map_version, self.now_s(),
                         acquired_ns=acquired_ns,
                         values=(msg.elevation_m, msg.sigma_m, msg.obstacle))
        hazards = sum(1 for c in cells if c in self.scene.blocked)
        self.get_logger().info(f'{agent_id} reported {len(cells)} cells ({hazards} blocked) on map v{self.map_version}')


def main():
    rclpy.init()
    try:
        rclpy.spin(SceneSensor())
    except KeyboardInterrupt:
        pass


if __name__ == '__main__':
    main()
