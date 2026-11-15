"""Ground-Z integration fixture regressions; synthetic scenes, no physical poses."""
from dataclasses import replace

import numpy as np
import pytest

from mge_planning.core import MotionProfile, PlanRequest, ResourceBudget, RouteStatus, TerrainGrid, plan_route
from tests.integration.ground_fixture import (
    initialize_ground_agents, observed_public_scene, simulated_ground_point)


def scenario(kind, continuous, height=-12.5):
    grid = TerrainGrid('SIMULATED-ground-z', 1, np.full((7, 7), height),
                       np.zeros((7, 7), dtype=np.int8), 1.)
    profile = MotionProfile(kind, 1., 30., .5, .1, .1, 1.,
                            oxygen_l_per_s=.1 if kind == 'human' else None)
    budget = ResourceBudget(kind, 100., 100., 5., 30. if kind == 'human' else None,
                            2. if kind == 'human' else None)
    xy = (2.1 if continuous else 2.5, 2.5)
    request = PlanRequest(grid.run_id, 'ground-fixture', kind+'_1', kind, 1,
                          simulated_ground_point(grid, xy), grid.point((2, 4)), budget,
                          return_to=grid.point((2, 1)), require_return=True)
    return grid, profile, request


@pytest.mark.parametrize('kind', ['human', 'rover'])
@pytest.mark.parametrize('continuous', [False, True])
def test_simulated_nonzero_ground_pose_is_valid_without_changing_xy(kind, continuous):
    grid, profile, request = scenario(kind, continuous)
    result = plan_route(terrain=grid, profile=profile, request=request, allow_continuous_start=continuous)
    assert result.status == RouteStatus.FEASIBLE
    assert result.outbound_path[0] == request.start
    assert request.start[2] == -12.5
    assert (result.start_connector is not None) == continuous
    if continuous:
        baseline = plan_route(terrain=grid, profile=profile, request=request)
        assert baseline.reason_code == 'NON_CELL_CENTER'


@pytest.mark.parametrize('kind', ['human', 'rover'])
@pytest.mark.parametrize('continuous', [False, True])
def test_explicit_zero_is_not_missing_and_incompatible_ground_z_still_fails(kind, continuous):
    grid, profile, request = scenario(kind, continuous)
    template = {'agents': [{'id': 'agent', 'kind': kind.upper(),
                             'x_m': request.start[0], 'y_m': request.start[1], 'z_m': 0.}]}
    unchanged = initialize_ground_agents(template, grid)
    assert unchanged == template
    request = replace(request, start=(*request.start[:2], unchanged['agents'][0]['z_m']))
    result = plan_route(terrain=grid, profile=profile, request=request, allow_continuous_start=continuous)
    assert result.status == RouteStatus.ERROR and result.reason_code == 'INVALID_START_Z'
    assert not result.outbound_path and not result.route_id


@pytest.mark.parametrize('continuous', [False, True])
def test_real_zero_surface_height_is_a_valid_coordinate(continuous):
    grid, profile, request = scenario('rover', continuous, 0.)
    result = plan_route(terrain=grid, profile=profile, request=request, allow_continuous_start=continuous)
    assert result.status == RouteStatus.FEASIBLE and result.outbound_path[0][2] == 0.


@pytest.mark.parametrize('hazard', ['unobserved', 'nodata', 'sigma', 'forbidden'])
@pytest.mark.parametrize('continuous', [False, True])
def test_no_ground_height_is_inferred_for_unknown_or_forbidden_scene(hazard, continuous):
    grid, profile, request = scenario('rover', continuous)
    cell = grid.cell(request.start)
    heights, mask = grid.elevation_m.copy(), grid.traversability.copy()
    sigma = np.zeros_like(heights)
    if hazard == 'unobserved':
        mask[cell] = -1  # A finite prior by itself is NOT a known ground scene.
    elif hazard == 'nodata':
        heights[cell] = np.nan
    elif hazard == 'sigma':
        sigma[cell] = np.nan
    else:
        mask[cell] = 100
    grid = replace(grid, elevation_m=heights, traversability=mask, sigma_m=sigma)
    with pytest.raises(ValueError):
        simulated_ground_point(grid, request.start[:2])
    # An explicit supplied position remains explicit; core decides terrain safety.
    result = plan_route(terrain=grid, profile=profile,
                        request=replace(request, start=(*request.start[:2], 0.)),
                        allow_continuous_start=continuous)
    assert result.status != RouteStatus.FEASIBLE and result.reason_code != 'INVALID_START_Z'


