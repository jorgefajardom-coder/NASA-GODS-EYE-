"""Analyze paired SIMULATED rigid/adaptive runs without pseudoreplication.

Mandatory AI disclosure: AI-assisted analysis code (OpenAI Codex); derived
synthetic results are not observational NASA measurements or LIVE evidence.
The frozen statistical plan, raw input hashes and this file hash accompany output.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import csv
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import platform
import sys

import numpy as np


STRATEGIES = ("RIGID", "ADAPTIVE")
Z95 = 1.959963984540054


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"),
                      parse_constant=lambda s: (_ for _ in ()).throw(ValueError(s)))


def write_json(path, value):
    Path(path).write_text(json.dumps(value, indent=2, ensure_ascii=False,
                                    allow_nan=False) + "\n", encoding="utf-8")


def bool_field(row, name):
    value = row.get(name)
    if value is not None and type(value) is not bool:
        raise ValueError(f"{name} must be bool or null, received {value!r}")
    return value


def optional_count(row):
    value = row.get("optional_completed")
    if value is None:
        return None
    if isinstance(value, list):
        return len(value)
    if type(value) not in (int, float) or not math.isfinite(value) or value < 0 or int(value) != value:
        raise ValueError("optional_completed must be a nonnegative integer/list/null")
    return int(value)


def credit(row):
    """No credit is a software/model outcome, not a physical failure assertion."""
    return int(bool_field(row, "primary_completed") is True
               and bool_field(row, "returned") is True
               and bool_field(row, "resource_violation") is False
               and bool_field(row, "reserve_violation") is False
               and bool_field(row, "unknown") is False)


def stratum(row):
    return (str(row.get("sector", "UNSPECIFIED")), str(row.get("family", "UNSPECIFIED")),
            int(row.get("side_m", 0)))


def read_blocks(paths):
    rows = {}
    duplicates = 0
    for path in paths:
        raw = Path(path).read_bytes()
        if raw and not raw.endswith(b"\n"):
            raise ValueError(f"Truncated JSONL, retained unchanged: {path}")
        journal_identity = None
        for line_no, line in enumerate(raw.splitlines(), 1):
            if not line.strip():
                raise ValueError(f"Blank JSONL record: {path}:{line_no}")
            item = json.loads(line, parse_constant=lambda s: (_ for _ in ()).throw(ValueError(s)))
            if "payload" in item and isinstance(item["payload"], dict):
                if item.get("seq") != line_no:
                    raise ValueError(f"Journal sequence conflict: {path}:{line_no}")
                if journal_identity is None:
                    journal_identity = item.get("identity")
                if item.get("identity") != journal_identity:
                    raise ValueError(f"Journal identity conflict: {path}:{line_no}")
                payload_hash = hashlib.sha256(canonical(item["payload"]).encode("utf-8")).hexdigest()
                if item.get("payload_sha256") != payload_hash:
                    raise ValueError(f"Journal payload hash conflict: {path}:{line_no}")
                if item.get("case_id") != item["payload"].get("block_id"):
                    raise ValueError(f"Journal case/block identity conflict: {path}:{line_no}")
                item = item["payload"]
            block_id = item.get("block_id")
            if not isinstance(block_id, str) or not block_id:
                raise ValueError(f"Missing block_id: {path}:{line_no}")
            encoded = canonical(item)
            if block_id in rows:
                if rows[block_id][0] != encoded:
                    raise ValueError(f"Conflicting duplicate block_id {block_id}")
                duplicates += 1
                continue
            rows[block_id] = (encoded, item)
    return [rows[k][1] for k in sorted(rows)], duplicates


def inventory_rows(path):
    if path is None:
        return []
    obj = load_json(path)
    if isinstance(obj, list):
        return obj
    for key in ("blocks", "planned_blocks", "planned_cases", "tasks", "inventory"):
        if isinstance(obj.get(key), list):
            return obj[key]
    raise ValueError("Inventory must be a list or object containing blocks/planned_blocks/planned_cases/tasks/inventory")


def wilson(successes, n):
    if not n:
        return None
    p = successes / n
    den = 1 + Z95 * Z95 / n
    center = (p + Z95 * Z95 / (2*n)) / den
    half = Z95 * math.sqrt(p*(1-p)/n + Z95*Z95/(4*n*n)) / den
    return [max(0., center-half), min(1., center+half)]


def exact_mcnemar(rigid_only, adaptive_only):
    """Exact two-sided binomial calculation on independent discordant pairs."""
    n = rigid_only + adaptive_only
    if not n:
        return 1.
    k = min(rigid_only, adaptive_only)
    logs = [math.lgamma(n+1)-math.lgamma(i+1)-math.lgamma(n-i+1)-n*math.log(2)
            for i in range(k+1)]
    top = max(logs)
    return min(1., 2*math.exp(top)*sum(math.exp(x-top) for x in logs))


def bootstrap(rows, metric, planned_strata, repeats, seed):
    """One row per independent world; equal-stratum paired cluster bootstrap."""
    groups = defaultdict(list)
    for row in rows:
        value = row.get(metric)
        if value is not None:
            if not math.isfinite(value):
                raise ValueError(f"Nonfinite metric {metric}")
            groups[row["stratum"]].append(float(value))
    if not groups:
        return {"estimate": None, "ci95": None, "n_blocks": 0, "n_strata": 0,
                "planned_strata": len(planned_strata), "full_planned_target_covered": False}
    metric_seed = int.from_bytes(hashlib.sha256(metric.encode()).digest()[:8], "little")
    rng = np.random.default_rng(np.random.SeedSequence([seed, metric_seed]))
    draws = np.zeros(repeats)
    point = []
    small = []
    for key, values in sorted(groups.items()):
        x = np.asarray(values, dtype=float)
        point.append(float(x.mean()))
        if len(x) < 2:
            small.append(list(key))
        # Chunking bounds memory independently of the number of worlds.
        for first in range(0, repeats, 250):
            count = min(250, repeats-first)
            draws[first:first+count] += x[rng.integers(0, len(x), size=(count, len(x)))].mean(axis=1)
    draws /= len(groups)
    lo, hi = np.quantile(draws, [.025, .975])
    return {"estimate": float(np.mean(point)), "ci95": [float(lo), float(hi)],
            "n_blocks": sum(map(len, groups.values())), "n_strata": len(groups),
            "planned_strata": len(planned_strata),
            "full_planned_target_covered": bool(planned_strata) and set(groups) == set(planned_strata),
            "small_strata_less_than_two_blocks": small,
            "degenerate_interval": bool(abs(hi-lo) < 1e-15),
            "covered_strata_only": set(groups) != set(planned_strata),
            "method": "equal-stratum percentile paired-world cluster bootstrap"}


def normalize(blocks, expected):
    pairs, worlds, incomplete, audit = [], [], [], Counter()
    for block in blocks:
        design = block.get("design", "directed" if block.get("directed") else "broad")
        s = stratum(block)
        base = {"block_id": block["block_id"], "design": design,
                "sector": s[0], "family": s[1], "side_m": s[2], "stratum": s,
                "index": block.get("index"), "status": block.get("status", "UNSPECIFIED"),
                "map_id": block.get("map_id"),
                "world_sha256": block.get("world_sha256", block.get("world_hash", block.get("world_metadata", {}).get("world_sha256")))}
        audit[f"block_status:{base['status']}"] += 1
        local = {}
        for pair in block.get("pairs", []):
            key = (pair.get("agent_id"), pair.get("mode"))
            if key in local:
                raise ValueError(f"Duplicate condition {key} in {block['block_id']}")
            if key not in expected:
                raise ValueError(f"Unexpected condition {key}; frozen expected set is {expected}")
            strategies = pair.get("strategies", {})
            if set(strategies) != set(STRATEGIES):
                audit["incomplete_strategy_pair"] += 1
                continue
            row = {**base, "agent_id": key[0], "mode": key[1],
                   "initial_status": pair.get("initial_status", "UNSPECIFIED"),
                   "pair_status": pair.get("status", "POSTERIOR_EVALUATED")}
            audit[f"pair_status:{row['pair_status']}"] += 1
            for name in STRATEGIES:
                strategy = strategies[name]
                prefix = name.lower()
                row[f"{prefix}_credit"] = credit(strategy)
                row[f"{prefix}_optional"] = optional_count(strategy)
                for field in ("primary_completed", "returned", "resource_violation", "reserve_violation", "unknown", "decision_changed", "geometry_changed", "optional_unknown"):
                    row[f"{prefix}_{field}"] = bool_field(strategy, field)
                row[f"{prefix}_status"] = str(strategy.get("status", "UNSPECIFIED"))
                audit[f"episode_status:{name}:{row[f'{prefix}_status']}"] += 1
                row[f"{prefix}_query_count"] = len(strategy.get("searches", []))
                row[f"{prefix}_query_wall_s"] = sum(float(q.get("wall_s", 0)) for q in strategy.get("searches", []))
                row[f"{prefix}_planner_unknown"] = row["initial_status"] == "UNKNOWN" or any(q.get("status") == "UNKNOWN" for q in strategy.get("searches", []))
                for query in strategy.get("searches", []):
                    audit[f"query_status:{name}:{query.get('status', 'UNSPECIFIED')}:{query.get('reason_code', 'UNSPECIFIED')}"] += 1
                for field in ("elapsed_s", "energy_wh", "oxygen_l"):
                    value = strategy.get(field)
                    if value is not None and (type(value) not in (int, float) or not math.isfinite(value) or value < 0):
                        raise ValueError(f"Invalid {field} in {block['block_id']}")
                    row[f"{prefix}_{field}"] = value
            row["completion_delta"] = row["adaptive_credit"]-row["rigid_credit"]
            row["optional_delta"] = (row["adaptive_optional"]-row["rigid_optional"]
                                     if row["adaptive_optional"] is not None and row["rigid_optional"] is not None else None)
            known_endpoints = all(type(row[f"{name}_{field}"]) is bool
                                  for name in ("rigid", "adaptive")
                                  for field in ("primary_completed", "returned"))
            known_comparison = known_endpoints and row["rigid_unknown"] is False and row["adaptive_unknown"] is False
            different_endpoints = known_comparison and any(row[f"rigid_{field}"] != row[f"adaptive_{field}"]
                                                           for field in ("primary_completed", "returned"))
            added_optional = row["optional_delta"] is not None and row["optional_delta"] > 0
            # Frozen runner's broad action flag also includes a no-op optional
            # decline. Reconstruct the predeclared geometry/work criterion.
            if row["adaptive_geometry_changed"] is True or added_optional or different_endpoints:
                row["adaptive_meaningful_change"] = True
            elif row["adaptive_geometry_changed"] is False and row["optional_delta"] is not None and known_comparison:
                row["adaptive_meaningful_change"] = False
            else:
                row["adaptive_meaningful_change"] = None
            pairs.append(row)
            local[key] = row
        complete = set(local) == set(expected)
        world = {**base, "complete_conditions": complete, "recorded_pairs": len(local)}
        if not complete:
            incomplete.append({"block_id": block["block_id"], "missing_conditions": [list(x) for x in expected if x not in local], "status": base["status"]})
        else:
            for metric in ("rigid_credit", "adaptive_credit", "completion_delta", "rigid_optional", "adaptive_optional", "optional_delta", "rigid_query_count", "adaptive_query_count", "rigid_query_wall_s", "adaptive_query_wall_s"):
                values = [x[metric] for x in local.values()]
                world[metric] = float(np.mean(values)) if all(v is not None for v in values) else None
            changed = [x["adaptive_meaningful_change"] for x in local.values()]
            world["any_adaptive_change"] = int(any(changed)) if any(v is True for v in changed) or all(v is False for v in changed) else None
            for name in ("rigid", "adaptive"):
                violations = [row[f"{name}_{field}"] for row in local.values()
                              for field in ("resource_violation", "reserve_violation")]
                world[f"{name}_any_violation"] = int(any(violations)) if any(v is True for v in violations) or all(v is False for v in violations) else None
                unknowns = [x[f"{name}_unknown"] for x in local.values()]
                world[f"{name}_any_unknown"] = int(any(unknowns)) if any(v is True for v in unknowns) or all(v is False for v in unknowns) else None
                world[f"{name}_any_planner_unknown"] = int(any(x[f"{name}_planner_unknown"] for x in local.values()))
        worlds.append(world)
    return pairs, worlds, incomplete, audit


def export_csv(path, rows):
    if not rows:
        Path(path).write_text("", encoding="utf-8")
        return
    fields = list(dict.fromkeys(k for row in rows for k in row if k != "stratum"))
    with Path(path).open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def analyze(blocks, plan, inventory, repeats, seed, scope="primary"):
    expected = [tuple(x) for x in plan["expected_conditions"]]
    pairs, worlds, incomplete, audit = normalize(blocks, expected)
    selected_design = "directed" if scope == "directed" else "broad"
    if any(x["design"] != selected_design for x in worlds):
        raise ValueError("Keep broad and directed catalogues in separate analyses")
    if scope == "primary":
        grid = plan.get("planned_main_grid", {})
        for row in worlds:
            if row["side_m"] not in grid.get("sides_m", []) or row["sector"] not in grid.get("sectors", []) or row["family"] not in grid.get("families", []):
                raise ValueError("Primary catalogue is outside the frozen main grid; use a separate broad_extension analysis")
    main = [x for x in worlds if x["design"] == selected_design and x["complete_conditions"]]
    planned = [x for x in inventory if x.get("design", "broad") == selected_design]
    planned_strata = set(map(stratum, planned))
    if not planned_strata:
        if scope == "primary":
            grid = plan.get("planned_main_grid", {})
            planned_strata = {(s, f, m) for s in grid.get("sectors", []) for f in grid.get("families", []) for m in grid.get("sides_m", [])}
        else:
            planned_strata = {x["stratum"] for x in worlds}
    metrics = {name: bootstrap(main, name, planned_strata, repeats, seed) for name in
               ("rigid_credit", "adaptive_credit", "completion_delta", "rigid_optional", "adaptive_optional", "optional_delta", "any_adaptive_change", "rigid_any_violation", "adaptive_any_violation", "rigid_any_unknown", "adaptive_any_unknown", "rigid_any_planner_unknown", "adaptive_any_planner_unknown", "rigid_query_count", "adaptive_query_count", "rigid_query_wall_s", "adaptive_query_wall_s")}
    strata = []
    for key in sorted(planned_strata | {x["stratum"] for x in worlds}):
        w = [x for x in main if x["stratum"] == key]
        attempted = [x for x in worlds if x["design"] == selected_design and x["stratum"] == key]
        row = {"sector": key[0], "family": key[1], "side_m": key[2], "attempted_blocks": len(attempted), "complete_blocks": len(w)}
        for metric in ("rigid_credit", "adaptive_credit", "completion_delta", "optional_delta"):
            values = [x[metric] for x in w if x.get(metric) is not None]
            row[metric] = float(np.mean(values)) if values else None
        changes = [x["any_adaptive_change"] for x in w if x.get("any_adaptive_change") is not None]
        row["changed_worlds"] = sum(changes)
        row["change_evaluable_worlds"] = len(changes)
        row["change_wilson_ci95"] = wilson(sum(changes), len(changes))
        strata.append(row)
    conditions = []
    for agent_id, mode in expected:
        for panel in ("all_attempted", "initially_FEASIBLE"):
            selected = [x for x in pairs if x["design"] == selected_design and x["agent_id"] == agent_id and x["mode"] == mode and (panel == "all_attempted" or x["initial_status"] == "FEASIBLE")]
            b = sum(x["rigid_credit"] == 1 and x["adaptive_credit"] == 0 for x in selected)
            c = sum(x["rigid_credit"] == 0 and x["adaptive_credit"] == 1 for x in selected)
            conditions.append({"agent_id": agent_id, "mode": mode, "panel": panel, "n_independent_worlds": len(selected),
                               "rigid_only": b, "adaptive_only": c, "both_credit": sum(x["rigid_credit"] and x["adaptive_credit"] for x in selected),
                               "neither_credit": sum(not x["rigid_credit"] and not x["adaptive_credit"] for x in selected),
                               "exact_mcnemar_p_exploratory": exact_mcnemar(b, c),
                               "completion_delta": bootstrap(selected, "completion_delta", planned_strata, repeats, seed),
                               "optional_delta": bootstrap(selected, "optional_delta", planned_strata, repeats, seed)})
    attempted_ids = {x["block_id"] for x in blocks}
    pending = [x for x in inventory if x.get("block_id") not in attempted_ids]
    planned_ids = {x["block_id"] for x in planned}
    complete_ids = {x["block_id"] for x in main}
    complete_planned_seed_coverage = bool(planned_ids) and planned_ids <= complete_ids
    for metric in metrics.values():
        # Representing every stratum does not mean that every planned seed ran.
        metric["all_planned_strata_represented"] = metric["full_planned_target_covered"]
        metric["complete_planned_seed_coverage"] = complete_planned_seed_coverage
        metric["full_planned_target_covered"] = metric["all_planned_strata_represented"] and complete_planned_seed_coverage
    world_hash_counts = Counter(x["world_sha256"] for x in worlds if x.get("world_sha256"))
    directed_pairs = [x for x in pairs if x["design"] == "directed"]
    directed = {"n_recorded_blocks": sum(x["design"] == "directed" for x in worlds),
                "n_complete_blocks": sum(x["design"] == "directed" and x["complete_conditions"] for x in worlds),
                "n_recorded_pairs": len(directed_pairs),
                "rigid_only_credit_pairs": sum(x["rigid_credit"] and not x["adaptive_credit"] for x in directed_pairs),
                "adaptive_only_credit_pairs": sum(x["adaptive_credit"] and not x["rigid_credit"] for x in directed_pairs),
                "both_credit_pairs": sum(x["adaptive_credit"] and x["rigid_credit"] for x in directed_pairs),
                "neither_credit_pairs": sum(not x["adaptive_credit"] and not x["rigid_credit"] for x in directed_pairs),
                "interpretation": "Corridor-conditioned mechanism cases, descriptive only. Repeated conditions are dependent; counts are not broadly sampled Mars hazard or discovery probabilities."}
    summary = {"classification": "SIMULATED_EXPLORATORY_ANALYTICAL_NOT_LIVE", "analysis_scope": scope, "selected_design": selected_design,
               "independent_unit": "independently seeded scenario/mission block conditional on fixed public terrains", "primary_design": "broad",
               "n_planned_blocks": len(inventory) if inventory or scope != "primary" else plan.get("planned_main_grid", {}).get("world_blocks"),
               "n_planned_selected_blocks": len(planned) if inventory or scope != "primary" else plan.get("planned_main_grid", {}).get("world_blocks"),
               "n_planned_broad_blocks": sum(x.get("design", "broad") == "broad" for x in inventory) if inventory or scope != "primary" else plan.get("planned_main_grid", {}).get("world_blocks"),
               "n_recorded_blocks": len(blocks), "n_complete_broad_worlds": sum(x["design"] == "broad" and x["complete_conditions"] for x in worlds),
               "n_independent_analysis_blocks": len(main), "n_recorded_paired_conditions": len(pairs),
               "n_directed_blocks": sum(x["design"] == "directed" for x in worlds),
               "n_incomplete_blocks": len(incomplete), "n_pending_inventory_blocks": len(pending) if inventory else None,
               "coverage": {"all_planned_seed_blocks_complete": complete_planned_seed_coverage,
                            "n_planned_selected_design_blocks": len(planned_ids),
                            "n_planned_selected_design_blocks_complete": len(planned_ids & complete_ids),
                            "unexpected_recorded_block_ids": sorted(attempted_ids-{x["block_id"] for x in inventory}) if inventory else [],
                            "interpretation": "Complete stratum representation and complete planned-seed execution are separate checks. Deadline-dependent availability can bias a partial catalogue."},
               "terrain_realizations": {"n_recorded_world_array_hashes": len(world_hash_counts),
                                        "n_blocks_with_world_hash": sum(world_hash_counts.values()),
                                        "array_hash_multiplicities": dict(sorted(world_hash_counts.items())),
                                        "interpretation": "Independent scenario seeds do not imply distinct terrain arrays. Unchanged cases can share the same fixed public prior; intervals condition on these selected terrains."},
               "planned_strata": [list(x) for x in sorted(planned_strata)], "metrics": metrics, "directed_cases": directed,
               "outcome_counts": dict(sorted(audit.items())), "conditions": conditions, "incomplete_blocks": incomplete,
               "pending_inventory_blocks": pending, "strata": strata,
               "uncertainty": {"method": "stratified paired-world percentile bootstrap", "replicates": repeats, "seed": seed, "confidence_level": .95},
               "interpretation": "Declared synthetic scenario ensemble conditional on selected fixed public terrains only. Repeated agent/mode/strategy episodes are dependent. Unknown and unavailable are reported; no new approval or LIVE verification."}
    return summary, pairs, worlds


def case_examples(blocks):
    """Deterministic first examples for declared mechanisms, including harm/null.

    Selection is explanatory rather than a separate statistical sample. The
    complete signed catalogue remains the denominator for policy comparison.
    """
    found = {}
    for block in sorted(blocks, key=lambda b: b["block_id"]):
        for pair in sorted(block.get("pairs", []), key=lambda p: (p["agent_id"], p["mode"])):
            if set(pair.get("strategies", {})) != set(STRATEGIES):
                continue
            rigid, adaptive = [pair["strategies"][s] for s in STRATEGIES]
            r, a = credit(rigid), credit(adaptive)
            categories = []
            if r and not a:
                categories.append("adverse_primary_comparison")
            if a and not r:
                categories.append("improved_primary_comparison")
            if r and a and adaptive.get("geometry_changed") is False:
                categories.append("primary_preserved_without_geometric_change")
            if a and optional_count(adaptive) and not optional_count(rigid):
                categories.append("new_optional_work_completed")
            if a and optional_count(adaptive) == 0 and any(d.get("action") == "DECLINE_OPTIONAL" for d in adaptive.get("decisions", [])):
                categories.append("optional_work_declined_primary_preserved")
            if block.get("design") == "directed" and not a and not r and pair.get("initial_status") == "FEASIBLE":
                categories.append("directed_case_both_without_completion_credit")
            if adaptive.get("unknown") is True:
                categories.append("unresolved_adaptive_search")
            for category in categories:
                if category in found:
                    continue
                observation = pair.get("common_observation")
                example = {"category": category, "block_id": block["block_id"], "design": block.get("design", "broad"),
                           "sector": block.get("sector"), "family": block.get("family"), "side_m": block.get("side_m"),
                           "index": block.get("index"), "agent_id": pair["agent_id"], "mode": pair["mode"],
                           "initial_status": pair.get("initial_status"), "base": block.get("base"), "goal": block.get("goal"),
                           "common_reached": pair.get("common_reached"), "common_remaining": pair.get("common_remaining"),
                           "observation": {"source_kind": observation.get("source_kind"), "observation_id": observation.get("observation_id"),
                                           "cells": len(observation.get("cell_indices", [])),
                                           "reported_obstacle_cells": sum(x == 100 for x in observation.get("obstacles", [])),
                                           "sha256": hashlib.sha256(canonical(observation).encode()).hexdigest()} if observation else None,
                           "opportunity": pair.get("opportunity"), "strategies": {},
                           "selection": "First sorted catalogue example satisfying a declared explanatory category; not a prevalence estimate."}
                for name, strategy in (("RIGID", rigid), ("ADAPTIVE", adaptive)):
                    example["strategies"][name] = {k: strategy.get(k) for k in
                        ("status", "primary_completed", "returned", "unknown", "optional_unknown", "optional_completed", "geometry_changed", "decisions", "remaining", "reserve_margins", "elapsed_s", "energy_wh", "oxygen_l", "resource_violation", "reserve_violation", "pose")}
                    example["strategies"][name]["completion_credit"] = credit(strategy)
                    example["strategies"][name]["n_post_observation_queries"] = len(strategy.get("searches", []))
                found[category] = example
    return {"classification": "SIMULATED_EXPLANATORY_CASES", "selection_rule": "First sorted example per category, include adverse and null outcomes; preserve all raw cases separately", "examples": found}


def balanced_prefix(blocks, inventory, expected):
    """Exploratory deadline-coverage sensitivity; retain whole three-tier cycles.

    Never replace source records or use success/benefit as an inclusion rule.
    A complete block has all frozen conditions and both recorded strategies,
    including unsuccessful and UNKNOWN episodes.
    """
    complete_ids = set()
    for block in blocks:
        conditions = block.get("pairs", [])
        if (len(conditions) == len(expected)
                and {(p.get("agent_id"), p.get("mode")) for p in conditions} == set(expected)
                and all(set(p.get("strategies", {})) == set(STRATEGIES) for p in conditions)):
            complete_ids.add(block["block_id"])
    planned_by_index = defaultdict(list)
    for row in inventory:
        planned_by_index[int(row["index"])].append(row)
    prefix = []
    for index in sorted(planned_by_index):
        if index != len(prefix):
            break
        if not all(row["block_id"] in complete_ids for row in planned_by_index[index]):
            break
        prefix.append(index)
    # Allocation/reserve/perturbation tiers repeat every three indices.
    selected = prefix[:len(prefix)//3*3]
    retained_ids = {row["block_id"] for index in selected for row in planned_by_index[index]}
    meta = {"classification": "EXPLORATORY_POSTHOC_COVERAGE_SENSITIVITY_NOT_PRIMARY",
            "rule": "Largest fully completed index prefix across all planned strata, trimmed to whole three-index stress-tier cycles; no outcome-success selection.",
            "source_recorded_blocks": len(blocks), "source_planned_blocks": len(inventory),
            "fully_completed_prefix_indices": prefix, "selected_complete_tier_cycle_indices": selected,
            "retained_blocks": len(retained_ids),
            "interpretation": "Retains a balanced finite seed subset while disclosing deadline censoring in the full catalogue. It does not make runtime-dependent coverage a random sample or repair unexecuted seeds."}
    return [b for b in blocks if b["block_id"] in retained_ids], [b for b in inventory if b["block_id"] in retained_ids], meta


def display_metric(metric, percentage=False):
    if metric["estimate"] is None:
        return "unavailable"
    factor = 100 if percentage else 1
    suffix = " percentage points" if percentage else ""
    ci = metric["ci95"]
    return f"{metric['estimate']*factor:.3f}{suffix} (95% paired-world interval {ci[0]*factor:.3f} to {ci[1]*factor:.3f})"


def report(summary):
    m = summary["metrics"]
    lines = ["# Rigid and adaptive analytical mission comparison", "", "Classification: SIMULATED; local exploratory analysis. These results do not constitute a verified LIVE mission.", "",
             f"Analysis scope: {summary['analysis_scope']}; sampling design: {summary['selected_design']}. The input contains {summary['n_recorded_blocks']} recorded scenario blocks and {summary['n_recorded_paired_conditions']} matched agent/mode conditions. The analysis uses {summary['n_independent_analysis_blocks']} complete, independently seeded scenario/mission blocks. There are {summary['n_incomplete_blocks']} incomplete blocks; planned but unexecuted blocks are retained in the coverage inventory. Supplementary or directed batches do not modify the frozen main estimand.", "",
             f"Recorded scenarios contain {summary['terrain_realizations']['n_recorded_world_array_hashes']} distinct private-world array hashes across {summary['terrain_realizations']['n_blocks_with_world_hash']} blocks with a world hash. Independent mission draws are conditional on the selected public terrains; repeated unchanged arrays are not independent geological samples.", "",
             f"The standardized adaptive-minus-rigid completion-credit difference is {display_metric(m['completion_delta'], True)}. Credit requires the primary objective and directed return, with explicit evidence of no resource or reserve violation and no UNKNOWN outcome. A no-credit UNKNOWN is an unresolved model computation, rather than evidence that physical passage is impossible.", "",
             f"The optional-work difference is {display_metric(m['optional_delta'])} completed objectives per agent/mode episode, averaged within worlds. Optional-work responsiveness is partly defined by the policy: a rigid plan cannot add new targets by construction. This endpoint must be read separately from safe recovery and primary completion.", "",
             "The analysis first averages the four fixed agent/mode conditions within each world and then equally weights sector/family/size strata. Confidence intervals resample paired worlds within these strata, retaining every dependent episode. When a stratum is uncovered, only the covered-strata estimate is available; incomplete target coverage prevents a full planned-target claim. Zero-width bootstrap intervals and strata containing fewer than two worlds are flagged in the machine-readable output.", "",
             "| Sector | Family | Side (m) | Attempted worlds | Complete worlds | Completion difference | Optional difference |", "|---|---|---:|---:|---:|---:|---:|"]
    for row in summary["strata"]:
        delta = "—" if row["completion_delta"] is None else f"{100*row['completion_delta']:.2f} pp"
        optional = "—" if row["optional_delta"] is None else f"{row['optional_delta']:.3f}"
        lines.append(f"| {row['sector']} | {row['family']} | {row['side_m']} | {row['attempted_blocks']} | {row['complete_blocks']} | {delta} | {optional} |")
    lines += ["", "Broadly generated worlds and corridor-conditioned directed cases have separate denominators. Their ensemble frequencies are not estimates of Mars hazard rates or probabilities of scientific discovery. Costs, sensing and execution remain limited to the frozen analytical model and its recorded assumptions.", "",
              "The numerical implementation follows paired resampling as documented by [SciPy](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.bootstrap.html). Descriptive binary world indicators use [Wilson intervals documented by NIST](https://www.itl.nist.gov/div898/handbook/prc/section2/prc241.htm). Condition-specific discordance is also reported using the [exact binomial McNemar calculation](https://www.statsmodels.org/stable/generated/statsmodels.stats.contingency_tables.mcnemar.html); these auxiliary comparisons are exploratory.", "",
              "AI use: OpenAI Codex assisted the protocol, analysis code and generated explanatory figures. Simulated outputs are not NASA observations.", ""]
    return "\n".join(lines)


def figures(summary, out, deps):
    if deps:
        sys.path.insert(0, str(Path(deps).resolve()))
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(1, 2, figsize=(11.8, 5.4), layout="constrained")
    for ax, metric, title, scale in ((axes[0], "completion_delta", "Primary objective + directed return", 100), (axes[1], "optional_delta", "New optional work completed", 1)):
        data = summary["metrics"][metric]
        if data["estimate"] is not None:
            x = data["estimate"]*scale
            lo, hi = [v*scale for v in data["ci95"]]
            ax.errorbar([x], [0], xerr=[[max(0., x-lo)], [max(0., hi-x)]], fmt="o", markersize=10, capsize=8, color="#176b87")
            ax.annotate(f"{x:.2f}\n95% interval [{lo:.2f}, {hi:.2f}]", (x, 0), xytext=(0, 35), textcoords="offset points", ha="center")
        else:
            ax.text(.5, .5, "No evaluable paired worlds", transform=ax.transAxes, ha="center")
        ax.axvline(0, color="#8a8a8a", linestyle="--", linewidth=1)
        ax.set_yticks([])
        ax.set_ylim(-.5, .6)
        ax.set_title(title)
        ax.set_xlabel("Adaptive − rigid (percentage points)" if scale == 100 else "Adaptive − rigid (objectives per episode)")
        ax.grid(axis="x", alpha=.2)
    fig.suptitle(f"Paired policy comparison · {summary['n_independent_analysis_blocks']} scenario seeds · {summary['analysis_scope']}", fontsize=14)
    fig.text(.5, -.025, "AI-generated | SIMULATED · analytical model only · 95% stratified paired-world bootstrap", ha="center", fontsize=10, color="#6b2434")
    fig.savefig(out/"paired-effects.png", dpi=180, bbox_inches="tight", metadata={"Description": "AI-generated | SIMULATED statistical figure, OpenAI Codex assisted"})
    plt.close(fig)
    rows = summary["strata"]
    fig, ax = plt.subplots(figsize=(10.4, max(5.5, len(rows)*.20)), layout="constrained")
    labels = [f"{r['sector']} · {r['family']} · {r['side_m']} m" for r in rows]
    pos = np.arange(len(rows))
    ax.barh(pos, [r["attempted_blocks"] for r in rows], label="Recorded attempts", color="#cbd5df")
    ax.barh(pos, [r["complete_blocks"] for r in rows], label="Complete paired-world blocks", color="#176b87")
    ax.set_yticks(pos, labels, fontsize=8)
    ax.invert_yaxis()
    ax.set_xlabel("Independently seeded scenario blocks")
    ax.set_title("Coverage and incomplete work remain part of the report")
    ax.legend(loc="lower right")
    fig.text(.5, -.02, "AI-generated | SIMULATED · no episode-level pseudoreplication", ha="center", fontsize=10, color="#6b2434")
    fig.savefig(out/"paired-coverage.png", dpi=180, bbox_inches="tight", metadata={"Description": "AI-generated | SIMULATED statistical figure, OpenAI Codex assisted"})
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("inputs", nargs="+", type=Path)
    parser.add_argument("--protocol", required=True, type=Path)
    parser.add_argument("--inventory", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--plot-deps", type=Path)
    parser.add_argument("--no-plots", action="store_true")
    parser.add_argument("--replicates", type=int)
    parser.add_argument("--scope", choices=("primary", "broad_extension", "directed"), default="primary")
    parser.add_argument("--complete-prefix-only", action="store_true",
                        help="Exploratory extension-only view: complete seed prefix and whole three-tier cycles")
    args = parser.parse_args()
    plan = load_json(args.protocol)
    repeats = args.replicates or int(plan["uncertainty"]["bootstrap_replicates"])
    if repeats < 100:
        raise ValueError("At least 100 bootstrap replicates required")
    blocks, duplicates = read_blocks(args.inputs)
    inventory = inventory_rows(args.inventory)
    sensitivity = None
    if args.complete_prefix_only:
        if args.scope != "broad_extension" or not inventory:
            raise ValueError("Complete-prefix sensitivity requires a separate broad_extension inventory")
        blocks, inventory, sensitivity = balanced_prefix(blocks, inventory, [tuple(x) for x in plan["expected_conditions"]])
    summary, pairs, worlds = analyze(blocks, plan, inventory, repeats, int(plan["uncertainty"]["bootstrap_seed"]), args.scope)
    if sensitivity is not None:
        summary["coverage_sensitivity"] = sensitivity
    summary["exact_duplicate_records_ignored"] = duplicates
    summary["provenance"] = {"analyzed_at_utc": datetime.now(timezone.utc).isoformat(),
                             "inputs": [{"path": str(p), "sha256": digest(p)} for p in args.inputs],
                             "protocol_sha256": digest(args.protocol), "script_sha256": digest(__file__),
                             "inventory_sha256": digest(args.inventory) if args.inventory else None,
                             "versions": {"python": platform.python_version(), "numpy": np.__version__},
                             "mandatory_ai_declaration": "OpenAI Codex assisted analysis code and derived synthetic data; not observational NASA data."}
    args.output.mkdir(parents=True, exist_ok=True)
    write_json(args.output/"summary.json", summary)
    write_json(args.output/"case-studies.json", case_examples(blocks))
    export_csv(args.output/"paired-conditions.csv", pairs)
    export_csv(args.output/"world-blocks.csv", worlds)
    export_csv(args.output/"strata.csv", summary["strata"])
    (args.output/"analysis.md").write_text(report(summary), encoding="utf-8")
    if not args.no_plots:
        figures(summary, args.output, args.plot_deps)
    print(canonical({"independent_broad_worlds": summary["n_complete_broad_worlds"], "recorded_pairs": len(pairs),
                     "primary": summary["metrics"]["completion_delta"], "output": str(args.output)}))


if __name__ == "__main__":
    main()
