# Human activity durations: evidence and analytical pilot

Recorded 14 November 2026 for David, Diego and Jesús. This is a source review
and **analytical pilot**, not a suited test, executor run or approval. The
approved JZ-P03 check-in (120 s), JZ-P07 sampling example (180 s), resource
caps and reserves remain unchanged. No profile coefficient is newly approved.

## What the sources support

| Source | Duration and scope | Evidence type and transfer limits |
|---|---|---|
| [Chappell et al., NASA/TM-2010-216138](https://ntrs.nasa.gov/api/citations/20110001417/downloads/20110001417.pdf#page=20), §3.1/Table 3, printed p.12 / PDF p.20 | 30 s manual pickup without tools; 60 s hammering; 180 s trenching | Lunar surface **model assumptions**, not measured complete sample cycles. Table 4 classifies contextual work/pickup as light and hammering/trenching as heavy. These distinct primitives are not a statistical duration range for one task. |
| [Hurtado et al., LPSC 2011 abstract 1334](https://ntrs.nasa.gov/api/citations/20120011761/downloads/20120011761.pdf), pp.1–2, field protocol and time/task management | Approximately 10 min per documented sample | Reported D-RATS 2010 terrestrial experience with simulated suits. Context imagery, descriptions, acquisition, recording, bagging and tool recovery contribute. No timing distribution or Mars transfer factor is supplied. |
| [Bekdash et al., ICES-2020-175](https://ntrs.nasa.gov/api/citations/20205003610/downloads/ARGOS%20ICES%202020%20-Final%20for%20Export%20Control.pdf), §II.A p.3, §II.C.1 pp.6–7 | 10 min sampling block per subsite, after contextual survey/documentation; simulation about one hour | Prescribed ARGOS pilot block, **not measured time per sample**. MKIII was pressurized; the facility imposed task/space adaptations. Do not add its context-before-sampling model to the D-RATS total as though they were one protocol. |
| [Arnold et al., 2006](https://ntrs.nasa.gov/api/citations/20060013538/downloads/20060013538.pdf#page=5), Surface Activity Planning, PDF p.5 | Geology stops can be about 10 min and rarely exceed an hour in its Apollo-based planning discussion | Whole-stop planning context, including several activities. It is not an isolated inspection duration or a hard maximum for future Mars work. |

No universal, independently timed **Mars inspection** duration was established
by these sources. The 120 s baseline remains a chosen brief visual check-in;
it should not be described as a complete geological survey. A 300 s inspection
is included only as an explicitly labelled engineering sensitivity, not a
measured average. No gravity-only scaling from lunar/terrestrial timings is
justified: task definition, suit, tools, documentation, crew coordination and
communications matter. These human sources do not establish rover inspection
or drone survey duration; their existing assumptions remain separate.

## Pilot supplied for review

[Pilot inputs](../config/activity_duration.pilot.json) preserve source URL,
locator, scope, evidence category and modeling caveat per case. The mixed
600 s workflow allocates **420 s light + 180 s heavy work**: its total is
anchored to the D-RATS report, but this phase split is **our assumption**, not
a reported measurement. `inspect` is the existing light-work costing alias,
not proof of a completed inspection or a new human task capability. The
all-heavy 600 s ARGOS case is an analytical power bound, not its measured load.

```sh
python scripts/export_cost_agreement_vectors.py --run-id duration-vectors \
  --activity-pilot config/activity_duration.pilot.json --output-dir tmp/duration-vectors
python scripts/evaluate_activity_duration_pilot.py --run-id duration-impact \
  --vectors tmp/duration-vectors/cost_vectors.json --output-dir tmp/duration-impact
```

The first command exports 38 baseline vectors plus seven duration cases. The
second reuses the unchanged public-prior human cost probe and checks the same
approved budgets/reserves. No planner substitute, observation, work completion
or route authorization is produced. Complete sample cycles include their own
documentation; primitive acquisition durations are alternatives, not extra
time to append inside that same cycle. A separate primary check-in remains a
separate task in the additive cases. Replacing it requires a new scenario review.

| Case | Isolated analytical activity cost | Combined with approved primary cost probe |
|---|---|---|
| 30 s pickup, light | 2.984 Wh; 0.609 L O2 | Fits the modeled envelope; acquisition only |
| 60 s hammering, heavy | 7.686 Wh; 1.570 L | Fits the modeled envelope; acquisition only |
| 180 s trenching, heavy | 23.059 Wh; 4.709 L | 581.12 s / 68.33 Wh / 13.95 L; fits usable resources |
| Replace 120 s check-in by 300 s light observation | 29.840 Wh; 6.093 L | 581.12 s / 63.17 Wh / 12.90 L; proposed replacement only |
| Add one 600 s documented workflow, mixed | 64.835 Wh; 13.239 L | **1001.12 s / 110.10 Wh / 22.48 L: fails all three usable resources** |

The human usable limits after the unchanged 20% reserve are 960 s / 80 Wh /
20 L. Thus a full documented sample cannot simply replace the existing
three-minute example without reconsidering the experimental scope or allocation.
These additive cases exclude extra optional travel and additional coordination
delays, so actual assignments may cost more. Oxygen remains a metabolic model
estimate; suit losses are excluded. Passing these examples does not demonstrate
physical capability, executor behavior, joint uncertainty robustness or success.

The [retained impact](../evidence/mission-cost-closure-20261114/pilot-final/activity_pilot_impact.json)
and [vectors](../evidence/mission-cost-closure-20261114/vectors-final/cost_vectors.json)
keep exact numerical inputs and hashes. The pilot is deliberately small; it
does not freeze A/B/C, establish an empirical task distribution or change any
approved value.

## Handoff to Diego and Jesús

Diego needs the same directed itinerary and explicit phase schedule, including
activity identity, remaining service, wait type, current resources and reserves.
Use the [cost contract](cost_agreement_handoff.md): one fixed service power and
one O2/time rate cannot represent all these cases. Matching finite vectors is
necessary but not proof of global formula identity or profile approval.

Jesús needs real stationary phases at B, public start/progress/completion
evidence, and resource depletion during service and wait. The current executor's
movement-rate averaging is not that implementation. A primary completion
claim must not pass just because a pose reaches B. Interrupted work must expose
completed and remaining service once, with no double charge on replan.

Next review: retain 120 s as a brief technical check-in, or explicitly approve
a longer geological workflow and revised allocation after this pilot. Do not
automatically replace the baseline or set approval flags. This packet is ready
to share manually; no message to another team member was sent by these tools.
