# F03.3-B experimental scientific cost adapter

Reference main: 6bcf208868e37b7e15e9189fac11de96e7414eff; local parent
1f90854407817ef464f9acc74b5501d21f687c1c is preserved. No merge was performed.
Intervening main changes concern the viewer and documentation. Scientific model,
registry, experimental agreement and final David vectors match published main.
Source hashes and nine directed comparisons are in evidence/planner-f033b-20261114.

## Implemented boundary

resource_costs.py is an opt-in pure Python module, not imported by production
search/node/policy. ScientificCosts delegates movement and activity to
mge_mission.models.estimate_segment/estimate_activity using immutable AgentProfile
from load_profiles. No formula, coefficient or model is copied. All costs are
predictions: seconds, human metabolic Wh and equivalent ideal dry O2 litres,
or robot electrical Wh with oxygen None. Drone estimates do not validate flight.

Segment represents an explicit directed ENU edge. Activity requires an identity,
kind and remaining duration; the model rejects unsupported kinds/durations.
total accepts only explicit pending operations, rejects duplicate activity IDs
within that evaluation, and infers neither service nor return. An already spent
prefix must not be supplied. It is not a persistent consumption/deduplication
ledger and cannot establish that a caller's claimed duration is authoritative.
The caller supplies coherent geometry, schedule, current capacity and reserves.

check_budget uses (available - reserve) - candidate cost independently per resource
and requires every margin >= 0. Comparison tolerances rel1e-5/abs1e-3 grant no
capacity. It checks applicability of human oxygen; rejected margins yield explicit
resource reasons and no feasible-margin object. Existing runtime reserve and
mission guards remain authoritative and unchanged.

## Numeric evidence

Tests consume David's stored final vectors directly, not regenerated expectations.
They cover flat/up/down, zero, ground vertical rejection/drone vertical estimates,
directed itinerary, inspect/sample/observe/waits, partial service and all published
budget boundaries. Additional tests reject duplicate activities, missing activity
kind, wrong oxygen applicability and a nextafter-sized reserve shortage. Empty
pending work costs zero. Profiles remain proposed and agreement unapproved.

For a human 2 m segment rising 0.1 m, current projected search estimates
2.643403676 s / 0.389544606 Wh / 0.111141324 L; the adapter estimates
2.640105604 s / 0.389058586 Wh / 0.079446821 L. On the reverse edge the energies
are 0.278825686 versus 0.306325586 Wh. Thus the projection is not a universal
conservative bound. Full comparison.json includes all three agents and grades.
These are synthetic model comparisons, not measured physiology or vehicle data.

## Proposed next integration (NOT IMPLEMENTED)

1. Keep geometry admission independent: obstacles, unknowns, uncertainty,
   directed grade/step limits, footprint and swept clearance remain mandatory.
   After admission, evaluate each graph edge's exact XYZ using movement.
2. Use the identical backend/profile for the continuous connector once; initialize
   the first label with its cost. Preserve validated ground z and default-off ROS
   continuous starts. Never equate drone estimates with 3D route safety.
3. Bind an immutable explicit activity schedule to run/request/agent/map and
   model/profile/scenario hashes. Charge pending goal activities once at the phase
   transition; do not guess inspect from service_time_s. Unexpected holds belong
   to authoritative execution accounting and subsequent remaining snapshots.
4. Search actual directed return edges jointly; do not double outbound costs.
   In SERVICE retain unfinished work only; contingency RETURN abandons goal work.
5. ReplanPolicy pending-path estimates must use the same backend and remaining
   schedule. Preserve the admission guard from 1f90854 and external route authority.
6. Re-prove the planar-distance/max-speed plus fixed-pending-duration lower bound.
   Human horizontal speed and rover speed*(1-slip) provide upper speed bounds;
   do not transfer legacy grade factors. Prove nonnegative additive labels and
   dominance for fixed schedules using independent Dijkstra/exhaustive oracles.
   SAFE retains clearance ordering but its feasible optimum may change. Share
   backend/context across every SAFE trial; bound labels/work and benchmark before
   claiming unchanged performance. Cache keys include backend/profile/context.

## Dependencies and owner decisions

Both package manifests currently have no dependency on the other package.
models imports only the standard library; YAML profile loading uses existing
PyYAML. Current monorepo pytest exposes both packages without ROS. Only importing
the experimental module requires mge_mission. No dependency was installed or
manifest changed; isolated installed planning cannot yet promise this module works.
Jesus must review a declared planning->mission runtime dependency (or a shared
pure-package extraction) and colcon/import graph before enabling it. Mission does
not currently declare a planning dependency; runtime coupling must still be checked.

David reviews equivalence, profile provenance, activity semantics and precision;
Jesus reviews immutable schedule binding and actual service/consumer transport.
PlanRoute lacks activity/wait context: runtime integration stays blocked until
that binding is agreed. No wire fields, MissionManager or model approval flags
change. MODEL_NOT_AGREED/MODEL_MISMATCH, independent consumer audit and scientific
approval gates remain. This adapter provides no route authorization.

Run: python -m pytest tests/planning/test_resource_costs.py; python -m pytest;
python scripts/check_repository.py; git diff --check. JUnit evidence records
executed selections. No new native ROS, Gazebo or LIVE integration is implied;
WSL resource failure from the previous cut remains an unresolved validation limit.
Submission readiness and organizer endorsement are separate pending team gates.

Final local validation: 48 equivalence/boundary cases passed; complete Python
suite 1073 passed, 20 skipped, one existing warning. The selections overlap.
Repository and whitespace checks passed; native ROS was not executed.
