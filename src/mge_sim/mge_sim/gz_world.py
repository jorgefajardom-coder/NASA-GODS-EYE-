"""Gazebo Harmonic world of a run: public Jezero terrain, SIMULATED scene rocks and agents.

No ROS imports. `build_world(out_dir, ...)` writes one self-contained directory:

  heightmap.png  16-bit, 129 x 129 vertices ALIGNED WITH THE PLANNER'S CELL CENTRES: every
                 fourth vertex sits exactly on a cell centre with that cell's public prior
                 height (the planner's belief height), the vertices between are linear in
                 between. The Gazebo ground therefore matches the planner's terrain model, so
                 a physical agent's height agrees with what the planner expects. The lattice
                 starts at the first cell centre (half a cell inside the grid's south-west
                 edge) and its last row/column repeats the edge cells. It is the only
                 collision surface of the ground; NoData cells take the lowest finite height.
  albedo.png     terrain colour: the real MRO CTX orthoimage DN of the crop (panchromatic),
                 cubic-resampled, tinted with a Mars regolith palette and multiplied by a
                 fine procedural grain. The tint and grain are COSMETIC.
  normal.png     a procedural regolith normal map (COSMETIC: shading only, no geometry).
  rock_<k>.obj   five irregular boulder meshes (procedural, seeded).
  world.sdf      terrain + one boulder (mesh visual, ellipsoid collision) on every blocked
                 cell of the SIMULATED scene, smaller visual-only rocks around it, Mars
                 gravity, a low sun, a dusty sky, and one visual-only model per agent.
  world.json     frame and z_ref_m (gz z = ROS z - z_ref_m) for gz_mirror, and ground_z_m:
                 the Gazebo ground height at every cell centre (rows from origin_y upwards),
                 so the mirror can tell an airborne drone without loading the heightmap.

Boulders follow the viewer's display choice (main rock from 1.5 m, deliberately enlarged
for readability; Golombek-Rapp tail above it). Nothing here is a NASA product, a measured
rock or a validated mission.
"""
import json
import math
from pathlib import Path
import shutil
import struct
import warnings
import zlib

import numpy as np

# The drone's rotor animation lives in mge_sim.rotors (pure Python, imported by gz_mirror);
# re-exported here for existing callers.
from mge_sim.rotors import ROTOR_RAD_S, ROTOR_SPINDOWN_PER_S, ROTOR_SPINUP_PER_S, rotor_command  # noqa: F401

HEIGHTMAP_SIZE = 129             # 2^7 + 1 vertices per side
TEXTURE_PX = 1024
HAZARD_ROCK_M = 1.5
ROCK_DECAY_PER_M = 1.79 + 0.152 / 0.05   # Golombek & Rapp (1997), k = 0.05 (illustrative)
ROCK_VARIANTS = 5
MARS_GRAVITY = 3.721
REGOLITH_DARK = np.array([0.36, 0.22, 0.15])
REGOLITH_LIGHT = np.array([0.86, 0.62, 0.44])
AGENT_MODELS = {   # kind -> (model, rgba, geometry, lift above ground in m)
    'ROVER': ('rover', '0.62 0.62 0.66 1', '<box><size>3.0 2.7 2.2</size></box>', 1.1),
    'HUMAN': ('astronaut', '0.95 0.95 0.95 1', '<capsule><radius>0.3</radius><length>1.3</length></capsule>', 0.95),
    'DRONE': ('drone', '0.25 0.6 0.9 1', '<box><size>1.2 1.2 0.25</size></box>', 0.125),
}


def _png(width, height, rows_bytes, depth, color_type):
    raw = b''.join(b'\x00' + r for r in rows_bytes)

    def chunk(kind, data):
        return struct.pack('>I', len(data)) + kind + data + struct.pack('>I', zlib.crc32(kind + data) & 0xffffffff)
    return (b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', width, height, depth, color_type, 0, 0, 0))
            + chunk(b'IDAT', zlib.compress(raw, 9)) + chunk(b'IEND', b''))


def png_gray16(a):
    """a: 2-D uint16 array, row 0 = top (north)."""
    a = np.ascontiguousarray(a, dtype='>u2')
    return _png(a.shape[1], a.shape[0], [r.tobytes() for r in a], 16, 0)


def png_rgb8(a):
    """a: H x W x 3 float array in [0, 1], row 0 = top (north)."""
    a = np.ascontiguousarray(np.clip(np.round(a * 255), 0, 255).astype(np.uint8))
    return _png(a.shape[1], a.shape[0], [r.tobytes() for r in a], 8, 2)


def centre_lattice(grid, n, order=1):
    """Sample a cell-centre grid (row 0 = south) on an n x n lattice from the first cell centre
    to one cell beyond the last (index units 0 .. cols), returned with row 0 = north. With
    (n - 1) a multiple of cols, lattice points land exactly on cell centres (order=1: linear in
    between, no overshoot). Points beyond the last centre repeat the edge cells."""
    rows, cols = grid.shape
    t = np.linspace(0.0, 1.0, n)
    return resample(grid, (1.0 - t) * rows, t * cols, order=order)     # north first


def _axis_weights(coords, size, order, wrap):
    """(len(coords) x size) interpolation weights along one axis at fractional indices `coords`:
    order 1 = linear, order 3 = cubic convolution (Catmull-Rom). Out-of-range taps clamp to the
    edge ('nearest') or wrap around (wrap=True)."""
    c = np.asarray(coords, dtype=float)
    if not wrap:
        c = np.clip(c, 0.0, size - 1.0)
    i0 = np.floor(c).astype(np.int64)
    u = c - i0
    if order == 1:
        taps, w = (0, 1), (1.0 - u, u)
    elif order == 3:
        u2, u3 = u * u, u * u * u
        taps = (-1, 0, 1, 2)
        w = (-0.5 * u3 + u2 - 0.5 * u, 1.5 * u3 - 2.5 * u2 + 1.0, -1.5 * u3 + 2.0 * u2 + 0.5 * u, 0.5 * u3 - 0.5 * u2)
    else:
        raise ValueError('order must be 1 or 3')
    out = np.zeros((len(c), size))
    rows = np.arange(len(c))
    for d, wk in zip(taps, w):
        j = np.mod(i0 + d, size) if wrap else np.clip(i0 + d, 0, size - 1)
        np.add.at(out, (rows, j), wk)
    return out


def resample(a, ys, xs, order=1, wrap=False):
    """2-D array `a` sampled on the grid of fractional row indices `ys` x column indices `xs`
    (separable linear or cubic interpolation, pure numpy). Integer indices return the exact
    samples; order=1 never overshoots."""
    a = np.asarray(a, dtype=float)
    return _axis_weights(ys, a.shape[0], order, wrap) @ a @ _axis_weights(xs, a.shape[1], order, wrap).T


def fractal_noise(n, seed, octaves=6, base=8):
    """Seeded fractal value noise in [0, 1], n x n (cosmetic detail)."""
    rng = np.random.default_rng(seed)
    total, amp, norm = np.zeros((n, n)), 1.0, 0.0
    for o in range(octaves):
        cells = base * 2 ** o
        coarse = rng.random((cells + 1, cells + 1))
        at = np.linspace(0.0, cells, n)            # the coarse lattice stretched over n samples
        total += amp * resample(coarse, at, at, order=3, wrap=True)
        norm += amp
        amp *= 0.55
    total /= norm
    return (total - total.min()) / max(1e-9, total.max() - total.min())


def terrain_heights(heights):
    """Fill NoData with the lowest finite height; returns (filled grid, z_ref, span) inputs."""
    a = np.array(heights, dtype=float)
    finite = np.isfinite(a)
    if not finite.any():
        raise ValueError('the terrain has no finite height')
    a[~finite] = a[finite].min()
    return a


def albedo_texture(ctx_dn, n=TEXTURE_PX, seed=11):
    """CTX DN (rows x cols, row 0 = south) -> tinted RGB texture with cosmetic grain."""
    dn = centre_lattice(np.asarray(ctx_dn, dtype=float), n, order=3)
    lo, hi = np.percentile(dn, 2), np.percentile(dn, 98)
    tone = np.clip((dn - lo) / max(1e-6, hi - lo), 0, 1) * 0.6 + 0.2
    grain = fractal_noise(n, seed)
    tone = np.clip(tone * (0.82 + 0.36 * grain), 0, 1)
    rgb = REGOLITH_DARK + (REGOLITH_LIGHT - REGOLITH_DARK) * tone[..., None]
    return rgb


def normal_texture(n=TEXTURE_PX, seed=23, strength=2.5):
    h = fractal_noise(n, seed, octaves=7, base=16)
    gy, gx = np.gradient(h)
    nx, ny, nz = -gx * strength * n / 64, gy * strength * n / 64, np.ones_like(h)
    norm = np.sqrt(nx ** 2 + ny ** 2 + nz ** 2)
    return np.stack([nx / norm, ny / norm, nz / norm], axis=-1) * 0.5 + 0.5


