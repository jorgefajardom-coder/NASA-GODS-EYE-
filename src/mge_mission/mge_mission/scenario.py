"""Readiness diagnostics for public terrain and unapproved mission candidates.

This consumer delegates terrain loading to the data owner. It neither discovers
tasks nor plans routes, synthesizes observations, or approves a mission.
"""

import hashlib
import json
import math
from pathlib import Path
import zipfile

import numpy as np
import yaml
from jsonschema.exceptions import ValidationError

from mge_data.core import load_public_terrain

from .models import MODEL_ID, estimate_activity, load_profiles

PRIVATE_PARTS = {"reference", "evaluation_reference", "ground_truth", "hirise", ".git", ".env"}
REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
EXPERIMENTAL_VALUE_FIELDS = (
    "dataset_id", "manifest_path", "manifest_sha256", "frame_id", "base_enu_m",
    "primary_goal_enu_m", "primary_agent_id", "mode", "return_tolerance_m",
    "primary_service_time_s", "primary_activity", "primary_service_meaning",
    "optional_human_sampling", "optional_tasks", "connectivity", "budgets",
    "agent_staging_cells", "sizing",
)


def experimental_values(configuration):
    """Exact values covered by JZ-P01..07; profiles and runtime flags excluded."""
    return {key: configuration[key] for key in EXPERIMENTAL_VALUE_FIELDS}


def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def _scenario_approval(mission, root):
    declaration = mission.get("scenario_approval")
    if declaration is None:
        return {"status": "NOT_RECORDED"}
    receipt_path = _public_path(root, root / declaration["receipt_path"])
    if _sha(receipt_path) != declaration["receipt_sha256"]:
        raise ValueError("Experimental approval receipt hash mismatch")
    receipt = _document(receipt_path)
    decisions = [f"JZ-P{i:02d}" for i in range(1, 8)]
    if (declaration.get("status") != "approved_experimental_values"
            or receipt.get("schema_version") != "1.0.0"
            or receipt.get("scope") != "experimental_scenario_values_only"
            or receipt.get("approval_id") != "JZ-APP-20261114-01"
            or receipt.get("decision_ids") != decisions
            or receipt.get("approved_by") != "David"
            or receipt.get("approved_on") != "2026-11-14"):
        raise ValueError("Experimental approval scope, identity or decisions are invalid")
    for key in ("profiles_approved", "cost_agreement_approved", "execution_evidence_approved", "operational_authorization"):
        if receipt.get(key) is not False:
            raise ValueError("Experimental approval cannot approve profiles, model agreement or execution")
    proposal_path = _public_path(root, root / receipt["reviewed_proposal_path"])
    if _sha(proposal_path) != receipt["reviewed_proposal_sha256"]:
        raise ValueError("Reviewed proposal hash mismatch")
    values = _canonical(receipt["approved_values"])
    if (hashlib.sha256(values.encode("utf-8")).hexdigest() != receipt["approved_values_sha256"]
            or values != _canonical(experimental_values(_document(proposal_path)))
            or values != _canonical(experimental_values(mission))):
        raise ValueError("Experimental values differ from the approved proposal/receipt")
    return {"status": "APPROVED_EXPERIMENTAL_VALUES", "approval_id": receipt["approval_id"],
            "approved_by": receipt["approved_by"], "approved_on": receipt["approved_on"],
            "decision_ids": decisions, "scope": receipt["scope"],
            "receipt_sha256": declaration["receipt_sha256"], "profiles_approved": False,
            "cost_agreement_approved": False, "execution_evidence_approved": False,
            "operational_authorization": False}


def _sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _document(path):
    text = path.read_text(encoding="utf-8")
    if path.suffix.lower() in {".yaml", ".yml"}:
        result = yaml.safe_load(text)
    else:
        result = json.loads(text, parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)))
    if not isinstance(result, dict):
        raise ValueError("Configuration must be an object")
    json.dumps(result, allow_nan=False)
    return result


def _public_path(root, path):
    resolved = path.resolve(strict=True)
    if (not resolved.is_file() or not resolved.is_relative_to(root)
            or any(part.casefold() in PRIVATE_PARTS for part in resolved.parts)):
        raise ValueError("Public inputs must be files confined to the public package, outside evaluator/private paths")
    return resolved


