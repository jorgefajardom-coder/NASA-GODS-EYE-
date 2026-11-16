"""Pure control boundary for the experimental Gazebo rover; no ROS imports.

This follows an authorized route, never plans or authorizes one. Resource
accounting is illustrative MOCK accounting, not a physical power model.
"""
from dataclasses import dataclass, replace
import math

from mge_sim.kinematics import ExecutionRefused, PathFollower, length, route_rates

LOOKAHEAD_M = 1.2
ARRIVE_M = 0.6
TURN_IN_PLACE_RAD = 0.6
MAX_YAW_RATE = 0.5
STOP_VELOCITY_EPSILON = 1e-9  # same boundary as recovery.stopped_after
MAX_DATUM_OFFSET_M = 0.3


def map_height(prior, origin, res, x, y):
    """Bilinear cell-centre height (row 0 south), clamped at the grid edges.

    Diagnostic only: never used to calibrate or replace an acquired or published
    position. Nonfinite source cells stay unavailable.
    """
    rows, cols = len(prior), len(prior[0])
    if (rows < 2 or cols < 2 or not all(math.isfinite(v) for v in (*origin, res, x, y))
            or res <= 0 or any(len(row) != cols for row in prior)):
        raise ValueError('height diagnostics need a finite rectangular cell-centre grid')
    fx = min(max((x - origin[0]) / res - 0.5, 0.0), cols - 1.0)
    fy = min(max((y - origin[1]) / res - 0.5, 0.0), rows - 1.0)
    c0, r0 = min(int(fx), cols - 2), min(int(fy), rows - 2)
    tx, ty = fx - c0, fy - r0
    return ((prior[r0][c0] * (1 - tx) + prior[r0][c0 + 1] * tx) * (1 - ty)
            + (prior[r0 + 1][c0] * (1 - tx) + prior[r0 + 1][c0 + 1] * tx) * ty)


def datum_offset(map_z, physics_z):
    """Return a bounded finite height discrepancy for diagnosis, otherwise None."""
    if not all(math.isfinite(v) for v in (map_z, physics_z)):
        return None
    offset = map_z - physics_z
    return offset if abs(offset) <= MAX_DATUM_OFFSET_M else None


def gz_pose(state, meta):
    """Convert a ROS ENU pose to the explicitly offset Gazebo display frame."""
    p, q = state.pose.position, state.pose.orientation
    lift = meta['agents'][state.agent_id]['lift_m']
    w = q.w if (q.x, q.y, q.z, q.w) != (0.0, 0.0, 0.0, 0.0) else 1.0
    return (p.x, p.y, p.z - meta['z_ref_m'] + lift, q.x, q.y, q.z, w)


def yaw_of(q):
    return math.atan2(2 * (q[3] * q[2] + q[0] * q[1]), 1 - 2 * (q[1] ** 2 + q[2] ** 2))


def pursuit(pose_xy, yaw, points, index, speed):
    """Return linear/yaw commands and progress along the authorized XY path."""
    x, y = pose_xy
    while index < len(points) - 1 and math.dist((x, y), points[index]) < LOOKAHEAD_M:
        index += 1
    tx, ty = points[index]
    if index == len(points) - 1 and math.dist((x, y), (tx, ty)) < ARRIVE_M:
        return 0.0, 0.0, index, True
    err = math.atan2(ty - y, tx - x) - yaw
    err = math.atan2(math.sin(err), math.cos(err))
    w = max(-MAX_YAW_RATE, min(MAX_YAW_RATE, 1.5 * err))
    v = 0.0 if abs(err) > TURN_IN_PLACE_RAD else speed * math.cos(err)
    return v, w, index, False


def rotate_vector(vector, q):
    """Rotate a body-frame vector into the map frame, with unit XYZW q."""
    x, y, z, w = q
    vx, vy, vz = vector
    return ((1 - 2 * (y*y + z*z))*vx + 2*(x*y - z*w)*vy + 2*(x*z + y*w)*vz,
            2*(x*y + z*w)*vx + (1 - 2*(x*x + z*z))*vy + 2*(y*z - x*w)*vz,
            2*(x*z - y*w)*vx + 2*(y*z + x*w)*vy + (1 - 2*(x*x + y*y))*vz)


@dataclass(frozen=True)
class OdomSample:
    stamp_ns: int
    received_at: float
    position: tuple
    orientation: tuple
    linear: tuple
    angular: tuple

    def __post_init__(self):
        if (type(self.stamp_ns) is not int or self.stamp_ns < 0
                or self.stamp_ns >= (2**31) * 10**9
                or len(self.position) != 3 or len(self.orientation) != 4
                or len(self.linear) != 3 or len(self.angular) != 3
                or not all(math.isfinite(v) for v in
                           (self.received_at, *self.position, *self.orientation,
                            *self.linear, *self.angular))
                or abs(sum(c*c for c in self.orientation) - 1) > 1e-6):
            raise ValueError('odometry requires a valid stamp and finite 6-DOF pose/twist')


