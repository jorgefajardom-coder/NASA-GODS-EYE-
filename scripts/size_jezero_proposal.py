"""Reproduce public-prior cost probes for a proposed mission, never plan a route."""

import argparse
from dataclasses import asdict, replace
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import subprocess
import sys

import yaml

ROOT = Path(__file__).resolve().parents[1]
for package in ("mge_mission", "mge_data"):
    sys.path.insert(0, str(ROOT / "src" / package))

from mge_data.core import load_public_terrain
from mge_mission.models import estimate_activity, estimate_segment, load_profiles
from mge_mission.scenario import diagnose


def expand(corners):
    """Expand explicit unit-cell axis/diagonal cost geometry; no search or snapping."""
    cells = [tuple(corners[0])]
    for end in corners[1:]:
        start = cells[-1]
        dr, dc = end[0] - start[0], end[1] - start[1]
        if dr and dc and abs(dr) != abs(dc):
            raise ValueError("Explicit grid probes require axis or diagonal legs")
        count = max(abs(dr), abs(dc))
        cells.extend((start[0] + i * (0 if not dr else 1 if dr > 0 else -1),
                      start[1] + i * (0 if not dc else 1 if dc > 0 else -1))
                     for i in range(1, count + 1))
    return cells


def probe(profile, points, service_s, wait_s, activity, budget):
    out = [estimate_segment(profile, a, b) for a, b in zip(points, points[1:])]
    reverse = list(reversed(points))
    back = [estimate_segment(profile, a, b) for a, b in zip(reverse, reverse[1:])]
    service = estimate_activity(profile, activity, service_s)
    waiting = estimate_activity(profile, "idle", wait_s)
    def total(costs):
        return {"time_s": sum(c.time_s for c in costs),
                "energy_wh": sum(c.energy_wh for c in costs),
                "oxygen_l": sum(c.oxygen_l for c in costs) if profile.kind == "human" else None}
    result = total([*out, *back, service, waiting])
    margin = {"time_s": budget["time_s"] - budget["reserve_time_s"] - result["time_s"],
              "energy_wh": budget["energy_wh"] - budget["reserve_wh"] - result["energy_wh"]}
    if profile.kind == "human":
        margin["oxygen_l"] = budget["oxygen_l"] - budget["reserve_oxygen_l"] - result["oxygen_l"]
    step = max(abs(a[2] - b[2]) for a, b in zip(points, points[1:]))
    return {"total": result, "outbound": total(out), "return": total(back),
            "service": asdict(service), "wait": asdict(waiting), "reserve_margins": margin,
            "resource_envelope_fits": all(v >= 0 for v in margin.values()),
            "max_height_change_per_probe_edge_m": step,
            "step_proxy_exceeded": step > profile.parameters["max_step_m"] if profile.kind != "drone" else None,
            "horizontal_one_way_m": sum(math.hypot(b[0]-a[0], b[1]-a[1]) for a, b in zip(points, points[1:]))}


