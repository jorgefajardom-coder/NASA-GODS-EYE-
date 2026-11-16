"""Private import isolation and evidence arithmetic; no scientific acceptance."""

import hashlib
import json
from pathlib import Path
import sys
import types

import pytest

from mge_mission import conformance
from mge_mission.models import OXYGEN_L_PER_WH, load_profiles

ROOT = Path(__file__).resolve().parents[2]
REVISION = "34c515b6b86f73336844e8b3614c70b144574ec3"
REPOSITORY = "https://github.com/jorgefajardom-coder/NASA-GODS-EYE-.git"


@pytest.fixture
def profiles():
    return load_profiles(ROOT / "config/science_profiles.proposed.json")


@pytest.fixture
def snapshot(tmp_path):
    root = tmp_path / "published-snapshot"
    package = root / "src/mge_planning/mge_planning"
    package.mkdir(parents=True)
    (package / "__init__.py").write_text("raise RuntimeError('initializer must not run')\n")
    (package / "core.py").write_text("from dataclasses import dataclass\n@dataclass\nclass Record:\n    value: int\n")
    files = {p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
             for p in package.glob("*.py")}
    manifest = {"schema_version": "1.0.0", "repository": REPOSITORY,
                "revision": REVISION, "package_root": package.relative_to(root).as_posix(),
                "files": files}
    (root / "source_manifest.json").write_text(json.dumps(manifest))
    return root, package


def test_verified_source_requires_explicit_provenance_not_a_working_checkout(tmp_path):
    package = tmp_path / "working-checkout"
    package.mkdir()
    with pytest.raises(ValueError, match="source_manifest"):
        conformance._verified_source(package, REVISION)


def test_source_manifest_pins_revision_and_all_executable_files(snapshot):
    root, package = snapshot
    verified, provenance = conformance._verified_source(package, REVISION)
    assert verified == package
    assert provenance["revision"] == REVISION
    assert len(provenance["package_python_files"]) == 2
    with pytest.raises(ValueError, match="revision"):
        conformance._verified_source(package, "a" * 40)
    (package / "core.py").write_text("tampered = True\n")
    with pytest.raises(ValueError, match="hash mismatch"):
        conformance._verified_source(package, REVISION)


def test_unmanifested_python_file_is_not_executed(snapshot):
    _, package = snapshot
    (package / "extra.py").write_text("raise RuntimeError('not trusted')\n")
    with pytest.raises(ValueError, match="every planner"):
        conformance._verified_source(package, REVISION)


def test_snapshot_root_and_declared_package_must_match(snapshot):
    root, package = snapshot
    manifest_path = root / "source_manifest.json"
    manifest = json.loads(manifest_path.read_text())
    manifest["package_root"] = "../outside"
    manifest_path.write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match="escapes"):
        conformance._verified_source(package, REVISION)


def test_manifest_artifact_paths_cannot_escape(snapshot):
    root, package = snapshot
    manifest_path = root / "source_manifest.json"
    manifest = json.loads(manifest_path.read_text())
    manifest["files"]["../outside.py"] = "0" * 64
    manifest_path.write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match="escapes"):
        conformance._verified_source(package, REVISION)


def test_package_symlink_escape_is_rejected(snapshot, tmp_path):
    _, package = snapshot
    link = tmp_path / "planner-link"
    try:
        link.symlink_to(package, target_is_directory=True)
    except OSError:
        pytest.skip("Host does not permit creating symlink fixtures")
    with pytest.raises(ValueError, match="symlinks"):
        conformance._verified_source(link, REVISION)


def test_import_registers_dataclass_namespace_without_public_module_pollution(snapshot, monkeypatch):
    _, package = snapshot
    sentinel = types.ModuleType("mge_planning")
    monkeypatch.setitem(sys.modules, "mge_planning", sentinel)
    prior_path = list(sys.path)
    prior_aliases = {name for name in sys.modules if name.startswith("_mge_conformance_")}
    with conformance._isolated_core(package) as core:
        assert core.Record(7).value == 7
        assert core.Record.__module__ in sys.modules
        assert sys.modules["mge_planning"] is sentinel
    assert sys.path == prior_path
    assert sys.modules["mge_planning"] is sentinel
    assert {name for name in sys.modules if name.startswith("_mge_conformance_")} == prior_aliases
    assert not (package / "__pycache__").exists()


