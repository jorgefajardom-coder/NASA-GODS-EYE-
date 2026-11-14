"""MOCK terrain provider.

Publishes a TerrainMeta for a synthetic flat grid and bumps map_version for
every new TerrainObservation. It carries no Mars data and publishes no
rasters; it only lets consumers exercise map versioning before the real data
provider and belief map exist.
"""
import rclpy
from rclpy.node import Node

from mge_interfaces.msg import TerrainMeta, TerrainObservation
from mge_sim.common import LATCHED, RELIABLE, TOPIC_OBSERVATIONS, TOPIC_TERRAIN_META


class MockTerrain(Node):

    def __init__(self):
        super().__init__('mock_terrain')
        self.run_id = self.declare_parameter('run_id', 'mock-run').value
        self.rows = self.declare_parameter('rows', 200).value
        self.cols = self.declare_parameter('cols', 200).value
        self.resolution_m = self.declare_parameter('resolution_m', 5.0).value
        self.map_version = 1
        self.seen = set()
        self.pub = self.create_publisher(TerrainMeta, TOPIC_TERRAIN_META, LATCHED)
        self.create_subscription(
            TerrainObservation, TOPIC_OBSERVATIONS, self.on_observation, RELIABLE)
        self.get_logger().warn('MOCK data: synthetic flat grid, no Mars products')
        self.publish()

    def on_observation(self, obs):
        if obs.run_id != self.run_id:
            self.get_logger().warn(f'dropped observation of run {obs.run_id!r}')
            return
        if obs.observation_id in self.seen:
            self.get_logger().info(f'duplicate observation {obs.observation_id} ignored')
            return
        self.seen.add(obs.observation_id)
        self.map_version += 1
        self.publish()

    def publish(self):
        msg = TerrainMeta()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = 'map'
        msg.run_id = self.run_id
        msg.dataset_id = 'MOCK-flat-grid'
        msg.map_version = self.map_version
        half_w = self.cols * self.resolution_m / 2.0
        half_h = self.rows * self.resolution_m / 2.0
        msg.origin_x_m = -half_w
        msg.origin_y_m = -half_h
        msg.resolution_m = float(self.resolution_m)
        msg.rows = self.rows
        msg.cols = self.cols
        msg.crs = 'MOCK'
        msg.vertical_datum = 'MOCK'
        msg.nodata_value = float('nan')
        msg.sources = ['MOCK synthetic flat grid, not derived from any mission data']
        self.pub.publish(msg)


def main():
    rclpy.init()
    try:
        rclpy.spin(MockTerrain())
    except KeyboardInterrupt:
        pass


if __name__ == '__main__':
    main()
