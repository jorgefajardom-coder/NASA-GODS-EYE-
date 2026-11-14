"""Validate a replay package offline: no ROS graph, gateway or network.

    check_replay <package directory>

Exits 0 if the package is consistent, 1 with one line per problem otherwise.
"""
import json
import os
import sys

from mge_gateway.replay import MANIFEST, SNAPSHOT
from mge_gateway.store import (
    DECLARABLE_SOURCE_MODES, mock_evidence, SCHEMA_VERSION, valid_event_sequence)

ENVELOPE = ('schema_version', 'run_id', 'mode', 'map_version', 'timestamp_sim_s')
KINDS = ('event', 'state', 'terrain_meta')


def check_package(path):
    """Return a list of problems; empty means the package is valid."""
    problems = []

    def load(name):
        try:
            with open(os.path.join(path, name), encoding='utf-8') as f:
                return json.load(f)
        except (OSError, ValueError) as e:
            problems.append(f'{name}: cannot read ({e})')
            return None

    manifest = load(MANIFEST)
    snapshot = load(SNAPSHOT)
    if manifest is None or snapshot is None:
        return problems
    run_id = manifest.get('run_id')

    def check_envelope(name, obj):
        for field in ENVELOPE:
            if field not in obj:
                problems.append(f'{name}: missing {field}')
        if obj.get('schema_version') != SCHEMA_VERSION:
            problems.append(f'{name}: schema_version is {obj.get("schema_version")!r}')
        if obj.get('mode') != 'REPLAY':
            problems.append(f'{name}: mode is {obj.get("mode")!r}, a package must say REPLAY')
        if obj.get('run_id') != run_id:
            problems.append(f'{name}: run_id {obj.get("run_id")!r} differs from the manifest')

    check_envelope(MANIFEST, manifest)
    check_envelope(SNAPSHOT, snapshot)
    # Optional field: packages recorded before it existed do not have it.
    source_mode = manifest.get('source_mode', 'UNKNOWN')
    if source_mode not in DECLARABLE_SOURCE_MODES:
        problems.append(f'{MANIFEST}: source_mode is {source_mode!r}, a recording '
                        f'may only say one of {", ".join(DECLARABLE_SOURCE_MODES)}')
    elif mock_evidence(manifest.get('terrain_meta')) and manifest.get('source_mode', 'MOCK') != 'MOCK':
        problems.append(f'{MANIFEST}: source_mode is {source_mode!r} but the terrain says MOCK')
    if os.path.basename(os.path.normpath(path)) != run_id:
        problems.append(f'directory name differs from run_id {run_id!r}')

    records = []
    timeline = manifest.get('files', {}).get('timeline', '')
    try:
        with open(os.path.join(path, timeline), encoding='utf-8') as f:
            for n, line in enumerate(f, 1):
                try:
                    records.append(json.loads(line))
                except ValueError:
                    problems.append(f'{timeline}:{n}: not JSON')
    except OSError as e:
        problems.append(f'{timeline}: cannot read ({e})')
        return problems

    if len(records) != manifest.get('record_count'):
        problems.append(f'{timeline}: {len(records)} records, manifest says '
                        f'{manifest.get("record_count")}')

    events, last_state = [], None
    last_t = last_state_seq = last_map = -1
    for n, rec in enumerate(records, 1):
        where = f'{timeline}:{n}'
        check_envelope(where, rec)
        kind = rec.get('type')
        if kind not in KINDS or kind not in rec:
            problems.append(f'{where}: bad record type {kind!r}')
            continue
        body = rec[kind]
        if body.get('run_id') != run_id:
            problems.append(f'{where}: payload of run {body.get("run_id")!r}')
        t = rec.get('timestamp_sim_s', -1)
        if t < last_t:
            problems.append(f'{where}: time goes backwards')
        last_t = max(last_t, t)
        if kind == 'event':
            if not valid_event_sequence(body.get('seq')):
                problems.append(f'{where}: event seq must be a positive uint64')
                continue
            events.append(body)
        elif kind == 'state':
            if body['last_event_seq'] < last_state_seq:
                problems.append(f'{where}: older mission state after a newer one')
            last_state_seq = body['last_event_seq']
            if body['map_version'] < last_map:
                problems.append(f'{where}: map_version decreases')
            last_map = body['map_version']
            last_state = body
    ids = [e['event_id'] for e in events]
    if len(ids) != len(set(ids)):
        problems.append(f'{timeline}: duplicate event_id')
    seqs = [e['seq'] for e in events]
    if len(seqs) != len(set(seqs)):
        problems.append(f'{timeline}: duplicate event seq')

    # The timeline preserves arrival order, including late DDS deliveries.
    # Reconstruct the same logical event history as RunStore and the snapshot.
    events.sort(key=lambda e: e['seq'])

    if snapshot.get('events') != events:
        problems.append(f'{SNAPSHOT}: events differ from the timeline')
    if snapshot.get('mission_state') != last_state:
        problems.append(f'{SNAPSHOT}: mission_state is not the last state of the timeline')
    if manifest.get('event_count') != len(events):
        problems.append(f'{MANIFEST}: event_count differs from the timeline')
    return problems


def main():
    if len(sys.argv) != 2:
        print(__doc__.strip(), file=sys.stderr)
        sys.exit(2)
    problems = check_package(sys.argv[1])
    for p in problems:
        print(p)
    if problems:
        sys.exit(1)
    print(f'OK: {sys.argv[1]} is a consistent replay package')


if __name__ == '__main__':
    main()
