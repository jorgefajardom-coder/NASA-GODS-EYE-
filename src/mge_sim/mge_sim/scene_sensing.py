"""SIMULATED on-board sensing of a declared test scene. No ROS imports.

The scene is the simulation's ground truth: public prior heights plus a
declared set of blocked cells (for instance from `mge_sim.obstacle_field`). It is
a synthetic test scene, never a NASA measurement or evaluator reference.

Each sensing agent sees the cells whose centres lie within its radius. The
ledger decides what to report so motion is not interrupted for nothing:
  * while an agent moves, a report is sent only when it sees a blocked cell
    that was never reported (a hazard ahead); the report then carries every
    unreported cell in view, free ones included;
  * while an agent is stopped, any unreported cells in view are reported
    (coverage costs no interruption).
A report is retired only when its values are present in one coherent public
map batch; a version advance alone never acknowledges it. There is one report
in flight. After a timeout its footprint needs a fresh acquisition, rather than
a retagged retry. Deferred drone sightings keep their acquisition contexts;
only the current footprint is newly sampled when the drone stops. Publishing
an entire historical flight survey requires a separately reconciled contract.
"""
from dataclasses import dataclass, field
import json
import math
import struct

SCENE_SCHEMA = 'mge-sim-scene-1.0.0'


@dataclass(frozen=True)
class Scene:
    rows: int
    cols: int
    origin_x_m: float
    origin_y_m: float
    resolution_m: float
    heights: tuple            # row-major truth heights; None for NoData
    blocked: frozenset        # flat indices of blocked cells

    def centre(self, cell):
        r, c = divmod(cell, self.cols)
        return (self.origin_x_m + (c + 0.5) * self.resolution_m,
                self.origin_y_m + (r + 0.5) * self.resolution_m)


def scene_from_file(path, grid, heights):
    """Read a SIMULATED scene file for `grid` = (rows, cols, origin_x, origin_y, resolution)."""
    with open(path, encoding='utf-8') as f:
        data = json.load(f)
    if data.get('schema_version') != SCENE_SCHEMA:
        raise ValueError(f'scene schema must be {SCENE_SCHEMA}')
    if data.get('source_kind') != 'SIMULATED':
        raise ValueError('a scene is a SIMULATED test input')
    rows, cols, ox, oy, res = grid
    if (data.get('rows'), data.get('cols')) != (rows, cols):
        raise ValueError('scene grid differs from the terrain grid')
    if len(heights) != rows * cols:
        raise ValueError('heights must cover the grid')
    blocked = data.get('blocked', [])
    if any(type(i) is not int or not 0 <= i < rows * cols for i in blocked):
        raise ValueError('blocked cells must be in-grid flat indices')
    clean = tuple(None if h is None or not math.isfinite(h) else float(h) for h in heights)
    return Scene(rows, cols, float(ox), float(oy), float(res), clean, frozenset(blocked))


def footprint(scene, x, y, radius_m):
    """In-grid cells with finite truth height whose centre lies within `radius_m` of (x, y)."""
    if not all(math.isfinite(v) for v in (x, y, radius_m)) or radius_m < 0:
        return []
    res = scene.resolution_m
    c0 = math.floor((x - radius_m - scene.origin_x_m) / res)
    c1 = math.floor((x + radius_m - scene.origin_x_m) / res)
    r0 = math.floor((y - radius_m - scene.origin_y_m) / res)
    r1 = math.floor((y + radius_m - scene.origin_y_m) / res)
    out = []
    for r in range(max(0, r0), min(scene.rows - 1, r1) + 1):
        for c in range(max(0, c0), min(scene.cols - 1, c1) + 1):
            cell = r * scene.cols + c
            cx, cy = scene.centre(cell)
            if math.hypot(cx - x, cy - y) <= radius_m and scene.heights[cell] is not None:
                out.append(cell)
    return out


