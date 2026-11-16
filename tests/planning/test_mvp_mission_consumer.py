"""MVP-PL-01: actual Python consumers, synthetic inputs, no runtime activation.

The fixture explicitly enables illustrative manager admission to exercise its
independent cost audit. It is not model approval or an execution binding.
"""
from dataclasses import asdict, replace
import json

import numpy as np
import pytest
from mge_mission.manager import MissionManager
from mge_mission.models import estimate_segment
from mge_mission.types import AgentSnapshot, GoalRequest, Point, RouteDecision
from mge_planning.core import PlanRequest, ResourceBudget, RouteStatus, SearchLimits, plan_route
from mge_planning.resource_costs import Activity, scientific_plan_route
from tests.planning.terrain_fixtures import PROFILES, scene
from tests.planning.test_d07_twenty_metres import misses_box


def case(mode='FAST', agreed=True):
    grid, profile, _ = scene()
    grid = replace(grid, run_id='mvp-pl-01-synthetic', elevation_m=np.zeros((7, 9)),
                   traversability=np.zeros((7, 9)), sigma_m=np.zeros((7, 9)), resolution_m=4.)
    base, goal = Point(*grid.point((3, 1))), Point(*grid.point((3, 7)))
    # Test-local approval labels only; published profiles and coefficients unchanged.
    illustrative = {key: replace(value, approval_status='illustrative') for key, value in PROFILES.items()}
    manager = MissionManager(grid.run_id, illustrative, base, .01, allow_illustrative=True,
                             primary_service_activity='inspect', primary_service_time_s=10.,
                             planner_model_agreed=agreed)
    agent = AgentSnapshot(grid.run_id, 'human_1', 'human', base, 1000., 100., 100.)
    assert manager.update_map(grid.run_id, 1, 0.) and manager.update_agent(agent)
    assert manager.set_goal(GoalRequest('mvp-goal', grid.run_id, agent.agent_id, base, goal,
                                       mode, 1000., 100., 100., 10., 1., 1.)).accepted
    return grid, profile, manager, agent


def compute(grid, profile, pending, *, scientific=True, limits=None):
    """Test-only explicit translation; never infer the activity from seconds."""
    request = PlanRequest(pending.run_id, pending.request_id, pending.agent_id,
                          pending.agent_kind.lower(), pending.map_version, pending.start.coordinates(),
                          pending.goal.coordinates(), ResourceBudget(pending.agent_kind.lower(),
                          pending.time_budget_s, pending.energy_budget_wh, pending.reserve_wh,
                          pending.oxygen_budget_l, pending.reserve_oxygen_l),
                          return_to=pending.return_to.coordinates(), require_return=pending.require_return,
                          mode=pending.mode, service_time_s=pending.service_time_s,
                          reserve_time_s=pending.reserve_time_s)
    service = (Activity('pending-work', pending.service_activity, pending.service_time_s),) if pending.service_time_s else ()
    options = {'allow_continuous_start': True}
    if limits is not None:
        options['limits'] = limits
    if scientific:
        result = scientific_plan_route(terrain=grid, motion_profile=profile, request=request,
                       scientific_profile=PROFILES[pending.agent_id], activities=service, **options)
    else:
        result = plan_route(terrain=grid, profile=profile, request=request, **options)
    fields = ('run_id', 'request_id', 'route_id', 'agent_id', 'mode', 'map_version_used',
              'reason_code', 'detail', 'travel_time_s', 'energy_est_wh', 'oxygen_est_l',
              'min_clearance_m', 'reserve_time_s', 'reserve_wh', 'reserve_oxygen_l')
    decision = RouteDecision(**{name: getattr(result, name) for name in fields}, status=result.status.value,
                             outbound_path=tuple(Point(*p) for p in result.outbound_path),
                             return_path=tuple(Point(*p) for p in result.return_path))
    return result, decision


