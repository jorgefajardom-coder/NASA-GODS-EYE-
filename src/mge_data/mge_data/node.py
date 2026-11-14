"""ROS 2 DataProvider node for validated public terrain metadata and prior layer."""

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

    rclpy.init(args=args)
    node = Node("data_node")
    manifest_param = node.declare_parameter("manifest_path", str(DEFAULT_MANIFEST_PATH)).value
    run_id_param = node.declare_parameter("run_id", "run-1").value

    try:
        tile = load_public_terrain(Path(manifest_param))
        meta_dict = build_terrain_meta_dict(tile, run_id=str(run_id_param))
        qos = QoSProfile(
            depth=1,
            reliability=ReliabilityPolicy.RELIABLE,
            durability=DurabilityPolicy.TRANSIENT_LOCAL,
        )
        try:
            from mge_interfaces.msg import TerrainMeta
            from sensor_msgs.msg import Image

            meta_pub = node.create_publisher(TerrainMeta, "/mge/terrain/meta", qos)
            prior_pub = node.create_publisher(Image, "/mge/terrain/prior", qos)

            msg = TerrainMeta()
            msg.header.frame_id = meta_dict["frame_id"]
            msg.header.stamp = node.get_clock().now().to_msg()
            msg.run_id = meta_dict["run_id"]
            msg.dataset_id = meta_dict["dataset_id"]
            msg.map_version = meta_dict["map_version"]
            msg.origin_x_m = meta_dict["origin_x_m"]
            msg.origin_y_m = meta_dict["origin_y_m"]
            msg.resolution_m = meta_dict["resolution_m"]
            msg.rows = meta_dict["rows"]
            msg.cols = meta_dict["cols"]
            msg.crs = meta_dict["crs"]
            msg.origin_lat_deg = meta_dict["origin_lat_deg"]
            msg.origin_lon_deg = meta_dict["origin_lon_deg"]
            msg.vertical_datum = meta_dict["vertical_datum"]
            msg.nodata_value = meta_dict["nodata_value"]
            msg.sources = meta_dict["sources"]
            msg.checksum_sha256 = meta_dict["checksum_sha256"]
            meta_pub.publish(msg)

            img = Image()
            img.header = msg.header
            img.height = tile.metadata.rows
            img.width = tile.metadata.cols
            img.encoding = "32FC1"
            img.is_bigendian = 0
            img.step = tile.metadata.cols * 4
            img.data = tile.prior.astype("<f4").tobytes()
            prior_pub.publish(img)
            node.get_logger().info(
                f"Published validated public terrain '{meta_dict['dataset_id']}' "
                f"({meta_dict['rows']}x{meta_dict['cols']} @ {meta_dict['resolution_m']} m)"
            )
        except ImportError:
            node.get_logger().warning("mge_interfaces or sensor_msgs not built; validated terrain loaded in memory only")
    except Exception as exc:  # noqa: BLE001
        node.get_logger().error(f"Failed to load public terrain manifest: {exc}")

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
