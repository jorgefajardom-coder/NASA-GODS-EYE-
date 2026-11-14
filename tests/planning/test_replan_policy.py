"""Synthetic F03.4 event integration, not ROS or supervisor execution evidence."""

from dataclasses import replace

import numpy as np
import pytest

from mge_planning.core import RouteStatus, SearchLimits, plan_route
from mge_planning.replan import (
    EventKind, MissionPhase, ReplanAction, ReplanConfig, ReplanEvent,
    ReplanPolicy, ReplanState, _segment_issue,
)
from mge_planning.core import _Geometry
from tests.planning.test_d07_twenty_metres import setup_case, costs, length, misses_box


def scene(kind="human"):
    grid, profile, mission, route, travelled, used, current, obstacle = setup_case(kind)
    state = ReplanState(mission, mission, route, MissionPhase.OUTBOUND,
                        mission.start, 1, mission.budget, mission.service_time_s)
    moved = replace(state, pose=travelled[-1], next_waypoint=7, remaining=current.budget)
    return grid, profile, state, moved, obstacle, travelled, used


def policy(**changes):
    return ReplanPolicy(ReplanConfig(**(dict(deviation_enter_m=1., deviation_exit_m=.4,
                                             min_interval_s=10., immediate_horizon_m=3.) | changes)))


def evaluate(p, grid, profile, state, kind=EventKind.MAP, event_id="e1", now=0., version=None):
    return p.evaluate(terrain=grid, profile=profile, state=state,
                      event=ReplanEvent(event_id, grid.run_id, grid.map_version if version is None else version, kind),
                      now_s=now)


def block(grid, cell):
    mask = grid.traversability.copy()
    mask[cell] = 100
    return replace(grid, map_version=grid.map_version+1, traversability=mask)


@pytest.mark.parametrize("agent", ["human", "rover"])
def test_automatic_d07_after_twenty_metres_uses_current_pose_map_remaining_and_return(agent):
    grid, profile, start, moved, obstacle, travelled, used = scene(agent)
    p = policy()
    assert evaluate(p, grid, profile, start).action == ReplanAction.KEEP
    assert length(travelled) == pytest.approx(20.)
    revised = block(grid, obstacle)
    result = evaluate(p, revised, profile, moved, event_id="observation", now=10.)
    assert result.action == ReplanAction.REPLAN
    assert result.invalidate_active and result.trigger_reason == "CORRIDOR_BLOCKED"
    request, candidate = result.request, result.candidate
    assert request.start == moved.pose == (24.5, 13.5, 0.)
    assert request.map_version == candidate.map_version_used == 2
    assert request.budget is moved.remaining  # No second debit or reserve subtraction.
    assert request.service_time_s == start.mission.service_time_s
    assert candidate.status == RouteStatus.FEASIBLE
    assert candidate.outbound_path[0] == moved.pose
    assert start.pose not in candidate.outbound_path
    assert candidate.start_connector.distance_m == pytest.approx(1.)
    assert candidate.return_path[-1] == start.mission.return_to
    row, col = obstacle
    radius = profile.radius_m+profile.localization_error_m
    for path in (candidate.outbound_path, candidate.return_path):
        for a, b in zip(path, path[1:]):
            assert misses_box(a, b, (col*3-radius, row*3-radius), ((col+1)*3+radius, (row+1)*3+radius))
    totals = costs(candidate.outbound_path+candidate.return_path[1:], profile, service_s=request.service_time_s)
    assert candidate.travel_time_s == pytest.approx(totals["time_s"])
    assert candidate.energy_est_wh == pytest.approx(totals["energy_wh"])
    assert used["time_s"] + candidate.travel_time_s + request.reserve_time_s <= start.remaining.time_s
    assert used["energy_wh"] + candidate.energy_est_wh + request.budget.reserve_wh <= start.remaining.energy_wh
    if agent == "human":
        assert used["oxygen_l"] + candidate.oxygen_est_l + request.budget.reserve_oxygen_l <= start.remaining.oxygen_l
    # Candidate is not auto-authorized, even on the next harmless tick.
    waiting = evaluate(p, revised, profile, moved, EventKind.TICK, "wait", 11.)
    assert waiting.action == ReplanAction.STOP_REQUIRED and waiting.request is None
    # Mission explicitly adopts the candidate; cursor resets for its new leg.
    accepted = replace(moved, active_route=candidate, active_request=request, next_waypoint=1)
    assert evaluate(p, revised, profile, accepted, EventKind.TICK, "adopt", 12.).action == ReplanAction.KEEP


