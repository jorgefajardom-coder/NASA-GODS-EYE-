"""Gazebo world generation: heightmap, textures, rocks inside cells, agents and frame."""
import json
import math
import struct
from types import SimpleNamespace as NS
import xml.etree.ElementTree as ET

import numpy as np
import pytest

from mge_sim.gz_world import HEIGHTMAP_SIZE, ROCK_VARIANTS, boulder_obj, build_world, rock_layout

GRID = (-64.0, -64.0, 4.0, 32, 32)


def png_size(path):
    data = path.read_bytes()
    assert data[:8] == b'\x89PNG\r\n\x1a\n'
    width, height, depth, color = struct.unpack('>IIBB', data[16:26])
    return width, height, depth, color


@pytest.fixture
def world(tmp_path):
    yy, xx = np.mgrid[0:32, 0:32]
    heights = -2570.0 + 0.2 * xx + 0.1 * yy          # rises to the east and north
    heights[0, 0] = np.nan                             # one NoData cell
    agents = [('human_1', 'HUMAN', -14.0, -14.0, -2568.0), ('drone_1', 'DRONE', -10.0, -14.0, -2568.0)]
    meta = build_world(tmp_path, GRID, heights, [12 * 32 + 15, 20 * 32 + 20], agents,
                       ctx_dn=np.full((32, 32), 130.0))
    return tmp_path, meta


def test_files_and_formats(world):
    out, meta = world
    assert png_size(out / 'heightmap.png') == (HEIGHTMAP_SIZE, HEIGHTMAP_SIZE, 16, 0)
    assert png_size(out / 'albedo.png')[2:] == (8, 2) and png_size(out / 'normal.png')[2:] == (8, 2)
    assert all((out / f'rock_{k}.obj').exists() for k in range(ROCK_VARIANTS))
    assert json.loads((out / 'world.json').read_text()) == meta


def test_world_sdf_has_mars_gravity_terrain_rocks_and_agents(world):
    out, meta = world
    root = ET.parse(out / 'world.sdf').getroot()
    w = root.find('world')
    assert w.findtext('gravity') == '0 0 -3.721'
    names = [m.get('name') for m in w.findall('model')]
    assert 'terrain' in names and 'human_1' in names and 'drone_1' in names
    boulders = [m for m in w.findall('model') if m.get('name', '').endswith('_0')]
    assert len(boulders) == meta['boulders'] == 2
    assert all(m.find('link/collision') is not None for m in boulders)
    small = [m for m in w.findall('model') if m.get('name', '').startswith('rock_') and not m.get('name').endswith('_0')]
    assert small and all(m.find('link/collision') is None for m in small)
    agent = next(m for m in w.findall('model') if m.get('name') == 'human_1')
    assert agent.find('link/collision') is None and agent.findtext('link/gravity') == 'false'


def test_frame_keeps_ros_heights_recoverable(world):
    _, meta = world
    assert -2570.0 <= meta['z_ref_m'] <= -2569.8                   # lowest vertex (NoData filled low)
    assert 9.0 < meta['relief_m'] < 10.0                          # bilinear: within the data range
    assert meta['agents']['human_1']['model'] == 'astronaut'


def test_rocks_stay_inside_their_cells_and_main_boulders_are_hazard_size():
    rocks = rock_layout(GRID, range(1024))
    for r in rocks:
        cell = int(r['name'].split('_')[1])
        row, col = divmod(cell, 32)
        assert -64 + col * 4 <= r['x'] <= -64 + (col + 1) * 4
        assert -64 + row * 4 <= r['y'] <= -64 + (row + 1) * 4
        width = 2 * max(r['radii'][:2])
        assert width >= 1.5 * 0.85 - 1e-9 if r['collide'] else width < 1.5
    assert sum(r['collide'] for r in rocks) == 1024


def test_boulder_mesh_is_a_closed_triangle_mesh():
    text = boulder_obj(3)
    verts = [line for line in text.splitlines() if line.startswith('v ')]
    faces = [line for line in text.splitlines() if line.startswith('f ')]
    assert len(verts) == 162 and len(faces) == 320
    normals = [line for line in text.splitlines() if line.startswith('vn ')]
    assert len(normals) == 162
    assert all(abs(sum(float(c) ** 2 for c in n.split()[1:]) - 1) < 1e-3 for n in normals)
    assert '//' in faces[0]
    assert min(float(v.split()[2]) for v in verts) >= -0.35       # flat base


