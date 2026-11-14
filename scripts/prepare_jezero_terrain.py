"""Prepare the multi-mission Jezero terrain package from official NASA/USGS sources.

Sources ingested via bounded HTTP 206 range reads:
1. MRO / CTX DTM (prior, 20 m native): DOI 10.5066/P906QQT8
2. MRO / HiRISE DTM (evaluation_reference, 1 m native, isolated in data/reference/): DOI 10.5066/P9REJ9JN
3. Mars Global Surveyor / MOLA MEGDR DEM (regional_context, 463 m native): PDS urn:nasa:pds:mgs_mola_topography_derived::1.0
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from functools import lru_cache
import hashlib
import io
import json
import math
from pathlib import Path
import platform
import struct
import sys
import urllib.request
import zlib

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
S3_BASE = "https://asc-pds-services.s3.us-west-2.amazonaws.com/mosaic/"

SOURCES = {
    "CTX": {
        "mission": "MRO",
        "instrument": "CTX",
        "role": "prior",
        "product_id": "JEZ_ctx_B_soc_008_DTM_MOLAtopography_DeltaGeoid_20m_Eqc_latTs0_lon0",
        "source_url": S3_BASE + "mars2020_trn/CTX/JEZ_ctx_B_soc_008_DTM_MOLAtopography_DeltaGeoid_20m_Eqc_latTs0_lon0.tif",
        "native_resolution_m": 20.0,
        "doi": "https://doi.org/10.5066/P906QQT8",
        "citation": "Fergason et al. (2020), Mars 2020 Terrain Relative Navigation CTX DTM Mosaic, USGS Astrogeology Science Center.",
        "license_or_terms_url": "https://www.usgs.gov/information-policies-and-instructions/copyrights-and-credits",
    },
    "HiRISE": {
        "mission": "MRO",
        "instrument": "HiRISE",
        "role": "evaluation_reference",
        "product_id": "JEZ_hirise_soc_006_DTM_MOLAtopography_DeltaGeoid_1m_Eqc_latTs0_lon0_blend40",
        "source_url": S3_BASE + "mars2020_trn/HiRISE/JEZ_hirise_soc_006_DTM_MOLAtopography_DeltaGeoid_1m_Eqc_latTs0_lon0_blend40.tif",
        "native_resolution_m": 1.0,
        "doi": "https://doi.org/10.5066/P9REJ9JN",
        "citation": "Fergason et al. (2020), Mars 2020 Terrain Relative Navigation HiRISE DTM Mosaic, USGS Astrogeology Science Center.",
        "license_or_terms_url": "https://www.usgs.gov/information-policies-and-instructions/copyrights-and-credits",
    },
    "MOLA": {
        "mission": "Mars Global Surveyor",
        "instrument": "MOLA",
        "role": "regional_context",
        "product_id": "Mars_MGS_MOLA_DEM_mosaic_global_463m (urn:nasa:pds:mgs_mola_topography_derived::1.0)",
        "source_url": S3_BASE + "Mars_MGS_MOLA_DEM_mosaic_global_463m.tif",
        "fallback_urls": [
            "https://planetarymaps.usgs.gov/mosaic/Mars_MGS_MOLA_DEM_mosaic_global_463m.tif",
        ],
        "native_resolution_m": 463.0,
        "pds_bundle": "urn:nasa:pds:mgs_mola_topography_derived::1.0",
        "citation": "Smith et al. (2001), Mars Orbiter Laser Altimeter (MOLA) MEGDR Global DEM 463m, NASA PDS / USGS Astrogeology.",
        "license_or_terms_url": "https://www.usgs.gov/information-policies-and-instructions/copyrights-and-credits",
    },
}

MARS_RADIUS_M = 3396190.0
DEFAULT_PRIOR_SIGMA_M = 2.5
DEFAULT_LATITUDE_DEG = 18.45
DEFAULT_LONGITUDE_DEG = 77.45
DEFAULT_SIDE_M = 128.0
DEFAULT_RESOLUTION_M = 4.0
AGENT_SLOPE_LIMITS_DEG = {"human": 10.0, "rover": 20.0, "drone": 90.0}
DEFAULT_JEZERO_BOUNDS = {
    "lat_min_deg": 18.3068,
    "lat_max_deg": 18.6693,
    "lon_min_deg": 77.2229,
    "lon_max_deg": 77.5840,
}


class HTTPRangeReader(io.RawIOBase):
    """Seekable bounded HTTP 206 range reader for cloud-optimized/tiled planetary GeoTIFFs."""

    def __init__(self, url: str, headers: dict[str, str], block_size: int = 1024 * 1024):
        super().__init__()
        self.url = url
        self.length = int(headers["Content-Length"])
        self.etag = headers.get("ETag")
        self.position = 0
        self.block_size = block_size

    def readable(self) -> bool:
        return True

    def seekable(self) -> bool:
        return True

    def tell(self) -> int:
        return self.position

    def seek(self, offset: int, whence: int = 0) -> int:
        if whence == 0:
            target = offset
        elif whence == 1:
            target = self.position + offset
        elif whence == 2:
            target = self.length + offset
        else:
            raise ValueError(f"invalid whence: {whence}")
        if target < 0:
            raise ValueError("negative seek offset")
        self.position = target
        return target

    @lru_cache(maxsize=64)
    def _block(self, index: int) -> bytes:
        start = index * self.block_size
        end = min(start + self.block_size, self.length) - 1
        headers = {"Range": f"bytes={start}-{end}", "Accept-Encoding": "identity"}
        if self.etag:
            headers["If-Match"] = self.etag
        request = urllib.request.Request(self.url, headers=headers)
        with urllib.request.urlopen(request, timeout=90) as response:
            if response.status != 206:
                raise OSError(f"upstream server did not return HTTP 206 (got {response.status})")
            payload = response.read(end - start + 2)
        if len(payload) != end - start + 1:
            raise OSError("incomplete or oversized HTTP 206 range payload")
        return payload

    def read(self, size: int = -1) -> bytes:
        if size is None or size < 0:
            size = self.length - self.position
        size = max(0, min(size, self.length - self.position))
        if size > 32 * 1024 * 1024:
            raise OSError("refusing unbounded upstream read; request a bounded window")
        end = self.position + size
        result = bytearray()
        while self.position < end:
            block = self._block(self.position // self.block_size)
            offset = self.position % self.block_size
            count = min(len(block) - offset, end - self.position)
            result.extend(block[offset:offset + count])
            self.position += count
        return bytes(result)

    def readinto(self, buffer: bytearray | memoryview) -> int:
        payload = self.read(len(buffer))
        buffer[:len(payload)] = payload
        return len(payload)


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def south_first(elevation: np.ndarray, valid: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Convert a north-up raster (row 0 = north) into ICD south-to-north order (row 0 = south)."""
    if elevation.ndim != 2 or valid.shape != elevation.shape:
        raise ValueError("elevation and validity must be matching 2D grids")
    return np.flipud(elevation).copy(), np.flipud(valid).copy()


