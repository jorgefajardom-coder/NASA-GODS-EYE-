"""Actual ROS scientific-context/PlanRoute exchange on declared synthetic terrain.

These tests verify numerical transport and fail-closed authorization, not physical
execution or approval of the illustrative scientific coefficients.
"""
from copy import deepcopy
from pathlib import Path
import math
import struct
from time import monotonic
from types import SimpleNamespace

import pytest

rclpy = pytest.importorskip("rclpy", reason="Requires built ROS 2 Jazzy workspace")
from builtin_interfaces.msg import Time
from geometry_msgs.msg import Point as WirePoint
from mge_interfaces.msg import AgentState, TerrainMeta
from mge_interfaces.srv import PlanRoute, RegisterPlanningContext, SetMissionGoal
from nav_msgs.msg import OccupancyGrid
from rclpy.executors import MultiThreadedExecutor
from rclpy.parameter import Parameter
from rclpy.qos import DurabilityPolicy, QoSProfile, ReliabilityPolicy
from rosgraph_msgs.msg import Clock
from sensor_msgs.msg import Image

from mge_mission.manager import MissionManager
from mge_mission.conformance import _cases, audit_returned_paths
from mge_mission.models import MODEL_ID, estimate_activity, estimate_segment, load_profiles
from mge_mission.node import create_node_class
from mge_mission.planning_context import (
    PlanningActivity, context_for_request, context_to_wire, profile_registry_sha256,
)
from mge_mission.types import Point
from mge_planning.node import make_node_class

ROOT = Path(__file__).resolve().parents[2]
PROFILES = ROOT / "config/scenario_demo.yaml"
RUN = "scientific-cost-ros-test"
RETAINED = QoSProfile(depth=1, durability=DurabilityPolicy.TRANSIENT_LOCAL)


def spin(executor, predicate, timeout=8.0, tick=None):
    end = monotonic() + timeout
    while monotonic() < end:
        if predicate():
            return
        if tick:
            tick()
        executor.spin_once(timeout_sec=.01)
    assert predicate(), "Scientific ROS service deadline exceeded"


def meta():
    message = TerrainMeta()
    message.header.frame_id, message.header.stamp = "map", Time(sec=10)
    message.run_id, message.dataset_id, message.map_version = RUN, "synthetic-science-cost-grid", 1
    message.rows = message.cols = 5
    message.resolution_m, message.nodata_value = 4.0, -9999.0
    message.crs, message.vertical_datum = "LOCAL_ENU_SYNTHETIC", "illustrative"
    return message


def wire_request(identifier, duration=0.0):
    request = PlanRoute.Request()
    request.run_id, request.request_id, request.agent_id = RUN, identifier, "human_1"
    request.agent_kind, request.mode, request.map_version = "HUMAN", "FAST", 1
    request.start = WirePoint(x=6., y=6., z=0.)
    request.goal = WirePoint(x=10., y=6., z=0.)
    request.return_to = deepcopy(request.start)
    request.require_return, request.service_time_s = True, duration
    request.time_budget_s, request.energy_budget_wh, request.oxygen_budget_l = 3600., 600., 150.
    request.reserve_time_s, request.reserve_wh, request.reserve_oxygen_l = 360., 60., 15.
    return request


@pytest.fixture
def graph():
    rclpy.init()
    decisions = []
    class CapturingPlanner(make_node_class()):
        def _plan(self, message, response):
            result = super()._plan(message, response)
            decisions.append((deepcopy(message), deepcopy(result.decision)))
            return result
    planner = CapturingPlanner(parameter_overrides=[
        Parameter("scientific_profiles_path", value=str(PROFILES)),
        Parameter("allow_illustrative_profiles", value=True),
        Parameter("snapshot_contract_confirmed", value=True),
    ])
    metadata = meta()
    planner.store.ingest_meta(metadata)
    image = Image(header=metadata.header, height=5, width=5, encoding="32FC1", step=20,
                  data=struct.pack("<25f", *([0.] * 25)))
    planner.store.ingest_image("belief", image)
    planner.store.ingest_image("sigma", image)
    mask = OccupancyGrid(header=metadata.header, data=[0] * 25)
    mask.info.height = mask.info.width = 5
    mask.info.resolution, mask.info.origin.orientation.w = 4., 1.
    planner.store.ingest_mask("human", mask)
    peer = rclpy.create_node("scientific_cost_service_probe")
    route = peer.create_client(PlanRoute, "/mge/planner/plan_route")
    register = peer.create_client(RegisterPlanningContext, "/mge/planner/register_context")
    executor = MultiThreadedExecutor(num_threads=4)
    executor.add_node(planner); executor.add_node(peer)
    spin(executor, lambda: route.service_is_ready() and register.service_is_ready())
    owned = []
    try:
        yield planner, peer, route, register, executor, decisions, owned
    finally:
        executor.shutdown(timeout_sec=5)
        for node in owned:
            node.destroy_node()
        planner.destroy_node(); peer.destroy_node(); rclpy.shutdown()


