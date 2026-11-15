# Local synthetic terrain evidence

Source: d737e0fa plus hashed diagnostic/test changes in validation.json.
Run: python -m pytest -q -o junit_family=xunit1 --junitxml=tmp/terrain-verified.xml
Final: 1268 passed,22 skipped,0 failed;32 new cases passed.
comparisons.json retains30 directed scenario/agent comparisons; two further cases test scientific directional costs and orbital-step rejection.
Timings are single computational observations, not a performance guarantee.
Raw unsuccessful fixture attempts remain under ignored tmp, described in validation.json.
No Mars microtopography, evaluator reference, ROS activation or physical certification.
