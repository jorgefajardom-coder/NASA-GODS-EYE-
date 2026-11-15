"""ROS 2 DataProvider node: publishes the immutable public prior layer.

Terrain metadata is not published here. A map version is one batch of metadata,
belief, sigma and masks under a single stamp (docs/ICD.md, section 5), and the
planner rejects metadata of the same version that arrives with another stamp.
`mapping_node` owns the map version, so it is the only metadata publisher.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from mge_data.core import (
    AuxiliaryTerrainLayers,
    TerrainTile,
    default_manifest_path,
    load_auxiliary_terrain_layers,
    load_public_terrain,
)

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


def build_aux_layer_messages_dict(
    tile: TerrainTile,
    aux: AuxiliaryTerrainLayers,
) -> dict[str, dict[str, Any]]:
    """Build RViz-ready Image and OccupancyGrid payload dictionaries for auxiliary terrain layers."""
    meta = tile.metadata
    return {
        "ctx_ortho": {
            "topic": "/mge/terrain/aux/ctx_ortho",
            "msg_type": "sensor_msgs/msg/Image",
            "frame_id": meta.frame_id,
            "height": int(meta.rows),
            "width": int(meta.cols),
            "encoding": "mono8",
            "is_bigendian": 0,
            "step": int(meta.cols),
            "data": aux.ctx_ortho_dn.tobytes(),
        },
        "surface_zones": {
            "topic": "/mge/terrain/aux/surface_zones",
            "msg_type": "nav_msgs/msg/OccupancyGrid",
            "frame_id": meta.frame_id,
            "resolution": float(meta.resolution_m),
            "width": int(meta.cols),
            "height": int(meta.rows),
            "origin_x_m": float(meta.origin_x_m),
            "origin_y_m": float(meta.origin_y_m),
            "data": [int(v) for v in aux.surface_zone_rviz_occupancy.reshape(-1)],
            "legend": list(aux.manifest.get("surface_zones", {}).get("definitions", [])),
        },
        "geology_zones": {
            "topic": "/mge/terrain/aux/geology_zones",
            "msg_type": "nav_msgs/msg/OccupancyGrid",
            "frame_id": meta.frame_id,
            "resolution": float(meta.resolution_m),
            "width": int(meta.cols),
            "height": int(meta.rows),
            "origin_x_m": float(meta.origin_x_m),
            "origin_y_m": float(meta.origin_y_m),
            "data": [int(v) for v in aux.geology_rviz_occupancy.reshape(-1)],
            "legend": list(aux.geology.get("units", [])),
        },
    }


def main(args=None) -> None:
    import rclpy
    from nav_msgs.msg import OccupancyGrid
    from rclpy.node import Node
    from rclpy.qos import DurabilityPolicy, QoSProfile, ReliabilityPolicy
    from sensor_msgs.msg import Image

    rclpy.init(args=args)
    node = Node("data_node")
    manifest_param = node.declare_parameter("manifest_path", str(DEFAULT_MANIFEST_PATH)).value
    node.declare_parameter("run_id", "run-1")
    publish_aux = bool(node.declare_parameter("publish_aux_layers", True).value)
    try:
        # A provider without valid terrain must not stay up looking healthy.
        tile = load_public_terrain(Path(manifest_param))
        qos = QoSProfile(
            depth=1,
            reliability=ReliabilityPolicy.RELIABLE,
            durability=DurabilityPolicy.TRANSIENT_LOCAL,
        )
        now_msg = node.get_clock().now().to_msg()
        prior_pub = node.create_publisher(Image, "/mge/terrain/prior", qos)
        img = Image()
        img.header.frame_id = tile.metadata.frame_id
        img.header.stamp = now_msg
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

        # Optional auxiliary layers for RViz / 3D terrain zone visualization (non-breaking if absent or disabled)
        aux_pubs = []
        if publish_aux:
            aux = load_auxiliary_terrain_layers(Path(manifest_param), tile=tile, strict=False)
            if aux is not None:
                aux_msgs = build_aux_layer_messages_dict(tile, aux)

                ortho_info = aux_msgs["ctx_ortho"]
                ortho_pub = node.create_publisher(Image, ortho_info["topic"], qos)
                ortho_msg = Image()
                ortho_msg.header.frame_id = ortho_info["frame_id"]
                ortho_msg.header.stamp = now_msg
                ortho_msg.height = ortho_info["height"]
                ortho_msg.width = ortho_info["width"]
                ortho_msg.encoding = ortho_info["encoding"]
                ortho_msg.is_bigendian = ortho_info["is_bigendian"]
                ortho_msg.step = ortho_info["step"]
                ortho_msg.data = ortho_info["data"]
                ortho_pub.publish(ortho_msg)
                aux_pubs.append(ortho_pub)

                for key in ("surface_zones", "geology_zones"):
                    grid_info = aux_msgs[key]
                    grid_pub = node.create_publisher(OccupancyGrid, grid_info["topic"], qos)
                    grid_msg = OccupancyGrid()
                    grid_msg.header.frame_id = grid_info["frame_id"]
                    grid_msg.header.stamp = now_msg
                    grid_msg.info.resolution = grid_info["resolution"]
                    grid_msg.info.width = grid_info["width"]
                    grid_msg.info.height = grid_info["height"]
                    grid_msg.info.origin.position.x = grid_info["origin_x_m"]
                    grid_msg.info.origin.position.y = grid_info["origin_y_m"]
                    grid_msg.info.origin.position.z = 0.0
                    grid_msg.info.origin.orientation.w = 1.0
                    grid_msg.data = grid_info["data"]
                    grid_pub.publish(grid_msg)
                    aux_pubs.append(grid_pub)

                node.get_logger().info(
                    "Published optional auxiliary NASA/USGS layers on "
                    "/mge/terrain/aux/{ctx_ortho,surface_zones,geology_zones}"
                )

        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
