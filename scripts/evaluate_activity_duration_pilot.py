"""Compare analytical activity costs with approved experimental budgets; no execution."""

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from size_jezero_proposal import build_report
from export_cost_agreement_vectors import validate_experimental_inputs
from mge_mission.scenario import experimental_values


def evaluate(vectors_path, *, run_id):
    path = vectors_path.resolve(strict=True)
    if any(p.casefold() in {"reference", ".git", ".env"} for p in path.parts):
        raise ValueError("Use public cost vectors only")
    vectors = json.loads(path.read_text(encoding="utf-8"),
                         parse_constant=lambda x: (_ for _ in ()).throw(ValueError(x)))
    original = ROOT / "config/mission_jezero.proposed.yaml"
    config_path = ROOT / "config/mission_jezero.experimental.yaml"
    base = build_report(original, run_id=run_id)
    original_config = yaml.safe_load(original.read_text(encoding="utf-8"))
    config, readiness = validate_experimental_inputs(config_path, ROOT / original_config["profiles_path"], run_id=run_id)
    if experimental_values(config) != experimental_values(original_config):
        raise ValueError("Analytical baseline must retain the approved experimental values")
    expected = base["readiness"]["inputs_sha256"]
    if (vectors["inputs_sha256"]["profiles"] != expected["profiles"]
            or vectors["inputs_sha256"]["model_source"] != expected["model_source"]
            or vectors["inputs_sha256"]["scenario"] != hashlib.sha256(config_path.read_bytes()).hexdigest()):
        raise ValueError("Compare identical model, profiles and scenario versions")
    human = base["probes"][0]["nominal"]
    rows = []
    for vector in vectors["vectors"]:
        item = vector.get("pilot_input")
        if item is None:
            continue
        if vector["agent_id"] != "human_1":
            raise ValueError("This pilot assesses human workflow durations only")
        application = item["application"]
        cost = vector["expected"]["cost"]
        row = {"case_id": item["case_id"], "evidence_kind": item["evidence_kind"],
               "task_scope": item["task_scope"], "application": application,
               "activity_cost": cost, "task_assigned": False, "operational_authorization": False}
        if application == "comparison_only":
            row["combined_mission_cost"] = None
        elif application in {"replace_primary_service", "additional_after_primary"}:
            total = {key: human["total"][key] + cost[key] - (
                human["service"][key] if application == "replace_primary_service" else 0)
                for key in cost}
            budget = config["budgets"]["human_1"]
            margins = {metric: budget[capacity] - budget[reserve] - total[metric]
                       for metric, capacity, reserve in (("time_s", "time_s", "reserve_time_s"),
                       ("energy_wh", "energy_wh", "reserve_wh"), ("oxygen_l", "oxygen_l", "reserve_oxygen_l"))}
            row.update(combined_mission_cost=total, reserve_margins=margins,
                       resource_envelope_fits=all(v >= 0 for v in margins.values()))
        else:
            raise ValueError("Pilot application must be explicit")
        rows.append(row)
    if not rows:
        raise ValueError("Activity pilot vectors are required")
    return {"schema_version": "1.0.0", "run_id": run_id, "kind": "ANALYTIC_ACTIVITY_DURATION_PILOT",
            "status": "PENDING_DURATION_REVIEW", "approved_values_changed": False,
            "cost_agreement_approved": False, "scientific_approval": False,
            "integrated_mission_executed": False, "mission_execution_authorized": False,
            "baseline_primary_probe": human, "cases": rows,
            "scenario_readiness": readiness,
            "baseline_readiness_inputs_sha256": base["readiness"]["inputs_sha256"],
            "inputs_sha256": {"vectors": hashlib.sha256(path.read_bytes()).hexdigest(),
                "original_proposal": hashlib.sha256(original.read_bytes()).hexdigest(),
                "approved_scenario": hashlib.sha256(config_path.read_bytes()).hexdigest(),
                "model": expected["model_source"], "profiles": expected["profiles"],
                "analysis_source": hashlib.sha256(Path(__file__).read_bytes()).hexdigest()},
            "implementation_sha256": {relative: hashlib.sha256((ROOT / relative).read_bytes()).hexdigest()
                for relative in ("scripts/size_jezero_proposal.py", "scripts/export_cost_agreement_vectors.py",
                    "src/mge_mission/mge_mission/scenario.py", "src/mge_data/mge_data/core.py")},
            "limitations": ["Public-prior cost probes only, no route or execution evidence.",
                "Additional sample cases add a separate workflow after the approved primary check-in; do not add primitive collection time again inside a complete workflow.",
                "No optional travel, extra coordination delay or suit losses are included; actual assignments may cost more.",
                "Replacing primary service is a proposed sensitivity, not a modification of JZ-P03.",
                "Reported analog totals are not measured Mars task durations; mixed power allocation is an engineering assumption."]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--vectors", type=Path, required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    report = evaluate(args.vectors, run_id=args.run_id)
    report.update(recorded_at_utc=datetime.now(timezone.utc).isoformat(), command=[sys.executable, *sys.argv])
    for field, command in (("source_revision", ["git", "rev-parse", "HEAD"]),
                           ("working_tree_dirty", ["git", "status", "--porcelain"])):
        result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=False)
        report[field] = (bool(result.stdout.strip()) if field == "working_tree_dirty" else result.stdout.strip()) if result.returncode == 0 else None
    if any(p.casefold() in {"reference", ".git", ".env"} for p in args.output_dir.resolve().parts):
        raise ValueError("Output must remain outside evaluator/private paths")
    args.output_dir.mkdir(parents=True, exist_ok=False)
    with (args.output_dir / "activity_pilot_impact.json").open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(json.dumps(report, indent=2, allow_nan=False) + "\n")
    print(f"Recorded {len(report['cases'])} analytical activity cases; approved scenario unchanged.")


if __name__ == "__main__":
    main()
