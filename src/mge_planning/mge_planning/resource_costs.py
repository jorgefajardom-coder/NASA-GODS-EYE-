"""Shared scientific costs and the production scientific-search entry point.

Formulas delegate to mission. Search prices every admitted directed edge and
explicit pending goal activity through this API; mission retains authorization.
AI-assisted integration and tests are declared in docs/ai_usage.json.
"""
from dataclasses import dataclass
import math

from mge_mission.models import AgentProfile, CostEstimate, estimate_activity, estimate_segment


@dataclass(frozen=True)
class Segment:
    start: tuple[float, float, float]
    end: tuple[float, float, float]


@dataclass(frozen=True)
class Activity:
    activity_id: str
    kind: str
    remaining_s: float

    def __post_init__(self):
        if not isinstance(self.activity_id, str) or not self.activity_id.strip():
            raise ValueError("explicit activity identity required")
        if not isinstance(self.kind, str) or not self.kind.strip():
            raise ValueError("explicit activity kind required")


@dataclass(frozen=True)
class BudgetCheck:
    feasible: bool
    reasons: tuple[str, ...]
    margins: CostEstimate | None


@dataclass(frozen=True)
class ScientificCosts:
    profile: AgentProfile

    @property
    def maximum_horizontal_speed(self):
        """An admissible horizontal-time bound for the declared science model."""
        p = self.profile.parameters
        return p["speed_m_s"] * (1-p["slip"] if self.profile.kind == "rover" else 1.)

    def movement(self, start, end):
        return estimate_segment(self.profile, start, end)

    def activity(self, activity: Activity):
        return estimate_activity(self.profile, activity.kind, activity.remaining_s)

    def total(self, itinerary):
        """Sum explicitly ordered pending work once, including directed return.

        No implicit return, service, completed prefix or reserve is added.
        Caller supplies admitted geometry and remaining durations; no ledger.
        """
        components, seen = [], set()
        for item in itinerary:
            if isinstance(item, Segment):
                cost = self.movement(item.start, item.end)
            elif isinstance(item, Activity):
                if item.activity_id in seen:
                    raise ValueError("duplicate activity identity")
                seen.add(item.activity_id)
                cost = self.activity(item)
            else:
                raise ValueError("explicit Segment or Activity required")
            components.append(cost)
        return CostEstimate(sum(c.time_s for c in components),
                            sum(c.energy_wh for c in components),
                            sum(c.oxygen_l for c in components)
                            if self.profile.kind == "human" else None)

    def check_budget(self, cost: CostEstimate, available: CostEstimate,
                     reserves: CostEstimate):
        """Strict capacity check; numerical equivalence tolerances grant no slack."""
        human = self.profile.kind == "human"
        if any((c.oxygen_l is not None) != human for c in (cost, available, reserves)):
            raise ValueError("oxygen applicability must match agent kind")
        names = ("time_s", "energy_wh", "oxygen_l") if human else ("time_s", "energy_wh")
        margins = {name: getattr(available, name)-getattr(reserves, name)-getattr(cost, name)
                   for name in names}
        reasons = tuple(name for name, margin in margins.items() if margin < 0)
        # CostEstimate forbids negatives; rejected margins are not clamped into feasibility.
        return BudgetCheck(not reasons, reasons, None if reasons else CostEstimate(
            margins["time_s"], margins["energy_wh"], margins.get("oxygen_l")))



def _scientific_geometry_contract(motion, science):
    if motion.agent_kind != science.kind:
        raise ValueError("motion and scientific profile kinds differ")
    p = science.parameters
    down = motion.max_downhill_slope_deg if motion.max_downhill_slope_deg is not None else motion.max_slope_deg
    if motion.max_slope_deg > p["max_slope_deg"] or down > p.get("max_downhill_slope_deg", p["max_slope_deg"]):
        raise ValueError("motion geometry exceeds scientific directed slope limits")
    if motion.max_step_m > p["max_step_m"]:
        raise ValueError("motion geometry exceeds scientific step limit")
    if motion.radius_m < p["radius_m"] or motion.localization_error_m < p["localization_error_m"]:
        raise ValueError("motion footprint is smaller than the scientific profile")
    if motion.max_sigma_m is None or motion.max_sigma_m > p["max_sigma_m"]:
        raise ValueError("motion uncertainty admission exceeds the scientific profile")