def register_context(executor, client, request, activities):
    context = context_for_request(request, MODEL_ID, profile_registry_sha256(PROFILES), activities)
    future = client.call_async(context_to_wire(context, RegisterPlanningContext.Request()))
    spin(executor, future.done)
    return context, future.result()


def ask(executor, client, request):
    future = client.call_async(request)
    spin(executor, future.done)
    return future.result().decision


def audit(decision, activities):
    profile = load_profiles(PROFILES)["human_1"]
    parts = []
    for path in (decision.outbound_path, decision.return_path):
        parts.extend(estimate_segment(profile, (a.x, a.y, a.z), (b.x, b.y, b.z))
                     for a, b in zip(path, path[1:]))
    parts.extend(estimate_activity(profile, a.kind, a.remaining_s) for a in activities)
    for field, attribute in (("travel_time_s", "time_s"), ("energy_est_wh", "energy_wh"), ("oxygen_est_l", "oxygen_l")):
        assert getattr(decision, field) == pytest.approx(sum(getattr(x, attribute) for x in parts), rel=1e-5, abs=1e-3)


def test_actual_service_requires_context_and_distinguishes_activity_and_wait(graph):
    planner, peer, route, register, executor, decisions, owned = graph
    missing = ask(executor, route, wire_request("missing", 20.))
    assert missing.status == "UNKNOWN" and missing.reason_code == "COST_CONTEXT_REQUIRED"
    identity_request = wire_request("identity-check")
    identity = context_for_request(identity_request, MODEL_ID, profile_registry_sha256(PROFILES))
    for field, value, reason in (
        ("profile_registry_sha256", "0"*64, "COST_MODEL_MISMATCH"),
        ("model_source_sha256", "0"*64, "COST_MODEL_MISMATCH"),
        ("run_id", "wrong-run", "RUN_MISMATCH"),
        ("map_version", 2, "STALE_MAP"),
    ):
        invalid = context_to_wire(identity, RegisterPlanningContext.Request())
        setattr(invalid, field, value)
        answer = register.call_async(invalid)
        spin(executor, answer.done)
        assert not answer.result().accepted and answer.result().reason_code == reason
    results = {}
    for activity in ("inspect", "sample"):
        request = wire_request(activity, 35.)
        activities = (PlanningActivity(activity, activity, 20.), PlanningActivity(activity+":wait", "wait", 15.))
        context, accepted = register_context(executor, register, request, activities)
        assert accepted.accepted and accepted.context_sha256 == context.digest
        duplicate = register.call_async(context_to_wire(context, RegisterPlanningContext.Request()))
        spin(executor, duplicate.done)
        assert duplicate.result().accepted and duplicate.result().reason_code == "COST_CONTEXT_DUPLICATE"
        decision = ask(executor, route, request)
        assert decision.status == "FEASIBLE", (decision.reason_code, decision.detail)
        audit(decision, activities)
        results[activity] = decision
        altered = deepcopy(request); altered.energy_budget_wh -= 1.
        rejected = ask(executor, route, altered)
        assert rejected.status == "ERROR" and rejected.reason_code == "COST_CONTEXT_REQUEST_MISMATCH"
    assert results["sample"].travel_time_s == results["inspect"].travel_time_s
    assert results["sample"].energy_est_wh > results["inspect"].energy_est_wh
    request = wire_request("inspect", 35.)
    _, conflict = register_context(executor, register, request, (PlanningActivity("other", "sample", 35.),))
    assert not conflict.accepted and conflict.reason_code == "COST_CONTEXT_CONFLICT"


