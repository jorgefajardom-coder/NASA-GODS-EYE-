"""Public raster recording: assembly by stamp, package file and oracle checks.

Layer values are illustrative test inputs on small grids and on the geometry
of the pinned MOCK recording; they are not terrain or observations.
"""
from copy import deepcopy
import json
import math
import os
from pathlib import Path
import shutil

import pytest

from mge_gateway import contract_replay
from mge_gateway.contract_replay import (
    check_public_rasters, read_package, read_public_rasters, ReplayContractError, to_viewer,
)
from mge_gateway.public_rasters import (
    FILE, GEOMETRY, PublicRasterAssembler, RasterInputError, SCHEMA,
)
from mge_gateway.replay import ReplayWriter
from mge_gateway.replay_check import check_package

FIXTURE = Path(__file__).resolve().parents[1] / 'fixtures' / 'replay' / 'mock-vertical-001'
RUN = 'run-r'
ROWS, COLS = 2, 3
CELLS = ROWS * COLS


def header(sec, nanosec=0):
    return {'frame_id': 'map', 'stamp': {'sec': sec, 'nanosec': nanosec}}


def meta(version, sec, nodata=None, run_id=RUN, **changes):
    return {'header': header(sec), 'run_id': run_id, 'map_version': version,
            'dataset_id': 'test-grid', 'rows': ROWS, 'cols': COLS,
            'origin_x_m': -3.0, 'origin_y_m': -2.0, 'resolution_m': 2.0, 'crs': 'local',
            'origin_lat_deg': 0.0, 'origin_lon_deg': 0.0, 'vertical_datum': 'test',
            'nodata_value': nodata, **changes}


def batch(assembler, sec, belief=None, sigma=None, observed=None, skip=()):
    belief = belief or [float(i) for i in range(CELLS)]
    sigma = sigma or [0.5] * CELLS
    observed = observed or [0] * CELLS
    changed = False
    for layer, values in (('belief', belief), ('sigma', sigma), ('observed', observed)):
        if layer not in skip:
            changed = assembler.on_layer(layer, header(sec), ROWS, COLS, values) or changed
    return changed


def test_shared_constants_match_the_oracle():
    assert GEOMETRY == contract_replay.GEOMETRY
    assert SCHEMA == contract_replay.PUBLIC_RASTER_SCHEMA
    assert FILE == contract_replay.RASTER_FILE


def test_version_completes_only_with_every_layer_of_its_stamp():
    a = PublicRasterAssembler(RUN)
    a.on_prior(ROWS, COLS, [1.0] * CELLS)
    batch(a, 10, skip=('observed',))                # layers before their metadata
    assert a.on_meta(meta(1, 10)) is False          # observed still missing
    assert a.attachment() is None
    assert a.on_layer('observed', header(10), ROWS, COLS, [1, 0, 0, 0, 0, 1]) is True
    out = a.attachment()
    assert out['schema_version'] == SCHEMA and out['run_id'] == RUN
    assert out['terrain_geometry'] == {k: meta(1, 10)[k] for k in GEOMETRY}
    assert out['versions']['1']['observed'] == [0, 5]
    assert out['versions']['1']['belief'] == [float(i) for i in range(CELLS)]
    # A repeat of the complete batch changes nothing.
    assert batch(a, 10) is False and a.on_meta(meta(1, 10)) is False


def test_layers_of_another_stamp_never_complete_a_version():
    a = PublicRasterAssembler(RUN)
    a.on_prior(ROWS, COLS, [1.0] * CELLS)
    a.on_meta(meta(1, 10))
    batch(a, 11)                                     # no metadata with this stamp
    assert a.attachment() is None


def test_prior_is_needed_and_immutable():
    a = PublicRasterAssembler(RUN)
    a.on_meta(meta(1, 10))
    assert batch(a, 10) is False                     # complete, but no prior yet
    assert a.on_prior(ROWS, COLS, [1.0] * CELLS) is True
    assert a.on_prior(ROWS, COLS, [1.0] * CELLS) is False
    with pytest.raises(RasterInputError, match='immutable prior'):
        a.on_prior(ROWS, COLS, [2.0] * CELLS)


