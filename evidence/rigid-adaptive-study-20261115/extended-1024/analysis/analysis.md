# Rigid and adaptive analytical mission comparison

Classification: SIMULATED; local exploratory analysis. These results do not constitute a verified LIVE mission.

Analysis scope: broad_extension; sampling design: broad. The input contains 180 recorded scenario blocks and 720 matched agent/mode conditions. The analysis uses 180 complete, independently seeded scenario/mission blocks. There are 0 incomplete blocks; planned but unexecuted blocks are retained in the coverage inventory. Supplementary or directed batches do not modify the frozen main estimand.

Recorded scenarios contain 111 distinct private-world array hashes across 180 blocks with a world hash. Independent mission draws are conditional on the selected public terrains; repeated unchanged arrays are not independent geological samples.

The standardized adaptive-minus-rigid completion-credit difference is -3.056 percentage points (95% paired-world interval -4.306 to -1.944). Credit requires the primary objective and directed return, with explicit evidence of no resource or reserve violation and no UNKNOWN outcome. A no-credit UNKNOWN is an unresolved model computation, rather than evidence that physical passage is impossible.

The optional-work difference is 0.114 (95% paired-world interval 0.082 to 0.149) completed objectives per agent/mode episode, averaged within worlds. Optional-work responsiveness is partly defined by the policy: a rigid plan cannot add new targets by construction. This endpoint must be read separately from safe recovery and primary completion.

The analysis first averages the four fixed agent/mode conditions within each world and then equally weights sector/family/size strata. Confidence intervals resample paired worlds within these strata, retaining every dependent episode. When a stratum is uncovered, only the covered-strata estimate is available; incomplete target coverage prevents a full planned-target claim. Zero-width bootstrap intervals and strata containing fewer than two worlds are flagged in the machine-readable output.

| Sector | Family | Side (m) | Attempted worlds | Complete worlds | Completion difference | Optional difference |
|---|---|---:|---:|---:|---:|---:|
| bright | blocked | 1024 | 12 | 12 | -4.17 pp | 0.062 |
| bright | detour | 1024 | 12 | 12 | -2.08 pp | 0.167 |
| bright | relief | 1024 | 12 | 12 | 0.00 pp | 0.000 |
| bright | resource | 1024 | 12 | 12 | 0.00 pp | 0.042 |
| bright | unchanged | 1024 | 12 | 12 | -4.17 pp | 0.104 |
| bunsen | blocked | 1024 | 12 | 12 | -6.25 pp | 0.146 |
| bunsen | detour | 1024 | 12 | 12 | 0.00 pp | 0.000 |
| bunsen | relief | 1024 | 12 | 12 | 0.00 pp | 0.000 |
| bunsen | resource | 1024 | 12 | 12 | 0.00 pp | 0.083 |
| bunsen | unchanged | 1024 | 12 | 12 | 0.00 pp | 0.000 |
| hawksbill | blocked | 1024 | 12 | 12 | 0.00 pp | 0.312 |
| hawksbill | detour | 1024 | 12 | 12 | -6.25 pp | 0.229 |
| hawksbill | relief | 1024 | 12 | 12 | -10.42 pp | 0.000 |
| hawksbill | resource | 1024 | 12 | 12 | -8.33 pp | 0.312 |
| hawksbill | unchanged | 1024 | 12 | 12 | -4.17 pp | 0.250 |

Broadly generated worlds and corridor-conditioned directed cases have separate denominators. Their ensemble frequencies are not estimates of Mars hazard rates or probabilities of scientific discovery. Costs, sensing and execution remain limited to the frozen analytical model and its recorded assumptions.

The numerical implementation follows paired resampling as documented by [SciPy](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.bootstrap.html). Descriptive binary world indicators use [Wilson intervals documented by NIST](https://www.itl.nist.gov/div898/handbook/prc/section2/prc241.htm). Condition-specific discordance is also reported using the [exact binomial McNemar calculation](https://www.statsmodels.org/stable/generated/statsmodels.stats.contingency_tables.mcnemar.html); these auxiliary comparisons are exploratory.

AI use: OpenAI Codex assisted the protocol, analysis code and generated explanatory figures. Simulated outputs are not NASA observations.
