"""Synthetic full-coverage local-surface experiments using the unchanged A*."""
from dataclasses import replace,asdict
import json,math,time
import numpy as np
import pytest
from mge_planning.core import TerrainGrid,plan_route,SearchLimits
from mge_planning.local_surface import LocalSurface,SurfaceLimits,evaluate_surface
from tests.planning.test_scientific_context import scene,context

NAMES=('flat','ramp5','ramp10','ramp15','ramp25','step','missing','side10','side35','crest','valley','rough','alternative','sigma','nodata')

def setup_case(kind,name,mode='FAST'):
 _,p,r=scene(kind);n=9;spacing=.35/math.tan(math.radians(5));fine=spacing/n
 y,x=np.indices((27,45));xx=(x+.5)*fine;yy=(y+.5)*fine
 slope={'ramp5':5,'ramp10':10,'ramp15':15,'ramp25':25}.get(name,0)
 z=xx*math.tan(math.radians(slope))
 if name=='step':z=np.where(xx>=2.5*spacing,.35,0.)
 if name.startswith('side'):z=yy*math.tan(math.radians(int(name[4:])))
 if name in ('crest','valley'):z=(1 if name=='crest' else -1)*abs(xx-2.5*spacing)*.02
 if name=='rough':z=((x+y)%2)*.05
 mask=np.zeros_like(z);sigma=np.zeros_like(z)
 if name in ('rough','alternative'):mask[11:16,21:24]=100
 if name=='sigma':sigma[:]=10.
 if name=='nodata':z=z.copy();z[10,20]=np.nan
 g=TerrainGrid('synthetic-f02',1,z,mask,fine,sigma_m=sigma)
 coarse=TerrainGrid(g.run_id,1,z[4::9,4::9],np.zeros((3,5)),spacing,sigma_m=np.zeros((3,5)))
 r=replace(r,run_id=g.run_id,start=coarse.point((1,1)),goal=coarse.point((1,3)),return_to=coarse.point((1,1)),mode=mode,budget=replace(r.budget,time_s=10000.,energy_wh=1000.))
 surface=LocalSurface(g,'analytic-'+name,'map','SYNTHETIC_Z_UP',fine)
 if name=='missing':surface=replace(surface,native_spacing_m=20.)
 limits=SurfaceLimits(.5,30.,.1)
 return coarse,p,r,surface,limits

@pytest.mark.parametrize('kind',['human','rover'])
@pytest.mark.parametrize('mode',['FAST','SAFE'])
@pytest.mark.parametrize('name',NAMES)
def test_matrix(kind,mode,name,record_property):
 coarse,p,r,s,l=setup_case(kind,name,mode)
 before=s.fingerprint;old=plan_route(terrain=coarse,profile=p,request=r)
 started=time.perf_counter();out=evaluate_surface(terrain=coarse,profile=p,request=r,surface=s,limits=l,vertical_datum=s.vertical_datum)
 result=out.candidate;elapsed=time.perf_counter()-started
 assert s.fingerprint==before and not out.authorization and out.is_current(s,coarse,l,p)
 if name in ('flat','ramp5','alternative','side10','crest','valley'):
  assert result.status.value=='FEASIBLE',(name,result.reason_code)
  assert result.return_path[-1]==r.return_to
  assert result.reserve_wh>=r.budget.reserve_wh
  assert result.reserve_time_s>=r.reserve_time_s
  if kind=='human':assert result.reserve_oxygen_l>=r.budget.reserve_oxygen_l
 if name=='ramp5':assert old.status.value!='FEASIBLE'
 if name in ('missing','sigma','nodata'):assert result.status.value=='UNKNOWN'
 if name in ('step','side35','ramp25'):assert result.status.value!='FEASIBLE'
 record_property('surface_comparison',json.dumps({'scenario':name,'kind':kind,'mode':mode,'profile':asdict(p),'native_m':s.native_spacing_m,'evaluation_m':s.grid.resolution_m,'coarse_m':coarse.resolution_m,'evidence':s.fingerprint,'legacy':old.status.value,'legacy_reason':old.reason_code,'experimental':result.status.value,'reason':result.reason_code,'time_s':result.travel_time_s,'energy_wh':result.energy_est_wh,'oxygen_l':result.oxygen_est_l,'reserve_wh':result.reserve_wh,'labels':result.expanded_labels,'latency_s':elapsed},allow_nan=True))

@pytest.mark.parametrize('kind',['human','rover'])
def test_identity_staleness_science_continuous_and_bounds(kind):
 g,p,r,s,l=setup_case(kind,'ramp5')
 out=evaluate_surface(terrain=g,profile=p,request=r,surface=s,limits=l,vertical_datum=s.vertical_datum,scientific_context=context(r))
 assert out.candidate.status.value=='FEASIBLE' and out.candidate.cost_context is not None
 assert (out.candidate.run_id,out.candidate.request_id,out.candidate.agent_id)==(r.run_id,r.request_id,r.agent_id)
 new=replace(g,map_version=2)
 assert not out.is_current(s,new,l,p)
 stale=evaluate_surface(terrain=new,profile=p,request=replace(r,map_version=2),surface=s,limits=l,vertical_datum=s.vertical_datum)
 assert stale.candidate.status.value=='STALE_MAP'
 tiny=evaluate_surface(terrain=g,profile=p,request=r,surface=s,limits=l,vertical_datum=s.vertical_datum,search_limits=SearchLimits(max_labels=1))
 assert tiny.candidate.reason_code=='SEARCH_LIMIT'
 # Explicit local-grid surface telemetry, never projected from coarse z.
 point=s.grid.point(s.grid.cell(r.start));pose=(point[0]+.01,point[1],point[2])
 continuous=evaluate_surface(terrain=g,profile=p,request=replace(r,start=pose),surface=s,limits=l,vertical_datum=s.vertical_datum,allow_continuous_start=True)
 assert continuous.candidate.status.value=='FEASIBLE'
 assert continuous.candidate.outbound_path[0]==pose
 assert continuous.candidate.start_connector is not None
 bad=evaluate_surface(terrain=g,profile=p,request=r,surface=s,limits=l,vertical_datum='wrong')
 assert bad.candidate.reason_code=='SURFACE_DATUM_MISMATCH'