def test_prior_before_metadata_keeps_its_own_shape():
    # Same cell count, transposed grid: must not be accepted as the 2 x 3 grid.
    a = PublicRasterAssembler(RUN)
    assert a.on_prior(COLS, ROWS, [float(i) for i in range(CELLS)]) is False
    with pytest.raises(RasterInputError, match='3 x 2 differs from the metadata grid 2 x 3'):
        a.on_meta(meta(1, 10))
    batch(a, 10)
    assert a.prior is None and a.attachment() is None
    # The metadata was kept, so a prior of the right shape completes the run.
    assert a.on_prior(ROWS, COLS, [1.0] * CELLS) is True
    assert a.attachment()['prior'] == [1.0] * CELLS


def test_a_repeated_prior_with_another_shape_is_rejected():
    a = PublicRasterAssembler(RUN)
    a.on_prior(ROWS, COLS, [1.0] * CELLS)
    with pytest.raises(RasterInputError, match='immutable prior'):
        a.on_prior(COLS, ROWS, [1.0] * CELLS)


def test_nodata_becomes_null_and_infinities_are_rejected():
    a = PublicRasterAssembler(RUN)
    a.on_prior(ROWS, COLS, [math.nan, -9999.0, 1.0, 1.0, 1.0, 1.0])
    a.on_meta(meta(1, 10, nodata=-9999.0))
    batch(a, 10, belief=[math.nan, -9999.0, 3.0, 3.0, 3.0, 3.0])
    out = a.attachment()
    assert out['prior'][:3] == [None, None, 1.0]
    assert out['versions']['1']['belief'][:3] == [None, None, 3.0]
    with pytest.raises(RasterInputError, match='infinite'):
        a.on_prior(ROWS, COLS, [math.inf] * CELLS)
    b = PublicRasterAssembler(RUN)
    b.on_meta(meta(1, 10))
    with pytest.raises(RasterInputError, match='negative'):
        batch(b, 10, sigma=[-1.0] * CELLS)


@pytest.mark.parametrize('change,error', [
    (lambda a: a.on_meta(meta(1, 11)), 'second stamp'),
    (lambda a: a.on_meta(meta(2, 10)), 'reused'),
    (lambda a: a.on_meta(meta(2, 11, resolution_m=4.0)), 'geometry changed'),
    (lambda a: a.on_layer('belief', header(11), ROWS, COLS + 1, [0.0] * (CELLS + ROWS)), 'differs'),
    (lambda a: a.on_layer('reference', header(11), ROWS, COLS, [0.0] * CELLS), 'unknown layer'),
    (lambda a: a.on_layer('belief', {**header(11), 'frame_id': 'odom'}, ROWS, COLS,
                          [0.0] * CELLS), 'not map'),
])
def test_mixed_or_malformed_batches_are_rejected(change, error):
    a = PublicRasterAssembler(RUN)
    a.on_meta(meta(1, 10))
    with pytest.raises(RasterInputError, match=error):
        change(a)


def test_observed_mask_must_be_binary():
    a = PublicRasterAssembler(RUN)
    a.on_meta(meta(1, 10))
    with pytest.raises(RasterInputError, match='0 or 1'):
        batch(a, 10, observed=[2] * CELLS)          # checked when the batch completes


def test_metadata_of_another_run_is_ignored():
    a = PublicRasterAssembler(RUN)
    assert a.on_meta(meta(1, 10, run_id='other')) is False
    assert a.meta is None


def recorded_package(tmp_path):
    """A writer package with metadata for versions 1 and 2 and states on both."""
    writer = ReplayWriter(str(tmp_path), RUN, 'system', 'MOCK')
    for version, sec in ((1, 10), (2, 20)):
        writer.record('terrain_meta', meta(version, sec))
        writer.record('state', {'header': header(sec), 'run_id': RUN, 'last_event_seq': 0,
                                'route_id': '', 'map_version': version, 'agents': []})
    assembler = PublicRasterAssembler(RUN)
    assembler.on_prior(ROWS, COLS, [1.0] * CELLS)
    for version, sec in ((1, 10), (2, 20)):
        assembler.on_meta(meta(version, sec))
        batch(assembler, sec, observed=[0] * CELLS if version == 1 else [1] + [0] * (CELLS - 1))
    writer.write_public_rasters(assembler.attachment())
    writer.close()
    return writer.dir


