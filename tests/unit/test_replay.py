"""Replay package writer and offline validator. No ROS graph needed."""
import json
import os

import pytest

from mge_gateway.replay import ReplayWriter
from mge_gateway.replay_check import check_package

RUN = 'run-a'


def hdr(t):
    return {'stamp': {'sec': int(t), 'nanosec': 0}, 'frame_id': 'map'}


def state(t, seq, route_id='', map_version=1, run_id=RUN):
    return {'header': hdr(t), 'run_id': run_id, 'last_event_seq': seq, 'route_id': route_id,
            'map_version': map_version,
            'agents': [{'header': hdr(t), 'agent_id': 'human_1', 'agent_kind': 'HUMAN'}]}


def event(t, seq, run_id=RUN):
    return {'header': hdr(t), 'run_id': run_id, 'event_id': f'{run_id}-e{seq}', 'seq': seq}


def meta(t, version=1):
    return {'header': hdr(t), 'run_id': RUN, 'map_version': version, 'dataset_id': 'MOCK'}


@pytest.fixture
def package(tmp_path):
    w = ReplayWriter(str(tmp_path), RUN, 'system')
    w.record('terrain_meta', meta(10))
    w.record('state', state(10, 0))
    w.record('event', event(11, 1))
    w.record('state', state(11, 1, route_id='r1'))
    w.close()
    return w.dir


def read(path, name):
    with open(os.path.join(path, name), encoding='utf-8') as f:
        return json.load(f)


def lines(path):
    with open(os.path.join(path, 'timeline.jsonl'), encoding='utf-8') as f:
        return [json.loads(line) for line in f]


def test_package_is_consistent_and_marked_replay(package):
    assert check_package(package) == []
    for name in ('manifest.json', 'snapshot.json', 'timeline.jsonl'):
        with open(os.path.join(package, name), encoding='utf-8') as f:
            text = f.read()
        assert '"REPLAY"' in text and '"mode": "LIVE"' not in text
    recs = lines(package)
    assert [r['type'] for r in recs] == ['terrain_meta', 'state', 'event', 'state']
    assert recs[2]['event']['seq'] == 1          # same shape as a WebSocket message


def test_never_overwrites_a_run(package, tmp_path):
    with pytest.raises(FileExistsError):
        ReplayWriter(str(tmp_path), RUN, 'system')


def test_drops_duplicates_stale_and_foreign_data(tmp_path):
    w = ReplayWriter(str(tmp_path), RUN, 'system')
    assert w.record('state', state(10, 5, route_id='r5'))
    assert not w.record('state', state(11, 5, route_id='r5'))   # same content, new stamp
    assert not w.record('state', state(12, 4, route_id='r4'))   # older than the one held
    assert w.record('event', event(12, 1))
    assert not w.record('event', event(13, 1))                  # duplicate event_id
    assert not w.record('event', event(13, 2, run_id='run-b'))  # another run
    assert not w.record('terrain_meta', {**meta(14), 'run_id': 'run-b'})
    w.close()
    assert [r['type'] for r in lines(w.dir)] == ['state', 'event']
    assert check_package(w.dir) == []


def test_validator_reports_tampering(package):
    path = os.path.join(package, 'snapshot.json')
    with open(path, encoding='utf-8') as f:
        snap = json.load(f)
    snap['mode'] = 'LIVE'
    snap['mission_state']['route_id'] = 'forged'
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(snap, f)
    problems = check_package(package)
    assert any('must say REPLAY' in p for p in problems)
    assert any('mission_state is not the last state' in p for p in problems)


def test_validator_reports_missing_package(tmp_path):
    assert check_package(str(tmp_path / 'nothing'))


