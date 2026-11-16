from dataclasses import replace
from pathlib import Path
import numpy as np
import pytest
from mge_mission.models import load_profiles,export_planner_profiles,estimate_activity,estimate_segment
from mge_planning.core import TerrainGrid,MotionProfile,PlanRequest,ResourceBudget,RouteStatus
from mge_planning.resource_costs import Activity,scientific_plan_route
from mge_planning.replan import ReplanPolicy,ReplanConfig,ReplanState,ReplanEvent,EventKind,MissionPhase

def case():
    science=load_profiles(Path(__file__).resolve().parents[2]/'config/scenario_demo.yaml')['human_1']
    motion=MotionProfile(**export_planner_profiles({'human_1':science})['profiles']['human_1'])
    grid=TerrainGrid(run_id='science-policy',map_version=1,elevation_m=np.zeros((20,20)),
        sigma_m=np.zeros((20,20)),traversability=np.zeros((20,20),dtype=int),resolution_m=1.)
    req=PlanRequest('science-policy','primary','human_1','human',1,(2.5,2.5,0.),(16.5,2.5,0.),
        ResourceBudget('human',3600.,600.,60.,150.,15.),return_to=(2.5,2.5,0.),service_time_s=60.,reserve_time_s=360.)
    route=scientific_plan_route(terrain=grid,request=req,motion_profile=motion,scientific_profile=science,
        activities=(Activity('work','sample',60.),))
    assert route.status==RouteStatus.FEASIBLE
    policy=ReplanPolicy(ReplanConfig(1.,.4,0.,4.))
    return science,motion,grid,req,route,policy

def test_scientific_replan_never_calls_legacy_search_and_costs_match(monkeypatch):
    import mge_planning.replan as module
    science,motion,grid,req,route,policy=case()
    monkeypatch.setattr(module,'plan_route',lambda **kw:(_ for _ in ()).throw(AssertionError('legacy search')))
    state=ReplanState(req,req,route,MissionPhase.OUTBOUND,req.start,1,req.budget,60.)
    event=ReplanEvent('first',req.run_id,1,EventKind.TICK)
    assert policy.evaluate(terrain=grid,profile=motion,state=state,event=event,now_s=0.,scientific_profile=science,service_activity='sample').action.value=='KEEP'
    mask=grid.traversability.copy();mask[2,5]=100;new=replace(grid,map_version=2,traversability=mask)
    answer=policy.evaluate(terrain=new,profile=motion,state=state,event=ReplanEvent('obstacle',req.run_id,2,EventKind.MAP),now_s=1.,scientific_profile=science,service_activity='sample')
    assert answer.invalidate_active and answer.candidate.status==RouteStatus.FEASIBLE
    costs=[estimate_segment(science,a,b) for p in (answer.candidate.outbound_path,answer.candidate.return_path) for a,b in zip(p,p[1:])]+[estimate_activity(science,'sample',60.)]
    assert answer.candidate.energy_est_wh==pytest.approx(sum(x.energy_wh for x in costs))
    assert answer.candidate.oxygen_est_l==pytest.approx(sum(x.oxygen_l for x in costs))
    assert answer.request.budget is state.remaining

def test_return_phase_stays_direct_return_with_no_new_service():
    science,motion,grid,req,route,policy=case()
    state=ReplanState(req,req,route,MissionPhase.RETURN,req.goal,1,req.budget,0.)
    mask=grid.traversability.copy();mask[2,8]=100;new=replace(grid,map_version=2,traversability=mask)
    answer=policy.evaluate(terrain=new,profile=motion,state=state,event=ReplanEvent('return-obstacle',req.run_id,2,EventKind.MAP),now_s=1.,scientific_profile=science,service_activity='sample')
    assert answer.candidate_phase==MissionPhase.RETURN
    assert answer.request.goal==req.return_to and not answer.request.require_return
    assert answer.request.service_time_s==0.
