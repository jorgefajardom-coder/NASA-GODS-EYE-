"""Real multi-label search against independent enumeration; no ROS activation."""
from dataclasses import replace
import math
from types import SimpleNamespace

import numpy as np
import pytest

from mge_mission.models import CostEstimate, estimate_activity, estimate_segment
from mge_planning.core import (
    GeometryCache, RouteStatus, SearchLimits, _ScientificGeometry, _Work, _motion_costs,
    _search, plan_route,
)
from mge_planning.resource_costs import Activity
from tests.planning.scientific_oracle import choose, enumerate_itineraries
from tests.planning.test_scientific_context import PROFILES, context, scene
from tests.planning.test_scientific_oracle import EDGES, POINTS


class GraphGeometry:
    """Explicit synthetic admitted graph ONLY; actual search is not replaced."""
    def __init__(self,p):
        self.grid=SimpleNamespace(point=POINTS.__getitem__,resolution_m=2.)
        self.profile=p
        self.allowed={n:True for n in POINTS}
        self.known=self.allowed
        self.clearance={n:5. for n in POINTS}

    def edge(self,a,b):
        if (a,b) not in EDGES:return None
        return (EDGES[a,b],*_motion_costs(self.profile,math.dist(POINTS[a][:2],POINTS[b][:2]),
                                        POINTS[b][2]-POINTS[a][2]))

    def neighbours(self,cell,threshold=0.):
        for a,b in EDGES:
            if a==cell and EDGES[a,b]>=threshold:yield b,self.edge(a,b)


@pytest.mark.parametrize('mode',['FAST','SAFE'])
@pytest.mark.parametrize('cap',[1.36,100.])
def test_real_search_engine_matches_graph_oracle_and_route_flip(mode,cap):
    g,p,r=scene()
    r=replace(r,start=POINTS['S'],goal=POINTS['G'],return_to=POINTS['S'],mode=mode,
              budget=replace(r.budget,energy_wh=cap+1.))
    c=context(r);c.validate(r,p)
    geometry=_ScientificGeometry(GraphGeometry(p),c)
    work=_Work(SearchLimits(10000,10.))
    found=_search(geometry,r,'S','G','S',0.,work)
    assert found is not None
    if mode=='SAFE':
        while True:
            threshold=math.nextafter(found.labels[found.terminal].clearance,math.inf)
            candidate=_search(geometry,r,'S','G','S',threshold,work)
            if candidate is None:break
            found=candidate
    reference=choose(enumerate_itineraries(PROFILES['human_1'],POINTS,EDGES,'S','G','S',()),
                     CostEstimate(r.budget.time_s,r.budget.energy_wh,r.budget.oxygen_l),
                     CostEstimate(r.reserve_time_s,r.budget.reserve_wh,r.budget.reserve_oxygen_l),safe=mode=='SAFE')
    final=found.labels[found.terminal]
    assert (final.time,final.energy,final.oxygen,final.clearance)==pytest.approx(
        (reference.cost.time_s,reference.cost.energy_wh,reference.cost.oxygen_l,reference.clearance))
    out=[];idx=found.terminal
    while idx is not None:
        label=found.labels[idx]
        if not label.phase:out.append(label.cell)
        idx=label.parent
    assert tuple(reversed(out))==reference.outbound
    if cap==1.36:assert reference.outbound==('S','D','G')


def raster_graph(g,p):
    """Independent open-raster boundary model for a tiny exhaustive oracle.

    No production geometry/cost/pruning helper is used. Obstacle cases below
    separately exercise actual production geometry, not this open-grid oracle.
    """
    points={(r,c):g.point((r,c)) for r in range(g.rows) for c in range(g.cols)}
    radius=p.radius_m+p.localization_error_m
    def margin(a):
        x,y,_=points[a]
        return min(x-g.origin_x_m,y-g.origin_y_m,g.cols*g.resolution_m+g.origin_x_m-x,
                   g.rows*g.resolution_m+g.origin_y_m-y)-radius
    edges={}
    for a in points:
        for b in points:
            if a!=b and max(abs(a[i]-b[i]) for i in (0,1))==1:
                edges[a,b]=min(margin(a),margin(b))
    return points,edges


