from types import SimpleNamespace as N
from time import monotonic
import pytest
from mge_mission.stop_ack import StopBarrier

def feedback(ns,mode="HALTED",x=2.,v=0.,run="run",agent="human_1"):
    return N(run_id=run,agent_id=agent,header=N(frame_id="map",stamp=N(sec=ns//10**9,nanosec=ns%10**9)),
             pose=N(position=N(x=x,y=3.,z=0.)),mode=mode,
             velocity=N(linear=N(x=v,y=0.,z=0.),angular=N(x=0.,y=0.,z=0.)))

def barrier():return StopBarrier("run","human_1","old-route",10**9,monotonic())

def test_requires_two_distinct_fresh_stationary_samples():
    b=barrier()
    assert not b.observe(feedback(10**9),2*10**9)
    assert not b.observe(feedback(1_100_000_000),2*10**9)
    assert not b.observe(feedback(1_100_000_000),2*10**9)
    assert b.observe(feedback(1_200_000_000),2*10**9)

@pytest.mark.parametrize("change",[dict(mode="MOVING"),dict(v=.1),dict(v=float('nan')),dict(run="other"),dict(agent="other"),dict(x=float('inf'))])
def test_wrong_scope_or_nonstationary_feedback_never_acknowledges(change):
    b=barrier();assert not b.observe(feedback(1_100_000_000,**change),2*10**9)
    assert not b.acknowledged

def test_future_pose_motion_and_position_changes_cannot_supply_stability():
    b=barrier();assert not b.observe(feedback(3*10**9),2*10**9)
    assert not b.observe(feedback(1_100_000_000),2*10**9)
    assert not b.observe(feedback(1_200_000_000,x=2.1),2*10**9)
    assert b.observe(feedback(1_300_000_000,x=2.1),2*10**9)

@pytest.mark.parametrize("poll_first", [False, True])
@pytest.mark.parametrize("now", [6_000_000_000, 6_000_000_001, 8_000_000_000])
def test_late_ack_is_terminal_in_either_callback_order(poll_first, now):
    b = StopBarrier("run", "human_1", "old-route", 10**9, 100.)
    assert not b.observe(feedback(1_100_000_000), 2*10**9, wall_s=100.1)
    if poll_first:
        assert b.failure_reason(now, wall_s=100.2) == "STOP_ACK_TIMEOUT"
    # The feedback itself is old but otherwise valid. Arrival/run time governs.
    assert not b.observe(feedback(1_200_000_000), now, wall_s=100.3)
    assert b.failure_reason(now, wall_s=100.4) == "STOP_ACK_TIMEOUT"
    assert not b.acknowledged
    assert not b.observe(feedback(now), now, wall_s=100.5)


def test_pause_preserves_run_time_budget_and_resume_can_ack_before_deadline():
    b = StopBarrier("run", "human_1", "old-route", 10**9, 100., watchdog_s=20.)
    assert b.failure_reason(10**9, wall_s=110.) == ""
    assert not b.observe(feedback(1_100_000_000), 1_100_000_000, wall_s=110.1)
    assert b.observe(feedback(1_200_000_000), 1_200_000_000, wall_s=110.2)
    # ACK met its deadline. Waiting for a candidate does not reopen that deadline.
    assert b.failure_reason(9*10**9, wall_s=110.3) == ""


@pytest.mark.parametrize("poll_first", [False, True])
def test_paused_clock_still_has_a_separate_latched_safety_watchdog(poll_first):
    b = StopBarrier("run", "human_1", "old-route", 10**9, 100.)
    if poll_first:
        assert b.failure_reason(10**9, wall_s=105.) == "STOP_ACK_LIVENESS_TIMEOUT"
    assert not b.observe(feedback(1_100_000_000), 2*10**9, wall_s=105.)
    assert not b.observe(feedback(1_200_000_000), 2*10**9, wall_s=105.1)
    assert b.failure_reason(2*10**9, wall_s=105.2) == "STOP_ACK_LIVENESS_TIMEOUT"
    assert not b.acknowledged


@pytest.mark.parametrize("change", [dict(mode="MOVING"), dict(x=2.1), dict(v=.1)])
def test_ack_cannot_authorize_after_motion_resumes_without_permission(change):
    b = barrier()
    assert not b.observe(feedback(1_100_000_000), 2*10**9)
    assert b.observe(feedback(1_200_000_000), 2*10**9)
    assert not b.observe(feedback(1_300_000_000, **change), 2*10**9)
    assert b.failure == "STOP_ACK_LOST"
    assert not b.observe(feedback(1_400_000_000), 2*10**9)


def test_stale_repeated_feedback_cannot_extend_ack_liveness():
    b = StopBarrier("run", "human_1", "old-route", 10**9, 100.)
    assert not b.observe(feedback(1_100_000_000), 2*10**9, wall_s=100.1)
    assert b.observe(feedback(1_200_000_000), 2*10**9, wall_s=100.2)
    assert not b.observe(feedback(1_200_000_000), 2*10**9, wall_s=104.)
    assert b.failure_reason(2*10**9, wall_s=105.2) == "STOP_ACK_LIVENESS_TIMEOUT"


def test_fresh_stationary_feedback_maintains_liveness_until_authorization():
    b = StopBarrier("run", "human_1", "old-route", 10**9, 100.)
    assert not b.observe(feedback(1_100_000_000), 2*10**9, wall_s=100.1)
    assert b.observe(feedback(1_200_000_000), 2*10**9, wall_s=100.2)
    assert b.observe(feedback(1_300_000_000), 2*10**9, wall_s=104.)
    assert b.failure_reason(2*10**9, wall_s=108.) == ""


def test_clock_reset_latches_failure_even_if_the_clock_recovers():
    b = StopBarrier("run", "human_1", "old-route", 10**9, 100.)
    assert b.failure_reason(2*10**9, wall_s=100.1) == ""
    assert b.failure_reason(10**9, wall_s=100.2) == "CLOCK_RESET"
    assert not b.observe(feedback(2_100_000_000), 3*10**9, wall_s=100.3)


@pytest.mark.parametrize("values", [dict(timeout_s=0.), dict(timeout_s=float('nan')),
                                    dict(watchdog_s=-1.), dict(watchdog_s=float('inf'))])
def test_invalid_deadlines_fail_closed(values):
    with pytest.raises(ValueError):
        StopBarrier("run", "human_1", "old-route", 10**9, 100., **values)
