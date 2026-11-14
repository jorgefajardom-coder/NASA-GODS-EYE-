"""Proposed mapping entry point; fusion and map-version authority remain pending."""

from dataclasses import dataclass
from math import isfinite


@dataclass(frozen=True)
class SimulatedObservation:
    """Flat row-major cell indices; all measurements are simulated elevations in m."""

    observation_id: str
    agent_id: str
    run_id: str
    source_map_version: int
    timestamp_sim_s: float
    cell_indices: tuple[int, ...]
    elevations_m: tuple[float, ...]

    def __post_init__(self):
        if not all((self.observation_id, self.agent_id, self.run_id)):
            raise ValueError("observation, agent and run identifiers are required")
        if type(self.source_map_version) is not int or self.source_map_version < 0:
            raise ValueError("source_map_version must be a nonnegative integer")
        if not isfinite(self.timestamp_sim_s) or self.timestamp_sim_s < 0:
            raise ValueError("timestamp_sim_s must be finite and nonnegative")
        if not self.cell_indices or len(self.cell_indices) != len(self.elevations_m):
            raise ValueError("each observed cell needs one elevation")
        if len(set(self.cell_indices)) != len(self.cell_indices):
            raise ValueError("duplicate cell indices are invalid")
        if any(type(index) is not int or index < 0 for index in self.cell_indices):
            raise ValueError("cell indices must be nonnegative integers")
        if any(not isfinite(value) for value in self.elevations_m):
            raise ValueError("observed elevations must be finite")


def fuse_observation(belief, observation: SimulatedObservation):
    """Pending: bounds/footprint checks, deduplication, sigma and atomic version update."""
    raise NotImplementedError("Daniel must implement audited observation fusion")