def test_irrelevant_update_including_travelled_prefix_keeps_pending_route():
    grid, profile, start, moved, _, _, _ = scene()
    p = policy()
    evaluate(p, grid, profile, start)
    # Behind the actor AND away from the future return corridor.
    revised = block(grid, (0, 0))
    result = evaluate(p, revised, profile, moved, event_id="irrelevant", now=1.)
    assert result.action == ReplanAction.KEEP and not result.invalidate_active
    assert result.request is None and result.map_version == 2


@pytest.mark.parametrize("change", ["sigma", "nodata", "unknown", "margin", "height"])
def test_uncertainty_margin_and_surface_changes_invalidate_pending_segments(change):
    grid, profile, start, moved, obstacle, _, _ = scene()
    p = policy()
    evaluate(p, grid, profile, start)
    if change == "margin":
        # Occupied neighbour overlaps the swept radius though all path cells stay free.
        profile = replace(profile, radius_m=1.6, localization_error_m=0.)
        revised = block(grid, (obstacle[0]+1, obstacle[1]))
    elif change == "height":
        h = grid.elevation_m.copy(); h[obstacle] = 2.
        revised = replace(grid, map_version=2, elevation_m=h)
    elif change == "unknown":
        mask = grid.traversability.copy(); mask[obstacle] = -1
        revised = replace(grid, map_version=2, traversability=mask)
    else:
        h = grid.elevation_m.copy()
        sigma = np.zeros(h.shape)
        if change == "sigma":
            sigma[obstacle] = 4.
            profile = replace(profile, max_sigma_m=1.)
        else:
            h[obstacle] = np.nan
        revised = replace(grid, map_version=2, elevation_m=h, sigma_m=sigma)
    result = evaluate(p, revised, profile, moved, event_id="change", now=1.)
    assert result.invalidate_active and result.request is not None
    assert result.action != ReplanAction.KEEP


def test_segment_checker_rejects_interior_obstacle_with_clear_endpoints():
    grid, profile, *_ = scene()
    revised = block(grid, (4, 10))
    a, b = (25.5, 13.5, 0.), (40.5, 13.5, 0.)
    assert revised.traversability[revised.cell(a)] == revised.traversability[revised.cell(b)] == 0
    assert _segment_issue(_Geometry(revised, profile), a, b, 10000) == "CORRIDOR_BLOCKED"


def test_deviation_has_enter_exit_hysteresis_and_deferred_task_runs_on_tick():
    grid, profile, start, moved, *_ = scene()
    p = policy()
    evaluate(p, grid, profile, start)
    out = replace(moved, pose=(24.5, 14.7, 0.))
    first = evaluate(p, grid, profile, out, EventKind.POSE, "off", 10.)
    assert first.action == ReplanAction.REPLAN and first.reason_code == "CORRIDOR_DEVIATION"
    # Still outside exit threshold, even though inside enter threshold.
    between = replace(out, pose=(24.5, 14.2, 0.))
    deferred = evaluate(p, grid, profile, between, EventKind.POSE, "jitter", 11.)
    assert deferred.reason_code == "REPLAN_DEFERRED" and deferred.request is None
    settled = evaluate(p, grid, profile, moved, EventKind.TICK, "settle", 20.)
    assert settled.request is None and settled.action == ReplanAction.KEEP  # Deviation cleared; no stale search.
    assert evaluate(p, grid, profile, moved, EventKind.TICK, "quiet", 21.).action == ReplanAction.KEEP
    task = evaluate(p, grid, profile, moved, EventKind.TASK, "task", 22.)
    assert task.request is not None and task.reason_code == "TASK_REEVALUATION"
    queued = evaluate(p, grid, profile, moved, EventKind.TASK, "task-next", 23.)
    assert queued.reason_code == "REPLAN_DEFERRED"
    tick = evaluate(p, grid, profile, moved, EventKind.TICK, "flush", 32.)
    assert tick.request is not None and tick.trigger_reason == "TASK_REEVALUATION"


def test_duplicate_events_do_not_repeat_search_or_lose_urgent_invalidation():
    grid, profile, start, moved, obstacle, *_ = scene()
    p = policy()
    first = evaluate(p, grid, profile, start, EventKind.TASK)
    duplicate = evaluate(p, grid, profile, start, EventKind.TASK, now=1.)
    assert first.request is not None and duplicate.request is None
    revised = block(grid, (4, 8))  # At the actor, not just a distant route cell.
    # Reused event id cannot suppress a freshly discovered current hazard.
    danger = evaluate(p, revised, profile, moved, EventKind.TASK, now=2.)
    assert danger.invalidate_active and danger.action != ReplanAction.KEEP


