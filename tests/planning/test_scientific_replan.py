"""Explicit scientific contexts through local policy; never ROS authority."""
from dataclasses import replace

import pytest
from mge_mission.models import estimate_activity, estimate_segment
from mge_planning.core import RouteStatus, plan_route
from mge_planning.replan import (
    EventKind, MissionPhase, ReplanAction, ReplanEvent, ReplanState,
)
from mge_planning.resource_costs import Activity
from tests.planning.test_replan_policy import policy
from tests.planning.test_scientific_context import PROFILES, context, scene


def scientific_case(kind='human', seconds=10., waiting=5.):
    service=(Activity('inspect','inspect',seconds),)
    waits=(Activity('hold','wait',waiting),) if waiting else ()
    g,p,r=scene(kind,service)
    # Room for both unchanged published footprints, including blocked-goal tests.
    g=replace(g,resolution_m=4.)
    r=replace(r,start=g.point((0,0)),goal=g.point((0,2)),return_to=g.point((0,0)))
    c=context(r,service,waits)
    route=plan_route(terrain=g,request=r,profile=p,scientific_context=c)
    assert route.status==RouteStatus.FEASIBLE
    s=ReplanState(r,r,route,MissionPhase.OUTBOUND,r.start,1,r.budget,seconds)
    return g,p,s


def pending(g,s,service=None,waiting=None):
    active=s.active_route.cost_context
    returning=s.phase==MissionPhase.RETURN
    r=replace(s.mission,request_id=s.active_request.request_id,start=s.pose,
              goal=s.mission.return_to if returning else s.mission.goal,
              require_return=False if returning else s.mission.require_return,
              return_to=s.mission.return_to,map_version=g.map_version,budget=s.remaining,
              service_time_s=0. if returning else s.service_remaining_s)
    return replace(active,request=r,phase=s.phase.value,
                   service=() if returning else active.service if service is None else service,
                   waiting=() if returning else active.waiting if waiting is None else waiting)


def evaluate(pol,g,p,s,c,kind=EventKind.TICK,event_id='tick',now=0.):
    return pol.evaluate(terrain=g,profile=p,state=s,scientific_context=c,
                        event=ReplanEvent(event_id,g.run_id,g.map_version,kind),now_s=now)


@pytest.mark.parametrize('agent,field',[('human','time_s'),('human','energy_wh'),('human','oxygen_l'),
                                      ('rover','time_s'),('rover','energy_wh')])
def test_scientific_replan_preserves_A_increase_guard_and_authorized_recovery(agent,field,monkeypatch):
    g,p,s=scientific_case(agent);pol=policy()
    assert evaluate(pol,g,p,s,pending(g,s)).action==ReplanAction.KEEP
    bad=replace(s,remaining=replace(s.remaining,**{field:getattr(s.remaining,field)+1.}))
    import mge_planning.replan as module
    original=module.plan_route
    monkeypatch.setattr(module,'plan_route',lambda **kwargs:pytest.fail('inflation reached search'))
    result=evaluate(pol,g,p,bad,pending(g,bad),EventKind.RESOURCES,'bad',1.)
    assert result.reason_code.endswith('AVAILABILITY_INCREASE') and result.invalidate_active
    assert result.request is None
    corrected=evaluate(pol,g,p,s,pending(g,s),event_id='corrected',now=2.)
    assert corrected.action==ReplanAction.STOP_REQUIRED
    monkeypatch.setattr(module,'plan_route',original)
    candidate=evaluate(pol,g,p,s,pending(g,s),EventKind.TASK,'authorize-next',10.)
    assert candidate.candidate.status==RouteStatus.FEASIBLE and candidate.invalidate_active
    adopted=replace(s,active_request=candidate.request,active_route=candidate.candidate)
    assert evaluate(pol,g,p,adopted,pending(g,adopted),event_id='adopted',now=11.).action==ReplanAction.KEEP
    bad=replace(adopted,remaining=bad.remaining)
    assert evaluate(pol,g,p,bad,pending(g,bad),event_id='bad-again',now=12.).invalidate_active


