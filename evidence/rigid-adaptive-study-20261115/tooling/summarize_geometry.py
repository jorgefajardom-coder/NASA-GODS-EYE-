"""Descriptive route/work counts for resolved SIMULATED posterior queries.

Mandatory AI disclosure: OpenAI Codex assisted this analysis code and its
derived synthetic tables. Conditions sharing a scenario are dependent.
"""
import argparse
from collections import Counter
import hashlib
import importlib.util
import json
from pathlib import Path

spec = importlib.util.spec_from_file_location("paired_analysis", Path(__file__).with_name("analyze_rigid_adaptive.py"))
analysis = importlib.util.module_from_spec(spec)
spec.loader.exec_module(analysis)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    blocks, duplicates = analysis.read_blocks([args.input])
    groups = {}
    for subset in ("all_families", "unchanged_only"):
        counts = Counter()
        for block in blocks:
            if subset == "unchanged_only" and block["family"] != "unchanged":
                continue
            for pair in block.get("pairs", []):
                if pair.get("status") != "PAIRED":
                    continue
                counts["posterior_decisions_reached"] += 1
                strategy = pair["strategies"]["ADAPTIVE"]
                searches = strategy.get("searches", [])
                first_status = searches[0].get("status", "UNSPECIFIED") if searches else "NO_QUERY"
                counts["first_query_"+first_status] += 1
                if first_status == "FEASIBLE":
                    changed = strategy["geometry_changed"]
                    if type(changed) is not bool:
                        raise ValueError("Geometry change must be explicit for FEASIBLE posterior route")
                    extra = strategy["optional_completed"] > 0
                    geometry = "geometry_changed" if changed else "geometry_retained"
                    counts[geometry] += 1
                    counts[geometry+("_with_extra_work" if extra else "_without_extra_work")] += 1
        groups[subset] = dict(counts)
    output = {"classification": "SIMULATED_DESCRIPTIVE_REPEATED_CONDITIONS",
              "independent_unit": "scenario/mission seed; table rows count dependent agent/mode conditions",
              "denominator": "PAIRED conditions that reach the shared posterior decision; geometry panel uses only first posterior FEASIBLE routes. UNKNOWN is not a keep decision.",
              "groups": groups, "exact_duplicates_ignored": duplicates,
              "provenance": {"input_sha256": analysis.digest(args.input), "script_sha256": analysis.digest(__file__),
                             "validator_sha256": analysis.digest(analysis.__file__)},
              "mandatory_ai_declaration": "OpenAI Codex assisted code and derived synthetic table; not observational NASA data."}
    args.output.write_text(json.dumps(output, indent=2, ensure_ascii=False)+"\n", encoding="utf-8")
    print(json.dumps(groups, sort_keys=True))


if __name__ == "__main__":
    main()
