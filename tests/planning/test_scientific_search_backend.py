"""Production A* scientific pricing; no ROS or physical execution claim.

AI-assisted test code is declared in docs/ai_usage.json.
"""
from dataclasses import replace
import math
from pathlib import Path

import numpy as np
import pytest

from mge_mission.models import estimate_activity, estimate_segment, export_planner_profiles, load_profiles
from mge_planning.core import (GeometryCache, MotionProfile, PlanRequest, ResourceBudget,
                               RouteStatus, SearchLimits, TerrainGrid, plan_route)
from mge_planning.resource_costs import Activity, ScientificCosts, scientific_plan_route

ROOT = Path(__file__).resolve().parents[2]
PROFILES = load_profiles(ROOT / "config/science_profiles.proposed.json")


def scene(agent="human_1", *, elevations=None, mask=None, resolution=2., mode="FAST", **changes):
    science = PROFILES[agent]
    motion = MotionProfile(**export_planner_profiles({agent: science})["profiles"][agent])
    z = np.zeros((9, 10)) if elevations is None else np.asarray(elevations, dtype=float)
    m = np.zeros(z.shape, dtype=np.int8) if mask is None else np.asarray(mask, dtype=np.int8)
    terrain = TerrainGrid("scientific-core-test", 1, z, m, resolution, sigma_m=np.zeros(z.shape))
    human = science.kind == "human"
    budget = ResourceBudget(science.kind, 100000., 100000., 10.,
                            100000. if human else None, 10. if human else None)
    values = dict(run_id=terrain.run_id, request_id="scientific-core-1", agent_id=agent,
                  agent_kind=science.kind, map_version=1, start=terrain.point((4, 2)),
                  goal=terrain.point((4, 6)), return_to=terrain.point((4, 2)),
                  require_return=True, budget=budget, mode=mode, reserve_time_s=10.)
    values.update(changes)
    return terrain, PlanRequest(**values), motion, science


def audit(result, request, science, activities):
    parts = [estimate_segment(science, a, b)
             for path in (result.outbound_path, result.return_path)
             for a, b in zip(path, path[1:])]
    parts += [estimate_activity(science, a.kind, a.remaining_s) for a in activities]
    for name, output in (("time_s", "travel_time_s"), ("energy_wh", "energy_est_wh")):
        assert getattr(result, output) == pytest.approx(sum(getattr(p, name) for p in parts), rel=1e-12)
    if science.kind == "human":
        assert result.oxygen_est_l == pytest.approx(sum(p.oxygen_l for p in parts), rel=1e-12)
    else:
        assert result.oxygen_est_l is None and result.reserve_oxygen_l is None
    assert result.reserve_time_s >= request.reserve_time_s
    assert result.reserve_wh >= request.budget.reserve_wh


def test_actual_astar_rejects_legacy_hill_and_finds_a_flat_route_under_136_wh():
    z = np.zeros((9, 10)); z[4, 4] = .2
    grid, request, motion, science = scene(elevations=z, require_return=False,
        budget=ResourceBudget("human", 1000., 2.36, 1., 1000., 1.))
    legacy = plan_route(terrain=grid, request=request, profile=motion)
    result = scientific_plan_route(terrain=grid, request=request, motion_profile=motion,
                                   scientific_profile=science)
    assert legacy.status == result.status == RouteStatus.FEASIBLE
    legacy_science = sum(estimate_segment(science, a, b).energy_wh
                         for a, b in zip(legacy.outbound_path, legacy.outbound_path[1:]))
    assert legacy.energy_est_wh == pytest.approx(1.338953692, abs=1e-9)
    assert legacy_science == pytest.approx(1.390768345, abs=1e-9)
    assert legacy.energy_est_wh <= 1.36 < legacy_science
    assert result.outbound_path != legacy.outbound_path
    assert all(p[2] == 0 for p in result.outbound_path)
    assert result.energy_est_wh == pytest.approx(1.344609791, abs=1e-9)
    assert result.energy_est_wh <= 1.36
    audit(result, request, science, ())


@pytest.mark.parametrize("agent", PROFILES)
@pytest.mark.parametrize("mode", ["FAST", "SAFE"])
def test_all_agents_charge_directed_movement_mixed_service_and_wait_once(agent, mode):
    science = PROFILES[agent]
    activities = ((Activity("inspect", "inspect", 20.), Activity("wait", "wait", 15.),
                   Activity("sample", "sample", 10.)) if science.kind == "human" else
                  (Activity("inspect", "inspect", 20.), Activity("wait", "wait", 15.))
                  if science.kind == "rover" else
                  (Activity("observe", "observe", 20.), Activity("ground", "ground_wait", 15.)))
    z = np.tile(np.arange(10) * .03, (9, 1))
    grid, request, motion, science = scene(agent, elevations=z, mode=mode,
                                          service_time_s=sum(a.remaining_s for a in activities))
    result = scientific_plan_route(terrain=grid, request=request, motion_profile=motion,
                                   scientific_profile=science, activities=activities)
    assert result.status == RouteStatus.FEASIBLE
    assert result.return_path[-1] == request.return_to
    audit(result, request, science, activities)
    up = estimate_segment(science, grid.point((4, 2)), grid.point((4, 6)))
    down = estimate_segment(science, grid.point((4, 6)), grid.point((4, 2)))
    assert up.energy_wh > down.energy_wh


