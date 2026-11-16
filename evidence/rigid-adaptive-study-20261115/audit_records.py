"""Independent, read-only record audit of the paired analytical study."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys

REPO = Path(__file__).resolve().parents[2]
if REPO.name == ".local":
    REPO = REPO.parent
SOURCE = Path(__file__).resolve().parent / "frozen-main"
sys.path.insert(0, str(SOURCE / "src/mge_mission"))
from mge_mission.models import load_profiles, estimate_segment, estimate_activity


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                    ensure_ascii=False, allow_nan=False).encode()).hexdigest()


def audit(directory):
    directory = Path(directory)
    manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
    for name, lock in manifest["imported_module_locks"].items():
        assert sha(lock["path"]) == lock["sha256"], ("source mutated", name)
    profiles = load_profiles(manifest["config"]["profiles_path"])
    data = (directory / "paired-blocks.jsonl").read_bytes()
    assert data.endswith(b"\n"), "Concurrent append or truncated final line: retry without changing the journal"
    counts = dict(blocks=0, conditions=0, paired_episodes=0, explicit_unavailable=0,
                  observations=0, movement_intervals=0, activity_intervals=0)
    ids = set()
    for number, line in enumerate(data.decode("utf-8").splitlines(), 1):
        envelope = json.loads(line)
        assert envelope["seq"] == number
        assert envelope["identity"] == manifest["identity"]
        assert envelope["payload_sha256"] == digest(envelope["payload"])
        block = envelope["payload"]
        assert block["block_id"] not in ids
        ids.add(block["block_id"])
        counts["blocks"] += 1
        if "world_metadata" in block:
            assert block["world_metadata"]["full_world_exposed"] is False
        for pair in block.get("pairs", []):
            counts["conditions"] += 1
            assert set(pair["strategies"]) == {"RIGID", "ADAPTIVE"}
            if pair["status"] != "PAIRED":
                counts["explicit_unavailable"] += 1
                continue
            assert pair["same_initial_candidate"] and pair["same_world"]
            assert pair["same_paid_observation_and_reached_prefix"]
            observation = pair["common_observation"]
            assert observation["source_kind"] == "SIMULATED"
            assert observation["source_map_version"] == 1
            assert observation["timestamp_sim_s"] >= 0
            assert pair["opportunity"]["activity"] == "inspect"
            counts["observations"] += 1
            profile = profiles[pair["agent_id"]]
            for strategy, result in pair["strategies"].items():
                counts["paired_episodes"] += 1
                ledger = result["service_ledger"]
                previous = None
                for interval in ledger:
                    if interval["kind"] == "movement":
                        if previous is not None:
                            assert interval["start"] == previous, (block["block_id"], strategy, "teleport")
                        previous = interval["end"]
                        expected = estimate_segment(profile, interval["start"], interval["end"])
                        counts["movement_intervals"] += 1
                    else:
                        expected = estimate_activity(profile, interval["activity"], interval["duration_s"])
                        counts["activity_intervals"] += 1
                    for component in ("time_s", "energy_wh", "oxygen_l"):
                        actual = interval["cost"][component]
                        predicted = getattr(expected, component)
                        assert actual is None if predicted is None else abs(actual - predicted) < 1e-9
                for component, gross in pair["gross"].items():
                    if gross is None:
                        assert result["remaining"][component] is None
                        continue
                    consumed = sum(interval["cost"][component] for interval in ledger)
                    assert abs(gross-consumed-result["remaining"][component]) < 1e-6
                    assert result["remaining"][component] >= pair["reserves"][component]-1e-10
                if result["returned"]:
                    assert all(abs(a-b) < 1e-6 for a, b in zip(result["pose"], block["base"]))
                if result["primary_completed"]:
                    assert sum(x.get("label") == "primary-B-service" for x in ledger) == 1
                if result["optional_completed"]:
                    assert result["primary_completed"]
                    assert sum(x.get("label") == pair["opportunity"]["event_id"] for x in ledger) == 1
    return {"classification": "SIMULATED_ANALYTICAL_RECORD_AUDIT_NOT_OPERATIONAL_ACCEPTANCE",
            "audited_at_utc": datetime.now(timezone.utc).isoformat(),
            "directory": str(directory.resolve()), "manifest_sha256": sha(directory / "manifest.json"),
            "journal_sha256": hashlib.sha256(data).hexdigest(), "journal_bytes": len(data),
            "auditor_sha256": sha(__file__), "module_hashes_verified": len(manifest["imported_module_locks"]),
            "checks": "PASS", "counts": counts,
            "limits": ["Read-only prefix snapshot while workers may append later records",
                       "No physical, ROS, sensor, geological or scientific-profile approval",
                       "Unavailable conditions have no executed itinerary; safety cannot be inferred for unattempted motion"]}


if __name__ == "__main__":
    print(json.dumps(audit(sys.argv[1]), indent=2, ensure_ascii=False, allow_nan=False))
