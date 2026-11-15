"""Remaining availability admission, not a consumption ledger or ROS authority."""
from dataclasses import replace

import pytest

from mge_planning.core import RouteStatus, plan_route
from mge_planning.replan import EventKind, MissionPhase, ReplanAction, RemainingResources
from tests.planning.test_replan_policy import scene, policy, evaluate


@pytest.mark.parametrize('kind', ['human', 'rover'])
@pytest.mark.parametrize('live', [False, True])
def test_constant_then_travel_decrease_preserves_supplied_availability(kind, live):
    grid, profile, start, moved, *_ = scene(kind)
    if live:
        start = replace(start, remaining=RemainingResources(**vars(start.remaining)))
        moved = replace(moved, remaining=RemainingResources(**vars(moved.remaining)))
    p = policy()
    assert evaluate(p, grid, profile, start).action == ReplanAction.KEEP
    assert evaluate(p, grid, profile, start, EventKind.TICK, 'constant', 1.).action == ReplanAction.KEEP
    result = evaluate(p, grid, profile, moved, EventKind.TASK, 'travel', 10.)
    assert result.candidate.status == RouteStatus.FEASIBLE
    assert result.request.start == moved.pose and result.candidate.start_connector is not None
    assert result.request.budget.energy_wh == moved.remaining.energy_wh
    assert result.request.budget.time_s == moved.remaining.time_s
    assert result.request.budget.reserve_wh == start.mission.budget.reserve_wh
    assert result.request.budget.oxygen_l == moved.remaining.oxygen_l


@pytest.mark.parametrize('kind,field,reason', [
    ('human', 'time_s', 'TIME_AVAILABILITY_INCREASE'),
    ('human', 'energy_wh', 'ENERGY_AVAILABILITY_INCREASE'),
    ('human', 'oxygen_l', 'OXYGEN_AVAILABILITY_INCREASE'),
    ('rover', 'time_s', 'TIME_AVAILABILITY_INCREASE'),
    ('rover', 'energy_wh', 'ENERGY_AVAILABILITY_INCREASE')])
@pytest.mark.parametrize('live', [False, True])
def test_increase_rejected_before_search_and_cannot_raise_future_bound(kind, field, reason, live, monkeypatch):
    grid, profile, _, moved, *_ = scene(kind)
    if live:
        moved = replace(moved, remaining=RemainingResources(**vars(moved.remaining)))
    p = policy()
    evaluate(p, grid, profile, moved)
    import mge_planning.replan as module
    monkeypatch.setattr(module, 'plan_route', lambda **kwargs: pytest.fail('Increased availability reached search'))
    bad = replace(moved, remaining=replace(moved.remaining, **{field: getattr(moved.remaining, field)+1.}))
    result = evaluate(p, grid, profile, bad, EventKind.RESOURCES, 'increase', 1.)
    assert result.action == ReplanAction.UNKNOWN and result.reason_code == reason
    assert result.invalidate_active and result.request is result.candidate is None
    # Reject the same inflated value again; an invalid update cannot ratchet up.
    again = evaluate(p, grid, profile, bad, EventKind.TICK, 'retry', 2.)
    assert again.reason_code == reason and again.request is None
    corrected = evaluate(p, grid, profile, moved, EventKind.TICK, 'corrected', 3.)
    assert corrected.action == ReplanAction.STOP_REQUIRED and corrected.invalidate_active


@pytest.mark.parametrize('kind', ['human', 'rover'])
def test_partial_service_decreases_are_not_debited_again(kind):
    grid, profile, start, *_ = scene(kind)
    p = policy()
    evaluate(p, grid, profile, start)
    service = replace(start, phase=MissionPhase.SERVICE, pose=start.mission.goal,
                      next_waypoint=1, service_remaining_s=2.,
                      remaining=replace(start.remaining, time_s=70., energy_wh=70.,
                                        oxygen_l=20. if kind == 'human' else None))
    first = evaluate(p, grid, profile, service, EventKind.TASK, 'service1', 10.)
    partial = replace(service, service_remaining_s=1., remaining=replace(service.remaining,
                      time_s=69., energy_wh=69.9, oxygen_l=19.8 if kind == 'human' else None))
    result = evaluate(p, grid, profile, partial, EventKind.TASK, 'service2', 20.)
    assert first.request.service_time_s == 2. and result.request.service_time_s == 1.
    assert result.request.budget is partial.remaining
    assert result.candidate.status == RouteStatus.FEASIBLE
    assert result.candidate.travel_time_s == pytest.approx(1.+39./2.)