@dataclass
class SensorLedger:
    resend_s: float = 3.0
    reported: set = field(default_factory=set)
    pending: dict = field(default_factory=dict)   # report id -> PendingReport (at most one)
    unconfirmed: dict = field(default_factory=dict)  # retained expired acquisitions, never counted as coverage
    defer: frozenset = frozenset()                  # agents that report only when stopped
    seen: dict = field(default_factory=dict)        # agent -> cell -> (acquisition ns, base version)

    def view(self, agent_id, in_view, moving, *, acquired_ns=0, base_version=0):
        """Remember deferred acquisitions without relabelling flight history as a new scan.

        Only the current footprint may be sampled when a deferred agent stops.
        Historical sightings retain their acquisition context for diagnosis; the
        current-base/global-clock fusion contract cannot accept their union as a
        newly acquired observation. Revisit those cells to acquire fresh evidence.
        """
        if agent_id not in self.defer:
            return in_view, moving
        memory = self.seen.setdefault(agent_id, {})
        memory.update((cell, (acquired_ns, base_version)) for cell in in_view)
        if moving:
            return [], True
        return in_view, False

    def confirm(self, feedback):
        """Retire a footprint only when a coherent public batch contains its evidence.

        A version advance is not an acknowledgement of an observation ID. This
        proves the requested values are public, not which producer supplied them.
        """
        if feedback is None:
            return
        for rid, report in list(self.pending.items()):
            if feedback.contains(report):
                self.reported.update(report.cells)
                del self.pending[rid]

    def expire(self, now_s):
        for rid, report in list(self.pending.items()):
            if now_s - report.sent_at_s >= self.resend_s:
                self.unconfirmed[rid] = report
                del self.pending[rid]

    def select(self, scene, in_view, moving):
        """Cells to report now, or [] when nothing should be sent."""
        if self.pending:
            return []       # serialize globally, including different agents and disjoint footprints
        new = sorted(set(in_view) - self.reported)
        if not new:
            return []
        if moving and not any(c in scene.blocked for c in new):
            return []
        return new

    def sent(self, report_id, cells, base_version, now_s, *, acquired_ns, values):
        if self.pending:
            raise ValueError('only one observation may await public evidence')
        self.pending[report_id] = PendingReport(
            tuple(cells), base_version, now_s, acquired_ns,
            tuple(tuple(v) for v in values))


@dataclass(frozen=True)
class PendingReport:
    cells: tuple
    base_version: int
    sent_at_s: float
    acquired_ns: int
    values: tuple               # elevation, sigma, obstacle parallel arrays


def float32(value):
    """The public raster and TerrainObservation arrays both use ROS float32."""
    return struct.unpack('<f', struct.pack('<f', value))[0]


@dataclass(frozen=True)
class SensorFeedback:
    version: int
    stamp_ns: int
    belief: tuple
    sigma: tuple
    observed: tuple
    traversability: tuple

    def contains(self, report):
        if self.version <= report.base_version or self.stamp_ns < report.acquired_ns:
            return False
        heights, sigmas, obstacles = report.values
        return all(self.observed[c] == 1
                   and self.belief[c] == float32(h)
                   and self.sigma[c] == float32(s)
                   and self.traversability[c] == obstacle
                   for c, h, s, obstacle in zip(report.cells, heights, sigmas, obstacles))