def test_late_events_preserve_arrival_and_logical_history(tmp_path):
    writer = ReplayWriter(str(tmp_path), RUN, 'system')
    assert writer.record('state', state(10, 0))
    assert writer.record('event', event(12, 2))
    assert writer.record('state', state(12, 2, route_id='r2'))
    assert writer.record('event', event(11, 1))
    writer.close()

    records = lines(writer.dir)
    assert [r['type'] for r in records] == ['state', 'event', 'state', 'event']
    assert [r['event']['seq'] for r in records if r['type'] == 'event'] == [2, 1]
    assert [r['timestamp_sim_s'] for r in records] == [10, 12, 12, 12]
    # The original producer stamp is preserved even when receipt time is clamped.
    assert records[-1]['event']['header']['stamp']['sec'] == 11
    with open(os.path.join(writer.dir, 'snapshot.json'), encoding='utf-8') as f:
        snapshot = json.load(f)
    assert [e['seq'] for e in snapshot['events']] == [1, 2]
    assert snapshot['mission_state']['route_id'] == 'r2'
    assert check_package(writer.dir) == []


def test_validator_rejects_conflicting_event_sequences(tmp_path):
    writer = ReplayWriter(str(tmp_path), RUN, 'system')
    assert writer.record('event', event(11, 1))
    assert writer.record('event', event(12, 2))
    writer.close()
    records = lines(writer.dir)
    records[1]['event']['seq'] = 1  # distinct IDs claiming the same logical event
    with open(os.path.join(writer.dir, 'timeline.jsonl'), 'w', encoding='utf-8') as f:
        for record in records:
            f.write(json.dumps(record) + '\n')
    snapshot_path = os.path.join(writer.dir, 'snapshot.json')
    with open(snapshot_path, encoding='utf-8') as f:
        snapshot = json.load(f)
    snapshot['events'][1]['seq'] = 1
    with open(snapshot_path, 'w', encoding='utf-8') as f:
        json.dump(snapshot, f)
    assert any('duplicate event seq' in p for p in check_package(writer.dir))


def test_conflicting_sequence_is_not_recorded(tmp_path):
    writer = ReplayWriter(str(tmp_path), RUN, 'system')
    assert writer.record('event', event(11, 1))
    assert not writer.record('event', {**event(12, 1), 'event_id': 'conflicting-id'})
    writer.close()
    assert len(lines(writer.dir)) == 1
    assert check_package(writer.dir) == []


def test_manifest_records_who_produced_the_data(tmp_path):
    # The fixture terrain says MOCK, so no declaration can relabel it.
    writer = ReplayWriter(str(tmp_path), RUN, 'sim', 'SIMULATION')
    assert read(writer.dir, 'manifest.json')['source_mode'] == 'SIMULATION'
    writer.record('terrain_meta', meta(10))
    writer.close()
    manifest = read(writer.dir, 'manifest.json')
    assert manifest['source_mode'] == 'MOCK'
    assert manifest['recorded_from'] == 'LIVE' and manifest['mode'] == 'REPLAY'
    assert check_package(writer.dir) == []


def test_undeclared_source_is_unknown_not_live(tmp_path):
    writer = ReplayWriter(str(tmp_path), RUN, 'system')
    writer.close()
    assert read(writer.dir, 'manifest.json')['source_mode'] == 'UNKNOWN'


def test_recording_cannot_declare_a_live_source(tmp_path):
    with pytest.raises(ValueError, match='LIVE_BACKEND_UNAVAILABLE'):
        ReplayWriter(str(tmp_path), RUN, 'system', 'LIVE')
    assert not os.path.exists(os.path.join(str(tmp_path), RUN))


@pytest.mark.parametrize('value', ['LIVE', 'SIMULATION', 'REAL'])
def test_validator_reports_relabelled_source(package, value):
    manifest = read(package, 'manifest.json')
    manifest['source_mode'] = value
    with open(os.path.join(package, 'manifest.json'), 'w', encoding='utf-8') as f:
        json.dump(manifest, f)
    assert any('source_mode' in p for p in check_package(package))


def test_a_closed_package_is_never_extended(tmp_path):
    w = ReplayWriter(str(tmp_path), RUN, 'system')
    w.record('terrain_meta', meta(10))
    w.record('state', state(10, 0))
    w.close()
    w.close()                                   # second close is harmless
    # A late callback after shutdown must not touch the package.
    assert w.record('event', event(11, 1)) is False
    assert len(lines(w.dir)) == 2
    manifest = read(w.dir, 'manifest.json')
    assert manifest['record_count'] == 2 and manifest['event_count'] == 0
    assert check_package(w.dir) == []
