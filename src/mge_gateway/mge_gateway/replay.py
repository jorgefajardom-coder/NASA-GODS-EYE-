"""Replay package writer. No ROS imports.

A package is a directory named after the run:

    <run_id>/manifest.json    what the run is and which files it has
    <run_id>/timeline.jsonl   one accepted record per line, in arrival order
    <run_id>/snapshot.json    last known state, same shape as the live snapshot

Timeline records have the shape of the gateway WebSocket messages
(`type` plus an object of that name), so a web client can feed live messages
and replay records to the same handler. Everything is stamped mode=REPLAY.
Files are rewritten atomically after every record, so an interrupted run
still leaves a readable package. An existing run directory is never
overwritten.
"""
import json
import os

from mge_gateway.store import RunStore

TIMELINE = 'timeline.jsonl'
SNAPSHOT = 'snapshot.json'
MANIFEST = 'manifest.json'


def strip_headers(value):
    """Copy without `header` fields, to compare content regardless of stamps."""
    if isinstance(value, dict):
        return {k: strip_headers(v) for k, v in value.items() if k != 'header'}
    if isinstance(value, list):
        return [strip_headers(v) for v in value]
    return value


def stamp_s(payload):
    stamp = payload['header']['stamp']
    return stamp['sec'] + stamp['nanosec'] / 1e9


def write_json(path, data):
    tmp = path + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=1, allow_nan=False)
        f.write('\n')
    os.replace(tmp, path)


class ReplayWriter:

    def __init__(self, root, run_id, clock_source):
        self.dir = os.path.join(root, run_id)
        os.makedirs(self.dir)       # raises FileExistsError: never overwrite a run
        self.store = RunStore(run_id)
        self.clock_source = clock_source
        self.count = 0
        self.first_s = None
        self.last_s = 0.0
        self._last_state = None
        self._timeline = open(os.path.join(self.dir, TIMELINE), 'w', encoding='utf-8')
        self._write_summary()

    def record(self, kind, payload):
        """kind: 'event' | 'state' | 'terrain_meta'. Returns True if recorded."""
        if kind == 'event':
            accepted = self.store.apply_event(payload)
        elif kind == 'state':
            content = strip_headers(payload)
            accepted = content != self._last_state and self.store.apply_state(payload)
            if accepted:
                self._last_state = content
        else:
            previous = self.store.meta()
            accepted = self.store.apply_meta(payload) and (
                previous is None or strip_headers(previous) != strip_headers(payload))
        if not accepted:
            return False
        # Records are stored in arrival order; keep their time non-decreasing.
        self.last_s = max(self.last_s, stamp_s(payload))
        if self.first_s is None:
            self.first_s = self.last_s
        self.count += 1
        line = self.store.envelope(self.last_s, mode='REPLAY', type=kind, **{kind: payload})
        self._timeline.write(json.dumps(line, allow_nan=False) + '\n')
        self._timeline.flush()
        self._write_summary()
        return True

    def _write_summary(self):
        state = self.store.state()
        write_json(os.path.join(self.dir, SNAPSHOT), self.store.envelope(
            self.last_s, mode='REPLAY', mission_state=state,
            terrain_meta=self.store.meta(), events=self.store.events()))
        write_json(os.path.join(self.dir, MANIFEST), self.store.envelope(
            self.last_s, mode='REPLAY',
            recorded_from='LIVE',
            clock_source=self.clock_source,
            time_start_sim_s=self.first_s,
            record_count=self.count,
            event_count=len(self.store.events()),
            terrain_meta=self.store.meta(),
            agents=[{'agent_id': a['agent_id'], 'agent_kind': a['agent_kind']}
                    for a in (state['agents'] if state else [])],
            files={'timeline': TIMELINE, 'snapshot': SNAPSHOT}))

    def close(self):
        self._timeline.close()
