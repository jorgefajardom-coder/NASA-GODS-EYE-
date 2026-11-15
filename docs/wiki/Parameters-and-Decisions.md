# Parameters, scenarios and decisions

[Home](Home.md) · [Resource models](05-Resource-Models.md) · [Experimental method](07-Experimental-Method.md)

A parameter value becomes useful when its meaning is clear. A mass can describe a reference vehicle; a power can be transferred from an analogue study; a reserve can express a policy chosen for an experiment. Recording these roles makes it possible to ask which conclusions depend on each choice.

This catalogue is a reading guide to the existing registries. The linked configurations retain the exact numerical values, source locators, sensitivity ranges and approval states. The Wiki describes them without changing their status.

## Nominal resource-model anchors

| Quantity | Nominal value | Basis and role |
|---|---:|---|
| Mars gravity | 3.71 m/s² | Physical reference from the JPL planetary table, rounded to the model's declared value. |
| Human body / analogue suit mass | 80.7 / 120 kg | Reference subject and suit scale in the lunar-analogue model. |
| Human walking / light / heavy power | 417.70 / 358.08 / 461.17 W | Rounded conversions of Chappell et al.'s Table 4; transfer and activity associations belong to this model. |
| Human horizontal speed | 0.8333 m/s | Selected reference value used by the estimator. |
| Human grade slowdown / climb efficiency | 2 / 0.25 | Engineering assumptions in the time and positive-climb terms. |
| Reference oxygen / metabolic power | 0.086 kg/h / 295 W | BVAD Rev2 Table 4-70. Proportional extension to each activity is a project formulation. |
| Oxygen equivalent-volume conditions | 273.15 K / 101.325 kPa | Proposed dry ideal-gas convention. |
| Nominal oxygen conversion | 0.2042027191 L/Wh | Derived from the stated mass, molar mass and volume convention. |
| Rover reference mass | 1,025 kg | Perseverance reference scale. |
| Rover command speed | 0.04 m/s | Selected operating value. |
| Rolling resistance / slip / drive efficiency | 0.05 / 0.10 / 0.35 | Assumed coefficients, with sensitivity recorded in the registry. |
| Rover auxiliary / waiting / inspection power | 100 / 80 / 200 W | Assumed electrical loads for distinct phases. |
| Drone reference mass | 1.8 kg | Ingenuity reference scale. |
| Drone translation / observation / ground-wait power | 350 / 230 / 5 W | Reference-informed engineering values; the 230 W combines a reported approximately 210 W rotor value and 20 W assumed auxiliaries. |
| Drone horizontal / vertical speed | 2 / 1 m/s | Selected kinematic limits. |
| Drone climb efficiency | 0.5 | Assumption in the additional positive-climb term. |

The [complete proposed registry](../../config/science_profiles.proposed.json) contains additional map-related bounds, footprints and coefficient-specific sensitivity records. [Chapter 5](05-Resource-Models.md) explains how the quantities enter the equations. A sensitivity range expresses an experimental choice unless its record identifies a measured statistical basis.

## The approved compact scenario

The owner approved JZ-P01 through JZ-P07 for an experimental scenario on 14 November 2026. The [approval receipt](../science_approvals/jezero_scenario_20261114.json) binds the proposal hash and the approved values. The following selection provides an accessible summary.

| Element | Approved experimental value |
|---|---|
| Public terrain | `jezero_mvp`, 128 m window, 32 × 32 cells at 4 m computational sampling. |
| Base A, local ENU m | (−14, −14, −2571.199462890625). |
| Primary B, local ENU m | (30, 30, −2573.264892578125). |
| Primary stationary activity | 120 s visual observation/check-in, modeled as light work. |
| Return criterion | Within 1 m in the declared 3D model after B completion. |
| Human allocation | 1,200 s; 100 metabolic Wh; 25 equivalent O₂ L. |
| Human separate reserve | 240 s; 20 Wh; 5 L. |
| Rover allocation / reserve | 1,200 s and 60 electrical Wh / 240 s and 12 Wh. |
| Drone allocation / reserve | 180 s and 15 electrical Wh / 36 s and 3 Wh. |

The receipt's scope is scenario values. It records profile, cost-agreement and execution-evidence approval separately. The 1 m tolerance is a model-space rule rather than an estimate of terrain or physical positioning accuracy. The 20% reserve is an experimental policy rather than a NASA-prescribed fraction.

## Later proposals and local cases

The [campaign proposal](../agent_campaign_proposal.md) separates robotic reconnaissance, human EVA and individual drone flights. Its larger regional allocations remain proposals. The Bunsen row, for example, allocates 35 min, 225 metabolic Wh and 45 L to the human program; the rover program has a separate 6 h 30 min and 800 electrical Wh allocation. These are workload-based experiment inputs.

The local analytical run `local-cost-eva-bunsen-20261115-02` uses that human allocation, A = (−226, −218) m and B = (−238, −82) m. Its initial domain is 512 m; a later paired check establishes a sufficient 256 m active crop for two particular requests. [Chapter 8](08-Case-Studies.md) follows its time and resource record. This case has its own identity and does not replace the compact approved scenario.

The documented-sample pilot introduces another distinction. Hurtado et al. report approximately 600 s for a complete documented sample in D-RATS experience. The project's 420 s light-work plus 180 s heavy-work split is an assumed decomposition of that total. The compact scenario's 120 s check-in and its earlier 180 s acquisition example remain identifiable choices. The [duration review](../activity_duration_research.md) preserves that history.

## Map and uncertainty choices

CTX product sampling is 20 m; the delivered computational grid is 4 m. Resampling supports numerical operations while retaining the source's spatial-information limits. NoData, obstacles and uncertainty are retained explicitly.

The strict profile uncertainty threshold is 1 m. Research copies also test `max_sigma_m=3`, alongside the strict control. Prior sigma values are declared scenario inputs, not measured posterior error distributions. A proposed 0.25 m observation sigma in the local analytical sensor case belongs to its simulated observation model.

Likewise, an absolute step bound between adjacent cell centres can restrict traversable grade when the cell spacing changes. Local terrain-profile variants investigate that interpretation separately. The [research decision record](../science_decisions.md) and [hypotheses](../research_hypotheses.md) retain the exact scope of those variants. The Wiki does not modify a planner parameter to improve a displayed outcome.

## Decisions that guide interpretation

| Decision or record | Meaning |
|---|---|
| JZ-P01–JZ-P07 approval | Accepts the identified compact experimental scenario values. |
| D-EST-01 | Accepts proposing routes over valid orbital estimates, with observation-driven revision and retained constraints. |
| D-COST-02 | Accepts reuse of the scientific cost API as the reconciliation direction; coefficient approval and production context transport retain their own review. |
| Four-predicate success specification | Defines the required conjunction of primary work, return, traversal coverage and resource accounting. |
| Local analytical verification proposal | Defines a reviewable model-consistency level and the additional records needed for integrated or physical claims. |

The relevant records are the [scientific decisions](../science_decisions.md), [estimated-terrain decision](../decisions/2026-11-14-estimated-terrain-planning.md), [shared-cost decision](../decisions/2026-11-14-shared-scientific-cost-api.md), [success contract](../mission_success_contract.md) and [verification proposal](../mission_simulated_verification.md).

For every proposed change, the useful audit question is the same: which source, assumption or observation motivates it, and which result would change if it were accepted? This question keeps the catalogue connected to the mission reasoning developed throughout the Wiki.

[Bibliography](Bibliography.md) · [Reproduction guide](Reproducibility.md)