def test_danger_and_next_segment_obstacle_bypass_cooldown_and_latch_stop():
    grid, profile, start, moved, *_ = scene()
    p = policy()
    evaluate(p, grid, profile, start, EventKind.TASK)
    danger = evaluate(p, grid, profile, moved, EventKind.DANGER, "danger", 1.)
    assert danger.action == ReplanAction.STOP_REQUIRED and danger.request is None
    assert evaluate(p, grid, profile, moved, EventKind.TICK, "tick", 2.).action == ReplanAction.STOP_REQUIRED
    revised = block(grid, (4, 9))  # Next edge after the 1 m attachment.
    stop = evaluate(p, revised, profile, moved, event_id="near", now=3.)
    assert stop.action == ReplanAction.STOP_REQUIRED
    assert stop.request is not None and stop.candidate.status == RouteStatus.FEASIBLE
    assert stop.invalidate_active  # Feasible replacement does not authorize motion.


def test_stale_map_and_event_never_start_search():
    grid, profile, start, moved, *_ = scene()
    p = policy()
    evaluate(p, grid, profile, start)
    revised = block(grid, (0, 0))
    mismatch = evaluate(p, revised, profile, moved, event_id="old-event", now=1., version=1)
    assert mismatch.action == ReplanAction.UNKNOWN and mismatch.request is None and mismatch.invalidate_active
    stale = evaluate(p, grid, profile, moved, event_id="old-map", now=2.)
    assert stale.reason_code == "STALE_MAP" and stale.invalidate_active


def test_insufficient_remaining_resources_require_stop_with_no_executable_candidate():
    grid, profile, start, moved, *_ = scene()
    p = policy()
    evaluate(p, grid, profile, start)
    moved = replace(moved, remaining=replace(moved.remaining, energy_wh=6.))
    result = evaluate(p, grid, profile, moved, EventKind.RESOURCES, "low", 1.)
    assert result.action == ReplanAction.STOP_REQUIRED and result.invalidate_active
    assert result.trigger_reason == "REMAINING_BUDGET_INSUFFICIENT"
    assert result.request.budget == moved.remaining
    assert result.candidate.status == RouteStatus.INSUFFICIENT_BUDGET


def test_service_only_charges_remaining_activity_then_return_does_not_repeat_goal():
    grid, profile, start, *_ = scene()
    p = policy()
    evaluate(p, grid, profile, start)
    at_goal = replace(start, pose=start.mission.goal, phase=MissionPhase.SERVICE,
                      service_remaining_s=1., next_waypoint=1,
                      remaining=replace(start.remaining, time_s=70., energy_wh=70., oxygen_l=20.))
    service = evaluate(p, grid, profile, at_goal, EventKind.TASK, "service", 10.)
    assert service.request.service_time_s == 1. and service.request.budget == at_goal.remaining
    assert service.candidate.travel_time_s == pytest.approx(1+39/2)
    assert service.candidate.energy_est_wh == pytest.approx(39*.5+90/3600)
    # A RETURN request uses goal=base and no second return/service phase.
    returning = replace(at_goal, phase=MissionPhase.RETURN, pose=(35.5, 13.5, 0.),
                        next_waypoint=3, service_remaining_s=0.)
    back = evaluate(p, grid, profile, returning, EventKind.TASK, "return", 20.)
    assert back.candidate_phase == MissionPhase.RETURN
    assert back.request.start == returning.pose
    assert back.request.goal == start.mission.return_to and not back.request.require_return
    assert back.request.service_time_s == 0.
    assert not back.candidate.return_path
    assert back.candidate.outbound_path[-1] == start.mission.return_to
    assert start.mission.goal not in back.candidate.outbound_path
    assert back.candidate.travel_time_s == pytest.approx(length(back.candidate.outbound_path)/2)
    # Mission installs single-leg result; policy reads outbound_path as RETURN.
    accepted = replace(returning, active_request=back.request, active_route=back.candidate, next_waypoint=1)
    assert evaluate(p, grid, profile, accepted, EventKind.TICK, "adopt-return", 21.).action == ReplanAction.KEEP


def test_completed_service_transitions_to_single_leg_return_candidate():
    grid, profile, start, *_ = scene()
    state = replace(start, phase=MissionPhase.SERVICE, pose=start.mission.goal,
                    service_remaining_s=0., next_waypoint=1)
    result = evaluate(policy(), grid, profile, state, EventKind.TASK)
    assert result.candidate_phase == MissionPhase.RETURN and result.request.service_time_s == 0
    assert result.candidate.travel_time_s == pytest.approx(39/2)


