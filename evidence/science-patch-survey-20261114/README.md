# Local scientific patch survey

Research cut: 14 November 2026, America/Bogota. Source baseline:
`c3ec4c1f1515dbc981ba82eed2ab1f54e9586264`, `feat/mission`. The owner requested
local work only during a separate reconciliation audit. No commit, push, merge,
new terrain package, operational configuration or executed mission is produced.

| Artifact | Scope |
|---|---|
| [Scientific report](../../docs/science_patch_survey.md) | Source-based selection of 17 sectors and conditional map-size recommendation |
| [Requests to Daniel](../../docs/science_patch_map_requests.md) | Three prioritized Jezero map requests; Mawrth conditional alternative; data acceptance requirements |
| [Jezero catalogue](jezero_candidates.proposed.json) | Six proposed sectors, 13 primary references, evidence limits and secondary opportunities |
| [Alternative catalogue](alternative_candidates.proposed.json) | Eleven sectors, 18 primary references, known products and unresolved import/registration |
| [Map requests](map_requests.proposed.json) | Approximate geographic query centres/envelopes; no operational A/B or verified crop footprint |
| [Selected historical anchors](waypoint_anchors.selected.json) | Five unchanged NASA public waypoint features, original indices and source hashes; unverified target associations |
| [Scale/resource assessment](scale_assessment.json) | Public-loader audit and ideal flat resource ceilings using the unchanged model and approved allocations |
| [Reproducer](reproduce_scale_assessment.py) | ROS-free calculation, pinned source/input checks, exclusive output creation |

The catalogues are literature research, not runtime POIs, new discoveries or a
hidden evaluator catalogue. The waypoint subset copies published NASA values;
selection/query boxes and analytical results are generated proposals. The full
remote waypoint response is identified by hash; the selected features preserve
the actual values used. No imagery/raster or private evaluator array is imported.

## Reproduce the scale calculation

From the repository root at the recorded source revision and unchanged inputs:

```sh
python evidence/science-patch-survey-20261114/reproduce_scale_assessment.py \
  --output tmp/new-science-patch-scale-assessment.json
```

Use a fresh output path. Existing output is refused. The source pin prevents a
changed implementation being silently called the same experiment. The report
records code and input hashes, versions, command, run ID and approval state.
The current sample's 20 m native DTM, 6 m image product and 4 m computational
grid remain distinct. No larger map is created by this calculation.

Ideal straight out-and-back one-way ceilings are about 222.98 m human,
14.04 m rover and 103.57 m drone after the declared stationary phases/reserves.
These are not reachable discs, candidate acceptance, sensor footprints or
certified mobility. The human phase is the approved visual check-in costed as
light work; it does not complete an optional inspection. Takeoff/landing and
terrain/coordination additions are excluded as detailed in the assessment.

## Validation and pending work

Local checks: Python 979 passed / 19 environment skips; frontend 161 passed /
one optional external-package skip; production build and repository checker
passed. The reproducer executed successfully. Detailed commands, actual logs,
hashes and preservation assertions are retained in `validation/`.

ROS/colcon and live services were not started for this documentation/analysis
cut. Runtime, canonical configuration, public arrays, interfaces and other
owners' source paths remain unchanged. Existing software fixtures in the test
suite are not new mission results. No scientific or operational approval is
inferred from the checks.

The owner confirms Daniel has generation tools but not these new crops.
Await actual footprint/registration/coverage and the reviewed public/evaluator
partition; then choose operational A/B, observation capability and resource
agreement. The original scenario approval and remaining six readiness gates
are retained. Larger contextual maps do not increase consumables or prove a
better A/B/C outcome.
