"""Ordering rules of the gateway store (ICD section 2). No ROS graph needed."""
import json
import math

from mge_gateway.store import RunStore, to_json


def state(seq, route_id, run_id='run-a', map_version=1):
    return {'run_id': run_id, 'last_event_seq': seq, 'route_id': route_id,
            'map_version': map_version}


def event(seq, run_id='run-a'):
    return {'run_id': run_id, 'event_id': f'{run_id}-e{seq}', 'seq': seq}


def test_late_older_state_does_not_replace_newer():
    # I-03: answer 4 arrives after answer 5.
    store = RunStore('run-a')
    assert store.apply_state(state(5, 'route-5'))
    assert not store.apply_state(state(4, 'route-4'))
    assert store.state()['route_id'] == 'route-5'


def test_duplicate_event_is_applied_once():
    # I-04
    store = RunStore('run-a')
    assert store.apply_event(event(1))
    assert not store.apply_event(event(1))
    assert len(store.events()) == 1


def test_other_run_is_dropped():
    store = RunStore('run-a')
    assert not store.apply_state(state(9, 'x', run_id='run-b'))
    assert not store.apply_event(event(1, run_id='run-b'))
    assert not store.apply_meta({'run_id': 'run-b', 'map_version': 3})
    assert store.state() is None and store.events() == [] and store.meta() is None


def test_events_are_ordered_and_filtered_by_seq():
    store = RunStore('run-a')
    for seq in (3, 1, 2):
        store.apply_event(event(seq))
    assert [e['seq'] for e in store.events()] == [1, 2, 3]
    assert [e['seq'] for e in store.events(after_seq=2)] == [3]


def test_envelope_declares_required_fields():
    store = RunStore('run-a')
    store.apply_state(state(1, 'r', map_version=7))
    env = store.envelope(12.5, extra=1)
    assert env == {'schema_version': '1.0', 'run_id': 'run-a', 'mode': 'LIVE',
                   'map_version': 7, 'timestamp_sim_s': 12.5, 'extra': 1}


def test_nan_becomes_null():
    data = to_json({'a': math.nan, 'b': [1.0, math.inf], 'c': 'x'})
    assert data == {'a': None, 'b': [1.0, None], 'c': 'x'}
    json.dumps(data, allow_nan=False)
