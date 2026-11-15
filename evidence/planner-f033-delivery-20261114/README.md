# Remaining-resource guard: delivery revalidation

Published main baseline: b5dc681bb51f8c5f1028e75581c14a1d5c61bb71.
No PR implementation imported. No new commit or publication made.

Read validation.json for exact counts, skip reasons, source hashes, preserved
historical evidence and limitations. JUnit files contain actual software results,
not scientific observations. Selections overlap and must not be added.

Reproduce from repository root with existing Python 3.12 .venv dependencies:

```powershell
.venv\Scripts\python.exe -m pytest tests/planning -q -p no:cacheprovider --basetemp=tmp/f033-delivery-plan --junitxml=tmp/f033-delivery-plan.xml
.venv\Scripts\python.exe -m pytest tests/planning/test_f033_resource_guard.py tests/planning/test_replan_policy.py tests/planning/test_d07_twenty_metres.py -q -p no:cacheprovider --basetemp=tmp/f033-delivery-focused --junitxml=tmp/f033-delivery-focused.xml
.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider --basetemp=tmp/f033-delivery-full --junitxml=tmp/f033-delivery-full.xml
.venv\Scripts\python.exe scripts/check_repository.py
git diff --check
```

From web, npm test and npm run build passed. Existing Node24.18.1 differs from
the pinned24.18.0 by a patch; no installation or pin change was made.

Fresh native ROS validation could not start: Ubuntu24.04 WSL returned
HCS/ERROR_NO_SYSTEM_RESOURCES before shell/colcon/pytest execution, twice. No ROS
test from this delivery cut is recorded as passed or pytest-skipped. Intended
target checks remain colcon build, interface inspection and planning/contract/
mission/unit pytest, followed by separate full integration acceptance.

Historical guard evidence on main0339bbd contains 946 passed/1 skipped for the
native Jazzy selection, eight packages built and six messages/two services
inspected. Relevant source hashes still match; this is supporting historical
compatibility evidence only. It is not a final-baseline ROS/integration pass.
Keep real execution, same-run replay and scientific agreement gates open.

AI assistance for generated code/test/document construction is declared in
docs/AI_USAGE.md and docs/ai_usage.json; test outputs represent actual executions.
