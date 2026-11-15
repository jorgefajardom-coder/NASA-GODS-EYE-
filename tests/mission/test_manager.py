"""Synthetic authority scenarios; these are not simulated mission acceptance runs."""

from dataclasses import FrozenInstanceError, replace
from pathlib import Path

import pytest

from mge_mission.core import assign_optional_task
from mge_mission.manager import MissionManager
from mge_mission.models import estimate_activity, estimate_segment, load_profiles
from mge_mission.types import (AgentSnapshot, Budgets, GoalRequest, MissionEvidence,
                               MissionSpec, ObservedTask, Point, RouteDecision, TaskEvidence)

A, B = Point(0.5, 0.5), Point(2.5, 0.5)


@pytest.fixture
def profiles():
    path = Path(__file__).resolve().parents[2] / "config/science_profiles.proposed.json"
    return {key: replace(value, approval_status="illustrative")
            for key, value in load_profiles(path).items()}


def agent(agent_id="human_1", kind="human", position=A, stamp=0.0):
    return AgentSnapshot("test-run", agent_id, kind, position, 1000.0, 1000.0,
                         500.0 if kind == "human" else None, timestamp_sim_s=stamp)


def goal(**changes):
    result = GoalRequest("goal-1", "test-run", "human_1", A, B, "FAST",
                         1000.0, 1000.0, 500.0, 100.0, 50.0, 10.0)
    return replace(result, **changes)


@pytest.fixture
def manager(profiles):
    result = MissionManager("test-run", profiles, A, 0.01, allow_illustrative=True,
                            primary_service_time_s=10, planner_model_agreed=True)
    assert result.update_map("test-run", 1, 0)
    for agent_id, kind in (("human_1", "human"), ("rover_1", "rover"), ("drone_1", "drone")):
        assert result.update_agent(agent(agent_id, kind))
    return result


def feasible(request, profiles, route_id="route-1", outbound=None, back=None):
    outbound = (request.start, request.goal) if outbound is None else tuple(outbound)
    back = ((request.goal, request.return_to) if request.require_return else ()) if back is None else tuple(back)
    profile = profiles[request.agent_id]
    parts = [estimate_segment(profile, a.coordinates(), b.coordinates())
             for path in (outbound, back) for a, b in zip(path, path[1:])]
    parts.append(estimate_activity(profile, request.service_activity, request.service_time_s))
    time_s, energy = sum(p.time_s for p in parts), sum(p.energy_wh for p in parts)
    oxygen = sum(p.oxygen_l for p in parts) if profile.kind == "human" else None
    return RouteDecision(request.run_id, request.request_id, route_id, request.agent_id,
                         request.mode, request.map_version, "FEASIBLE", outbound_path=outbound,
                         return_path=back, travel_time_s=time_s, energy_est_wh=energy,
                         oxygen_est_l=oxygen, min_clearance_m=1,
                         reserve_time_s=request.time_budget_s-time_s,
                         reserve_wh=request.energy_budget_wh-energy,
                         reserve_oxygen_l=request.oxygen_budget_l-oxygen if oxygen is not None else None)


def ready(manager, profiles):
    assert manager.set_goal(goal()).accepted
    response = feasible(manager.pending_plan(), profiles)
    assert manager.apply_plan(response)
    return response


def primary_done(manager, route):
    assert manager.update_agent(agent(position=B, stamp=1))
    evidence = MissionEvidence("primary-complete", "test-run", 1, route.route_id, 1,
                               primary_goal_completed=True)
    assert manager.record_evidence(evidence)
    return evidence


def discover(manager, kind="inspect", task_id="inspect-1", predecessor_id="", position=A):
    task = ObservedTask(task_id, "test-run", 1, f"discovery-{task_id}", "drone_1",
                        kind, position, 5, predecessor_id)
    assert manager.discover_task(task)
    return task


def budget(kind="human"):
    return Budgets(900, 900, 450 if kind == "human" else None,
                   100, 50, 10 if kind == "human" else None)