def test_real_mission_registers_context_before_plan_and_preserves_approval_gate(graph):
    planner, peer, route, register, executor, decisions, owned = graph
    profiles = load_profiles(PROFILES)
    manager = MissionManager(RUN, profiles, Point(6., 6., 0.), .5, allow_illustrative=True,
                             primary_service_time_s=20., primary_service_activity="sample",
                             planner_model_agreed=False)
    mission = create_node_class()(manager=manager, parameter_overrides=[
        Parameter("use_sim_time", value=True), Parameter("profiles_path", value=str(PROFILES))])
    owned.append(mission); executor.add_node(mission)
    clock = peer.create_publisher(Clock, "/clock", QoSProfile(depth=1, reliability=ReliabilityPolicy.BEST_EFFORT))
    terrain = peer.create_publisher(TerrainMeta, "/mge/terrain/meta", RETAINED)
    agent = peer.create_publisher(AgentState, "/mge/agents/human_1/state", 10)
    goals = peer.create_client(SetMissionGoal, "/mge/mission/set_goal")
    state = AgentState()
    state.header.frame_id, state.header.stamp = "map", Time(sec=10)
    state.run_id, state.agent_id, state.agent_kind = RUN, "human_1", "HUMAN"
    state.pose.position, state.pose.orientation.w = WirePoint(x=6., y=6., z=0.), 1.
    state.mode, state.confidence = "IDLE", 1.
    state.time_remaining_s, state.energy_remaining_wh, state.oxygen_remaining_l = 3600., 600., 150.
    def tick():
        clock.publish(Clock(clock=Time(sec=10)))
        terrain.publish(meta()); agent.publish(state)
    spin(executor, lambda: goals.service_is_ready() and mission._context_client.service_is_ready()
         and mission._planner_client.service_is_ready() and mission._ready_clock()
         and "human_1" in manager._agents and manager.map_version == 1, tick=tick)
    goal = SetMissionGoal.Request()
    goal.run_id, goal.request_id, goal.primary_agent_id, goal.mode = RUN, "normal-producer", "human_1", "FAST"
    goal.base, goal.goal = WirePoint(x=6., y=6., z=0.), WirePoint(x=10., y=6., z=0.)
    goal.time_budget_s, goal.energy_budget_wh, goal.oxygen_budget_l = 3600., 600., 150.
    goal.reserve_time_s, goal.reserve_wh, goal.reserve_oxygen_l = 360., 60., 15.
    sent = goals.call_async(goal)
    spin(executor, sent.done, tick=tick)
    assert sent.result().accepted
    spin(executor, lambda: manager.snapshot().reason_code == "MODEL_NOT_AGREED", tick=tick)
    assert not manager.planner_model_agreed
    assert manager.snapshot().route_id == ""
    produced = [(request, decision) for request, decision in decisions if request.request_id != "missing"]
    assert len(produced) == 1 and produced[0][1].status == "FEASIBLE"
    request, decision = produced[0]
    context = planner.contexts.resolve(request, expected_model_id=MODEL_ID,
                                       expected_profile_registry_sha256=profile_registry_sha256(PROFILES))
    assert len(context.activities) == 1 and context.activities[0].kind == "sample"
    audit(decision, context.activities)


