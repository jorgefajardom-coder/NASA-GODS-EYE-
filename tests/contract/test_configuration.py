"""Source hashes/version and provider selection are configuration evidence only."""
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET

import pytest
from mge_bringup.launch_profiles import profile_providers, validate_provider_receipt, launch_parameters

ROOT=Path(__file__).resolve().parents[2]


def test_canonical_ros_definitions_match_locked_baseline():
    baseline=json.loads((ROOT/"docs/contract_baseline.json").read_text())
    actual=sorted(str(p.relative_to(ROOT)).replace("\\", "/") for p in (ROOT/"src/mge_interfaces").glob("*/*") if p.suffix in (".msg", ".srv"))
    assert sorted(baseline["ros_definition_sha256"]) == actual
    for name,digest in baseline["ros_definition_sha256"].items():
        assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest() == digest
    assert ET.parse(ROOT/"src/mge_interfaces/package.xml").findtext("version") == baseline["ros_package_version"]


def receipt(profile):
    return dict(baseline_version="1.0.0-rc.1",integration_approved=True,
                providers={p.role:dict(package=p.package,executable=p.executable,kind=p.kind) for p in profile_providers(profile)})


@pytest.mark.parametrize("profile", ["mock", "integration", "simulation"])
def test_single_planner_and_mission_in_each_profile(profile):
    providers=profile_providers(profile)
    assert sum(p.role=="planner" for p in providers)==1
    assert sum(p.role=="mission" for p in providers)==1
    if profile!="mock":
        assert all(p.kind=="REAL" for p in providers if p.role in ("planner","mission"))


def test_no_implicit_scaffold_activation_or_live():
    bad=receipt("mock"); bad["integration_approved"]=False
    with pytest.raises(ValueError,match="REVIEW_REQUIRED"): validate_provider_receipt("mock",bad)
    with pytest.raises(ValueError,match="SCIENTIFIC_INTEGRATION_PENDING"): validate_provider_receipt("integration",receipt("integration"))
    with pytest.raises(ValueError,match="LIVE_BACKEND_UNAVAILABLE"): profile_providers("live")
    wrong=receipt("mock"); wrong["providers"]["planner"]["kind"]="REAL"
    with pytest.raises(ValueError,match="PROVIDER_SET"): validate_provider_receipt("mock",wrong)


def test_owner_parameters_reach_selected_providers_without_identity_override():
    doc=receipt("mock"); doc["parameters"]={"gateway":{"host":"127.0.0.1"}}
    assert launch_parameters("mock",doc,"run-a")["gateway"] == {"host":"127.0.0.1","run_id":"run-a","use_sim_time":False,"source_mode":"MOCK"}
    doc["parameters"]["gateway"]["run_id"]="other"
    with pytest.raises(ValueError,match="OVERRIDE_FORBIDDEN"): launch_parameters("mock",doc,"run-a")


def test_real_provider_configuration_is_explicit_and_preserved():
    doc=receipt("integration")
    doc.update(science_approved=True,resource_model_agreed=True,dataset_approved=True,snapshot_contract_confirmed=True)
    with pytest.raises(ValueError,match="PLANNER_CONFIGURATION"): launch_parameters("integration",doc,"run-a")
    doc["parameters"]={"planner":{"scientific_profiles_path":"approved-science.json","snapshot_contract_confirmed":True}}
    with pytest.raises(ValueError,match="MISSION_CONFIGURATION"): launch_parameters("integration",doc,"run-a")
    doc["parameters"]["mission"]={"profiles_path":"approved-science.json","mission_path":"mission.yaml","model_agreement_confirmed":True,"approved_model_id":"reviewed-model"}
    result=launch_parameters("integration",doc,"run-a")
    assert result["planner"]["scientific_profiles_path"]=="approved-science.json"
    assert result["mission"]["approved_model_id"]=="reviewed-model"
    assert all(value["use_sim_time"] is True for value in result.values())


def test_launcher_declares_source_mode_and_never_live():
    doc=receipt("mock")
    assert launch_parameters("mock",doc,"run-a")["gateway"]["source_mode"]=="MOCK"
    assert "source_mode" not in launch_parameters("mock",doc,"run-a")["planner"]
    doc["parameters"]={"gateway":{"source_mode":"SIMULATION"}}
    with pytest.raises(ValueError,match="OVERRIDE_FORBIDDEN"): launch_parameters("mock",doc,"run-a")
    real={"planner":{"scientific_profiles_path":"approved-science.json","snapshot_contract_confirmed":True},
          "mission":{"profiles_path":"approved-science.json","mission_path":"mission.yaml","model_agreement_confirmed":True,"approved_model_id":"reviewed-model"}}
    for profile,expected in (("integration","MOCK"),("simulation","SIMULATION")):
        doc=receipt(profile)
        doc.update(science_approved=True,resource_model_agreed=True,dataset_approved=True,snapshot_contract_confirmed=True,parameters=real)
        assert launch_parameters(profile,doc,"run-a")["gateway"]["source_mode"]==expected