@pytest.mark.parametrize("problem", ["cursor", "service", "identity", "surface_mutation", "time", "geometry"])
def test_bad_context_fails_closed(problem):
    grid, profile, start, moved, *_ = scene()
    p = policy()
    evaluate(p, grid, profile, start)
    if problem == "cursor":
        moved = replace(moved, next_waypoint=999)
    elif problem == "service":
        moved = replace(moved, phase=MissionPhase.RETURN, service_remaining_s=1.)
    elif problem == "identity":
        moved = replace(moved, remaining=replace(moved.remaining, agent_kind="rover", oxygen_l=None, reserve_oxygen_l=None))
    elif problem == "surface_mutation":
        h = grid.elevation_m.copy(); h[0, 0] = 1.
        grid = replace(grid, elevation_m=h)  # Same version, forbidden.
    elif problem == "time":
        evaluate(p, grid, profile, moved, now=2., event_id="later")
    else:
        grid = replace(grid, resolution_m=4., map_version=2)
    result = evaluate(p, grid, profile, moved, event_id="bad", now=1.)
    assert result.action == ReplanAction.UNKNOWN and result.invalidate_active and result.request is None


def test_progress_rollback_and_retired_route_cannot_reactivate():
    grid, profile, start, moved, obstacle, *_ = scene()
    p = policy()
    evaluate(p, grid, profile, moved)
    rollback = evaluate(p, grid, profile, start, event_id="rollback", now=1.)
    assert rollback.reason_code == "PROGRESS_ROLLBACK"
    revised = block(grid, obstacle)
    proposal = evaluate(p, revised, profile, moved, event_id="new-map", now=2.)
    accepted = replace(moved, active_route=proposal.candidate, active_request=proposal.request, next_waypoint=1)
    evaluate(p, revised, profile, accepted, event_id="adopt", now=3.)
    old = evaluate(p, revised, profile, moved, event_id="old-route", now=4.)
    assert old.reason_code == "STALE_ROUTE_ADOPTION" and old.invalidate_active


def test_validation_and_search_work_bounds_return_unknown():
    grid, profile, start, moved, obstacle, *_ = scene()
    p = policy(max_segment_samples=2)
    result = evaluate(p, grid, profile, start)
    assert result.action == ReplanAction.UNKNOWN and result.reason_code == "VALIDATION_LIMIT"
    p = ReplanPolicy(policy().config, limits=SearchLimits(max_labels=1, timeout_s=10.))
    result = evaluate(p, block(grid, obstacle), profile, moved)
    assert result.action == ReplanAction.UNKNOWN and result.candidate.reason_code == "SEARCH_LIMIT"


def test_distinct_tasks_recheck_even_when_pose_and_resources_are_unchanged():
    grid, profile, start, *_ = scene()
    p = policy()
    first = evaluate(p, grid, profile, start, EventKind.TASK, "task-1")
    second = evaluate(p, grid, profile, start, EventKind.TASK, "task-2", 10.)
    assert first.request is not None and second.request is not None
    assert first.request.request_id != second.request.request_id


def test_service_completion_cannot_be_rolled_back():
    grid, profile, start, *_ = scene()
    p = policy()
    state = replace(start, phase=MissionPhase.SERVICE, pose=start.mission.goal,
                    service_remaining_s=1., next_waypoint=1)
    evaluate(p, grid, profile, state)
    result = evaluate(p, grid, profile, replace(state, service_remaining_s=2.), event_id="bad-service", now=1.)
    assert result.reason_code == "SERVICE_PROGRESS_ROLLBACK" and result.request is None


def test_obstacle_behind_actor_that_blocks_future_return_is_relevant():
    grid, profile, start, moved, *_ = scene()
    result = evaluate(policy(), block(grid, (4, 3)), profile, moved)
    assert result.action == ReplanAction.REPLAN and result.invalidate_active
    assert result.candidate.status == RouteStatus.FEASIBLE


def test_new_hazard_during_deferred_task_is_not_delayed():
    grid, profile, start, moved, *_ = scene()
    p = policy()
    evaluate(p, grid, profile, start, EventKind.TASK, "task-1")
    deferred = evaluate(p, grid, profile, moved, EventKind.TASK, "task-2", 1.)
    assert deferred.reason_code == "REPLAN_DEFERRED"
    result = evaluate(p, block(grid, (4, 9)), profile, moved, event_id="hazard", now=2.)
    assert result.action == ReplanAction.STOP_REQUIRED and result.request is not None


def test_hazard_at_actor_and_time_reserve_exhaustion_fail_closed():
    grid, profile, start, moved, *_ = scene()
    result = evaluate(policy(), block(grid, (4, 8)), profile, moved)
    assert result.action == ReplanAction.STOP_REQUIRED and result.invalidate_active
    assert result.candidate.status == RouteStatus.NO_PATH
    result = evaluate(policy(), grid, profile,
                      replace(moved, remaining=replace(moved.remaining, time_s=4.)))
    assert result.action == ReplanAction.STOP_REQUIRED and result.reason_code == "TIME_RESERVE_DEPLETED"


