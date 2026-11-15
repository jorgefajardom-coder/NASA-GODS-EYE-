"""Benchmark input/limit integrity, not a benchmark success requirement."""
import importlib.util
from pathlib import Path

import numpy as np

ROOT=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('scientific_benchmark',ROOT/'scripts/benchmark_scientific_planner.py')
benchmark=importlib.util.module_from_spec(spec)
spec.loader.exec_module(benchmark)


def test_public_control_preserves_uncertainty_profiles_and_declared_work():
    g,p,r,c,metadata=benchmark.build_case('jezero_public_primary','FAST')
    assert metadata['observed_cells']==0 and metadata['control_points_verified_by_owner_loader']>=3
    assert np.all(g.sigma_m==2.5) and p.max_sigma_m==1.
    assert r.start==(-14.,-14.,-2571.199462890625)
    assert r.goal==(30.,30.,-2573.264892578125)
    assert r.budget.time_s==1200. and r.reserve_time_s==240.
    assert c.service[0].kind=='inspect' and c.service[0].remaining_s==120. and not c.waiting
    assert c.profile.approval_status=='proposed'


def test_synthetic_search_control_is_existing_D07_without_profile_relaxation():
    g,p,r,c,metadata=benchmark.build_case('existing_synthetic_D07','SAFE')
    assert (g.rows,g.cols,g.resolution_m)==(9,18,3.)
    assert r.start==(4.5,13.5,0.) and r.goal==(43.5,13.5,0.)
    assert r.service_time_s==4. and c.goal_costs[0]==4.
    assert p.max_slope_deg==10. and p.max_step_m==.2 and p.max_sigma_m==1.


def test_benchmark_limits_and_termination_statistics_are_not_relaxed():
    assert benchmark.SearchLimits().timeout_s==2. and benchmark.SearchLimits().max_labels==200000
    summary=benchmark.aggregate([
        {'latency_ms':10.,'process_peak_rss_bytes':100,'expanded_labels':1,'status':'FEASIBLE','reason':'FEASIBLE_UNDER_MODEL'},
        {'latency_ms':20.,'process_peak_rss_bytes':None,'expanded_labels':2,'status':'UNKNOWN','reason':'SEARCH_LIMIT'},
    ])
    assert summary['unknown_rate']==summary['search_limit_rate']==.5
    assert summary['latency_ms_p50']==15. and summary['max_process_peak_rss_bytes']==100
