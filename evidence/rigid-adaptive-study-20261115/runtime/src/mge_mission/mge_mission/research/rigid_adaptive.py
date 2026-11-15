"""Paired, private-world analytical experiments; never LIVE execution evidence.

AI-assisted experimental code: mandatory project declaration is maintained in
the study manifest. Worlds, observations and analytic completion are SIMULATED.
"""
from concurrent.futures import ProcessPoolExecutor, wait, FIRST_COMPLETED
from dataclasses import asdict, replace
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import sys
import time
import traceback

import numpy as np

from mge_mapping.core import BeliefMap, SimulatedObservation, fuse_observation
from mge_mission.models import estimate_activity, estimate_segment, export_planner_profiles, load_profiles
from mge_mission.scientific_search import scientific_plan
from mge_mission.terrain_profile_variants import orbital_grade_projection
from mge_planning import core, resource_costs as rc
from .design import endpoint_cells
from .protocol import Journal, canonical, digest, now, read, sha, write_new
from .world import WorldClient

FAMILIES = ("unchanged", "detour", "blocked", "relief", "resource")
NAMESPACE = 7241903


def _cost(profile, parts):
    return {"time_s": sum(p.time_s for p in parts), "energy_wh": sum(p.energy_wh for p in parts),
            "oxygen_l": sum(p.oxygen_l for p in parts) if profile.kind == "human" else None}


def _move(profile, path):
    return _cost(profile, [estimate_segment(profile, tuple(a), tuple(b)) for a, b in zip(path, path[1:])])


def _subtract(available, cost):
    return {k: v-cost[k] if v is not None else None for k, v in available.items()}


def _fits(cost, available, reserve):
    return all(available[k]-reserve[k]-v >= 0 for k,v in cost.items() if v is not None)


def _xy(path):
    return [list(p[:2]) for p in path]


def _result(result):
    return {"status": result.status.value, "reason_code": result.reason_code, "detail": result.detail,
            "outbound_path": result.outbound_path, "return_path": result.return_path,
            "time_s": result.travel_time_s, "energy_wh": result.energy_est_wh,
            "oxygen_l": result.oxygen_est_l, "elapsed_s": result.elapsed_s,
            "expanded_labels": result.expanded_labels}


def _point(record, z, cell):
    return (record["origin_x_m"]+(cell[1]+.5)*4, record["origin_y_m"]+(cell[0]+.5)*4, float(z[cell]))