def test_foreign_run_and_stale_replacement_are_not_adopted():
    grid, profile, start, moved, *_ = scene()
    p = policy()
    evaluate(p, grid, profile, start)
    new = replace(start.active_request, request_id="other")
    other = plan_route(allow_continuous_start=True, terrain=grid, request=new, profile=profile)
    revised = block(grid, (0, 0))
    result = evaluate(p, revised, profile, replace(moved, active_request=new, active_route=other), now=1.)
    assert result.reason_code == "STALE_ROUTE_ADOPTION"
    result = evaluate(policy(), replace(grid, run_id="foreign"), profile, start)
    assert result.reason_code == "RUN_MISMATCH" and result.request is None


def test_no_alternative_automatic_replan_and_small_work_limits():
    grid, profile, start, moved, obstacle, *_ = scene()
    mask = grid.traversability.copy()
    mask[:, obstacle[1]] = 100
    result = evaluate(policy(), replace(grid, map_version=2, traversability=mask), profile, moved)
    assert result.action == ReplanAction.REPLAN and result.reason_code == "CONTINGENCY_RETURN"
    assert result.primary_candidate.status == RouteStatus.NO_PATH
    assert result.candidate_phase == MissionPhase.RETURN and result.candidate.status == RouteStatus.FEASIBLE
    result = evaluate(policy(max_route_segments=2), grid, profile, start)
    assert result.action == ReplanAction.UNKNOWN and result.reason_code == "VALIDATION_LIMIT"


def test_cell_crossing_near_corner_cannot_skip_a_steep_cell():
    grid, profile, *_ = scene()
    heights = grid.elevation_m.copy()
    # Segment enters (row 4,col 4) for only a tiny length near its NW corner.
    heights[4, 4] = 3.
    changed = replace(grid, elevation_m=heights)
    a, b = (11.9, 14.99, 0.), (12.1, 15.009, 0.)
    assert _segment_issue(_Geometry(changed, profile), a, b, 1000) == "TRANSITION_INVALID"


def test_new_route_adoption_cannot_undo_mission_phase():
    grid, profile, start, *_ = scene()
    p = policy()
    returning = replace(start, phase=MissionPhase.RETURN, pose=(35.5, 13.5, 0.),
                        next_waypoint=3, service_remaining_s=0.)
    proposal = evaluate(p, grid, profile, returning, EventKind.TASK)
    bad = replace(returning, active_request=proposal.request, active_route=proposal.candidate,
                  phase=MissionPhase.OUTBOUND, next_waypoint=1)
    result = evaluate(p, grid, profile, bad, event_id="bad-phase", now=1.)
    assert result.reason_code == "PHASE_ROLLBACK" and result.candidate is None


def test_centred_height_change_cannot_teleport_the_actor_vertically():
    grid, profile, start, *_ = scene()
    heights = grid.elevation_m.copy()
    heights[grid.cell(start.pose)] = .1
    revised = replace(grid, map_version=2, elevation_m=heights)
    result = evaluate(policy(), revised, profile, start, EventKind.TASK)
    assert result.action == ReplanAction.UNKNOWN
    assert result.reason_code == "INVALID_START_Z" and result.candidate is None


def test_feasible_soft_proposal_does_not_clear_a_previously_latched_stop():
    grid, profile, start, moved, *_ = scene()
    p = policy()
    evaluate(p, grid, profile, start)
    stopped = evaluate(p, grid, profile, moved, EventKind.DANGER, "stop", 1.)
    assert stopped.invalidate_active
    proposal = evaluate(p, grid, profile, moved, EventKind.TASK, "new-task", 20.)
    assert proposal.candidate.status == RouteStatus.FEASIBLE
    assert proposal.invalidate_active  # Still latched; proposal is not adoption.


def test_unchanged_mission_template_and_profile_are_explicit_input_contracts():
    grid, profile, start, *_ = scene()
    p = policy()
    evaluate(p, grid, profile, start)
    result = evaluate(p, grid, profile, replace(start, mission=replace(start.mission, goal=(40.5, 13.5, 0.))),
                      EventKind.TASK, "new-objective", 1.)
    assert result.reason_code == "MISSION_TEMPLATE_CHANGED" and result.candidate is None


@pytest.mark.parametrize("change", [dict(deviation_exit_m=1.), dict(min_interval_s=-1.),
                                  dict(max_route_segments=0), dict(immediate_horizon_m=float("nan"))])
def test_policy_configuration_rejects_invalid_thresholds(change):
    with pytest.raises(ValueError):
        policy(**change)


