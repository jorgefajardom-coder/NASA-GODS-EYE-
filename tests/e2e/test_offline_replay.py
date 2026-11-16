"""T08 offline replay (R15): every run the viewer catalogues opens from static files alone.

The deployed viewer has no backend: it fetches `replay/<run>/manifest.json` and the files that
manifest names, relative to the site. This test resolves each catalogued run exactly as the
build does (web/public/replay/<run>, else data/sample/replay/<run> emitted by vite.config.ts),
checks that every file the loader requests exists and parses, validates recorder packages with
the offline gateway checker, and checks that no evaluator reference is published (R05/AC-07).

Static checks only: rendering in a browser with the backend off is checked separately and
recorded in the handoff. Packages are MOCK or illustrative; nothing here is a LIVE mission.
"""
import json
from pathlib import Path
import re

import pytest

from mge_gateway.replay_check import check_package
from mge_gateway.store import mock_evidence

ROOT = Path(__file__).resolve().parents[2]
ADAPTER = ROOT / 'web/src/data/replayAdapter.ts'
PUBLIC = ROOT / 'web/public'
SAMPLE = ROOT / 'data/sample/replay'
# Optional manifest sections the loader fetches when present (replayAdapter.loadReplay).
OPTIONAL_SECTIONS = ('geology', 'atmosphere', 'context', 'rover_stops')


def catalogued_runs():
    """Run ids of the RUNS catalogue, read from the viewer source so the two cannot drift."""
    source = ADAPTER.read_text(encoding='utf-8')
    block = source[source.index('export const RUNS'):]
    block = block[:block.index('];')]
    constants = dict(re.findall(r"export const (\w+_ENTRY) = '([\w.-]+)'", source))
    ids = [constants.get(name, name) for name in re.findall(r"\{ id: '?([\w.-]+)'?,", block)]
    assert ids and all(re.fullmatch(r'[\w.-]+', i) for i in ids), ids
    return ids


def package_dir(run):
    for base in (PUBLIC / 'replay', SAMPLE):
        if (base / run / 'manifest.json').is_file():
            return base / run
    return None


def load_json(path):
    return json.loads(path.read_text(encoding='utf-8'))


def requested_files(manifest):
    """Files the viewer fetches for this manifest, relative to the package directory."""
    files = manifest.get('files') or {}
    if 'snapshot' in files:                       # recorder (gateway) package
        names = [files['timeline'], files['snapshot']]
        names += [files['public_rasters']] if files.get('public_rasters') else []
        return names
    names = [files['rasters'], files['timeline'], files['routes']]
    for section in OPTIONAL_SECTIONS:
        entry = manifest.get(section)
        if isinstance(entry, dict) and entry.get('file'):
            names.append(entry['file'])
    return names


RUNS = catalogued_runs()


def test_catalogue_has_the_default_and_unique_runs():
    assert 'demo' in RUNS
    assert len(RUNS) == len(set(RUNS))


@pytest.mark.parametrize('run', RUNS)
def test_every_catalogued_run_has_a_static_package(run):
    directory = package_dir(run)
    assert directory is not None, f'{run}: no replay/{run}/manifest.json in the site or data/sample'
    manifest = load_json(directory / 'manifest.json')
    for name in requested_files(manifest):
        assert '/' not in name and '..' not in name, f'{run}: {name} leaves the package'
        path = directory / name
        assert path.is_file(), f'{run}: manifest names {name}, which is missing'
        if path.suffix == '.json':
            load_json(path)
        elif path.suffix == '.jsonl':
            lines = [line for line in path.read_text(encoding='utf-8').splitlines() if line.strip()]
            assert lines, f'{run}: empty timeline'
            for line in lines:
                json.loads(line)


@pytest.mark.parametrize('run', [r for r in RUNS if package_dir(r) is not None
                                 and 'snapshot' in (load_json(package_dir(r) / 'manifest.json').get('files') or {})])
def test_recorder_packages_pass_the_offline_checker(run):
    problems = check_package(str(package_dir(run)))
    # The viewer addresses a package by folder and keeps its recorded run_id intact
    # (App.tsx: RUN_ID comment), so a renamed folder is expected here.
    problems = [p for p in problems if not p.startswith('directory name differs from run_id')]
    assert problems == []


@pytest.mark.parametrize('run', [r for r in RUNS if package_dir(r) is not None])
def test_replays_are_labelled_mock_or_illustrative_never_live(run):
    manifest = load_json(package_dir(run) / 'manifest.json')
    assert manifest.get('source_mode') != 'LIVE'
    # Same rule as the gateway store and the viewer's resolveSourceMode: MOCK terrain
    # metadata labels an older package MOCK even without a declared source_mode.
    mock = manifest.get('source_mode') == 'MOCK' or mock_evidence(manifest.get('terrain_meta'))
    assert mock or manifest.get('illustrative') is True, f'{run}: neither MOCK nor illustrative'


def test_no_evaluator_reference_is_published():
    """R05/AC-07: the hidden reference stays out of the static site and sample replays."""
    published = [p for base in (PUBLIC, SAMPLE) for p in base.rglob('*') if p.is_file()]
    names = [p.relative_to(ROOT).as_posix() for p in published
             if re.search(r'(^|/)(evaluator|reference|evaluation_reference|ground_truth)([/._-]|$)',
                          p.relative_to(ROOT).as_posix().lower())]
    assert names == []
    for path in published:
        if path.suffix == '.json' and path.parent.parent.name == 'replay' and path.stat().st_size < 50_000_000:
            data = load_json(path)
            if isinstance(data, dict):
                assert 'reference' not in data, f'{path.relative_to(ROOT)} carries a reference raster'
