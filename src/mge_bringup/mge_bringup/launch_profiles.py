"""Mutually exclusive provider inventory, not evidence that providers are ready."""
from dataclasses import dataclass


@dataclass(frozen=True)
class Provider:
    role: str
    package: str
    executable: str
    kind: str


def profile_providers(profile):
    if profile not in ("mock", "integration", "simulation", "live"):
        raise ValueError("UNKNOWN_LAUNCH_PROFILE")
    if profile == "live":
        raise ValueError("NOT_READY: LIVE_BACKEND_UNAVAILABLE")
    providers = [Provider("gateway", "mge_gateway", "gateway", "REAL")]
    if profile == "mock":
        providers += [Provider(role, "mge_sim", "mock_" + role, "MOCK")
                      for role in ("terrain", "planner", "mission", "agents")]
    else:
        providers += [Provider("terrain", "mge_data", "data_node", "REAL"),
                      Provider("mapping", "mge_mapping", "mapping_node", "REAL"),
                      Provider("planner", "mge_planning", "planning_node", "REAL"),
                      Provider("mission", "mge_mission", "mission_node", "REAL"),
                      Provider("agents", "mge_sim", "mock_agents" if profile == "integration" else "sim_node",
                               "MOCK" if profile == "integration" else "REAL")]
    return tuple(providers)


def source_mode(providers):
    """Provenance the gateway declares for a run of this provider inventory."""
    return "MOCK" if any(p.kind == "MOCK" for p in providers) else "SIMULATION"


def validate_provider_receipt(profile, receipt):
    """Explicit review/config gate; receipt alone is never mission acceptance.

    Integration and simulation additionally need real owner approvals. Executable
    availability and active ROS service collisions are checked by launch preflight.
    """
    providers = profile_providers(profile)
    if receipt.get("baseline_version") != "1.0.0-rc.1":
        raise ValueError("BASELINE_RECEIPT_MISMATCH")
    expected = {p.role: {"package": p.package, "executable": p.executable, "kind": p.kind}
                for p in providers}
    if receipt.get("providers") != expected:
        raise ValueError("PROVIDER_SET_MISMATCH")
    if receipt.get("integration_approved") is not True:
        raise ValueError("NOT_READY: INTEGRATION_REVIEW_REQUIRED")
    if profile != "mock" and any(receipt.get(name) is not True for name in (
            "science_approved", "resource_model_agreed", "dataset_approved", "snapshot_contract_confirmed")):
        raise ValueError("NOT_READY: SCIENTIFIC_INTEGRATION_PENDING")
    return providers


def launch_parameters(profile, receipt, run_id):
    """Pass owner configuration through unchanged; never infer science inputs."""
    providers = validate_provider_receipt(profile, receipt)
    if not isinstance(run_id, str) or not run_id.strip():
        raise ValueError("RUN_ID_REQUIRED")
    parameters = receipt.get("parameters", {})
    if not isinstance(parameters, dict) or set(parameters) - {p.role for p in providers}:
        raise ValueError("UNEXPECTED_PROVIDER_PARAMETERS")
    result = {}
    for p in providers:
        values = parameters.get(p.role, {})
        if not isinstance(values, dict) or {"run_id", "use_sim_time", "source_mode"} & set(values):
            raise ValueError("PARAMETER_IDENTITY_OVERRIDE_FORBIDDEN")
        result[p.role] = {**values, "run_id": run_id, "use_sim_time": profile != "mock"}
    # One MOCK provider makes the whole run MOCK; LIVE is never declared here.
    result["gateway"]["source_mode"] = source_mode(providers)
    if profile != "mock":
        planner, mission = result["planner"], result["mission"]
        if (not planner.get("scientific_profiles_path")
                or planner.get("allow_legacy_cost_model", False) is not False
                or planner.get("snapshot_contract_confirmed") is not True):
            raise ValueError("NOT_READY: PLANNER_CONFIGURATION_REQUIRED")
        if (not mission.get("profiles_path") or not mission.get("mission_path")
                or mission.get("model_agreement_confirmed") is not True or not mission.get("approved_model_id")):
            raise ValueError("NOT_READY: MISSION_CONFIGURATION_REQUIRED")
        if planner["scientific_profiles_path"] != mission["profiles_path"]:
            raise ValueError("NOT_READY: SCIENTIFIC_PROFILE_IDENTITY_MISMATCH")
    return result
