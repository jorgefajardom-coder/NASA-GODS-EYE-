"""Reject malformed observations before a future fusion implementation sees them."""

import pytest

from mge_mapping.core import SimulatedObservation


def observation(**changes):
    values = dict(observation_id="observation-1", agent_id="drone-1", run_id="test-run",
                  source_map_version=2, timestamp_sim_s=10.0,
                  cell_indices=(1, 2), elevations_m=(0.5, 1.0))
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


@pytest.mark.parametrize("changes", [dict(cell_indices=(), elevations_m=()),
                                     dict(elevations_m=(1.0,)),
                                     dict(elevations_m=(1.0, 2.0, 3.0))])
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
