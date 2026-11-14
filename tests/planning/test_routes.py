"""New illustrative acceptance cases; no prior Sandbox results are imported."""

from dataclasses import replace
import heapq
import math

import numpy as np
import pytest

from mge_planning.core import (
    MotionProfile, PlanRequest, ResourceBudget, RouteMode, RouteStatus,
    SearchLimits, TerrainGrid, plan_route,
)


def profile(kind="rover", **changes):
    values = dict(agent_kind=kind, speed_m_s=1.0, max_slope_deg=85.0,
                  max_step_m=10.0, radius_m=0.0, localization_error_m=0.0,
                  energy_wh_per_m=1.0,
                  oxygen_l_per_s=0.1 if kind == "human" else None)
    return MotionProfile(**(values | changes))


def grid(mask=None, elevations=None, version=1):
    mask = np.zeros((10, 10), dtype=np.int8) if mask is None else np.array(mask)
    heights = np.zeros(mask.shape) if elevations is None else np.array(elevations)
    return TerrainGrid("illustrative-tests", version, heights, mask, 1.0)


def request(terrain, kind="rover", **changes):
    budget = ResourceBudget(kind, 1000.0, 1000.0, 0.0,
                            1000.0 if kind == "human" else None,
                            0.0 if kind == "human" else None)
    values = dict(run_id=terrain.run_id, request_id="acceptance-1", agent_id=f"{kind}_1",
                  agent_kind=kind, map_version=terrain.map_version,
                  start=(1.5, 1.5, 0.0), goal=(8.5, 8.5, 0.0),
                  return_to=(1.5, 1.5, 0.0), require_return=False, budget=budget)
    return PlanRequest(**(values | changes))


def independent_flat_dijkstra(mask, start, goal):
    """Reference graph written independently, for flat point-agent cases only."""
    rows, cols = mask.shape
    queue = [(0.0, start)]
    best = {start: 0.0}
    while queue:
        cost, (row, col) = heapq.heappop(queue)
        if cost != best[(row, col)]:
            continue
        if (row, col) == goal:
            return cost
        for dr in (-1, 0, 1):
            for dc in (-1, 0, 1):
                if dr == dc == 0:
                    continue
                nr, nc = row + dr, col + dc
                if not (0 <= nr < rows and 0 <= nc < cols) or mask[nr, nc] != 0:
                    continue
                if dr and dc and (mask[row, nc] != 0 or mask[nr, col] != 0):
                    continue
                candidate = cost + math.hypot(dr, dc)
                if candidate < best.get((nr, nc), math.inf):
                    best[(nr, nc)] = candidate
                    heapq.heappush(queue, (candidate, (nr, nc)))
    return math.inf


@pytest.mark.parametrize("seed", [7, 19, 41])
def test_d01_fast_matches_independent_dijkstra_on_flat_minigrids(seed):
    random = np.random.default_rng(seed)
    mask = np.where(random.random((10, 10)) < 0.15, 100, 0).astype(np.int8)
    # Preserve one known corridor without promising the optimum follows it.
    mask[1, 1:9] = 0
    mask[1:9, 8] = 0
    terrain = grid(mask)
    expected = independent_flat_dijkstra(mask, (1, 1), (8, 8))
    result = plan_route(terrain=terrain, request=request(terrain), profile=profile())
    assert result.status == RouteStatus.FEASIBLE
    assert result.travel_time_s == pytest.approx(expected)
    assert result.energy_est_wh == pytest.approx(expected)


def test_d02_blocked_diagonal_cannot_cut_a_corner():
    mask = np.zeros((3, 3), dtype=np.int8)
    mask[0, 1] = mask[1, 0] = 100
    terrain = grid(mask)
    result = plan_route(terrain=terrain, profile=profile(),
                        request=request(terrain, start=(0.5, 0.5, 0.0),
                                        goal=(2.5, 2.5, 0.0)))
    assert result.status == RouteStatus.NO_PATH
    assert not result.outbound_path


@pytest.mark.parametrize("gap_value,expected", [(100, RouteStatus.NO_PATH),
                                               (-1, RouteStatus.UNKNOWN)])
def test_d03_known_barrier_differs_from_possible_unknown_corridor(gap_value, expected):
    mask = np.zeros((7, 7), dtype=np.int8)
    mask[3, :] = 100
    mask[3, 3] = gap_value
    terrain = grid(mask)
    result = plan_route(terrain=terrain, profile=profile(),
                        request=request(terrain, start=(3.5, 1.5, 0.0),
                                        goal=(3.5, 5.5, 0.0)))
    assert result.status == expected
    assert not result.route_id