def test_accepted_goal_is_idempotent_and_does_not_complete(manager, profiles):
    first = manager.set_goal(goal())
    request = manager.pending_plan()
    count = manager.snapshot().last_event_seq
    assert manager.set_goal(goal()) == first
    assert manager.pending_plan() == request
    assert manager.snapshot().last_event_seq == count
    assert manager.apply_plan(feasible(request, profiles))
    snapshot = manager.snapshot()
    assert snapshot.mission_state == "READY"
    assert snapshot.mission_success is False
    assert snapshot.active_route.agent_id == "human_1"
    with pytest.raises(FrozenInstanceError):
        snapshot.mission_state = "COMPLETE"


def test_pending_context_refreshes_remaining_resources_without_pose_change(manager):
    assert manager.set_goal(goal()).accepted
    first = manager.pending_plan()
    assert manager.update_agent(replace(agent(stamp=1), time_remaining_s=990., energy_remaining_wh=995.,
                                        oxygen_remaining_l=499.))
    assert manager.pending_plan() == first
    assert manager.refresh_pending_resources()
    refreshed = manager.pending_plan()
    assert refreshed.request_id != first.request_id
    assert refreshed.start == first.start and refreshed.state_revision == first.state_revision
    assert (refreshed.time_budget_s, refreshed.energy_budget_wh, refreshed.oxygen_budget_l) == (990., 995., 499.)
    assert manager.update_agent(replace(agent(stamp=2), time_remaining_s=990., energy_remaining_wh=995.,
                                        oxygen_remaining_l=499.))
    assert manager.pending_plan() == refreshed  # Timestamp-only telemetry is not a new budget snapshot.
    assert not manager.refresh_pending_resources()


def test_conflicting_id_cannot_change_goal(manager):
    assert manager.set_goal(goal()).accepted
    assert manager.set_goal(goal(goal=A)).reason_code == "REQUEST_ID_CONFLICT"
    assert manager.snapshot().primary_goal == B


@pytest.mark.parametrize("changes,reason", [
    ({"run_id": "other"}, "WRONG_RUN"),
    ({"base": B}, "INVALID_POSITION"),
    ({"goal": Point(float("nan"), 0)}, "INVALID_POSITION"),
    ({"time_budget_s": 1001}, "BUDGET_EXCEEDS_REMAINING"),
    ({"reserve_wh": 1001}, "INVALID_RESERVE"),
    ({"oxygen_budget_l": None}, "INVALID_OXYGEN_BUDGET"),
    ({"oxygen_budget_l": float("nan")}, "INVALID_OXYGEN_BUDGET"),
    ({"mode": "UNSUPPORTED"}, "MODE_NOT_SUPPORTED"),
    ({"primary_agent_id": "rover_1"}, "PRIMARY_AGENT_UNSUPPORTED"),
])
def test_goal_validation_preserves_inactive_authority(manager, changes, reason):
    response = manager.set_goal(goal(**changes))
    assert not response.accepted
    assert response.reason_code == reason
    assert manager.pending_plan() is None
    assert manager.snapshot().route_id == ""


def test_empty_run_id_resolves_current_run(manager):
    assert manager.set_goal(goal(run_id="")).accepted
    assert manager.pending_plan().run_id == "test-run"


def test_profile_and_model_approval_are_separate_gates(profiles):
    proposed = {key: replace(value, approval_status="proposed") for key, value in profiles.items()}
    m = MissionManager("test-run", proposed, A, 0.01, allow_illustrative=True)
    m.update_map("test-run", 1)
    m.update_agent(agent())
    assert m.set_goal(goal()).reason_code == "PROFILE_NOT_APPROVED"
    approved = {key: replace(value, approval_status="approved") for key, value in profiles.items()}
    m = MissionManager("test-run", approved, A, 0.01)
    m.update_map("test-run", 1)
    m.update_agent(agent())
    assert m.set_goal(goal()).reason_code == "MODEL_NOT_APPROVED"


