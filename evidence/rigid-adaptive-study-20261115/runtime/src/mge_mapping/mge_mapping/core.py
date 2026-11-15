"""Incremental belief mapping, footprint-bounded observation fusion and traversability.

Applies audited SIMULATED observations to the public belief grid, enforces
idempotency by observation_id, preserves NoData/unknown semantics, and
increments map_version by exactly 1 per accepted observation event.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import math
from math import isfinite
from typing import TYPE_CHECKING, Any

import numpy as np

if TYPE_CHECKING:
    from mge_data.core import TerrainTile

DEFAULT_OBSERVATION_SIGMA_M = 0.25
NANOSECONDS_PER_SECOND = 1_000_000_000
MAX_TIMESTAMP_SIM_NS = (2**31) * NANOSECONDS_PER_SECOND - 1


def _observation_clock_ns(seconds: float, exact_ns: int | None, *, name: str) -> int:
    """Keep a canonical ROS clock key alongside descriptive float seconds.

    Wire callers supply sec*1e9+nanosec exactly. Legacy Python callers supplying
    only seconds derive the nearest integer nanosecond of that float (ties to
    even); they must supply the exact key when sub-float ordering matters.
    No nanosecond ordering decision uses the descriptive seconds field.
    """
    if isinstance(seconds, bool) or not isfinite(seconds) or seconds < 0:
        raise ValueError(f"{name} must be finite and nonnegative")
    numerator, denominator = float(seconds).as_integer_ratio()
    if exact_ns is None:
        quotient, remainder = divmod(numerator * NANOSECONDS_PER_SECOND, denominator)
        exact_ns = quotient + int(2*remainder > denominator
                                  or (2*remainder == denominator and quotient % 2 == 1))
    if type(exact_ns) is not int or not 0 <= exact_ns <= MAX_TIMESTAMP_SIM_NS:
        raise ValueError(f"{name} nanoseconds must fit a nonnegative ROS int32-second stamp")
    represented = (exact_ns // NANOSECONDS_PER_SECOND
                   + (exact_ns % NANOSECONDS_PER_SECOND) / NANOSECONDS_PER_SECOND)
    # Exact rational comparison preserves half-nanosecond ties. The equality
    # branch permits a wire stamp's descriptive seconds to round at large epochs.
    if (seconds != represented
            and 2*abs(numerator*NANOSECONDS_PER_SECOND - exact_ns*denominator) > denominator):
        raise ValueError(f"{name} seconds and nanoseconds disagree")
    return exact_ns


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
    sigmas_m: tuple[float, ...] | None = None
    obstacles: tuple[int, ...] | None = None
    source_kind: str = "SIMULATED"
    timestamp_sim_ns: int | None = None

    def __post_init__(self) -> None:
        if not all((self.observation_id, self.agent_id, self.run_id)):
            raise ValueError("observation, agent and run identifiers are required")
        if self.source_kind != "SIMULATED":
            raise ValueError("only SIMULATED observations are supported in P0")
        if type(self.source_map_version) is not int or self.source_map_version < 0:
            raise ValueError("source_map_version must be a nonnegative integer")
        object.__setattr__(self, "timestamp_sim_ns", _observation_clock_ns(
            self.timestamp_sim_s, self.timestamp_sim_ns, name="timestamp_sim_s"))
        if not self.cell_indices or len(self.cell_indices) != len(self.elevations_m):
            raise ValueError("each observed cell needs one elevation")
        if len(set(self.cell_indices)) != len(self.cell_indices):
            raise ValueError("duplicate cell indices are invalid")
        if any(type(index) is not int or index < 0 for index in self.cell_indices):
            raise ValueError("cell indices must be nonnegative integers")
        if any(isinstance(value, bool) or not isfinite(value) for value in self.elevations_m):
            raise ValueError("observed elevations must be finite")
        if self.sigmas_m is not None:
            if len(self.sigmas_m) != len(self.cell_indices):
                raise ValueError("sigmas_m must match cell_indices length")
            if any(isinstance(s, bool) or not isfinite(s) or s <= 0 for s in self.sigmas_m):
                raise ValueError("observed sigmas must be finite and positive")
        if self.obstacles is not None:
            if len(self.obstacles) != len(self.cell_indices):
                raise ValueError("obstacles must match cell_indices length")
            if any(type(obs) is not int or obs not in {-1, 0, 100} for obs in self.obstacles):
                raise ValueError("obstacles must be int8 occupancy codes in {-1, 0, 100}")


@dataclass(frozen=True)
class BeliefMap:
    """Immutable snapshot of the evolving public terrain belief and uncertainty."""

    run_id: str
    dataset_id: str
    rows: int
    cols: int
    resolution_m: float
    origin_x_m: float
    origin_y_m: float
    map_version: int
    prior: np.ndarray
    belief: np.ndarray
    sigma: np.ndarray
    nodata_mask: np.ndarray
    observed_mask: np.ndarray
    obstacle_grid: np.ndarray
    frame_id: str = "map"
    applied_observations: tuple[str, ...] = field(default_factory=tuple)
    last_observation_timestamp_sim_s: float = 0.0
    last_observation_timestamp_sim_ns: int | None = None

    def __post_init__(self) -> None:
        if not self.run_id or not self.dataset_id or self.frame_id != "map":
            raise ValueError("run_id, dataset_id and frame_id='map' are required")
        if any(type(v) is not int or v <= 0 for v in (self.rows, self.cols)):
            raise ValueError("rows and cols must be positive integers")
        if type(self.map_version) is not int or self.map_version < 0:
            raise ValueError("map_version must be a nonnegative integer")
        object.__setattr__(self, "last_observation_timestamp_sim_ns", _observation_clock_ns(
            self.last_observation_timestamp_sim_s, self.last_observation_timestamp_sim_ns,
            name="last observation timestamp"))
        if isinstance(self.resolution_m, bool) or not isfinite(self.resolution_m) or self.resolution_m <= 0:
            raise ValueError("resolution_m must be finite and positive")
        shape = (self.rows, self.cols)
        for name in ("prior", "belief", "sigma", "nodata_mask", "observed_mask", "obstacle_grid"):
            arr = getattr(self, name)
            if not isinstance(arr, np.ndarray) or arr.shape != shape:
                raise ValueError(f"{name} must be a 2D array with shape {shape}")
        if self.nodata_mask.dtype != np.bool_ or self.observed_mask.dtype != np.bool_:
            raise ValueError("nodata_mask and observed_mask must be boolean arrays")
        if np.any(self.nodata_mask & self.observed_mask):
            raise ValueError("NoData cells cannot be marked as observed")

    @classmethod
    def from_terrain_tile(
        cls,
        tile: TerrainTile,
        *,
        run_id: str = "run-1",
        initial_map_version: int = 1,
    ) -> BeliefMap:
        prior = np.array(tile.prior, dtype=np.float32, copy=True)
        belief = np.array(tile.belief, dtype=np.float32, copy=True)
        sigma = np.array(tile.sigma, dtype=np.float32, copy=True)
        nodata_mask = np.array(tile.nodata_mask, dtype=bool, copy=True)
        observed_mask = np.array(tile.observed_mask, dtype=bool, copy=True)
        obstacle_grid = np.full(prior.shape, -1, dtype=np.int8)
        for arr in (prior, belief, sigma, nodata_mask, observed_mask, obstacle_grid):
            arr.setflags(write=False)
        return cls(
            run_id=run_id,
            dataset_id=tile.metadata.dataset_id,
            rows=tile.metadata.rows,
            cols=tile.metadata.cols,
            resolution_m=tile.metadata.resolution_m,
            origin_x_m=tile.metadata.origin_x_m,
            origin_y_m=tile.metadata.origin_y_m,
            map_version=initial_map_version,
            prior=prior,
            belief=belief,
            sigma=sigma,
            nodata_mask=nodata_mask,
            observed_mask=observed_mask,
            obstacle_grid=obstacle_grid,
            frame_id=tile.metadata.frame_id,
            applied_observations=(),
        )

    @classmethod
    def from_arrays(
        cls,
        prior: Any,
        *,
        run_id: str = "test-run",
        dataset_id: str = "jezero_mvp",
        resolution_m: float = 4.0,
        origin_x_m: float = -64.0,
        origin_y_m: float = -64.0,
        map_version: int = 1,
        prior_sigma_m: float = 2.5,
    ) -> BeliefMap:
        prior_arr = np.array(prior, dtype=np.float32, copy=True)
        if prior_arr.ndim != 2 or not prior_arr.size:
            raise ValueError("prior must be a non-empty 2D array")
        rows, cols = prior_arr.shape
        nodata_mask = ~np.isfinite(prior_arr)
        observed_mask = np.zeros((rows, cols), dtype=bool)
        belief_arr = prior_arr.copy()
        sigma_arr = np.where(~nodata_mask, np.float32(prior_sigma_m), np.float32(np.inf)).astype(np.float32)
        obstacle_grid = np.full((rows, cols), -1, dtype=np.int8)
        for arr in (prior_arr, belief_arr, sigma_arr, nodata_mask, observed_mask, obstacle_grid):
            arr.setflags(write=False)
        return cls(
            run_id=run_id,
            dataset_id=dataset_id,
            rows=rows,
            cols=cols,
            resolution_m=resolution_m,
            origin_x_m=origin_x_m,
            origin_y_m=origin_y_m,
            map_version=map_version,
            prior=prior_arr,
            belief=belief_arr,
            sigma=sigma_arr,
            nodata_mask=nodata_mask,
            observed_mask=observed_mask,
            obstacle_grid=obstacle_grid,
            frame_id="map",
            applied_observations=(),
        )

    def traversability_grid(
        self,
        *,
        max_slope_deg: float = 20.0,
        max_sigma_m: float = 1.0,
        allow_estimated: bool = False,
    ) -> np.ndarray:
        """Compute OccupancyGrid (-1 unknown, 0 admissible, 100 forbidden).

        By default unobserved cells remain unknown. An explicit experimental
        policy may admit finite estimates without changing observed coverage or
        sigma. Zero then means candidate-admissible, never verified or safe.
        """
        if type(allow_estimated) is not bool:
            raise ValueError("allow_estimated must be boolean")
        if not isfinite(max_sigma_m) or max_sigma_m <= 0:
            raise ValueError("max_sigma_m must be positive and finite")
        if not isfinite(max_slope_deg) or not 0 <= max_slope_deg <= 90:
            raise ValueError("max_slope_deg must be within [0, 90]")
        grid = np.full((self.rows, self.cols), -1, dtype=np.int8)
        knowledge = np.ones_like(self.observed_mask) if allow_estimated else self.observed_mask
        valid_and_observed = ((~self.nodata_mask) & knowledge & np.isfinite(self.belief)
                              & np.isfinite(self.sigma) & (self.sigma >= 0)
                              & (self.sigma <= max_sigma_m))
        if np.any(valid_and_observed):
            # Estimate conservative local slope magnitude from finite neighbors
            filled = np.where(np.isfinite(self.belief), self.belief, 0.0)
            gy, gx = np.gradient(filled, self.resolution_m)
            slope_deg = np.degrees(np.arctan(np.hypot(gx, gy)))
            admissible = valid_and_observed & (slope_deg <= max_slope_deg) & (self.obstacle_grid != 100)
            blocked = (valid_and_observed & (slope_deg > max_slope_deg)) | (self.obstacle_grid == 100)
            grid[admissible] = 0
            grid[blocked] = 100
        grid[self.obstacle_grid == 100] = 100
        # Explicitly guarantee NoData cells never become free (0)
        grid[self.nodata_mask] = -1
        return grid


def fuse_observation(
    belief: BeliefMap,
    observation: SimulatedObservation,
    *,
    default_sigma_m: float = DEFAULT_OBSERVATION_SIGMA_M,
) -> BeliefMap:
    """Apply a validated SIMULATED observation to the belief map.

    - Rejects mismatched run_id, noncurrent source_map_version, out-of-bounds cell indices,
      or attempts to turn source NoData cells into observed cells.
    - Deduplicates by observation_id: applying the same observation_id twice is a no-op.
    - Requires a timestamp no earlier than the last accepted observation globally.
      This conservative policy also rejects delayed disjoint footprints; reobserve
      against the current map instead of retagging the old measurement.
    - Updates only the cells in observation.cell_indices and increments map_version by 1.
    """
    if not isinstance(belief, BeliefMap):
        raise TypeError("belief must be a BeliefMap instance")
    if not isinstance(observation, SimulatedObservation):
        raise TypeError("observation must be a SimulatedObservation instance")
    if observation.run_id != belief.run_id:
        raise ValueError(f"observation run_id '{observation.run_id}' does not match belief run_id '{belief.run_id}'")
    total_cells = belief.rows * belief.cols
    for idx in observation.cell_indices:
        if idx < 0 or idx >= total_cells:
            raise ValueError(f"cell index {idx} is out of grid bounds [0, {total_cells})")

    # Idempotency check (T-06): duplicate observation_id has no effect
    if observation.observation_id in belief.applied_observations:
        return belief
    if observation.source_map_version > belief.map_version:
        raise ValueError("observation source_map_version cannot exceed current belief map_version")
    if observation.source_map_version != belief.map_version:
        raise ValueError("observation source_map_version must match current belief map_version")
    if observation.timestamp_sim_ns < belief.last_observation_timestamp_sim_ns:
        raise ValueError("observation timestamp precedes the last applied observation")

    rows_idx = [idx // belief.cols for idx in observation.cell_indices]
    cols_idx = [idx % belief.cols for idx in observation.cell_indices]

    # Source NoData protection (T-04): source NoData cells cannot become free observed terrain
    for r, c in zip(rows_idx, cols_idx):
        if belief.nodata_mask[r, c]:
            raise ValueError(f"cell ({r}, {c}) is marked as source NoData and cannot be observed as valid terrain")

    new_belief = np.array(belief.belief, dtype=np.float32, copy=True)
    new_sigma = np.array(belief.sigma, dtype=np.float32, copy=True)
    new_observed = np.array(belief.observed_mask, dtype=bool, copy=True)
    new_obstacles = np.array(belief.obstacle_grid, dtype=np.int8, copy=True)

    sigmas = (
        observation.sigmas_m
        if observation.sigmas_m is not None
        else tuple(default_sigma_m for _ in observation.cell_indices)
    )
    obstacles = (
        observation.obstacles
        if observation.obstacles is not None
        else tuple(int(belief.obstacle_grid[r, c]) for r, c in zip(rows_idx, cols_idx))
    )

    for r, c, elev_m, obs_sigma_m, obs_code in zip(rows_idx, cols_idx, observation.elevations_m, sigmas, obstacles):
        new_belief[r, c] = np.float32(elev_m)
        new_sigma[r, c] = np.float32(obs_sigma_m)
        new_observed[r, c] = True
        # Missing/unknown obstacle evidence cannot clear a confirmed obstacle.
        # An explicit current, nonolder FREE observation may supersede it.
        new_obstacles[r, c] = np.int8(100 if obs_code == -1 and belief.obstacle_grid[r, c] == 100 else obs_code)

    for arr in (new_belief, new_sigma, new_observed, new_obstacles):
        arr.setflags(write=False)

    return BeliefMap(
        run_id=belief.run_id,
        dataset_id=belief.dataset_id,
        rows=belief.rows,
        cols=belief.cols,
        resolution_m=belief.resolution_m,
        origin_x_m=belief.origin_x_m,
        origin_y_m=belief.origin_y_m,
        map_version=belief.map_version + 1,
        prior=belief.prior,
        belief=new_belief,
        sigma=new_sigma,
        nodata_mask=belief.nodata_mask,
        observed_mask=new_observed,
        obstacle_grid=new_obstacles,
        frame_id=belief.frame_id,
        applied_observations=(*belief.applied_observations, observation.observation_id),
        last_observation_timestamp_sim_s=observation.timestamp_sim_s,
        last_observation_timestamp_sim_ns=observation.timestamp_sim_ns,
    )


class ObservationFusion:
    """Stateful manager wrapping a BeliefMap and applying incoming observations."""

    def __init__(self, initial_belief: BeliefMap, *, default_sigma_m: float = DEFAULT_OBSERVATION_SIGMA_M) -> None:
        self._belief = initial_belief
        self._default_sigma_m = default_sigma_m

    @property
    def belief_map(self) -> BeliefMap:
        return self._belief

    @property
    def map_version(self) -> int:
        return self._belief.map_version

    def apply(self, observation: SimulatedObservation) -> tuple[BeliefMap, bool]:
        """Apply an observation and return (updated_belief, was_applied)."""
        prev_version = self._belief.map_version
        self._belief = fuse_observation(
            self._belief, observation, default_sigma_m=self._default_sigma_m
        )
        return self._belief, (self._belief.map_version > prev_version)
