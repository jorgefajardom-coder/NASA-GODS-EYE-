"""Create new provisional raster crops from official USGS/MRO upstream products.

Only CTX is published. HiRISE stays under the ignored evaluator reference tree.
No source code, arrays, scenarios or reported outcomes are imported from Sandbox.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import io
import json
import math
from pathlib import Path
import platform
from functools import lru_cache
import urllib.request

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
BASE = "https://asc-pds-services.s3.us-west-2.amazonaws.com/mosaic/mars2020_trn/"
SOURCES = {
    "CTX": {
        "product_id": "JEZ_ctx_B_soc_008_DTM_MOLAtopography_DeltaGeoid_20m_Eqc_latTs0_lon0",
        "source_url": BASE + "CTX/JEZ_ctx_B_soc_008_DTM_MOLAtopography_DeltaGeoid_20m_Eqc_latTs0_lon0.tif",
        "native_resolution_m": 20.0,
        "doi": "https://doi.org/10.5066/P906QQT8",
        "citation": "Fergason et al. (2020), Mars 2020 Terrain Relative Navigation CTX DTM Mosaic, USGS.",
    },
    "HiRISE": {
        "product_id": "JEZ_hirise_soc_006_DTM_MOLAtopography_DeltaGeoid_1m_Eqc_latTs0_lon0_blend40",
        "source_url": BASE + "HiRISE/JEZ_hirise_soc_006_DTM_MOLAtopography_DeltaGeoid_1m_Eqc_latTs0_lon0_blend40.tif",
        "native_resolution_m": 1.0,
        "doi": "https://doi.org/10.5066/P9REJ9JN",
        "citation": "Fergason et al. (2020), Mars 2020 Terrain Relative Navigation HiRISE DTM Mosaic, USGS.",
    },
}


class HTTPRangeReader(io.RawIOBase):
    """Seekable bounded HTTP reader, avoiding native GDAL curl on Windows.

    Every payload request requires a 206 response. There is no full-file fallback.
    A 32-block LRU retains at most 32 MiB of fetched bytes per open handle.
    """

    def __init__(self, url: str, headers: dict[str, str], block_size: int = 1024 * 1024):
        super().__init__()
        self.url = url
        self.length = int(headers["Content-Length"])
        self.etag = headers.get("ETag")
        self.position = 0
        self.block_size = block_size

    def readable(self):
        return True

    def seekable(self):
        return True

    def tell(self):
        return self.position

    def seek(self, offset, whence=0):
        target = offset if whence == 0 else self.position + offset if whence == 1 else self.length + offset
        if whence not in (0, 1, 2) or target < 0:
            raise ValueError("invalid upstream raster seek")
        self.position = target
        return target

    @lru_cache(maxsize=32)
    def _block(self, index: int) -> bytes:
        start = index * self.block_size
        end = min(start + self.block_size, self.length) - 1
        headers = {"Range": f"bytes={start}-{end}", "Accept-Encoding": "identity"}
        if self.etag:
            headers["If-Match"] = self.etag
        request = urllib.request.Request(self.url, headers=headers)
        with urllib.request.urlopen(request, timeout=90) as response:
            if response.status != 206 or not response.headers.get("Content-Range", "").startswith(f"bytes {start}-{end}/"):
                raise OSError("official upstream did not honor the bounded HTTP Range request")
            payload = response.read(end - start + 2)
        if len(payload) != end - start + 1:
            raise OSError("incomplete or oversized upstream range payload")
        return payload

    def read(self, size=-1):
        if size is None or size < 0:
            size = self.length - self.position
        size = max(0, min(size, self.length - self.position))
        if size > 16 * 1024 * 1024:
            raise OSError("refusing unbounded upstream read; request a raster window")
        end = self.position + size
        result = bytearray()
        while self.position < end:
            block = self._block(self.position // self.block_size)
            offset = self.position % self.block_size
            count = min(len(block) - offset, end - self.position)
            result.extend(block[offset:offset + count])
            self.position += count
        return bytes(result)

    def readinto(self, buffer):
        payload = self.read(len(buffer))
        buffer[:len(payload)] = payload
        return len(payload)


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def south_first(elevation: np.ndarray, valid: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Convert a north-first raster into the ICD's south-first row convention."""
    if elevation.ndim != 2 or valid.shape != elevation.shape:
        raise ValueError("elevation and validity must be matching two-dimensional grids")
    return np.flipud(elevation).copy(), np.flipud(valid).copy()