@pytest.mark.parametrize('mode', ['FAST', 'SAFE'])
def test_real_python_consumer_replans_from_remaining_pose_and_returns(mode, record_property):
    grid, profile, manager, agent = case(mode)
    first, decision = compute(grid, profile, manager.pending_plan())
    assert first.status == RouteStatus.FEASIBLE
    assert manager.snapshot().active_route is None  # Computation cannot authorize.
    assert manager.apply_plan(decision)
    assert manager.snapshot().mission_state == 'READY' and not manager.snapshot().mission_success
    pose = Point(agent.position.x + 1., agent.position.y, agent.position.z)
    spent = estimate_segment(PROFILES[agent.agent_id], agent.position.coordinates(), pose.coordinates())
    moved = replace(agent, position=pose, timestamp_sim_s=1.,
                    time_remaining_s=agent.time_remaining_s-spent.time_s,
                    energy_remaining_wh=agent.energy_remaining_wh-spent.energy_wh,
                    oxygen_remaining_l=agent.oxygen_remaining_l-spent.oxygen_l)
    assert manager.update_agent(moved)
    mask = grid.traversability.copy(); mask[3, 5] = 100
    updated = replace(grid, map_version=2, traversability=mask)
    assert manager.update_map(grid.run_id, 2, 2.)
    assert manager.snapshot().active_route is None
    pending = manager.pending_plan()
    assert pending.start == pose and pending.map_version == 2
    assert pending.energy_budget_wh == pytest.approx(moved.energy_remaining_wh)
    assert pending.time_budget_s == pytest.approx(moved.time_remaining_s)
    assert pending.oxygen_budget_l == pytest.approx(moved.oxygen_remaining_l)
    assert not manager.apply_plan(decision) and manager.pending_plan() == pending
    result, new_decision = compute(updated, profile, pending)
    assert result.status == RouteStatus.FEASIBLE and result.start_connector is not None
    assert result.outbound_path[0] == pose.coordinates()
    assert result.return_path[-1] == agent.position.coordinates()
    assert all(updated.cell(p) != (3, 5) for p in (*result.outbound_path, *result.return_path))
    radius = profile.radius_m + profile.localization_error_m
    for path in (result.outbound_path, result.return_path):
        for a, b in zip(path, path[1:]):
            assert misses_box(a, b, (20.-radius, 12.-radius), (24.+radius, 16.+radius))
    assert result.reserve_time_s >= pending.reserve_time_s
    assert result.reserve_wh >= pending.reserve_wh and result.reserve_oxygen_l >= pending.reserve_oxygen_l
    assert manager.snapshot().active_route is None
    assert manager.apply_plan(new_decision) and not manager.snapshot().mission_success
    assert manager.request_return('TEST_CONTINGENCY')
    returning = manager.pending_plan()
    assert not returning.require_return and returning.service_time_s == 0.
    back, back_decision = compute(updated, profile, returning)
    assert back.status == RouteStatus.FEASIBLE and not back.return_path
    assert returning.service_time_s == 0. and back.outbound_path[-1] == agent.position.coordinates()
    assert manager.apply_plan(back_decision)
    assert manager.snapshot().mission_state == 'RETURNING' and not manager.snapshot().mission_success
    record_property('synthetic_trace', json.dumps({'initial': asdict(decision), 'remaining': asdict(pending),
                    'replanned': asdict(new_decision), 'return': asdict(back_decision)}, allow_nan=False))


@pytest.mark.parametrize('field,value', [('run_id','other'), ('request_id','other'),
                                        ('agent_id','rover_1'), ('map_version_used',0)])
def test_real_scientific_candidate_identity_cannot_authorize_wrong_context(field, value):
    grid, profile, manager, _ = case()
    result, decision = compute(grid, profile, manager.pending_plan())
    assert result.status == RouteStatus.FEASIBLE
    assert not manager.apply_plan(replace(decision, **{field:value}))
    assert manager.snapshot().active_route is None and not manager.snapshot().mission_success


@pytest.mark.parametrize('scientific,agreed,reason', [(True,False,'MODEL_NOT_AGREED'),
                                                    (False,True,'MODEL_MISMATCH')])
def test_actual_candidate_preserves_model_gate_and_legacy_behavior(scientific, agreed, reason):
    grid, profile, manager, _ = case(agreed=agreed)
    result, decision = compute(grid, profile, manager.pending_plan(), scientific=scientific)
    assert result.status == RouteStatus.FEASIBLE
    assert not manager.apply_plan(decision)
    assert manager.snapshot().reason_code == reason and manager.snapshot().active_route is None


@pytest.mark.parametrize('field', ['time_budget_s','energy_budget_wh','oxygen_budget_l'])
def test_actual_candidate_cannot_spend_reserved_resource(field):
    grid, profile, manager, _ = case()
    pending = manager.pending_plan()
    reserve = {'time_budget_s':pending.reserve_time_s, 'energy_budget_wh':pending.reserve_wh,
               'oxygen_budget_l':pending.reserve_oxygen_l}[field]
    result, decision = compute(grid, profile, replace(pending, **{field:reserve}))
    assert result.status == RouteStatus.INSUFFICIENT_BUDGET
    assert not manager.apply_plan(decision) and manager.snapshot().active_route is None


def test_actual_search_limit_is_inconclusive_and_never_authorized():
    grid, profile, manager, _ = case()
    result, decision = compute(grid, profile, manager.pending_plan(), limits=SearchLimits(max_labels=1))
    assert result.status == RouteStatus.UNKNOWN and result.reason_code == 'SEARCH_LIMIT'
    assert not manager.apply_plan(decision)
    assert manager.snapshot().reason_code == 'SEARCH_LIMIT' and manager.snapshot().active_route is None
