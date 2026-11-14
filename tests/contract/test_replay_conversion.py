"""Offline contract tests; the pinned source recording is entirely MOCK."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path

import pytest

from mge_gateway.contract_replay import (
    GEOMETRY, PUBLIC_RASTER_SCHEMA, ReplayContractError, read_package,
    to_viewer, validate_package, write_package,
)

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "replay"


@pytest.fixture
def package():
    return read_package(FIXTURES / "mock-vertical-001")


def test_source_recording_hashes():
    provenance = json.loads((FIXTURES / "provenance.json").read_text(encoding="utf-8"))
    assert provenance["source_commit"] == "d28f3e23f268d50c6c55f2b1f85a1cadbe9281ed"
    for name, expected in provenance["files"].items():
        actual = hashlib.sha256((FIXTURES / "mock-vertical-001" / name).read_bytes()).hexdigest()
        assert actual == expected["sha256"]


def test_recorded_mock_converts_without_fabricating_rasters(package):
    result = to_viewer(*package)
    assert result["status"] == "NOT_READY"
    assert result["reason_code"] == "PUBLIC_RASTERS_REQUIRED"
    assert result["rasters"] is None
    assert result["manifest"]["mode"] == "REPLAY"
    assert result["manifest"]["source_mode"] == "MOCK"
    # recorded_from=LIVE was process terminology in the source. Preserve it,
    # but never promote the mock physics to validated LIVE.
    assert result["manifest"]["recorded_from"] == "LIVE"
    assert result["manifest"]["clock_source"] == "system"
    assert result["manifest"]["title"].startswith("REPLAY / MOCK")
    assert len(result["timeline"]["frames"]) == 5
    assert len(result["timeline"]["events"]) == 9
    assert len(result["routes"]["routes"]) == 2


def test_conversion_preserves_coordinates_costs_versions_and_ids(package):
    manifest, records, snapshot = package
    result = to_viewer(*package)
    frame = result["timeline"]["frames"][2]
    original = [r["state"] for r in records if r["type"] == "state"][2]
    assert frame["mission_state"]["base"] == original["base"]
    assert frame["mission_state"]["primary_goal"] == original["primary_goal"]
    route = frame["mission_state"]["active_route"]
    for field in ("route_id", "request_id", "map_version_used", "status",
                  "outbound_path", "return_path", "travel_time_s",
                  "energy_est_wh", "oxygen_est_l", "reserve_wh"):
        assert route[field] == original["active_route"][field]
    assert "active_route" not in result["timeline"]["frames"][0]["mission_state"]
    assert [f["mission_state"]["map_version"] for f in result["timeline"]["frames"]] == [1, 1, 1, 2, 2]
    assert frame["timestamp_sim_s"] == [r for r in records if r["type"] == "state"][2]["timestamp_sim_s"] - manifest["time_start_sim_s"]


def public_rasters(manifest):
    meta = manifest["terrain_meta"]
    count = meta["rows"] * meta["cols"]
    # Explicit contract MOCK attachment, not measurements.
    return {
        "schema_version": PUBLIC_RASTER_SCHEMA,
        "run_id": manifest["run_id"], "dataset_id": meta["dataset_id"],
        "rows": meta["rows"], "cols": meta["cols"],
        "terrain_geometry": {k: meta[k] for k in GEOMETRY},
        "prior": [0.0] * count,
        "versions": {str(v): {"belief": [0.0] * count, "sigma": [1.0] * count, "observed": []}
                     for v in (1, 2)},
    }


def test_complete_public_attachment_matches_legacy_file_shapes(package):
    raster = public_rasters(package[0])
    result = to_viewer(*package, public_rasters=raster)
    assert result["status"] == "READY"  # serialization ready, not mission accepted
    assert result["manifest"]["schema_version"] == "mge-web-0.1-draft"
    assert result["manifest"]["reference_available"] is False
    assert set(result["manifest"]["files"]) == {"rasters", "timeline", "routes"}
    assert result["rasters"]["versions"]["1"]["belief"] == raster["versions"]["1"]["belief"]
    assert all(v is None for v in result["rasters"]["reference"])
    assert "reference" not in raster
    assert json.loads(json.dumps(result, allow_nan=False)) == result


def test_conversion_is_deterministic_and_does_not_mutate_input(package):
    original = deepcopy(package)
    assert to_viewer(*package) == to_viewer(*package)
    assert original == package


def test_offline_encode_decode_roundtrip_and_no_overwrite(package, tmp_path):
    target = tmp_path / package[0]["run_id"]
    write_package(target, *package)
    assert read_package(target) == package
    assert to_viewer(*read_package(target)) == to_viewer(*package)
    with pytest.raises(FileExistsError):
        write_package(target, *package)


@pytest.mark.parametrize("change,error", [
    (lambda p: p[0].update(schema_version="mge-web-0.1-draft"), "UNSUPPORTED_SCHEMA"),
    (lambda p: p[0].update(mode="LIVE"), "REPLAY_MODE_REQUIRED"),
    (lambda p: p[1][0].update(run_id="other-run"), "RUN_MISMATCH"),
    (lambda p: p[1][-1].update(timestamp_sim_s=0), "CLOCK_REGRESSION"),
    (lambda p: p[2].update(events=[]), "SNAPSHOT_EVENTS_MISMATCH"),
    (lambda p: p[0].update(files={"timeline": "../secret.json", "snapshot": "snapshot.json"}), "UNSUPPORTED_FILE_LAYOUT"),
    (lambda p: p[0].update(reference_dem=[1]), "EVALUATOR_REFERENCE_FORBIDDEN"),
])
def test_invalid_saved_packages_fail_closed(package, change, error):
    change(package)
    with pytest.raises(ReplayContractError, match=error):
        validate_package(*package)


def test_duplicate_event_conflict_rejected(package):
    events = [r for r in package[1] if r["type"] == "event"]
    events[1]["event"]["event_id"] = events[0]["event"]["event_id"]
    with pytest.raises(ReplayContractError, match="DUPLICATE_EVENT_ID"):
        validate_package(*package)


def test_stale_active_route_rejected(package):
    state = next(r["state"] for r in package[1] if r["type"] == "state" and r["state"]["route_id"])
    state["active_route"]["map_version_used"] = 0
    with pytest.raises(ReplayContractError, match="STALE_ROUTE"):
        validate_package(*package)


@pytest.mark.parametrize("change,error", [
    (lambda r: r.update(run_id="other"), "RASTER_IDENTITY_MISMATCH"),
    (lambda r: r["terrain_geometry"].update(resolution_m=4), "RASTER_GEOMETRY_MISMATCH"),
    (lambda r: r["versions"].pop("1"), "RASTER_VERSION_MISMATCH"),
    (lambda r: r["versions"]["1"].update(belief=[0]), "RASTER_LENGTH_MISMATCH"),
    (lambda r: r["versions"]["2"]["sigma"].__setitem__(0, -1), "INVALID_RASTER_VALUE"),
    (lambda r: r.update(reference=[0]), "EVALUATOR_REFERENCE_FORBIDDEN"),
])
def test_raster_mixing_or_reference_rejected(package, change, error):
    rasters = public_rasters(package[0])
    change(rasters)
    with pytest.raises(ReplayContractError, match=error):
        to_viewer(*package, public_rasters=rasters)


def test_nan_tokens_are_not_json(tmp_path, package):
    write_package(tmp_path / "run", *package)
    path = tmp_path / "run" / "manifest.json"
    path.write_text(path.read_text().replace('"1.0.0"', 'NaN', 1), encoding="utf-8")
    with pytest.raises(ReplayContractError, match="Non-standard JSON token"):
        read_package(path.parent)



def test_nonfinite_in_memory_values_rejected(package):
    package[0]["timestamp_sim_s"] = float("nan")
    with pytest.raises(ReplayContractError, match="NON_JSON_NUMBER"):
        validate_package(*package)


def test_bool_is_not_a_ros_uint(package):
    package[1][0]["map_version"] = True
    with pytest.raises(ReplayContractError, match="INVALID_MAP_VERSION"):
        validate_package(*package)
