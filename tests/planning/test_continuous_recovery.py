"""Synthetic interrupted-route recovery; no physical ground/flight validation."""

from dataclasses import replace
import math

import numpy as np
import pytest

from mge_planning.core import (
    MotionProfile, PlanRequest, ResourceBudget, RouteStatus, TerrainGrid, plan_route,
)
from mge_planning.replan import (
    EventKind, MissionPhase, ReplanConfig, ReplanEvent, ReplanPolicy, ReplanState,
)


def sloped_scene(kind):
    heights = np.tile(np.arange(7, dtype=float) * .1, (7, 1))
    grid = TerrainGrid("interrupted-slope", 1, heights,
                       np.zeros((7, 7), dtype=np.int8), 1.)
    profile = MotionProfile(kind, 1.5, 30., .2, 0., 0., 2.,
                            oxygen_l_per_s=.2 if kind == "human" else None,
                            uphill_time_factor=1., downhill_time_factor=2.,
                            uphill_energy_factor=3., downhill_energy_factor=4.,
                            service_power_w=12.)
    budget = ResourceBudget(kind, 1000., 1000., 20.,
                            100. if kind == "human" else None,
                            5. if kind == "human" else None)
    request = PlanRequest(grid.run_id, "original", kind+"_1", kind, 1,
                          grid.point((2, 1)), grid.point((2, 5)), budget,
                          return_to=grid.point((2, 1)), require_return=True,
                          service_time_s=3., reserve_time_s=20.)
    original = plan_route(terrain=grid, request=request, profile=profile)
    assert original.status == RouteStatus.FEASIBLE
    a, b = original.outbound_path[1:3]
    pose = tuple(x + .3*(y-x) for x, y in zip(a, b))
    assert abs(pose[2]-grid.point(grid.cell(pose))[2]) > 1e-6
    return grid, profile, request, original, pose


def independent_costs(paths, profile, service_s):
    time_s = service_s
    energy_wh = profile.service_power_w*service_s/3600.
    for path in paths:
        for a, b in zip(path, path[1:]):
            horizontal = math.dist(a[:2], b[:2])
            dz = b[2]-a[2]
            up, down = max(dz, 0.)/horizontal, max(-dz, 0.)/horizontal
            length = math.dist(a, b)
            time_s += length/profile.speed_m_s*(1+profile.uphill_time_factor*up
                                               + profile.downhill_time_factor*down)
            energy_wh += length*profile.energy_wh_per_m*(1+profile.uphill_energy_factor*up
                                                         + profile.downhill_energy_factor*down)
    return time_s, energy_wh


@pytest.mark.parametrize("kind", ["human", "rover"])
def test_opted_in_recovery_preserves_interpolated_xyz_and_charges_directed_connector(kind):
    grid, profile, request, _, pose = sloped_scene(kind)
    request = replace(request, request_id="resume", start=pose)
    baseline = plan_route(terrain=grid, request=request, profile=profile)
    assert (baseline.status, baseline.reason_code) == (RouteStatus.ERROR, "NON_CELL_CENTER")
    resumed = plan_route(terrain=grid, request=request, profile=profile,
                         allow_continuous_start=True)
    assert resumed.status == RouteStatus.FEASIBLE
    connector = resumed.start_connector
    assert resumed.outbound_path[0] == connector.start == pose
    assert connector.end == grid.point(grid.cell(pose)) == resumed.outbound_path[1]
    assert connector.distance_m == pytest.approx(math.dist(connector.start, connector.end))
    assert connector.distance_m > math.dist(connector.start[:2], connector.end[:2])
    connector_time, connector_energy = independent_costs(((connector.start, connector.end),), profile, 0.)
    assert connector.travel_time_s == pytest.approx(connector_time)
    assert connector.energy_est_wh == pytest.approx(connector_energy)
    expected_time, expected_energy = independent_costs(
        (resumed.outbound_path, resumed.return_path), profile, request.service_time_s)
    assert resumed.travel_time_s == pytest.approx(expected_time)
    assert resumed.energy_est_wh == pytest.approx(expected_energy)
    assert resumed.reserve_time_s == pytest.approx(request.budget.time_s-expected_time)
    assert resumed.reserve_wh == pytest.approx(request.budget.energy_wh-expected_energy)
    assert resumed.oxygen_est_l == (pytest.approx(expected_time*.2) if kind == "human" else None)
    assert resumed.return_path[-1] == request.return_to


@pytest.mark.parametrize("kind", ["human", "rover"])
def test_policy_can_propose_recovery_from_the_actual_interpolated_pose(kind):
    grid, profile, mission, original, pose = sloped_scene(kind)
    state = ReplanState(mission, mission, original, MissionPhase.OUTBOUND,
                        pose, 2, mission.budget, mission.service_time_s)
    policy = ReplanPolicy(ReplanConfig(1., .4, 1., 1.))
    result = policy.evaluate(terrain=grid, profile=profile, state=state,
        event=ReplanEvent("resume-task", grid.run_id, 1, EventKind.TASK), now_s=1.)
    assert result.candidate.status == RouteStatus.FEASIBLE
    assert result.request.start == result.candidate.outbound_path[0] == pose
    assert result.candidate.start_connector.start == pose
    assert result.request.budget == state.remaining


@pytest.mark.parametrize("kind", ["human", "rover"])
@pytest.mark.parametrize("change,z", [
    ({"max_slope_deg": 20.}, -.3),
    ({"max_downhill_slope_deg": 20.}, .3),
    ({"max_step_m": .2}, -.3),
    ({"max_step_m": .2}, .3),
])
def test_continuous_z_must_obey_directed_slope_and_step_limits(kind, change, z):
    grid, profile, request, _, _ = sloped_scene(kind)
    grid = replace(grid, elevation_m=np.zeros((7, 7)))
    profile = replace(profile, **({"max_slope_deg": 60., "max_step_m": 1.} | change))
    request = replace(request, start=(2.2, 2.5, z))
    result = plan_route(terrain=grid, request=request, profile=profile,
                        allow_continuous_start=True)
    assert (result.status, result.reason_code) == (RouteStatus.ERROR, "INVALID_START_Z")
    assert not result.outbound_path and not result.route_id and result.start_connector is None


@pytest.mark.parametrize("kind", ["human", "rover"])
def test_opt_in_keeps_centred_height_guard_and_rejects_impossible_continuous_height(kind):
    grid, profile, request, _, _ = sloped_scene(kind)
    for start in ((2.5, 2.5, 5.), (2.8, 2.5, 5.)):
        result = plan_route(terrain=grid, request=replace(request, start=start), profile=profile,
                            allow_continuous_start=True)
        assert (result.status, result.reason_code) == (RouteStatus.ERROR, "INVALID_START_Z")
        assert not result.outbound_path


def test_continuous_drone_recovery_remains_unsupported():
    grid, profile, request, _, pose = sloped_scene("drone")
    result = plan_route(terrain=grid, request=replace(request, start=pose), profile=profile,
                        allow_continuous_start=True)
    assert (result.status, result.reason_code) == (RouteStatus.ERROR, "CONTINUOUS_START_NOT_SUPPORTED")
    assert not result.outbound_path
