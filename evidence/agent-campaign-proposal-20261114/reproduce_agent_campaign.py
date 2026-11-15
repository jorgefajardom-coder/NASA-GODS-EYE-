"""Price declared analytical agent workloads; no route, execution or hardware approval."""
import argparse
from dataclasses import asdict, replace
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src/mge_mission"))
from mge_mission.models import MODEL_ID, estimate_activity, estimate_segment, load_profiles


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def add(profile, costs):
    return {"time_s": sum(c["time_s"] for c in costs),
            "energy_wh": sum(c["energy_wh"] for c in costs),
            "oxygen_l": sum(c["oxygen_l"] for c in costs) if profile.kind == "human" else None}


def phase(profile, name, *, activity=None, duration=None, start=None, end=None):
    cost = estimate_activity(profile, activity, duration) if activity else estimate_segment(profile, start, end)
    return {"phase": name, "activity": activity, "duration_input_s": duration,
            "start_analytic_enu_m": start, "end_analytic_enu_m": end, "cost": asdict(cost)}


def total(profile, phases):
    return add(profile, [p["cost"] for p in phases])


def allocation(profile, cost, fraction, rounding):
    quanta = {"time_s": rounding[f"{profile.kind}_time_s"], "energy_wh": rounding[f"{profile.kind}_energy_wh"]}
    if profile.kind == "human":
        quanta["oxygen_l"] = rounding["human_oxygen_l"]
    requested = {key: math.ceil(cost[key] / (1-fraction) / step) * step for key, step in quanta.items()}
    reserves = {key: value * fraction for key, value in requested.items()}
    return {"requested": requested, "separate_reserves": reserves, "reserve_fraction": fraction,
            "scope": "Engineering requirement, not battery/suit capacity or physical availability"}


def compare(cost, cap):
    margins = {key: cap["requested"][key] - cap["separate_reserves"][key] - cost[key] for key in cap["requested"]}
    return {"reserve_margins": margins, "modeled_resource_envelope_fits": all(v >= 0 for v in margins.values()),
            "candidate_authorized": False, "tolerance_budget_credit": False}


def adverse(profile, registry):
    params, powers, changes = dict(profile.parameters), dict(profile.activity_power_w), []
    minimum = {"speed_m_s", "vertical_speed_m_s", "climb_efficiency", "drive_efficiency"}
    maximum = {"mass_kg", "body_mass_kg", "suit_mass_kg", "slope_slowdown", "slip", "rolling_resistance", "auxiliary_power_w", "oxygen_scale"}
    for item in registry["assumptions"]:
        parts = item["parameter"].split(".")
        if len(parts) != 4 or parts[1] != profile.agent_id:
            continue
        group, name = parts[2:]
        if group == "activity_power_w" or (group == "parameters" and name in minimum | maximum):
            endpoint = "sensitivity_min" if name in minimum else "sensitivity_max"
            (powers if group == "activity_power_w" else params)[name] = item[endpoint]
            changes.append({"parameter": item["parameter"], "nominal": item["value"], "endpoint": endpoint, "value": item[endpoint]})
    return replace(profile, parameters=params, activity_power_w=powers), changes


def human(case, profile, assumptions, stress=False, drop_sample=False):
    factors = assumptions["joint_adverse"]
    d = case["human_total_horizontal_m"] * (factors["distance_factor"] if stress else 1)
    h = case["human_positive_ascent_m"] * (factors["positive_ascent_factor"] if stress else 1)
    service = factors["service_duration_factor"] if stress else 1
    n = max(0, case["human_sample_workflows"] - int(drop_sample))
    phases = [phase(profile, "outbound", start=[0,0,0], end=[d/2,0,h]),
              phase(profile, "primary_visual_checkin_not_optional_inspection", activity="inspect", duration=assumptions["human"]["primary_checkin_s"]*service)]
    for i in range(n):
        phases += [phase(profile, f"documented_sample_{i+1}_light", activity="inspect", duration=assumptions["human"]["sample_light_phase_s"]*service),
                   phase(profile, f"documented_sample_{i+1}_heavy", activity="sample", duration=assumptions["human"]["sample_heavy_phase_s"]*service)]
    phases += [phase(profile, "coordination_wait", activity="wait", duration=case["human_coordination_wait_s"]),
               phase(profile, "directed_return", start=[d/2,0,h], end=[0,0,0])]
    return {"phases": phases, "total": total(profile, phases), "sample_workflows": n,
            "total_horizontal_m": d, "positive_ascent_m": h, "source": "Analytical workload only, not a terrain route"}


