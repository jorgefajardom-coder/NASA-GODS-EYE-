# Fixed and adaptive analytical mission study

Classification: SIMULATED analytical research, with development pilots and controls kept separate.

The one-hour research request began at 2026-11-15 21:35 UTC. The experiment consumes published planning, mapping and scientific-model code at `3c82d72f972109113216039bff5cfd491df5f1ba`, with an explicitly archived local scientific-cost consumer and analytical execution harness. No production source, shared API or operational configuration is activated by this publication.

## Catalogue and units

| Batch | Recorded scenario blocks | Planned | Pending |
|---|---:|---:|---:|
| main | 360 | 360 | 0 |
| directed | 120 | 120 | 0 |
| extended-1024 | 180 | 180 | 0 |
| strict-sigma | 3 | 3 | 0 |
| published-step | 3 | 3 | 0 |
| development-pilot-1 | 2 | 2 | 0 |
| development-pilot-2 | 2 | 2 | 0 |

The primary comparison is the main 360-block grid. Each block nests human/rover × FAST/SAFE conditions and their paired fixed/adaptive policies. These repeated conditions are not independent geological samples. Initially unavailable routes and UNKNOWN remain in the main denominator; records without an executed itinerary are not completed physical missions. Directed cases, the 1,024 m supplementary grid, controls and development pilots have separate denominators. The first development pilot recorded Windows process/import failures; its catalogue is retained and excluded from all scientific estimands. Pilot code was corrected before freezing the main harness.

The two strict controls respectively retain 1 m uncertainty admission, and the published 0.20 m centre-height step with a 3 m uncertainty cap. Research batches use an explicitly declared grade-consistent step projection and 3 m uncertainty cap, with no new scientific approval. Main/directed queries use 8 s / 1,000,000 labels; the 1,024 m supplementary batch uses 20 s / 1,000,000 labels. Public CTX native resolution remains 20 m, independently of the 4 m computational resampling.

## Files and integrity

Every batch includes its unchanged configuration and pre-run manifest, durable JSONL catalogue compressed with deterministic gzip, and final supervisor summary. `publication-manifest.json` records both uncompressed and compressed SHA-256 values. Decompression restores the exact original journal bytes, including identities, sequence numbers, payload hashes, typed simulated observations and disjoint cost ledgers. The analysis exports readable JSON, CSV, case records and marked numerical figures.

`statistical-plan.json` is the frozen local protocol. `statistical-clarifications.json` identifies later vocabulary and reporting clarifications without changing the primary estimand. `input-closure.json` records the post-start capture of the allocation helper and campaign JSON explicitly; no modification of those inputs was observed. The original main/directed outcomes are preserved even if a later quiet serial query resolves differently. Such diagnostic queries do not rerun execution or replace completion outcomes.

`runtime/` is a reproducibility archive of exact source bytes and inputs, outside production paths. Its published-module copies retain their original authorship and licences from the pinned repository; the local extension is identified in module locks and AI declarations. Public crop files contain elevation and validity arrays only, with provenance/geometry/hash records. Evaluator reference data, browser profiles and personal documents are excluded.

## Reproduce

Use a separate checkout at the declared published SHA and a Python environment with the recorded NumPy/SciPy versions. `tooling/prepare_reproduction.py ARCHIVE --source EXACT_CHECKOUT --batch main --output NEW_DIRECTORY` generates portable paths. Set a future UTC deadline in the resulting configuration, then run `python ARCHIVE/runtime/scripts/run_rigid_adaptive_study.py run --config NEW_DIRECTORY/config.json`. Use a fresh output directory; never overwrite the retained journal. The same seeds reproduce mission/world construction; wall-time-limited search outcomes can vary with hardware and concurrent load.

To reproduce the statistical analysis, decompress `main/paired-blocks.jsonl.gz` into a new local file, then run `python tooling/analyze_rigid_adaptive.py JOURNAL --protocol statistical-plan.json --inventory main/manifest.json --output NEW_ANALYSIS --scope primary --no-plots`. `tooling/check_analysis_controls.py` checks the arithmetic and rejection behavior. Original scientific ledger checks and their exact commands/results are retained in `source-review-*-final.json`, `source-review-tests.txt` and `validation.json`.

The 1,024 m partial-coverage analysis, if applicable, retains every pending seed and a separately labelled balanced-prefix sensitivity view. A deadline-completed subset can overrepresent easy or quickly rejected cases. Map-size comparisons also change physical A/B separation while keeping sector allocations, so they are not isolated serial latency benchmarks.

## Interpretation and acceptance

The comparison concerns one paid shared checkpoint and one posterior decision. Hypothetical obstacles/relief and noiseless simulated observations are declared experimental inputs; the 0.25 m observation sigma is an assumption. An analytical world guard stops before inadmissible motion and does not represent a calibrated onboard detector. New work means an exogenous additional inspection at B, with no claim of new spatial POI discovery, sampling precedence completion or integrated three-agent execution.

The Wiki article, complete raw catalogues and independent ledgers support model-level conclusions. Profile approval, production scientific-cost agreement, calibrated sensing, task/work/traversal evidence and verified operational mission acceptance retain their separate gates. Historical Wiki integrity reports remain dated seals of their original publication cuts; this experiment adds its own manifest without rewriting those records.

AI use: OpenAI Codex assisted the experimental code, synthetic records, statistics, audits and explanation. All new result plots visibly retain `AI-generated | SIMULATED`. Original public CTX data retain their source attribution. Both mandatory project AI registers are updated in the same publication.
