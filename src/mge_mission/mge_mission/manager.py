"""Single mission authority, independent of ROS and of the planner implementation.

All inputs are public run state or explicit execution evidence. A candidate route
never demonstrates traversal, task completion or a successful return.
"""

from dataclasses import replace
from math import dist, isclose, isfinite
from types import MappingProxyType

from .core import mission_success
from .models import estimate_activity, estimate_segment
from .types import (AgentSnapshot, Budgets, GoalResponse, MissionEvent,
                    MissionSnapshot, MissionSpec, PlanRequest, Point, TaskSnapshot)

_STATUSES = {"FEASIBLE", "UNKNOWN", "NO_PATH", "INSUFFICIENT_BUDGET", "STALE_MAP", "ERROR"}
_TERMINAL = {"COMPLETE", "ABORTED"}


def _number(value):
    return type(value) in (int, float) and isfinite(value) and value >= 0


def _point(value):
    return isinstance(value, Point) and all(type(v) in (int, float) and isfinite(v)
                                           for v in value.coordinates())


def _near(a, b, tolerance=1e-5):
    return _point(a) and _point(b) and dist(a.coordinates(), b.coordinates()) <= tolerance


def _on_segment(point, a, b):
    delta = tuple(y-x for x, y in zip(a.coordinates(), b.coordinates()))
    norm2 = sum(x*x for x in delta)
    if norm2 == 0:
        return _near(point, a)
    along = sum((x-y)*d for x, y, d in zip(point.coordinates(), a.coordinates(), delta)) / norm2
    projected = tuple(x+along*d for x, d in zip(a.coordinates(), delta))
    return 0 <= along <= 1 and dist(point.coordinates(), projected) <= 1e-5