class FeedbackBatches:
    """Consume the existing stamped public topics; incomplete/mixed batches never confirm.

    The drone mask is used only as evidence: a requested FREE cell must be 0,
    a requested obstacle 100. UNKNOWN or a policy/slope ambiguity stays pending.
    No obstacle classification is inferred from a human slope restriction.
    """
    layers = frozenset(('belief', 'sigma', 'observed', 'traversability'))

    def __init__(self, count):
        self.count = count
        self.version = 0
        self.stamp_ns = -1
        self.pending = {}

    def on_meta(self, version, stamp_ns):
        if version < self.version:
            return
        if ((version == self.version and stamp_ns != self.stamp_ns)
                or (version > self.version and stamp_ns <= self.stamp_ns)):
            raise ValueError('map version/stamp identity changed or clock moved backwards')
        self.version, self.stamp_ns = version, stamp_ns

    def on_layer(self, name, stamp_ns, values):
        if name not in self.layers or len(values) != self.count:
            raise ValueError('feedback layer name/shape does not match the scene')
        values = tuple(values)
        if name in ('belief', 'sigma'):
            # Mapping may publish +inf sigma for NoData. It can never match a
            # report's finite sigma; do not disable valid cells elsewhere.
            if any((name == 'belief' and math.isinf(v)) or (name == 'sigma' and v < 0) for v in values):
                raise ValueError('invalid public feedback values')
        elif any(v not in ((0, 1) if name == 'observed' else (-1, 0, 100)) for v in values):
            raise ValueError('invalid feedback occupancy/mask')
        batch = self.pending.setdefault(stamp_ns, {})
        previous = batch.get(name)
        if previous is not None and any(a != b and not (math.isnan(a) and math.isnan(b))
                for a, b in zip(previous, values)):
            raise ValueError('feedback layer changed under the same stamp')
        batch[name] = values
        while len(self.pending) > 8:
            del self.pending[min(self.pending)]

    def current(self):
        batch = self.pending.get(self.stamp_ns, {})
        if set(batch) != self.layers:
            return None
        return SensorFeedback(self.version, self.stamp_ns, **batch)


def stamp_ns(stamp):
    if (type(stamp.sec) is not int or not 0 <= stamp.sec < 2**31
            or type(stamp.nanosec) is not int or not 0 <= stamp.nanosec < 1_000_000_000):
        raise ValueError('invalid ROS acquisition stamp')
    return stamp.sec * 1_000_000_000 + stamp.nanosec


class FreshTelemetry:
    """Ordered, bounded-age telemetry. A backwards clock requires a new run/node."""

    def __init__(self, run_id, agent_ids, max_age_s):
        if not math.isfinite(max_age_s) or max_age_s <= 0:
            raise ValueError('telemetry_max_age_s must be positive and finite')
        self.run_id, self.agent_ids = run_id, frozenset(agent_ids)
        self.max_age_ns = round(max_age_s * 1_000_000_000)
        self.states, self.used = {}, {}
        self.last_clock_ns = None
        self.clock_failed = False

    def clock(self, now_ns):
        if self.last_clock_ns is not None and now_ns < self.last_clock_ns:
            self.clock_failed = True
            self.states.clear()
        self.last_clock_ns = now_ns
        return not self.clock_failed

    def accept(self, msg, now_ns):
        if not self.clock(now_ns):
            return False
        if (msg.run_id != self.run_id or msg.header.frame_id != 'map'
                or msg.agent_id not in self.agent_ids):
            return False
        try:
            acquired = stamp_ns(msg.header.stamp)
        except ValueError:
            return False
        p, v, a = msg.pose.position, msg.velocity.linear, msg.velocity.angular
        if (msg.mode not in {'IDLE', 'MOVING', 'OBSERVING', 'WORKING', 'RETURNING', 'HALTED'}
                or not all(math.isfinite(x) for x in (p.x, p.y, p.z, v.x, v.y, v.z, a.x, a.y, a.z))
                or not 0 <= now_ns - acquired <= self.max_age_ns):
            return False
        previous = self.states.get(msg.agent_id)
        if previous is not None and acquired <= stamp_ns(previous.header.stamp):
            return False
        self.states[msg.agent_id] = msg
        return True

    def acquire(self, agent_id, now_ns, min_stamp_ns):
        msg = self.states.get(agent_id)
        if not self.clock(now_ns) or msg is None:
            return None
        acquired = stamp_ns(msg.header.stamp)
        if (not 0 <= now_ns - acquired <= self.max_age_ns or acquired < min_stamp_ns
                or acquired <= self.used.get(agent_id, -1)):
            return None
        self.used[agent_id] = acquired
        return msg


def observation_values(scene, cells, sigma_m):
    """Parallel arrays for a TerrainObservation: truth heights, sigma and obstacle codes."""
    return ([scene.heights[c] for c in cells], [float(sigma_m)] * len(cells),
            [100 if c in scene.blocked else 0 for c in cells])
