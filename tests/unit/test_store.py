"""Ordering rules of the gateway store (ICD section 2). No ROS graph needed."""
import json
import math

import pytest

from mge_gateway.store import (
    agent_json, event_json, meta_json, NonFiniteValue, route_json, RunStore, state_json,
    strict_json, to_json)


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


def test_conflicting_event_sequence_is_rejected():
    store = RunStore('run-a')
    assert store.apply_event(event(1))
    assert not store.apply_event({**event(1), 'event_id': 'different-id'})
    assert store.events() == [event(1)]


@pytest.mark.parametrize('seq', [0, -1, True, '1', None, 2**64])
def test_invalid_event_sequence_is_rejected(seq):
    store = RunStore('run-a')
    assert not store.apply_event({**event(1), 'seq': seq})
    assert store.events() == []


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
    assert env == {'schema_version': '1.0.0', 'run_id': 'run-a', 'mode': 'LIVE',
                   'map_version': 7, 'timestamp_sim_s': 12.5, 'extra': 1}


def test_error_detail_helper_is_lossy_by_design():
    data = to_json({'a': math.nan, 'b': [1.0, math.inf], 'c': 'x'})
    assert data == {'a': None, 'b': [1.0, None], 'c': 'x'}
    json.dumps(data, allow_nan=False)


def test_map_version_is_the_newest_seen():
    store = RunStore('run-a')
    store.apply_state(state(1, 'r', map_version=1))
    store.apply_meta({'run_id': 'run-a', 'map_version': 2})
    assert store.map_version() == 2


# Typed serialization (ICD section 5): NaN is null only where the contract
# gives it a meaning. Values are illustrative, not mission results.

def route(status='FEASIBLE', agent_id='rover_1', **fields):
    return {'route_id': 'r1' if status == 'FEASIBLE' else '', 'agent_id': agent_id,
            'status': status, 'travel_time_s': 10.0, 'energy_est_wh': 5.0,
            'oxygen_est_l': math.nan, 'min_clearance_m': 1.0, 'reserve_time_s': 90.0,
            'reserve_wh': 95.0, 'reserve_oxygen_l': math.nan, **fields}


def agent(kind='ROVER', oxygen=math.nan, agent_id='rover_1'):
    return {'agent_id': agent_id, 'agent_kind': kind, 'oxygen_remaining_l': oxygen,
            'energy_remaining_wh': 100.0}


def test_non_human_oxygen_nan_is_null():
    assert agent_json(agent())['oxygen_remaining_l'] is None
    data = route_json(route(), 'ROVER')
    assert data['oxygen_est_l'] is None and data['reserve_oxygen_l'] is None
    json.dumps(data, allow_nan=False)


def test_human_oxygen_must_be_a_number():
    assert agent_json(agent('HUMAN', 600.0))['oxygen_remaining_l'] == 600.0
    with pytest.raises(NonFiniteValue, match='oxygen_remaining_l'):
        agent_json(agent('HUMAN'))
    with pytest.raises(NonFiniteValue, match='oxygen_est_l'):
        route_json(route(), 'HUMAN')


def test_feasible_route_oxygen_needs_a_known_agent_kind():
    with pytest.raises(NonFiniteValue):
        route_json(route(), None)


@pytest.mark.parametrize('field', ['travel_time_s', 'energy_est_wh', 'min_clearance_m',
                                   'reserve_time_s', 'reserve_wh'])
def test_feasible_route_metric_is_never_nulled(field):
    with pytest.raises(NonFiniteValue, match=field):
        route_json(route(**{field: math.nan}), 'ROVER')


@pytest.mark.parametrize('status', ['UNKNOWN', 'NO_PATH', 'INSUFFICIENT_BUDGET',
                                    'STALE_MAP', 'ERROR', ''])
def test_unavailable_metrics_of_a_route_without_result_are_null(status):
    nan = {name: math.nan for name in ('travel_time_s', 'energy_est_wh', 'min_clearance_m',
                                       'reserve_time_s', 'reserve_wh')}
    data = route_json(route(status, **nan), 'HUMAN')
    assert all(data[name] is None for name in nan)
    assert data['oxygen_est_l'] is None


@pytest.mark.parametrize('status', ['FEASIBLE', 'NO_PATH'])
@pytest.mark.parametrize('value', [math.inf, -math.inf])
def test_infinity_is_never_a_sentinel(status, value):
    with pytest.raises(NonFiniteValue):
        route_json(route(status, travel_time_s=value), 'ROVER')
    with pytest.raises(NonFiniteValue):
        agent_json(agent(oxygen=value))
    with pytest.raises(NonFiniteValue):
        meta_json({'nodata_value': value})


def test_terrain_nodata_nan_is_null_but_geometry_is_not():
    assert meta_json({'nodata_value': math.nan, 'resolution_m': 5.0}) == {
        'nodata_value': None, 'resolution_m': 5.0}
    with pytest.raises(NonFiniteValue, match='terrain_meta.origin_x_m'):
        meta_json({'nodata_value': math.nan, 'origin_x_m': math.nan})


def test_mission_state_uses_the_kind_of_the_route_agent():
    human = agent('HUMAN', 600.0, 'human_1')
    data = state_json({'run_id': 'run-a', 'agents': [human, agent()],
                       'active_route': route(agent_id='rover_1')})
    assert data['active_route']['oxygen_est_l'] is None
    assert data['agents'][1]['oxygen_remaining_l'] is None
    json.dumps(data, allow_nan=False)
    with pytest.raises(NonFiniteValue, match='mission_state.active_route.oxygen_est_l'):
        state_json({'agents': [human], 'active_route': route(agent_id='human_1')})


def test_invalid_position_rejects_the_whole_state():
    bad = {'agents': [{**agent(), 'pose': {'position': {'x': math.nan, 'y': 0.0}}}]}
    with pytest.raises(NonFiniteValue, match=r'agents\[0\].pose.position.x'):
        state_json(bad)
    with pytest.raises(NonFiniteValue, match='base.y'):
        state_json({'agents': [], 'base': {'x': 0.0, 'y': math.inf}})


def test_converters_do_not_modify_their_input():
    source = {'agents': [agent()], 'active_route': route()}
    state_json(source)
    assert math.isnan(source['agents'][0]['oxygen_remaining_l'])
    assert math.isnan(source['active_route']['oxygen_est_l'])
    assert event_json({'seq': 1, 'detail': 'x'}) == {'seq': 1, 'detail': 'x'}
    assert strict_json({'a': [1.0, 'x', None, True]}) == {'a': [1.0, 'x', None, True]}
