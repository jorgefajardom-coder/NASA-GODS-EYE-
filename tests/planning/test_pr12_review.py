"""Regression evidence for review comment 6882884265; synthetic inputs only."""

from dataclasses import replace
import math

import numpy as np
import pytest

from mge_planning import core, replan
from tests.planning.test_replan_policy import scene, policy, evaluate, block


@pytest.mark.parametrize("kind", ["human", "rover"])
@pytest.mark.parametrize("phase", [replan.MissionPhase.SERVICE, replan.MissionPhase.RETURN])
@pytest.mark.parametrize("dimensions", [2, 3])
def test_r1_goal_and_base_are_horizontal_targets(kind, phase, dimensions):
    grid, profile, start, *_ = scene(kind)
    grid = replace(grid, elevation_m=np.full(grid.elevation_m.shape, 5.))
    mission = replace(start.mission, start=(*start.pose[:2], 5.),
                      goal=start.mission.goal[:dimensions], return_to=start.mission.return_to[:dimensions])
    route = core.plan_route(terrain=grid, request=mission, profile=profile)
    assert route.status == core.RouteStatus.FEASIBLE
    pose = (*mission.goal[:2], 5.) if phase == replan.MissionPhase.SERVICE else (35.5, 13.5, 5.)
    state = replace(start, mission=mission, active_request=mission, active_route=route,
                    phase=phase, pose=pose, next_waypoint=1 if phase == replan.MissionPhase.SERVICE else 3,
                    service_remaining_s=1. if phase == replan.MissionPhase.SERVICE else 0.)
    result = evaluate(policy(), grid, profile, state, replan.EventKind.TASK)
    assert result.candidate.status == core.RouteStatus.FEASIBLE
    assert result.request.start == pose and result.candidate.outbound_path[0] == pose


@pytest.mark.parametrize("kind", ["human", "rover"])
@pytest.mark.parametrize("x", [4.5, 4.7])
def test_r2_ground_z_rejection_is_uniform_and_never_path_impossibility(kind, x):
    grid, profile, start, *_ = scene(kind)
    grid = replace(grid, elevation_m=np.full(grid.elevation_m.shape, 5.))
    request = replace(start.mission, start=(x, 13.5, 0.))
    invalid = core.plan_route(terrain=grid, profile=profile, request=request, allow_continuous_start=True)
    assert invalid.status == core.RouteStatus.ERROR and invalid.reason_code == "INVALID_START_Z"
    assert not invalid.outbound_path
    request = replace(request, start=(x, 13.5, 5.))
    valid = core.plan_route(terrain=grid, profile=profile, request=request, allow_continuous_start=True)
    assert valid.status == core.RouteStatus.FEASIBLE and valid.outbound_path[0] == request.start


@pytest.mark.parametrize("kind", ["human", "rover"])
def test_r3_stationary_height_change_requires_coherent_pose_then_recovers(kind):
    grid, profile, start, *_ = scene(kind)
    p = policy()
    evaluate(p, grid, profile, start)
    heights = grid.elevation_m.copy(); heights[grid.cell(start.pose)] = .1
    changed = replace(grid, map_version=2, elevation_m=heights)
    incoherent = evaluate(p, changed, profile, start, event_id="height", now=1.)
    assert incoherent.action == replan.ReplanAction.UNKNOWN and incoherent.reason_code == "INVALID_START_Z"
    assert incoherent.request is None and incoherent.invalidate_active
    fresh_pose = replace(start, pose=(*start.pose[:2], .1))
    recovered = evaluate(p, changed, profile, fresh_pose, replan.EventKind.POSE, "fresh-pose", 2.)
    assert recovered.candidate.status == core.RouteStatus.FEASIBLE
    assert recovered.candidate.outbound_path[0] == fresh_pose.pose
    assert recovered.invalidate_active  # A replacement is still only a proposal.


@pytest.mark.parametrize("eventual_success", [False, True])
def test_r4_search_limit_retries_are_delayed_bounded_and_recover(eventual_success, monkeypatch):
    grid, profile, start, *_ = scene()
    p = policy()
    calls = []
    actual = replan.plan_route

    def bounded(**kwargs):
        calls.append(kwargs)
        result = actual(**kwargs)
        if eventual_success and len(calls) == 2:
            return result
        return replace(result, status=core.RouteStatus.UNKNOWN, reason_code="SEARCH_LIMIT",
                       route_id="", outbound_path=(), return_path=())

    monkeypatch.setattr(replan, "plan_route", bounded)
    first = evaluate(p, grid, profile, start, replan.EventKind.TASK)
    assert first.action == replan.ReplanAction.UNKNOWN and len(calls) == 1
    early = evaluate(p, grid, profile, start, replan.EventKind.TICK, "early", 1.)
    assert early.reason_code == "SEARCH_RETRY_DEFERRED" and len(calls) == 1
    second = evaluate(p, grid, profile, start, replan.EventKind.TICK, "retry1", 10.)
    assert len(calls) == 2
    if eventual_success:
        assert second.candidate.status == core.RouteStatus.FEASIBLE
        assert second.invalidate_active
    else:
        last = evaluate(p, grid, profile, start, replan.EventKind.TICK, "retry2", 20.)
        assert last.action == replan.ReplanAction.STOP_REQUIRED and last.reason_code == "SEARCH_RETRIES_EXHAUSTED"
        assert len(calls) == 3
        again = evaluate(p, grid, profile, start, replan.EventKind.TICK, "after-limit", 30.)
        assert again.reason_code == "SEARCH_RETRIES_EXHAUSTED" and len(calls) == 3


