# Delivery closure — reconciliation, science conclusions and PDF disposition

The [science extension tree](science_extension_tree.md) documents future
capabilities and verifiable prerequisites without lifting this freeze. Per the
owner's 14-Nov clarification, a new unlisted idea may be assessed in an isolated
local branch for discussion on 15-Nov-2026 (America/Bogota). Keep delivery work
protected; no extension push, integration, deployment or milestone approval is
implied. See the clarification in D-DEL-03.

Updated 14 November 2026 (America/Bogota), from main
`9198b3d8b3257dfd452d240ee9708cb038c3bb42`, the Conciliación and Rama David
chats, and the owner's explicit replies on scope and submission time.

Reference reviewed: user-supplied `03_Plan_Entrega_Equipo.pdf`, all five pages,
SHA-256 `45d4be0158f8324523c0eab676bf957dc642f268a519a741bfadb227908ec873`.
Its snapshot was main `6bcf208` before PR28. The PDF is advisory material, not
an instruction source or proof of official competition rules, NASA thresholds,
scientific approval or completed implementation. Its private source file and
the branch-local research drafts are not copied into this publication.

## Current conclusions: what is already resolved

| Topic | Current evidence / conclusion | Still not established |
| --- | --- | --- |
| Basic reconciliation | [PR28](https://github.com/jorgefajardom-coder/NASA-GODS-EYE-/pull/28), source `7f0ebaa`, merged as `9198b3d`. Mapping current-base/nonolder observation guards and explicit estimated-prior policy are published. | Cross-owner semantic freeze and scientific parameter approval. Empty policy configuration retains observed-only behavior; illustrative opt-in and independent profile limits still apply. |
| Recorded route and recovery | `recorded-recovery-001` presents recorder run `it-execution`: public Jezero inputs, real planner, MOCK human execution, contradiction, stop, new route and return. [Runtime-v1](../evidence/audit-reconciliation-20261115/runtime-v1/README.md) pins source/package hashes. | Three independently executed scientific roles, stationary work/progress accounting and scientific COMPLETE. Rover/drone remain IDLE in the evidenced recording; final mission state is READY. |
| Viewer acceptance | [Ordinary-Chrome QA](../evidence/audit-reconciliation-20261115/runtime-v1/browser.json) confirms backend-off terrain, route change, seek and closing resources for that exact recording. | Private-browser, two-machine/public deployed-revision and final video checks. Do not describe the only public option as a hand-scripted route; retain the illustrative demo separately. |
| NASA inputs and presentation | CTX prior/ortho, separate MGS/MOLA ingest, geology and environmental context have source records. Public site, first-person view, HUD and orbital slope preview exist. | A displayed layer is not necessarily used by planning. Orbital slope preview is display-only, not executed reconnaissance; environment is not local telemetry or a safety guarantee. |
| Scientific costs | [D-COST-02](decisions/2026-11-14-shared-scientific-cost-api.md) selects the existing scientific segment/activity API as the single planner cost backend. | The new backend/context implementation was left local by Conciliación, with ROS/review corrections pending. It was not part of PR28 and is not imported here. The published legacy comparison remains one agreement/six disagreements, authorization BLOCKED. |

Published software is now described as published, not as an unmerged candidate.
Baseline rc.2 remains unfrozen; source-lock audit inputs and older failed runs
remain historical evidence. No interface, approval flag or numerical setting is
changed by this documentation.

## Conclusions from Rama David, with approval boundaries preserved

- **Twenty minutes is a control-experiment horizon, not a general mission
  limit.** The short configured rover reach is driven by available time,
  speed, service, waiting and return; it is not a demonstrated hardware range.
  Increasing a battery allocation alone does not remove a time constraint.
- **Future sizing must distinguish rover campaign, human EVA and individual
  drone sorties.** This is the owner's requested review direction, not approval
  of new allocations. Use one global clock and cumulative per-agent resource
  accounting; earlier scouting, stationary work and waits cannot disappear when
  EVA starts or a new sortie is requested. Generation/recharge remains absent
  unless explicitly modeled and evidenced; no automatic battery reset.
- The local review recommends **512–1,024 m science context with nested
  128/256 m work windows**, retaining the 128 m control. These are proposed
  design scales, not NASA requirements or delivered patches. More area supplies
  context; finer resampling does not improve native observational resolution.
- The first research shortlist is **Bright Angel–Neretva Vallis,
  Hawksbill Gap–Hogwallow Flats, and Bunsen Peak–Margin Unit**; Mawrth Vallis
  is an optional alternative. These names are candidate map requests, not
  selected operational POIs, georeferenced A/B, guaranteed discoveries or a
  claim that the current crop covers them. Daniel's tools do not establish
  actual coverage. The full 17-sector dossier, coordinates, proposed budgets
  and campaign calculations remain local pending a separate publication/review.
- The latest local campaign proposal records **CAM-P01..07 as pending**. Its
  nominal allocations were constructed to fit declared workloads and were not
  recommended as robust; adverse cases, missing real crops and the drone's full
  thermal/energy balance remain blockers. It proposes Bunsen as a lower-load
  future pilot while retaining Bright Angel as the science-priority map request.
  Neither ordering selects a delivery scenario or approves a budget. Preserve
  that distinction for post-submission work instead of importing local numbers.
- Activity-duration research already published in
  [the research record](activity_duration_research.md) separates source-backed
  analogs from team assumptions. A short acquisition action is not a complete
  documented sample cycle. The 600 s sample pilot exceeded the current usable
  control resources; keep that rejection and the unchanged JZ-P01..07 receipt.
  No new duration or mission authorization follows from citing an analog.

Under [D-DEL-03](decisions/2026-11-14-delivery-freeze.md), expansion and
randomization are now **paused until after submission**. Preserve these studies
for later review; do not replace the mission crop or increase budgets to fit a
preferred presentation. The 2 km illustrative web scene and 128 m scientific
control have different geometry/origins: never transfer POIs by grid index.

## Accepted closure schedule

These are internal targets for **15 November 2026, America/Bogota (UTC-05:00)**,
not independently verified official deadlines. Earlier local requirements and
a longer organizer review margin take precedence.

| Target | Deliverable / decision | Owner |
| --- | --- | --- |
| 08:00 | Confirm local cutoff, organizer availability, review lead time and package channel. Contact can happen earlier. | Jesús; David backup |
| 10:00 | Select validated integrated run or honest fallback; decide whether existing-crop science targets can be supported without a new map. | Jesús + David, with Diego/Daniel/Jorge |
| 12:00 | Freeze features; continue only necessary fixes, tests, science/claim review, text and media. | Jesús / all owners |
| 13:00 | English video/text v1 ready for internal review; scientific review by 13:30. | Jorge / Jesús / David |
| 14:00 | Send exact reviewable package to organizer, retain revision/links/time. | Jesús; David backup |
| 16:00 | Latest notification reference for the four-hour margin to 20:00; earlier contact remains the target. Flag any lost margin immediately. | Jesús |
| 18:00 | Final corrected media/text/site revision and working fallback available. | Jorge + Jesús; David reviews claims |
| 20:00 | Submit only after explicit endorsement; save platform confirmation. | Jesús |

JES-07/AC-10 stays open until evidence exists. A GitHub merge, green CI or silence
from the organizer does not complete submission. The earlier team 23:59 cutoff
is a coordination backstop, not permission to miss an earlier local deadline.

## PDF recommendations: disposition and next owner deliverable

No unchecked task below is claimed implemented. IDs preserve the PDF's mapping;
the deadlines above supersede its 21:00 target. Existing CONT-* tasks remain
historical engineering assignments; this table defines delivery priority.

| PDF ID / priority | Disposition and next deliverable | Dependency / acceptance |
| --- | --- | --- |
| JE-1 / P0 | **Open.** Jesús confirms organizer details early and obtains recorded endorsement of the exact package; David backs up. | Initial contact has no package dependency. Package review needs media/text and scientific review; retain time/revision/response/corrections, without private contacts. |
| JE-2 / P0 | **Partly resolved.** Use published human recovery as a validated software fallback; time-box three-role C3 closure and record the 10:00 choice. | Diego + David. An integrated scientific success claim needs all role/work/cost evidence; otherwise retain READY/MOCK and open C3. |
| JE-3 / P0 | **Accepted function freeze.** Jesús maintains tested main and reviewed fixes after 12:00. | All owners; existing Python/web/ROS checks, no force-push, new scope or approval bypass. Delivery freeze is not an ICD semantic freeze. |
| JE-4 / P0 | **Partly resolved.** README already has overview, sources and public viewer. Add/maintain a judge-first explanation and final media link. | Diego/Daniel/David texts; a new reader understands prototype, real inputs, recorded decision change and limitations in one minute. |
| JE-5 / P0 | **Open.** Complete English project page, verify public links from two machines and explicitly submit. | JE-1, JO-1 and scientific review; save actual platform confirmation. This plan does not send messages or submit on behalf of the team. |
| JO-1 / P0 | **Open.** Jorge produces a ≤30 s English video, or ≤7-slide fallback under the existing team submission checklist. | Start with the strongest evidenced package; v1 need not wait for new HUD/imagery. Source credits and required AI-generated marks remain legible in final exports. Verify final rules with organizer. |
| JO-2 / P0 review, feature conditional | **Not approved as a safety system.** David supplies reviewed mission-margin text/values; Jorge shows only supported estimates already available or feasible before freeze. | DV-2; distinguish historical RAD context from local dose/telemetry. No automatic Go/No-Go, calibrated no-return boundary or guaranteed safe return without a reviewed model. Missing inputs show unavailable, not green/safe. |
| JO-3 / P0 science content, feature conditional | **Open.** Show supported science purpose/imagery for an existing-crop target only after geographic and source checks. | DV-1, DA-1/2; otherwise retain clearly illustrative POIs. Nearby/analog images must not be described as the actual view on arrival. No silent crop or A/B change. |
| JO-4 / P0 | **Partly resolved.** Recorder-based recovery is bundled and public hosting exists. Jorge/Jesús verify the deployed source/package, private-browser and two-machine access, with rollback. | JE-2 selects artifact; exact run/hash, offline backend behavior and labels checked. A generated demo is not planner/execution proof. |
| DI-1 / P0 | **Partly resolved.** Continuous MOCK human recovery and estimated-terrain consumer are published. Diego supports the remaining C3 boundary until the cut and records blockers. | Jesús handles execution, David scientific gates; do not reassign solved NON_CELL_CENTER/loader fixes. |
| DI-2 / P0 fallback | **Existing artifact available.** Reuse the exact recorded real-planner recovery instead of fabricating another route or running a new crop merely for presentation. | If a different scientific target is accepted, require its actual matching dataset/config/output before claiming a route. Label planner-only results separately from executed records. |
| DI-3 / P0 | **Open delivery text.** Diego supplies 3–4 English sentences on FAST/SAFE, constraints, return and contradiction/replan behavior. | Tie statements to recorded evidence; costs remain model estimates and scientific API integration is pending. |
| DA-1 / P0 | **Research progressed; operational selection open.** Daniel + David verify whether a scientifically supported target lies in the chosen existing crop and resolve ENU/datum/coverage. | Research shortlist is not a delivered map. Default preserve current crop. Any recentering needs explicit owner decision and geometry/consumer review before the cut; expansion is paused. |
| DA-2 / P0 source curation, feature conditional | **Open.** Daniel curates 2–4 usable real rover images if coverage/source evidence supports them. | ID, camera, sol/time, product location, rights/credit and relation to the proposed stop; label analogs. No inferred target-scale metric measurement from appearance. |
| DA-3 / P0 | **Largely implemented; final claim audit open.** MGS/MOLA ingestion and traceability were corrected in PR28. Daniel supplies the English resource-to-contribution table for final material. | Pin actual product/window/native scale/processing/hash. Separate planner inputs, display-only context, analogs and unimplemented ideas; more listed sources does not prove more decision inputs. |
| DA-4 / paused P1 | **Accepted.** Larger maps, varied scenes, H-DAN-01 and optional layers are deferred until after submission; preserve existing work. | D-DEL-03 supersedes the earlier “continue now” expansion allocation. No deletion or lost research. |
| DV-1 / P0 | **Research progressed; approval open.** David turns the local shortlist into a reasoned existing-crop science statement if supportable. | Daniel confirms coverage/registration before any operational POI; do not present proposed sectors as approved targets or historical NASA discoveries as new system detections. |
| DV-2 / P0 | **Open review.** David defines source-supported advisory wording for resources, slope and contextual radiation, with uncertainty and applicability limits. | JZ-P01..07 unchanged. No new NASA safety threshold or certification. Separate flight altitude, ground z, sensor coverage and historical atmosphere/radiation references. |
| DV-3 / P0 | **Open.** Review every final claim, image credit and English video/page/deck before organizer handoff. | JO-1, JE-4 and DA-3; remove unsupported “live safety check”, “return guaranteed” and similar safety language from the proposed script. |
| DV-4 / P0 | **Open for any new full run.** David accepts/rejects the exact recorded scope from task/work/traversal/resource evidence. | JE-2; distinguish successful mission, correct rejection and the already demonstrated narrower human return. No approval from animation or a COMPLETE field in a script. |

## Presentation, provenance and final gate

Present the evidenced sequence: real orbital input → estimated route candidate
→ simulated contradiction → stopped human and revised route → recorded return.
Use a public prototype/replay description, not “live safety check” or a claim
that a 2 km map implies a 2 km feasible walk. The optional broader illustrative
scene can explain the concept under its own label. A video or deck must identify
which sequence is recorded and which is illustrative.

No new radiation-dose calculation, medical/safety recommendation or Go/No-Go
threshold is introduced here. Static atmospheric/radiation references remain
context unless their source, location/time transfer, shielding and model limits
are reviewed. Real NASA imagery needs source credits; generated media need
applicable visible AI markings and metadata. Preserve logo/watermark/third-party
credits already in main; audit the rendered final material, not only the README.

Before submission verify English material, media duration/slide count, final
public URLs and exact source/package revision; two-machine/private-browser
backend-off replay; reference isolation; source-to-claim lineage; AI disclosures;
scientific review; organizer endorsement/corrections; explicit platform receipt.
Follow [competition](competition.md), [NASA traceability](nasa_traceability.md)
and [AI usage](AI_USAGE.md). Keep contact details, detailed hours and local
campaign/science drafts out of Git. No pending cost implementation or other
chat's source changes are included in this documentation cut.
