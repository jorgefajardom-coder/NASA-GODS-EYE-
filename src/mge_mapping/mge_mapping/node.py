"""ROS 2 Mapping node for incremental belief updates and traversability publication."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from mge_data.core import default_manifest_path, load_public_terrain
from mge_mapping.core import BeliefMap, ObservationFusion, SimulatedObservation

DEFAULT_MANIFEST_PATH = default_manifest_path()
AGENT_SLOPE_LIMITS_DEG = {"human": 10.0, "rover": 20.0, "drone": 90.0}


def build_mapping_state_summary(belief: BeliefMap) -> dict[str, Any]:
    """Return a serializable summary of the current public BeliefMap state."""
    return {
        "run_id": belief.run_id,
        "dataset_id": belief.dataset_id,
        "frame_id": belief.frame_id,
        "map_version": int(belief.map_version),
        "rows": int(belief.rows),
        "cols": int(belief.cols),
        "resolution_m": float(belief.resolution_m),
        "observed_cell_count": int(belief.observed_mask.sum()),
        "nodata_cell_count": int(belief.nodata_mask.sum()),
        "applied_observations": list(belief.applied_observations),
    }


def main(args=None) -> None:
    import rclpy
    from rclpy.node import Node
    from rclpy.qos import DurabilityPolicy, QoSProfile, ReliabilityPolicy

    rclpy.init(args=args)
    node = Node("mapping_node")
    manifest_param = node.declare_parameter("manifest_path", str(DEFAULT_MANIFEST_PATH)).value
    run_id_param = str(node.declare_parameter("run_id", "run-1").value)

    try:
        tile = load_public_terrain(Path(manifest_param))
        initial_belief = BeliefMap.from_terrain_tile(tile, run_id=run_id_param, initial_map_version=1)
        fusion = ObservationFusion(initial_belief)

        latched_qos = QoSProfile(
            depth=1,
            reliability=ReliabilityPolicy.RELIABLE,
            durability=DurabilityPolicy.TRANSIENT_LOCAL,
        )
        obs_qos = QoSProfile(
            depth=10,
            reliability=ReliabilityPolicy.RELIABLE,
        )

        try:
            from mge_interfaces.msg import TerrainMeta, TerrainObservation
            from nav_msgs.msg import OccupancyGrid
            from sensor_msgs.msg import Image

            meta_pub = node.create_publisher(TerrainMeta, "/mge/terrain/meta", latched_qos)
            belief_pub = node.create_publisher(Image, "/mge/terrain/belief", latched_qos)
            sigma_pub = node.create_publisher(Image, "/mge/terrain/sigma", latched_qos)
            trav_pubs = {
                kind: node.create_publisher(OccupancyGrid, f"/mge/terrain/traversability/{kind}", latched_qos)
                for kind in AGENT_SLOPE_LIMITS_DEG
            }

            def publish_layers(bmap: BeliefMap) -> None:
                stamp = node.get_clock().now().to_msg()
                for arr, pub in ((bmap.belief, belief_pub), (bmap.sigma, sigma_pub)):
                    img = Image()
                    img.header.frame_id = bmap.frame_id
                    img.header.stamp = stamp
                    img.height = bmap.rows
                    img.width = bmap.cols
                    img.encoding = "32FC1"
                    img.is_bigendian = 0
                    img.step = bmap.cols * 4
                    img.data = arr.astype("<f4").tobytes()
                    pub.publish(img)

                for kind, max_slope in AGENT_SLOPE_LIMITS_DEG.items():
                    occ = OccupancyGrid()
                    occ.header.frame_id = bmap.frame_id
                    occ.header.stamp = stamp
                    occ.info.resolution = float(bmap.resolution_m)
                    occ.info.width = bmap.cols
                    occ.info.height = bmap.rows
                    occ.info.origin.position.x = float(bmap.origin_x_m)
                    occ.info.origin.position.y = float(bmap.origin_y_m)
                    occ.info.origin.orientation.w = 1.0
                    occ_grid = bmap.traversability_grid(max_slope_deg=max_slope)
                    occ.data = [int(v) for v in occ_grid.ravel()]
                    trav_pubs[kind].publish(occ)

                meta = TerrainMeta()
                meta.header.frame_id = bmap.frame_id
                meta.header.stamp = stamp
                meta.run_id = bmap.run_id
                meta.dataset_id = bmap.dataset_id
                meta.map_version = bmap.map_version
                meta.origin_x_m = float(bmap.origin_x_m)
                meta.origin_y_m = float(bmap.origin_y_m)
                meta.resolution_m = float(bmap.resolution_m)
                meta.rows = bmap.rows
                meta.cols = bmap.cols
                meta.crs = tile.metadata.crs
                meta.origin_lat_deg = float(tile.metadata.origin_lat_deg)
                meta.origin_lon_deg = float(tile.metadata.origin_lon_deg)
                meta.vertical_datum = tile.metadata.vertical_datum
                meta.nodata_value = float(tile.metadata.nodata_value)
                meta.sources = list(tile.sources.public_sources_summary())
                meta.checksum_sha256 = tile.metadata.checksum_sha256
                meta_pub.publish(meta)

            def on_observation(msg: Any) -> None:
                stamp_s = float(msg.header.stamp.sec) + float(msg.header.stamp.nanosec) * 1e-9
                obs = SimulatedObservation(
                    observation_id=str(msg.observation_id),
                    agent_id=str(msg.agent_id),
                    run_id=str(msg.run_id),
                    source_map_version=int(msg.base_map_version),
                    timestamp_sim_s=max(0.0, stamp_s),
                    cell_indices=tuple(int(i) for i in msg.cell_indices),
                    elevations_m=tuple(float(z) for z in msg.elevation_m),
                    sigmas_m=tuple(float(s) for s in msg.sigma_m) if msg.sigma_m else None,
                    obstacles=tuple(int(o) for o in msg.obstacle) if msg.obstacle else None,
                    source_kind=str(msg.source_kind),
                )
                updated, applied = fusion.apply(obs)
                if applied:
                    publish_layers(updated)

            publish_layers(fusion.belief_map)
            node.create_subscription(TerrainObservation, "/mge/observations", on_observation, obs_qos)
            node.get_logger().info(f"Initialized mapping_node at map_version={fusion.map_version}")
        except ImportError:
            node.get_logger().warning("ROS interfaces not compiled; mapping fusion initialized in memory only")
    except Exception as exc:  # noqa: BLE001
        node.get_logger().error(f"Failed to initialize mapping_node: {exc}")

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