class MissionManager:
    """Serialized-call mission reducer; the ROS adapter supplies locking.

    Profiles are immutable for a run. ``planner_model_agreed`` is a deployment
    assertion, not a wire handshake; numerical cost agreement is checked again.
    Only the primary human's route is exposed as the active locomotion path.
    """

    @classmethod
    def from_spec(cls, spec: MissionSpec, profiles, **safety_options):
        return cls(spec.run_id, profiles, spec.base, spec.return_tolerance_m,
                   primary_service_time_s=spec.primary_service_time_s,
                   primary_service_activity=spec.primary_service_activity, **safety_options)

    def __init__(self, run_id, profiles, base, return_tolerance_m,
                 allow_illustrative=False, primary_service_time_s=0.0,
                 planner_model_agreed=False, approved_model_id=None,
                 primary_service_activity="wait"):
        if not run_id or not _point(base) or not _number(return_tolerance_m):
            raise ValueError("run, finite base and explicit nonnegative tolerance required")
        if not _number(primary_service_time_s):
            raise ValueError("service duration must be finite and nonnegative")
        if any(key != profile.agent_id for key, profile in profiles.items()):
            raise ValueError("profile key and agent ID differ")
        self.run_id, self.base = run_id, base
        self.profiles = MappingProxyType(dict(profiles))
        self.return_tolerance_m = return_tolerance_m
        self.allow_illustrative = allow_illustrative
        self.primary_service_time_s = primary_service_time_s
        if not isinstance(primary_service_activity, str) or not primary_service_activity:
            raise ValueError("an explicit primary service activity is required")
        self.primary_service_activity = primary_service_activity
        self.spec = MissionSpec(run_id, base, return_tolerance_m,
                                primary_service_time_s, primary_service_activity)
        self.planner_model_agreed = planner_model_agreed
        self.approved_model_id = approved_model_id
        self.map_version = None
        self._agents, self._revisions = {}, {}
        self._goal = None
        self._allocation_origin = None
        self._pending = None
        self._route = None
        self._route_request = None
        self._state, self._reason, self._detail = "IDLE", "", ""
        self._clock = None
        self._seq = self._plan_counter = 0
        self._events, self._goals, self._evidence = [], {}, {}
        self._used_route_ids = set()
        self._tasks, self._discoveries, self._optional = {}, {}, {}
        self._facts = dict(primary_goal_completed=False,
                           returned_to_base_within_tolerance=False,
                           verified_ground_traversal_under_model=False,
                           no_budget_violation=False)
        self._return_requested = False
        self._active_task_id = self._active_task_kind = self._active_task_state = ""

    def _emit(self, event_type, cause, *, reason="", detail="", previous="", new="",
              task_id="", agent_id="", route_id=None):
        self._seq += 1
        self._events.append(MissionEvent(
            self.run_id, f"{self.run_id}:event:{self._seq}", self._seq, cause,
            event_type, task_id, agent_id, self.map_version or 0,
            self._route.route_id if route_id is None and self._route else (route_id or ""),
            previous, new, reason, detail, self._clock))

    def _state_to(self, state, cause, reason="", detail=""):
        previous = self._state
        self._state, self._reason, self._detail = state, reason, detail
        if previous != state or reason:
            self._emit("MISSION_STATE_CHANGED", cause, reason=reason, detail=detail,
                       previous=previous, new=state)

    def _clear_route(self, cause, reason):
        if self._route:
            old = self._route.route_id
            self._route = None
            self._route_request = None
            self._emit("ROUTE_INVALIDATED", cause, reason=reason, route_id=old)

    def _profile_reason(self, profile):
        if profile.approval_status == "illustrative" and self.allow_illustrative:
            return ""
        if profile.approval_status != "approved":
            return "PROFILE_NOT_APPROVED"
        if not self.approved_model_id or profile.model_id != self.approved_model_id:
            return "MODEL_NOT_APPROVED"
        return ""

    def _reset_return_evidence(self):
        # These facts describe the completed execution, never a future route.
        for key in ("returned_to_base_within_tolerance",
                    "verified_ground_traversal_under_model", "no_budget_violation"):
            self._facts[key] = False

    @staticmethod
    def _budget_reason(kind, budget, agent):
        values = (budget.time_s, budget.energy_wh, budget.reserve_time_s, budget.reserve_wh)
        if not all(_number(value) for value in values):
            return "INVALID_BUDGET"
        if budget.reserve_time_s > budget.time_s or budget.reserve_wh > budget.energy_wh:
            return "INVALID_RESERVE"
        if budget.time_s > agent.time_remaining_s or budget.energy_wh > agent.energy_remaining_wh:
            return "BUDGET_EXCEEDS_REMAINING"
        if kind == "human":
            if not all(_number(v) for v in (budget.oxygen_l, budget.reserve_oxygen_l)):
                return "INVALID_OXYGEN_BUDGET"
            if budget.reserve_oxygen_l > budget.oxygen_l:
                return "INVALID_RESERVE"
            if budget.oxygen_l > agent.oxygen_remaining_l:
                return "BUDGET_EXCEEDS_REMAINING"
        elif budget.oxygen_l is not None or budget.reserve_oxygen_l is not None:
            return "OXYGEN_NOT_APPLICABLE"
        return ""

    def update_map(self, run_id, map_version, timestamp_sim_s=None):
        if run_id != self.run_id or type(map_version) is not int or not 0 <= map_version < 2**32:
            return False
        if timestamp_sim_s is not None and not _number(timestamp_sim_s):
            return False
        if self.map_version is not None and map_version < self.map_version:
            return False
        if map_version == self.map_version:
            return True
        self.map_version = map_version
        if timestamp_sim_s is not None:
            self._clock = max(self._clock or 0, timestamp_sim_s)
        cause = f"{self.run_id}:map:{map_version}"
        self._emit("MAP_UPDATED", cause)
        self._optional.clear()
        for task_id, task in tuple(self._tasks.items()):
            if task.state in {"ELIGIBLE", "ASSIGNED", "EXECUTING"}:
                self._task_to(task_id, "BLOCKED", cause, "STALE_MAP")
        self._clear_route(cause, "MAP_CHANGED")
        if self._goal and self._state not in _TERMINAL:
            self._schedule_plan(cause, "REPLAN")
        return True

    def update_agent(self, agent: AgentSnapshot):
        profile = self.profiles.get(agent.agent_id)
        if (agent.run_id != self.run_id or profile is None or agent.kind != profile.kind
                or not _point(agent.position) or not _number(agent.timestamp_sim_s)
                or not _number(agent.time_remaining_s) or not _number(agent.energy_remaining_wh)
                or not _number(agent.confidence) or agent.confidence > 1):
            return False
        if ((agent.kind == "human" and not _number(agent.oxygen_remaining_l))
                or (agent.kind != "human" and agent.oxygen_remaining_l is not None)):
            return False
        previous = self._agents.get(agent.agent_id)
        if previous:
            if agent.timestamp_sim_s < previous.timestamp_sim_s:
                return False
            fields = ("position", "time_remaining_s", "energy_remaining_wh", "oxygen_remaining_l")
            changed = any(getattr(previous, f) != getattr(agent, f) for f in fields)
            pose_changed = not _near(previous.position, agent.position)
            if changed and agent.timestamp_sim_s == previous.timestamp_sim_s:
                return False
            if any(getattr(agent, f) > getattr(previous, f)
                   for f in ("time_remaining_s", "energy_remaining_wh")):
                return False  # Replenishment requires a separately defined contract.
            if agent.kind == "human" and agent.oxygen_remaining_l > previous.oxygen_remaining_l:
                return False
        else:
            changed = True
            pose_changed = True
        self._agents[agent.agent_id] = agent
        self._clock = max(self._clock or 0, agent.timestamp_sim_s)
        if pose_changed:
            self._revisions[agent.agent_id] = self._revisions.get(agent.agent_id, 0) + 1
            self._optional = {k: v for k, v in self._optional.items() if v[0].agent_id != agent.agent_id}
        if self._goal and agent.agent_id == self._goal.primary_agent_id and self._state not in _TERMINAL:
            if (self._facts["returned_to_base_within_tolerance"]
                    and not _near(agent.position, self.base, self.return_tolerance_m)):
                self._reset_return_evidence()
            remaining = self._remaining_primary_budgets()
            if (remaining.time_s < remaining.reserve_time_s
                    or remaining.energy_wh < remaining.reserve_wh
                    or remaining.oxygen_l < remaining.reserve_oxygen_l):
                self._facts["no_budget_violation"] = False
                self._pending = None
                self._clear_route(agent.agent_id, "RESERVE_VIOLATION")
                self._state_to("ABORTED", agent.agent_id, "RESERVE_VIOLATION")
            elif self._pending and pose_changed:
                self._schedule_plan(agent.agent_id, "REPLAN")
            elif self._route:
                continuation = self._continuation_reason()
                if continuation == "RETURN_BUDGET_AT_RISK":
                    self.request_return(continuation)
                elif continuation:
                    self._clear_route(agent.agent_id, continuation)
                    self._schedule_plan(agent.agent_id, "REPLAN")
                elif agent.mode == "MOVING" and self._state == "READY":
                    self._active_task_state = "EXECUTING"
                    self._state_to("ACTIVE", agent.agent_id)
        return True

    def set_goal(self, request):
        cached = self._goals.get(request.request_id)
        if cached:
            if cached[0] == request:
                return cached[1]
            return GoalResponse(False, request.request_id, self.run_id, self._state,
                                "REQUEST_ID_CONFLICT", "The request ID already identifies another payload.")
        reason = ""
        agent = self._agents.get(request.primary_agent_id)
        profile = self.profiles.get(request.primary_agent_id)
        if not request.request_id:
            reason = "INVALID_REQUEST_ID"
        elif request.run_id not in ("", self.run_id):
            reason = "WRONG_RUN"
        elif self.map_version is None:
            reason = "MAP_NOT_READY"
        elif agent is None or profile is None:
            reason = "AGENT_NOT_READY"
        elif profile.kind != "human" or "reach" not in profile.capabilities:
            reason = "PRIMARY_AGENT_UNSUPPORTED"
        elif self._profile_reason(profile):
            reason = self._profile_reason(profile)
        elif not _point(request.goal) or not _near(request.base, self.base):
            reason = "INVALID_POSITION"
        elif request.mode not in {"FAST", "SAFE", "EFFICIENT"}:
            reason = "MODE_NOT_SUPPORTED"
        elif self._goal is not None:
            reason = "MISSION_ALREADY_CONFIGURED"
        else:
            budget = Budgets(request.time_budget_s, request.energy_budget_wh, request.oxygen_budget_l,
                             request.reserve_time_s, request.reserve_wh, request.reserve_oxygen_l)
            reason = self._budget_reason(profile.kind, budget, agent)
        if reason:
            response = GoalResponse(False, request.request_id, self.run_id, self._state,
                                    reason, "The mission goal was not accepted.")
            self._emit("GOAL_REJECTED", request.request_id, reason=reason, detail=response.detail)
        else:
            self._goal = request
            self._allocation_origin = agent
            self._active_task_id, self._active_task_kind, self._active_task_state = "primary", "primary", "ELIGIBLE"
            self._emit("GOAL_ACCEPTED", request.request_id, agent_id=request.primary_agent_id)
            self._schedule_plan(request.request_id, "PLANNING")
            response = GoalResponse(True, request.request_id, self.run_id, self._state, "", "Goal accepted for planning.")
        if request.request_id:
            self._goals[request.request_id] = (request, response)
        return response

    def _make_plan(self, agent, goal, return_to, require_return, budgets, mode, duration, activity, prefix):
        self._plan_counter += 1
        return PlanRequest(self.run_id, f"{self.run_id}:{prefix}:plan:{self._plan_counter}",
                           agent.agent_id, agent.kind.upper(), agent.position, goal, return_to,
                           require_return, mode, self.map_version, duration,
                           budgets.time_s, budgets.energy_wh, budgets.oxygen_l,
                           budgets.reserve_time_s, budgets.reserve_wh, budgets.reserve_oxygen_l,
                           self._revisions[agent.agent_id], activity)

    def _schedule_plan(self, cause, state):
        if self._goal is None or self.map_version is None:
            return
        agent = self._agents[self._goal.primary_agent_id]
        goal = self._goal
        returning = self._return_requested or self._facts["primary_goal_completed"]
        budgets = self._remaining_primary_budgets()
        reason = self._budget_reason(agent.kind, budgets, agent)
        if reason:
            self.block_runtime(reason)
            return
        self._pending = self._make_plan(agent, self.base if returning else goal.goal,
                                       self.base, not returning, budgets, goal.mode,
                                       0.0 if returning else self.primary_service_time_s,
                                       "wait" if returning else self.primary_service_activity,
                                       "return" if returning else "primary")
        self._state_to("RETURNING" if returning else state, cause)

    def _remaining_primary_budgets(self):
        goal, origin = self._goal, self._allocation_origin
        agent = self._agents[goal.primary_agent_id]
        return Budgets(goal.time_budget_s - (origin.time_remaining_s - agent.time_remaining_s),
                       goal.energy_budget_wh - (origin.energy_remaining_wh - agent.energy_remaining_wh),
                       goal.oxygen_budget_l - (origin.oxygen_remaining_l - agent.oxygen_remaining_l),
                       goal.reserve_time_s, goal.reserve_wh, goal.reserve_oxygen_l)

    def _continuation_reason(self):
        """Audit remaining declared polyline; an off-route pose requires replanning.

        This never projects/snaps an off-route pose onto a safe corridor. The
        remaining service duration is counted in full until explicit completion.
        """
        request, route = self._route_request, self._route
        agent = self._agents[request.agent_id]
        path = route.outbound_path
        suffix = None
        for index, (a, b) in enumerate(zip(path, path[1:])):
            if _on_segment(agent.position, a, b):
                suffix = (agent.position, *path[index + 1:])
                break
        if len(path) == 1 and _near(agent.position, path[0]):
            suffix = (agent.position,)
        if suffix is None:
            return "OFF_ROUTE"
        profile = self.profiles[request.agent_id]
        try:
            parts = [estimate_segment(profile, a.coordinates(), b.coordinates())
                     for route_path in (suffix, route.return_path)
                     for a, b in zip(route_path, route_path[1:])]
            parts.append(estimate_activity(profile, request.service_activity, request.service_time_s))
        except (ValueError, TypeError, KeyError, OverflowError):
            return "MODEL_INPUT_INVALID"
        budget = self._remaining_primary_budgets()
        if (sum(p.time_s for p in parts) + budget.reserve_time_s > budget.time_s
                or sum(p.energy_wh for p in parts) + budget.reserve_wh > budget.energy_wh
                or sum(p.oxygen_l for p in parts) + budget.reserve_oxygen_l > budget.oxygen_l):
            return "RETURN_BUDGET_AT_RISK"
        return ""

    def pending_plan(self):
        return self._pending

    def refresh_pending_resources(self):
        """Refresh a pre-search context after its acknowledgement, if needed.

        Telemetry does not invalidate an already dispatched search on every
        stationary clock/resource tick. Its candidate is independently checked
        against current resources by apply_plan.
        """
        request = self._pending
        if request is None or self._route is not None:
            return False
        budgets = self._remaining_primary_budgets()
        before = (request.time_budget_s, request.energy_budget_wh, request.oxygen_budget_l)
        current = (budgets.time_s, budgets.energy_wh, budgets.oxygen_l)
        if before == current:
            return False
        self._schedule_plan(request.request_id, "REPLAN")
        return True

    def _audit(self, request, decision):
        if (decision.run_id != self.run_id or decision.map_version_used != self.map_version
                or request.map_version != self.map_version):
            return "STALE_MAP"
        if request.state_revision != self._revisions.get(request.agent_id):
            return "START_STATE_CHANGED"
        if (decision.request_id != request.request_id or decision.agent_id != request.agent_id
                or decision.mode != request.mode):
            return "RESPONSE_MISMATCH"
        if decision.status not in _STATUSES:
            return "INVALID_ROUTE_STATUS"
        if decision.status != "FEASIBLE":
            return decision.reason_code or decision.status
        if not self.planner_model_agreed:
            return "MODEL_NOT_AGREED"
        profile = self.profiles[request.agent_id]
        if self._profile_reason(profile):
            return self._profile_reason(profile)
        if not decision.route_id or not _number(decision.min_clearance_m):
            return "INVALID_ROUTE"
        if decision.route_id in self._used_route_ids:
            return "ROUTE_ID_REUSED"
        outbound, back = decision.outbound_path, decision.return_path
        if (not outbound or not all(_point(p) for p in (*outbound, *back))
                or not _near(outbound[0], request.start) or not _near(outbound[-1], request.goal)):
            return "INVALID_ROUTE_ENDPOINTS"
        if request.require_return:
            if not back or not _near(back[0], request.goal) or not _near(back[-1], request.return_to):
                return "RETURN_PATH_REQUIRED"
        elif back:
            return "UNEXPECTED_RETURN_PATH"
        try:
            segments = [estimate_segment(profile, a.coordinates(), b.coordinates())
                        for path in (outbound, back) for a, b in zip(path, path[1:])]
            segments.append(estimate_activity(profile, request.service_activity, request.service_time_s))
            time_s = sum(s.time_s for s in segments)
            energy_wh = sum(s.energy_wh for s in segments)
            oxygen_l = sum(s.oxygen_l for s in segments) if profile.kind == "human" else None
        except (ValueError, TypeError, KeyError, OverflowError):
            return "MODEL_INPUT_INVALID"
        agent = self._agents[request.agent_id]
        remaining = (self._remaining_primary_budgets() if request.agent_id == self._goal.primary_agent_id
                     else Budgets(agent.time_remaining_s, agent.energy_remaining_wh,
                                  agent.oxygen_remaining_l, request.reserve_time_s,
                                  request.reserve_wh, request.reserve_oxygen_l))
        limits = [(time_s, request.time_budget_s, request.reserve_time_s, remaining.time_s),
                  (energy_wh, request.energy_budget_wh, request.reserve_wh, remaining.energy_wh)]
        if profile.kind == "human":
            limits.append((oxygen_l, request.oxygen_budget_l, request.reserve_oxygen_l, remaining.oxygen_l))
        if any(cost + reserve > min(available, current) for cost, available, reserve, current in limits):
            return "INSUFFICIENT_BUDGET"
        expected = [(decision.travel_time_s, time_s), (decision.energy_est_wh, energy_wh),
                    (decision.reserve_time_s, request.time_budget_s - time_s),
                    (decision.reserve_wh, request.energy_budget_wh - energy_wh)]
        if profile.kind == "human":
            expected += [(decision.oxygen_est_l, oxygen_l),
                         (decision.reserve_oxygen_l, request.oxygen_budget_l - oxygen_l)]
        elif decision.oxygen_est_l is not None or decision.reserve_oxygen_l is not None:
            return "OXYGEN_NOT_APPLICABLE"
        if any(not _number(actual) or not isclose(actual, value, rel_tol=1e-5, abs_tol=1e-3)
               for actual, value in expected):
            return "MODEL_MISMATCH"
        return ""

    def _with_current_reserves(self, request, decision):
        agent = self._agents[request.agent_id]
        if request.agent_id == self._goal.primary_agent_id:
            budget = self._remaining_primary_budgets()
        else:
            budget = Budgets(agent.time_remaining_s, agent.energy_remaining_wh,
                             agent.oxygen_remaining_l, request.reserve_time_s,
                             request.reserve_wh, request.reserve_oxygen_l)
        return replace(decision,
                       reserve_time_s=min(request.time_budget_s, budget.time_s) - decision.travel_time_s,
                       reserve_wh=min(request.energy_budget_wh, budget.energy_wh) - decision.energy_est_wh,
                       reserve_oxygen_l=(min(request.oxygen_budget_l, budget.oxygen_l) - decision.oxygen_est_l
                                         if agent.kind == "human" else None))

    def apply_plan(self, decision):
        if self._pending is None or decision.request_id != self._pending.request_id or decision.run_id != self.run_id:
            self._emit("ERROR", decision.request_id, reason="STALE_RESPONSE", detail="Unrequested candidate discarded.")
            return False
        request = self._pending
        reason = self._audit(request, decision)
        self._pending = None
        if reason:
            self._clear_route(decision.request_id, reason)
            self._state_to("BLOCKED", decision.request_id, reason, decision.detail)
            return False
        self._route = self._with_current_reserves(request, decision)
        self._route_request = request
        self._reset_return_evidence()
        self._used_route_ids.add(decision.route_id)
        returning = self._return_requested or self._facts["primary_goal_completed"]
        self._active_task_id, self._active_task_kind = ("return", "return") if returning else ("primary", "primary")
        self._active_task_state = "ASSIGNED"
        self._emit("ROUTE_PUBLISHED", decision.request_id, agent_id=decision.agent_id)
        self._state_to("RETURNING" if returning else "READY", decision.request_id)
        return True

    def fail_pending_plan(self, reason, detail=""):
        if self._pending:
            cause = self._pending.request_id
            self._pending = None
            self._clear_route(cause, reason)
            self._state_to("BLOCKED", cause, reason, detail)

    def block_runtime(self, reason, detail=""):
        self._pending = None
        self._optional.clear()
        self._clear_route(reason, reason)
        self._state_to("BLOCKED", reason, reason, detail)

    def request_return(self, reason="RETURN_PRIORITY"):
        if self._goal is None or self._state in _TERMINAL:
            return False
        self._return_requested = True
        self._optional.clear()
        for task_id, task in tuple(self._tasks.items()):
            if task.state in {"ELIGIBLE", "ASSIGNED", "EXECUTING"}:
                self._task_to(task_id, "BLOCKED", reason, reason)
        self._clear_route(reason, reason)
        self._active_task_id, self._active_task_kind, self._active_task_state = "return", "return", "ELIGIBLE"
        self._schedule_plan(reason, "RETURNING")
        return True

    def record_evidence(self, evidence):
        cached = self._evidence.get(evidence.evidence_id)
        if cached:
            return cached == evidence
        if (not evidence.evidence_id or evidence.run_id != self.run_id or self._route is None
                or evidence.route_id != self._route.route_id or evidence.map_version != self.map_version
                or not _number(evidence.timestamp_sim_s) or evidence.timestamp_sim_s < (self._clock or 0)):
            return False
        provided = {k: getattr(evidence, k) for k in self._facts if getattr(evidence, k) is not None}
        if not provided or any(type(value) is not bool for value in provided.values()):
            return False
        agent = self._agents[self._goal.primary_agent_id]
        if (provided.get("primary_goal_completed") and not self._facts["primary_goal_completed"]
                and not _near(agent.position, self._goal.goal, self.return_tolerance_m)):
            return False
        if provided.get("returned_to_base_within_tolerance"):
            if not ((provided.get("primary_goal_completed", self._facts["primary_goal_completed"])
                     or self._return_requested)
                    and _near(agent.position, self.base, self.return_tolerance_m)):
                return False
        if provided.get("verified_ground_traversal_under_model"):
            if not (provided.get("returned_to_base_within_tolerance", self._facts["returned_to_base_within_tolerance"])
                    and _near(agent.position, self.base, self.return_tolerance_m)):
                return False  # Global evidence cannot verify future, untraversed legs.
        self._evidence[evidence.evidence_id] = evidence
        self._clock = evidence.timestamp_sim_s
        primary_just_completed = not self._facts["primary_goal_completed"] and provided.get("primary_goal_completed")
        self._facts.update(provided)
        if primary_just_completed:
            self._emit("TASK_STATE_CHANGED", evidence.evidence_id, task_id="primary",
                       previous=self._active_task_state, new="DONE")
        elif provided.get("returned_to_base_within_tolerance"):
            self._emit("TASK_STATE_CHANGED", evidence.evidence_id, task_id="return",
                       previous=self._active_task_state, new="DONE")
        else:
            self._emit("MISSION_STATE_CHANGED", evidence.evidence_id,
                       previous=self._state, new=self._state, reason="EVIDENCE_RECORDED")
        if provided.get("no_budget_violation") is False:
            self._pending = None
            self._clear_route(evidence.evidence_id, "BUDGET_VIOLATION")
            self._state_to("ABORTED", evidence.evidence_id, "BUDGET_VIOLATION")
        elif self._facts["returned_to_base_within_tolerance"] and not self._facts["primary_goal_completed"]:
            self._pending = None
            self._clear_route(evidence.evidence_id, "PRIMARY_INCOMPLETE")
            self._state_to("ABORTED", evidence.evidence_id, "PRIMARY_INCOMPLETE")
        elif mission_success(**self._facts):
            self._clear_route(evidence.evidence_id, "MISSION_COMPLETE")
            self._active_task_state = "DONE"
            self._state_to("COMPLETE", evidence.evidence_id)
        elif self._facts["primary_goal_completed"]:
            if primary_just_completed:
                self._clear_route(evidence.evidence_id, "PRIMARY_COMPLETE")
                self._active_task_id, self._active_task_kind, self._active_task_state = "return", "return", "ELIGIBLE"
                self._schedule_plan(evidence.evidence_id, "RETURNING")
            else:
                self._state_to("RETURNING", evidence.evidence_id)
        return True

    def discover_task(self, task):
        old = self._tasks.get(task.task_id)
        if old:
            return old.task == task
        observer = self.profiles.get(task.observer_id)
        if (not task.task_id or task.task_id in {"primary", "return"}
                or not task.discovery_id or task.run_id != self.run_id
                or task.map_version != self.map_version or task.source_kind != "SIMULATED"
                or observer is None or "observe" not in observer.capabilities
                or task.observer_id not in self._agents
                or task.kind not in {"inspect", "sample"} or not _point(task.position)
                or not _number(task.duration_s) or task.discovery_id in self._discoveries):
            return False
        self._discoveries[task.discovery_id] = task.task_id
        self._tasks[task.task_id] = TaskSnapshot(task, "DISCOVERED")
        self._emit("TASK_DISCOVERED", task.discovery_id, task_id=task.task_id)
        return True

    def _task_to(self, task_id, state, cause, reason="", agent_id=None, route_id=None):
        old = self._tasks[task_id]
        self._tasks[task_id] = replace(old, state=state, reason_code=reason,
                                       agent_id=old.agent_id if agent_id is None else agent_id,
                                       route_id=old.route_id if route_id is None else route_id)
        self._emit("TASK_STATE_CHANGED", cause, task_id=task_id, agent_id=agent_id or old.agent_id,
                   route_id=route_id or old.route_id, previous=old.state, new=state, reason=reason)

    def prepare_optional(self, task_id, agent_id, budgets: Budgets):
        record, agent, profile = self._tasks.get(task_id), self._agents.get(agent_id), self.profiles.get(agent_id)
        reason = ""
        if record is None or agent is None or profile is None:
            return None
        task = record.task
        if self._return_requested or self._state in _TERMINAL or self._goal is None:
            reason = "RETURN_PRIORITY"
        elif record.state in {"ASSIGNED", "EXECUTING", "DONE"}:
            return None
        elif task.map_version != self.map_version:
            reason = "STALE_MAP"
        elif task.kind not in profile.capabilities:
            reason = "CAPABILITY_MISMATCH"
        elif self._profile_reason(profile):
            reason = self._profile_reason(profile)
        elif task.kind == "sample" and (profile.kind != "human" or not self._facts["primary_goal_completed"]):
            reason = "PRIMARY_NOT_COMPLETE"
        elif task.kind == "sample" and (not task.predecessor_id or task.predecessor_id not in self._tasks
                or self._tasks[task.predecessor_id].task.kind != "inspect"
                or self._tasks[task.predecessor_id].state != "DONE"
                or not _near(self._tasks[task.predecessor_id].task.position, task.position, self.return_tolerance_m)):
            reason = "PRECEDENCE_NOT_MET"
        elif profile.kind == "human" and not self._facts["primary_goal_completed"]:
            reason = "PRIMARY_NOT_COMPLETE"
        else:
            reason = self._budget_reason(profile.kind, budgets, agent)
            if not reason and profile.kind == "human":
                remaining = self._remaining_primary_budgets()
                if (budgets.reserve_time_s < self._goal.reserve_time_s
                        or budgets.reserve_wh < self._goal.reserve_wh
                        or budgets.reserve_oxygen_l < self._goal.reserve_oxygen_l):
                    reason = "RESERVE_REQUIREMENT_REDUCED"
                elif (budgets.time_s > remaining.time_s or budgets.energy_wh > remaining.energy_wh
                        or budgets.oxygen_l > remaining.oxygen_l):
                    reason = "BUDGET_EXCEEDS_REMAINING"
        if reason:
            self._task_to(task_id, "REJECTED", task.discovery_id, reason)
            return None
        self._task_to(task_id, "ELIGIBLE", task.discovery_id)
        request = self._make_plan(agent, task.position,
                                  self.base if profile.kind == "human" else agent.position,
                                  True, budgets, self._goal.mode, task.duration_s, task.kind, task_id)
        self._optional = {k: v for k, v in self._optional.items() if v[1] != task_id}
        self._optional[request.request_id] = (request, task_id)
        return request

    def assign_optional_task(self, task_id, feasibility):
        stored = self._optional.pop(feasibility.request_id, None)
        if stored is None or stored[1] != task_id:
            return False
        if self._tasks[task_id].state != "ELIGIBLE":
            return False
        request, _ = stored
        reason = "RETURN_PRIORITY" if self._return_requested else self._audit(request, feasibility)
        if reason:
            self._task_to(task_id, "REJECTED", request.request_id, reason)
            return False
        self._used_route_ids.add(feasibility.route_id)
        if self.profiles[request.agent_id].kind == "human":
            self._pending = None
            self._clear_route(request.request_id, "OPTIONAL_TASK_ASSIGNED")
            self._route = self._with_current_reserves(request, feasibility)
            self._route_request = request
            self._reset_return_evidence()
            self._active_task_id, self._active_task_kind, self._active_task_state = task_id, self._tasks[task_id].task.kind, "ASSIGNED"
            self._emit("ROUTE_PUBLISHED", request.request_id, task_id=task_id, agent_id=request.agent_id)
            self._state_to("READY", request.request_id)
        self._task_to(task_id, "ASSIGNED", request.request_id, agent_id=request.agent_id, route_id=feasibility.route_id)
        return True

    def start_task(self, evidence):
        return self._task_evidence(evidence, "ASSIGNED", "EXECUTING")

    def complete_task(self, evidence):
        return self._task_evidence(evidence, "EXECUTING", "DONE")

    def _task_evidence(self, evidence, previous, new):
        cached = self._evidence.get(evidence.evidence_id)
        if cached:
            return cached == evidence
        task = self._tasks.get(evidence.task_id)
        if (not evidence.evidence_id or task is None or task.state != previous
                or evidence.run_id != self.run_id or evidence.map_version != self.map_version
                or evidence.route_id != task.route_id or not _number(evidence.timestamp_sim_s)
                or evidence.timestamp_sim_s < (self._clock or 0)
                or not _near(self._agents[task.agent_id].position, task.task.position, self.return_tolerance_m)):
            return False
        self._clock = evidence.timestamp_sim_s
        self._evidence[evidence.evidence_id] = evidence
        self._task_to(evidence.task_id, new, evidence.evidence_id)
        if task.agent_id == (self._goal.primary_agent_id if self._goal else "") and new == "DONE":
            self.request_return("OPTIONAL_TASK_COMPLETE")
        return True

    def snapshot(self):
        return MissionSnapshot(self.run_id, self._state, self._reason, self._detail, self.base,
                               self._goal.goal if self._goal else None,
                               self._goal.primary_agent_id if self._goal else "",
                               self._active_task_id, self._active_task_kind, self._active_task_state,
                               self.map_version, self._route.route_id if self._route else "", self._route,
                               tuple(self._agents[k] for k in sorted(self._agents)), self._seq,
                               self._clock, mission_success(**self._facts),
                               tuple(self._tasks[k] for k in sorted(self._tasks)))

    def drain_events(self):
        result = tuple(self._events)
        self._events.clear()
        return result
