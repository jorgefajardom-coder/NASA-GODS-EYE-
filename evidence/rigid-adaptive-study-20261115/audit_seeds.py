"""Post-hoc seed/world reproduction, outside the planner consumer process."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys

import numpy as np

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parent.parent
SOURCE = ROOT / "frozen-main"
sys.path[:0] = [str(SOURCE / "src" / name) for name in ("mge_mission", "mge_planning", "mge_mapping", "mge_data")]
import mge_mission
mge_mission.__path__.append(str(REPO / "src/mge_mission/mge_mission"))
from mge_mission.research.design import endpoint_cells
from mge_mission.research.rigid_adaptive import FAMILIES, NAMESPACE
from mge_mission.research.world import generate


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def audit(name):
    directory = ROOT / name
    manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
    for module, item in manifest["imported_module_locks"].items():
        assert sha(item["path"]) == item["sha256"], ("source changed", module)
    raw = (directory / "paired-blocks.jsonl").read_bytes()
    assert raw.endswith(b"\n")
    cases = []
    maps = {}
    maximum_block_error = 0.
    for line in raw.decode("utf-8").splitlines():
        block = json.loads(line)["payload"]
        path = block["map_path"]
        if path not in maps:
            with np.load(path, allow_pickle=False) as arrays:
                z = np.asarray(arrays["elevation_m"], dtype=float)
                z[~arrays["valid_mask"].astype(bool)] = np.nan
            maps[path] = z
        z = maps[path]
        prefix = [20261115, NAMESPACE, block["sector_index"], block["side_m"],
                  FAMILIES.index(block["family"]), block["index"]]
        mission_rng = np.random.default_rng(np.random.SeedSequence(prefix + [0]))
        endpoints = endpoint_cells(z, mission_rng, 64)
        if endpoints is None:
            assert block["status"] == "ENDPOINT_UNAVAILABLE"
            cases.append({"block_id": block["block_id"], "endpoint_reproduced": True, "world_unavailable": True})
            continue
        assert [list(x) for x in endpoints] == block["endpoint_cells"]
        spec = block["world_spec"]
        assert spec["world_seed"] == prefix + [1]
        assert spec["base"] == list(endpoints[0]) and spec["goal"] == list(endpoints[1])
        if block["design"] == "broad":
            assert spec["target"] is None and spec["directed"] is False
        height, obstacles, metadata = generate(z, spec)
        original = block["world_metadata"]
        assert metadata["world_sha256"] == original["world_sha256"]
        assert metadata["hypothetical_obstacle_cells"] == original["hypothetical_obstacle_cells"]
        assert np.array_equal(np.isfinite(height), np.isfinite(z)), "NoData changed"
        assert height[endpoints[0]] == z[endpoints[0]], "Protected base elevation changed"
        error = metadata["max_block_mean_error_m"]
        assert error <= .001, (block["block_id"], error)
        assert abs(error-original["max_block_mean_error_m"]) < 1e-12
        maximum_block_error = max(maximum_block_error, error)
        cases.append({"block_id": block["block_id"], "endpoint_reproduced": True,
                      "world_sha256": metadata["world_sha256"], "max_block_mean_error_m": error})
    return {"classification": "POSTHOC_PRIVATE_SYNTHETIC_WORLD_AUDIT_NOT_PLANNER_INPUT",
            "audited_at_utc": datetime.now(timezone.utc).isoformat(), "batch": name, "checks": "PASS",
            "journal_sha256": hashlib.sha256(raw).hexdigest(), "auditor_sha256": sha(__file__),
            "blocks": len(cases), "max_20m_computational_block_mean_error_m": maximum_block_error,
            "checks_performed": ["Independent mission seed to endpoint reproduction",
                "Independent world stream seed derivation", "Public prior plus recorded world specification to complete world hash",
                "NoData preservation", "Protected base elevation", "20m computation-block residual mean within1mm"],
            "scope": "The post-hoc auditor may reconstruct the private hypothetical world after decisions were recorded. No generated private arrays or future observations are exported to the planner consumer.",
            "cases": cases}


if __name__ == "__main__":
    for name in sys.argv[1:]:
        record = audit(name)
        path = ROOT / ("seed-review-" + name + ".json")
        with path.open("x", encoding="utf-8") as stream:
            json.dump(record, stream, ensure_ascii=True, indent=2, allow_nan=False)
        print(json.dumps({"batch": name, "checks": record["checks"], "blocks": record["blocks"],
                          "max_block_mean_error_m": record["max_20m_computational_block_mean_error_m"]}), flush=True)
