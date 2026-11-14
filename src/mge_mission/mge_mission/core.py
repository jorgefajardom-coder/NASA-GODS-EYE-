"""Mission vocabulary and success criterion; no mission authority is running yet."""

from enum import Enum


class MissionStatus(str, Enum):
    IDLE = "IDLE"
    PLANNING = "PLANNING"
    READY = "READY"
    ACTIVE = "ACTIVE"
    REPLAN = "REPLAN"
    RETURNING = "RETURNING"
    COMPLETE = "COMPLETE"
    BLOCKED = "BLOCKED"
    ABORTED = "ABORTED"


class TaskStatus(str, Enum):
    DISCOVERED = "DISCOVERED"
    ELIGIBLE = "ELIGIBLE"
    ASSIGNED = "ASSIGNED"
    EXECUTING = "EXECUTING"
    DONE = "DONE"
    REJECTED = "REJECTED"
    BLOCKED = "BLOCKED"


def mission_success(*, primary_goal_completed: bool,
                    returned_to_base_within_tolerance: bool,
                    verified_ground_traversal_under_model: bool,
                    no_budget_violation: bool) -> bool:
    """Guide criterion only; callers must provide actual verified evidence."""
    checks = (primary_goal_completed, returned_to_base_within_tolerance,
              verified_ground_traversal_under_model, no_budget_violation)
    if any(type(value) is not bool for value in checks):
        raise TypeError("mission success requires four explicit boolean evidence checks")
    return all(checks)


def assign_optional_task(*, mission_state, discovered_task, feasibility):
    """Pending: precedences, capability, incremental costs, primary goal and return."""
    raise NotImplementedError("David and Jesus must implement mission task authority")
