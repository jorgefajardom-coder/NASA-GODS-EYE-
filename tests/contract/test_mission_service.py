"""Real ROS service/topic smoke tests with an explicitly controlled planner.

These verify the adapter, not an integrated simulator, real terrain or a mission.
Run on Jazzy after colcon build and sourcing install/setup.bash.
"""

from pathlib import Path
from time import monotonic

import pytest

rclpy = pytest.importorskip("rclpy", reason="Requires ROS 2 Jazzy")
pytest.importorskip("mge_interfaces.msg", reason="Requires built mission interfaces")

from builtin_interfaces.msg import Time
from geometry_msgs.msg import Point as WirePoint
from mge_interfaces.msg import AgentState, MissionEvent, MissionState, RouteDecision, TerrainMeta
from mge_interfaces.srv import PlanRoute, SetMissionGoal
from nav_msgs.msg import Path as WirePath
from rclpy.executors import SingleThreadedExecutor
from rclpy.node import Node
from rclpy.parameter import Parameter
from rclpy.qos import DurabilityPolicy, HistoryPolicy, QoSProfile, ReliabilityPolicy
from rosgraph_msgs.msg import Clock

from mge_mission import adapter
from mge_mission.manager import MissionManager
from mge_mission.models import MODEL_ID, estimate_activity, estimate_segment, load_profiles
from mge_mission.node import create_node_class
from mge_mission.types import Point, RouteDecision as CoreDecision


CLOCK_QOS = QoSProfile(
    history=HistoryPolicy.KEEP_LAST, depth=1,
    reliability=ReliabilityPolicy.BEST_EFFORT,
    durability=DurabilityPolicy.VOLATILE,
)


def spin_until(executor, predicate, timeout=5.0, tick=None):
    end = monotonic() + timeout
    while monotonic() < end:
        if predicate():
            return
        if tick is not None:
            tick()
        executor.spin_once(timeout_sec=0.02)
    assert predicate(), "ROS condition did not become true before the timeout"


