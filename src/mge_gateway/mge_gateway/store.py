"""Thread-safe run state held by the gateway. No ROS imports: inputs are the
JSON-ready dicts produced by `to_json`, so the ordering rules can be unit
tested without a ROS graph.

Rules (docs/ICD.md, section 2):
- data of another run_id is dropped;
- an event_id is applied once;
- a mission state older than the one held (lower last_event_seq) is dropped,
  so a late answer never replaces the route in force.
"""
import math
import threading

SCHEMA_VERSION = '1.0'


def to_json(value):
    """Make a message dict JSON-safe: NaN / infinity become null."""
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    if isinstance(value, dict):
        return {k: to_json(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [to_json(v) for v in value]
    return value


class RunStore:

    def __init__(self, run_id):
        self.run_id = run_id
        self._lock = threading.Lock()
        self._state = None
        self._meta = None
        self._events = []
        self._event_ids = set()

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
            self._event_ids.add(event['event_id'])
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
        with self._lock:
            if self._state:
                return self._state['map_version']
            return self._meta['map_version'] if self._meta else 0

    def envelope(self, timestamp_sim_s, **payload):
        """Fields every web response declares, plus the payload."""
        return {
            'schema_version': SCHEMA_VERSION,
            'run_id': self.run_id,
            'mode': 'LIVE',
            'map_version': self.map_version(),
            'timestamp_sim_s': timestamp_sim_s,
            **payload,
        }