def test_r4_danger_bypasses_waiting_search_retry(monkeypatch):
    grid, profile, start, *_ = scene()
    original = replan.plan_route
    calls = []

    def capped(**kwargs):
        calls.append(1)
        return replace(original(**kwargs), status=core.RouteStatus.UNKNOWN, reason_code="SEARCH_LIMIT")

    monkeypatch.setattr(replan, "plan_route", capped)
    p = policy()
    assert evaluate(p, grid, profile, start, replan.EventKind.TASK).reason_code == "SEARCH_LIMIT"
    danger = evaluate(p, grid, profile, start, replan.EventKind.DANGER, "danger", .1)
    assert danger.action == replan.ReplanAction.STOP_REQUIRED and danger.invalidate_active
    assert danger.reason_code == "IMMEDIATE_DANGER" and danger.request is None and len(calls) == 1


def test_r5_core_baseline_rejects_continuous_start_without_opt_in():
    grid, profile, _, moved, *_ = scene()
    default = core.plan_route(terrain=grid, profile=profile, request=replace(moved.mission, start=moved.pose))
    assert default.status == core.RouteStatus.ERROR and default.reason_code == "NON_CELL_CENTER"
    experimental = core.plan_route(terrain=grid, profile=profile,
                                   request=replace(moved.mission, start=moved.pose), allow_continuous_start=True)
    assert experimental.status == core.RouteStatus.FEASIBLE


@pytest.mark.parametrize("kind", ["human", "rover"])
def test_r6_service_can_be_abandoned_to_fund_contingency_return(kind):
    grid, profile, start, *_ = scene(kind)
    budget = replace(start.remaining, time_s=2000., energy_wh=1000.,
                     oxygen_l=300. if kind == "human" else None)
    mission = replace(start.mission, service_time_s=600., budget=budget)
    route = core.plan_route(terrain=grid, request=mission, profile=profile)
    remaining = replace(budget, time_s=30., energy_wh=100., oxygen_l=10. if kind == "human" else None)
    state = replace(start, mission=mission, active_request=mission, active_route=route,
                    phase=replan.MissionPhase.SERVICE, pose=mission.goal, next_waypoint=1,
                    service_remaining_s=600., remaining=remaining)
    result = evaluate(policy(), grid, profile, state, replan.EventKind.RESOURCES)
    assert result.primary_candidate.status == core.RouteStatus.INSUFFICIENT_BUDGET
    assert result.candidate.status == core.RouteStatus.FEASIBLE
    assert result.candidate_phase == replan.MissionPhase.RETURN and result.reason_code == "CONTINGENCY_RETURN"
    assert result.request.service_time_s == 0. and result.request.budget is remaining
    assert result.candidate.travel_time_s == pytest.approx(39./2)
    assert result.invalidate_active


@pytest.mark.parametrize("kind,resource,reason", [
    ("human", "time_s", "TIME_RESERVE_DEPLETED"),
    ("human", "energy_wh", "ENERGY_RESERVE_DEPLETED"),
    ("human", "oxygen_l", "OXYGEN_RESERVE_DEPLETED"),
    ("rover", "time_s", "TIME_RESERVE_DEPLETED"),
    ("rover", "energy_wh", "ENERGY_RESERVE_DEPLETED")])
def test_r7_depleted_live_resources_stop_before_creating_search_budget(kind, resource, reason):
    grid, profile, start, *_ = scene(kind)
    values = dict(agent_kind=kind, time_s=100., energy_wh=100., reserve_wh=5.,
                  oxygen_l=30. if kind == "human" else None,
                  reserve_oxygen_l=2. if kind == "human" else None)
    values[resource] = 1.
    live = replan.RemainingResources(**values)
    result = evaluate(policy(), grid, profile, replace(start, remaining=live), replan.EventKind.RESOURCES)
    assert result.action == replan.ReplanAction.STOP_REQUIRED and result.reason_code == reason
    assert result.invalidate_active and result.request is None
    if resource != "time_s":
        with pytest.raises(ValueError):
            core.ResourceBudget(**values)  # Planner admission invariant remains strict.


def test_r7_admissible_live_resources_convert_without_debits():
    grid, profile, start, *_ = scene()
    live = replan.RemainingResources("human", 100., 100., 5., 30., 2.)
    result = evaluate(policy(), grid, profile, replace(start, remaining=live), replan.EventKind.TASK)
    assert result.request.budget == live.planning_budget()
    assert result.candidate.status == core.RouteStatus.FEASIBLE