def test_private_names_are_removed_after_import_failure(snapshot):
    _, package = snapshot
    (package / "core.py").write_text("raise RuntimeError('failed import')\n")
    aliases = {name for name in sys.modules if name.startswith("_mge_conformance_")}
    with pytest.raises(RuntimeError, match="failed import"):
        with conformance._isolated_core(package):
            pass
    assert {name for name in sys.modules if name.startswith("_mge_conformance_")} == aliases


def test_missing_optional_dependencies_produce_not_run_not_success(snapshot, profiles, monkeypatch):
    _, package = snapshot
    def missing():
        raise ModuleNotFoundError("No module named numpy")
    monkeypatch.setattr(conformance, "_load_dependencies", missing)
    result = conformance.run_conformance(package, profiles, REVISION, backend="legacy")
    assert result["classification"] == "MODEL_CONFORMANCE"
    assert result["status"] == "NOT_RUN"
    assert result["reason_code"] == "DEPENDENCIES_UNAVAILABLE"
    assert result["cases"] == []
    assert result["authorization"] == "BLOCKED"
    assert result["scientific_approval_changed"] is False
    assert {p["approval_status"] for p in result["science"]["profiles"].values()} == {"proposed"}
    json.dumps(result, allow_nan=False)


def human_result(profile, *, energy_extra=0, reserve_extra=0):
    travel_time = 4 / .8333
    time = travel_time + 20 + 15
    energy = (417.70 * travel_time + 461.17 * 20 + 358.08 * 15) / 3600
    oxygen = energy * OXYGEN_L_PER_WH
    budget = {"time_s": 1000, "energy_wh": 100, "oxygen_l": 100}
    decision = {
        "outbound_path": [(0, 0, 0), (1, 0, 0), (2, 0, 0)],
        "return_path": [(2, 0, 0), (1, 0, 0), (0, 0, 0)],
        "travel_time_s": time, "energy_est_wh": energy + energy_extra,
        "oxygen_est_l": oxygen, "reserve_time_s": budget["time_s"] - time,
        "reserve_wh": budget["energy_wh"] - energy + reserve_extra,
        "reserve_oxygen_l": budget["oxygen_l"] - oxygen}
    return decision, budget, time, energy, oxygen


def test_audit_uses_actual_returned_paths_and_charges_service_wait_once(profiles):
    profile = profiles["human_1"]
    decision, budget, time, energy, oxygen = human_result(profile)
    audit = conformance.audit_returned_paths(profile, decision, service_activity="sample",
                                            service_time_s=20, wait_time_s=15, budget=budget)
    assert audit["agreement"] is True
    assert audit["science_costs"] == pytest.approx({"time_s": time, "energy_wh": energy, "oxygen_l": oxygen})
    assert audit["cost_deltas_planner_minus_science"] == pytest.approx({"time_s": 0, "energy_wh": 0, "oxygen_l": 0})
    assert audit["science_reserves"]["energy_wh"] == pytest.approx(100 - energy)


def test_audit_keeps_cost_and_reserve_disagreements_visible(profiles):
    profile = profiles["human_1"]
    decision, budget, _, _, _ = human_result(profile, energy_extra=.5, reserve_extra=-.5)
    audit = conformance.audit_returned_paths(profile, decision, service_activity="sample",
                                            service_time_s=20, wait_time_s=15, budget=budget)
    assert audit["agreement"] is False
    assert audit["cost_deltas_planner_minus_science"]["energy_wh"] == pytest.approx(.5)
    assert audit["reserve_deltas_planner_minus_science"]["energy_wh"] == pytest.approx(-.5)
    assert audit["costs_within_tolerance"]["energy_wh"] is False


def test_missing_return_and_disconnected_paths_are_not_zero_cost_successes(profiles):
    profile = profiles["human_1"]
    decision, _, _, _, _ = human_result(profile)
    decision["return_path"] = []
    with pytest.raises(ValueError, match="both returned paths"):
        conformance.audit_returned_paths(profile, decision, service_activity="sample", service_time_s=20)
    decision["return_path"] = [(99, 0, 0), (0, 0, 0)]
    with pytest.raises(ValueError, match="connect"):
        conformance.audit_returned_paths(profile, decision, service_activity="sample", service_time_s=20)