def test_d04_agent_profile_changes_admissible_slope():
    heights = np.zeros((5, 7))
    heights[:, 3:] = 1.0
    terrain = grid(np.zeros(heights.shape), heights)
    query = request(terrain, start=(1.5, 2.5, 0.0), goal=(5.5, 2.5, 1.0))
    low_limit = plan_route(terrain=terrain, request=query,
                          profile=profile(max_slope_deg=20.0))
    high_limit = plan_route(terrain=terrain, request=query,
                           profile=profile(max_slope_deg=60.0))
    assert low_limit.status == RouteStatus.NO_PATH
    assert high_limit.status == RouteStatus.FEASIBLE


def test_d05_expensive_directional_return_is_not_assumed_equal_to_outbound():
    heights = np.tile(np.arange(7, dtype=float), (3, 1))
    terrain = grid(np.zeros(heights.shape), heights)
    model = profile(downhill_time_factor=3.0)
    query = request(terrain, start=(0.5, 1.5, 0.0), goal=(5.5, 1.5, 5.0),
                    return_to=(0.5, 1.5, 0.0),
                    budget=ResourceBudget("rover", 15.0, 1000.0, 0.0))
    outbound = plan_route(terrain=terrain, request=query, profile=model)
    roundtrip = plan_route(terrain=terrain, request=replace(query, require_return=True),
                           profile=model)
    assert outbound.status == RouteStatus.FEASIBLE
    assert roundtrip.status == RouteStatus.INSUFFICIENT_BUDGET


def test_d06_human_oxygen_includes_service_return_and_reserve():
    terrain = grid()
    query = request(terrain, kind="human", start=(1.5, 1.5, 0.0),
                    goal=(6.5, 1.5, 0.0), return_to=(1.5, 1.5, 0.0),
                    require_return=True, service_time_s=5.0,
                    budget=ResourceBudget("human", 1000.0, 1000.0, 0.0, 1.4, 0.1))
    result = plan_route(terrain=terrain, request=query, profile=profile("human"))
    assert result.status == RouteStatus.INSUFFICIENT_BUDGET
    assert not result.outbound_path


def test_feasible_roundtrip_reports_service_costs_for_every_resource():
    terrain = grid()
    query = request(terrain, kind="human", start=(1.5, 1.5, 0.0),
                    goal=(6.5, 1.5, 0.0), return_to=(1.5, 1.5, 0.0),
                    require_return=True, service_time_s=5.0,
                    budget=ResourceBudget("human", 100.0, 100.0, 10.0, 50.0, 5.0))
    result = plan_route(terrain=terrain, request=query,
                        profile=profile("human", service_power_w=3600.0))
    assert result.status == RouteStatus.FEASIBLE
    assert result.travel_time_s == pytest.approx(15.0)
    assert result.energy_est_wh == pytest.approx(15.0)
    assert result.oxygen_est_l == pytest.approx(1.5)
    assert result.return_path[-1] == query.return_to


def test_reachable_goal_with_known_impossible_return_is_not_feasible():
    mask = np.zeros((7, 7), dtype=np.int8)
    mask[3, :] = 100
    terrain = grid(mask)
    query = request(terrain, start=(1.5, 1.5, 0.0), goal=(5.5, 1.5, 0.0),
                    return_to=(5.5, 5.5, 0.0), require_return=True)
    result = plan_route(terrain=terrain, request=query, profile=profile())
    assert result.status == RouteStatus.NO_PATH
    assert not result.route_id


def test_joint_search_finds_longer_feasible_alternative_to_energy_expensive_shortest_route():
    heights = np.zeros((7, 9))
    heights[:, 4] = 2.0
    heights[5, 4] = 0.0
    terrain = grid(np.zeros(heights.shape), heights)
    query = request(terrain, start=(1.5, 1.5, 0.0), goal=(7.5, 1.5, 0.0),
                    return_to=(1.5, 1.5, 0.0), require_return=True,
                    budget=ResourceBudget("rover", 1000.0, 25.0, 0.0))
    result = plan_route(terrain=terrain, request=query,
                        profile=profile(uphill_energy_factor=10.0),
                        limits=SearchLimits(timeout_s=10.0))
    assert result.status == RouteStatus.FEASIBLE
    assert result.energy_est_wh <= 25.0
    assert any(x == pytest.approx(4.5) and y == pytest.approx(5.5)
               for x, y, _ in result.outbound_path)


def test_d07_map_update_replans_from_current_pose_without_reusing_old_route():
    terrain = grid()
    first = plan_route(terrain=terrain, request=request(terrain), profile=profile())
    mask = np.zeros((10, 10), dtype=np.int8)
    mask[4, 4] = 100
    revised = grid(mask, version=2)
    current_pose = (3.5, 3.5, 0.0)
    second = plan_route(terrain=revised, profile=profile(),
                        request=request(revised, start=current_pose))
    assert first.status == second.status == RouteStatus.FEASIBLE
    assert second.outbound_path[0] == current_pose
    assert second.map_version_used == 2
    assert second.route_id != first.route_id
    assert (4.5, 4.5, 0.0) not in second.outbound_path


