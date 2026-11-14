# ICD-ROS2-V1 | Result of one planning request.
# Returned by PlanRoute and embedded in MissionState for the route in force.
# UNKNOWN does not mean NO_PATH. A decision computed on an older map version
# is answered with STALE_MAP or dropped by the consumer.

string STATUS_FEASIBLE=FEASIBLE
string STATUS_UNKNOWN=UNKNOWN
string STATUS_NO_PATH=NO_PATH
string STATUS_INSUFFICIENT_BUDGET=INSUFFICIENT_BUDGET
string STATUS_STALE_MAP=STALE_MAP
string STATUS_ERROR=ERROR

string MODE_FAST=FAST
string MODE_EFFICIENT=EFFICIENT
string MODE_SAFE=SAFE

std_msgs/Header header          # frame_id = "map", stamp = simulated time
string run_id
string request_id               # echoes the request
string route_id                 # unique per route version; empty if not FEASIBLE
string agent_id
string mode                     # MODE_*
uint32 map_version_used
string status                   # STATUS_*
string reason_code              # machine-readable, UPPER_SNAKE_CASE
string detail                   # short English sentence for the UI

geometry_msgs/Point[] outbound_path   # start -> goal, cell centres in "map"
geometry_msgs/Point[] return_path     # goal -> return point

float32 travel_time_s           # outbound + service + return, estimated
float32 energy_est_wh
float32 oxygen_est_l            # NaN for agents that are not HUMAN
float32 min_clearance_m         # smallest distance to a forbidden cell
float32 reserve_time_s          # left after the plan, estimated
float32 reserve_wh
float32 reserve_oxygen_l        # NaN for agents that are not HUMAN
