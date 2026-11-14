"""Pure, bounded resource-constrained planning on a public ENU belief grid.

This module contains no NASA evaluator/reference input and no certified mobility
or EVA defaults. Profiles must be supplied explicitly. FAST minimizes complete
mission time under all resource constraints. SAFE maximizes the minimum
conservative footprint clearance, breaking ties by FAST. Neither publishes an
active route: that authority belongs to MissionManager.
"""

from dataclasses import dataclass
from enum import Enum
import hashlib
import heapq
import math
from time import monotonic
from typing import Any

import numpy as np
from scipy.spatial import cKDTree


class RouteStatus(str, Enum):
    FEASIBLE = "FEASIBLE"
    UNKNOWN = "UNKNOWN"
    NO_PATH = "NO_PATH"
    INSUFFICIENT_BUDGET = "INSUFFICIENT_BUDGET"
    STALE_MAP = "STALE_MAP"
    ERROR = "ERROR"


class RouteMode(str, Enum):
    FAST = "FAST"
    SAFE = "SAFE"
    EFFICIENT = "EFFICIENT"


def _number(value, name, *, positive=False):
    if isinstance(value, (bool, np.bool_)):
        raise ValueError(f"{name} must be a finite number")
    try:
        valid = math.isfinite(value) and (value > 0 if positive else value >= 0)
    except (TypeError, ValueError):
        valid = False
    if not valid:
        raise ValueError(f"{name} must be finite and {'positive' if positive else 'nonnegative'}")


def _integer(value, name, *, positive=False):
    if type(value) is not int or value < (1 if positive else 0):
        raise ValueError(f"{name} must be a {'positive' if positive else 'nonnegative'} integer")


@dataclass(frozen=True)
class ResourceBudget:
    """Hypothetical simulation resources; oxygen is applicable to humans only."""
    agent_kind: str
    time_s: float
    energy_wh: float
    reserve_wh: float
    oxygen_l: float | None = None
    reserve_oxygen_l: float | None = None

    def __post_init__(self):
        if self.agent_kind not in {"human", "rover", "drone"}:
            raise ValueError("agent_kind must be human, rover or drone")
        for name in ("time_s", "energy_wh", "reserve_wh"):
            _number(getattr(self, name), name)
        if self.reserve_wh > self.energy_wh:
            raise ValueError("energy reserve exceeds available energy")
        if self.agent_kind == "human":
            if self.oxygen_l is None or self.reserve_oxygen_l is None:
                raise ValueError("a human requires a separate oxygen budget and reserve")
            _number(self.oxygen_l, "oxygen_l")
            _number(self.reserve_oxygen_l, "reserve_oxygen_l")
            if self.reserve_oxygen_l > self.oxygen_l:
                raise ValueError("oxygen reserve exceeds available oxygen")
        elif self.oxygen_l is not None or self.reserve_oxygen_l is not None:
            raise ValueError("rover and drone budgets must not include human oxygen")