def resolve_upstream(source_info: dict) -> tuple[str, dict[str, str]]:
    urls = [source_info["source_url"], *source_info.get("fallback_urls", [])]
    last_err = None
    for url in urls:
        try:
            req = urllib.request.Request(url, method="HEAD")
            with urllib.request.urlopen(req, timeout=60) as resp:
                return resp.url, dict(resp.headers)
        except Exception as exc:  # noqa: BLE001
            last_err = exc
    raise RuntimeError(f"failed to reach upstream URLs for {source_info['instrument']}: {last_err}")


def crop_source(
    key: str,
    *,
    latitude: float,
    longitude: float,
    side_m: float,
    resolution_m: float,
    padding_pixels: int = 3,
) -> tuple[np.ndarray, np.ndarray, dict]:
    """Fetch bounded upstream window and reproject to Mars-local Equirectangular ENU grid."""
    import rasterio
    from rasterio.crs import CRS
    from rasterio.enums import Resampling
    from rasterio.transform import from_origin
    from rasterio.warp import reproject, transform_bounds
    from rasterio.windows import Window, from_bounds

    target_crs = CRS.from_proj4(
        f"+proj=eqc +lat_ts={latitude} +lat_0={latitude} +lon_0={longitude} "
        f"+R={int(MARS_RADIUS_M)} +units=m +no_defs"
    )
    n = round(side_m / resolution_m)
    half = side_m / 2.0
    north_transform = from_origin(-half, half, resolution_m, resolution_m)
    source_info = SOURCES[key]
    resolved_url, upstream_headers = resolve_upstream(source_info)
    virtual_name = f"upstream_{key}.tif"

    def opener(path, mode="rb"):
        if str(path) != virtual_name:
            raise FileNotFoundError(path)
        return HTTPRangeReader(resolved_url, upstream_headers)

    with rasterio.Env(GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR"):
        with rasterio.open(virtual_name, opener=opener) as src:
            if src.crs is None:
                raise ValueError(f"upstream {key} raster has no declared planetary CRS")
            bounds = transform_bounds(target_crs, src.crs, -half, -half, half, half, densify_pts=21)
            fractional = from_bounds(*bounds, transform=src.transform)
            x0 = math.floor(fractional.col_off) - padding_pixels
            y0 = math.floor(fractional.row_off) - padding_pixels
            x1 = math.ceil(fractional.col_off + fractional.width) + padding_pixels
            y1 = math.ceil(fractional.row_off + fractional.height) + padding_pixels
            window = Window(x0, y0, max(4, x1 - x0), max(4, y1 - y0)).intersection(
                Window(0, 0, src.width, src.height)
            )
            raw = src.read(1, window=window, masked=True).astype(np.float32)
            native = raw.filled(np.nan)
            destination = np.full((n, n), np.nan, dtype=np.float32)
            reproject(
                source=native,
                destination=destination,
                src_transform=src.window_transform(window),
                src_crs=src.crs,
                src_nodata=np.nan,
                dst_transform=north_transform,
                dst_crs=target_crs,
                dst_nodata=np.nan,
                resampling=Resampling.bilinear,
            )
            native_valid = native[np.isfinite(native)]
            details = {
                "mission": source_info["mission"],
                "instrument": source_info["instrument"],
                "role": source_info["role"],
                "product_id": source_info["product_id"],
                "source_url": resolved_url,
                "license_or_terms_url": source_info["license_or_terms_url"],
                "native_resolution_m": source_info["native_resolution_m"],
                "citation": source_info["citation"],
                "source_window_col_row_width_height": [
                    int(window.col_off),
                    int(window.row_off),
                    int(window.width),
                    int(window.height),
                ],
                "source_window_values_sha256": hashlib.sha256(native.astype("<f4").tobytes()).hexdigest(),
                "source_shape": [int(src.height), int(src.width)],
                "source_crs_wkt": src.crs.to_wkt(),
                "source_nodata": str(src.nodata),
                "target_crs_wkt": target_crs.to_wkt(),
                "resampling": "bilinear, GDAL NoData-aware; no synthetic replacement",
                "native_valid_fraction": float(np.isfinite(native).mean()),
                "native_min_m": float(native_valid.min()) if native_valid.size else None,
                "native_max_m": float(native_valid.max()) if native_valid.size else None,
                "native_mean_m": float(native_valid.mean()) if native_valid.size else None,
                "upstream_etag": upstream_headers.get("ETag"),
                "upstream_last_modified": upstream_headers.get("Last-Modified"),
                "upstream_content_length": int(upstream_headers["Content-Length"]),
                "read_method": "fresh HTTP 206 ranges via bounded urllib reader",
            }
    south_elev, valid_mask = south_first(destination, np.isfinite(destination))
    if not valid_mask.any():
        raise ValueError(f"the {key} crop contains no valid upstream elevations")
    return south_elev, valid_mask, details


def compute_control_points(
    elevation: np.ndarray,
    *,
    origin_x_m: float,
    origin_y_m: float,
    resolution_m: float,
    target_crs_wkt: str,
) -> list[dict]:
    """Compute 4 non-collinear ENU control points including asymmetric off-diagonal cells (row != col)."""
    from rasterio.crs import CRS
    from rasterio.warp import transform

    rows, cols = elevation.shape
    # Include SW corner (0,0), two strongly asymmetric off-diagonal points (5,26) and (25,6), and NE corner (31,31)
    spec = [
        ("cp_sw_origin", 0, 0),
        ("cp_se_offdiag", min(5, rows - 1), min(26, cols - 1)),
        ("cp_nw_offdiag", min(25, rows - 1), min(6, cols - 1)),
        ("cp_ne_corner", rows - 1, cols - 1),
    ]
    xs = [origin_x_m + (col + 0.5) * resolution_m for _, _, col in spec]
    ys = [origin_y_m + (row + 0.5) * resolution_m for _, row, _ in spec]
    longitudes, latitudes = transform(
        CRS.from_wkt(target_crs_wkt),
        CRS.from_proj4(f"+proj=longlat +R={int(MARS_RADIUS_M)} +no_defs"),
        xs,
        ys,
    )
    points = []
    for (cp_id, row, col), x_m, y_m, lat, lon in zip(spec, xs, ys, latitudes, longitudes):
        val = float(elevation[row, col]) if np.isfinite(elevation[row, col]) else None
        points.append(
            {
                "id": cp_id,
                "row": int(row),
                "col": int(col),
                "x_east_m": float(x_m),
                "y_north_m": float(y_m),
                "elevation_m": val,
                "lat_planetocentric_deg": float(lat),
                "lon_east_deg": float(lon % 360.0),
            }
        )
    return points


def write_grayscale_png(path: Path, array: np.ndarray, scale_factor: int = 4) -> None:
    """Write a deterministic 8-bit grayscale preview PNG from a 2D elevation array (north-up view)."""
    north_up = np.flipud(array)
    finite = np.isfinite(north_up)
    if finite.any():
        vmin = float(north_up[finite].min())
        vmax = float(north_up[finite].max())
        span = max(vmax - vmin, 1e-6)
        norm = np.where(finite, (north_up - vmin) / span, 0.0)
    else:
        norm = np.zeros_like(north_up, dtype=np.float32)
    pixels = np.clip(np.round(norm * 255.0), 0, 255).astype(np.uint8)
    if scale_factor > 1:
        pixels = np.repeat(np.repeat(pixels, scale_factor, axis=0), scale_factor, axis=1)
    height, width = pixels.shape

    def chunk(tag: bytes, data: bytes) -> bytes:
        crc = zlib.crc32(tag + data) & 0xFFFFFFFF
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", crc)

    raw_rows = b"".join(b"\x00" + pixels[r].tobytes() for r in range(height))
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 0, 0, 0, 0)
    png_bytes = (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", ihdr)
        + chunk(b"IDAT", zlib.compress(raw_rows, level=9))
        + chunk(b"IEND", b"")
    )
    path.write_bytes(png_bytes)


