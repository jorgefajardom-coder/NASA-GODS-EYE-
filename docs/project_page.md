# Project page — ready to paste into the Space Apps form

English text for the NASA Space Apps 2026 project page of team *Houston, We Have a
Bug!*, challenge **Interplanetary Survival Guide: Martian Map**. The sections follow
the fields of the official
[Project Submission Guide](https://www.spaceappschallenge.org/resources/project-submission-guide/),
in order; copy each one into its field. Text in `[brackets]` must be filled in by
the team before saving.

Before submitting: David reviews every scientific statement (DV-3), the demo link
works in a private browser on two machines (JO-4), and the local organizer has
explicitly endorsed the package (JES-07 / AC-10). Silence is not endorsement.

---

## Project Name

Mars Gods Eye

## High-Level Project Summary

Mars Gods Eye is a layered, walkable map of real Mars terrain for a crew on a
Marswalk: an astronaut, a rover and a drone. It stacks NASA data from several
missions on one view (orbital terrain, orbital imagery, geology, weather, water,
radiation, real rover stops and real rover photos) over six Mars zones. The crew
can see it from orbit, in 3D, or through a first-person helmet display. A route
planner checks time, energy and oxygen for the way out, the work at the science
stop and the way back. When an observation contradicts the orbital map, the
crew member stops and gets a new route from where they actually are. This
answers the challenge's gap: tools like Mars Trek are built for regional views,
while a crew on foot needs to know, metre by metre, which ground is only
estimated from orbit, what the walk costs, and how to get home. Every run is
recorded and replays in a web browser, with no server.

## Link to Project Demo

`[30-second video or 7-slide deck: public link, no login. English, or English
subtitles. Script below.]`

## Link to Final Project

- Web viewer: <https://jorgefajardom-coder.github.io/NASA-GODS-EYE-/>
- Source code and documentation: <https://github.com/jorgefajardom-coder/NASA-GODS-EYE->

## Detailed Project Description

### What it does

1. **Choose a place.** A Mars globe (Viking colour mosaic) shows six zones:
   Jezero (Perseverance), Gale (Curiosity), Gusev (Spirit), Elysium Planitia
   (InSight), Meridiani Planum (Opportunity) and Valles Marineris. Each card shows
   the zone's orbital image, its water and its daily radiation dose.
2. **Plan a Marswalk.** The science stops are real NASA science sites: the
   Perseverance sample sites Salette and Swift Run, the Curiosity drill holes
   Buckskin and Big Sky, and the Spirit and Opportunity contact-science rocks. The
   planner proposes FAST or SAFE routes over the orbital terrain. It avoids steep
   ground, keeps NoData and uncertainty, and checks time, energy and oxygen for
   the whole trip with a reserve.
3. **Walk it.** The first-person helmet display shows:
   - a compass tape with site bearings and a heading-up minimap;
   - gauges for oxygen, exhaled CO₂, energy, time, atmosphere and radiation dose;
   - the route draped on the ground, with the next waypoint;
   - alerts that compare what is left with what finishing the route, or walking
     back now, would need (*Route uses the reserve*, *Turn back*, *Return to base
     now*).
4. **React to the unexpected.** When a drone or rover observation contradicts the
   orbital estimate, the affected crew member stops, the route is cancelled and a
   new one is planned with the resources left.
5. **See what to expect.** At every real rover stop the viewer shows NASA's real
   rover photos, turning the view to where each photo was taken. The rover can be
   driven from its real cameras: Navcam, Mastcam-Z, Hazcams and WATSON.
6. **Replay and audit.** Every decision is recorded and replays offline, in REPLAY
   mode, with the source of every layer shown.

### How it works

- **Data:** public NASA terrain models and orbital mosaics are cropped to a local
  east-north-up grid, keeping their source, version and checksum. Orbital terrain
  starts as an *estimate*, with its uncertainty; a cell becomes *observed* only
  after a simulated observation.
- **Planner and mission authority:** Python and ROS 2 Jazzy nodes (planner,
  mapping, mission manager, gateway and recorder), with a Gazebo Harmonic
  simulation. Routes are costed with a resource model for walking, climbing and
  working in a suit, plus the return.
- **Viewer:** TypeScript with React and three.js, built with Vite, published as a
  static site. It plays recorded runs with no backend and falls back to a 2D map
  on computers without WebGL.

### Benefits

- **One view instead of many tools:** terrain, imagery, geology, weather, water,
  radiation and real ground photos together, at the scale of a walk.
- **Honest about uncertainty:** orbital estimates are never shown as
  observations. Every layer states its source and whether it is real, derived,
  estimated or simulated.
- **Built around the walk back:** the alerts follow NASA's Artemis rule that a
  crew must always be able to return to the habitat with its suit consumables.

### What we hope to achieve

A planning and walking aid that a crew could load before an EVA and keep on the
visor during it. It would draw on the data NASA already has, update when the
ground disagrees with the map, and be clear about what is known and what is
assumed.

### Tools and languages

Python, ROS 2 Jazzy, Gazebo Harmonic, TypeScript, React, three.js, Vite, Node.js,
GitHub Actions and GitHub Pages; Blender for the base model.

### The challenge, point by point

| The challenge asks | What we deliver | Status |
| --- | --- | --- |
| A layered, integrated view of a location or route, with data from several NASA missions | Six zones; each drapes NASA imagery on a NASA terrain model. Jezero combines MRO CTX, Mars 2020, MSL, Mars Odyssey and MGS products with the USGS geologic map | Delivered |
| A map, tool or interface an astronaut can use during a surface excursion | 3D map, heading-up minimap and first-person helmet display | Delivered |
| Scientific goals and a location chosen for them | Real NASA science sites as stops in every rover zone; the reasoning is in the [science POI dossier](science_poi_dossier.md) | Delivered; scientific review **pending** |
| At least three kinds of data | Jezero: topography, optical, geology, atmosphere, radiation, water (6). Other zones: topography, optical, water, radiation (4) | Delivered |
| Astronaut safety, radiation and space weather | Dose per zone from MSL RAD (measured at Gale, estimated elsewhere), shown against NASA's 600 mSv career limit; example dose for a 4 h Marswalk; resource alerts; stop on contradiction | Delivered as context; live space weather is **future work** |
| Spacesuit mobility and load | Time, energy, oxygen and exhaled CO₂ for walking, working and returning, with reserve alerts | Delivered; costs are model estimates **pending** review |
| A route that avoids obstacles | Routes avoid steep slopes and keep uncertainty; replanning after a contradiction | Delivered for slope; rock maps are **future work** |
| (Optional) Helmet HUD, tablet or habitat display | First-person HUD and map view | Delivered |
| (Optional) Several locations | Six zones from a Mars globe | Delivered |
| (Optional) Surface imagery as the view on arrival | Real Perseverance and Curiosity raw images at real rover stops | Delivered |
| (Optional) Rovers or robots helping the crew | Rover and drone in the mission | Delivered; in the featured recording only the astronaut moves |
| (Optional) Astronauts in pairs | One astronaut | **Future work** |

Data layered per zone:

| Zone | Terrain | Imagery | Geology | Weather | Water | Radiation | Rover stops and photos |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Jezero (Perseverance) | CTX DTM 20 m | CTX orthomosaic | USGS SIM 3464 | MEDA, REMS | Odyssey GRS | RAD relation | Stops and raw images |
| Gale (Curiosity) | MSL Gale DEM | CTX mosaic | — | — | Odyssey GRS | RAD measured | Stops and raw images by sol |
| Gusev (Spirit) | Columbia Hills DEM (HiRISE/CTX/HRSC) | Visible mosaic | — | — | Odyssey GRS | RAD relation, extrapolated | Stops; no images in the feed |
| Elysium Planitia (InSight) | InSight DEM (HiRISE/CTX/HRSC) | CTX mosaic | — | — | Odyssey GRS | RAD relation | Lander, no stops |
| Meridiani Planum (Opportunity) | Endeavour HiRISE DEM | CTX mosaic | — | — | Odyssey GRS | RAD relation, extrapolated | Stops; no images in the feed |
| Valles Marineris (Melas) | CTX stereo DEM | CTX orthoimage | — | — | Odyssey GRS | RAD relation | Never visited |

### Limitations and future work

- **Prototype, not a safety system.** It replays recorded and simulated runs and
  does not certify that a route is safe to walk.
- **Mission.** In the featured recording only the astronaut moves, the
  contradicting observation is simulated, and costs are model estimates.
- **Space weather.** Radiation values are surface averages without shielding;
  solar flares and particle events are not included. A live NASA DONKI check is
  future work.
- **Rocks.** Orbital terrain cannot resolve rocks smaller than its grid; HiRISE
  rock maps are future work.
- **Pairs.** One astronaut; a two-person Marswalk is future work.
- **Other zones.** Geology and weather layers exist only at Jezero; boxwork in Gale
  (the challenge's own example) is not yet a target.
- **Astronaut resources.** The planner and the mission audit still use different
  cost models. Unifying them is already decided; the follow-up steps are in the
  [astronaut resources proposal](astronaut_resources_proposal.md).

## Use of Super Intelligence (SI)

*(Not shown to the judges; the watermarks and declarations below are visible in
the project.)*

SI tools helped us build faster. The idea, the scope and every decision are the
team's. Full record, file by file: [AI_USAGE.md](AI_USAGE.md) and
[ai_usage.json](ai_usage.json).

- **Code, tests and documentation:** OpenAI Codex, Claude (Anthropic) through
  Claude Code and Google Antigravity assisted with code, tests, data-processing
  scripts and documentation. Each use is declared in text and metadata, file by
  file. No NASA observation was generated: all terrain, imagery, rover stops,
  photos and environmental values come from NASA and USGS sources.
- **Images:** the team logo and the astronaut portrait were generated with ChatGPT
  (OpenAI). Each carries a visible `AI-generated` watermark.
- **Video:** the intro screen was generated with Kling and carries
  `AI-GENERATED · KLING` burned into every frame. Its audio track is declared and
  played muted.
- **3D model:** the surface base was generated with OpenAI Codex and is declared
  as AI-generated.
- **NASA branding:** no generated content uses NASA logos, flags or mission marks.
  The rover and drone models are NASA/JPL-Caltech models with agency branding
  removed.

## NASA Data

- **MRO CTX** stereo terrain model and orthomosaic of Jezero (Mars 2020 TRN
  products, USGS Astrogeology, Fergason et al. 2020,
  [doi:10.5066/P906QQT8](https://doi.org/10.5066/P906QQT8)). They are the terrain the
  planner routes over, plus the draped image.
- **MRO HiRISE** terrain model of Jezero (Fergason et al. 2020). Held back as a
  hidden reference to evaluate results; never given to the planner or the viewer.
- **MGS MOLA** global elevation (NASA PDS): regional context and vertical alignment.
- **JPL Mars Trek** (<https://trek.nasa.gov/mars/>): the terrain models and mosaics
  of the other zones (MSL Gale DEM mosaic, Columbia Hills and InSight
  HiRISE/CTX/HRSC mosaics, Endeavour crater HiRISE DEM, CTX stereo DEM of Melas
  Chasma), and the Viking MDIM 2.1 colour mosaic of the globe.
- **USGS-NASA Planetary Geologic Mapping Program:** SIM 3464, geologic map of Jezero
  crater (Sun and Stack 2020, [doi:10.3133/sim3464](https://doi.org/10.3133/sim3464)).
- **Rover traverses:** Mars 2020 and MSL waypoints (MMGIS), and Spirit and
  Opportunity corrected traverses from the PDS Geosciences Node.
- **Rover photos:** Perseverance and Curiosity raw images from NASA's public feed
  (<https://mars.nasa.gov/mars2020/multimedia/raw-images/>).
- **Environment:**
  - Perseverance MEDA and Curiosity REMS weather summaries;
  - MSL RAD surface radiation dose (Hassler et al. 2014,
    [doi:10.1126/science.1244797](https://doi.org/10.1126/science.1244797));
  - Mars Odyssey GRS water-equivalent hydrogen (Boynton et al. 2007, PDS
    ODY-M-GRS-5-ELEMENTS-V1.0).
- **Mission design references:**
  - *Tenets of Lunar EVAs for Artemis III* (NASA 2023) for the walk-back reserve;
  - NASA's Human Exploration Zone rubric for the habitat-area slope criterion;
  - *Curiosity's Proposed Path up Mount Sharp* as the route-map design reference.
- **3D models and time:**
  - Perseverance and Ingenuity 3D models (NASA/JPL-Caltech);
  - NASA GISS Mars24 for Mars time and the Sun.

Sources, product IDs and checksums: [data sources](data_sources.md),
[NASA traceability](nasa_traceability.md) and
[THIRD_PARTY_NOTICES.md](../THIRD_PARTY_NOTICES.md).

## Space Agency Partner Data and Other References

- **ESA Mars Express HRSC:** HRSC stereo data are part of the Columbia Hills
  (Gusev) and InSight terrain mosaics distributed through JPL Mars Trek.
- **Science references:**
  - Guo et al. 2018, *JGR Planets* (RAD dose-pressure relation);
  - Herd 2025 and Vasavada 2022 (rover sampling and science strategy);
  - Squyres 2003 (MER contact science);
  - Maki et al. 2020 and Bell et al. 2021, *Space Science Reviews* (rover camera
    specifications);
  - Allison and McEwen 2000 (Mars time);
  - Yale Bright Star Catalogue (Hoffleit and Warren 1991) for the night sky;
  - NASA-STD-3001 (radiation career limit, scale only).
- **Third-party assets:**
  - Animated astronaut model by LasquetiSpice (Sketchfab, CC BY 4.0);
  - Barlow Condensed, IBM Plex Mono and Rajdhani fonts (SIL Open Font
    License 1.1).
- **Software:** React, three.js, Vite, ROS 2, Gazebo and their open-source
  dependencies under their own licences. Our own code is MIT-licensed.

---

## Demo script (30 seconds)

Follows the timing in the official guide. Use real screen captures from the
viewer, label what is recorded and what is illustrative, and keep the
`AI-GENERATED · KLING` mark visible if the intro appears.

| Time | Picture | Narration (English) |
| --- | --- | --- |
| 0:00 | Team logo (with its AI-generated mark) | "We are Houston, We Have a Bug!" |
| 0:02 | Mars globe turning | "Mars maps are made for regions. Astronauts walk metres." |
| 0:05 | Zone card, then *Travel* onto the terrain | "Mars Gods Eye: a walkable map built from NASA data." |
| 0:10 | 3D terrain with layers, then the helmet HUD with oxygen, CO₂ and dose | "Terrain, imagery, geology, water and radiation from six NASA missions, with oxygen and the way home on the visor." |
| 0:17 | Recorded run: contradiction, stop, new route | "When the ground disagrees with the map, the astronaut stops and gets a new route home." |
| 0:23 | Real Perseverance photo at a real stop | "Real rover photos show what is waiting there." |
| 0:27 | Wide shot of the zone | "The first map you would want on Mars." |
