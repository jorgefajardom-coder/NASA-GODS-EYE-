"""Export analytic scientific-cost vectors; no planner, executor or observations."""

import argparse
from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import re
import subprocess
import sys

import yaml

ROOT = Path(__file__).resolve().parents[1]
for package in ("mge_mission", "mge_data"):
    sys.path.insert(0, str(ROOT / "src" / package))

from mge_mission.conformance import ABSOLUTE_TOLERANCE, RELATIVE_TOLERANCE
from mge_mission.models import MODEL_ID, estimate_activity, estimate_segment, load_profiles
from mge_mission.scenario import diagnose


def _sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _public_input(path):
    resolved = Path(path).resolve(strict=True)
    if any(part.casefold() in {"reference", "evaluation_reference", "ground_truth", ".git", ".env"} for part in resolved.parts):
        raise ValueError("Input must stay outside private/evaluator paths")
    return resolved


def validate_experimental_inputs(scenario_path, profiles_path, *, run_id):
    """Validate scoped approval and public bindings without authorizing execution."""
    scenario_path, profiles_path = map(_public_input, (scenario_path, profiles_path))
    scenario = yaml.safe_load(scenario_path.read_text(encoding="utf-8"))
    manifest_path = _public_input(ROOT / scenario["manifest_path"])
    if (scenario.get("model_id") != MODEL_ID
            or _public_input(ROOT / scenario["profiles_path"]) != profiles_path
            or scenario.get("manifest_sha256") != _sha(manifest_path)):
        raise ValueError("Experimental model/profile/manifest bindings differ from supplied inputs")
    readiness = diagnose(manifest_path, profiles_path, scenario_path, run_id=run_id)
    if (readiness["dataset_status"] != "PUBLIC_PACKAGE_VALIDATED"
            or readiness["findings"]
            or readiness["scenario_approval"]["status"] != "APPROVED_EXPERIMENTAL_VALUES"):
        raise ValueError(f"Experimental scenario approval/public inputs are invalid: {readiness['findings']}")
    return scenario, readiness


def _cost_sum(profile, costs):
    return {"time_s": sum(x.time_s for x in costs),
            "energy_wh": sum(x.energy_wh for x in costs),
            "oxygen_l": sum(x.oxygen_l for x in costs) if profile.kind == "human" else None}


def _schedule(profile, schedule):
    parts, costs = [], []
    for item in schedule:
        cost = (estimate_segment(profile, item["start_enu_m"], item["end_enu_m"])
                if item["kind"] == "segment" else
                estimate_activity(profile, item["activity"], item["duration_s"]))
        parts.append({"input": item, "cost": asdict(cost)})
        costs.append(cost)
    return {"components": parts, "cost": _cost_sum(profile, costs)}


def _margins(profile, budget, cost):
    result = {"time_s": budget["time_s"] - budget["reserve_time_s"] - cost["time_s"],
              "energy_wh": budget["energy_wh"] - budget["reserve_wh"] - cost["energy_wh"]}
    if profile.kind == "human":
        result["oxygen_l"] = budget["oxygen_l"] - budget["reserve_oxygen_l"] - cost["oxygen_l"]
    return {"reserve_margins": result, "resource_feasible": all(value >= 0 for value in result.values())}


def _activity(name, seconds):
    return {"kind": "activity", "activity": name, "duration_s": seconds}


def _segment(start, end):
    return {"kind": "segment", "start_enu_m": list(start), "end_enu_m": list(end)}


