"""MOCK kinematic execution: following, consumption rates and stopping.

Paths and estimates are illustrative test inputs, not routes or a model.
"""
import math

import pytest

from mge_sim.kinematics import (
    ExecutionRefused, HALTED, IDLE, MOVING, PathFollower, Rates, length, route_rates,
)

OUT = [(0.0, 0.0, 0.0), (4.0, 0.0, 0.0), (4.0, 3.0, 0.0)]       # 7 m
BACK = [(4.0, 3.0, 0.0), (0.0, 0.0, 0.0)]                       # 5 m


def on_segment(p, a, b, tol=1e-9):
    d = [y - x for x, y in zip(a, b)]
    t = sum((pi - ai) * di for pi, ai, di in zip(p, a, d)) / sum(di * di for di in d)
    q = [ai + t * di for ai, di in zip(a, d)]
    return -tol <= t <= 1 + tol and math.dist(p, q) <= tol


def test_rates_come_from_the_route_estimates():
    rates = route_rates(OUT, BACK, 24.0, 12.0, 6.0)
    assert rates == Rates(speed_m_s=0.5, energy_wh_s=0.5, oxygen_l_s=0.25)
    assert route_rates(OUT, BACK, 24.0, 12.0, math.nan).oxygen_l_s == 0.0   # not a human


@pytest.mark.parametrize('args', [
    (OUT, BACK, 0.0, 1.0, 1.0), (OUT, BACK, math.nan, 1.0, 1.0),
    (OUT, BACK, 1.0, math.inf, 1.0), (OUT, BACK, 1.0, 1.0, -1.0),
    ([(0.0, 0.0, 0.0)], [], 1.0, 1.0, 1.0),
])
def test_unusable_estimates_refuse_execution(args):
    with pytest.raises(ExecutionRefused):
        route_rates(*args)


def test_follower_stays_on_the_polyline_and_arrives():
    follower = PathFollower(OUT, Rates(1.0, 0.0, 0.0), OUT[0])
    assert follower.advance(2.5) == pytest.approx(2.5)
    assert follower.position == pytest.approx((2.5, 0.0, 0.0))
    assert follower.direction() == pytest.approx((1.0, 0.0, 0.0))
    follower.advance(2.0)                                   # crosses the corner
    assert follower.position == pytest.approx((4.0, 0.5, 0.0))
    assert on_segment(follower.position, OUT[1], OUT[2])
    assert follower.advance(10.0) == pytest.approx(2.5)     # only the remaining time
    assert follower.state == IDLE and follower.position == OUT[-1]
    assert follower.direction() == (0.0, 0.0, 0.0)
    assert follower.advance(1.0) == 0.0


def test_stop_halts_in_place_and_never_resumes():
    follower = PathFollower(OUT, Rates(1.0, 0.0, 0.0), OUT[0])
    follower.advance(3.0)
    follower.stop()
    assert follower.state == HALTED and follower.position == pytest.approx((3.0, 0.0, 0.0))
    assert follower.advance(5.0) == 0.0
    assert follower.position == pytest.approx((3.0, 0.0, 0.0))  # not the next waypoint
    assert follower.direction() == (0.0, 0.0, 0.0)


def test_path_must_start_at_the_agent():
    with pytest.raises(ExecutionRefused, match='does not start'):
        PathFollower(OUT, Rates(1.0, 0.0, 0.0), (0.5, 0.0, 0.0))
    # Height comes from the path (belief surface), not the configured agent z.
    follower = PathFollower(OUT, Rates(1.0, 0.0, 0.0), (0.0, 0.0, -2571.0))
    assert follower.position == OUT[0]
    with pytest.raises(ExecutionRefused, match='two points'):
        PathFollower(OUT[:1], Rates(1.0, 0.0, 0.0), OUT[0])


def test_repeated_waypoint_and_three_dimensional_segments():
    path = OUT + BACK                       # mock mission joins outbound and return
    follower = PathFollower(path, Rates(2.0, 0.0, 0.0), path[0])
    follower.advance(length(path) / 2.0)
    assert follower.state == IDLE and follower.position == path[-1]
    slope = [(0.0, 0.0, 0.0), (3.0, 0.0, 4.0)]
    follower = PathFollower(slope, Rates(1.0, 0.0, 0.0), slope[0])
    follower.advance(2.5)
    assert follower.position == pytest.approx((1.5, 0.0, 2.0))
    assert on_segment(follower.position, *slope)
    assert follower.state == MOVING
