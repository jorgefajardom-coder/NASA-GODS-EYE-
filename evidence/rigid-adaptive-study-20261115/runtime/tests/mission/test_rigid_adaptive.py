"""Independent accounting/retreat controls for the local analytical extension."""
import json
from pathlib import Path
import subprocess
import sys

import pytest


ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / ".local/rigid-adaptive-study/frozen-main"


def invoke(body):
    """Keep the exact-source experimental namespace out of other unit tests."""
    if not (SOURCE / "src/mge_planning/mge_planning/resource_costs.py").exists():
        pytest.skip("Explicit published source snapshot is not materialized")
    setup = f"""
import sys, json
from pathlib import Path
from dataclasses import replace
root=Path({str(ROOT)!r})
source=Path({str(SOURCE)!r})
sys.path[:0]=[str(source/'src'/p) for p in ('mge_mission','mge_planning','mge_mapping','mge_data')]
import mge_mission
mge_mission.__path__.append(str(root/'src/mge_mission/mge_mission'))
from mge_mission.research import rigid_adaptive as study
from mge_mission.models import load_profiles, estimate_segment, export_planner_profiles
profile=load_profiles(source/'config/science_profiles.proposed.json')['human_1']
motion=study.core.MotionProfile(**export_planner_profiles({{'human_1':profile}})['profiles']['human_1'])
"""
    result = subprocess.run([sys.executable, "-c", setup + body], cwd=ROOT,
                            capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stdout + result.stderr
    return json.loads(result.stdout)


def test_reserves_are_not_numerical_credit():
    value = invoke("""
available={'time_s':10.,'energy_wh':1.,'oxygen_l':None}
reserve={'time_s':0.,'energy_wh':.5,'oxygen_l':None}
print(json.dumps({'at':study._fits({'time_s':0.,'energy_wh':.5,'oxygen_l':None},available,reserve),
                  'over':study._fits({'time_s':0.,'energy_wh':.5+1e-10,'oxygen_l':None},available,reserve)}))
""")
    assert value == {"at": True, "over": False}


def test_actual_directed_xyz_is_debited_once_and_guard_stops_before_obstacle():
    value = invoke("""
class World:
    def ask(self,**message):
        return {'traversed_points':[(2.,2.,0.),(6.,2.,.15)],'stop_reason':'HALT_BEFORE_PRIVATE_INADMISSIBLE_SEGMENT'}
available={'time_s':1000.,'energy_wh':100.,'oxygen_l':30.}
reserve={'time_s':100.,'energy_wh':10.,'oxygen_l':3.}
ledger=[]
actual,remaining,stop=study._execute(World(),{'origin_x_m':0.,'origin_y_m':0.},profile,motion,
 available,reserve,[(2.,2.,0.),(6.,2.,0.),(10.,2.,0.)],ledger,'guarded')
expected=estimate_segment(profile,(2.,2.,0.),(6.,2.,.15))
assert len(ledger)==1
assert actual[-1]==(6.,2.,.15)
assert all(abs(remaining[k]-(available[k]-getattr(expected,k)))<1e-10 for k in available)
assert ledger[0]['end']==actual[-1]
print(json.dumps({'stop':stop,'intervals':len(ledger),'pose':actual[-1]}))
""")
    assert value["stop"] == "HALT_BEFORE_PRIVATE_INADMISSIBLE_SEGMENT"
    assert value["intervals"] == 1
    assert value["pose"] == [6.0, 2.0, 0.15]


def test_unaffordable_segment_is_not_entered_or_debited():
    value = invoke("""
class World:
    def ask(self,**message):
        return {'traversed_points':[(2.,2.,0.),(6.,2.,0.)],'stop_reason':'PREFIX_REACHED'}
edge=estimate_segment(profile,(2.,2.,0.),(6.,2.,0.))
available={'time_s':1000.,'energy_wh':10.+edge.energy_wh-1e-10,'oxygen_l':30.}
reserve={'time_s':0.,'energy_wh':10.,'oxygen_l':0.}
ledger=[]
actual,remaining,stop=study._execute(World(),{'origin_x_m':0.,'origin_y_m':0.},profile,motion,
 available,reserve,[(2.,2.,0.),(6.,2.,0.)],ledger,'resource')
assert actual==[(2.,2.,0.)] and remaining==available and ledger==[]
print(json.dumps({'stop':stop}))
""")
    assert value["stop"] == "RESOURCE_GUARD_HALT"


def test_optional_guard_retreat_preserves_the_previous_return_to_base():
    value = invoke("""
from types import SimpleNamespace
base=(2.,2.,0.);goal=(6.,2.,0.);optional=(10.,2.,0.)
class World:
    def ask(self,**message):
        cells=message['cells']
        if cells==[[0,1],[0,2]]:
            return {'traversed_points':[goal],'stop_reason':'HALT_BEFORE_PRIVATE_INADMISSIBLE_SEGMENT'}
        return {'traversed_points':[(2.+4*c,2.+4*r,0.) for r,c in cells],'stop_reason':'PREFIX_REACHED'}
def plan(*args,**kwargs):
    label=args[12]
    if label=='posterior-primary':
        result=SimpleNamespace(status=study.core.RouteStatus.FEASIBLE,outbound_path=[goal],return_path=[goal,base])
    else:
        result=SimpleNamespace(status=study.core.RouteStatus.FEASIBLE,outbound_path=[goal,optional],return_path=[optional,goal,base])
    return result,{'status':'FEASIBLE'}
study._plan=plan
event={'available':True,'capable_kinds':['human'],'prerequisite':'PRIMARY_B_COMPLETED',
 'activity':'inspect','duration_s':10.,'position':optional,'event_id':'public-notice'}
result=study._strategy('ADAPTIVE',{},World(),{'origin_x_m':0.,'origin_y_m':0.},profile,motion,None,
 {'time_s':1000.,'energy_wh':100.,'oxygen_l':30.}, {'time_s':0.,'energy_wh':0.,'oxygen_l':0.},
 goal,base,goal,[goal],[goal,base],[], 'FAST',{},event,[])
print(json.dumps({'primary':result['primary_completed'],'returned':result['returned'],'optional':result['optional_completed']}))
""")
    assert value == {"primary": True, "returned": True, "optional": 0}
