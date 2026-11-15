"""Local computational audit, not a mission benchmark or physical validation.

One fresh worker per sample; only plan_route is timed. Existing public Jezero
scenario and existing synthetic D-07 geometry; unchanged profiles/default limits.
No observations, sigma reduction, approval override or evaluator-reference input.
"""
import argparse
from collections import Counter
from dataclasses import asdict, replace
import hashlib
import json
from pathlib import Path
import platform
import subprocess
import sys
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]
for package in ('mge_planning', 'mge_mission', 'mge_data', 'mge_mapping'):
    sys.path.insert(0, str(ROOT/'src'/package))

import numpy as np
import yaml
from mge_data.core import load_public_terrain
from mge_mapping.core import BeliefMap
from mge_mission.models import export_planner_profiles, load_profiles
from mge_planning.core import MotionProfile, PlanRequest, ResourceBudget, SearchLimits, TerrainGrid, plan_route
from mge_planning.resource_costs import Activity, ScientificContext

SCENARIO = ROOT/'config/mission_jezero.experimental.yaml'
REGISTRY = ROOT/'config/science_profiles.proposed.json'
CASES = ('jezero_public_primary', 'existing_synthetic_D07')


def build_case(case, mode):
    scenario = yaml.safe_load(SCENARIO.read_text(encoding='utf-8'))
    agent = scenario['primary_agent_id']
    profile = load_profiles(REGISTRY)[agent]
    motion = MotionProfile(**export_planner_profiles({agent: profile})['profiles'][agent])
    if case == 'jezero_public_primary':
        tile = load_public_terrain(ROOT/scenario['manifest_path'])
        belief = BeliefMap.from_terrain_tile(tile, run_id='local-scientific-benchmark')
        policy = json.loads((ROOT/'config/exploration_policy.illustrative.json').read_text(encoding='utf-8'))
        limits = policy['limits'][profile.kind]
        # Existing explicit estimated-prior MASK policy; independently preserve
        # the planner profile's stricter sigma=1.0 and the source sigma=2.5.
        mask = belief.traversability_grid(allow_estimated=True, **limits)
        grid = TerrainGrid(belief.run_id, belief.map_version, belief.belief, mask,
                           belief.resolution_m, belief.origin_x_m, belief.origin_y_m,
                           sigma_m=belief.sigma)
        b = scenario['budgets'][agent]
        budget = ResourceBudget(profile.kind, b['time_s'], b['energy_wh'], b['reserve_wh'],
                                b.get('oxygen_l'), b.get('reserve_oxygen_l'))
        request = PlanRequest(grid.run_id, 'primary', agent, profile.kind, grid.map_version,
                              tuple(scenario['base_enu_m']), tuple(scenario['primary_goal_enu_m']),
                              budget, return_to=tuple(scenario['base_enu_m']), mode=mode,
                              service_time_s=scenario['primary_service_time_s'], reserve_time_s=b['reserve_time_s'])
        service = (Activity('primary-service', scenario['primary_activity'], request.service_time_s),)
        provenance = {'kind': 'public_unobserved_orbital_prior', 'rows':grid.rows,'cols':grid.cols,
                      'resolution_m':grid.resolution_m,'control_points_verified_by_owner_loader':len(tile.control_points),
                      'observed_cells':int(np.count_nonzero(tile.observed_mask)),
                      'sigma_m_min':float(np.min(grid.sigma_m)), 'sigma_m_max':float(np.max(grid.sigma_m)),
                      'profile_max_sigma_m':motion.max_sigma_m,
                      'mask_policy':'config/exploration_policy.illustrative.json',
                      'wait_allowance_not_scheduled':'Sizing allowance is not a declared executed/pending wait interval'}
    elif case == 'existing_synthetic_D07':
        # Same flat 9x18/3m, 39m outbound and 4s service as existing D-07.
        # Allocation matches the already local C2 scientific D-07 test (no new
        # resource coefficients or limit increase). This is a search control,
        # not a replacement for public terrain or a simulated execution run.
        grid = TerrainGrid('synthetic-D07-benchmark',1,np.zeros((9,18)),np.zeros((9,18)),3.,
                           sigma_m=np.zeros((9,18)))
        request = PlanRequest(grid.run_id,'D07-initial-route',agent,profile.kind,1,
                              (4.5,13.5,0.),(43.5,13.5,0.),
                              ResourceBudget('human',10000.,1000.,1.,100.,1.),
                              return_to=(4.5,13.5,0.),mode=mode,service_time_s=4.,reserve_time_s=1.)
        service = (Activity('D07-service','inspect',4.),)
        provenance = {'kind':'existing_synthetic_D07_search_control','rows':9,'cols':18,
                      'resolution_m':3.,'sigma_m':0.,'future_obstacle_not_in_this_initial_snapshot':True}
    else:
        raise ValueError('unknown fixed benchmark case')
    context = ScientificContext.from_files(request=request,registry_path=REGISTRY,scenario_path=SCENARIO,
                                           phase='OUTBOUND',service=service,waiting=())
    return grid,motion,request,context,provenance