@pytest.mark.parametrize('kind',['human','rover'])
def test_current_continuous_pose_map_and_remaining_budget_survive_scientific_contingency(kind):
    g,p,s=scientific_case(kind);pol=policy()
    assert evaluate(pol,g,p,s,pending(g,s)).action==ReplanAction.KEEP
    pose=(s.pose[0]+.37,s.pose[1],s.pose[2]);spent=estimate_segment(PROFILES[s.mission.agent_id],s.pose,pose)
    moved=replace(s,pose=pose,remaining=replace(s.remaining,
                  time_s=s.remaining.time_s-spent.time_s,energy_wh=s.remaining.energy_wh-spent.energy_wh,
                  oxygen_l=s.remaining.oxygen_l-spent.oxygen_l if kind=='human' else None))
    mask=g.traversability.copy();mask[:,2]=100;new=replace(g,map_version=2,traversability=mask)
    result=evaluate(pol,new,p,moved,pending(new,moved),EventKind.MAP,'new-obstacle',10.)
    assert result.reason_code=='CONTINGENCY_RETURN' and result.invalidate_active
    assert result.primary_candidate.status==RouteStatus.NO_PATH
    assert result.candidate.status==RouteStatus.FEASIBLE
    assert result.candidate_phase==MissionPhase.RETURN
    assert result.candidate.outbound_path[0]==pose
    assert result.candidate.start_connector is not None
    assert result.request.budget is moved.remaining and result.request.map_version==2
    assert result.candidate.cost_context.phase=='RETURN'
    assert result.candidate.cost_context.service==result.candidate.cost_context.waiting==()
    assert result.candidate.outbound_path[-1]==s.mission.return_to


@pytest.mark.parametrize('kind',['human','rover'])
def test_partial_scientific_service_then_explicit_wait_then_return(kind):
    g,p,s=scientific_case(kind,seconds=120.,waiting=30.);pol=policy()
    evaluate(pol,g,p,s,pending(g,s))
    profile=PROFILES[s.mission.agent_id]
    spent=[estimate_segment(profile,a,b) for a,b in zip(s.active_route.outbound_path,s.active_route.outbound_path[1:])]
    spent.append(estimate_activity(profile,'inspect',45.))
    remaining=replace(s.remaining,time_s=s.remaining.time_s-sum(c.time_s for c in spent),
                      energy_wh=s.remaining.energy_wh-sum(c.energy_wh for c in spent),
                      oxygen_l=s.remaining.oxygen_l-sum(c.oxygen_l for c in spent) if kind=='human' else None)
    service=replace(s,phase=MissionPhase.SERVICE,pose=s.mission.goal,remaining=remaining,service_remaining_s=75.)
    c=pending(g,service,(Activity('inspect','inspect',75.),))
    result=evaluate(pol,g,p,service,c,EventKind.TASK,'partial',10.)
    assert result.candidate.status==RouteStatus.FEASIBLE and result.request.budget is remaining
    assert result.candidate.cost_context.goal_costs[0]==105.
    assert result.candidate.cost_context.service[0].remaining_s==75.
    # Goal waiting is not silently abandoned merely because service duration is 0.
    done=replace(service,service_remaining_s=0.)
    wait=pending(g,done,(),(Activity('hold','wait',20.),))
    result=evaluate(pol,g,p,done,wait,EventKind.TASK,'wait',20.)
    assert result.candidate.status==RouteStatus.FEASIBLE
    assert result.candidate_phase==MissionPhase.SERVICE
    assert result.request.goal==s.mission.goal and result.candidate.cost_context.goal_costs[0]==20.
    # Explicit RETURN abandons all remaining goal work and plans one directed leg.
    returning=replace(done,phase=MissionPhase.RETURN)
    result=evaluate(pol,g,p,returning,pending(g,returning),EventKind.TASK,'return',30.)
    assert result.candidate.status==RouteStatus.FEASIBLE and not result.request.require_return
    assert result.candidate.cost_context.goal_costs==(0.,0.,0.)


def test_missing_model_mismatch_and_rollback_contexts_never_fall_back():
    g,p,s=scientific_case();pol=policy();c=pending(g,s)
    assert evaluate(pol,g,p,s,None).reason_code=='INVALID_SCIENTIFIC_CONTEXT'
    # Corrected context can produce a candidate but cannot itself authorize movement.
    assert evaluate(pol,g,p,s,c,event_id='correct',now=1.).action==ReplanAction.STOP_REQUIRED
    bad=replace(c,scenario_sha256='f'*64)
    assert evaluate(pol,g,p,s,bad,event_id='different',now=2.).reason_code=='INVALID_SCIENTIFIC_CONTEXT'
    legacy=plan_route(terrain=g,request=s.mission,profile=p)
    assert legacy.status==RouteStatus.FEASIBLE
    old=replace(s,active_route=legacy)
    assert evaluate(pol,g,p,old,None,event_id='downgrade',now=3.).reason_code=='SCIENTIFIC_MODEL_CHANGED'


