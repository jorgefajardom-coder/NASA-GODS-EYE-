# Simulation adapter scaffold

Owner: Jesus (integration), Daniel (observations), David (model approval).
R02/R06/R13; F05; SimulationAdapter; executable `sim_node`.

The `sim_node` placeholder starts and emits a warning; it publishes no clock,
state or observation. The existing `mock_agents` executable is also preserved:
it publishes clearly labelled, static MOCK agent states from an agents YAML file.
Its poses do not move and resources do not deplete. `smoke.launch.py` starts that
mock publisher using wall time by default, for graph inspection only; its output
is not a simulated mission, a perception result or resource validation.
No Gazebo world, physical dynamics or real perception is supplied. First implement
a clearly labelled SIMULATED adapter with agent IDs matching shared configuration.
Then validate observation footprints, simulated clock and one map update per event.
The evaluator's hidden reference must never be supplied to the route planner.

Gazebo Harmonic is the target. `ros_gz_bridge` may bridge supported native types
such as Clock, Image, Odometry and Twist. Custom `mge_interfaces` messages stay
inside ROS and are serialized by the web gateway. Add bridge mappings only after
checking actual Gazebo topic names and types; no invented mapping is included.

Acceptance: clock consistency, duplicate observation rejection with Mapping,
three-agent startup, and an evidence run showing an observation causes replanning.
All are pending. The existing MIT package metadata/version are preserved;
maintainer contact is a placeholder and repository/asset licensing needs review.
