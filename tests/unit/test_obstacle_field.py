"""SIMULATED obstacle fields: inside the window, passable, deterministic, detour-forcing."""
import pytest

from mge_sim.obstacle_field import flat_indices, generate_field, passage_exists

WINDOW = (8, 23, 8, 23)
BASE, GOAL = (12, 12), (21, 21)
AREA = {(r, c) for r in range(8, 24) for c in range(8, 24)}


@pytest.mark.parametrize('seed', range(25))
def test_field_stays_inside_the_window_and_keeps_a_passage(seed):
    f = generate_field(32, 32, WINDOW, BASE, GOAL, protected=[(12, 13), (13, 12)], seed=seed)
    assert f.blocked <= AREA
    assert passage_exists(BASE, GOAL, AREA - f.blocked)
    for cell in (BASE, GOAL, (12, 13), (13, 12)):
        r, c = cell
        assert not any((r + dr, c + dc) in f.blocked for dr in (-1, 0, 1) for dc in (-1, 0, 1))


def test_ridge_closes_the_direct_corridor_so_a_detour_is_needed():
    f = generate_field(32, 32, WINDOW, BASE, GOAL, seed=3, rock_clusters=0)
    diagonal = {(BASE[0] + k, BASE[1] + k) for k in range(GOAL[0] - BASE[0] + 1)}
    assert diagonal & f.blocked, 'the straight base-goal line must cross the ridge'
    assert f.gap and not set(f.gap) & f.blocked
    assert passage_exists(BASE, GOAL, AREA - f.blocked)


def test_same_seed_same_field_and_other_seeds_differ():
    a = generate_field(32, 32, WINDOW, BASE, GOAL, seed=11)
    b = generate_field(32, 32, WINDOW, BASE, GOAL, seed=11)
    c = generate_field(32, 32, WINDOW, BASE, GOAL, seed=12)
    assert a.blocked == b.blocked and a.blocked != c.blocked


def test_clusters_that_would_close_every_passage_are_dropped():
    f = generate_field(32, 32, WINDOW, BASE, GOAL, seed=5, rock_clusters=200, rock_radius=(2, 3))
    assert f.dropped > 0
    assert passage_exists(BASE, GOAL, AREA - f.blocked)


def test_invalid_windows_and_cells_are_rejected():
    with pytest.raises(ValueError):
        generate_field(32, 32, (8, 40, 8, 23), BASE, GOAL)
    with pytest.raises(ValueError):
        generate_field(32, 32, WINDOW, (2, 2), GOAL)


def test_flat_indices_are_row_major():
    assert flat_indices({(1, 2), (0, 31)}, 32) == [31, 34]
