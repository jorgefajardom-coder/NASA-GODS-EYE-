"""ROS-independent event policy. Recommendations/candidates, never route authority.

One instance per run/agent/mission, called serially. Mission supplies authoritative
progress and remaining availability. The supervisor, not this module, stops motion.
"""

from collections import OrderedDict
from dataclasses import dataclass, replace
from enum import Enum
import hashlib
import math

import numpy as np

from .core import (
    MotionProfile, PlanRequest, ResourceBudget, RouteResult, RouteStatus,
    SearchLimits, TerrainGrid, GeometryCache, _motion_costs, _segment_clearance,
    _start_z_mismatch, _number, plan_route,
)


class ReplanAction(str, Enum):
    KEEP = "KEEP"
    REPLAN = "REPLAN"
    STOP_REQUIRED = "STOP_REQUIRED"
    UNKNOWN = "UNKNOWN"


class MissionPhase(str, Enum):
    OUTBOUND = "OUTBOUND"
    SERVICE = "SERVICE"
    RETURN = "RETURN"


class EventKind(str, Enum):
    MAP = "MAP"
    POSE = "POSE"
    TASK = "TASK"
    RESOURCES = "RESOURCES"
    TICK = "TICK"
    DANGER = "DANGER"


@dataclass(frozen=True)
class ReplanEvent:
    event_id: str
    run_id: str
    map_version: int
    kind: EventKind
    task_id: str = ""

    def __post_init__(self):
        if not self.event_id or not self.run_id or type(self.map_version) is not int or self.map_version < 0:
            raise ValueError("Event needs identifiers and a nonnegative integer map version")
        object.__setattr__(self, "kind", EventKind(self.kind))


@dataclass(frozen=True)
class RemainingResources:
    """Live availability can be below reserves; not a valid planning budget.

    The policy must issue STOP before conversion to ResourceBudget. This keeps
    ResourceBudget's stronger admission invariant intact for every A* request.
    """
    agent_kind: str
    time_s: float
    energy_wh: float
    reserve_wh: float
    oxygen_l: float | None = None
    reserve_oxygen_l: float | None = None

    def __post_init__(self):
        if self.agent_kind not in {"human", "rover", "drone"}:
            raise ValueError("Unsupported agent kind")
        for name in ("time_s", "energy_wh", "reserve_wh"):
            _number(getattr(self, name), name)
        if self.agent_kind == "human":
            for name in ("oxygen_l", "reserve_oxygen_l"):
                _number(getattr(self, name), name)
        elif self.oxygen_l is not None or self.reserve_oxygen_l is not None:
            raise ValueError("Nonhuman oxygen is not applicable")

    def planning_budget(self):
        return ResourceBudget(self.agent_kind, self.time_s, self.energy_wh,
                              self.reserve_wh, self.oxygen_l, self.reserve_oxygen_l)


@dataclass(frozen=True)
class ReplanState:
    mission: PlanRequest
    active_request: PlanRequest
    active_route: RouteResult  # Supplied only after MissionManager authorization.
    phase: MissionPhase
    pose: tuple
    next_waypoint: int  # Monotonic index in the current leg; never inferred by nearest point.
    remaining: ResourceBudget | RemainingResources
    service_remaining_s: float

    def __post_init__(self):
        object.__setattr__(self, "phase", MissionPhase(self.phase))
        object.__setattr__(self, "pose", tuple(self.pose))
        if len(self.pose) != 3 or not all(math.isfinite(x) for x in self.pose):
            raise ValueError("A finite ENU 3-D pose is required")
        if type(self.next_waypoint) is not int or self.next_waypoint < 1:
            raise ValueError("next_waypoint must be a positive integer")
        if not math.isfinite(self.service_remaining_s) or self.service_remaining_s < 0:
            raise ValueError("service_remaining_s must be finite and nonnegative")


