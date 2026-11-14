# Resources are simulated estimates, not certified EVA limits.
string HUMAN=human
string DRONE=drone
string ROVER=rover
std_msgs/Header header
string schema_version
string run_id
string agent_id
string agent_kind
geometry_msgs/Pose pose
geometry_msgs/Twist velocity
string state
float64 timestamp_sim_s
float64 time_remaining_s
float64 energy_remaining_wh
# Zero for non-human agents; oxygen_applicable must be false for them.
bool oxygen_applicable
float64 oxygen_remaining_l
float64 confidence