def boulder_obj(seed, subdivisions=2):
    """Irregular boulder: displaced icosphere (radius ~1), flat underside. OBJ text."""
    t = (1 + 5 ** 0.5) / 2
    verts = [(-1, t, 0), (1, t, 0), (-1, -t, 0), (1, -t, 0), (0, -1, t), (0, 1, t), (0, -1, -t), (0, 1, -t),
             (t, 0, -1), (t, 0, 1), (-t, 0, -1), (-t, 0, 1)]
    verts = [tuple(c / math.sqrt(sum(x * x for x in v)) for c in v) for v in verts]
    faces = [(0, 11, 5), (0, 5, 1), (0, 1, 7), (0, 7, 10), (0, 10, 11), (1, 5, 9), (5, 11, 4), (11, 10, 2),
             (10, 7, 6), (7, 1, 8), (3, 9, 4), (3, 4, 2), (3, 2, 6), (3, 6, 8), (3, 8, 9), (4, 9, 5), (2, 4, 11),
             (6, 2, 10), (8, 6, 7), (9, 8, 1)]
    for _ in range(subdivisions):
        cache, new = {}, []

        def mid(a, b):
            key = (min(a, b), max(a, b))
            if key not in cache:
                m = [(verts[a][i] + verts[b][i]) / 2 for i in range(3)]
                length = math.sqrt(sum(x * x for x in m))
                verts.append(tuple(x / length for x in m))
                cache[key] = len(verts) - 1
            return cache[key]
        for a, b, c in faces:
            ab, bc, ca = mid(a, b), mid(b, c), mid(c, a)
            new += [(a, ab, ca), (b, bc, ab), (c, ca, bc), (ab, bc, ca)]
        faces = new
    rng = np.random.default_rng(seed)
    bumps = rng.normal(0, 1, (6, 3))
    out = []
    for x, y, z in verts:
        # A few broad lobes plus small facets: angular, not spherical.
        r = 1 + 0.18 * sum(math.sin(3.1 * (bx * x + by * y + bz * z) + k) for k, (bx, by, bz) in enumerate(bumps)) / 3
        r += 0.06 * math.sin(17 * x + 5 * seed) * math.cos(13 * y)
        px, py, pz = x * r, y * r * 0.8, z * r
        out.append((px, max(py, -0.35), pz))   # flat base (y up in OBJ)
    # Smooth vertex normals (area-weighted face normals), so the renderer can light the rock.
    pts = np.array(out)
    normals = np.zeros_like(pts)
    for a, b, c in faces:
        n = np.cross(pts[b] - pts[a], pts[c] - pts[a])
        normals[[a, b, c]] += n
    normals /= np.maximum(np.linalg.norm(normals, axis=1, keepdims=True), 1e-12)
    lines = ['# procedural boulder (display only)'] + [f'v {x:.4f} {y:.4f} {z:.4f}' for x, y, z in out]
    lines += [f'vn {x:.4f} {y:.4f} {z:.4f}' for x, y, z in normals]
    lines += [f'f {a + 1}//{a + 1} {b + 1}//{b + 1} {c + 1}//{c + 1}' for a, b, c in faces]
    return '\n'.join(lines) + '\n'


def _stream(seed):
    s = ((seed + 1) * 2654435761) & 0xffffffff
    while True:
        s ^= (s << 13) & 0xffffffff
        s ^= s >> 17
        s ^= (s << 5) & 0xffffffff
        yield s / 4294967296


def rock_layout(grid, blocked):
    """Per blocked cell: one hazard boulder (collision) and 4-8 small rocks (visual only).

    Returns dicts with name, x, y, radii (rx, ry, rz) in m, yaw, variant and collide.
    Every rock centre stays inside its cell (inside the terrain).
    """
    ox, oy, res, rows, cols = grid
    out = []
    for cell in sorted(blocked):
        r, c = divmod(cell, cols)
        if not (0 <= r < rows and 0 <= c < cols):
            continue
        rnd = _stream(cell)
        cx, cy = ox + (c + 0.5) * res, oy + (r + 0.5) * res
        count = 5 + int(next(rnd) * 5)
        for k in range(count):
            hazard = k == 0
            if hazard:
                d = min(res * 0.8, HAZARD_ROCK_M - math.log(1 - next(rnd) * 0.999) / ROCK_DECAY_PER_M)
            else:
                d = min(HAZARD_ROCK_M * 0.5, 0.1 - math.log(1 - next(rnd) * 0.999) / ROCK_DECAY_PER_M)
            room = max(0.0, res / 2 - d * 0.6)
            spread = 0.35 if hazard else 1.0
            out.append({
                'name': f'rock_{cell}_{k}', 'collide': hazard,
                'x': cx + (next(rnd) * 2 - 1) * room * spread, 'y': cy + (next(rnd) * 2 - 1) * room * spread,
                'radii': (d / 2 * (0.85 + 0.3 * next(rnd)), d / 2 * (0.75 + 0.3 * next(rnd)),
                          d / 2 * (0.45 + 0.35 * next(rnd))),
                'yaw': next(rnd) * math.tau, 'variant': int(next(rnd) * ROCK_VARIANTS),
                'shade': 0.8 + 0.35 * next(rnd)})
    return out


def _rock_sdf(rock, z):
    rx, ry, rz = rock['radii']
    s = rock['shade']
    # OBJ is y-up; Gazebo is z-up: rotate +90 deg about x, then scale (x, depth, height).
    visual = (f'<visual name="v"><pose>0 0 0 1.5708 0 0</pose><geometry><mesh><uri>rock_{rock["variant"]}.obj</uri>'
              f'<scale>{rx:.3f} {rz:.3f} {ry:.3f}</scale></mesh></geometry><material>'
              f'<ambient>{0.40 * s:.3f} {0.27 * s:.3f} {0.21 * s:.3f} 1</ambient>'
              f'<diffuse>{0.56 * s:.3f} {0.38 * s:.3f} {0.28 * s:.3f} 1</diffuse>'
              '<specular>0.05 0.04 0.03 1</specular></material></visual>')
    collision = (f'<collision name="c"><geometry><ellipsoid><radii>{rx:.3f} {ry:.3f} {rz:.3f}</radii>'
                 '</ellipsoid></geometry></collision>' if rock['collide'] else '')
    return (f'<model name="{rock["name"]}"><static>true</static>'
            f'<pose>{rock["x"]:.3f} {rock["y"]:.3f} {z + rz * 0.55:.3f} 0 0 {rock["yaw"]:.3f}</pose>'
            f'<link name="link">{collision}{visual}</link></model>')


def _agent_sdf(agent_id, kind, x, y, z, glb=None, rotors=None, walker=None):
    if glb is not None and rotors:      # the web's drone with its two rotors on spinning joints
        return drone_sdf(agent_id, x, y, z, glb, rotors)
    if walker is not None:              # an invisible mirrored leader and the walking actor
        return (f'<model name="{agent_id}"><pose>{x:.3f} {y:.3f} {z:.3f} 0 0 0</pose><link name="link">'
                '<gravity>false</gravity></link></model>' + walking_actor_sdf(agent_id, x, y, z, walker))
    if glb is not None:     # the web's model, resting on its origin (lift 0)
        return (f'<model name="{agent_id}"><pose>{x:.3f} {y:.3f} {z:.3f} 0 0 0</pose><link name="link">'
                f'<gravity>false</gravity>{web_model_visual("v", glb[0], kind, glb[1], glb[2])}</link></model>')
    _, color, geom, lift = AGENT_MODELS[kind]
    # Visual only, no gravity, no collision: its pose comes from ROS through gz_mirror.
    return (f'<model name="{agent_id}"><pose>{x:.3f} {y:.3f} {z + lift:.3f} 0 0 0</pose>'
            f'<link name="link"><gravity>false</gravity><visual name="v"><geometry>{geom}</geometry>'
            f'<material><ambient>{color}</ambient><diffuse>{color}</diffuse></material></visual></link></model>')


# The web viewer's GLB models, drawn at the same true sizes (web/src/components/AgentLayer.tsx,
# AstronautModel.tsx, BaseModel.tsx): the fit rule and target size per kind.
WEB_MODEL_FIT = {'ROVER': ('length', 3.6), 'DRONE': ('length', 1.2), 'HUMAN': ('height', 1.9), 'BASE': ('scale', 1.0)}
BASE_CLUSTER_OFFSET = (34.0, -22.0)   # the web's CLUSTER_OFFSET of the habitat from the base point


