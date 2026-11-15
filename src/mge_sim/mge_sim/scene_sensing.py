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
A report counts as delivered only when the map version advances past the
version it was taken against; otherwise it is sent again after `resend_s`.
An agent in `defer` (a drone flying above ground obstacles) never reports while
moving: it remembers every cell it saw and reports them all once it stops, so a
flight is not interrupted by ground hazards it does not face.
"""
from dataclasses import dataclass, field
import json
import math

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
    pending: dict = field(default_factory=dict)   # report id -> (cells, base_version, sent_at)
    defer: frozenset = frozenset()                  # agents that report only when stopped
    seen: dict = field(default_factory=dict)        # deferring agent -> cells seen in motion

    def view(self, agent_id, in_view, moving):
        """Cells this agent may report now; a deferring agent in motion only remembers."""
        if agent_id not in self.defer:
            return in_view, moving
        memory = self.seen.setdefault(agent_id, set())
        memory.update(in_view)
        if moving:
            return [], True
        memory -= self.reported            # forget only what the map has confirmed
        return sorted(memory), False

    def confirm(self, map_version):
        """The map advanced: reports taken against older versions were applied."""
        for rid, (cells, base, _) in list(self.pending.items()):
            if map_version > base:
                self.reported.update(cells)
                del self.pending[rid]

    def expire(self, now_s):
        for rid, (_, _, sent) in list(self.pending.items()):
            if now_s - sent >= self.resend_s:
                del self.pending[rid]

    def select(self, scene, in_view, moving):
        """Cells to report now, or [] when nothing should be sent."""
        waiting = set().union(*(c for c, _, _ in self.pending.values())) if self.pending else set()
        new = sorted(set(in_view) - self.reported - waiting)
        if not new:
            return []
        if moving and not any(c in scene.blocked for c in new):
            return []
        return new

    def sent(self, report_id, cells, base_version, now_s):
        self.pending[report_id] = (tuple(cells), base_version, now_s)


def observation_values(scene, cells, sigma_m):
    """Parallel arrays for a TerrainObservation: truth heights, sigma and obstacle codes."""
    return ([scene.heights[c] for c in cells], [float(sigma_m)] * len(cells),
            [100 if c in scene.blocked else 0 for c in cells])
