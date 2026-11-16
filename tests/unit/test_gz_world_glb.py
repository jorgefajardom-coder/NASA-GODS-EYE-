"""Derived Gazebo meshes from valid glTF 2.0 edge cases: sparse accessors (with and without a
base bufferView) are decoded, and unsupported cosmetic derivations degrade without aborting
the world build."""
import json
import struct

import numpy as np
import pytest

from mge_sim.gz_world import (accessor_array, build_world, derive_walking_actor, glb_bbox, read_glb,
                              write_glb)

GRID = (-64.0, -64.0, 4.0, 32, 32)


def _wheels():
    """Six square 'wheels' (radius 0.25) at mesh-local x = +-1, z = -1, 0, +1, two triangles each."""
    pos, idx = [], []
    for x in (-1.0, 1.0):
        for z in (-1.0, 0.0, 1.0):
            base = len(pos)
            pos += [(x, 0.0, z - 0.25), (x, 0.5, z - 0.25), (x, 0.5, z + 0.25), (x, 0.0, z + 0.25)]
            idx += [base, base + 1, base + 2, base, base + 2, base + 3]
    return np.array(pos, dtype=np.float32), np.array(idx, dtype=np.uint16)


class Glb:
    """A tiny GLB writer for the tests."""

    def __init__(self):
        self.blob, self.views, self.accs = bytearray(), [], []

    def view(self, data, target=None, stride=None):
        v = {'buffer': 0, 'byteOffset': len(self.blob), 'byteLength': len(data)}
        if target:
            v['target'] = target
        if stride:
            v['byteStride'] = stride
        self.blob.extend(data + b'\x00' * (-len(data) % 4))
        self.views.append(v)
        return len(self.views) - 1

    def dense(self, arr, ctype, kind, target=None):
        a = np.asarray(arr, dtype={5126: np.float32, 5123: np.uint16}[ctype])
        acc = {'bufferView': self.view(a.tobytes(), target), 'componentType': ctype, 'count': len(a), 'type': kind}
        if kind == 'VEC3':
            acc['min'], acc['max'] = a.min(axis=0).tolist(), a.max(axis=0).tolist()
        self.accs.append(acc)
        return len(self.accs) - 1

    def sparse(self, true, base=None, base_stride=None):
        """A float VEC3 accessor equal to `true`: zeros (base=None, no bufferView) or `base`
        (interleaved with byteStride=base_stride when given), with every differing vertex
        substituted by the sparse block."""
        true = np.asarray(true, dtype=np.float32)
        start = np.zeros_like(true) if base is None else np.asarray(base, dtype=np.float32)
        changed = np.flatnonzero(np.any(start != true, axis=1)).astype(np.uint16)
        acc = {'componentType': 5126, 'count': len(true), 'type': 'VEC3',
               'min': true.min(axis=0).tolist(), 'max': true.max(axis=0).tolist(),
               'sparse': {'count': int(changed.size),
                          'indices': {'bufferView': self.view(changed.tobytes()), 'componentType': 5123},
                          'values': {'bufferView': self.view(true[changed].tobytes())}}}
        if base is not None:
            if base_stride:            # interleave the base with 4 padding bytes per vertex
                rows = np.zeros((len(start), base_stride), dtype=np.uint8)
                rows[:, :12] = np.frombuffer(start.tobytes(), dtype=np.uint8).reshape(-1, 12)
                acc['bufferView'] = self.view(rows.tobytes(), 34962, stride=base_stride)
            else:
                acc['bufferView'] = self.view(start.tobytes(), 34962)
        self.accs.append(acc)
        return len(self.accs) - 1

    def write(self, path, gltf):
        gltf = {'asset': {'version': '2.0'}, **gltf, 'accessors': self.accs, 'bufferViews': self.views,
                'buffers': [{'byteLength': len(self.blob)}]}
        body = json.dumps(gltf).encode()
        body += b' ' * (-len(body) % 4)
        path.write_bytes(struct.pack('<4sII', b'glTF', 2, 12 + 8 + len(body) + 8 + len(self.blob))
                         + struct.pack('<I4s', len(body), b'JSON') + body
                         + struct.pack('<I4s', len(self.blob), b'BIN\x00') + bytes(self.blob))
        return path


def sparse_rover_glb(path, mode):
    """A rover whose wheel POSITION accessor is sparse: mode 'zeros' (no bufferView), 'base'
    (a base view with some wrong vertices) or 'strided' (an interleaved base view)."""
    pos, idx = _wheels()
    b = Glb()
    if mode == 'zeros':
        wp = b.sparse(pos)
    else:
        base = pos.copy()
        base[::3] = 9.0                              # every third vertex is replaced by the sparse block
        wp = b.sparse(pos, base, base_stride=16 if mode == 'strided' else None)
    wi = b.dense(idx, 5123, 'SCALAR', 34963)
    bp = b.dense([(-1.2, 0.5, -1.4), (1.2, 0.5, -1.4), (1.2, 1.5, 1.4)], 5126, 'VEC3', 34962)
    return b.write(path, {
        'scene': 0, 'scenes': [{'nodes': [0]}],
        'nodes': [{'name': 'Empty', 'rotation': [0, 0.7071068, 0, 0.7071068], 'children': [1, 2]},
                  {'name': 'Body', 'mesh': 0}, {'name': 'Wheels_objs', 'mesh': 1}],
        'meshes': [{'primitives': [{'attributes': {'POSITION': bp}}]},
                   {'primitives': [{'attributes': {'POSITION': wp}, 'indices': wi}]}]}), pos


