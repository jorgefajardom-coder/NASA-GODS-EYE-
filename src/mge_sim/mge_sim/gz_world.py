"""Gazebo Harmonic world of a run: public Jezero terrain, SIMULATED scene rocks and agents.

No ROS imports. `build_world(out_dir, ...)` writes one self-contained directory:

  heightmap.png  16-bit, 129 x 129 vertices, bilinear resampling of the public prior's
                 cell centres. It is the only collision surface of the ground: no relief is
                 invented there. NoData cells take the lowest finite height.
  albedo.png     terrain colour: the real MRO CTX orthoimage DN of the crop (panchromatic),
                 cubic-resampled, tinted with a Mars regolith palette and multiplied by a
                 fine procedural grain. The tint and grain are COSMETIC.
  normal.png     a procedural regolith normal map (COSMETIC: shading only, no geometry).
  rock_<k>.obj   five irregular boulder meshes (procedural, seeded).
  world.sdf      terrain + one boulder (mesh visual, ellipsoid collision) on every blocked
                 cell of the SIMULATED scene, smaller visual-only rocks around it, Mars
                 gravity, a low sun, a dusty sky, and one visual-only model per agent.
  world.json     frame and z_ref_m (gz z = ROS z - z_ref_m) for gz_mirror.

Boulders follow the viewer's display choice (main rock from 1.5 m, deliberately enlarged
for readability; Golombek-Rapp tail above it). Nothing here is a NASA product, a measured
rock or a validated mission.
"""
import json
import math
from pathlib import Path
import struct
import zlib

import numpy as np
from scipy import ndimage

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


def _sample(grid, n, order=3):
    """Spline sample (cubic by default) of a cell-centre grid (row 0 = south) on an n x n lattice spanning the
    grid's outer edges, returned with row 0 = north."""
    rows, cols = grid.shape
    t = np.linspace(0.0, 1.0, n)
    yy = (1.0 - t)[:, None] * rows - 0.5          # north first
    xx = t[None, :] * cols - 0.5
    coords = np.array([np.broadcast_to(yy, (n, n)), np.broadcast_to(xx, (n, n))])
    return ndimage.map_coordinates(grid, coords, order=order, mode='nearest')


def fractal_noise(n, seed, octaves=6, base=8):
    """Seeded fractal value noise in [0, 1], n x n (cosmetic detail)."""
    rng = np.random.default_rng(seed)
    total, amp, norm = np.zeros((n, n)), 1.0, 0.0
    for o in range(octaves):
        cells = base * 2 ** o
        coarse = rng.random((cells + 1, cells + 1))
        total += amp * ndimage.zoom(coarse, n / (cells + 1), order=3, mode='wrap')[:n, :n]
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
    dn = _sample(np.asarray(ctx_dn, dtype=float), n)
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


def _agent_sdf(agent_id, kind, x, y, z):
    _, color, geom, lift = AGENT_MODELS[kind]
    # Visual only, no gravity, no collision: its pose comes from ROS through gz_mirror.
    return (f'<model name="{agent_id}"><pose>{x:.3f} {y:.3f} {z + lift:.3f} 0 0 0</pose>'
            f'<link name="link"><gravity>false</gravity><visual name="v"><geometry>{geom}</geometry>'
            f'<material><ambient>{color}</ambient><diffuse>{color}</diffuse></material></visual></link></model>')


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


def physical_rover_sdf(agent_id, x, y, z, yaw=0.0):
    """A six-wheel rover driven by gz DiffDrive on /model/<id>/cmd_vel, with ground-truth
    odometry on /model/<id>/odometry_gt. It rests on the terrain under Mars gravity."""
    cz = WHEEL_R + CLEARANCE + CHASSIS[2] / 2 - 0.35
    mat = '<material><ambient>0.6 0.6 0.62 1</ambient><diffuse>0.78 0.78 0.8 1</diffuse></material>'
    dark = '<material><ambient>0.15 0.15 0.16 1</ambient><diffuse>0.22 0.22 0.24 1</diffuse></material>'
    links = (f'<link name="chassis"><pose>0 0 {cz:.3f} 0 0 0</pose>{_box_inertia(900, *CHASSIS)}'
             f'<collision name="c"><geometry><box><size>{CHASSIS[0]} {CHASSIS[1]} {CHASSIS[2]}</size></box></geometry></collision>'
             f'<visual name="body"><geometry><box><size>{CHASSIS[0]} {CHASSIS[1]} {CHASSIS[2]}</size></box></geometry>{mat}</visual>'
             f'<visual name="mast"><pose>0.9 0.6 1.0 0 0 0</pose><geometry><cylinder><radius>0.08</radius><length>1.5</length></cylinder></geometry>{mat}</visual>'
             f'<visual name="head"><pose>0.9 0.6 1.8 0 0 0</pose><geometry><box><size>0.3 0.5 0.25</size></box></geometry>{dark}</visual>'
             f'<visual name="rtg"><pose>-1.45 0 0.35 0 0.6 0</pose><geometry><cylinder><radius>0.3</radius><length>0.7</length></cylinder></geometry>{dark}</visual>'
             '</link>')
    joints, left, right = '', [], []
    for side, sy in (('l', WHEEL_Y), ('r', -WHEEL_Y)):
        for k, wx in enumerate(WHEEL_X):
            name = f'wheel_{side}{k}'
            geom = f'<cylinder><radius>{WHEEL_R}</radius><length>{WHEEL_W}</length></cylinder>'
            links += (f'<link name="{name}"><pose>{wx} {sy} {WHEEL_R} -1.5708 0 0</pose>'
                      '<inertial><mass>25</mass><inertia><ixx>0.8</ixx><iyy>0.8</iyy><izz>0.9</izz>'
                      '<ixy>0</ixy><ixz>0</ixz><iyz>0</iyz></inertia></inertial>'
                      f'<collision name="c"><geometry>{geom}</geometry><surface><friction><ode><mu>0.9</mu><mu2>0.9</mu2></ode></friction></surface></collision>'
                      f'<visual name="v"><geometry>{geom}</geometry>{dark}</visual></link>')
            joints += (f'<joint name="{name}_joint" type="revolute"><parent>chassis</parent><child>{name}</child>'
                       '<axis><xyz>0 0 1</xyz><limit><lower>-1e16</lower><upper>1e16</upper></limit></axis></joint>')
            (left if side == 'l' else right).append(f'{name}_joint')
    plugins = ('<plugin filename="gz-sim-diff-drive-system" name="gz::sim::systems::DiffDrive">'
               + ''.join(f'<left_joint>{j}</left_joint>' for j in left)
               + ''.join(f'<right_joint>{j}</right_joint>' for j in right)
               + f'<wheel_separation>{2 * WHEEL_Y}</wheel_separation><wheel_radius>{WHEEL_R}</wheel_radius>'
               f'<topic>/model/{agent_id}/cmd_vel</topic><max_linear_acceleration>0.5</max_linear_acceleration>'
               '<max_angular_acceleration>1.0</max_angular_acceleration></plugin>'
               '<plugin filename="gz-sim-odometry-publisher-system" name="gz::sim::systems::OdometryPublisher">'
               f'<odom_topic>/model/{agent_id}/odometry_gt</odom_topic><dimensions>3</dimensions>'
               '<odom_publish_frequency>20</odom_publish_frequency></plugin>')
    return (f'<model name="{agent_id}"><pose>{x:.3f} {y:.3f} {z + 0.05:.3f} 0 0 {yaw:.3f}</pose>'
            + links + joints + plugins + '</model>')


