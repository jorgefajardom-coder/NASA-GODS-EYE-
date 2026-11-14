"""MOCK kinematic execution of an authorized route. No ROS imports.

An agent follows the polyline it was given at one constant speed and spends
its resources linearly in time. Speed and consumption are derived only from
the route's own planner estimates: the speed covers the outbound and return
paths in `travel_time_s`, and time, energy and oxygen fall at the rates
`travel_time_s`, `energy_est_wh` and `oxygen_est_l` imply over that time.
This is a stand-in for the simulation backend, not dynamics, terrain contact
or a resource model, and it never plans: it only follows the given points.

A stop leaves the agent exactly where it is, on the polyline; it never moves
on to the next waypoint, which may lie in the area that caused the stop.

A path must start at the agent's horizontal position. Its height is taken from
the path, whose z is the public belief surface the planner adopted for that
start; the agent configuration carries no measured elevation.
"""
from dataclasses import dataclass
import math

MOVING, HALTED, IDLE = 'MOVING', 'HALTED', 'IDLE'


class ExecutionRefused(ValueError):
    """A route that cannot be followed as given; the agent does not move."""


def length(points):
    return sum(math.dist(a, b) for a, b in zip(points, points[1:]))


@dataclass(frozen=True)
class Rates:
    speed_m_s: float
    energy_wh_s: float
    oxygen_l_s: float       # 0 for agents without oxygen


def route_rates(outbound, back, travel_time_s, energy_est_wh, oxygen_est_l):
    """Constant rates implied by the route's own estimates."""
    distance = length(outbound) + length(back)
    if not (isinstance(travel_time_s, (int, float)) and math.isfinite(travel_time_s)
            and travel_time_s > 0):
        raise ExecutionRefused('route has no positive finite travel_time_s')
    if not math.isfinite(energy_est_wh) or energy_est_wh < 0:
        raise ExecutionRefused('route has no finite energy estimate')
    oxygen = 0.0 if oxygen_est_l is None or math.isnan(oxygen_est_l) else oxygen_est_l
    if not math.isfinite(oxygen) or oxygen < 0:
        raise ExecutionRefused('route has an invalid oxygen estimate')
    if distance <= 0:
        raise ExecutionRefused('route has no length')
    return Rates(distance / travel_time_s, energy_est_wh / travel_time_s, oxygen / travel_time_s)


class PathFollower:
    """Position along one authorized polyline, advanced by elapsed time."""

    def __init__(self, points, rates, start, tolerance_m=1e-6):
        points = [tuple(float(c) for c in p) for p in points]
        if len(points) < 2:
            raise ExecutionRefused('a path needs at least two points')
        if math.dist(points[0][:2], tuple(start)[:2]) > tolerance_m:
            # Never teleport: the path must begin where the agent is.
            raise ExecutionRefused('path does not start at the agent position')
        self.points, self.rates = points, rates
        self.segment, self.along_m = 0, 0.0
        self.position = points[0]
        self.state = MOVING

    def direction(self):
        """Unit vector of the current segment (zero once not moving)."""
        if self.state != MOVING:
            return (0.0, 0.0, 0.0)
        a, b = self.points[self.segment], self.points[self.segment + 1]
        d = math.dist(a, b)
        return tuple((y - x) / d for x, y in zip(a, b)) if d else (0.0, 0.0, 0.0)

    def advance(self, dt_s):
        """Move for dt_s seconds; returns the seconds actually spent moving."""
        if self.state != MOVING or dt_s <= 0:
            return 0.0
        remaining_m, moved_m = dt_s * self.rates.speed_m_s, 0.0
        while remaining_m > 0 and self.segment < len(self.points) - 1:
            a, b = self.points[self.segment], self.points[self.segment + 1]
            segment_m = math.dist(a, b)
            step = min(remaining_m, segment_m - self.along_m)
            self.along_m += step
            remaining_m -= step
            moved_m += step
            if self.along_m >= segment_m:
                self.segment, self.along_m = self.segment + 1, 0.0
                self.position = b
            else:
                f = self.along_m / segment_m
                self.position = tuple(x + f * (y - x) for x, y in zip(a, b))
        if self.segment >= len(self.points) - 1:
            self.position, self.state = self.points[-1], IDLE      # arrived
        return moved_m / self.rates.speed_m_s

    def stop(self):
        """Halt where the agent is; it never continues to the next waypoint."""
        if self.state == MOVING:
            self.state = HALTED