def test_all_seven_published_conformance_cases_through_actual_ros_service():
    """Run the same seven synthetic grids through registration and PlanRoute DDS."""
    profile_path = ROOT / "config/science_profiles.proposed.json"
    profiles = load_profiles(profile_path)
    registry_hash = profile_registry_sha256(profile_path)
    rclpy.init()
    planner = make_node_class()(parameter_overrides=[
        Parameter("scientific_profiles_path", value=str(profile_path)),
        Parameter("allow_illustrative_profiles", value=True),
        Parameter("snapshot_contract_confirmed", value=True),
    ])
    peer = rclpy.create_node("seven_scientific_conformance_service_probe")
    route = peer.create_client(PlanRoute, "/mge/planner/plan_route")
    registration = peer.create_client(RegisterPlanningContext, "/mge/planner/register_context")
    executor = MultiThreadedExecutor(num_threads=4)
    executor.add_node(planner); executor.add_node(peer)
    outcomes = []
    try:
        spin(executor, lambda: route.service_is_ready() and registration.service_is_ready())
        for index, (case_id, profile, grade, activity, service_s, wait_s) in enumerate(_cases(profiles)):
            metadata = TerrainMeta()
            metadata.header.frame_id, metadata.header.stamp = "map", Time(sec=100+index)
            metadata.run_id, metadata.dataset_id = "conformance-"+case_id, "synthetic-seven-case-cost-grid"
            metadata.map_version, metadata.rows, metadata.cols = 1, 13, 13
            metadata.resolution_m, metadata.nodata_value = 1., -9999.
            metadata.crs, metadata.vertical_datum = "LOCAL_ENU_SYNTHETIC", "illustrative"
            planner.store.ingest_meta(metadata)
            heights = [column*grade for row in range(13) for column in range(13)]
            image = Image(header=metadata.header, height=13, width=13, encoding="32FC1", step=52,
                          data=struct.pack("<169f", *heights))
            sigma = Image(header=metadata.header, height=13, width=13, encoding="32FC1", step=52,
                          data=struct.pack("<169f", *([0.]*169)))
            planner.store.ingest_image("belief", image)
            planner.store.ingest_image("sigma", sigma)
            mask = OccupancyGrid(header=metadata.header, data=[0]*169)
            mask.info.height = mask.info.width = 13
            mask.info.resolution, mask.info.origin.orientation.w = 1., 1.
            planner.store.ingest_mask(profile.kind, mask)
            request = PlanRoute.Request()
            request.run_id, request.request_id = metadata.run_id, case_id
            request.agent_id, request.agent_kind = profile.agent_id, profile.kind.upper()
            request.map_version, request.mode, request.require_return = 1, "FAST", True
            request.start = WirePoint(x=4.5, y=4.5, z=4*grade)
            request.goal = WirePoint(x=6.5, y=4.5, z=6*grade)
            request.return_to = deepcopy(request.start)
            request.service_time_s = service_s+wait_s
            request.time_budget_s = request.energy_budget_wh = 100000.
            request.reserve_time_s = request.reserve_wh = 10.
            request.oxygen_budget_l = 100000. if profile.kind == "human" else math.nan
            request.reserve_oxygen_l = 10. if profile.kind == "human" else math.nan
            schedule = (PlanningActivity(case_id+":service", activity, service_s),
                        PlanningActivity(case_id+":wait", "wait", wait_s))
            context = context_for_request(request, MODEL_ID, registry_hash, schedule)
            pending = registration.call_async(context_to_wire(context, RegisterPlanningContext.Request()))
            spin(executor, pending.done)
            assert pending.result().accepted, (case_id, pending.result().reason_code)
            assert pending.result().context_sha256 == context.digest
            decision = ask(executor, route, request)
            assert decision.status == "FEASIBLE", (case_id, decision.reason_code, decision.detail)
            values = {name: getattr(decision, name) for name in (
                "travel_time_s", "energy_est_wh", "oxygen_est_l", "reserve_time_s", "reserve_wh", "reserve_oxygen_l")}
            for name in ("outbound_path", "return_path"):
                values[name] = tuple((point.x, point.y, point.z) for point in getattr(decision, name))
            independent = audit_returned_paths(profile, SimpleNamespace(**values), service_activity=activity,
                service_time_s=service_s, wait_time_s=wait_s,
                budget={"time_s": 100000., "energy_wh": 100000.,
                        "oxygen_l": 100000. if profile.kind == "human" else None},
                relative_tolerance=1e-5, absolute_tolerance=1e-3)
            assert independent["agreement"], (case_id, independent)
            outcomes.append((case_id, decision.status, independent["agreement"]))
        assert len(outcomes) == 7 and all(feasible == "FEASIBLE" and agreement for _, feasible, agreement in outcomes)
        print("Actual ROS scientific conformance: 7 AGREE, 0 DISAGREE; profile/mission approval unchanged")
    finally:
        executor.shutdown(timeout_sec=5)
        planner.destroy_node(); peer.destroy_node(); rclpy.shutdown()
