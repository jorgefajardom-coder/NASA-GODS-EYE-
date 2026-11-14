"""Public terrain metadata only; no evaluator reference can be bundled here."""

from dataclasses import dataclass
from enum import Enum
from math import isfinite
from pathlib import Path


class TerrainRole(str, Enum):
    PRIOR = "prior"
    BELIEF = "belief"
    SIGMA = "sigma"
    REGIONAL_CONTEXT = "regional_context"


@dataclass(frozen=True)
class TerrainMetadata:
    """Local Cartesian ENU grid; vertical datum must come from the actual product."""

    dataset_id: str
    rows: int
    cols: int
    resolution_m: float
    vertical_datum: str
    frame_id: str = "map"
    map_version: int = 0

    def __post_init__(self):
        if not self.dataset_id or not self.vertical_datum or self.frame_id != "map":
            raise ValueError("dataset, vertical datum and the agreed map frame are required")
        if any(type(value) is not int or value <= 0 for value in (self.rows, self.cols)):
            raise ValueError("grid dimensions must be positive integers")
        if not isfinite(self.resolution_m) or self.resolution_m <= 0:
            raise ValueError("resolution_m must be finite and positive")
        if type(self.map_version) is not int or self.map_version < 0:
            raise ValueError("map_version must be a nonnegative integer")


def load_public_terrain(manifest_path: Path):
    """Pending: validate provenance and load prior/context without evaluator assets."""
    raise NotImplementedError("Daniel must implement validated public terrain import")