@pytest.fixture
def graph():
    rclpy.init()
    profiles = load_profiles(Path(__file__).resolve().parents[2] / "config/scenario_demo.yaml")
    manager = MissionManager(
        "contract-run", profiles, Point(0.0, 0.0, 0.0), 0.5,
        allow_illustrative=True, primary_service_time_s=60.0,
        primary_service_activity="sample", planner_model_agreed=True,
        approved_model_id=MODEL_ID,
    )
    mission = create_node_class()(
        parameter_overrides=[Parameter("use_sim_time", value=True)], manager=manager)
    peer = Node("controlled_mission_contract_peer")
    executor = SingleThreadedExecutor()
    executor.add_node(peer)
    executor.add_node(mission)
    reliable = QoSProfile(depth=10, reliability=ReliabilityPolicy.RELIABLE)
    retained = QoSProfile(depth=10, reliability=ReliabilityPolicy.RELIABLE,
                          durability=DurabilityPolicy.TRANSIENT_LOCAL)
    clock = peer.create_publisher(Clock, "/clock", CLOCK_QOS)
    meta = peer.create_publisher(TerrainMeta, "/mge/terrain/meta", retained)
    agent = peer.create_publisher(AgentState, "/mge/agents/human_1/state", reliable)
    states, events, paths, requests = [], [], [], []
    peer.create_subscription(MissionState, "/mge/mission/state", states.append, retained)
    peer.create_subscription(MissionEvent, "/mge/mission/events", events.append, reliable)
    peer.create_subscription(WirePath, "/mge/planner/active_path", paths.append, retained)
    behavior = {"value": "FEASIBLE"}

    def planner(request, response):
        requests.append(request)
        output = response.decision
        if behavior["value"] in {"UNKNOWN", "NO_PATH", "INSUFFICIENT_BUDGET"}:
            # Matches failure representation from published planner 34c515b6:
            # no loaded snapshot may mean stamp zero, and all costs are NaN.
            output.header.frame_id, output.header.stamp = "map", Time()
            output.run_id, output.request_id = request.run_id, request.request_id
            output.agent_id, output.mode = request.agent_id, request.mode
            output.map_version_used, output.status = request.map_version, behavior["value"]
            output.reason_code = {"UNKNOWN": "MAP_NOT_VERIFIED", "NO_PATH": "NO_ADMISSIBLE_PATH",
                                  "INSUFFICIENT_BUDGET": "BUDGET_EXCEEDED"}[behavior["value"]]
            output.detail = "Controlled planner rejection."
            for name in ("travel_time_s", "energy_est_wh", "oxygen_est_l", "min_clearance_m",
                         "reserve_time_s", "reserve_wh", "reserve_oxygen_l"):
                setattr(output, name, float("nan"))
            return response
        profile = profiles[request.agent_id]
        start, goal, home = (Point(*adapter.point_values(getattr(request, name)))
                             for name in ("start", "goal", "return_to"))
        outbound, back = (start, goal), (goal, home) if request.require_return else ()
        costs = [estimate_segment(profile, a.coordinates(), b.coordinates())
                 for route in (outbound, back) for a, b in zip(route, route[1:])]
        costs.append(estimate_activity(profile, "sample", request.service_time_s))
        duration = sum(cost.time_s for cost in costs)
        energy = sum(cost.energy_wh for cost in costs)
        oxygen = sum(cost.oxygen_l for cost in costs)
        decision = CoreDecision(
            request.run_id, request.request_id, f"route-{len(requests)}", request.agent_id,
            request.mode, request.map_version - (1 if behavior["value"] == "STALE" else 0),
            "FEASIBLE", outbound_path=outbound, return_path=back,
            travel_time_s=duration, energy_est_wh=energy, oxygen_est_l=oxygen,
            min_clearance_m=1.0, reserve_time_s=request.time_budget_s - duration,
            reserve_wh=request.energy_budget_wh - energy,
            reserve_oxygen_l=request.oxygen_budget_l - oxygen,
        )
        response.decision = adapter.decision_to_wire(decision, RouteDecision(), Time(sec=9 + request.map_version), WirePoint)
        if behavior["value"] == "WRONG_RUN":
            response.decision.run_id = "another-run"
        elif behavior["value"] == "FUTURE":
            response.decision.header.stamp.sec = 1000
        elif behavior["value"] == "WRONG_FRAME":
            response.decision.header.frame_id = "odom"
        elif behavior["value"] == "WRONG_STAMP":
            response.decision.header.stamp.sec += 1
        return response

    service = peer.create_service(PlanRoute, "/mge/planner/plan_route", planner)
    goal_client = peer.create_client(SetMissionGoal, "/mge/mission/set_goal")

    def send_inputs(version=1, agent_stamp=None):
        map_stamp = 9 + version
        agent_stamp = map_stamp if agent_stamp is None else agent_stamp
        clock.publish(Clock(clock=Time(sec=max(map_stamp, agent_stamp))))
        terrain = TerrainMeta()
        terrain.header.frame_id, terrain.header.stamp = "map", Time(sec=map_stamp)
        terrain.run_id, terrain.dataset_id, terrain.map_version = "contract-run", "synthetic-contract", version
        terrain.rows, terrain.cols, terrain.resolution_m = 20, 20, 1.0
        meta.publish(terrain)
        state = AgentState()
        state.header.frame_id, state.header.stamp = "map", Time(sec=agent_stamp)
        state.run_id, state.agent_id, state.agent_kind = "contract-run", "human_1", "HUMAN"
        state.pose.orientation.w, state.mode, state.confidence = 1.0, "IDLE", 1.0
        state.time_remaining_s, state.energy_remaining_wh, state.oxygen_remaining_l = 3600.0, 600.0, 150.0
        agent.publish(state)

    def goal_request():
        request = SetMissionGoal.Request()
        request.request_id, request.run_id, request.primary_agent_id = "goal-1", "", "human_1"
        request.base, request.goal, request.mode = WirePoint(), WirePoint(x=10.0), "FAST"
        request.time_budget_s, request.energy_budget_wh, request.oxygen_budget_l = 3600.0, 600.0, 150.0
        request.reserve_time_s, request.reserve_wh, request.reserve_oxygen_l = 360.0, 60.0, 15.0
        return request

    context = dict(mission=mission, peer=peer, executor=executor, manager=manager,
                   states=states, events=events, paths=paths, requests=requests,
                   behavior=behavior, client=goal_client, send_inputs=send_inputs,
                   goal_request=goal_request, planner_service=service, clock=clock)
    try:
        spin_until(executor, lambda: goal_client.service_is_ready() and mission._planner_client.service_is_ready())
        yield context
    finally:
        executor.remove_node(mission)
        executor.remove_node(peer)
        mission.destroy_node()
        peer.destroy_node()
        executor.shutdown()
        rclpy.shutdown()


