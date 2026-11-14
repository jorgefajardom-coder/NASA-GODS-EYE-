"""Thread-safe run state held by the gateway. No ROS imports: inputs are the
JSON-ready dicts produced by the typed converters below, so the ordering and
serialization rules can be unit tested without a ROS graph.

Rules (docs/ICD.md, sections 2, 5 and 6):
- data of another run_id is dropped;
- an event_id is applied once;
- a mission state older than the one held (lower last_event_seq) is dropped,
  so a late answer never replaces the route in force;
- NaN becomes null only where the wire contract defines it as "not applicable"
  or "unavailable"; any other NaN or infinity rejects the whole message.
"""
import math
import threading

SCHEMA_VERSION = '1.0.0'

ROUTE_METRICS = ('travel_time_s', 'energy_est_wh', 'oxygen_est_l', 'min_clearance_m',
                 'reserve_time_s', 'reserve_wh', 'reserve_oxygen_l')
ROUTE_OXYGEN = ('oxygen_est_l', 'reserve_oxygen_l')
NON_HUMAN_KINDS = ('ROVER', 'DRONE')


class NonFiniteValue(ValueError):
    """A NaN or infinity where the contract has no null meaning for it."""


def valid_event_sequence(value):
    """Events start at 1; 0 is the polling cursor before the first event."""
    return type(value) is int and 0 < value < 2**64


def to_json(value):
    """Lossy: every NaN / infinity becomes null. Only for echoing rejected
    input in error details; never for mission data (use the typed converters).
    """
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    if isinstance(value, dict):
        return {k: to_json(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [to_json(v) for v in value]
    return value


def strict_json(value, path='value'):
    """Copy a message dict, refusing any NaN or infinity left in it."""
    if isinstance(value, float):
        if not math.isfinite(value):
            raise NonFiniteValue(f'NONFINITE_VALUE: {path}')
        return value
    if isinstance(value, dict):
        return {k: strict_json(v, f'{path}.{k}') for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [strict_json(v, f'{path}[{i}]') for i, v in enumerate(value)]
    return value


def _nan_to_null(data, keys):
    """NaN is the only sentinel: an infinity in the same field stays an error."""
    for key in keys:
        if isinstance(data.get(key), float) and math.isnan(data[key]):
            data[key] = None


def meta_json(meta):
    """TerrainMeta: NaN `nodata_value` is how 32FC1 rasters mark NoData."""
    data = dict(meta)
    _nan_to_null(data, ('nodata_value',))
    return strict_json(data, 'terrain_meta')


def agent_json(agent, path='agent'):
    """AgentState: oxygen is not applicable (NaN) to agents that are not HUMAN."""
    data = dict(agent)
    if data.get('agent_kind') in NON_HUMAN_KINDS:
        _nan_to_null(data, ('oxygen_remaining_l',))
    return strict_json(data, path)


def route_json(route, agent_kind, path='route'):
    """RouteDecision: metrics are unavailable (NaN) unless the route is
    FEASIBLE; a FEASIBLE route keeps NaN only for non-human oxygen."""
    data = dict(route)
    if data.get('status') != 'FEASIBLE':
        _nan_to_null(data, ROUTE_METRICS)
    elif agent_kind in NON_HUMAN_KINDS:
        _nan_to_null(data, ROUTE_OXYGEN)
    return strict_json(data, path)


def state_json(state):
    """MissionState: the route's agent kind is read from the agents it lists."""
    data = dict(state)
    data['agents'] = [agent_json(a, f'mission_state.agents[{i}]')
                      for i, a in enumerate(data.get('agents', []))]
    route = data.get('active_route')
    if route is not None:
        kinds = {a.get('agent_id'): a.get('agent_kind') for a in data['agents']}
        data['active_route'] = route_json(
            route, kinds.get(route.get('agent_id')), 'mission_state.active_route')
    return strict_json(data, 'mission_state')


def event_json(event):
    return strict_json(event, 'event')


CONVERTERS = {'state': state_json, 'event': event_json, 'terrain_meta': meta_json}


def unavailable(reason_code, run_id=None, status='NOT_READY'):
    """Envelope used while no run is loaded. It invents no run, map, clock or
    mode: only a run with a mission state may be reported as LIVE or REPLAY."""
    return {
        'schema_version': SCHEMA_VERSION,
        'run_id': run_id,
        'mode': None,
        'map_version': None,
        'timestamp_sim_s': None,
        'status': status,
        'reason_code': reason_code,
    }


class RunStore:

    def __init__(self, run_id):
        self.run_id = run_id
        self._lock = threading.Lock()
        self._state = None
        self._meta = None
        self._events = []
        self._event_ids = set()
        self._event_seqs = set()

    def apply_state(self, state):
        """Return True if the state was accepted."""
        with self._lock:
            if state['run_id'] != self.run_id:
                return False
            if self._state and state['last_event_seq'] < self._state['last_event_seq']:
                return False
            self._state = state
            return True

    def apply_event(self, event):
        """Return True if the event was accepted."""
        with self._lock:
            if event['run_id'] != self.run_id or event['event_id'] in self._event_ids:
                return False
            seq = event.get('seq')
            if not valid_event_sequence(seq) or seq in self._event_seqs:
                return False
            self._event_ids.add(event['event_id'])
            self._event_seqs.add(seq)
            self._events.append(event)
            self._events.sort(key=lambda e: e['seq'])
            return True

    def apply_meta(self, meta):
        with self._lock:
            if meta['run_id'] != self.run_id:
                return False
            if self._meta and meta['map_version'] < self._meta['map_version']:
                return False
            self._meta = meta
            return True

    def state(self):
        with self._lock:
            return self._state

    def meta(self):
        with self._lock:
            return self._meta

    def events(self, after_seq=0):
        with self._lock:
            return [e for e in self._events if e['seq'] > after_seq]

    def map_version(self):
        """Newest map version seen, from either the mission state or the terrain."""
        with self._lock:
            return max(self._state['map_version'] if self._state else 0,
                       self._meta['map_version'] if self._meta else 0)

    def envelope(self, timestamp_sim_s, mode='LIVE', **payload):
        """Fields every web response declares, plus the payload."""
        return {
            'schema_version': SCHEMA_VERSION,
            'run_id': self.run_id,
            'mode': mode,
            'map_version': self.map_version(),
            'timestamp_sim_s': timestamp_sim_s,
            **payload,
        }