def test_model_agreement_is_explicit(manager, profiles):
    manager.planner_model_agreed = False
    manager.set_goal(goal())
    assert not manager.apply_plan(feasible(manager.pending_plan(), profiles))
    assert manager.snapshot().reason_code == "MODEL_NOT_AGREED"


@pytest.mark.parametrize("status", ["UNKNOWN", "NO_PATH", "INSUFFICIENT_BUDGET", "STALE_MAP", "ERROR"])
def test_planner_failures_are_distinct_and_never_publish(manager, status):
    manager.set_goal(goal())
    request = manager.pending_plan()
    result = RouteDecision("test-run", request.request_id, "", "human_1", "FAST", 1, status,
                           reason_code="NON_CELL_CENTER" if status == "ERROR" else status)
    assert not manager.apply_plan(result)
    assert manager.snapshot().reason_code == ("NON_CELL_CENTER" if status == "ERROR" else status)
    assert manager.snapshot().route_id == ""


def test_no_silent_pose_snapping_and_delayed_response_cannot_win(manager, profiles):
    manager.set_goal(goal())
    old = manager.pending_plan()
    moving = agent(position=Point(0.6, 0.5), stamp=1)
    assert manager.update_agent(moving)
    fresh = manager.pending_plan()
    assert fresh.start == moving.position
    assert fresh.request_id != old.request_id
    assert not manager.apply_plan(feasible(old, profiles))
    assert manager.pending_plan() == fresh
    assert manager.snapshot().route_id == ""


def test_map_change_clears_route_replans_latest_pose_and_ignores_old_response(manager, profiles):
    route = ready(manager, profiles)
    assert manager.update_agent(agent(position=Point(1.5, 0.5), stamp=1))
    assert manager.update_map("test-run", 2, 2)
    assert manager.snapshot().active_route is None
    assert manager.pending_plan().start == Point(1.5, 0.5)
    assert manager.pending_plan().map_version == 2
    assert not manager.apply_plan(route)
    assert manager.pending_plan().map_version == 2
    assert not manager.update_map("test-run", 1)
    assert not manager.update_map("other", 3)


def test_current_resource_change_supersedes_pending_and_forbids_replenishment(manager, profiles):
    manager.set_goal(goal())
    old = manager.pending_plan()
    reduced = replace(agent(stamp=1), energy_remaining_wh=900)
    assert manager.update_agent(reduced)
    assert manager.pending_plan() == old
    assert manager.apply_plan(feasible(old, profiles))
    assert manager.snapshot().active_route.reserve_wh < 900
    assert not manager.update_agent(agent(stamp=2))
    current = next(a for a in manager.snapshot().agents if a.agent_id == "human_1")
    assert current.energy_remaining_wh == 900


def test_replanning_subtracts_consumption_from_allocated_budget(manager):
    assert manager.set_goal(goal(time_budget_s=600, energy_budget_wh=600, oxygen_budget_l=300)).accepted
    reduced = replace(agent(stamp=1), time_remaining_s=900, energy_remaining_wh=900, oxygen_remaining_l=450)
    assert manager.update_agent(reduced)
    manager.update_map("test-run", 2, 1)
    request = manager.pending_plan()
    assert (request.time_budget_s, request.energy_budget_wh, request.oxygen_budget_l) == (500, 500, 250)


def test_stationary_periodic_resource_updates_do_not_starve_planner(manager, profiles):
    manager.set_goal(goal())
    request = manager.pending_plan()
    for tick in range(1, 6):
        current = replace(agent(stamp=tick), time_remaining_s=1000-tick,
                          energy_remaining_wh=1000-tick/100)
        assert manager.update_agent(current)
        assert manager.pending_plan().request_id == request.request_id
    assert manager.apply_plan(feasible(request, profiles))


