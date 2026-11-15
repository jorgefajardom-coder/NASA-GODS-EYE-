"""D-EST-01 candidate hypothesis, local contradiction and same-run recording.

Real data/mapping/planner/recorder; MOCK mission and kinematic primary execution.
No ROS observation prepares the initial corridor. One later SIMULATED footprint
contradicts the estimated route. This is not scientific or physical acceptance.
"""
from copy import deepcopy
import json
import math
from pathlib import Path
import struct

import pytest

pytest.importorskip("rclpy", reason="Requires built ROS 2 workspace")
from sensor_msgs.msg import Image
from mge_interfaces.msg import AgentState, TerrainMeta, TerrainObservation
from mge_gateway.contract_replay import read_package, read_public_rasters, to_viewer
from mge_gateway.replay_check import check_package
from mge_mapping.policy import load_knowledge_policy
from tests.integration.test_vertical_mock import wait_for
from tests.integration.test_vertical_execution import (
    Stack, ROOT, RUN_ID, HOME, REQUEST, LATCHED, centre, get, mission, submit,
    polyline, position, speed, stamp_seconds, movement_costs, rasters_cover,
)
from tests.integration.ground_fixture import simulated_ground_point

POLICY_FILE = ROOT / "config/exploration_policy.illustrative.json"


@pytest.fixture(scope="module")
def estimated_stack(tmp_path_factory, planner_ready):
    stack = Stack(str(tmp_path_factory.mktemp("estimated-replay")),
                  extra_launch_args=(f"exploration_policy_file:={POLICY_FILE}",))
    stack.observed = stack.meta = None
    stack.node.create_subscription(Image, "/mge/terrain/observed",
                                   lambda msg: setattr(stack, "observed", msg), LATCHED)
    stack.node.create_subscription(TerrainMeta, "/mge/terrain/meta",
                                   lambda msg: setattr(stack, "meta", msg), LATCHED)
    try:
        wait_for(lambda: len(get("/api/manifest").get("agents", [])) == 3,
                 timeout_s=30., what="gateway and three labelled MOCK agent states")
        wait_for(lambda: mission()["map_version"] == 1, timeout_s=30., what="initial estimated map")
        planner_ready()
        stack.until(lambda: stack.observed is not None and stack.meta is not None
                    and stack.belief is not None and stack.human,
                    "initial estimated batch and agent pose")
        wait_for(lambda: rasters_cover(stack.package, {"1"}), timeout_s=30.,
                 what="recorded unobserved version 1")
        yield stack
    finally:
        stack.stop()


def publish_contradiction(stack, cell):
    stack.until(lambda: stack.observations.get_subscription_count() >= 1, "mapping observation subscriber")
    heights = struct.unpack(f"<{stack.belief.height*stack.belief.width}f", bytes(stack.belief.data))
    obs = TerrainObservation()
    obs.header.frame_id = "map"
    obs.header.stamp = stack.node.get_clock().now().to_msg()
    obs.observation_id, obs.run_id, obs.agent_id = "local-contradiction", RUN_ID, "drone_1"
    obs.base_map_version, obs.source_kind = 1, TerrainObservation.SOURCE_SIMULATED
    obs.cell_indices, obs.elevation_m, obs.sigma_m = [cell], [heights[cell]+3.], [.25]
    obs.obstacle = [TerrainObservation.OBSTACLE_BLOCKED]
    stack.observations.publish(obs)
    return obs, heights[cell]