def rover(case, profile, assumptions, human_elapsed, stress=False):
    factors = assumptions["joint_adverse"]
    d = case["rover_total_horizontal_m"] * (factors["distance_factor"] if stress else 1)
    h = case["rover_positive_ascent_m"] * (factors["positive_ascent_factor"] if stress else 1)
    service = factors["service_duration_factor"] if stress else 1
    phases = [phase(profile, "outbound_reconnaissance", start=[0,0,0], end=[d/2,0,h])]
    phases += [phase(profile, f"visual_station_{i+1}", activity="inspect", duration=assumptions["rover"]["visual_station_s"]*service)
               for i in range(case["rover_visual_stations"])]
    phases += [phase(profile, "pre_EVA_coordination", activity="wait", duration=assumptions["rover"]["coordination_wait_s"])]
    prefix = total(profile, phases)["time_s"]
    phases += [phase(profile, "wait_during_actual_human_EVA", activity="wait", duration=human_elapsed),
               phase(profile, "directed_return_after_human", start=[d/2,0,h], end=[0,0,0])]
    cost = total(profile, phases)
    return {"phases": phases, "total": cost, "human_launch_offset_s": prefix,
            "human_end_offset_s": prefix + human_elapsed, "rover_return_offset_s": cost["time_s"],
            "human_predeployment_charged_to_EVA": False, "unpriced_extra_calendar_gap": False,
            "timing_scope": "Episode ends at rover return; any additional night/hold interval needs a new cost, never free time"}