@pytest.mark.parametrize("agent", ["human", "rover"])
@pytest.mark.parametrize("case", ["detour", "base_only", "neither", "uncertain"])
def test_outbound_contingency_distinguishes_goal_detour_return_and_no_escape(agent, case):
    grid, profile, start, moved, obstacle, travelled, used = scene(agent)
    p = policy()
    evaluate(p, grid, profile, start)
    mask = grid.traversability.copy()
    if case == "detour":
        mask[obstacle] = 100
    else:
        mask[:, obstacle[1]] = 100
        if case in ("neither", "uncertain"):
            mask[:, 5] = 100 if case == "neither" else -1  # Between current pose and base.
    revised = replace(grid, map_version=2, traversability=mask)
    result = evaluate(p, revised, profile, moved, event_id="contingency", now=10.)
    assert length(travelled) == pytest.approx(20.)
    assert result.invalidate_active
    if case == "detour":
        assert result.action == ReplanAction.REPLAN and result.primary_candidate is None
        assert result.request.goal == start.mission.goal and result.request.require_return
        assert result.candidate_phase == MissionPhase.OUTBOUND
        assert result.candidate.return_path[-1] == start.mission.return_to
    elif case == "uncertain":
        assert result.action == ReplanAction.UNKNOWN and not result.candidate.outbound_path
        assert result.primary_candidate.status == RouteStatus.NO_PATH
        assert result.candidate.status == RouteStatus.UNKNOWN
    elif case == "neither":
        assert result.action == ReplanAction.STOP_REQUIRED
        assert result.primary_candidate.status == result.candidate.status == RouteStatus.NO_PATH
        assert not result.candidate.outbound_path and not result.candidate.route_id
    else:
        assert result.action == ReplanAction.REPLAN and result.reason_code == "CONTINGENCY_RETURN"
        assert result.primary_request.goal == start.mission.goal
        assert result.primary_candidate.status == RouteStatus.NO_PATH
        assert result.candidate_phase == MissionPhase.RETURN
        assert result.request.start == moved.pose and result.request.goal == start.mission.return_to
        assert result.request.budget is moved.remaining and result.request.map_version == 2
        assert result.request.service_time_s == 0. and not result.request.require_return
        assert not result.candidate.return_path
        path = result.candidate.outbound_path
        assert path[0] == moved.pose and path[-1] == start.mission.return_to
        assert result.candidate.start_connector is not None
        assert start.mission.goal not in path
        independent = costs(path, profile)
        assert result.candidate.travel_time_s == pytest.approx(independent["time_s"])
        assert result.candidate.energy_est_wh == pytest.approx(independent["energy_wh"])
        assert used["energy_wh"]+result.candidate.energy_est_wh+moved.remaining.reserve_wh <= start.remaining.energy_wh
        if agent == "human":
            assert result.candidate.oxygen_est_l == pytest.approx(independent["oxygen_l"])
        waiting = evaluate(p, revised, profile, moved, EventKind.TICK, "wait-contingency", 11.)
        assert waiting.action == ReplanAction.STOP_REQUIRED and waiting.request is None
        # Only mission can enact the phase transition and abandon the service.
        accepted = replace(moved, phase=MissionPhase.RETURN, service_remaining_s=0.,
                           active_request=result.request, active_route=result.candidate, next_waypoint=1)
        assert evaluate(p, revised, profile, accepted, EventKind.TICK, "adopt-contingency", 12.).action == ReplanAction.KEEP


@pytest.mark.parametrize("agent", ["human", "rover"])
def test_budget_failure_can_fund_direct_contingency_return_without_service(agent):
    grid, profile, start, moved, *_ = scene(agent)
    moved = replace(moved, remaining=replace(moved.remaining, energy_wh=20.))
    result = evaluate(policy(), grid, profile, moved, EventKind.RESOURCES)
    assert result.primary_candidate.status == RouteStatus.INSUFFICIENT_BUDGET
    assert result.candidate.status == RouteStatus.FEASIBLE
    assert result.candidate_phase == MissionPhase.RETURN and result.invalidate_active
    assert result.action == ReplanAction.STOP_REQUIRED  # Resource danger is still urgent.
    assert result.request.service_time_s == 0. and result.request.budget.energy_wh == 20.


@pytest.mark.parametrize("agent", ["human", "rover"])
def test_failed_contingency_also_respects_remaining_budget(agent):
    grid, profile, start, moved, obstacle, *_ = scene(agent)
    mask = grid.traversability.copy(); mask[:, obstacle[1]] = 100
    moved = replace(moved, remaining=replace(moved.remaining, energy_wh=6.))
    result = evaluate(policy(), replace(grid, map_version=2, traversability=mask), profile, moved)
    assert result.primary_candidate.status == RouteStatus.NO_PATH
    assert result.candidate.status == RouteStatus.INSUFFICIENT_BUDGET
    assert result.action == ReplanAction.STOP_REQUIRED and not result.candidate.outbound_path


