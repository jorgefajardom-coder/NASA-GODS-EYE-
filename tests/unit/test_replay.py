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
