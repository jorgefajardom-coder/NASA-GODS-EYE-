"""Safety/proof boundaries beyond the guide's first acceptance scenarios."""

from dataclasses import replace

import numpy as np

from mge_planning.core import (
    MotionProfile, PlanRequest, ResourceBudget, RouteMode, RouteStatus,
    TerrainGrid, plan_route,
)


def scenario(mask=None):
    mask = np.zeros((5, 5), dtype=np.int8) if mask is None else mask
    grid = TerrainGrid("guard-run", 1, np.zeros(mask.shape), mask, 1.)
    profile = MotionProfile("rover", 1., 45., 1., 0., 0., 1.)
    request = PlanRequest("guard-run", "guard-request", "rover_1", "rover", 1,
                          (1.5, 2.5), (3.5, 2.5),
                          ResourceBudget("rover", 100., 100., 0.))
    return grid, profile, request


def test_continuous_pose_is_not_teleported_to_a_free_cell_centre():
    grid, profile, request = scenario()
    result = plan_route(terrain=grid, profile=profile,
                        request=replace(request, start=(1.1, 2.5)))
    assert result.status == RouteStatus.ERROR
    assert result.reason_code == "NON_CELL_CENTER"
    assert result.outbound_path == ()


def test_unknown_shortcuts_prevent_an_unproven_global_budget_rejection():
    mask = np.zeros((5, 5), dtype=np.int8)
    mask[0, 0] = -1
    grid, profile, request = scenario(mask)
    result = plan_route(terrain=grid, profile=profile,
                        request=replace(request, budget=ResourceBudget("rover", 1., 1., 0.)))
    assert result.status == RouteStatus.UNKNOWN
    assert result.reason_code == "UNVERIFIED_BUDGET_CORRIDOR"


def test_request_lists_and_source_rasters_cannot_mutate_a_created_snapshot():
    heights = np.zeros((5, 5))
    mask = np.zeros((5, 5), dtype=np.int8)
    grid = TerrainGrid("guard-run", 1, heights, mask, 1.)
    heights[:] = 50
    mask[:] = 100
    assert not np.any(grid.elevation_m)
    assert not np.any(grid.traversability)
    assert not grid.elevation_m.flags.writeable
    _, profile, request = scenario()
    position = [1.5, 2.5]
    request = replace(request, start=position)
    position[0] = 99
    assert request.start == (1.5, 2.5)
    assert plan_route(terrain=grid, profile=profile, request=request).status == RouteStatus.FEASIBLE


def test_stationary_safe_route_accounts_for_service_and_reserves():
    grid, profile, request = scenario()
    request = replace(request, goal=request.start, mode=RouteMode.SAFE, service_time_s=5.)
    result = plan_route(terrain=grid, profile=profile, request=request)
    assert result.status == RouteStatus.FEASIBLE
    assert result.travel_time_s == 5.
    assert len(result.outbound_path) == len(result.return_path) == 1
    assert result.energy_est_wh == 0.
    assert result.reserve_time_s == 95.
