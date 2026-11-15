"""Rejected scientific snapshots must not mutate admitted resource availability."""
from dataclasses import replace

import pytest

from mge_planning.core import RouteStatus
from mge_planning.replan import EventKind, ReplanAction, RemainingResources
from tests.planning.test_replan_policy import policy
from tests.planning.test_scientific_replan import scientific_case, pending, evaluate


@pytest.mark.parametrize('agent,field',[
    ('human','time_s'),('human','energy_wh'),('human','oxygen_l'),
    ('rover','time_s'),('rover','energy_wh')])
@pytest.mark.parametrize('bad_context',['mismatched_model','missing'])
def test_rejected_reduction_does_not_make_corrected_availability_a_replenishment(agent,field,bad_context):
    g,p,s=scientific_case(agent);pol=policy();legitimate=pending(g,s)
    assert evaluate(pol,g,p,s,legitimate).action==ReplanAction.KEEP
    reduced=replace(s,remaining=replace(s.remaining,**{field:getattr(s.remaining,field)-1.}))
    invalid=pending(g,reduced)
    invalid=replace(invalid,scenario_sha256='f'*64) if bad_context=='mismatched_model' else None
    rejected=evaluate(pol,g,p,reduced,invalid,event_id='invalid',now=1.)
    assert rejected.reason_code=='INVALID_SCIENTIFIC_CONTEXT' and rejected.invalidate_active
    assert rejected.request is rejected.candidate is None
    corrected=evaluate(pol,g,p,s,legitimate,event_id='corrected',now=2.)
    assert corrected.reason_code=='AWAITING_ROUTE_AUTHORIZATION'
    assert corrected.action==ReplanAction.STOP_REQUIRED and corrected.invalidate_active
    # Correction alone grants no movement; a valid task can produce a candidate,
    # and only a separately authorized adoption can recover the latch.
    proposed=evaluate(pol,g,p,s,legitimate,EventKind.TASK,'propose',10.)
    assert proposed.candidate.status==RouteStatus.FEASIBLE and proposed.invalidate_active
    adopted=replace(s,active_route=proposed.candidate,active_request=proposed.request)
    assert evaluate(pol,g,p,adopted,pending(g,adopted),event_id='adopt',now=11.).action==ReplanAction.KEEP
    # An ACTUALLY admitted reduction must still make a later increase invalid.
    admitted=replace(adopted,remaining=reduced.remaining)
    result=evaluate(pol,g,p,admitted,pending(g,admitted),event_id='lower',now=12.)
    assert result.action==ReplanAction.KEEP
    increased=evaluate(pol,g,p,adopted,pending(g,adopted),event_id='inflated',now=13.)
    assert increased.reason_code.endswith('AVAILABILITY_INCREASE') and increased.invalidate_active


@pytest.mark.parametrize('agent',['human','rover'])
def test_invalid_depleted_scientific_snapshot_stops_without_admitting_its_value(agent):
    g,p,s=scientific_case(agent);pol=policy();c=pending(g,s)
    evaluate(pol,g,p,s,c)
    live=RemainingResources(**vars(s.remaining))
    depleted=replace(s,remaining=replace(live,time_s=0.))
    # No valid ScientificContext can bind an availability below required reserves.
    stopped=evaluate(pol,g,p,depleted,None,event_id='invalid-depleted',now=1.)
    assert stopped.action==ReplanAction.STOP_REQUIRED and stopped.reason_code=='TIME_RESERVE_DEPLETED'
    assert stopped.invalidate_active and stopped.request is None
    corrected=evaluate(pol,g,p,s,c,event_id='corrected',now=2.)
    assert corrected.reason_code=='AWAITING_ROUTE_AUTHORIZATION' and corrected.action==ReplanAction.STOP_REQUIRED


@pytest.mark.parametrize('agent',['human','rover'])
def test_valid_scientific_snapshot_at_reserve_keeps_its_lower_admitted_bound(agent):
    g,p,s=scientific_case(agent);pol=policy();evaluate(pol,g,p,s,pending(g,s))
    low=replace(s,remaining=replace(s.remaining,time_s=s.mission.reserve_time_s))
    stopped=evaluate(pol,g,p,low,pending(g,low),EventKind.RESOURCES,'at-reserve',1.)
    assert stopped.invalidate_active
    restored=evaluate(pol,g,p,s,pending(g,s),event_id='restore',now=2.)
    assert restored.reason_code=='TIME_AVAILABILITY_INCREASE' and restored.request is None
