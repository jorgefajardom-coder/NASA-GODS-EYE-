# Public scenario readiness and candidate configuration

The mission branch consumes Daniel's public terrain API from main `6ec9b84`
(PR #8). It does not replace the data loader or mapping provider. Source
provenance remains in [data documentation](data_sources.md). The old web demo
and its future POIs, routes and budgets are not imported into this scenario.

```sh
python scripts/check_mission_scenario.py --run-id scenario-review \
  --output-dir tmp/scenario-review
```

Defaults are `data/sample/manifest.json`, the proposed science profile registry
and `config/mission.yaml`. The output directory must be new. The tool writes
`scenario_diagnostic.json` and `mission_candidate.json`; exit code 2 means
`NOT_READY`, including missing operational inputs. It never launches agents,
plans a route, supplies observations or authorizes a mission.

The diagnostic checks confinement to the public package, archive key isolation,
explicit masks/uncertainty, loader hashes, ENU geometry and south-to-north rows,
at least three verified control points and finite valid-cell uncertainty.
Only fixed public files are opened; no evaluator reference is loaded. The
producer's current legacy provenance manifest (`schema_version: 1`) is consumed
through its published loader, not relabelled as dataset.delivery 1.0.0.

`PUBLIC_PACKAGE_VALIDATED` refers to those checks only. The delivered sample
has a 32 by 32 grid at 4 m, derived from a native 20 m CTX prior. The finer grid
does not increase source resolution. Its initially unobserved cells remain
unknown for execution; no synthetic observations are supplied by this tool.

The candidate binds the actual manifest/public files, mission input, profile
registry and science-model source by SHA-256. It reports missing base/B,
dataset binding, service assumptions, capacities, reserves, tolerance and owner
approval references explicitly. Provided coordinates must be finite, inside
valid terrain and at cell centres under the pinned main contract; the tool
reports `NON_CELL_CENTER` rather than moving them. Human oxygen is required;
robot oxygen is absent. Reserves cannot exceed capacities.

All candidate values remain pending review. Even fully populated and consistent
inputs yield `CONFIGURATION_CONSISTENT_REVIEW_REQUIRED`, with
`mission_execution_authorized=false` and `scientific_approval=false`. No owner
approval is inferred from a producer manifest saying `ready` or from nonempty
approval-reference strings. Source/configuration hashes and run ID distinguish
this consistency diagnostic from any later mission execution.

The CLI also hashes its own code, diagnostic code and Daniel's loader. An
exported source snapshot without Git retains these hashes and reports unknown
revision/dirty state rather than inventing a checkout identity.
