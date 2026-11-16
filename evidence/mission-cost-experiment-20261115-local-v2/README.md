# Exact costs and a complete local analytical EVA

**Local review packet; no publication, production cost agreement or verified
ROS/physical mission.** Source: published main
`64985e7b4b69ac9683661db4842885d5a8293695`.

The [80-second video](bunsen-eva-simulated.mp4) visualizes the actual recorded
analytical timeline, with permanent `AI-generated | SIMULATED | NOT LIVE`
watermark. It is silent H.264,1280×720,15fps,1,200 frames; ffprobe checks passed.
Preview PNGs and video/source hashes accompany it. No agency branding is used.

## Result

The declared single-human EVA on the public Bunsen512 query window completed
68 simulated ground steps,283.0374 m and1,226.8855 s (20.45 min). It includes
600 s coordination wait, a programmed120 s terrain inspection, a12 m typed
synthetic observation, route invalidation and replanning from the reached pose,
120 s primary service at B, and independently directed return to A. The
simulated obstacle is deliberately conditioned on the initial corridor; it is
not a NASA observation or a test of autonomous early hazard detection.

| Resource | Initial | Consumed | Remaining | Separate reserve |
|---|---:|---:|---:|---:|
| Active EVA time, s |2100|1226.8855|873.1145|420|
| Estimated metabolic energy, Wh |225|136.7195|88.2805|45|
| Equivalent dry O2, L |45|27.9185|17.0815|9|

The600 s sampling alternative was not assigned: rover-inspection evidence was
absent and its cost plus return also failed time/energy/O2 margins. Sampling
was not completed or inferred from presence at B. No rover/drone role, flight,
physical localization accuracy or actual scientific discovery was demonstrated.
The selected query anchor is not a registered geological workspace; canonical
regional packaging and independent controls are still Daniel's dependency.

`analytical-audit.json` independently checks all73 disjoint cost intervals,
68 public-map step admissions, B stationary duration, return, conservation and
reserves, typed observation causality and duplicate handling, journal recovery
under the same run ID and video/source correspondence. Physical/ROS mission
success remains null. The model's ideal/noiseless sensor assumption, sigma3
admission, CTX20 m versus computational4 m, grade-derived height bound and
planning wall-latency-as-wait assumption are explicit; they are not approvals.

## Cost reconciliation

The new mission-owned composition consumes the actual published ScientificCosts
adapter through the planner's existing geometry-cache hook. Original search,
geometry, footprint, masks, NoData, directed grades and clearance are reused.
Exact fixed-goal service costs and an admissible scientific time heuristic are
bound to one explicit schedule. This is not copied planner code or a mutation
of another owner's implementation, and no ROS field was changed.

All36 kernel/activity contexts and two returned EVA itineraries agree with the
independent canonical scientific API within the unchanged tolerances. Each
context records source/profile/scenario/model hashes, remaining work/resources
and separate reserves. Duplicate content is a no-op; conflicts/stale identities
are rejected. Resource acceptance gets no numerical tolerance credit. These
checks establish local numerical/software agreement, not empirical validation
of physiological or vehicle coefficients.

**Remaining production agreement:** Diego must review/adopt this composition
in the actual planner consumer and Jesus must implement/review immutable
activity/context and execution evidence transport. Inspect and sample of equal
duration remain indistinguishable on the existing PlanRoute service alone.
Profile approvals, producer/consumer deployment review and operational model
agreement flags remain false. No new MOCK was created.

## Large-map search and retained attempts

The owner authorized extending local research bounds. Fixed Bunsen1024 draw0
was tested for human and rover under2 s/200,000 labels and20 s/1,000,000 labels
with the same exact-cost composition and allocations. **All four returned
UNKNOWN/SEARCH_LIMIT.** Larger limits did not resolve these cases; this is not
a proof of impassability or insufficient budget. Do not change limits to make
a result pass. Hardware wall latencies are diagnostic, not a controlled
performance benchmark.

V1 remains in the neighbouring directory, including its original executed
runner and video. Its successful bounded trace still had return margin after
initial planning wait, but lacked a prior full-itinerary recheck and explicit
public-map step predicates, and omitted some child-process source bindings.
V2 adds those safeguards and uses its own frozen runner for the private process.
No records were silently rewritten. The planned inspection interval fits this
bounded case; a production controller must additionally prove its policy for
arbitrary low-margin interruptions before spending inspection/planning delays.

## Verification and next owner decisions

See [proposed verification levels](../../docs/mission_simulated_verification.md).
Level S means independent consistency under declared analytical assumptions,
subject to David's review, always retaining SIMULATED. Level R requires the
existing four conjunctive mission predicates: public B-work result and stationary
coverage, observed post-B return, complete justified executed traversal and
resource-ledger closure. It also needs registered terrain, profile and
cost/context reviews, conforming executor/stop/work/traversal producers and the
same-run recorder/replay/video. Neither level is physical or LIVE validation.

This harness does not invoke MissionManager, publish ROS execution telemetry or
manufacture a ROS termination state. Existing EvidenceRecorder stores the typed
analytical inputs in execution.jsonl and verifies recovery. Its canonical
benchmark export is intentionally not forced with invented ROS state or success
predicates. The simulation's abstract service result is not a public work-result
producer for the integrated mission.

Fresh Ubuntu24.04/Jazzy build compiled eight baseline packages plus the two
new mission modules in an isolated candidate tree;26 selected adapter/context
tests passed and service fields were inspected. Native source/version receipt
is in native-environment.json. Full working-tree Python, repository, frontend
and build commands/results are in software-validation.json and adjacent logs;
these are software checks, not mission acceptance.

Effective working-tree results: **1,108 Python passed /21 environment skips /
one existing Starlette warning; frontend201 passed /one skipped; repository,
whitespace and build passed.** The first Python invocation hit PermissionError
on the host's global pytest temp (180 fixture errors, retained in python-tests.log).
The retry used a checked, new workspace temp and passed in25.26 s; see
python-tests-workspace-temp.log and its JUnit. No product checks were disabled.
Ubuntu's26 new tests passed in1.72 s; the8-package build completed in23.4 s.

Reproduction uses scripts/run_mission_cost_experiment.py and
scripts/render_mission_experiment_video.py. Outputs are exclusive and a rerun
needs a fresh root/run identity; don't overwrite this packet. The protocol,
source/code locks, context records, source-attribution.json, private-world hash,
raw journal, analytical audit, video receipt and final manifest preserve lineage.
The earlier sealed environment/overnight studies remain unchanged, with shared
documents preserved before these registers evolve.

All work remains local pending the owner's final green light. This is not a
submission-readiness announcement. JES-07/AC-10 organizer notification and
explicit endorsement remain pending; Jesus coordinates, David is backup and
the agreed review margin must be preserved.
