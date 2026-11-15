"""Python context admission; published proposed profiles remain unapproved."""
from dataclasses import FrozenInstanceError, replace
from pathlib import Path

import numpy as np
import pytest

from mge_mission.models import export_planner_profiles, load_profiles
from mge_planning.core import MotionProfile, PlanRequest, ResourceBudget, TerrainGrid
from mge_planning.resource_costs import Activity, ScientificContext

ROOT = Path(__file__).resolve().parents[2]
REGISTRY = ROOT/'config/science_profiles.proposed.json'
SCENARIO = ROOT/'config/mission_jezero.experimental.yaml'
PROFILES = load_profiles(REGISTRY)


def scene(kind='human', service=()):
    agent = kind+'_1'
    p = MotionProfile(**export_planner_profiles({agent: PROFILES[agent]})['profiles'][agent])
    g = TerrainGrid('science', 1, np.array([[0., .1, 0.], [0., .1, 0.]]),
                    np.zeros((2,3)), 4. if kind=='rover' else 2., sigma_m=np.zeros((2,3)))
    budget = ResourceBudget(kind, 1000., 100., 1., 100. if kind=='human' else None,
                            1. if kind=='human' else None)
    r = PlanRequest(g.run_id,'request',agent,kind,1,g.point((0,0)),g.point((0,2)),
                    budget,return_to=g.point((0,0)),reserve_time_s=1.,
                    service_time_s=sum(a.remaining_s for a in service))
    return g,p,r


def context(request, service=(), waiting=(), phase='OUTBOUND'):
    return ScientificContext.from_files(request=request, registry_path=REGISTRY,
                                       scenario_path=SCENARIO, phase=phase,
                                       service=service, waiting=waiting)


@pytest.mark.parametrize('kind', ['human','rover'])
def test_context_defensively_freezes_schedule_and_preserves_proposed_profile(kind):
    service=[Activity('a','inspect',10.)];g,p,r=scene(kind,service)
    c=context(r,service);service.clear()
    assert c.service==(Activity('a','inspect',10.),)
    assert c.profile.approval_status=='proposed'
    assert len(c.fingerprint)==64 and c.model_id=='mge-science-1.0.0'
    c.validate(r,p)
    with pytest.raises(FrozenInstanceError):c.phase='RETURN'
    with pytest.raises(TypeError):c.profile.parameters['speed_m_s']=99.
    assert replace(c,request=replace(r,request_id='new')).fingerprint!=c.fingerprint


@pytest.mark.parametrize('change', [
    {'model_id':'unpublished'}, {'phase':'UNKNOWN'}, {'profile_registry_sha256':''},
    {'scenario_sha256':'xyz'}, {'waiting':(Activity('missing','unknown',1.),)},
    {'service':(Activity('a','inspect',1.),)},
    {'waiting':(Activity('a','wait',1.),Activity('a','wait',2.))},
    {'waiting':(Activity('a','wait',float('nan')),)},
    {'waiting':(Activity('a','wait',True),)},
    {'phase':'RETURN'}, {'phase':'SERVICE'},
])
def test_incomplete_or_inconsistent_context_rejected(change):
    g,p,r=scene();c=context(r)
    with pytest.raises((ValueError,TypeError)):replace(c,**change)


@pytest.mark.parametrize('change', [
    {'radius_m':0.}, {'localization_error_m':0.}, {'max_step_m':1.},
    {'max_slope_deg':90.}, {'max_downhill_slope_deg':90.},
    {'max_sigma_m':None}, {'max_sigma_m':10.},
])
def test_science_cannot_weaken_geometric_limits(change):
    g,p,r=scene();c=context(r)
    with pytest.raises(ValueError):c.validate(r,replace(p,**change))


def test_request_scope_and_service_have_no_implicit_activity():
    g,p,r=scene();c=context(r)
    for bad in [replace(r,map_version=2),replace(r,request_id='other'),replace(r,start=g.point((1,0)))]:
        with pytest.raises(ValueError):c.validate(bad,p)
    with pytest.raises(ValueError):context(replace(r,service_time_s=10.))
    s=replace(r,start=r.goal,service_time_s=5.)
    assert context(s,(Activity('s','sample',5.),),phase='SERVICE').goal_costs[0]==5.
    back=replace(r,goal=r.return_to,require_return=False)
    assert context(back,phase='RETURN').goal_costs==(0.,0.,0.)


def test_no_duplicate_between_service_and_waiting():
    g,p,r=scene(service=(Activity('same','inspect',1.),))
    with pytest.raises(ValueError):context(r,(Activity('same','inspect',1.),),(Activity('same','wait',1.),))
