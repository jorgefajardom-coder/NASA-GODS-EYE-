"""Bounded MOCK recovery checks; these do not approve a scientific model."""
import math


def stamp_key(header):
    return header.stamp.sec, header.stamp.nanosec


def stopped_after(agent, barrier):
    """A fresh, finite zero-velocity state acknowledges the invalidation fence."""
    p, v, w = agent.pose.position, agent.velocity.linear, agent.velocity.angular
    return (agent.header.frame_id == 'map' and stamp_key(agent.header) >= barrier
            and agent.mode in ('HALTED', 'IDLE')
            and all(math.isfinite(x) for x in (p.x, p.y, p.z))
            and all(math.isfinite(x) and abs(x) <= 1e-9
                    for x in (v.x, v.y, v.z, w.x, w.y, w.z)))


def remaining_allocation(limit, initial, current):
    """Charge observed consumption against the original goal allocation once."""
    if not all(math.isfinite(x) and x >= 0 for x in (limit, initial, current)):
        raise ValueError('Resource availability must be finite and nonnegative')
    return max(0., min(current, limit - max(0., initial - current)))
