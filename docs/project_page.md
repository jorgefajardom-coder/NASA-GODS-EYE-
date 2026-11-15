# Project page draft — how Mars Gods Eye answers the challenge

English draft for the NASA Space Apps project page of **Interplanetary Survival
Guide: Martian Map** (team *Houston, We Have a Bug!*). It maps each part of the
challenge text to what the repository actually contains. Items marked
**pending** or **future work** are not delivered. Scientific statements still
need David's review before submission (DV-3), and the organizer endorsement
gate (JES-07 / AC-10) is separate from this text.

## Summary (for the project page)

Mars Gods Eye is a layered, walkable map of real Mars terrain for a small crew:
an astronaut, a rover and a drone. It combines NASA orbital terrain, orbital
imagery, geology, weather, water and radiation context with real rover stops and
real rover photos, and shows them from orbit, in 3D and through a first-person
helmet display. A route planner checks time, energy and oxygen for the way out,
the work at the stop and the way back; when an observation contradicts the
orbital map, the affected crew member stops and gets a new route. Every run is
recorded and replays in a web browser with no server. It is a prototype that
replays recorded and simulated runs, not a live mission or a safety system.

## The challenge, point by point

| The challenge asks | What we deliver | Status |
| --- | --- | --- |
| A layered, integrated view of a location or route, with data from several NASA missions | Six Mars zones on a globe selector; each scene drapes NASA imagery on a NASA terrain model. Jezero combines MRO CTX, Mars 2020, MSL, Mars Odyssey and MGS products with the USGS geologic map | Delivered |
| A map, tool or interface an astronaut can use during a surface excursion | 3D map view, heading-up minimap and a first-person helmet display (compass tape with site bearings, resource gauges, the route in force draped on the ground with the next waypoint) | Delivered |
| Scientific goals and a location chosen for them | Each rover zone targets real NASA science sites as inspection stops: Perseverance sample sites Salette and Swift Run (Jezero), Curiosity drill holes Buckskin and Big Sky (Gale), Spirit and Opportunity contact-science targets (Gusev, Meridiani). The reasoning is in the [science POI dossier](science_poi_dossier.md) | Delivered; scientific review **pending** |
| At least three kinds of data | Jezero: topography (CTX DTM), optical (CTX orthomosaic), geology (USGS SIM 3464), atmosphere (Perseverance MEDA, Curiosity REMS), radiation (MSL RAD) and water (Mars Odyssey GRS). Every other zone: topography, optical, water and radiation | Delivered (Jezero 6 kinds; other zones 4) |
| Astronaut safety, radiation and space weather | Per-zone surface dose from MSL RAD (measured at Gale; elsewhere from RAD's dose-pressure relation, flagged where it extrapolates) with an example dose for a 4 h Marswalk; resource sufficiency alerts with a 20 % reserve; the crew member stops on a contradicting observation | Delivered as context. Live space weather (NASA DONKI) is **future work**; solar particle events are not in the dose |
| Spacesuit mobility and load | Time, energy and oxygen costs for walking, working and returning; amber and red alerts when the route uses the reserve or no longer fits | Delivered; costs are model estimates **pending** scientific review |
| A route that avoids obstacles | The planner routes over the orbital terrain avoiding steep slopes, keeps NoData and uncertainty, and replans after a contradiction | Delivered for slope. Individual rocks are below the 20 m orbital spacing: rock maps are **future work** |
| (Optional) Helmet HUD, tablet or habitat display | First-person helmet HUD and the map view | Delivered |
| (Optional) Interactive product for several locations | Six zones from a Mars globe built from the Viking MDIM 2.1 mosaic | Delivered |
| (Optional) Surface imagery as the view on arrival | Real Perseverance and Curiosity raw images at the real rover stops, in a photo tour seen from the rover's own cameras. NASA's feed has no Spirit or Opportunity images, and the viewer says so | Delivered |
| (Optional) Rovers or robots helping the crew | Rover and drone in the mission; drone camera and survey map | Delivered; in the featured recording only the astronaut moves |
| (Optional) Astronauts working in pairs | One astronaut | **Future work** |

## Data layered per zone

| Zone | Terrain | Imagery | Geology | Weather | Water | Radiation | Rover stops and photos |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Jezero (Perseverance) | CTX DTM 20 m | CTX orthomosaic | USGS SIM 3464 | MEDA, REMS | Odyssey GRS | RAD relation | Stops and raw images |
| Gale (Curiosity) | MSL Gale DEM | CTX mosaic | — | — | Odyssey GRS | RAD measured | Stops and raw images by sol |
| Gusev (Spirit) | Columbia Hills DEM | Visible mosaic | — | — | Odyssey GRS | RAD relation, extrapolated | Stops; no images in the feed |
| Elysium Planitia (InSight) | InSight DEM | CTX mosaic | — | — | Odyssey GRS | RAD relation | Lander, no stops |
| Meridiani Planum (Opportunity) | Endeavour HiRISE DEM | CTX mosaic | — | — | Odyssey GRS | RAD relation, extrapolated | Stops; no images in the feed |
| Valles Marineris (Melas) | CTX stereo DEM | CTX orthoimage | — | — | Odyssey GRS | RAD relation | Never visited |

Sources, product IDs and hashes: [data sources](data_sources.md),
[NASA traceability](nasa_traceability.md) and
[THIRD_PARTY_NOTICES.md](../THIRD_PARTY_NOTICES.md).

## Limitations and future work (for the project page)

- **Prototype, not a safety system.** It replays recorded and simulated runs; it
  does not certify that a route is safe to walk.
- **Space weather.** Radiation values are surface averages without shielding;
  solar flares and particle events are not included. A live check against NASA
  DONKI is future work (its public API could not be reached when this was
  written).
- **Rocks.** Orbital terrain cannot resolve rocks smaller than its grid spacing;
  HiRISE-based rock maps are future work.
- **Pairs.** One astronaut; a two-person Marswalk is future work.
- **Other zones.** Geology and weather layers exist only at Jezero.
- **Boxwork.** The challenge's own example, the boxwork Curiosity studied on
  Mount Sharp in 2025, is not yet a target in the Gale scene.
- **Astronaut resources.** The planner and the mission audit still use different cost
  models; unifying them (already decided, D-COST-02) and the follow-up steps are in the
  [astronaut resources proposal](astronaut_resources_proposal.md).
- **Mission.** In the featured recording only the astronaut moves, the
  contradicting observation is simulated and costs are model estimates.
- **AI use** is declared in [AI_USAGE.md](AI_USAGE.md); AI-generated media carry
  a visible `AI-generated` mark.
