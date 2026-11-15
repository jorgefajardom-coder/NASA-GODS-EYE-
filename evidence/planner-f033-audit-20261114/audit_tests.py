"""Audit characterizations, not scientific agreement or production fixes."""
from dataclasses import replace
from pathlib import Path
import json
import numpy as np
import pytest
from mge_planning import core
from mge_mission.models import load_profiles,export_planner_profiles,estimate_segment,estimate_activity

BASE=Path(__file__).resolve().parents[2]
PROFILES=load_profiles(BASE/'config/science_profiles.proposed.json')
PROJECTION=export_planner_profiles(PROFILES)['profiles']


def test_projection_is_the_actual_main_registry():
    assert PROJECTION==json.loads((BASE/'config/planner_profiles.proposed.json').read_text())['profiles']


@pytest.mark.parametrize('agent',['human_1','rover_1','drone_1'])
def test_activity_split_additivity_in_scientific_model(agent):
    p=PROFILES[agent]
    activity='inspect' if p.kind!='drone' else 'observe'
    whole=estimate_activity(p,activity,120.)
    prefix=estimate_activity(p,activity,45.)
    remaining=estimate_activity(p,activity,75.)
    assert prefix.energy_wh+remaining.energy_wh==pytest.approx(whole.energy_wh)
    if p.kind=='human':
        assert prefix.oxygen_l+remaining.oxygen_l==pytest.approx(whole.oxygen_l)
    else:
        assert whole.oxygen_l is prefix.oxygen_l is remaining.oxygen_l is None


@pytest.mark.parametrize('agent',['human_1','rover_1'])
def test_wait_and_service_are_not_interchangeable(agent):
    p=PROFILES[agent]; q=core.MotionProfile(**PROJECTION[agent])
    wait=estimate_activity(p,'wait',120.)
    projected=q.service_power_w*120/3600
    assert projected>wait.energy_wh  # Characterize existing mismatch, not approve it.


@pytest.mark.parametrize('mode',['FAST','SAFE'])
def test_complete_directed_roundtrip_can_fit_search_but_breach_science_reserve(mode):
    p=PROFILES['human_1']; q=core.MotionProfile(**PROJECTION['human_1'])
    expected=10*(core._motion_costs(q,1.,.1)[1]+core._motion_costs(q,1.,-.1)[1])
    heights=np.tile(np.arange(15)*.1,(7,1))
    grid=core.TerrainGrid('SIMULATED-F033',1,heights,np.zeros((7,15),dtype=np.int8),1.,sigma_m=np.zeros((7,15)))
    budget=core.ResourceBudget('human',200.,expected+5.,5.,30.,2.)
    req=core.PlanRequest(grid.run_id,'audit','human_1','human',1,grid.point((3,2)),grid.point((3,12)),budget,
                         return_to=grid.point((3,2)),mode=mode)
    result=core.plan_route(terrain=grid,request=req,profile=q,limits=core.SearchLimits(timeout_s=10.))
    assert result.status==core.RouteStatus.FEASIBLE
    assert result.energy_est_wh<=budget.energy_wh-budget.reserve_wh
    scientific=sum(estimate_segment(p,a,b).energy_wh for path in (result.outbound_path,result.return_path)
                   for a,b in zip(path,path[1:]))
    assert scientific>budget.energy_wh-budget.reserve_wh  # Mismatch reproduced on returned paths.


@pytest.mark.parametrize('kind',['human','rover'])
def test_policy_uses_supplied_remaining_budget_without_an_execution_ledger(kind):
    from tests.planning.test_replan_policy import scene,policy,evaluate
    from mge_planning.replan import EventKind
    grid,profile,start,moved,*_=scene(kind)
    p=policy()
    first=evaluate(p,grid,profile,moved,EventKind.TASK,'spent',0.)
    assert first.request.budget is moved.remaining
    reset=replace(moved,remaining=start.remaining)
    again=evaluate(p,grid,profile,reset,EventKind.TASK,'bad-caller-reset',20.)
    assert again.request.budget is start.remaining
    assert again.request.budget.energy_wh>first.request.budget.energy_wh
    # This characterizes trusted-input boundary; MissionManager rejects replenishment.
