"""MOCK stop-fence and allocation checks, with no ROS runtime."""
from types import SimpleNamespace as NS

import pytest

from mge_sim.recovery import remaining_allocation, stopped_after


def state(*, sec=12, mode='HALTED', velocity=0., z=3., frame='map'):
    return NS(header=NS(frame_id=frame, stamp=NS(sec=sec, nanosec=0)), mode=mode,
              pose=NS(position=NS(x=1., y=2., z=z)),
              velocity=NS(linear=NS(x=velocity, y=0., z=0.),
                          angular=NS(x=0., y=0., z=0.)))


@pytest.mark.parametrize('change', [dict(sec=11), dict(mode='MOVING'),
                         dict(velocity=.1), dict(z=float('nan')), dict(frame='odom')])
def test_stop_fence_refuses_old_moving_or_invalid_feedback(change):
    assert not stopped_after(state(**change), (12, 0))


@pytest.mark.parametrize('mode', ['HALTED', 'IDLE'])
def test_stop_fence_accepts_fresh_stationary_feedback(mode):
    assert stopped_after(state(mode=mode), (12, 0))


def test_replan_charges_original_allocation_without_replenishing_it():
    # The goal has 100 Wh of a 1000 Wh battery; consuming 30 leaves 70, not 100.
    assert remaining_allocation(100., 1000., 970.) == 70.
    assert remaining_allocation(100., 1000., 950.) == 50.
    assert remaining_allocation(100., 1000., 850.) == 0.
    # A goal allocation cannot grant more than the actual resource availability.
    assert remaining_allocation(1000., 100., 70.) == 70.


@pytest.mark.parametrize('value', [-1., float('inf'), float('nan')])
def test_invalid_resource_feedback_is_refused(value):
    with pytest.raises(ValueError):
        remaining_allocation(100., 100., value)
