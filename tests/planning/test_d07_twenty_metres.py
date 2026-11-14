"""D-07 explicit-request integration on synthetic flat terrain, without ROS.

Travel here means interpolation along the planned polyline, not simulated vehicle
dynamics. All rates are illustrative; accounting is independent of core helpers.
"""

from dataclasses import asdict, replace
import json
import math

import numpy as np
import pytest

from mge_planning.core import (
    MotionProfile, PlanRequest, ResourceBudget, RouteStatus, TerrainGrid, plan_route,
)


def length(path):
    return sum(math.dist(a, b) for a, b in zip(path, path[1:]))


def advance(path, distance):
    """Walk complete segments then interpolate the last one at accumulated distance."""
    travelled = [path[0]]
    remaining = distance
    for index, (a, b) in enumerate(zip(path, path[1:])):
        segment = math.dist(a, b)
        if remaining < segment:
            pose = tuple(x + remaining/segment*(y-x) for x, y in zip(a, b))
            travelled.append(pose)
            return tuple(travelled), (pose,) + path[index+1:]
        travelled.append(b)
        remaining -= segment
    raise AssertionError("Initial path must be longer than the requested travel")


def costs(path, profile, *, service_s=0.):
    """Independent accounting for these flat, constant-rate test scenarios only."""
    assert all(point[2] == 0. for point in path)
    duration = length(path)/profile.speed_m_s + service_s
    return dict(time_s=duration,
                energy_wh=length(path)*profile.energy_wh_per_m
                + service_s*profile.service_power_w/3600.,
                oxygen_l=duration*profile.oxygen_l_per_s if profile.agent_kind == "human" else None)


def setup_case(kind, resource=None):
    grid = TerrainGrid("SIMULATED-D07-20m", 1, np.zeros((9, 18)),
                       np.zeros((9, 18), dtype=np.int8), 3.)
    profile = MotionProfile(kind, 2., 30., .5, .2, .1, .5,
                            oxygen_l_per_s=.2 if kind == "human" else None,
                            service_power_w=90.)
    budget = ResourceBudget(kind, 100., 100., 5.,
                            30. if kind == "human" else None,
                            2. if kind == "human" else None)
    request = PlanRequest(grid.run_id, "before-obstacle", kind+"_1", kind, 1,
                          (4.5, 13.5, 0.), (43.5, 13.5, 0.), budget,
                          return_to=(4.5, 13.5, 0.), require_return=True,
                          service_time_s=4., reserve_time_s=5.)
    first = plan_route(terrain=grid, profile=profile, request=request)
    assert first.status == RouteStatus.FEASIBLE
    if resource:
        # Original complete mission fits EXACTLY with its reserve. The obstacle's
        # detour must then exhaust the chosen resource, not fail the initial plan.
        value = {"time_s": first.travel_time_s + request.reserve_time_s,
                 "energy_wh": first.energy_est_wh + budget.reserve_wh,
                 "oxygen_l": (first.oxygen_est_l + budget.reserve_oxygen_l)
                 if kind == "human" else None}[resource]
        request = replace(request, budget=replace(budget, **{resource: value}))
        first = plan_route(terrain=grid, profile=profile, request=request)
        assert first.status == RouteStatus.FEASIBLE
    travelled, pending = advance(first.outbound_path, 20.)
    assert length(travelled) == pytest.approx(20., abs=1e-10)
    pose = travelled[-1]
    assert pose == pytest.approx((24.5, 13.5, 0.))
    assert pose != grid.point(grid.cell(pose))
    consumed = costs(travelled, profile)  # No service has happened yet.
    assert consumed["time_s"] == pytest.approx(10.)
    assert consumed["energy_wh"] == pytest.approx(10.)
    if kind == "human":
        assert consumed["oxygen_l"] == pytest.approx(2.)
    b = request.budget
    remaining = replace(b, time_s=b.time_s-consumed["time_s"],
                        energy_wh=b.energy_wh-consumed["energy_wh"],
                        oxygen_l=b.oxygen_l-consumed["oxygen_l"] if kind == "human" else None)
    # Keep reserves, do not subtract either them or the old route estimates.
    assert remaining.reserve_wh == b.reserve_wh
    assert remaining.reserve_oxygen_l == b.reserve_oxygen_l
    obstacle = first.outbound_path[-5]
    assert obstacle in pending and obstacle not in travelled
    updated = replace(request, request_id="after-obstacle", map_version=2,
                      start=pose, budget=remaining)
    return grid, profile, request, first, travelled, consumed, updated, grid.cell(obstacle)


def misses_box(a, b, lower, upper):
    """Independent slab intersection of the entire segment with a closed AABB."""
    enter, leave = 0., 1.
    for axis in (0, 1):
        delta = b[axis]-a[axis]
        if delta == 0:
            if a[axis] < lower[axis] or a[axis] > upper[axis]:
                return True
        else:
            t1, t2 = sorted(((lower[axis]-a[axis])/delta, (upper[axis]-a[axis])/delta))
            enter, leave = max(enter, t1), min(leave, t2)
            if enter > leave:
                return True
    return False


def record(tmp_path, case, original, first, travelled, consumed, updated, obstacle, result, profile):
    report = dict(provenance="SIMULATED: synthetic flat grid and illustrative rates; no physical validation",
                  case=case, agent_kind=original.agent_kind, motion_profile=asdict(profile),
                  grid=dict(rows=9, cols=18, resolution_m=3., elevation_m=0.,
                            original_mask="all admissible", updated_obstacle_cell=obstacle,
                            barrier=case == "no_alternative"),
                  initial_request=asdict(original), initial_route=asdict(first),
                  travelled_path=travelled, travelled_distance_m=length(travelled),
                  consumed=consumed, updated_request=asdict(updated), result=asdict(result))
    (tmp_path / "d07.json").write_text(json.dumps(report, indent=2, allow_nan=False), encoding="utf-8")


