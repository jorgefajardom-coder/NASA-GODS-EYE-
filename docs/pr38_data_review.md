# PR38 auxiliary-context correction handoff

Source: PR38 `bd8c2717b5e74314655451049dbb698f064e73d9` over main `9013beb`.
Current auxiliary contract: [AUXILIARY_LAYERS.md](AUXILIARY_LAYERS.md).

- Require the canonical public terrain and its valid DEM before any auxiliary-generation network or output operation. Grid overrides assert the existing geometry; they cannot manufacture another crop or zero elevation.
- Bind visual sidecars to dataset, prior hash, datum, CRS, planetary/grid origins, dimensions, orientation and cell-centre axes. Constrain file paths and require hashes, shapes, dtypes, finite axes and known public array names. The node helper independently checks alignment before publishing.
- Validate HTTP 206 and Content-Range before reading any body. Bound reads to the expected size plus one byte and reject excessive, missing or truncated bodies, including coalesced ranges.
- Preserve existing acquired raster, PNG and geology bytes. Describe DN/slope categories as estimated visual proxies, not mapped facies or per-agent passage authorization. Preserve canonical -1/0/100 traversability independently of the auxiliary RViz palette.
- Declare nav_msgs as a runtime dependency and add an actual ROS data-node consumer case. No canonical ROS fields, version or production scientific parameters changed.

Validation: native full Python 1214 passed, 24 platform/ROS skips; focused auxiliary tests103 passed/2 skips. HTTP targeted tests51 passed. Repository checker/diff check passed. The initial negative auxiliary suite reproduced29 failures before the fix; corrected tests pass. Jazzy built all eight packages, inspected six messages/two services, and passed all169 selected tests with no skips, including the actual data-node subscriber; no remote data was downloaded or regenerated.

Jesus reviews integration, Daniel provenance/alignment, and David scientific interpretation; no semantic freeze or operational approval is implied. Source and tests remain separate from the height branch and any unfinished scientific-cost draft.

Delivery: Jesus hands the exact sealed package to the organizer at20:00 America/Bogota today15 November; final deadline23:59, target22:00 after explicit endorsement. Contact is confirmed; endorsement of the final revision and submission receipt remain pending. No external message or submission is performed by this work.