def control_points(elevation: np.ndarray, *, side_m: float, resolution_m: float,
                   target_crs_wkt: str) -> list[dict]:
    """Three cell-centre checks for consumers, with explicit Mars coordinates."""
    from rasterio.crs import CRS
    from rasterio.warp import transform
    n = elevation.shape[0]
    cells = [(0, 0), (n // 2, n // 2), (n - 1, n - 1)]
    xs = [-side_m / 2 + (col + 0.5) * resolution_m for row, col in cells]
    ys = [-side_m / 2 + (row + 0.5) * resolution_m for row, col in cells]
    longitudes, latitudes = transform(
        CRS.from_wkt(target_crs_wkt), CRS.from_proj4("+proj=longlat +R=3396190 +no_defs"), xs, ys
    )
    return [{"row": row, "col": col, "x_m": x, "y_m": y,
             "elevation_m": float(elevation[row, col]) if np.isfinite(elevation[row, col]) else None,
             "lat_planetocentric_deg": lat, "lon_east_deg": lon % 360}
            for (row, col), x, y, lat, lon in zip(cells, xs, ys, latitudes, longitudes)]


def validate_public_crop(manifest: dict, path: Path) -> None:
    """Validate integrity and the public/reference boundary, not mobility safety."""
    if manifest.get("role") != "prior" or manifest.get("source", {}).get("instrument") != "CTX":
        raise ValueError("only the CTX prior belongs in the public planner crop")
    if manifest.get("row_orientation") != "south_to_north":
        raise ValueError("the public crop must use the ICD south-first row convention")
    if file_sha256(path) != manifest.get("sha256"):
        raise ValueError("public crop checksum mismatch")
    with np.load(path, allow_pickle=False) as dataset:
        expected = {"elevation_m", "valid_mask", "resolution_m", "origin_x_m", "origin_y_m", "row_orientation"}
        if set(dataset.files) != expected:
            raise ValueError("unexpected arrays or missing public crop metadata")
        elevation, valid = dataset["elevation_m"], dataset["valid_mask"]
        if elevation.shape != (manifest["rows"], manifest["cols"]) or valid.shape != elevation.shape:
            raise ValueError("public grid dimensions do not match its manifest")
        if valid.dtype != np.bool_ or not np.array_equal(valid, np.isfinite(elevation)):
            raise ValueError("valid_mask must identify exactly the finite source elevations")
        for name in ("resolution_m", "origin_x_m", "origin_y_m"):
            if float(dataset[name]) != manifest[name]:
                raise ValueError(f"grid metadata mismatch: {name}")
        if str(dataset["row_orientation"]) != manifest["row_orientation"]:
            raise ValueError("raster row convention differs from manifest")


def crop_source(instrument: str, *, latitude: float, longitude: float,
                side_m: float, resolution_m: float) -> tuple[np.ndarray, np.ndarray, dict]:
    """Read only a bounded upstream window, then warp to a local Mars grid."""
    import rasterio
    from rasterio.crs import CRS
    from rasterio.enums import Resampling
    from rasterio.transform import from_origin
    from rasterio.warp import reproject, transform_bounds
    from rasterio.windows import Window, from_bounds

    target_crs = CRS.from_proj4(
        f"+proj=eqc +lat_ts={latitude} +lat_0={latitude} +lon_0={longitude} "
        "+R=3396190 +units=m +no_defs"
    )
    n = round(side_m / resolution_m)
    half = side_m / 2
    north_transform = from_origin(-half, half, resolution_m, resolution_m)
    source_info = SOURCES[instrument]
    env_options = {"GDAL_DISABLE_READDIR_ON_OPEN": "EMPTY_DIR"}
    with urllib.request.urlopen(urllib.request.Request(source_info["source_url"], method="HEAD"), timeout=90) as response:
        upstream_headers = dict(response.headers)
    virtual_name = f"upstream_{instrument}.tif"

    def opener(path, mode="rb"):
        if str(path) != virtual_name:
            raise FileNotFoundError(path)
        return HTTPRangeReader(source_info["source_url"], upstream_headers)

    with rasterio.Env(**env_options):
        with rasterio.open(virtual_name, opener=opener) as source:
            if source.crs is None:
                raise ValueError("the upstream raster has no declared planetary CRS")
            bounds = transform_bounds(target_crs, source.crs, -half, -half, half, half, densify_pts=21)
            fractional = from_bounds(*bounds, transform=source.transform)
            x0, y0 = math.floor(fractional.col_off) - 2, math.floor(fractional.row_off) - 2
            x1 = math.ceil(fractional.col_off + fractional.width) + 2
            y1 = math.ceil(fractional.row_off + fractional.height) + 2
            window = Window(x0, y0, x1 - x0, y1 - y0).intersection(
                Window(0, 0, source.width, source.height)
            )
            raw = source.read(1, window=window, masked=True).astype(np.float32)
            native = raw.filled(np.nan)
            destination = np.full((n, n), np.nan, dtype=np.float32)
            reproject(
                source=native,
                destination=destination,
                src_transform=source.window_transform(window),
                src_crs=source.crs,
                src_nodata=np.nan,
                dst_transform=north_transform,
                dst_crs=target_crs,
                dst_nodata=np.nan,
                resampling=Resampling.bilinear,
            )
            details = {
                "mission": "MRO", "instrument": instrument, **source_info,
                "license_or_terms_url": "https://www.usgs.gov/information-policies-and-instructions/copyrights-and-credits",
                "source_window_col_row_width_height": [int(window.col_off), int(window.row_off), int(window.width), int(window.height)],
                "source_window_values_sha256": hashlib.sha256(native.astype("<f4").tobytes()).hexdigest(),
                "source_shape": [source.height, source.width],
                "source_crs_wkt": source.crs.to_wkt(),
                "source_nodata": str(source.nodata),
                "target_crs_wkt": target_crs.to_wkt(),
                "resampling": "bilinear, GDAL NoData-aware; no synthetic replacement",
                "native_valid_fraction": float(np.isfinite(native).mean()),
                "upstream_etag": upstream_headers.get("ETag"),
                "upstream_last_modified": upstream_headers.get("Last-Modified"),
                "upstream_content_length": int(upstream_headers["Content-Length"]),
                "read_method": "fresh HTTP 206 ranges via bounded urllib reader",
            }
    south, valid = south_first(destination, np.isfinite(destination))
    if not valid.any():
        raise ValueError(f"the {instrument} crop contains no valid upstream elevations")
    return south, valid, details


def save_crop(directory: Path, *, instrument: str, latitude: float, longitude: float,
              side_m: float, resolution_m: float, retrieved_utc: str) -> dict:
    elevation, valid, source = crop_source(
        instrument, latitude=latitude, longitude=longitude, side_m=side_m, resolution_m=resolution_m
    )
    directory.mkdir(parents=True, exist_ok=True)
    half = side_m / 2
    path = directory / "terrain.npz"
    np.savez_compressed(
        path, elevation_m=elevation, valid_mask=valid,
        resolution_m=np.array(resolution_m), origin_x_m=np.array(-half), origin_y_m=np.array(-half),
        row_orientation=np.array("south_to_north"),
    )
    manifest = {
        "schema_version": 1, "status": "provisional",
        "dataset_type": "NEW_DERIVATIVE_OF_OFFICIAL_MRO_PRODUCT",
        "role": "prior" if instrument == "CTX" else "evaluation_reference",
        "knowledge_state": "orbital_prior_not_locally_verified" if instrument == "CTX" else "held_out_evaluator_reference",
        "dataset_id": f"jezero_planner_{instrument.lower()}_{elevation.shape[0]}",
        "frame_id": "map", "rows": elevation.shape[0], "cols": elevation.shape[1],
        "resolution_m": resolution_m, "origin_x_m": -half, "origin_y_m": -half,
        "row_orientation": "south_to_north", "vertical_units": "m",
        "vertical_datum": "MOLA topography / DeltaGeoid from source product; no Earth datum conversion",
        "local_origin": {"lat_planetocentric_deg": latitude, "lon_east_deg": longitude},
        "mars_sphere_radius_m": 3396190,
        "retrieved_utc": retrieved_utc,
        "processed_utc": datetime.now(timezone.utc).isoformat(),
        "artifact": "terrain.npz", "sha256": file_sha256(path),
        "valid_fraction": float(valid.mean()), "source": source,
        "control_points": control_points(elevation, side_m=side_m, resolution_m=resolution_m,
                                          target_crs_wkt=source["target_crs_wkt"]),
        "processing_versions": {"python": platform.python_version(), "numpy": np.__version__},
        "limitations": [
            "A valid DEM sample is not a locally observed or verified corridor.",
            "No mobility, soil mechanics, EVA or drone flight certification.",
            "Computational resampling creates no additional native spatial information.",
            "CTX and HiRISE are both MRO instruments; no multi-mission claim.",
        ],
    }
    import rasterio
    manifest["processing_versions"]["rasterio"] = rasterio.__version__
    manifest["processing_versions"]["gdal"] = rasterio.__gdal_version__
    (directory / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    if instrument == "CTX":
        validate_public_crop(manifest, path)
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--latitude", type=float, default=18.45)
    parser.add_argument("--longitude", type=float, default=77.45)
    parser.add_argument("--side-m", type=float, default=128.0)
    parser.add_argument("--resolution-m", type=float, default=4.0)
    parser.add_argument("--public-dir", type=Path, default=ROOT / "data/planner_provisional")
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()
    if not all(math.isfinite(v) for v in (args.latitude, args.longitude, args.side_m, args.resolution_m)):
        parser.error("all coordinates and dimensions must be finite")
    if not -90 < args.latitude < 90 or not 0 <= args.longitude < 360:
        parser.error("Mars latitude/longitude are out of range")
    if args.resolution_m <= 0 or args.side_m <= 0:
        parser.error("side and resolution must be positive")
    cells = args.side_m / args.resolution_m
    if not math.isclose(cells, round(cells)) or not 4 <= cells <= 512:
        parser.error("side/resolution must be an integer from 4 to 512")
    reference_dir = ROOT / "data/reference/planner_provisional"
    public_dir = args.public_dir.resolve()
    if public_dir == reference_dir.resolve() or public_dir in reference_dir.resolve().parents or reference_dir.resolve() in public_dir.parents:
        parser.error("public and evaluator-reference directories must be separate")
    for directory in (public_dir, reference_dir):
        if not args.overwrite and ((directory / "manifest.json").exists() or (directory / "terrain.npz").exists()):
            parser.error(f"{directory} already has an artifact; choose a new public path or explicitly --overwrite")
    acquired = datetime.now(timezone.utc).isoformat()
    for instrument, directory in (("CTX", public_dir), ("HiRISE", reference_dir)):
        result = save_crop(directory, instrument=instrument, latitude=args.latitude, longitude=args.longitude,
                           side_m=args.side_m, resolution_m=args.resolution_m, retrieved_utc=acquired)
        print(json.dumps({"instrument": instrument, "role": result["role"], "shape": [result["rows"], result["cols"]],
                          "valid_fraction": result["valid_fraction"], "sha256": result["sha256"], "directory": str(directory)}), flush=True)


if __name__ == "__main__":
    main()
