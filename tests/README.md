# Verification areas

contracts validates interchange and the gateway HTTP contract without ROS.
unit covers the gateway store and replay package rules without ROS.
contract and integration need a built ROS 2 workspace and are skipped without it.
planning, mapping, mission, integration and e2e are handoff areas for the cases
in docs/requirements.md. Empty areas are not test passes. Node tests live in web.
Label synthetic fixtures; keep hidden reference out of planner/mission/web inputs.
