# Source-traced activity and terrain models

Status: **proposed engineering models, pending David's scientific approval**.
The current implementation supports model `mge-science-1.0.0`. Profile approval,
planner model agreement, and evidence that a mission ran are separate decisions.
No profile is a certified vehicle, suit, human limit, or measurement on Mars.

## Profile registry and provenance

[Proposed profiles](../config/science_profiles.proposed.json) record a value,
unit, origin, direct source, locator, sensitivity range, owner and approval state
for every rate and coefficient. Sensitivity ranges are chosen experiment
scenarios, not confidence intervals from NASA. `load_profiles` preserves
approval status. A proposed profile can be inspected and evaluated; the mission
authority must reject operational use without explicit approval or an explicitly
selected illustrative run.

[The illustrative scenario](../config/scenario_demo.yaml) retains the synthetic
test inputs. A separate [Jezero proposal](jezero_mission_proposal.md) combines
Daniel's public observational terrain with proposed positions, services,
allocations, reserves and a model-pose tolerance for David's review. It grants
no approval and creates no observations or hidden sites. Operational
configuration remains incomplete.

`AgentProfile` copies and freezes capabilities, parameters and powers, so later
mutation of a caller's dictionaries cannot silently change an accepted profile.
The model takes only public ENU endpoints and explicit activity/duration inputs.
It neither reads terrain/reference files nor infers observations from a route.

## Human

The activity anchors are walking 417.70 W, stationary light work 358.08 W and
stationary heavy work 461.17 W. Their reference subject is 80.7 kg with a 120 kg
test suit. These values are rounded conversions from NASA's lunar analog
modeling table, not measurements or validated rates for Mars. Mapping light work
to inspection/waiting and heavy work to sampling is a modeling choice.
[Source: NASA/TM-2010-216138, Table 4, printed p.13 / PDF p.21](https://ntrs.nasa.gov/api/citations/20110001417/downloads/20110001417.pdf#page=21).

For horizontal distance `h`, directed height change `dz`, and `g = abs(dz)/h`:

```text
time = h * (1 + slope_slowdown * g) / speed
energy_Wh = (walking_power_W * time
             + (body_mass + suit_mass) * gravity * max(dz, 0) / climb_efficiency) / 3600
```

The proposed speed is 0.8333 m/s, slope slowdown 2, efficiency 0.25 and slope limit
10 degrees. These transferred/selected coefficients remain assumptions. Downhill
does not regenerate metabolic energy; it still takes time and consumes resources.
A vertical-only ground edge is invalid. A zero-length edge has zero duration and
cost. Stationary service and waiting use their explicit powers once.

Oxygen scales proportionally to metabolic energy using BVAD Rev2's 0.086 kg/h
and 295 W reference. That proportional extension across activities and grades is
an engineering assumption; metabolic consumption does not include complete suit
leakage, purge, cooling, CO2 removal, or pre/post-EVA consumables.
[Source: BVAD Rev2, Table 4-70, printed p.135 / PDF p.149](https://ntrs.nasa.gov/api/citations/20210024855/downloads/BVAD_2.15.22-final.pdf?attachment=true#page=149).

All `oxygen_l` values mean **equivalent ideal dry O2 litres at 273.15 K and
101.325 kPa**, including capacities and reserves. They never mean bottle/suit
geometrical volume. Molar mass 0.0319988 kg/mol and ideal molar volume
22.41396954 L/mol yield 60.23980213132992 L/h at the reference rate, or
0.204202719089254 L/Wh. No segment-level rounding occurs.
The human-only `oxygen_scale` multiplier defaults to 1 and exposes the proposed
0.75/1/1.25 sensitivity without changing metabolic energy; it does not model
hardware losses.
[NIST oxygen molar mass](https://webbook.nist.gov/cgi/cbook.cgi?Name=O2);
[NIST CODATA ideal molar volume](https://www.physics.nist.gov/cuu/pdf/wall_2022.pdf).

## Rover

The 1025 kg reference scale is Perseverance's. The chosen 0.04 m/s operating
speed is below its reported 152 m/h maximum; auxiliary, idle and inspection
powers, rolling resistance, slip and efficiency are proposed assumptions.
[Reference component specifications](https://science.nasa.gov/mission/mars-2020-perseverance/rover-components/).

For three-dimensional edge length `L` and directed inclination `theta`:

```text
time = L / (speed * (1 - slip))
force = mass * gravity * (rolling_resistance * cos(theta) + sin(theta))
energy_Wh = (auxiliary_power * time
             + max(force, 0) * L / (drive_efficiency * (1 - slip))) / 3600
```

This separates auxiliary and tractive power; the coefficients are not calibrated
Perseverance soil/drive properties. A downhill negative force receives no energy
credit, while auxiliary power still consumes energy. Slip must be below one.
[JPL power-model background, pp.3-4](https://dartslab.jpl.nasa.gov/References/pdf/2011-howard_ieeeaero_2011.pdf).

## Drone

The reference mass is 1.8 kg and translation/ascent uses a 350 W flight-power
anchor. Both are reference scales, not a reconstructed aerodynamic model.
[Ingenuity overview](https://science.nasa.gov/mission/mars-2020-perseverance/ingenuity-mars-helicopter/).
The 230 W hover/observation/descent model adds an assumed 20 W avionics load to
NASA's approximately 210 W rotor hover reference; descent/observation reuse is
another assumption.
[Flight-control and aerodynamic report](https://science.nasa.gov/blog/what-were-learning-about-ingenuitys-flight-control-and-aerodynamic-performance/).

`time = max(horizontal_distance / horizontal_speed, abs(dz) / vertical_speed)`.
A segment with horizontal displacement uses translation power; vertical-only
ascent/descent uses its named power. Positive climb adds `mass * gravity * dz /
climb_efficiency`; this extra term and its efficiency are proposed and are not
claimed to isolate real Ingenuity subsystem loads. Ground waiting uses 5 W;
airborne waiting must explicitly request `hover` or `observe`, at 230 W.

The 90-degree slope and finite 1,000,000 m step entries only express the current
ground-grid planner projection. They do not establish flight clearance or
obstacle avoidance. No aerodynamic, takeoff/landing, thermal, battery-state,
solar charging or atmosphere model is claimed.

All three kinds use Mars gravity 3.71 m/s².
[Source: JPL planetary physical parameters](https://ssd.jpl.nasa.gov/planets/phys_par.html).

## Planner handoff and limits

`export_planner_profiles` returns JSON-compatible `MotionProfile` fields for the
current planner. Its status is `pending_model_agreement`; scientific approval of
the source profile does not approve the projection. Only an all-illustrative
input produces an `illustrative` projection, requiring the planner's explicit
illustrative opt-in.

The projection has per-distance energy and constant human oxygen, whereas this
model integrates activities and direction-specific climbing. Its conservative
human oxygen rate is the maximum admitted grade/service rate, not physiology.
A candidate must be audited with the complete itinerary and service durations;
an approximate candidate is not verified execution evidence. Flight projection
is especially limited to the shared ground grid.

The estimator checks finite inputs and proposed grade bounds. Step,
localization/footprint clearance, unknown cells and sigma gates require the
public map and stay with the planner. A known geometric path is not proof of
safe traversal. Missing model inputs and unsupported activities fail explicitly.
Service time/cost belongs in an itinerary once; do not sum full round trips to
insert an optional task before the primary objective and return.

Before comparison, record the model/configuration hash, data version, seeds and
sensitivity choices; retain rejected and failed runs. No A/B/C result is supplied
by these models.
