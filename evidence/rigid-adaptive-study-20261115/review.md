# Independent review of the paired analytical study

The study compares two explicitly defined policies over the same public terrain, synthetic world, initial candidate, reached prefix, remaining allocation and paid observation. The fixed policy retains its initial geometry and objective set. The adaptive policy asks the published planner to reconsider the remaining primary itinerary and may accept additional inspection at B. The observations cost 120 s for both policies. Movement, stationary work and waiting occupy separate ledger intervals, and reserves remain separate from the directed return.

The primary broad catalogue closed with 360 blocks and 1,440 human/rover and FAST/SAFE conditions. Of these, 888 conditions reached the shared decision point and generated 1,776 executed strategy episodes. The other 552 conditions retain explicit unavailable outcomes. The independent record audit checked all 96,137 movement intervals and 5,975 activity intervals against the scientific API, reproduced the resource ledgers, checked XYZ continuity and return coordinates, and verified 14 imported source hashes and the journal identities. All checked invariants passed. Four targeted tests passed, covering reserve boundaries, directed movement with actual reached elevations, resource stops and retreat after an interrupted optional leg. The complete main journal SHA-256 is `307f1466b19948b7455bb76595f9fadf3ea0ad194a68b9e3582895cd8ae2429a`.

These checks establish consistency of the recorded analytical experiment. Scientific profile approval, production model agreement, execution telemetry, physical stopping and verified mission completion remain separate acceptance gates.

## Four explanatory themes

The case selection is purposive. It illustrates mechanisms and provides exact payload hashes in `case-audit.json`; its proportions are not frequency estimates.

1. Keeping a useful route. In `bunsen-256-unchanged-1-broad`, `rover_1:FAST`, both policies completed the primary work and returned with exactly the same recorded time, 7,167.475 s, and energy, 247.577 Wh. The adaptive result retained the geometry. Additional inspection was unavailable in this case. The paid observation therefore supported keeping the existing decision.

2. Responding to an observed obstruction. In `bright-256-detour-0-directed`, `human_1:FAST`, the shared footprint exposed one synthetic obstacle cell. The adaptive policy changed geometry, completed the primary work and an additional inspection, and returned. The fixed itinerary encountered the analytical safety guard and retreated without completing B. The adaptive ledger total was 1,914.052 s, 195.503 Wh and 39.922 equivalent litres of oxygen; the fixed retreat used 1,064.889 s, 107.381 Wh and 21.927 litres. The different totals reflect different completed work. The obstruction was deliberately conditioned on the initial corridor, so this example demonstrates a recovery mechanism rather than the prevalence of such obstacles on Mars.

3. Accepting and declining additional work. In `hawksbill-256-blocked-0-broad`, `rover_1:FAST`, both policies completed B and returned. The adaptive policy accepted 300 s of additional inspection at B, adding 16.667 Wh while preserving the return and reserves. The fixed policy declined it because its objective set was fixed. In `bunsen-256-relief-0-broad`, `rover_1:FAST`, the adaptive policy instead declined additional inspection with `INVALID_START_Z`; both policies still completed the primary work and returned. The actual elevation reached at B differed from its unobserved prior elevation. Preserving that actual XYZ exposed the planner's strict centred-start height contract. A new observation at B would be a separate, charged observation opportunity for a future experiment.

4. A computationally adverse adaptation. In `bright-512-blocked-0-broad`, `human_1:SAFE`, the initial candidate was feasible and the fixed policy subsequently completed B and returned. The adaptive posterior primary query reached the 8 s search limit, reported `UNKNOWN`, and selected a separately planned return. It returned with reserves intact but did not earn primary completion credit. All 20 rigid-only primary-completion conditions in the main catalogue had this SAFE search-limit mechanism. This is a result of the tested bounded-computation policy, rather than proof that the terrain lacked a feasible route. The separate quiet serial diagnostic, if executed, must retain the original outcomes and report its query results separately.

## Interpretation and limits

The executed policy has one shared checkpoint, one paid local terrain footprint, and a posterior primary planning decision. It does not repeatedly observe and replan after every later guard stop. The private world process releases observation footprints and guarded reached points; the guard represents ideal analytical stopping rather than a validated sensor or braking system. Height measurements are noiseless synthetic values with a declared sigma of 0.25 m. That sigma is an experimental uncertainty setting, not measured sensor accuracy.

