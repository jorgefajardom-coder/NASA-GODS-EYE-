"""Synthetic ground-start connectors; no ROS or physical safety certification."""

from dataclasses import replace
import math

import numpy as np
import pytest

from mge_planning.core import (
    MotionProfile, PlanRequest, ResourceBudget, RouteMode, RouteStatus,
    TerrainGrid, plan_route,
)


def scenario(kind="rover", *, mask=None, heights=None, sigma=None, version=1):
    mask = np.zeros((7, 7), dtype=np.int8) if mask is None else mask
    heights = np.zeros(mask.shape) if heights is None else heights
    grid = TerrainGrid("continuous-test", version, heights, mask, 1., sigma_m=sigma)
    profile = MotionProfile(kind, 1., 45., 1., 0., 0., 1.,
                            oxygen_l_per_s=.1 if kind == "human" else None)
    budget = ResourceBudget(kind, 100., 100., 10.,
                            100. if kind == "human" else None,
                            10. if kind == "human" else None)
    request = PlanRequest(grid.run_id, "r1", f"{kind}_1", kind, version,
                          (2.1, 2.5, 0.), (4.5, 2.5, 0.), budget,
                          return_to=(1.5, 2.5, 0.), require_return=False)
    return grid, profile, request


@pytest.mark.parametrize("kind", ["rover", "human"])
def test_clear_start_preserves_requested_pose_and_graph_waypoints(kind):
    grid, profile, request = scenario(kind)
    result = plan_route(terrain=grid, profile=profile, request=request)
    assert result.status == RouteStatus.FEASIBLE
    assert result.outbound_path == (request.start, (2.5, 2.5, 0.),
                                    (3.5, 2.5, 0.), request.goal)
    c = result.start_connector
    assert (c.start, c.end) == result.outbound_path[:2]
    assert c.distance_m == pytest.approx(.4)
    assert result.travel_time_s == pytest.approx(2.4)
    assert result.energy_est_wh == pytest.approx(2.4)
    assert result.oxygen_est_l == (pytest.approx(.24) if kind == "human" else None)


def test_directed_connector_costs_service_return_and_reserves_are_charged_once():
    grid, profile, request = scenario("human")
    profile = replace(profile, speed_m_s=2., energy_wh_per_m=3.,
                      downhill_time_factor=2., downhill_energy_factor=4.,
                      service_power_w=3600.)
    request = replace(request, start=(2.1, 2.5, .3), require_return=True,
                      service_time_s=2., reserve_time_s=5.)
    result = plan_route(terrain=grid, profile=profile, request=request)
    assert result.status == RouteStatus.FEASIBLE
    c = result.start_connector
    assert c.distance_m == pytest.approx(.5)  # sqrt(.4**2 + .3**2)
    assert c.travel_time_s == pytest.approx(.625)
    assert c.energy_est_wh == pytest.approx(6.)
    assert c.oxygen_est_l == pytest.approx(.0625)
    # Two metres outbound, three back, plus service and the directed connector.
    assert result.travel_time_s == pytest.approx(.625 + 5/2 + 2)
    assert result.energy_est_wh == pytest.approx(6 + 5*3 + 2)
    assert result.oxygen_est_l == pytest.approx(result.travel_time_s*.1)
    assert result.reserve_time_s == pytest.approx(100-result.travel_time_s)
    assert result.reserve_wh == pytest.approx(100-result.energy_est_wh)
    assert result.reserve_oxygen_l == pytest.approx(100-result.oxygen_est_l)
    assert result.return_path[-1] == request.return_to
    assert result.outbound_path[0] == request.start


@pytest.mark.parametrize("hazard", ["forbidden", "unknown", "nodata", "sigma", "missing_sigma"])
def test_unsafe_containing_cell_cannot_be_snapped_to_another_free_cell(hazard):
    mask = np.zeros((7, 7), dtype=np.int8)
    heights = np.zeros((7, 7))
    sigma = np.zeros((7, 7))
    if hazard == "forbidden":
        mask[2, 2] = 100
    elif hazard == "unknown":
        mask[2, 2] = -1
    elif hazard == "nodata":
        heights[2, 2] = np.nan
    elif hazard == "sigma":
        sigma[2, 2] = 2.
    else:
        sigma = None
    grid, profile, request = scenario(mask=mask, heights=heights, sigma=sigma)
    profile = replace(profile, max_sigma_m=1.)
    # Pose is only .01 m from a neighbouring FREE cell; escaping to it is forbidden.
    request = replace(request, start=(2.01, 2.5, 0.))
    result = plan_route(terrain=grid, profile=profile, request=request)
    expected = RouteStatus.NO_PATH if hazard == "forbidden" else RouteStatus.UNKNOWN
    assert result.status == expected
    assert result.reason_code == ("NO_ADMISSIBLE_START_CONNECTOR" if hazard == "forbidden"
                                  else "UNVERIFIED_START_CONNECTOR")
    assert not result.outbound_path and not result.route_id
    assert result.start_connector is None


