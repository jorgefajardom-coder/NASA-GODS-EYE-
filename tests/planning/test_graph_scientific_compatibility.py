"""Original S/H/D/G oracle against PR50 search, not a second backend."""
from dataclasses import replace
from types import SimpleNamespace
import math,json
import pytest
from mge_planning.core import _search,_Work,SearchLimits
from mge_planning.resource_costs import ScientificCosts
from mge_mission.models import CostEstimate
from tests.planning.test_scientific_oracle import POINTS,EDGES,PROFILES,runs
from tests.planning.scientific_oracle import choose
from tests.planning.terrain_fixtures import scene

CELLS={name:(point[1]/2.,point[0]/2.) for name,point in POINTS.items()}
REVERSE={cell:POINTS[name] for name,cell in CELLS.items()}
class AdmittedGraph:
 def __init__(self,profile):
  self.grid=SimpleNamespace(point=REVERSE.__getitem__,resolution_m=2.)
  self.profile=profile;self.cost_model=ScientificCosts(PROFILES['human_1'])
  self.allowed={k:True for k in REVERSE};self.clearance={k:5. for k in REVERSE}
 def neighbours(self,cell,threshold=0.):
  for (a,b),clearance in EDGES.items():
   if CELLS[a]==cell and clearance>=threshold:
    c=self.cost_model.movement(POINTS[a],POINTS[b])
    yield CELLS[b],(clearance,c.time_s,c.energy_wh,c.oxygen_l)

@pytest.mark.parametrize('mode',['FAST','SAFE'])
@pytest.mark.parametrize('cap',[1.36,100.])
def test_original_graph_search_matches_exhaustive_oracle(mode,cap,record_property):
 _,p,r=scene();r=replace(r,start=POINTS['S'],goal=POINTS['G'],return_to=POINTS['S'],mode=mode,budget=replace(r.budget,energy_wh=cap+1.))
 geometry=AdmittedGraph(p);work=_Work(SearchLimits())
 found=_search(geometry,r,CELLS['S'],CELLS['G'],CELLS['S'],0.,work,stationary_costs=(0.,0.,0.))
 assert found is not None
 if mode=='SAFE':
  while True:
   trial=_search(geometry,r,CELLS['S'],CELLS['G'],CELLS['S'],math.nextafter(found.labels[found.terminal].clearance,math.inf),work,stationary_costs=(0.,0.,0.))
   if trial is None:break
   found=trial
 ref=choose(runs(),CostEstimate(r.budget.time_s,r.budget.energy_wh,r.budget.oxygen_l),CostEstimate(r.reserve_time_s,1.,1.),safe=mode=='SAFE')
 final=found.labels[found.terminal]
 assert final.energy==pytest.approx(ref.cost.energy_wh)
 assert final.time==pytest.approx(ref.cost.time_s)
 if cap==1.36:assert ref.outbound==('S','D','G')
 record_property('graph_oracle',json.dumps({'cap_wh':cap,'mode':mode,'selected':ref.outbound,'actual_wh':final.energy,'references':[{'out':t.outbound,'energy_wh':t.cost.energy_wh} for t in runs()]}))