@pytest.mark.parametrize('kind', ['human', 'rover'])
def test_authorized_adoption_recovers_latch_but_never_resets_bound(kind):
    grid, profile, _, moved, *_ = scene(kind)
    p = policy()
    proposal = evaluate(p, grid, profile, moved, EventKind.TASK)
    bad = replace(moved, remaining=replace(moved.remaining, energy_wh=moved.remaining.energy_wh+1.))
    assert evaluate(p, grid, profile, bad, EventKind.RESOURCES, 'bad', 1.).invalidate_active
    adopted = replace(bad, active_request=proposal.request, active_route=proposal.candidate, next_waypoint=1)
    rejected = evaluate(p, grid, profile, adopted, EventKind.TICK, 'bad-adopt', 2.)
    assert rejected.reason_code == 'ENERGY_AVAILABILITY_INCREASE' and rejected.invalidate_active
    adopted = replace(adopted, remaining=moved.remaining)
    recovered = evaluate(p, grid, profile, adopted, EventKind.TICK, 'adopt', 3.)
    assert recovered.action == ReplanAction.KEEP and not recovered.invalidate_active
    assert evaluate(p, grid, profile, replace(adopted, remaining=bad.remaining),
                    EventKind.TICK, 'reset-after-adoption', 4.).reason_code == 'ENERGY_AVAILABILITY_INCREASE'


@pytest.mark.parametrize('kind', ['human', 'rover'])
@pytest.mark.parametrize('new_run', [False, True])
def test_new_mission_needs_new_policy_instance_and_its_own_allocation(kind, new_run):
    grid, profile, start, moved, *_ = scene(kind)
    p = policy()
    evaluate(p, grid, profile, moved)
    run = 'new-authorized-run' if new_run else grid.run_id
    new_grid = replace(grid, run_id=run)
    mission = replace(start.mission, run_id=run, request_id='new-authorized-mission',
                      budget=replace(start.remaining, energy_wh=120.))
    route = plan_route(terrain=new_grid, profile=profile, request=mission)
    fresh = replace(start, mission=mission, active_request=mission, active_route=route, remaining=mission.budget)
    old = evaluate(p, new_grid, profile, fresh, EventKind.TICK, 'new', 1.)
    assert old.reason_code == ('POLICY_SCOPE_MISMATCH' if new_run else 'MISSION_TEMPLATE_CHANGED')
    assert old.invalidate_active and old.request is None
    accepted = evaluate(policy(), new_grid, profile, fresh)
    assert accepted.action == ReplanAction.KEEP and not accepted.invalidate_active
    excessive = replace(fresh, remaining=replace(fresh.remaining, energy_wh=121.))
    assert evaluate(policy(), new_grid, profile, excessive).reason_code == 'ENERGY_AVAILABILITY_INCREASE'


@pytest.mark.parametrize('kind', ['human', 'rover'])
def test_duplicate_and_obsolete_events_do_not_erase_or_bypass_bound(kind):
    grid, profile, _, moved, *_ = scene(kind)
    p = policy()
    evaluate(p, grid, profile, moved)
    dropped = replace(moved, remaining=replace(moved.remaining, energy_wh=moved.remaining.energy_wh-1.))
    assert evaluate(p, grid, profile, dropped, event_id='e1', now=1.).request is None
    bad = evaluate(p, grid, profile, moved, event_id='e1', now=2.)
    assert bad.reason_code == 'ENERGY_AVAILABILITY_INCREASE' and bad.invalidate_active
    stale = evaluate(p, grid, profile, dropped, EventKind.MAP, 'obsolete', 3., version=0)
    assert stale.reason_code == 'EVENT_MAP_MISMATCH' and stale.invalidate_active
    assert evaluate(p, grid, profile, moved, EventKind.TICK, 'reset', 4.).reason_code == 'ENERGY_AVAILABILITY_INCREASE'


@pytest.mark.parametrize('kind', ['human', 'rover'])
def test_exhausted_reserve_still_stops_without_search(kind):
    grid, profile, _, moved, *_ = scene(kind)
    p = policy()
    evaluate(p, grid, profile, moved)
    depleted = RemainingResources(kind, 4., 4., moved.remaining.reserve_wh,
                                  1. if kind == 'human' else None,
                                  moved.remaining.reserve_oxygen_l)
    result = evaluate(p, grid, profile, replace(moved, remaining=depleted), EventKind.RESOURCES, 'depleted', 1.)
    assert result.action == ReplanAction.STOP_REQUIRED and result.request is None
    assert result.reason_code == 'TIME_RESERVE_DEPLETED' and result.invalidate_active
    reset = evaluate(p, grid, profile, moved, EventKind.TICK, 'restore-after-depletion', 2.)
    assert reset.reason_code == 'TIME_AVAILABILITY_INCREASE' and reset.request is None
