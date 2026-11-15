"""Exercise the real mapping conversion/fusion boundary on synthetic messages."""
from types import SimpleNamespace as NS

import numpy as np
import pytest

from mge_mapping.core import BeliefMap, ObservationFusion
from mge_mapping.node import observation_from_message
from mge_planning.core import (
    MotionProfile, PlanRequest, ResourceBudget, RouteStatus, TerrainGrid, plan_route,
)


def message(*, frame="map", sec=20, nanosec=0, base=1, identifier="obstacle", cells=(4,), obstacle=(100,)):
    return NS(header=NS(frame_id=frame, stamp=NS(sec=sec, nanosec=nanosec)),
              observation_id=identifier, agent_id="drone_1", run_id="adapter-run",
              base_map_version=base, source_kind="SIMULATED", cell_indices=cells,
              elevation_m=(0.,)*len(cells), sigma_m=(.25,)*len(cells), obstacle=obstacle)


@pytest.mark.parametrize("invalid", [
    dict(frame="odom"), dict(frame=""), dict(sec=-1), dict(sec=1.5),
    dict(sec=True), dict(sec=2**31), dict(nanosec=-1), dict(nanosec=1_000_000_000),
    dict(nanosec=.5), dict(nanosec=True),
])
def test_bad_frame_or_timestamp_is_rejected_before_fusion_without_repair(invalid):
    initial = BeliefMap.from_arrays(np.zeros((3, 3)), run_id="adapter-run")
    fusion = ObservationFusion(initial)
    with pytest.raises(ValueError):
        fusion.apply(observation_from_message(message(**invalid)))
    assert fusion.belief_map is initial and fusion.map_version == 1


def test_canonical_subsecond_stamp_is_preserved_and_empty_obstacle_is_not_free_evidence():
    obs = observation_from_message(message(sec=12, nanosec=345_000_000, obstacle=()))
    assert obs.timestamp_sim_s == 12.345
    assert obs.timestamp_sim_ns == 12_345_000_000
    assert obs.obstacles is None
    assert obs.source_map_version == 1 and obs.source_kind == "SIMULATED"


def test_delayed_ros_shaped_free_message_cannot_change_the_real_planners_blocked_goal():
    fusion = ObservationFusion(BeliefMap.from_arrays(np.zeros((3, 3)), run_id="adapter-run"))
    fusion.apply(observation_from_message(message(sec=10, identifier="survey",
                  cells=tuple(range(9)), obstacle=(0,)*9)))
    fusion.apply(observation_from_message(message(base=2)))
    protected = fusion.belief_map
    delayed = message(sec=11, base=2, identifier="delayed-free", obstacle=(0,))
    with pytest.raises(ValueError):
        fusion.apply(observation_from_message(delayed))
    assert fusion.belief_map is protected
    grid = TerrainGrid(protected.run_id, protected.map_version, protected.belief,
                        protected.traversability_grid(), protected.resolution_m,
                        protected.origin_x_m, protected.origin_y_m, sigma_m=protected.sigma)
    profile = MotionProfile("rover", 1., 30., .5, 0., 0., 1.)
    request = PlanRequest(grid.run_id, "blocked-goal", "rover_1", "rover", grid.map_version,
                          grid.point((0, 0)), grid.point((1, 1)),
                          ResourceBudget("rover", 100., 100., 5.), require_return=False)
    result = plan_route(terrain=grid, request=request, profile=profile)
    assert result.status == RouteStatus.NO_PATH and not result.outbound_path


def test_generated_ros_observation_uses_the_same_conversion_and_fusion_boundary():
    wire = pytest.importorskip("mge_interfaces.msg", reason="Requires built ROS 2 interfaces")
    msg = wire.TerrainObservation()
    msg.header.frame_id = "map"
    msg.header.stamp.sec, msg.header.stamp.nanosec = 12, 345_000_000
    msg.observation_id, msg.agent_id, msg.run_id = "generated", "drone_1", "adapter-run"
    msg.base_map_version, msg.source_kind = 1, "SIMULATED"
    msg.cell_indices, msg.elevation_m, msg.sigma_m, msg.obstacle = [4], [0.], [.25], [100]
    fusion = ObservationFusion(BeliefMap.from_arrays(np.zeros((3, 3)), run_id=msg.run_id))
    actual, applied = fusion.apply(observation_from_message(msg))
    assert applied and actual.map_version == 2
    assert actual.last_observation_timestamp_sim_s == 12.345
    assert actual.last_observation_timestamp_sim_ns == 12_345_000_000
    assert actual.obstacle_grid[1, 1] == 100
    assert fusion.apply(observation_from_message(msg)) == (actual, False)


def test_large_epoch_older_nanoseconds_cannot_clear_an_obstacle_when_float_seconds_collide():
    fusion = ObservationFusion(BeliefMap.from_arrays(np.zeros((3, 3)), run_id="adapter-run"))
    blocked = observation_from_message(message(sec=1_794_694_700, nanosec=500))
    fusion.apply(blocked)
    before = fusion.belief_map
    older_free = observation_from_message(message(sec=1_794_694_700, nanosec=400,
        base=2, identifier="older-free", obstacle=(0,)))
    assert blocked.timestamp_sim_s == older_free.timestamp_sim_s
    assert blocked.timestamp_sim_ns - older_free.timestamp_sim_ns == 100
    with pytest.raises(ValueError, match="timestamp precedes"):
        fusion.apply(older_free)
    assert fusion.belief_map is before and fusion.map_version == 2
    assert before.obstacle_grid[1, 1] == 100
    assert before.last_observation_timestamp_sim_ns == 1_794_694_700_000_000_500
    # The applied ID stays a no-op even though its original base is now old.
    assert fusion.apply(blocked) == (before, False)
    equal = observation_from_message(message(sec=1_794_694_700, nanosec=500,
        base=2, identifier="same-time-distinct-footprint", cells=(5,), obstacle=(0,)))
    updated, applied = fusion.apply(equal)
    assert applied and updated.map_version == 3
    assert updated.last_observation_timestamp_sim_ns == blocked.timestamp_sim_ns
    assert updated.obstacle_grid[1, 1] == 100 and updated.obstacle_grid[1, 2] == 0
    assert fusion.apply(equal) == (updated, False)


def test_wire_stamp_last_representable_ros_nanosecond_retains_exact_identity():
    obs = observation_from_message(message(sec=2**31-1, nanosec=999_999_999))
    assert obs.timestamp_sim_ns == (2**31)*1_000_000_000-1