def test_pending_candidate_rechecks_material_stationary_budget_loss(manager, profiles):
    manager.set_goal(goal(energy_budget_wh=100))
    request = manager.pending_plan()
    candidate = feasible(request, profiles)
    # Allocation left is 50.01 Wh, above reserve but below route + reserve.
    assert manager.update_agent(replace(agent(stamp=1), energy_remaining_wh=950.01))
    assert manager.pending_plan() == request
    assert not manager.apply_plan(candidate)
    assert manager.snapshot().reason_code == "INSUFFICIENT_BUDGET"


def test_active_budget_deterioration_requests_return_before_reserve_breach(manager, profiles):
    manager.set_goal(goal(energy_budget_wh=100))
    candidate = feasible(manager.pending_plan(), profiles)
    assert manager.apply_plan(candidate)
    remaining_allocation = 50 + candidate.energy_est_wh - 0.001
    current = replace(agent(stamp=1), energy_remaining_wh=900 + remaining_allocation)
    assert manager.update_agent(current)
    assert remaining_allocation > 50
    assert manager.snapshot().mission_state == "RETURNING"
    assert manager.snapshot().route_id == ""
    assert manager.pending_plan().start == A and manager.pending_plan().goal == A
    assert manager.pending_plan().require_return is False


def test_off_route_movement_invalidates_path_without_snapping(manager, profiles):
    ready(manager, profiles)
    current = agent(position=Point(1.5, 0.6), stamp=1)
    assert manager.update_agent(current)
    assert manager.snapshot().active_route is None
    assert manager.pending_plan().start == current.position
    assert manager.pending_plan().goal == B


def test_primary_service_activity_is_selected_explicitly(manager, profiles):
    manager.primary_service_activity = "sample"
    manager.set_goal(goal())
    request = manager.pending_plan()
    assert request.service_activity == "sample"
    candidate = feasible(request, profiles)
    assert manager.apply_plan(candidate)


def test_immutable_spec_constructs_manager_and_rejects_invalid_frame(profiles):
    spec = MissionSpec("test-run", A, 0.01, 60, "sample")
    authority = MissionManager.from_spec(spec, profiles, allow_illustrative=True)
    assert authority.spec == spec
    with pytest.raises(ValueError):
        MissionSpec("test-run", A, 1, frame_id="earth")
    with pytest.raises(FrozenInstanceError):
        spec.primary_service_time_s = 0


def test_reserve_violation_aborts_without_fabricating_return(manager, profiles):
    ready(manager, profiles)
    reduced = replace(agent(stamp=1), energy_remaining_wh=49)
    assert manager.update_agent(reduced)
    assert manager.snapshot().mission_state == "ABORTED"
    assert manager.snapshot().reason_code == "RESERVE_VIOLATION"
    assert manager.snapshot().route_id == ""
    assert manager.snapshot().mission_success is False


@pytest.mark.parametrize("changes,reason", [
    ({"energy_est_wh": 200}, "MODEL_MISMATCH"),
    ({"reserve_wh": 0}, "MODEL_MISMATCH"),
    ({"oxygen_est_l": None}, "MODEL_MISMATCH"),
    ({"return_path": ()}, "RETURN_PATH_REQUIRED"),
    ({"outbound_path": (B, A)}, "INVALID_ROUTE_ENDPOINTS"),
    ({"agent_id": "rover_1"}, "RESPONSE_MISMATCH"),
    ({"min_clearance_m": float("nan")}, "INVALID_ROUTE"),
    ({"map_version_used": 0}, "STALE_MAP"),
])
def test_candidate_audit_is_independent_and_fail_closed(manager, profiles, changes, reason):
    manager.set_goal(goal())
    candidate = replace(feasible(manager.pending_plan(), profiles), **changes)
    assert not manager.apply_plan(candidate)
    assert manager.snapshot().reason_code == reason
    assert manager.snapshot().route_id == ""


