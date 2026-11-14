"""Export offline sensitivity checks using explicit, illustrative scenario inputs."""

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src/mge_mission"))

from mge_mission.models import load_profiles
from mge_mission.sensitivity import SensitivityCase, sweep
from mge_mission.types import Budgets


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profiles", type=Path, default=ROOT / "config/science_profiles.proposed.json")
    parser.add_argument("--scenario", type=Path, default=ROOT / "config/scenario_demo.yaml")
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    registry = json.loads(args.profiles.read_text(encoding="utf-8"))
    scenario = yaml.safe_load(args.scenario.read_text(encoding="utf-8"))
    cases = []
    for item in scenario["sensitivity_cases"]:
        data = dict(item)
        data["budgets"] = Budgets(**{
            "oxygen_l": None, "reserve_oxygen_l": None,
            **scenario["mission"]["budgets"][data["agent_id"]]})
        cases.append(SensitivityCase(**data))
    report = sweep(load_profiles(args.profiles), registry["assumptions"], cases)
    report.update(run_id=args.run_id, command=[sys.executable, *sys.argv],
                  scenario_status=scenario["status"], model_id=registry["model_id"])
    revision = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=True)
    status = subprocess.run(["git", "status", "--porcelain"], cwd=ROOT, capture_output=True, text=True, check=True)
    report.update(source_revision=revision.stdout.strip(), working_tree_dirty=bool(status.stdout.strip()))
    report["inputs_sha256"] = {str(path.relative_to(ROOT) if path.is_relative_to(ROOT) else path):
        hashlib.sha256(path.read_bytes()).hexdigest() for path in (
            args.profiles.resolve(), args.scenario.resolve(), Path(__file__).resolve(),
            ROOT / "src/mge_mission/mge_mission/sensitivity.py",
            ROOT / "src/mge_mission/mge_mission/models.py")}
    args.output_dir.mkdir(parents=True, exist_ok=False)
    with (args.output_dir / "sensitivity.json").open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(json.dumps(report, indent=2, allow_nan=False) + "\n")
    print(f"Recorded {len(report['results'])} model rows; no mission executed.")


if __name__ == "__main__":
    main()