def _finite(value, *, positive=False):
    return (type(value) in (int, float) and math.isfinite(value)
            and (value > 0 if positive else value >= 0))


def diagnose(manifest_path, profiles_path, mission_path, *, run_id):
    """Return a finite JSON diagnostic and a hash-bound candidate, never authority.

    `ready` in the producer's provenance manifest does not mean scientific
    approval. Missing operational values and approval references remain explicit.
    """
    if not isinstance(run_id, str) or not run_id.strip():
        raise ValueError("A nonempty diagnostic run_id is required")
    report = {
        "schema_version": "1.0.0", "run_id": run_id, "kind": "SCENARIO_DIAGNOSTIC",
        "status": "NOT_READY", "dataset_status": "NOT_READY",
        "scientific_approval": False, "mission_execution_authorized": False,
        "integrated_mission_executed": False, "model_id": MODEL_ID,
        "findings": [], "missing_inputs": [], "inputs_sha256": {},
        "limitations": [
            "Public-package/configuration consistency only; no operational or scientific approval.",
            "No reference files, hidden tasks, planner or executor inputs are consumed.",
            "NoData/unobserved cells remain unknown; no traversability is invented.",
            "Grid resampling does not improve the native resolution of the orbital source.",
        ],
    }

    def finding(code, detail, *, owner="David", severity="error"):
        report["findings"].append(dict(code=code, detail=detail, owner=owner, severity=severity))

    manifest_path, profiles_path, mission_path = map(Path, (manifest_path, profiles_path, mission_path))
    package_root = manifest_path.absolute().parent.resolve()
    tile = None
    try:
        manifest = _public_path(package_root, manifest_path)
        for entry in package_root.iterdir():
            lower = entry.name.casefold()
            if any(token in lower for token in ("hirise", "reference", "ground_truth")):
                raise ValueError("Evaluator-named content must not exist in the public package")
        public_files = {"manifest": manifest}
        for name in ("terrain.npz", "provenance_details.json", "mola_regional_context.npz"):
            path = package_root / name
            if path.exists() or path.is_symlink():
                public_files[name] = _public_path(package_root, path)
        # Inspect names only. Never read evaluator arrays, including a forbidden
        # key accidentally bundled by a producer, before its public loader runs.
        keys = set()
        for name in ("terrain.npz", "mola_regional_context.npz"):
            if name not in public_files:
                continue
            with zipfile.ZipFile(public_files[name]) as archive:
                array_keys = {Path(item.replace("\\", "/")).stem.casefold() for item in archive.namelist()}
            if array_keys.intersection({"reference", "hirise", "evaluation_reference", "ground_truth"}):
                raise ValueError("Public archive contains evaluator-only array keys")
            if name == "terrain.npz":
                keys = array_keys
        required = {"prior", "belief", "sigma", "nodata_mask", "observed_mask"}
        if not required.issubset(keys):
            raise ValueError("Explicit public prior/belief/sigma/NoData/observed arrays are required; loader defaults are not measurements")
        report["inputs_sha256"].update({key: _sha(path) for key, path in public_files.items()})
        tile = load_public_terrain(manifest)
        metadata, transform = tile.metadata, tile.transform
        if metadata.row_orientation != "south_to_north" or transform.row_orientation != "south_to_north":
            raise ValueError("Mission requires the main south-to-north row convention")
        if metadata.frame_id != "map" or transform.frame_id != "map":
            raise ValueError("Mission requires the map ENU frame")
        if any(not math.isfinite(value) for value in (metadata.origin_x_m, metadata.origin_y_m)):
            raise ValueError("Public grid origin must be finite")
        if (metadata.rows, metadata.cols, metadata.resolution_m, metadata.origin_x_m, metadata.origin_y_m) != (
                transform.rows, transform.cols, transform.resolution_m, transform.origin_x_m, transform.origin_y_m):
            raise ValueError("Public metadata and ENU transform disagree")
        valid = ~tile.nodata_mask
        if (not np.array_equal(tile.nodata_mask, ~np.isfinite(tile.belief))
                or not np.all(np.isfinite(tile.sigma[valid])) or np.any(tile.sigma[valid] <= 0)):
            raise ValueError("Public belief/NoData masks and positive finite uncertainty must agree")
        if not np.any(valid):
            raise ValueError("Public package has no valid terrain cells")
        if len(tile.control_points) < 3:
            raise ValueError("At least three verified public control points are required")
        transform.verify_control_points(tile.control_points, tile.prior)
        document = _document(manifest)
        report["inputs_sha256"].update({key: _sha(path) for key, path in public_files.items()})
        report["dataset_status"] = "PUBLIC_PACKAGE_VALIDATED"
        report["terrain"] = {
            "dataset_id": metadata.dataset_id, "manifest_schema_version": document["schema_version"],
            "delivery_form": "data_owner_public_loader_provenance_package",
            "frame_id": metadata.frame_id, "rows": metadata.rows, "cols": metadata.cols,
            "map_version": metadata.map_version,
            "grid_resolution_m": metadata.resolution_m,
            "prior_native_resolution_m": tile.sources.by_role("prior").native_resolution_m,
            "row_orientation": metadata.row_orientation,
            "origin_enu_m": [metadata.origin_x_m, metadata.origin_y_m],
            "vertical_datum": metadata.vertical_datum, "control_point_count": len(tile.control_points),
            "valid_cells": int(np.count_nonzero(valid)), "nodata_cells": int(np.count_nonzero(~valid)),
            "observed_cells": int(np.count_nonzero(tile.observed_mask)),
            "unobserved_cells": int(np.count_nonzero(valid & ~tile.observed_mask)),
            "sigma_range_m": [float(np.min(tile.sigma[valid])), float(np.max(tile.sigma[valid]))],
            "execution_traversability_assumed": False,
        }
    except (OSError, ValueError, KeyError, TypeError, AssertionError, ValidationError, zipfile.BadZipFile) as error:
        finding("PUBLIC_PACKAGE_INVALID", str(error), owner="Daniel")
        tile = None

    profiles, mission = {}, {}
    for name, path in (("profiles", profiles_path), ("mission", mission_path)):
        try:
            if any(part.casefold() in PRIVATE_PARTS for part in path.resolve().parts):
                raise ValueError("Configuration must stay outside evaluator/private paths")
            report["inputs_sha256"][name] = _sha(path)
            if name == "profiles":
                profiles = load_profiles(path)
                report["profile_approval_states"] = {key: value.approval_status for key, value in profiles.items()}
            else:
                mission = _document(path)
        except (OSError, ValueError, KeyError, TypeError, yaml.YAMLError) as error:
            finding(f"{name.upper()}_INVALID", str(error))

    required_fields = ("dataset_id", "base_enu_m", "primary_goal_enu_m", "primary_agent_id",
                       "return_tolerance_m", "primary_service_time_s", "primary_activity", "budgets")
    for name in required_fields:
        if mission.get(name) is None:
            report["missing_inputs"].append(name)
    for name in ("base_enu_m", "primary_goal_enu_m"):
        point = mission.get(name)
        if point is not None:
            if (not isinstance(point, (list, tuple)) or len(point) != 3
                    or any(type(x) not in (int, float) or not math.isfinite(x) for x in point)):
                finding("INVALID_COORDINATES", f"{name} must contain finite ENU XYZ")
            elif tile is not None:
                try:
                    row, col = tile.transform.enu_to_cell(point[0], point[1])
                    if tile.nodata_mask[row, col]:
                        raise ValueError("coordinate lies in NoData")
                    centre = tile.transform.cell_to_enu(row, col)
                    if any(abs(a - b) > 1e-6 for a, b in zip(point[:2], centre)):
                        finding("NON_CELL_CENTER", f"{name} must retain a centred XY input; no silent snapping")
                except ValueError as error:
                    finding("COORDINATE_OUTSIDE_PUBLIC_TERRAIN", f"{name}: {error}")
    if mission.get("return_tolerance_m") is not None and not _finite(mission["return_tolerance_m"]):
        finding("INVALID_TOLERANCE", "return_tolerance_m must be finite and nonnegative")
    if mission.get("frame_id") != "map":
        finding("INVALID_MISSION_FRAME", "Mission frame_id must be map")
    if tile is not None and mission.get("dataset_id") not in (None, tile.metadata.dataset_id):
        finding("DATASET_ID_MISMATCH", "Mission dataset_id differs from the public package")
    agent = mission.get("primary_agent_id")
    valid_agent = isinstance(agent, str) and agent in profiles and profiles[agent].kind == "human"
    if agent is not None and not valid_agent:
        finding("INVALID_PRIMARY_AGENT", "Primary locomotion requires a registered human")
    duration, activity = mission.get("primary_service_time_s"), mission.get("primary_activity")
    if duration is not None and not _finite(duration):
        finding("INVALID_SERVICE_DURATION", "primary_service_time_s must be finite and nonnegative")
    if activity is not None:
        if not isinstance(activity, str) or not activity:
            finding("INVALID_SERVICE_ACTIVITY", "primary_activity must be explicit")
        elif valid_agent:
            try:
                estimate_activity(profiles[agent], activity, 0)
            except ValueError as error:
                finding("INVALID_SERVICE_ACTIVITY", str(error))
    budgets = mission.get("budgets")
    if budgets is not None:
        if not isinstance(budgets, dict) or not valid_agent or agent not in budgets:
            finding("INVALID_BUDGETS", "Budgets must contain the primary agent")
        else:
            for agent_id, budget in budgets.items():
                if agent_id not in profiles or not isinstance(budget, dict):
                    finding("INVALID_BUDGETS", "Budget agent must have a registered profile and resource object")
                    continue
                kind = profiles[agent_id].kind
                keys = ("time_s", "energy_wh", "reserve_time_s", "reserve_wh")
                if kind == "human":
                    keys += ("oxygen_l", "reserve_oxygen_l")
                if any(not _finite(budget.get(key)) for key in keys):
                    finding("INVALID_BUDGETS", f"{agent_id} requires finite nonnegative capacities and reserves")
                    continue
                if kind != "human" and any(budget.get(k) is not None for k in ("oxygen_l", "reserve_oxygen_l")):
                    finding("ROBOT_OXYGEN", f"{agent_id} cannot have oxygen resources")
                for capacity, reserve in (("time_s", "reserve_time_s"), ("energy_wh", "reserve_wh"),
                                          *(([("oxygen_l", "reserve_oxygen_l")]) if kind == "human" else [])):
                    if budget[reserve] > budget[capacity]:
                        finding("RESERVE_EXCEEDS_CAPACITY", f"{agent_id}: {reserve} exceeds {capacity}")

    try:
        report["scenario_approval"] = _scenario_approval(mission, REPOSITORY_ROOT)
    except (OSError, ValueError, KeyError, TypeError, yaml.YAMLError) as error:
        report["scenario_approval"] = {"status": "INVALID"}
        finding("EXPERIMENTAL_APPROVAL_INVALID", str(error))
    approvals = mission.get("approval_evidence", {})
    for key in ("dataset", "science", "resource_model_agreement", "snapshot_contract"):
        if not isinstance(approvals, dict) or not isinstance(approvals.get(key), str) or not approvals[key].strip():
            report["missing_inputs"].append(f"approval_evidence.{key}")
    if mission.get("status") != "approved":
        report["missing_inputs"].append("mission.status=approved")
    if not profiles or any(profile.approval_status != "approved" for profile in profiles.values()):
        report["missing_inputs"].append("approved_agent_profiles")
    model_source = Path(__file__).with_name("models.py")
    report["inputs_sha256"]["model_source"] = _sha(model_source)
    report["candidate_configuration"] = {
        "schema_version": "1.0.0", "status": "pending_review", "run_id": run_id,
        "model_id": MODEL_ID, "bindings_sha256": dict(report["inputs_sha256"]),
        "dataset_id": tile.metadata.dataset_id if tile is not None else None,
        "mission_inputs": {key: mission.get(key) for key in required_fields},
        "approval_evidence": approvals if isinstance(approvals, dict) else {},
        "scenario_approval": report["scenario_approval"],
    }
    if not report["missing_inputs"] and not report["findings"]:
        report["status"] = "CONFIGURATION_CONSISTENT_REVIEW_REQUIRED"
    return report
