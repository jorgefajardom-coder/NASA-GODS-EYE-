# Shared configuration

These are specification templates, not active node parameters. Fields left null
must be supplied and approved, not treated as zero or unlimited resources.
David owns mission/agent semantics; Daniel owns terrain provenance and coordinates;
Jesus owns integration. Keep numeric illustrative values in a separately labeled
scenario_demo.yaml if added. None is a certified EVA/flight/mobility parameter.

Runtime ROS parameters live in node-specific launch/config once implemented.
Set an agreed ROS_DOMAIN_ID in the environment before team ROS tests. Gazebo
must supply /clock with use_sim_time enabled; the skeleton creates no clock.
# Mission scientific profiles

`science_profiles.proposed.json` contains source-traced activity/grade model
parameters and sensitivity ranges. Its status remains proposed: loading it for
formula estimation is not permission to execute a mission. Existing mission and
agent templates retain pending budgets, coordinates and scientific approval.

`scenario_demo.yaml` is an explicitly illustrative fixture for controlled tests;
its geometry, budgets and tolerances are not NASA observations or real limits.
Operational configuration must supply an approved scenario separately. Never
promote the illustrative fixture or proposed profile registry silently.

The planner profile projection is approximate and does not establish model
agreement. Review [scientific models](../docs/science_models.md) and
[integration dependencies](../docs/mission_handoff.md) before enabling routes.
