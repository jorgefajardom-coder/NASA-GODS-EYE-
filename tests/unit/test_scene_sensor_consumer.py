"""Scene delivery against the real mapping consumer; no ROS or evaluator data."""
from dataclasses import replace
from types import SimpleNamespace as NS

import numpy as np
import pytest

from mge_mapping.core import BeliefMap, ObservationFusion, SimulatedObservation
from mge_sim.scene_sensing import (
    FeedbackBatches, FreshTelemetry, Scene, SensorLedger, observation_values,
)


def scenario(blocked=(9,)):
    scene = Scene(4, 4, 0., 0., 4., (0.,) * 16, frozenset(blocked))
    fusion = ObservationFusion(BeliefMap.from_arrays(np.zeros((4, 4)), run_id='run'))
    return scene, fusion, SensorLedger(resend_s=1.)


def report(scene, ledger, rid, cells, version, stamp):
    values = observation_values(scene, cells, .25)
    ledger.sent(rid, cells, version, stamp, acquired_ns=stamp * 1_000_000_000, values=values)
    return SimulatedObservation(rid, 'rover_1', 'run', version, float(stamp), tuple(cells),
                                tuple(values[0]), tuple(values[1]), tuple(values[2]))


def feedback(belief, stamp):
    batches = FeedbackBatches(belief.rows * belief.cols)
    batches.on_meta(belief.map_version, stamp * 1_000_000_000)
    for name, values in (
            ('belief', belief.belief.ravel()), ('sigma', belief.sigma.ravel()),
            ('observed', belief.observed_mask.ravel().astype(int)),
            ('traversability', belief.traversability_grid(max_slope_deg=90).ravel())):
        batches.on_layer(name, stamp * 1_000_000_000, values)
    return batches


def test_reports_a_and_b_are_serialized_until_each_footprint_is_public():
    scene, fusion, ledger = scenario()
    a = report(scene, ledger, 'a', [1], 1, 10)
    assert ledger.select(scene, [9], moving=True) == []
    with pytest.raises(ValueError, match='one observation'):
        report(scene, ledger, 'b-rejected-at-source', [9], 1, 10)
    belief, applied = fusion.apply(a)
    assert applied
    batch = feedback(belief, 11)
    ledger.confirm(batch.current())
    assert ledger.reported == {1} and 9 not in ledger.reported
    assert ledger.select(scene, [9], moving=True) == [9]
    b = report(scene, ledger, 'b-fresh', [9], belief.map_version, 12)
    belief, applied = fusion.apply(b)
    assert applied
    ledger.confirm(feedback(belief, 13).current())
    assert ledger.reported == {1, 9}
    assert belief.applied_observations == ('a', 'b-fresh')
    assert belief.obstacle_grid.ravel()[9] == 100


def test_foreign_update_cannot_ack_or_hide_a_rejected_hazard_report():
    scene, fusion, ledger = scenario()
    pending = report(scene, ledger, 'hazard', [9], 1, 10)
    external = SimulatedObservation('external', 'human_1', 'run', 1, 11., (1,), (0.,), (.25,), (0,))
    belief, _ = fusion.apply(external)
    with pytest.raises(ValueError, match='current belief'):
        fusion.apply(pending)
    ledger.confirm(feedback(belief, 12).current())
    assert ledger.reported == set() and 'hazard' in ledger.pending
    ledger.expire(12.)
    assert ledger.reported == set() and 'hazard' in ledger.unconfirmed
    fresh = report(scene, ledger, 'hazard-reobserved', [9], 2, 13)
    belief, _ = fusion.apply(fresh)
    ledger.confirm(feedback(belief, 14).current())
    assert ledger.reported == {9}