def test_float32_estimate_tolerance_does_not_weaken_full_precision_budget(manager, profiles):
    manager.set_goal(goal())
    candidate = feasible(manager.pending_plan(), profiles)
    assert manager.apply_plan(replace(candidate, energy_est_wh=candidate.energy_est_wh + 0.0005))
    # A separately recomputed complete trip costs more than the tiny energy budget.
    other = MissionManager("test-run", profiles, A, 0.01, allow_illustrative=True,
                           planner_model_agreed=True)
    other.update_map("test-run", 1)
    other.update_agent(agent())
    assert other.set_goal(goal(energy_budget_wh=0.0001, reserve_wh=0)).accepted
    request = other.pending_plan()
    assert not other.apply_plan(feasible(request, profiles))
    assert other.snapshot().reason_code == "INSUFFICIENT_BUDGET"


def test_service_and_return_are_audited_once(manager, profiles):
    manager.set_goal(goal())
    request = manager.pending_plan()
    candidate = feasible(request, profiles)
    assert manager.apply_plan(candidate)
    assert candidate.travel_time_s == pytest.approx(4 / profiles["human_1"].parameters["speed_m_s"] + 10)


def test_explicit_primary_and_verified_return_evidence_are_required(manager, profiles):
    route = ready(manager, profiles)
    wrong_place = MissionEvidence("fake-primary", "test-run", 1, route.route_id, 0,
                                  primary_goal_completed=True)
    assert not manager.record_evidence(wrong_place)
    primary = primary_done(manager, route)
    sequence = manager.snapshot().last_event_seq
    assert manager.record_evidence(primary)
    assert manager.snapshot().last_event_seq == sequence
    assert manager.snapshot().mission_state == "RETURNING"
    assert manager.snapshot().mission_success is False
    assert manager.snapshot().active_route is None
    request = manager.pending_plan()
    assert request.start == B and request.goal == A and not request.require_return
    returning = feasible(request, profiles, "return-route")
    assert manager.apply_plan(returning)
    assert manager.update_agent(agent(position=A, stamp=2))
    final = MissionEvidence("verified-return", "test-run", 1, returning.route_id, 2,
                            True, True, True, True)
    assert manager.record_evidence(final)
    assert manager.snapshot().mission_state == "COMPLETE"
    assert manager.snapshot().mission_success is True
    assert manager.snapshot().route_id == ""


def test_global_traversal_evidence_cannot_verify_a_future_return(manager, profiles):
    route = ready(manager, profiles)
    premature = MissionEvidence("premature-verification", "test-run", 1, route.route_id, 0,
                                verified_ground_traversal_under_model=True)
    assert not manager.record_evidence(premature)
    assert not manager.snapshot().mission_success


def test_commanded_safe_return_before_primary_is_honest_abort(manager, profiles):
    ready(manager, profiles)
    assert manager.request_return()
    returning = feasible(manager.pending_plan(), profiles, "abort-return-route")
    assert manager.apply_plan(returning)
    returned = MissionEvidence("safe-abort-return", "test-run", 1, returning.route_id, 0,
                               returned_to_base_within_tolerance=True,
                               verified_ground_traversal_under_model=True,
                               no_budget_violation=True)
    assert manager.record_evidence(returned)
    assert manager.snapshot().mission_state == "ABORTED"
    assert manager.snapshot().reason_code == "PRIMARY_INCOMPLETE"
    assert manager.snapshot().mission_success is False


@pytest.mark.parametrize("changes", [
    {"run_id": "other"}, {"map_version": 0}, {"route_id": "other-route"},
    {"primary_goal_completed": "true"}, {"timestamp_sim_s": float("nan")},
])
def test_evidence_wrong_context_or_nonboolean_is_rejected(manager, profiles, changes):
    route = ready(manager, profiles)
    primary_done(manager, route)
    returning = feasible(manager.pending_plan(), profiles, "return-route")
    assert manager.apply_plan(returning)
    evidence = MissionEvidence("new-evidence", "test-run", 1, returning.route_id, 1,
                               verified_ground_traversal_under_model=True)
    assert not manager.record_evidence(replace(evidence, **changes))
    assert not manager.snapshot().mission_success


