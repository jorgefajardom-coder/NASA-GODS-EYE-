"""Mission vocabulary, strict success criterion and optional allocation facade."""

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
    """Delegate to the authoritative manager; never allocate from a bare snapshot.

    ``discovered_task`` is the previously registered task ID. Call
    ``prepare_optional`` first to obtain the matching planner request.
    """
    allocator = getattr(mission_state, "assign_optional_task", None)
    if allocator is None:
        raise TypeError("optional allocation requires an authoritative MissionManager")
    return allocator(discovered_task, feasibility)
