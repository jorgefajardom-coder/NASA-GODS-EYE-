"""Pure regressions for physical execution authority and telemetry freshness."""
from dataclasses import replace
import math
from types import SimpleNamespace as NS

import pytest

from mge_sim.gz_control import (OdomSample, RoverControl, StationaryWindow,
                                authorized_route, datum_offset, odometry_sample)


def mission(points=((0., 0., 0.), (10., 0., 0.)), route_id='route-1'):
    r = NS(run_id='run', request_id='req-1', agent_id='rover_1', route_id=route_id,
           status='FEASIBLE', mode='FAST', map_version_used=2, header=NS(frame_id='map'),
           outbound_path=[NS(x=x, y=y, z=z) for x, y, z in points], return_path=[],
           travel_time_s=20., energy_est_wh=10., oxygen_est_l=math.nan,
           reserve_time_s=1., reserve_wh=1., reserve_oxygen_l=math.nan, min_clearance_m=0.)
    return NS(run_id='run', primary_agent_id='rover_1', route_id=route_id, active_route=r,
              map_version=2, mission_state='READY', header=NS(frame_id='map'))


def path(m):
    return [(p.x, p.y, p.z) for p in m.active_route.outbound_path]


def sample(t, position=(0., 0., 0.), linear=(0., 0., 0.), angular=(0., 0., 0.)):
    return OdomSample(round(t * 1e9), t, position, (0., 0., 0., 1.), linear, angular)


def update(c, s, m=None):
    c.receive(s)
    return c.step(m, path(m) if m else [], s.stamp_ns, s.received_at)


def ready(**kwargs):
    c = RoverControl('run', 'rover_1', 100., 100., **kwargs)
    for t in (1., 1.15, 1.31):
        update(c, sample(t))
    assert c.mode == 'IDLE'
    return c


def moving():
    c, m = ready(), mission()
    command, acquired = c.step(m, path(m), c.sample.stamp_ns, c.sample.received_at)
    assert command[0] > 0 and acquired is None
    return c, m


@pytest.mark.parametrize('target,field,value', [
    ('mission', 'run_id', 'other'), ('route', 'run_id', 'other'),
    ('mission', 'primary_agent_id', 'other'), ('route', 'agent_id', 'other'),
    ('route', 'status', 'UNKNOWN'), ('route', 'map_version_used', 1),
    ('mission', 'map_version', 0), ('mission', 'mission_state', 'BLOCKED'),
    ('route', 'energy_est_wh', math.nan), ('route', 'reserve_wh', math.inf),
    ('route', 'travel_time_s', 0.), ('route', 'oxygen_est_l', 0.),
])
def test_foreign_stale_nonfeasible_or_nonfinite_route_never_moves(target, field, value):
    c, m = ready(), mission()
    setattr(m if target == 'mission' else m.active_route, field, value)
    command, _ = c.step(m, path(m), c.sample.stamp_ns, c.sample.received_at)
    assert command == (0., 0.) and c.follow is None


@pytest.mark.parametrize('field', ['x', 'z'])
def test_route_start_must_equal_current_physical_xyz(field):
    c, m = ready(), mission()
    setattr(m.active_route.outbound_path[0], field, 1.)
    command, _ = c.step(m, path(m), c.sample.stamp_ns, c.sample.received_at)
    assert command == (0., 0.) and c.follow is None
    assert c.reason == 'START_XYZ_MISMATCH'


def test_height_discrepancy_is_diagnostic_and_cannot_admit_a_map_height_route():
    c, m = RoverControl('run', 'rover_1', 100., 100.), mission()
    for t in (1., 1.15, 1.31):
        _, acquired = update(c, sample(t, position=(0., 0., -.0824)))
    assert datum_offset(0., acquired.position[2]) == pytest.approx(.0824)
    assert acquired.position == (0., 0., -.0824)
    command, _ = c.step(m, path(m), c.sample.stamp_ns, c.sample.received_at)
    assert command == (0., 0.) and c.follow is None
    assert c.reason == 'START_XYZ_MISMATCH' and c.sample.position[2] == -.0824


def test_nan_path_is_rejected_even_when_the_same_nan_is_shared():
    m = mission()
    m.active_route.outbound_path[0].x = math.nan
    assert authorized_route(m, path(m), 'run', 'rover_1') is None


def test_invalid_return_geometry_is_rejected_even_with_outbound_only_active_path():
    m = mission()
    m.active_route.return_path = [NS(x=math.nan, y=0., z=0.), NS(x=0., y=0., z=0.)]
    assert authorized_route(m, path(m), 'run', 'rover_1') is None


def test_changed_geometry_under_same_route_id_brakes_and_cannot_resume():
    c, m = moving()
    changed = mission(((0., 0., 0.), (0., 10., 0.)))
    command, _ = update(c, sample(1.4, linear=(.2, 0., 0.)), changed)
    assert command == (0., 0.) and c.follow is None and c.mode == 'MOVING'
    for t in (1.5, 1.7, 1.9):
        command, _ = update(c, sample(t), m)
    assert c.mode == 'HALTED' and command == (0., 0.) and c.follow is None