def glb_bbox(path):
    """Axis-aligned bounds (min, max) of a GLB's scene in its own Y-up frame, from accessor bounds."""
    data = Path(path).read_bytes()
    length = struct.unpack('<I', data[12:16])[0]
    g = json.loads(data[20:20 + length])

    def local(node):
        if 'matrix' in node:
            return np.array(node['matrix'], dtype=float).reshape(4, 4).T
        x, y, z, w = node.get('rotation', [0, 0, 0, 1])
        m = np.eye(4)
        rot = np.array([[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
                        [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
                        [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]])
        m[:3, :3] = rot * np.array(node.get('scale', [1, 1, 1]))
        m[:3, 3] = node.get('translation', [0, 0, 0])
        return m
    lo, hi = np.full(3, np.inf), np.full(3, -np.inf)

    def walk(i, parent):
        node = g['nodes'][i]
        m = parent @ local(node)
        if 'mesh' in node:
            for prim in g['meshes'][node['mesh']]['primitives']:
                acc = g['accessors'][prim['attributes']['POSITION']]
                for corner in np.array(np.meshgrid(*zip(acc['min'], acc['max']))).T.reshape(-1, 3):
                    q = (m @ np.append(corner, 1.0))[:3]
                    lo[:], hi[:] = np.minimum(lo, q), np.maximum(hi, q)
        for child in node.get('children', []):
            walk(child, m)
    for i in g['scenes'][g.get('scene', 0)]['nodes']:
        walk(i, np.eye(4))
    return lo, hi


# ---------------------------------------------------------------------------------------------
# Derived parts of the web GLBs (COSMETIC, derived at world-build time from the same files; the
# source GLBs are never modified). Gazebo turns a whole mesh visual with its link, so the parts
# that move in the web viewer (the rover's six wheels, the drone's two rotors) are written as
# separate small GLBs with the same vertices, normals, UVs and materials, and the rest of the
# model as a body GLB. Pure numpy; no glTF library is needed.

_COMPONENTS = {5120: np.int8, 5121: np.uint8, 5122: np.int16, 5123: np.uint16, 5125: np.uint32, 5126: np.float32}
_WIDTH = {'SCALAR': 1, 'VEC2': 2, 'VEC3': 3, 'VEC4': 4, 'MAT2': 4, 'MAT3': 9, 'MAT4': 16}
ROVER_WHEELS_NODE = 'Wheels_objs'                       # VehicleModel.tsx WHEELS = /^Wheels_objs/
DRONE_ROTOR_NODES = (('rotors_01', 1), ('rotors_02', -1))  # VehicleModel.tsx ROTORS (coaxial, counter-rotating)


def read_glb(path):
    """(glTF JSON, BIN chunk bytes) of a binary glTF."""
    data = Path(path).read_bytes()
    if data[:4] != b'glTF':
        raise ValueError(f'{path} is not a binary glTF')
    n = struct.unpack('<I', data[12:16])[0]
    g = json.loads(data[20:20 + n])
    rest = data[20 + n:]
    bin_ = rest[8:8 + struct.unpack('<I', rest[:4])[0]] if len(rest) >= 8 and rest[4:8] == b'BIN\x00' else b''
    return g, bin_


def _view_bytes(g, bin_, view_index, offset, item, count, what):
    """`count` tightly packed items of `item` bytes from a bufferView (byteStride removed)."""
    view = g['bufferViews'][view_index]
    start = view.get('byteOffset', 0) + offset
    stride = view.get('byteStride') or item
    end = start + stride * (count - 1) + item if count else start
    if view.get('buffer', 0) != 0 or end > len(bin_) or end - view.get('byteOffset', 0) > view['byteLength']:
        raise ValueError(f'{what} reads outside its bufferView or the GLB BIN chunk')
    if stride == item:
        return bin_[start:start + item * count]
    return b''.join(bin_[start + k * stride:start + k * stride + item] for k in range(count))


def _accessor_bytes(g, bin_, i):
    """Tightly packed raw bytes of accessor i (byteStride removed), sparse substitutions applied.

    glTF 2.0: an accessor without a bufferView starts as zeros; a sparse accessor starts from
    that base (its bufferView, or zeros) and then replaces the elements at `sparse.indices`
    with `sparse.values` (both tightly packed, in their own bufferViews)."""
    acc = g['accessors'][i]
    if acc.get('componentType') not in _COMPONENTS or acc.get('type') not in _WIDTH:
        raise ValueError(f'accessor {i} has an unsupported componentType or type')
    item = np.dtype(_COMPONENTS[acc['componentType']]).itemsize * _WIDTH[acc['type']]
    count = acc['count']
    if 'bufferView' in acc:
        base = _view_bytes(g, bin_, acc['bufferView'], acc.get('byteOffset', 0), item, count, f'accessor {i}')
    else:
        base = bytes(item * count)
    sparse = acc.get('sparse')
    if not sparse or not sparse.get('count'):
        return base
    n, ind, val = sparse['count'], sparse['indices'], sparse['values']
    if ind.get('componentType') not in (5121, 5123, 5125):
        raise ValueError(f'accessor {i} has an unsupported sparse index componentType')
    ind_type = np.dtype(_COMPONENTS[ind['componentType']])
    idx = np.frombuffer(_view_bytes(g, bin_, ind['bufferView'], ind.get('byteOffset', 0), ind_type.itemsize, n,
                                    f'accessor {i} sparse indices'), dtype=ind_type).astype(np.int64)
    if idx.size and idx.max() >= count:
        raise ValueError(f'accessor {i} has a sparse index beyond its count')
    values = np.frombuffer(_view_bytes(g, bin_, val['bufferView'], val.get('byteOffset', 0), item, n,
                                       f'accessor {i} sparse values'), dtype=np.uint8).reshape(n, item)
    out = np.frombuffer(base, dtype=np.uint8).reshape(count, item).copy()
    out[idx] = values
    return out.tobytes()


def accessor_array(g, bin_, i):
    acc = g['accessors'][i]
    a = np.frombuffer(_accessor_bytes(g, bin_, i), dtype=_COMPONENTS[acc['componentType']])
    return a.reshape(acc['count'], _WIDTH[acc['type']]) if _WIDTH[acc['type']] > 1 else a


def _local_matrix(node):
    if 'matrix' in node:
        return np.array(node['matrix'], dtype=float).reshape(4, 4).T
    x, y, z, w = node.get('rotation', [0, 0, 0, 1])
    m = np.eye(4)
    m[:3, :3] = np.array([[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
                          [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
                          [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]]) * np.array(node.get('scale', [1, 1, 1]))
    m[:3, 3] = node.get('translation', [0, 0, 0])
    return m


def node_world_matrices(g):
    """{node index: 4x4 scene matrix} for the default scene."""
    out = {}

    def walk(i, parent):
        out[i] = parent @ _local_matrix(g['nodes'][i])
        for c in g['nodes'][i].get('children', []):
            walk(c, out[i])
    for i in g['scenes'][g.get('scene', 0)]['nodes']:
        walk(i, np.eye(4))
    return out


def _node_by_prefix(g, prefix):
    return next((i for i, n in enumerate(g['nodes']) if n.get('name', '').startswith(prefix)), None)


def _subtree(g, i):
    out = [i]
    for c in g['nodes'][i].get('children', []):
        out += _subtree(g, c)
    return out


def _prim_indices(g, bin_, prim):
    if 'indices' in prim:
        return accessor_array(g, bin_, prim['indices']).astype(np.uint32)
    return np.arange(g['accessors'][prim['attributes']['POSITION']]['count'], dtype=np.uint32)


def split_wheel_triangles(parts, iterations=12):
    """The web viewer's wheel split (VehicleModel.tsx splitWheels), in the mesh's own frame
    (x lateral, z forward): triangle centroids are grouped by side (sign of x) and by the
    nearest of three axle positions along z (1-D k-means from min, middle, max over every part),
    so a tyre, its rim and its hub share a wheel. parts = [(positions N x 3, indices 3T)].
    Returns (per part: six index arrays, wheel centres 6 x 3, wheel radii 6). Wheels 0-2 are
    the -x side, 3-5 the +x side, each ordered by axle position along z (low to high)."""
    cents = []
    for pos, idx in parts:
        tri = np.asarray(pos, dtype=float)[np.asarray(idx).reshape(-1, 3)]
        cents.append(tri.mean(axis=1))
    allz = np.concatenate([c[:, 2] for c in cents])
    centres = np.array([allz.min(), (allz.min() + allz.max()) / 2, allz.max()])
    for _ in range(iterations):
        near = np.argmin(np.abs(allz[:, None] - centres[None, :]), axis=1)
        centres = np.array([allz[near == k].mean() if (near == k).any() else centres[k] for k in range(3)])
    out, lo, hi = [], np.full((6, 3), np.inf), np.full((6, 3), -np.inf)
    for (pos, idx), c in zip(parts, cents):
        wheel = np.where(c[:, 0] < 0, 0, 3) + np.argmin(np.abs(c[:, 2][:, None] - centres[None, :]), axis=1)
        tris = np.asarray(idx).reshape(-1, 3)
        groups = []
        for w in range(6):
            ids = tris[wheel == w].reshape(-1)
            groups.append(ids)
            if ids.size:
                p = np.asarray(pos, dtype=float)[ids]
                lo[w], hi[w] = np.minimum(lo[w], p.min(axis=0)), np.maximum(hi[w], p.max(axis=0))
        out.append(groups)
    if not np.isfinite(lo).all():
        raise ValueError('the wheel meshes do not look like 2 x 3 wheels')
    return out, (lo + hi) / 2, (hi[:, 1] - lo[:, 1]) / 2


def write_glb(path, g, bin_, nodes):
    """A compact GLB of selected primitives of a source glTF (g, bin_), each output node with its
    own 4x4 matrix: nodes = [(matrix, [(primitive dict, index array or None)])]. Vertex
    attributes, materials, textures and images are copied unchanged; new index lists are
    written as uint32. No animation, skin or morph target is copied."""
    out = {'asset': {'version': '2.0', 'generator': 'mge_sim.gz_world (derived part of a web model)'},
           'scene': 0, 'scenes': [{'nodes': list(range(len(nodes)))}], 'nodes': [], 'meshes': [],
           'accessors': [], 'bufferViews': [], 'buffers': []}
    blob = bytearray()
    acc_map, mat_map, tex_map, img_map, smp_map = {}, {}, {}, {}, {}

    def view(data, target=None):
        blob.extend(b'\x00' * (-len(blob) % 4))
        v = {'buffer': 0, 'byteOffset': len(blob), 'byteLength': len(data)}
        if target:
            v['target'] = target
        blob.extend(data)
        out['bufferViews'].append(v)
        return len(out['bufferViews']) - 1

    def accessor(i, target=34962):
        if i not in acc_map:
            src = g['accessors'][i]
            a = {k: src[k] for k in ('componentType', 'count', 'type', 'normalized', 'min', 'max') if k in src}
            a['bufferView'] = view(_accessor_bytes(g, bin_, i), target)
            out['accessors'].append(a)
            acc_map[i] = len(out['accessors']) - 1
        return acc_map[i]

    def remap(table, key, i, copy):
        if i not in table:
            out.setdefault(key, []).append(None)
            table[i] = len(out[key]) - 1
            out[key][table[i]] = copy(i)
        return table[i]

    def image(i):
        src = dict(g['images'][i])
        if 'bufferView' in src:
            v = g['bufferViews'][src['bufferView']]
            src['bufferView'] = view(bin_[v.get('byteOffset', 0):v.get('byteOffset', 0) + v['byteLength']])
        return src

    def texture(i):
        src = dict(g['textures'][i])
        if 'source' in src:
            src['source'] = remap(img_map, 'images', src['source'], image)
        if 'sampler' in src:
            src['sampler'] = remap(smp_map, 'samplers', src['sampler'], lambda k: dict(g['samplers'][k]))
        return src

    def retex(obj):
        if isinstance(obj, dict):
            return {k: (remap(tex_map, 'textures', v, texture) if k == 'index' and isinstance(v, int) else retex(v))
                    for k, v in obj.items()}
        return [retex(v) for v in obj] if isinstance(obj, list) else obj

    def subset(i, used):
        """Accessor i restricted to the vertices `used` (POSITION bounds recomputed)."""
        src = g['accessors'][i]
        a = accessor_array(g, bin_, i)[used]
        new = {k: src[k] for k in ('componentType', 'type', 'normalized') if k in src}
        new['count'] = int(len(used))
        if 'min' in src:
            flat = a.reshape(len(used), -1)
            new['min'], new['max'] = flat.min(axis=0).tolist(), flat.max(axis=0).tolist()
        new['bufferView'] = view(np.ascontiguousarray(a).tobytes(), 34962)
        out['accessors'].append(new)
        return len(out['accessors']) - 1

    keep = ('POSITION', 'NORMAL', 'TEXCOORD_', 'COLOR_', 'TANGENT')
    for matrix, prims in nodes:
        mesh = {'primitives': []}
        for prim, indices in prims:
            attrs = {k: v for k, v in prim['attributes'].items() if k.startswith(keep)}
            if indices is not None:     # only the vertices this part uses, re-indexed
                used, ids = np.unique(np.asarray(indices, dtype=np.int64), return_inverse=True)
                p = {'attributes': {k: subset(v, used) for k, v in attrs.items()}}
                ids = np.ascontiguousarray(ids, dtype='<u4')
                out['accessors'].append({'componentType': 5125, 'count': int(ids.size), 'type': 'SCALAR',
                                         'bufferView': view(ids.tobytes(), 34963)})
                p['indices'] = len(out['accessors']) - 1
            else:
                p = {'attributes': {k: accessor(v) for k, v in attrs.items()}}
                if 'indices' in prim:
                    p['indices'] = accessor(prim['indices'], 34963)
            if 'material' in prim:
                p['material'] = remap(mat_map, 'materials', prim['material'], lambda k: retex(g['materials'][k]))
            if 'mode' in prim:
                p['mode'] = prim['mode']
            mesh['primitives'].append(p)
        out['meshes'].append(mesh)
        out['nodes'].append({'mesh': len(out['meshes']) - 1,
                             'matrix': [float(v) for v in np.asarray(matrix, dtype=float).T.reshape(-1)]})
    for key in ('extensionsUsed',):
        if key in g:
            out[key] = list(g[key])
    blob.extend(b'\x00' * (-len(blob) % 4))
    out['buffers'].append({'byteLength': len(blob)})
    text = json.dumps(out, separators=(',', ':')).encode()
    text += b' ' * (-len(text) % 4)
    Path(path).write_bytes(struct.pack('<4sII', b'glTF', 2, 12 + 8 + len(text) + 8 + len(blob))
                           + struct.pack('<I4s', len(text), b'JSON') + text
                           + struct.pack('<I4s', len(blob), b'BIN\x00') + bytes(blob))


def _mesh_nodes(g, wm, skip=()):
    return [(wm[i], [(p, None) for p in g['meshes'][g['nodes'][i]['mesh']]['primitives']])
            for i in sorted(wm) if 'mesh' in g['nodes'][i] and i not in skip]


def derive_rover_parts(src, out_dir, stem='rover'):
    """Split the web rover GLB like the web viewer: <stem>_body.glb (everything but the wheels,
    in scene coordinates) and <stem>_wheel_<k>.glb (one wheel each, centred on its axle).
    Returns {'body': file, 'wheels': [(file, axle centre in scene coordinates)] ordered like
    split_wheel_triangles, 'radii', 'width' (scene units) and 'box' (scene bounds of the wheel
    set)}, or None when the model has no 2 x 3 wheel set."""
    g, bin_ = read_glb(src)
    w = _node_by_prefix(g, ROVER_WHEELS_NODE)
    if w is None or 'mesh' not in g['nodes'][w]:
        return None
    wm = node_world_matrices(g)
    prims = g['meshes'][g['nodes'][w]['mesh']]['primitives']
    parts = [(accessor_array(g, bin_, p['attributes']['POSITION']), _prim_indices(g, bin_, p)) for p in prims]
    try:
        groups, centres, radii = split_wheel_triangles(parts)
    except ValueError:
        return None
    out = Path(out_dir)
    write_glb(out / f'{stem}_body.glb', g, bin_, _mesh_nodes(g, wm, skip={w}))
    wheels = []
    for k in range(6):
        c = (wm[w] @ np.append(centres[k], 1.0))[:3]
        shift = np.eye(4)
        shift[:3, 3] = -c
        name = f'{stem}_wheel_{k}.glb'
        write_glb(out / name, g, bin_, [(shift @ wm[w], [(p, groups[j][k]) for j, p in enumerate(prims) if groups[j][k].size])])
        wheels.append((name, c))
    scale = float(np.linalg.norm(wm[w][:3, 1]))
    used = np.concatenate([np.asarray(pos, dtype=float)[np.asarray(idx)] for pos, idx in parts])
    scene = (wm[w] @ np.c_[used, np.ones(len(used))].T).T[:, :3]
    widths = []
    for k in range(6):      # lateral (mesh x) extent of each wheel
        ids = np.concatenate([groups[j][k] for j in range(len(parts))])
        xs = np.concatenate([np.asarray(parts[j][0], dtype=float)[groups[j][k], 0] for j in range(len(parts))]) if ids.size else [0]
        widths.append(float(np.ptp(xs)))
    return {'body': f'{stem}_body.glb', 'wheels': wheels, 'radii': radii * scale,
            'width': max(float(np.mean(widths)), float(np.mean(radii)) / 2) * scale, 'box': (scene.min(axis=0), scene.max(axis=0))}


def derive_drone_parts(src, out_dir, stem='drone'):
    """<stem>_body.glb (everything but the rotors) and <stem>_rotor_<k>.glb (one rotor, its hub
    at the origin). Returns {'body': file, 'rotors': [(file, hub in scene coordinates, spin
    direction)]} like derive_rover_parts, or None."""
    g, bin_ = read_glb(src)
    found = [(_node_by_prefix(g, name), d) for name, d in DRONE_ROTOR_NODES]
    if any(i is None for i, _ in found):
        return None
    wm = node_world_matrices(g)
    rotor_nodes = {j for i, _ in found for j in _subtree(g, i)}
    out = Path(out_dir)
    write_glb(out / f'{stem}_body.glb', g, bin_, _mesh_nodes(g, wm, skip=rotor_nodes))
    rotors = []
    for k, (i, d) in enumerate(found):
        hub = wm[i][:3, 3].copy()
        shift = np.eye(4)
        shift[:3, 3] = -hub
        name = f'{stem}_rotor_{k}.glb'
        write_glb(out / name, g, bin_, [(shift @ m, prims) for m, prims in _mesh_nodes(g, {j: wm[j] for j in _subtree(g, i)})])
        rotors.append((name, hub, d))
    return {'body': f'{stem}_body.glb', 'rotors': rotors}


# The astronaut as a Gazebo <actor> walking with the web's moon_walk clip (AstronautModel.tsx).
# gz-common's glTF loader (assimp) ignores the transforms of the nodes above the skeleton (the
# Sketchfab root rotation and 1/100 scale), so the derived file bakes the web size and the
# Y-up -> Z-up, face +x turn into the skeleton, the bind matrices, the clip and the vertices.
WALK_CLIP = 'moon_walk'
_PERM = [2, 0, 1]           # glTF (x, y, z) -> Gazebo (z, x, y): up y -> z, forward z -> x


def _sample(times, values, t):
    """LINEAR glTF sampler at time t (quaternions renormalised)."""
    i = int(np.clip(np.searchsorted(times, t) - 1, 0, len(times) - 2)) if len(times) > 1 else 0
    if len(times) == 1:
        return values[0]
    u = float(np.clip((t - times[i]) / max(times[i + 1] - times[i], 1e-9), 0, 1))
    a, b = values[i], values[i + 1]
    if len(a) == 4:
        b = b if np.dot(a, b) >= 0 else -b
        q = a + (b - a) * u
        return q / np.linalg.norm(q)
    return a + (b - a) * u


def clip_walk_speed(g, bin_, clip, samples=200):
    """The web's clipWalkSpeed (astronautPose.ts) in glTF scene units per second: median
    horizontal speed of the stance (lower) ankle relative to the hips over the clip."""
    names = {k: next((i for i, n in enumerate(g['nodes']) if n.get('name', '').startswith(k)), None)
             for k in ('Center', 'L_Ankle', 'R_Ankle')}
    if None in names.values():
        return 0.0
    chans = {}
    for c in clip['channels']:
        s = clip['samplers'][c['sampler']]
        chans[(c['target']['node'], c['target']['path'])] = (
            accessor_array(g, bin_, s['input']).astype(float), accessor_array(g, bin_, s['output']).astype(float))
    duration = max(float(t[-1]) for t, _ in chans.values())
    parent = {ch: i for i, n in enumerate(g['nodes']) for ch in n.get('children', [])}

    def world(i, t, memo):
        if i in memo:
            return memo[i]
        node = dict(g['nodes'][i])
        for path in ('translation', 'rotation', 'scale'):
            if (i, path) in chans:
                node[path] = list(_sample(*chans[(i, path)], t))
        m = _local_matrix(node)
        memo[i] = (world(parent[i], t, memo) @ m) if i in parent else m
        return memo[i]
    speeds, prev = [], None
    dt = duration / samples
    for k in range(samples + 1):
        memo = {}
        h, a, b = (world(names[n], min(k * dt, duration - 1e-6), memo)[:3, 3] for n in ('Center', 'L_Ankle', 'R_Ankle'))
        left = a[1] < b[1]
        foot = a if left else b
        cur = (left, foot[0] - h[0], foot[2] - h[2])
        if prev and prev[0] == left:
            speeds.append(math.hypot(cur[1] - prev[1], cur[2] - prev[2]) / dt)
        prev = cur
    return float(np.median(speeds)) if speeds else 0.0


def derive_walking_actor(src, out_dir, height_m=WEB_MODEL_FIT['HUMAN'][1], clip_name=WALK_CLIP,
                         name='astronaut_walk.glb'):
    """Write the skinned astronaut with only `clip_name`, at the web's height, Z-up and facing
    +x, for a Gazebo <actor>. Returns (file, clip ground speed in m/s) or None."""
    g, bin_ = read_glb(src)
    if not g.get('skins') or not any(a.get('name') == clip_name for a in g.get('animations', [])):
        return None
    sk = g['skins'][0]
    parent = {c: i for i, n in enumerate(g['nodes']) for c in n.get('children', [])}
    joints = set(sk['joints'])
    root = parent.get(sk['joints'][0])
    while root is not None and root in joints:
        root = parent.get(root)
    if root is None:
        return None
    lo, hi = glb_bbox(src)
    above = node_world_matrices(g)[root][:3, :3]
    f = height_m / (hi[1] - lo[1]) * float(np.cbrt(abs(np.linalg.det(above))))   # metres per skeleton unit
    clip = next(a for a in g['animations'] if a['name'] == clip_name)
    speed = clip_walk_speed(g, bin_, clip) * height_m / (hi[1] - lo[1])
    data = bytearray(bin_)
    P = np.eye(4)[[*_PERM, 3]]
    A, A_inv = np.diag([f, f, f, 1.0]) @ P, P.T @ np.diag([1 / f, 1 / f, 1 / f, 1.0])

    def rewrite(i, fn):
        acc = g['accessors'][i]
        if acc.get('componentType') != 5126:
            raise ValueError(f'accessor {i} is not float32; the walking actor cannot be rescaled in place')
        a = fn(accessor_array(g, bin_, i).astype(np.float32).copy()).astype(np.float32)
        if 'sparse' in acc or 'bufferView' not in acc:
            # No dense bytes to rewrite in place (and a sparse base view may be shared): store the
            # decoded, transformed values as a new bufferView and drop the sparse block.
            data.extend(b'\x00' * (-len(data) % 4))
            g['bufferViews'].append({'buffer': 0, 'byteOffset': len(data), 'byteLength': a.nbytes})
            data.extend(np.ascontiguousarray(a, dtype='<f4').tobytes())
            acc.pop('sparse', None)
            acc.pop('byteOffset', None)
            acc['bufferView'] = len(g['bufferViews']) - 1
        else:
            view = g['bufferViews'][acc['bufferView']]
            item = a[0].nbytes
            start = view.get('byteOffset', 0) + acc.get('byteOffset', 0)
            stride = view.get('byteStride') or item
            for k in range(len(a)):
                data[start + k * stride:start + k * stride + item] = a[k].tobytes()
        if 'min' in acc:
            flat = a.reshape(len(a), -1)
            acc['min'], acc['max'] = flat.min(axis=0).tolist(), flat.max(axis=0).tolist()

    def vec(scale):
        return lambda a: a[:, _PERM] * scale

    def quat(a):
        return a[:, [2, 0, 1, 3]]

    def tangent(a):
        a[:, :3] = a[:, _PERM]
        return a

    def ibm(a):
        m = a.reshape(-1, 4, 4).transpose(0, 2, 1)          # column-major -> row-major
        return (A @ m @ A_inv).transpose(0, 2, 1).reshape(-1, 16)
    done = set()
    for mesh in g['meshes']:
        for prim in mesh['primitives']:
            if 'targets' in prim:
                return None
            for key, fn in (('POSITION', vec(f)), ('NORMAL', vec(1.0)), ('TANGENT', tangent)):
                i = prim['attributes'].get(key)
                if i is not None and i not in done:
                    rewrite(i, fn)
                    done.add(i)
    rewrite(sk['inverseBindMatrices'], ibm)
    for c in clip['channels']:
        i = clip['samplers'][c['sampler']]['output']
        fn = {'translation': vec(f), 'rotation': quat, 'scale': vec(1.0)}.get(c['target']['path'])
        if fn is not None and i not in done:
            rewrite(i, fn)
            done.add(i)
    for i in [j for j in range(len(g['nodes'])) if j in joints or parent.get(j) == root]:
        node = g['nodes'][i]
        if 'matrix' in node:
            return None
        if 'translation' in node:
            node['translation'] = [float(v) * f for v in np.asarray(node['translation'])[_PERM]]
        if 'rotation' in node:
            x, y, z, w = node['rotation']
            node['rotation'] = [z, x, y, w]
        if 'scale' in node:
            node['scale'] = [float(v) for v in np.asarray(node['scale'])[_PERM]]
    g['nodes'][root] = {k: v for k, v in g['nodes'][root].items() if k not in ('translation', 'rotation', 'scale', 'matrix')}
    g['scenes'], g['scene'] = [{'nodes': [root]}], 0
    g['animations'] = [clip]
    g['asset'] = {**g.get('asset', {}), 'generator': 'mge_sim.gz_world (derived walking actor of the web astronaut)'}
    data.extend(b'\x00' * (-len(data) % 4))
    if g.get('buffers'):
        g['buffers'][0]['byteLength'] = len(data)
    text = json.dumps(g, separators=(',', ':')).encode()
    text += b' ' * (-len(text) % 4)
    Path(out_dir, name).write_bytes(struct.pack('<4sII', b'glTF', 2, 12 + 8 + len(text) + 8 + len(data))
                                    + struct.pack('<I4s', len(text), b'JSON') + text
                                    + struct.pack('<I4s', len(data), b'BIN\x00') + bytes(data))
    return name, speed


def walking_actor_sdf(agent_id, x, y, z, actor):
    """A Gazebo <actor> playing the web's walk clip, led by the agent's mirrored model through
    gz FollowActor (set_pose cannot move an actor): it walks toward the model at up to
    WALKER_SPEED_MPS (above the illustrative 0.9 m/s human speed, so it keeps up) while the
    model is more than 5 cm away, the walk cycle advancing with the distance walked divided by
    the clip's ground speed (so the stance foot does not slide, like the web), and freezes in
    its current frame when it arrives (no idle clip). FollowActor keeps the actor at its spawn
    height (no terrain following) and turns it only about the vertical."""
    name, speed = actor
    return (f'<actor name="{agent_id}_walker"><pose>{x:.3f} {y:.3f} {z:.3f} 0 0 0</pose>'
            f'<skin><filename>{name}</filename></skin>'
            f'<animation name="{WALK_CLIP}"><filename>{name}</filename><interpolate_x>false</interpolate_x></animation>'
            '<plugin filename="gz-sim-follow-actor-system" name="gz::sim::systems::FollowActor">'
            f'<target>{agent_id}</target><min_distance>0.05</min_distance><max_distance>100000</max_distance>'
            f'<velocity>{WALKER_SPEED_MPS}</velocity><animation>{WALK_CLIP}</animation>'
            f'<animation_x_vel>{1.0 / max(speed, 1e-3):.4f}</animation_x_vel></plugin></actor>')


WALKER_SPEED_MPS = 1.0


def web_scale(kind, lo, hi):
    """Metres per GLB unit of the web viewer's fit rule for `kind`."""
    rule, target = WEB_MODEL_FIT[kind]
    size = hi - lo
    if rule == 'length':
        return target / max(size[0], size[2])
    return target / size[1] if rule == 'height' else target


def to_gz(p, s, centre, lo):
    """A point of a Y-up GLB scene (x, y, z) in the model frame of its visual: roll +90 deg maps
    glTF (x, y, z) to Gazebo (x, -z, y); centred horizontally on `centre` (glTF x, z) and resting
    on z = 0 (the GLB's lowest point)."""
    return ((p[0] - centre[0]) * s, -(p[2] - centre[1]) * s, (p[1] - lo[1]) * s)


def web_model_visual(name, uri, kind, lo, hi, z_shift=0.0, centre=None):
    """A <visual> drawing a Y-up GLB upright (Z-up), sized like the web and resting on z = 0.
    It is centred horizontally on its bounds, or on `centre` (glTF x, z) when given."""
    s = web_scale(kind, lo, hi)
    cx, cz = centre if centre is not None else ((lo[0] + hi[0]) / 2, (lo[2] + hi[2]) / 2)
    # Roll +90 deg about x maps glTF (x, y, z) to Gazebo (x, -z, y): centre it, base on z = 0.
    return (f'<visual name="{name}"><pose>{-cx * s:.4f} {cz * s:.4f} {-lo[1] * s + z_shift:.4f} 1.5708 0 0</pose>'
            f'<geometry><mesh><uri>{uri}</uri><scale>{s:.5f} {s:.5f} {s:.5f}</scale></mesh></geometry></visual>')


def _mesh_visual(name, uri, s, rpy='1.5708 0 0', xyz='0 0 0'):
    return (f'<visual name="{name}"><pose>{xyz} {rpy}</pose><geometry><mesh><uri>{uri}</uri>'
            f'<scale>{s:.5f} {s:.5f} {s:.5f}</scale></mesh></geometry></visual>')


def drone_sdf(agent_id, x, y, z, glb, rotors):
    """The web's drone as a body link plus one link per rotor on a revolute joint about the
    vertical through its hub. rotors = {'body': body GLB, 'rotors': derive_drone_parts(...)}.
    A JointController (velocity mode) per rotor listens on
    /model/<id>/joint/<rotor>_joint/cmd_vel (gz_mirror commands it from the AgentState mode).
    Visual only: no collision, no gravity; the body is heavy so the light rotors cannot turn it."""
    uri, lo, hi = glb
    s = web_scale('DRONE', lo, hi)
    centre = ((lo[0] + hi[0]) / 2, (lo[2] + hi[2]) / 2)
    links = (f'<link name="link"><gravity>false</gravity>{_box_inertia(500, 1.2, 1.2, 0.6)}'
             + web_model_visual('v', rotors['body'], 'DRONE', lo, hi) + '</link>')
    joints, plugins = '', ''
    for k, (name, hub, _) in enumerate(rotors['rotors']):
        hx, hy, hz = to_gz(hub, s, centre, lo)
        link = f'rotor_{k}'
        links += (f'<link name="{link}"><pose>{hx:.4f} {hy:.4f} {hz:.4f} 0 0 0</pose><gravity>false</gravity>'
                  '<inertial><mass>0.05</mass><inertia><ixx>0.002</ixx><iyy>0.002</iyy><izz>0.004</izz>'
                  '<ixy>0</ixy><ixz>0</ixz><iyz>0</iyz></inertia></inertial>'
                  + _mesh_visual('v', name, s) + '</link>')
        joints += (f'<joint name="{link}_joint" type="revolute"><parent>link</parent><child>{link}</child>'
                   '<axis><xyz>0 0 1</xyz><limit><lower>-1e16</lower><upper>1e16</upper></limit></axis></joint>')
        plugins += ('<plugin filename="gz-sim-joint-controller-system" name="gz::sim::systems::JointController">'
                    f'<joint_name>{link}_joint</joint_name><topic>/model/{agent_id}/joint/{link}_joint/cmd_vel</topic>'
                    '<initial_velocity>0</initial_velocity></plugin>')
    plugins += ('<plugin filename="gz-sim-joint-state-publisher-system" name="gz::sim::systems::JointStatePublisher">'
                + ''.join(f'<joint_name>rotor_{k}_joint</joint_name>' for k in range(len(rotors['rotors']))) + '</plugin>')
    return (f'<model name="{agent_id}"><pose>{x:.3f} {y:.3f} {z:.3f} 0 0 0</pose>' + links + joints + plugins + '</model>')


# Physical rover (display proportions near Perseverance's: 3 m long, 2.7 m wide, 52.5 cm wheels;
# masses and friction are illustrative). Model origin = ground contact, so ROS z = gz z + z_ref.
WHEEL_R = 0.2625
WHEEL_W = 0.4
WHEEL_X = (1.1, 0.0, -1.1)
WHEEL_Y = 1.25
CHASSIS = (2.6, 2.0, 0.55)
CLEARANCE = 0.6


def _box_inertia(m, x, y, z):
    return (f'<inertial><mass>{m}</mass><inertia><ixx>{m * (y * y + z * z) / 12:.3f}</ixx>'
            f'<iyy>{m * (x * x + z * z) / 12:.3f}</iyy><izz>{m * (x * x + y * y) / 12:.3f}</izz>'
            '<ixy>0</ixy><ixz>0</ixz><iyz>0</iyz></inertia></inertial>')


def rover_wheel_layout(glb, parts):
    """Physical wheel layout from the web rover's split wheels (derive_rover_parts), at the
    web's size: [(link name, x, y, radius, width, wheel GLB)] in the model frame (origin under
    the wheel-set centre, on the ground), named wheel_<l|r><k> with k = 0 at the front like
    the stand-in layout; plus the wheel-set centre (glTF x, z) the body visual is centred on."""
    uri, lo, hi = glb
    s = web_scale('ROVER', lo, hi)
    wheels, radii, width, box = parts['wheels'], parts['radii'], parts['width'], parts['box']
    centre = ((box[0][0] + box[1][0]) / 2, (box[0][2] + box[1][2]) / 2)
    placed = [(to_gz(c, s, centre, lo), r * s, name) for (name, c), r in zip(wheels, radii)]
    out = []
    for side, sign in (('l', 1), ('r', -1)):
        row = sorted((p for p in placed if p[0][1] * sign > 0), key=lambda p: -p[0][0])
        out += [(f'wheel_{side}{k}', xyz, r, width * s, name) for k, (xyz, r, name) in enumerate(row)]
    return out, centre


def usable_wheel_layout(glb, parts):
    """rover_wheel_layout when it gives three wheels per side, else (None, None).

    The single rule both the SDF and world.json use, so the metadata never claims per-wheel
    visuals for a rover that is drawn as the whole model on its chassis."""
    if glb is None or not parts:
        return None, None
    layout, centre = rover_wheel_layout(glb, parts)
    if len(layout) != 6 or sum(w[0].startswith('wheel_l') for w in layout) != 3:
        return None, None
    return layout, centre


def physical_rover_sdf(agent_id, x, y, z, yaw=0.0, glb=None, parts=None):
    """A six-wheel rover driven by gz DiffDrive on /model/<id>/cmd_vel, with ground-truth
    odometry on /model/<id>/odometry_gt. It rests on the terrain under Mars gravity.

    With the web rover GLB split into parts (derive_rover_parts), the six physical wheels take
    the web model's wheel positions and radius and each wheel link draws its own wheel mesh,
    so the wheels visibly roll with the physics; the chassis draws the body without wheels."""
    cz = WHEEL_R + CLEARANCE + CHASSIS[2] / 2 - 0.35
    mat = '<material><ambient>0.6 0.6 0.62 1</ambient><diffuse>0.78 0.78 0.8 1</diffuse></material>'
    dark = '<material><ambient>0.15 0.15 0.16 1</ambient><diffuse>0.22 0.22 0.24 1</diffuse></material>'
    layout, centre = usable_wheel_layout(glb, parts)   # the web's rover split into body + six wheels
    if layout is not None:
        body = web_model_visual('web_model', parts['body'], 'ROVER', glb[1], glb[2], z_shift=-cz, centre=centre)
        s = web_scale('ROVER', glb[1], glb[2])
    elif glb is not None:   # the web's rover model; the chassis link sits cz above the ground
        body = web_model_visual('web_model', glb[0], 'ROVER', glb[1], glb[2], z_shift=-cz)
    else:                   # simple stand-in shapes
        body = (f'<visual name="body"><geometry><box><size>{CHASSIS[0]} {CHASSIS[1]} {CHASSIS[2]}</size></box></geometry>{mat}</visual>'
                f'<visual name="mast"><pose>0.9 0.6 1.0 0 0 0</pose><geometry><cylinder><radius>0.08</radius><length>1.5</length></cylinder></geometry>{mat}</visual>'
                f'<visual name="head"><pose>0.9 0.6 1.8 0 0 0</pose><geometry><box><size>0.3 0.5 0.25</size></box></geometry>{dark}</visual>'
                f'<visual name="rtg"><pose>-1.45 0 0.35 0 0.6 0</pose><geometry><cylinder><radius>0.3</radius><length>0.7</length></cylinder></geometry>{dark}</visual>')
    links = (f'<link name="chassis"><pose>0 0 {cz:.3f} 0 0 0</pose>{_box_inertia(900, *CHASSIS)}'
             f'<collision name="c"><geometry><box><size>{CHASSIS[0]} {CHASSIS[1]} {CHASSIS[2]}</size></box></geometry></collision>'
             + body + '</link>')
    if layout is None:
        layout = [(f'wheel_{side}{k}', (wx, sy, WHEEL_R), WHEEL_R, WHEEL_W, None)
                  for side, sy in (('l', WHEEL_Y), ('r', -WHEEL_Y)) for k, wx in enumerate(WHEEL_X)]
    joints, left, right = '', [], []
    for name, (wx, wy, _), r, width, mesh in layout:
        if mesh is not None:    # the web wheel, centred on its axle: link z (axle) = model +y
            visual = _mesh_visual('v', mesh, s, rpy='3.14159 0 0')
        elif glb is not None:   # the whole web model is on the chassis
            visual = ''
        else:
            visual = (f'<visual name="v"><geometry><cylinder><radius>{r}</radius><length>{width}</length>'
                      f'</cylinder></geometry>{dark}</visual>')
        links += (f'<link name="{name}"><pose>{wx:.4f} {wy:.4f} {r:.4f} -1.5708 0 0</pose>'
                  '<inertial><mass>25</mass><inertia><ixx>0.8</ixx><iyy>0.8</iyy><izz>0.9</izz>'
                  '<ixy>0</ixy><ixz>0</ixz><iyz>0</iyz></inertia></inertial>'
                  f'<collision name="c"><geometry><cylinder><radius>{r:.4f}</radius><length>{width:.4f}</length>'
                  '</cylinder></geometry>'
                  '<surface><friction><ode><mu>0.9</mu><mu2>0.9</mu2></ode></friction></surface></collision>'
                  + visual + '</link>')
        joints += (f'<joint name="{name}_joint" type="revolute"><parent>chassis</parent><child>{name}</child>'
                   '<axis><xyz>0 0 1</xyz><limit><lower>-1e16</lower><upper>1e16</upper></limit></axis></joint>')
        (left if name.startswith('wheel_l') else right).append(f'{name}_joint')
    separation = sum(abs(w[1][1]) for w in layout) / len(layout) * 2
    radius = sum(w[2] for w in layout) / len(layout)
    plugins = ('<plugin filename="gz-sim-diff-drive-system" name="gz::sim::systems::DiffDrive">'
               + ''.join(f'<left_joint>{j}</left_joint>' for j in left)
               + ''.join(f'<right_joint>{j}</right_joint>' for j in right)
               + f'<wheel_separation>{separation:.4f}</wheel_separation><wheel_radius>{radius:.4f}</wheel_radius>'
               f'<topic>/model/{agent_id}/cmd_vel</topic><max_linear_acceleration>0.5</max_linear_acceleration>'
               '<max_angular_acceleration>1.0</max_angular_acceleration></plugin>'
               '<plugin filename="gz-sim-odometry-publisher-system" name="gz::sim::systems::OdometryPublisher">'
               f'<odom_topic>/model/{agent_id}/odometry_gt</odom_topic><dimensions>3</dimensions>'
               '<odom_publish_frequency>20</odom_publish_frequency></plugin>'
               '<plugin filename="gz-sim-joint-state-publisher-system" name="gz::sim::systems::JointStatePublisher">'
               + ''.join(f'<joint_name>{j}</joint_name>' for j in left + right) + '</plugin>')
    return (f'<model name="{agent_id}"><pose>{x:.3f} {y:.3f} {z + 0.05:.3f} 0 0 {yaw:.3f}</pose>'
            + links + joints + plugins + '</model>')


def _base_sdf(models, base_xy, ground):
    """The web's habitat model at the base point plus the web's cluster offset (visual only)."""
    if base_xy is None or 'BASE' not in models:
        return ''
    bx, by = base_xy[0] + BASE_CLUSTER_OFFSET[0], base_xy[1] + BASE_CLUSTER_OFFSET[1]
    uri, lo, hi = models['BASE']
    return (f'<model name="base"><static>true</static><pose>{bx:.3f} {by:.3f} {ground(bx, by):.3f} 0 0 0</pose>'
            f'<link name="link">{web_model_visual("v", uri, "BASE", lo, hi)}</link></model>')


# glTF layouts the minimal reader does not support (Draco/meshopt compression, sparse or
# view-less accessors, missing min/max, truncated buffers) surface as these errors.
DERIVE_ERRORS = (ValueError, KeyError, IndexError, TypeError, struct.error)


def _derived_or_none(derive, *args):
    """Run a COSMETIC part derivation; on an unsupported model warn and return None, so the
    world is still built with the whole web model (the behaviour before part derivation)."""
    try:
        return derive(*args)
    except DERIVE_ERRORS as e:
        warnings.warn(f'{derive.__name__}({Path(args[0]).name}): {type(e).__name__}: {e}; '
                      'drawing the whole web model instead', RuntimeWarning, stacklevel=2)
        return None


def build_world(out_dir, grid, heights, blocked, agents, ctx_dn=None, world_name='jezero', physical=(),
                web_models=None, base_xy=None, walking_actor=False):
    """grid = (origin_x_m, origin_y_m, resolution_m, rows, cols); heights and ctx_dn are
    rows x cols arrays with row 0 = south (None/NaN = NoData); blocked = flat indices of the
    SIMULATED scene's obstacle cells; agents = [(agent_id, kind, x, y, z)] in ROS ENU;
    physical = agent IDs built as driven rovers (gz_rover_driver) instead of mirrored models;
    web_models = {'ROVER'|'DRONE'|'HUMAN'|'BASE': path to the web viewer's GLB} draws the same
    models at the same true sizes (copied into the world); base_xy = base point of the habitat.

    With the web models, the moving parts follow the web viewer (COSMETIC, derived GLB parts):
    a physical rover's six wheels are split from the rover GLB and drawn on its wheel links
    (they roll with the physics); a drone's two rotors are links on revolute joints spun by
    gz_mirror while the drone is not IDLE. walking_actor=True (opt-in) draws the astronaut as
    a Gazebo actor walking with the web's walk clip behind its mirrored (invisible) model; the
    actor keeps its spawn height, so on sloped ground it floats or sinks."""
    ox, oy, res, rows, cols = grid
    if rows != cols:
        raise ValueError('the heightmap needs a square grid')
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    h = terrain_heights(np.array(heights, dtype=float).reshape(rows, cols))
    verts = centre_lattice(h, HEIGHTMAP_SIZE)     # vertices on the planner's cell centres
    z_ref, span = float(verts.min()), max(float(verts.max() - verts.min()), 0.01)
    (out / 'heightmap.png').write_bytes(png_gray16(np.round((verts - z_ref) / span * 65535)))
    dn = np.full((rows, cols), 135.0) if ctx_dn is None else np.array(ctx_dn, dtype=float).reshape(rows, cols)
    (out / 'albedo.png').write_bytes(png_rgb8(albedo_texture(dn)))
    (out / 'normal.png').write_bytes(png_rgb8(normal_texture()))
    for k in range(ROCK_VARIANTS):
        (out / f'rock_{k}.obj').write_text(boulder_obj(k + 1), encoding='utf-8')
    models = {}
    for kind, src in (web_models or {}).items():
        if src and Path(src).exists():
            shutil.copyfile(src, out / Path(src).name)
            lo, hi = glb_bbox(src)
            models[kind] = (Path(src).name, lo, hi)
    # Moving parts like the web viewer's (derived at build time; the source GLBs are untouched).
    # Any unsupported model falls back to the whole web model instead of aborting the build.
    rover_parts = drone_parts = None
    if 'ROVER' in models and any(a in physical and k == 'ROVER' for a, k, *_ in agents):
        rover_parts = _derived_or_none(derive_rover_parts, out / models['ROVER'][0], out)
        if usable_wheel_layout(models['ROVER'], rover_parts)[0] is None:
            rover_parts = None      # the SDF would draw the whole model; claim no wheel parts
    if 'DRONE' in models and any(k == 'DRONE' and a not in physical for a, k, *_ in agents):
        drone_parts = _derived_or_none(derive_drone_parts, out / models['DRONE'][0], out)
    walker = None
    if walking_actor and 'HUMAN' in models and any(k == 'HUMAN' and a not in physical for a, k, *_ in agents):
        walker = _derived_or_none(derive_walking_actor, out / models['HUMAN'][0], out)
    width, height = cols * res, rows * res
    x0, y0 = ox + res / 2, oy + res / 2               # the lattice starts on the first cell centre

    def ground(x, y):
        j = (x - x0) / width * (HEIGHTMAP_SIZE - 1)
        i = (1 - (y - y0) / height) * (HEIGHTMAP_SIZE - 1)
        return float(resample(verts, [i], [j], order=1)[0, 0]) - z_ref

    terrain = (f'<heightmap><texture><diffuse>albedo.png</diffuse><normal>normal.png</normal>'
               f'<size>{width}</size></texture><uri>heightmap.png</uri>'
               f'<size>{width} {height} {span:.3f}</size><pos>{x0 + width / 2} {y0 + height / 2} 0</pos></heightmap>')
    rocks = rock_layout(grid, blocked)
    sdf = ('<?xml version="1.0"?><sdf version="1.10">'
           f'<world name="{world_name}"><gravity>0 0 -{MARS_GRAVITY}</gravity>'
           '<physics name="default" type="dart"><max_step_size>0.004</max_step_size><real_time_factor>1</real_time_factor></physics>'
           '<plugin filename="gz-sim-physics-system" name="gz::sim::systems::Physics"/>'
           '<plugin filename="gz-sim-user-commands-system" name="gz::sim::systems::UserCommands"/>'
           '<plugin filename="gz-sim-scene-broadcaster-system" name="gz::sim::systems::SceneBroadcaster"/>'
           '<scene><ambient>0.42 0.33 0.28 1</ambient><background>0.78 0.6 0.46 1</background>'
           '<grid>false</grid><shadows>true</shadows>'
           '<fog><type>linear</type><color>0.78 0.6 0.46 1</color><start>120</start><end>600</end></fog></scene>'
           '<light type="directional" name="sun"><cast_shadows>true</cast_shadows><pose>0 0 200 0 0 0</pose>'
           '<diffuse>1.0 0.92 0.82 1</diffuse><specular>0.2 0.18 0.15 1</specular>'
           '<direction>-0.62 0.35 -0.45</direction></light>'
           '<model name="terrain"><static>true</static><link name="link">'
           f'<collision name="c"><geometry>{terrain}</geometry></collision>'
           f'<visual name="v"><geometry>{terrain}</geometry></visual></link></model>'
           + ''.join(_rock_sdf(r, ground(r['x'], r['y'])) for r in rocks)
           + ''.join(physical_rover_sdf(a, x, y, ground(x, y), glb=models.get(k),
                                        parts=rover_parts if k == 'ROVER' else None) if a in physical
                     else _agent_sdf(a, k, x, y, (ground(x, y) if k in models else z - z_ref), glb=models.get(k),
                                     rotors=drone_parts if k == 'DRONE' else None,
                                     walker=walker if k == 'HUMAN' else None)
                     for a, k, x, y, z in agents)
           + _base_sdf(models, base_xy, ground)
           + '</world></sdf>')
    (out / 'world.sdf').write_text(sdf, encoding='utf-8')
    meta = {'world_name': world_name, 'origin_x_m': ox, 'origin_y_m': oy, 'resolution_m': res,
            'rows': rows, 'cols': cols, 'z_ref_m': z_ref, 'relief_m': span,
            'heightmap_origin_m': [x0, y0], 'heightmap_on_cell_centres': True,
            # Gazebo ground z at each cell centre (row i = origin_y upwards): lets gz_mirror tell
            # an airborne drone like the web viewer, without numpy or the heightmap.
            'ground_z_m': [[round(ground(x0 + j * res, y0 + i * res), 4) for j in range(cols)]
                           for i in range(rows)],
            'boulders': sum(r['collide'] for r in rocks), 'small_rocks': sum(not r['collide'] for r in rocks),
            'agents': {a: {'model': AGENT_MODELS[k][0],
                           'lift_m': 0.0 if a in physical or k in models else AGENT_MODELS[k][3],
                           'physical': a in physical, 'web_model': k in models} for a, k, *_ in agents},
            'web_models': {k: v[0] for k, v in models.items()},
            'attribution': ('astronaut.glb: "Animated Astronaut Character in Space Suit Loop" by LasquetiSpice, '
                            'CC BY 4.0; rover.glb, drone.glb: NASA models with agency branding removed; '
                            'see THIRD_PARTY_NOTICES.md') if models else None,
            'real_inputs': ['public prior heights (collision surface)', 'MRO CTX orthoimage DN (albedo)'],
            'cosmetic': ['regolith tint and grain', 'normal map', 'boulder shapes and sizes (enlarged)'],
            'note': 'SIMULATED scene on the public Jezero crop; not a NASA product or a validated mission.'}
    derived = []
    for a, k, *_ in agents:
        if k == 'ROVER' and a in physical and rover_parts:
            meta['agents'][a]['wheel_visuals'] = True       # each physical wheel draws its web wheel
        if k == 'DRONE' and a not in physical and drone_parts:
            meta['agents'][a]['rotors'] = [{'joint': f'rotor_{i}_joint', 'direction': d, 'max_rad_s': ROTOR_RAD_S,
                                            'topic': f'/model/{a}/joint/rotor_{i}_joint/cmd_vel'}
                                           for i, (_, _, d) in enumerate(drone_parts['rotors'])]
        if k == 'HUMAN' and a not in physical and walker:
            meta['agents'][a]['walker'] = {'actor': f'{a}_walker', 'clip': WALK_CLIP,
                                           'clip_speed_mps': round(walker[1], 4), 'max_speed_mps': WALKER_SPEED_MPS}
    if walker:
        derived.append(walker[0])
    if rover_parts:
        derived += [rover_parts['body']] + [n for n, _ in rover_parts['wheels']]
    if drone_parts:
        derived += [drone_parts['body']] + [n for n, _, _ in drone_parts['rotors']]
    if derived:
        meta['derived_models'] = derived
        meta['cosmetic'].append('derived GLB parts (body, wheels, rotors) split from the web models for animation')
    (out / 'world.json').write_text(json.dumps(meta, indent=1), encoding='utf-8')
    return meta
