"""Local in-process scientific-cost consumer of the published search hook.

This is an explicitly separate research configuration, not ROS integration,
profile approval, production cost agreement or mission route authorization.
The planner's geometry and search implementations are neither copied nor
modified. Its published geometry_cache dependency supplies the extension point.
"""
from dataclasses import replace
import math

from .models import estimate_activity, estimate_segment


POLICY_ID = "LOCAL_INPROCESS_EXACT_COST_SEARCH_NOT_ROS"


class ScientificSearchAuditError(ValueError):
    """A returned candidate failed independent cost/resource reconciliation."""


def _finite_duration(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
        raise ValueError("Activity duration must be finite and nonnegative")
    return float(value)


class _ScientificGeometry:
    def __init__(self, geometry, costs):
        self.original, self.costs = geometry, costs

    def __getattr__(self, name):
        return getattr(self.original, name)

    def _priced_edge(self, a, b, admitted):
        if admitted is None:
            return None
        g = self.original
        if g.optimistic and (not g.known[a] or not g.known[b]):
            # Optimistic connectivity diagnoses unresolved terrain only. Its
            # flattened unknown heights must never become asserted science.
            return admitted
        cost = self.costs.movement(g.grid.point(a), g.grid.point(b))
        return (admitted[0], cost.time_s, cost.energy_wh, cost.oxygen_l or 0.)

    def edge(self, a, b):
        return self._priced_edge(a, b, self.original.edge(a, b))

    def neighbours(self, cell, threshold=0.):
        for other, admitted in self.original.neighbours(cell, threshold):
            yield other, self._priced_edge(cell, other, admitted)

    def connect_start(self, position, cell):
        connector = self.original.connect_start(position, cell)
        if connector is None:
            return None
        if self.original.optimistic and not self.original.known[cell]:
            return connector
        cost = self.costs.movement(connector.start, connector.end)
        return replace(connector, travel_time_s=cost.time_s,
                       energy_est_wh=cost.energy_wh, oxygen_est_l=cost.oxygen_l)


class _ScientificGeometryCache:
    def __init__(self, core, costs):
        self.original, self.costs = core.GeometryCache(), costs
        self.entries = {}

    def get(self, terrain, profile, *, optimistic=False):
        geometry = self.original.get(terrain, profile, optimistic=optimistic)
        key = id(geometry)
        if key not in self.entries:
            self.entries[key] = _ScientificGeometry(geometry, self.costs)
        return self.entries[key]


def _independent_audit(result, profile, activities, request):
    if getattr(result.status, "value", result.status) != "FEASIBLE":
        return
    parts = []
    for path in (result.outbound_path, result.return_path):
        parts.extend(estimate_segment(profile, a, b) for a, b in zip(path, path[1:]))
    parts.extend(estimate_activity(profile, item.kind, item.remaining_s) for item in activities)
    values = {"time_s": sum(p.time_s for p in parts), "energy_wh": sum(p.energy_wh for p in parts),
              "oxygen_l": sum(p.oxygen_l for p in parts) if profile.kind == "human" else None}
    fields = {"time_s": "travel_time_s", "energy_wh": "energy_est_wh", "oxygen_l": "oxygen_est_l"}
    for name, expected in values.items():
        actual = getattr(result, fields[name])
        if expected is None:
            if actual is not None:
                raise ScientificSearchAuditError("Robot oxygen must remain absent")
        elif not isinstance(actual, (int, float)) or not math.isfinite(actual) or not math.isclose(actual, expected, rel_tol=1e-5, abs_tol=1e-3):
            raise ScientificSearchAuditError("SCIENTIFIC_SEARCH_COST_MISMATCH: " + name)
    available = {"time_s": request.budget.time_s, "energy_wh": request.budget.energy_wh,
                 "oxygen_l": request.budget.oxygen_l}
    reserve = {"time_s": request.reserve_time_s, "energy_wh": request.budget.reserve_wh,
               "oxygen_l": request.budget.reserve_oxygen_l}
    if any(available[k] - reserve[k] - value < 0 for k, value in values.items() if value is not None):
        raise ScientificSearchAuditError("SCIENTIFIC_SEARCH_BUDGET_EXCEEDED: no comparison-tolerance credit")


def scientific_plan(core, scientific_costs, *, terrain, request, motion_profile,
                    activities=(), limits=None, allow_continuous_start=False):
    """Run unchanged FAST/SAFE search with exact movement and fixed-goal work.

    ``core`` and ``scientific_costs`` are explicit, source-identified published
    consumers supplied by the caller. Activities use the existing planner
    Activity objects (activity_id, kind, remaining_s), ordered at the goal.
    No waiting outside that fixed schedule, partial-work evidence or arbitrary
    multi-location task order is inferred. Callers debit prior intervals once
    before supplying current remaining budgets and separate reserves.

    The stock search's one stationary transition is represented by the exact
    schedule's duration and aggregate rates, while movement uses the individual
    scientific API for every admitted directed edge. This scalar equivalence
    is local to this immutable fixed schedule; it is not a ROS context channel.
    """
    profile = scientific_costs.profile
    if profile.kind not in {"human", "rover"}:
        raise ValueError("Scientific search currently supports ground agents only")
    if request.agent_id != profile.agent_id or request.agent_kind != profile.kind or motion_profile.agent_kind != profile.kind:
        raise ValueError("Request, motion and scientific agent identities must match")
    activities = tuple(activities)
    seen, costs = set(), []
    for item in activities:
        if not isinstance(item.activity_id, str) or not item.activity_id.strip() or item.activity_id in seen:
            raise ValueError("Activity identities must be explicit and unique")
        if not isinstance(item.kind, str) or not item.kind.strip():
            raise ValueError("Explicit activity kind is required")
        seen.add(item.activity_id)
        declared_duration = _finite_duration(item.remaining_s)
        cost = scientific_costs.activity(item)
        if cost.time_s != declared_duration:
            raise ValueError("Activity backend duration must match the declared remaining work")
        costs.append(cost)
    duration = sum(_finite_duration(item.remaining_s) for item in activities)
    if not math.isclose(request.service_time_s, duration, rel_tol=0., abs_tol=1e-9):
        raise ValueError("Request service_time_s must equal the explicit remaining activity schedule")
    up = profile.parameters["max_slope_deg"]
    down = profile.parameters.get("max_downhill_slope_deg", up)
    if motion_profile.max_slope_deg > up or (motion_profile.max_downhill_slope_deg if motion_profile.max_downhill_slope_deg is not None else motion_profile.max_slope_deg) > down:
        raise ValueError("Motion geometry cannot exceed the scientific directed grade limits")
    energy = sum(p.energy_wh for p in costs)
    oxygen = sum(p.oxygen_l for p in costs) if profile.kind == "human" else None
    # Horizontal distance / fastest admitted speed is an admissible lower
    # bound for both scientific ground models, including all service time.
    speed = profile.parameters["speed_m_s"] * (1 - profile.parameters["slip"] if profile.kind == "rover" else 1)
    motion = replace(motion_profile, speed_m_s=speed,
                     service_power_w=energy * 3600 / duration if duration else 0.,
                     oxygen_l_per_s=(oxygen / duration if duration else 0.) if profile.kind == "human" else None)
    result = core.plan_route(terrain=terrain, request=request, profile=motion,
                             limits=limits, allow_continuous_start=allow_continuous_start,
                             geometry_cache=_ScientificGeometryCache(core, scientific_costs))
    _independent_audit(result, profile, activities, request)
    return result