def build_vectors(contract_path, *, run_id, activity_pilot_path=None):
    if not re.fullmatch(r"[A-Za-z0-9_-]+", run_id):
        raise ValueError("run_id must contain only letters, digits, hyphens and underscores")
    contract_path = _public_input(contract_path)
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    if (contract["model_id"] != MODEL_ID or contract["status"] != "awaiting_consumer_agreement"
            or contract["comparison_tolerances"] != {"relative": RELATIVE_TOLERANCE, "absolute": ABSOLUTE_TOLERANCE}):
        raise ValueError("Model, pending agreement status and existing tolerances must be retained")
    scenario_path, profiles_path = (_public_input(ROOT / contract[key]) for key in ("scenario_path", "profiles_path"))
    scenario, readiness = validate_experimental_inputs(scenario_path, profiles_path, run_id=run_id)
    profiles = load_profiles(profiles_path)
    if scenario["primary_activity"] != "inspect" or scenario["primary_service_time_s"] != 120:
        raise ValueError("Primary service differs from the approved experimental baseline")
    vectors = []
    for agent, profile in sorted(profiles.items()):
        activity = {"human": scenario["primary_activity"], "rover": "inspect", "drone": "observe"}[profile.kind]
        seconds = scenario["sizing"]["service_s"][agent]
        wait = scenario["sizing"]["wait_allowance_s"][agent]
        cases = [("flat", [_segment((0, 0, 0), (2, 0, 0))]),
                 ("ascent", [_segment((0, 0, 0), (2, 0, 0.1))]),
                 ("descent", [_segment((2, 0, 0.1), (0, 0, 0))]),
                 ("zero", [_segment((0, 0, 0), (0, 0, 0))]),
                 ("ground_vertical_or_drone_climb", [_segment((0, 0, 0), (0, 0, 1))]),
                 ("wait", [_activity("idle", wait)]),
                 ("service", [_activity(activity, seconds)]),
                 ("invalid_duration", [_activity(activity, -1)])]
        if profile.kind == "human":
            cases += [("sampling", [_activity("sample", 180)]), ("light_work", [_activity("inspect", 120)])]
        if profile.kind == "drone":
            cases += [("hover", [_activity("hover", 30)]), ("ground_wait", [_activity("ground_wait", 10)]),
                      ("vertical_descent", [_segment((0, 0, 1), (0, 0, 0))])]
        full = [_segment((0, 0, 0), (2, 0, 0.1)), _activity(activity, seconds),
                _activity("idle", wait), _segment((2, 0, 0.1), (0, 0, 0))]
        cases.append(("directed_itinerary", full))
        for name, schedule in cases:
            row = {"vector_id": f"{agent}-{name}", "agent_id": agent, "agent_kind": profile.kind,
                   "input_kind": "analytic_geometry_and_duration", "schedule": schedule}
            try:
                row["expected"] = {"status": "ESTIMATED", **_schedule(profile, schedule)}
            except ValueError as error:
                row["expected"] = {"status": "MODEL_INPUT_REJECTED", "exception": "ValueError", "detail": str(error)}
            vectors.append(row)
        complete = _schedule(profile, full)["cost"]
        budget = dict(scenario["budgets"][agent])
        boundaries = [{"case": "approved_scenario_allocation", "budget": budget}]
        exact = {**budget, "time_s": complete["time_s"] + budget["reserve_time_s"],
                 "energy_wh": complete["energy_wh"] + budget["reserve_wh"]}
        if profile.kind == "human":
            exact["oxygen_l"] = complete["oxygen_l"] + budget["reserve_oxygen_l"]
        # Preserve exact arithmetic equality of (budget-reserve)-cost at the boundary.
        # Floating addition/subtraction can introduce rounding at a constructed boundary;
        # use representable upper neighbour only when necessary, never a feasibility tolerance.
        for key, reserve in (("time_s", "reserve_time_s"), ("energy_wh", "reserve_wh"), ("oxygen_l", "reserve_oxygen_l")):
            if key in exact:
                while exact[key] - exact[reserve] < complete[key]:
                    exact[key] = math.nextafter(exact[key], math.inf)
        boundaries.append({"case": "representable_feasible_boundary", "budget": exact,
                           "construction": "Cost plus reserve, moved to the next representable upper capacity only if subtraction rounds below the cost; no comparison tolerance credit"})
        for key in ("time_s", "energy_wh", *(("oxygen_l",) if profile.kind == "human" else ())):
            boundaries.append({"case": "below_boundary_" + key, "budget": {**exact, key: exact[key] - 0.002}})
        boundaries.append({"case": "reserve_exceeds_capacity", "budget": {**exact, "energy_wh": exact["reserve_wh"] - 0.002}})
        vectors.append({"vector_id": f"{agent}-resource_boundaries", "agent_id": agent, "agent_kind": profile.kind,
                        "input_kind": "analytic_geometry_and_duration", "schedule": full,
                        "expected": {"status": "ESTIMATED", "cost": complete,
                                     "budget_cases": [{**x, **_margins(profile, x["budget"], complete)} for x in boundaries]}})
        done = [_segment((0, 0, 0), (2, 0, 0.1)), _activity(activity, seconds * 0.375)]
        remaining = [_activity(activity, seconds * 0.625), _activity("idle", wait),
                     _segment((2, 0, 0.1), (0, 0, 0))]
        consumed = _schedule(profile, done)["cost"]
        current = {**budget, "time_s": budget["time_s"] - consumed["time_s"],
                   "energy_wh": budget["energy_wh"] - consumed["energy_wh"]}
        if profile.kind == "human":
            current["oxygen_l"] = budget["oxygen_l"] - consumed["oxygen_l"]
        rest = _schedule(profile, remaining)
        vectors.append({"vector_id": f"{agent}-partial_service_remaining", "agent_id": agent,
            "agent_kind": profile.kind, "input_kind": "analytic_accounting_example_not_execution",
            "already_completed_schedule": done, "already_consumed_cost": consumed,
            "initial_budget": budget, "current_remaining_budget": current, "schedule": remaining,
            "expected": {"status": "ESTIMATED", **rest, **_margins(profile, current, rest["cost"]),
                         "completed_plus_remaining_cost": {key: consumed[key] + rest["cost"][key] if consumed[key] is not None else None for key in consumed},
                         "original_complete_cost": complete}})
    pilot = None
    if activity_pilot_path is not None:
        activity_pilot_path = _public_input(activity_pilot_path)
        pilot = json.loads(activity_pilot_path.read_text(encoding="utf-8"))
        if pilot.get("schema_version") != "1.0.0" or pilot.get("status") not in {"proposed", "pending_review"}:
            raise ValueError("Activity pilot must remain explicitly proposed/pending review")
        if not isinstance(pilot.get("cases"), list) or not pilot["cases"]:
            raise ValueError("Activity pilot requires nonempty analytic cases")
        seen = set()
        for item in pilot["cases"]:
            case_id, agent = item["case_id"], item["agent_id"]
            if not re.fullmatch(r"[A-Za-z0-9_-]+", case_id) or case_id in seen or agent not in profiles:
                raise ValueError("Activity pilot requires unique case IDs and registered agents")
            if (not isinstance(item.get("source_url"), str) or not item["source_url"].startswith("https://")
                    or not isinstance(item.get("source_locator"), str) or not item["source_locator"].strip()):
                raise ValueError("Activity pilot cases need an explicit source and locator")
            seen.add(case_id)
            if "schedule" in item:
                if "activity" in item or "duration_s" in item:
                    raise ValueError("Pilot case must use a mixed schedule or one activity/duration, not both")
                phases = item["schedule"]
                if (not isinstance(phases, list) or not phases
                        or any(not isinstance(phase, dict) or set(phase) != {"activity", "duration_s"} for phase in phases)):
                    raise ValueError("Mixed pilot schedule requires explicit activity/duration phases")
                schedule = [_activity(phase["activity"], phase["duration_s"]) for phase in phases]
            else:
                schedule = [_activity(item["activity"], item["duration_s"])]
            vectors.append({"vector_id": "activity-pilot-" + case_id, "agent_id": agent,
                            "agent_kind": profiles[agent].kind, "input_kind": "analytic_activity_pilot_not_execution",
                            "pilot_input": item, "schedule": schedule,
                            "expected": {"status": "ESTIMATED", **_schedule(profiles[agent], schedule)}})
    model_source = ROOT / "src/mge_mission/mge_mission/models.py"
    report = {"schema_version": "1.0.0", "run_id": run_id, "kind": "COST_AGREEMENT_VECTORS",
            "contract_id": contract["contract_id"], "status": "AWAITING_CONSUMER_AGREEMENT",
            "model_id": MODEL_ID, "scientific_approval": False, "cost_agreement_approved": False,
            "mission_execution_authorized": False, "integrated_mission_executed": False,
            "tolerances": contract["comparison_tolerances"],
            "profile_approval_states": {key: value.approval_status for key, value in profiles.items()},
            "profile_inputs": {key: {"kind": p.kind, "parameters": dict(p.parameters), "activity_power_w": dict(p.activity_power_w)} for key, p in profiles.items()},
            "inputs_sha256": {"contract": _sha(contract_path), "scenario": _sha(scenario_path),
                              "profiles": _sha(profiles_path), "model_source": _sha(model_source),
                              "exporter_source": _sha(Path(__file__))},
            "scenario_readiness": readiness,
            "limitations": ["Analytic vectors only; no planner, executor, terrain observation, task or mission runs.",
                            "Geometry/sigma/clearance are not established by a cost estimate.",
                            "Partial-service states are accounting examples, not invented execution evidence.",
                            "Passing finite comparisons alone approves neither profiles nor scientific error bounds.",
                            "No ROS field or activity/context binding is changed; consumer agreement remains required."],
            "vectors": vectors}
    if pilot is not None:
        report["activity_pilot"] = pilot
        report["inputs_sha256"]["activity_pilot"] = _sha(activity_pilot_path)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--contract", type=Path, default=ROOT / "config/cost_agreement.experimental.json")
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--activity-pilot", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    report = build_vectors(args.contract, run_id=args.run_id, activity_pilot_path=args.activity_pilot)
    report.update(recorded_at_utc=datetime.now(timezone.utc).isoformat(), command=[sys.executable, *sys.argv])
    for field, command in (("source_revision", ["git", "rev-parse", "HEAD"]),
                           ("working_tree_dirty", ["git", "status", "--porcelain"])):
        result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=False)
        report[field] = (bool(result.stdout.strip()) if field == "working_tree_dirty" else result.stdout.strip()) if result.returncode == 0 else None
    target = args.output_dir.resolve()
    if any(x.casefold() in {"reference", ".git", ".env"} for x in target.parts):
        raise ValueError("Output must remain outside private/evaluator paths")
    target.mkdir(parents=True, exist_ok=False)
    with (target / "cost_vectors.json").open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(json.dumps(report, indent=2, allow_nan=False) + "\n")
    print(f"Recorded {len(report['vectors'])} analytic vectors; cost agreement remains pending.")


if __name__ == "__main__":
    main()