def _audit_scientific_candidate(result, request, profile, activities):
    """Independent path/schedule reconciliation; comparison grants no resources."""
    parts = [estimate_segment(profile, a, b)
             for path in (result.outbound_path, result.return_path)
             for a, b in zip(path, path[1:])]
    parts.extend(estimate_activity(profile, a.kind, a.remaining_s) for a in activities)
    expected = CostEstimate(sum(p.time_s for p in parts), sum(p.energy_wh for p in parts),
                            sum(p.oxygen_l for p in parts) if profile.kind == "human" else None)
    for field, output in (("time_s", "travel_time_s"), ("energy_wh", "energy_est_wh"),
                          ("oxygen_l", "oxygen_est_l")):
        actual, wanted = getattr(result, output), getattr(expected, field)
        if wanted is None:
            if actual is not None:
                raise ValueError("nonhuman oxygen must remain absent")
        elif not isinstance(actual, (int, float)) or not math.isfinite(actual) or not math.isclose(actual, wanted, rel_tol=1e-5, abs_tol=1e-3):
            raise ValueError("candidate differs from independent scientific itinerary: " + field)
    values = ((request.budget.time_s, request.reserve_time_s, expected.time_s, result.reserve_time_s),
              (request.budget.energy_wh, request.budget.reserve_wh, expected.energy_wh, result.reserve_wh))
    if profile.kind == "human":
        values += ((request.budget.oxygen_l, request.budget.reserve_oxygen_l,
                    expected.oxygen_l, result.reserve_oxygen_l),)
    for available, reserve, spent, remaining in values:
        if spent > available-reserve:
            raise ValueError("independent scientific itinerary violates a strict reserve")
        if remaining is None or not math.isfinite(remaining) or not math.isclose(remaining, available-spent, rel_tol=1e-5, abs_tol=1e-3):
            raise ValueError("candidate remaining resources differ from the scientific ledger")


def scientific_plan_route(*, terrain, request, motion_profile, scientific_profile,
                          activities=(), limits=None, allow_continuous_start=False):
    """Plan with scientific movement, activity and directed-return costs.

    The fixed, explicit schedule belongs to the goal. Spent work is excluded by
    the caller's current allocations. This function is used by the ROS service;
    profile approval, typed request/context transport and mission authorization
    remain separate checks. No coefficient, state, or pose is silently changed.
    """
    from .core import RouteResult, RouteStatus, plan_route
    if request.agent_id != scientific_profile.agent_id or request.agent_kind != scientific_profile.kind:
        raise ValueError("request and scientific profile identities differ")
    _scientific_geometry_contract(motion_profile, scientific_profile)
    activities = tuple(activities)
    if any(not isinstance(a, Activity) for a in activities):
        raise ValueError("explicit Activity records are required")
    backend = ScientificCosts(scientific_profile)
    service = backend.total(activities)
    if not math.isclose(service.time_s, request.service_time_s, rel_tol=0., abs_tol=1e-9):
        raise ValueError("service_time_s differs from the explicit pending goal schedule")
    result = plan_route(terrain=terrain, request=request, profile=motion_profile,
                        limits=limits, allow_continuous_start=allow_continuous_start,
                        cost_model=backend,
                        stationary_costs=(service.time_s, service.energy_wh, service.oxygen_l or 0.))
    if result.status != RouteStatus.FEASIBLE:
        return result
    try:
        _audit_scientific_candidate(result, request, scientific_profile, activities)
    except ValueError as error:
        return RouteResult(status=RouteStatus.ERROR, reason_code="SCIENTIFIC_COST_MISMATCH", detail=str(error),
                           run_id=result.run_id, request_id=result.request_id, agent_id=result.agent_id,
                           mode=result.mode, map_version_used=result.map_version_used,
                           expanded_labels=result.expanded_labels, elapsed_s=result.elapsed_s)
    return result
