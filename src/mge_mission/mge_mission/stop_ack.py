"""Fail-closed stop receipt: run-time ACK deadline, separate steady watchdog.

This is software feedback, not physical stop or scientific-work evidence.
Failure is terminal for this receipt; only a new run can recover the authority.
"""
from dataclasses import dataclass, field
import math
from time import monotonic

def stamp_ns(stamp):
    if (type(stamp.sec) is not int or stamp.sec < 0
            or type(stamp.nanosec) is not int or not 0 <= stamp.nanosec < 10**9):
        raise ValueError("invalid stop-feedback stamp")
    return stamp.sec * 10**9 + stamp.nanosec

@dataclass
class StopBarrier:
    run_id: str
    agent_id: str
    route_id: str
    requested_ns: int
    started_wall_s: float
    timeout_s: float = 5.0
    watchdog_s: float = 5.0
    previous: tuple | None = field(default=None, init=False)
    acknowledged: bool = field(default=False, init=False)
    failure: str = field(default="", init=False)
    _last_clock_ns: int = field(default=0, init=False)
    _last_feedback_wall_s: float | None = field(default=None, init=False)

    def __post_init__(self):
        if type(self.requested_ns) is not int or self.requested_ns < 0:
            raise ValueError("invalid stop request time")
        if not math.isfinite(self.started_wall_s):
            raise ValueError("invalid watchdog start")
        if any(not math.isfinite(value) or value <= 0
               for value in (self.timeout_s, self.watchdog_s)):
            raise ValueError("stop deadlines must be finite and positive")
        self._last_clock_ns = self.requested_ns

    def _fail(self, reason):
        self.failure = self.failure or reason
        self.acknowledged = False
        self.previous = None
        return self.failure

    def failure_reason(self, now_ns, *, wall_s=None):
        """Latch expiry before feedback or authorization can use the receipt.

        The deadline is exclusive: an ACK arriving at the deadline is late.
        A paused run consumes no ACK budget. The steady watchdog still blocks
        missing feedback, including an acknowledged stop awaiting authorization.
        Neither clock check changes resource balances or fabricates timestamps.
        """
        if self.failure:
            return self.failure
        if type(now_ns) is not int or now_ns < self._last_clock_ns:
            return self._fail("CLOCK_RESET")
        self._last_clock_ns = now_ns
        if not self.acknowledged and now_ns >= self.requested_ns + round(self.timeout_s * 10**9):
            return self._fail("STOP_ACK_TIMEOUT")
        wall_s = monotonic() if wall_s is None else wall_s
        baseline = (self._last_feedback_wall_s if self.acknowledged
                    else self.started_wall_s)
        if not math.isfinite(wall_s) or wall_s < self.started_wall_s or wall_s - baseline >= self.watchdog_s:
            return self._fail("STOP_ACK_LIVENESS_TIMEOUT")
        return ""

    def observe(self, message, now_ns, *, wall_s=None):
        wall_s = monotonic() if wall_s is None else wall_s
        if self.failure_reason(now_ns, wall_s=wall_s):
            return False
        if (message.run_id != self.run_id or message.agent_id != self.agent_id
                or message.header.frame_id != "map"):
            return False
        try:
            stamp = stamp_ns(message.header.stamp)
        except ValueError:
            return False
        if stamp <= self.requested_ns or stamp > now_ns:
            return False
        if self.previous is not None and stamp <= self.previous[0]:
            return False
        p = message.pose.position
        pose = (p.x, p.y, p.z)
        v, w = message.velocity.linear, message.velocity.angular
        values = (*pose,v.x,v.y,v.z,w.x,w.y,w.z)
        stationary = (all(math.isfinite(x) for x in values)
                      and message.mode in {"HALTED","IDLE"}
                      and max(abs(x) for x in values[3:]) <= 1e-6)
        if self.acknowledged:
            if not stationary or math.dist(pose, self.previous[1]) > 1e-6:
                self._fail("STOP_ACK_LOST")
                return False
            self.previous = (stamp, pose)
            self._last_feedback_wall_s = wall_s
            return True
        if not stationary:
            self.previous = None
            return False
        if self.previous is not None:
            old_stamp, old_pose = self.previous
            if stamp-old_stamp >= 50_000_000 and math.dist(pose,old_pose) <= 1e-6:
                self.acknowledged = True
                self._last_feedback_wall_s = wall_s
        self.previous = (stamp, pose)
        return self.acknowledged
