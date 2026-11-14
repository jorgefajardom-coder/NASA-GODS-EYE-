# Integration tests

These need a built and sourced ROS 2 workspace; without it they are skipped.

`test_vertical_mock.py` and `test_replay_package.py` launch the MOCK vertical
and check the integration plumbing through the gateway: identifiers, versions,
ordering, error states and the replay package. The routes come from a mock
planner, so these tests are not acceptance evidence for any mission requirement.
The cases assigned in docs/requirements.md remain to be implemented against the
real modules.

`test_vertical_planner.py` puts the real planner on the synthetic MOCK terrain.
`test_terrain_batch.py` checks the real data and mapping providers against the
real planner without a mission. `test_vertical_terrain.py` launches the whole
vertical with `terrain:=real planner:=real`: unobserved Jezero terrain answers
`UNKNOWN`, a SIMULATED observation that repeats prior heights yields map
version 2 and a FEASIBLE route through the gateway, and the recorded package
validates offline. Mission and agents are still MOCK in all of them, so none is
mission evidence.
