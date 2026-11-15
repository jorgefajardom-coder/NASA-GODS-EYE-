"""Illustrative estimated-terrain producer/planner checks, never authorization."""
from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest

from mge_mapping.core import BeliefMap, SimulatedObservation, fuse_observation
from mge_mapping.policy import load_knowledge_policy
from mge_planning.core import (
    MotionProfile, PlanRequest, ResourceBudget, RouteStatus, TerrainGrid, plan_route,
)

ROOT = Path(__file__).resolve().parents[2]


def scene(kind="human", *, prior=None):
    policy = load_knowledge_policy(ROOT / "config/exploration_policy.illustrative.json")
    belief = BeliefMap.from_arrays(np.zeros((7, 9)) if prior is None else prior,
                                   run_id="estimated-candidate", resolution_m=4.)
    profile = MotionProfile(kind, 1., 30., 1., .25, .1, .2,
                            oxygen_l_per_s=.01 if kind == "human" else None)
    budget = ResourceBudget(kind, 1000., 1000., 20.,
                            100. if kind == "human" else None,
                            5. if kind == "human" else None)
    grid = candidate_grid(belief, policy, kind)
    request = PlanRequest(grid.run_id, "estimated-route", kind+"_1", kind, 1,
                          grid.point((3, 1)), grid.point((3, 7)), budget,
                          return_to=grid.point((3, 1)), require_return=True,
                          reserve_time_s=30.)
    return policy, belief, profile, request


def candidate_grid(belief, policy, kind):
    mask = belief.traversability_grid(**dict(policy.limits[kind]), allow_estimated=policy.allow_estimated)
    return TerrainGrid(belief.run_id, belief.map_version, belief.belief, mask,
                        belief.resolution_m, belief.origin_x_m, belief.origin_y_m,
                        sigma_m=belief.sigma)


@pytest.mark.parametrize("kind", ["human", "rover"])
def test_valid_prior_can_propose_a_roundtrip_without_becoming_observed(kind):
    policy, belief, profile, request = scene(kind)
    grid = candidate_grid(belief, policy, kind)
    result = plan_route(terrain=grid, request=request, profile=profile)
    assert result.status == RouteStatus.FEASIBLE
    assert not np.any(belief.observed_mask)
    assert np.all(belief.sigma == 2.5) and np.array_equal(belief.prior, belief.belief)
    assert set(grid.traversability.ravel()) == {0}
    assert set(belief.traversability_grid().ravel()) == {-1}  # Baseline is unchanged.
    assert result.return_path[-1] == request.return_to
    assert result.travel_time_s + request.reserve_time_s <= request.budget.time_s
    assert result.energy_est_wh + request.budget.reserve_wh <= request.budget.energy_wh
    if kind == "human":
        assert result.oxygen_est_l + request.budget.reserve_oxygen_l <= request.budget.oxygen_l


def test_local_contradiction_changes_the_route_without_preobserving_the_corridor():
    policy, belief, profile, request = scene()
    first = plan_route(terrain=candidate_grid(belief, policy, "human"), request=request, profile=profile)
    assert first.status == RouteStatus.FEASIBLE
    cell = 3*belief.cols+4
    observed = fuse_observation(belief, SimulatedObservation(
        "local-contradiction", "drone_1", belief.run_id, 1, 20.,
        (cell,), (3.,), (.25,), (100,)))
    revised = plan_route(terrain=candidate_grid(observed, policy, "human"),
                         request=replace(request, map_version=2, request_id="revised"), profile=profile)
    assert revised.status == RouteStatus.FEASIBLE
    assert revised.outbound_path != first.outbound_path
    assert all(candidate_grid(observed, policy, "human").cell(p) != (3, 4)
               for path in (revised.outbound_path, revised.return_path) for p in path)
    assert observed.observed_mask.sum() == 1 and observed.sigma.flat[cell] == .25
    untouched = np.ones_like(belief.observed_mask); untouched.flat[cell] = False
    assert np.array_equal(observed.belief[untouched], belief.belief[untouched])
    assert np.array_equal(observed.sigma[untouched], belief.sigma[untouched])
    assert np.array_equal(observed.prior, belief.prior)


def test_all_alternatives_blocked_and_nodata_still_refuse_a_route():
    policy, belief, profile, request = scene()
    wall = tuple(r*belief.cols+4 for r in range(belief.rows))
    blocked = fuse_observation(belief, SimulatedObservation(
        "blocked-all", "drone_1", belief.run_id, 1, 20.,
        wall, (0.,)*len(wall), (.25,)*len(wall), (100,)*len(wall)))
    refused = plan_route(terrain=candidate_grid(blocked, policy, "human"),
                         request=replace(request, map_version=2), profile=profile)
    assert refused.status == RouteStatus.NO_PATH and not refused.outbound_path
    prior = np.zeros((7, 9)); prior[:, 4] = np.nan
    policy, missing, profile, request = scene(prior=prior)
    grid = candidate_grid(missing, policy, "human")
    assert np.all(grid.traversability[:, 4] == -1) and not np.any(missing.observed_mask)
    unverified = plan_route(terrain=grid, request=request, profile=profile)
    assert unverified.status == RouteStatus.UNKNOWN and not unverified.outbound_path


def test_exploration_policy_does_not_weaken_the_planners_independent_uncertainty_limit():
    policy, belief, profile, request = scene()
    result = plan_route(terrain=candidate_grid(belief, policy, "human"), request=request,
                        profile=replace(profile, max_sigma_m=1.))
    assert result.status == RouteStatus.UNKNOWN and not result.outbound_path
    assert np.all(belief.sigma == 2.5) and not np.any(belief.observed_mask)


def test_estimated_route_still_cannot_spend_the_return_reserve():
    policy, belief, profile, request = scene()
    result = plan_route(terrain=candidate_grid(belief, policy, "human"), profile=profile,
                        request=replace(request, budget=replace(request.budget, energy_wh=25.)))
    assert result.status == RouteStatus.INSUFFICIENT_BUDGET and not result.outbound_path
