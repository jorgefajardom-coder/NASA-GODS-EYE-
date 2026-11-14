"""Demonstrate that the newly imported orbital prior is not a verified corridor."""

import argparse
from dataclasses import asdict
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src/mge_planning"))

from mge_planning.adapter import load_profiles, load_unverified_prior
from mge_planning.core import PlanRequest, ResourceBudget, RouteStatus, plan_route


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=ROOT / "data/planner_provisional/manifest.json")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    grid = load_unverified_prior(args.manifest, run_id="provisional-ctx-prior-check")
    profile = load_profiles(ROOT / "config/planner_profiles.illustrative.json", True)["human_1"]
    start, goal = grid.point((0, 0)), grid.point((grid.rows-1, grid.cols-1))
    request = PlanRequest(grid.run_id, "prior-is-not-observation", "human_1", "human", 0,
                          start, goal, ResourceBudget("human", 10000, 10000, 10, 1000, 10), return_to=start)
    result = plan_route(terrain=grid, request=request, profile=profile)
    record = {"created_utc": datetime.now(timezone.utc).isoformat(),
              "commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
              "source_manifest": str(args.manifest.relative_to(ROOT)) if args.manifest.is_relative_to(ROOT) else args.manifest.name,
              "provenance": "Real CTX orbital prior; illustrative budget/profile; no local observations",
              "result": asdict(result)}
    content = json.dumps(record, indent=2, allow_nan=False) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open("x", encoding="utf-8") as stream:
            stream.write(content)
        print(f"Recorded {result.status.value}: {result.reason_code}")
    else:
        print(content)
    return 0 if result.status == RouteStatus.UNKNOWN and not result.route_id else 1


if __name__ == "__main__":
    raise SystemExit(main())