@pytest.mark.parametrize("agent", ["human_1", "rover_1"])
def test_actual_continuous_pose_connector_is_scientifically_priced_once(agent):
    grid, request, motion, science = scene(agent)
    point = list(request.start); point[0] += .3
    request = replace(request, start=tuple(point))
    result = scientific_plan_route(terrain=grid, request=request, motion_profile=motion,
        scientific_profile=science, allow_continuous_start=True)
    assert result.status == RouteStatus.FEASIBLE
    assert result.start_connector is not None
    assert result.outbound_path[0] == tuple(point)
    cost = estimate_segment(science, result.start_connector.start, result.start_connector.end)
    assert result.start_connector.energy_est_wh == pytest.approx(cost.energy_wh, rel=1e-14)
    audit(result, request, science, ())


def test_service_kind_changes_feasibility_without_changing_duration():
    grid, request, motion, science = scene(service_time_s=20., require_return=False)
    inspect = scientific_plan_route(terrain=grid, request=request, motion_profile=motion,
        scientific_profile=science, activities=(Activity("work", "inspect", 20.),))
    sample = scientific_plan_route(terrain=grid, request=request, motion_profile=motion,
        scientific_profile=science, activities=(Activity("work", "sample", 20.),))
    assert inspect.status == sample.status == RouteStatus.FEASIBLE
    assert sample.energy_est_wh > inspect.energy_est_wh
    cap = (sample.energy_est_wh+inspect.energy_est_wh)/2
    request = replace(request, budget=replace(request.budget, energy_wh=cap+request.budget.reserve_wh))
    assert scientific_plan_route(terrain=grid, request=request, motion_profile=motion,
        scientific_profile=science, activities=(Activity("work", "inspect", 20.),)).status == RouteStatus.FEASIBLE
    assert scientific_plan_route(terrain=grid, request=request, motion_profile=motion,
        scientific_profile=science, activities=(Activity("work", "sample", 20.),)).status == RouteStatus.INSUFFICIENT_BUDGET


def test_schedule_duration_identity_and_geometry_must_be_explicit_and_coherent():
    grid, request, motion, science = scene(service_time_s=20.)
    kwargs=dict(terrain=grid,request=request,motion_profile=motion,scientific_profile=science)
    with pytest.raises(ValueError, match="service_time"):
        scientific_plan_route(**kwargs)
    with pytest.raises(ValueError, match="duplicate"):
        scientific_plan_route(**kwargs, activities=(Activity("x", "inspect", 10.), Activity("x", "wait", 10.)))
    with pytest.raises(ValueError, match="identities"):
        scientific_plan_route(**(kwargs | {"scientific_profile":replace(science,agent_id="someone_else")}))
    with pytest.raises(ValueError, match="step"):
        scientific_plan_route(**(kwargs | {"motion_profile":replace(motion,max_step_m=motion.max_step_m+1)}))


def test_search_limits_and_unobserved_corridors_remain_unknown():
    grid, request, motion, science = scene()
    result = scientific_plan_route(terrain=grid,request=request,motion_profile=motion,
        scientific_profile=science, limits=SearchLimits(max_labels=1,timeout_s=1.))
    assert result.status == RouteStatus.UNKNOWN and result.reason_code == "SEARCH_LIMIT"
    mask = np.zeros((9,10),dtype=np.int8); mask[:,4] = -1
    heights = np.zeros(mask.shape); heights[:,4] = np.nan
    grid, request, motion, science = scene(mask=mask,elevations=heights)
    result = scientific_plan_route(terrain=grid,request=request,motion_profile=motion,scientific_profile=science)
    assert result.status == RouteStatus.UNKNOWN and result.reason_code == "UNVERIFIED_CORRIDOR"


def test_backend_cache_identity_and_strict_nextafter_reserve():
    grid, request, motion, science = scene(require_return=False)
    cache=GeometryCache()
    first=ScientificCosts(science)
    second=ScientificCosts(replace(science,activity_power_w={**science.activity_power_w,"walk":science.activity_power_w["walk"]*2}))
    a=plan_route(terrain=grid,request=request,profile=motion,cost_model=first,stationary_costs=(0.,0.,0.),geometry_cache=cache)
    b=plan_route(terrain=grid,request=request,profile=motion,cost_model=second,stationary_costs=(0.,0.,0.),geometry_cache=cache)
    assert a.status == b.status == RouteStatus.FEASIBLE
    assert b.energy_est_wh == pytest.approx(a.energy_est_wh*2,rel=1e-14)
    assert len(cache.entries)==2
    # Zero separate reserve lets nextafter express an exact one-ULP shortfall.
    request=replace(request,budget=replace(request.budget,energy_wh=math.nextafter(a.energy_est_wh,0.),reserve_wh=0.))
    rejected=scientific_plan_route(terrain=grid,request=request,motion_profile=motion,scientific_profile=science)
    assert rejected.status == RouteStatus.INSUFFICIENT_BUDGET


def test_backend_maximum_speed_is_a_time_lower_bound_for_all_models():
    for profile in PROFILES.values():
        backend=ScientificCosts(profile)
        for dz in (-.1,0.,.1):
            cost=backend.movement((0.,0.,0.),(2.,1.,dz))
            assert cost.time_s >= math.hypot(2.,1.)/backend.maximum_horizontal_speed