def _cell(record, point):
    return [int((point[1]-record["origin_y_m"])//4), int((point[0]-record["origin_x_m"])//4)]


def _plan(belief, record, profile, motion, pose, goal, base, available, reserve, service, mode, limits, label, require_return=True):
    if any(v < reserve[k] for k,v in available.items() if v is not None):
        return None, {"status":"INSUFFICIENT_BUDGET", "reason_code":"CURRENT_RESERVES_UNAVAILABLE"}
    grid=core.TerrainGrid(belief.run_id, belief.map_version, belief.belief,
        belief.traversability_grid(max_slope_deg=motion.max_slope_deg,max_sigma_m=motion.max_sigma_m,allow_estimated=True),
        4.,record["origin_x_m"],record["origin_y_m"],sigma_m=belief.sigma)
    request=core.PlanRequest(belief.run_id,label,profile.agent_id,profile.kind,belief.map_version,tuple(pose),tuple(goal),
        core.ResourceBudget(profile.kind,available["time_s"],available["energy_wh"],reserve["energy_wh"],available["oxygen_l"],reserve["oxygen_l"]),
        tuple(base),require_return,mode,sum(t for _,t in service),reserve["time_s"])
    activities=tuple(rc.Activity(label+":"+str(i), kind, seconds) for i,(kind,seconds) in enumerate(service))
    start=time.perf_counter()
    result=scientific_plan(core,rc.ScientificCosts(profile),terrain=grid,request=request,motion_profile=motion,
        activities=activities,limits=core.SearchLimits(**limits))
    item=_result(result);item["wall_s"]=time.perf_counter()-start
    return result,item


def _allocation(cfg, sector, profile, index):
    if "allocations" in cfg:
        row=cfg["allocations"][sector][profile.kind]
        gross=dict(row["gross"]);reserve=dict(row["reserves"]);wait_s=row.get("wait_s",0.)
    else:
        from mge_mission.environment_pilots import proposed_allocation
        row=proposed_allocation(Path(cfg["prior_root"]),sector,profile)
        gross=dict(row["gross"]);reserve=dict(row["reserves"]);wait_s=row["assumed_wait_s"]
    gross.setdefault("oxygen_l",None);reserve.setdefault("oxygen_l",None)
    # Predeclared deterministic strata, not posterior feasibility selection.
    factor=(.8,1.,1.2)[index%3] if cfg.get("vary_budgets",True) else 1.
    fraction=(.1,.2,.3)[index%3] if cfg.get("vary_reserves",True) else None
    gross={k:v*factor if v is not None else None for k,v in gross.items()}
    if fraction is not None:reserve={k:v*fraction if v is not None else None for k,v in gross.items()}
    return gross,reserve,wait_s


def _execute(client, record, profile, motion, available, reserve, path, ledger, label):
    """Guard reveals only reached poses. Charge actual directed segments once."""
    if not path:return [],available,"NO_PATH"
    response=client.ask(op="walk",cells=[_cell(record,p) for p in path],profile=asdict(motion))
    reached=[tuple(p) for p in response["traversed_points"]]
    accepted=[reached[0]]
    for a,b in zip(reached,reached[1:]):
        cost=asdict(estimate_segment(profile,a,b))
        # Reserve is not spendable, even when a hypothetical world is harder.
        if not _fits(cost,available,reserve):
            return accepted,available,"RESOURCE_GUARD_HALT"
        available=_subtract(available,cost)
        ledger.append({"kind":"movement","label":label,"start":a,"end":b,"cost":cost})
        accepted.append(b)
    return accepted,available,response["stop_reason"]


def _charge(profile, available, reserve, ledger, kind, seconds, label):
    cost=asdict(estimate_activity(profile,kind,seconds))
    if not _fits(cost,available,reserve):return available,False
    ledger.append({"kind":"activity","activity":kind,"label":label,"duration_s":seconds,"cost":cost})
    return _subtract(available,cost),True


def _strategy(name, cfg, client, record, profile, motion, belief, available, reserve, pose, base, goal,
              rigid_out, rigid_back, service, mode, limits, opportunity, common_ledger):
    ledger=list(common_ledger); decisions=[]; unknown=False; optional_unknown=False; primary=False; optional=0
    geometry_changed=False; status="STARTED"; searches=[]
    if name=="RIGID":
        outbound=list(rigid_out);back=list(rigid_back)
        estimate=_cost(profile,[*[_as_estimate(_move(profile,outbound)),_as_estimate(_move(profile,back))],
                              *[estimate_activity(profile,k,t) for k,t in service]])
        if not _fits(estimate,available,reserve):
            decisions.append({"action":"HOLD","reason":"INITIAL_ITINERARY_NO_LONGER_FITS"})
            outbound=[];back=[];status="BUDGET_HOLD"
        else:decisions.append({"action":"KEEP","reason":"FIXED_INITIAL_ITINERARY"})
    else:
        result,search=_plan(belief,record,profile,motion,pose,goal,base,available,reserve,service,mode,limits,"posterior-primary")
        searches.append(search)
        if result is not None and result.status==core.RouteStatus.FEASIBLE:
            outbound=list(result.outbound_path);back=list(result.return_path)
            geometry_changed=_xy(outbound)!=_xy(rigid_out) or _xy(back)!=_xy(rigid_back)
            decisions.append({"action":"DETOUR" if geometry_changed else "KEEP","reason":"CURRENT_MAP_AND_RESOURCES"})
        else:
            unknown=search["status"]=="UNKNOWN";outbound=[];back=[]
            status="UNKNOWN" if unknown else "PRIMARY_REJECTED"
            decisions.append({"action":"UNKNOWN" if unknown else "RETURN","reason":search.get("reason_code")})
    if outbound:
        reached,available,stop=_execute(client,record,profile,motion,available,reserve,outbound,ledger,"primary-outbound")
        pose=reached[-1];arrived=stop=="PREFIX_REACHED" and _xy([pose])==_xy([outbound[-1]])
        if arrived:
            for kind,seconds in service:
                available,ok=_charge(profile,available,reserve,ledger,kind,seconds,"primary-B-service")
                if not ok:break
            else:primary=True
            status="PRIMARY_COMPLETED" if primary else "PRIMARY_SERVICE_RESOURCE_HOLD"
        else:
            status=stop;decisions.append({"action":"HOLD","reason":stop,"guard":"analytical_private_world_safety_guard_not_sensor"})
            # A guarded retreat reverses only actually reached geometry; no new route.
            back=list(reversed(reached))
            if tuple(back[-1])!=tuple(base):
                back.extend(list(reversed([tuple(x["start"]) for x in common_ledger if x["kind"]=="movement"])))
        # Opportunity is public and identical, but fixed strategy does not add work.
        if primary and opportunity["available"] and name=="ADAPTIVE":
            event=opportunity
            compatible=profile.kind in event["capable_kinds"]
            prerequisites=primary and event["prerequisite"]=="PRIMARY_B_COMPLETED"
            if compatible and prerequisites:
                task_service=[(event["activity"],event["duration_s"])]
                task,search=_plan(belief,record,profile,motion,pose,event["position"],base,available,reserve,task_service,mode,limits,"posterior-optional")
                searches.append(search)
                if task is not None and task.status==core.RouteStatus.FEASIBLE:
                    decisions.append({"action":"ACCEPT_OPTIONAL","reason":"CAPABILITY_PRECEDENCE_DIRECTED_RETURN_AND_RESERVES_FIT","event_id":event["event_id"]})
                    reached,available,stop=_execute(client,record,profile,motion,available,reserve,task.outbound_path,ledger,"optional-outbound")
                    pose=reached[-1]
                    if stop=="PREFIX_REACHED" and _xy([pose])==_xy([event["position"]]):
                        available,ok=_charge(profile,available,reserve,ledger,event["activity"],event["duration_s"],event["event_id"])
                        optional=int(ok);back=list(task.return_path)
                    else:
                        back=list(reversed(reached))+list(back[1:]);decisions.append({"action":"HOLD","reason":stop})
                else:
                    optional_unknown=search["status"]=="UNKNOWN"
                    decisions.append({"action":"DECLINE_OPTIONAL","reason":search.get("reason_code"),"status":search["status"]})
            else:decisions.append({"action":"DECLINE_OPTIONAL","reason":"CAPABILITY_OR_PRECEDENCE"})
        elif opportunity["available"]:
            decisions.append({"action":"DECLINE_OPTIONAL","reason":"FIXED_TASK_SET" if name=="RIGID" else "PRIMARY_PRECEDENCE_INCOMPLETE"})
    if not outbound and name=="ADAPTIVE":
        ret,search=_plan(belief,record,profile,motion,pose,base,base,available,reserve,[],mode,limits,"posterior-retreat",False)
        searches.append(search)
        back=list(ret.outbound_path) if ret is not None and ret.status==core.RouteStatus.FEASIBLE else []
        unknown|=search["status"]=="UNKNOWN"
    if not outbound and name=="RIGID":
        # Fixed-route safety retreat along reached prefix, without replanning.
        back=[pose]+list(reversed([tuple(x["start"]) for x in common_ledger if x["kind"]=="movement"]))
    returned=_xy([pose])==_xy([base])
    if back and not returned:
        reached,available,stop=_execute(client,record,profile,motion,available,reserve,back,ledger,"return")
        pose=reached[-1];returned=stop=="PREFIX_REACHED" and _xy([pose])==_xy([base])
        if not returned:status="RETURN_"+stop
    margins={k:v-reserve[k] if v is not None else None for k,v in available.items()}
    cost={k:sum(x["cost"][k] for x in ledger) if available[k] is not None else None for k in available}
    violation=any(v < -1e-8 for v in available.values() if v is not None)
    reserve_violation=any(v < -1e-8 for v in margins.values() if v is not None)
    meaningful=geometry_changed or optional>0 or any(d["action"] in {"RETURN","HOLD","DECLINE_OPTIONAL"} and d.get("reason")!="FIXED_TASK_SET" for d in decisions)
    return {"primary_completed":primary,"returned":returned,"optional_completed":optional,
        "analytic_primary_and_return":primary and returned and not violation and not reserve_violation,
        "resource_violation":violation,"reserve_violation":reserve_violation,"unknown":unknown,"optional_unknown":optional_unknown,"status":status,
        "decision_changed":meaningful,"geometry_changed":geometry_changed,"elapsed_s":cost["time_s"],
        "energy_wh":cost["energy_wh"],"oxygen_l":cost["oxygen_l"],"remaining":available,"reserve_margins":margins,
        "pose":pose,"service_ledger":ledger,"decisions":decisions,"searches":searches,
        "completion_kind":"SIMULATED_ANALYTICAL_NOT_OPERATIONAL_EVIDENCE"}


def _as_estimate(value):
    from mge_mission.models import CostEstimate
    return CostEstimate(**value)


def _unavailable(status, unknown=True):
    return {"primary_completed":False,"returned":False,"optional_completed":0,"unknown":unknown,
        "resource_violation":False,"reserve_violation":False,"status":status,"decision_changed":False,
        "analytic_primary_and_return":False,"completion_kind":"NO_EXECUTED_ITINERARY_NOT_PHYSICAL_FAILURE"}


def run_block(cfg, case):
    start=time.perf_counter();record=read(case["record_path"]);path=Path(case["map_path"])
    block_id=case["block_id"]
    out={**case,"classification":"SIMULATED","status":"STARTED","pairs":[],"source_sha":cfg["source_sha"],
         "input_hashes":{"map":sha(path),"record":sha(case["record_path"]),"profiles":sha(cfg["profiles_path"])}}
    try:
        if record["file_sha256"]!=sha(path):raise ValueError("PUBLIC_MAP_HASH_MISMATCH")
        with np.load(path,allow_pickle=False) as a:
            z=np.asarray(a["elevation_m"],dtype=float);z[~a["valid_mask"].astype(bool)]=np.nan
        rng=np.random.default_rng(np.random.SeedSequence([20261115,NAMESPACE,case["sector_index"],case["side_m"],FAMILIES.index(case["family"]),case["index"],0]))
        endpoints=endpoint_cells(z,rng,64)
        if endpoints is None:out["status"]="ENDPOINT_UNAVAILABLE";return out
        base,goal=(_point(record,z,c) for c in endpoints)
        profiles=load_profiles(cfg["profiles_path"])
        preliminary=[]
        for agent in cfg.get("agents",["human_1","rover_1"]):
            profile=profiles[agent]
            profile=replace(profile,parameters={**profile.parameters,"max_sigma_m":cfg.get("max_sigma_m",3.)},approval_status="illustrative")
            projection=export_planner_profiles({agent:profile})
            if cfg.get("grade_consistent_projection",True):projection=orbital_grade_projection(projection,4.)
            motion=core.MotionProfile(**projection["profiles"][agent])
            gross,reserve,wait_s=_allocation(cfg,case["sector"],profile,case["index"])
            service=[("inspect",120. if profile.kind=="human" else (300.,600.,900.)[case["index"]%3])]
            wait_cost=asdict(estimate_activity(profile,"wait",wait_s));available=_subtract(gross,wait_cost)
            belief=BeliefMap.from_arrays(z,run_id=block_id,dataset_id=record["id"],resolution_m=4.,origin_x_m=record["origin_x_m"],origin_y_m=record["origin_y_m"])
            for mode in cfg.get("modes",["FAST","SAFE"]):
                initial,item=_plan(belief,record,profile,motion,base,goal,base,available,reserve,service,mode,cfg["search_limits"],"common-initial-"+agent+mode)
                preliminary.append((profile,motion,gross,reserve,available,belief,service,initial,item,mode,wait_s,wait_cost))
        target=None
        if case.get("design","broad")=="directed":
            feasible=next((p[7] for p in preliminary if p[7] is not None and p[7].status==core.RouteStatus.FEASIBLE and len(p[7].outbound_path)>6),None)
            if feasible:target=_cell(record,feasible.outbound_path[max(2,len(feasible.outbound_path)//4)+2])
        spec={"family":case["family"],"world_seed":[20261115,NAMESPACE,case["sector_index"],case["side_m"],FAMILIES.index(case["family"]),case["index"],1],
            "base":list(endpoints[0]),"goal":list(endpoints[1]),"directed":case.get("design")=="directed","target":target,
            "amplitude_m":(.1,.2,.3)[case["index"]%3],"correlation_m":(8.,16.,32.)[case["index"]%3],"obstacle_cells":(1,2,4)[case["index"]%3]}
        client=WorldClient(Path(cfg["script_path"]),Path(cfg["output_dir"]),Path(cfg["output_dir"])/(block_id.replace("/","_")+".world.log"))
        try:
            out["world_metadata"]=client.ask(op="create",public_path=str(path),record=record,spec=spec)
            out["world_spec"]=spec;out["endpoint_cells"]=endpoints;out["base"]=base;out["goal"]=goal
            for profile,motion,gross,reserve,available,belief,service,initial,item,mode,wait_s,wait_cost in preliminary:
                pair={"agent_id":profile.agent_id,"mode":mode,"initial_status":item["status"],"initial":item,"strategies":{},
                      "condition_id":profile.agent_id+":"+mode,"gross":gross,"reserves":reserve,"motion_profile":asdict(motion)}
                out["pairs"].append(pair)
                if initial is None or initial.status!=core.RouteStatus.FEASIBLE:
                    pair["status"]="INITIAL_UNAVAILABLE"
                    pair["strategies"]={s:_unavailable(item["status"],item["status"]=="UNKNOWN") for s in ("RIGID","ADAPTIVE")}
                    continue
                prefix_index=max(1,len(initial.outbound_path)//4)
                prefix=list(initial.outbound_path[:prefix_index+1]);ledger=[{"kind":"activity","activity":"wait","label":"initial-coordination","duration_s":wait_s,"cost":wait_cost}]
                reached,remaining,stop=_execute(client,record,profile,motion,available,reserve,prefix,ledger,"common-prefix")
                pose=reached[-1];pair["common_prefix_stop"]=stop
                if stop!="PREFIX_REACHED":
                    pair["status"]="COMMON_PREFIX_HALTED";pair["common_reached"]=reached
                    pair["strategies"]={s:_unavailable(stop) for s in ("RIGID","ADAPTIVE")};continue
                response=client.ask(op="observe",center_xy=list(pose[:2]),radius_m=cfg.get("footprint_radius_m",12.))
                obs=SimulatedObservation(block_id+":"+profile.agent_id+":"+mode+":paid",profile.agent_id,belief.run_id,belief.map_version,
                    sum(x["cost"]["time_s"] for x in ledger),tuple(response["cell_indices"]),tuple(response["elevations_m"]),tuple(response["sigmas_m"]),tuple(response["obstacles"]))
                belief=fuse_observation(belief,obs)
                remaining,ok=_charge(profile,remaining,reserve,ledger,"inspect",cfg.get("observation_duration_s",120.),"paid-common-observation")
                if not ok:
                    pair["status"]="OBSERVATION_RESOURCE_UNAVAILABLE"
                    pair["strategies"]={s:_unavailable(pair["status"]) for s in ("RIGID","ADAPTIVE")};continue
                if case["family"]=="resource":
                    seconds=(120.,300.,600.)[case["index"]%3]
                    remaining,ok=_charge(profile,remaining,reserve,ledger,"wait",seconds,"common-posterior-delay")
                    if not ok:
                        pair["status"]="COMMON_DELAY_RESOURCE_HALT"
                        pair["strategies"]={s:_unavailable(pair["status"]) for s in ("RIGID","ADAPTIVE")};continue
                opportunity={"event_id":block_id+":public-opportunity","source_kind":"SIMULATED_PUBLIC_TYPED_EVENT",
                    "available":case["index"]%2==0,"position":goal,"prerequisite":"PRIMARY_B_COMPLETED",
                    "capable_kinds":[profile.kind],"activity":"inspect",
                    "duration_s":600. if profile.kind=="human" else (300.,600.,900.)[case["index"]%3],
                    "appearance_phase":"AFTER_SHARED_REACHED_OBSERVATION","inspection_evidence":"primary_B_service_required_before_optional",
                    "event_semantics":"EXOGENOUS_SIMULATED_PUBLIC_MISSION_NOTICE_NOT_SENSOR_DISCOVERY",
                    "task_scope":"additional_inspection_not_sampling_workflow"}
                pair.update(status="PAIRED",common_observation=asdict(obs),common_reached=reached,common_remaining=remaining,
                            opportunity=opportunity,common_paid_schedule=[(x.get("activity"),x.get("duration_s")) for x in ledger if x["kind"]=="activity"])
                for strategy in ("RIGID","ADAPTIVE"):
                    pair["strategies"][strategy]=_strategy(strategy,cfg,client,record,profile,motion,belief,dict(remaining),reserve,pose,base,goal,
                        initial.outbound_path[prefix_index:],initial.return_path,service,mode,cfg["search_limits"],opportunity,ledger)
                pair["same_initial_candidate"]=True;pair["same_world"]=True;pair["same_paid_observation_and_reached_prefix"]=True
            out["status"]="COMPLETED_PAIRED_BLOCK"
            out["world_sha256"]=out["world_metadata"]["world_sha256"]
        finally:client.close()
    except Exception as error:
        out.update(status="ERROR",error_type=type(error).__name__,error=str(error),traceback=traceback.format_exc())
    finally:out["wall_s"]=time.perf_counter()-start
    return out


def run_study(config_path):
    cfg=read(config_path);root=Path(cfg["output_dir"]);root.mkdir(parents=True,exist_ok=True)
    cases=[]
    for record_path in cfg["map_records"]:
        record=read(record_path);sector=record["region"]["id"]
        for family in cfg.get("families",FAMILIES):
            for index in range(cfg.get("indices",16)):
                for design in cfg.get("designs",["broad"]):
                    block_id=f"{sector}-{record['side_m']}-{family}-{index}-{design}"
                    cases.append({"block_id":block_id,"record_path":str(Path(record_path).resolve()),
                        "map_path":str((Path(record_path).parent/Path(record["path"]).name).resolve()),"map_id":record["id"],
                        "sector":sector,"sector_index":("bright","hawksbill","bunsen").index(sector),"side_m":record["side_m"],
                        "family":family,"index":index,"design":design,"partition":"holdout" if index%16>=12 else "exploration"})
    # Interleave sectors/families/sizes, preserving all scheduled indices.
    cases.sort(key=lambda c:(c["index"],c["family"],c["side_m"],c["sector"],c["design"]))
    identity=digest(cfg);journal=Journal(root/"paired-blocks.jsonl",identity)
    if not (root/"manifest.json").exists():
        import scipy
        imported={name:{"path":str(Path(module.__file__).resolve()),"sha256":sha(module.__file__)}
                  for name,module in sorted(sys.modules.items())
                  if name.startswith(("mge_mission","mge_planning","mge_mapping","mge_data")) and getattr(module,"__file__",None) and Path(module.__file__).is_file()}
        write_new(root/"manifest.json",{"identity":identity,"config":cfg,"planned_cases":cases,"classification":"SIMULATED_ANALYTICAL",
            "root_seed":20261115,"seed_namespace":NAMESPACE,"code_sha256":sha(__file__),"script_sha256":sha(cfg["script_path"]),
            "imported_module_locks":imported,"software_versions":{"python":platform.python_version(),"numpy":np.__version__,"scipy":scipy.__version__},
            "map_locks":[{"record_path":r,"record_sha256":sha(r),"map_sha256":read(r)["file_sha256"]} for r in cfg["map_records"]],
            "no_seed_replacement":True,"unit":"independent_world_block_modes_agents_strategies_nested",
            "ai_usage":{"tool":"Codex","scope":"experimental Python runner and synthetic records; not observational NASA data"}})
    workers=cfg.get("workers",3)
    if not 1<=workers<=6:raise ValueError("At most six paired workers; each starts one private-world process")
    pending=[case for case in cases if case["block_id"] not in journal.ids]
    deadline=datetime.fromisoformat(cfg["deadline_utc"].replace("Z","+00:00"))
    inflight={};submitted=0
    with ProcessPoolExecutor(max_workers=workers) as pool:
        while pending or inflight:
            can_start=now()<deadline
            while pending and len(inflight)<workers and can_start:
                case=pending.pop(0);future=pool.submit(run_block,cfg,case);inflight[future]=case;submitted+=1
            if not inflight:break
            done,_=wait(inflight,timeout=1.,return_when=FIRST_COMPLETED)
            for future in done:
                case=inflight.pop(future)
                try:result=future.result()
                except Exception as error:result={**case,"status":"WORKER_ERROR","error":str(error),"pairs":[]}
                journal.append(case["block_id"],result)
                print(canonical({"completed":len(journal.rows),"planned":len(cases),"block_id":case["block_id"],"status":result["status"]}),flush=True)
            if not can_start:pending=[]
    summary={"completed_blocks":len(journal.rows),"planned_blocks":len(cases),"journal_sha256":sha(journal.path),
             "remaining_case_ids":[case["block_id"] for case in cases if case["block_id"] not in journal.ids],"ended_at_utc":now().isoformat()}
    target=root/("summary-"+now().strftime("%H%M%S")+".json");write_new(target,summary)
    return summary