def test_events_are_ordered_causal_and_drained_without_resetting_sequence(manager, profiles):
    ready(manager, profiles)
    events = manager.drain_events()
    assert [e.seq for e in events] == list(range(1, len(events)+1))
    assert len({e.event_id for e in events}) == len(events)
    assert all(e.run_id == "test-run" and e.causality_id for e in events)
    assert manager.drain_events() == ()
    manager.block_runtime("CLOCK_REGRESSION")
    later = manager.drain_events()
    assert later[0].seq == events[-1].seq + 1
    assert manager.snapshot().active_route is None
    assert manager.pending_plan() is None


def test_human_sampling_requires_primary_and_completed_inspection(manager, profiles):
    route = ready(manager, profiles)
    discover(manager, "sample", "sample-1", "inspect-1", B)
    assert manager.prepare_optional("sample-1", "human_1", budget()) is None
    assert manager.snapshot().tasks[0].reason_code == "PRIMARY_NOT_COMPLETE"
    primary_done(manager, route)
    assert manager.prepare_optional("sample-1", "human_1", budget()) is None
    assert manager.snapshot().tasks[0].reason_code == "PRECEDENCE_NOT_MET"


def test_sampling_cannot_reuse_inspection_from_another_site(manager, profiles):
    route = ready(manager, profiles)
    discover(manager, position=A)
    request = manager.prepare_optional("inspect-1", "rover_1", budget("rover"))
    inspect = feasible(request, profiles, "inspect-route")
    assert manager.assign_optional_task("inspect-1", inspect)
    assert manager.start_task(TaskEvidence("inspect-start", "test-run", 1, inspect.route_id, "inspect-1", 0))
    assert manager.complete_task(TaskEvidence("inspect-done", "test-run", 1, inspect.route_id, "inspect-1", 0))
    primary_done(manager, route)
    discover(manager, "sample", "sample-1", "inspect-1", B)
    assert manager.prepare_optional("sample-1", "human_1", budget()) is None
    sample = next(t for t in manager.snapshot().tasks if t.task.task_id == "sample-1")
    assert sample.reason_code == "PRECEDENCE_NOT_MET"


def test_robot_inspection_assignment_and_completion_are_external(manager, profiles):
    ready(manager, profiles)
    task = discover(manager)
    assert manager.discover_task(task)
    request = manager.prepare_optional("inspect-1", "rover_1", budget("rover"))
    candidate = feasible(request, profiles, "inspection-route")
    assert manager.assign_optional_task("inspect-1", candidate)
    assert manager.snapshot().active_route.agent_id == "human_1"
    assert manager.snapshot().tasks[0].state == "ASSIGNED"
    finish = TaskEvidence("inspect-done", "test-run", 1, candidate.route_id, "inspect-1", 0)
    assert not manager.complete_task(finish)
    start = replace(finish, evidence_id="inspect-start")
    assert manager.start_task(start)
    assert manager.complete_task(finish)
    assert manager.complete_task(finish)
    assert manager.snapshot().tasks[0].state == "DONE"
    assert not manager.snapshot().mission_success