@dataclass(frozen=True)
class ReplanConfig:
    deviation_enter_m: float
    deviation_exit_m: float
    min_interval_s: float
    immediate_horizon_m: float
    max_segment_samples: int = 10000
    max_route_segments: int = 10000
    event_history_size: int = 1024
    max_search_retries: int = 2

    def __post_init__(self):
        if type(self.max_search_retries) is not int or self.max_search_retries < 0:
            raise ValueError("max_search_retries must be a nonnegative integer")
        values = (self.deviation_enter_m, self.deviation_exit_m,
                  self.min_interval_s, self.immediate_horizon_m)
        if not all(math.isfinite(x) and x >= 0 for x in values):
            raise ValueError("Policy thresholds must be finite and nonnegative")
        if self.deviation_exit_m >= self.deviation_enter_m:
            raise ValueError("Deviation exit must be below enter threshold")
        if any(type(x) is not int or x < 2 for x in (self.max_segment_samples, self.max_route_segments, self.event_history_size)):
            raise ValueError("Policy work/history bounds must be integers >= 2")


@dataclass(frozen=True)
class ReplanDecision:
    action: ReplanAction
    reason_code: str
    map_version: int
    invalidate_active: bool = False
    request: PlanRequest | None = None
    candidate: RouteResult | None = None
    candidate_phase: MissionPhase | None = None
    trigger_reason: str = ""
    primary_request: PlanRequest | None = None
    primary_candidate: RouteResult | None = None


def _distance_to_segment(point, a, b):
    p, start, end = (np.asarray(x[:2], dtype=float) for x in (point, a, b))
    delta = end-start
    squared = float(delta @ delta)
    t = 0. if squared == 0 else float(np.clip((p-start) @ delta/squared, 0., 1.))
    return float(np.linalg.norm(p-start-t*delta))


def _planning_request(state, terrain, request_id, *, returning=False):
    """Snapshot current authority-supplied availability; never debit consumption."""
    m = state.mission
    base = m.return_to if m.return_to is not None else m.start
    return replace(m, request_id=request_id, start=state.pose,
                   goal=base if returning else m.goal,
                   require_return=False if returning else m.require_return,
                   return_to=base, budget=(state.remaining.planning_budget()
                   if isinstance(state.remaining, RemainingResources) else state.remaining),
                   map_version=terrain.map_version,
                   service_time_s=0. if returning else state.service_remaining_s)


def _segment_issue(geometry, a, b, max_samples):
    """Whole-segment footprint bound plus traversed-cell directed transitions.

    No collision decision is based on endpoints only. Distances to blocked square
    centres are 1-Lipschitz; subtracting half sample spacing covers BETWEEN samples.
    Unresolved cells are blocked by known geometry. Conservative over-rejection is
    allowed. Surface changes at pending waypoints invalidate the stored polyline.
    """
    g = geometry.grid
    h = math.dist(a[:2], b[:2])
    margin = _segment_clearance(geometry, a, b, max_samples)
    if margin is None:
        return "VALIDATION_LIMIT"
    if margin < 0:
        return "CORRIDOR_BLOCKED"
    # Exact grid-line split: uniform probes alone can miss a tiny crossed cell
    # near a corner and thus miss a directed step/slope restriction there.
    cuts = {0., 1.}
    for axis, origin in ((0, g.origin_x_m), (1, g.origin_y_m)):
        delta = b[axis]-a[axis]
        if delta:
            low, high = sorted(((a[axis]-origin)/g.resolution_m,
                                (b[axis]-origin)/g.resolution_m))
            if high-low > max_samples:
                return "VALIDATION_LIMIT"
            for index in range(math.floor(low)+1, math.ceil(high)):
                t = (origin+index*g.resolution_m-a[axis])/delta
                if 0 < t < 1:
                    cuts.add(t)
    cuts = sorted(cuts)
    if len(cuts) > max_samples:
        return "VALIDATION_LIMIT"
    probes = [0.] + [(x+y)/2 for x, y in zip(cuts, cuts[1:])] + [1.]
    previous = None
    for t in probes:
        point = (a[0]+t*(b[0]-a[0]), a[1]+t*(b[1]-a[1]))
        try:
            cell = g.cell(point)
        except ValueError:
            return "OUTSIDE_MAP"
        if not geometry.allowed[cell]:
            return "CORRIDOR_BLOCKED"
        if previous is not None and previous != cell and geometry.edge(previous, cell) is None:
            return "TRANSITION_INVALID"
        previous = cell
    if h == 0:
        return None if abs(a[2]-b[2]) <= 1e-6 else "TRANSITION_INVALID"
    if _motion_costs(geometry.profile, h, b[2]-a[2]) is None:
        return "TRANSITION_INVALID"
    return None