def build_report(proposal_path, *, run_id):
    data = yaml.safe_load(proposal_path.read_text(encoding="utf-8"))
    manifest, registry = ROOT / data["manifest_path"], ROOT / data["profiles_path"]
    readiness = diagnose(manifest, registry, proposal_path, run_id=run_id)
    if readiness["dataset_status"] != "PUBLIC_PACKAGE_VALIDATED" or readiness["findings"]:
        raise ValueError(f"Invalid public proposal inputs: {readiness['findings']}")
    if hashlib.sha256(manifest.read_bytes()).hexdigest() != data["manifest_sha256"]:
        raise ValueError("Proposal manifest identity differs from its frozen public input")
    if data["status"] != "proposed":
        raise ValueError("Sizing only accepts an explicitly proposed configuration")
    if (data["primary_service_time_s"] != data["sizing"]["service_s"]["human_1"]
            or data["primary_activity"] != data["sizing"]["service_activity"]["human_1"]):
        raise ValueError("Primary service and sizing inputs must agree")
    tile, profiles = load_public_terrain(manifest), load_profiles(registry)
    def point(cell):
        row, col = cell
        return (*tile.transform.cell_to_enu(row, col), float(tile.prior[row, col]))
    if tuple(data["base_enu_m"]) != point(data["sizing"]["human_probe_cells"][0]):
        raise ValueError("Base must retain the exact public cell centre/height")
    if tuple(data["primary_goal_enu_m"]) != point(data["sizing"]["human_probe_cells"][-1]):
        raise ValueError("Goal must retain the exact public cell centre/height")
    rows = []
    for agent, key in (("human_1", "human_probe_cells"), ("rover_1", "rover_probe_cells"),
                       ("drone_1", "drone_probe_cells")):
        cells = data["sizing"][key]
        if cells[0] != data["agent_staging_cells"][agent]:
            raise ValueError("Cost probe must begin at the proposed agent staging cell")
        # Drone chord is only a scalar model comparison, no terrain-following flight prescription.
        if profiles[agent].kind != "drone":
            cells = expand(cells)
        points = [point(cell) for cell in cells]
        kwargs = dict(points=points, service_s=data["sizing"]["service_s"][agent],
                      wait_s=data["sizing"]["wait_allowance_s"][agent],
                      activity=data["sizing"]["service_activity"][agent], budget=data["budgets"][agent])
        nominal = probe(profiles[agent], **kwargs)
        sensitivity = []
        for assumption in json.loads(registry.read_text(encoding="utf-8"))["assumptions"]:
            parts = assumption["parameter"].split(".")
            if len(parts) != 4 or parts[1] != agent:
                continue
            for label in ("sensitivity_min", "sensitivity_max"):
                values = dict(getattr(profiles[agent], parts[2]))
                values[parts[3]] = assumption[label]
                variant = replace(profiles[agent], **{parts[2]: values})
                try:
                    value = probe(variant, **kwargs)
                except ValueError as error:
                    value = {"model_rejected": str(error)}
                sensitivity.append({"parameter": assumption["parameter"], "level": label,
                                    "value": assumption[label], **value})
        rows.append({"agent_id": agent, "probe_cells": cells, "probe_points_enu_m": points,
                     "route_verified": False, "geometry_admissibility": "UNKNOWN",
                     "nominal": nominal, "coefficient_sensitivity_oat": sensitivity,
                     "reserve_fraction_sensitivity": [{"fraction": f, **probe(profiles[agent], **{
                         **kwargs, "budget": {**kwargs["budget"], "reserve_time_s": f * kwargs["budget"]["time_s"],
                         "reserve_wh": f * kwargs["budget"]["energy_wh"],
                         **({"reserve_oxygen_l": f * kwargs["budget"]["oxygen_l"]} if profiles[agent].kind == "human" else {})}})}
                         for f in data["sizing"]["reserve_fraction_sensitivity"]]})
    sample = estimate_activity(profiles["human_1"], "sample", data["sizing"]["optional_sample_duration_s"])
    human = rows[0]["nominal"]["total"]
    sample_sensitivity = []
    for duration in (60, 180, 300):
        extra = estimate_activity(profiles["human_1"], "sample", duration)
        combined = {key: human[key] + getattr(extra, key) for key in human}
        budget = data["budgets"]["human_1"]
        margins = {"time_s": budget["time_s"] - budget["reserve_time_s"] - combined["time_s"],
                   "energy_wh": budget["energy_wh"] - budget["reserve_wh"] - combined["energy_wh"],
                   "oxygen_l": budget["oxygen_l"] - budget["reserve_oxygen_l"] - combined["oxygen_l"]}
        sample_sensitivity.append({"duration_s": duration, "combined_cost_only": combined,
            "reserve_margins": margins, "additional_cost_fits": all(x >= 0 for x in margins.values()),
            "task_assigned": False})
    diagonal = expand([data["sizing"]["human_probe_cells"][0], data["sizing"]["human_probe_cells"][-1]])
    max_diagonal_step = max(abs(point(a)[2] - point(b)[2]) for a, b in zip(diagonal, diagonal[1:]))
    return {"schema_version": "1.0.0", "run_id": run_id, "kind": "PUBLIC_PRIOR_MODEL_SIZING",
            "proposal_id": data["proposal_id"], "approval_status": "proposed",
            "scientific_approval": False, "integrated_mission_executed": False,
            "mission_execution_authorized": False, "readiness": readiness, "probes": rows,
            "optional_sample_cost_only": asdict(sample),
            "optional_sample_duration_sensitivity": sample_sensitivity,
            "direct_diagonal_counterexample": {"max_height_step_m": max_diagonal_step,
                "step_proxy_exceeded": max_diagonal_step > profiles["human_1"].parameters["max_step_m"],
                "route_verified": False},
            "limitations": ["Cost probes only; no route search, observation, task or execution is generated.",
                            "All unobserved cells and uncertainty gates are preserved.",
                            "Step proxy is a DEM edge difference, not measured obstacle height or a clearance check.",
                            "Drone endpoints use public elevations only for scalar comparison; no flight altitude or path is approved.",
                            "OAT varies one coefficient at a time; joint extremes can invalidate these budgets.",
                            "Caps/reserves are experimental choices, not hardware or EVA capacities."]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--proposal", type=Path, default=ROOT / "config/mission_jezero.proposed.yaml")
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    report = build_report(args.proposal, run_id=args.run_id)
    report.update(recorded_at_utc=datetime.now(timezone.utc).isoformat(), command=[sys.executable, *sys.argv])
    revision = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=False)
    status = subprocess.run(["git", "status", "--porcelain"], cwd=ROOT, capture_output=True, text=True, check=False)
    report.update(source_revision=revision.stdout.strip() if revision.returncode == 0 else None,
                  working_tree_dirty=bool(status.stdout.strip()) if status.returncode == 0 else None)
    report["implementation_sha256"] = {p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in (Path(__file__).resolve(), ROOT / "src/mge_mission/mge_mission/models.py",
                  ROOT / "src/mge_mission/mge_mission/scenario.py", ROOT / "src/mge_data/mge_data/core.py")}
    if any(part.casefold() in {"reference", ".git", ".env"} for part in args.output_dir.resolve().parts):
        raise ValueError("Output must stay outside private/evaluator paths")
    args.output_dir.mkdir(parents=True, exist_ok=False)
    with (args.output_dir / "proposal_sizing.json").open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(json.dumps(report, indent=2, allow_nan=False) + "\n")
    print("Recorded public-prior model sizing; proposal remains NOT_READY and unapproved.")


if __name__ == "__main__":
    main()