@pytest.mark.parametrize("kind", ["human", "rover"])
def test_d07_twenty_metres_then_explicit_replan_with_remaining_resources(kind, tmp_path):
    grid, profile, original, first, travelled, consumed, request, obstacle = setup_case(kind)
    mask = grid.traversability.copy()
    mask[obstacle] = 100
    revised = replace(grid, map_version=2, traversability=mask)
    result = plan_route(terrain=revised, profile=profile, request=request)
    assert result.status == RouteStatus.FEASIBLE, result.detail
    assert result.map_version_used == 2 and result.route_id != first.route_id
    assert result.run_id == first.run_id and result.request_id == "after-obstacle"
    assert result.outbound_path[0] == travelled[-1] == request.start
    assert original.start not in result.outbound_path
    assert all(p[0] >= request.start[0] for p in result.outbound_path)
    connector = result.start_connector
    assert connector.start == request.start and connector.end == revised.point(revised.cell(request.start))
    assert connector.distance_m == pytest.approx(1.)
    assert connector.min_clearance_m >= 0.
    assert result.outbound_path[1] == connector.end
    assert result.outbound_path[-1] == result.return_path[0] == request.goal
    assert result.return_path[-1] == original.return_to
    radius = profile.radius_m + profile.localization_error_m
    row, col = obstacle
    lower = (col*3.-radius, row*3.-radius)
    upper = ((col+1)*3.+radius, (row+1)*3.+radius)
    # Whole-segment collision check including connector AND return, not waypoints only.
    for path in (result.outbound_path, result.return_path):
        for a, b in zip(path, path[1:]):
            assert misses_box(a, b, lower, upper)
    full = result.outbound_path + result.return_path[1:]
    independent = costs(full, profile, service_s=request.service_time_s)
    assert result.travel_time_s == pytest.approx(independent["time_s"])
    assert result.energy_est_wh == pytest.approx(independent["energy_wh"])
    assert result.oxygen_est_l == (pytest.approx(independent["oxygen_l"]) if kind == "human" else None)
    for field, estimate, reserve in (("time_s", result.travel_time_s, request.reserve_time_s),
                                     ("energy_wh", result.energy_est_wh, request.budget.reserve_wh)):
        # Conservation across the complete timeline: prefix + NEW mission, once.
        left = getattr(original.budget, field)-consumed[field]-estimate
        assert left >= reserve
        assert left == pytest.approx(getattr(request.budget, field)-estimate)
    assert result.reserve_time_s == pytest.approx(request.budget.time_s-result.travel_time_s)
    assert result.reserve_wh == pytest.approx(request.budget.energy_wh-result.energy_est_wh)
    if kind == "human":
        left = original.budget.oxygen_l-consumed["oxygen_l"]-result.oxygen_est_l
        assert left >= request.budget.reserve_oxygen_l
        assert result.reserve_oxygen_l == pytest.approx(left)
    # Identical input yields identical paths/costs and route identifier.
    again = plan_route(terrain=revised, profile=profile, request=request)
    assert again.status == result.status and again.route_id == result.route_id
    assert again.outbound_path == result.outbound_path and again.return_path == result.return_path
    stale = plan_route(terrain=revised, profile=profile, request=replace(request, map_version=1))
    assert stale.status == RouteStatus.STALE_MAP and not stale.outbound_path
    record(tmp_path, "alternative", original, first, travelled, consumed, request, obstacle, result, profile)


@pytest.mark.parametrize("kind", ["human", "rover"])
def test_d07_twenty_metres_then_obstacle_without_alternative(kind, tmp_path):
    grid, profile, original, first, travelled, consumed, request, obstacle = setup_case(kind)
    mask = grid.traversability.copy()
    mask[:, obstacle[1]] = 100  # Fully known barrier contains the pending obstacle.
    revised = replace(grid, map_version=2, traversability=mask)
    result = plan_route(terrain=revised, profile=profile, request=request)
    assert result.status == RouteStatus.NO_PATH
    assert result.reason_code == "NO_ADMISSIBLE_PATH" and result.map_version_used == 2
    assert not result.outbound_path and not result.return_path and not result.route_id
    record(tmp_path, "no_alternative", original, first, travelled, consumed, request, obstacle, result, profile)


@pytest.mark.parametrize("kind,resource", [("human", "time_s"), ("human", "energy_wh"),
                                          ("human", "oxygen_l"), ("rover", "time_s"),
                                          ("rover", "energy_wh")])
def test_d07_twenty_metres_then_remaining_resource_cannot_fund_detour(kind, resource, tmp_path):
    grid, profile, original, first, travelled, consumed, request, obstacle = setup_case(kind, resource)
    mask = grid.traversability.copy()
    mask[obstacle] = 100
    revised = replace(grid, map_version=2, traversability=mask)
    result = plan_route(terrain=revised, profile=profile, request=request)
    assert result.status == RouteStatus.INSUFFICIENT_BUDGET
    assert result.reason_code == "BUDGET_EXCEEDED" and result.map_version_used == 2
    assert not result.outbound_path and not result.return_path and not result.route_id
    record(tmp_path, "insufficient_"+resource, original, first, travelled, consumed, request, obstacle, result, profile)
