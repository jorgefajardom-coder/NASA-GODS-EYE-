"""PlanRoute server. MissionManager, not this node, authorizes active routes."""

from math import isfinite

from .adapter import SnapshotStore, load_profiles, request_from_ros
from .core import RouteStatus, SearchLimits, plan_route
from .resource_costs import Activity
from mge_mission.models import estimate_activity, export_planner_profiles, load_profiles as load_scientific_profiles
from mge_mission.planning_context import (
    ContextStore, PlanningContextError, context_from_wire, profile_registry_sha256,
    scientific_model_sha256,
)


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
    from mge_interfaces.srv import PlanRoute, RegisterPlanningContext
    from nav_msgs.msg import OccupancyGrid
    from rclpy.callback_groups import MutuallyExclusiveCallbackGroup
    from rclpy.node import Node
    from rclpy.qos import DurabilityPolicy, QoSProfile, ReliabilityPolicy
    from sensor_msgs.msg import Image

    class PlanningNode(Node):
        def __init__(self, **kwargs):
            super().__init__("planning_node", **kwargs)
            self.store = SnapshotStore()
            path = self.declare_parameter("profiles_file", "").value
            allow = self.declare_parameter("allow_illustrative_profiles", False).value
            self.allow_legacy = self.declare_parameter("allow_legacy_cost_model", False).value
            self.scientific_path = self.declare_parameter("scientific_profiles_path", "").value
            self.contexts = ContextStore(self.declare_parameter("context_capacity", 4096).value)
            self.scientific_profiles, self.registry_hash = {}, ""
            self.kernel_hash = scientific_model_sha256()
            self.contract_confirmed = self.declare_parameter("snapshot_contract_confirmed", False).value
            self.allow_continuous = self.declare_parameter("allow_continuous_starts", False).value
            self.limits = SearchLimits(
                max_labels=self.declare_parameter("max_labels", 200000).value,
                timeout_s=self.declare_parameter("search_timeout_s", 2.0).value,
            )
            try:
                if self.allow_legacy:
                    self.profiles = load_profiles(path, allow)
                    self.get_logger().warning("LEGACY_PROJECTED_COST_MODEL explicitly enabled; not scientific cost agreement")
                else:
                    if not self.scientific_path:
                        raise ValueError("scientific_profiles_path is required; legacy costs have no automatic fallback")
                    self.scientific_profiles = load_scientific_profiles(self.scientific_path)
                    if not allow and any(p.approval_status != "approved" for p in self.scientific_profiles.values()):
                        raise ValueError("Scientific profiles require approval or explicit illustrative opt-in")
                    self.registry_hash = profile_registry_sha256(self.scientific_path)
                    from .core import MotionProfile
                    projected = export_planner_profiles(self.scientific_profiles)
                    self.profiles = {key: MotionProfile(**value) for key, value in projected["profiles"].items()}
                self.profile_error = ""
            except (OSError, ValueError, TypeError) as error:
                self.profiles = {}
                self.profile_error = str(error)
                self.get_logger().error(f"Profiles unavailable: {error}")
            # Ingestion already serializes on SnapshotStore.lock. Do not let
            # repeated layers occupy every executor worker waiting on that lock.
            # Search has its own group so new map versions can invalidate it.
            self.map_group = MutuallyExclusiveCallbackGroup()
            self.plan_group = MutuallyExclusiveCallbackGroup()
            qos = QoSProfile(depth=1, reliability=ReliabilityPolicy.RELIABLE,
                             durability=DurabilityPolicy.TRANSIENT_LOCAL)
            self.subscriptions_owned = [
                self.create_subscription(TerrainMeta, "/mge/terrain/meta",
                                         self._meta, qos, callback_group=self.map_group),
            ]
            for layer in ("belief", "sigma"):
                self.subscriptions_owned.append(self.create_subscription(
                    Image, f"/mge/terrain/{layer}",
                    lambda message, name=layer: self._layer(name, message),
                    qos, callback_group=self.map_group))
            for kind in ("human", "rover", "drone"):
                self.subscriptions_owned.append(self.create_subscription(
                    OccupancyGrid, f"/mge/terrain/traversability/{kind}",
                    lambda message, name=kind: self._mask(name, message),
                    qos, callback_group=self.map_group))
            self.service = self.create_service(PlanRoute, "/mge/planner/plan_route",
                                               self._plan, callback_group=self.plan_group)
            self.context_service = self.create_service(RegisterPlanningContext, "/mge/planner/register_context",
                                                        self._register_context, callback_group=self.plan_group)
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

        def _register_context(self, message, response):
            response.accepted, response.context_sha256 = False, ""
            try:
                if self.allow_legacy:
                    raise PlanningContextError("LEGACY_COST_MODEL", "Legacy search cannot acknowledge scientific context")
                context = context_from_wire(message)
                profile = self.scientific_profiles.get(context.agent_id)
                if profile is None:
                    raise PlanningContextError("PROFILE_NOT_READY", self.profile_error or "Scientific agent profile unavailable")
                if profile_registry_sha256(self.scientific_path) != self.registry_hash:
                    raise PlanningContextError("PROFILE_CHANGED", "Profile bytes changed after node initialization")
                if context.model_id != profile.model_id or context.profile_registry_sha256 != self.registry_hash:
                    raise PlanningContextError("COST_MODEL_MISMATCH", "Context model/profile identity differs from planner")
                if scientific_model_sha256() != self.kernel_hash or context.model_source_sha256 != self.kernel_hash:
                    raise PlanningContextError("COST_MODEL_MISMATCH", "Context scientific kernel differs from planner")
                for activity in context.activities:
                    estimate_activity(profile, activity.kind, activity.remaining_s)
                with self.store.lock:
                    meta = self.store.meta
                    if meta is not None and context.run_id != meta.run_id:
                        raise PlanningContextError("RUN_MISMATCH", "Context and current terrain belong to different runs")
                    if meta is not None and context.map_version != meta.map_version:
                        raise PlanningContextError("STALE_MAP", "Context does not match current terrain version")
                result = self.contexts.register(context)
                response.accepted, response.reason_code = result.accepted, result.reason_code
                response.context_sha256 = result.context_sha256
            except (OSError, ValueError, TypeError) as error:
                response.reason_code = getattr(error, "reason_code", "INVALID_COST_CONTEXT")
            return response

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
                    # The batch, not the store revision: masks of other agent kinds
                    # completing the same batch must not discard this search.
                    key = self.store.batch_key
                if terrain is None:
                    return _failure(message, response, RouteStatus.UNKNOWN, reason,
                                    "Waiting for matching public belief, sigma and traversability")
                if request.run_id != terrain.run_id:
                    return _failure(message, response, RouteStatus.UNKNOWN, "RUN_MISMATCH",
                                    "Request and public map belong to different runs")
                if request.map_version != terrain.map_version:
                    return _failure(message, response, RouteStatus.STALE_MAP, "MAP_VERSION_MISMATCH",
                                    "Request does not match the current public map version")
                if self.allow_legacy:
                    result = plan_route(terrain=terrain, request=request, profile=profile, limits=self.limits,
                                        allow_continuous_start=self.allow_continuous)
                else:
                    if profile_registry_sha256(self.scientific_path) != self.registry_hash:
                        raise PlanningContextError("PROFILE_CHANGED", "Profile bytes changed after node initialization")
                    if scientific_model_sha256() != self.kernel_hash:
                        raise PlanningContextError("MODEL_SOURCE_CHANGED", "Scientific kernel bytes changed after initialization")
                    science = self.scientific_profiles[request.agent_id]
                    context = self.contexts.resolve(message, expected_model_id=science.model_id,
                                                    expected_profile_registry_sha256=self.registry_hash,
                                                    expected_model_source_sha256=self.kernel_hash)
                    from .resource_costs import scientific_plan_route
                    result = scientific_plan_route(
                        terrain=terrain, request=request, motion_profile=profile, scientific_profile=science,
                        activities=tuple(Activity(a.activity_id, a.kind, a.remaining_s) for a in context.activities),
                        limits=self.limits, allow_continuous_start=self.allow_continuous)
            except PlanningContextError as error:
                status = RouteStatus.UNKNOWN if error.reason_code in {"COST_CONTEXT_REQUIRED", "PROFILE_CHANGED"} else RouteStatus.ERROR
                return _failure(message, response, status, error.reason_code, str(error))
            except (OSError, ValueError, TypeError, OverflowError) as error:
                return _failure(message, response, RouteStatus.ERROR, "INVALID_INPUT", str(error))
            if key != self.store.batch_key:
                return _failure(message, response, RouteStatus.STALE_MAP, "SNAPSHOT_CHANGED_DURING_SEARCH",
                                "Map inputs changed or were rejected; recompute from the current pose")
            if not self.allow_legacy:
                try:
                    if profile_registry_sha256(self.scientific_path) != self.registry_hash:
                        raise PlanningContextError("PROFILE_CHANGED", "Profile bytes changed during search")
                    if scientific_model_sha256() != self.kernel_hash:
                        raise PlanningContextError("MODEL_SOURCE_CHANGED", "Scientific kernel bytes changed during search")
                except (OSError, ValueError) as error:
                    return _failure(message, response, RouteStatus.ERROR,
                                    getattr(error, "reason_code", "PROFILE_CHANGED"), str(error))
            _failure(message, response, result.status, result.reason_code, result.detail)
            if self.allow_legacy:
                response.decision.detail = "LEGACY_PROJECTED_COST_MODEL; " + response.decision.detail
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
