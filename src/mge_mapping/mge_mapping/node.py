"""ROS 2 Mapping node for incremental belief updates and traversability publication.

Publishes the public map batch the planner consumes (docs/ICD.md, section 5):
metadata first, then belief, sigma, the observed mask and one traversability
mask per agent kind, all with the same stamp. The observed mask (mono8, 1 for a
cell some applied observation covered) is for the recorder and viewer; the
planner does not subscribe to it. One stamp identifies one map version and is never
reused. Topics have no common delivery order, so the same batch is repeated.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from mge_data.core import default_manifest_path, load_public_terrain
from mge_mapping.core import BeliefMap, ObservationFusion, SimulatedObservation
from mge_mapping.policy import load_knowledge_policy

DEFAULT_MANIFEST_PATH = default_manifest_path()
# PLACEHOLDER slope limits per agent kind, pending David's scientific approval.
AGENT_SLOPE_LIMITS_DEG = {"human": 10.0, "rover": 20.0, "drone": 90.0}


def observation_from_message(msg: Any) -> SimulatedObservation:
    """Validate wire frame/clock before passing a measurement to fusion.

    Kept ROS-independent so tests can exercise the production conversion. Invalid
    timestamps are rejected, never clamped or normalized into a different time.
    """
    if msg.header.frame_id != "map":
        raise ValueError("observation frame_id must be map")
    sec, nanosec = msg.header.stamp.sec, msg.header.stamp.nanosec
    if (type(sec) is not int or not 0 <= sec < 2**31 or type(nanosec) is not int
            or not 0 <= nanosec < 1_000_000_000):
        raise ValueError("observation stamp requires nonnegative int32 seconds and nanoseconds below 1e9")
    return SimulatedObservation(
        observation_id=msg.observation_id,
        agent_id=msg.agent_id,
        run_id=msg.run_id,
        source_map_version=msg.base_map_version,
        timestamp_sim_s=sec + nanosec * 1e-9,
        timestamp_sim_ns=sec * 1_000_000_000 + nanosec,
        cell_indices=tuple(msg.cell_indices),
        elevations_m=tuple(msg.elevation_m),
        sigmas_m=tuple(msg.sigma_m) if msg.sigma_m else None,
        obstacles=tuple(msg.obstacle) if msg.obstacle else None,
        source_kind=msg.source_kind,
    )


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
        "last_observation_timestamp_sim_s": belief.last_observation_timestamp_sim_s,
    }


def main(args=None) -> None:
    import rclpy
    from nav_msgs.msg import OccupancyGrid
    from rclpy.node import Node
    from rclpy.qos import DurabilityPolicy, QoSProfile, ReliabilityPolicy
    from rclpy.time import Time
    from sensor_msgs.msg import Image

    from mge_interfaces.msg import TerrainMeta, TerrainObservation

    rclpy.init(args=args)
    node = Node("mapping_node")
    manifest_param = node.declare_parameter("manifest_path", str(DEFAULT_MANIFEST_PATH)).value
    run_id_param = str(node.declare_parameter("run_id", "run-1").value)
    # Slow by default: re-ingesting layers at 1 Hz starves the planner service.
    repeat_s = float(node.declare_parameter("repeat_period_s", 5.0).value)
    policy_path = str(node.declare_parameter("exploration_policy_file", "").value)

    try:
        # A provider without valid terrain must not stay up looking healthy.
        tile = load_public_terrain(Path(manifest_param))
        policy = load_knowledge_policy(policy_path) if policy_path else None
        if policy is not None:
            node.get_logger().warning(policy.source_record + "; not execution authorization")
        fusion = ObservationFusion(
            BeliefMap.from_terrain_tile(tile, run_id=run_id_param, initial_map_version=1))

        latched_qos = QoSProfile(
            depth=1,
            reliability=ReliabilityPolicy.RELIABLE,
            durability=DurabilityPolicy.TRANSIENT_LOCAL,
        )
        obs_qos = QoSProfile(depth=10, reliability=ReliabilityPolicy.RELIABLE)
        meta_pub = node.create_publisher(TerrainMeta, "/mge/terrain/meta", latched_qos)
        belief_pub = node.create_publisher(Image, "/mge/terrain/belief", latched_qos)
        sigma_pub = node.create_publisher(Image, "/mge/terrain/sigma", latched_qos)
        observed_pub = node.create_publisher(Image, "/mge/terrain/observed", latched_qos)
        trav_pubs = {
            kind: node.create_publisher(OccupancyGrid, f"/mge/terrain/traversability/{kind}", latched_qos)
            for kind in AGENT_SLOPE_LIMITS_DEG
        }
        batch = {"version": None, "stamp": None, "messages": ()}

        def new_stamp():
            """Strictly later than the stamp of the previous map version."""
            now = node.get_clock().now()
            if batch["stamp"] is not None:
                previous_ns = Time.from_msg(batch["stamp"]).nanoseconds
                if now.nanoseconds <= previous_ns:
                    now = Time(nanoseconds=previous_ns + 1, clock_type=now.clock_type)
            return now.to_msg()

        def build_batch(bmap: BeliefMap) -> None:
            stamp = new_stamp()
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
            if policy is not None:
                meta.sources.append(policy.source_record)
            meta.checksum_sha256 = tile.metadata.checksum_sha256
            messages = [(meta_pub, meta)]           # metadata first: layers need it

            for arr, pub in ((bmap.belief, belief_pub), (bmap.sigma, sigma_pub)):
                img = Image()
                img.header = meta.header
                img.height = bmap.rows
                img.width = bmap.cols
                img.encoding = "32FC1"
                img.is_bigendian = 0
                img.step = bmap.cols * 4
                img.data = arr.astype("<f4").tobytes()
                messages.append((pub, img))

            observed = Image()
            observed.header = meta.header
            observed.height = bmap.rows
            observed.width = bmap.cols
            observed.encoding = "mono8"
            observed.is_bigendian = 0
            observed.step = bmap.cols
            observed.data = bmap.observed_mask.astype("u1").tobytes()
            messages.append((observed_pub, observed))

            for kind, max_slope in AGENT_SLOPE_LIMITS_DEG.items():
                occ = OccupancyGrid()
                occ.header = meta.header
                occ.info.map_load_time = stamp
                occ.info.resolution = float(bmap.resolution_m)
                occ.info.width = bmap.cols
                occ.info.height = bmap.rows
                occ.info.origin.position.x = float(bmap.origin_x_m)
                occ.info.origin.position.y = float(bmap.origin_y_m)
                occ.info.origin.orientation.w = 1.0
                limits = dict(policy.limits[kind]) if policy else {"max_slope_deg": max_slope}
                occ_grid = bmap.traversability_grid(
                    **limits, allow_estimated=policy.allow_estimated if policy else False)
                occ.data = [int(v) for v in occ_grid.ravel()]
                messages.append((trav_pubs[kind], occ))

            batch.update(version=bmap.map_version, stamp=stamp, messages=tuple(messages))

        def publish_batch() -> None:
            for pub, message in batch["messages"]:
                pub.publish(message)

        def on_observation(msg: Any) -> None:
            # A bad observation is dropped; it must not stop the map provider.
            try:
                obs = observation_from_message(msg)
                updated, applied = fusion.apply(obs)
            except (ValueError, TypeError) as exc:
                node.get_logger().warning(f"Rejected observation '{msg.observation_id}': {exc}")
                return
            if applied:
                build_batch(updated)
                publish_batch()

        build_batch(fusion.belief_map)
        publish_batch()
        node.create_subscription(TerrainObservation, "/mge/observations", on_observation, obs_qos)
        if repeat_s > 0:
            node.create_timer(repeat_s, publish_batch)
        node.get_logger().info(f"Initialized mapping_node at map_version={fusion.map_version}")
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