@pytest.mark.parametrize("agent", ["human", "rover"])
def test_unresolved_primary_search_does_not_claim_goal_infeasible(agent):
    grid, profile, start, moved, obstacle, *_ = scene(agent)
    p = ReplanPolicy(policy().config, limits=SearchLimits(max_labels=1, timeout_s=10.))
    result = evaluate(p, block(grid, obstacle), profile, moved)
    assert result.action == ReplanAction.UNKNOWN and result.candidate.reason_code == "SEARCH_LIMIT"
    assert result.primary_candidate is None and result.request.goal == start.mission.goal
    assert result.candidate_phase == MissionPhase.OUTBOUND


@pytest.mark.parametrize("agent", ["human", "rover"])
def test_failure_during_existing_return_does_not_recursively_retry_return(agent):
    grid, profile, start, *_ = scene(agent)
    state = replace(start, phase=MissionPhase.RETURN, pose=(35.5, 13.5, 0.),
                    next_waypoint=3, service_remaining_s=0.)
    mask = grid.traversability.copy(); mask[:, 5] = 100
    result = evaluate(policy(), replace(grid, map_version=2, traversability=mask), profile, state)
    assert result.action == ReplanAction.STOP_REQUIRED and result.candidate.status == RouteStatus.NO_PATH
    assert result.primary_candidate is None and result.candidate_phase == MissionPhase.RETURN


@pytest.mark.parametrize("agent", ["human", "rover"])
@pytest.mark.parametrize("remaining_service", [0., 5., 9.999])
@pytest.mark.parametrize("seen_initial_state", [False, True])
def test_outbound_cannot_debit_ten_second_service_before_arrival(
        agent, remaining_service, seen_initial_state, monkeypatch):
    grid, profile, start, moved, *_ = scene(agent)
    mission = replace(start.mission, service_time_s=10.)
    route = plan_route(allow_continuous_start=True, terrain=grid, profile=profile, request=mission)
    assert route.status == RouteStatus.FEASIBLE
    start = replace(start, mission=mission, active_request=mission, active_route=route,
                    service_remaining_s=10.)
    moved = replace(moved, mission=mission, active_request=mission, active_route=route,
                    service_remaining_s=remaining_service)
    assert moved.pose != mission.goal and moved.phase == MissionPhase.OUTBOUND
    p = policy()
    if seen_initial_state:
        assert evaluate(p, grid, profile, start).action == ReplanAction.KEEP

    def forbidden_search(**kwargs):
        raise AssertionError("Invalid service accounting must not reach the planner")

    monkeypatch.setattr("mge_planning.replan.plan_route", forbidden_search)
    result = evaluate(p, grid, profile, moved, EventKind.TASK, "premature-service", 1.)
    assert result.action == ReplanAction.UNKNOWN and result.invalidate_active
    assert result.reason_code == "OUTBOUND_SERVICE_MISMATCH"
    assert result.request is None and result.candidate is None
    assert result.primary_candidate is None


@pytest.mark.parametrize("agent", ["human", "rover"])
def test_only_service_phase_at_goal_can_debit_the_original_ten_seconds(agent):
    grid, profile, start, *_ = scene(agent)
    mission = replace(start.mission, service_time_s=10.)
    route = plan_route(allow_continuous_start=True, terrain=grid, profile=profile, request=mission)
    start = replace(start, mission=mission, active_request=mission, active_route=route,
                    service_remaining_s=10.)
    p = policy()
    evaluate(p, grid, profile, start)
    at_goal = replace(start, phase=MissionPhase.SERVICE, pose=mission.goal,
                      next_waypoint=1, service_remaining_s=5.)
    result = evaluate(p, grid, profile, at_goal, EventKind.TASK, "service-progress", 10.)
    assert result.candidate.status == RouteStatus.FEASIBLE
    assert result.request.service_time_s == 5.
    assert result.candidate.travel_time_s == pytest.approx(5.+39./profile.speed_m_s)


@pytest.mark.parametrize("agent", ["human", "rover"])
@pytest.mark.parametrize("event_version", [1, 3])
def test_event_map_mismatch_invalidates_even_unaffected_route_and_stays_latched(agent, event_version):
    grid, profile, start, moved, *_ = scene(agent)
    p = policy()
    assert evaluate(p, grid, profile, start).action == ReplanAction.KEEP
    revised = block(grid, (0, 0))  # Harmless change, so no geometric invalidation.
    result = evaluate(p, revised, profile, moved, EventKind.MAP, "mismatched-event", 1., event_version)
    assert result.action == ReplanAction.UNKNOWN and result.reason_code == "EVENT_MAP_MISMATCH"
    assert result.invalidate_active and result.request is None and result.candidate is None
    tick = evaluate(p, revised, profile, moved, EventKind.TICK, "matching-tick", 2.)
    assert tick.action == ReplanAction.STOP_REQUIRED and tick.invalidate_active
    assert tick.reason_code == "AWAITING_ROUTE_AUTHORIZATION"
    # Only external adoption of a current-version route can clear invalidation.
    request = replace(moved.mission, request_id="reauthorized", start=moved.pose,
                      map_version=2, budget=moved.remaining)
    candidate = plan_route(allow_continuous_start=True, terrain=revised, request=request, profile=profile)
    adopted = replace(moved, active_request=request, active_route=candidate, next_waypoint=1)
    assert evaluate(p, revised, profile, adopted, EventKind.TICK, "adopted", 3.).action == ReplanAction.KEEP