def test_goal_requires_actual_simulation_clock(graph):
    future = graph["client"].call_async(graph["goal_request"]())
    spin_until(graph["executor"], future.done)
    assert future.result().accepted is False
    assert future.result().reason_code == "CLOCK_NOT_READY"
    assert not graph["requests"]
    spin_until(graph["executor"], lambda: graph["manager"].snapshot().agents,
               tick=graph["send_inputs"])
    duplicate = graph["client"].call_async(graph["goal_request"]())
    spin_until(graph["executor"], duplicate.done)
    assert duplicate.result().reason_code == "CLOCK_NOT_READY"
    assert not graph["requests"]


def test_ros_goal_plan_topics_idempotency_and_map_invalidation(graph):
    manager, executor = graph["manager"], graph["executor"]
    spin_until(executor, lambda: manager.snapshot().map_version == 1 and len(manager.snapshot().agents) == 1,
               tick=graph["send_inputs"])
    future = graph["client"].call_async(graph["goal_request"]())
    spin_until(executor, future.done)
    assert future.result().accepted is True and future.result().run_id == "contract-run"
    spin_until(executor, lambda: any(state.route_id for state in graph["states"]) and any(path.poses for path in graph["paths"]))
    assert manager.snapshot().mission_state == "READY"
    assert manager.snapshot().mission_success is False
    assert all(state.mission_state != "COMPLETE" for state in graph["states"])
    assert graph["requests"][0].agent_kind == "HUMAN"
    assert graph["requests"][0].service_time_s == 60.0
    count = len(graph["requests"])
    duplicate = graph["client"].call_async(graph["goal_request"]())
    spin_until(executor, duplicate.done)
    assert duplicate.result().accepted is True
    assert duplicate.result().mission_state == future.result().mission_state
    assert len(graph["requests"]) == count
    changed = graph["goal_request"]()
    changed.goal.x = 11.0
    conflict = graph["client"].call_async(changed)
    spin_until(executor, conflict.done)
    assert conflict.result().accepted is False
    assert conflict.result().reason_code == "REQUEST_ID_CONFLICT"
    assert len(graph["requests"]) == count
    graph["behavior"]["value"] = "UNKNOWN"
    paths_before = len(graph["paths"])
    spin_until(executor, lambda: manager.snapshot().map_version == 2 and manager.snapshot().mission_state == "BLOCKED",
               tick=lambda: graph["send_inputs"](2))
    spin_until(executor, lambda: any(not path.poses for path in graph["paths"][paths_before:]))
    assert not manager.snapshot().route_id
    assert manager.snapshot().reason_code == "MAP_NOT_VERIFIED"
    spin_until(executor, lambda: any(event.event_type == "ROUTE_INVALIDATED" for event in graph["events"]))
    seq = [event.seq for event in graph["events"]]
    assert seq == sorted(set(seq))


def test_stale_planner_response_never_publishes_active_route(graph):
    graph["behavior"]["value"] = "STALE"
    manager, executor = graph["manager"], graph["executor"]
    spin_until(executor, lambda: manager.snapshot().map_version == 1 and manager.snapshot().agents,
               tick=graph["send_inputs"])
    future = graph["client"].call_async(graph["goal_request"]())
    spin_until(executor, lambda: future.done() and manager.snapshot().mission_state == "BLOCKED")
    assert manager.snapshot().reason_code == "STALE_MAP"
    assert not manager.snapshot().route_id
    assert not any(path.poses for path in graph["paths"])


@pytest.mark.parametrize("status,reason", [("UNKNOWN", "MAP_NOT_VERIFIED"),
                                          ("NO_PATH", "NO_ADMISSIBLE_PATH"),
                                          ("INSUFFICIENT_BUDGET", "BUDGET_EXCEEDED")])
def test_actual_service_preserves_planner_failure_reason_with_nan_metrics(graph, status, reason):
    graph["behavior"]["value"] = status
    manager, executor = graph["manager"], graph["executor"]
    spin_until(executor, lambda: manager.snapshot().map_version == 1 and manager.snapshot().agents,
               tick=graph["send_inputs"])
    future = graph["client"].call_async(graph["goal_request"]())
    spin_until(executor, lambda: future.done() and manager.snapshot().mission_state == "BLOCKED")
    assert future.result().accepted is True
    assert manager.snapshot().reason_code == reason
    assert manager.snapshot().active_route is None
    assert not any(path.poses for path in graph["paths"])
    spin_until(executor, lambda: any(event.reason_code == reason for event in graph["events"]))


