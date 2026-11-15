"""Predeclared draws and strict, separate scientific accounting."""
from dataclasses import asdict, replace
import math

import numpy as np
from scipy.stats import qmc

from mge_mission.models import estimate_activity, estimate_segment, export_planner_profiles, load_profiles
from mge_planning.core import MotionProfile, ResourceBudget

from .protocol import FAMILIES, REGIONS, read


def rng_for(region, family, index, stream, size=0):
    return np.random.default_rng(np.random.SeedSequence([20261115,region,FAMILIES.index(family),index,stream,size]))


def sample_design(root, region_index, family, index, agent_id):
    registry=read(root/"profiles.source.json")
    profiles=load_profiles(root/"profiles.source.json")
    profile=profiles[agent_id]
    # All policies and extents share these draws. Geometry and world streams differ.
    records=[r for r in registry["assumptions"] if r["parameter"].startswith(f"profiles.{agent_id}.parameters.")
             and r["sensitivity_min"]!=r["sensitivity_max"] and not r["parameter"].endswith("max_sigma_m")]
    seed=np.random.default_rng(np.random.SeedSequence([20261115,region_index,FAMILIES.index(family),101,0 if profile.kind=="human" else 1]))
    sample=qmc.LatinHypercube(len(records)+5,rng=seed).random(16)[index]
    params=dict(profile.parameters)
    changes=[]
    for r,u in zip(records,sample):
        key=r["parameter"].split(".")[-1]
        value=r["sensitivity_min"]+float(u)*(r["sensitivity_max"]-r["sensitivity_min"])
        params[key]=value
        changes.append({"parameter":r["parameter"],"value":value,"min":r["sensitivity_min"],"max":r["sensitivity_max"],"origin":r["origin"],"source_url":r["source_url"]})
    params["max_sigma_m"]=3.
    power_factor=.8+.4*float(sample[-5])
    profile=replace(profile,parameters=params,activity_power_w={k:v*power_factor for k,v in profile.activity_power_w.items()},approval_status="illustrative")
    projection=export_planner_profiles({agent_id:profile})
    motion=MotionProfile(**projection["profiles"][agent_id])
    analyses=read(root/"campaign-campaign_analysis.json")
    row=next(x for x in analyses["cases"] if x["case"]["id"]==REGIONS[region_index]["campaign"])
    budget_factor=.8+.4*float(sample[-4])
    fraction=(.1,.2,.3)[min(2,int(sample[-3]*3))]
    request={k:v*budget_factor for k,v in row["requested_caps"][profile.kind]["requested"].items()}
    reserves={k:v*fraction for k,v in request.items()}
    budget=ResourceBudget(profile.kind,request["time_s"],request["energy_wh"],reserves["energy_wh"],request.get("oxygen_l"),reserves.get("oxygen_l"))
    wait_factor=.5+float(sample[-2])
    case=row["case"]
    if profile.kind=="human":
        workflow=(600,900)[int(sample[-1]>=.5)]
        optional=[("inspect",workflow*.7),("sample",workflow*.3)]*case["human_sample_workflows"]
        primary=[("inspect",120.)]
        wait=case["human_coordination_wait_s"]*wait_factor
    else:
        station=(300,600,900)[min(2,int(sample[-1]*3))]
        primary=[("inspect",float(station))]
        optional=[("inspect",float(station))]*(case["rover_visual_stations"]-1)
        wait=(1800+row["nominal"]["human"]["total"]["time_s"])*wait_factor
    return {"profile":profile,"motion":motion,"budget":budget,"reserves":reserves,"primary":primary,
            "optional":optional,"wait_s":wait,"nominal_wait_s":wait/wait_factor,"budget_factor":budget_factor,"reserve_fraction":fraction,
            "draws":changes,"power_factor":power_factor,"projection":projection,
            "drone_known_cap":row["requested_caps"]["drone"],"drone_per_sortie_cap":row["drone_per_sortie_cap"]}