@dataclass(frozen=True)
class TerrainGrid:
    """One immutable public snapshot; row zero is south and columns grow east.

    Traversability is -1 unknown, 0 admissible, 100 forbidden. Nonfinite height
    and invalid sigma become unknown rather than free. Elevation is the public
    belief, never hidden evaluator reference. Arrays are defensively copied.
    """
    run_id: str
    map_version: int
    elevation_m: Any
    traversability: Any
    resolution_m: float
    origin_x_m: float = 0.0
    origin_y_m: float = 0.0
    frame_id: str = "map"
    sigma_m: Any = None

    def __post_init__(self):
        if not isinstance(self.run_id, str) or not self.run_id:
            raise ValueError("run_id is required")
        _integer(self.map_version, "map_version")
        if self.map_version > 2**32 - 1:
            raise ValueError("map_version exceeds ROS uint32")
        if self.frame_id != "map":
            raise ValueError("frame_id must be map")
        _number(self.resolution_m, "resolution_m", positive=True)
        if not all(math.isfinite(x) for x in (self.origin_x_m, self.origin_y_m)):
            raise ValueError("origin must be finite")
        height = np.array(self.elevation_m, dtype=float, copy=True)
        mask = np.array(self.traversability, copy=True)
        if height.ndim != 2 or not height.size or mask.shape != height.shape:
            raise ValueError("height and traversability must be nonempty equal 2-D grids")
        if not np.isin(mask, (-1, 0, 100)).all():
            raise ValueError("traversability must contain only -1, 0 or 100")
        mask = mask.astype(np.int8)
        sigma = None if self.sigma_m is None else np.array(self.sigma_m, dtype=float, copy=True)
        if sigma is not None and sigma.shape != height.shape:
            raise ValueError("sigma must match the height grid")
        for name, array in (("elevation_m", height), ("traversability", mask), ("sigma_m", sigma)):
            if array is not None:
                array.setflags(write=False)
            object.__setattr__(self, name, array)

    @property
    def rows(self):
        return self.elevation_m.shape[0]

    @property
    def cols(self):
        return self.elevation_m.shape[1]

    def cell(self, point):
        if len(point) not in (2, 3) or not all(math.isfinite(x) for x in point):
            raise ValueError("positions must contain two or three finite coordinates")
        c = math.floor((point[0] - self.origin_x_m) / self.resolution_m)
        r = math.floor((point[1] - self.origin_y_m) / self.resolution_m)
        if not (0 <= r < self.rows and 0 <= c < self.cols):
            raise ValueError("position is outside the terrain grid")
        return int(r), int(c)

    def point(self, cell):
        r, c = cell
        return (self.origin_x_m + (c + .5) * self.resolution_m,
                self.origin_y_m + (r + .5) * self.resolution_m,
                float(self.elevation_m[r, c]))


@dataclass(frozen=True)
class MotionProfile:
    """Explicit illustrative/approved model, with no scientific numeric defaults.

    Let h be horizontal edge length, d be 3-D length, u=max(dz,0)/h and
    v=max(-dz,0)/h. time=d/speed*(1+uphill_time_factor*u+downhill_time_factor*v).
    energy=d*energy_wh_per_m*(1+uphill_energy_factor*u+downhill_energy_factor*v).
    Human oxygen=time*oxygen_l_per_s. Service uses service_power_w*time/3600
    energy and the same human oxygen rate. Coefficients are nonnegative, giving
    an optimistic planar-distance/speed time heuristic. This is not physiology.
    """
    agent_kind: str
    speed_m_s: float
    max_slope_deg: float
    max_step_m: float
    radius_m: float
    localization_error_m: float
    energy_wh_per_m: float
    oxygen_l_per_s: float | None = None
    uphill_time_factor: float = 0.0
    downhill_time_factor: float = 0.0
    uphill_energy_factor: float = 0.0
    downhill_energy_factor: float = 0.0
    service_power_w: float = 0.0
    max_downhill_slope_deg: float | None = None
    max_sigma_m: float | None = None

    def __post_init__(self):
        if self.agent_kind not in {"human", "rover", "drone"}:
            raise ValueError("invalid profile agent kind")
        _number(self.speed_m_s, "speed_m_s", positive=True)
        for name in ("max_slope_deg", "max_step_m", "radius_m", "localization_error_m",
                     "energy_wh_per_m", "uphill_time_factor", "downhill_time_factor",
                     "uphill_energy_factor", "downhill_energy_factor", "service_power_w"):
            _number(getattr(self, name), name)
        if self.max_slope_deg > 90:
            raise ValueError("max_slope_deg must not exceed 90")
        if self.max_downhill_slope_deg is not None:
            _number(self.max_downhill_slope_deg, "max_downhill_slope_deg")
            if self.max_downhill_slope_deg > 90:
                raise ValueError("max_downhill_slope_deg must not exceed 90")
        if self.max_sigma_m is not None:
            _number(self.max_sigma_m, "max_sigma_m")
        if self.agent_kind == "human":
            if self.oxygen_l_per_s is None:
                raise ValueError("human profile requires oxygen_l_per_s")
            _number(self.oxygen_l_per_s, "oxygen_l_per_s")
        elif self.oxygen_l_per_s is not None:
            raise ValueError("nonhuman profile must not include human oxygen")


