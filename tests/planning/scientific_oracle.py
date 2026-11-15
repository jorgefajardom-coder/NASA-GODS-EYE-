"""Test-only exhaustive directed itinerary oracle, independent of planner search.

Edges and clearances are synthetic admitted-graph inputs, NOT terrain clearance
validation. No heuristic, dominance, planner geometry or consumption ledger.
"""
from dataclasses import dataclass
from mge_mission.models import CostEstimate, estimate_activity, estimate_segment


@dataclass(frozen=True)
class Itinerary:
    outbound: tuple
    returning: tuple
    cost: CostEstimate
    clearance: float


def paths(edges, start, goal):
    def visit(node, path):
        if node == goal:
            yield path
            return
        for a, b in edges:
            if a == node and b not in path:
                yield from visit(b, path + (b,))
    yield from visit(start, (start,))


def enumerate_itineraries(profile, points, edges, start, goal, base, activities):
    """Enumerate all simple paths per leg; return revisits remain legal.

    Complete enumeration is finite on tiny graphs. Nonnegative fixed additive
    costs make cycles unnecessary. History-dependent activities are unsupported.
    Activities contain (unique ID, explicit kind, pending seconds).
    """
    activities = tuple(activities)
    ids = [a[0] for a in activities]
    if len(set(ids)) != len(ids) or any(not a[0] or not a[1] for a in activities):
        raise ValueError('explicit unique activity IDs and kinds required')
    work = [estimate_activity(profile, kind, seconds) for _, kind, seconds in activities]
    for out in paths(edges, start, goal):
        for back in paths(edges, goal, base):
            components = [estimate_segment(profile, points[a], points[b])
                          for path in (out, back) for a, b in zip(path, path[1:])]
            components += work
            cost = CostEstimate(sum(c.time_s for c in components),
                                sum(c.energy_wh for c in components),
                                sum(c.oxygen_l for c in components) if profile.kind == 'human' else None)
            clearance = min((edges[a, b] for path in (out, back)
                             for a, b in zip(path, path[1:])), default=float('inf'))
            yield Itinerary(out, back, cost, clearance)


def feasible(itinerary, available, reserves):
    fields = ('time_s', 'energy_wh', 'oxygen_l') if itinerary.cost.oxygen_l is not None else ('time_s', 'energy_wh')
    if any((c.oxygen_l is None) != (itinerary.cost.oxygen_l is None) for c in (available, reserves)):
        raise ValueError('oxygen applicability mismatch')
    return all(getattr(available, k)-getattr(reserves, k) >= getattr(itinerary.cost, k) for k in fields)


def choose(itineraries, available, reserves, *, safe=False):
    candidates = [r for r in itineraries if feasible(r, available, reserves)]
    return min(candidates, key=lambda r: (-r.clearance, r.cost.time_s) if safe else (r.cost.time_s,), default=None)
