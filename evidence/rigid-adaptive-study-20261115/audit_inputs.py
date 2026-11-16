"""Closing byte-level verification of all experimental source/input locks."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def audit():
    closure = read(ROOT / "input-closure.json")
    files = []
    for item in closure["files"]:
        runtime = Path(item["runtime_path"])
        snapshot = ROOT / "runtime-snapshot" / item["snapshot_path"]
        assert sha(runtime) == item["sha256"], ("runtime input changed", str(runtime))
        assert sha(snapshot) == item["sha256"], ("snapshot mismatch", str(snapshot))
        files.append({"path": item["snapshot_path"], "sha256": item["sha256"]})
    batches = []
    for name in ("results", "directed-results", "strict-sigma-controls", "published-step-controls", "extended-1024-results"):
        directory = ROOT / name
        if not (directory / "manifest.json").exists():
            continue
        manifest = read(directory / "manifest.json")
        assert manifest["config"]["source_sha"] == closure["published_main_sha"]
        for module, item in manifest["imported_module_locks"].items():
            assert sha(item["path"]) == item["sha256"], (name, "source mutated", module)
        assert sha(manifest["config"]["script_path"]) == manifest["script_sha256"]
        cfg = manifest["config"]
        profile_path = Path(cfg["profiles_path"])
        profile_lock = next(item for item in closure["files"] if item["snapshot_path"] == "config/science_profiles.proposed.json")
        assert sha(profile_path) == profile_lock["sha256"]
        map_checks = []
        for item in manifest["map_locks"]:
            record_path = Path(item["record_path"])
            assert sha(record_path) == item["record_sha256"]
            record = read(record_path)
            terrain = record_path.parent / Path(record["path"]).name
            assert sha(terrain) == item["map_sha256"] == record["file_sha256"]
            with np.load(terrain, allow_pickle=False) as arrays:
                assert set(arrays.files) == {"elevation_m", "valid_mask"}, ("unexpected array", terrain)
                z = arrays["elevation_m"]
                valid = arrays["valid_mask"].astype(bool)
                assert z.shape == valid.shape == (record["rows"], record["cols"])
                assert np.array_equal(valid, np.isfinite(z))
            assert record["resolution_m"] == 4 and record["native_resolution_m"] == 20
            assert record["row_orientation"] == "south_to_north"
            map_checks.append({"id": record["id"], "map_sha256": item["map_sha256"],
                               "record_sha256": item["record_sha256"], "nodata_cells": int((~valid).sum())})
        batches.append({"batch": name, "manifest_sha256": sha(directory / "manifest.json"),
                        "summary_present": any(directory.glob("summary-*.json")),
                        "module_locks_verified": len(manifest["imported_module_locks"]),
                        "profile_sha256": sha(profile_path), "map_checks": map_checks})
    return {"classification": "INDEPENDENT_SOURCE_AND_PUBLIC_INPUT_CLOSURE_NOT_OPERATIONAL_ACCEPTANCE",
            "audited_at_utc": datetime.now(timezone.utc).isoformat(), "checks": "PASS",
            "auditor_sha256": sha(__file__), "input_closure_sha256": sha(ROOT / "input-closure.json"),
            "source_sha": closure["published_main_sha"], "runtime_and_snapshot_files_verified": files,
            "batches": batches, "provenance_limitation": closure["note"],
            "resume_note": "The runner journal does not itself enforce the imported-module byte locks on resume. These independent final byte checks supplement the explicit source freeze; main and directed batches did not resume."}


if __name__ == "__main__":
    print(json.dumps(audit(), indent=2, ensure_ascii=True, allow_nan=False))
