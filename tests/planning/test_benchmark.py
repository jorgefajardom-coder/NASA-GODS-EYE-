"""D-10: benchmark observations are reproducible inputs, not invented metrics."""

import importlib.util
import json
from pathlib import Path

import pytest


def benchmark_module():
    path = Path(__file__).resolve().parents[2] / "scripts/benchmark_planner.py"
    spec = importlib.util.spec_from_file_location("planner_benchmark", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_d10_three_seed_benchmark_records_actual_samples_and_cost_references():
    report = benchmark_module().run_benchmark(repeats=1)
    assert report["configuration"]["seeds"] == [7, 19, 41]
    assert len(report["samples"]) == 3
    assert report["latency_ms"]["sample_count"] == 3
    assert 0 <= report["latency_ms"]["p50"] <= report["latency_ms"]["p95"]
    assert report["all_match_reference"]
    assert all(s["latency_ms"] >= 0 and s["matches_reference"]
               for s in report["samples"])
    assert "SIMULATED" in report["provenance"]
    json.dumps(report, allow_nan=False)


def test_repeated_seed_queries_keep_costs_and_paths_while_latency_is_measured():
    report = benchmark_module().run_benchmark(seeds=(19,), repeats=2)
    first, second = report["samples"]
    assert first["outbound_path"] == second["outbound_path"]
    assert first["return_path"] == second["return_path"]
    assert first["travel_time_s"] == second["travel_time_s"]
    assert first["energy_est_wh"] == second["energy_est_wh"]


@pytest.mark.parametrize("seeds,repeats", [((), 1), ((7,), 0)])
def test_benchmark_refuses_an_empty_sample_population(seeds, repeats):
    with pytest.raises(ValueError):
        benchmark_module().run_benchmark(seeds=seeds, repeats=repeats)
