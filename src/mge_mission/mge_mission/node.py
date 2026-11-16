"""ROS 2 mission authority; ROS imports are deferred for non-ROS tests."""

from copy import deepcopy
from functools import wraps
from math import isfinite
from pathlib import Path
from time import monotonic
from threading import RLock

from . import adapter
from .planning_context import (
    PlanningActivity, context_for_request, context_to_wire, profile_registry_sha256,
    scientific_model_sha256,
)


def _serialized(method):
    @wraps(method)
    def call(self, *args, **kwargs):
        lock = getattr(self, "_lock", None)
        if lock is None:
            return method(self, *args, **kwargs)
        with lock:
            return method(self, *args, **kwargs)
    return call


def create_node_class():
    """Return the real rclpy Node class after sourcing the ROS workspace."""
    from builtin_interfaces.msg import Time
    from geometry_msgs.msg import Point as WirePoint, PoseStamped
    from mge_interfaces.msg import AgentState, MissionEvent, MissionState, RouteDecision, TerrainMeta
    from mge_interfaces.srv import PlanRoute, RegisterPlanningContext, SetMissionGoal
    from nav_msgs.msg import Path as WirePath
    from rcl_interfaces.msg import ParameterDescriptor
    from rclpy.clock import Clock, ClockType
    from rclpy.node import Node
    from rclpy.qos import DurabilityPolicy, HistoryPolicy, QoSProfile, ReliabilityPolicy
    from rosgraph_msgs.msg import Clock as ClockMessage

    from .manager import MissionManager
    from .models import load_profiles
    from .types import MissionSpec, Point

    clock_qos = QoSProfile(
        history=HistoryPolicy.KEEP_LAST, depth=1,
        reliability=ReliabilityPolicy.BEST_EFFORT,
        durability=DurabilityPolicy.VOLATILE,
    )

    class MissionNode(Node):
        def __init__(self, *, parameter_overrides=None, manager=None):
            super().__init__("mission_node", parameter_overrides=parameter_overrides)
            self._lock = RLock()
            self._manager = manager
            self._configuration_error = ""
            self._clock_seen = self._clock_failed = self._destroying = False
            self._clock_s = 0.0
            self._clock_stamp = Time()
            self._waiting_meta = None
            self._terrain_signature, self._map_stamp = None, None
            self._map_stamp_key = None
            self._agent_wire, self._agent_stamps = {}, {}
            self._goal_answers = {}
            self._future = self._inflight_plan = self._request_wall_s = None
            self._inflight_request = self._inflight_context = None
            self._inflight_map_stamp = None
            self._last_path_key = None
            for name, default in {
                "run_id": "", "profiles_path": "", "mission_path": "",
                "model_agreement_confirmed": False, "approved_model_id": "",
                "allow_illustrative": False, "return_tolerance_m": -1.0,
                "primary_service_time_s": -1.0, "primary_service_activity": "",
                "planner_timeout_s": 5.0,
            }.items():
                self.declare_parameter(name, default)
            self.declare_parameter("base_enu_m", [], descriptor=ParameterDescriptor(dynamic_typing=True))
            if not self.has_parameter("use_sim_time"):
                self.declare_parameter("use_sim_time", True)
            self._use_sim_time = self.get_parameter("use_sim_time").value is True
            if manager is not None:
                self._run_id, self._profiles = manager.snapshot().run_id, dict(manager.profiles)
            else:
                self._run_id, self._profiles = self.get_parameter("run_id").value, {}
                try:
                    config = {}
                    mission_path = self.get_parameter("mission_path").value
                    if mission_path:
                        import yaml
                        with Path(mission_path).open(encoding="utf-8") as handle:
                            config = yaml.safe_load(handle)
                        if not isinstance(config, dict) or config.get("frame_id", "map") != "map":
                            raise ValueError("mission configuration must be an object in frame map")
                        status = config.get("status")
                        if status == "illustrative" and not self.get_parameter("allow_illustrative").value:
                            raise ValueError("illustrative mission configuration requires allow_illustrative=true")
                        if status not in {"approved", "illustrative"}:
                            raise ValueError("mission configuration is not approved or explicitly illustrative")
                        if "mission" in config:
                            config = config["mission"]
                            if not isinstance(config, dict):
                                raise ValueError("nested mission configuration must be an object")
                    if not isinstance(self._run_id, str) or not self._run_id.strip():
                        raise ValueError("run_id must be explicitly configured")
                    profiles_path = self.get_parameter("profiles_path").value
                    if not profiles_path:
                        raise ValueError("profiles_path must be explicitly configured")
                    self._profiles = load_profiles(profiles_path)
                    base = self.get_parameter("base_enu_m").value
                    if not base:
                        base = config.get("base_enu_m")
                    if not isinstance(base, (list, tuple)) or len(base) != 3:
                        raise ValueError("base_enu_m requires three explicit ENU coordinates")
                    base = Point(*(adapter.finite_number(value, "base_enu_m") for value in base))
                    tolerance = self.get_parameter("return_tolerance_m").value
                    tolerance = config.get("return_tolerance_m") if tolerance < 0 else tolerance
                    tolerance = adapter.finite_number(tolerance, "return_tolerance_m", nonnegative=True)
                    service_time = self.get_parameter("primary_service_time_s").value
                    service_time = config.get("primary_service_time_s") if service_time < 0 else service_time
                    service_time = adapter.finite_number(service_time, "primary_service_time_s", nonnegative=True)
                    activity = self.get_parameter("primary_service_activity").value or config.get("primary_activity")
                    if not isinstance(activity, str) or not activity:
                        raise ValueError("primary_service_activity must be explicitly configured")
                    spec = MissionSpec(self._run_id, base, tolerance, service_time, activity)
                    self._manager = MissionManager.from_spec(
                        spec, self._profiles,
                        allow_illustrative=self.get_parameter("allow_illustrative").value,
                        planner_model_agreed=self.get_parameter("model_agreement_confirmed").value,
                        approved_model_id=self.get_parameter("approved_model_id").value or None,
                    )
                except Exception as exc:
                    self._configuration_error, self._manager = str(exc), None
                    self.get_logger().error(f"Mission is unavailable: {exc}")
            timeout = self.get_parameter("planner_timeout_s").value
            if isinstance(timeout, bool) or not isinstance(timeout, (int, float)) or not isfinite(timeout) or timeout <= 0:
                self.destroy_node()
                raise ValueError("planner_timeout_s must be finite and positive")
            self._planner_timeout_s = float(timeout)
            self._profiles_path = self.get_parameter("profiles_path").value
            self._kernel_hash = scientific_model_sha256()
            try:
                if not self._profiles_path:
                    raise ValueError("profiles_path is required to bind the scientific profile registry")
                registered_profiles = load_profiles(self._profiles_path)
                if registered_profiles != self._profiles:
                    raise ValueError("Configured profile registry differs from the mission manager profiles")
                self._registry_hash = profile_registry_sha256(self._profiles_path)
                self._context_configuration_error = ""
            except (OSError, ValueError, TypeError) as exc:
                self._registry_hash = ""
                self._context_configuration_error = str(exc)
            reliable = QoSProfile(history=HistoryPolicy.KEEP_LAST, depth=10,
                reliability=ReliabilityPolicy.RELIABLE, durability=DurabilityPolicy.VOLATILE)
            retained = QoSProfile(history=HistoryPolicy.KEEP_LAST, depth=1,
                reliability=ReliabilityPolicy.RELIABLE, durability=DurabilityPolicy.TRANSIENT_LOCAL)
            self._state_publisher = self.create_publisher(MissionState, "/mge/mission/state", retained)
            self._event_publisher = self.create_publisher(MissionEvent, "/mge/mission/events", reliable)
            self._path_publisher = self.create_publisher(WirePath, "/mge/planner/active_path", retained)
            self._planner_client = self.create_client(PlanRoute, "/mge/planner/plan_route")
            self._context_client = self.create_client(RegisterPlanningContext, "/mge/planner/register_context")
            self._goal_service = self.create_service(SetMissionGoal, "/mge/mission/set_goal", self._set_goal)
            self.create_subscription(ClockMessage, "/clock", self._on_clock, clock_qos)
            self.create_subscription(TerrainMeta, "/mge/terrain/meta", self._on_meta, retained)
            self._agent_subscriptions = [self.create_subscription(
                AgentState, f"/mge/agents/{agent_id}/state",
                lambda message, expected=agent_id: self._on_agent(message, expected), reliable,
            ) for agent_id in self._profiles]
            self._steady_clock = Clock(clock_type=ClockType.STEADY_TIME)
            self._timer = self.create_timer(0.05, self._poll, clock=self._steady_clock)
            if not self._use_sim_time:
                self.get_logger().error("Mission control requires use_sim_time=true and a received /clock")

        def _ready_clock(self):
            return self._use_sim_time and self._clock_seen and not self._clock_failed

        @_serialized
        def _on_clock(self, message):
            try:
                now = adapter.stamp_seconds(message.clock)
            except ValueError as exc:
                self.get_logger().warning(str(exc))
                return
            if self._clock_seen and now < self._clock_s:
                self._clock_failed = True
                if self._manager is not None:
                    self._manager.block_runtime("CLOCK_RESET", "Simulation clock moved backwards; start a new run.")
                    self._publish(force=True)
                self._publish_empty_path()
                self.get_logger().error("Simulation clock moved backwards; restart with a new run ID")
                return
            self._clock_s, self._clock_stamp, self._clock_seen = now, deepcopy(message.clock), True
            if self._ready_clock() and self._waiting_meta is not None:
                pending, self._waiting_meta = self._waiting_meta, None
                self._on_meta(pending)

        @_serialized
        def _on_meta(self, message):
            if self._manager is None:
                return
            if not self._ready_clock():
                self._waiting_meta = deepcopy(message)
                return
            try:
                stamp = adapter.validate_header(message, self._run_id, self._clock_s)
                if type(message.map_version) is not int or not 0 <= message.map_version <= 0xFFFFFFFF:
                    raise ValueError("invalid map version")
                if not message.dataset_id or message.rows == 0 or message.cols == 0:
                    raise ValueError("terrain metadata requires dataset and positive dimensions")
                if adapter.finite_number(message.resolution_m, "resolution_m", nonnegative=True) <= 0:
                    raise ValueError("resolution_m must be positive")
                for name in ("origin_x_m", "origin_y_m"):
                    adapter.finite_number(getattr(message, name), name)
                signature = tuple(getattr(message, name) for name in (
                    "dataset_id", "origin_x_m", "origin_y_m", "resolution_m", "rows", "cols",
                    "crs", "vertical_datum", "checksum_sha256"))
                if self._terrain_signature is not None and signature != self._terrain_signature:
                    raise ValueError("terrain geometry or source identity changed within the run")
                if self._map_stamp is not None and stamp < self._map_stamp:
                    raise ValueError("terrain metadata is older than the accepted map context")
                stamp_key = (message.header.stamp.sec, message.header.stamp.nanosec)
                current_version = self._manager.snapshot().map_version
                if self._map_stamp_key is not None:
                    if current_version == message.map_version and stamp_key != self._map_stamp_key:
                        raise ValueError("terrain batch timestamp changed without a new map version")
                    if current_version != message.map_version and stamp_key == self._map_stamp_key:
                        raise ValueError("terrain batch timestamp was reused for another map version")
                if self._manager.update_map(message.run_id, message.map_version, stamp):
                    self._terrain_signature, self._map_stamp = signature, stamp
                    self._map_stamp_key = stamp_key
                self._publish()
            except (TypeError, ValueError) as exc:
                self.get_logger().warning(f"Ignored terrain metadata: {exc}")

        @_serialized
        def _on_agent(self, message, expected_id):
            if self._manager is None or not self._ready_clock():
                return
            try:
                if message.agent_id != expected_id:
                    raise ValueError("agent ID does not match subscribed topic")
                state = adapter.agent_from_wire(message, self._run_id, self._clock_s)
                previous_stamp = self._agent_stamps.get(expected_id)
                if previous_stamp is not None and state.timestamp_sim_s < previous_stamp:
                    raise ValueError("agent state is older than the last accepted state")
                if self._manager.update_agent(state):
                    self._agent_wire[expected_id] = deepcopy(message)
                    self._agent_stamps[expected_id] = state.timestamp_sim_s
                    self._publish()
            except (TypeError, ValueError) as exc:
                self.get_logger().warning(f"Ignored agent state: {exc}")

        def _reject_goal(self, request, response, reason, detail):
            response.accepted, response.request_id, response.run_id = False, request.request_id, self._run_id
            response.mission_state = self._manager.snapshot().mission_state if self._manager else "BLOCKED"
            response.reason_code, response.detail = reason, detail
            return response

        @_serialized
        def _set_goal(self, request, response):
            # Cache boundary rejections too. Retrying the same key after clock
            # or configuration availability changes must return its first answer.
            payload = adapter.goal_fingerprint(request, self._run_id)
            cached = self._goal_answers.get(request.request_id) if request.request_id else None
            fields = ("accepted", "request_id", "run_id", "mission_state", "reason_code", "detail")
            if cached is not None:
                if payload != cached[0]:
                    return self._reject_goal(request, response, "REQUEST_ID_CONFLICT", "The request ID already identifies another payload.")
                for name, value in zip(fields, cached[1]):
                    setattr(response, name, value)
                return response
            response = self._handle_goal(request, response)
            if request.request_id:
                self._goal_answers[request.request_id] = (payload, tuple(getattr(response, name) for name in fields))
            return response

        def _handle_goal(self, request, response):
            if self._manager is None:
                return self._reject_goal(request, response, "CONFIG_NOT_READY", self._configuration_error)
            if not self._ready_clock():
                return self._reject_goal(request, response, "CLOCK_NOT_READY", "A monotonic simulation clock is required.")
            try:
                profile = self._profiles.get(request.primary_agent_id)
                if profile is None:
                    raise ValueError("primary agent is not configured")
                result = self._manager.set_goal(adapter.goal_from_wire(request, self._run_id, primary_kind=profile.kind))
                for name in ("accepted", "request_id", "run_id", "mission_state", "reason_code", "detail"):
                    setattr(response, name, getattr(result, name))
                self._publish()
                self._dispatch_plan()
                return response
            except (ValueError, TypeError) as exc:
                return self._reject_goal(request, response, "INVALID_GOAL", str(exc))

        def _fail_if_current(self, request_id, reason, detail):
            current = self._manager.pending_plan()
            if current is not None and current.request_id == request_id:
                self._manager.fail_pending_plan(reason, detail)

        def _dispatch_plan(self):
            if self._manager is None or not self._ready_clock() or self._future is not None:
                return
            plan = self._manager.pending_plan()
            if plan is None:
                return
            if not self._planner_client.service_is_ready():
                self._manager.fail_pending_plan("PLANNER_UNAVAILABLE", "The ROS planner service is unavailable.")
                self._publish()
                return
            if self._context_configuration_error or not self._context_client.service_is_ready():
                self._manager.fail_pending_plan("COST_CONTEXT_UNAVAILABLE",
                    self._context_configuration_error or "Scientific context service is unavailable")
                self._publish()
                return
            try:
                request = adapter.plan_to_wire(plan, PlanRoute.Request(), WirePoint)
                if profile_registry_sha256(self._profiles_path) != self._registry_hash:
                    raise ValueError("Scientific profile registry changed after initialization")
                if scientific_model_sha256() != self._kernel_hash:
                    raise ValueError("Scientific model source changed after initialization")
                activities = (() if request.service_time_s == 0 else
                    (PlanningActivity(plan.request_id + ":goal-service", plan.service_activity,
                                      float(request.service_time_s)),))
                context = context_for_request(request, self._profiles[plan.agent_id].model_id,
                                              self._registry_hash, activities, model_source_sha256=self._kernel_hash)
                self._inflight_plan, self._request_wall_s = plan, monotonic()
                self._inflight_request, self._inflight_context = request, context
                if self._map_stamp_key is None:
                    raise ValueError("no explicit terrain batch timestamp is available")
                self._inflight_map_stamp = self._map_stamp_key
                registration = context_to_wire(context, RegisterPlanningContext.Request())
                self._future = self._context_client.call_async(registration)
                self._future.add_done_callback(self._on_context_result)
            except (OSError, ValueError, TypeError, RuntimeError) as exc:
                self._future = self._inflight_plan = None
                self._manager.fail_pending_plan("PLANNER_ERROR", str(exc))
                self._publish()

        @_serialized
        def _on_context_result(self, future):
            if self._destroying or future is not self._future:
                return
            plan = self._inflight_plan
            try:
                if not self._ready_clock():
                    return
                if self._manager.pending_plan() != plan or self._map_stamp_key != self._inflight_map_stamp:
                    self._future = self._inflight_plan = None
                    self._inflight_request = self._inflight_context = None
                    return  # A newer request/map must acquire its own immutable context.
                result = future.result()
                if result is None or result.accepted is not True:
                    raise ValueError("Context registration rejected: " + str(getattr(result, "reason_code", "NO_RESPONSE")))
                if result.context_sha256 != self._inflight_context.digest:
                    raise ValueError("Context acknowledgement does not identify the dispatched schedule")
                if profile_registry_sha256(self._profiles_path) != self._registry_hash:
                    raise ValueError("Scientific profile registry changed while context registration was pending")
                if scientific_model_sha256() != self._kernel_hash:
                    raise ValueError("Scientific model source changed while context registration was pending")
                if self._manager.refresh_pending_resources():
                    self._future = self._inflight_plan = None
                    self._inflight_request = self._inflight_context = None
                    self._publish()
                    return
                self._future = self._planner_client.call_async(self._inflight_request)
                self._future.add_done_callback(self._on_plan_result)
            except Exception as exc:
                self._future = self._inflight_plan = None
                self._inflight_request = self._inflight_context = None
                self._fail_if_current(plan.request_id, "COST_CONTEXT_REJECTED", str(exc))
                self._publish()

        @_serialized
        def _on_plan_result(self, future):
            if self._destroying or future is not self._future:
                return
            plan = self._inflight_plan
            map_stamp = self._inflight_map_stamp
            self._future = self._inflight_plan = None
            self._inflight_request = self._inflight_context = None
            try:
                if not self._ready_clock():
                    return
                result = future.result()
                if result is None:
                    raise ValueError("planner returned no response")
                decision = adapter.decision_from_wire(result.decision, self._run_id, self._clock_s,
                                                     kind=adapter.kind_from_wire(plan.agent_kind))
                stamp_key = (result.decision.header.stamp.sec, result.decision.header.stamp.nanosec)
                if decision.status == "FEASIBLE" and stamp_key != map_stamp:
                    raise ValueError("planner response stamp does not match the dispatched terrain batch")
                if decision.request_id != plan.request_id:
                    raise ValueError("planner request ID does not match the dispatched request")
                self._manager.apply_plan(decision)
            except Exception as exc:
                self._fail_if_current(plan.request_id, "INVALID_PLANNER_RESPONSE", str(exc))
                self.get_logger().warning(f"Rejected planner response: {exc}")
            finally:
                self._publish()

        @_serialized
        def _poll(self):
            if self._manager is None or not self._ready_clock():
                return
            if self._future is not None and monotonic() - self._request_wall_s > self._planner_timeout_s:
                future, plan = self._future, self._inflight_plan
                self._future = self._inflight_plan = None
                future.cancel()
                self._fail_if_current(plan.request_id, "PLANNER_TIMEOUT", "Planner exceeded its configured wall-clock timeout.")
                self._publish()
            self._dispatch_plan()

        def _stamp_for(self, seconds):
            if seconds is None:
                return deepcopy(self._clock_stamp)
            total_ns = round(adapter.finite_number(seconds, "timestamp_sim_s", nonnegative=True) * 1_000_000_000)
            return Time(sec=total_ns // 1_000_000_000, nanosec=total_ns % 1_000_000_000)

        def _publish_empty_path(self):
            if hasattr(self, "_path_publisher"):
                self._path_publisher.publish(adapter.active_path_to_wire(None, WirePath(), self._clock_stamp, PoseStamped))
            self._last_path_key = None

        def _publish(self, *, force=False):
            if self._manager is None or not (self._ready_clock() or (force and self._clock_seen and self._use_sim_time)):
                return
            snapshot = self._manager.snapshot()
            stamp = self._stamp_for(snapshot.timestamp_sim_s)
            self._state_publisher.publish(adapter.snapshot_to_wire(
                snapshot, MissionState(), stamp, WirePoint, RouteDecision, self._agent_wire))
            for event in self._manager.drain_events():
                self._event_publisher.publish(adapter.event_to_wire(event, MissionEvent(), self._stamp_for(event.timestamp_sim_s)))
            key = (snapshot.route_id, snapshot.map_version)
            if key != self._last_path_key:
                self._path_publisher.publish(adapter.active_path_to_wire(snapshot.active_route, WirePath(), stamp, PoseStamped))
                self._last_path_key = key

        @_serialized
        def destroy_node(self):
            self._destroying = True
            future = getattr(self, "_future", None)
            if future is not None:
                self._future = None
                future.cancel()
            return super().destroy_node()

    return MissionNode


def main(args=None):
    import rclpy
    rclpy.init(args=args)
    node = None
    try:
        node = create_node_class()()
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        if node is not None:
            node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
