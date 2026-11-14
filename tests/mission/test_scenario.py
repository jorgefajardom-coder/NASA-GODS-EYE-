"""Public data consumer diagnostics; configuration checks are not missions."""

import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys

import numpy as np
import pytest
import yaml

from mge_mission.scenario import diagnose

ROOT = Path(__file__).resolve().parents[2]
PROFILES = ROOT / "config/science_profiles.proposed.json"
MISSION = ROOT / "config/mission.yaml"
MANIFEST = ROOT / "data/sample/manifest.json"


def codes(report):
    return {entry["code"] for entry in report["findings"]}


@pytest.fixture
def public_package(tmp_path):
    target = tmp_path / "public"
    target.mkdir()
    for filename in ("manifest.json", "terrain.npz", "mola_regional_context.npz", "provenance_details.json"):
        shutil.copyfile(MANIFEST.parent / filename, target / filename)
    return target / "manifest.json"


def check(manifest=MANIFEST, mission=MISSION, profiles=PROFILES):
    return diagnose(manifest, profiles, mission, run_id="scenario-consumer-test")


def rewrite_archive(manifest, transform):
    archive = manifest.parent / "terrain.npz"
    with np.load(archive, allow_pickle=False) as data:
        arrays = {key: data[key].copy() for key in data.files}
    transform(arrays)
    np.savez_compressed(archive, **arrays)
    document = json.loads(manifest.read_text())
    next(x for x in document["sources"] if x["role"] == "prior")["sha256"] = hashlib.sha256(archive.read_bytes()).hexdigest()
    manifest.write_text(json.dumps(document), encoding="utf-8")


def test_main_public_loader_consumer_preserves_native_resolution_and_unknowns():
    report = check()
    assert report["dataset_status"] == "PUBLIC_PACKAGE_VALIDATED"
    assert report["status"] == "NOT_READY"
    assert not report["findings"]
    terrain = report["terrain"]
    assert terrain["grid_resolution_m"] == 4
    assert terrain["prior_native_resolution_m"] == 20
    assert terrain["observed_cells"] == 0
    assert terrain["unobserved_cells"] == terrain["valid_cells"]
    assert terrain["execution_traversability_assumed"] is False
    assert {"base_enu_m", "primary_goal_enu_m", "return_tolerance_m", "budgets",
            "approval_evidence.dataset", "approved_agent_profiles", "primary_service_time_s",
            "primary_activity"} <= set(report["missing_inputs"])
    assert report["candidate_configuration"]["dataset_id"] == "jezero_mvp"
    assert report["candidate_configuration"]["mission_inputs"]["base_enu_m"] is None
    assert report["mission_execution_authorized"] is False
    json.dumps(report, allow_nan=False)


def test_tampered_hash_is_not_repaired_or_accepted(public_package):
    data = json.loads(public_package.read_text())
    data["sources"][0]["sha256"] = "0" * 64
    public_package.write_text(json.dumps(data), encoding="utf-8")
    before = public_package.read_bytes()
    report = check(public_package)
    assert codes(report) == {"PUBLIC_PACKAGE_INVALID"}
    assert report["dataset_status"] == "NOT_READY"
    assert "SHA-256 mismatch" in report["findings"][0]["detail"]
    assert public_package.read_bytes() == before
    assert report["inputs_sha256"]["manifest"] == hashlib.sha256(before).hexdigest()


@pytest.mark.parametrize("change", [
    lambda arrays: arrays.pop("sigma"),
    lambda arrays: arrays["sigma"].fill(-1),
    lambda arrays: arrays.update(reference=np.zeros((32, 32))),
    lambda arrays: arrays.update(nodata_mask=np.ones((32, 32), dtype=bool)),
    lambda arrays: arrays.update(row_orientation=np.array("north_to_south")),
])
def test_missing_uncertainty_masks_reference_and_geometry_fail(public_package, change):
    rewrite_archive(public_package, change)
    report = check(public_package)
    assert codes(report) == {"PUBLIC_PACKAGE_INVALID"}
    assert report["dataset_status"] == "NOT_READY"
    assert not report["mission_execution_authorized"]


def test_reference_named_file_is_rejected_without_opening_it(public_package):
    (public_package.parent / "reference.json").write_text("THIS IS NOT JSON AND MUST NOT BE OPENED")
    report = check(public_package)
    assert codes(report) == {"PUBLIC_PACKAGE_INVALID"}
    assert "Evaluator-named content" in report["findings"][0]["detail"]