def drone(case, profile, assumptions, stress=False):
    factors, a = assumptions["joint_adverse"], assumptions["drone"]
    distance = case["drone_outward_horizontal_m"] * (factors["distance_factor"] if stress else 1)
    altitude = a["altitude_m"] * (factors["positive_ascent_factor"] if stress else 1)
    service = factors["service_duration_factor"] if stress else 1
    phases = [phase(profile, "takeoff_hover_surrogate", activity="hover", duration=a["takeoff_hover_surrogate_s"]*service),
        phase(profile, "vertical_ascent", start=[0,0,0], end=[0,0,altitude]),
        phase(profile, "outward_translation", start=[0,0,altitude], end=[distance,0,altitude]),
        phase(profile, "suspended_observation", activity="observe", duration=a["observation_s"]*service),
        phase(profile, "return_translation", start=[distance,0,altitude], end=[0,0,altitude]),
        phase(profile, "vertical_descent", start=[0,0,altitude], end=[0,0,0]),
        phase(profile, "landing_hover_surrogate", activity="hover", duration=a["landing_hover_surrogate_s"]*service),
        phase(profile, "ground_wait", activity="ground_wait", duration=a["ground_wait_s"])]
    one = total(profile, phases)
    airborne = sum(p["cost"]["time_s"] for p in phases if p["phase"] != "ground_wait")
    n = case["drone_sorties"]
    return {"phases_per_sortie": phases, "per_sortie": one, "airborne_time_s": airborne,
            "historical_Flight12_reference_s": 169.5, "exceeds_historical_reference": airborne > 169.5,
            "historical_record_is_certified_limit": False, "sorties": n,
            "known_subset_total": add(profile, [one]*n),
            "cumulative_consumption_after_each_sortie": [add(profile, [one]*i) for i in range(1,n+1)],
            "energy_reset_between_sorties": False, "recharge_credit_wh": 0,
            "whole_campaign_energy_status": "NOT_ESTIMATED_SLEEP_THERMAL_RECHARGE_UNMODELED",
            "whole_campaign_feasible": None, "flight_validated": False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path(__file__).with_name("campaign_analysis.json"))
    args = parser.parse_args()
    revision = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT).decode().strip()
    if revision != "c3ec4c1f1515dbc981ba82eed2ab1f54e9586264":
        raise ValueError("Use the pinned local scientific source baseline")
    assumption_path = Path(__file__).with_name("assumptions.proposed.json")
    assumptions = json.loads(assumption_path.read_text(encoding="utf-8"))
    registry_path = ROOT / "config/science_profiles.proposed.json"
    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    profiles = load_profiles(registry_path)
    variants = {name: adverse(p, registry) for name,p in profiles.items()}
    names = ["config/science_profiles.proposed.json", "config/mission_jezero.experimental.yaml", "config/mission_jezero.proposed.yaml",
             "src/mge_mission/mge_mission/models.py", "docs/science_approvals/jezero_scenario_20261114.json",
             "evidence/science-patch-survey-20261114/jezero_candidates.proposed.json", "evidence/science-patch-survey-20261114/map_requests.proposed.json"]
    identities = {name: sha(ROOT/name) for name in names}
    identities[assumption_path.relative_to(ROOT).as_posix()] = sha(assumption_path)
    identities[Path(__file__).relative_to(ROOT).as_posix()] = sha(Path(__file__))
    rows = []
    for case in assumptions["cases"]:
        hp, rp, dp = (profiles[k] for k in ("human_1", "rover_1", "drone_1"))
        h = human(case,hp,assumptions); r = rover(case,rp,assumptions,h["total"]["time_s"]); d = drone(case,dp,assumptions)
        nominals = {"human":h["total"], "rover":r["total"], "drone":d["known_subset_total"]}
        caps = {p.kind: allocation(p,nominals[p.kind],assumptions["reserve_fraction"],assumptions["rounding"]) for p in (hp,rp,dp)}
        hh = human(case,variants[hp.agent_id][0],assumptions,True)
        rr = rover(case,variants[rp.agent_id][0],assumptions,hh["total"]["time_s"],True)
        dd = drone(case,variants[dp.agent_id][0],assumptions,True)
        hf = human(case,hp,assumptions,drop_sample=True)
        rf = rover(case,rp,assumptions,hf["total"]["time_s"])
        hfa = human(case,variants[hp.agent_id][0],assumptions,True,True)
        rfa = rover(case,variants[rp.agent_id][0],assumptions,hfa["total"]["time_s"],True)
        def checked(profile, value, cap):
            return {**value, **compare(value["total"],cap)}
        gap = max(0,r["total"]["time_s"]-d["known_subset_total"]["time_s"])
        rows.append({"case":case,"nominal":{"human":checked(hp,h,caps["human"]),"rover":checked(rp,r,caps["rover"]),
             "drone":{**d,**compare(d["known_subset_total"],caps["drone"]) }},
             "requested_caps":caps,"drone_per_sortie_cap":allocation(dp,d["per_sortie"],assumptions["reserve_fraction"],assumptions["rounding"]),
             "joint_adverse":{"human":checked(hp,hh,caps["human"]),"rover":checked(rp,rr,caps["rover"]),"drone":{**dd,**compare(dd["known_subset_total"],caps["drone"]) }},
             "drop_one_optional_sample_same_route":{"nominal_human":checked(hp,hf,caps["human"]),"nominal_rover":checked(rp,rf,caps["rover"]),
                "adverse_human":checked(hp,hfa,caps["human"]),"adverse_rover":checked(rp,rfa,caps["rover"]),"route_shortening_invented":False},
             "reserve_policy_sensitivity":{str(f):{p.kind:allocation(p,nominals[p.kind],f,assumptions["rounding"]) for p in (hp,rp,dp)} for f in assumptions["reserve_fraction_sensitivity"]},
             "drone_awake_gap_thought_experiment":{"gap_s":gap,"power_w":dp.activity_power_w["ground_wait"],
                "additional_energy_wh":gap*dp.activity_power_w["ground_wait"]/3600,"known_subset_plus_awake_proxy_wh":d["known_subset_total"]["energy_wh"]+gap*dp.activity_power_w["ground_wait"]/3600,
                "interpretation":"Subtracts already priced flights/ground phases from rover episode; illustrative awake proxy only, not a sleep or full hardware model"},
             "rover_nominal_episode_within_one_sol_reference":r["total"]["time_s"]<=assumptions["calendar_reference"]["sol_s"],
             "mission_execution_authorized":False,"operational_feasible":None})
    sol = assumptions["calendar_reference"]["sol_s"]
    report = {"schema_version":"1.0.0","run_id":"agent-campaign-analytic-proposal-20261114","classification":"ANALYTICAL_DESIGN_REQUIREMENTS_NOT_ROUTES_OR_HARDWARE_CAPACITIES",
        "recorded_at_utc":datetime.now(timezone.utc).isoformat(),"revision":revision,"working_tree_dirty":bool(subprocess.check_output(["git","status","--porcelain"],cwd=ROOT).strip()),
        "command":[sys.executable,*sys.argv],"model_id":MODEL_ID,"source_sha256":identities,"assumptions":assumptions,
        "adverse_profile_endpoint_changes":{key:value[1] for key,value in variants.items()},"cases":rows,
        "standby_calendar_thought_experiment":[{"sols":n,"elapsed_s":sol*n,"rover_wait_energy_wh_80w":80*sol*n/3600,
            "rover_wait_energy_wh_96w":96*sol*n/3600,"MMRTG_110w_gross_reference_wh":110*sol*n/3600,
            "generation_credit_wh":0,"battery_capacity_wh":None,"state_of_charge_proven":False,"net_feasibility":None} for n in (1,2)],
        "limitations":["Distances/ascent/stations are proposed workloads, not extracted terrain routes or completed work.",
            "Conditional upon georegistration, public geometry/uncertainty, instruments, model agreement and separate approvals.",
            "Joint adverse endpoints are a declared stress case, not confidence bounds or a global worst-case proof.",
            "Human oxygen is metabolic dry-gas equivalent, excluding complete life-support losses; Wh is metabolic, not suit battery energy.",
            "No wind cleaning, charging, generation, sleep or thermal capacity is assumed; gross energy is not stored battery availability.",
            "Aircraft phases are surrogates; neither clearance nor aerodynamic/flight validation is established.",
            "Campaign beyond the priced episode needs explicit gap costs; no idle interval is free and no sortie resets cumulative energy."],
        "scientific_approval":False,"cost_agreement_approved":False,"mission_execution_authorized":False,"integrated_mission_executed":False,"new_mock_created":False}
    if any(sha(ROOT/name)!=value for name,value in identities.items()):
        raise ValueError("Inputs changed during analysis")
    with args.output.resolve().open("x",encoding="utf-8",newline="\n") as stream:
        stream.write(json.dumps(report,indent=2,allow_nan=False)+"\n")
    print(json.dumps({"output":str(args.output),"cases":len(rows),"nominal_caps":{row["case"]["id"]:row["requested_caps"] for row in rows}}))


if __name__ == "__main__":
    main()
