# Route resource sufficiency check (viewer alerts)

Status: **display check, proposed**. It does not change the planner, MissionManager,
the ICD or any recorded result. The reserve share it uses is the project's approved
**experimental** policy JZ-P06 ([science_decisions.md](science_decisions.md)), not a
NASA standard. David approves scientific assumptions; this note asks for that review
of the assumptions in section 4.

Code: `web/src/lib/routeSufficiency.ts` (calculation), `web/src/lib/resourceAlert.ts`
(alert wording), shown in the first-person HUD (`FirstPersonHud.tsx`). Tests:
`web/tests/resourceAlert.test.ts`.

## 1. Why: when a resource is dangerous

On a surface EVA the danger is not a low number on its own but **not being able to get
back**. NASA's planning documents tie the safe distance from the lander or habitat to
the consumables needed to return:

- *Tenets of Lunar EVAs for Artemis III* (NASA, 2023, p. 2, tenet 5): distance from the
  lander is at most 2 km "from a suit contingency constraint assuming a 1hr crew emergency
  return capability based on xEVAS contingency O2 requirements", and that return time
  depends on terrain, lighting, O2 supply and walk-back rate. Tenet 7: "a contingency
  reserve is required for each EVA to protect safe crew return."
  <https://ntrs.nasa.gov/citations/20230008183>
- Z. C. Scoville, *Artemis III EVA mission capability for de Gerlache-Shackleton ridge*,
  LPSC 2022, abstract 1079: "At any point during an EVA, astronauts must be able to return
  to the lander and repressurize the airlock within one hour. This time is driven by
  reserve suit consumables" (about 1.38 km there).
  <https://www.hou.usra.edu/meetings/lpsc2022/pdf/1079.pdf>
- NASA EVA-EXP-0075, *Lunar surface EVA concept of operations* (2020, p. 22): walking range
  about 2 km on level regolith, unpressurized rover about 10 km "(~5 hr walk back)", with
  "Distance must be balanced with suit consumables remaining"; slopes and obstacles shorten
  it. <https://www.nasa.gov/wp-content/uploads/2020/01/topic_1-_eva_lunar_surface_concept_of_operations.pdf>

So the check asks, at every moment of the replay and for every resource of the viewed
agent: **is what is left enough to finish the route and come back, keeping the reserve;
and if not, is it still enough to walk back now?** That is the walk-back rule above,
written for our received data. Our scenario is a Mars analog with the project's own
budgets; the Moon figures (2 km, 1 h) are not copied, only the rule.

## 2. Inputs (received data only)

| Input | Source | Note |
|---|---|---|
| Whole-itinerary cost `C` (`travel_time_s`, `energy_est_wh`, `oxygen_est_l`) | `RouteDecision` (ICD) | Outbound plus the costed return (JZ-P06: "in addition to costed return") |
| Outbound and return paths | `RouteDecision.outbound_path`, `return_path` | ENU metres; lengths `L_out`, `L_ret` on the ground plane |
| Remaining amount `E` | `AgentState` at the replay time | Oxygen for the astronaut only |
| Reference `B` | First received sample of the agent (viewer budget) | Same reference as the dial gauges |
| Reserve share `f = 0.20` | JZ-P06 (approved experimental) | Human 240 s / 20 Wh / 5 L, rover 240 s / 12 Wh, drone 36 s / 3 Wh at the proposal allocations |

The check only runs on a route that belongs to the viewed agent. Without one, it can only
say whether the reserve itself is being used (`E < f·B`).

## 3. Calculation

Cost per metre of itinerary, for each resource: `r = C / (L_out + L_ret)`.

Position on the itinerary (`routeProgress`, projection on the nearest segment):

- outbound: distance still to go `D_go = remaining outbound + L_ret`; distance already
  travelled outbound `D_back = L_out − remaining outbound`;
- return leg: `D_go = D_back = remaining return`.

Needs and margins, with the reserve `R = f·B`:

```
need_finish   = r · D_go          margin_finish   = E − need_finish − R
need_walkback = r · D_back        margin_walkback = E − need_walkback − R
turn-back point (outbound) = margin_walkback / (2 r)    # x farther costs x out and x back
```

| Level | Condition | Viewer alert |
|---|---|---|
| OK | `margin_finish ≥ 0` | none |
| Caution | `margin_finish < 0` and `E ≥ need_finish` | amber *Route uses the reserve*, with the turn-back point |
| Turn back | `E < need_finish` and `margin_walkback ≥ 0` | red *Turn back · return to base*, base distance and bearing |
| Return now | `margin_walkback < 0` (or `E < R` without a route) | red *Return to base now* |

The most severe resource is shown; the alert pulses while critical and disappears when
the margin recovers (for example after a replan with a shorter route).

Worked example (test fixture): 1000 m out and 1000 m back costing 200 Wh, so 0.1 Wh/m;
reference 300 Wh, reserve 60 Wh. At 400 m out the route still needs 160 Wh and the
walk-back 40 Wh. With 230 Wh left: OK. With 200 Wh: caution, turn-back point 500 m ahead.
With 120 Wh: turn back (walk-back margin +20 Wh). With 90 Wh: return now.

## 4. Assumptions to review (David)

1. **Uniform cost per metre.** Route totals are spread evenly along the itinerary. The
   real cost depends on grade and activity: in the Jezero proposal the human outward leg is
   12.83 Wh and the return 14.54 Wh ([jezero_mission_proposal.md](jezero_mission_proposal.md)),
   about ±6% around the mean, so an uphill return can be under-estimated by that order. The
   20% reserve covers it in the example, but a per-segment cost from the planner would remove it.
2. **Walk-back retraces the travelled outbound path**, ground the agent has already crossed
   (verified traversal), not the planned return path, which may cross unobserved estimated
   ground (D-EST-01). A shorter straight line to the base is not assumed safe.
3. **Reference = first received sample**, as in the dial gauges; a recorded budget field in
   the replay would be better.
4. **Reserve share 20%** is JZ-P06 (alternatives 10/20/30% recorded there). It plays the role
   of NASA's per-EVA contingency reserve but is not a NASA value.
5. **Service and waiting time** inside `travel_time_s` are spread over distance like travel.

## 5. Limits

Display only: it never stops an agent, never replans and is not a safety certification.
It uses estimates, not measurements; UNKNOWN or non-FEASIBLE routes (NaN costs) give no
route check, only the reserve check. The planner and MissionManager keep the authority on
feasibility, reserves and return (ICD, JZ-P06).
