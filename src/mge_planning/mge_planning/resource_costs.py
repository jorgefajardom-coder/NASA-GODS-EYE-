"""Experimental estimates only; not wired into search or route authorization.

Delegates scientific formulas to mission. Geometry admission and authoritative
execution accounting remain external. Importing this module requires mge_mission.
"""
from dataclasses import dataclass

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
