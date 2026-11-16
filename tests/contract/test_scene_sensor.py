"""Real generated ROS messages through scene-sensor callbacks and mapping conversion.

These callback/consumer checks require Jazzy; they do not claim DDS or Gazebo acceptance.
"""
from types import MethodType, SimpleNamespace as NS
from unittest.mock import Mock

import numpy as np
import pytest

pytest.importorskip('rclpy', reason='Requires ROS 2 Jazzy messages')
from mge_interfaces.msg import AgentState, TerrainMeta  # noqa: E402
from nav_msgs.msg import OccupancyGrid  # noqa: E402
from sensor_msgs.msg import Image  # noqa: E402
from mge_mapping.core import BeliefMap, ObservationFusion  # noqa: E402
from mge_mapping.node import observation_from_message  # noqa: E402
from mge_sim.scene_sensor import SceneSensor  # noqa: E402
from mge_sim.scene_sensing import FeedbackBatches, FreshTelemetry, Scene, SensorLedger  # noqa: E402


def harness():
    h = NS(run_id='run', radii={'rover_1': 0.}, scene=Scene(4, 4, 0., 0., 4., (0.,) * 16, frozenset({9})),
           feedback=FeedbackBatches(16), telemetry=FreshTelemetry('run', ['rover_1'], 1.),
           ledger=SensorLedger(resend_s=1.), sigma_m=0.25, failed=False, map_version=0, count=0, session_id='test',
           pub=Mock(), now=10_000_000_000)
    h.expected_meta = dict(dataset_id='grid', rows=4, cols=4, origin_x_m=0., origin_y_m=0., resolution_m=4.,
                           crs='Mars test', origin_lat_deg=0., origin_lon_deg=0.,
                           vertical_datum='test', checksum_sha256='a' * 64)
    h.get_clock = lambda: NS(now=lambda: NS(nanoseconds=h.now))
    h.get_logger = lambda: NS(error=Mock(), info=Mock())
    for name in ('on_meta', 'on_layer', 'on_traversability', 'on_state', 'tick', 'report', 'fail', 'now_s'):
        setattr(h, name, MethodType(getattr(SceneSensor, name), h))
    return h


def stamp(header, sec):
    header.frame_id, header.stamp.sec = 'map', sec


def publish_batch(h, belief, sec, *, skip=()):
    meta = TerrainMeta()
    stamp(meta.header, sec)
    meta.run_id, meta.map_version = 'run', belief.map_version
    for key, value in h.expected_meta.items():
        setattr(meta, key, value)
    h.on_meta(meta)
    for name, values in (('belief', belief.belief), ('sigma', belief.sigma),
                         ('observed', belief.observed_mask.astype(np.uint8))):
        if name in skip:
            continue
        image = Image()
        stamp(image.header, sec)
        image.height = image.width = 4
        image.encoding, image.step = ('mono8', 4) if name == 'observed' else ('32FC1', 16)
        image.data = values.astype('u1' if name == 'observed' else '<f4').tobytes()
        h.on_layer(name, image)
    if 'traversability' not in skip:
        grid = OccupancyGrid()
        stamp(grid.header, sec)
        grid.info.height = grid.info.width = 4
        grid.info.resolution, grid.info.origin.orientation.w = 4., 1.
        grid.data = [int(v) for v in belief.traversability_grid(max_slope_deg=90).ravel()]
        h.on_traversability(grid)


def telemetry(sec, x=6., y=10.):
    state = AgentState()
    stamp(state.header, sec)
    state.run_id, state.agent_id, state.agent_kind, state.mode = 'run', 'rover_1', 'ROVER', 'IDLE'
    state.pose.position.x, state.pose.position.y = x, y  # cell 9 at (6, 10)
    return state


def test_callback_report_keeps_acquisition_stamp_and_waits_for_complete_applied_batch():
    h = harness()
    fusion = ObservationFusion(BeliefMap.from_arrays(np.zeros((4, 4)), run_id='run',
                                                    origin_x_m=0., origin_y_m=0.))
    publish_batch(h, fusion.belief_map, 9)
    h.on_state(telemetry(10))
    h.now = 10_500_000_000
    h.tick()
    obs = h.pub.publish.call_args.args[0]
    assert (obs.header.stamp.sec, obs.header.stamp.nanosec) == (10, 0)  # never publish-time 10.5
    assert list(obs.cell_indices) == [9] and list(obs.obstacle) == [100]
    belief, applied = fusion.apply(observation_from_message(obs))
    assert applied
    h.now = 11_000_000_000
    h.on_state(telemetry(11, x=10.))
    h.tick()
    assert h.pub.publish.call_count == 1  # B cannot be sent before A is evidenced
    publish_batch(h, belief, 11, skip=('traversability',))
    assert not h.ledger.reported and h.ledger.pending
    publish_batch(h, belief, 11)
    assert h.ledger.reported == {9} and not h.ledger.pending


def test_stale_state_and_clock_reset_never_create_current_observations():
    h = harness()
    belief = BeliefMap.from_arrays(np.zeros((4, 4)), run_id='run')
    publish_batch(h, belief, 9)
    h.on_state(telemetry(10))
    h.now = 12_000_000_000
    h.tick()
    h.pub.publish.assert_not_called()
    h.now = 1_000_000_000
    h.tick()
    assert h.failed
    h.now = 13_000_000_000
    h.on_state(telemetry(13))
    h.tick()
    h.pub.publish.assert_not_called()


def test_same_size_shifted_traversability_cannot_confirm_the_scene():
    h = harness()
    grid = OccupancyGrid()
    stamp(grid.header, 10)
    grid.info.height = grid.info.width = 4
    grid.info.resolution, grid.info.origin.orientation.w = 4., 1.
    grid.info.origin.position.x = 1.
    grid.data = [0] * 16
    h.on_traversability(grid)
    assert h.failed and not h.ledger.reported


def test_measured_idle_roundoff_uses_the_existing_stop_tolerance_for_coverage():
    h = harness()
    belief = BeliefMap.from_arrays(np.zeros((4, 4)), run_id='run',
                                  origin_x_m=0., origin_y_m=0.)
    publish_batch(h, belief, 9)
    state = telemetry(10, x=10., y=2.)  # free cell 2; no new hazard to trigger a moving scan
    state.velocity.linear.z = 5e-10
    state.velocity.angular.x = -5e-10
    h.on_state(state)
    h.tick()
    observation = h.pub.publish.call_args.args[0]
    assert list(observation.cell_indices) == [2]
    assert list(observation.obstacle) == [0]