def peak_rss():
    """OS process high-water RSS INCLUDING imports/input setup, not heap delta."""
    if sys.platform == 'win32':
        import ctypes
        from ctypes import wintypes
        class Counters(ctypes.Structure):
            _fields_ = [('cb',wintypes.DWORD),('PageFaultCount',wintypes.DWORD)]+[
                (name,ctypes.c_size_t) for name in ('PeakWorkingSetSize','WorkingSetSize',
                'QuotaPeakPagedPoolUsage','QuotaPagedPoolUsage','QuotaPeakNonPagedPoolUsage',
                'QuotaNonPagedPoolUsage','PagefileUsage','PeakPagefileUsage')]
        current = ctypes.windll.kernel32.GetCurrentProcess
        current.restype = wintypes.HANDLE
        get = ctypes.windll.psapi.GetProcessMemoryInfo
        get.argtypes = [wintypes.HANDLE,ctypes.POINTER(Counters),wintypes.DWORD]
        get.restype = wintypes.BOOL
        counters = Counters();counters.cb=ctypes.sizeof(counters)
        if not get(current(),ctypes.byref(counters),counters.cb):
            return None
        return counters.PeakWorkingSetSize
    import resource
    value = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return int(value if sys.platform == 'darwin' else value*1024)


def worker(case, backend, mode):
    if backend not in {'legacy','scientific'} or mode not in {'FAST','SAFE'}:
        raise ValueError('explicit supported backend/mode required')
    grid,profile,request,context,provenance = build_case(case,mode)
    limits = SearchLimits()  # Deliberately no CLI override of limits.
    before = peak_rss()
    started = perf_counter()
    result = plan_route(terrain=grid,request=request,profile=profile,limits=limits,
                        **({'scientific_context':context} if backend=='scientific' else {}))
    elapsed = 1000*(perf_counter()-started)
    peak = peak_rss()
    return {'case':case,'backend':backend,'mode':mode,'latency_ms':elapsed,
            'status':result.status.value,'reason':result.reason_code,'expanded_labels':result.expanded_labels,
            'process_peak_rss_bytes':peak,'process_peak_before_call_bytes':before,
            'additional_process_high_water_bytes':max(0,peak-before) if peak is not None and before is not None else None,
            'time_est_s':result.travel_time_s,'energy_est_wh':result.energy_est_wh,
            'oxygen_est_l':result.oxygen_est_l,'reserve_time_s':result.reserve_time_s,
            'reserve_wh':result.reserve_wh,'reserve_oxygen_l':result.reserve_oxygen_l,
            'min_clearance_m':result.min_clearance_m,'route_id':result.route_id,
            'budget':asdict(request.budget),'required_time_reserve_s':request.reserve_time_s,
            'limits':asdict(limits),'provenance':provenance}


