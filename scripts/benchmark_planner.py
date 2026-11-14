"""Measure newly generated illustrative planner cases; no physical claims.

Run from the repository root. Nothing is written unless --output is provided.
Each sample includes its actual measured latency, result and synthetic seed.
"""

import argparse
from dataclasses import asdict
from datetime import datetime, timezone
import heapq
import json
import math
from pathlib import Path
import platform
import subprocess
import sys
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src/mge_planning"))

import numpy as np

from mge_planning.core import (
    MotionProfile, PlanRequest, ResourceBudget, SearchLimits, TerrainGrid,
    plan_route,
)


def make_case(seed):
    """An illustrative flat map with a preserved public corridor, generated now."""
    random = np.random.default_rng(seed)
    mask = np.where(random.random((16, 16)) < 0.12, 100, 0).astype(np.int8)
    mask[2, 2:14] = 0
    mask[2:14, 13] = 0
    terrain = TerrainGrid(f"illustrative-benchmark-{seed}", 1,
                          np.zeros(mask.shape), mask, 1.0)
    profile = MotionProfile(
        agent_kind="rover", speed_m_s=1.0, max_slope_deg=85.0,
        max_step_m=10.0, radius_m=0.0, localization_error_m=0.0,
        energy_wh_per_m=1.0,
    )
    request = PlanRequest(
        run_id=terrain.run_id, request_id=f"seed-{seed}", agent_id="rover_1",
        agent_kind="rover", map_version=1, start=(2.5, 2.5, 0.0),
        goal=(13.5, 13.5, 0.0), return_to=(2.5, 2.5, 0.0),
        require_return=True, budget=ResourceBudget("rover", 1000.0, 1000.0, 0.0),
    )
    return terrain, profile, request


def reference_distance(mask, start=(2, 2), goal=(13, 13)):
    """Independent Dijkstra on this flat, point-agent, known-cell graph."""
    rows, cols = mask.shape
    best = {start: 0.0}
    queue = [(0.0, start)]
    while queue:
        cost, cell = heapq.heappop(queue)
        if cost != best[cell]:
            continue
        if cell == goal:
            return cost
        row, col = cell
        for dr in (-1, 0, 1):
            for dc in (-1, 0, 1):
                if dr == dc == 0:
                    continue
                nr, nc = row + dr, col + dc
                if not (0 <= nr < rows and 0 <= nc < cols) or mask[nr, nc] != 0:
                    continue
                if dr and dc and (mask[row, nc] != 0 or mask[nr, col] != 0):
                    continue
                new_cost = cost + math.hypot(dr, dc)
                if new_cost < best.get((nr, nc), math.inf):
                    best[(nr, nc)] = new_cost
                    heapq.heappush(queue, (new_cost, (nr, nc)))
    return math.inf


def _commit():
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def run_benchmark(seeds=(7, 19, 41), repeats=3):
    if repeats < 1 or not seeds:
        raise ValueError("provide at least one seed and one repeat")
    samples = []
    limits = SearchLimits(max_labels=200000, timeout_s=10.0)
    for seed in seeds:
        terrain, profile, request = make_case(seed)
        expected = 2.0 * reference_distance(terrain.traversability)
        for repeat in range(repeats):
            started = perf_counter()
            result = plan_route(terrain=terrain, request=request, profile=profile,
                                limits=limits)
            elapsed_ms = (perf_counter() - started) * 1000.0
            status = getattr(result.status, "value", result.status)
            samples.append({
                "seed": seed, "repeat": repeat, "run_id": request.run_id,
                "request_id": request.request_id, "map_version": 1,
                "status": status, "reason_code": result.reason_code,
                "route_id": result.route_id, "latency_ms": elapsed_ms,
                "travel_time_s": result.travel_time_s,
                "energy_est_wh": result.energy_est_wh,
                "min_clearance_m": result.min_clearance_m,
                "expanded_labels": result.expanded_labels,
                "reference_roundtrip_time_s": expected,
                "matches_reference": status == "FEASIBLE" and
                    math.isclose(result.travel_time_s, expected, rel_tol=1e-9),
                "outbound_path": result.outbound_path,
                "return_path": result.return_path,
            })
    latencies = [sample["latency_ms"] for sample in samples]
    return {
        "schema_version": "1.0.0",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "commit": _commit(),
        "provenance": "SIMULATED: newly generated illustrative acceptance grids",
        "source": "scripts/benchmark_planner.py; no previous Sandbox run imported",
        "limitations": [
            "Point-agent flat-grid benchmark with illustrative resource rates.",
            "No real NASA terrain or approved scientific profile is evaluated.",
            "Latency is measured for this machine and invocation, not a guarantee.",
        ],
        "environment": {"python": platform.python_version(),
                        "platform": platform.platform(), "numpy": np.__version__},
        "configuration": {"seeds": list(seeds), "repeats": repeats,
                          "rows": 16, "cols": 16, "resolution_m": 1.0,
                          "obstacle_probability": 0.12,
                          "profile": asdict(profile), "limits": asdict(limits)},
        "latency_ms": {"p50": float(np.percentile(latencies, 50)),
                       "p95": float(np.percentile(latencies, 95)),
                       "sample_count": len(samples)},
        "all_match_reference": all(s["matches_reference"] for s in samples),
        "samples": samples,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path,
                        help="Write a new JSON artifact; refuses to overwrite one")
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--seeds", type=int, nargs="+", default=[7, 19, 41])
    args = parser.parse_args()
    report = run_benchmark(tuple(args.seeds), args.repeats)
    content = json.dumps(report, indent=2, allow_nan=False) + "\n"
    if args.output is None:
        print(content, end="")
    else:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open("x", encoding="utf-8") as stream:
            stream.write(content)
        print(f"Wrote {len(report['samples'])} measured samples to {args.output}")
    return 0 if report["all_match_reference"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
