# Simulation adapter scaffold

Owner: Jesus (integration), Daniel (observations), David (model approval).
R02/R06/R13; F05; SimulationAdapter; executable `sim_node`.

The node starts and emits a warning; it publishes no clock, state or observation.
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
All are pending. Maintainer contact and license await team confirmation.
