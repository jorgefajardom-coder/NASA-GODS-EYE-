"""NEW SIMULATED scene setup, not observations or live pose correction."""
from copy import deepcopy
from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest
import yaml

from mge_data.core import default_manifest_path, load_public_terrain
from mge_sim import initial_conditions
from mge_sim.initial_conditions import load_agents


ROOT = Path(__file__).resolve().parents[2]
JEZERO = ROOT / 'src/mge_bringup/config/agents_jezero.yaml'


def configuration(tmp_path, data):
    path = tmp_path / 'agents.yaml'
    path.write_text(yaml.safe_dump(data), encoding='utf-8')
    return path


def agent(**changes):
    return dict(id='drone_1', kind='DRONE', x_m=2.5, y_m=3.5,
                time_budget_s=600., energy_budget_wh=100., **changes)


def test_missing_altitude_is_never_a_zero_or_implicit_scene(tmp_path):
    with pytest.raises(ValueError, match='missing altitude is not zero'):
        load_agents(configuration(tmp_path, {'agents': [agent()]}))


@pytest.mark.parametrize('kind', ['HUMAN', 'ROVER', 'DRONE'])
def test_explicit_xyz_is_preserved_without_loading_any_surface(tmp_path, monkeypatch, kind):
    data = {'agents': [dict(agent(z_m=0.), kind=kind)]}
    monkeypatch.setattr(initial_conditions, '_scene_terrain', lambda _: pytest.fail('no implicit terrain lookup'))
    assert load_agents(configuration(tmp_path, data)) == data['agents']


@pytest.mark.parametrize('field,value', [('x_m', float('nan')), ('y_m', float('inf')),
                                      ('z_m', -float('inf')), ('z_m', True), ('z_m', '0')])
def test_nonfinite_or_untyped_positions_are_rejected(tmp_path, field, value):
    value = dict(agent(z_m=-20.), **{field: value})
    with pytest.raises(ValueError, match='explicit finite coordinate'):
        load_agents(configuration(tmp_path, {'agents': [value]}))


def test_public_scene_initializes_all_new_agents_in_same_datum_with_parked_drone():
    original = yaml.safe_load(JEZERO.read_text())
    snapshot = deepcopy(original)
    tile = load_public_terrain(default_manifest_path())
    agents = load_agents(JEZERO)
    assert yaml.safe_load(JEZERO.read_text()) == snapshot
    for value in agents:
        cell = tile.transform.enu_to_cell(value['x_m'], value['y_m'])
        assert value['z_m'] == float(tile.prior[cell])
        assert value['z_m'] < -2500.
    drone = next(a for a in agents if a['kind'] == 'DRONE')
    assert drone['z_m'] == -2571.231201171875
    assert not tile.observed_mask.any()  # Initialization creates no observations.


def test_explicit_scene_positions_are_checked_without_projection(tmp_path):
    data = yaml.safe_load(JEZERO.read_text())
    actual = load_agents(JEZERO)
    data['agents'] = actual
    assert load_agents(configuration(tmp_path, data)) == actual
    data['agents'][1]['z_m'] += 10.  # A flying pose is not the declared PARKED scene.
    unchanged = deepcopy(data)
    with pytest.raises(ValueError, match='explicit XYZ disagrees'):
        load_agents(configuration(tmp_path, data))
    assert data == unchanged


@pytest.mark.parametrize('field,value', [('phase', 'RECEIVED_TELEMETRY'), ('source_kind', 'OBSERVED'),
                                      ('height_source', 'BELIEF'), ('drone_state', 'FLYING'),
                                      ('vertical_datum', 'unrelated datum'), ('dataset_id', 'another_dataset'),
                                      ('prior_sha256', '0'*64)])
def test_scene_or_terrain_identity_cannot_be_inferred_or_changed(tmp_path, field, value):
    data = yaml.safe_load(JEZERO.read_text())
    data['initial_conditions'][field] = value
    with pytest.raises(ValueError):
        load_agents(configuration(tmp_path, data))


def test_nodata_and_outside_coverage_do_not_supply_initial_height(tmp_path, monkeypatch):
    data = yaml.safe_load(JEZERO.read_text())
    tile = load_public_terrain(default_manifest_path())
    cell = tile.transform.enu_to_cell(data['agents'][1]['x_m'], data['agents'][1]['y_m'])
    heights, mask = tile.prior.copy(), tile.nodata_mask.copy()
    heights[cell], mask[cell] = np.nan, True
    invalid = replace(tile, prior=heights, nodata_mask=mask)
    monkeypatch.setattr(initial_conditions, '_scene_terrain', lambda _: invalid)
    with pytest.raises(ValueError, match='no public scene height'):
        load_agents(configuration(tmp_path, data))
    data['agents'][1]['x_m'] = 10000.
    with pytest.raises(ValueError, match='outside grid bounds'):
        load_agents(configuration(tmp_path, data))


def test_flat_mock_configuration_has_explicit_xyz_for_every_agent():
    agents = load_agents(ROOT / 'src/mge_bringup/config/agents.yaml')
    assert all(a['z_m'] == 0. for a in agents)