def test_optional_human_sampling_after_B_and_inspection_preserves_return(manager, profiles):
    route = ready(manager, profiles)
    discover(manager, position=B)
    request = manager.prepare_optional("inspect-1", "rover_1", budget("rover"))
    decision = feasible(request, profiles, "inspection-route")
    assert manager.assign_optional_task("inspect-1", decision)
    assert manager.update_agent(agent("rover_1", "rover", B, 1))
    assert manager.start_task(TaskEvidence("inspect-start", "test-run", 1, decision.route_id, "inspect-1", 1))
    assert manager.complete_task(TaskEvidence("inspect-done", "test-run", 1, decision.route_id, "inspect-1", 1))
    primary_done(manager, route)
    discover(manager, "sample", "sample-1", "inspect-1", B)
    request = manager.prepare_optional("sample-1", "human_1", budget())
    assert request.goal == B and request.return_to == A and request.require_return
    decision = feasible(request, profiles, "sample-route")
    assert assign_optional_task(mission_state=manager, discovered_task="sample-1", feasibility=decision)
    assert manager.snapshot().active_route.route_id == "sample-route"
    assert manager.start_task(TaskEvidence("sample-start", "test-run", 1, decision.route_id, "sample-1", 1))
    assert manager.complete_task(TaskEvidence("sample-done", "test-run", 1, decision.route_id, "sample-1", 1))
    assert manager.snapshot().mission_state == "RETURNING"
    assert manager.pending_plan().goal == A
    assert manager.pending_plan().service_time_s == 0
    assert not manager.snapshot().mission_success


def test_return_priority_cancels_optional_work(manager, profiles):
    ready(manager, profiles)
    discover(manager)
    request = manager.prepare_optional("inspect-1", "rover_1", budget("rover"))
    assert manager.request_return()
    assert not manager.assign_optional_task("inspect-1", feasible(request, profiles, "late-route"))
    assert manager.snapshot().tasks[0].state == "BLOCKED"
    assert manager.pending_plan().goal == A
    assert manager.pending_plan().require_return is False


def test_cross_run_hidden_or_stale_discoveries_are_rejected(manager):
    task = ObservedTask("task", "other", 1, "discovery", "drone_1", "inspect", A, 5)
    assert not manager.discover_task(task)
    assert not manager.discover_task(replace(task, run_id="test-run", source_kind="EVALUATOR"))
    assert not manager.discover_task(replace(task, run_id="test-run", map_version=0))
    assert manager.snapshot().tasks == ()


def test_optional_rejected_by_resources_and_capability_with_reason(manager, profiles):
    ready(manager, profiles)
    discover(manager)
    assert manager.prepare_optional("inspect-1", "human_1", budget()) is None
    assert manager.snapshot().tasks[0].reason_code == "CAPABILITY_MISMATCH"
    request = manager.prepare_optional("inspect-1", "rover_1", Budgets(900, 0.0001, None, 100, 0, None))
    assert not manager.assign_optional_task("inspect-1", feasible(request, profiles, "too-expensive"))
    assert manager.snapshot().tasks[0].reason_code == "INSUFFICIENT_BUDGET"


def test_map_update_invalidates_optional_assignment(manager, profiles):
    ready(manager, profiles)
    discover(manager)
    request = manager.prepare_optional("inspect-1", "rover_1", budget("rover"))
    assert manager.assign_optional_task("inspect-1", feasible(request, profiles, "inspect-route"))
    manager.update_map("test-run", 2, 1)
    assert manager.snapshot().tasks[0].state == "BLOCKED"
    assert manager.snapshot().tasks[0].reason_code == "STALE_MAP"


def sampling_eligible(manager, profiles):
    route = ready(manager, profiles)
    discover(manager, position=B)
    request = manager.prepare_optional("inspect-1", "rover_1", budget("rover"))
    inspect = feasible(request, profiles, "inspection-route")
    assert manager.assign_optional_task("inspect-1", inspect)
    assert manager.update_agent(agent("rover_1", "rover", B, 1))
    assert manager.start_task(TaskEvidence("inspect-start", "test-run", 1, inspect.route_id, "inspect-1", 1))
    assert manager.complete_task(TaskEvidence("inspect-done", "test-run", 1, inspect.route_id, "inspect-1", 1))
    primary_done(manager, route)
    discover(manager, "sample", "sample-1", "inspect-1", B)