@dataclass(frozen=True)
class PlanRequest:
    run_id: str
    request_id: str
    agent_id: str
    agent_kind: str
    map_version: int
    start: tuple
    goal: tuple
    budget: ResourceBudget
    return_to: tuple | None = None
    require_return: bool = True
    mode: RouteMode | str = RouteMode.FAST
    service_time_s: float = 0.0
    reserve_time_s: float = 0.0

    def __post_init__(self):
        if not all(isinstance(x, str) and x for x in (self.run_id, self.request_id, self.agent_id)):
            raise ValueError("run, request and agent identifiers are required")
        _integer(self.map_version, "map_version")
        if self.agent_kind != self.budget.agent_kind:
            raise ValueError("request and budget agent kinds differ")
        if type(self.require_return) is not bool:
            raise ValueError("require_return must be boolean")
        _number(self.service_time_s, "service_time_s")
        _number(self.reserve_time_s, "reserve_time_s")
        if self.reserve_time_s > self.budget.time_s:
            raise ValueError("time reserve exceeds available time")
        for name in ("start", "goal", "return_to"):
            point = getattr(self, name)
            if point is not None:
                if len(point) not in (2, 3) or not all(math.isfinite(x) for x in point):
                    raise ValueError("positions must contain two or three finite coordinates")
                object.__setattr__(self, name, tuple(point))


@dataclass(frozen=True)
class SearchLimits:
    max_labels: int = 200000
    timeout_s: float = 2.0

    def __post_init__(self):
        _integer(self.max_labels, "max_labels", positive=True)
        _number(self.timeout_s, "timeout_s", positive=True)


@dataclass(frozen=True)
class StartConnector:
    """Validated directed segment to the containing cell centre (Python metadata).

    Costs are included in route totals, not additional charges. A 2-D input uses
    belief elevation; a supplied 3-D ground z must agree with that elevation.
    """
    start: tuple
    end: tuple
    distance_m: float
    travel_time_s: float
    energy_est_wh: float
    oxygen_est_l: float | None
    min_clearance_m: float


@dataclass(frozen=True)
class RouteResult:
    status: RouteStatus
    reason_code: str
    detail: str
    run_id: str
    request_id: str
    agent_id: str
    mode: str
    map_version_used: int
    route_id: str = ""
    outbound_path: tuple = ()
    return_path: tuple = ()
    travel_time_s: float | None = None
    energy_est_wh: float | None = None
    oxygen_est_l: float | None = None
    min_clearance_m: float | None = None
    reserve_time_s: float | None = None
    reserve_wh: float | None = None
    reserve_oxygen_l: float | None = None
    expanded_labels: int = 0
    elapsed_s: float = 0.0
    start_connector: StartConnector | None = None


class _LimitReached(Exception):
    pass


class _Work:
    def __init__(self, limits):
        self.limits, self.started, self.expanded = limits, monotonic(), 0

    def check(self, *, expand=False):
        if expand:
            self.expanded += 1
        if self.expanded > self.limits.max_labels or monotonic() - self.started >= self.limits.timeout_s:
            raise _LimitReached


_DIRECTIONS = ((-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1))


def _motion_costs(profile, horizontal, dz):
    """Shared directed transition limits and nonnegative movement costs."""
    p = profile
    slope = math.degrees(math.atan2(abs(dz), horizontal))
    limit = p.max_slope_deg if dz >= 0 or p.max_downhill_slope_deg is None else p.max_downhill_slope_deg
    if abs(dz) > p.max_step_m or slope > limit:
        return None
    length = math.hypot(horizontal, dz)
    up, down = max(dz, 0)/horizontal, max(-dz, 0)/horizontal
    duration = length/p.speed_m_s*(1+p.uphill_time_factor*up+p.downhill_time_factor*down)
    energy = length*p.energy_wh_per_m*(1+p.uphill_energy_factor*up+p.downhill_energy_factor*down)
    return duration, energy, duration*(p.oxygen_l_per_s or 0.)


