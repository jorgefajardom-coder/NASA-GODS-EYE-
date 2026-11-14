# Shared configuration

These are specification templates, not active node parameters. Fields left null
must be supplied and approved, not treated as zero or unlimited resources.
David owns mission/agent semantics; Daniel owns terrain provenance and coordinates;
Jesus owns integration. Keep numeric illustrative values in a separately labeled
scenario_demo.yaml if added. None is a certified EVA/flight/mobility parameter.

Runtime ROS parameters live in node-specific launch/config once implemented.
Set an agreed ROS_DOMAIN_ID in the environment before team ROS tests. Gazebo
must supply /clock with use_sim_time enabled; the skeleton creates no clock.
