"""Reproduce a public-data scale audit and ideal flat resource ceilings only."""

import argparse
from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import subprocess
import sys

import numpy as np
import yaml

ROOT = Path(__file__).resolve().parents[2]
EXPECTED_REVISION = "c3ec4c1f1515dbc981ba82eed2ab1f54e9586264"
sys.path[:0] = [str(ROOT / "src/mge_mission"), str(ROOT / "src/mge_data")]

from mge_data.core import load_public_terrain
from mge_mission.models import MODEL_ID, estimate_activity, estimate_segment, load_profiles
from mge_mission.scenario import diagnose


def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT)


def sha(value):
    return hashlib.sha256(value).hexdigest()


def input_identity(name, revision):
    path = ROOT / name
    if any(part.casefold() in {"reference", "ground_truth", "evaluation_reference"} for part in path.parts):
        raise ValueError("Evaluator files are excluded from this assessment")
    working_bytes = path.read_bytes()
    blob_bytes = git("show", f"{revision}:{name}")
    text_file = path.suffix in {".json", ".yaml", ".yml", ".py", ".md"}
    return {
        "working_tree_sha256": sha(working_bytes),
        "git_blob_content_sha256": sha(blob_bytes),
        "git_blob_object_id": git("rev-parse", f"{revision}:{name}").decode().strip(),
        "git_blob_object_id_algorithm": "sha1",
        "sha256_meaning": "SHA-256 of file/content bytes, distinct from the Git object ID",
        "working_tree_size_bytes": len(working_bytes),
        "git_blob_content_size_bytes": len(blob_bytes),
        "bytes_identical": working_bytes == blob_bytes,
        "equivalent_after_CRLF_to_LF_normalization": (
            working_bytes.replace(b"\r\n", b"\n") == blob_bytes.replace(b"\r\n", b"\n")
            if text_file else None),
    }


def add_costs(profile, values):
    return {
        "time_s": sum(value.time_s for value in values),
        "energy_wh": sum(value.energy_wh for value in values),
        "oxygen_l": sum(value.oxygen_l for value in values) if profile.kind == "human" else None,
    }