def test_stale_free_acquisition_cannot_erase_a_newer_external_obstacle():
    scene, fusion, ledger = scenario(blocked=())
    free = report(scene, ledger, 'old-free', [9], 1, 10)
    newer = SimulatedObservation('new-obstacle', 'human_1', 'run', 1, 11., (9,), (0.,), (.25,), (100,))
    belief, _ = fusion.apply(newer)
    ledger.confirm(feedback(belief, 12).current())
    assert 'old-free' in ledger.pending and not ledger.reported
    with pytest.raises(ValueError, match='current belief'):
        fusion.apply(free)
    with pytest.raises(ValueError, match='precedes'):
        fusion.apply(replace(free, source_map_version=2))
    assert fusion.belief_map.obstacle_grid.ravel()[9] == 100


def test_mixed_missing_or_ambiguous_public_layers_do_not_confirm():
    scene, fusion, ledger = scenario()
    pending = report(scene, ledger, 'hazard', [9], 1, 10)
    belief, _ = fusion.apply(pending)
    complete = feedback(belief, 11).current()
    batch = FeedbackBatches(16)
    batch.on_meta(2, complete.stamp_ns)
    for name in ('belief', 'sigma', 'observed'):
        batch.on_layer(name, complete.stamp_ns, getattr(complete, name))
    batch.on_layer('traversability', complete.stamp_ns + 1, complete.traversability)
    assert batch.current() is None
    ledger.confirm(batch.current())
    assert 'hazard' in ledger.pending
    unknown = replace(complete, traversability=(-1,) * 16)
    ledger.confirm(unknown)
    assert 'hazard' in ledger.pending
    ledger.confirm(complete)
    assert ledger.reported == {9}


def test_nodata_in_an_unrelated_cell_does_not_disable_a_valid_footprint():
    scene, _, ledger = scenario()
    prior = np.zeros((4, 4))
    prior[0, 0] = np.nan
    fusion = ObservationFusion(BeliefMap.from_arrays(prior, run_id='run'))
    pending = report(scene, ledger, 'finite-hazard', [9], 1, 10)
    belief, _ = fusion.apply(pending)
    batch = feedback(belief, 11)
    assert np.isnan(batch.current().belief[0]) and np.isposinf(batch.current().sigma[0])
    ledger.confirm(batch.current())
    assert ledger.reported == {9}


def state(t=10, *, run='run', frame='map', x=2.):
    zero = lambda: NS(x=0., y=0., z=0.)
    return NS(run_id=run, agent_id='rover_1', mode='IDLE',
              header=NS(frame_id=frame, stamp=NS(sec=t, nanosec=0)),
              pose=NS(position=NS(x=x, y=2., z=0.)), velocity=NS(linear=zero(), angular=zero()))


def test_telemetry_requires_run_frame_finite_pose_order_and_bounded_age():
    guard = FreshTelemetry('run', ['rover_1'], 1.)
    for msg in (state(run='other'), state(frame='odom'), state(x=float('nan')), state(t=9), state(t=12)):
        assert not guard.accept(msg, 10_500_000_000)
    assert guard.accept(state(), 10_500_000_000)
    assert not guard.accept(state(t=9), 10_500_000_000)
    assert not guard.accept(state(), 10_500_000_000)
    assert guard.acquire('rover_1', 10_500_000_000, 10_100_000_000) is None
    assert guard.acquire('rover_1', 11_100_000_000, 0) is None
    assert guard.accept(state(t=11), 11_100_000_000)
    assert guard.acquire('rover_1', 11_100_000_000, 11_000_000_000) is not None
    assert guard.acquire('rover_1', 11_100_000_000, 0) is None  # never reacquire from the same stored pose


def test_backwards_clock_latches_sensing_off_even_if_old_epoch_later_catches_up():
    guard = FreshTelemetry('run', ['rover_1'], 1.)
    assert guard.accept(state(t=10), 10_000_000_000)
    assert not guard.clock(1_000_000_000)
    assert not guard.accept(state(t=11), 11_000_000_000)
    assert guard.acquire('rover_1', 11_000_000_000, 0) is None
    assert guard.clock_failed and not guard.states
