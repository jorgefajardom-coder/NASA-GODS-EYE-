# Bibliography and source interpretation

[Home](Home.md) · [Glossary](Glossary.md) · [Parameters](Parameters-and-Decisions.md) · [Reproducibility](Reproducibility.md)

The references below connect each explanation to its scientific basis. Chapters cite author and year, link the original publication or product, and identify the relevant table, section or figure when a numerical value is used. Web resources were consulted on 15 November 2026. Publication dates, archive migration dates and retrieval dates describe different events; a newer archive record does not make an older observation recent.

Four kinds of statement recur throughout the Wiki. A published observation reports what the cited investigation measured. A model formulation describes how the project represents a process. An experimental choice specifies a scenario, coefficient or policy selected for comparison. A project result records what happened under identified inputs. The source supports its stated contribution: selecting a reference scale or equation structure does not approve every coefficient used in our implementation. Worked calculations cite the parameter registry and scientific API alongside the original anchors.

## Planetary science and geological setting

- Farley, K. A., et al. (2020). [Mars 2020 Mission Overview](https://doi.org/10.1007/s11214-020-00762-y). Space Science Reviews, 216, 142. Original mission paper; abstract and science objectives support the context in [Chapter 1](01-Research-Question.md).
- Sun, V. Z., and Stack, K. M. (2020). [Geologic map of Jezero crater and the Nili Planum region, Mars](https://doi.org/10.3133/sim3464). USGS Scientific Investigations Map 3464, scale 1:75,000. Regional units and contacts; local registration is considered separately.
- Hurowitz, J. A., et al. (2025). [Redox-driven mineral and organic associations in Jezero Crater, Mars](https://doi.org/10.1038/s41586-025-09413-0). Nature, 645, 332–340. Original instrumental investigation. Figures 1–3 connect spatial context, workspace and target measurements used in [Chapter 2](02-Jezero-Science.md).
- Stack, K. M., et al. (2024). [Sedimentology and Stratigraphy of the Shenandoah Formation, Western Fan, Jezero Crater, Mars](https://doi.org/10.1029/2023JE008187). Journal of Geophysical Research: Planets, 129, e2023JE008187. Section 6.2.5 describes the Hogwallow Flats member. Publication year is 2024; the DOI contains the manuscript identifier 2023.
- Benison, K. C., et al. (2024). [Depositional and Diagenetic Sulfates of Hogwallow Flats and Yori Pass, Jezero Crater: Evaluating Preservation Potential of Environmental Indicators and Possible Biosignatures From Past Martian Surface Waters and Groundwaters](https://doi.org/10.1029/2023JE008155). Original sedimentological and diagenetic study.
- Broz, A. (2024, 16 April). [Comet Geyser: Perseverance's 21st Rock Core](https://science.nasa.gov/blog/comet-geyser-perseverances-21st-rock-core/). NASA mission-team field account. The writer is credited in the article; the later page update is distinct from original publication. Used for Bunsen workspace context.

## Terrain products and their interpretation

- USGS. [Mars 2020 Terrain Relative Navigation CTX DTM Mosaic](https://doi.org/10.5066/P906QQT8). Data release underlying the public prior. The [project source register](../data_sources.md) identifies processing and delivered products.
- USGS. [Mars ASP Generated CTX DTMs and Orthoimages](https://stac.astrogeology.usgs.gov/docs/data/mars/ctxdtms/). Technical product documentation; consult the production description and “Accuracy, Errors, and Issues” for post spacing, resolving capability and artifacts. The general guidance is distinguished from metadata specific to our crop.
- Smith, D. E., Neumann, G., and Hughes, M. N. (2026 archive edition). [MGS MOLA Derived Topography — MEGDR and SHADR Dataset Bundle](https://doi.org/10.17189/1z1b-kv84), version 1.0; identifier `urn:nasa:pds:mgs_mola_topography_derived::1.0`. PDS4 migration of older MOLA datasets; its archive publication year does not date the observations. Regional context is explained in [Chapter 3](03-Terrain-and-Scale.md).

## Human activity, physiology and units

- Chappell, S. P., Norcross, J. R., Abercromby, A. F., and Gernhardt, M. L. (2010). [Life Sciences Implications of Lunar Surface Operations](https://ntrs.nasa.gov/citations/20110001417). NASA/TM-2010-216138. Table 3, printed p. 12/PDF p. 20, contains activity primitives; Table 4, printed p. 13/PDF p. 21, supplies lunar-analogue metabolic anchors. Mars transfer and our activity associations are modeling choices.
- Ewert, M. K., Chen, T. T., and Powell, C. D., eds. (2022). [Life Support Baseline Values and Assumptions Document](https://ntrs.nasa.gov/citations/20210024855), BVAD, NASA/TP-2015-218570/Rev2. Table 4-70, printed p. 135/PDF p. 149, supplies the reference oxygen and energy rates. The edition is 2022 despite the report number's 2015 component.
- Hurtado, J. M., Jr., et al. (2011). [Lessons Learned for Geologic Data Collection and Sampling: Insights from the Desert RATS 2010 Geologist Crewmembers](https://ntrs.nasa.gov/citations/20120011761). LPSC abstract 1334, pp. 1–2. Reported terrestrial-analogue workflow experience supports the documented-sample duration discussion.
- Bekdash, O. S., et al. (2020). [Development and Evaluation of the Active Response Gravity Offload System as a Lunar and Martian EVA Simulation Environment](https://ntrs.nasa.gov/citations/20205003610). ICES-2020-175, Section II.C.1, pp. 6–7. Its prescribed sampling blocks and test configuration are interpreted separately from measured complete cycles.
- NIST. [Chemistry WebBook: Oxygen](https://webbook.nist.gov/cgi/cbook.cgi?Name=O2). Molecular-weight entry used in the oxygen amount conversion.
- NIST (2022 adjustment). [Fundamental Physical Constants — Extensive Listing](https://physics.nist.gov/cuu/pdf/all.pdf). Ideal-gas constants and molar-volume reference conditions. [Chapter 5](05-Resource-Models.md) states the implementation's retained numerical precision.

## Robot reference scales and power structure

- Howard, T. M., Cameron, J., Myint, S., Nayar, H., and Jain, A. (2011). [An KML Interface for Dynamics Simulation of Robotic Planetary Exploration](https://dartslab.jpl.nasa.gov/References/pdf/2011-howard_ieeeaero_2011.pdf). IEEE Aerospace Conference. The LSOS/ROAMS power discussion on p. 4 informs decomposition into system loads and movement work; vehicle coefficients require their own identification.
- NASA. [Perseverance Rover Components](https://science.nasa.gov/mission/mars-2020-perseverance/rover-components/). Mission specifications; “Body” and “Rover Speed” provide reference mass and speed scales.
- JPL. [Mars 2020 Perseverance Landing Press Kit: Power](https://www.jpl.nasa.gov/news/press_kits/mars_2020/landing/mission/spacecraft/power/). Mission account of MMRTG generation and batteries. The mission name is not used as an inferred publication year.
- NASA Science Editorial Team (2021, 30 April). [What We're Learning About Ingenuity's Flight Control and Aerodynamic Performance](https://science.nasa.gov/blog/what-were-learning-about-ingenuitys-flight-control-and-aerodynamic-performance/). Mission-team flight report; hover discussion supports the rotor-power reference, while auxiliary power is our assumption.
- JPL Solar System Dynamics. [Planetary Physical Parameters](https://ssd.jpl.nasa.gov/planets/phys_par.html). Mars row: reference equatorial gravity used by the model.

## Experimental methods and project evidence

- Hart, P. E., Nilsson, N. J., and Raphael, B. (1968). [A Formal Basis for the Heuristic Determination of Minimum Cost Paths](https://doi.org/10.1109/TSSC.1968.300136). IEEE Transactions on Systems Science and Cybernetics, 4(2), 100–107. Foundational heuristic-search principle; the project's resource labels and FAST/SAFE semantics are documented in its planner implementation.
- McKay, M. D., Beckman, R. J., and Conover, W. J. (1979). [A Comparison of Three Methods for Selecting Values of Input Variables in the Analysis of Output from a Computer Code](https://doi.org/10.2307/1268522). Technometrics. Methodological origin of Latin hypercube sampling.
- SciPy developers. [LatinHypercube reference](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.qmc.LatinHypercube.html). Official sampling-interface documentation. Actual experiment versions are recorded with the run.
- NumPy developers. [Parallel random number generation](https://numpy.org/doc/stable/reference/random/parallel.html). Official reference for explicit random streams and seed derivation.

Project-specific choices are recorded in the [scientific decisions](../science_decisions.md), [parameter registry](../../config/science_profiles.proposed.json) and [scenario approval](../science_approvals/jezero_scenario_20261114.json). Results cite the [research catalogue](../../evidence/overnight-mission-research-20261115-v3/README.md), [analytical EVA](../../evidence/mission-cost-experiment-20261115-local-v2/README.md), or [crop comparison](../../evidence/mission-3d-video-20261115-local/map-analysis/crop-comparison.json). The [reproduction guide](Reproducibility.md) explains how source identities, configurations and run identifiers bind those records to the claims in this Wiki.