def test_initial_estimate_then_one_contradiction_stop_replan_return_and_offline_package(estimated_stack):
    stack = estimated_stack
    policy = load_knowledge_policy(POLICY_FILE)
    assert stack.meta.map_version == 1
    assert policy.source_record in stack.meta.sources
    assert set(bytes(stack.observed.data)) == {0}
    assert mission()["route_id"] == ""
    before = stack.human[-1]
    assert position(before)[:2] == HOME and speed(before) == 0.
    initial_agents = mission()['agents']
    assert {a['agent_id'] for a in initial_agents} == {'human_1', 'rover_1', 'drone_1'}
    for agent in initial_agents:
        point = agent['pose']['position']
        assert tuple(point[k] for k in ('x', 'y', 'z')) == simulated_ground_point(
            stack.surface, (point['x'], point['y']))
        assert agent['mode'] == 'IDLE'

    initial = submit("estimated-initial", centre(19, 19))
    assert initial["mission_state"] == "READY", initial["active_route"]
    first_route = initial["active_route"]
    assert (first_route["status"], first_route["map_version_used"]) == ("FEASIBLE", 1)
    assert polyline(first_route)[0] == position(before)
    assert set(bytes(stack.observed.data)) == {0}  # Proposal precedes every local observation.
    start = len(stack.human)
    stack.until(lambda: any(s.mode == AgentState.MODE_MOVING
                 and math.dist(position(s)[:2], HOME) > 2. for s in stack.human[start:]),
                 "movement along the initial estimated hypothesis")
    outbound = first_route["outbound_path"]
    target = outbound[len(outbound)//2]
    target_cell = stack.surface.cell((target["x"], target["y"]))
    index = target_cell[0]*stack.surface.cols+target_cell[1]
    assert math.dist(position(stack.human[-1])[:2], (target["x"], target["y"])) > 8.
    obs, prior_height = publish_contradiction(stack, index)

    halted = stack.until(lambda: next((s for s in stack.human[start:]
                             if s.mode == AgentState.MODE_HALTED), None), "stop acknowledgement")
    assert speed(halted) == 0.
    revised = wait_for(lambda: (m := mission())["map_version"] == 2
                       and m["mission_state"] in ("READY", "BLOCKED") and m,
                       timeout_s=30., what="replan on the contradictory map version")
    assert revised["mission_state"] == "READY", revised["active_route"]
    route = revised["active_route"]
    path = polyline(route)
    assert (route["status"], route["map_version_used"]) == ("FEASIBLE", 2)
    assert revised["route_id"] != initial["route_id"] and path[0] == position(halted)
    assert path[1] == stack.surface.point(stack.surface.cell(position(halted)))
    assert math.dist(path[0][:2], path[1][:2]) > 1e-3
    assert all(stack.surface.cell(point) != target_cell for point in path)
    expected = movement_costs(route)
    for field, cost in zip(("travel_time_s", "energy_est_wh", "oxygen_est_l"), expected):
        assert route[field] == pytest.approx(cost, rel=1e-5)
    for field, reserve, cost in zip(("time_remaining_s", "energy_remaining_wh", "oxygen_remaining_l"),
                                  ("reserve_time_s", "reserve_wh", "reserve_oxygen_l"), expected):
        assert cost + REQUEST[reserve] <= getattr(halted, field)+1e-4

    events = get(f"/api/run/{RUN_ID}/events")["events"]
    invalidated = next(e for e in events if e["event_type"] == "ROUTE_INVALIDATED"
                       and e["route_id"] == initial["route_id"])
    published = next(e for e in events if e["event_type"] == "ROUTE_PUBLISHED"
                     and e["route_id"] == revised["route_id"])
    assert invalidated["seq"] < published["seq"]
    assert stamp_seconds(invalidated["header"]) <= stamp_seconds(halted.header) <= stamp_seconds(published["header"])
    stack.until(lambda: any(s.mode == AgentState.MODE_MOVING
                            and stamp_seconds(s.header) >= stamp_seconds(published["header"])
                            for s in stack.human[start:]), "movement after revised authorization")

    # Neither an old base nor retagging an old timestamp can erase the new danger.
    for identifier, base in (("late-free-old-base", 1), ("late-free-current-base", 2)):
        stale = deepcopy(obs)
        stale.observation_id, stale.base_map_version = identifier, base
        stale.header.stamp.sec -= 1
        stale.elevation_m, stale.obstacle = [prior_height], [TerrainObservation.OBSTACLE_FREE]
        stack.observations.publish(stale)
    stack.observations.publish(obs)  # Idempotent retransmission has old base, unchanged ID.
    stack.spin(1.0)
    assert stack.meta.map_version == mission()["map_version"] == 2
    assert [i for i, value in enumerate(bytes(stack.observed.data)) if value] == [index]

    stack.until(lambda: stack.human[-1].mode == AgentState.MODE_IDLE and speed(stack.human[-1]) == 0.
                and position(stack.human[-1])[:2] == pytest.approx(HOME), "resumed return at base", 120.)
    returned = stack.human[-1]
    assert position(returned) == pytest.approx(path[-1])
    after = stack.human[next(i for i, s in enumerate(stack.human) if s is halted):]
    assert any(s.mode == AgentState.MODE_MOVING for s in after)
    for a, b in zip(after, after[1:]):
        assert b.time_remaining_s <= a.time_remaining_s
        assert b.energy_remaining_wh <= a.energy_remaining_wh
        assert b.oxygen_remaining_l <= a.oxygen_remaining_l
    for field, cost in zip(("time_remaining_s", "energy_remaining_wh", "oxygen_remaining_l"), expected):
        assert getattr(halted, field)-getattr(returned, field) == pytest.approx(cost, rel=1e-3)
    wait_for(lambda: any(a["agent_id"] == "human_1" and a["mode"] == "IDLE"
                        and tuple(a["pose"]["position"][k] for k in ("x", "y")) == pytest.approx(HOME)
                        for a in mission()["agents"]), timeout_s=10., what="recordable final pose")
    wait_for(lambda: rasters_cover(stack.package, {"1", "2"}), timeout_s=30., what="both recorded public maps")
    stack.stop()
    assert check_package(stack.package) == []
    manifest, records, snapshot = read_package(stack.package)
    public = read_public_rasters(stack.package, manifest)
    assert set(public["versions"]) == {"1", "2"}
    assert public["versions"]["1"]["observed"] == []
    assert public["versions"]["2"]["observed"] == [index]
    assert all(value == 2.5 for value in public["versions"]["1"]["sigma"])
    assert public["versions"]["2"]["sigma"][index] == .25
    assert public["versions"]["2"]["belief"][index] == pytest.approx(prior_height+3.)
    assert manifest["source_mode"] == "MOCK" and manifest["run_id"] == RUN_ID
    converted = to_viewer(manifest, records, snapshot, public)
    assert converted["status"] == "READY"
    assert all(value is None for value in converted["rasters"]["reference"])
    assert snapshot["mission_state"]["mission_state"] == "READY"  # Never scientific COMPLETE.
    for record in records:
        if record['type'] == 'state':
            for agent in record['state']['agents']:
                if agent['agent_kind'] == 'DRONE':
                    point = agent['pose']['position']
                    assert tuple(point[k] for k in ('x', 'y', 'z')) == simulated_ground_point(
                        stack.surface, (point['x'], point['y']))
                    assert agent['mode'] == 'IDLE'
    # A compact audit points only to this run's actual recorded data.
    (Path(stack.package).parent / "estimated-run-result.json").write_text(json.dumps({
        "run_id": RUN_ID, "package": stack.package, "policy": policy.source_record,
        "observation_id": obs.observation_id, "observed_cell": index,
        "initial_route_id": initial["route_id"], "revised_route_id": revised["route_id"],
        "halted_pose": position(halted), "final_pose": position(returned),
        "status": "MOCK_RECOVERY_RECORDED", "scientific_mission_complete": False,
    }, indent=2))