def _segment_clearance(geometry, a, b, max_samples=10000):
    """One conservative swept-footprint bound for search, connector and policy.

    Uniform spacing <= resolution/4, minus half that spacing, covers the whole
    segment by 1-Lipschitz continuity. Zero obstacle contact is inadmissible;
    boundary tangency is allowed when the entire footprint stays within the map.
    None indicates a validation work limit, never collision-free geometry.
    """
    h = math.dist(a[:2], b[:2])
    count = max(5, math.ceil(h/(geometry.grid.resolution_m/4))+1)
    if count > max_samples:
        return None
    points = np.linspace(a[:2], b[:2], count)
    margin = float(np.min(geometry._boundary(points)))-geometry.radius
    if geometry.tree is not None:
        obstacle = (float(np.min(geometry.tree.query(points)[0]))
                    - geometry.grid.resolution_m/math.sqrt(2)
                    - h/(2*(count-1))-geometry.radius)
        if obstacle <= 0:
            return min(margin, obstacle, -np.finfo(float).eps)
        margin = min(margin, obstacle)
    return margin


def _start_z_mismatch(grid, point, kind, profile=None):
    """A supplied ground z is a consistency check, never an altitude command."""
    if kind in {"human", "rover"} and len(point) == 3:
        cell = grid.cell(point)
        if grid.traversability[cell] != 0:
            return False  # Unresolved terrain is UNKNOWN, not an asserted z error.
        if grid.sigma_m is not None:
            sigma = grid.sigma_m[cell]
            if (not math.isfinite(sigma) or sigma < 0
                    or (profile is not None and profile.max_sigma_m is not None and sigma > profile.max_sigma_m)):
                return False
        elif profile is not None and profile.max_sigma_m is not None:
            return False
        z = grid.point(cell)[2]
        return math.isfinite(z) and abs(point[2]-z) > 1e-6
    return False


class GeometryCache:
    """Bounded geometry reuse for one immutable snapshot and up to four profiles.

    Arrays must retain TerrainGrid's read-only contract. A different snapshot
    object clears the cache, even if its run/version strings were reused.
    Call serially; never use as an asynchronous snapshot/authorization store.
    """
    def __init__(self):
        self.grid = None
        self.entries = {}

    def get(self, grid, profile, *, optimistic=False):
        if self.grid is not grid:
            self.grid, self.entries = grid, {}
        key = profile, optimistic
        if key not in self.entries:
            if len(self.entries) >= 8:
                self.entries.clear()
            self.entries[key] = _Geometry(grid, profile, optimistic=optimistic)
        return self.entries[key]