@pytest.mark.parametrize('kind', ['human', 'rover'])
@pytest.mark.parametrize('continuous', [False, True])
def test_map_height_change_preserves_pose_and_requires_strict_z_or_bounded_opt_in_connector(kind, continuous):
    grid, profile, request = scenario(kind, continuous)
    newer = replace(grid, map_version=2, elevation_m=grid.elevation_m+.2)
    stale_pose = replace(request, map_version=2)
    result = plan_route(terrain=newer, profile=profile, request=stale_pose,
                        allow_continuous_start=continuous)
    if continuous:
        # The experimental connector moves from the unchanged supplied XYZ to
        # the containing centre. This is not a new measured/projected pose.
        assert result.status == RouteStatus.FEASIBLE
        connector = result.start_connector
        assert result.outbound_path[0] == connector.start == request.start
        assert connector.end == newer.point(newer.cell(request.start))
        distance = ((connector.end[0]-request.start[0])**2 + .2**2)**.5
        assert connector.distance_m == pytest.approx(distance)
        assert connector.travel_time_s == pytest.approx(distance/profile.speed_m_s)
        assert connector.energy_est_wh == pytest.approx(distance*profile.energy_wh_per_m)
        assert connector.oxygen_est_l == (pytest.approx(distance*.1) if kind == 'human' else None)
    else:
        assert result.reason_code == 'INVALID_START_Z' and not result.outbound_path
    current = replace(stale_pose, start=simulated_ground_point(newer, request.start[:2]))
    accepted = plan_route(terrain=newer, profile=profile, request=current,
                          allow_continuous_start=continuous)
    assert request.start[2] == -12.5 and current.start[2] == pytest.approx(-12.3)
    assert accepted.status == RouteStatus.FEASIBLE
    assert accepted.map_version_used == 2 and accepted.outbound_path[0] == current.start
    excessive = replace(grid, map_version=3, elevation_m=grid.elevation_m+.6)
    refused = plan_route(terrain=excessive, profile=profile,
                         request=replace(request, map_version=3),
                         allow_continuous_start=continuous)
    assert refused.reason_code == 'INVALID_START_Z' and not refused.outbound_path


def test_initialization_fills_only_absent_ground_z_and_never_projects_existing_pose():
    grid, *_ = scenario('rover', False)
    template = {'agents': [dict(id=kind, kind=kind, x_m=2.5, y_m=2.5)
                            for kind in ('HUMAN', 'ROVER', 'DRONE')]}
    initialized = initialize_ground_agents(template, grid)
    assert all('z_m' not in agent for agent in template['agents'])
    assert [a.get('z_m') for a in initialized['agents']] == [-12.5, -12.5, -12.5]
    with pytest.raises(ValueError):
        simulated_ground_point(grid, (2.5, 2.5, 0.))


def test_public_fixture_scene_marks_only_its_explicit_simulated_observations_known():
    # The actual public loader stays isolated from evaluator reference rasters.
    block = [r*32+c for r in range(8, 24) for c in range(8, 24)]
    surface, datum = observed_public_scene('SIMULATED-public-ground-fixture', block)
    assert datum == 'MOLA topography / DeltaGeoid (Mars 2000 Sphere, R=3396190 m); no Earth datum conversion'
    assert surface.map_version == 2 and surface.frame_id == 'map'
    assert simulated_ground_point(surface, (-14., -14.))[2] == -2571.199462890625
    assert surface.traversability[0, 0] == -1
    with pytest.raises(ValueError):
        simulated_ground_point(surface, surface.point((0, 0))[:2])