@pytest.mark.parametrize("hazard,expected", [(100, RouteStatus.NO_PATH), (-1, RouteStatus.UNKNOWN)])
def test_connector_footprint_cannot_overlap_adjacent_obstacle_or_unknown(hazard, expected):
    mask = np.zeros((7, 7), dtype=np.int8)
    mask[2, 1] = hazard
    grid, profile, request = scenario(mask=mask)
    # Centre (2.5,2.5) is clear for radius .15; initial pose is only .1 from obstacle.
    profile = replace(profile, radius_m=.1, localization_error_m=.05)
    result = plan_route(terrain=grid, profile=profile, request=request)
    assert result.status == expected
    assert not result.outbound_path


def test_point_start_on_blocked_corner_is_rejected_even_with_zero_radius():
    mask = np.zeros((7, 7), dtype=np.int8)
    mask[1, 2] = mask[2, 1] = 100
    grid, profile, request = scenario(mask=mask)
    result = plan_route(terrain=grid, profile=profile,
                        request=replace(request, start=(2., 2., 0.)))
    assert result.status == RouteStatus.NO_PATH
    assert result.reason_code == "NO_ADMISSIBLE_START_CONNECTOR"
    assert not result.outbound_path


@pytest.mark.parametrize("change", [dict(max_slope_deg=20.), dict(max_step_m=.2),
                                  dict(max_downhill_slope_deg=20.)])
def test_connector_rejects_slope_step_and_directed_downhill_limit(change):
    grid, profile, request = scenario()
    request = replace(request, start=(2.1, 2.5, .3))  # 36.87 degrees downhill
    result = plan_route(terrain=grid, profile=replace(profile, **change), request=request)
    assert result.status == RouteStatus.NO_PATH
    assert result.reason_code == "NO_ADMISSIBLE_START_CONNECTOR"


@pytest.mark.parametrize("point", [(-.01, 2.5, 0.), (7., 2.5, 0.)])
def test_outside_start_is_not_clamped(point):
    grid, profile, request = scenario()
    result = plan_route(terrain=grid, profile=profile, request=replace(request, start=point))
    assert result.status == RouteStatus.ERROR and result.reason_code == "INVALID_POSITION"


def test_start_footprint_must_fit_inside_map_for_entire_connector():
    grid, profile, request = scenario()
    result = plan_route(terrain=grid, profile=replace(profile, radius_m=.1),
                        request=replace(request, start=(.05, 2.5, 0.)))
    assert result.status == RouteStatus.NO_PATH
    assert result.reason_code == "NO_ADMISSIBLE_START_CONNECTOR"


@pytest.mark.parametrize("resource", ["time", "energy", "oxygen"])
def test_connector_resources_are_in_search_budget_not_added_after_feasibility(resource):
    grid, profile, request = scenario("human")
    # The 2 m graph route fits these caps; the .4 m connector does not.
    if resource == "time":
        request = replace(request, budget=replace(request.budget, time_s=3.2), reserve_time_s=1.)
    elif resource == "energy":
        request = replace(request, budget=replace(request.budget, energy_wh=12.2))
    else:
        request = replace(request, budget=replace(request.budget, oxygen_l=10.22))
    result = plan_route(terrain=grid, profile=profile, request=request)
    assert result.status == RouteStatus.INSUFFICIENT_BUDGET
    assert result.reason_code == "BUDGET_EXCEEDED"
    assert not result.outbound_path and result.start_connector is None


@pytest.mark.parametrize("mode", [RouteMode.FAST, RouteMode.SAFE])
def test_start_at_cell_centre_keeps_graph_only_path_and_exact_costs(mode):
    grid, profile, request = scenario()
    result = plan_route(terrain=grid, profile=profile,
                        request=replace(request, start=(2.5, 2.5, 0.), mode=mode))
    assert result.status == RouteStatus.FEASIBLE
    assert result.start_connector is None
    assert result.outbound_path == ((2.5, 2.5, 0.), (3.5, 2.5, 0.), request.goal)
    assert result.travel_time_s == result.energy_est_wh == 2.


