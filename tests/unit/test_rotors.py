"""Cosmetic drone rotor animation (mge_sim.rotors): web parity and import isolation."""
import ast
from pathlib import Path

import pytest

from mge_sim.rotors import AIRBORNE_M, ground_at, is_airborne, rotor_command, should_publish

SIM = Path(__file__).resolve().parents[2] / 'src/mge_sim/mge_sim'


def test_rotor_command_ramps_like_the_web():
    assert rotor_command(0.0, 'IDLE', 1.0) == 0.0
    assert rotor_command(0.0, 'MOVING', 1.0) == pytest.approx(0.25)        # about 4 s to full speed
    assert rotor_command(0.9, 'OBSERVING', 1.0) == 1.0
    assert rotor_command(1.0, 'IDLE', 1.0) == pytest.approx(0.8)           # about 5 s to stop
    assert rotor_command(0.1, 'IDLE', 1.0) == 0.0


def test_rotors_keep_spinning_while_an_idle_drone_is_airborne():
    """The web's target is `rotorsOn || airborne` (VehicleModel.tsx), not the mode alone."""
    assert rotor_command(1.0, 'IDLE', 1.0, airborne=True) == 1.0
    assert rotor_command(0.0, 'IDLE', 1.0, airborne=True) == pytest.approx(0.25)
    assert rotor_command(1.0, 'IDLE', 1.0, airborne=False) == pytest.approx(0.8)


def test_still_rotors_get_no_new_command():
    assert not should_publish(0.0, 0.0)
    assert should_publish(0.0, 0.25) and should_publish(0.2, 0.0) and should_publish(1.0, 1.0)


META = {'origin_x_m': -8.0, 'origin_y_m': -8.0, 'resolution_m': 4.0,
        'ground_z_m': [[0.0, 4.0, 8.0, 12.0], [1.0, 5.0, 9.0, 13.0],
                       [2.0, 6.0, 10.0, 14.0], [3.0, 7.0, 11.0, 15.0]]}


def test_ground_is_bilinear_between_cell_centres_and_clamped():
    assert ground_at(META, -6.0, -6.0) == 0.0                   # first cell centre
    assert ground_at(META, -4.0, -6.0) == pytest.approx(2.0)    # halfway along x
    assert ground_at(META, -2.0, -4.0) == pytest.approx(4.5)    # (row 0.5, col 1)
    assert ground_at(META, 100.0, 100.0) == 15.0                # clamped to the last centre
    assert ground_at(META, -100.0, -100.0) == 0.0
    assert ground_at({'resolution_m': 4.0}, 0.0, 0.0) is None   # world.json before ground_z_m


def test_airborne_uses_the_drawn_height_above_ground():
    assert not is_airborne(META, (-6.0, -6.0, AIRBORNE_M))     # at the threshold: on the ground
    assert is_airborne(META, (-6.0, -6.0, AIRBORNE_M + 0.01))
    assert not is_airborne({'resolution_m': 4.0}, (0.0, 0.0, 50.0))   # unknown ground: mode decides


def imported_modules(path):
    tree = ast.parse(path.read_text(encoding='utf-8'))
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names |= {a.name for a in node.names}
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module)
    return names


def test_mirror_and_rotors_do_not_load_the_world_generator():
    """gz_mirror must start without numpy/scipy or mge_sim.gz_world (PR #51 review)."""
    heavy = {'numpy', 'scipy', 'scipy.ndimage', 'mge_sim.gz_world'}
    assert not imported_modules(SIM / 'gz_mirror.py') & heavy
    assert imported_modules(SIM / 'rotors.py') <= {'math'}