class _Geometry:
    def __init__(self, grid, profile, *, optimistic=False):
        self.grid, self.profile, self.optimistic = grid, profile, optimistic
        known = (grid.traversability == 0) & np.isfinite(grid.elevation_m)
        if grid.sigma_m is not None:
            known &= np.isfinite(grid.sigma_m) & (grid.sigma_m >= 0)
            if profile.max_sigma_m is not None:
                known &= grid.sigma_m <= profile.max_sigma_m
        elif profile.max_sigma_m is not None:
            known[:] = False
        self.known = known
        self.allowed = grid.traversability != 100 if optimistic else known
        blocked = np.argwhere(~self.allowed)
        self.tree = None
        if len(blocked):
            centres = np.column_stack((grid.origin_x_m + (blocked[:, 1] + .5) * grid.resolution_m,
                                       grid.origin_y_m + (blocked[:, 0] + .5) * grid.resolution_m))
            self.tree = cKDTree(centres)
        self.radius = profile.radius_m + profile.localization_error_m
        rr, cc = np.indices(grid.elevation_m.shape)
        points = np.column_stack((grid.origin_x_m + (cc.ravel() + .5) * grid.resolution_m,
                                  grid.origin_y_m + (rr.ravel() + .5) * grid.resolution_m))
        self.clearance = self._point_clearance(points).reshape(grid.elevation_m.shape)
        self.allowed = self.allowed & (self.clearance >= 0)
        self.cache = {}

    def _boundary(self, points):
        g = self.grid
        return np.minimum.reduce((points[:, 0] - g.origin_x_m,
                                  g.origin_x_m + g.cols*g.resolution_m - points[:, 0],
                                  points[:, 1] - g.origin_y_m,
                                  g.origin_y_m + g.rows*g.resolution_m - points[:, 1]))

    def _point_clearance(self, points):
        """Vectorized zero-length form of the shared swept-footprint bound."""
        bound = self._boundary(points) - self.radius
        if self.tree is not None:
            distance = self.tree.query(points)[0] - self.grid.resolution_m / math.sqrt(2) - self.radius
            distance = np.where(distance <= 0, np.minimum(distance, -np.finfo(float).eps), distance)
            bound = np.minimum(bound, distance)
        return bound

    def connect_start(self, position, cell):
        """Conservative within-cell connector; never jump to another free cell.

        The containing cell is convex, so the centre segment cannot cross any
        other cell interior. The swept footprint is checked against ALL blocked
        (including unknown) cell squares via the shared lower distance bound:
        at least five samples minus half spacing and the square circumradius.
        Graph edges and policy validation reject the same nonpositive obstacle
        bound, so contact/corner crossings cannot be accepted.
        Optimistic use is diagnostic only and never yields an executable segment.
        """
        if not self.allowed[cell]:
            return None
        g, p = self.grid, self.profile
        end = g.point(cell)
        # Unknown elevations are flattened only for optimistic diagnosis.
        z = position[2] if len(position) == 3 else end[2]
        if self.optimistic and not self.known[cell]:
            z = z if math.isfinite(z) else 0.
            end = (*end[:2], z)
        start = (position[0], position[1], z)
        a, b = np.array(start[:2]), np.array(end[:2])
        horizontal = float(np.linalg.norm(b-a))
        costs = _motion_costs(p, horizontal, end[2]-start[2])
        if costs is None:
            return None
        margin = _segment_clearance(self, start, end)
        if margin is None or margin < 0:
            return None
        duration, energy, oxygen = costs
        return StartConnector(start, end, math.hypot(horizontal, end[2]-start[2]),
                              duration, energy, oxygen if p.agent_kind == "human" else None,
                              min(margin, float(self.clearance[cell])))

    def edge(self, a, b):
        """Return conservative continuous-segment clearance and directed costs.

        Obstacle centre distance minus its square's circumradius bounds distance
        to the entire occupied cell. Segment samples minus half their spacing
        extend the bound between samples (distance is 1-Lipschitz). The boundary
        is handled exactly for the straight segment. Conservative rejection is
        intentional and part of the declared grid/footprint model.
        """
        if not self.allowed[b] or not self.allowed[a]:
            return None
        dr, dc = b[0]-a[0], b[1]-a[1]
        if dr and dc and (not self.allowed[a[0], b[1]] or not self.allowed[b[0], a[1]]):
            return None
        g, p = self.grid, self.profile
        horizontal = math.hypot(dr, dc)*g.resolution_m
        unknown = not self.known[a] or not self.known[b]
        dz = 0.0 if self.optimistic and unknown else float(g.elevation_m[b]-g.elevation_m[a])
        costs = _motion_costs(p, horizontal, dz)
        if costs is None:
            return None
        key = tuple(sorted((a, b)))
        if key not in self.cache:
            self.cache[key] = _segment_clearance(self, g.point(a), g.point(b))
        clearance = self.cache[key]
        if clearance is None or clearance < 0:
            return None
        return (clearance, *costs)

    def neighbours(self, cell, threshold=0.):
        for dr, dc in _DIRECTIONS:
            other = cell[0]+dr, cell[1]+dc
            if 0 <= other[0] < self.grid.rows and 0 <= other[1] < self.grid.cols:
                edge = self.edge(cell, other)
                if edge is not None and edge[0] >= threshold:
                    yield other, edge


