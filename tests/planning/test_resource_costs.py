"""Compare to published David vectors, not regenerated expected formulas."""
import json
import math
from pathlib import Path

import pytest
from mge_mission.models import CostEstimate, load_profiles
from mge_planning.resource_costs import Activity, ScientificCosts, Segment

ROOT = Path(__file__).resolve().parents[2]
REPORT = json.loads((ROOT / 'evidence/mission-cost-closure-20261114/vectors-final/cost_vectors.json').read_text())
PROFILES = load_profiles(ROOT / 'config/science_profiles.proposed.json')
ROWS = REPORT['vectors']


def schedule(rows):
    return [Segment(x['start_enu_m'], x['end_enu_m']) if x['kind'] == 'segment'
            else Activity(str(i), x['activity'], x['duration_s']) for i, x in enumerate(rows)]


def equal(actual, expected):
    for key, value in expected.items():
        if value is None:
            assert getattr(actual, key) is None
        else:
            assert getattr(actual, key) == pytest.approx(value, rel=REPORT['tolerances']['relative'],
                                                       abs=REPORT['tolerances']['absolute'])


def budget(x):
    return (CostEstimate(x['time_s'], x['energy_wh'], x.get('oxygen_l')),
            CostEstimate(x['reserve_time_s'], x['reserve_wh'], x.get('reserve_oxygen_l')))


@pytest.mark.parametrize('row', ROWS, ids=lambda x: x['vector_id'])
def test_published_vectors(row):
    backend = ScientificCosts(PROFILES[row['agent_id']])
    if row['expected']['status'] == 'MODEL_INPUT_REJECTED':
        with pytest.raises(ValueError):
            backend.total(schedule(row['schedule']))
        return
    cost = backend.total(schedule(row['schedule']))
    equal(cost, row['expected']['cost'])
    for case in row['expected'].get('budget_cases', []):
        assert backend.check_budget(cost, *budget(case['budget'])).feasible == case['resource_feasible']
    if 'already_completed_schedule' in row:
        completed = backend.total(schedule(row['already_completed_schedule']))
        equal(completed, row['already_consumed_cost'])
        assert backend.check_budget(cost, *budget(row['current_remaining_budget'])).feasible
        equal(CostEstimate(completed.time_s+cost.time_s, completed.energy_wh+cost.energy_wh,
                           completed.oxygen_l+cost.oxygen_l if completed.oxygen_l is not None else None),
              row['expected']['original_complete_cost'])


@pytest.mark.parametrize('agent', PROFILES)
def test_strict_sub_tolerance_shortages_and_no_inferred_work(agent):
    b = ScientificCosts(PROFILES[agent]); human = b.profile.kind == 'human'
    c = CostEstimate(1., 1., 1. if human else None)
    reserves = CostEstimate(1., 1., 1. if human else None)
    assert b.check_budget(c, CostEstimate(2., 2., 2. if human else None), reserves).feasible
    for field in ('time_s', 'energy_wh', 'oxygen_l') if human else ('time_s', 'energy_wh'):
        values = dict(time_s=2., energy_wh=2., oxygen_l=2. if human else None)
        values[field] = math.nextafter(2., 0.)
        assert not b.check_budget(c, CostEstimate(**values), reserves).feasible
    equal(b.total([]), dict(time_s=0., energy_wh=0., oxygen_l=0. if human else None))
    with pytest.raises(ValueError):
        b.total([Activity('same', 'idle', 1.), Activity('same', 'idle', 1.)])
    with pytest.raises(ValueError):
        b.activity(Activity('a', 'missing', 1.))
    with pytest.raises(ValueError):
        b.activity(Activity('a', '', 1.))
    with pytest.raises(ValueError):
        b.check_budget(c, CostEstimate(2., 2., None if human else 2.), reserves)