def build_world(out_dir, grid, heights, blocked, agents, ctx_dn=None, world_name='jezero', physical=()):
    """grid = (origin_x_m, origin_y_m, resolution_m, rows, cols); heights and ctx_dn are
    rows x cols arrays with row 0 = south (None/NaN = NoData); blocked = flat indices of the
    SIMULATED scene's obstacle cells; agents = [(agent_id, kind, x, y, z)] in ROS ENU;
    physical = agent IDs built as driven rovers (gz_rover_driver) instead of mirrored models."""
    ox, oy, res, rows, cols = grid
    if rows != cols:
        raise ValueError('the heightmap needs a square grid')
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    h = terrain_heights(np.array(heights, dtype=float).reshape(rows, cols))
    verts = _sample(h, HEIGHTMAP_SIZE, order=1)   # bilinear: no overshoot, no invented relief
    z_ref, span = float(verts.min()), max(float(verts.max() - verts.min()), 0.01)
    (out / 'heightmap.png').write_bytes(png_gray16(np.round((verts - z_ref) / span * 65535)))
    dn = np.full((rows, cols), 135.0) if ctx_dn is None else np.array(ctx_dn, dtype=float).reshape(rows, cols)
    (out / 'albedo.png').write_bytes(png_rgb8(albedo_texture(dn)))
    (out / 'normal.png').write_bytes(png_rgb8(normal_texture()))
    for k in range(ROCK_VARIANTS):
        (out / f'rock_{k}.obj').write_text(boulder_obj(k + 1), encoding='utf-8')
    width, height = cols * res, rows * res

    def ground(x, y):
        j = (x - ox) / width * (HEIGHTMAP_SIZE - 1)
        i = (1 - (y - oy) / height) * (HEIGHTMAP_SIZE - 1)
        return float(ndimage.map_coordinates(verts, [[i], [j]], order=1, mode='nearest')[0]) - z_ref

    terrain = (f'<heightmap><texture><diffuse>albedo.png</diffuse><normal>normal.png</normal>'
               f'<size>{width}</size></texture><uri>heightmap.png</uri>'
               f'<size>{width} {height} {span:.3f}</size><pos>{ox + width / 2} {oy + height / 2} 0</pos></heightmap>')
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
           + ''.join(physical_rover_sdf(a, x, y, ground(x, y)) if a in physical else _agent_sdf(a, k, x, y, z - z_ref)
                     for a, k, x, y, z in agents)
           + '</world></sdf>')
    (out / 'world.sdf').write_text(sdf, encoding='utf-8')
    meta = {'world_name': world_name, 'origin_x_m': ox, 'origin_y_m': oy, 'resolution_m': res,
            'rows': rows, 'cols': cols, 'z_ref_m': z_ref, 'relief_m': span,
            'boulders': sum(r['collide'] for r in rocks), 'small_rocks': sum(not r['collide'] for r in rocks),
            'agents': {a: {'model': AGENT_MODELS[k][0], 'lift_m': 0.0 if a in physical else AGENT_MODELS[k][3],
                           'physical': a in physical} for a, k, *_ in agents},
            'real_inputs': ['public prior heights (collision surface)', 'MRO CTX orthoimage DN (albedo)'],
            'cosmetic': ['regolith tint and grain', 'normal map', 'boulder shapes and sizes (enlarged)'],
            'note': 'SIMULATED scene on the public Jezero crop; not a NASA product or a validated mission.'}
    (out / 'world.json').write_text(json.dumps(meta, indent=1), encoding='utf-8')
    return meta
