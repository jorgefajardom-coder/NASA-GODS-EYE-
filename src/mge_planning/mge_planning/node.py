"""PlanRoute server. MissionManager, not this node, authorizes active routes."""

from math import isfinite

from .adapter import SnapshotStore, load_profiles, request_from_ros
from .core import RouteStatus, SearchLimits, plan_route


def _failure(message, response, status, reason, detail):
    decision = response.decision
    decision.run_id = message.run_id
    decision.request_id = message.request_id
    decision.agent_id = message.agent_id
    decision.mode = message.mode
    decision.map_version_used = message.map_version
    decision.header.frame_id = "map"
    decision.status = status.value
    decision.reason_code = reason
    decision.detail = detail
    decision.route_id = ""
    decision.outbound_path = []
    decision.return_path = []
    for name in ("travel_time_s", "energy_est_wh", "oxygen_est_l", "min_clearance_m",
                 "reserve_time_s", "reserve_wh", "reserve_oxygen_l"):
        setattr(decision, name, float("nan"))
    return response


def make_node_class():
    # Keep adapters/core importable on computers without ROS.
    from geometry_msgs.msg import Point
    from mge_interfaces.msg import TerrainMeta
    from mge_interfaces.srv import PlanRoute
    from nav_msgs.msg import OccupancyGrid
    from rclpy.callback_groups import ReentrantCallbackGroup
    from rclpy.node import Node
    from rclpy.qos import DurabilityPolicy, QoSProfile, ReliabilityPolicy
    from sensor_msgs.msg import Image

    class PlanningNode(Node):
        def __init__(self, **kwargs):
            super().__init__("planning_node", **kwargs)
            self.store = SnapshotStore()
            path = self.declare_parameter("profiles_file", "").value
            allow = self.declare_parameter("allow_illustrative_profiles", False).value
            self.contract_confirmed = self.declare_parameter("snapshot_contract_confirmed", False).value
            self.allow_continuous = self.declare_parameter("allow_continuous_starts", False).value
            self.limits = SearchLimits(
                max_labels=self.declare_parameter("max_labels", 200000).value,
                timeout_s=self.declare_parameter("search_timeout_s", 2.0).value,
            )
            try:
                self.profiles = load_profiles(path, allow)
                self.profile_error = ""
            except (OSError, ValueError, TypeError) as error:
                self.profiles = {}
                self.profile_error = str(error)
                self.get_logger().error(f"Profiles unavailable: {error}")
            self.group = ReentrantCallbackGroup()
            qos = QoSProfile(depth=1, reliability=ReliabilityPolicy.RELIABLE,
                             durability=DurabilityPolicy.TRANSIENT_LOCAL)
            self.subscriptions_owned = [
                self.create_subscription(TerrainMeta, "/mge/terrain/meta",
                                         self._meta, qos, callback_group=self.group),
            ]
            for layer in ("belief", "sigma"):
                self.subscriptions_owned.append(self.create_subscription(
                    Image, f"/mge/terrain/{layer}",
                    lambda message, name=layer: self._layer(name, message),
                    qos, callback_group=self.group))
            for kind in ("human", "rover", "drone"):
                self.subscriptions_owned.append(self.create_subscription(
                    OccupancyGrid, f"/mge/terrain/traversability/{kind}",
                    lambda message, name=kind: self._mask(name, message),
                    qos, callback_group=self.group))
            self.service = self.create_service(PlanRoute, "/mge/planner/plan_route",
                                               self._plan, callback_group=self.group)
            self.get_logger().info("PlanRoute ready; waits for explicit profiles and coherent public map batches")

        def _ingest(self, function, *args):
            try:
                function(*args)
            except (ValueError, TypeError, OverflowError) as error:
                self.store.invalidate()
                self.get_logger().warning(f"Rejected map input: {error}")

        def _meta(self, message):
            self._ingest(self.store.ingest_meta, message)

        def _layer(self, name, message):
            self._ingest(self.store.ingest_image, name, message)

        def _mask(self, name, message):
            self._ingest(self.store.ingest_mask, name, message)

        def _plan(self, message, response):
            try:
                request = request_from_ros(message)
            except (ValueError, TypeError, OverflowError) as error:
                return _failure(message, response, RouteStatus.ERROR, "INVALID_REQUEST", str(error))
            if not self.contract_confirmed:
                return _failure(message, response, RouteStatus.UNKNOWN, "SNAPSHOT_CONTRACT_UNCONFIRMED",
                                "Producer must confirm the unique-stamp metadata-first batch protocol")
            profile = self.profiles.get(request.agent_id)
            if profile is None:
                return _failure(message, response, RouteStatus.UNKNOWN, "PROFILE_NOT_READY",
                                self.profile_error or "An explicit approved or opted-in illustrative profile is required")
            try:
                with self.store.lock:
                    terrain, reason = self.store.snapshot(request.agent_kind)
                    key = self.store.key
                if terrain is None:
                    return _failure(message, response, RouteStatus.UNKNOWN, reason,
                                    "Waiting for matching public belief, sigma and traversability")
                result = plan_route(terrain=terrain, request=request, profile=profile, limits=self.limits,
                                    allow_continuous_start=self.allow_continuous)
            except (ValueError, TypeError, OverflowError) as error:
                return _failure(message, response, RouteStatus.ERROR, "INVALID_INPUT", str(error))
            if key != self.store.key:
                return _failure(message, response, RouteStatus.STALE_MAP, "SNAPSHOT_CHANGED_DURING_SEARCH",
                                "Map inputs changed or were rejected; recompute from the current pose")
            _failure(message, response, result.status, result.reason_code, result.detail)
            decision = response.decision
            decision.map_version_used = result.map_version_used
            decision.header.stamp.sec, decision.header.stamp.nanosec = key[2]
            if result.status != RouteStatus.FEASIBLE:
                return response
            decision.route_id = result.route_id
            for name in ("travel_time_s", "energy_est_wh", "oxygen_est_l", "min_clearance_m",
                         "reserve_time_s", "reserve_wh", "reserve_oxygen_l"):
                value = getattr(result, name)
                if value is not None and (not isfinite(value) or abs(value) > 3.4028234663852886e38):
                    return _failure(message, response, RouteStatus.ERROR, "SERIALIZATION_RANGE",
                                    "A result cannot be represented by the existing float32 wire fields")
                setattr(decision, name, float("nan") if value is None else float(value))
            decision.outbound_path = [Point(x=float(x), y=float(y), z=float(z)) for x, y, z in result.outbound_path]
            decision.return_path = [Point(x=float(x), y=float(y), z=float(z)) for x, y, z in result.return_path]
            return response

    return PlanningNode


def main(args=None):
    import rclpy
    from rclpy.executors import MultiThreadedExecutor

    rclpy.init(args=args)
    node = make_node_class()()
    executor = MultiThreadedExecutor(num_threads=4)
    executor.add_node(node)
    try:
        executor.spin()
    except KeyboardInterrupt:
        pass
    finally:
        executor.shutdown()
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
