"""Quiet serial reruns of every adverse SAFE/SEARCH_LIMIT primary query.

This diagnostic preserves the original primary catalogue and does not simulate
new execution, replace outcomes, or upgrade unresolved searches into successes.
"""
from dataclasses import replace
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
import time

import numpy as np

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parent.parent
SOURCE = ROOT / "frozen-main"
sys.path[:0] = [str(SOURCE / "src" / name) for name in ("mge_mission", "mge_planning", "mge_mapping", "mge_data")]
import mge_mission
mge_mission.__path__.append(str(REPO / "src/mge_mission/mge_mission"))
from mge_mapping.core import BeliefMap, SimulatedObservation, fuse_observation
from mge_mission.models import load_profiles
from mge_mission.research.rigid_adaptive import _plan
from mge_planning.core import MotionProfile


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def credit(episode):
    return (episode.get("primary_completed") is True and episode.get("returned") is True
            and episode.get("resource_violation") is False
            and episode.get("reserve_violation") is False and episode.get("unknown") is False)


def run(directory, output):
    directory, output = Path(directory), Path(output)
    manifest = read(directory / "manifest.json")
    for name, lock in manifest["imported_module_locks"].items():
        assert sha(lock["path"]) == lock["sha256"], ("source changed", name)
    raw = (directory / "paired-blocks.jsonl").read_bytes()
    assert raw.endswith(b"\n"), "Journal may still be appending; wait for the closed catalogue"
    profiles = load_profiles(manifest["config"]["profiles_path"])
    selected = []
    for line in raw.decode("utf-8").splitlines():
        envelope = json.loads(line)
        block = envelope["payload"]
        for pair in block.get("pairs", []):
            strategies = pair.get("strategies", {})
            if pair.get("mode") != "SAFE" or set(strategies) != {"RIGID", "ADAPTIVE"}:
                continue
            adaptive, rigid = strategies["ADAPTIVE"], strategies["RIGID"]
            searches = adaptive.get("searches", [])
            if (credit(rigid) and not credit(adaptive) and searches
                    and searches[0].get("status") == "UNKNOWN"
                    and searches[0].get("reason_code") == "SEARCH_LIMIT"):
                selected.append((envelope, block, pair))
    if output.exists():
        raise FileExistsError("Refuse to overwrite diagnostic output")
    output.mkdir(parents=True)
    lock = {"classification": "SEPARATE_SERIAL_LOAD_DIAGNOSTIC_NOT_PRIMARY_OUTCOME_REPLACEMENT",
            "started_at_utc": datetime.now(timezone.utc).isoformat(),
            "input_manifest_sha256": sha(directory / "manifest.json"),
            "input_journal_sha256": hashlib.sha256(raw).hexdigest(),
            "script_sha256": sha(__file__), "selected_conditions": len(selected),
            "selection": "ALL original SAFE conditions with RIGID completion credit, no ADAPTIVE completion credit, and posterior-primary UNKNOWN/SEARCH_LIMIT",
            "limits": manifest["config"]["search_limits"],
            "rule": "One serial repeat each, original limits and exact public state; preserve success and failure alike; no primary estimates are replaced",
            "quiet_execution": "Caller must stop other experiment workers first; this script does not inspect or terminate other processes",
            "conditions": [{"block_id": b["block_id"], "condition_id": p["condition_id"],
                            "source_payload_sha256": e["payload_sha256"]} for e, b, p in selected]}
    (output / "manifest.json").write_text(json.dumps(lock, indent=2, ensure_ascii=False), encoding="utf-8")
    results = []
    with (output / "queries.jsonl").open("x", encoding="utf-8") as stream:
        for envelope, block, pair in selected:
            record = read(block["record_path"])
            with np.load(block["map_path"], allow_pickle=False) as arrays:
                elevation = np.asarray(arrays["elevation_m"], dtype=float)
                elevation[~arrays["valid_mask"].astype(bool)] = np.nan
            belief = BeliefMap.from_arrays(elevation, run_id=block["block_id"], dataset_id=record["id"],
                resolution_m=4., origin_x_m=record["origin_x_m"], origin_y_m=record["origin_y_m"])
            belief = fuse_observation(belief, SimulatedObservation(**pair["common_observation"]))
            profile = profiles[pair["agent_id"]]
            profile = replace(profile, parameters={**profile.parameters,
                "max_sigma_m": manifest["config"].get("max_sigma_m", 3.)}, approval_status="illustrative")
            motion = MotionProfile(**pair["motion_profile"])
            completed_work = [entry for entry in pair["strategies"]["RIGID"]["service_ledger"]
                              if entry.get("label") == "primary-B-service"]
            assert completed_work, "Adverse-case rigid credit requires actual primary service interval"
            services = [(entry["activity"], entry["duration_s"]) for entry in completed_work]
            start = time.perf_counter()
            result, query = _plan(belief, record, profile, motion, pair["common_reached"][-1],
                block["goal"], block["base"], pair["common_remaining"], pair["reserves"],
                services, pair["mode"], manifest["config"]["search_limits"], "posterior-primary")
            item = {"block_id": block["block_id"], "condition_id": pair["condition_id"],
                "source_payload_sha256": envelope["payload_sha256"],
                "original": pair["strategies"]["ADAPTIVE"]["searches"][0], "serial_repeat": query,
                "reconstructed_map_version": belief.map_version, "actual_start_xyz": pair["common_reached"][-1],
                "remaining_resources": pair["common_remaining"], "reserves": pair["reserves"],
                "service_schedule": services, "wall_s": time.perf_counter()-start,
                "execution_rerun": False, "primary_outcome_replaced": False}
            stream.write(json.dumps(item, ensure_ascii=False, allow_nan=False)+"\n")
            stream.flush()
            results.append(item)
            print(json.dumps({"completed": len(results), "total": len(selected),
                              "block_id": block["block_id"], "condition_id": pair["condition_id"],
                              "serial_status": query["status"]}), flush=True)
    counts = {}
    for item in results:
        status = item["serial_repeat"]["status"]
        counts[status] = counts.get(status, 0)+1
    summary = {"ended_at_utc": datetime.now(timezone.utc).isoformat(), "queries": len(results),
               "statuses": counts, "queries_sha256": sha(output / "queries.jsonl"),
               "classification": lock["classification"]}
    (output / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary


if __name__ == "__main__":
    print(json.dumps(run(sys.argv[1], sys.argv[2]), ensure_ascii=False, allow_nan=False))
