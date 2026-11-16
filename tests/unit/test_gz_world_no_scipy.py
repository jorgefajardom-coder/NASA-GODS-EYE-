"""The Gazebo world modules (gz_world, gz_mirror) need numpy only: SciPy is not a dependency
of mge_sim, so they must import and build a world on a minimal install without it."""
import os
from pathlib import Path
import subprocess
import sys

import pytest

GRID = (-64.0, -64.0, 4.0, 32, 32)
ROOT = Path(__file__).resolve().parents[2]


def _env():
    paths = [str(ROOT / 'src' / 'mge_sim'), os.environ.get('PYTHONPATH', '')]
    return {**os.environ, 'PYTHONPATH': os.pathsep.join(p for p in paths if p)}


def test_gz_world_imports_and_builds_without_scipy(tmp_path):
    code = ("import sys; sys.modules['scipy'] = None\n"
            "import numpy as np\n"
            "from mge_sim.gz_world import build_world\n"
            f"build_world(r'{tmp_path}', {GRID!r}, np.full((32, 32), -2570.0), [5], "
            "[('drone_1', 'DRONE', -10.0, -14.0, -2568.0)])\n"
            "assert 'scipy' not in [m.split('.')[0] for m in sys.modules if sys.modules[m] is not None]\n")
    run = subprocess.run([sys.executable, '-c', code], cwd=ROOT, capture_output=True, text=True,
                         env=_env())
    assert run.returncode == 0, run.stderr
    assert (tmp_path / 'world.sdf').exists()


def test_no_mge_sim_module_imports_scipy():
    for path in (ROOT / 'src' / 'mge_sim' / 'mge_sim').glob('*.py'):
        text = path.read_text(encoding='utf-8')
        assert 'import scipy' not in text and 'from scipy' not in text, path.name


def test_gz_mirror_imports_without_scipy():
    pytest.importorskip('rclpy')
    pytest.importorskip('mge_interfaces')
    code = "import sys; sys.modules['scipy'] = None\nimport mge_sim.gz_mirror\n"
    run = subprocess.run([sys.executable, '-c', code], cwd=ROOT, capture_output=True, text=True, env=_env())
    assert run.returncode == 0, run.stderr


def test_linear_resample_matches_the_former_scipy_heights():
    """The heightmap and ground heights (order 1, edges repeated) are unchanged by the port."""
    ndimage = pytest.importorskip('scipy.ndimage')
    import numpy as np
    from mge_sim.gz_world import HEIGHTMAP_SIZE, centre_lattice, resample
    rng = np.random.default_rng(3)
    h = rng.normal(-2570.0, 3.0, (32, 32))
    t = np.linspace(0.0, 1.0, HEIGHTMAP_SIZE)
    yy, xx = (1.0 - t)[:, None] * 32, t[None, :] * 32
    coords = np.array([np.broadcast_to(yy, (129, 129)), np.broadcast_to(xx, (129, 129))])
    assert np.allclose(centre_lattice(h, HEIGHTMAP_SIZE),
                       ndimage.map_coordinates(h, coords, order=1, mode='nearest'), atol=1e-9)
    pts = rng.uniform(-3.0, 35.0, (2, 50))
    assert np.allclose([resample(h, [i], [j])[0, 0] for i, j in pts.T],
                       ndimage.map_coordinates(h, pts, order=1, mode='nearest'), atol=1e-9)


def test_cubic_resample_is_exact_on_samples_and_wraps():
    import numpy as np
    from mge_sim.gz_world import fractal_noise, resample
    a = np.arange(20.0).reshape(4, 5)
    assert np.allclose(resample(a, [0, 1, 2, 3], [0, 1, 2, 3, 4], order=3), a)
    assert np.allclose(resample(a, [0.5], [2.0], order=3, wrap=True)[0, 0],
                       (-a[3, 2] + 9 * a[0, 2] + 9 * a[1, 2] - a[2, 2]) / 16)
    n = fractal_noise(64, 11)
    assert n.shape == (64, 64) and n.min() == 0.0 and n.max() == 1.0