class ReplanPolicy:
    def __init__(self, config: ReplanConfig, *, limits: SearchLimits | None = None):
        self.config, self.limits = config, limits
        self._identity = None
        self._version = -1
        self._map_digest = None
        self._map_geometry = None
        self._events = OrderedDict()
        self._route_id = None
        self._retired_routes = set()
        self._progress = (-1, 0)
        self._invalidated = False
        self._deviated = False
        self._pending = None
        self._last_plan_s = -math.inf
        self._last_now = -math.inf
        self._attempt = None
        self._sequence = 0
        self._task_generation = 0
        self._service_remaining = math.inf
        self._mission = None
        self._phase_index = -1
        self._geometry_cache = GeometryCache()
        self._map_snapshot = None
        self._retry_key, self._retry_count = None, 0
        self._remaining_floor = None  # Observed availability bound, never a consumption ledger.
        self._cost_mode = None
        self._science_activity_floor = None

    def evaluate(self, *, terrain: TerrainGrid, profile: MotionProfile, state: ReplanState,
                 event: ReplanEvent, now_s: float, scientific_context=None) -> ReplanDecision:
        """Validate every call, then deduplicate/debounce and optionally call A*.

        STOP_REQUIRED is advisory and persists after a feasible candidate. Only a
        different authorized active_route supplied by mission clears invalidation.
        Event retries cannot hide new hazards in a changed pose/map/resource state.
        """
        def decision(action, reason, invalid=False, **kwargs):
            if invalid:
                self._invalidated = True
            return ReplanDecision(action, reason, terrain.map_version, self._invalidated, **kwargs)

        m, r, active = state.mission, state.active_request, state.active_route
        identity = (m.run_id, m.agent_id, m.agent_kind)
        if event.run_id != terrain.run_id or terrain.run_id != m.run_id:
            return decision(ReplanAction.UNKNOWN, "RUN_MISMATCH", True)
        if event.kind == EventKind.DANGER:
            return decision(ReplanAction.STOP_REQUIRED, "IMMEDIATE_DANGER", True)
        if self._identity is not None and self._identity != identity:
            return decision(ReplanAction.UNKNOWN, "POLICY_SCOPE_MISMATCH", True)
        if self._mission is not None and self._mission != m:
            return decision(ReplanAction.UNKNOWN, "MISSION_TEMPLATE_CHANGED", True)
        if (active.status != RouteStatus.FEASIBLE or not active.route_id
                or (active.run_id, active.agent_id, profile.agent_kind) != identity
                or (r.run_id, r.agent_id, r.agent_kind) != identity
                or active.request_id != r.request_id or active.map_version_used != r.map_version
                or state.remaining.agent_kind != m.agent_kind):
            return decision(ReplanAction.UNKNOWN, "ACTIVE_CONTEXT_MISMATCH", True)
        phase_index = list(MissionPhase).index(state.phase)
        if phase_index < self._phase_index:
            return decision(ReplanAction.UNKNOWN, "PHASE_ROLLBACK", True)
        # Availability can decrease with execution; the mission's required
        # reserves cannot be changed by a resource update or adopted request.
        for budget in (r.budget, state.remaining):
            if (budget.reserve_wh != m.budget.reserve_wh
                    or budget.reserve_oxygen_l != m.budget.reserve_oxygen_l):
                return decision(ReplanAction.UNKNOWN, "RESERVE_CONTEXT_MISMATCH", True)
        if r.reserve_time_s != m.reserve_time_s:
            return decision(ReplanAction.UNKNOWN, "RESERVE_CONTEXT_MISMATCH", True)
        base = m.return_to if m.return_to is not None else m.start
        same_xy = lambda a, b: math.dist(a[:2], b[:2]) <= 1e-6
        # An ordinary return uses the original round-trip request. A direct
        # contingency return uses a new one-leg request and must be in RETURN.
        direct_return = state.phase == MissionPhase.RETURN and not r.require_return
        expected_goal = base if direct_return else m.goal
        if not same_xy(r.goal, expected_goal):
            return decision(ReplanAction.UNKNOWN, "ACTIVE_GOAL_MISMATCH", True)
        if not direct_return and r.require_return != m.require_return:
            return decision(ReplanAction.UNKNOWN, "ACTIVE_RETURN_MISMATCH", True)
        if r.require_return:
            requested_base = r.return_to if r.return_to is not None else r.start
            if not same_xy(requested_base, base):
                return decision(ReplanAction.UNKNOWN, "ACTIVE_RETURN_MISMATCH", True)
        if (not active.outbound_path or not same_xy(active.outbound_path[-1], r.goal)
                or (r.require_return and (not active.return_path
                    or not same_xy(active.return_path[0], r.goal)
                    or not same_xy(active.return_path[-1], base)))
                or (not r.require_return and active.return_path)):
            return decision(ReplanAction.UNKNOWN, "ACTIVE_PATH_MISMATCH", True)
        if not math.isfinite(now_s) or now_s < self._last_now:
            return decision(ReplanAction.UNKNOWN, "NON_MONOTONIC_TIME", True)
        self._last_now = now_s
        if terrain.map_version < max(self._version, active.map_version_used):
            return decision(ReplanAction.UNKNOWN, "STALE_MAP", True)
        geometry_key = (terrain.rows, terrain.cols, terrain.resolution_m,
                        terrain.origin_x_m, terrain.origin_y_m, terrain.frame_id)
        if self._map_geometry is not None and geometry_key != self._map_geometry:
            return decision(ReplanAction.UNKNOWN, "GRID_GEOMETRY_CHANGED", True)
        # Immutable snapshot identity is the fast path for POSE/TICK. A distinct
        # object at the same version is still hashed to detect illegal mutation.
        if terrain is self._map_snapshot:
            fingerprint = self._map_digest
        else:
            digest = hashlib.sha256()
            for array in (terrain.elevation_m, terrain.traversability, terrain.sigma_m):
                digest.update(b"absent" if array is None else array.tobytes())
            fingerprint = digest.digest()
        if terrain.map_version == self._version and fingerprint != self._map_digest:
            return decision(ReplanAction.UNKNOWN, "IMMUTABLE_MAP_CHANGED", True)
        self._identity, self._version = identity, terrain.map_version
        self._mission = m
        self._map_geometry, self._map_digest = geometry_key, fingerprint
        self._map_snapshot = terrain
        self._phase_index = phase_index
        changed_route = active.route_id != self._route_id
        if not changed_route and (phase_index, state.next_waypoint) < self._progress:
            return decision(ReplanAction.UNKNOWN, "PROGRESS_ROLLBACK", True)
        if changed_route and (active.route_id in self._retired_routes or
                (self._route_id is not None and active.map_version_used != terrain.map_version)):
            return decision(ReplanAction.UNKNOWN, "STALE_ROUTE_ADOPTION", True)
        # A new authorized route is not a new mission/resource allocation. Check
        # before adoption can clear invalidation; rejected increases never move
        # the bound upward. The first state is bounded by the mission allocation.
        available = (state.remaining.time_s, state.remaining.energy_wh,
                     state.remaining.oxygen_l)
        ceiling = self._remaining_floor or (m.budget.time_s, m.budget.energy_wh,
                                            m.budget.oxygen_l)
        for current, previous, reason in zip(available, ceiling, (
                "TIME_AVAILABILITY_INCREASE", "ENERGY_AVAILABILITY_INCREASE",
                "OXYGEN_AVAILABILITY_INCREASE")):
            if current is not None and current > previous:
                return decision(ReplanAction.UNKNOWN, reason, True)
        if changed_route:
            if self._route_id is not None:
                self._retired_routes.add(self._route_id)
                self._invalidated = False
            self._route_id = active.route_id
            self._progress = (-1, 0)
            self._pending, self._deviated = None, False
            self._retry_key, self._retry_count = None, 0
        self._progress = (phase_index, state.next_waypoint)
        if state.service_remaining_s > m.service_time_s or (state.phase == MissionPhase.RETURN and state.service_remaining_s != 0):
            return decision(ReplanAction.UNKNOWN, "SERVICE_STATE_INVALID", True)
        if state.phase == MissionPhase.OUTBOUND and state.service_remaining_s != m.service_time_s:
            # Arrival alone does not establish elapsed service. Only an explicit
            # SERVICE phase at the goal may debit the original service activity.
            return decision(ReplanAction.UNKNOWN, "OUTBOUND_SERVICE_MISMATCH", True)
        if state.service_remaining_s > self._service_remaining:
            return decision(ReplanAction.UNKNOWN, "SERVICE_PROGRESS_ROLLBACK", True)
        self._service_remaining = state.service_remaining_s
        base = m.return_to if m.return_to is not None else m.start
        remaining = state.remaining
        if (remaining.reserve_wh != m.budget.reserve_wh
                or remaining.reserve_oxygen_l != m.budget.reserve_oxygen_l):
            return decision(ReplanAction.UNKNOWN, "RESERVE_STATE_MISMATCH", True)
        for actual, reserve, reason in (
                (remaining.time_s, m.reserve_time_s, "TIME_RESERVE_DEPLETED"),
                (remaining.energy_wh, remaining.reserve_wh, "ENERGY_RESERVE_DEPLETED"),
                (remaining.oxygen_l, remaining.reserve_oxygen_l, "OXYGEN_RESERVE_DEPLETED")):
            if actual is not None and actual < reserve:
                # Keep the legacy depleted-telemetry bound. A scientific snapshot
                # below reserves cannot form a valid planning context/budget:
                # STOP immediately, but do not admit unvalidated availability.
                scientific = (scientific_context is not None or active.cost_context is not None
                              or (self._cost_mode is not None and self._cost_mode[0] == 'science'))
                if not scientific:
                    self._remaining_floor = available
                return decision(ReplanAction.STOP_REQUIRED, reason, True)
        try:
            if _start_z_mismatch(terrain, state.pose, m.agent_kind, profile,
                                 allow_continuous_start=True):
                return decision(ReplanAction.UNKNOWN, "INVALID_START_Z", True)
        except ValueError:
            return decision(ReplanAction.UNKNOWN, "INVALID_POSITION", True)
        if state.phase == MissionPhase.SERVICE and math.dist(state.pose[:2], m.goal[:2]) > 1e-6:
            return decision(ReplanAction.UNKNOWN, "SERVICE_POSE_MISMATCH", True)
        if state.phase == MissionPhase.OUTBOUND:
            leg, future = active.outbound_path, active.return_path
        else:
            leg = active.return_path if r.require_return else active.outbound_path
            future = ()
        if not leg or state.next_waypoint >= len(leg):
            # Stationary goal/base paths still need safety/resource checks.
            if len(leg) != 1 or state.next_waypoint != 1:
                return decision(ReplanAction.UNKNOWN, "INVALID_PROGRESS_CURSOR", True)
        if state.phase != MissionPhase.OUTBOUND and (not leg or math.dist(leg[-1][:2], base[:2]) > 1e-6):
            return decision(ReplanAction.UNKNOWN, "RETURN_CONTEXT_MISMATCH", True)
        if state.phase == MissionPhase.OUTBOUND and m.require_return and not future:
            return decision(ReplanAction.UNKNOWN, "RETURN_CONTEXT_MISSING", True)
        context = None
        science_selected = scientific_context is not None or active.cost_context is not None
        mode = 'science' if science_selected else 'legacy'
        if self._cost_mode is not None and self._cost_mode[0] != mode:
            return decision(ReplanAction.UNKNOWN, "SCIENTIFIC_MODEL_CHANGED", True)
        if science_selected:
            try:
                from .resource_costs import ScientificContext, ScientificCosts
                if (not isinstance(scientific_context, ScientificContext)
                        or not isinstance(active.cost_context, ScientificContext)):
                    raise ValueError("both active and explicit pending scientific contexts are required")
                active.cost_context.validate(r, profile)
                expected = _planning_request(state, terrain, r.request_id,
                                             returning=state.phase == MissionPhase.RETURN)
                scientific_context.validate(expected, profile)
                if scientific_context.phase != state.phase.value:
                    raise ValueError("pending context phase mismatch")
                if scientific_context.model_key != active.cost_context.model_key:
                    raise ValueError("active and pending science identities differ")
                if self._cost_mode is not None and self._cost_mode[1] != scientific_context.model_key:
                    raise ValueError("scientific model/profile cannot change within a policy")
                if state.phase == MissionPhase.OUTBOUND and (
                        scientific_context.service != active.cost_context.service
                        or scientific_context.waiting != active.cost_context.waiting):
                    raise ValueError("OUTBOUND cannot complete pending goal activities")
                def durations(ctx):
                    return {(role, a.activity_id, a.kind): a.remaining_s
                            for role in ('service', 'waiting') for a in getattr(ctx, role)}
                before = self._science_activity_floor
                if before is None:
                    before = durations(active.cost_context)
                current = durations(scientific_context)
                if any(k not in before or v > before[k] for k, v in current.items()):
                    raise ValueError("pending activity progress cannot increase or change kind")
                if state.phase == MissionPhase.SERVICE and state.service_remaining_s > 0 and any(
                        current.get(k, 0.) != v for k, v in before.items() if k[0] == 'waiting'):
                    raise ValueError("goal waiting cannot complete before service")
                context = scientific_context
                self._science_activity_floor = {k: current.get(k, 0.) for k in before}
            except (ValueError, TypeError, OverflowError):
                return decision(ReplanAction.UNKNOWN, "INVALID_SCIENTIFIC_CONTEXT", True)
        # Admit availability only after ALL applicable context checks. A rejected
        # lower value must not make a corrected snapshot look like replenishment.
        # The earlier increase check still uses the last admitted bound; the
        # invalidation latch is not cleared by correcting inputs.
        self._remaining_floor = available
        self._cost_mode = (mode, context.model_key if context is not None else None)
        pending = (state.pose,) + leg[state.next_waypoint:]
        if len(pending) == 1:
            pending += (leg[-1],)
        paths = (pending,) + ((future,) if future else ())
        if sum(len(path)-1 for path in paths) > self.config.max_route_segments:
            return decision(ReplanAction.UNKNOWN, "VALIDATION_LIMIT", True)
        known = self._geometry_cache.get(terrain, profile)
        issue, immediate = None, False
        reference = leg[max(0, state.next_waypoint-1)]
        try:
            cell = terrain.cell(state.pose)
            if (cell == terrain.cell(reference) and known.known[cell]
                    and abs(reference[2]-terrain.point(cell)[2]) > 1e-6):
                issue, immediate = "SURFACE_CHANGED", True
        except ValueError:
            issue, immediate = "OUTSIDE_MAP", True
        distance = 0.
        for path_index, path in enumerate(paths):
            for a, b in zip(path, path[1:]):
                failure = _segment_issue(known, a, b, self.config.max_segment_samples)
                try:
                    # Retained grid waypoints must still lie on the current surface.
                    if failure is None and abs(b[2]-terrain.point(terrain.cell(b))[2]) > 1e-6:
                        failure = "SURFACE_CHANGED"
                except ValueError:
                    failure = "OUTSIDE_MAP"
                if failure:
                    issue = issue or failure
                    immediate |= path_index == 0 and distance <= self.config.immediate_horizon_m
                distance += math.dist(a[:2], b[:2])
        # Budget check of pending geometry, without subtracting consumed resources.
        time, energy, oxygen = state.service_remaining_s, profile.service_power_w*state.service_remaining_s/3600., 0.
        oxygen += time*(profile.oxygen_l_per_s or 0.)
        if context is not None:
            time, energy, oxygen = context.goal_costs
        if issue is None:
            for path in paths:
                for a, b in zip(path, path[1:]):
                    h = math.dist(a[:2], b[:2])
                    if context is not None:
                        try:
                            c = ScientificCosts(context.profile).movement(a, b)
                            time += c.time_s
                            energy += c.energy_wh
                            oxygen += c.oxygen_l or 0.
                        except (ValueError, OverflowError):
                            return decision(ReplanAction.UNKNOWN, "SCIENTIFIC_COST_ERROR", True)
                    elif h:
                        dt, de, do = _motion_costs(profile, h, b[2]-a[2])
                        time += dt
                        energy += de
                        oxygen += do
            if context is not None and not all(math.isfinite(x) for x in (time, energy, oxygen)):
                return decision(ReplanAction.UNKNOWN, "SCIENTIFIC_COST_ERROR", True)
            b = state.remaining
            if (time > b.time_s-m.reserve_time_s or energy > b.energy_wh-b.reserve_wh
                    or (b.agent_kind == "human" and oxygen > b.oxygen_l-b.reserve_oxygen_l)):
                issue, immediate = "REMAINING_BUDGET_INSUFFICIENT", True
        corridor = _distance_to_segment(state.pose, leg[max(0, state.next_waypoint-1)],
                                        leg[min(state.next_waypoint, len(leg)-1)])
        if corridor > self.config.deviation_enter_m:
            self._deviated = True
        elif corridor <= self.config.deviation_exit_m:
            self._deviated = False
        if self._pending == "CORRIDOR_DEVIATION" and not self._deviated:
            self._pending = None
            self._retry_key, self._retry_count = None, 0
        # Safety precedes stale-event checks and deduplication.
        if issue:
            self._invalidated = True
        if event.map_version != terrain.map_version:
            return decision(ReplanAction.STOP_REQUIRED if immediate else ReplanAction.UNKNOWN,
                            issue or "EVENT_MAP_MISMATCH", True)
        previous = self._events.get(event.event_id)
        if previous is not None and previous != event:
            return decision(ReplanAction.STOP_REQUIRED if immediate else ReplanAction.UNKNOWN,
                            "EVENT_ID_REUSED", True)
        duplicate = previous is not None
        self._events[event.event_id] = event
        if len(self._events) > self.config.event_history_size:
            self._events.popitem(last=False)
        trigger = issue or ("CORRIDOR_DEVIATION" if self._deviated else None)
        if event.kind == EventKind.TASK and not duplicate:
            self._pending = "TASK_REEVALUATION"
            self._task_generation += 1
        trigger = trigger or self._pending
        if not trigger:
            return decision(ReplanAction.STOP_REQUIRED if self._invalidated else ReplanAction.KEEP,
                            "AWAITING_ROUTE_AUTHORIZATION" if self._invalidated else "DUPLICATE_EVENT" if duplicate else "ROUTE_UNAFFECTED",
                            self._invalidated)
        action = ReplanAction.STOP_REQUIRED if immediate else ReplanAction.REPLAN
        attempt = (active.route_id, terrain.map_version, fingerprint, state.phase, state.pose,
                   state.next_waypoint, state.remaining, state.service_remaining_s, profile,
                   m, trigger, self._task_generation, context.fingerprint if context is not None else None)
        retrying = self._retry_key == attempt
        if retrying:
            if self._retry_count > self.config.max_search_retries:
                return decision(ReplanAction.STOP_REQUIRED, "SEARCH_RETRIES_EXHAUSTED", True)
            if now_s-self._last_plan_s < self.config.min_interval_s:
                return decision(ReplanAction.UNKNOWN, "SEARCH_RETRY_DEFERRED", True)
        else:
            self._retry_key, self._retry_count = None, 0
        if not retrying and attempt == self._attempt:
            return decision(ReplanAction.STOP_REQUIRED if self._invalidated else ReplanAction.KEEP,
                            "ALREADY_EVALUATED", self._invalidated)
        if not retrying and issue is None and now_s-self._last_plan_s < self.config.min_interval_s:
            self._pending = trigger
            return decision(ReplanAction.STOP_REQUIRED if self._invalidated else ReplanAction.KEEP,
                            "REPLAN_DEFERRED", self._invalidated)
        if issue == "VALIDATION_LIMIT":
            return decision(ReplanAction.UNKNOWN, issue, True)
        self._attempt, self._last_plan_s = attempt, now_s
        self._sequence += 1
        returning = state.phase == MissionPhase.RETURN or (
            state.phase == MissionPhase.SERVICE and state.service_remaining_s == 0
            and (context is None or not any(a.remaining_s for a in context.waiting)))
        request = _planning_request(state, terrain, f"{m.request_id}-replan-{self._sequence}", returning=returning)
        def science_args(req, is_return):
            if context is None:
                return {}
            return {'scientific_context': replace(context, request=req,
                    phase='RETURN' if is_return else state.phase.value,
                    service=() if is_return else context.service,
                    waiting=() if is_return else context.waiting)}
        candidate = plan_route(terrain=terrain, request=request, profile=profile, limits=self.limits,
                               allow_continuous_start=True, geometry_cache=self._geometry_cache,
                               **science_args(request, returning))
        self._pending = None
        primary = {}
        contingency = ((state.phase == MissionPhase.OUTBOUND or
                        (state.phase == MissionPhase.SERVICE and state.service_remaining_s > 0))
                       and candidate.status in (RouteStatus.NO_PATH, RouteStatus.INSUFFICIENT_BUDGET))
        if contingency:
            # Failure of the complete primary mission does NOT imply that direct
            # return is impossible. Preserve its evidence and test one return leg
            # using the SAME authoritative availability; service is abandoned.
            primary = dict(primary_request=request, primary_candidate=candidate)
            request = replace(request, request_id=request.request_id+"-contingency-return",
                              goal=base, require_return=False, service_time_s=0.)
            candidate = plan_route(terrain=terrain, request=request, profile=profile, limits=self.limits,
                               allow_continuous_start=True, geometry_cache=self._geometry_cache,
                               **science_args(request, True))
            returning = True
        if candidate.status == RouteStatus.FEASIBLE and math.dist(candidate.outbound_path[0][:2], state.pose[:2]) > 1e-6:
            # Start z was already checked uniformly against the ground snapshot.
            # This guard protects horizontal identity without mixing 2-D/3-D data.
            return decision(ReplanAction.UNKNOWN, "CANDIDATE_HORIZONTAL_START_MISMATCH", True,
                            request=request, trigger_reason=trigger, **primary)
        if candidate.status == RouteStatus.FEASIBLE:
            legs = (candidate.outbound_path, candidate.return_path)
            if (sum(max(0, len(path)-1) for path in legs) > self.config.max_route_segments
                    or any(_segment_issue(known, a, b, self.config.max_segment_samples)
                           for path in legs for a, b in zip(path, path[1:]))):
                return decision(ReplanAction.UNKNOWN, "CANDIDATE_VALIDATION_FAILED", True,
                                request=request, trigger_reason=trigger, **primary)
        if candidate.status != RouteStatus.FEASIBLE:
            action = ReplanAction.UNKNOWN if candidate.status in (RouteStatus.UNKNOWN, RouteStatus.STALE_MAP, RouteStatus.ERROR) else ReplanAction.STOP_REQUIRED
        if candidate.status == RouteStatus.UNKNOWN and candidate.reason_code == "SEARCH_LIMIT":
            self._retry_key = attempt
            self._retry_count += 1
            self._pending = trigger
            self._attempt = None
            action = (ReplanAction.STOP_REQUIRED if self._retry_count > self.config.max_search_retries
                      else ReplanAction.UNKNOWN)
            return decision(action, "SEARCH_RETRIES_EXHAUSTED" if action == ReplanAction.STOP_REQUIRED else "SEARCH_LIMIT",
                            True, request=request, candidate=candidate,
                            candidate_phase=MissionPhase.RETURN if returning else state.phase,
                            trigger_reason=trigger, **primary)
        self._retry_key, self._retry_count = None, 0
        # Even a feasible candidate never clears invalidation or grants authorization.
        reason = ("CONTINGENCY_RETURN" if contingency else trigger) if candidate.status == RouteStatus.FEASIBLE else candidate.reason_code
        return decision(action, reason,
                        contingency or issue is not None or candidate.status != RouteStatus.FEASIBLE,
                        request=request, candidate=candidate,
                        candidate_phase=MissionPhase.RETURN if returning else state.phase,
                        trigger_reason=trigger, **primary)