The optional opportunity is an exogenous simulated public mission notice for additional inspection at the already selected B. It is not a newly detected spatial POI, a sampling workflow, or evidence that another agent completed an inspection. Its availability and duration are declared by the experiment. The result therefore measures willingness and modeled capacity to add work at B, rather than discovery of additional geological targets.

The notice's complete experimental identity is `(study identity, block_id, condition_id, event_id)`. Its short event ID is reused across the four nested agent/mode conditions, whose capabilities and durations can differ. Each matched policy pair receives the identical notice payload. These conditions are separate analytical missions; their notices are not submitted together to a single MissionManager or ROS run.

The fixed policy's safety retreat reverses actually traversed geometry without a new search. When its primary query is unavailable, the adaptive policy requests a fresh planner return; that return can itself reach a search limit. This fallback asymmetry is part of the tested policy definitions and should accompany any interpretation of return rates. A future comparison can give both policies the same retained-prefix fallback under a separately frozen protocol.

All 76 `INVALID_START_Z` query results in the complete main catalogue occurred in the relief family during optional queries after primary completion. Every affected episode returned successfully. The paid checkpoint observation agrees with the reached checkpoint height; the later B height was not refreshed in this one-observation design. These errors are distinct from primary `UNKNOWN`, resource rejection and a demonstrated absence of a path.

In the broad implementation, initial planning queries finish before the private world is materialized. The world seed is predeclared independently and its target remains null; initial results do not determine the broad perturbation. Directed cases deliberately derive a target from an initial feasible route. The valid broad-sampling claim is independence of its randomness and absence of route conditioning, rather than materialization of the complete world before the first planner call.

The principal maps are fixed public CTX priors at 20 m native resolution, resampled to a 4 m computation grid. The named query anchors do not independently verify that each precise geological outcrop is inside the crop. The experimental 3 m uncertainty allowance and grade-consistent endpoint-height projection are explicit research variants. The controls using the published stricter bounds remain separate. Budget factors, reserve fractions and rover service duration cycle together by index, so their individual causal contributions cannot be separated by this design. Human/rover conditions and FAST/SAFE modes within one seeded block are dependent repeated conditions, not additional independent worlds.

Searches ran in parallel under a wall-clock limit. Parallel elapsed times describe this workload and host; they are not comparable serial latency benchmarks or hardware-independent algorithmic feasibility guarantees. The complete attempted-seed inventory, unavailable cases and adverse results belong in the denominator. Broad and corridor-conditioned results have different interpretations and must remain separate.

The local exact-cost wrapper, research runner, world process and terrain-constraint projection are unpublished experimental extensions around the published planner. The frozen producer baseline is main `3c82d72f972109113216039bff5cfd491df5f1ba`. The lazy allocation helper and campaign JSON received a clearly labelled post-start dependency closure; that supplement does not claim a pre-run hash record for those two inputs. Reproduction should use the recorded source and data snapshots and preserve this provenance limitation.

The journal checks configuration identity, sequence and payload hashes. Its resume operation does not itself enforce the imported-module byte locks. Main and directed batches completed without resuming; their explicit independent closing audits verify the source hashes. Source and input closure checks remain necessary before any later resumed run.

AI-assisted code and analytical records are subject to the project's mandatory usage declaration. This independent review does not assign authorship to the assistance tool.

## Reproduction records

- `source-review-main-final.json`: complete primary-catalogue independent audit.
- `source-review-directed-final.json`: complete directed-catalogue independent audit.
- `source-review-strict-sigma-final.json` and `source-review-published-step-final.json`: separate strict controls.
- `source-review-tests.txt`: four targeted tests and their actual result.
- `audit_records.py`: read-only journal, model-cost, resource and coordinate checks.
- `case-audit.json`: exact selected block IDs, condition IDs, sequences, payload hashes, world metadata, checkpoint resources and outcomes.
- `input-closure.json` and `external-dependencies.json`: imported source/data snapshots and post-start closure limitation.
- `replay_adverse.py`: prepared separate serial search diagnostic; it does not replace primary results.
