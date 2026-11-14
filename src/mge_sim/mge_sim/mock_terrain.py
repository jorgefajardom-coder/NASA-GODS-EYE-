"""MOCK terrain provider.

Publishes a coherent public map batch for a synthetic flat grid: metadata,
belief, sigma and one traversability mask per agent kind, all with the same
snapshot stamp (planner batch protocol, docs/ICD.md). Every new
TerrainObservation bumps map_version and yields a new batch with a new stamp;
the layers themselves do not change. It carries no Mars data: it only lets
consumers exercise map versioning before the real data provider and belief
map exist.
"""
import array

from nav_msgs.msg import OccupancyGrid
import rclpy
from rclpy.node import Node
from rclpy.time import Time
from sensor_msgs.msg import Image

from mge_interfaces.msg import TerrainMeta, TerrainObservation
from mge_sim.common import LATCHED, RELIABLE, TOPIC_OBSERVATIONS, TOPIC_TERRAIN_META

KINDS = ('human', 'rover', 'drone')
SIGMA_M = 0.1           # PLACEHOLDER uncertainty of the synthetic surface


class MockTerrain(Node):

    def __init__(self):
        super().__init__('mock_terrain')
        self.run_id = self.declare_parameter('run_id', 'mock-run').value
        self.rows = self.declare_parameter('rows', 200).value
        self.cols = self.declare_parameter('cols', 200).value
        self.resolution_m = self.declare_parameter('resolution_m', 5.0).value
        repeat_s = self.declare_parameter('repeat_period_s', 5.0).value
        self.map_version = 1
        self.stamp = self.new_stamp(None)
        self.seen = set()
        self.pub_meta = self.create_publisher(TerrainMeta, TOPIC_TERRAIN_META, LATCHED)
        self.pub_image = {
            name: self.create_publisher(Image, f'/mge/terrain/{name}', LATCHED)
            for name in ('belief', 'sigma')}
        self.pub_mask = {
            kind: self.create_publisher(
                OccupancyGrid, f'/mge/terrain/traversability/{kind}', LATCHED)
            for kind in KINDS}
        self.create_subscription(
            TerrainObservation, TOPIC_OBSERVATIONS, self.on_observation, RELIABLE)
        # Topics have no common delivery order, so the same batch is repeated.
        # Slowly: at 1 Hz the planner node spends its time re-ingesting layers and
        # stops answering PlanRoute (measured with grids of 60 x 60 cells and up).
        if repeat_s > 0:
            self.create_timer(repeat_s, self.publish)
        self.get_logger().warn('MOCK data: synthetic flat grid, no Mars products')
        self.publish()

    def new_stamp(self, previous):
        """One stamp identifies one map version and is never reused."""
        now = self.get_clock().now()
        if previous is not None and now.nanoseconds <= Time.from_msg(previous).nanoseconds:
            now = Time(nanoseconds=Time.from_msg(previous).nanoseconds + 1,
                       clock_type=now.clock_type)
        return now.to_msg()

    def on_observation(self, obs):
        if obs.run_id != self.run_id:
            self.get_logger().warn(f'dropped observation of run {obs.run_id!r}')
            return
        if obs.observation_id in self.seen:
            self.get_logger().info(f'duplicate observation {obs.observation_id} ignored')
            return
        self.seen.add(obs.observation_id)
        self.map_version += 1
        self.stamp = self.new_stamp(self.stamp)
        self.publish()

    def publish(self):
        origin_x = -self.cols * self.resolution_m / 2.0
        origin_y = -self.rows * self.resolution_m / 2.0
        cells = self.rows * self.cols

        meta = TerrainMeta()
        meta.header.stamp = self.stamp
        meta.header.frame_id = 'map'
        meta.run_id = self.run_id
        meta.dataset_id = 'MOCK-flat-grid'
        meta.map_version = self.map_version
        meta.origin_x_m = origin_x
        meta.origin_y_m = origin_y
        meta.resolution_m = float(self.resolution_m)
        meta.rows = self.rows
        meta.cols = self.cols
        meta.crs = 'MOCK'
        meta.vertical_datum = 'MOCK'
        meta.nodata_value = float('nan')
        meta.sources = ['MOCK synthetic flat grid, not derived from any mission data']
        self.pub_meta.publish(meta)

        for name, value in (('belief', 0.0), ('sigma', SIGMA_M)):
            image = Image()
            image.header = meta.header
            image.height = self.rows
            image.width = self.cols
            image.encoding = '32FC1'
            image.is_bigendian = 0
            image.step = self.cols * 4
            layer = array.array('f', [value]) * cells
            if layer.itemsize != 4:
                raise RuntimeError('float32 layout expected')
            image.data = array.array('B', layer.tobytes())
            self.pub_image[name].publish(image)

        for kind in KINDS:
            grid = OccupancyGrid()
            grid.header = meta.header
            grid.info.map_load_time = self.stamp
            grid.info.resolution = float(self.resolution_m)
            grid.info.width = self.cols
            grid.info.height = self.rows
            grid.info.origin.position.x = origin_x
            grid.info.origin.position.y = origin_y
            grid.info.origin.orientation.w = 1.0
            grid.data = array.array('b', [0]) * cells      # every cell admissible
            self.pub_mask[kind].publish(grid)


def main():
    rclpy.init()
    try:
        rclpy.spin(MockTerrain())
    except KeyboardInterrupt:
        pass


if __name__ == '__main__':
    main()