def test_mirror_pose_uses_the_world_frame():
    from mge_sim.gz_control import gz_pose
    meta = {'z_ref_m': -2570.0, 'agents': {'human_1': {'lift_m': 0.95}}}
    state = NS(agent_id='human_1', pose=NS(position=NS(x=1.0, y=2.0, z=-2568.0),
                                          orientation=NS(x=0.0, y=0.0, z=0.0, w=0.0)))
    assert gz_pose(state, meta) == (1.0, 2.0, pytest.approx(2.95), 0.0, 0.0, 0.0, 1.0)


def test_physical_rover_has_six_driven_wheels_and_ground_truth_odometry(tmp_path):
    heights = np.full((32, 32), -2570.0)
    agents = [('rover_1', 'ROVER', -14.0, -10.0, -2570.0), ('human_1', 'HUMAN', -14.0, -14.0, -2570.0)]
    meta = build_world(tmp_path, GRID, heights, [], agents, physical=('rover_1',))
    w = ET.parse(tmp_path / 'world.sdf').getroot().find('world')
    rover = next(m for m in w.findall('model') if m.get('name') == 'rover_1')
    assert len([j for j in rover.findall('joint') if j.get('type') == 'revolute']) == 6
    plugins = {p.get('name'): p for p in rover.findall('plugin')}
    drive = plugins['gz::sim::systems::DiffDrive']
    assert len(drive.findall('left_joint')) == 3 and len(drive.findall('right_joint')) == 3
    assert drive.findtext('topic') == '/model/rover_1/cmd_vel'
    assert plugins['gz::sim::systems::OdometryPublisher'].findtext('odom_topic') == '/model/rover_1/odometry_gt'
    assert rover.find('link[@name="chassis"]/collision') is not None       # it can hit rocks
    assert rover.find('link/gravity') is None                              # it falls onto the ground
    assert meta['agents']['rover_1'] == {'model': 'rover', 'lift_m': 0.0, 'physical': True, 'web_model': False}
    assert meta['agents']['human_1']['physical'] is False


def test_pure_pursuit_turns_first_then_drives_and_stops_at_the_end():
    from mge_sim.gz_control import pursuit
    points = [(0.0, 0.0), (10.0, 0.0), (10.0, 10.0)]
    v, w, i, done = pursuit((0.0, 0.0), math.pi, points, 0, 0.65)       # facing backwards
    assert v == 0.0 and abs(w) > 0 and not done                         # turn in place
    v, w, i, done = pursuit((2.0, 0.0), 0.0, points, i, 0.65)
    assert v == pytest.approx(0.65) and w == pytest.approx(0.0) and i == 1
    v, w, i, done = pursuit((10.0, 9.7), math.pi / 2, points, 2, 0.65)
    assert done and (v, w) == (0.0, 0.0)


def test_heightmap_vertices_sit_on_the_planner_cell_centres():
    from mge_sim.gz_world import centre_lattice
    rng = np.random.default_rng(4)
    h = rng.random((32, 32)) * 7
    v = centre_lattice(h, HEIGHTMAP_SIZE)
    for r in (0, 5, 31):
        for c in (0, 17, 31):
            assert v[HEIGHTMAP_SIZE - 1 - 4 * r, 4 * c] == pytest.approx(h[r, c])
    # Linear between two neighbouring centres, never outside their range.
    mid = v[HEIGHTMAP_SIZE - 1 - 4 * 5, 4 * 17 + 2]
    assert mid == pytest.approx((h[5, 17] + h[5, 18]) / 2)


def test_world_heightmap_is_placed_on_the_cell_centres(world):
    out, meta = world
    assert meta['heightmap_origin_m'] == [-62.0, -62.0] and meta['heightmap_on_cell_centres']
    pos = ET.parse(out / 'world.sdf').getroot().find('world/model[@name="terrain"]/link/collision/geometry/heightmap/pos').text
    assert pos.split()[:2] == ['2.0', '2.0']                      # lattice spans -62 .. 66 m