def nominal_design(root, region_index, agent_id, strict=False):
    d=sample_design(root,region_index,"unchanged",0,agent_id)
    profiles=load_profiles(root/"profiles.source.json")
    p=profiles[agent_id]
    params={**p.parameters,"max_sigma_m":1. if strict else 3.}
    p=replace(p,parameters=params,approval_status="illustrative")
    d["profile"]=p
    d["motion"]=MotionProfile(**export_planner_profiles({agent_id:p})["profiles"][agent_id])
    row=read(root/"campaign-campaign_analysis.json")["cases"]
    row=next(x for x in row if x["case"]["id"]==REGIONS[region_index]["campaign"])
    cap=row["requested_caps"][p.kind]
    b=cap["requested"]; r=cap["separate_reserves"]
    d.update(budget=ResourceBudget(p.kind,b["time_s"],b["energy_wh"],r["energy_wh"],b.get("oxygen_l"),r.get("oxygen_l")),reserves=r,
             wait_s=600. if p.kind=="human" else 1800.,primary=[("inspect",120. if p.kind=="human" else 600.)],optional=[])
    return d


def endpoint_cells(z, rng, attempts=64, fixed_span=None):
    rows,cols=z.shape
    margin=2
    for _ in range(attempts):
        if fixed_span is None:
            a=(int(rng.integers(margin,rows-margin)),int(rng.integers(margin,cols-margin)))
            b=(int(rng.integers(margin,rows-margin)),int(rng.integers(margin,cols-margin)))
            distance=math.dist(a,b)
            if not rows/8<=distance<=rows/2:
                continue
        else:
            # Extent-only comparison: identical physical A/B in every nested grid.
            a=(rows//2-4,cols//2-4)
            b=(rows//2+4,cols//2+4)
        if np.isfinite(z[a]) and np.isfinite(z[b]):
            return a,b
    return None


def sum_costs(profile, costs):
    return {"time_s":sum(c["time_s"] for c in costs),"energy_wh":sum(c["energy_wh"] for c in costs),
            "oxygen_l":sum(c["oxygen_l"] for c in costs) if profile.kind=="human" else None}


def movement(profile, path):
    return sum_costs(profile,[asdict(estimate_segment(profile,tuple(a),tuple(b))) for a,b in zip(path,path[1:])])


def activities(profile, schedule):
    return sum_costs(profile,[asdict(estimate_activity(profile,a,t)) for a,t in schedule])


def subtract(available, cost):
    # Negative availability is retained by the ledger; never reset/clamp into credit.
    return {k:v-cost[k] if v is not None else None for k,v in available.items()}


def within(cost, available, reserves):
    margins={k:available[k]-reserves[k]-v for k,v in cost.items() if v is not None}
    return {"resource_envelope_fits":all(v>=0 for v in margins.values()),"margins":margins}


def scientific_audit(profile, result, schedule, available, reserves):
    if result.status.value!="FEASIBLE":
        return {"status":"NO_ITINERARY","resource_envelope_fits":None,"model_agreement":False}
    try:
        travel=movement(profile,result.outbound_path)
        back=movement(profile,result.return_path)
        service=activities(profile,schedule)
        cost=sum_costs(profile,[travel,back,service])
        reported={"time_s":result.travel_time_s,"energy_wh":result.energy_est_wh,"oxygen_l":result.oxygen_est_l}
        matches={k:math.isclose(v,reported[k],rel_tol=1e-5,abs_tol=.001) for k,v in cost.items() if v is not None}
        return {"status":"AUDITED", "cost":cost, "components":{"outbound":travel,"return":back,"service":service},
                **within(cost,available,reserves),"numerical_projection_match":matches,"model_agreement":False}
    except ValueError as error:
        return {"status":"SCIENTIFIC_REJECTED","detail":str(error),"resource_envelope_fits":False,"model_agreement":False}