def test_r8_cache_reuses_hash_and_geometry_and_rechecks_distinct_same_version(monkeypatch):
    grid, profile, start, *_ = scene()
    builds, hashes = [], []
    geometry, sha = core._Geometry, replan.hashlib.sha256

    def build(*args, **kwargs):
        builds.append(args)
        return geometry(*args, **kwargs)

    def digest(*args, **kwargs):
        if not args:
            hashes.append(1)
        return sha(*args, **kwargs)

    monkeypatch.setattr(core, "_Geometry", build)
    monkeypatch.setattr(replan.hashlib, "sha256", digest)
    p = policy()
    evaluate(p, grid, profile, start)
    for now in range(1, 5):
        evaluate(p, grid, profile, start, replan.EventKind.TICK, str(now), now)
    proposal = evaluate(p, grid, profile, start, replan.EventKind.TASK, "task", 10.)
    assert proposal.candidate.status == core.RouteStatus.FEASIBLE
    assert len(builds) == len(hashes) == 1  # policy AND A* share the same geometry.
    mask = grid.traversability.copy(); mask[0, 0] = 100
    illegal = evaluate(p, replace(grid, traversability=mask), profile, start, event_id="mutated", now=11.)
    assert illegal.reason_code == "IMMUTABLE_MAP_CHANGED" and len(hashes) == 2


def test_r8_geometry_cache_does_not_reuse_a_different_profile_or_snapshot():
    grid, profile, start, *_ = scene()
    cache = core.GeometryCache()
    small = cache.get(grid, profile)
    large = cache.get(grid, replace(profile, radius_m=14.))
    assert small is cache.get(grid, profile)
    assert small.allowed[grid.cell(start.pose)] and not large.allowed[grid.cell(start.pose)]
    changed = block(grid, grid.cell(start.pose))
    latest = cache.get(changed, profile)
    assert latest is not small and not latest.allowed[grid.cell(start.pose)]
    assert len(cache.entries) == 1


def test_r9_one_clearance_rule_rejects_exact_zero_obstacle_margin():
    grid, profile, *_ = scene()
    # Scale to unit cells; the legacy edge clamped to zero and accepted, whereas
    # its policy rejected the exact same bound. All uses now share one rule.
    mask = grid.traversability.copy(); mask[1, 2] = 100
    grid = replace(grid, resolution_m=1., traversability=mask)
    radius = 1.-1./math.sqrt(2)-1./8
    profile = replace(profile, radius_m=radius, localization_error_m=0.)
    geo = core._Geometry(grid, profile)
    a, b = grid.point((2, 2)), grid.point((2, 3))
    assert core._segment_clearance(geo, a, b) < 0
    assert geo.edge((2, 2), (2, 3)) is None
    assert replan._segment_issue(geo, a, b, 1000) == "CORRIDOR_BLOCKED"


def test_r9_stationary_path_uses_same_strict_obstacle_contact_rule():
    grid, profile, start, *_ = scene()
    mask = grid.traversability.copy(); mask[1, 2] = 100
    grid = replace(grid, resolution_m=1., traversability=mask)
    profile = replace(profile, radius_m=1.-1./math.sqrt(2), localization_error_m=0.)
    geo = core._Geometry(grid, profile)
    pose = grid.point((2, 2))
    assert geo.clearance[2, 2] < 0 and not geo.allowed[2, 2]
    assert replan._segment_issue(geo, pose, pose, 1000) == "CORRIDOR_BLOCKED"
    request = replace(start.mission, start=pose, goal=pose, return_to=pose)
    result = core.plan_route(terrain=grid, request=request, profile=profile)
    assert result.status == core.RouteStatus.NO_PATH


def test_r10_deferred_deviation_is_dropped_but_task_notification_is_retained():
    grid, profile, start, moved, *_ = scene()
    p = policy()
    out = replace(moved, pose=(24.5, 14.7, 0.))
    first = evaluate(p, grid, profile, out, replan.EventKind.POSE)
    assert first.request is not None
    deferred = evaluate(p, grid, profile, replace(out, pose=(24.5, 14.2, 0.)), replan.EventKind.POSE, "defer", 1.)
    assert deferred.reason_code == "REPLAN_DEFERRED"
    cleared = evaluate(p, grid, profile, moved, replan.EventKind.TICK, "clear", 2.)
    assert cleared.action == replan.ReplanAction.KEEP and cleared.request is None
    task = evaluate(p, grid, profile, moved, replan.EventKind.TASK, "task", 3.)
    assert task.reason_code == "REPLAN_DEFERRED"
    flushed = evaluate(p, grid, profile, moved, replan.EventKind.TICK, "flush", 10.)
    assert flushed.request is not None and flushed.reason_code == "TASK_REEVALUATION"
