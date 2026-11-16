"""SIMULATED scene sensing: footprint, reporting policy and delivery bookkeeping."""
import json

import pytest

from mge_sim.scene_sensing import (
    SCENE_SCHEMA, Scene, SensorFeedback, SensorLedger, footprint, observation_values, scene_from_file,
)

GRID = (8, 8, 0.0, 0.0, 4.0)


def scene(blocked=(), nodata=()):
    heights = tuple(None if i in nodata else float(i) for i in range(64))
    return Scene(8, 8, 0.0, 0.0, 4.0, heights, frozenset(blocked))


def test_footprint_is_a_disc_of_cell_centres_inside_the_grid():
    s = scene()
    assert footprint(s, 2.0, 2.0, 0.0) == [0]
    assert sorted(footprint(s, 2.0, 2.0, 4.0)) == [0, 1, 8]
    assert len(footprint(s, 16.0, 16.0, 100.0)) == 64          # clipped to the grid
    assert footprint(s, -50.0, -50.0, 4.0) == []                # off the terrain sees nothing
    assert footprint(s, float('nan'), 0.0, 4.0) == []


def test_footprint_skips_nodata_cells():
    assert 1 not in footprint(scene(nodata={1}), 2.0, 2.0, 4.0)


def test_moving_agents_report_only_when_a_new_obstacle_is_in_view():
    s, ledger = scene(blocked={9}), SensorLedger()
    assert ledger.select(s, [0, 1, 8], moving=True) == []
    assert ledger.select(s, [0, 1, 8, 9], moving=True) == [0, 1, 8, 9]
    assert ledger.select(s, [0, 1, 8], moving=False) == [0, 1, 8]


def feedback(s, cells, version=3, stamp=13_000_000_000):
    observed, mask = [0] * 64, [-1] * 64
    sigma = [2.5] * 64
    for c in cells:
        observed[c], mask[c], sigma[c] = 1, 100 if c in s.blocked else 0, 0.25
    return SensorFeedback(version, stamp, s.heights, tuple(sigma), tuple(observed), tuple(mask))


def sent(ledger, s, rid, cells, version, now):
    ledger.sent(rid, cells, version, now, acquired_ns=round(now * 1e9),
                values=observation_values(s, cells, 0.25))


def test_reports_need_matching_public_evidence_and_expired_reports_require_reacquisition():
    s, ledger = scene(blocked={9}), SensorLedger(resend_s=3.0)
    sent(ledger, s, 'r1', [8, 9], 2, 10.0)
    assert ledger.select(s, [8, 9], moving=False) == []        # in flight
    ledger.confirm(feedback(s, [], version=3))                # unrelated map advance is not ACK
    assert 'r1' in ledger.pending
    ledger.expire(13.0)
    assert 'r1' in ledger.unconfirmed and ledger.reported == set()
    assert ledger.select(s, [8, 9], moving=True) == [8, 9]     # needs new acquisition
    sent(ledger, s, 'r2', [8, 9], 3, 13.0)
    ledger.confirm(feedback(s, [8, 9], version=4))
    assert ledger.reported == {8, 9} and not ledger.pending
    assert ledger.select(s, [8, 9], moving=False) == []


def test_observation_values_use_truth_heights_and_obstacle_codes():
    heights, sigma, codes = observation_values(scene(blocked={3}), [2, 3], 0.25)
    assert heights == [2.0, 3.0] and sigma == [0.25, 0.25] and codes == [0, 100]


def test_scene_file_must_be_simulated_and_match_the_grid(tmp_path):
    path = tmp_path / 'scene.json'
    good = {'schema_version': SCENE_SCHEMA, 'source_kind': 'SIMULATED', 'rows': 8, 'cols': 8, 'blocked': [5]}
    path.write_text(json.dumps(good))
    assert scene_from_file(path, GRID, [0.0] * 64).blocked == {5}
    for change in ({'source_kind': 'MEASURED'}, {'rows': 9}, {'blocked': [64]},
                   {'schema_version': 'x'}, {'blocked': [True]}):
        path.write_text(json.dumps({**good, **change}))
        with pytest.raises(ValueError):
            scene_from_file(path, GRID, [0.0] * 64)


def test_deferred_flight_history_keeps_original_context_and_is_not_relabelled_on_landing():
    s, ledger = scene(blocked={9}), SensorLedger(defer=frozenset({'drone_1'}))
    for tick, cells in enumerate(([0, 1], [8, 9], [10]), 10):
        view, moving = ledger.view('drone_1', cells, moving=True, acquired_ns=tick * 1_000_000_000,
                                   base_version=2)
        assert ledger.select(s, view, moving) == []            # never interrupts the flight
    view, moving = ledger.view('drone_1', [2], moving=False, acquired_ns=20_000_000_000, base_version=3)
    assert ledger.select(s, view, moving) == [2]               # only actual landing footprint
    assert ledger.seen['drone_1'][9] == (11_000_000_000, 2)
    assert ledger.seen['drone_1'][2] == (20_000_000_000, 3)
    assert ledger.view('human_1', [9], True) == ([9], True)    # ground agents report hazards at once


def test_expired_deferred_report_requires_return_to_its_footprint():
    s, ledger = scene(), SensorLedger(resend_s=1.0, defer=frozenset({'drone_1'}))
    ledger.view('drone_1', [0, 1], moving=True, acquired_ns=1, base_version=3)
    view, moving = ledger.view('drone_1', [2], moving=False, acquired_ns=2, base_version=3)
    sent(ledger, s, 'r1', ledger.select(s, view, moving), 3, 0.0)
    ledger.expire(1.0)                                          # the map never advanced
    view, moving = ledger.view('drone_1', [], moving=False, acquired_ns=1_000_000_000, base_version=3)
    assert ledger.select(s, view, moving) == []                 # no replay of old sightings
    assert 'r1' in ledger.unconfirmed