def test_datum_offset_diagnostic_is_bounded():
    from mge_sim.gz_control import MAX_DATUM_OFFSET_M, datum_offset, map_height
    prior = [[0.0, 4.0], [8.0, 12.0]]
    assert map_height(prior, (0.0, 0.0), 4.0, 2.0, 2.0) == pytest.approx(0.0)
    assert map_height(prior, (0.0, 0.0), 4.0, 4.0, 4.0) == pytest.approx(6.0)
    assert datum_offset(-2571.3296, -2571.4120) == pytest.approx(0.0824)
    assert datum_offset(0.0, -MAX_DATUM_OFFSET_M - 0.01) is None
    assert datum_offset(math.nan, 0.0) is None
    assert datum_offset(0.0, math.inf) is None


def tiny_glb(path, lo, hi, translation=(0.0, 0.0, 0.0), scale=(1.0, 1.0, 1.0)):
    """A minimal GLB whose single mesh has the given POSITION bounds (no geometry needed)."""
    gltf = {'asset': {'version': '2.0'}, 'scene': 0, 'scenes': [{'nodes': [0]}],
            'nodes': [{'mesh': 0, 'translation': list(translation), 'scale': list(scale)}],
            'meshes': [{'primitives': [{'attributes': {'POSITION': 0}}]}],
            'accessors': [{'componentType': 5126, 'count': 2, 'type': 'VEC3', 'min': list(lo), 'max': list(hi)}]}
    body = json.dumps(gltf).encode()
    body += b' ' * (-len(body) % 4)
    path.write_bytes(struct.pack('<4sII', b'glTF', 2, 12 + 8 + len(body)) + struct.pack('<I4s', len(body), b'JSON') + body)
    return path


def test_glb_bounds_follow_node_transforms(tmp_path):
    from mge_sim.gz_world import glb_bbox
    lo, hi = glb_bbox(tiny_glb(tmp_path / 'm.glb', (-1, 0, -0.5), (1, 2, 0.5), translation=(3, 0, 0), scale=(2, 2, 2)))
    assert list(lo) == pytest.approx([1, 0, -1]) and list(hi) == pytest.approx([5, 4, 1])


def test_web_models_are_drawn_at_the_web_true_sizes(tmp_path):
    models = tmp_path / 'models'
    models.mkdir()
    tiny_glb(models / 'rover.glb', (-2.0, 0.0, -1.0), (2.0, 2.0, 1.0))      # 4 m long -> 3.6 m
    tiny_glb(models / 'astronaut.glb', (-0.5, 0.0, -0.3), (0.5, 3.8, 0.3))  # 3.8 m tall -> 1.9 m
    out = tmp_path / 'w'
    agents = [('rover_1', 'ROVER', -14.0, -10.0, -2570.0), ('human_1', 'HUMAN', -14.0, -14.0, -2570.0)]
    meta = build_world(out, GRID, np.full((32, 32), -2570.0), [], agents, physical=('rover_1',),
                       web_models={'ROVER': models / 'rover.glb', 'HUMAN': models / 'astronaut.glb'})
    assert (out / 'rover.glb').exists() and (out / 'astronaut.glb').exists()
    w = ET.parse(out / 'world.sdf').getroot().find('world')
    rover = next(m for m in w.findall('model') if m.get('name') == 'rover_1')
    assert rover.findtext('link[@name="chassis"]/visual/geometry/mesh/scale') == '0.90000 0.90000 0.90000'
    assert all(link.find('visual') is None for link in rover.findall('link') if link.get('name').startswith('wheel'))
    human = next(m for m in w.findall('model') if m.get('name') == 'human_1')
    assert human.findtext('link/visual/geometry/mesh/scale') == '0.50000 0.50000 0.50000'
    assert meta['agents']['human_1']['lift_m'] == 0.0 and meta['web_models'] == {'ROVER': 'rover.glb', 'HUMAN': 'astronaut.glb'}
    assert 'CC BY 4.0' in meta['attribution']
