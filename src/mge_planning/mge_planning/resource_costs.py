"""Experimental Python-only estimates; never route authorization.

Delegates scientific formulas to mission. Geometry admission and authoritative
execution accounting remain external. Importing this module requires mge_mission.
"""
from dataclasses import dataclass, field
import hashlib
import json
from pathlib import Path
import re

from mge_mission.models import AgentProfile, CostEstimate, estimate_activity, estimate_segment
from mge_mission import models


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


@dataclass(frozen=True)
class ScientificContext:
    """Explicit pending goal work for ONE immutable Python request snapshot.

    Hashes bind declared inputs, not scientific approval or authorization. Prefer
    from_files to bind the actual registry/scenario bytes. No runtime ROS binding.
    Service and waiting are separate, fixed goal schedules; no route stopovers,
    arrival-time-dependent costs, recharge or execution ledger are supported.
    """
    request: object
    profile: AgentProfile
    model_id: str
    profile_registry_sha256: str
    scenario_sha256: str
    phase: str
    service: tuple[Activity, ...]
    waiting: tuple[Activity, ...]
    model_source_sha256: str = field(init=False)
    profile_sha256: str = field(init=False)
    goal_costs: tuple[float, float, float] = field(init=False)

    def __post_init__(self):
        from .core import PlanRequest, ResourceBudget
        if not isinstance(self.request, PlanRequest) or not isinstance(self.profile, AgentProfile):
            raise ValueError("a typed request and scientific profile are required")
        if not isinstance(self.request.budget, ResourceBudget):
            raise ValueError("an immutable planning budget is required")
        if self.model_id != models.MODEL_ID or self.profile.model_id != self.model_id:
            raise ValueError("scientific model identity mismatch")
        for digest in (self.profile_registry_sha256, self.scenario_sha256):
            if not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest):
                raise ValueError("registry and scenario SHA256 are required")
        if self.phase not in {"OUTBOUND", "SERVICE", "RETURN"}:
            raise ValueError("explicit mission phase required")
        if self.profile.kind not in {"human", "rover"}:
            raise ValueError("scientific search currently supports ground agents only")
        r = self.request
        if (r.agent_id, r.agent_kind) != (self.profile.agent_id, self.profile.kind):
            raise ValueError("scientific profile agent mismatch")
        ids = set()
        for name in ("service", "waiting"):
            values = tuple(getattr(self, name))
            for item in values:
                if not isinstance(item, Activity):
                    raise ValueError("explicit Activity instances required")
                if item.activity_id in ids:
                    raise ValueError("duplicate pending activity identity")
                ids.add(item.activity_id)
                # Validate kinds/durations through the shared scientific API.
                estimate_activity(self.profile, item.kind, item.remaining_s)
            object.__setattr__(self, name, values)
        if len(self.service) + len(self.waiting) > 256:
            raise ValueError("at most 256 fixed goal activities are supported")
        if sum(x.remaining_s for x in self.service) != r.service_time_s:
            raise ValueError("explicit pending service must match service_time_s")
        if self.phase == "SERVICE" and r.start[:2] != r.goal[:2]:
            raise ValueError("SERVICE must start at the goal")
        if self.phase == "RETURN" and (self.service or self.waiting or r.require_return):
            raise ValueError("RETURN requires explicit one-leg request and no goal work")
        c = ScientificCosts(self.profile).total(self.service + self.waiting)
        object.__setattr__(self, "goal_costs", (c.time_s, c.energy_wh, c.oxygen_l or 0.))
        object.__setattr__(self, "model_source_sha256", hashlib.sha256(Path(models.__file__).read_bytes()).hexdigest())
        payload = (self.profile.agent_id, self.profile.kind, self.profile.model_id,
                   self.profile.approval_status, self.profile.capabilities,
                   sorted(self.profile.parameters.items()), sorted(self.profile.activity_power_w.items()))
        object.__setattr__(self, "profile_sha256", hashlib.sha256(json.dumps(payload).encode()).hexdigest())

    @classmethod
    def from_files(cls, *, request, registry_path, scenario_path, phase, service, waiting):
        """Load unchanged published-profile format, without promoting approval."""
        profiles = models.load_profiles(registry_path)
        return cls(request, profiles.get(request.agent_id), models.MODEL_ID,
                   hashlib.sha256(Path(registry_path).read_bytes()).hexdigest(),
                   hashlib.sha256(Path(scenario_path).read_bytes()).hexdigest(),
                   phase, service, waiting)

    @property
    def model_key(self):
        return (self.model_id, self.model_source_sha256, self.profile_registry_sha256,
                self.scenario_sha256, self.profile_sha256)

    @property
    def fingerprint(self):
        return hashlib.sha256(repr((self.model_key, self.request, self.phase,
                                    self.service, self.waiting)).encode()).hexdigest()

    def validate(self, request, motion_profile):
        if self.request != request:
            raise ValueError("scientific context does not match request snapshot")
        p = self.profile.parameters
        if motion_profile.agent_kind != self.profile.kind:
            raise ValueError("scientific geometry kind mismatch")
        # More conservative geometry is allowed; science never relaxes admission.
        if (motion_profile.max_slope_deg > p['max_slope_deg']
                or motion_profile.max_step_m > p['max_step_m']
                or motion_profile.radius_m < p['radius_m']
                or motion_profile.localization_error_m < p['localization_error_m']
                or (motion_profile.max_downhill_slope_deg if motion_profile.max_downhill_slope_deg is not None
                    else motion_profile.max_slope_deg) > p.get('max_downhill_slope_deg', p['max_slope_deg'])
                or motion_profile.max_sigma_m is None
                or motion_profile.max_sigma_m > p['max_sigma_m']):
            raise ValueError("geometry limits may not weaken the scientific profile")
