"""Synthetic stale-observation regressions, not physical sensing evidence."""
from dataclasses import replace

import numpy as np
import pytest

from mge_mapping.core import BeliefMap, ObservationFusion, SimulatedObservation


def flat_map():
    return BeliefMap.from_arrays(np.zeros((3, 3)), run_id="causal-run")


def observation(identifier, *, base=1, stamp=20., cells=(4,), obstacles=(100,)):
    return SimulatedObservation(identifier, "drone_1", "causal-run", base, stamp,
                                cells, (0.,)*len(cells), (.25,)*len(cells), obstacles)


def protected_map():
    fusion = ObservationFusion(flat_map())
    fusion.apply(observation("new-obstacle"))
    return fusion


@pytest.mark.parametrize("change", [
    dict(base=1, stamp=10.),             # Original delayed/free-over-obstacle defect.
    dict(base=2, stamp=10.),             # Retagging base does not refresh a measurement.
    dict(base=3, stamp=21.),             # A future base is not a usable snapshot.
])
def test_rejected_free_measurement_is_atomic_and_cannot_erase_obstacle(change):
    fusion = protected_map()
    before = fusion.belief_map
    with pytest.raises(ValueError):
        fusion.apply(observation("late-free", obstacles=(0,), **change))
    assert fusion.belief_map is before
    assert fusion.map_version == 2
    assert before.last_observation_timestamp_sim_s == 20.
    assert before.applied_observations == ("new-obstacle",)
    assert before.obstacle_grid[1, 1] == before.traversability_grid()[1, 1] == 100
    assert before.belief[1, 1] == 0. and before.sigma[1, 1] == .25


def test_duplicate_is_a_noop_after_newer_base_and_timestamp_have_been_applied():
    fusion = protected_map()
    second = observation("next-cell", base=2, stamp=30., cells=(0,), obstacles=(0,))
    fusion.apply(second)
    current = fusion.belief_map
    actual, applied = fusion.apply(observation("new-obstacle"))
    assert actual is current and not applied
    assert fusion.map_version == 3 and actual.last_observation_timestamp_sim_s == 30.


@pytest.mark.parametrize("base,stamp", [(1, 30.), (2, 19.)])
def test_global_current_base_policy_also_rejects_delayed_disjoint_footprints(base, stamp):
    fusion = protected_map()
    current = fusion.belief_map
    with pytest.raises(ValueError):
        fusion.apply(observation("disjoint", base=base, stamp=stamp, cells=(0,), obstacles=(0,)))
    assert fusion.belief_map is current and not current.observed_mask[0, 0]


def test_current_base_at_equal_timestamp_can_apply_a_distinct_footprint_once():
    fusion = protected_map()
    actual, applied = fusion.apply(observation("disjoint", base=2, stamp=20., cells=(0,), obstacles=(0,)))
    assert applied and actual.map_version == 3
    assert actual.last_observation_timestamp_sim_s == 20.
    assert actual.observed_mask[0, 0] and actual.obstacle_grid[1, 1] == 100


@pytest.mark.parametrize("obstacles", [None, (-1,)])
def test_omitted_or_unknown_obstacle_data_does_not_clear_a_confirmed_obstacle(obstacles):
    fusion = protected_map()
    actual, applied = fusion.apply(observation("height-only", base=2, stamp=21., obstacles=obstacles))
    assert applied and actual.map_version == 3
    assert actual.obstacle_grid[1, 1] == actual.traversability_grid()[1, 1] == 100


def test_explicit_current_newer_free_evidence_can_supersede_a_confirmed_obstacle():
    fusion = protected_map()
    actual, applied = fusion.apply(observation("new-free", base=2, stamp=21., obstacles=(0,)))
    assert applied and actual.obstacle_grid[1, 1] == actual.traversability_grid()[1, 1] == 0


def test_mixed_footprint_rejection_preserves_all_cells_prior_and_clock():
    fusion = protected_map()
    current = fusion.belief_map
    with pytest.raises(ValueError):
        fusion.apply(observation("mixed", base=1, cells=(0, 4), obstacles=(0, 0)))
    assert fusion.belief_map is current and fusion.map_version == 2
    assert not current.observed_mask[0, 0] and current.obstacle_grid[1, 1] == 100
    assert np.array_equal(current.prior, np.zeros((3, 3)))


@pytest.mark.parametrize("value", [-1., float("nan"), float("inf"), True])
def test_last_observation_clock_is_a_valid_snapshot_invariant(value):
    with pytest.raises(ValueError, match="last observation timestamp"):
        replace(flat_map(), last_observation_timestamp_sim_s=value)


@pytest.mark.parametrize("value", [-1, True, 20.0, (2**31)*1_000_000_000])
def test_exact_nanosecond_keys_reject_invalid_types_and_ros_range(value):
    with pytest.raises(ValueError, match="nanoseconds"):
        replace(observation("invalid-clock"), timestamp_sim_ns=value)
    with pytest.raises(ValueError, match="nanoseconds"):
        replace(flat_map(), last_observation_timestamp_sim_ns=value)


def test_float_only_python_clock_derives_nearest_ns_without_ambiguous_replace():
    obs = observation("legacy-float", stamp=20.1234567891)
    assert obs.timestamp_sim_ns == 20_123_456_789
    updated, applied = ObservationFusion(flat_map()).apply(obs)
    assert applied and updated.last_observation_timestamp_sim_s == obs.timestamp_sim_s
    assert updated.last_observation_timestamp_sim_ns == obs.timestamp_sim_ns
    # Replacing one clock representation cannot silently retain the other.
    with pytest.raises(ValueError, match="seconds and nanoseconds disagree"):
        replace(obs, timestamp_sim_s=21.)
    with pytest.raises(ValueError, match="seconds and nanoseconds disagree"):
        replace(updated, last_observation_timestamp_sim_s=21.)
    assert replace(obs, timestamp_sim_s=21., timestamp_sim_ns=None).timestamp_sim_ns == 21_000_000_000


def test_inconsistent_exact_clock_fields_are_rejected_before_mutation():
    before = flat_map()
    with pytest.raises(ValueError, match="seconds and nanoseconds disagree"):
        replace(observation("wrong-ns"), timestamp_sim_ns=21_000_000_000)
    with pytest.raises(ValueError, match="seconds and nanoseconds disagree"):
        replace(before, last_observation_timestamp_sim_s=20.,
                last_observation_timestamp_sim_ns=21_000_000_000)
    assert before.map_version == 1 and before.last_observation_timestamp_sim_ns == 0


def test_float_only_clock_quantization_uses_nearest_nanosecond_ties_to_even():
    assert observation("half-even-zero", stamp=1/1024).timestamp_sim_ns == 976_562
    assert observation("half-even-up", stamp=3/1024).timestamp_sim_ns == 2_929_688
