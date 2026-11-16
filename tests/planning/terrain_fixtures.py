"""Historical synthetic geometry fixture; published profiles, no approval."""
from dataclasses import replace
from pathlib import Path
import numpy as np
from mge_mission.models import load_profiles,export_planner_profiles
from mge_planning.core import TerrainGrid,MotionProfile,PlanRequest,ResourceBudget
PROFILES=load_profiles(Path(__file__).resolve().parents[2]/'config/science_profiles.proposed.json')
def scene(kind='human'):
 agent=kind+'_1';p=MotionProfile(**export_planner_profiles({agent:PROFILES[agent]})['profiles'][agent])
 g=TerrainGrid('science',1,np.array([[0.,.1,0.],[0.,.1,0.]]),np.zeros((2,3)),4. if kind=='rover' else 2.,sigma_m=np.zeros((2,3)))
 b=ResourceBudget(kind,1000.,100.,1.,100. if kind=='human' else None,1. if kind=='human' else None)
 r=PlanRequest(g.run_id,'request',agent,kind,1,g.point((0,0)),g.point((0,2)),b,return_to=g.point((0,0)),reserve_time_s=1.)
 return g,p,r