def test_writer_names_the_attachment_and_check_replay_validates_it(tmp_path):
    path = recorded_package(tmp_path)
    with open(os.path.join(path, 'manifest.json'), encoding='utf-8') as f:
        manifest = json.load(f)
    assert manifest['files'] == {'timeline': 'timeline.jsonl', 'snapshot': 'snapshot.json',
                                 'public_rasters': FILE}
    assert check_package(path) == []

    with open(os.path.join(path, FILE), encoding='utf-8') as f:
        attachment = json.load(f)
    del attachment['versions']['2']                 # a version the mission used
    with open(os.path.join(path, FILE), 'w', encoding='utf-8') as f:
        json.dump(attachment, f)
    assert any('RASTER_VERSION_MISMATCH' in p for p in check_package(path))


def test_writer_refuses_rasters_of_another_run(tmp_path):
    writer = ReplayWriter(str(tmp_path), RUN, 'system')
    with pytest.raises(ValueError, match='another run'):
        writer.write_public_rasters({'run_id': 'other'})


def fixture_attachment(manifest, records):
    """Assemble the pinned MOCK recording's two versions on its own geometry."""
    metas = [r['terrain_meta'] for r in records if r['type'] == 'terrain_meta']
    cells = manifest['terrain_meta']['rows'] * manifest['terrain_meta']['cols']
    rows, cols = manifest['terrain_meta']['rows'], manifest['terrain_meta']['cols']
    assembler = PublicRasterAssembler(manifest['run_id'])
    assembler.on_prior(rows, cols, [0.0] * cells)
    for m in metas:
        assembler.on_meta(m)
        for layer, values in (('belief', [0.0] * cells), ('sigma', [0.1] * cells),
                              ('observed', [1] * cells)):
            assembler.on_layer(layer, m['header'], rows, cols, values)
    return assembler.attachment()


def test_assembled_attachment_makes_the_pinned_recording_ready():
    manifest, records, snapshot = read_package(FIXTURE)
    attachment = fixture_attachment(manifest, records)
    assert set(attachment['versions']) == {'1', '2'}
    result = to_viewer(manifest, records, snapshot, public_rasters=attachment)
    assert result['status'] == 'READY'
    assert all(v is None for v in result['rasters']['reference'])
    assert json.loads(json.dumps(result, allow_nan=False)) == result


def test_oracle_versions_extra_unrecorded_and_missing():
    manifest, records, snapshot = read_package(FIXTURE)
    attachment = fixture_attachment(manifest, records)
    extra = deepcopy(attachment)
    extra['versions']['3'] = extra['versions']['2']  # never recorded metadata
    with pytest.raises(ReplayContractError, match='RASTER_VERSION_MISMATCH'):
        check_public_rasters(manifest, records, extra)
    # A state at version 0 (no map yet) needs no raster.
    early = deepcopy(records)
    first_state = next(r for r in early if r['type'] == 'state')
    early.insert(early.index(first_state), {**deepcopy(first_state), 'map_version': 0,
                 'state': {**first_state['state'], 'map_version': 0}})
    check_public_rasters(manifest, early, attachment)


def test_recorded_attachment_is_read_from_the_package(tmp_path):
    shutil.copytree(FIXTURE, tmp_path / FIXTURE.name)
    manifest, records, snapshot = read_package(tmp_path / FIXTURE.name)
    assert read_public_rasters(tmp_path / FIXTURE.name, manifest) is None
    manifest['files']['public_rasters'] = FILE
    attachment = fixture_attachment(manifest, records)
    (tmp_path / FIXTURE.name / FILE).write_text(json.dumps(attachment), encoding='utf-8')
    assert read_public_rasters(tmp_path / FIXTURE.name, manifest) == attachment
    attachment['reference'] = [0.0]
    (tmp_path / FIXTURE.name / FILE).write_text(json.dumps(attachment), encoding='utf-8')
    with pytest.raises(ReplayContractError, match='EVALUATOR_REFERENCE_FORBIDDEN'):
        read_public_rasters(tmp_path / FIXTURE.name, manifest)
