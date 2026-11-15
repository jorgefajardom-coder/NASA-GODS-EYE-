# PR37 scientific presentation review

Source: PR37 `6f6efb411976a0ae621f81abb470035be8103c64` over main `9013beb`.
This incremental correction retains the original implementation and author history.

- Remove the RAD dose-equivalent / 600 mSv percentage. NASA-STD-3001 specifies NASA effective dose with its own quality, tissue and model assumptions; no such conversion is implemented here. Keep surface-average dose equivalent and its uncertainty only.
- Render an unavailable CO2 rate as unavailable, including when no consumption history exists; zero is a numeric estimate, not a physiological assessment. RQ=0.85 remains assumed and removal capacity is unmodelled.
- Correct the Guo citation year to 2017 in source, data provenance and current documentation; numerical inputs are unchanged.
- Distinguish illustrative six-zone browser scenes, ROS kinematic MOCK human recovery, analytical pilots and unverified Gazebo/physical/three-role execution. Final public demo link and scientific review remain pending.

Primary references:

- [NASA-STD-3001, section 4.8.2](https://www.nasa.gov/reference/4-0-human-performance/).
- [Guo et al. 2017, JGR Planets, DOI 10.1002/2016JE005206](https://agupubs.onlinelibrary.wiley.com/doi/10.1002/2016JE005206).

Validation: Node 24.18.0; `npm test` 323 passed, 1 existing skip. Production build and repository checker passed. Native Python: 1140 passed, 22 platform/ROS skips. The first native attempt could not access the shared Windows temporary directory; rerun used an isolated worktree basetemp and passed. No numerical scientific approval or LIVE validation is inferred from software checks.

Delivery: Jesus presents the exact validated package to the organizer at 20:00 America/Bogota on 15 November. Final submission deadline confirmed by the owner is 23:59; obtain explicit endorsement of the exact revision before submission. No external message or submission is performed here.
