"""ROS 2 DataProvider node: publishes the immutable public prior layer.

Terrain metadata is not published here. A map version is one batch of metadata,
belief, sigma and masks under a single stamp (docs/ICD.md, section 5), and the
planner rejects metadata of the same version that arrives with another stamp.
`mapping_node` owns the map version, so it is the only metadata publisher.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from mge_data.core import TerrainTile, default_manifest_path, load_public_terrain

DEFAULT_MANIFEST_PATH = default_manifest_path()


def build_terrain_meta_dict(tile: TerrainTile, *, run_id: str = "run-1") -> dict[str, Any]:
    """Serialize public TerrainTile metadata to the canonical ICD TerrainMeta fields."""
    meta = tile.metadata
    return {
        "frame_id": meta.frame_id,
        "run_id": run_id,
        "dataset_id": meta.dataset_id,
        "map_version": int(meta.map_version),
        "origin_x_m": float(meta.origin_x_m),
        "origin_y_m": float(meta.origin_y_m),
        "resolution_m": float(meta.resolution_m),
        "rows": int(meta.rows),
        "cols": int(meta.cols),
        "crs": meta.crs,
        "origin_lat_deg": float(meta.origin_lat_deg),
        "origin_lon_deg": float(meta.origin_lon_deg),
        "vertical_datum": meta.vertical_datum,
        "nodata_value": float(meta.nodata_value),
        "sources": list(tile.sources.public_sources_summary()),
        "checksum_sha256": meta.checksum_sha256,
    }


def main(args=None) -> None:
    import rclpy
    from rclpy.node import Node
    from rclpy.qos import DurabilityPolicy, QoSProfile, ReliabilityPolicy
    from sensor_msgs.msg import Image

    rclpy.init(args=args)
    node = Node("data_node")
    manifest_param = node.declare_parameter("manifest_path", str(DEFAULT_MANIFEST_PATH)).value
    node.declare_parameter("run_id", "run-1")
    try:
        # A provider without valid terrain must not stay up looking healthy.
        tile = load_public_terrain(Path(manifest_param))
        qos = QoSProfile(
            depth=1,
            reliability=ReliabilityPolicy.RELIABLE,
            durability=DurabilityPolicy.TRANSIENT_LOCAL,
        )
        prior_pub = node.create_publisher(Image, "/mge/terrain/prior", qos)
        img = Image()
        img.header.frame_id = tile.metadata.frame_id
        img.header.stamp = node.get_clock().now().to_msg()
        img.height = tile.metadata.rows
        img.width = tile.metadata.cols
        img.encoding = "32FC1"
        img.is_bigendian = 0
        img.step = tile.metadata.cols * 4
        img.data = tile.prior.astype("<f4").tobytes()
        prior_pub.publish(img)
        node.get_logger().info(
            f"Published public prior of '{tile.metadata.dataset_id}' "
            f"({tile.metadata.rows}x{tile.metadata.cols} @ {tile.metadata.resolution_m} m)"
        )
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
