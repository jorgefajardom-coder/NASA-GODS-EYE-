#!/usr/bin/env python3
"""Prepare optional, separate NASA/USGS auxiliary terrain layers aligned with data/sample/terrain.npz.

This script does NOT modify data/sample/terrain.npz, data/sample/manifest.json, or
data/sample/provenance_details.json. Instead, it reads the active grid geometry
(lat, lon, rows, cols, resolution_m, origin_x_m, origin_y_m, elevation_m) and
generates standalone auxiliary files in the same directory:
  1. jezero_aux_layers.npz  - Cell-aligned (rows, cols) south_to_north arrays:
       * ctx_ortho_dn (uint8): Real MRO/CTX 6 m/px orthomosaic radiometric DN
       * ctx_ortho_norm (float32): Normalized [0, 1] CTX 6 m/px reflectance
       * ctx_ortho_valid_mask (bool): Valid mask for CTX 6 m/px orthomosaic
       * slope_deg (float32): Local terrain slope in degrees from elevation_m
       * geology_unit_code (int16): USGS SIM 3464 geologic unit integer ID per cell
       * geology_rviz_occupancy (int8): RViz OccupancyGrid (-1 or 0..100) for geologic units
       * surface_zone_code (int8): Literal orbital surface-facies & slope zone ID (0..5)
       * surface_zone_rviz_occupancy (int8): RViz OccupancyGrid (-1, 15, 35, 55, 75, 95)
       * x_m (float32), y_m (float32): Grid cell center coordinates in local ENU metres
  2. ctx_ortho.png          - North-up 8-bit grayscale PNG texture for 3D/web drape
  3. geology.json           - USGS SIM 3464 clipped polygons in local ENU metres
  4. aux_layers_manifest.json - Provenance, SHA-256 checksums, legends, and RViz topics
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import struct
import sys
import urllib.parse
import urllib.request
import zlib
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.prepare_jezero_terrain import (
    HTTPRangeReader,
    MARS_RADIUS_M,
    S3_BASE,
    load_slope_limits,
    resolve_upstream,
    south_first,
)

CTX_ORTHO_SOURCE: dict[str, Any] = {
    "mission": "Mars Reconnaissance Orbiter",
    "instrument": "CTX",
    "role": "auxiliary_orbital_imagery",
    "product_id": "JEZ_ctx_B_soc_008_orthoMosaic_6m_Eqc_latTs0_lon0",
    "source_url": S3_BASE + "mars2020_trn/CTX/JEZ_ctx_B_soc_008_orthoMosaic_6m_Eqc_latTs0_lon0.tif",
    "fallback_urls": [
        "https://planetarymaps.usgs.gov/mosaic/mars2020_trn/CTX/JEZ_ctx_B_soc_008_orthoMosaic_6m_Eqc_latTs0_lon0.tif",
    ],
    "license_or_terms_url": "https://www.usgs.gov/information-policies-and-instructions/copyrights-and-credits",
    "native_resolution_m": 6.0,
    "citation": (
        "USGS Astrogeology Science Center (2020), Mars 2020 Terrain Relative Navigation "
        "CTX 6 m/px Controlled Orthomosaic (JEZ_ctx_B_soc_008_orthoMosaic_6m_Eqc_latTs0_lon0)."
    ),
}

SIM3464_FEATURE_SERVER_URL = (
    "https://services.arcgis.com/v01gqwM5QqNysAAi/arcgis/rest/services/"
    "Jezero_FeatureServiceFromPro/FeatureServer/8/query"
)
SIM3464_LON0_DEG = 77.5

# Official USGS SIM 3464 unit catalog (Sun & Stack, 2020, https://doi.org/10.3133/sim3464)
SIM3464_UNITS: dict[str, dict[str, Any]] = {
    "1": {
        "code": 1,
        "symbol": "Avf",
        "name": "Volcanic floor unit",
        "group": "Interior",
        "color_hex": "#8c6d62",
        "rviz_occupancy": 20,
    },
    "2": {
        "code": 2,
        "symbol": "Njf",
        "name": "Jezero floor unit",
        "group": "Interior",
        "color_hex": "#b07c56",
        "rviz_occupancy": 35,
    },
    "3": {
        "code": 3,
        "symbol": "Nle",
        "name": "Lower etched unit",
        "group": "Interior",
        "color_hex": "#d4a359",
        "rviz_occupancy": 50,
    },
    "5": {
        "code": 5,
        "symbol": "Nhf",
        "name": "Hummocky floor unit",
        "group": "Interior",
        "color_hex": "#c4884b",
        "rviz_occupancy": 60,
    },
    "11": {
        "code": 11,
        "symbol": "Nnp",
        "name": "Nili Planum fractured unit",
        "group": "Background",
        "color_hex": "#9b8b7a",
        "rviz_occupancy": 70,
    },
    "16": {
        "code": 16,
        "symbol": "Hr",
        "name": "Rugged unit",
        "group": "Fluvial/lacustrine",
        "color_hex": "#5f8c87",
        "rviz_occupancy": 45,
    },
    "17": {
        "code": 17,
        "symbol": "Hdl",
        "name": "Delta layered rough unit",
        "group": "Fluvial/lacustrine",
        "color_hex": "#4b7b96",
        "rviz_occupancy": 30,
    },
    "18": {
        "code": 18,
        "symbol": "Hdb",
        "name": "Delta blocky unit",
        "group": "Fluvial/lacustrine",
        "color_hex": "#3b6587",
        "rviz_occupancy": 25,
    },
    "19": {
        "code": 19,
        "symbol": "Hdt",
        "name": "Delta truncated curvilinear layered unit",
        "group": "Fluvial/lacustrine",
        "color_hex": "#2f5373",
        "rviz_occupancy": 15,
    },
    "20": {
        "code": 20,
        "symbol": "Hds",
        "name": "Delta smooth unit",
        "group": "Fluvial/lacustrine",
        "color_hex": "#6a99b5",
        "rviz_occupancy": 40,
    },
    "22": {
        "code": 22,
        "symbol": "Ae",
        "name": "Eolian bedform unit",
        "group": "Surficial",
        "color_hex": "#e2c878",
        "rviz_occupancy": 80,
    },
    "24": {
        "code": 24,
        "symbol": "As",
        "name": "Smooth talus unit",
        "group": "Surficial",
        "color_hex": "#b5a895",
        "rviz_occupancy": 85,
    },
    "25": {
        "code": 25,
        "symbol": "Acu",
        "name": "Crater unit, undivided",
        "group": "Crater",
        "color_hex": "#7c7067",
        "rviz_occupancy": 90,
    },
}

SURFACE_ZONE_DEFINITIONS: list[dict[str, Any]] = [
    {
        "code": 0,
        "id": "nodata",
        "label": "NoData / Unmapped",
        "rviz_occupancy": -1,
        "color_hex": "#404040",
        "traversable_agents": [],
        "description": "Missing orbital elevation or CTX orthomosaic reflectance.",
    },
    {
        "code": 1,
        "id": "dark_floor_facies",
        "label": "Low-albedo smooth floor facies",
        "rviz_occupancy": 15,
        "color_hex": "#5c5346",
        "traversable_agents": ["human", "rover", "drone"],
        "description": "Low-slope (<= human limit) terrain with lower CTX 6 m reflectance (< P33).",
    },
    {
        "code": 2,
        "id": "intermediate_plains_facies",
        "label": "Intermediate-albedo plains facies",
        "rviz_occupancy": 35,
        "color_hex": "#9c7a54",
        "traversable_agents": ["human", "rover", "drone"],
        "description": "Low-slope (<= human limit) terrain with intermediate CTX 6 m reflectance (P33..P67).",
    },
    {
        "code": 3,
        "id": "bright_etched_or_bedform_facies",
        "label": "High-albedo etched ridge / bedform facies",
        "rviz_occupancy": 55,
        "color_hex": "#d9b36c",
        "traversable_agents": ["human", "rover", "drone"],
        "description": "Low-slope (<= human limit) terrain with higher CTX 6 m reflectance (> P67).",
    },
    {
        "code": 4,
        "id": "moderate_slope_rover_zone",
        "label": "Moderate slope transition zone (rover/drone)",
        "rviz_occupancy": 75,
        "color_hex": "#d97b29",
        "traversable_agents": ["rover", "drone"],
        "description": "Moderate slope exceeding human limit (> 10 deg) up to rover limit (<= 20 deg).",
    },
    {
        "code": 5,
        "id": "steep_scarp_hazard_zone",
        "label": "Steep scarp / hazard zone (drone only)",
        "rviz_occupancy": 95,
        "color_hex": "#c93b2b",
        "traversable_agents": ["drone"],
        "description": "Steep slope exceeding rover limit (> 20 deg); surface obstacle.",
    },
]


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_north_up_grayscale_png(path: Path, dn_south_up: np.ndarray, scale_factor: int = 1) -> None:
    """Write a deterministic 8-bit grayscale PNG (row 0 = north) from a south_to_north uint8 array."""
    north_up = np.flipud(dn_south_up).astype(np.uint8)
    if scale_factor > 1:
        north_up = np.repeat(np.repeat(north_up, scale_factor, axis=0), scale_factor, axis=1)
    height, width = north_up.shape

    def chunk(tag: bytes, data: bytes) -> bytes:
        crc = zlib.crc32(tag + data) & 0xFFFFFFFF
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", crc)

    raw_rows = b"".join(b"\x00" + north_up[r].tobytes() for r in range(height))
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 0, 0, 0, 0)
    png_bytes = (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", ihdr)
        + chunk(b"IDAT", zlib.compress(raw_rows, level=9))
        + chunk(b"IEND", b"")
    )
    path.write_bytes(png_bytes)


def crop_ctx_orthomosaic(
    *,
    latitude: float,
    longitude: float,
    rows: int,
    cols: int,
    resolution_m: float,
    origin_x_m: float,
    origin_y_m: float,
    padding_pixels: int = 4,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, dict[str, Any]]:
    """Fetch bounded window of MRO/CTX 6 m/px controlled orthomosaic via HTTP 206 ranges."""
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
    west_m = float(origin_x_m)
    south_m = float(origin_y_m)
    east_m = west_m + cols * resolution_m
    north_m = south_m + rows * resolution_m
    north_transform = from_origin(west_m, north_m, resolution_m, resolution_m)

    resolved_url, upstream_headers = resolve_upstream(CTX_ORTHO_SOURCE)
    virtual_name = "upstream_CTX_ORTHO_6M.tif"
    active_readers: list[HTTPRangeReader] = []

    def opener(path, mode="rb"):
        if str(path) != virtual_name:
            raise FileNotFoundError(path)
        reader = HTTPRangeReader(resolved_url, upstream_headers, block_size=1024 * 1024)
        active_readers.append(reader)
        return reader

    with rasterio.Env(GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR"):
        with rasterio.open(virtual_name, opener=opener) as src:
            if src.crs is None:
                raise ValueError("upstream CTX orthomosaic raster has no declared planetary CRS")
            bounds = transform_bounds(target_crs, src.crs, west_m, south_m, east_m, north_m, densify_pts=21)
            fractional = from_bounds(*bounds, transform=src.transform)
            x0 = math.floor(fractional.col_off) - padding_pixels
            y0 = math.floor(fractional.row_off) - padding_pixels
            x1 = math.ceil(fractional.col_off + fractional.width) + padding_pixels
            y1 = math.ceil(fractional.row_off + fractional.height) + padding_pixels
            window = Window(x0, y0, max(4, x1 - x0), max(4, y1 - y0)).intersection(
                Window(0, 0, src.width, src.height)
            )
            approx_span = int(window.height) * int(src.width)
            for reader in active_readers:
                reader.expected_span_bytes = approx_span

            raw = src.read(1, window=window, masked=True).astype(np.float32)
            native = raw.filled(np.nan)
            destination = np.full((rows, cols), np.nan, dtype=np.float32)
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
                "mission": CTX_ORTHO_SOURCE["mission"],
                "instrument": CTX_ORTHO_SOURCE["instrument"],
                "role": CTX_ORTHO_SOURCE["role"],
                "product_id": CTX_ORTHO_SOURCE["product_id"],
                "source_url": resolved_url,
                "license_or_terms_url": CTX_ORTHO_SOURCE["license_or_terms_url"],
                "native_resolution_m": CTX_ORTHO_SOURCE["native_resolution_m"],
                "citation": CTX_ORTHO_SOURCE["citation"],
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
                "native_min_dn": float(native_valid.min()) if native_valid.size else None,
                "native_max_dn": float(native_valid.max()) if native_valid.size else None,
                "native_mean_dn": float(native_valid.mean()) if native_valid.size else None,
                "upstream_etag": upstream_headers.get("ETag"),
                "upstream_last_modified": upstream_headers.get("Last-Modified"),
                "upstream_content_length": int(upstream_headers["Content-Length"]),
                "read_method": "fresh HTTP 206 ranges via bounded keep-alive reader",
            }

    south_float, valid_mask = south_first(destination, np.isfinite(destination))
    if not valid_mask.any():
        raise ValueError("CTX 6 m orthomosaic crop contains no valid pixels")

    dn_south = np.where(valid_mask, np.clip(np.round(south_float), 1, 255), 0).astype(np.uint8)
    valid_vals = south_float[valid_mask]
    vmin = float(valid_vals.min())
    vmax = float(valid_vals.max())
    span = max(vmax - vmin, 1.0)
    norm_south = np.where(valid_mask, (south_float - vmin) / span, np.nan).astype(np.float32)
    return dn_south, norm_south, valid_mask.astype(bool), details


def _enu_to_latlon_deg(x_east_m: float, y_north_m: float, lat0_deg: float, lon0_deg: float) -> tuple[float, float]:
    lat0_rad = math.radians(lat0_deg)
    lat_deg = lat0_deg + math.degrees(y_north_m / MARS_RADIUS_M)
    lon_deg = lon0_deg + math.degrees(x_east_m / (MARS_RADIUS_M * math.cos(lat0_rad)))
    return lat_deg, lon_deg


def _latlon_to_sim3464_tm(lat_deg: float, lon_deg: float) -> tuple[float, float]:
    """Spherical Transverse Mercator (lon0 = 77.5 deg E, R = 3396190 m) used by USGS SIM 3464."""
    phi = math.radians(lat_deg)
    lam = math.radians(lon_deg - SIM3464_LON0_DEG)
    b_val = math.cos(phi) * math.sin(lam)
    x_tm = 0.5 * MARS_RADIUS_M * math.log((1.0 + b_val) / (1.0 - b_val))
    y_tm = MARS_RADIUS_M * math.atan2(math.tan(phi), math.cos(lam))
    return x_tm, y_tm


def _sim3464_tm_to_latlon(x_tm: float, y_tm: float) -> tuple[float, float]:
    """Inverse spherical Transverse Mercator (lon0 = 77.5 deg E, R = 3396190 m) to (lat_deg, lon_deg)."""
    d_val = y_tm / MARS_RADIUS_M
    phi = math.asin(math.sin(d_val) / math.cosh(x_tm / MARS_RADIUS_M))
    lam = math.atan2(math.sinh(x_tm / MARS_RADIUS_M), math.cos(d_val))
    return math.degrees(phi), SIM3464_LON0_DEG + math.degrees(lam)


def _sim3464_tm_to_local_enu(x_tm: float, y_tm: float, lat0_deg: float, lon0_deg: float) -> tuple[float, float]:
    lat_deg, lon_deg = _sim3464_tm_to_latlon(x_tm, y_tm)
    lat0_rad = math.radians(lat0_deg)
    x_east_m = math.radians(lon_deg - lon0_deg) * MARS_RADIUS_M * math.cos(lat0_rad)
    y_north_m = math.radians(lat_deg - lat0_deg) * MARS_RADIUS_M
    return round(x_east_m, 2), round(y_north_m, 2)


def _clip_ring_to_box(
    ring: list[tuple[float, float]],
    xmin: float,
    ymin: float,
    xmax: float,
    ymax: float,
) -> list[list[float]]:
    """Sutherland-Hodgman polygon clipping of a 2D ring to [xmin, xmax] x [ymin, ymax]."""

    def clip_edge(
        pts: list[tuple[float, float]],
        inside_fn,
        intersect_fn,
    ) -> list[tuple[float, float]]:
        if not pts:
            return []
        out: list[tuple[float, float]] = []
        prev = pts[-1]
        prev_in = inside_fn(prev)
        for curr in pts:
            curr_in = inside_fn(curr)
            if curr_in:
                if not prev_in:
                    out.append(intersect_fn(prev, curr))
                out.append(curr)
            elif prev_in:
                out.append(intersect_fn(prev, curr))
            prev, prev_in = curr, curr_in
        return out

    pts = list(ring)
    if len(pts) > 1 and pts[0] == pts[-1]:
        pts = pts[:-1]
    pts = clip_edge(
        pts,
        lambda p: p[0] >= xmin,
        lambda a, b: (xmin, a[1] + (b[1] - a[1]) * (xmin - a[0]) / (b[0] - a[0])),
    )
    pts = clip_edge(
        pts,
        lambda p: p[0] <= xmax,
        lambda a, b: (xmax, a[1] + (b[1] - a[1]) * (xmax - a[0]) / (b[0] - a[0])),
    )
    pts = clip_edge(
        pts,
        lambda p: p[1] >= ymin,
        lambda a, b: (a[0] + (b[0] - a[0]) * (ymin - a[1]) / (b[1] - a[1]), ymin),
    )
    pts = clip_edge(
        pts,
        lambda p: p[1] <= ymax,
        lambda a, b: (a[0] + (b[0] - a[0]) * (ymax - a[1]) / (b[1] - a[1]), ymax),
    )
    rounded = [[round(x, 2), round(y, 2)] for x, y in pts]
    if len(rounded) < 3 or _ring_area(rounded) < 0.1:
        return []
    return rounded


def _ring_area(ring: list[list[float]]) -> float:
    """Unsigned shoelace area of a 2D ring."""
    n = len(ring)
    if n < 3:
        return 0.0
    area2 = 0.0
    for i in range(n):
        x0, y0 = ring[i]
        x1, y1 = ring[(i + 1) % n]
        area2 += x0 * y1 - x1 * y0
    return 0.5 * abs(area2)


def _point_in_ring(x: float, y: float, ring: list[list[float]]) -> bool:
    """Ray-casting point-in-polygon check for a closed or open 2D ring."""
    inside = False
    n = len(ring)
    if n < 3:
        return False
    j = n - 1
    for i in range(n):
        xi, yi = ring[i][0], ring[i][1]
        xj, yj = ring[j][0], ring[j][1]
        if ((yi > y) != (yj > y)) and (x < (xj - xi) * (y - yi) / ((yj - yi) or 1e-12) + xi):
            inside = not inside
        j = i
    return inside


def fetch_and_rasterize_sim3464_geology(
    *,
    latitude: float,
    longitude: float,
    x_m: np.ndarray,
    y_m: np.ndarray,
    origin_x_m: float,
    origin_y_m: float,
    rows: int,
    cols: int,
    resolution_m: float,
    context_margin_m: float = 300.0,
) -> tuple[np.ndarray, np.ndarray, dict[str, Any]]:
    """Query USGS SIM 3464 geologic units, clip to local ENU crop & context boxes, and rasterize."""
    xmin = float(origin_x_m)
    ymin = float(origin_y_m)
    xmax = xmin + cols * resolution_m
    ymax = ymin + rows * resolution_m

    ctx_xmin = xmin - context_margin_m
    ctx_ymin = ymin - context_margin_m
    ctx_xmax = xmax + context_margin_m
    ctx_ymax = ymax + context_margin_m

    lat_min, lon_min = _enu_to_latlon_deg(ctx_xmin, ctx_ymin, latitude, longitude)
    lat_max, lon_max = _enu_to_latlon_deg(ctx_xmax, ctx_ymax, latitude, longitude)
    tm_x0, tm_y0 = _latlon_to_sim3464_tm(lat_min, lon_min)
    tm_x1, tm_y1 = _latlon_to_sim3464_tm(lat_max, lon_max)

    envelope = json.dumps(
        {
            "xmin": round(min(tm_x0, tm_x1), 2),
            "ymin": round(min(tm_y0, tm_y1), 2),
            "xmax": round(max(tm_x0, tm_x1), 2),
            "ymax": round(max(tm_y0, tm_y1), 2),
        }
    )
    query_params = urllib.parse.urlencode(
        {
            "where": "1=1",
            "geometry": envelope,
            "geometryType": "esriGeometryEnvelope",
            "spatialRel": "esriSpatialRelIntersects",
            "outFields": "*",
            "returnGeometry": "true",
            "f": "json",
        }
    )
    query_url = f"{SIM3464_FEATURE_SERVER_URL}?{query_params}"
    req = urllib.request.Request(query_url, headers={"User-Agent": "NASA-GODS-EYE-AuxBuilder/1.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        payload = json.loads(resp.read().decode("utf-8"))

    if payload.get("error"):
        raise RuntimeError(f"ArcGIS SIM 3464 query error: {payload['error']}")

    features = payload.get("features", [])
    polygons_crop: list[dict[str, Any]] = []
    polygons_context: list[dict[str, Any]] = []
    units_present: dict[str, dict[str, Any]] = {}

    for feat in features:
        attrs = feat.get("attributes") or {}
        unit_key = str(attrs.get("GeoUnits") or attrs.get("unit") or "").strip()
        unit_meta = SIM3464_UNITS.get(
            unit_key,
            {
                "code": int(unit_key) if unit_key.isdigit() else 99,
                "symbol": f"U{unit_key}",
                "name": f"Geologic unit {unit_key}",
                "group": "Unclassified",
                "color_hex": "#888888",
                "rviz_occupancy": 50,
            },
        )
        rings_tm = (feat.get("geometry") or {}).get("rings") or []
        enu_rings: list[list[tuple[float, float]]] = [
            [_sim3464_tm_to_local_enu(pt[0], pt[1], latitude, longitude) for pt in ring]
            for ring in rings_tm
        ]

        clipped_crop = [
             clipped
            for ring in enu_rings
            if len(clipped := _clip_ring_to_box(ring, xmin, ymin, xmax, ymax)) >= 3
        ]
        if clipped_crop:
            units_present[unit_meta["symbol"]] = {
                "id": unit_key,
                "code": unit_meta["code"],
                "symbol": unit_meta["symbol"],
                "name": str(attrs.get("name") or unit_meta["name"]),
                "group": unit_meta["group"],
                "color_hex": unit_meta["color_hex"],
                "rviz_occupancy": unit_meta["rviz_occupancy"],
                "description": str(attrs.get("Unit_Description") or ""),
                "characteristics": str(attrs.get("Additional_Characteristics") or ""),
                "interpretation": str(attrs.get("Unit_Interpretation") or ""),
            }
            polygons_crop.append(
                {
                    "unit": unit_key,
                    "symbol": unit_meta["symbol"],
                    "code": unit_meta["code"],
                    "rings": clipped_crop,
                }
            )

        clipped_ctx = [
            clipped
            for ring in enu_rings
            if len(clipped := _clip_ring_to_box(ring, ctx_xmin, ctx_ymin, ctx_xmax, ctx_ymax)) >= 3
        ]
        if clipped_ctx:
            units_present[unit_meta["symbol"]] = {
                "id": unit_key,
                "code": unit_meta["code"],
                "symbol": unit_meta["symbol"],
                "name": str(attrs.get("name") or unit_meta["name"]),
                "group": unit_meta["group"],
                "color_hex": unit_meta["color_hex"],
                "rviz_occupancy": unit_meta["rviz_occupancy"],
                "description": str(attrs.get("Unit_Description") or ""),
                "characteristics": str(attrs.get("Additional_Characteristics") or ""),
                "interpretation": str(attrs.get("Unit_Interpretation") or ""),
            }
            polygons_context.append(
                {
                    "unit": unit_key,
                    "symbol": unit_meta["symbol"],
                    "code": unit_meta["code"],
                    "rings": clipped_ctx,
                }
            )

    unit_code_grid = np.zeros((rows, cols), dtype=np.int16)
    rviz_occ_grid = np.full((rows, cols), -1, dtype=np.int8)

    for r in range(rows):
        yc = float(y_m[r])
        for c in range(cols):
            xc = float(x_m[c])
            for poly in polygons_crop:
                outer_in = _point_in_ring(xc, yc, poly["rings"][0])
                holes_in = any(_point_in_ring(xc, yc, hole) for hole in poly["rings"][1:])
                if outer_in and not holes_in:
                    sym = poly["symbol"]
                    unit_code_grid[r, c] = int(poly["code"])
                    rviz_occ_grid[r, c] = int(units_present[sym]["rviz_occupancy"])
                    break

    geology_doc = {
        "source": {
            "title": "Geologic Map of Jezero Crater and the Nili Planum Region, Mars",
            "authors": "Vivian Z. Sun and Kathryn M. Stack",
            "publisher": "U.S. Geological Survey",
            "series": "Scientific Investigations Map 3464",
            "year": 2020,
            "scale": "1:75,000",
            "doi": "https://doi.org/10.3133/sim3464",
            "data_release": "https://doi.org/10.5066/P9CZYIO7",
            "service": "https://services.arcgis.com/v01gqwM5QqNysAAi/arcgis/rest/services/Jezero_FeatureServiceFromPro/FeatureServer/8",
            "licence": "USGS publication, public domain",
            "basemap_note": (
                "Mapped on CTX 6 m/px uncontrolled mosaic and HiRISE 25 cm/px orthoimages; "
                "positional accuracy relative to the Mars 2020 TRN controlled CTX DEM is ~100-200 m."
            ),
        },
        "frame": {
            "crs": "Crop local ENU (same as terrain_meta)",
            "origin_x_m": xmin,
            "origin_y_m": ymin,
            "width_m": float(cols * resolution_m),
            "height_m": float(rows * resolution_m),
            "origin_lat_deg": float(latitude),
            "origin_lon_deg": float(longitude),
            "sphere_radius_m": float(MARS_RADIUS_M),
            "bbox_enu_m": [xmin, ymin, xmax, ymax],
            "context_margin_m": float(context_margin_m),
            "context_bbox_enu_m": [ctx_xmin, ctx_ymin, ctx_xmax, ctx_ymax],
        },
        "units": [units_present[sym] for sym in sorted(units_present.keys())],
        "polygons": [
            {"unit": p["unit"], "symbol": p["symbol"], "code": p["code"], "rings": p["rings"]}
            for p in polygons_crop
        ],
        "context_polygons": [
            {"unit": p["unit"], "symbol": p["symbol"], "code": p["code"], "rings": p["rings"]}
            for p in polygons_context
        ],
    }
    return unit_code_grid, rviz_occ_grid, geology_doc


def compute_literal_surface_zones(
    elevation_m: np.ndarray,
    ctx_ortho_dn: np.ndarray,
    ctx_ortho_valid_mask: np.ndarray,
    *,
    resolution_m: float,
    slope_limits_deg: dict[str, float],
) -> tuple[np.ndarray, np.ndarray, np.ndarray, dict[str, float]]:
    """Classify each cell into literal surface-facies & slope zones (0..5) and RViz OccupancyGrid values."""
    gy, gx = np.gradient(elevation_m.astype(np.float64), float(resolution_m), float(resolution_m))
    slope_deg = np.degrees(np.arctan(np.hypot(gx, gy))).astype(np.float32)

    valid = np.isfinite(elevation_m) & np.isfinite(slope_deg) & ctx_ortho_valid_mask & (ctx_ortho_dn > 0)
    if valid.any():
        p33 = float(np.percentile(ctx_ortho_dn[valid], 33.33))
        p67 = float(np.percentile(ctx_ortho_dn[valid], 66.67))
    else:
        p33, p67 = 85.0, 170.0

    human_limit = float(slope_limits_deg.get("human", 10.0))
    rover_limit = float(slope_limits_deg.get("rover", 20.0))

    zone_code = np.zeros(elevation_m.shape, dtype=np.int8)
    low_slope = valid & (slope_deg <= human_limit)
    mod_slope = valid & (slope_deg > human_limit) & (slope_deg <= rover_limit)
    steep_slope = valid & (slope_deg > rover_limit)

    zone_code[low_slope & (ctx_ortho_dn <= p33)] = 1
    zone_code[low_slope & (ctx_ortho_dn > p33) & (ctx_ortho_dn <= p67)] = 2
    zone_code[low_slope & (ctx_ortho_dn > p67)] = 3
    zone_code[mod_slope] = 4
    zone_code[steep_slope] = 5

    code_to_occ = {int(d["code"]): int(d["rviz_occupancy"]) for d in SURFACE_ZONE_DEFINITIONS}
    rviz_occupancy = np.full(elevation_m.shape, -1, dtype=np.int8)
    for code_val, occ_val in code_to_occ.items():
        rviz_occupancy[zone_code == code_val] = occ_val

    thresholds = {
        "ctx_dn_p33": round(p33, 3),
        "ctx_dn_p67": round(p67, 3),
        "human_max_slope_deg": human_limit,
        "rover_max_slope_deg": rover_limit,
        "drone_max_slope_deg": float(slope_limits_deg.get("drone", 90.0)),
    }
    return slope_deg, zone_code, rviz_occupancy, thresholds


def build_auxiliary_package(
    *,
    manifest_path: Path = ROOT / "data/sample/manifest.json",
    terrain_npz_path: Path | None = None,
    out_dir: Path | None = None,
    lat_override: float | None = None,
    lon_override: float | None = None,
    rows_override: int | None = None,
    cols_override: int | None = None,
    resolution_override: float | None = None,
    context_margin_m: float = 300.0,
) -> dict[str, Any]:
    """Generate standalone auxiliary NASA/USGS layers aligned with the target terrain grid."""
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    sample_dir = manifest_path.parent
    target_out_dir = out_dir or sample_dir
    target_out_dir.mkdir(parents=True, exist_ok=True)

    npz_path = terrain_npz_path or (sample_dir / "terrain.npz")
    origin = manifest.get("local_origin") or {}
    latitude = float(lat_override if lat_override is not None else origin.get("lat_planetocentric_deg", 18.45))
    longitude = float(lon_override if lon_override is not None else origin.get("lon_east_deg", 77.45))
    rows = int(rows_override if rows_override is not None else manifest.get("rows", 32))
    cols = int(cols_override if cols_override is not None else manifest.get("cols", 32))
    resolution_m = float(resolution_override if resolution_override is not None else manifest.get("resolution_m", 4.0))
    origin_x_m = float(origin.get("origin_x_m", -(cols / 2.0) * resolution_m))
    origin_y_m = float(origin.get("origin_y_m", -(rows / 2.0) * resolution_m))

    terrain_sha256: str | None = None
    if npz_path.exists():
        with np.load(npz_path, allow_pickle=False) as terrain_arrays:
            keys = set(terrain_arrays.files)
            elev_key = "prior" if "prior" in keys else "elevation_m"
            elev = np.asarray(terrain_arrays[elev_key], dtype=np.float32)
            if elev.shape == (rows, cols) and lat_override is None and lon_override is None:
                elevation_m = elev
                if "origin_x_m" in keys:
                    origin_x_m = float(terrain_arrays["origin_x_m"])
                if "origin_y_m" in keys:
                    origin_y_m = float(terrain_arrays["origin_y_m"])
                x_m = (
                    np.asarray(terrain_arrays["x_m"], dtype=np.float32)
                    if "x_m" in keys
                    else (origin_x_m + (np.arange(cols, dtype=np.float32) + 0.5) * resolution_m).astype(np.float32)
                )
                y_m = (
                    np.asarray(terrain_arrays["y_m"], dtype=np.float32)
                    if "y_m" in keys
                    else (origin_y_m + (np.arange(rows, dtype=np.float32) + 0.5) * resolution_m).astype(np.float32)
                )
                terrain_sha256 = sha256_file(npz_path)
            else:
                elevation_m = np.zeros((rows, cols), dtype=np.float32)
                x_m = (origin_x_m + (np.arange(cols, dtype=np.float32) + 0.5) * resolution_m).astype(np.float32)
                y_m = (origin_y_m + (np.arange(rows, dtype=np.float32) + 0.5) * resolution_m).astype(np.float32)
    else:
        elevation_m = np.zeros((rows, cols), dtype=np.float32)
        x_m = (origin_x_m + (np.arange(cols, dtype=np.float32) + 0.5) * resolution_m).astype(np.float32)
        y_m = (origin_y_m + (np.arange(rows, dtype=np.float32) + 0.5) * resolution_m).astype(np.float32)

    ctx_dn, ctx_norm, ctx_valid, ctx_details = crop_ctx_orthomosaic(
        latitude=latitude,
        longitude=longitude,
        rows=rows,
        cols=cols,
        resolution_m=resolution_m,
        origin_x_m=origin_x_m,
        origin_y_m=origin_y_m,
    )

    geology_code, geology_rviz_occ, geology_doc = fetch_and_rasterize_sim3464_geology(
        latitude=latitude,
        longitude=longitude,
        x_m=x_m,
        y_m=y_m,
        origin_x_m=origin_x_m,
        origin_y_m=origin_y_m,
        rows=rows,
        cols=cols,
        resolution_m=resolution_m,
        context_margin_m=context_margin_m,
    )

    slope_limits, _ = load_slope_limits()
    slope_deg, surface_zone_code, surface_zone_rviz_occ, zone_thresholds = compute_literal_surface_zones(
        elevation_m,
        ctx_dn,
        ctx_valid,
        resolution_m=resolution_m,
        slope_limits_deg=slope_limits,
    )

    aux_npz_path = target_out_dir / "jezero_aux_layers.npz"
    ctx_png_path = target_out_dir / "ctx_ortho.png"
    geology_json_path = target_out_dir / "geology.json"
    aux_manifest_path = target_out_dir / "aux_layers_manifest.json"

    np.savez_compressed(
        aux_npz_path,
        ctx_ortho_dn=ctx_dn,
        ctx_ortho_norm=ctx_norm,
        ctx_ortho_valid_mask=ctx_valid,
        slope_deg=slope_deg,
        geology_unit_code=geology_code,
        geology_rviz_occupancy=geology_rviz_occ,
        surface_zone_code=surface_zone_code,
        surface_zone_rviz_occupancy=surface_zone_rviz_occ,
        x_m=x_m,
        y_m=y_m,
    )

    # Write north-up grayscale PNG stretched to 0..255 for visual texture draping
    stretched_dn = np.where(ctx_valid, np.clip(np.round(ctx_norm * 255.0), 0, 255), 0).astype(np.uint8)
    write_north_up_grayscale_png(ctx_png_path, stretched_dn, scale_factor=1)
    geology_json_path.write_text(json.dumps(geology_doc, indent=2) + "\n", encoding="utf-8", newline="\n")

    zone_counts = {
        defn["id"]: int(np.sum(surface_zone_code == int(defn["code"])))
        for defn in SURFACE_ZONE_DEFINITIONS
    }
    geology_counts = {
        info["symbol"]: int(np.sum(geology_code == int(info["code"])))
        for info in geology_doc["units"]
    }

    aux_manifest = {
        "schema_version": "1.0.0",
        "status": "ready",
        "optional_layer_bundle": True,
        "region_id": manifest.get("region_id", "jezero_mvp"),
        "frame_id": manifest.get("frame_id", "map"),
        "row_orientation": manifest.get("row_orientation", "south_to_north"),
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "aligned_terrain_npz_sha256": terrain_sha256,
        "grid": {
            "lat_planetocentric_deg": latitude,
            "lon_east_deg": longitude,
            "rows": rows,
            "cols": cols,
            "resolution_m": resolution_m,
            "origin_x_m": origin_x_m,
            "origin_y_m": origin_y_m,
        },
        "files": {
            "aux_npz": {
                "path": aux_npz_path.name,
                "sha256": sha256_file(aux_npz_path),
                "arrays": [
                    "ctx_ortho_dn",
                    "ctx_ortho_norm",
                    "ctx_ortho_valid_mask",
                    "slope_deg",
                    "geology_unit_code",
                    "geology_rviz_occupancy",
                    "surface_zone_code",
                    "surface_zone_rviz_occupancy",
                    "x_m",
                    "y_m",
                ],
            },
            "ctx_ortho_png": {
                "path": ctx_png_path.name,
                "sha256": sha256_file(ctx_png_path),
                "width": cols,
                "height": rows,
                "row0": "north",
                "product_id": CTX_ORTHO_SOURCE["product_id"],
                "native_resolution_m": CTX_ORTHO_SOURCE["native_resolution_m"],
            },
            "geology_json": {
                "path": geology_json_path.name,
                "sha256": sha256_file(geology_json_path),
                "doi": geology_doc["source"]["doi"],
                "scale": geology_doc["source"]["scale"],
            },
        },
        "rviz_integration": {
            "enabled_by_default": True,
            "can_be_disabled_or_removed_safely": True,
            "topics": {
                "ctx_ortho_image": {
                    "topic": "/mge/terrain/aux/ctx_ortho",
                    "msg_type": "sensor_msgs/msg/Image",
                    "encoding": "mono8",
                    "array_key": "ctx_ortho_dn",
                },
                "surface_zones_grid": {
                    "topic": "/mge/terrain/aux/surface_zones",
                    "msg_type": "nav_msgs/msg/OccupancyGrid",
                    "array_key": "surface_zone_rviz_occupancy",
                    "description": "Literal orbital surface-facies & slope zones (-1 NoData, 15/35/55/75/95 zones)",
                },
                "geology_zones_grid": {
                    "topic": "/mge/terrain/aux/geology_zones",
                    "msg_type": "nav_msgs/msg/OccupancyGrid",
                    "array_key": "geology_rviz_occupancy",
                    "description": "USGS SIM 3464 mapped geologic units (-1 unmapped, 0..100 per unit)",
                },
            },
        },
        "surface_zones": {
            "thresholds": zone_thresholds,
            "definitions": SURFACE_ZONE_DEFINITIONS,
            "cell_counts": zone_counts,
        },
        "geology_zones": {
            "units": geology_doc["units"],
            "cell_counts": geology_counts,
            "crop_polygon_count": len(geology_doc["polygons"]),
            "context_polygon_count": len(geology_doc["context_polygons"]),
        },
        "provenance": {
            "ctx_orthomosaic": ctx_details,
            "usgs_sim3464": geology_doc["source"],
        },
    }
    aux_manifest_path.write_text(json.dumps(aux_manifest, indent=2) + "\n", encoding="utf-8", newline="\n")
    return aux_manifest


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--manifest",
        type=Path,
        default=ROOT / "data/sample/manifest.json",
        help="Path to the primary terrain manifest.json (read-only).",
    )
    parser.add_argument(
        "--terrain-npz",
        type=Path,
        default=None,
        help="Optional explicit path to terrain.npz (read-only).",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=None,
        help="Directory to write auxiliary layer files (defaults to manifest directory).",
    )
    parser.add_argument("--lat", type=float, default=None, help="Override planetocentric latitude (deg N).")
    parser.add_argument("--lon", type=float, default=None, help="Override east longitude (deg E).")
    parser.add_argument("--rows", type=int, default=None, help="Override grid row count.")
    parser.add_argument("--cols", type=int, default=None, help="Override grid col count.")
    parser.add_argument("--resolution-m", type=float, default=None, help="Override cell resolution in metres.")
    parser.add_argument(
        "--context-margin-m",
        type=float,
        default=300.0,
        help="Context margin in metres around the crop box for SIM 3464 geology polygons (default: 300).",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    aux_manifest = build_auxiliary_package(
        manifest_path=args.manifest,
        terrain_npz_path=args.terrain_npz,
        out_dir=args.out_dir,
        lat_override=args.lat,
        lon_override=args.lon,
        rows_override=args.rows,
        cols_override=args.cols,
        resolution_override=args.resolution_m,
        context_margin_m=args.context_margin_m,
    )
    grid = aux_manifest["grid"]
    print(
        f"Prepared auxiliary NASA/USGS layers for {aux_manifest['region_id']} "
        f"({grid['rows']}x{grid['cols']} @ {grid['resolution_m']} m, "
        f"lat={grid['lat_planetocentric_deg']}, lon={grid['lon_east_deg']})"
    )
    print(f"  - {aux_manifest['files']['aux_npz']['path']} (sha256={aux_manifest['files']['aux_npz']['sha256'][:16]}...)")
    print(f"  - {aux_manifest['files']['ctx_ortho_png']['path']} ({grid['cols']}x{grid['rows']} north-up PNG)")
    print(
        f"  - {aux_manifest['files']['geology_json']['path']} "
        f"(crop polygons={aux_manifest['geology_zones']['crop_polygon_count']}, "
        f"context polygons={aux_manifest['geology_zones']['context_polygon_count']})"
    )
    print(f"  - surface_zones cell_counts={aux_manifest['surface_zones']['cell_counts']}")
    print(f"  - geology_zones cell_counts={aux_manifest['geology_zones']['cell_counts']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
