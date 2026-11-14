# Planner/science model conformance

This probe compares a published planner snapshot with the declared mission
science model. Its classification is **MODEL_CONFORMANCE**, using synthetic
known-public inputs. It is not an A/B/C mission benchmark, a simulated
execution, verified traversal, or a LIVE mission. Authorization remains
**BLOCKED**, including when a positive control agrees.

## Source and import isolation

Call `mge_mission.conformance.run_conformance(planner_package_path, profiles,
planner_revision)` with an explicitly materialized, trusted planner package.
No current working checkout or installed `mge_planning` package is inferred.

The snapshot root must contain `source_manifest.json` with schema version,
repository, full Git revision, package root and SHA-256 hashes. The requested
revision must match the manifest. Every Python file in the package must be
listed; all listed files are checked before execution and after the probe.
Escaping relative paths, package symlink/junction paths and mismatched hashes
are rejected. Hash verification identifies the supplied source; it does not
make arbitrary Python safe or authenticate a self-written manifest. The caller
must obtain the snapshot from the declared trusted repository/revision.

The core loads under a unique private import alias, registered before execution
so its dataclasses resolve correctly. The public `sys.path` and public planner
module are unchanged. Probe aliases are removed even after failure. The package
initializer is hashed but not executed; core compilation does not write
bytecode into the read-only snapshot. No planner code or module globals are
patched. The current pinned core imports only standard modules, NumPy and SciPy.

NumPy and SciPy are optional for the mission module. Missing or broken optional
imports return `NOT_RUN / DEPENDENCIES_UNAVAILABLE`, an empty case list and no
fabricated pass. Ordinary conformance unit tests do not require these libraries;
the explicitly materialized published-snapshot check skips when unavailable.

## Seven controlled cases

All cases use a 13 by 13 grid, one-metre cells, public admissible cells and zero
sigma. Start/goal are interior cell centres, with a two-metre horizontal
separation. Ground slopes change elevation by 0.05 m per column. Each request
requires return to its start. Large explicit test budgets avoid a budget-search
failure obscuring cost comparison; those budgets are probe fixtures, not
mission parameters.

| Case | Services after reaching the goal |
| --- | --- |
| Human flat | None |
| Human slope | None |
| Human service/wait | 20 s sample, 15 s waiting |
| Rover flat | None |
| Rover slope | None |
| Rover service/wait | 20 s inspection, 15 s waiting |
| Drone observation | 30 s observation |

The actual public `plan_route` function returns each candidate. The audit then
recomputes its actual outbound and return path segments using
`estimate_segment`, followed by the specified service and waiting activities
exactly once. It does not substitute an assumed straight route. Empty or
disconnected returned paths fail explicitly.

Compare total time, energy and human oxygen, plus remaining resources against
the same initial budgets. Relative tolerance is 1e-5 and absolute tolerance is
1e-3 in the reported units. Deltas use **planner minus science**; negative
energy means the planner underestimated that itinerary. Nonhuman oxygen remains
null, never a measured zero. Every report includes inputs, paths, source/model
hashes, profile values and approval states, projection metadata, dependency
versions and raw cost/reserve deltas.

The existing projection's high human oxygen rate is an approximation; its
energy model is not a proven conservative bound. Agreement in one case proves
neither configuration identity nor complete equivalence.

## Published-snapshot observation

The tested reference revision is
`34c515b6b86f73336844e8b3614c70b144574ec3`, with the proposed
`mge-science-1.0.0` profiles. All seven planner calls returned FEASIBLE.
One positive control agreed; six cases disagreed. These are numerical probe
observations, not mission outcomes:

| Case | Time delta, s | Energy delta, Wh | O2 delta, standard L |
| --- | ---: | ---: | ---: |
| Human flat | 0 | 0 | +0.0880912 |
| Human slope | +0.00659614 | -0.0270139 | +0.0802833 |
| Human service/wait | approximately 0 | +0.429542 | +0.731809 |
| Rover flat | 0 | 0 | null |
| Rover slope | 0 | +0.336596 | null |
| Rover service/wait | 0 | +0.500000 | null |
| Drone observation | 0 | +1.000000 | null |

Service/wait differences expose the planner's single service-power projection;
human oxygen differs from activity-dependent consumption. The slope case also
exposes a small time difference and an **underestimate** of human round-trip
energy. Preserve these findings when reconciling models rather than loosening
tolerances to hide them.

## Acceptance boundary

Reproduce the published-snapshot comparison without merging branches:

```sh
python -m pip install -r requirements-conformance.txt
python scripts/check_planner_conformance.py \
  --planner-ref 34c515b6b86f73336844e8b3614c70b144574ec3 \
  --run-id my-conformance-check --output-dir evidence/my-conformance-check
```

The CLI archives only the selected planner package from the local Git object
database into a temporary source snapshot, verifies hashes, runs the comparison
and retains its exact revision and raw profile-registry hash. It changes neither
branch. Existing report files are not overwritten. See the
[recorded comparison](../evidence/planner-conformance-20261114/conformance.json).

A successful probe means the comparison ran and produced evidence. It does not
change profile approval, freeze the ICD, authorize routes or close the planner
model-agreement dependency. Retain the emitted JSON with exact hashes before
using its table in a handoff. Further model changes require a fresh run and
source/configuration identities; retain earlier results.