@pytest.mark.parametrize("field", ["reserve_time_s", "reserve_wh", "reserve_oxygen_l"])
def test_human_optional_cannot_reduce_any_primary_reserve(manager, profiles, field):
    sampling_eligible(manager, profiles)
    weaker = replace(budget(), **{field: 0})
    assert manager.prepare_optional("sample-1", "human_1", weaker) is None
    sample = next(t for t in manager.snapshot().tasks if t.task.task_id == "sample-1")
    assert sample.reason_code == "RESERVE_REQUIREMENT_REDUCED"


def test_human_optional_cost_fitting_zero_reserve_cannot_spend_primary_reserve(manager, profiles):
    sampling_eligible(manager, profiles)
    profile = profiles["human_1"]
    sampling = estimate_activity(profile, "sample", 5)
    returning = estimate_segment(profile, B.coordinates(), A.coordinates())
    energy_budget = sampling.energy_wh + returning.energy_wh + 0.1
    assert sampling.energy_wh + returning.energy_wh < energy_budget
    assert sampling.energy_wh + returning.energy_wh + 50 > energy_budget
    weaker = Budgets(900, energy_budget, 450, 0, 0, 0)
    assert manager.prepare_optional("sample-1", "human_1", weaker) is None
    sample = next(t for t in manager.snapshot().tasks if t.task.task_id == "sample-1")
    assert sample.reason_code == "RESERVE_REQUIREMENT_REDUCED"
    assert manager.snapshot().active_route is None


@pytest.mark.parametrize("reserved_id", ["primary", "return"])
def test_discovery_cannot_collide_with_authoritative_task_ids(manager, reserved_id):
    task = ObservedTask(reserved_id, "test-run", 1, "discovery", "drone_1", "inspect", A, 5)
    assert not manager.discover_task(task)


def test_new_human_route_cannot_reuse_old_return_and_traversal_evidence(manager, profiles):
    sampling_eligible(manager, profiles)
    returning = feasible(manager.pending_plan(), profiles, "return-route")
    assert manager.apply_plan(returning)
    assert manager.update_agent(agent(position=A, stamp=2))
    partial = MissionEvidence("prior-return", "test-run", 1, returning.route_id, 2,
                               returned_to_base_within_tolerance=True,
                               verified_ground_traversal_under_model=True)
    assert manager.record_evidence(partial)
    assert not manager.snapshot().mission_success
    request = manager.prepare_optional("sample-1", "human_1", budget())
    optional = feasible(request, profiles, "new-sample-route")
    assert manager.assign_optional_task("sample-1", optional)
    assert manager.update_agent(agent(position=B, stamp=3))
    budget_only = MissionEvidence("new-budget-check", "test-run", 1, optional.route_id, 3,
                                  no_budget_violation=True)
    assert manager.record_evidence(budget_only)
    assert manager.snapshot().mission_state != "COMPLETE"
    assert manager.snapshot().mission_success is False
    assert manager.snapshot().route_id == optional.route_id


def test_moving_away_from_base_expires_prior_return_evidence(manager, profiles):
    route = ready(manager, profiles)
    primary_done(manager, route)
    returning = feasible(manager.pending_plan(), profiles, "return-route")
    assert manager.apply_plan(returning)
    assert manager.update_agent(agent(position=A, stamp=2))
    partial = MissionEvidence("prior-return", "test-run", 1, returning.route_id, 2,
                               returned_to_base_within_tolerance=True,
                               verified_ground_traversal_under_model=True)
    assert manager.record_evidence(partial)
    assert manager.update_agent(agent(position=Point(1.5, 0.5), stamp=3))
    # This position is on the retained return polyline, so no new authorization
    # is needed. Merely leaving base must still expire its completion evidence.
    assert manager.snapshot().route_id == returning.route_id
    budget_only = MissionEvidence("budget-after-move", "test-run", 1, returning.route_id, 3,
                                  no_budget_violation=True)
    assert manager.record_evidence(budget_only)
    assert manager.snapshot().mission_success is False
    assert manager.snapshot().mission_state != "COMPLETE"
