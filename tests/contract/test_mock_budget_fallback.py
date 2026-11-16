"""Opt-in MOCK budget fallback: nearer targets, then the base, on a resource rejection."""
from types import MethodType, SimpleNamespace as NS
from unittest.mock import Mock

import pytest

pytest.importorskip('rclpy', reason='Requires ROS 2 Jazzy messages')
from builtin_interfaces.msg import Time  # noqa: E402
from geometry_msgs.msg import Point  # noqa: E402
from mge_interfaces.msg import MissionEvent, MissionState, RouteDecision  # noqa: E402
from mge_interfaces.srv import SetMissionGoal  # noqa: E402
from mge_sim.mock_mission import MockMission, budget_blocked, fallback_targets  # noqa: E402

GRID = (-64.0, -64.0, 4.0, 32, 32)


def point(x, y):
    return Point(x=float(x), y=float(y), z=0.0)


def harness(enabled=True):
    goal = SetMissionGoal.Request()
    goal.request_id, goal.primary_agent_id = 'far', 'human_1'
    goal.base, goal.goal = point(-14, -14), point(22, 22)
    m = NS(run_id='budget', budget_fallback=enabled, fallback_fractions=[0.75, 0.5, 0.25],
           grid=GRID, fallback=None, goal=goal, state=MissionState.STATE_REPLAN, reason='',
           map_version=4, pending='far#v4.1', attempt=1, limit_retries=0,
           route=RouteDecision(), request_plan=Mock(), seq=0, pub_event=Mock(),
           get_clock=lambda: NS(now=lambda: NS(to_msg=Time)),
           get_logger=lambda: NS(info=Mock()))
    # The real emit builds every MissionEvent, so a wrong field fails here, not on the robot.
    m.emit = Mock(side_effect=MethodType(MockMission.emit, m))

    def set_state(new, cause='', reason=''):
        m.state, m.reason = new, reason
    m.set_state = set_state
    for name in ('on_plan_done', 'try_budget_fallback'):
        setattr(m, name, MethodType(getattr(MockMission, name), m))
    return m


def answer(m, status, reason):
    d = RouteDecision()
    d.request_id, d.run_id, d.agent_id = m.pending, m.run_id, 'human_1'
    d.map_version_used, d.status, d.reason_code = m.map_version, status, reason
    m.on_plan_done(NS(result=lambda: NS(decision=d)))


def reasons(m):
    return [c.kwargs.get('reason') for c in m.emit.call_args_list]


def test_targets_are_cell_centres_on_the_segment_then_the_base():
    targets = fallback_targets(point(-14, -14), point(22, 22), [0.25, 0.75, 0.5, 1.0, 0.0], GRID)
    assert targets == [(14.0, 14.0), (6.0, 6.0), (-6.0, -6.0), (-14.0, -14.0)]
    for x, y in targets:
        assert (x + 62) % 4 == 0 and (y + 62) % 4 == 0


def test_budget_reasons_are_recognised_but_geometry_is_not():
    assert budget_blocked(NS(status='UNKNOWN', reason_code='UNVERIFIED_BUDGET_CORRIDOR'))
    assert budget_blocked(NS(status='INSUFFICIENT_BUDGET', reason_code='BUDGET_EXCEEDED'))
    assert not budget_blocked(NS(status='UNKNOWN', reason_code='UNVERIFIED_TERRAIN'))
    assert not budget_blocked(NS(status='NO_PATH', reason_code='NO_PATH'))


def test_resource_rejection_switches_to_a_nearer_target_with_the_same_allocation():
    m = harness()
    budgets = (m.goal.time_budget_s, m.goal.energy_budget_wh, m.goal.oxygen_budget_l)
    answer(m, 'UNKNOWN', 'UNVERIFIED_BUDGET_CORRIDOR')
    assert (m.state, m.reason) == (MissionState.STATE_REPLAN, 'BUDGET_FALLBACK')
    assert (m.goal.goal.x, m.goal.goal.y) == (14.0, 14.0)
    assert (m.goal.base.x, m.goal.base.y) == (-14.0, -14.0)
    assert (m.goal.time_budget_s, m.goal.energy_budget_wh, m.goal.oxygen_budget_l) == budgets
    m.request_plan.assert_called_once()
    event = next(c.kwargs for c in m.emit.call_args_list if c.kwargs.get('reason') == 'BUDGET_FALLBACK')
    assert event['task_id'] == 'primary' and 'nearer target (14, 14)' in event['detail']
    assert 'does not fit the remaining allocation' in event['detail']
    assert m.emit.call_args_list[-1].args[0] == MissionEvent.TYPE_TASK_STATE_CHANGED
    published = [c.args[0] for c in m.pub_event.publish.call_args_list]
    fallback = next(e for e in published if e.reason_code == 'BUDGET_FALLBACK')
    assert (fallback.task_id, fallback.event_type) == ('primary', MissionEvent.TYPE_TASK_STATE_CHANGED)
    assert [e.seq for e in published] == list(range(1, len(published) + 1))


