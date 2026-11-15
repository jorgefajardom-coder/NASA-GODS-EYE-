# Glossary and notation

This glossary defines terms as used in the project. A product's metadata or a cited scientific paper may use a more specialized definition; the chapter using that source explains the connection.

| Term | Meaning in this Wiki |
|---|---|
| Activity | A specified interval of work, observation or waiting with an associated cost model. |
| Allocation | The time, energy or oxygen assigned to an agent for a declared mission interval. |
| Analytical simulation | A numerical workflow that advances reached poses, activities and resources under explicit assumptions. |
| Belief map | The public terrain representation available to the decision process at a particular version. |
| Campaign | An operational period that can contain several traverses, work intervals and, if modelled, replenishment opportunities. |
| Cell centre | The ENU position represented by the midpoint of one computational raster cell. |
| Context | The identities and versions binding a cost or evidence item to its run, agent, map, route, model and activity. |
| CTX | The Context Camera instrument on Mars Reconnaissance Orbiter; here the terrain source is a derived CTX DTM product. |
| Datum | The reference defining coordinates or elevations. A vertical datum is part of the interpretation of height. |
| DEM / DTM | Digital elevation model / digital terrain model. The product supplies a sampled surface, not a complete mobility or soil description. |
| Directed cost | A segment cost evaluated from its start to its end. Reversing a slope can change the result. |
| ENU | East, north, up: the project's local Cartesian coordinate convention, in metres. |
| Estimated cell | A valid orbital-prior cell that has not become a local observation merely by being used in a route. |
| EVA | Extravehicular activity; the active human mission interval in this model. |
| Evidence | A context-bound record supporting a particular claim, such as completed service or an executed step. |
| FEASIBLE | A planner result satisfying the implemented checks for the declared request and model. |
| Footprint | The spatial support of an observation or an agent; its geometry must be stated. |
| Grade | Dimensionless rise divided by horizontal run; distinct from slope angle in degrees. |
| Hash | A content digest used to identify exact bytes or a specified canonical array representation. |
| Holdout / check set | Prespecified seed indices used to check conclusions drawn from the exploratory group. |
| Hypothetical world | An explicitly synthetic environment used to test decisions under declared perturbations. |
| Itinerary | Outbound motion, unfinished work and directed return considered with current resources. |
| Journal | An ordered persistent record whose accepted entries can reconstruct the same run. |
| Latin hypercube | A stratified sampling design used to cover declared parameter ranges. |
| Margin | Remaining allocation minus the relevant estimated costs and separate reserve. |
| Metabolic Wh | Integrated human metabolic power; a different resource from a robot's electrical Wh. |
| NoData | Missing or invalid terrain information; it is not equivalent to a known free cell. |
| Observation | A typed, time- and context-bound input exposing information within its declared footprint. |
| Oxygen equivalent litre | Proposed dry ideal-gas-equivalent oxygen at 273.15 K and 101.325 kPa; not tank volume. |
| Paired comparison | Two strategies evaluated with controlled shared conditions so the stated intervention can be interpreted. |
| Prior | Information available before a particular local observation, here derived from public orbital data. |
| REPLAY | Presentation of an existing recorded timeline, rather than a new execution. |
| Reserve | A separately retained allocation, additional to the cost of the planned return. |
| Resolution | A property requiring qualification: native spacing, effective resolving ability and computational cell size differ. |
| Run identifier | The identity of a recorded execution context. Analytical counterfactual arms require their own full episode keys. |
| Service | Stationary work at a target, with duration and activity identity stated explicitly. |
| Sigma | A declared uncertainty parameter used by the model; its physical/statistical interpretation requires provenance. |
| SIMULATED | Provenance indicating model-generated conditions or outcomes. |
| UNKNOWN | A result that leaves the request unresolved, including bounded-search limits; it is not proof of no path. |
| Verified traversal | Closure of the actually executed steps against the declared public model and evidence requirements. |

Common symbols are $t$ for duration in seconds, $E$ for energy in Wh, $P$ for power in W, $m$ for mass in kg, $g$ for gravitational acceleration in m/s², $\eta$ for efficiency, $\Delta z$ for signed elevation change, and $s$ for grade. Each equation defines its variables locally so notation remains understandable without memorizing this table.

Return to [Home](Home.md), [Resource models](05-Resource-Models.md), or the [Bibliography](Bibliography.md).