@pytest.mark.parametrize('kind',['human','rover'])
def test_cost_audit_reserve_and_same_grid_policy(kind):
 from mge_mission.models import estimate_segment,estimate_activity
 from mge_planning.resource_costs import Activity
 from mge_planning.replan import ReplanState,MissionPhase,ReplanEvent,EventKind
 from tests.planning.test_replan_policy import policy
 from tests.planning.test_scientific_context import PROFILES
 g,p,r,s,l=setup_case(kind,'ramp5')
 r=replace(r,service_time_s=1.)
 c=context(r,(Activity('pending','inspect',1.),))
 out=evaluate_surface(terrain=g,profile=p,request=r,surface=s,limits=l,vertical_datum=s.vertical_datum,scientific_context=c)
 route=out.candidate;assert route.status.value=='FEASIBLE'
 costs=[estimate_segment(PROFILES[r.agent_id],a,b) for path in (route.outbound_path,route.return_path) for a,b in zip(path,path[1:])]
 costs.append(estimate_activity(PROFILES[r.agent_id],'inspect',1.))
 assert route.energy_est_wh==pytest.approx(sum(x.energy_wh for x in costs))
 assert route.travel_time_s==pytest.approx(sum(x.time_s for x in costs))
 if kind=='human':assert route.oxygen_est_l==pytest.approx(sum(x.oxygen_l for x in costs))
 state=ReplanState(r,r,route,MissionPhase.OUTBOUND,r.start,1,r.budget,1.)
 decision=policy().evaluate(terrain=out.evaluation_grid,profile=p,state=state,scientific_context=c,
     event=ReplanEvent('same-surface',g.run_id,1,EventKind.TICK),now_s=0.)
 assert decision.action.value=='KEEP'
 low=replace(r,budget=replace(r.budget,energy_wh=r.budget.reserve_wh),service_time_s=0.)
 exhausted=evaluate_surface(terrain=g,profile=p,request=low,surface=s,limits=l,vertical_datum=s.vertical_datum)
 assert exhausted.candidate.status.value=='INSUFFICIENT_BUDGET'
 assert not out.is_current(s,g,replace(l,max_plane_residual_m=.2),p)
 changed=replace(s,source_id='another-source')
 assert not out.is_current(changed,g,l,p)
 assert evaluate_surface(terrain=g,profile=p,request=r,surface=changed,limits=l,vertical_datum=s.vertical_datum,scientific_context=c).candidate.route_id!=route.route_id

@pytest.mark.parametrize('kind',['human','rover'])
@pytest.mark.parametrize('change,reason',[
 ('origin','SURFACE_GEOMETRY_MISMATCH'),('run','SURFACE_MAP_MISMATCH'),
 ('coverage','INSUFFICIENT_TERRAIN_EVIDENCE'),('sigma_downgrade','SURFACE_EVIDENCE_DOWNGRADE')])
def test_reject_incompatible_surface(kind,change,reason):
 g,p,r,s,l=setup_case(kind,'flat')
 if change=='origin':s=replace(s,grid=replace(s.grid,origin_x_m=.1))
 if change=='run':s=replace(s,grid=replace(s.grid,run_id='other'))
 if change=='coverage':
  mask=s.grid.traversability.copy();mask[1,1]=-1;s=replace(s,grid=replace(s.grid,traversability=mask))
 if change=='sigma_downgrade':g=replace(g,sigma_m=np.full_like(g.elevation_m,.1))
 out=evaluate_surface(terrain=g,profile=p,request=r,surface=s,limits=l,vertical_datum=s.vertical_datum)
 assert out.candidate.reason_code==reason and out.candidate.status.value!='FEASIBLE'

@pytest.mark.parametrize('kind',['human','rover'])
def test_diagonal_and_immutable_evidence(kind):
 from dataclasses import FrozenInstanceError
 g,p,r,s,l=setup_case(kind,'ramp5');r=replace(r,goal=g.point((2,3)))
 out=evaluate_surface(terrain=g,profile=p,request=r,surface=s,limits=l,vertical_datum=s.vertical_datum)
 assert out.candidate.status.value=='FEASIBLE'
 assert any(a[0]!=b[0] and a[1]!=b[1] for a,b in zip(out.candidate.outbound_path,out.candidate.outbound_path[1:]))
 with pytest.raises(FrozenInstanceError):s.source_id='changed'
 with pytest.raises(ValueError):s.grid.elevation_m[1,1]=9.
 with pytest.raises(ValueError):replace(s,frame_id='odom')

@pytest.mark.parametrize('kind',['human','rover'])
def test_ramp_and_step_exact_same_endpoint_rise(kind):
 outcomes=[];rises=[]
 for name in ('ramp5','step'):
  g,p,r,s,l=setup_case(kind,name)
  r=replace(r,goal=g.point((1,2)))
  rises.append(r.goal[2]-r.start[2])
  outcomes.append(evaluate_surface(terrain=g,profile=p,request=r,surface=s,limits=l,vertical_datum=s.vertical_datum).candidate.status.value)
 assert rises==pytest.approx([.35,.35])
 assert outcomes[0]=='FEASIBLE' and outcomes[1]!='FEASIBLE'
