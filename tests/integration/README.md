# Integration tests

These need a built and sourced ROS 2 workspace; without it they are skipped.

`test_vertical_mock.py` and `test_replay_package.py` launch the MOCK vertical
and check the integration plumbing through the gateway: identifiers, versions,
ordering, error states and the replay package. The routes come from a mock
planner, so these tests are not acceptance evidence for any mission requirement.
The cases assigned in docs/requirements.md remain to be implemented against the
real modules.