def test_map_batch_response_accepts_newer_current_agent_timestamp(graph):
    manager, executor = graph["manager"], graph["executor"]
    spin_until(executor, lambda: manager.snapshot().map_version == 1 and manager.snapshot().agents,
               tick=lambda: graph["send_inputs"](agent_stamp=12))
    assert manager.snapshot().agents[0].timestamp_sim_s == 12.0
    assert graph["mission"]._map_stamp_key == (10, 0)
    future = graph["client"].call_async(graph["goal_request"]())
    spin_until(executor, lambda: future.done() and manager.snapshot().mission_state == "READY")
    assert manager.snapshot().route_id
    assert not manager.snapshot().mission_success


@pytest.mark.parametrize("behavior", ["WRONG_RUN", "FUTURE", "WRONG_FRAME", "WRONG_STAMP"])
def test_actual_service_rejects_invalid_candidate_envelope(graph, behavior):
    graph["behavior"]["value"] = behavior
    manager, executor = graph["manager"], graph["executor"]
    spin_until(executor, lambda: manager.snapshot().map_version == 1 and manager.snapshot().agents,
               tick=lambda: graph["send_inputs"](agent_stamp=12))
    future = graph["client"].call_async(graph["goal_request"]())
    spin_until(executor, lambda: future.done() and manager.snapshot().mission_state == "BLOCKED")
    assert manager.snapshot().reason_code == "INVALID_PLANNER_RESPONSE"
    assert manager.snapshot().active_route is None
    assert not any(path.poses for path in graph["paths"])


def test_clock_reset_clears_retained_route_and_blocks_further_commands(graph):
    manager, executor = graph["manager"], graph["executor"]
    spin_until(executor, lambda: manager.snapshot().map_version == 1 and manager.snapshot().agents,
               tick=graph["send_inputs"])
    future = graph["client"].call_async(graph["goal_request"]())
    spin_until(executor, lambda: future.done() and any(state.route_id for state in graph["states"]))
    graph["clock"].publish(Clock(clock=Time(sec=9)))
    spin_until(executor, lambda: any(state.reason_code == "CLOCK_RESET" for state in graph["states"]))
    blocked = next(state for state in graph["states"] if state.reason_code == "CLOCK_RESET")
    assert blocked.mission_state == "BLOCKED" and blocked.route_id == ""
    assert blocked.header.stamp.sec == 10
    assert manager.snapshot().active_route is None
    spin_until(executor, lambda: graph["paths"] and not graph["paths"][-1].poses)
    duplicate = graph["client"].call_async(graph["goal_request"]())
    spin_until(executor, duplicate.done)
    assert duplicate.result().accepted is True  # Idempotent answer; no command is executed again.
    assert manager.snapshot().mission_state == "BLOCKED"
    fresh = graph["goal_request"]()
    fresh.request_id = "after-clock-reset"
    rejected = graph["client"].call_async(fresh)
    spin_until(executor, rejected.done)
    assert rejected.result().reason_code == "CLOCK_NOT_READY"


def test_missing_configuration_stays_unavailable():
    rclpy.init()
    node = create_node_class()(parameter_overrides=[Parameter("use_sim_time", value=True)])
    try:
        response = node._set_goal(SetMissionGoal.Request(), SetMissionGoal.Response())
        assert response.accepted is False and response.reason_code == "CONFIG_NOT_READY"
        assert node._manager is None
    finally:
        node.destroy_node()
        rclpy.shutdown()


@pytest.mark.parametrize("allow", [False, True])
def test_illustrative_runtime_configuration_requires_explicit_opt_in(allow):
    rclpy.init()
    path = str(Path(__file__).resolve().parents[2] / "config/scenario_demo.yaml")
    node = create_node_class()(parameter_overrides=[
        Parameter("use_sim_time", value=True), Parameter("run_id", value="configuration-test"),
        Parameter("profiles_path", value=path), Parameter("mission_path", value=path),
        Parameter("allow_illustrative", value=allow),
    ])
    try:
        if allow:
            assert node._manager is not None
            assert node._manager.primary_service_time_s == 60.0
            assert node._manager.primary_service_activity == "sample"
            assert node._manager.return_tolerance_m == 0.5
            assert node._manager.planner_model_agreed is False
        else:
            assert node._manager is None
            assert "allow_illustrative" in node._configuration_error
    finally:
        node.destroy_node()
        rclpy.shutdown()
