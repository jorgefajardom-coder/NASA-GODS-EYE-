"""Record reproducible formula checks, never NASA observations or a live run."""

import argparse
from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src" / "mge_mission"))

from mge_mission.models import MODEL_ID, estimate_activity, estimate_segment, load_profiles


def build_record(profile_path: Path, run_id: str) -> dict:
    profiles = load_profiles(profile_path)
    rows = []
    for agent_id, profile in sorted(profiles.items()):
        # Synthetic directed geometry: these coordinates do not depict Mars data.
        cases = (
            ("flat", (0.0, 0.0, 0.0), (10.0, 0.0, 0.0)),
            ("uphill", (0.0, 0.0, 0.0), (10.0, 0.0, 1.0)),
            ("downhill", (10.0, 0.0, 1.0), (0.0, 0.0, 0.0)),
        )
        for name, start, end in cases:
            cost = estimate_segment(profile, start, end)
            rows.append(dict(agent_id=agent_id, case=name, input_kind="synthetic_geometry",
                             start_enu_m=start, end_enu_m=end, **asdict(cost)))
        activity = {"human": "sample", "rover": "inspect", "drone": "observe"}[profile.kind]
        for name in ("idle", activity):
            rows.append(dict(agent_id=agent_id, case=name, input_kind="synthetic_duration",
                             duration_s=30.0, **asdict(estimate_activity(profile, name, 30.0))))
    revision = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True,
                              capture_output=True, check=False)
    git_status = subprocess.run(["git", "status", "--porcelain"], cwd=ROOT, text=True,
                                capture_output=True, check=False)
    return {
        "schema_version": "1.0.0", "run_id": run_id,
        "recorded_at_utc": datetime.now(timezone.utc).isoformat(),
        "mode": "MODEL_CHECK", "implementation_revision": revision.stdout.strip() or None,
        "working_tree_dirty": bool(git_status.stdout.strip()) if git_status.returncode == 0 else None,
        "model_id": MODEL_ID, "profile_sha256": hashlib.sha256(profile_path.read_bytes()).hexdigest(),
        "model_source_sha256": hashlib.sha256((ROOT / "src/mge_mission/mge_mission/models.py").read_bytes()).hexdigest(),
        "checker_source_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "profile_states": {key: item.approval_status for key, item in profiles.items()},
        "profile_inputs": {
            key: {"kind": item.kind, "capabilities": item.capabilities,
                  "model_id": item.model_id, "approval_status": item.approval_status,
                  "parameters": dict(item.parameters), "activity_power_w": dict(item.activity_power_w)}
            for key, item in profiles.items()
        },
        "scientific_acceptance": False, "observational_nasa_data": False,
        "integrated_mission_executed": False, "datasets_used": [], "seed": None,
        "command": [sys.executable, *sys.argv],
        "limitations": ["Formula estimates on synthetic geometry and durations only.",
                        "No ROS, simulator, hidden reference, real traversal or task execution.",
                        "Proposed profiles remain proposed regardless of formula-check success."],
        "results": rows,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profiles", type=Path,
                        default=ROOT / "config" / "science_profiles.proposed.json")
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    if not args.run_id or any(char not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-" for char in args.run_id):
        parser.error("run-id must contain only letters, digits, hyphens and underscores")
    record = build_record(args.profiles.resolve(), args.run_id)
    destination = args.output_dir.resolve()
    destination.mkdir(parents=True, exist_ok=True)
    # An existing evidence record is immutable. Reruns need another run ID/path.
    target = destination / "model_checks.json"
    with target.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(record, stream, indent=2, allow_nan=False)
        stream.write("\n")
    print(f"Recorded {len(record['results'])} synthetic formula estimates: {target}")


if __name__ == "__main__":
    main()
