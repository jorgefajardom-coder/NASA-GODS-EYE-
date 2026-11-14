"""Offline tests for the configurable region options of scripts/prepare_jezero_terrain.py.

Network-backed helpers (coverage query, window validation, package build) are not exercised here.
"""

import importlib.util
import json
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("prepare_jezero_terrain", ROOT / "scripts/prepare_jezero_terrain.py")
terrain = importlib.util.module_from_spec(spec)
spec.loader.exec_module(terrain)


@pytest.mark.parametrize("lat, lon, side, res", [
    (18.45, 77.45, 128.0, 4.0),
    (0.0, 0.0, 16.0, 4.0),
    (-89.9, 359.9, 2048.0, 4.0),
])
def test_valid_region_parameters_pass(lat, lon, side, res):
    terrain.validate_request_params(lat, lon, side_m=side, resolution_m=res)


@pytest.mark.parametrize("lat, lon, side, res", [
    (90.0, 77.45, 128.0, 4.0),        # pole excluded
    (18.45, 360.0, 128.0, 4.0),       # east longitude is [0, 360)
    (18.45, -1.0, 128.0, 4.0),
    (float("nan"), 77.45, 128.0, 4.0),
    (18.45, 77.45, 0.0, 4.0),
    (18.45, 77.45, 130.0, 4.0),       # not a whole number of cells
    (18.45, 77.45, 8.0, 4.0),         # fewer than 4 cells
    (18.45, 77.45, 4096.0, 4.0),      # more than 512 cells
])
def test_invalid_region_parameters_are_rejected(lat, lon, side, res):
    with pytest.raises(ValueError):
        terrain.validate_request_params(lat, lon, side_m=side, resolution_m=res)


def test_non_interactive_defaults_keep_the_control_region():
    assert terrain.request_region_params(interactive=False, latitude=None, longitude=None) == (18.45, 77.45, 128.0)
    assert terrain.request_region_params(
        interactive=False, latitude=18.5, longitude=77.4, side_m=256.0) == (18.5, 77.4, 256.0)


def test_scale_tiers_are_whole_grids():
    assert terrain.SCALE_TO_SIDE_M == {1: 128.0, 2: 256.0, 3: 512.0}
    for side in terrain.SCALE_TO_SIDE_M.values():
        terrain.validate_request_params(18.45, 77.45, side_m=side, resolution_m=terrain.DEFAULT_RESOLUTION_M)


def test_slope_limits_come_from_the_proposed_profiles():
    limits, status = terrain.load_slope_limits()
    profiles = json.loads((ROOT / "config/planner_profiles.proposed.json").read_text(encoding="utf-8"))
    expected = {p["agent_kind"]: float(p["max_slope_deg"]) for p in profiles["profiles"].values()}
    assert limits == expected
    assert status == profiles["status"]


def test_slope_limits_reject_conflicting_profiles(tmp_path):
    path = tmp_path / "profiles.json"
    path.write_text(json.dumps({"status": "x", "profiles": {
        "a": {"agent_kind": "rover", "max_slope_deg": 20.0},
        "b": {"agent_kind": "rover", "max_slope_deg": 15.0}}}), encoding="utf-8")
    with pytest.raises(ValueError):
        terrain.load_slope_limits(path)


def test_slope_screen_on_a_known_ramp():
    # 10 % ramp along x on a 4 m grid: slope = atan(0.1) = 5.71 degrees everywhere.
    x = np.arange(8, dtype=np.float32) * 4.0
    elevation = np.tile(0.1 * x, (8, 1))
    valid = np.ones_like(elevation, dtype=bool)
    valid[0, 0] = False
    elevation[0, 0] = np.nan
    summary = terrain.estimate_traversability_summary(
        elevation, valid, 4.0, slope_limits_deg={"human": 5.0, "rover": 6.0}, limits_status="test")
    assert summary["valid_fraction"] == round(63 / 64, 4)
    assert summary["admissible_fraction_by_kind"]["human"] == 0.0
    # NoData and the cells whose gradient touches it are never counted as admissible.
    assert 0.0 < summary["admissible_fraction_by_kind"]["rover"] < summary["valid_fraction"]
    assert summary["slope_limits_status"] == "test"
    assert "not certified" in summary["note"]


def test_terrain_yml_sync_reproduces_the_committed_configuration(tmp_path):
    manifest = json.loads((ROOT / "data/sample/manifest.json").read_text(encoding="utf-8"))
    provenance = json.loads((ROOT / "data/sample/provenance_details.json").read_text(encoding="utf-8"))
    origin = manifest["local_origin"]
    out = tmp_path / "terrain.yml"
    terrain.sync_terrain_yml(
        out,
        region_id=manifest["region_id"],
        latitude=origin["lat_planetocentric_deg"],
        longitude=origin["lon_east_deg"],
        side_m=manifest["rows"] * manifest["resolution_m"],
        resolution_m=manifest["resolution_m"],
        rows=manifest["rows"],
        cols=manifest["cols"],
        vertical_datum=manifest["vertical_datum"],
        control_points=provenance["control_points"],
    )
    assert out.read_text(encoding="utf-8") == (ROOT / "config/terrain.yml").read_text(encoding="utf-8")


def test_sync_refuses_a_non_default_sample_dir(tmp_path, monkeypatch):
    monkeypatch.setattr("sys.argv", [
        "prepare_jezero_terrain.py", "--sync-terrain-yml", "--no-interactive",
        "--sample-dir", str(tmp_path / "sample"), "--reference-dir", str(tmp_path / "reference")])
    with pytest.raises(SystemExit) as exc:
        terrain.main()
    assert exc.value.code == 2
