"""Small independent arithmetic controls, not mission experiment records.

Mandatory AI disclosure: AI-assisted validation code, OpenAI Codex.
"""
import importlib.util
import copy
import hashlib
import json
from pathlib import Path

spec = importlib.util.spec_from_file_location("paired_analysis", Path(__file__).with_name("analyze_rigid_adaptive.py"))
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

plan = module.load_json(Path(__file__).parents[1]/"statistical-plan.json")
expected = [tuple(x) for x in plan["expected_conditions"]]


def episode(completed, unknown=False):
    return {"primary_completed": completed, "returned": completed,
            "resource_violation": False, "reserve_violation": False,
            "unknown": unknown, "optional_completed": int(completed),
            "decision_changed": completed, "status": "CONTROL_ONLY",
            "elapsed_s": 0., "energy_wh": 0., "oxygen_l": None}


blocks = []
for i, (rigid, adaptive) in enumerate(((False, True), (False, True), (False, True), (True, False))):
    pairs = [{"agent_id": agent, "mode": mode, "initial_status": "FEASIBLE",
              "strategies": {"RIGID": episode(rigid), "ADAPTIVE": episode(adaptive)}} for agent, mode in expected]
    blocks.append({"block_id": f"CONTROL_ONLY-{i}", "design": "broad", "sector": "control",
                   "family": "arithmetic", "side_m": 4, "index": i, "status": "CONTROL_ONLY", "pairs": pairs})

inventory = [{k: v for k, v in block.items() if k != "pairs"} for block in blocks]
summary, pairs, worlds = module.analyze(blocks, plan, inventory, 1000, 731, scope="broad_extension")
assert summary["n_complete_broad_worlds"] == 4
assert len(pairs) == 16  # Dependence is retained; these are not 16 worlds.
assert summary["metrics"]["completion_delta"]["estimate"] == .5
assert summary["metrics"]["optional_delta"]["estimate"] == .5
assert summary["metrics"]["completion_delta"]["n_blocks"] == 4
assert abs(module.exact_mcnemar(3, 1)-.625) < 1e-14
assert module.exact_mcnemar(0, 0) == 1.
assert abs(module.wilson(0, 4)[1]-.4898908364545973) < 1e-12
unknown = episode(True, unknown=True)
assert module.credit(unknown) == 0
missing_safety = episode(True)
missing_safety.pop("reserve_violation")
assert module.credit(missing_safety) == 0

incomplete = dict(blocks[0], block_id="CONTROL_ONLY-incomplete", pairs=blocks[0]["pairs"][:-1])
s2, _, _ = module.analyze(blocks+[incomplete], plan, inventory, 1000, 731, scope="broad_extension")
assert s2["n_incomplete_blocks"] == 1
assert s2["n_complete_broad_worlds"] == 4
assert s2["metrics"]["completion_delta"]["estimate"] == .5

try:
    duplicated = dict(blocks[0], pairs=blocks[0]["pairs"]+[blocks[0]["pairs"][0]])
    module.normalize([duplicated], expected)
    raise AssertionError("Duplicate condition was not rejected")
except ValueError as exc:
    assert "Duplicate condition" in str(exc)

repeat = module.analyze(blocks, plan, inventory, 1000, 731, scope="broad_extension")[0]
assert repeat["metrics"] == summary["metrics"]
balanced, planned_subset, selection = module.balanced_prefix(blocks, inventory, expected)
assert len(balanced) == 3 and len(planned_subset) == 3
assert selection["selected_complete_tier_cycle_indices"] == [0, 1, 2]
broken = [b for b in blocks if b["index"] != 1]
assert module.balanced_prefix(broken, inventory, expected)[0] == []
assert module.balanced_prefix(blocks, inventory, expected)[2] == selection

faults = Path(__file__).parents[1]/"analysis-control-inputs"
faults.mkdir(exist_ok=True)
plain = faults/"CONTROL_ONLY-duplicates.jsonl"
plain.write_text(module.canonical(blocks[0])+"\n"+module.canonical(blocks[0])+"\n", encoding="utf-8")
assert module.read_blocks([plain])[1] == 1


def reject_unchanged(name, data, reason):
    path = faults/name
    path.write_bytes(data)
    before = path.read_bytes()
    try:
        module.read_blocks([path])
        raise AssertionError("Faulty catalogue accepted")
    except ValueError as exc:
        assert reason in str(exc), (reason, str(exc))
    assert path.read_bytes() == before


reject_unchanged("CONTROL_ONLY-truncated.jsonl", module.canonical(blocks[0]).encode(), "Truncated JSONL")
conflicting = copy.deepcopy(blocks[0])
conflicting["pairs"][0]["strategies"]["RIGID"]["status"] = "CONFLICT_CONTROL_ONLY"
reject_unchanged("CONTROL_ONLY-conflict.jsonl", (module.canonical(blocks[0])+"\n"+module.canonical(conflicting)+"\n").encode(), "Conflicting duplicate")
wrapper = {"seq": 1, "identity": "CONTROL_ONLY", "case_id": blocks[0]["block_id"], "payload": blocks[0],
           "payload_sha256": hashlib.sha256(module.canonical(blocks[0]).encode()).hexdigest()}
valid = faults/"CONTROL_ONLY-valid-journal.jsonl"
valid.write_text(module.canonical(wrapper)+"\n", encoding="utf-8")
assert len(module.read_blocks([valid])[0]) == 1
bad_seq = dict(wrapper, seq=2)
reject_unchanged("CONTROL_ONLY-sequence.jsonl", (module.canonical(bad_seq)+"\n").encode(), "Journal sequence conflict")
bad_hash = dict(wrapper, payload_sha256="0"*64)
reject_unchanged("CONTROL_ONLY-payload-hash.jsonl", (module.canonical(bad_hash)+"\n").encode(), "Journal payload hash conflict")
second = dict(wrapper, seq=2, identity="CONFLICT_CONTROL_ONLY")
reject_unchanged("CONTROL_ONLY-identity.jsonl", (module.canonical(wrapper)+"\n"+module.canonical(second)+"\n").encode(), "Journal identity conflict")
print("PASS: paired denominator/deltas, exact discordance, Wilson boundary, UNKNOWN, safety, incomplete worlds, duplicate conditions, reproducible bootstrap, whole-tier prefix; JSONL exact duplicates, conflict, truncation, sequence, identity and payload hash faults rejected without mutation")
