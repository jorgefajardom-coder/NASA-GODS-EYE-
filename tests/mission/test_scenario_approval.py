"""Approval scope and tamper tests; no execution evidence is generated."""

import hashlib
import json
from pathlib import Path
import shutil

import pytest
import yaml

from mge_mission import scenario

ROOT = Path(__file__).resolve().parents[2]
EXPERIMENT = ROOT / "config/mission_jezero.experimental.yaml"
RECEIPT = ROOT / "docs/science_approvals/jezero_scenario_20261114.json"
PROFILES = ROOT / "config/science_profiles.proposed.json"
MANIFEST = ROOT / "data/sample/manifest.json"


def check(path=EXPERIMENT):
    return scenario.diagnose(MANIFEST, PROFILES, path, run_id="scenario-approval-software-check")


def test_approval_is_scoped_and_six_runtime_requirements_stay_pending():
    report = check()
    assert report["scenario_approval"]["status"] == "APPROVED_EXPERIMENTAL_VALUES"
    assert report["scenario_approval"]["decision_ids"] == [f"JZ-P{i:02d}" for i in range(1, 8)]
    for name in ("profiles_approved", "cost_agreement_approved", "execution_evidence_approved", "operational_authorization"):
        assert report["scenario_approval"][name] is False
    assert report["status"] == "NOT_READY"
    assert not report["scientific_approval"]
    assert not report["mission_execution_authorized"]
    assert len(report["missing_inputs"]) == 6
    assert report["terrain"]["observed_cells"] == 0
    assert report["terrain"]["unobserved_cells"] == 1024
    assert set(report["profile_approval_states"].values()) == {"proposed"}
    config = yaml.safe_load(EXPERIMENT.read_text(encoding="utf-8"))
    assert config["status"] == "pending_integration"
    assert config["approval_evidence"] == {}
    assert config["optional_tasks"] == []
    assert report["findings"] == []


@pytest.fixture
def copied_approval(tmp_path, monkeypatch):
    for path in (EXPERIMENT, RECEIPT, ROOT / "config/mission_jezero.proposed.yaml"):
        target = tmp_path / path.relative_to(ROOT)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, target)
    monkeypatch.setattr(scenario, "REPOSITORY_ROOT", tmp_path.resolve())
    return tmp_path, tmp_path / EXPERIMENT.relative_to(ROOT), tmp_path / RECEIPT.relative_to(ROOT)


def rewrite_yaml(path, data):
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")


def test_numeric_drift_is_not_covered_by_old_approval(copied_approval):
    _, config, _ = copied_approval
    data = yaml.safe_load(config.read_text(encoding="utf-8"))
    data["budgets"]["human_1"]["energy_wh"] += 1
    rewrite_yaml(config, data)
    report = check(config)
    assert report["scenario_approval"]["status"] == "INVALID"
    assert {x["code"] for x in report["findings"]} == {"EXPERIMENTAL_APPROVAL_INVALID"}
    assert report["status"] == "NOT_READY"


@pytest.mark.parametrize("mutation", ["hash", "scope", "ids", "profiles", "values", "proposal"])
def test_receipt_tamper_does_not_expand_approval(copied_approval, mutation):
    root, config, path = copied_approval
    receipt = json.loads(path.read_text(encoding="utf-8"))
    if mutation == "hash":
        receipt["approved_by"] = "other"
    elif mutation == "scope":
        receipt["scope"] = "all_mission_parameters"
    elif mutation == "ids":
        receipt["decision_ids"].pop()
    elif mutation == "profiles":
        receipt["profiles_approved"] = True
    elif mutation == "values":
        receipt["approved_values"]["return_tolerance_m"] += 0.1
        receipt["approved_values_sha256"] = hashlib.sha256(
            scenario._canonical(receipt["approved_values"]).encode("utf-8")).hexdigest()
    elif mutation == "proposal":
        proposal = root / receipt["reviewed_proposal_path"]
        proposal.write_bytes(proposal.read_bytes() + b"# altered\n")
    path.write_text(json.dumps(receipt), encoding="utf-8")
    if mutation != "hash":
        data = yaml.safe_load(config.read_text(encoding="utf-8"))
        data["scenario_approval"]["receipt_sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
        rewrite_yaml(config, data)
    report = check(config)
    assert report["scenario_approval"]["status"] == "INVALID"
    assert report["status"] == "NOT_READY"
    assert not report["mission_execution_authorized"]


def test_original_proposal_and_operational_template_are_not_relabelled():
    original = yaml.safe_load((ROOT / "config/mission_jezero.proposed.yaml").read_text(encoding="utf-8"))
    operational = yaml.safe_load((ROOT / "config/mission.yaml").read_text(encoding="utf-8"))
    assert original["status"] == "proposed"
    assert operational["status"] == "pending_scientific_approval"
    assert check(ROOT / "config/mission_jezero.proposed.yaml")["scenario_approval"]["status"] == "NOT_RECORDED"
