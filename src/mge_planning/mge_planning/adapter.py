"""Strict ROS-shaped input adapters, importable without a ROS installation.

Native Image/OccupancyGrid lack run/version IDs. The producer must confirm the
ICD batch protocol: metadata first, globally unique snapshot stamp, then all
layers at that stamp. No layer is inferred from arrival order or prior terrain.
"""

from dataclasses import dataclass
import hashlib
import json
from math import isfinite, isnan
from pathlib import Path
from threading import RLock

import numpy as np

from .core import MotionProfile, PlanRequest, ResourceBudget, RouteMode, TerrainGrid


def stamp_key(header):
    if header.frame_id != "map":
        raise ValueError("frame must be map")
    sec, ns = header.stamp.sec, header.stamp.nanosec
    if type(sec) is not int or type(ns) is not int or sec < 0 or not 0 <= ns < 10**9:
        raise ValueError("invalid simulation timestamp")
    return sec, ns


@dataclass(frozen=True)
class GridMeta:
    run_id: str
    dataset_id: str
    map_version: int
    rows: int
    cols: int
    resolution_m: float
    origin_x_m: float
    origin_y_m: float
    nodata_value: float
    crs: str
    vertical_datum: str
    stamp: tuple[int, int]


class SnapshotStore:
    """Assemble only explicit, matching metadata/belief/sigma/profile-mask batches."""

    def __init__(self):
        self.lock = RLock()
        self.meta = None
        self.layers = {}
        self.stamp_owners = {}
        self.retired_runs = set()
        self.revision = 0
        self.error = ""

    @property
    def key(self):
        with self.lock:
            m = self.meta
            return None if m is None else (m.run_id, m.map_version, m.stamp, self.revision, self.error)

    @property
    def batch_key(self):
        """Identity of the inputs a search used: one immutable batch, unless it was rejected.

        Unlike `key`, the arrival of another agent kind's mask for the same batch does not
        change it: layers are immutable within a stamp, and a changed layer sets `error`.
        """
        with self.lock:
            m = self.meta
            return None if m is None else (m.run_id, m.map_version, m.stamp, self.error)

    def invalidate(self, reason="INVALID_SNAPSHOT"):
        with self.lock:
            self.error = reason
            self.revision += 1

    def ingest_meta(self, message):
        stamp = stamp_key(message.header)
        if not message.run_id or not message.dataset_id:
            raise ValueError("run and dataset identifiers required")
        if any(type(v) is not int or v <= 0 for v in (message.rows, message.cols)):
            raise ValueError("positive integer grid dimensions required")
        if type(message.map_version) is not int or not 0 <= message.map_version < 2**32:
            raise ValueError("invalid map version")
        if not all(isfinite(v) for v in (message.resolution_m, message.origin_x_m, message.origin_y_m)):
            raise ValueError("nonfinite grid geometry")
        if message.resolution_m <= 0 or not message.crs or not message.vertical_datum:
            raise ValueError("grid resolution, planetary CRS and datum required")
        meta = GridMeta(message.run_id, message.dataset_id, message.map_version,
                        message.rows, message.cols, message.resolution_m,
                        message.origin_x_m, message.origin_y_m,
                        message.nodata_value, message.crs, message.vertical_datum, stamp)
        owner = (meta.run_id, meta.map_version)
        with self.lock:
            if meta.run_id in self.retired_runs:
                return False
            previous_owner = self.stamp_owners.get(stamp)
            if previous_owner is not None and previous_owner != owner:
                raise ValueError("snapshot timestamp reused across runs or versions")
            if self.meta and self.meta.run_id == meta.run_id:
                if meta.map_version < self.meta.map_version:
                    return False  # Late metadata cannot roll the map backwards.
                if meta.map_version == self.meta.map_version:
                    # A version identifies one immutable batch, including geometry.
                    old = self.meta
                    fields = ("dataset_id", "rows", "cols", "resolution_m", "origin_x_m", "origin_y_m", "crs", "vertical_datum", "stamp")
                    if any(getattr(old, f) != getattr(meta, f) for f in fields):
                        raise ValueError("metadata changed without a new version")
                    if old.nodata_value != meta.nodata_value and not (isnan(old.nodata_value) and isnan(meta.nodata_value)):
                        raise ValueError("NoData changed without a new version")
                    return True
            if self.meta and self.meta.run_id != meta.run_id:
                self.retired_runs.add(self.meta.run_id)
            self.stamp_owners[stamp] = owner
            self.meta = meta
            self.layers = {}
            self.error = ""
            self.revision += 1
            return True

    def _put_layer(self, name, array):
        previous = self.layers.get(name)
        if previous is not None:
            if not np.array_equal(previous, array, equal_nan=True):
                self.invalidate("IMMUTABLE_BATCH_CHANGED")
                raise ValueError("native layer changed without a new map version")
            return
        self.layers[name] = array.copy()
        self.revision += 1

    def _matches(self, header):
        return self.meta is not None and stamp_key(header) == self.meta.stamp

    def ingest_image(self, name, message):
        if name not in {"belief", "sigma"}:
            raise ValueError("only public belief and sigma images are accepted")
        with self.lock:
            if not self._matches(message.header):
                return False
            m = self.meta
            if (message.height, message.width) != (m.rows, m.cols) or message.encoding != "32FC1":
                raise ValueError("image shape/encoding does not match metadata")
            if message.step < m.cols * 4 or message.step % 4 or len(message.data) != message.step * m.rows:
                raise ValueError("invalid 32FC1 row stride or buffer length")
            dtype = ">f4" if message.is_bigendian else "<f4"
            array = np.frombuffer(bytes(message.data), dtype=dtype).reshape(m.rows, message.step // 4)
            array = array[:, :m.cols].astype(float, copy=True)
            if name == "belief" and isfinite(m.nodata_value):
                array[array == m.nodata_value] = np.nan
            self._put_layer(name, array)
            return True

    def ingest_mask(self, kind, message):
        if kind not in {"human", "rover", "drone"}:
            raise ValueError("unsupported agent kind")
        with self.lock:
            if not self._matches(message.header):
                return False
            m, info = self.meta, message.info
            q, position = info.origin.orientation, info.origin.position
            if (info.height, info.width) != (m.rows, m.cols) or len(message.data) != m.rows * m.cols:
                raise ValueError("mask shape does not match metadata")
            if not np.isclose(info.resolution, m.resolution_m, rtol=1e-7, atol=1e-8):
                raise ValueError("mask resolution mismatch")
            if not np.allclose([position.x, position.y, position.z], [m.origin_x_m, m.origin_y_m, 0.0], rtol=0, atol=1e-6):
                raise ValueError("mask origin mismatch")
            if not np.allclose([q.x, q.y, q.z, abs(q.w)], [0, 0, 0, 1], rtol=0, atol=1e-6):
                raise ValueError("rotated grids are not supported by the ENU contract")
            array = np.asarray(message.data, dtype=int).reshape(m.rows, m.cols)
            if not np.isin(array, [-1, 0, 100]).all():
                raise ValueError("mask values must be -1, 0 or 100")
            self._put_layer(kind, array)
            return True

    def snapshot(self, kind):
        with self.lock:
            if self.meta is None:
                return None, "MAP_NOT_READY"
            if self.error:
                return None, self.error
            if any(k not in self.layers for k in ("belief", "sigma", kind)):
                return None, "SNAPSHOT_INCOMPLETE"
            m = self.meta
            return TerrainGrid(
                run_id=m.run_id, map_version=m.map_version,
                elevation_m=self.layers["belief"], sigma_m=self.layers["sigma"],
                traversability=self.layers[kind], resolution_m=m.resolution_m,
                origin_x_m=m.origin_x_m, origin_y_m=m.origin_y_m,
            ), ""


def load_profiles(path, allow_illustrative=False):
    if not path:
        return {}
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    status = data.get("status")
    if status != "approved" and not (status == "illustrative" and allow_illustrative):
        raise ValueError("profiles need scientific approval or explicit illustrative opt-in")
    if not isinstance(data.get("profiles"), dict):
        raise ValueError("profiles must map agent IDs to explicit motion parameters")
    return {agent_id: MotionProfile(**values) for agent_id, values in data["profiles"].items()}


def request_from_ros(message):
    kind = {"HUMAN": "human", "ROVER": "rover", "DRONE": "drone"}.get(message.agent_kind)
    if kind is None:
        raise ValueError("unknown ROS agent kind")
    if kind != "human" and not all(isnan(v) for v in (message.oxygen_budget_l, message.reserve_oxygen_l)):
        raise ValueError("non-human ROS oxygen fields must be NaN")
    budget = ResourceBudget(kind, message.time_budget_s, message.energy_budget_wh,
                            message.reserve_wh,
                            message.oxygen_budget_l if kind == "human" else None,
                            message.reserve_oxygen_l if kind == "human" else None)
    return PlanRequest(
        run_id=message.run_id, request_id=message.request_id,
        agent_id=message.agent_id, agent_kind=kind, map_version=message.map_version,
        start=(message.start.x, message.start.y, message.start.z),
        goal=(message.goal.x, message.goal.y, message.goal.z),
        return_to=(message.return_to.x, message.return_to.y, message.return_to.z),
        require_return=message.require_return, mode=RouteMode(message.mode),
        budget=budget, service_time_s=message.service_time_s,
        reserve_time_s=message.reserve_time_s,
    )


def load_unverified_prior(manifest_path, run_id, map_version=0):
    """Load a public prior as unknown; finite NASA heights do not verify mobility."""
    path = Path(manifest_path)
    manifest = json.loads(path.read_text(encoding="utf-8"))
    if manifest.get("role") != "prior" or manifest.get("row_orientation") != "south_to_north":
        raise ValueError("a public south-first prior manifest is required")
    artifact = (path.parent / manifest["artifact"]).resolve()
    if artifact.parent != path.parent.resolve():
        raise ValueError("prior artifact must remain inside its manifest directory")
    if hashlib.sha256(artifact.read_bytes()).hexdigest() != manifest["sha256"]:
        raise ValueError("prior artifact checksum mismatch")
    with np.load(artifact, allow_pickle=False) as archive:
        heights = archive["elevation_m"].copy()
        valid = archive["valid_mask"].astype(bool)
    if heights.shape != (manifest["rows"], manifest["cols"]) or valid.shape != heights.shape:
        raise ValueError("prior array dimensions do not match manifest")
    heights[~valid] = np.nan
    return TerrainGrid(run_id=run_id, map_version=map_version, elevation_m=heights,
                       sigma_m=np.full(heights.shape, np.nan),
                       traversability=np.full(heights.shape, -1, dtype=np.int8),
                       resolution_m=manifest["resolution_m"], origin_x_m=manifest["origin_x_m"],
                       origin_y_m=manifest["origin_y_m"])
