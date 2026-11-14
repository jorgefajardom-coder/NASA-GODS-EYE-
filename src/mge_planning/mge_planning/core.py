"""Proposed route API. A* and resource verification are not yet implemented."""

from dataclasses import dataclass
from enum import Enum
from math import isfinite


class RouteStatus(str, Enum):
    FEASIBLE = "FEASIBLE"
    UNKNOWN = "UNKNOWN"
    NO_PATH = "NO_PATH"
    INSUFFICIENT_BUDGET = "INSUFFICIENT_BUDGET"
    STALE_MAP = "STALE_MAP"
    ERROR = "ERROR"


class RouteMode(str, Enum):
    FAST = "FAST"
    SAFE = "SAFE"
    EFFICIENT = "EFFICIENT"


@dataclass(frozen=True)
class ResourceBudget:
    """Hypothetical simulation resources; oxygen is applicable to humans only."""

    agent_kind: str
    time_s: float
    energy_wh: float
    reserve_wh: float
    oxygen_l: float | None = None
    reserve_oxygen_l: float | None = None

    def __post_init__(self):
        if self.agent_kind not in {"human", "rover", "drone"}:
            raise ValueError("agent_kind must be human, rover or drone")
        values = (self.time_s, self.energy_wh, self.reserve_wh)
        if any(not isfinite(value) or value < 0 for value in values):
            raise ValueError("resources must be finite and nonnegative")
        if self.reserve_wh > self.energy_wh:
            raise ValueError("energy reserve exceeds available energy")
        if self.agent_kind == "human":
            if self.oxygen_l is None or self.reserve_oxygen_l is None:
                raise ValueError("a human requires a separate oxygen budget and reserve")
            if any(not isfinite(value) or value < 0
                   for value in (self.oxygen_l, self.reserve_oxygen_l)):
                raise ValueError("oxygen resources must be finite and nonnegative")
            if self.reserve_oxygen_l > self.oxygen_l:
                raise ValueError("oxygen reserve exceeds available oxygen")
        elif self.oxygen_l is not None or self.reserve_oxygen_l is not None:
            raise ValueError("rover and drone budgets must not include human oxygen")


def plan_route(*, terrain, request):
    """Pending: use belief/masks only, never evaluator reference or hidden POIs."""
    raise NotImplementedError("Diego must implement and verify route feasibility")