@dataclass
class _Label:
    cell: tuple
    phase: int
    time: float
    energy: float
    oxygen: float
    parent: int | None
    clearance: float
    active: bool = True


@dataclass
class _Found:
    labels: list
    terminal: int
    connector: StartConnector | None = None


def _search(geometry, request, start, goal, back, threshold, work, connector=None):
    """Joint outbound/service/return A*; no independent-leg greedy selection."""
    g, p = geometry.grid, geometry.profile
    if any(not geometry.allowed[c] or geometry.clearance[c] < threshold for c in (start, goal, back)):
        return None
    if connector is not None and connector.min_clearance_m < threshold:
        return None
    budget = request.budget
    cap = (budget.time_s-request.reserve_time_s, budget.energy_wh-budget.reserve_wh,
           (budget.oxygen_l-budget.reserve_oxygen_l) if budget.agent_kind == "human" else math.inf)
    labels = []
    frontier = {}
    heap = []

    def heuristic(cell, phase):
        distance = lambda a, b: math.hypot(a[0]-b[0], a[1]-b[1])*g.resolution_m
        if phase:
            return distance(cell, back)/p.speed_m_s if request.require_return else 0.
        return (distance(cell, goal) + (distance(goal, back) if request.require_return else 0.))/p.speed_m_s + request.service_time_s

    def add(label):
        if label.time > cap[0] or label.energy > cap[1] or label.oxygen > cap[2]:
            return
        state = label.cell, label.phase
        current = frontier.setdefault(state, [])
        vector = label.time, label.energy, label.oxygen
        if any(all(x <= y for x, y in zip((labels[i].time, labels[i].energy, labels[i].oxygen), vector))
               for i in current):
            return
        retained = []
        for i in current:
            previous = labels[i]
            if all(x <= y for x, y in zip(vector, (previous.time, previous.energy, previous.oxygen))):
                previous.active = False
            else:
                retained.append(i)
        identifier = len(labels)
        labels.append(label)
        frontier[state] = retained + [identifier]
        heapq.heappush(heap, (label.time+heuristic(label.cell, label.phase), label.time, identifier))
        if len(labels) > work.limits.max_labels:
            raise _LimitReached

    add(_Label(start, 0, connector.travel_time_s if connector else 0.,
               connector.energy_est_wh if connector else 0.,
               (connector.oxygen_est_l or 0.) if connector else 0., None,
               connector.min_clearance_m if connector else float(geometry.clearance[start])))
    while heap:
        work.check(expand=True)
        _, _, identifier = heapq.heappop(heap)
        label = labels[identifier]
        if not label.active:
            continue
        if label.phase and (not request.require_return or label.cell == back):
            return _Found(labels, identifier, connector)
        if label.phase == 0 and label.cell == goal:
            dt = request.service_time_s
            add(_Label(label.cell, 1, label.time+dt, label.energy+p.service_power_w*dt/3600.,
                       label.oxygen+dt*(p.oxygen_l_per_s or 0.), identifier, label.clearance))
            continue
        for other, edge in geometry.neighbours(label.cell, threshold):
            margin, duration, energy, oxygen = edge
            add(_Label(other, label.phase, label.time+duration, label.energy+energy,
                       label.oxygen+oxygen, identifier, min(label.clearance, margin)))
    return None