@pytest.mark.parametrize('kind',['human','rover'])
@pytest.mark.parametrize('mode',['FAST','SAFE'])
def test_public_planner_raster_matches_full_itinerary_oracle(kind,mode):
    service=(Activity('inspect','inspect',7.),)
    waiting=(Activity('hold','wait',3.),)
    g,p,r=scene(kind,service);r=replace(r,mode=mode)
    c=context(r,service,waiting)
    result=plan_route(terrain=g,request=r,profile=p,scientific_context=c)
    assert result.status==RouteStatus.FEASIBLE
    points,edges=raster_graph(g,p)
    ref=choose(enumerate_itineraries(PROFILES[r.agent_id],points,edges,(0,0),(0,2),(0,0),
               [('inspect','inspect',7.),('hold','wait',3.)]),
               CostEstimate(r.budget.time_s,r.budget.energy_wh,r.budget.oxygen_l),
               CostEstimate(r.reserve_time_s,r.budget.reserve_wh,r.budget.reserve_oxygen_l),safe=mode=='SAFE')
    assert (result.travel_time_s,result.energy_est_wh,result.min_clearance_m)==pytest.approx(
        (ref.cost.time_s,ref.cost.energy_wh,ref.clearance))
    assert result.oxygen_est_l==pytest.approx(ref.cost.oxygen_l) if kind=='human' else result.oxygen_est_l is None
    assert result.cost_context is c
    assert result.return_path[-1]==r.return_to


@pytest.mark.parametrize('kind',['human','rover'])
def test_connector_and_partial_service_costs_only_pending_work(kind):
    work=(Activity('inspect','inspect',75.),)
    g,p,r=scene(kind,work)
    r=replace(r,start=(r.start[0]+.37,r.start[1],r.start[2]))
    c=context(r,work)
    result=plan_route(terrain=g,request=r,profile=p,scientific_context=c,allow_continuous_start=True)
    assert result.status==RouteStatus.FEASIBLE and result.outbound_path[0]==r.start
    b=PROFILES[r.agent_id];conn=estimate_segment(b,r.start,g.point((0,0)))
    assert result.start_connector.energy_est_wh==conn.energy_wh
    parts=[estimate_segment(b,a,z) for path in (result.outbound_path,result.return_path) for a,z in zip(path,path[1:])]
    parts+=[estimate_activity(b,'inspect',75.)]
    assert result.energy_est_wh==pytest.approx(sum(x.energy_wh for x in parts))
    assert result.travel_time_s==pytest.approx(sum(x.time_s for x in parts))
    # Explicit SERVICE starts at the goal; only its unfinished service and return.
    r=replace(r,start=r.goal);c=context(r,work,phase='SERVICE')
    s=plan_route(terrain=g,request=r,profile=p,scientific_context=c)
    assert s.status==RouteStatus.FEASIBLE and s.outbound_path==(r.goal,)


@pytest.mark.parametrize('kind',['human','rover'])
def test_directional_costs_and_cache_do_not_reuse_reverse_or_backend(kind):
    g,p,r=scene(kind);cache=GeometryCache();c=context(r)
    view=_ScientificGeometry(cache.get(g,p),c)
    up=view.edge((0,0),(0,1));down=view.edge((0,1),(0,0))
    assert up[2]>down[2]
    legacy=plan_route(terrain=g,request=r,profile=p,geometry_cache=cache)
    science=plan_route(terrain=g,request=r,profile=p,geometry_cache=cache,scientific_context=c)
    again=plan_route(terrain=g,request=r,profile=p,geometry_cache=cache)
    assert legacy.route_id==again.route_id and legacy.energy_est_wh==again.energy_est_wh
    assert science.route_id!=legacy.route_id and science.cost_context is c


@pytest.mark.parametrize('field',['time_s','energy_wh','oxygen_l'])
def test_strict_science_budget_boundary_and_sub_tolerance_shortage(field):
    work=(Activity('task','inspect',1.),);g,p,r=scene(service=work)
    r=replace(r,goal=r.start,return_to=r.start,reserve_time_s=0.,
              budget=replace(r.budget,reserve_wh=0.,reserve_oxygen_l=0.))
    c=context(r,work);cost=c.goal_costs
    r=replace(r,budget=replace(r.budget,time_s=cost[0],energy_wh=cost[1],oxygen_l=cost[2]))
    c=replace(c,request=r)
    assert plan_route(terrain=g,request=r,profile=p,scientific_context=c).status==RouteStatus.FEASIBLE
    bad=replace(r,budget=replace(r.budget,**{field:math.nextafter(getattr(r.budget,field),0.)}))
    rejected=plan_route(terrain=g,request=bad,profile=p,scientific_context=replace(c,request=bad))
    assert rejected.status==RouteStatus.INSUFFICIENT_BUDGET


@pytest.mark.parametrize('issue',['obstacle','unknown','nodata','sigma','slope','step','z','connector'])
def test_science_preserves_raster_geometry_safety(issue):
    g,p,r=scene();c=context(r)
    if issue in ('obstacle','unknown'):
        mask=g.traversability.copy();mask[:,1]=100 if issue=='obstacle' else -1
        g=replace(g,traversability=mask)
    elif issue in ('nodata','slope','step'):
        height=g.elevation_m.copy();height[:,1]={'nodata':np.nan,'slope':1.,'step':.21}[issue]
        g=replace(g,elevation_m=height)
    elif issue=='sigma':
        sigma=g.sigma_m.copy();sigma[:,1]=2.;g=replace(g,sigma_m=sigma)
    elif issue=='z':r=replace(r,start=(1.,1.,.1));c=replace(c,request=r)
    else:
        r=replace(r,start=(.1,1.,0.));c=replace(c,request=r)
    result=plan_route(terrain=g,request=r,profile=p,scientific_context=c,allow_continuous_start=True)
    assert result.status!=RouteStatus.FEASIBLE
    assert result.outbound_path==()


