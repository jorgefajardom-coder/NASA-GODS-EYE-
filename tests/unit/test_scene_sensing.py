"""SIMULATED scene sensing: footprint, reporting policy and delivery bookkeeping."""
import json

import pytest

from mge_sim.scene_sensing import (
    SCENE_SCHEMA, Scene, SensorLedger, footprint, observation_values, scene_from_file,
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


def test_reports_count_once_the_map_advances_and_are_resent_otherwise():
    s, ledger = scene(blocked={9}), SensorLedger(resend_s=3.0)
    ledger.sent('r1', [8, 9], base_version=2, now_s=10.0)
    assert ledger.select(s, [8, 9], moving=False) == []        # in flight
    ledger.confirm(2)
    assert 'r1' in ledger.pending
    ledger.expire(13.0)
    assert ledger.select(s, [8, 9], moving=True) == [8, 9]     # lost: sent again
    ledger.sent('r2', [8, 9], base_version=2, now_s=13.0)
    ledger.confirm(3)
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


def test_a_deferring_drone_remembers_its_flight_and_reports_on_landing():
    s, ledger = scene(blocked={9}), SensorLedger(defer=frozenset({'drone_1'}))
    for cells in ([0, 1], [8, 9], [10]):
        view, moving = ledger.view('drone_1', cells, moving=True)
        assert ledger.select(s, view, moving) == []            # never interrupts the flight
    view, moving = ledger.view('drone_1', [2], moving=False)
    assert ledger.select(s, view, moving) == [0, 1, 2, 8, 9, 10]
    assert ledger.view('human_1', [9], True) == ([9], True)    # ground agents report hazards at once


def test_a_lost_deferred_report_is_sent_again():
    s, ledger = scene(), SensorLedger(resend_s=1.0, defer=frozenset({'drone_1'}))
    ledger.view('drone_1', [0, 1], moving=True)
    view, moving = ledger.view('drone_1', [2], moving=False)
    ledger.sent('r1', ledger.select(s, view, moving), base_version=3, now_s=0.0)
    ledger.expire(1.0)                                          # the map never advanced
    view, moving = ledger.view('drone_1', [], moving=False)
    assert ledger.select(s, view, moving) == [0, 1, 2]
