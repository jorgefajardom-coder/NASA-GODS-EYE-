"""Public terrain metadata, georeferencing, manifest validation and loader.

Evaluator reference assets (e.g. HiRISE DTM) are strictly isolated in
data/reference/ and must never be bundled into data/sample/ or returned by
public terrain loaders.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import hashlib
import json
import math
from math import isfinite
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator
import numpy as np

MARS_2000_SPHERE_RADIUS_M = 3396190.0
FORBIDDEN_CRS_TOKENS = ("epsg:4326", "wgs84", "wgs 84", "epsg:3857", "nad83")
FORBIDDEN_PUBLIC_ARRAY_KEYS = ("reference", "hirise", "evaluation_reference", "ground_truth")


class TerrainRole(str, Enum):
    PRIOR = "prior"
    BELIEF = "belief"
    SIGMA = "sigma"
    REGIONAL_CONTEXT = "regional_context"


@dataclass(frozen=True)
class SourceRecord:
    """Provenance record for a single planetary dataset source."""

    mission: str
    instrument: str
    role: str
    product_id: str
    native_resolution_m: float
    source_url: str
    sha256: str
    license_or_terms_url: str

    def __post_init__(self) -> None:
        for name in (
            "mission",
            "instrument",
            "role",
            "product_id",
            "source_url",
            "sha256",
            "license_or_terms_url",
        ):
            val = getattr(self, name)
            if not isinstance(val, str) or not val.strip():
                raise ValueError(f"source {name} must be a non-empty string")
        if self.role not in {"prior", "evaluation_reference", "regional_context"}:
            raise ValueError(f"unsupported source role: {self.role}")
        if (
            isinstance(self.native_resolution_m, bool)
            or not isinstance(self.native_resolution_m, (int, float))
            or not isfinite(self.native_resolution_m)
            or self.native_resolution_m <= 0
        ):
            raise ValueError("native_resolution_m must be a finite positive number")
        if len(self.sha256) != 64 or any(c not in "0123456789abcdef" for c in self.sha256):
            raise ValueError("sha256 must be a 64-character lowercase hexadecimal digest")


@dataclass(frozen=True)
class SourceRegistry:
    """Validated registry of multi-mission planetary sources for a terrain package."""

    records: tuple[SourceRecord, ...]

    def __post_init__(self) -> None:
        if not self.records:
            raise ValueError("SourceRegistry requires at least one SourceRecord")
        roles = {r.role for r in self.records}
        required_roles = {"prior", "evaluation_reference", "regional_context"}
        missing = required_roles - roles
        if missing:
            raise ValueError(f"SourceRegistry missing required roles: {sorted(missing)}")
        missions = {r.mission for r in self.records}
        if "Mars Global Surveyor" not in missions or "MRO" not in missions:
            raise ValueError("SourceRegistry requires multi-mission provenance (MRO and Mars Global Surveyor)")

    @classmethod
    def from_manifest_sources(cls, sources: list[dict[str, Any]]) -> SourceRegistry:
        return cls(tuple(SourceRecord(**item) for item in sources))

    def by_role(self, role: str) -> SourceRecord:
        for record in self.records:
            if record.role == role:
                return record
        raise KeyError(f"no source registered for role '{role}'")

    def public_sources_summary(self) -> tuple[str, ...]:
        """Return human-readable provenance strings for public ROS TerrainMeta messages."""
        return tuple(
            f"{r.mission}/{r.instrument} ({r.role}): {r.product_id} "
            f"[{r.native_resolution_m}m, sha256={r.sha256}]"
            for r in self.records
            if r.role in {"prior", "regional_context"}
        )


@dataclass(frozen=True)
class GeoTransform:
    """Explicit Mars-local Cartesian ENU transform on the Mars 2000 IAU sphere."""

    origin_lat_deg: float
    origin_lon_deg: float
    origin_x_m: float
    origin_y_m: float
    resolution_m: float
    rows: int
    cols: int
    row_orientation: str = "south_to_north"
    frame_id: str = "map"
    mars_radius_m: float = MARS_2000_SPHERE_RADIUS_M

    def __post_init__(self) -> None:
        if self.frame_id != "map":
            raise ValueError("frame_id must be 'map'")
        if any(tok in self.frame_id.lower() for tok in FORBIDDEN_CRS_TOKENS):
            raise ValueError("Earth CRS is forbidden in Mars ENU transform")
        if self.row_orientation not in {"south_to_north", "north_to_south"}:
            raise ValueError("row_orientation must be 'south_to_north' or 'north_to_south'")
        if any(type(v) is not int or v <= 0 for v in (self.rows, self.cols)):
            raise ValueError("rows and cols must be positive integers")
        for name in ("origin_lat_deg", "origin_lon_deg", "origin_x_m", "origin_y_m", "resolution_m", "mars_radius_m"):
            val = getattr(self, name)
            if isinstance(val, bool) or not isinstance(val, (int, float)) or not isfinite(val):
                raise ValueError(f"{name} must be a finite number")
        if not (-90.0 <= self.origin_lat_deg <= 90.0):
            raise ValueError("origin_lat_deg out of range [-90, 90]")
        if not (0.0 <= self.origin_lon_deg < 360.0):
            raise ValueError("origin_lon_deg out of range [0, 360)")
        if self.resolution_m <= 0 or self.mars_radius_m <= 0:
            raise ValueError("resolution_m and mars_radius_m must be positive")

    def flat_index(self, row: int, col: int) -> int:
        if not (0 <= row < self.rows and 0 <= col < self.cols):
            raise ValueError(f"cell ({row}, {col}) is outside grid ({self.rows}, {self.cols})")
        return int(row * self.cols + col)

    def row_col_from_index(self, index: int) -> tuple[int, int]:
        if type(index) is not int or not (0 <= index < self.rows * self.cols):
            raise ValueError(f"flat index {index} is outside [0, {self.rows * self.cols})")
        return divmod(index, self.cols)

    def cell_to_enu(self, row: int, col: int) -> tuple[float, float]:
        """Return cell-center (x_east_m, y_north_m) in the local map frame."""
        if not (0 <= row < self.rows and 0 <= col < self.cols):
            raise ValueError(f"cell ({row}, {col}) is outside grid ({self.rows}, {self.cols})")
        x_east_m = self.origin_x_m + (col + 0.5) * self.resolution_m
        if self.row_orientation == "south_to_north":
            y_north_m = self.origin_y_m + (row + 0.5) * self.resolution_m
        else:
            y_north_m = self.origin_y_m + (self.rows - 1 - row + 0.5) * self.resolution_m
        return float(x_east_m), float(y_north_m)

    def enu_to_cell(self, x_east_m: float, y_north_m: float) -> tuple[int, int]:
        """Map local ENU coordinates (x_east_m, y_north_m) to (row, col)."""
        if not (isfinite(x_east_m) and isfinite(y_north_m)):
            raise ValueError("ENU coordinates must be finite")
        col = math.floor((x_east_m - self.origin_x_m) / self.resolution_m)
        rel_y = math.floor((y_north_m - self.origin_y_m) / self.resolution_m)
        row = rel_y if self.row_orientation == "south_to_north" else (self.rows - 1 - rel_y)
        if not (0 <= row < self.rows and 0 <= col < self.cols):
            raise ValueError(f"ENU point ({x_east_m}, {y_north_m}) is outside grid bounds")
        return int(row), int(col)

    def enu_to_planetocentric(self, x_east_m: float, y_north_m: float) -> tuple[float, float]:
        """Convert local tangent/equirectangular ENU (m) to (lat_planetocentric_deg, lon_east_deg)."""
        lat0_rad = math.radians(self.origin_lat_deg)
        dlat_deg = math.degrees(y_north_m / self.mars_radius_m)
        dlon_deg = math.degrees(x_east_m / (self.mars_radius_m * math.cos(lat0_rad)))
        return float(self.origin_lat_deg + dlat_deg), float((self.origin_lon_deg + dlon_deg) % 360.0)

    def planetocentric_to_enu(self, lat_planetocentric_deg: float, lon_east_deg: float) -> tuple[float, float]:
        """Convert (lat_planetocentric_deg, lon_east_deg) to local (x_east_m, y_north_m)."""
        lat0_rad = math.radians(self.origin_lat_deg)
        dlat_rad = math.radians(lat_planetocentric_deg - self.origin_lat_deg)
        dlon_deg = ((lon_east_deg - self.origin_lon_deg + 180.0) % 360.0) - 180.0
        dlon_rad = math.radians(dlon_deg)
        x_east_m = self.mars_radius_m * math.cos(lat0_rad) * dlon_rad
        y_north_m = self.mars_radius_m * dlat_rad
        return float(x_east_m), float(y_north_m)

    def verify_control_points(
        self,
        control_points: list[dict[str, Any]] | tuple[dict[str, Any], ...],
        elevation_grid: np.ndarray,
        *,
        atol_m: float = 1e-3,
        atol_deg: float = 1e-4,
    ) -> None:
        """Verify >=3 non-collinear control points including at least one asymmetric point (row != col)."""
        if len(control_points) < 3:
            raise ValueError("at least 3 control points are required")
        if not any( int(cp["row"]) != int(cp["col"]) for cp in control_points ):
            raise ValueError("control points must include at least one off-diagonal cell (row != col) to detect x/y transpose")

        coords_xy = []
        for cp in control_points:
            row = int(cp["row"])
            col = int(cp["col"])
            x_expected, y_expected = self.cell_to_enu(row, col)
            x_actual = float(cp.get("x_east_m", cp.get("x_m")))
            y_actual = float(cp.get("y_north_m", cp.get("y_m")))
            if abs(x_actual - x_expected) > atol_m or abs(y_actual - y_expected) > atol_m:
                raise ValueError(
                    f"control point ({row}, {col}) ENU mismatch: got ({x_actual}, {y_actual}), "
                    f"expected ({x_expected}, {y_expected})"
                )
            lat_expected, lon_expected = self.enu_to_planetocentric(x_expected, y_expected)
            lat_actual = float(cp["lat_planetocentric_deg"])
            lon_actual = float(cp["lon_east_deg"])
            if abs(lat_actual - lat_expected) > atol_deg or abs(lon_actual - lon_expected) > atol_deg:
                raise ValueError(
                    f"control point ({row}, {col}) lat/lon mismatch: got ({lat_actual}, {lon_actual}), "
                    f"expected ({lat_expected}, {lon_expected})"
                )
            elev_expected = float(elevation_grid[row, col])
            elev_actual = float(cp["elevation_m"])
            if not (isfinite(elev_expected) and isfinite(elev_actual)) or abs(elev_actual - elev_expected) > atol_m:
                raise ValueError(
                    f"control point ({row}, {col}) elevation mismatch: got {elev_actual}, expected {elev_expected}"
                )
            coords_xy.append((x_actual, y_actual))

        # Check non-collinearity across the point set via triangle area > 0
        x0, y0 = coords_xy[0]
        non_collinear = False
        for i in range(1, len(coords_xy)):
            for j in range(i + 1, len(coords_xy)):
                x1, y1 = coords_xy[i]
                x2, y2 = coords_xy[j]
                cross = abs((x1 - x0) * (y2 - y0) - (y1 - y0) * (x2 - x0))
                if cross > 1e-3:
                    non_collinear = True
                    break
        if not non_collinear:
            raise ValueError("control points are collinear; at least 3 non-collinear points are required")


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
    origin_x_m: float = -64.0
    origin_y_m: float = -64.0
    origin_lat_deg: float = 18.45
    origin_lon_deg: float = 77.45
    row_orientation: str = "south_to_north"
    crs: str = "Equirectangular Mars 2000 Sphere IAU (R=3396190 m) local ENU"
    nodata_value: float = float("nan")
    checksum_sha256: str = ""

    def __post_init__(self) -> None:
        if not self.dataset_id or not self.vertical_datum or self.frame_id != "map":
            raise ValueError("dataset, vertical datum and the agreed map frame are required")
        if any(tok in self.crs.lower() or tok in self.vertical_datum.lower() for tok in FORBIDDEN_CRS_TOKENS):
            raise ValueError("terrestrial WGS84/EPSG:4326 datum or CRS is forbidden")
        if any(type(value) is not int or value <= 0 for value in (self.rows, self.cols)):
            raise ValueError("grid dimensions must be positive integers")
        if isinstance(self.resolution_m, bool) or not isfinite(self.resolution_m) or self.resolution_m <= 0:
            raise ValueError("resolution_m must be finite and positive")
        if type(self.map_version) is not int or self.map_version < 0:
            raise ValueError("map_version must be a nonnegative integer")
        if self.row_orientation not in {"south_to_north", "north_to_south"}:
            raise ValueError("row_orientation must be 'south_to_north' or 'north_to_south'")


class ManifestValidator:
    """Validate terrain provenance manifests against data/manifest.schema.json and integrity rules."""

    def __init__(self, schema_path: Path | None = None) -> None:
        if schema_path is None:
            schema_path = _resolve_data_file("data/manifest.schema.json")
        self.schema_path = schema_path
        self.schema = json.loads(self.schema_path.read_text(encoding="utf-8"))
        Draft202012Validator.check_schema(self.schema)
        self._validator = Draft202012Validator(self.schema)

    def validate_document(self, document: dict[str, Any], *, require_ready: bool = True) -> SourceRegistry | None:
        self._validator.validate(document)
        if any(
            tok in str(document.get("vertical_datum", "")).lower()
            or tok in str(document.get("frame_id", "")).lower()
            for tok in FORBIDDEN_CRS_TOKENS
        ):
            raise ValueError("Earth datum/CRS is forbidden in Mars terrain manifest")
        if require_ready:
            if document.get("status") != "ready":
                raise ValueError("manifest status must be 'ready' for operational terrain loading")
            return SourceRegistry.from_manifest_sources(document["sources"])
        return None


@dataclass(frozen=True)
class TerrainTile:
    """Validated public terrain package; never carries evaluator reference rasters."""

    metadata: TerrainMetadata
    transform: GeoTransform
    sources: SourceRegistry
    prior: np.ndarray
    belief: np.ndarray
    sigma: np.ndarray
    nodata_mask: np.ndarray
    observed_mask: np.ndarray
    regional_context_m: np.ndarray | None = None
    control_points: tuple[dict[str, Any], ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        shape = (self.metadata.rows, self.metadata.cols)
        for name in ("prior", "belief", "sigma", "nodata_mask", "observed_mask"):
            arr = getattr(self, name)
            if not isinstance(arr, np.ndarray) or arr.shape != shape:
                raise ValueError(f"{name} must be a 2D numpy array with shape {shape}")
        if self.nodata_mask.dtype != np.bool_ or self.observed_mask.dtype != np.bool_:
            raise ValueError("nodata_mask and observed_mask must be boolean arrays")
        if not np.array_equal(self.nodata_mask, ~np.isfinite(self.prior)):
            raise ValueError("nodata_mask must match non-finite cells of prior")
        if np.any(self.nodata_mask & self.observed_mask):
            raise ValueError("NoData cells cannot be marked as locally observed")
        if self.regional_context_m is not None and self.regional_context_m.shape != shape:
            raise ValueError(f"regional_context_m must have shape {shape}")


def _resolve_data_file(relative_path: str) -> Path:
    """Resolve a repository data file from cwd or ancestor workspace directories."""
    candidate = Path.cwd() / relative_path
    if candidate.is_file():
        return candidate
    for parent in Path(__file__).resolve().parents:
        ws_candidate = parent / relative_path
        if ws_candidate.is_file():
            return ws_candidate
    return Path(__file__).resolve().parents[3] / relative_path


def default_manifest_path() -> Path:
    """Resolve data/sample/manifest.json from the workspace root or current directory."""
    return _resolve_data_file("data/sample/manifest.json")


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_public_terrain(manifest_path: Path | str) -> TerrainTile:
    """Validate provenance, checksums, masks and control points, then load public terrain."""
    manifest_file = Path(manifest_path).resolve()
    if "reference" in [p.name.lower() for p in manifest_file.parents]:
        raise PermissionError("refusing to load evaluator reference data through the public terrain loader")

    document = json.loads(manifest_file.read_text(encoding="utf-8"))
    if document.get("role") == "evaluation_reference":
        raise PermissionError("evaluation_reference manifests cannot be loaded as public terrain")

    validator = ManifestValidator()
    sources = validator.validate_document(document, require_ready=True)
    assert sources is not None

    sample_dir = manifest_file.parent
    # Enforce reference isolation in public directory
    for forbidden_file in sample_dir.glob("*hirise*"):
        raise PermissionError(f"evaluator reference file found in public directory: {forbidden_file.name}")

    terrain_npz_path = sample_dir / "terrain.npz"
    if not terrain_npz_path.is_file():
        raise FileNotFoundError(f"missing public terrain raster archive: {terrain_npz_path}")

    prior_source = sources.by_role("prior")
    actual_sha256 = _sha256_file(terrain_npz_path)
    if actual_sha256 != prior_source.sha256:
        raise ValueError(
            f"SHA-256 mismatch for {terrain_npz_path.name}: expected {prior_source.sha256}, got {actual_sha256}"
        )

    with np.load(terrain_npz_path, allow_pickle=False) as data:
        keys = set(data.files)
        for bad_key in FORBIDDEN_PUBLIC_ARRAY_KEYS:
            if bad_key in keys:
                raise PermissionError(f"public terrain archive contains forbidden reference key: {bad_key}")

        prior = np.array(data["prior" if "prior" in keys else "elevation_m"], dtype=np.float32, copy=True)
        nodata_mask = (
            np.array(data["nodata_mask"], dtype=bool, copy=True)
            if "nodata_mask" in keys
            else ~np.isfinite(prior)
        )
        observed_mask = (
            np.array(data["observed_mask"], dtype=bool, copy=True)
            if "observed_mask" in keys
            else np.zeros_like(nodata_mask, dtype=bool)
        )
        belief = (
            np.array(data["belief"], dtype=np.float32, copy=True)
            if "belief" in keys
            else prior.copy()
        )
        sigma = (
            np.array(data["sigma"], dtype=np.float32, copy=True)
            if "sigma" in keys
            else np.where(~nodata_mask, np.float32(2.5), np.float32(np.inf)).astype(np.float32)
        )
        origin_x_m = float(data["origin_x_m"]) if "origin_x_m" in keys else -0.5 * document["cols"] * document["resolution_m"]
        origin_y_m = float(data["origin_y_m"]) if "origin_y_m" in keys else -0.5 * document["rows"] * document["resolution_m"]
        if "row_orientation" in keys and str(data["row_orientation"]) != document["row_orientation"]:
            raise ValueError("row_orientation in terrain.npz does not match manifest.json")

    # Optional MGS/MOLA regional context verification
    regional_context_m = None
    mola_npz_path = sample_dir / "mola_regional_context.npz"
    if mola_npz_path.is_file():
        mola_source = sources.by_role("regional_context")
        if _sha256_file(mola_npz_path) != mola_source.sha256:
            raise ValueError("SHA-256 mismatch for mola_regional_context.npz")
        with np.load(mola_npz_path, allow_pickle=False) as mola_data:
            regional_context_m = np.array(mola_data["regional_elevation_m"], dtype=np.float32, copy=True)

    transform = GeoTransform(
        origin_lat_deg=float(document["local_origin"]["lat_planetocentric_deg"]),
        origin_lon_deg=float(document["local_origin"]["lon_east_deg"]),
        origin_x_m=origin_x_m,
        origin_y_m=origin_y_m,
        resolution_m=float(document["resolution_m"]),
        rows=int(document["rows"]),
        cols=int(document["cols"]),
        row_orientation=str(document["row_orientation"]),
        frame_id=str(document["frame_id"]),
    )

    control_points: tuple[dict[str, Any], ...] = ()
    details_path = sample_dir / "provenance_details.json"
    if details_path.is_file():
        details = json.loads(details_path.read_text(encoding="utf-8"))
        cpoints = details.get("control_points", [])
        if cpoints:
            transform.verify_control_points(cpoints, prior)
            control_points = tuple(cpoints)

    for arr in (prior, belief, sigma, nodata_mask, observed_mask):
        arr.setflags(write=False)
    if regional_context_m is not None:
        regional_context_m.setflags(write=False)

    metadata = TerrainMetadata(
        dataset_id=str(document["region_id"]),
        rows=int(document["rows"]),
        cols=int(document["cols"]),
        resolution_m=float(document["resolution_m"]),
        vertical_datum=str(document["vertical_datum"]),
        frame_id=str(document["frame_id"]),
        map_version=1,
        origin_x_m=origin_x_m,
        origin_y_m=origin_y_m,
        origin_lat_deg=float(document["local_origin"]["lat_planetocentric_deg"]),
        origin_lon_deg=float(document["local_origin"]["lon_east_deg"]),
        row_orientation=str(document["row_orientation"]),
        checksum_sha256=actual_sha256,
    )

    return TerrainTile(
        metadata=metadata,
        transform=transform,
        sources=sources,
        prior=prior,
        belief=belief,
        sigma=sigma,
        nodata_mask=nodata_mask,
        observed_mask=observed_mask,
        regional_context_m=regional_context_m,
        control_points=control_points,
    )


@dataclass(frozen=True)
class AuxiliaryTerrainLayers:
    """Optional NASA/USGS auxiliary layers aligned cell-for-cell with TerrainTile."""

    manifest: dict[str, Any]
    geology: dict[str, Any]
    ctx_ortho_dn: np.ndarray
    ctx_ortho_norm: np.ndarray
    ctx_ortho_valid_mask: np.ndarray
    slope_deg: np.ndarray
    geology_unit_code: np.ndarray
    geology_rviz_occupancy: np.ndarray
    surface_zone_code: np.ndarray
    surface_zone_rviz_occupancy: np.ndarray
    x_m: np.ndarray
    y_m: np.ndarray
    ctx_ortho_png_path: Path | None = None

    def zone_at_row_col(self, row: int, col: int) -> dict[str, Any]:
        """Return literal surface-facies zone and SIM 3464 geology attributes at (row, col)."""
        rows, cols = self.ctx_ortho_dn.shape
        if not (0 <= row < rows and 0 <= col < cols):
            raise IndexError(f"(row={row}, col={col}) out of bounds for ({rows}, {cols})")

        z_code = int(self.surface_zone_code[row, col])
        z_defs = {int(d["code"]): d for d in self.manifest.get("surface_zones", {}).get("definitions", [])}
        z_info = z_defs.get(z_code, {"id": "unknown", "label": "Unknown", "traversable_agents": []})

        g_code = int(self.geology_unit_code[row, col])
        g_units = {int(u["code"]): u for u in self.geology.get("units", []) if "code" in u}
        g_info = g_units.get(g_code, {"symbol": "unmapped", "name": "Unmapped", "group": "Unmapped"})

        return {
            "row": int(row),
            "col": int(col),
            "x_east_m": float(self.x_m[col]),
            "y_north_m": float(self.y_m[row]),
            "ctx_ortho_dn": int(self.ctx_ortho_dn[row, col]),
            "ctx_ortho_norm": float(self.ctx_ortho_norm[row, col]),
            "slope_deg": float(self.slope_deg[row, col]),
            "surface_zone_code": z_code,
            "surface_zone_id": str(z_info.get("id", "unknown")),
            "surface_zone_label": str(z_info.get("label", "Unknown")),
            "surface_zone_rviz_occupancy": int(self.surface_zone_rviz_occupancy[row, col]),
            "traversable_agents": list(z_info.get("traversable_agents", [])),
            "geology_unit_code": g_code,
            "geology_symbol": str(g_info.get("symbol", "unmapped")),
            "geology_name": str(g_info.get("name", "Unmapped")),
            "geology_rviz_occupancy": int(self.geology_rviz_occupancy[row, col]),
        }


def load_auxiliary_terrain_layers(
    manifest_path: Path | None = None,
    *,
    tile: TerrainTile | None = None,
    strict: bool = False,
) -> AuxiliaryTerrainLayers | None:
    """Load optional NASA/USGS auxiliary terrain layers if present; return None cleanly if absent."""
    target_manifest = Path(manifest_path) if manifest_path is not None else default_manifest_path()
    resolved = target_manifest.resolve()
    if "reference" in [part.lower() for part in resolved.parts]:
        raise PermissionError("Refusing to load evaluator reference data in public auxiliary loader")

    sample_dir = resolved.parent if resolved.name.endswith(".json") else resolved
    aux_manifest_path = (
        resolved if resolved.name == "aux_layers_manifest.json" else sample_dir / "aux_layers_manifest.json"
    )
    aux_npz_path = sample_dir / "jezero_aux_layers.npz"

    if not aux_manifest_path.is_file() or not aux_npz_path.is_file():
        if strict:
            raise FileNotFoundError(f"Auxiliary terrain layers not found in {sample_dir}")
        return None

    for forbidden_file in sample_dir.glob("*hirise*"):
        raise PermissionError(f"Forbidden evaluator reference file in public sample directory: {forbidden_file.name}")

    aux_manifest = json.loads(aux_manifest_path.read_text(encoding="utf-8"))
    files_meta = aux_manifest.get("files") or {}

    expected_npz_sha = (files_meta.get("aux_npz") or {}).get("sha256")
    if not expected_npz_sha or _sha256_file(aux_npz_path) != expected_npz_sha:
        raise ValueError("SHA-256 mismatch for jezero_aux_layers.npz against aux_layers_manifest.json")

    geology_json_path = sample_dir / str((files_meta.get("geology_json") or {}).get("path", "geology.json"))
    expected_geo_sha = (files_meta.get("geology_json") or {}).get("sha256")
    if not geology_json_path.is_file() or (expected_geo_sha and _sha256_file(geology_json_path) != expected_geo_sha):
        raise ValueError("SHA-256 mismatch or missing geology.json for auxiliary layers")
    geology_doc = json.loads(geology_json_path.read_text(encoding="utf-8"))

    ctx_png_name = str((files_meta.get("ctx_ortho_png") or {}).get("path", "ctx_ortho.png"))
    ctx_png_path = sample_dir / ctx_png_name
    expected_png_sha = (files_meta.get("ctx_ortho_png") or {}).get("sha256")
    if ctx_png_path.is_file() and expected_png_sha and _sha256_file(ctx_png_path) != expected_png_sha:
        raise ValueError("SHA-256 mismatch for ctx_ortho.png against aux_layers_manifest.json")

    grid = aux_manifest.get("grid") or {}
    rows = int(grid.get("rows", 0))
    cols = int(grid.get("cols", 0))
    if tile is not None:
        if (rows, cols) != (tile.metadata.rows, tile.metadata.cols):
            raise ValueError(
                f"Auxiliary layer grid ({rows}, {cols}) does not match TerrainTile ({tile.metadata.rows}, {tile.metadata.cols})"
            )
        if not math.isclose(float(grid.get("resolution_m", 0.0)), tile.metadata.resolution_m, rel_tol=1e-6):
            raise ValueError("Auxiliary layer resolution_m does not match TerrainTile")
        if str(aux_manifest.get("row_orientation")) != tile.metadata.row_orientation:
            raise ValueError("Auxiliary layer row_orientation does not match TerrainTile")

    with np.load(aux_npz_path, allow_pickle=False) as data:
        keys = set(data.files)
        forbidden = keys & set(FORBIDDEN_PUBLIC_ARRAY_KEYS)
        if forbidden or any("hirise" in k.lower() or "reference" in k.lower() for k in keys):
            raise PermissionError("jezero_aux_layers.npz contains a forbidden reference key")

        ctx_ortho_dn = np.array(data["ctx_ortho_dn"], dtype=np.uint8, copy=True)
        ctx_ortho_norm = np.array(data["ctx_ortho_norm"], dtype=np.float32, copy=True)
        ctx_ortho_valid_mask = np.array(data["ctx_ortho_valid_mask"], dtype=bool, copy=True)
        slope_deg = np.array(data["slope_deg"], dtype=np.float32, copy=True)
        geology_unit_code = np.array(data["geology_unit_code"], dtype=np.int16, copy=True)
        geology_rviz_occupancy = np.array(data["geology_rviz_occupancy"], dtype=np.int8, copy=True)
        surface_zone_code = np.array(data["surface_zone_code"], dtype=np.int8, copy=True)
        surface_zone_rviz_occupancy = np.array(data["surface_zone_rviz_occupancy"], dtype=np.int8, copy=True)
        x_m = np.array(data["x_m"], dtype=np.float32, copy=True)
        y_m = np.array(data["y_m"], dtype=np.float32, copy=True)

    for arr in (
        ctx_ortho_dn,
        ctx_ortho_norm,
        ctx_ortho_valid_mask,
        slope_deg,
        geology_unit_code,
        geology_rviz_occupancy,
        surface_zone_code,
        surface_zone_rviz_occupancy,
    ):
        if arr.shape != (rows, cols):
            raise ValueError(f"Auxiliary array shape {arr.shape} does not match grid ({rows}, {cols})")
        arr.setflags(write=False)

    x_m.setflags(write=False)
    y_m.setflags(write=False)

    return AuxiliaryTerrainLayers(
        manifest=aux_manifest,
        geology=geology_doc,
        ctx_ortho_dn=ctx_ortho_dn,
        ctx_ortho_norm=ctx_ortho_norm,
        ctx_ortho_valid_mask=ctx_ortho_valid_mask,
        slope_deg=slope_deg,
        geology_unit_code=geology_unit_code,
        geology_rviz_occupancy=geology_rviz_occupancy,
        surface_zone_code=surface_zone_code,
        surface_zone_rviz_occupancy=surface_zone_rviz_occupancy,
        x_m=x_m,
        y_m=y_m,
        ctx_ortho_png_path=ctx_png_path if ctx_png_path.is_file() else None,
    )