def validate_request_params(
    latitude: float,
    longitude: float,
    *,
    side_m: float = DEFAULT_SIDE_M,
    resolution_m: float = DEFAULT_RESOLUTION_M,
) -> None:
    if not all(math.isfinite(v) for v in (latitude, longitude, side_m, resolution_m)):
        raise ValueError("all coordinates and dimensions must be finite")
    if not -90.0 < latitude < 90.0 or not 0.0 <= longitude < 360.0:
        raise ValueError("Mars latitude (-90, 90) or east longitude [0, 360) is out of range")
    if resolution_m <= 0.0 or side_m <= 0.0:
        raise ValueError("side_m and resolution_m must be positive")
    cells = side_m / resolution_m
    if not math.isclose(cells, round(cells)) or not 4 <= cells <= 512:
        raise ValueError("side_m / resolution_m must be an integer between 4 and 512")


def query_available_coverage(keys: tuple[str, ...] = ("CTX", "HiRISE")) -> dict[str, Any]:
    """Read upstream GeoTIFF headers via HTTP 206 ranges to report valid Mars lat/lon bounds."""
    import rasterio
    from rasterio.crs import CRS
    from rasterio.warp import transform_bounds

    lonlat_crs = CRS.from_proj4(f"+proj=longlat +R={int(MARS_RADIUS_M)} +no_defs")
    per_source: dict[str, dict[str, float]] = {}

    for key in keys:
        source_info = SOURCES[key]
        resolved_url, upstream_headers = resolve_upstream(source_info)
        virtual_name = f"header_{key}.tif"

        def opener(path, mode="rb", url=resolved_url, headers=upstream_headers, expected=virtual_name):
            if str(path) != expected:
                raise FileNotFoundError(path)
            return HTTPRangeReader(url, headers)

        with rasterio.Env(GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR"):
            with rasterio.open(virtual_name, opener=opener) as src:
                if src.crs is None:
                    raise ValueError(f"upstream {key} raster has no declared planetary CRS")
                west, south, east, north = transform_bounds(src.crs, lonlat_crs, *src.bounds, densify_pts=21)
                per_source[key] = {
                    "lat_min_deg": float(south),
                    "lat_max_deg": float(north),
                    "lon_min_deg": float(west % 360.0),
                    "lon_max_deg": float(east % 360.0),
                }

    intersection = {
        "lat_min_deg": max(v["lat_min_deg"] for v in per_source.values()),
        "lat_max_deg": min(v["lat_max_deg"] for v in per_source.values()),
        "lon_min_deg": max(v["lon_min_deg"] for v in per_source.values()),
        "lon_max_deg": min(v["lon_max_deg"] for v in per_source.values()),
    }
    return {"sources": per_source, "intersection": intersection}


def is_window_valid(
    latitude: float,
    longitude: float,
    *,
    side_m: float = DEFAULT_SIDE_M,
    resolution_m: float = DEFAULT_RESOLUTION_M,
    min_valid_fraction: float = 1.0,
) -> bool:
    """Return True if both CTX and HiRISE have >= min_valid_fraction valid data in the window."""
    for key in ("CTX", "HiRISE"):
        try:
            _, valid_mask, _ = crop_source(
                key, latitude=latitude, longitude=longitude, side_m=side_m, resolution_m=resolution_m
            )
        except ValueError:
            return False
        if float(valid_mask.mean()) < min_valid_fraction:
            return False
    return True


def snap_to_valid_coordinates(
    latitude: float,
    longitude: float,
    *,
    bounds: dict[str, float] | None,
    side_m: float = DEFAULT_SIDE_M,
    resolution_m: float = DEFAULT_RESOLUTION_M,
) -> tuple[float, float]:
    """Adjust out-of-coverage or NoData-edge coordinates toward the valid mosaic interior."""
    if bounds is not None:
        lat = min(max(latitude, bounds["lat_min_deg"]), bounds["lat_max_deg"])
        lon = min(max(longitude, bounds["lon_min_deg"]), bounds["lon_max_deg"])
        center_lat = 0.5 * (bounds["lat_min_deg"] + bounds["lat_max_deg"])
        center_lon = 0.5 * (bounds["lon_min_deg"] + bounds["lon_max_deg"])
    else:
        lat, lon = latitude, longitude
        center_lat, center_lon = DEFAULT_LATITUDE_DEG, DEFAULT_LONGITUDE_DEG

    if is_window_valid(lat, lon, side_m=side_m, resolution_m=resolution_m, min_valid_fraction=1.0):
        return lat, lon

    if not is_window_valid(center_lat, center_lon, side_m=side_m, resolution_m=resolution_m, min_valid_fraction=1.0):
        center_lat, center_lon = DEFAULT_LATITUDE_DEG, DEFAULT_LONGITUDE_DEG

    # Binary search along the segment from requested (lat, lon) to valid interior (center_lat, center_lon)
    lo, hi = 0.0, 1.0
    best_lat, best_lon = center_lat, center_lon
    for _ in range(8):
        mid = 0.5 * (lo + hi)
        cand_lat = lat + mid * (center_lat - lat)
        cand_lon = lon + mid * (center_lon - lon)
        if is_window_valid(cand_lat, cand_lon, side_m=side_m, resolution_m=resolution_m, min_valid_fraction=1.0):
            best_lat, best_lon = cand_lat, cand_lon
            hi = mid
        else:
            lo = mid
    return round(best_lat, 6), round(best_lon, 6)


def prompt_custom_region(
    *,
    default_lat: float = DEFAULT_LATITUDE_DEG,
    default_lon: float = DEFAULT_LONGITUDE_DEG,
    default_side_m: float = DEFAULT_SIDE_M,
    resolution_m: float = DEFAULT_RESOLUTION_M,
    bounds: dict[str, float] = DEFAULT_JEZERO_BOUNDS,
) -> tuple[float, float, float]:
    """Prompt step-by-step for scale, latitude, and longitude using cached Jezero bounds."""
    size_options = {"1": 128.0, "128": 128.0, "2": 256.0, "256": 256.0, "3": 512.0, "4": 512.0, "512": 512.0}
    print(f"Escalas ({resolution_m:.1f} m/celda): 1 = 128m (32x32) | 2 = 256m (64x64) | 3 = 512m (128x128)")
    while True:
        raw_size = input(f"Elige escala [1, 2, 3] (o 'escala,lat,lon') [Enter = 1 / {int(default_side_m)}m]: ").strip()
        if "," in raw_size:
            parts = [p.strip() for p in raw_size.split(",")]
            if len(parts) == 3 and parts[0] in size_options:
                try:
                    chosen_side_m = size_options[parts[0]]
                    lat = float(parts[1])
                    lon = float(parts[2])
                    validate_request_params(lat, lon, side_m=chosen_side_m, resolution_m=resolution_m)
                    adj_lat, adj_lon = snap_to_valid_coordinates(
                        lat, lon, bounds=bounds, side_m=chosen_side_m, resolution_m=resolution_m
                    )
                    if (adj_lat, adj_lon) != (lat, lon):
                        print(f"Ajuste automatico: ({lat}, {lon}) -> ({adj_lat}, {adj_lon}) (borde NoData).")
                    return adj_lat, adj_lon, chosen_side_m
                except ValueError as exc:
                    print(f"Entrada invalida ({exc}). Intenta de nuevo.")
                    continue
        if not raw_size:
            chosen_side_m = default_side_m
            break
        if raw_size in size_options:
            chosen_side_m = size_options[raw_size]
            break
        print("Opcion invalida. Escribe 1, 2, 3 o presiona Enter.")

    while True:
        raw_lat = input(
            f"Latitud deg N [rango {bounds['lat_min_deg']:.4f} a {bounds['lat_max_deg']:.4f}] [Enter = {default_lat}]: "
        ).strip()
        raw_lon = input(
            f"Longitud deg E [rango {bounds['lon_min_deg']:.4f} a {bounds['lon_max_deg']:.4f}] [Enter = {default_lon}]: "
        ).strip()
        try:
            lat = default_lat if not raw_lat else float(raw_lat)
            lon = default_lon if not raw_lon else float(raw_lon)
            validate_request_params(lat, lon, side_m=chosen_side_m, resolution_m=resolution_m)
            adj_lat, adj_lon = snap_to_valid_coordinates(
                lat, lon, bounds=bounds, side_m=chosen_side_m, resolution_m=resolution_m
            )
            if (adj_lat, adj_lon) != (lat, lon):
                print(
                    f"Ajuste automatico: ({lat}, {lon}) cae fuera o en borde NoData; "
                    f"se movio a zona detectable ({adj_lat}, {adj_lon})."
                )
            return adj_lat, adj_lon, chosen_side_m
        except ValueError as exc:
            print(f"Entrada invalida ({exc}). Intenta de nuevo.")


def request_region_params(
    *,
    interactive: bool,
    latitude: float | None,
    longitude: float | None,
    side_m: float = DEFAULT_SIDE_M,
    resolution_m: float = DEFAULT_RESOLUTION_M,
) -> tuple[float, float, float]:
    """Decoupled region parameter provider (latitude, longitude, side_m)."""
    if not interactive:
        lat = DEFAULT_LATITUDE_DEG if latitude is None else float(latitude)
        lon = DEFAULT_LONGITUDE_DEG if longitude is None else float(longitude)
        validate_request_params(lat, lon, side_m=side_m, resolution_m=resolution_m)
        return lat, lon, side_m
    return prompt_custom_region(
        default_lat=DEFAULT_LATITUDE_DEG if latitude is None else float(latitude),
        default_lon=DEFAULT_LONGITUDE_DEG if longitude is None else float(longitude),
        default_side_m=side_m,
        resolution_m=resolution_m,
    )


def request_coordinates(
    *,
    interactive: bool,
    latitude: float | None,
    longitude: float | None,
    side_m: float = DEFAULT_SIDE_M,
    resolution_m: float = DEFAULT_RESOLUTION_M,
) -> tuple[float, float]:
    """Backward-compatible wrapper returning (latitude, longitude)."""
    lat, lon, _ = request_region_params(
        interactive=interactive,
        latitude=latitude,
        longitude=longitude,
        side_m=side_m,
        resolution_m=resolution_m,
    )
    return lat, lon


def estimate_traversability_summary(
    elevation: np.ndarray, valid_mask: np.ndarray, resolution_m: float
) -> dict[str, Any]:
    """Estimate valid elevation range and slope-based traversability fractions."""
    valid_elev = elevation[valid_mask]
    gy, gx = np.gradient(elevation, resolution_m, resolution_m)
    slope_deg = np.degrees(np.arctan(np.hypot(gx, gy)))
    admissible: dict[str, float] = {}
    total = float(elevation.size)
    for kind, limit in AGENT_SLOPE_LIMITS_DEG.items():
        ok = valid_mask & np.isfinite(slope_deg) & (slope_deg <= limit)
        admissible[kind] = round(float(ok.sum()) / total, 4)
    return {
        "valid_fraction": round(float(valid_mask.mean()), 4),
        "elevation_min_m": float(valid_elev.min()) if valid_elev.size else None,
        "elevation_max_m": float(valid_elev.max()) if valid_elev.size else None,
        "admissible_fraction_by_kind": admissible,
    }


def sync_terrain_yml(
    config_path: Path,
    *,
    region_id: str,
    latitude: float,
    longitude: float,
    side_m: float,
    resolution_m: float,
    rows: int,
    cols: int,
    vertical_datum: str,
    control_points: list[dict[str, Any]],
) -> None:
    """Update config/terrain.yml to match the newly generated data/sample package."""
    half = side_m / 2.0
    lines = [
        "# Validated public Jezero terrain configuration and shared ENU control points.",
        "# Evaluator reference (HiRISE) is deliberately isolated in data/reference/ and absent here.",
        'schema_version: "1.0.0"',
        "status: ready",
        f"region_id: {region_id}",
        "frame_id: map",
        "manifest_path: data/sample/manifest.json",
        "provenance_details_path: data/sample/provenance_details.json",
        "preview_path: data/sample/preview_ctx_prior.png",
        "prior_path: data/sample/terrain.npz#prior",
        "belief_path: data/sample/terrain.npz#belief",
        "sigma_path: data/sample/terrain.npz#sigma",
        "nodata_mask_path: data/sample/terrain.npz#nodata_mask",
        "observed_mask_path: data/sample/terrain.npz#observed_mask",
        "regional_context_path: data/sample/mola_regional_context.npz#regional_elevation_m",
        "",
        "grid:",
        f"  rows: {rows}",
        f"  cols: {cols}",
        f"  resolution_m: {float(resolution_m)}",
        f"  origin_x_m: {-half}",
        f"  origin_y_m: {-half}",
        "  row_orientation: south_to_north",
        f"  origin_lat_planetocentric_deg: {float(latitude)}",
        f"  origin_lon_east_deg: {float(longitude)}",
        f"  mars_sphere_radius_m: {float(MARS_RADIUS_M)}",
        "  vertical_units: m",
        f'  vertical_datum: "{vertical_datum}"',
        f"  default_prior_sigma_m: {float(DEFAULT_PRIOR_SIGMA_M)}",
        "",
        "control_points:",
    ]
    for cp in control_points:
        lines.extend([
            f"  - id: {cp['id']}",
            f"    row: {cp['row']}",
            f"    col: {cp['col']}",
            f"    x_east_m: {cp['x_east_m']}",
            f"    y_north_m: {cp['y_north_m']}",
            f"    elevation_m: {cp['elevation_m']}",
            f"    lat_planetocentric_deg: {cp['lat_planetocentric_deg']}",
            f"    lon_east_deg: {cp['lon_east_deg']}",
        ])
    config_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_package(
    *,
    latitude: float = DEFAULT_LATITUDE_DEG,
    longitude: float = DEFAULT_LONGITUDE_DEG,
    side_m: float = DEFAULT_SIDE_M,
    resolution_m: float = DEFAULT_RESOLUTION_M,
    region_id: str = "jezero_mvp",
    sample_dir: Path = ROOT / "data/sample",
    reference_dir: Path = ROOT / "data/reference",
) -> dict:
    import rasterio

    retrieved_utc = datetime.now(timezone.utc).isoformat()
    ctx_elev, ctx_valid, ctx_details = crop_source(
        "CTX", latitude=latitude, longitude=longitude, side_m=side_m, resolution_m=resolution_m
    )
    hirise_elev, hirise_valid, hirise_details = crop_source(
        "HiRISE", latitude=latitude, longitude=longitude, side_m=side_m, resolution_m=resolution_m
    )
    mola_elev, mola_valid, mola_details = crop_source(
        "MOLA",
        latitude=latitude,
        longitude=longitude,
        side_m=side_m,
        resolution_m=resolution_m,
        padding_pixels=6,
    )

    rows, cols = ctx_elev.shape
    origin_x_m = -side_m / 2.0
    origin_y_m = -side_m / 2.0

    nodata_mask = ~ctx_valid
    observed_mask = np.zeros((rows, cols), dtype=bool)
    prior = ctx_elev.astype(np.float32)
    belief = prior.copy()
    sigma = np.where(ctx_valid, np.float32(DEFAULT_PRIOR_SIGMA_M), np.float32(np.inf)).astype(np.float32)

    sample_dir.mkdir(parents=True, exist_ok=True)
    reference_dir.mkdir(parents=True, exist_ok=True)

    # 1. Save public CTX prior + initial belief/sigma/masks in data/sample/terrain.npz
    public_npz_path = sample_dir / "terrain.npz"
    np.savez_compressed(
        public_npz_path,
        prior=prior,
        belief=belief,
        sigma=sigma,
        nodata_mask=nodata_mask,
        observed_mask=observed_mask,
        elevation_m=prior,
        valid_mask=ctx_valid,
        resolution_m=np.array(resolution_m, dtype=np.float64),
        origin_x_m=np.array(origin_x_m, dtype=np.float64),
        origin_y_m=np.array(origin_y_m, dtype=np.float64),
        row_orientation=np.array("south_to_north"),
    )
    public_npz_sha256 = file_sha256(public_npz_path)

    # 2. Save MGS/MOLA regional context in data/sample/mola_regional_context.npz
    mola_npz_path = sample_dir / "mola_regional_context.npz"
    np.savez_compressed(
        mola_npz_path,
        regional_elevation_m=mola_elev.astype(np.float32),
        valid_mask=mola_valid,
        resolution_m=np.array(resolution_m, dtype=np.float64),
        native_resolution_m=np.array(mola_details["native_resolution_m"], dtype=np.float64),
        origin_x_m=np.array(origin_x_m, dtype=np.float64),
        origin_y_m=np.array(origin_y_m, dtype=np.float64),
        row_orientation=np.array("south_to_north"),
    )
    mola_npz_sha256 = file_sha256(mola_npz_path)

    # 3. Save reduced preview PNG in data/sample/preview_ctx_prior.png
    preview_path = sample_dir / "preview_ctx_prior.png"
    write_grayscale_png(preview_path, prior, scale_factor=4)

    # 4. Save isolated evaluator reference in data/reference/ (gitignored)
    ref_npz_path = reference_dir / "jezero_hirise_reference.npz"
    np.savez_compressed(
        ref_npz_path,
        elevation_m=hirise_elev.astype(np.float32),
        valid_mask=hirise_valid,
        resolution_m=np.array(resolution_m, dtype=np.float64),
        origin_x_m=np.array(origin_x_m, dtype=np.float64),
        origin_y_m=np.array(origin_y_m, dtype=np.float64),
        row_orientation=np.array("south_to_north"),
    )
    ref_npz_sha256 = file_sha256(ref_npz_path)

    cpoints = compute_control_points(
        prior,
        origin_x_m=origin_x_m,
        origin_y_m=origin_y_m,
        resolution_m=resolution_m,
        target_crs_wkt=ctx_details["target_crs_wkt"],
    )

    vertical_datum_str = (
        "MOLA topography / DeltaGeoid (Mars 2000 Sphere, R=3396190 m); no Earth datum conversion"
    )

    # 5. Write schema-compliant data/sample/manifest.json (strictly matching data/manifest.schema.json)
    manifest = {
        "schema_version": 1,
        "status": "ready",
        "region_id": region_id,
        "frame_id": "map",
        "local_origin": {
            "lat_planetocentric_deg": float(latitude),
            "lon_east_deg": float(longitude),
        },
        "resolution_m": float(resolution_m),
        "rows": int(rows),
        "cols": int(cols),
        "row_orientation": "south_to_north",
        "vertical_units": "m",
        "vertical_datum": vertical_datum_str,
        "sources": [
            {
                "mission": "MRO",
                "instrument": "CTX",
                "role": "prior",
                "product_id": ctx_details["product_id"],
                "native_resolution_m": float(ctx_details["native_resolution_m"]),
                "source_url": ctx_details["source_url"],
                "sha256": public_npz_sha256,
                "license_or_terms_url": ctx_details["license_or_terms_url"],
            },
            {
                "mission": "MRO",
                "instrument": "HiRISE",
                "role": "evaluation_reference",
                "product_id": hirise_details["product_id"],
                "native_resolution_m": float(hirise_details["native_resolution_m"]),
                "source_url": hirise_details["source_url"],
                "sha256": ref_npz_sha256,
                "license_or_terms_url": hirise_details["license_or_terms_url"],
            },
            {
                "mission": "Mars Global Surveyor",
                "instrument": "MOLA",
                "role": "regional_context",
                "product_id": mola_details["product_id"],
                "native_resolution_m": float(mola_details["native_resolution_m"]),
                "source_url": mola_details["source_url"],
                "sha256": mola_npz_sha256,
                "license_or_terms_url": mola_details["license_or_terms_url"],
            },
        ],
    }
    (sample_dir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    # 6. Write extended provenance & regional cross-check details in data/sample/provenance_details.json
    ctx_vs_mola_diff = prior[ctx_valid & mola_valid] - mola_elev[ctx_valid & mola_valid]
    provenance_details = {
        "schema_version": 1,
        "region_id": region_id,
        "frame_id": "map",
        "mars_sphere_radius_m": int(MARS_RADIUS_M),
        "origin_x_m": float(origin_x_m),
        "origin_y_m": float(origin_y_m),
        "resolution_m": float(resolution_m),
        "rows": int(rows),
        "cols": int(cols),
        "row_orientation": "south_to_north",
        "default_prior_sigma_m": float(DEFAULT_PRIOR_SIGMA_M),
        "retrieved_utc": retrieved_utc,
        "processed_utc": datetime.now(timezone.utc).isoformat(),
        "artifacts": {
            "public_terrain_npz": "terrain.npz",
            "public_terrain_sha256": public_npz_sha256,
            "mola_regional_npz": "mola_regional_context.npz",
            "mola_regional_sha256": mola_npz_sha256,
            "preview_png": "preview_ctx_prior.png",
            "preview_png_sha256": file_sha256(preview_path),
            "isolated_reference_npz": "data/reference/jezero_hirise_reference.npz",
            "isolated_reference_sha256": ref_npz_sha256,
        },
        "regional_mola_comparison": {
            "mola_mean_elevation_m": float(mola_elev[mola_valid].mean()),
            "ctx_mean_elevation_m": float(prior[ctx_valid].mean()),
            "mean_offset_ctx_minus_mola_m": float(ctx_vs_mola_diff.mean()),
            "max_abs_offset_ctx_minus_mola_m": float(np.abs(ctx_vs_mola_diff).max()),
            "scientific_role": (
                "MGS/MOLA 463 m laser altimetry establishes the regional topographic basin context "
                "for Jezero Crater (-2572 m relative to the MOLA areoid) and verifies vertical datum "
                "registration of the 20 m MRO/CTX prior without introducing Earth datum assumptions."
            ),
        },
        "control_points": cpoints,
        "upstream_sources": {
            "CTX": ctx_details,
            "HiRISE": hirise_details,
            "MOLA": mola_details,
        },
        "processing_versions": {
            "python": platform.python_version(),
            "numpy": np.__version__,
            "rasterio": rasterio.__version__,
            "gdal": rasterio.__gdal_version__,
        },
        "limitations": [
            "A valid orbital DEM sample is not a locally observed or ground-verified corridor.",
            "No mobility, soil mechanics, EVA or drone flight certification is implied.",
            "Bilinear resampling onto a 4 m computational grid creates no native sub-20 m CTX or sub-463 m MOLA information.",
            "Evaluator HiRISE reference arrays remain isolated in data/reference/ and are excluded from public bundles.",
        ],
    }
    (sample_dir / "provenance_details.json").write_text(
        json.dumps(provenance_details, indent=2) + "\n", encoding="utf-8"
    )

    # 7. Write evaluator reference manifest in data/reference/manifest.json
    ref_manifest = {
        "schema_version": 1,
        "role": "evaluation_reference",
        "knowledge_state": "held_out_evaluator_reference",
        "region_id": region_id,
        "frame_id": "map",
        "rows": int(rows),
        "cols": int(cols),
        "resolution_m": float(resolution_m),
        "origin_x_m": float(origin_x_m),
        "origin_y_m": float(origin_y_m),
        "row_orientation": "south_to_north",
        "artifact": "jezero_hirise_reference.npz",
        "sha256": ref_npz_sha256,
        "retrieved_utc": retrieved_utc,
        "source": hirise_details,
    }
    (reference_dir / "manifest.json").write_text(json.dumps(ref_manifest, indent=2) + "\n", encoding="utf-8")

    traversability_summary = estimate_traversability_summary(prior, ctx_valid, resolution_m)

    return {
        "manifest": manifest,
        "provenance_details": provenance_details,
        "traversability_summary": traversability_summary,
    }


def _build_sync_and_print(
    *,
    latitude: float,
    longitude: float,
    side_m: float,
    resolution_m: float,
    region_id: str,
    sample_dir: Path,
    reference_dir: Path,
    sync_yml: bool,
) -> None:
    result = build_package(
        latitude=latitude,
        longitude=longitude,
        side_m=side_m,
        resolution_m=resolution_m,
        region_id=region_id,
        sample_dir=sample_dir,
        reference_dir=reference_dir,
    )
    if sync_yml:
        sync_terrain_yml(
            ROOT / "config/terrain.yml",
            region_id=region_id,
            latitude=latitude,
            longitude=longitude,
            side_m=side_m,
            resolution_m=resolution_m,
            rows=result["manifest"]["rows"],
            cols=result["manifest"]["cols"],
            vertical_datum=result["manifest"]["vertical_datum"],
            control_points=result["provenance_details"]["control_points"],
        )
    print(
        json.dumps(
            {
                "status": result["manifest"]["status"],
                "region_id": result["manifest"]["region_id"],
                "local_origin": result["manifest"]["local_origin"],
                "rows": result["manifest"]["rows"],
                "cols": result["manifest"]["cols"],
                "traversability_summary": result["traversability_summary"],
            },
            indent=2,
        ),
        flush=True,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--latitude", type=float, default=None, help=f"Mars planetocentric latitude deg N (default {DEFAULT_LATITUDE_DEG})")
    parser.add_argument("--longitude", type=float, default=None, help=f"Mars east longitude deg E (default {DEFAULT_LONGITUDE_DEG})")
    parser.add_argument("--side-m", type=float, default=DEFAULT_SIDE_M)
    parser.add_argument("--scale", type=int, choices=(1, 2, 3, 4), default=None, help="Size tier (1=128m, 2=256m, 3=512m)")
    parser.add_argument("--resolution-m", type=float, default=DEFAULT_RESOLUTION_M)
    parser.add_argument("--region-id", type=str, default="jezero_mvp")
    parser.add_argument("--sample-dir", type=Path, default=ROOT / "data/sample")
    parser.add_argument("--reference-dir", type=Path, default=ROOT / "data/reference")
    parser.add_argument("-i", "--interactive", action="store_true", help="Prompt immediately instead of running default first")
    parser.add_argument("--no-interactive", action="store_true", help="Run once and exit without waiting for cc/d commands")
    parser.add_argument("--bounds-only", action="store_true", help="Only query and print available NASA/USGS lat/lon bounds")
    parser.add_argument("--sync-terrain-yml", action="store_true", help="Also update config/terrain.yml with the generated coordinates and control points")
    args = parser.parse_args()

    if args.bounds_only:
        print(json.dumps(query_available_coverage(("CTX", "HiRISE")), indent=2))
        return

    sample_dir = args.sample_dir.resolve()
    reference_dir = args.reference_dir.resolve()
    if sample_dir == reference_dir or sample_dir in reference_dir.parents or reference_dir in sample_dir.parents:
        parser.error("public sample_dir and evaluator reference_dir must be separate")

    scale_to_side = {1: 128.0, 2: 256.0, 3: 512.0, 4: 512.0}
    base_side_m = scale_to_side[args.scale] if args.scale is not None else args.side_m
    latitude, longitude, side_m = request_region_params(
        interactive=args.interactive,
        latitude=args.latitude,
        longitude=args.longitude,
        side_m=base_side_m,
        resolution_m=args.resolution_m,
    )
    _build_sync_and_print(
        latitude=latitude,
        longitude=longitude,
        side_m=side_m,
        resolution_m=args.resolution_m,
        region_id=args.region_id,
        sample_dir=sample_dir,
        reference_dir=reference_dir,
        sync_yml=args.sync_terrain_yml,
    )

    should_loop = (
        not args.no_interactive
        and not args.interactive
        and sys.stdin.isatty()
        and args.latitude is None
        and args.longitude is None
        and args.scale is None
    )
    if not should_loop:
        return

    try:
        while True:
            cmd = input("\nComandos: [cc] cambiar escala/coordenadas | [d] volver a default | [Ctrl+C] salir: ").strip().lower()
            if cmd == "cc":
                new_lat, new_lon, new_side_m = prompt_custom_region(resolution_m=args.resolution_m)
                _build_sync_and_print(
                    latitude=new_lat,
                    longitude=new_lon,
                    side_m=new_side_m,
                    resolution_m=args.resolution_m,
                    region_id=args.region_id,
                    sample_dir=sample_dir,
                    reference_dir=reference_dir,
                    sync_yml=args.sync_terrain_yml,
                )
            elif cmd == "d":
                _build_sync_and_print(
                    latitude=DEFAULT_LATITUDE_DEG,
                    longitude=DEFAULT_LONGITUDE_DEG,
                    side_m=DEFAULT_SIDE_M,
                    resolution_m=args.resolution_m,
                    region_id=args.region_id,
                    sample_dir=sample_dir,
                    reference_dir=reference_dir,
                    sync_yml=args.sync_terrain_yml,
                )
            elif cmd:
                print("Comando no reconocido. Usa 'cc', 'd' o Ctrl+C para salir.")
    except (KeyboardInterrupt, EOFError):
        print("\nCerrado.")


if __name__ == "__main__":
    main()