def test_invalid_context_is_not_legacy_fallback_and_limits_fail_unknown():
    g,p,r=scene()
    for c in [{}, object(), context(replace(r,request_id='other'))]:
        assert plan_route(terrain=g,request=r,profile=p,scientific_context=c).reason_code=='INVALID_SCIENTIFIC_CONTEXT'
    result=plan_route(terrain=g,request=r,profile=p,scientific_context=context(r),limits=SearchLimits(1,10.))
    assert result.status==RouteStatus.UNKNOWN and result.reason_code=='SEARCH_LIMIT'


def test_same_numeric_activities_still_bind_different_context_provenance():
    work=(Activity('a','inspect',10.),);g,p,r=scene(service=work)
    first=plan_route(terrain=g,request=r,profile=p,scientific_context=context(r,work))
    other=plan_route(terrain=g,request=r,profile=p,scientific_context=context(r,(Activity('a','wait',10.),)))
    assert first.energy_est_wh==other.energy_est_wh and first.route_id!=other.route_id


@pytest.mark.parametrize('mode',['FAST','SAFE'])
def test_actual_raster_route_changes_before_pruning_and_matches_oracle(mode):
    g,p,r=scene();g=replace(g,elevation_m=np.array([[0.,.2,0.],[0.,0.,0.]]))
    r=replace(r,mode=mode,budget=replace(r.budget,energy_wh=2.6))  # usable cap 1.6 Wh
    legacy=plan_route(terrain=g,request=r,profile=p)
    science=plan_route(terrain=g,request=r,profile=p,scientific_context=context(r))
    assert legacy.status==science.status==RouteStatus.FEASIBLE
    assert g.point((0,1)) in legacy.outbound_path and g.point((0,1)) not in science.outbound_path
    points,edges=raster_graph(g,p)
    oracle=choose(enumerate_itineraries(PROFILES[r.agent_id],points,edges,(0,0),(0,2),(0,0),()),
                  CostEstimate(r.budget.time_s,r.budget.energy_wh,r.budget.oxygen_l),
                  CostEstimate(r.reserve_time_s,r.budget.reserve_wh,r.budget.reserve_oxygen_l),safe=mode=='SAFE')
    assert science.travel_time_s==pytest.approx(oracle.cost.time_s)
    assert science.energy_est_wh==pytest.approx(oracle.cost.energy_wh)
    assert science.energy_est_wh<=1.6


def test_scientific_cache_is_not_retained_across_map_snapshot_changes():
    g,p,r=scene();cache=GeometryCache()
    first=plan_route(terrain=g,request=r,profile=p,scientific_context=context(r),geometry_cache=cache)
    new=replace(g,map_version=2,elevation_m=np.zeros((2,3)))
    req=replace(r,map_version=2)
    second=plan_route(terrain=new,request=req,profile=p,scientific_context=context(req),geometry_cache=cache)
    assert first.energy_est_wh>second.energy_est_wh
    assert first.route_id!=second.route_id and cache.grid is new


@pytest.mark.parametrize('kind',['human','rover'])
def test_medium_grid_has_bounded_work_without_a_wall_time_performance_claim(kind):
    g,p,r=scene(kind)
    g=replace(g,elevation_m=np.zeros((12,12)),traversability=np.zeros((12,12)),sigma_m=np.zeros((12,12)))
    r=replace(r,goal=g.point((10,10)),budget=replace(r.budget,time_s=10000.,energy_wh=1000.))
    result=plan_route(terrain=g,request=r,profile=p,scientific_context=context(r),limits=SearchLimits(10000,10.))
    assert result.status==RouteStatus.FEASIBLE and 0<result.expanded_labels<=10000
    stopped=plan_route(terrain=g,request=r,profile=p,scientific_context=context(r),limits=SearchLimits(1,10.))
    assert stopped.status==RouteStatus.UNKNOWN and stopped.reason_code=='SEARCH_LIMIT'


def test_legacy_import_does_not_require_mission_package():
    import os
    import subprocess
    import sys
    from tests.planning.test_scientific_context import ROOT
    env=dict(os.environ,PYTHONPATH=str(ROOT/'src/mge_planning'))
    subprocess.run([sys.executable,'-c',
                    "import sys; import mge_planning.core; import mge_planning.replan; "
                    "assert 'mge_mission' not in sys.modules; "
                    "assert 'mge_planning.resource_costs' not in sys.modules"],
                   env=env,check=True)
