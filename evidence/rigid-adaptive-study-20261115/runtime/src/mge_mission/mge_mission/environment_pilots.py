"""Local research input preparation and cost audit; no execution producer."""
from dataclasses import asdict
import hashlib
import json
from pathlib import Path

import numpy as np

from .models import estimate_activity, estimate_segment


def content_hash(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def load_audited_crop(prior_root, map_id):
    """Consume an unchanged public crop; do not manufacture a canonical package."""
    root = Path(prior_root)
    record = read_json(root / "public" / (map_id + ".json"))
    path = root / record["path"]
    if content_hash(path) != record["file_sha256"]:
        raise ValueError("Public crop checksum mismatch")
    with np.load(path, allow_pickle=False) as data:
        if any(k in data.files for k in ("reference", "hirise", "ground_truth")):
            raise ValueError("Evaluator arrays are forbidden")
        elevation = np.array(data["elevation_m"], dtype=np.float32, copy=True)
        valid = np.array(data["valid_mask"], dtype=bool, copy=True)
    if elevation.shape != (record["rows"], record["cols"]):
        raise ValueError("Crop geometry mismatch")
    if record["resolution_m"] != 4 or record["row_orientation"] != "south_to_north":
        raise ValueError("Unsupported research geometry")
    if not np.array_equal(valid, np.isfinite(elevation)):
        raise ValueError("Validity and NoData disagree")
    elevation[~valid] = np.nan
    return record, elevation


def recorded_endpoints(prior_root, map_id, indices):
    """Retain pre-existing geometric draws regardless of planner outcome."""
    selected = {}
    with (Path(prior_root) / "ensemble.jsonl").open(encoding="utf-8") as stream:
        for line in stream:
            row = json.loads(line)
            p = row["payload"]
            if p.get("map_id") == map_id and p.get("family") == "unchanged" and p.get("index") in indices:
                cells = tuple(tuple(cell) for cell in p["endpoint_cells"])
                selected[p["index"]] = {"index": p["index"], "cells": cells,
                    "source_seq": row["seq"], "source_payload_sha256": row["payload_sha256"],
                    "selection_depends_on_route": False}
    return [selected[i] if i in selected else {"index": i, "state": "SOURCE_CASE_UNAVAILABLE"} for i in indices]


def cell_point(record, elevation, cell):
    row, col = tuple(cell)
    if type(row) is not int or type(col) is not int or not (0 <= row < elevation.shape[0] and 0 <= col < elevation.shape[1]):
        raise ValueError("Invalid endpoint cell")
    z = float(elevation[row, col])
    if not np.isfinite(z):
        raise ValueError("NoData endpoint")
    return (record["origin_x_m"] + (col + .5) * 4,
            record["origin_y_m"] + (row + .5) * 4, z)


def sum_costs(profile, parts):
    return {"time_s": sum(p.time_s for p in parts), "energy_wh": sum(p.energy_wh for p in parts),
            "oxygen_l": sum(p.oxygen_l for p in parts) if profile.kind == "human" else None}


def proposed_allocation(prior_root, region_id, profile):
    campaign = {"bright": "CAM-BRIGHT", "hawksbill": "CAM-HAWKSBILL", "bunsen": "CAM-BUNSEN"}[region_id]
    row = next(r for r in read_json(Path(prior_root) / "campaign-campaign_analysis.json")["cases"] if r["case"]["id"] == campaign)
    cap = row["requested_caps"][profile.kind]
    gross, reserves = cap["requested"], cap["separate_reserves"]
    wait_s = row["case"]["human_coordination_wait_s"] if profile.kind == "human" else 1800 + row["nominal"]["human"]["total"]["time_s"]
    wait = asdict(estimate_activity(profile, "wait", wait_s))
    remaining = {k: v - wait[k] for k, v in gross.items()}
    remaining.setdefault("oxygen_l", None)
    return {"gross": gross, "reserves": reserves, "assumed_wait_s": wait_s, "assumed_wait_cost": wait,
            "remaining_for_planning": remaining, "service": [("inspect", 120. if profile.kind == "human" else 600.)],
            "approval": "PROPOSED_RESEARCH_ONLY", "wait_was_physically_executed": False}


def cost_audit(profile, decision, schedule, allocation):
    """Audit returned geometry once, including directed return and service."""
    if decision["status"] != "FEASIBLE":
        return {"status": "NO_ITINERARY", "model_agreement": False, "candidate_authorized": False}
    parts = []
    for name in ("outbound_path", "return_path"):
        path = [tuple(p[k] for k in ("x", "y", "z")) if isinstance(p, dict) else tuple(p) for p in decision[name]]
        parts.extend(estimate_segment(profile, a, b) for a, b in zip(path, path[1:]))
    parts.extend(estimate_activity(profile, activity, duration) for activity, duration in schedule)
    cost = sum_costs(profile, parts)
    available, reserve = allocation["remaining_for_planning"], allocation["reserves"]
    margins = {k: available[k] - reserve[k] - v for k, v in cost.items() if v is not None}
    fields = {"time_s": "travel_time_s", "energy_wh": "energy_est_wh", "oxygen_l": "oxygen_est_l"}
    reported = {k: decision[fields[k]] for k in cost}
    return {"status": "AUDITED", "cost": cost, "margins": margins,
            "resource_envelope_fits": all(v >= 0 for v in margins.values()),
            "projection_minus_science": {k: reported[k] - v if v is not None else None for k, v in cost.items()},
            "numerical_match": {k: bool(np.isclose(v, reported[k], rtol=1e-5, atol=1e-3)) for k, v in cost.items() if v is not None},
            "model_agreement": False, "candidate_authorized": False, "mission_success": None}