def aggregate(samples):
    latency = [s['latency_ms'] for s in samples]
    peaks = [s['process_peak_rss_bytes'] for s in samples if s['process_peak_rss_bytes'] is not None]
    return {'samples':len(samples),'latency_ms_p50':float(np.percentile(latency,50)),
            'latency_ms_p95':float(np.percentile(latency,95)),
            'max_process_peak_rss_bytes':max(peaks) if peaks else None,
            'labels_min':min(s['expanded_labels'] for s in samples),
            'labels_max':max(s['expanded_labels'] for s in samples),
            'terminations':dict(Counter(s['status']+'/'+s['reason'] for s in samples)),
            'unknown_rate':sum(s['status']=='UNKNOWN' for s in samples)/len(samples),
            'search_limit_rate':sum(s['reason']=='SEARCH_LIMIT' for s in samples)/len(samples)}


def run(repeats):
    groups=[];samples=[]
    # Interleave backend/mode order across repetitions to reduce drift bias.
    combinations=[(c,b,m) for c in CASES for b in ('legacy','scientific') for m in ('FAST','SAFE')]
    for repeat in range(repeats):
        for case,backend,mode in combinations if repeat%2==0 else reversed(combinations):
            result=subprocess.run([sys.executable,str(Path(__file__).resolve()),'--worker',case,backend,mode],
                                  check=True,capture_output=True,text=True,cwd=ROOT)
            sample=json.loads(result.stdout);sample['repeat']=repeat;samples.append(sample)
        print(f'Completed repeat {repeat+1}/{repeats}',flush=True)
    for case,backend,mode in combinations:
        groups.append({'case':case,'backend':backend,'mode':mode,
                       **aggregate([s for s in samples if (s['case'],s['backend'],s['mode'])==(case,backend,mode)])})
    files=['scripts/benchmark_scientific_planner.py','src/mge_planning/mge_planning/core.py',
           'src/mge_planning/mge_planning/resource_costs.py','src/mge_planning/mge_planning/replan.py',
           'src/mge_mission/mge_mission/models.py','config/science_profiles.proposed.json',
           'config/mission_jezero.experimental.yaml','config/exploration_policy.illustrative.json',
           'data/sample/manifest.json','data/sample/terrain.npz']
    return {'kind':'LOCAL_COMPUTATIONAL_PLANNER_AUDIT_NOT_MISSION_EXECUTION',
            'source_revision':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
            'source_sha256':{p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in files},
            'environment':{'python':platform.python_version(),'platform':platform.platform(),'numpy':np.__version__},
            'protocol':{'repeats':repeats,'cold_geometry_cache':True,'worker_process':'fresh per sample',
                        'timed_scope':'plan_route only; imports, public data validation and context preparation excluded',
                        'limits':asdict(SearchLimits()),'rss_scope':'OS process high-water including imports/setup; additional high-water is not isolated planner heap',
                        'no_sigma_or_profile_override':True,'no_evaluator_reference_read':True},
            'groups':groups,'samples':samples}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--worker',nargs=3,metavar=('CASE','BACKEND','MODE'))
    parser.add_argument('--repeats',type=int,default=10)
    parser.add_argument('--output',type=Path)
    args=parser.parse_args()
    if args.worker:
        print(json.dumps(worker(*args.worker),allow_nan=False));return
    if args.repeats<2 or args.output is None:parser.error('at least two repeats and a new output path required')
    if args.output.exists():parser.error('refusing to overwrite benchmark evidence')
    report=run(args.repeats);args.output.parent.mkdir(parents=True,exist_ok=True)
    with args.output.open('x',encoding='utf-8',newline='\n') as f:json.dump(report,f,indent=2,allow_nan=False);f.write('\n')
    print(f'Wrote {len(report["samples"])} samples to {args.output}')


if __name__=='__main__':main()
