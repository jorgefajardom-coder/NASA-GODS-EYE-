"""Exercise MOCK mission callbacks without launching a DDS graph."""
from types import MethodType, SimpleNamespace as NS
from unittest.mock import Mock

import pytest

pytest.importorskip('rclpy', reason='Requires ROS 2 Jazzy messages')
from mge_interfaces.msg import MissionState, RouteDecision
from mge_sim.mock_mission import MAX_RETRIES, MockMission
from tests.unit.test_recovery import state


def harness():
    clock = NS(nanoseconds=12_000_000_000, to_msg=lambda: NS(sec=12, nanosec=0))
    m = NS(run_id='recovery', require_stop_ack=True, stop_ack_timeout_s=5.,
           state=MissionState.STATE_READY, reason='', map_version=2,
           goal=NS(primary_agent_id='human_1'), agents={},
           route=NS(route_id='old-route'), pending='old-request', dispatched=object(),
           retry_timer=Mock(), stop_barrier=None, stop_deadline=None,
           attempt=0, limit_retries=0, request_plan=Mock(), emit=Mock(),
           publish_path=Mock(), get_clock=lambda: NS(now=lambda: clock),
           get_logger=lambda: NS(info=Mock()))
    def set_state(new, cause='', reason=''):
        m.state, m.reason = new, reason
    m.set_state = set_state
    for name in ('invalidate_planning', 'plan_after_stop', 'on_agent', 'on_meta',
                 'on_plan_done', 'check_stop_timeout'):
        setattr(m, name, MethodType(getattr(MockMission, name), m))
    return m, clock


def agent(**changes):
    s = state(**changes)
    s.run_id, s.agent_id = 'recovery', 'human_1'
    return s


def test_map_change_discards_old_answer_and_waits_for_fresh_stop():
    m, _ = harness()
    timer = m.retry_timer
    m.on_meta(NS(run_id=m.run_id, map_version=3))
    timer.cancel.assert_called_once()
    assert m.pending is None and not m.route.route_id
    assert m.state == MissionState.STATE_REPLAN
    m.request_plan.assert_not_called()
    m.on_plan_done(NS(result=lambda: NS(decision=NS(request_id='old-request'))))
    for a in (agent(sec=11), agent(mode='MOVING'), agent(velocity=.5)):
        m.on_agent(a)
    wrong = agent(sec=13)
    wrong.run_id = 'other-run'
    m.on_agent(wrong)
    m.request_plan.assert_not_called()
    m.on_agent(agent(sec=13))
    m.request_plan.assert_called_once()
    assert m.stop_barrier is None


def test_missing_stop_feedback_blocks_with_explicit_timeout():
    m, clock = harness()
    m.on_meta(NS(run_id=m.run_id, map_version=3))
    clock.nanoseconds = 18_000_000_000
    m.check_stop_timeout()
    assert (m.state, m.reason) == (MissionState.STATE_BLOCKED, 'STOP_ACK_TIMEOUT')
    m.on_agent(agent(sec=19))
    m.request_plan.assert_not_called()


def test_second_map_invalidates_the_first_stop_acknowledgement():
    m, clock = harness()
    m.on_meta(NS(run_id=m.run_id, map_version=3))
    clock.nanoseconds = 14_000_000_000
    clock.to_msg = lambda: NS(sec=14, nanosec=0)
    m.on_meta(NS(run_id=m.run_id, map_version=4))
    m.on_agent(agent(sec=13))
    m.request_plan.assert_not_called()
    m.on_agent(agent(sec=14))
    m.request_plan.assert_called_once()


def candidate():
    m, _ = harness()
    m.route = RouteDecision()
    m.goal = NS(primary_agent_id='human_1', time_budget_s=100., energy_budget_wh=20.,
                oxygen_budget_l=10., reserve_time_s=1., reserve_wh=2., reserve_oxygen_l=1.)
    m.goal_resources = (100., 20., 10.)
    a = agent()
    a.agent_kind = 'HUMAN'
    a.time_remaining_s, a.energy_remaining_wh, a.oxygen_remaining_l = m.goal_resources
    m.agents[a.agent_id] = a
    m.dispatched = NS(start=NS(x=1., y=2., z=3.))
    d = NS(request_id='old-request', run_id=m.run_id, agent_id=a.agent_id,
           route_id='new-route', map_version_used=2, status='FEASIBLE', reason_code='', detail='',
           travel_time_s=1., energy_est_wh=5., oxygen_est_l=1.,
           outbound_path=[NS(x=1., y=2., z=3.)])
    return m, a, d


def test_exhausted_retries_never_authorize_a_feasible_route_on_an_old_map():
    m, _, d = candidate()
    m.attempt = MAX_RETRIES
    d.map_version_used = 1
    m.on_plan_done(NS(result=lambda: NS(decision=d)))
    assert m.reason == 'STALE_MAP' and not m.route.route_id
    m.publish_path.assert_not_called()


def test_resource_update_during_search_cannot_spend_the_reserve():
    m, a, d = candidate()
    a.energy_remaining_wh = 5.  # The candidate needs 5 Wh plus the unchanged 2 Wh reserve.
    m.on_plan_done(NS(result=lambda: NS(decision=d)))
    assert m.reason == 'INSUFFICIENT_BUDGET' and not m.route.route_id
    m.publish_path.assert_not_called()


@pytest.mark.parametrize('change,reason', [
    ('pose', 'POSE_CHANGED_DURING_SEARCH'), ('moving', 'POSE_CHANGED_DURING_SEARCH'),
    ('candidate_start', 'CANDIDATE_START_MISMATCH'), ('agent', 'PLAN_CONTEXT_MISMATCH')])
def test_candidate_cannot_bypass_pose_stop_or_identity(change, reason):
    m, a, d = candidate()
    if change == 'pose':
        a.pose.position.x += .1
    elif change == 'moving':
        a.velocity.linear.x = .1
    elif change == 'candidate_start':
        d.outbound_path[0].z += .1
    else:
        d.agent_id = 'another-agent'
    m.on_plan_done(NS(result=lambda: NS(decision=d)))
    assert m.reason == reason and not m.route.route_id
    m.publish_path.assert_not_called()


def test_current_stopped_pose_and_resources_allow_a_matching_candidate():
    m, _, d = candidate()
    m.on_plan_done(NS(result=lambda: NS(decision=d)))
    assert m.state == MissionState.STATE_READY and m.route.route_id == 'new-route'
    m.publish_path.assert_called_once()