def _connected(geometry, start, goal, back, request, work):
    """Exhaustively diagnose geometry without budgets; never create output paths."""
    if any(not geometry.allowed[c] for c in (start, goal, back)):
        return False
    for source, target in ((start, goal), (goal, back)) if request.require_return else ((start, goal),):
        todo = [source]
        seen = {source}
        while todo:
            work.check(expand=True)
            cell = todo.pop()
            if cell == target:
                break
            for other, _ in geometry.neighbours(cell):
                if other not in seen:
                    seen.add(other); todo.append(other)
        else:
            return False
    return True


def _result(request, grid, work, status, reason, detail, found=None):
    mode = request.mode.value if isinstance(request.mode, RouteMode) else request.mode
    common = dict(status=status, reason_code=reason, detail=detail, run_id=request.run_id,
                  request_id=request.request_id, agent_id=request.agent_id, mode=mode,
                  map_version_used=grid.map_version, expanded_labels=work.expanded,
                  elapsed_s=monotonic()-work.started)
    if found is None:
        return RouteResult(**common)
    final = found.labels[found.terminal]
    trail = []
    identifier = found.terminal
    while identifier is not None:
        label = found.labels[identifier]; trail.append(label)
        identifier = label.parent
    trail.reverse()
    outbound = tuple(grid.point(x.cell) for x in trail if x.phase == 0)
    if found.connector is not None:
        outbound = (found.connector.start,) + outbound
    inbound = tuple(grid.point(x.cell) for x in trail if x.phase == 1) if request.require_return else ()
    digest = hashlib.sha256(repr((request.run_id, request.request_id, request.agent_id,
                                 grid.map_version, mode, outbound, inbound, final.time,
                                 final.energy, final.oxygen)).encode()).hexdigest()[:24]
    human = request.agent_kind == "human"
    return RouteResult(**common, route_id=f"route-{digest}", outbound_path=outbound,
                       return_path=inbound, travel_time_s=final.time, energy_est_wh=final.energy,
                       oxygen_est_l=final.oxygen if human else None, min_clearance_m=final.clearance,
                       reserve_time_s=request.budget.time_s-final.time,
                       reserve_wh=request.budget.energy_wh-final.energy,
                       reserve_oxygen_l=request.budget.oxygen_l-final.oxygen if human else None,
                       start_connector=found.connector)


