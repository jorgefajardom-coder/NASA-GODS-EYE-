# Reproduction, figures and evidence

[Home](Home.md) · [Experimental method](07-Experimental-Method.md) · [Case studies](08-Case-Studies.md)

Reproduction begins by identifying the unit of evidence. A teaching diagram is reconstructed from its drawing rules. A model example is recalculated from its profile and equations. A recorded case is checked against its original input hashes, timeline and ledger. These operations answer different questions and are described separately below.

## Documentation snapshot

The draft was prepared on 15 November 2026 in the mission worktree. The inspected branch HEAD is `5220bdd8314f6568a5211c5821adfe4bafb68b48`; fetched main is `9013bebf2400d605f5a3d68e79dadbd5d1c57d03`. Local research artifacts used by the case studies remain identified separately from those Git revisions. The [audit input record](audit/inputs.json) stores exact hashes of the documents, model and case inputs used in this cut.

The analytical Bunsen experiment used planner source `64985e7b4b69ac9683661db4842885d5a8293695`. The overnight broad audit froze `7ad605039a524d5b5cbe2c983f2da9113f8b1ce9`. The actual Web replay capture used viewer source `9013bebf2400d605f5a3d68e79dadbd5d1c57d03`. Naming these revisions separately avoids attributing all results to a later viewer build.

## Rebuild the explanatory graphics

From the repository root, use a Python environment with NumPy, Matplotlib and Pillow, then run:

```sh
python docs/wiki/tools/build_figures.py
python docs/wiki/tools/audit_publication.py
```

The drawing script reads the existing scientific estimator and proposed profile registry. It reads the recorded analytical case and its public terrain crop. It does not invoke ROS, a planner, a simulator or a technical build. The generated-asset manifest records input hashes and actual library versions.

During preparation, missing plotting libraries were installed under the Git-ignored `.local/wiki-figure-deps` directory. This isolated documentation environment leaves the application's dependency declarations unchanged. For a different workstation, a separate virtual environment can provide the three libraries. Exact versions used for this cut are listed in [the asset manifest](assets/manifest.json).

The conceptual cover is an image-generation output. Its saved file, prompt and hash are in [the cover provenance record](audit/cover-provenance.json); it is retained as an authored illustration rather than reconstructed by the plotting script. Generic vehicles and terrain introduce the cooperative roles without incorporating NASA insignia or mission branding.

## Reading the visual material

| Media type | Interpretation | Source of reproduction |
|---|---|---|
| Conceptual diagram | Explains a dependency or definition. | Drawing code and caption. |
| Model calculation | Shows estimates from stated equations and inputs. | Existing estimator, proposed profiles and worked example. |
| SIMULATED analytical case | Presents the recorded hypothetical mission. | Raw case, accepted observations and public terrain. |
| Conceptual cover | Introduces complementary agent roles. | Saved image-generation output and provenance. |

Every generated PNG carries a visible `AI-generated` footer. Every GIF frame includes the footer, and its comment metadata records its origin. The asset manifest identifies the figure's category and sources. This lets a reader distinguish the pedagogical drawing from a data-bearing plot without interrupting the scientific explanation.

For readers who prefer a still image, each animation has a static alternative:

- [Prior and observation: still](assets/prior-observation-poster.png) / [animation](assets/prior-observation.gif).
- [Mission decisions: still](assets/mission-decisions-poster.png) / [animation](assets/mission-decisions.gif).
- [Recorded adaptation: still](assets/adaptation-poster.png) / [animation](assets/adaptation.gif).

The adaptation GIF samples the recorded timeline at condensed display intervals. It retains source timestamps, phase order and resource values. The 3D video linked in Chapter 8 uses the same recorded analytical run in the actual published Web viewer, with its own capture and finalization receipts.

## Inspect the recorded cases

The principal analytical record is [experiment.json](../../evidence/mission-cost-experiment-20261115-local-v2/experiment.json). Its [independent audit](../../evidence/mission-cost-experiment-20261115-local-v2/analytical-audit.json) checks resource closure, identities, journal recovery and cost contexts. The [map-window comparison](../../evidence/mission-3d-video-20261115-local/map-analysis/crop-comparison.json) records the two fixed requests on both map sizes. The [overnight report](../../evidence/overnight-mission-research-20261115-v3/README.md) records the wider research design, partial coverage and outcome catalogue.

The figure builder resolves terrain through its hashed repository-relative path. The original experiment also contains a historical absolute machine path. That stored field remains unchanged; it is not used as a portable location or as a substitute for the input hash.

Input documents that evolve after a sealed result are retained as versioned copies in that result's provenance chain. For this Wiki cut, the [preservation record](audit/previous-packet-preservation.json) retains the AI declarations as they stood when the preceding 3D packet was sealed. The copies keep their exact bytes with a `.sealed` archive suffix, preserving their historical link context. The current declarations include this documentation work.

## Documentation audit

The original local Wiki checker verified local links, required pages, bold-markup absence, figure hashes, visible PNG footers and every decoded GIF frame; it also recalculated the directed model examples. Its record is preserved as [the local audit](audit/report.json). The publication checker verifies the complete reader structure, bounded payload and links against the frozen main baseline. It confirms that all21 assets are byte-identical to those already checked for visible watermarks, including57 decoded GIF frames. Its machine-readable record is [the publication audit](audit/publication-report.json).

Visual review supplements those checks. The figures are inspected at full size for clipped labels, causal arrow order, coordinate interpretation and legible watermarks. Contact sheets support comparison, while individual frames are used to check the animations. These checks concern the documentation and graphics. Earlier software and platform validation results remain attached to their original experimental packets.

The repository checker also passes. Its first run treated the archived Markdown copies as current pages and resolved their historical relative links from the archive directory. Explicit archive suffixes resolved that classification issue while retaining the original bytes; both checker logs remain in `audit`. Application, frontend and ROS tests were not repeated for this documentation-only cut.

The complete draft is prepared for owner audit. Publishing the Wiki, accepting proposed scientific parameters and endorsing the final competition package each retain their own review records. This documentation work changes no implementation, runtime configuration or shared contract.

## Publication package and historical archive

The [publication manifest](audit/publication-manifest.json) identifies every file in this bounded export. It includes the39 linked supporting records, the public Bunsen terrain needed to rebuild the figures, and final-video receipts. The [local draft manifest](audit/local-draft-manifest.json), previous-packet preservation records and original checks remain historical provenance.

The original `audit_wiki.py` verifies the3394-artifact local archive and is retained as that historical procedure. Running it requires the original local raw-capture/research archive; this publication does not upload or claim to contain that archive. Use `audit_publication.py` to verify this exported package. It uses only Python's standard library and resolves unchanged source links against the recorded main baseline when checking a prepared overlay.

Inline reproduction commands in supporting historical reports describe their original local research environment. The Wiki publication adds documentation, public/analytical records and media while leaving application implementations and experimental settings at their published source revisions. Owner scientific review remains pending.