def test_controls_are_required_even_if_loader_can_omit_them(public_package):
    (public_package.parent / "provenance_details.json").unlink()
    report = check(public_package)
    assert codes(report) == {"PUBLIC_PACKAGE_INVALID"}
    assert "three verified public control points" in report["findings"][0]["detail"]


def test_continuous_goal_is_not_snapped_and_bad_service_is_rejected(tmp_path):
    document = yaml.safe_load(MISSION.read_text())
    document.update(base_enu_m=[-62, -62, -2570.634765625], primary_goal_enu_m=[0, 0, 0],
                    primary_service_time_s=-1, primary_activity="unregistered-activity")
    mission = tmp_path / "mission.yaml"
    mission.write_text(yaml.safe_dump(document), encoding="utf-8")
    report = check(mission=mission)
    assert {"NON_CELL_CENTER", "INVALID_SERVICE_DURATION", "INVALID_SERVICE_ACTIVITY"} <= codes(report)
    assert report["candidate_configuration"]["mission_inputs"]["primary_goal_enu_m"] == [0, 0, 0]


def test_symlinked_public_archive_cannot_escape_package(public_package, tmp_path):
    archive = public_package.parent / "terrain.npz"
    outside = tmp_path / "outside.npz"
    shutil.copyfile(archive, outside)
    archive.unlink()
    try:
        archive.symlink_to(outside)
    except OSError as error:
        pytest.skip(f"Host does not allow symlink fixture: {error}")
    report = check(public_package)
    assert codes(report) == {"PUBLIC_PACKAGE_INVALID"}
    assert "confined" in report["findings"][0]["detail"]


def test_candidate_invalid_values_do_not_create_authority(tmp_path):
    document = yaml.safe_load(MISSION.read_text())
    document.update(dataset_id="other-grid", base_enu_m=[1000, 1000, 0],
                    primary_goal_enu_m=[0, 0, 0], return_tolerance_m=-1,
                    budgets={"human_1": dict(time_s=1, energy_wh=1, oxygen_l=1,
                              reserve_time_s=2, reserve_wh=0, reserve_oxygen_l=0)})
    mission = tmp_path / "mission.yaml"
    mission.write_text(yaml.safe_dump(document), encoding="utf-8")
    report = check(mission=mission)
    assert {"DATASET_ID_MISMATCH", "COORDINATE_OUTSIDE_PUBLIC_TERRAIN", "INVALID_TOLERANCE",
            "RESERVE_EXCEEDS_CAPACITY"} <= codes(report)
    assert not report["mission_execution_authorized"]


def test_nan_mission_configuration_becomes_a_finite_diagnostic(tmp_path):
    mission = tmp_path / "mission.yaml"
    mission.write_text("frame_id: map\nreturn_tolerance_m: .nan\n", encoding="utf-8")
    report = check(mission=mission)
    assert "MISSION_INVALID" in codes(report)
    json.dumps(report, allow_nan=False)


def test_bad_primary_agent_type_and_yaml_syntax_are_reported(tmp_path):
    mission = tmp_path / "mission.yaml"
    mission.write_text("frame_id: map\nprimary_agent_id: [human_1]\nbudgets: {}\n", encoding="utf-8")
    assert "INVALID_PRIMARY_AGENT" in codes(check(mission=mission))
    mission.write_text("frame_id: [\n", encoding="utf-8")
    assert "MISSION_INVALID" in codes(check(mission=mission))


def test_cli_exports_exclusively_and_reports_not_ready(tmp_path):
    target = tmp_path / "diagnostic"
    command = [sys.executable, str(ROOT / "scripts/check_mission_scenario.py"),
               "--run-id", "scenario-software-test", "--output-dir", str(target)]
    result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
    assert result.returncode == 2, result.stderr
    report = json.loads((target / "scenario_diagnostic.json").read_text())
    candidate = json.loads((target / "mission_candidate.json").read_text())
    assert report["kind"] == "SCENARIO_DIAGNOSTIC"
    assert report["dataset_status"] == "PUBLIC_PACKAGE_VALIDATED"
    assert candidate["bindings_sha256"]["manifest"] == hashlib.sha256(MANIFEST.read_bytes()).hexdigest()
    before = (target / "scenario_diagnostic.json").read_bytes()
    assert subprocess.run(command, cwd=ROOT, capture_output=True).returncode != 0
    assert (target / "scenario_diagnostic.json").read_bytes() == before
