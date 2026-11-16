"""Synthetic terrain diagnostics, never observed Mars microtopography."""
from dataclasses import replace,asdict
import math,json,time
from pathlib import Path
import numpy as np
import pytest
from mge_planning.core import plan_route
from mge_planning.terrain_diagnostics import TerrainEvidence,DiscontinuityEvidence,diagnose
from tests.planning.terrain_fixtures import scene,PROFILES
from mge_mission.models import estimate_segment

SCENARIOS=('flat','ramp5','ramp10','ramp15','over_limit','step','down','cross','crest','valley','turn','rough','unknown','nodata','alternative')

def fixture(kind,name):
 g,p,r=scene(kind);yy,xx=np.indices((9,9));angle={'ramp5':5,'ramp10':10,'ramp15':15,'over_limit':45,'down':-5}.get(name,0)
 z=xx*4*math.tan(math.radians(angle));mask=np.zeros((9,9));sigma=np.zeros((9,9))
 if name=='step':z=np.where(xx>=5,4*math.tan(math.radians(5)),0.)
 if name=='cross':z=yy*4*math.tan(math.radians(10))
 if name in ('crest','valley'):z=(1 if name=='crest' else -1)*(.1-np.abs(xx-4)*.025)
 if name=='turn':z=(xx+yy)*.02
 if name=='rough':z=((xx+yy)%2)*.1;mask[3,5]=100
 if name=='unknown':sigma[4,5]=10.
 if name=='nodata':z=z.copy();z[4,5]=np.nan
 if name=='alternative':mask[4,4]=100
 g=replace(g,elevation_m=z,traversability=mask,sigma_m=sigma,resolution_m=4.)
 r=replace(r,budget=replace(r.budget,time_s=10000.),start=g.point((4,2)),goal=g.point((4,6)),return_to=g.point((4,2)))
 return g,p,r

@pytest.mark.parametrize('kind',['human','rover'])
@pytest.mark.parametrize('name',SCENARIOS)
def test_scenarios(kind,name,record_property):
 g,p,r=fixture(kind,name);before=g.elevation_m.copy();a,b=(4,4),(4,5)
 e=TerrainEvidence('SYNTHETIC',.01 if name=='step' else 4.,'analytic-'+name)
 jump=DiscontinuityEvidence(1.995,2.005,0.,4*math.tan(math.radians(5)),e) if name=='step' else None
 d=diagnose(g,p,a,b,e,discontinuity=jump)
 assert d==diagnose(g,p,a,b,e,discontinuity=jump) and not d['authorization']
 np.testing.assert_array_equal(g.elevation_m,before)
 if name.startswith('ramp') or name=='down':
  degrees=-5 if name=='down' else int(name[4:])
  assert d['longitudinal_deg']==pytest.approx(degrees)
  assert d['delta_z_m']==pytest.approx(4*math.tan(math.radians(degrees)))
  assert d['local_jump_m'] is None
 if name=='step':assert 'RESOLVED_LOCAL_JUMP_EXCEEDS_STEP_LIMIT' in d['reasons']
 if name=='turn':assert diagnose(g,p,(4,4),(5,4),e)['longitudinal_deg']!=None
 if name=='cross':assert abs(d['transverse_deg'])==pytest.approx(10.)
 if name in ('unknown','nodata'):assert 'INSUFFICIENT_LOCAL_PATCH' in d['reasons']
 if name in ('crest','valley'):assert d['raster_plane_residual_rms_m']>0
 if name=='rough':assert 'INSUFFICIENT_LOCAL_PATCH' in d['reasons']
 if name=='flat':assert d['raster_plane_residual_rms_m']==pytest.approx(0.)
 if name=='over_limit':assert 'LONGITUDINAL_LIMIT_EXCEEDED' in d['reasons']
 start=time.perf_counter();result=plan_route(terrain=g,profile=p,request=r);elapsed=time.perf_counter()-start
 if name=='alternative':assert result.status.value=='FEASIBLE'
 if name=='ramp5':assert result.status.value!='FEASIBLE'
 record_property('comparison',json.dumps({'agent':kind,'scenario':name,'profile':asdict(p),'diagnostic':d,'current_status':result.status.value,'current_reason':result.reason_code,'labels':result.expanded_labels,'latency_s':elapsed},allow_nan=False))

@pytest.mark.parametrize('kind',['human','rover'])
def test_directional_costs_and_insufficient_orbital_evidence(kind):
 g,p,_=fixture(kind,'ramp5');e=TerrainEvidence('ORBITAL_ESTIMATE',20.,'CTX-resampled-synthetic-example')
 d=diagnose(g,p,(4,4),(4,5),e)
 assert d['local_jump_m'] is None and 'INSUFFICIENT_TERRAIN_EVIDENCE' in d['reasons']
 a,b=g.point((4,4)),g.point((4,5));science=PROFILES[kind+'_1']
 assert estimate_segment(science,a,b).energy_wh!=estimate_segment(science,b,a).energy_wh
 with pytest.raises(ValueError):DiscontinuityEvidence(1.,1.01,0.,.3,e)