def test_once_started_every_unauthorized_target_moves_on_until_the_base_then_blocks():
    m = harness()
    answer(m, 'INSUFFICIENT_BUDGET', 'BUDGET_EXCEEDED')
    for expected in ((6.0, 6.0), (-6.0, -6.0), (-14.0, -14.0)):
        answer(m, 'NO_PATH', 'NO_PATH')
        assert (m.goal.goal.x, m.goal.goal.y) == expected
    assert 'returning to base' in m.emit.call_args_list[-1].kwargs['detail']
    assert 'has no authorized route (NO_PATH)' in m.emit.call_args_list[-1].kwargs['detail']
    answer(m, 'NO_PATH', 'NO_PATH')
    assert (m.state, m.reason) == (MissionState.STATE_BLOCKED, 'NO_PATH')
    assert 'BUDGET_FALLBACK_EXHAUSTED' in reasons(m)


def test_disabled_or_non_budget_rejections_keep_the_original_block():
    for enabled, status, reason in ((False, 'UNKNOWN', 'UNVERIFIED_BUDGET_CORRIDOR'),
                                    (True, 'UNKNOWN', 'UNVERIFIED_TERRAIN')):
        m = harness(enabled)
        answer(m, status, reason)
        assert (m.state, m.reason) == (MissionState.STATE_BLOCKED, status)
        assert (m.goal.goal.x, m.goal.goal.y) == (22.0, 22.0)
        m.request_plan.assert_not_called()
        assert 'BUDGET_FALLBACK' not in reasons(m)


def test_goals_off_the_terrain_grid_are_detected():
    from mge_sim.mock_mission import on_grid
    assert on_grid(point(-62, -62), GRID) and on_grid(point(63.9, 63.9), GRID)
    for x, y in ((-64.1, 0), (0, 64.0), (float('nan'), 0), (200, 200)):
        assert not on_grid(point(x, y), GRID)


def completion_harness():
    from mge_interfaces.msg import AgentState
    m = harness()
    m.complete_on_return, m.departed, m.state = True, False, MissionState.STATE_READY
    m.route = RouteDecision()
    m.route.route_id = 'route-1'
    m.route.outbound_path = [point(-14, -14), point(22, 22)]
    m.route.return_path = [point(22, 22), point(-14, -14)]
    m.check_completion = MethodType(MockMission.check_completion, m)
    m.publish_path = Mock()

    def state(mode, x, y):
        s = AgentState()
        s.agent_id, s.mode = 'human_1', mode
        s.pose.position.x, s.pose.position.y = float(x), float(y)
        return s
    return m, state


def test_a_goal_completes_when_its_agent_rests_at_the_end_of_the_route():
    m, state = completion_harness()
    m.check_completion(state('IDLE', -14, -14))            # has not left yet: still in force
    assert m.goal is not None and m.state == MissionState.STATE_READY
    m.check_completion(state('MOVING', 0, 0))
    m.check_completion(state('IDLE', 5, 5))                # stopped away from the end
    assert m.goal is not None
    m.check_completion(state('IDLE', -14, -14))
    assert m.goal is None
    assert (m.state, m.reason) == (MissionState.STATE_IDLE, 'GOAL_COMPLETED')
    assert not m.route.route_id                             # finished route withdrawn
    m.publish_path.assert_called()
    published = [c.args[0] for c in m.pub_event.publish.call_args_list]
    assert any(e.reason_code == 'GOAL_COMPLETED' and e.route_id == 'route-1' for e in published)


def test_other_agents_and_unpublished_routes_never_complete_a_goal():
    m, state = completion_harness()
    other = state('MOVING', 0, 0)
    other.agent_id = 'drone_1'
    m.check_completion(other)
    m.check_completion(state('IDLE', -14, -14))
    assert m.goal is not None                               # the primary never departed
    m.route.route_id = ''
    m.check_completion(state('MOVING', 0, 0))
    m.check_completion(state('IDLE', -14, -14))
    assert m.goal is not None


def test_a_physical_agent_completes_within_the_tolerance_in_xy():
    m, state = completion_harness()
    m.completion_tolerance_m = 1.0
    m.check_completion(state('MOVING', 0, 0))
    m.check_completion(state('IDLE', -13.4, -14.5))                     # 0.78 m from the end
    assert m.goal is None and m.reason == 'GOAL_COMPLETED'