def test_goal_work_cannot_be_completed_outbound_or_rolled_back_in_service():
    g,p,s=scientific_case();pol=policy();evaluate(pol,g,p,s,pending(g,s))
    bad=pending(g,s,waiting=())
    assert evaluate(pol,g,p,s,bad,event_id='early-wait',now=1.).reason_code=='INVALID_SCIENTIFIC_CONTEXT'
    service=replace(s,phase=MissionPhase.SERVICE,pose=s.mission.goal,service_remaining_s=5.)
    c=pending(g,service,(Activity('inspect','inspect',5.),))
    bad=replace(c,waiting=())
    assert evaluate(pol,g,p,service,bad,event_id='early',now=2.).reason_code=='INVALID_SCIENTIFIC_CONTEXT'
    evaluate(pol,g,p,service,c,EventKind.TASK,'partial',10.)
    bad=replace(service,service_remaining_s=6.)
    assert evaluate(pol,g,p,bad,pending(g,bad,(Activity('inspect','inspect',6.),)),now=11.).reason_code=='SERVICE_PROGRESS_ROLLBACK'


@pytest.mark.parametrize('kind',['human','rover'])
def test_scientific_D07_after_actual_twenty_metre_prefix(kind):
    import numpy as np
    from mge_planning.core import TerrainGrid
    from tests.planning.test_d07_twenty_metres import advance, length, misses_box
    g,p,s=scientific_case(kind,seconds=4.,waiting=2.)
    g=TerrainGrid('scientific-D07',1,np.zeros((9,18)),np.zeros((9,18)),3.,sigma_m=np.zeros((9,18)))
    r=replace(s.mission,run_id=g.run_id,start=(4.5,13.5,0.),goal=(43.5,13.5,0.),
              return_to=(4.5,13.5,0.),budget=replace(s.remaining,time_s=10000.,energy_wh=1000.))
    c=context(r,(Activity('inspect','inspect',4.),),(Activity('hold','wait',2.),))
    route=plan_route(terrain=g,request=r,profile=p,scientific_context=c)
    assert route.status==RouteStatus.FEASIBLE
    initial=ReplanState(r,r,route,MissionPhase.OUTBOUND,r.start,1,r.budget,4.)
    travelled,_=advance(route.outbound_path,20.)
    assert length(travelled)==pytest.approx(20.) and travelled[-1]!=g.point(g.cell(travelled[-1]))
    parts=[estimate_segment(PROFILES[r.agent_id],a,b) for a,b in zip(travelled,travelled[1:])]
    remaining=replace(r.budget,time_s=r.budget.time_s-sum(x.time_s for x in parts),
                      energy_wh=r.budget.energy_wh-sum(x.energy_wh for x in parts),
                      oxygen_l=r.budget.oxygen_l-sum(x.oxygen_l for x in parts) if kind=='human' else None)
    moved=replace(initial,pose=travelled[-1],next_waypoint=len(travelled)-1,remaining=remaining)
    obstacle=g.cell(route.outbound_path[-5]);mask=g.traversability.copy();mask[obstacle]=100
    updated=replace(g,map_version=2,traversability=mask)
    pol=policy();evaluate(pol,g,p,initial,pending(g,initial))
    decision=evaluate(pol,updated,p,moved,pending(updated,moved),EventKind.MAP,'new-obstacle',10.)
    result=decision.candidate
    assert result.status==RouteStatus.FEASIBLE and decision.candidate_phase==MissionPhase.OUTBOUND
    assert result.outbound_path[0]==moved.pose and result.map_version_used==2
    assert result.start_connector is not None and result.return_path[-1]==r.return_to
    assert decision.request.budget is remaining
    assert decision.candidate.cost_context.goal_costs[0]==6.
    radius=p.radius_m+p.localization_error_m;row,col=obstacle
    for path in (result.outbound_path,result.return_path):
        for a,b in zip(path,path[1:]):
            assert misses_box(a,b,(col*3-radius,row*3-radius),((col+1)*3+radius,(row+1)*3+radius))
    spent=sum(x.energy_wh for x in parts)
    assert spent+result.energy_est_wh+r.budget.reserve_wh<=r.budget.energy_wh
    assert sum(x.time_s for x in parts)+result.travel_time_s+r.reserve_time_s<=r.budget.time_s


def test_science_activity_wait_progress_cannot_increase_after_service():
    g,p,s=scientific_case();pol=policy();evaluate(pol,g,p,s,pending(g,s))
    done=replace(s,phase=MissionPhase.SERVICE,pose=s.mission.goal,service_remaining_s=0.)
    c=pending(g,done,(),(Activity('hold','wait',2.),))
    assert evaluate(pol,g,p,done,c,EventKind.TASK,'wait',10.).candidate.status==RouteStatus.FEASIBLE
    bad=replace(c,waiting=(Activity('hold','wait',3.),))
    result=evaluate(pol,g,p,done,bad,event_id='rollback-wait',now=11.)
    assert result.reason_code=='INVALID_SCIENTIFIC_CONTEXT' and result.request is None and result.invalidate_active
