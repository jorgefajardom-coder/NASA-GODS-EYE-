# Height reconciliation and delivery handoff

Base: main `9013bebf2400d605f5a3d68e79dadbd5d1c57d03`. Working branch: `codex/closure-height-reconciliation`. This is software reconciliation pending the reviewed PR path, not scientific approval or contract freeze.

## Inputs, outputs and ownership

ROS ICD-ROS2-V1 / package 1.0.0, canonical replay 1.0.0 and public rasters `mge-public-rasters-1.0.0` are unchanged. Input elevation, pose.z and route.z share metres above TerrainMeta.vertical_datum; ENU maps to Three.js (x,z,-y) only for display.

- Jesus: static and kinematic MOCK producers share explicit new-scene initialization; no missing-Z zero fallback. A NEW_SCENE/SIMULATED/PUBLIC_PRIOR declaration binds dataset, prior hash and datum. New parked-drone/ground poses use that scene surface. Explicit incompatible XYZ and NoData fail; existing telemetry is never projected.
- Jesus/Diego: the follower requires finite full XYZ within the existing 1e-6 m model tolerance before motion. A rejection retains HALTED, pose and resources. A surface proposal does not authorize flight. Goal/base horizontal target semantics remain unchanged.
- Diego/Daniel: planner metadata retains and immutably compares planetary origin, checksum and sources; a changed duplicate cannot retain the old snapshot.
- Jorge: renderer and visual ground consumers share actual Float32 vertices, triangle topology and animated geometry. Visual draping does not change recorded pose or operational geometry.
- David: review scenario/scientific assumptions and claims. Parked drone is the owner-selected scope; flight, physical validation and coordinated three-role acceptance remain open.

## Verification ledger

- Native Python: 1200 passed, 23 platform/ROS skips, one existing Starlette deprecation warning. Evidence: `.local/height-native-clean.xml`.
- Web: Node 24.18.0, 321 passed, one existing skip; production build passed. Eight new regressions compare sampling with independent Three.js raycasts, including Gale, subdivision, negative heights, NoData, exaggeration and morph.
- Jazzy initial cut: eight packages built and six messages/two services inspected. ROS suites produced 806 passed, one skip and two failures in the new test clock stub. The harness was corrected to rclpy Time and all three focused ROS executor cases passed. A persistent ASCII workspace rebuilt all eight packages; fresh distinct run `height-recovery-20261115-01` passed in116.84s with package validator empty; source receipt matches223 files to implementation commit742eed5.
- Historical `recorded-recovery-001` files remain byte-identical. Its drone IDLE z=0 over ground -2571.2312 m is retained as a documented limitation, not evidence of flight.

Initial test-environment attempts failed on shared Windows temporary-directory permissions and a misplaced disposable WSL venv. The venv's five verified generated paths were removed without touching source files; the native suite passed with worktree-local basetemp. Use file-based WSL scripts and the isolated persistent cache venv.

## Recording and replay acceptance

Create a fresh recorder package with an explicit distinct run identity, source/configuration hashes, MOCK provenance and no overwrite. Consume that exact package through the existing adapter and viewer. Verify initial parked drone, XYZ-preserving stop/replan/return, resources, map versions and final READY. Do not edit the historical package or manufacture COMPLETE/three-role events. Preserve failed cuts and distinguish browser evidence from analytical pilot media.

PR37 corrections are published at `91e1d1b` with metadata-only follow-up `0f93652` with native 1140 passed/22 skips, web323 passed/one skip and build/checker success; exact-head CI and scientific review are separate. PR38 correction is in progress on its own isolated source, not included in this height branch.

## Delivery coordination confirmed by the owner

All time before 20:00 America/Bogota on 15 November 2026 is available for isolated pilots and validated integration. Keep a continuously usable stable package; only fully reviewed/tested/sealed candidates replace it. No earlier 17:00/19:00 freeze applies.

At 20:00 Jesus delivers the exact package to the local organizer; David is backup. The final submission deadline confirmed by the owner is 23:59, with an operational target of 22:00 after endorsement. No changes are planned after the organizer handoff. Explicit endorsement of that exact revision, any required corrections and final submission receipt are still required; contact confirmed alone does not close JES-07/AC-10. This work sends no external message or submission.

Fresh package and immutable receipts: [height evidence](../evidence/height-reconciliation-20261115/README.md). Recorded entry002 is URL-selected; the six-zone default/selector stays illustrative.