def plan_route(*, terrain: TerrainGrid, request: PlanRequest,
               profile: MotionProfile | None = None, limits: SearchLimits | None = None,
               allow_continuous_start: bool = False, geometry_cache: GeometryCache | None = None) -> RouteResult:
    """Return a candidate under the supplied model, never an execution command.

    A missing profile, unresolved corridor or exhausted work bound yields UNKNOWN.
    EFFICIENT is intentionally unsupported. SAFE proves maximal known-grid
    bottleneck by repeatedly asking for a strictly better feasible clearance;
    a bound reached during that proof yields UNKNOWN rather than a false optimum.
    """
    work = _Work(limits or SearchLimits())
    result = lambda status, reason, detail, found=None: _result(request, terrain, work, status, reason, detail, found)
    if request.run_id != terrain.run_id:
        return result(RouteStatus.UNKNOWN, "RUN_MISMATCH", "Request and public map belong to different runs.")
    if request.map_version != terrain.map_version:
        return result(RouteStatus.STALE_MAP, "MAP_VERSION_MISMATCH", "Request does not match the current public map version.")
    if profile is None:
        return result(RouteStatus.UNKNOWN, "PROFILE_NOT_READY", "An explicit reviewed or illustrative motion profile is required.")
    if profile.agent_kind != request.agent_kind:
        return result(RouteStatus.ERROR, "PROFILE_KIND_MISMATCH", "Request and motion profile agent kinds differ.")
    try:
        mode = RouteMode(request.mode)
    except ValueError:
        return result(RouteStatus.ERROR, "MODE_NOT_SUPPORTED", "Requested route mode is unsupported.")
    if mode == RouteMode.EFFICIENT:
        return result(RouteStatus.ERROR, "MODE_NOT_SUPPORTED", "EFFICIENT awaits an independently verified energy model.")
    try:
        start = terrain.cell(request.start); goal = terrain.cell(request.goal)
        back = terrain.cell(request.return_to if request.return_to is not None else request.start) if request.require_return else goal
    except (ValueError, TypeError):
        return result(RouteStatus.ERROR, "INVALID_POSITION", "Positions must be finite and inside the ENU grid.")
    positions = [(request.goal, goal)]
    if request.require_return:
        positions.append((request.return_to if request.return_to is not None else request.start, back))
    if any(not all(abs(point[i]-terrain.point(cell)[i]) <= 1e-6 for i in (0, 1))
           for point, cell in positions):
        return result(RouteStatus.ERROR, "NON_CELL_CENTER",
                      "Goal and return target must be ENU cell centres; a continuous start requires an explicit centred return target.")
    continuous_start = any(abs(request.start[i]-terrain.point(start)[i]) > 1e-6 for i in (0, 1))
    if continuous_start and not allow_continuous_start:
        return result(RouteStatus.ERROR, "NON_CELL_CENTER",
                      "Continuous starts require an explicit experimental opt-in.")
    if _start_z_mismatch(terrain, request.start, request.agent_kind, profile):
        return result(RouteStatus.ERROR, "INVALID_START_Z",
                      "Supplied ground start z must match belief height within 1e-6 m; no vertical snapping is performed.")
    if continuous_start and request.agent_kind == "drone":
        return result(RouteStatus.ERROR, "CONTINUOUS_START_NOT_SUPPORTED",
                      "Continuous start connectors currently support ground agents only.")
    try:
        cache = geometry_cache if geometry_cache is not None else GeometryCache()
        known = cache.get(terrain, profile)
        work.check()
        connector = known.connect_start(request.start, start) if continuous_start else None
        if continuous_start and connector is None:
            optimistic = cache.get(terrain, profile, optimistic=True)
            work.check()
            if optimistic.connect_start(request.start, start) is not None:
                return result(RouteStatus.UNKNOWN, "UNVERIFIED_START_CONNECTOR",
                              "The start connector or its footprint depends on unresolved terrain.")
            return result(RouteStatus.NO_PATH, "NO_ADMISSIBLE_START_CONNECTOR",
                          "No admissible connection to the containing cell centre under the declared model; no other connector is attempted.")
        best = _search(known, request, start, goal, back, 0., work, connector)
        if best is None:
            if _connected(known, start, goal, back, request, work):
                if np.any(~known.known & (terrain.traversability != 100)):
                    return result(RouteStatus.UNKNOWN, "UNVERIFIED_BUDGET_CORRIDOR",
                                  "Known routes exceed resources, but unresolved terrain prevents a global budget impossibility claim.")
                return result(RouteStatus.INSUFFICIENT_BUDGET, "BUDGET_EXCEEDED", "No known-grid route fits outbound, service, return and reserves.")
            optimistic = cache.get(terrain, profile, optimistic=True)
            work.check()
            if _connected(optimistic, start, goal, back, request, work):
                return result(RouteStatus.UNKNOWN, "UNVERIFIED_CORRIDOR", "A possible corridor depends on unknown or unverified terrain.")
            return result(RouteStatus.NO_PATH, "NO_ADMISSIBLE_PATH", "The declared grid/profile model has no admissible complete route.")
        if mode == RouteMode.SAFE:
            while True:
                threshold = float(np.nextafter(best.labels[best.terminal].clearance, math.inf))
                candidate = _search(known, request, start, goal, back, threshold, work, connector)
                if candidate is None:
                    break
                best = candidate
        return result(RouteStatus.FEASIBLE, "FEASIBLE_UNDER_MODEL",
                      "Verified known-grid candidate under the supplied resource and conservative footprint model; not certified physical safety.", best)
    except _LimitReached:
        return result(RouteStatus.UNKNOWN, "SEARCH_LIMIT", "Search effort limit reached; feasibility or requested optimality is unresolved.")