def flat_bound(profile, budget, stationary_costs):
    one_metre = estimate_segment(profile, (0.0, 0.0, 0.0), (1.0, 0.0, 0.0))
    fixed = add_costs(profile, stationary_costs)
    metric_keys = [("time_s", "reserve_time_s"), ("energy_wh", "reserve_wh")]
    if profile.kind == "human":
        metric_keys.append(("oxygen_l", "reserve_oxygen_l"))
    constraints = {}
    for metric, reserve in metric_keys:
        usable = budget[metric] - budget[reserve]
        residual = usable - fixed[metric]
        per_metre_outbound = 2 * getattr(one_metre, metric)
        constraints[metric] = {
            "initial_allocation": budget[metric],
            "separate_reserve": budget[reserve],
            "usable_after_reserve": usable,
            "stationary_consumption_once": fixed[metric],
            "residual_for_roundtrip_movement": residual,
            "cost_per_metre_of_outbound_displacement_with_same_way_return": per_metre_outbound,
            "theoretical_one_way_displacement_limit_m": residual / per_metre_outbound,
        }
    limiting_metric = min(constraints, key=lambda key: constraints[key]["theoretical_one_way_displacement_limit_m"])
    radius = constraints[limiting_metric]["theoretical_one_way_displacement_limit_m"]
    if radius < 0:
        raise ValueError("The declared stationary workflow already exceeds usable resources")
    raw_move = estimate_segment(profile, (0.0, 0.0, 0.0), (radius, 0.0, 0.0))
    raw_total = add_costs(profile, [*stationary_costs, raw_move, raw_move])
    # This is an illustrative display radius, never a candidate authorization.
    # Rounding down avoids suggesting that displayed decimals grant extra capacity.
    display_radius = math.floor(radius * 100) / 100
    display_move = estimate_segment(profile, (0.0, 0.0, 0.0), (display_radius, 0.0, 0.0))
    display_total = add_costs(profile, [*stationary_costs, display_move, display_move])
    return {
        "one_metre_one_way_cost": asdict(one_metre),
        "stationary_total_once": fixed,
        "constraints": constraints,
        "limiting_metric": limiting_metric,
        "approximate_theoretical_one_way_displacement_ceiling_m": radius,
        "approximate_theoretical_total_travel_ceiling_m": 2 * radius,
        "raw_float_cost_at_quotient": raw_total,
        "raw_float_reserve_margins_at_quotient": {
            metric: budget[metric] - budget[reserve] - raw_total[metric]
            for metric, reserve in metric_keys},
        "display_radius_rounded_down_to_centimetres_m": display_radius,
        "cost_at_rounded_down_display_radius": display_total,
        "reserve_margins_at_rounded_down_display_radius": {
            metric: budget[metric] - budget[reserve] - display_total[metric]
            for metric, reserve in metric_keys},
        "candidate_accepted": False,
        "mission_execution_authorized": False,
        "numerical_policy": "The quotient is an approximate theoretical ceiling. A negative floating-point reserve margin remains negative; no ULP or tolerance budget credit is granted. Display truncation does not verify a route.",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path,
                        default=Path(__file__).resolve().with_name("scale_assessment.json"))
    args = parser.parse_args()
    revision = git("rev-parse", "HEAD").decode().strip()
    if revision != EXPECTED_REVISION:
        raise ValueError(f"Expected pinned local revision {EXPECTED_REVISION}, found {revision}")
    names = [
        "config/mission_jezero.experimental.yaml", "config/science_profiles.proposed.json",
        "src/mge_mission/mge_mission/models.py", "src/mge_mission/mge_mission/scenario.py",
        "src/mge_data/mge_data/core.py", "data/sample/manifest.json", "data/sample/terrain.npz",
        "data/sample/mola_regional_context.npz", "config/terrain.yml",
        "data/sample/provenance_details.json", "docs/science_approvals/jezero_scenario_20261114.json",
        "config/mission_jezero.proposed.yaml",
    ]
    identities = {name: input_identity(name, revision) for name in names}
    mission_path = ROOT / "config/mission_jezero.experimental.yaml"
    mission = yaml.safe_load(mission_path.read_text(encoding="utf-8"))
    manifest_path = ROOT / mission["manifest_path"]
    profiles_path = ROOT / mission["profiles_path"]
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    profiles = load_profiles(profiles_path)
    tile = load_public_terrain(manifest_path)
    readiness = diagnose(manifest_path, profiles_path, mission_path, run_id="science-patch-scale-audit-20261114")
    if readiness["scenario_approval"]["status"] != "APPROVED_EXPERIMENTAL_VALUES" or readiness["findings"]:
        raise ValueError("Experimental-value approval/public-input validation failed")
    corners = [(-64.0, -64.0), (64.0, -64.0), (-64.0, 64.0), (64.0, 64.0)]
    if (tile.prior.shape != (32, 32) or tile.transform.resolution_m != 4.0
            or tile.transform.origin_x_m != -64.0 or tile.transform.origin_y_m != -64.0):
        raise ValueError("Public tile no longer matches the pinned 128 m control scenario")
    agents = {}
    for agent_id, profile in profiles.items():
        service_name = mission["sizing"]["service_activity"][agent_id]
        service_s = mission["sizing"]["service_s"][agent_id]
        wait_s = mission["sizing"]["wait_allowance_s"][agent_id]
        service = estimate_activity(profile, service_name, service_s)
        waiting = estimate_activity(profile, "idle", wait_s)
        result = {
            "kind": profile.kind, "model_id": profile.model_id,
            "profile_approval_status": profile.approval_status,
            "parameters": dict(profile.parameters), "activity_power_w": dict(profile.activity_power_w),
            "budget": mission["budgets"][agent_id],
            "service": {"activity": service_name, "duration_s": service_s, "cost": asdict(service)},
            "waiting": {"activity": "ground_wait" if profile.kind == "drone" else "wait", "duration_s": wait_s, "cost": asdict(waiting)},
            "baseline_flat_bound": flat_bound(profile, mission["budgets"][agent_id], [service, waiting]),
        }
        if profile.kind == "human":
            sample_s = mission["sizing"]["optional_sample_duration_s"]
            sample = estimate_activity(profile, "sample", sample_s)
            result["additional_approved_180s_acquisition_only"] = {
                "activity": "sample", "duration_s": sample_s, "cost": asdict(sample),
                "interpretation": "Resource-only sensitivity after the primary check-in. No task is created/assigned; discovery, completed public inspection and primary completion are still required. Extra optional travel/coordination is excluded. This acquisition primitive is not a documented complete sample cycle.",
                "flat_bound": flat_bound(profile, mission["budgets"][agent_id], [service, waiting, sample]),
            }
        agents[agent_id] = result
    source_metadata = []
    for source in manifest["sources"]:
        if source["role"] not in {"prior", "regional_context"}:
            continue
        source_metadata.append({key: source[key] for key in (
            "mission", "instrument", "role", "product_id", "native_resolution_m", "source_url")})
        source_metadata[-1]["manifest_sha256_field"] = source["sha256"]
        source_metadata[-1]["manifest_sha256_field_scope"] = "Processed local NPZ artifact identified by the manifest, not the remote GeoTIFF bytes"
        source_metadata[-1]["remote_product_downloaded_or_hashed_in_this_assessment"] = False
    report = {
        "schema_version": "1.0.0", "run_id": "science-patch-scale-audit-20261114",
        "classification": "ANALYTICAL_FLAT_RESOURCE_CEILINGS_AND_PUBLIC_DATA_SCALE_AUDIT",
        "recorded_at_utc": datetime.now(timezone.utc).isoformat(),
        "revision": revision, "working_tree_dirty": bool(git("status", "--porcelain").strip()),
        "assessment_code_sha256": sha(Path(__file__).read_bytes()),
        "command": [sys.executable, *sys.argv], "python_version": sys.version,
        "numpy_version": np.__version__, "pyyaml_version": yaml.__version__, "model_id": MODEL_ID,
        "source_identity": identities,
        "public_source_metadata": source_metadata,
        "public_tile": {
            "dataset_id": manifest["region_id"], "rows": 32, "cols": 32,
            "computational_cell_size_m": 4.0, "extent_side_m": 128.0,
            "native_prior_DTM_cell_size_m": 20.0,
            "separate_CTX_orthomosaic_cell_size_m": 6.0,
            "orthomosaic_metadata_basis": "Existing docs/data_sources.md and web/scripts/extract-ctx-ortho.mjs; image not loaded or fetched by this assessment",
            "origin_lat_planetocentric_deg": tile.transform.origin_lat_deg,
            "origin_lon_east_deg": tile.transform.origin_lon_deg,
            "frame": "map local ENU metres", "row_orientation": "south_to_north",
            "vertical_datum": manifest["vertical_datum"],
            "nodata_count": int(np.count_nonzero(tile.nodata_mask)),
            "observed_count": int(np.count_nonzero(tile.observed_mask)),
            "sigma_values_m": np.unique(tile.sigma).tolist(),
            "public_prior_elevation_min_m": float(tile.prior.min()),
            "public_prior_elevation_max_m": float(tile.prior.max()),
            "derived_extent_corners": [
                {"enu_xy_m": list(corner), "lat_planetocentric_deg": tile.transform.enu_to_planetocentric(*corner)[0],
                 "lon_east_deg": tile.transform.enu_to_planetocentric(*corner)[1]} for corner in corners],
            "coordinate_interpretation": "Corners derived from the public local transform, not independent surveyed controls",
        },
        "scenario_readiness": {key: readiness[key] for key in ("status", "dataset_status", "findings", "missing_inputs", "scenario_approval")},
        "scale_table": [
            {"side_m": side, "area_m2": side * side, "computational_cell_size_m": 4.0,
             "cells_per_axis": side // 4, "total_cells": (side // 4) ** 2,
             "cell_count_multiplier_over_current_128m": (side / 128) ** 2,
             "native_CTX_DTM_20m_sample_spacings_per_axis": side / 20,
             "native_CTX_DTM_20m_cell_areas_equivalent": (side / 20) ** 2,
             "separate_CTX_6m_image_sample_spacings_per_axis": side / 6,
             "larger_package_imported_or_verified": False}
            for side in (128, 256, 512, 1024, 2048)],
        "resource_bounds_by_agent": agents,
        "method": "Subtract each separate reserve and the explicit service/wait costs. For each remaining resource, divide by twice estimate_segment(profile,(0,0,0),(1,0,0)). The smallest quotient limits ideal one-way displacement with retraced return. No search, terrain route or execution evidence is produced.",
        "limitations": [
            "Proposed profile coefficients remain unapproved; scenario-value approval does not approve costs or physical limits.",
            "These ceilings are not reachable discs, surveyed footprints, sensor coverage, candidate acceptance or mission authorization.",
            "Flat estimates exclude real grades, detours, obstacles, uncertainty, footprint clearance, added coordination and extra tasks.",
            "Drone flat estimates exclude takeoff/landing, climb/descent, altitude, swept volume and validated flight.",
            "Bilinear 20 m to 4 m resampling creates no sub-20 m native topographic information or independent measurements.",
            "Native sample spacings and cell-area equivalents are scale ratios, not independent observational sample counts.",
            "128 by 128 computational cells at 4 m mean 512 by 512 m, distinct from the current 128 by 128 m tile.",
            "No remote GeoTIFF was downloaded or hashed today; manifest source SHA fields identify processed local artifacts.",
            "No evaluator array, hidden reference file, planner module, observation or task producer was used.",
        ],
        "candidate_accepted": False, "task_assigned": False, "integrated_mission_executed": False,
        "scientific_approval": False, "cost_agreement_approved": False,
        "mission_execution_authorized": False,
    }
    if any(sha((ROOT / name).read_bytes()) != value["working_tree_sha256"] for name, value in identities.items()):
        raise ValueError("An input changed during the assessment")
    if git("rev-parse", "HEAD").decode().strip() != revision:
        raise ValueError("Git revision changed during the assessment")
    target = args.output
    with target.open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(json.dumps(report, indent=2, allow_nan=False) + "\n")
    print(json.dumps({"saved": str(target), "inputs_stable": True,
        "approximate_theoretical_one_way_displacement_ceilings_m": {
            name: value["baseline_flat_bound"]["approximate_theoretical_one_way_displacement_ceiling_m"]
            for name, value in agents.items()}}, allow_nan=False))


if __name__ == "__main__":
    main()