def test_d08_stale_version_never_returns_executable_route():
    terrain = grid(version=2)
    result = plan_route(terrain=terrain, profile=profile(),
                        request=request(terrain, map_version=1))
    assert result.status == RouteStatus.STALE_MAP
    assert not result.route_id
    assert not result.outbound_path


def test_mismatched_run_is_not_accepted_as_current_map():
    terrain = grid()
    result = plan_route(terrain=terrain, profile=profile(),
                        request=request(terrain, run_id="different-run"))
    assert result.status in {RouteStatus.ERROR, RouteStatus.UNKNOWN, RouteStatus.STALE_MAP}
    assert not result.outbound_path
    assert result.reason_code


def test_d09_safe_maximizes_bottleneck_instead_of_using_fast_narrow_gap():
    mask = np.zeros((21, 31), dtype=np.int8)
    mask[4:17, 15] = 100
    mask[10, 15] = 0
    terrain = grid(mask)
    query = request(terrain, start=(3.5, 10.5, 0.0), goal=(27.5, 10.5, 0.0))
    limits = SearchLimits(timeout_s=10.0)
    fast = plan_route(terrain=terrain, request=query, profile=profile(), limits=limits)
    safe = plan_route(terrain=terrain, request=replace(query, mode=RouteMode.SAFE),
                      profile=profile(), limits=limits)
    assert fast.status == safe.status == RouteStatus.FEASIBLE
    assert safe.min_clearance_m > fast.min_clearance_m
    assert safe.travel_time_s >= fast.travel_time_s


def test_search_limit_is_unknown_not_a_proof_of_impossibility():
    terrain = grid()
    result = plan_route(terrain=terrain, request=request(terrain), profile=profile(),
                        limits=SearchLimits(max_labels=1, timeout_s=10.0))
    assert result.status == RouteStatus.UNKNOWN
    assert result.reason_code == "SEARCH_LIMIT"
    assert not result.route_id


def test_missing_profile_does_not_silently_use_scientific_defaults():
    terrain = grid()
    result = plan_route(terrain=terrain, request=request(terrain))
    assert result.status == RouteStatus.UNKNOWN
    assert not result.outbound_path


def test_unsupported_efficient_mode_does_not_silently_become_fast():
    terrain = grid()
    result = plan_route(terrain=terrain, profile=profile(),
                        request=request(terrain, mode=RouteMode.EFFICIENT))
    assert result.status == RouteStatus.ERROR
    assert result.reason_code


def test_coordinates_outside_grid_are_rejected_instead_of_clamped():
    terrain = grid()
    result = plan_route(terrain=terrain, profile=profile(),
                        request=request(terrain, start=(-0.1, 1.5, 0.0)))
    assert result.status == RouteStatus.ERROR
    assert not result.outbound_path


def test_footprint_and_localization_allowance_can_exclude_a_point_agent_corridor():
    mask = np.full((7, 9), 100, dtype=np.int8)
    mask[3, :] = 0
    terrain = grid(mask)
    query = request(terrain, start=(1.5, 3.5, 0.0), goal=(7.5, 3.5, 0.0))
    point = plan_route(terrain=terrain, request=query, profile=profile())
    wide = plan_route(terrain=terrain, request=query,
                      profile=profile(radius_m=0.5, localization_error_m=0.2))
    assert point.status == RouteStatus.FEASIBLE
    assert wide.status == RouteStatus.NO_PATH


def test_repeated_queries_keep_the_same_route_and_measured_costs():
    terrain = grid()
    query = request(terrain)
    first = plan_route(terrain=terrain, request=query, profile=profile())
    second = plan_route(terrain=terrain, request=query, profile=profile())
    assert first.status == second.status == RouteStatus.FEASIBLE
    assert first.route_id == second.route_id
    assert first.outbound_path == second.outbound_path
    assert first.travel_time_s == second.travel_time_s
    assert first.energy_est_wh == second.energy_est_wh


@pytest.mark.parametrize("invalid", [0.0, -1.0, float("nan")])
def test_invalid_grid_resolution_cannot_enter_a_search(invalid):
    with pytest.raises(ValueError):
        TerrainGrid("illustrative-tests", 1, np.zeros((2, 2)),
                    np.zeros((2, 2), dtype=np.int8), invalid)


def test_misaligned_height_and_mask_shapes_are_rejected():
    with pytest.raises(ValueError):
        TerrainGrid("illustrative-tests", 1, np.zeros((3, 3)),
                    np.zeros((2, 3), dtype=np.int8), 1.0)
