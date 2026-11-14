# Real mission provider handoff verification

Source255be89e4d3dab2620ab0a1a2c4a3d63b26d650f combines the unchanged mission
implementation8f69f62 with main6ec9b84. This is software-provider integration,
not operational mission acceptance. Logs/JUnit and exact input hashes accompany
validation.json.

Actual outcomes: Windows full suite636passed/15skipped. Ubuntu24.04/Jazzy builds
all eight packages and inspects six messages/two services; selected mission,
contract, integration, unit and gateway suites556passed/one optional snapshot
skip. Ten focused launch/real-consumer cases pass, including exactly one mission
service, the actual planner and real MissionManager behind HTTP, model-not-agreed
blocking with empty route, and conflicting-request rejection. Four web tests,
TypeScript/Vite build, repository checks and whitespace checks pass.

Commands:

```sh
python -m pytest -q --basetemp .local/mission-data-native
python scripts/check_repository.py
cd web
npm test
npm run build
```

On Jazzy, activate a Python environment with requirements-dev.txt and the existing
src/mge_gateway/requirements.txt, then run scripts/validate_mission_ros.sh. It
copies public source/config/tests/data/docs into a fresh ASCII workspace and
propagates the selected Python interpreter into colcon/CMake. Local final
validation used the same source-copy/build/inspect flow plus:

```sh
python -m pytest tests/contract/test_mission_launch.py tests/integration/test_vertical_mission.py -q
python -m pytest tests/mission tests/contract tests/integration tests/unit tests/contracts/test_gateway.py -q
```

HTTP/test packages use the repository constraints in an isolated system-site
Python environment; target ROS and scientific-computing system packages stay
available. The toy integration clock and terrain/agents are explicitly synthetic.
The source module's model/profile approval gates remain unchanged. Earlier
environment/preflight failures and their correction are identified in validation.json;
only final successful results are claimed above. Full science/real execution,
stop feedback and the known numerical model disagreements remain pending.
