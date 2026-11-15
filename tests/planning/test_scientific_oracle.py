"""Synthetic graph regressions; no claim of production backend integration."""
from dataclasses import replace
from pathlib import Path
import math
import pytest
from mge_mission.models import CostEstimate, load_profiles, estimate_segment
from mge_planning.resource_costs import ScientificCosts, Segment, Activity
from tests.planning.scientific_oracle import enumerate_itineraries, choose, feasible

ROOT = Path(__file__).resolve().parents[2]
PROFILES = load_profiles(ROOT/'config/science_profiles.proposed.json')
POINTS = {'S': (0.,0.,0.), 'H': (2.,0.,.2), 'D': (2.,1.5,0.), 'G': (4.,0.,0.), 'P': (-.37,0.,0.)}
EDGES = {('S','H'):2., ('H','G'):2., ('S','D'):4., ('D','G'):4., ('G','S'):5.}


def runs(agent='human_1', activities=(), start='S', edges=None):
    return list(enumerate_itineraries(PROFILES[agent], POINTS, EDGES if edges is None else edges,
                                     start, 'G', 'S', activities))


def capacity(agent, value):
    return CostEstimate(value, value, value if agent == 'human_1' else None)


@pytest.mark.parametrize('agent', ['human_1','rover_1'])
def test_directed_complete_cost_matches_adapter_not_production_search(agent):
    p = PROFILES[agent]; work = [('inspect-1','inspect',10.), ('wait-1','wait',5.)]
    for r in runs(agent, work):
        items = [Segment(POINTS[a],POINTS[b]) for path in (r.outbound,r.returning) for a,b in zip(path,path[1:])]
        items += [Activity(*a) for a in work]
        expected = ScientificCosts(p).total(items)
        assert r.cost.time_s == pytest.approx(expected.time_s)
        assert r.cost.energy_wh == pytest.approx(expected.energy_wh)
        assert r.cost.oxygen_l == expected.oxygen_l
    up = estimate_segment(p, POINTS['S'],POINTS['H'])
    down = estimate_segment(p, POINTS['H'],POINTS['S'])
    assert up.energy_wh > down.energy_wh


def test_slower_label_is_needed_for_energy_feasibility_and_safe():
    fast, slow = sorted(runs(),key=lambda r:r.cost.time_s)
    assert fast.outbound == ('S','H','G') and slow.outbound == ('S','D','G')
    assert fast.cost.energy_wh > slow.cost.energy_wh
    available = CostEstimate(100., (fast.cost.energy_wh+slow.cost.energy_wh)/2+1.,100.)
    reserve = CostEstimate(1.,1.,1.)
    assert choose(runs(),available,reserve) == slow
    assert choose(runs(),capacity('human_1',100.),reserve) == fast
    assert choose(runs(),capacity('human_1',100.),reserve,safe=True) == slow
    # Wide corridor still must satisfy every resource constraint.
    tight_time = replace(available,time_s=fast.cost.time_s+1.)
    assert choose(runs(),tight_time,reserve,safe=True) is None


@pytest.mark.parametrize('agent', ['human_1','rover_1'])
def test_partial_service_and_wait_are_separate_without_prefix_debit(agent):
    complete = runs(agent,[('inspect','inspect',120.),('hold','wait',30.)])[0]
    partial = runs(agent,[('inspect','inspect',75.),('hold','wait',30.)])[0]
    from mge_mission.models import estimate_activity
    spent = estimate_activity(PROFILES[agent],'inspect',45.)
    assert partial.cost.time_s+spent.time_s == pytest.approx(complete.cost.time_s)
    assert partial.cost.energy_wh+spent.energy_wh == pytest.approx(complete.cost.energy_wh)
    remaining = CostEstimate(10000.-spent.time_s,10000.-spent.energy_wh,
                            10000.-spent.oxygen_l if agent=='human_1' else None)
    assert feasible(partial,remaining,capacity(agent,1.))
    if agent=='rover_1':
        assert estimate_activity(PROFILES[agent],'inspect',30.).energy_wh != estimate_activity(PROFILES[agent],'wait',30.).energy_wh


@pytest.mark.parametrize('agent', ['human_1','rover_1'])
def test_exact_reserves_and_each_individual_shortage(agent):
    r = runs(agent)[0]
    # Zero is an exactly representable separate reserve boundary for all costs.
    reserve = capacity(agent,0.)
    assert feasible(r,r.cost,reserve)
    # Also check positive reserves, adjusted UP only for floating subtraction.
    reserve = capacity(agent,1.); values={}
    for k in ('time_s','energy_wh','oxygen_l'):
        cost=getattr(r.cost,k)
        if cost is None:values[k]=None;continue
        value=cost+1.
        while value-1.<cost:value=math.nextafter(value,math.inf)
        values[k]=value
    assert feasible(r,CostEstimate(**values),reserve)
    for k in ('time_s','energy_wh','oxygen_l') if agent=='human_1' else ('time_s','energy_wh'):
        bad=replace(r.cost,**{k:math.nextafter(getattr(r.cost,k),0.)})
        assert not feasible(r,bad,capacity(agent,0.))


@pytest.mark.parametrize('agent', ['human_1','rover_1'])
def test_real_pose_connector_is_included_once(agent):
    edges={**EDGES,('P','S'):3.}
    connected=runs(agent,start='P',edges=edges)[0]; centered=runs(agent)[0]
    connector=estimate_segment(PROFILES[agent],POINTS['P'],POINTS['S'])
    assert connected.outbound[0]=='P'
    assert connected.cost.energy_wh==pytest.approx(centered.cost.energy_wh+connector.energy_wh)
    assert connected.cost.time_s==pytest.approx(centered.cost.time_s+connector.time_s)
    assert not feasible(connected,centered.cost,capacity(agent,0.))


def test_known_legacy_science_feasibility_counterexample():
    from mge_mission.models import export_planner_profiles
    from mge_planning.core import MotionProfile, _motion_costs
    p=PROFILES['human_1']; projected=MotionProfile(**export_planner_profiles({'human_1':p})['profiles']['human_1'])
    old=_motion_costs(projected,2.,-.1)[1]
    new=estimate_segment(p,(0.,0.,.1),(2.,0.,0.)).energy_wh
    cap=(old+new)/2
    assert old < cap < new  # Fixed published coefficients; decision differs.
    # This is an edge-budget counterexample, not an alleged complete route flip.


def test_disconnected_graph_and_duplicate_work():
    assert not runs(edges={('S','H'):2.})
    with pytest.raises(ValueError):runs(activities=[('x','inspect',1.),('x','wait',1.)])


def test_complete_route_selection_changes_with_published_costs():
    from mge_mission.models import export_planner_profiles
    from mge_planning.core import MotionProfile, _motion_costs
    p = PROFILES['human_1']
    old_profile = MotionProfile(**export_planner_profiles({'human_1':p})['profiles']['human_1'])
    science = runs()
    legacy = []
    for r in science:
        costs = [_motion_costs(old_profile, math.dist(POINTS[a][:2],POINTS[b][:2]),
                               POINTS[b][2]-POINTS[a][2])
                 for leg in (r.outbound,r.returning) for a,b in zip(leg,leg[1:])]
        legacy.append(replace(r,cost=CostEstimate(*(sum(c[i] for c in costs) for i in range(3)))))
    # Fixed synthetic capacity, not a changed model coefficient. Includes return.
    available = CostEstimate(100.,2.36,100.)
    reserve = CostEstimate(1.,1.,1.)
    assert choose(legacy,available,reserve).outbound == ('S','H','G')
    assert choose(science,available,reserve).outbound == ('S','D','G')
