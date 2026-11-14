"""Diagnose the data owner's public scenario without planning or executing it."""

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
for package in ("mge_mission", "mge_data"):
    sys.path.insert(0, str(ROOT / "src" / package))

from mge_mission.scenario import diagnose


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=ROOT / "data/sample/manifest.json")
    parser.add_argument("--profiles", type=Path, default=ROOT / "config/science_profiles.proposed.json")
    parser.add_argument("--mission", type=Path, default=ROOT / "config/mission.yaml")
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    if not re.fullmatch(r"[A-Za-z0-9_-]+", args.run_id):
        parser.error("run-id must contain only letters, digits, underscores and hyphens")
    report = diagnose(args.manifest, args.profiles, args.mission, run_id=args.run_id)
    report["recorded_at_utc"] = datetime.now(timezone.utc).isoformat()
    report["command"] = [sys.executable, *sys.argv]
    revision = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT,
                              text=True, capture_output=True, check=False)
    status = subprocess.run(["git", "status", "--porcelain"], cwd=ROOT,
                            text=True, capture_output=True, check=False)
    report["implementation_revision"] = revision.stdout.strip() if revision.returncode == 0 else None
    report["working_tree_dirty"] = bool(status.stdout.strip()) if status.returncode == 0 else None
    report["implementation_sha256"] = {
        str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in (Path(__file__).resolve(), ROOT / "src/mge_mission/mge_mission/scenario.py",
                     ROOT / "src/mge_data/mge_data/core.py")}
    output = args.output_dir.resolve()
    if any(part.casefold() in {"reference", ".git", ".env"} for part in output.parts):
        parser.error("output must stay outside evaluator/private paths")
    output.mkdir(parents=True, exist_ok=False)
    for filename, data in (("scenario_diagnostic.json", report),
                           ("mission_candidate.json", report["candidate_configuration"])):
        with (output / filename).open("x", encoding="utf-8", newline="\n") as stream:
            json.dump(data, stream, indent=2, allow_nan=False)
            stream.write("\n")
    print(f"{report['status']}: dataset={report['dataset_status']}; "
          f"missing={len(report['missing_inputs'])}; findings={len(report['findings'])}; no mission executed")
    return 2 if report["status"] == "NOT_READY" else 0


if __name__ == "__main__":
    raise SystemExit(main())