def test_robot_oxygen_is_unavailable_and_never_changed_to_zero(profiles):
    rover = profiles["rover_1"]
    time = 4 / (.04 * .9)
    energy = (100 * time + (1025 * 3.71 * .05) * 4 / (.35 * .9)) / 3600
    decision = {"outbound_path": [(0, 0, 0), (2, 0, 0)], "return_path": [(2, 0, 0), (0, 0, 0)],
                "travel_time_s": time, "energy_est_wh": energy, "oxygen_est_l": None,
                "reserve_time_s": 1000 - time, "reserve_wh": 100 - energy, "reserve_oxygen_l": None}
    audit = conformance.audit_returned_paths(rover, decision, service_activity="inspect", service_time_s=0,
                                            budget={"time_s": 1000, "energy_wh": 100, "oxygen_l": None})
    assert audit["agreement"] is True
    assert audit["science_costs"]["oxygen_l"] is None
    assert audit["cost_deltas_planner_minus_science"]["oxygen_l"] is None
    decision["oxygen_est_l"] = 0
    with pytest.raises(ValueError, match="nonhuman"):
        conformance.audit_returned_paths(rover, decision, service_activity="inspect", service_time_s=0)


@pytest.mark.parametrize("bad", [float("nan"), float("inf"), True, -1])
def test_invalid_tolerance_cannot_make_disagreement_pass(profiles, bad):
    decision, _, _, _, _ = human_result(profiles["human_1"])
    with pytest.raises(ValueError, match="tolerance"):
        conformance.audit_returned_paths(profiles["human_1"], decision, service_activity="sample",
                                        service_time_s=20, absolute_tolerance=bad)


def test_all_seven_cases_have_public_synthetic_inputs_and_explicit_services(profiles):
    cases = conformance._cases(profiles)
    assert [case[0] for case in cases] == [
        "human_flat", "human_slope", "human_service_wait", "rover_flat",
        "rover_slope", "rover_service_wait", "drone_observe"]
    assert cases[2][4:] == (20, 15)
    assert cases[5][4:] == (20, 15)
    assert cases[6][3:] == ("observe", 30, 0)


def test_actual_published_snapshot_probe_when_explicit_snapshot_is_available(profiles):
    package = ROOT / "tmp/planner-peer/src/mge_planning/mge_planning"
    if not package.exists():
        pytest.skip("Explicit published planner snapshot is not materialized")
    pytest.importorskip("numpy")
    pytest.importorskip("scipy")
    before = {name for name in sys.modules if name.startswith("_mge_conformance_")}
    result = conformance.run_conformance(package, profiles, REVISION, backend="legacy")
    assert result["status"] == "COMPLETED"
    assert result["summary"] == {"AGREE": 1, "DISAGREE": 6, "NOT_FEASIBLE": 0, "ERROR": 0}
    assert result["authorization"] == "BLOCKED"
    assert next(c for c in result["cases"] if c["case_id"] == "rover_flat")["status"] == "AGREE"
    human_slope = next(c for c in result["cases"] if c["case_id"] == "human_slope")
    assert human_slope["audit"]["cost_deltas_planner_minus_science"]["energy_wh"] < 0
    assert {name for name in sys.modules if name.startswith("_mge_conformance_")} == before
    json.dumps(result, allow_nan=False)


def test_current_scientific_search_matches_all_seven_cases_and_preserves_legacy(tmp_path, profiles):
    """Execute the service's real facade; keep the old mismatch reproducible."""
    pytest.importorskip("numpy")
    pytest.importorskip("scipy")
    root = tmp_path / "candidate-snapshot"
    package = root / "src/mge_planning/mge_planning"
    package.mkdir(parents=True)
    original = ROOT / "src/mge_planning/mge_planning"
    for path in original.glob("*.py"):
        (package / path.name).write_bytes(path.read_bytes())
    fixture_revision = "e" * 40
    files = {p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
             for p in package.glob("*.py")}
    (root / "source_manifest.json").write_text(json.dumps({
        "schema_version": "1.0.0", "repository": REPOSITORY,
        "revision": fixture_revision, "package_root": package.relative_to(root).as_posix(),
        "files": files, "classification": "UNIT_TEST_SOURCE_SNAPSHOT_NOT_PUBLISHED_REVISION"}), encoding="utf-8")
    current = conformance.run_conformance(package, profiles, fixture_revision)
    assert current["cost_backend"] == "scientific"
    assert current["summary"] == {"AGREE": 7, "DISAGREE": 0, "NOT_FEASIBLE": 0, "ERROR": 0}
    assert current["authorization"] == "BLOCKED"
    assert current["scientific_approval_changed"] is False
    legacy = conformance.run_conformance(package, profiles, fixture_revision, backend="legacy")
    assert legacy["summary"] == {"AGREE": 1, "DISAGREE": 6, "NOT_FEASIBLE": 0, "ERROR": 0}
    assert legacy["authorization"] == "BLOCKED"