def odometry_sample(msg, z_ref, received_at):
    """Keep acquisition time and transform Gazebo's body-frame twist to map.

    Gazebo Sim 8 OdometryPublisher emits pose in odom/world and twist in the
    robot body frame (src/systems/odometry_publisher/OdometryPublisher.cc).
    The generated world uses only a translation between world and ROS map.
    """
    stamp = msg.header.stamp
    if not (0 <= stamp.nsec < 10**9):
        raise ValueError('invalid Gazebo nanoseconds')
    p, q, v, w = msg.pose.position, msg.pose.orientation, msg.twist.linear, msg.twist.angular
    quat = (q.x, q.y, q.z, q.w)
    norm = math.sqrt(sum(c*c for c in quat))
    if not math.isfinite(norm) or abs(norm - 1) > 1e-3:
        raise ValueError('invalid Gazebo orientation')
    quat = tuple(c / norm for c in quat)
    return OdomSample(stamp.sec * 10**9 + stamp.nsec, received_at,
                      (p.x, p.y, p.z + z_ref), quat,
                      rotate_vector((v.x, v.y, v.z), quat),
                      rotate_vector((w.x, w.y, w.z), quat))


@dataclass(frozen=True)
class Authorization:
    route_id: str
    points: tuple
    signature: tuple
    energy_per_m: float


def authorized_route(mission, path, run_id, agent_id):
    """Validate immutable route context; current physical XYZ is checked on adoption."""
    if mission is None or not mission.route_id or not path:
        return None
    m, r = mission, mission.active_route
    if (m.run_id != run_id or r.run_id != run_id or m.primary_agent_id != agent_id
            or r.agent_id != agent_id or r.route_id != m.route_id or r.status != 'FEASIBLE'
            or not r.request_id or r.mode not in ('FAST', 'SAFE', 'EFFICIENT')
            or m.header.frame_id != 'map' or r.header.frame_id != 'map'
            or m.map_version <= 0 or r.map_version_used != m.map_version
            or m.mission_state not in ('READY', 'ACTIVE', 'RETURNING')):
        return None
    try:
        xyz = lambda p: (p.x, p.y, p.z)
        outbound, back = tuple(map(xyz, r.outbound_path)), tuple(map(xyz, r.return_path))
        points = tuple(tuple(p) for p in path)
        if points not in (outbound, outbound + back[1:], outbound + back):
            return None
        rates = route_rates(outbound, back, r.travel_time_s, r.energy_est_wh, r.oxygen_est_l)
        # Reuse the existing strict finite-XYZ/path validation without moving it.
        PathFollower(points, rates, points[0])
        PathFollower(outbound + back, rates, outbound[0])
        distance = length(outbound) + length(back)
        if not math.isfinite(distance) or distance <= 0:
            return None
        applicable = (r.travel_time_s, r.energy_est_wh, r.min_clearance_m,
                      r.reserve_time_s, r.reserve_wh)
        if not all(math.isfinite(v) and v >= 0 for v in applicable):
            return None
        if not (math.isnan(r.oxygen_est_l) and math.isnan(r.reserve_oxygen_l)):
            return None  # this adapter only executes the non-human ROVER
        signature = (r.run_id, r.request_id, r.agent_id, m.map_version, r.mode,
                     outbound, back, *applicable)
        return Authorization(r.route_id, points, signature,
                             r.energy_est_wh / distance)
    except (AttributeError, TypeError, ValueError, IndexError):
        return None


class StationaryWindow:
    """Require distinct, advancing, quiet samples and a stable 6-DOF pose."""

    def __init__(self, duration_s=0.3):
        self.duration_ns = round(duration_s * 1e9)
        self.reset()

    def reset(self):
        self.anchor = None
        self.count = 0
        self.last_stamp = -1

    def observe(self, sample):
        if sample.stamp_ns <= self.last_stamp:
            return False
        self.last_stamp = sample.stamp_ns
        if any(abs(v) > STOP_VELOCITY_EPSILON for v in (*sample.linear, *sample.angular)):
            self.anchor, self.count = None, 0
            return False
        if self.anchor is not None:
            q, a = sample.orientation, self.anchor.orientation
            q_distance = min(math.dist(q, a), math.dist(q, tuple(-c for c in a)))
            if math.dist(sample.position, self.anchor.position) > 1e-6 or q_distance > 1e-6:
                self.anchor, self.count = None, 0
        if self.anchor is None:
            self.anchor = sample
        self.count += 1
        return self.count >= 3 and sample.stamp_ns - self.anchor.stamp_ns >= self.duration_ns