@pytest.mark.parametrize("agent", ["human", "rover"])
def test_remaining_resources_cannot_erase_the_original_mission_energy_reserve(agent):
    grid, profile, start, *_ = scene(agent)
    pending = costs(start.active_route.outbound_path + start.active_route.return_path[1:],
                    profile, service_s=start.service_remaining_s)["energy_wh"]
    remaining = replace(start.remaining, energy_wh=pending + 1., reserve_wh=0.)
    assert start.mission.budget.reserve_wh > 1.
    result = evaluate(policy(), grid, profile, replace(start, remaining=remaining), EventKind.RESOURCES)
    assert result.action == ReplanAction.UNKNOWN and result.invalidate_active
    assert result.reason_code == "RESERVE_CONTEXT_MISMATCH"
    assert result.request is None and result.candidate is None


@pytest.mark.parametrize("source", ["remaining", "active_request"])
@pytest.mark.parametrize("field", ["reserve_wh", "reserve_oxygen_l"])
def test_reserve_changes_in_resources_or_adopted_request_are_rejected(source, field):
    grid, profile, start, *_ = scene("human")
    if source == "remaining":
        state = replace(start, remaining=replace(start.remaining, **{field: 0.}))
    else:
        request = replace(start.active_request, budget=replace(start.active_request.budget, **{field: 0.}))
        state = replace(start, active_request=request)
    result = evaluate(policy(), grid, profile, state)
    assert result.action == ReplanAction.UNKNOWN and result.invalidate_active
    assert result.reason_code == "RESERVE_CONTEXT_MISMATCH"


def test_adopted_request_cannot_change_the_original_time_reserve():
    grid, profile, start, *_ = scene()
    state = replace(start, active_request=replace(start.active_request, reserve_time_s=0.))
    assert start.mission.reserve_time_s > 0.
    result = evaluate(policy(), grid, profile, state)
    assert result.reason_code == "RESERVE_CONTEXT_MISMATCH" and result.invalidate_active


@pytest.mark.parametrize("agent", ["human", "rover"])
def test_outbound_request_for_another_goal_is_not_kept(agent):
    grid, profile, start, *_ = scene(agent)
    request = replace(start.active_request, request_id="unrelated-goal", goal=(16.5, 13.5, 0.))
    route = plan_route(terrain=grid, profile=profile, request=request)
    assert route.status == RouteStatus.FEASIBLE
    state = replace(start, active_request=request, active_route=route)
    result = evaluate(policy(), grid, profile, state)
    assert result.action == ReplanAction.UNKNOWN and result.invalidate_active
    assert result.reason_code == "ACTIVE_GOAL_MISMATCH"


@pytest.mark.parametrize("leg,index", [("outbound_path", -1), ("return_path", 0), ("return_path", -1)])
def test_route_endpoints_must_match_the_request_goal_and_mission_base(leg, index):
    grid, profile, start, *_ = scene()
    path = list(getattr(start.active_route, leg))
    path[index] = (16.5, 13.5, 0.)
    route = replace(start.active_route, **{leg: tuple(path)})
    result = evaluate(policy(), grid, profile, replace(start, active_route=route))
    assert result.action == ReplanAction.UNKNOWN and result.invalidate_active
    assert result.reason_code == "ACTIVE_PATH_MISMATCH"


def test_outbound_request_cannot_drop_a_required_return():
    grid, profile, start, *_ = scene()
    request = replace(start.active_request, require_return=False)
    route = plan_route(terrain=grid, profile=profile, request=request)
    result = evaluate(policy(), grid, profile, replace(start, active_request=request, active_route=route))
    assert result.reason_code == "ACTIVE_RETURN_MISMATCH" and result.invalidate_active


def test_outbound_request_cannot_substitute_a_different_return_base():
    grid, profile, start, *_ = scene()
    request = replace(start.active_request, return_to=(7.5, 13.5, 0.))
    route = plan_route(terrain=grid, profile=profile, request=request)
    result = evaluate(policy(), grid, profile, replace(start, active_request=request, active_route=route))
    assert result.reason_code == "ACTIVE_RETURN_MISMATCH" and result.invalidate_active
