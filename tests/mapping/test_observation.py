"""Acceptance and unit tests (T-04, T-05, T-06, T-08) for observation validation and belief fusion."""

from pathlib import Path

import numpy as np
import pytest

from mge_data.core import load_public_terrain
from mge_mapping.core import (
    BeliefMap,
    ObservationFusion,
    SimulatedObservation,
    fuse_observation,
)
from mge_mapping.node import build_mapping_state_summary

ROOT = Path(__file__).resolve().parents[2]
READY_MANIFEST_PATH = ROOT / "data/sample/manifest.json"


def observation(**changes):
    values = dict(
        observation_id="observation-1",
        agent_id="drone-1",
        run_id="test-run",
        source_map_version=1,
        timestamp_sim_s=10.0,
        cell_indices=(1, 2),
        elevations_m=(0.5, 1.0),
    )
    return SimulatedObservation(**(values | changes))


@pytest.mark.parametrize("identifier", ["observation_id", "agent_id", "run_id"])
def test_missing_causal_identifier_is_rejected(identifier):
    with pytest.raises(ValueError, match="identifiers"):
        observation(**{identifier: ""})


@pytest.mark.parametrize("invalid", [-1, 1.5, float("nan"), True])
def test_map_version_must_be_nonnegative_integer(invalid):
    with pytest.raises(ValueError, match="source_map_version"):
        observation(source_map_version=invalid)


@pytest.mark.parametrize("invalid", [-1.0, float("nan"), float("inf")])
def test_invalid_simulation_time_is_rejected(invalid):
    with pytest.raises(ValueError, match="timestamp_sim_s"):
        observation(timestamp_sim_s=invalid)


@pytest.mark.parametrize(
    "changes",
    [
        dict(cell_indices=(), elevations_m=()),
        dict(elevations_m=(1.0,)),
        dict(elevations_m=(1.0, 2.0, 3.0)),
    ],
)
def test_each_observed_cell_requires_one_measurement(changes):
    with pytest.raises(ValueError, match="one elevation"):
        observation(**changes)


def test_same_cell_cannot_be_counted_twice_in_one_observation():
    with pytest.raises(ValueError, match="duplicate cell"):
        observation(cell_indices=(1, 1))


@pytest.mark.parametrize("indices", [(-1, 2), (1.5, 2), (True, 2)])
def test_grid_indices_cannot_be_negative_fractional_or_boolean(indices):
    with pytest.raises(ValueError, match="nonnegative integers"):
        observation(cell_indices=indices)


@pytest.mark.parametrize("invalid", [float("nan"), float("inf"), -float("inf")])
def test_nonfinite_measurement_is_not_silently_accepted(invalid):
    with pytest.raises(ValueError, match="elevations must be finite"):
        observation(elevations_m=(invalid, 1.0))


def test_observation_retains_source_version_without_claiming_fusion():
    sample = observation(source_map_version=0, timestamp_sim_s=0.0)
    assert sample.source_map_version == 0
    assert sample.cell_indices == (1, 2)


def test_t04_nodata_cells_remain_unknown_and_never_become_free():
    """T-04: NoData cells in prior stay -1 (unknown) in traversability and reject observations."""
    prior = np.array(
        [
            [-2570.0, -2570.1, np.nan],
            [-2570.2, -2570.3, -2570.4],
            [-2570.5, -2570.6, -2570.7],
        ],
        dtype=np.float32,
    )
    bmap = BeliefMap.from_arrays(prior, run_id="test-run")
    assert bmap.nodata_mask[0, 2] is np.True_
    assert not np.any(bmap.observed_mask)
    occ = bmap.traversability_grid()
    assert np.all(occ == -1)

    # Attempting to observe the NoData cell (index 2) is rejected
    with pytest.raises(ValueError, match="NoData"):
        fuse_observation(bmap, observation(cell_indices=(2,), elevations_m=(-2570.0,)))


def test_t05_simulated_observation_updates_only_footprint_and_increments_version_by_one():
    """T-05: A valid SimulatedObservation modifies only cell_indices and increments map_version by 1."""
    tile = load_public_terrain(READY_MANIFEST_PATH)
    initial = BeliefMap.from_terrain_tile(tile, run_id="test-run", initial_map_version=1)
    footprint = (0, 33, 66)
    measured_elevs = (-2570.10, -2571.25, -2572.40)
    measured_sigmas = (0.15, 0.20, 0.18)

    obs = observation(
        observation_id="obs-footprint-1",
        source_map_version=1,
        cell_indices=footprint,
        elevations_m=measured_elevs,
        sigmas_m=measured_sigmas,
    )
    updated = fuse_observation(initial, obs)

    assert updated.map_version == initial.map_version + 1
    assert int(updated.observed_mask.sum()) == len(footprint)

    flat_before = initial.belief.ravel()
    flat_after = updated.belief.ravel()
    flat_sigma_before = initial.sigma.ravel()
    flat_sigma_after = updated.sigma.ravel()

    for idx in range(initial.rows * initial.cols):
        if idx in footprint:
            pos = footprint.index(idx)
            assert np.isclose(flat_after[idx], measured_elevs[pos], atol=1e-4)
            assert np.isclose(flat_sigma_after[idx], measured_sigmas[pos], atol=1e-4)
            assert updated.observed_mask.ravel()[idx] is np.True_
        else:
            assert flat_after[idx] == flat_before[idx]
            assert flat_sigma_after[idx] == flat_sigma_before[idx]
            assert updated.observed_mask.ravel()[idx] is np.False_


def test_t06_duplicate_observation_id_is_idempotent():
    """T-06: Applying the same observation_id twice leaves map_version and belief unchanged."""
    tile = load_public_terrain(READY_MANIFEST_PATH)
    fusion = ObservationFusion(BeliefMap.from_terrain_tile(tile, run_id="test-run", initial_map_version=1))
    obs = observation(observation_id="obs-dup-1", cell_indices=(10, 11), elevations_m=(-2570.5, -2570.6))

    first_map, first_applied = fusion.apply(obs)
    assert first_applied is True
    assert first_map.map_version == 2

    second_map, second_applied = fusion.apply(obs)
    assert second_applied is False
    assert second_map.map_version == 2
    assert np.array_equal(second_map.belief, first_map.belief)
    assert np.array_equal(second_map.sigma, first_map.sigma)
    summary = build_mapping_state_summary(second_map)
    assert summary["map_version"] == 2
    assert summary["applied_observations"] == ["obs-dup-1"]


def test_t08_out_of_bounds_or_mismatched_run_observations_are_rejected():
    """T-08: Out-of-bounds cell indices, wrong run_id, future map_version, or invalid sigmas/obstacles fail."""
    tile = load_public_terrain(READY_MANIFEST_PATH)
    bmap = BeliefMap.from_terrain_tile(tile, run_id="test-run", initial_map_version=1)

    with pytest.raises(ValueError, match="out of grid bounds"):
        fuse_observation(bmap, observation(cell_indices=(32 * 32,), elevations_m=(-2570.0,)))

    with pytest.raises(ValueError, match="run_id"):
        fuse_observation(bmap, observation(run_id="other-run"))

    with pytest.raises(ValueError, match="cannot exceed current"):
        fuse_observation(bmap, observation(source_map_version=5))

    with pytest.raises(ValueError, match="sigmas must be finite and positive"):
        observation(sigmas_m=(0.0, 0.2))

    with pytest.raises(ValueError, match="obstacles must be int8 occupancy codes"):
        observation(obstacles=(50, 0))
