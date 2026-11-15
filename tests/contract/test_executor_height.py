"""Actual executor callbacks: reject height substitution without a DDS graph."""
from copy import deepcopy
from types import MethodType, SimpleNamespace as NS
from unittest.mock import Mock

import pytest

pytest.importorskip('rclpy', reason='Requires ROS 2 Jazzy messages')
from rclpy.time import Time
from mge_sim.executor import KinematicExecutor
from mge_sim.kinematics import HALTED, IDLE, MOVING


def harness(position, points, initial_mode=HALTED):
    agent = dict(position=position, mode=initial_mode, time_s=100., energy_wh=20., oxygen_l=10.)
    route = NS(outbound_path=[NS(x=x, y=y, z=z) for x, y, z in points], return_path=[],
               travel_time_s=10., energy_est_wh=2., oxygen_est_l=1.)
    m = NS(follow=None, agents={'human_1': agent}, finished=set(),
           authorized=lambda: ('human_1', 'new-route', points, route),
           get_logger=lambda: NS(error=Mock(), info=Mock()),
           last=Time(nanoseconds=1_000_000_000), publish=Mock(),
           get_clock=lambda: NS(now=lambda: Time(nanoseconds=2_000_000_000)))
    m.reconcile = MethodType(KinematicExecutor.reconcile, m)
    return m, agent


@pytest.mark.parametrize('initial_mode', [IDLE, HALTED])
def test_refused_surface_start_preserves_pose_resources_and_halted_mode(initial_mode):
    position = (1., 2., -2490.)
    m, agent = harness(position, [(1., 2., -2500.), (2., 2., -2500.)], initial_mode)
    before = deepcopy(agent)
    m.reconcile()
    assert m.follow is None and agent['mode'] == HALTED
    assert {k: v for k, v in agent.items() if k != 'mode'} == {k: v for k, v in before.items() if k != 'mode'}
    assert m.finished == {'new-route'}
    m.reconcile()  # The same rejected authorization cannot revive execution.
    assert m.follow is None and agent['position'] == position and agent['mode'] == HALTED
    KinematicExecutor.tick(m)
    m.publish.assert_called_once()
    assert m.publish.call_args.args[1] == (0., 0., 0.)
    assert {k: v for k, v in agent.items() if k != 'mode'} == {k: v for k, v in before.items() if k != 'mode'}


def test_matching_halted_xyz_can_resume_without_initial_position_or_budget_change():
    position = (1., 2., -2500.)
    m, agent = harness(position, [position, (2., 2., -2499.9)])
    before = deepcopy(agent)
    m.reconcile()
    assert m.follow[2].position == position and agent['position'] == position
    assert agent['mode'] == MOVING
    for field in ('time_s', 'energy_wh', 'oxygen_l'):
        assert agent[field] == before[field]
