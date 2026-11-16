# Operational scientific cost verification

Classification: executed software/model comparisons and actual ROS service tests on declared synthetic terrain. No physical mission or scientific coefficient approval is asserted.

Implementation source: `3830b8b0fb2d6269ac3e73e8b8fd8de71c876334`; prior main: `d13a4b3f1035260cebf9f065472c56cc53158401`.

| Consumer | Agreement | Other outcomes |
|---|---:|---|
| Default scientific service facade, exact committed search | 7/7 | Zero errors/non-feasible cases |
| Explicit legacy cost control, same committed search | 1/7 | Six numerical disagreements, zero errors |
| Real RegisterPlanningContext → PlanRoute DDS service | 7/7 | Independent cost/reserve audit for human, rover and drone cases |

The [scientific report](scientific/conformance.json) and [legacy control](legacy/conformance.json) retain original outputs, source/profile hashes, run IDs, commands and tolerance values. The service test in the [Jazzy JUnit record](ros/regression.xml) is `test_all_seven_published_conformance_cases_through_actual_ros_service`; it sends all seven controlled cases through the real nodes, including sample/inspect/observe and explicit waiting. Additional actual-service tests distinguish equal-duration inspection and sampling, reject missing/conflicting context and exercise the real MissionNode producer. The manager approval gate remains closed by default.

`authorization: BLOCKED` remains intentional in both diagnostic reports: a numerical test does not grant profile or operational mission approval. The scientific report's reason is `ALL_CASES_AGREE`; the legacy report retains `MODEL_DISAGREEMENT`. Existing historical1/7 records are unchanged.

Validation: 1,346 Windows Python tests passed (27 skipped), 871 Ubuntu/Jazzy contract/mission/integration tests passed (one skipped: optional historical snapshot), 412 frontend tests passed (one skipped), frontend build and repository checks passed. Colcon built all eight packages and the added context interface was inspected. The ROS test environment uses an isolated domain and task-owned dependencies; no other ROS session is modified. Full versions, source/checkout hashes and limitations are in [validation](validation.json) and [implementation files](implementation-files.json).

The compatibility migration is documented in [scientific cost integration](../../docs/scientific_cost_integration.md): old IDL fields are unchanged, the default service now requires registered immutable context, and interface package2.0.0 records that changed prerequisite. Legacy operation requires explicit opt-in. Approval, execution evidence and owner contract review retain their separate gates.

AI use: OpenAI Codex assisted the integration, tests, diagnostic orchestration, evidence assembly and explanation. The test maps are synthetic; these records are not observational NASA data. No model coefficient, budget, slope/uncertainty limit, reserve or comparison tolerance was changed to obtain agreement.
