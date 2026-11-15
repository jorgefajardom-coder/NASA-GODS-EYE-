"""Deterministic SIMULATED obstacle fields that agents must go around. No ROS imports.

`generate_field` places, inside an observed window of the map grid:
  * a ridge: a band of blocked cells across the base->goal line, perpendicular
    to it near its midpoint, with one gap placed off that line so the direct
    corridor is closed and a detour is required;
  * rock clusters: seeded blobs of blocked cells scattered in the window.
It never blocks the protected cells (base, goal, agent positions) or their
neighbours, never leaves the grid or the observed window, and keeps at least
one 4-connected free passage from base to goal: a rock cluster that would cut
every passage is dropped. The result is a test scene for the planner, not a
measurement; publish it only as a SIMULATED observation.
"""
from collections import deque
from dataclasses import dataclass, field
import math
import random


@dataclass
class ObstacleField:
    blocked: set = field(default_factory=set)      # (row, col) cells
    ridge: list = field(default_factory=list)      # (row, col) cells of the ridge band
    gap: list = field(default_factory=list)        # (row, col) cells left open in the ridge
    rocks: list = field(default_factory=list)      # list of cluster cell lists
    dropped: int = 0                                # clusters removed to keep a passage


def _neighbours4(cell):
    r, c = cell
    return ((r + 1, c), (r - 1, c), (r, c + 1), (r, c - 1))


def passage_exists(start, goal, free):
    """4-connected breadth-first search over the `free` cells (conservative: no diagonals)."""
    if start not in free or goal not in free:
        return False
    seen, queue = {start}, deque([start])
    while queue:
        cell = queue.popleft()
        if cell == goal:
            return True
        for n in _neighbours4(cell):
            if n in free and n not in seen:
                seen.add(n)
                queue.append(n)
    return False


def _halo(cells, rows, cols):
    out = set()
    for r, c in cells:
        for dr in (-1, 0, 1):
            for dc in (-1, 0, 1):
                if 0 <= r + dr < rows and 0 <= c + dc < cols:
                    out.add((r + dr, c + dc))
    return out


def generate_field(rows, cols, window, base, goal, protected=(), seed=0,
                   rock_clusters=6, rock_radius=(1, 2), ridge_gap_offset=4):
    """Return an ObstacleField inside `window` = (row0, row1, col0, col1), bounds inclusive.

    `base`, `goal` and `protected` are (row, col) cells that, with their neighbours,
    stay free. The same arguments always give the same field.
    """
    r0, r1, c0, c1 = window
    if not (0 <= r0 <= r1 < rows and 0 <= c0 <= c1 < cols):
        raise ValueError('window must lie inside the grid')
    area = {(r, c) for r in range(r0, r1 + 1) for c in range(c0, c1 + 1)}
    for cell in (base, goal):
        if cell not in area:
            raise ValueError(f'{cell} is outside the observed window')
    keep = _halo([base, goal, *protected], rows, cols)
    rng = random.Random(seed)
    result = ObstacleField()

    # Ridge perpendicular to base->goal through its midpoint, clipped to the window.
    (br, bc), (gr, gc) = base, goal
    dr, dc = gr - br, gc - bc
    length = math.hypot(dr, dc) or 1.0
    ur, uc = dr / length, dc / length          # along the route
    pr, pc = -uc, ur                           # across the route
    mr, mc = (br + gr) / 2.0, (bc + gc) / 2.0
    span = max(r1 - r0, c1 - c0) + 1
    gap_centre = ridge_gap_offset if rng.random() < 0.5 else -ridge_gap_offset
    for t in range(-span, span + 1):
        for w in (0.0, 0.5):                   # two samples per step: a band with no diagonal holes
            cell = (round(mr + pr * t + ur * w), round(mc + pc * t + uc * w))
            if cell not in area or cell in keep:
                continue
            if abs(t - gap_centre) <= 1:
                if cell not in result.gap:
                    result.gap.append(cell)
                continue
            if cell not in result.blocked:
                result.blocked.add(cell)
                result.ridge.append(cell)
    if not passage_exists(base, goal, area - result.blocked):
        # The gap fell outside the window or on a protected cell: open the ridge at its middle.
        for cell in sorted(result.ridge, key=lambda x: math.hypot(x[0] - mr, x[1] - mc))[:3]:
            result.blocked.discard(cell)
            result.ridge.remove(cell)
            result.gap.append(cell)

    # Seeded rock clusters; drop any that would close the last passage.
    candidates = sorted(area - keep - result.blocked - set(result.gap))
    for _ in range(rock_clusters):
        if not candidates:
            break
        cr, cc = rng.choice(candidates)
        radius = rng.randint(*rock_radius)
        blob = [(r, c) for r in range(cr - radius, cr + radius + 1)
                for c in range(cc - radius, cc + radius + 1)
                if (r, c) in area and (r, c) not in keep and (r, c) not in result.gap
                and math.hypot(r - cr, c - cc) <= radius + 0.25]
        trial = result.blocked | set(blob)
        if blob and passage_exists(base, goal, area - trial):
            result.blocked = trial
            result.rocks.append(blob)
        else:
            result.dropped += 1
    return result


def flat_indices(cells, cols):
    """Row-major flat indices of (row, col) cells, as TerrainObservation.cell_indices uses."""
    return sorted(r * cols + c for r, c in cells)