class RoverControl:
    """A fail-closed follower driven by new odometry, with a wall-time watchdog."""

    def __init__(self, run_id, agent_id, time_s, energy_wh, speed=0.65,
                 odom_timeout_s=0.5, stop_window_s=0.3):
        if not all(math.isfinite(v) and v > 0 for v in
                   (time_s, energy_wh, speed, odom_timeout_s, stop_window_s)):
            raise ValueError('driver resources, speed and timeouts must be positive and finite')
        self.run_id, self.agent_id = run_id, agent_id
        self.time_s, self.energy_wh, self.speed = time_s, energy_wh, speed
        self.odom_timeout_s = odom_timeout_s
        self.stationary = StationaryWindow(stop_window_s)
        self.sample = self.processed = None
        self.mode, self.stopping_to = 'MOVING', 'IDLE'  # spawning is not a proven stop
        self.follow = None
        self.index = 0
        self.seen = {}
        self.finished = set()
        self.fault = ''
        self.reason = ''
        self.last_ros_ns = None
        self.stop_after_ns = -1
        self.energy_per_m = 0.0
        self.accounting = False

    def receive(self, sample):
        if self.sample is not None and sample.stamp_ns <= self.sample.stamp_ns:
            if sample.stamp_ns < self.sample.stamp_ns:
                self.fault = 'ODOMETRY_CLOCK_REGRESSION'
            return False  # duplicates cannot refresh the watchdog or stop window
        self.sample = sample
        return True

    def interrupt(self, reason):
        if self.follow is not None or self.stopping_to is None:
            self.stationary.reset()
            self.stop_after_ns = self.sample.stamp_ns if self.sample else -1
        self.follow, self.stopping_to, self.reason = None, 'HALTED', reason
        self.mode = 'MOVING'  # no HALTED acknowledgement before measured stability

    def step(self, mission, path, ros_now_ns, monotonic_now):
        """Return ((linear command, yaw command), newly acquired sample or None)."""
        if self.last_ros_ns is not None and ros_now_ns < self.last_ros_ns:
            self.fault = 'ROS_CLOCK_REGRESSION'
        self.last_ros_ns = ros_now_ns
        s = self.sample
        timeout_ns = round(self.odom_timeout_s * 1e9)
        if (self.fault or s is None or monotonic_now - s.received_at > self.odom_timeout_s
                or monotonic_now < s.received_at or ros_now_ns <= 0
                or not -timeout_ns <= ros_now_ns - s.stamp_ns <= timeout_ns):
            self.interrupt(self.fault or 'ODOMETRY_UNAVAILABLE')
            return (0.0, 0.0), None

        is_new = self.processed is None or s.stamp_ns != self.processed.stamp_ns
        if is_new:
            previous = self.processed
            if previous is not None and self.accounting:
                dt = (s.stamp_ns - previous.stamp_ns) * 1e-9
                self.time_s = max(0.0, self.time_s - dt)
                self.energy_wh = max(0.0, self.energy_wh -
                                     self.energy_per_m * math.dist(previous.position, s.position))
            self.processed = s

        current = authorized_route(mission, path, self.run_id, self.agent_id)
        if current is not None:
            previous_signature = self.seen.setdefault(current.route_id, current.signature)
            if previous_signature != current.signature:
                self.finished.add(current.route_id)
                current = None
        if self.follow is not None and (current is None or current != self.follow):
            self.interrupt('ROUTE_INVALIDATED')
        if self.time_s <= 0 or self.energy_wh <= 0:
            if self.follow is not None or self.reason != 'RESOURCE_EXHAUSTED':
                self.interrupt('RESOURCE_EXHAUSTED')
            current = None

        if is_new and self.follow is None and s.stamp_ns > self.stop_after_ns:
            stable = self.stationary.observe(s)
            if self.stopping_to is not None and stable:
                self.mode, self.stopping_to = self.stopping_to, None
                self.energy_per_m = 0.0
                self.accounting = False
            elif self.stopping_to is None and not stable:
                self.interrupt('UNCOMMANDED_MOTION')

        if (self.follow is None and self.stopping_to is None and current is not None
                and current.route_id not in self.finished):
            self.finished.add(current.route_id)
            try:
                # Preserve the ICD 1e-6 m start-XYZ tolerance; do not snap physical telemetry.
                PathFollower(current.points, None, s.position)
            except ExecutionRefused:
                self.interrupt('START_XYZ_MISMATCH')
            else:
                self.follow, self.index = current, 0
                self.mode, self.energy_per_m = 'MOVING', current.energy_per_m
                self.accounting = True
                self.stationary.reset()

        command = (0.0, 0.0)
        if self.follow is not None:
            points_xy = [p[:2] for p in self.follow.points]
            v, w, self.index, done = pursuit(s.position[:2], yaw_of(s.orientation),
                                           points_xy, self.index, self.speed)
            if done:
                self.follow, self.stopping_to = None, 'IDLE'
                self.stop_after_ns = s.stamp_ns
                self.stationary.reset()
            else:
                command = (v, w)
        return command, s if is_new else None
