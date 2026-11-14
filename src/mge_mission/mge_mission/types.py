"""Immutable mission boundary values; ROS adapters translate these explicitly."""

from dataclasses import dataclass
from math import isfinite


@dataclass(frozen=True)
class Point:
    x: float
    y: float
    z: float = 0.0

    def coordinates(self):
        return (self.x, self.y, self.z)


@dataclass(frozen=True)
class MissionSpec:
    run_id: str
    base: Point
    return_tolerance_m: float
    primary_service_time_s: float = 0.0
    primary_service_activity: str = "wait"
    frame_id: str = "map"

    def __post_init__(self):
        if not isinstance(self.run_id, str) or not self.run_id.strip() or self.frame_id != "map":
            raise ValueError("a nonempty run and local ENU map frame are required")
        if not isinstance(self.base, Point) or any(type(x) not in (int, float) or not isfinite(x)
                                                  for x in self.base.coordinates()):
            raise ValueError("finite ENU base coordinates required")
        for value in (self.return_tolerance_m, self.primary_service_time_s):
            if type(value) not in (int, float) or not isfinite(value) or value < 0:
                raise ValueError("tolerance and service duration must be finite and nonnegative")
        if not isinstance(self.primary_service_activity, str) or not self.primary_service_activity:
            raise ValueError("an explicit primary service activity is required")


@dataclass(frozen=True)
class Budgets:
    time_s: float
    energy_wh: float
    oxygen_l: float | None
    reserve_time_s: float
    reserve_wh: float
    reserve_oxygen_l: float | None


@dataclass(frozen=True)
class AgentSnapshot:
    run_id: str
    agent_id: str
    kind: str
    position: Point
    time_remaining_s: float
    energy_remaining_wh: float
    oxygen_remaining_l: float | None = None
    mode: str = "IDLE"
    timestamp_sim_s: float = 0.0
    confidence: float = 1.0


@dataclass(frozen=True)
class GoalRequest:
    request_id: str
    run_id: str
    primary_agent_id: str
    base: Point
    goal: Point
    mode: str
    time_budget_s: float
    energy_budget_wh: float
    oxygen_budget_l: float | None
    reserve_time_s: float
    reserve_wh: float
    reserve_oxygen_l: float | None


@dataclass(frozen=True)
class GoalResponse:
    accepted: bool
    request_id: str
    run_id: str
    mission_state: str
    reason_code: str
    detail: str


@dataclass(frozen=True)
class PlanRequest:
    run_id: str
    request_id: str
    agent_id: str
    agent_kind: str
    start: Point
    goal: Point
    return_to: Point
    require_return: bool
    mode: str
    map_version: int
    service_time_s: float
    time_budget_s: float
    energy_budget_wh: float
    oxygen_budget_l: float | None
    reserve_time_s: float
    reserve_wh: float
    reserve_oxygen_l: float | None
    state_revision: int = 0
    service_activity: str = "idle"


@dataclass(frozen=True)
class RouteDecision:
    run_id: str
    request_id: str
    route_id: str
    agent_id: str
    mode: str
    map_version_used: int
    status: str
    reason_code: str = ""
    detail: str = ""
    outbound_path: tuple[Point, ...] = ()
    return_path: tuple[Point, ...] = ()
    travel_time_s: float | None = None
    energy_est_wh: float | None = None
    oxygen_est_l: float | None = None
    min_clearance_m: float | None = None
    reserve_time_s: float | None = None
    reserve_wh: float | None = None
    reserve_oxygen_l: float | None = None

    def __post_init__(self):
        object.__setattr__(self, "outbound_path", tuple(self.outbound_path))
        object.__setattr__(self, "return_path", tuple(self.return_path))


@dataclass(frozen=True)
class MissionEvidence:
    evidence_id: str
    run_id: str
    map_version: int
    route_id: str
    timestamp_sim_s: float
    primary_goal_completed: bool | None = None
    returned_to_base_within_tolerance: bool | None = None
    verified_ground_traversal_under_model: bool | None = None
    no_budget_violation: bool | None = None


@dataclass(frozen=True)
class ObservedTask:
    task_id: str
    run_id: str
    map_version: int
    discovery_id: str
    observer_id: str
    kind: str
    position: Point
    duration_s: float
    predecessor_id: str = ""
    source_kind: str = "SIMULATED"


@dataclass(frozen=True)
class TaskSnapshot:
    task: ObservedTask
    state: str
    agent_id: str = ""
    route_id: str = ""
    reason_code: str = ""


@dataclass(frozen=True)
class TaskEvidence:
    evidence_id: str
    run_id: str
    map_version: int
    route_id: str
    task_id: str
    timestamp_sim_s: float


@dataclass(frozen=True)
class MissionEvent:
    run_id: str
    event_id: str
    seq: int
    causality_id: str
    event_type: str
    task_id: str
    agent_id: str
    map_version: int
    route_id: str
    previous_state: str
    new_state: str
    reason_code: str
    detail: str
    timestamp_sim_s: float | None


@dataclass(frozen=True)
class MissionSnapshot:
    run_id: str
    mission_state: str
    reason_code: str
    detail: str
    base: Point
    primary_goal: Point | None
    primary_agent_id: str
    active_task_id: str
    active_task_kind: str
    active_task_state: str
    map_version: int | None
    route_id: str
    active_route: RouteDecision | None
    agents: tuple[AgentSnapshot, ...]
    last_event_seq: int
    timestamp_sim_s: float | None
    mission_success: bool
    tasks: tuple[TaskSnapshot, ...] = ()