def test_pause_watchdog_brakes_without_fabricating_fresh_samples_or_wall_costs():
    c, m = moving()
    _, acquired = update(c, sample(1.4, position=(.1, 0., 0.), linear=(.2, 0., 0.)), m)
    before = c.time_s, c.energy_wh
    command, repeated = c.step(m, path(m), acquired.stamp_ns, 2.4)
    assert command == (0., 0.) and repeated is None
    assert (c.time_s, c.energy_wh) == before and c.mode != 'HALTED'
    assert c.follow is None
    # On unpause, a new physical stop is required and the expired route stays spent.
    for t in (1.5, 1.7, 1.9):
        command, acquired = update(c, sample(t, position=(.1, 0., 0.)), m)
    assert c.mode == 'HALTED' and command == (0., 0.)
    assert acquired.stamp_ns == 1_900_000_000


@pytest.mark.parametrize('linear,angular', [
    ((0., 0., .1), (0., 0., 0.)), ((0., 0., 0.), (.1, 0., 0.)),
    ((0., 0., 0.), (0., .1, 0.)), ((0., 0., 0.), (0., 0., .1)),
])
def test_vertical_or_rotating_rover_never_acknowledges_stop(linear, angular):
    c, _ = moving()
    for t in (1.4, 1.6, 1.8, 2.):
        command, _ = update(c, sample(t, linear=linear, angular=angular))
        assert command == (0., 0.) and c.mode != 'HALTED'


def test_stop_requires_distinct_samples_and_reports_current_unfrozen_pose():
    c, _ = moving()
    update(c, sample(1.4, linear=(.1, 0., 0.)))
    for t in (1.5, 1.7):
        update(c, sample(t, position=(.1, 0., 0.)))
        assert c.mode != 'HALTED'
    command, acquired = update(c, sample(1.9, position=(.1000005, 0., 0.), linear=(1e-10, 0., 0.)))
    assert c.mode == 'HALTED' and command == (0., 0.)
    assert acquired.position == (.1000005, 0., 0.) and acquired.linear == (1e-10, 0., 0.)
    _, acquired = update(c, sample(2., position=(.2, 0., 0.), linear=(.01, 0., 0.)))
    assert c.mode != 'HALTED' and acquired.position == (.2, 0., 0.)


def test_duplicate_odom_cannot_refresh_watchdog_or_satisfy_stop_window():
    c, m = moving()
    assert not c.receive(replace(c.sample, received_at=10.))
    command, acquired = c.step(m, path(m), c.sample.stamp_ns, 10.)
    assert command == (0., 0.) and acquired is None
    window = StationaryWindow()
    s = sample(1.)
    for _ in range(10):
        assert not window.observe(s)


@pytest.mark.parametrize('clock', ['odometry', 'ros'])
def test_backward_clock_fails_closed_without_replenishing_resources(clock):
    c, m = moving()
    update(c, sample(1.5, position=(.1, 0., 0.), linear=(.2, 0., 0.)), m)
    before = c.time_s, c.energy_wh
    if clock == 'odometry':
        assert not c.receive(sample(.5))
    command, acquired = c.step(m, path(m), 500_000_000 if clock == 'ros' else 1_500_000_000, 1.5)
    assert command == (0., 0.) and acquired is None and c.fault
    assert (c.time_s, c.energy_wh) == before


def test_zero_energy_estimate_still_debits_simulation_time():
    c, m = ready(), mission()
    m.active_route.energy_est_wh = 0.
    c.step(m, path(m), c.sample.stamp_ns, c.sample.received_at)
    update(c, sample(1.5, position=(.1, 0., 0.)), m)
    assert c.time_s == pytest.approx(99.81) and c.energy_wh == 100.


def test_resource_depletion_brakes_before_another_motion_command():
    c, m = moving()
    c.time_s = .01
    command, acquired = update(c, sample(1.5, linear=(.2, 0., 0.)), m)
    assert command == (0., 0.) and acquired is not None and c.time_s == 0.
    assert c.mode != 'HALTED' and c.follow is None
    for t in (1.6, 1.8, 2., 2.2):
        command, _ = update(c, sample(t), m)
    assert c.mode == 'HALTED' and command == (0., 0.)


def test_body_twist_conversion_preserves_full_pose_stamp_and_six_velocity_axes():
    q = NS(x=0., y=0., z=math.sqrt(.5), w=math.sqrt(.5))
    msg = NS(header=NS(stamp=NS(sec=12, nsec=345)),
             pose=NS(position=NS(x=1., y=2., z=3.), orientation=q),
             twist=NS(linear=NS(x=1., y=2., z=3.), angular=NS(x=4., y=5., z=6.)))
    s = odometry_sample(msg, -2570., 99.)
    assert s.stamp_ns == 12_000_000_345 and s.received_at == 99.
    assert s.position == (1., 2., -2567.)
    assert s.orientation == pytest.approx((0., 0., math.sqrt(.5), math.sqrt(.5)))
    assert s.linear == pytest.approx((-2., 1., 3.))
    assert s.angular == pytest.approx((-5., 4., 6.))


@pytest.mark.parametrize('changes', [
    {'position': (math.nan, 0., 0.)}, {'linear': (0., math.inf, 0.)},
    {'angular': (0., 0., math.nan)}, {'stamp_ns': -1}, {'orientation': (0., 0., 0., 0.)},
])
def test_invalid_physical_samples_are_rejected(changes):
    with pytest.raises(ValueError):
        replace(sample(1.), **changes)