def test_safe_bottleneck_includes_the_connector_not_just_cell_centres():
    grid, profile, request = scenario()
    result = plan_route(terrain=grid, profile=profile,
                        request=replace(request, start=(.1, 2.5, 0.), mode=RouteMode.SAFE))
    assert result.status == RouteStatus.FEASIBLE
    assert result.min_clearance_m == pytest.approx(.1)
    assert result.start_connector.min_clearance_m == pytest.approx(.1)


def test_d07_replan_from_continuous_pose_after_obstacle_update():
    grid, profile, request = scenario()
    first = plan_route(terrain=grid, profile=profile,
                       request=replace(request, start=(2.5, 2.5, 0.)))
    assert (3.5, 2.5, 0.) in first.outbound_path
    mask = np.zeros((7, 7), dtype=np.int8)
    mask[2, 3] = 100
    revised, _, _ = scenario(mask=mask, version=2)
    query = replace(request, start=(2.2, 2.4, 0.), map_version=2, request_id="r2")
    second = plan_route(terrain=revised, profile=profile, request=query)
    assert first.status == second.status == RouteStatus.FEASIBLE
    assert second.outbound_path[:2] == (query.start, (2.5, 2.5, 0.))
    assert second.map_version_used == 2 and second.route_id != first.route_id
    assert (3.5, 2.5, 0.) not in second.outbound_path


def test_every_point_of_accepted_connector_stays_in_known_cell_and_clear_of_squares():
    mask = np.zeros((7, 7), dtype=np.int8)
    mask[2, 1] = 100
    mask[3, 2] = -1
    grid, profile, request = scenario(mask=mask)
    profile = replace(profile, radius_m=.05, localization_error_m=.05)
    request = replace(request, start=(2.4, 2.1, 0.))
    result = plan_route(terrain=grid, profile=profile, request=request)
    assert result.status == RouteStatus.FEASIBLE
    c = result.start_connector
    # Independent dense check against actual axis-aligned cell squares, not the
    # solver's circumscribed-circle clearance formula. The mathematical bound
    # (MODEL.md), rather than sampling alone, covers points between these probes.
    for t in np.linspace(0., 1., 1001):
        x = c.start[0] + t*(c.end[0]-c.start[0])
        y = c.start[1] + t*(c.end[1]-c.start[1])
        assert grid.cell((x, y)) == (2, 2)
        for row, col in np.argwhere(mask != 0):
            dx = max(col-x, 0., x-(col+1))
            dy = max(row-y, 0., y-(row+1))
            assert math.hypot(dx, dy) >= profile.radius_m + profile.localization_error_m


def test_two_dimensional_start_uses_belief_height_and_nonzero_origin_resolution():
    grid, profile, request = scenario(heights=np.full((7, 7), 3.))
    grid = replace(grid, origin_x_m=-10., origin_y_m=20., resolution_m=2.)
    request = replace(request, start=(-5.8, 25.), goal=(-1., 25.), require_return=False)
    result = plan_route(terrain=grid, profile=profile, request=request)
    assert result.status == RouteStatus.FEASIBLE
    assert result.outbound_path[0] == (-5.8, 25., 3.)
    assert result.start_connector.end == (-5., 25., 3.)
    assert result.start_connector.distance_m == pytest.approx(.8)


@pytest.mark.parametrize("change", [dict(goal=(4.1, 2.5, 0.)),
                                  dict(require_return=True, return_to=None),
                                  dict(require_return=True, return_to=(1.1, 2.5, 0.))])
def test_goal_and_return_target_remain_cell_centres(change):
    grid, profile, request = scenario()
    result = plan_route(terrain=grid, profile=profile, request=replace(request, **change))
    assert result.status == RouteStatus.ERROR and result.reason_code == "NON_CELL_CENTER"


def test_continuous_start_does_not_claim_drone_flight_support():
    grid, profile, request = scenario("drone")
    result = plan_route(terrain=grid, profile=profile, request=request)
    assert result.status == RouteStatus.ERROR
    assert result.reason_code == "CONTINUOUS_START_NOT_SUPPORTED"