@pytest.mark.parametrize('mode', ['zeros', 'base', 'strided'])
def test_sparse_accessors_are_decoded(tmp_path, mode):
    path, pos = sparse_rover_glb(tmp_path / 'rover.glb', mode)
    g, bin_ = read_glb(path)
    wp = g['meshes'][1]['primitives'][0]['attributes']['POSITION']
    assert np.array_equal(accessor_array(g, bin_, wp), pos)


@pytest.mark.parametrize('mode', ['zeros', 'base'])
def test_rover_with_sparse_wheels_is_split_into_six_wheels(tmp_path, mode):
    models = tmp_path / 'models'
    models.mkdir()
    sparse_rover_glb(models / 'rover.glb', mode)
    out = tmp_path / 'w'
    meta = build_world(out, GRID, np.full((32, 32), -2570.0), [], [('rover_1', 'ROVER', -14.0, -10.0, -2570.0)],
                       physical=('rover_1',), web_models={'ROVER': models / 'rover.glb'})
    assert meta['agents']['rover_1']['wheel_visuals'] is True and len(meta['derived_models']) == 7
    for k in range(6):
        g, _ = read_glb(out / f'rover_wheel_{k}.glb')
        assert all('sparse' not in a for a in g['accessors'])           # written dense
        lo, hi = glb_bbox(out / f'rover_wheel_{k}.glb')
        assert list((lo + hi) / 2) == pytest.approx([0, 0, 0], abs=1e-6) and hi[1] == pytest.approx(0.25)


def test_whole_sparse_primitive_is_copied_dense(tmp_path):
    path, pos = sparse_rover_glb(tmp_path / 'rover.glb', 'zeros')
    g, bin_ = read_glb(path)
    write_glb(tmp_path / 'copy.glb', g, bin_, [(np.eye(4), [(g['meshes'][1]['primitives'][0], None)])])
    h, hbin = read_glb(tmp_path / 'copy.glb')
    p = h['meshes'][0]['primitives'][0]
    assert 'sparse' not in h['accessors'][p['attributes']['POSITION']]
    assert np.array_equal(accessor_array(h, hbin, p['attributes']['POSITION']), pos)


def skinned_glb(path, sparse_positions):
    """A minimal skinned astronaut with a 'moon_walk' clip; POSITION may be a view-less sparse accessor."""
    pos = np.array([(0, 0, 0), (0.2, 0, 0), (0, 3.8, 0), (0, 3.8, 0.2)], dtype=np.float32)
    b = Glb()
    p = b.sparse(pos) if sparse_positions else b.dense(pos, 5126, 'VEC3', 34962)
    ibm = b.view(np.eye(4, dtype=np.float32).T.tobytes())
    b.accs.append({'bufferView': ibm, 'componentType': 5126, 'count': 1, 'type': 'MAT4'})
    t = b.view(np.array([0.0, 1.0], dtype=np.float32).tobytes())
    b.accs.append({'bufferView': t, 'componentType': 5126, 'count': 2, 'type': 'SCALAR', 'min': [0.0], 'max': [1.0]})
    out = b.sparse(np.array([(0, 0, 0), (0, 0, 1)], dtype=np.float32))     # a sparse clip output too
    return b.write(path, {
        'scene': 0, 'scenes': [{'nodes': [0]}],
        'nodes': [{'name': 'Root', 'children': [1, 2]}, {'name': 'Center'}, {'name': 'Body', 'mesh': 0, 'skin': 0}],
        'meshes': [{'primitives': [{'attributes': {'POSITION': p}}]}],
        'skins': [{'joints': [1], 'inverseBindMatrices': 1}],
        'animations': [{'name': 'moon_walk', 'samplers': [{'input': 2, 'output': out}],
                        'channels': [{'sampler': 0, 'target': {'node': 1, 'path': 'translation'}}]}]}), pos


@pytest.mark.parametrize('sparse', [False, True])
def test_walking_actor_rewrites_sparse_accessors(tmp_path, sparse):
    path, pos = skinned_glb(tmp_path / 'astronaut.glb', sparse)
    name, _ = derive_walking_actor(path, tmp_path)                       # 3.8 units tall -> 1.9 m
    g, bin_ = read_glb(tmp_path / name)
    acc = g['meshes'][0]['primitives'][0]['attributes']['POSITION']
    assert 'sparse' not in g['accessors'][acc]
    assert np.allclose(accessor_array(g, bin_, acc), pos[:, [2, 0, 1]] * 0.5)
    out = g['animations'][0]['samplers'][0]['output']
    assert np.allclose(accessor_array(g, bin_, out), [(0, 0, 0), (0.5, 0, 0)])
    assert g['buffers'][0]['byteLength'] == len(bin_)


def test_unsupported_cosmetic_parts_do_not_abort_the_world(tmp_path):
    models = tmp_path / 'models'
    models.mkdir()
    path, _ = sparse_rover_glb(models / 'rover.glb', 'base')
    data = path.read_bytes()                     # break the wheel indices (an unknown component type)
    n = struct.unpack('<I', data[12:16])[0]
    g = json.loads(data[20:20 + n])
    g['accessors'][1]['componentType'] = 9999
    body = json.dumps(g).encode()
    body += b' ' * (-len(body) % 4)
    rest = data[20 + n:]
    path.write_bytes(struct.pack('<4sII', b'glTF', 2, 12 + 8 + len(body) + len(rest))
                     + struct.pack('<I4s', len(body), b'JSON') + body + rest)
    out = tmp_path / 'w'
    with pytest.warns(RuntimeWarning, match='whole web model'):
        meta = build_world(out, GRID, np.full((32, 32), -2570.0), [], [('rover_1', 'ROVER', -14.0, -10.0, -2570.0)],
                           physical=('rover_1',), web_models={'ROVER': path})
    assert (out / 'world.sdf').exists() and 'derived_models' not in meta
    assert 'wheel_visuals' not in meta['agents']['rover_1']
