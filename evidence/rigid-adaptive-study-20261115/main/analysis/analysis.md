# Rigid and adaptive analytical mission comparison

Classification: SIMULATED; local exploratory analysis. These results do not constitute a verified LIVE mission.

Analysis scope: primary; sampling design: broad. The input contains 360 recorded scenario blocks and 1440 matched agent/mode conditions. The analysis uses 360 complete, independently seeded scenario/mission blocks. There are 0 incomplete blocks; planned but unexecuted blocks are retained in the coverage inventory. Supplementary or directed batches do not modify the frozen main estimand.

Recorded scenarios contain 222 distinct private-world array hashes across 360 blocks with a world hash. Independent mission draws are conditional on the selected public terrains; repeated unchanged arrays are not independent geological samples.

The standardized adaptive-minus-rigid completion-credit difference is -1.389 percentage points (95% paired-world interval -1.944 to -0.833). Credit requires the primary objective and directed return, with explicit evidence of no resource or reserve violation and no UNKNOWN outcome. A no-credit UNKNOWN is an unresolved model computation, rather than evidence that physical passage is impossible.

The optional-work difference is 0.220 (95% paired-world interval 0.188 to 0.253) completed objectives per agent/mode episode, averaged within worlds. Optional-work responsiveness is partly defined by the policy: a rigid plan cannot add new targets by construction. This endpoint must be read separately from safe recovery and primary completion.

The analysis first averages the four fixed agent/mode conditions within each world and then equally weights sector/family/size strata. Confidence intervals resample paired worlds within these strata, retaining every dependent episode. When a stratum is uncovered, only the covered-strata estimate is available; incomplete target coverage prevents a full planned-target claim. Zero-width bootstrap intervals and strata containing fewer than two worlds are flagged in the machine-readable output.

| Sector | Family | Side (m) | Attempted worlds | Complete worlds | Completion difference | Optional difference |
|---|---|---:|---:|---:|---:|---:|
| bright | blocked | 256 | 12 | 12 | 0.00 pp | 0.292 |
| bright | blocked | 512 | 12 | 12 | -2.08 pp | 0.125 |
| bright | detour | 256 | 12 | 12 | 0.00 pp | 0.333 |
| bright | detour | 512 | 12 | 12 | -2.08 pp | 0.250 |
| bright | relief | 256 | 12 | 12 | 0.00 pp | 0.000 |
| bright | relief | 512 | 12 | 12 | -2.08 pp | 0.000 |
| bright | resource | 256 | 12 | 12 | 0.00 pp | 0.375 |
| bright | resource | 512 | 12 | 12 | -4.17 pp | 0.188 |
| bright | unchanged | 256 | 12 | 12 | 0.00 pp | 0.125 |
| bright | unchanged | 512 | 12 | 12 | -2.08 pp | 0.208 |
| bunsen | blocked | 256 | 12 | 12 | 0.00 pp | 0.312 |
| bunsen | blocked | 512 | 12 | 12 | -4.17 pp | 0.250 |
| bunsen | detour | 256 | 12 | 12 | 0.00 pp | 0.333 |
| bunsen | detour | 512 | 12 | 12 | 0.00 pp | 0.250 |
| bunsen | relief | 256 | 12 | 12 | 0.00 pp | 0.000 |
| bunsen | relief | 512 | 12 | 12 | 0.00 pp | 0.042 |
| bunsen | resource | 256 | 12 | 12 | 0.00 pp | 0.250 |
| bunsen | resource | 512 | 12 | 12 | 0.00 pp | 0.208 |
| bunsen | unchanged | 256 | 12 | 12 | 0.00 pp | 0.333 |
| bunsen | unchanged | 512 | 12 | 12 | -6.25 pp | 0.250 |
| hawksbill | blocked | 256 | 12 | 12 | 0.00 pp | 0.292 |
| hawksbill | blocked | 512 | 12 | 12 | -6.25 pp | 0.271 |
| hawksbill | detour | 256 | 12 | 12 | 0.00 pp | 0.375 |
| hawksbill | detour | 512 | 12 | 12 | -2.08 pp | 0.125 |
| hawksbill | relief | 256 | 12 | 12 | 0.00 pp | 0.000 |
| hawksbill | relief | 512 | 12 | 12 | -4.17 pp | 0.000 |
| hawksbill | resource | 256 | 12 | 12 | 0.00 pp | 0.417 |
| hawksbill | resource | 512 | 12 | 12 | -6.25 pp | 0.354 |
| hawksbill | unchanged | 256 | 12 | 12 | 0.00 pp | 0.250 |
| hawksbill | unchanged | 512 | 12 | 12 | 0.00 pp | 0.396 |

Broadly generated worlds and corridor-conditioned directed cases have separate denominators. Their ensemble frequencies are not estimates of Mars hazard rates or probabilities of scientific discovery. Costs, sensing and execution remain limited to the frozen analytical model and its recorded assumptions.

The numerical implementation follows paired resampling as documented by [SciPy](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.bootstrap.html). Descriptive binary world indicators use [Wilson intervals documented by NIST](https://www.itl.nist.gov/div898/handbook/prc/section2/prc241.htm). Condition-specific discordance is also reported using the [exact binomial McNemar calculation](https://www.statsmodels.org/stable/generated/statsmodels.stats.contingency_tables.mcnemar.html); these auxiliary comparisons are exploratory.

AI use: OpenAI Codex assisted the protocol, analysis code and generated explanatory figures. Simulated outputs are not NASA observations.
