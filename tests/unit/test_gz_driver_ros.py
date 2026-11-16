"""Adapter regressions using generated ROS messages; no DDS/Gazebo processes."""
from types import SimpleNamespace as NS
from unittest.mock import Mock

import pytest

pytest.importorskip('rclpy', reason='Requires ROS 2 Jazzy generated messages')
from mge_sim.gz_control import OdomSample
from mge_sim.gz_rover_driver import GzRoverDriver
from rclpy.node import Node


def test_publication_keeps_acquisition_stamp_and_measured_six_dof_values():
    sample = OdomSample(12_000_000_345, 20., (1., 2., -2567.), (.5, .5, .5, .5),
                        (1e-10, 0., -1e-10), (0., 1e-10, 0.))
    h = NS(run_id='run', agent_id='rover_1', kind='ROVER', pub=Mock(),
           control=NS(mode='HALTED', time_s=90., energy_wh=80.))
    GzRoverDriver.publish(h, sample)
    msg = h.pub.publish.call_args.args[0]
    assert (msg.header.stamp.sec, msg.header.stamp.nanosec) == (12, 345)
    assert (msg.pose.position.x, msg.pose.position.y, msg.pose.position.z) == sample.position
    q = msg.pose.orientation
    assert (q.x, q.y, q.z, q.w) == sample.orientation
    v, w = msg.velocity.linear, msg.velocity.angular
    assert (v.x, v.y, v.z, w.x, w.y, w.z) == (*sample.linear, *sample.angular)
    assert msg.mode == 'HALTED'


def test_shutdown_sends_brake_without_waiting_for_simulation_clock(monkeypatch):
    d = GzRoverDriver.__new__(GzRoverDriver)
    d.Twist = lambda: NS(linear=NS(x=99.), angular=NS(z=99.))
    d.cmd = Mock()
    destroy = Mock(return_value=True)
    monkeypatch.setattr(Node, 'destroy_node', destroy)
    assert d.destroy_node()
    command = d.cmd.publish.call_args.args[0]
    assert command.linear.x == 0. and command.angular.z == 0.
    destroy.assert_called_once_with()
