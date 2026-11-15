"""SIMULATED on-board sensor node: agents report the declared test scene around them.

Reads a SIMULATED scene file (blocked cells; truth heights are the public prior
of the run's dataset), follows the configured agents' states and publishes
TerrainObservation messages on /mge/observations with source SIMULATED, using
the reporting policy of `mge_sim.scene_sensing`: hazards are reported as soon
as a moving agent sees them, plain coverage only while it is stopped. It never
uses evaluator reference data and never claims a measurement.
"""
import math

import rclpy
from rclpy.node import Node

from mge_data.core import default_manifest_path, load_public_terrain
from mge_interfaces.msg import AgentState, TerrainMeta, TerrainObservation
from mge_sim.common import LATCHED, RELIABLE, TOPIC_OBSERVATIONS, TOPIC_TERRAIN_META, agent_state_topic
from mge_sim.scene_sensing import SensorLedger, footprint, observation_values, scene_from_file


class SceneSensor(Node):

    def __init__(self):
        super().__init__('scene_sensor')
        self.run_id = self.declare_parameter('run_id', 'mock-run').value
        self.scene_file = self.declare_parameter('scene_file', '').value
        ids = list(self.declare_parameter('agent_ids', ['drone_1', 'human_1', 'rover_1']).value)
        radii = [float(r) for r in self.declare_parameter('radii_m', [24.0, 8.0, 12.0]).value]
        self.period_s = float(self.declare_parameter('period_s', 1.0).value)
        self.sigma_m = float(self.declare_parameter('sigma_m', 0.25).value)
        resend_s = float(self.declare_parameter('resend_s', 3.0).value)
        defer = list(self.declare_parameter('defer_while_moving', ['drone_1']).value)
        if len(ids) != len(radii) or any(not math.isfinite(r) or r < 0 for r in radii):
            raise ValueError('agent_ids and radii_m must pair up with finite nonnegative radii')
        if not self.scene_file:
            raise ValueError('scene_file is required: a SIMULATED scene declares what there is to sense')
        self.radii = dict(zip(ids, radii))
        self.ledger = SensorLedger(resend_s=resend_s, defer=frozenset(defer))
        self.scene = None
        self.map_version = 0
        self.states = {}
        self.count = 0
        self.pub = self.create_publisher(TerrainObservation, TOPIC_OBSERVATIONS, RELIABLE)
        self.create_subscription(TerrainMeta, TOPIC_TERRAIN_META, self.on_meta, LATCHED)
        for agent_id in ids:
            self.create_subscription(AgentState, agent_state_topic(agent_id), self.on_state, RELIABLE)
        self.create_timer(self.period_s, self.tick)
        self.get_logger().warn('SIMULATED scene sensor: reports a declared test scene, not measurements')

    def on_meta(self, meta):
        if meta.run_id != self.run_id:
            return
        if self.scene is None:
            tile = load_public_terrain(default_manifest_path())
            if tile.metadata.dataset_id != meta.dataset_id:
                self.get_logger().error(f'scene needs dataset {meta.dataset_id}, prior is {tile.metadata.dataset_id}')
                return
            grid = (meta.rows, meta.cols, meta.origin_x_m, meta.origin_y_m, meta.resolution_m)
            # NoData cells of the dataset carry no truth and are never sensed.
            heights = [None if nodata else float(h)
                       for h, nodata in zip(tile.prior.ravel(), tile.nodata_mask.ravel())]
            self.scene = scene_from_file(self.scene_file, grid, heights)
            self.get_logger().info(f'scene loaded: {len(self.scene.blocked)} blocked cells')
        if meta.map_version > self.map_version:
            self.map_version = meta.map_version
            self.ledger.confirm(meta.map_version)

    def on_state(self, msg):
        if msg.run_id == self.run_id and msg.header.frame_id == 'map':
            self.states[msg.agent_id] = msg

    def now_s(self):
        return self.get_clock().now().nanoseconds * 1e-9

    def tick(self):
        if self.scene is None or self.map_version == 0:
            return
        self.ledger.expire(self.now_s())
        for agent_id, state in sorted(self.states.items()):
            p = state.pose.position
            in_view, moving = self.ledger.view(
                agent_id, footprint(self.scene, p.x, p.y, self.radii[agent_id]),
                state.mode == AgentState.MODE_MOVING)
            cells = self.ledger.select(self.scene, in_view, moving=moving)
            if cells:
                self.report(agent_id, cells)
                return      # one report per tick: the next waits for the new map version

    def report(self, agent_id, cells):
        self.count += 1
        msg = TerrainObservation()
        msg.header.frame_id = 'map'
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.observation_id = f'{self.run_id}-sense-{self.count}'
        msg.run_id, msg.agent_id = self.run_id, agent_id
        msg.base_map_version = self.map_version
        msg.source_kind = TerrainObservation.SOURCE_SIMULATED
        msg.cell_indices = cells
        msg.elevation_m, msg.sigma_m, msg.obstacle = observation_values(self.scene, cells, self.sigma_m)
        self.pub.publish(msg)
        self.ledger.sent(msg.observation_id, cells, self.map_version, self.now_s())
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
